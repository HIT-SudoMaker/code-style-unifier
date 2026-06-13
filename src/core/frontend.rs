use unicode_width::UnicodeWidthStr;

use crate::core::error::{CoreError, Result};
use crate::core::evidence::{
    BlockRegionFact, CommentRegionFact, DependencyEdgeFact, DependencyGroup, DocRegionFact,
    EvidenceStore, ExpressionFact, ExpressionKind, LineSpanFact, ModuleUnitFact, PublicSurfaceFact,
    SymbolFact, SymbolKind, SymbolVisibility, TextRole, TextSpanFact,
};
use crate::core::issue::Language;
use crate::core::scanner::{FileUnit, WorkspaceState};

/// 从扫描状态提取文本、符号和结构化证据
pub fn extract_text_evidence(state: &WorkspaceState) -> Result<EvidenceStore> {
    extract_evidence(state)
}

fn extract_evidence(state: &WorkspaceState) -> Result<EvidenceStore> {
    let mut store = EvidenceStore::empty(state);
    for file in &state.files {
        let bytes = std::fs::read(&file.path).map_err(|source| CoreError::Io {
            path: file.path.display().to_string(),
            source,
        })?;
        let module_id = add_module_unit(file, "", &mut store);
        let Ok(source) = String::from_utf8(bytes) else {
            continue;
        };
        extract_lines(file.id.as_str(), &source, &mut store);
        extract_language_facts(file, &source, &module_id, &mut store);
    }
    Ok(store)
}

fn extract_language_facts(
    file: &FileUnit,
    source: &str,
    module_id: &str,
    store: &mut EvidenceStore,
) {
    update_module_unit(file, source, store);
    match file.language {
        Language::Python => {
            extract_python_text(file.id.as_str(), source, store);
            extract_python_facts(file, source, module_id, store);
        }
        Language::Rust => {
            extract_c_family_text(file.id.as_str(), source, store);
            extract_rust_facts(file, source, module_id, store);
            link_preceding_docs(file, store);
        }
        Language::C | Language::Cpp => {
            extract_c_family_text(file.id.as_str(), source, store);
            extract_c_family_facts(file, source, module_id, store);
            link_preceding_docs(file, store);
        }
    }
    refresh_module_doc_flag(file, store);
}

fn add_module_unit(file: &FileUnit, source: &str, store: &mut EvidenceStore) -> String {
    let line_count = source.lines().count().max(1);
    let module_hash = hash_text(&file.relative_path);
    let module_id = stable_id(&file.id, "module", "unit", 1, 1, &module_hash);
    let (include_guard, pragma_once) = if matches!(file.language, Language::C | Language::Cpp) {
        detect_include_boundary(source)
    } else {
        (None, false)
    };
    let has_module_doc_region = store
        .doc_regions
        .iter()
        .any(|doc| doc.file_id == file.id && doc.symbol_name == "__module__");

    store.module_units.push(ModuleUnitFact {
        id: module_id.clone(),
        file_id: file.id.clone(),
        language: file.language,
        path: file.relative_path.clone(),
        range: format!("1:1-{line_count}:1"),
        has_module_doc_region,
        is_header: is_header_path(&file.relative_path),
        include_guard,
        pragma_once,
    });
    module_id
}

fn update_module_unit(file: &FileUnit, source: &str, store: &mut EvidenceStore) {
    let line_count = source.lines().count().max(1);
    let (include_guard, pragma_once) = if matches!(file.language, Language::C | Language::Cpp) {
        detect_include_boundary(source)
    } else {
        (None, false)
    };
    if let Some(module) = store
        .module_units
        .iter_mut()
        .find(|module| module.file_id == file.id)
    {
        module.range = format!("1:1-{line_count}:1");
        module.include_guard = include_guard;
        module.pragma_once = pragma_once;
    }
}

fn refresh_module_doc_flag(file: &FileUnit, store: &mut EvidenceStore) {
    let has_module_doc_region = store
        .doc_regions
        .iter()
        .any(|doc| doc.file_id == file.id && doc.symbol_name == "__module__");
    if let Some(module) = store
        .module_units
        .iter_mut()
        .find(|module| module.file_id == file.id)
    {
        module.has_module_doc_region = has_module_doc_region;
    }
}

fn extract_lines(file_id: &str, source: &str, store: &mut EvidenceStore) {
    for (index, line) in source.lines().enumerate() {
        let line_hash = hash_text(line);
        store.line_spans.push(LineSpanFact {
            id: stable_id(file_id, "line", "line", index + 1, 1, &line_hash),
            file_id: file_id.to_string(),
            line: index + 1,
            visual_width: UnicodeWidthStr::width(line),
            line_hash: format!("blake3:{line_hash}"),
            suppression: line.find("csu:").map(|_| line.trim().to_string()),
        });
    }
}

fn extract_python_text(file_id: &str, source: &str, store: &mut EvidenceStore) {
    let lines: Vec<_> = source
        .lines()
        .enumerate()
        .map(|(index, line)| {
            if index == 0 {
                line.strip_prefix('\u{feff}').unwrap_or(line)
            } else {
                line
            }
        })
        .collect();
    let mut index = 0;

    if let Some(module_doc_index) = first_python_statement_index(&lines) {
        if let Some(docstring) = parse_docstring(&lines, module_doc_index) {
            add_python_docstring(store, file_id, "__module__".to_string(), &docstring);
        }
    }

    while index < lines.len() {
        let line_number = index + 1;
        let line = lines[index];

        if let Some(signature) = python_signature_at(&lines, index) {
            let docstring_index = next_non_empty_line(&lines, signature.end_index + 1);
            if let Some(docstring) =
                docstring_index.and_then(|index| parse_docstring(&lines, index))
            {
                add_python_docstring(store, file_id, signature.name, &docstring);
                index = docstring.end_line;
                continue;
            }
            index = signature.end_index + 1;
            continue;
        }

        if let Some(comment) = line_comment(line, line_number) {
            let text_hash = hash_text(&comment.text);
            let text_id = stable_id(
                file_id,
                "text",
                "comment",
                comment.text_start_line,
                comment.text_start_col,
                &text_hash,
            );
            store.text_spans.push(TextSpanFact {
                id: text_id.clone(),
                file_id: file_id.to_string(),
                range: format!(
                    "{}:{}-{}:{}",
                    comment.text_start_line,
                    comment.text_start_col,
                    comment.text_end_line,
                    comment.text_end_col
                ),
                role: TextRole::Comment,
                normalized_text: comment.text.clone(),
                text_hash: format!("blake3:{text_hash}"),
                terminal_punctuation: comment.text.chars().last(),
            });
            store.comment_regions.push(CommentRegionFact {
                id: stable_id(
                    file_id,
                    "comment",
                    "line_comment",
                    comment.region_start_line,
                    comment.region_start_col,
                    &text_hash,
                ),
                file_id: file_id.to_string(),
                range: format!(
                    "{}:{}-{}:{}",
                    comment.region_start_line,
                    comment.region_start_col,
                    comment.region_end_line,
                    comment.region_end_col
                ),
                kind: "line_comment".to_string(),
                text_id,
            });
            index += 1;
            continue;
        }

        if let Some(triple) = opening_triple_anywhere(line) {
            index = skip_triple_string(&lines, index, triple);
            continue;
        }

        index += 1;
    }
}

fn first_python_statement_index(lines: &[&str]) -> Option<usize> {
    lines.iter().position(|line| {
        let trimmed = line.trim();
        !trimmed.is_empty() && !trimmed.starts_with('#')
    })
}

fn next_non_empty_line(lines: &[&str], start_index: usize) -> Option<usize> {
    lines
        .iter()
        .enumerate()
        .skip(start_index)
        .find_map(|(index, line)| (!line.trim().is_empty()).then_some(index))
}

fn add_python_docstring(
    store: &mut EvidenceStore,
    file_id: &str,
    symbol_name: String,
    docstring: &Docstring,
) {
    let summary_hash = hash_text(&docstring.summary);
    let text_id = stable_id(
        file_id,
        "text",
        "doc_summary",
        docstring.summary_start_line,
        docstring.summary_start_col,
        &summary_hash,
    );
    store.text_spans.push(TextSpanFact {
        id: text_id.clone(),
        file_id: file_id.to_string(),
        range: format!(
            "{}:{}-{}:{}",
            docstring.summary_start_line,
            docstring.summary_start_col,
            docstring.summary_end_line,
            docstring.summary_end_col
        ),
        role: TextRole::DocSummary,
        normalized_text: docstring.summary.clone(),
        text_hash: format!("blake3:{summary_hash}"),
        terminal_punctuation: docstring.summary.chars().last(),
    });
    let full_text_hash = hash_text(&docstring.full_text);
    let full_text_id = stable_id(
        file_id,
        "text",
        "doc_body",
        docstring.start_line,
        docstring.start_col,
        &full_text_hash,
    );
    store.text_spans.push(TextSpanFact {
        id: full_text_id.clone(),
        file_id: file_id.to_string(),
        range: format!(
            "{}:{}-{}:{}",
            docstring.start_line, docstring.start_col, docstring.end_line, docstring.end_col
        ),
        role: TextRole::Other,
        normalized_text: docstring.full_text.clone(),
        text_hash: format!("blake3:{full_text_hash}"),
        terminal_punctuation: docstring.full_text.chars().last(),
    });

    let doc_hash = hash_text(&docstring.summary);
    store.doc_regions.push(DocRegionFact {
        id: stable_id(
            file_id,
            "doc",
            "doc_summary",
            docstring.start_line,
            docstring.start_col,
            &doc_hash,
        ),
        file_id: file_id.to_string(),
        symbol_name,
        range: format!(
            "{}:{}-{}:{}",
            docstring.start_line, docstring.start_col, docstring.end_line, docstring.end_col
        ),
        summary_text_id: text_id,
        full_text_id: Some(full_text_id),
    });
}

fn extract_python_facts(file: &FileUnit, source: &str, module_id: &str, store: &mut EvidenceStore) {
    let lines = source.lines().collect::<Vec<_>>();
    let mut index = 0;

    while index < lines.len() {
        let line_number = index + 1;
        let line = lines[index];
        let trimmed = line.trim();
        if trimmed.starts_with('#') {
            index += 1;
            continue;
        }

        if let Some(signature) = python_signature_at(&lines, index) {
            extract_python_fact_text(
                store,
                file,
                module_id,
                &lines,
                signature.logical_text.as_str(),
                signature.start_line,
                signature.start_index,
            );
            index = signature.end_index + 1;
            continue;
        }

        if let Some(triple) = opening_triple_anywhere(line) {
            let (segments, next_index) =
                python_fact_segments_skipping_triple_strings(&lines, index, triple);
            for segment in segments {
                extract_python_fact_text(
                    store,
                    file,
                    module_id,
                    &lines,
                    segment.text.as_str(),
                    segment.line_number,
                    segment.start_index,
                );
            }
            index = next_index;
            continue;
        }

        extract_python_fact_text(store, file, module_id, &lines, trimmed, line_number, index);
        index += 1;
    }
}

struct PythonFactSegment {
    text: String,
    line_number: usize,
    start_index: usize,
}

fn python_fact_segments_skipping_triple_strings(
    lines: &[&str],
    start_index: usize,
    first_opening: OpeningTriple<'_>,
) -> (Vec<PythonFactSegment>, usize) {
    let mut fact_chars = Vec::new();
    let mut index = start_index;
    let mut segment_start = 0;
    let mut opening = first_opening;

    loop {
        let line = lines[index];
        append_python_fact_chars(
            &mut fact_chars,
            &line[segment_start..opening.start_byte],
            index + 1,
        );
        append_python_fact_chars(&mut fact_chars, "\"\"", index + 1);

        let after_opening = opening.delimiter_byte + opening.quote.len();
        if let Some(close_offset) = line[after_opening..].find(opening.quote) {
            segment_start = after_opening + close_offset + opening.quote.len();
            if let Some(next_opening) = opening_triple_anywhere(&line[segment_start..]) {
                opening = offset_opening_triple(next_opening, segment_start);
                continue;
            }
            append_python_fact_chars(&mut fact_chars, &line[segment_start..], index + 1);
            return (split_python_fact_segments(fact_chars), index + 1);
        }

        index += 1;
        while index < lines.len() {
            let line = lines[index];
            let Some(close_byte) = line.find(opening.quote) else {
                index += 1;
                continue;
            };

            segment_start = close_byte + opening.quote.len();
            if let Some(next_opening) = opening_triple_anywhere(&line[segment_start..]) {
                opening = offset_opening_triple(next_opening, segment_start);
                break;
            }
            append_python_fact_chars(&mut fact_chars, &line[segment_start..], index + 1);
            return (split_python_fact_segments(fact_chars), index + 1);
        }

        if index >= lines.len() {
            return (split_python_fact_segments(fact_chars), lines.len());
        }
    }
}

fn append_python_fact_chars(output: &mut Vec<(char, usize)>, text: &str, line_number: usize) {
    output.extend(text.chars().map(|character| (character, line_number)));
}

fn split_python_fact_segments(chars: Vec<(char, usize)>) -> Vec<PythonFactSegment> {
    let mut segments = Vec::new();
    let mut current = Vec::new();
    let mut bracket_depth = 0usize;
    let mut paren_depth = 0usize;
    let mut brace_depth = 0usize;
    let mut quote = None;
    let mut escaped = false;

    for (character, line_number) in chars {
        if let Some(active_quote) = quote {
            current.push((character, line_number));
            if escaped {
                escaped = false;
            } else if character == '\\' {
                escaped = true;
            } else if character == active_quote {
                quote = None;
            }
            continue;
        }

        match character {
            '\'' | '"' => {
                quote = Some(character);
                current.push((character, line_number));
            }
            '[' => {
                bracket_depth += 1;
                current.push((character, line_number));
            }
            ']' => {
                bracket_depth = bracket_depth.saturating_sub(1);
                current.push((character, line_number));
            }
            '(' => {
                paren_depth += 1;
                current.push((character, line_number));
            }
            ')' => {
                paren_depth = paren_depth.saturating_sub(1);
                current.push((character, line_number));
            }
            '{' => {
                brace_depth += 1;
                current.push((character, line_number));
            }
            '}' => {
                brace_depth = brace_depth.saturating_sub(1);
                current.push((character, line_number));
            }
            ';' if bracket_depth == 0 && paren_depth == 0 && brace_depth == 0 => {
                push_python_fact_segment(&mut segments, &mut current);
            }
            _ => current.push((character, line_number)),
        }
    }
    push_python_fact_segment(&mut segments, &mut current);
    segments
}

fn push_python_fact_segment(
    segments: &mut Vec<PythonFactSegment>,
    current: &mut Vec<(char, usize)>,
) {
    let text = current
        .iter()
        .map(|(character, _)| *character)
        .collect::<String>();
    let trimmed = text.trim();
    if trimmed.is_empty() {
        current.clear();
        return;
    }
    let line_number = current
        .iter()
        .find(|(character, _)| !character.is_whitespace())
        .map(|(_, line_number)| *line_number)
        .unwrap_or(1);
    segments.push(PythonFactSegment {
        text: trimmed.to_string(),
        line_number,
        start_index: line_number.saturating_sub(1),
    });
    current.clear();
}

fn offset_opening_triple(opening: OpeningTriple<'_>, offset: usize) -> OpeningTriple<'_> {
    OpeningTriple {
        quote: opening.quote,
        start_byte: opening.start_byte + offset,
        delimiter_byte: opening.delimiter_byte + offset,
    }
}

fn extract_python_fact_text(
    store: &mut EvidenceStore,
    file: &FileUnit,
    module_id: &str,
    lines: &[&str],
    fact_text: &str,
    fact_line: usize,
    fact_start_index: usize,
) {
    if let Some((source_name, imported, alias, group, is_relative, is_glob)) =
        python_dependency(fact_text)
    {
        add_dependency(
            store,
            DependencyInput {
                file,
                module_id,
                group,
                source: source_name,
                imported,
                alias,
                line_number: fact_line,
                is_glob,
                is_public: false,
                is_relative,
            },
        );
    }

    if let Some(symbol) = python_symbol(fact_text, file, module_id, fact_line, store) {
        add_symbol(store, symbol);
    }
    for symbol in python_parameter_symbols(
        fact_text,
        file,
        module_id,
        fact_line,
        store,
        lines,
        fact_start_index,
    ) {
        add_symbol(store, symbol);
    }

    if let Some(symbol) = python_logger_symbol(fact_text, file, module_id, fact_line, store) {
        add_symbol(store, symbol);
    }

    if let Some(symbol) =
        python_bool_annotation_symbol(fact_text, file, module_id, fact_line, store)
    {
        add_symbol(store, symbol);
    }

    for type_expression in python_type_expressions(fact_text) {
        add_expression(
            store,
            ExpressionInput {
                file,
                module_id,
                symbol_id: None,
                kind: ExpressionKind::TypeExpression,
                line_number: fact_line,
                text: type_expression.text,
                callee: Some(type_expression.callee),
                arguments: Vec::new(),
            },
        );
    }

    if logging_callee(fact_text).is_some() {
        add_expression(
            store,
            ExpressionInput {
                file,
                module_id,
                symbol_id: None,
                kind: ExpressionKind::LoggingCall,
                line_number: fact_line,
                text: fact_text.to_string(),
                callee: logging_callee(fact_text),
                arguments: call_arguments(fact_text),
            },
        );
    }

    if let Some((callee, arguments)) = python_error_message(fact_text) {
        add_expression(
            store,
            ExpressionInput {
                file,
                module_id,
                symbol_id: None,
                kind: ExpressionKind::ErrorMessage,
                line_number: fact_line,
                text: fact_text.to_string(),
                callee: Some(callee),
                arguments,
            },
        );
    }
}

fn extract_rust_facts(file: &FileUnit, source: &str, module_id: &str, store: &mut EvidenceStore) {
    let mut pending_attributes = Vec::new();
    let mut string_state = RustStringState::Code;
    for (index, line) in source.lines().enumerate() {
        let line_number = index + 1;
        let code_line = rust_code_outside_strings(line, &mut string_state);
        let trimmed = code_line.trim();

        if let Some(attribute) = rust_attribute(trimmed) {
            add_expression(
                store,
                ExpressionInput {
                    file,
                    module_id,
                    symbol_id: None,
                    kind: ExpressionKind::MacroInvocation,
                    line_number,
                    text: trimmed.to_string(),
                    callee: Some(attribute.name),
                    arguments: Vec::new(),
                },
            );
            if !trimmed.starts_with("#![") {
                pending_attributes.push(attribute.text);
            }
            continue;
        }

        if let Some((source_name, imported, is_public)) = rust_dependency(trimmed) {
            add_dependency(
                store,
                DependencyInput {
                    file,
                    module_id,
                    group: dependency_group_for(&source_name, file.language),
                    source: source_name,
                    imported,
                    alias: None,
                    line_number,
                    is_glob: trimmed.contains("::*") || trimmed.ends_with("::*;"),
                    is_public,
                    is_relative: trimmed.contains("crate::") || trimmed.contains("super::"),
                },
            );
        }

        if let Some(symbol) = rust_symbol(
            trimmed,
            file,
            module_id,
            line_number,
            store,
            &pending_attributes,
        ) {
            add_symbol(store, symbol);
            pending_attributes.clear();
        } else if !trimmed.is_empty() && !trimmed.starts_with("//") {
            pending_attributes.clear();
        }

        let rust_code = strip_rust_non_code(trimmed);
        if rust_unsafe_block(&rust_code) {
            let intent_comment_id = preceding_intent_comment_id(
                store,
                file,
                line_number,
                &["SAFETY:", "Safety:", "安全"],
            );
            add_block(store, file, "unsafe", line_number, intent_comment_id);
        }
        if let Some(panic_callee) = panic_callee(&rust_code) {
            add_expression(
                store,
                ExpressionInput {
                    file,
                    module_id,
                    symbol_id: None,
                    kind: ExpressionKind::Panic,
                    line_number,
                    text: trimmed.to_string(),
                    callee: Some(panic_callee),
                    arguments: Vec::new(),
                },
            );
        }
        if trimmed.contains(".await") {
            add_expression(
                store,
                ExpressionInput {
                    file,
                    module_id,
                    symbol_id: None,
                    kind: ExpressionKind::Await,
                    line_number,
                    text: trimmed.to_string(),
                    callee: None,
                    arguments: Vec::new(),
                },
            );
        }
        if trimmed.contains(".lock(") || trimmed.contains("Mutex<") || trimmed.contains("RwLock<") {
            add_expression(
                store,
                ExpressionInput {
                    file,
                    module_id,
                    symbol_id: None,
                    kind: ExpressionKind::Lock,
                    line_number,
                    text: trimmed.to_string(),
                    callee: Some("lock".to_string()),
                    arguments: Vec::new(),
                },
            );
        }
        if trimmed.contains("thread::sleep(") || trimmed.contains("std::fs::") {
            add_expression(
                store,
                ExpressionInput {
                    file,
                    module_id,
                    symbol_id: None,
                    kind: ExpressionKind::Call,
                    line_number,
                    text: trimmed.to_string(),
                    callee: blocking_callee(trimmed),
                    arguments: call_arguments(trimmed),
                },
            );
        }
    }
}

fn extract_c_family_facts(
    file: &FileUnit,
    source: &str,
    module_id: &str,
    store: &mut EvidenceStore,
) {
    let mut pending_attributes = Vec::new();
    for (index, line) in source.lines().enumerate() {
        let line_number = index + 1;
        let trimmed = line.trim();

        if trimmed.starts_with("template ") {
            pending_attributes.push("template".to_string());
            continue;
        }

        if let Some(source_name) = include_source(trimmed) {
            add_dependency(
                store,
                DependencyInput {
                    file,
                    module_id,
                    group: dependency_group_for(&source_name, file.language),
                    source: source_name.clone(),
                    imported: source_name,
                    alias: None,
                    line_number,
                    is_glob: false,
                    is_public: is_header_path(&file.relative_path),
                    is_relative: trimmed.contains('"'),
                },
            );
        }

        if let Some(namespace) = using_namespace(trimmed) {
            add_dependency(
                store,
                DependencyInput {
                    file,
                    module_id,
                    group: dependency_group_for(&namespace, file.language),
                    source: namespace,
                    imported: "*".to_string(),
                    alias: None,
                    line_number,
                    is_glob: true,
                    is_public: is_header_path(&file.relative_path),
                    is_relative: false,
                },
            );
        }

        if let Some(symbol) = c_family_symbol(
            trimmed,
            file,
            module_id,
            line_number,
            store,
            &pending_attributes,
        ) {
            add_symbol(store, symbol);
            pending_attributes.clear();
        } else if !trimmed.is_empty() && !trimmed.starts_with("//") {
            pending_attributes.clear();
        }

        if trimmed.starts_with("#define ") {
            add_expression(
                store,
                ExpressionInput {
                    file,
                    module_id,
                    symbol_id: None,
                    kind: ExpressionKind::MacroDefinition,
                    line_number,
                    text: trimmed.to_string(),
                    callee: macro_name(trimmed),
                    arguments: Vec::new(),
                },
            );
        }
        if trimmed.starts_with("#if")
            || trimmed.starts_with("#ifdef")
            || trimmed.starts_with("#ifndef")
            || trimmed.starts_with("#endif")
        {
            add_expression(
                store,
                ExpressionInput {
                    file,
                    module_id,
                    symbol_id: None,
                    kind: ExpressionKind::Preprocessor,
                    line_number,
                    text: trimmed.to_string(),
                    callee: None,
                    arguments: Vec::new(),
                },
            );
            if !trimmed.starts_with("#endif") {
                add_block(store, file, "preprocessor", line_number, None);
            }
        }
        if let Some(allocation_callee) = allocation_callee(trimmed) {
            add_expression(
                store,
                ExpressionInput {
                    file,
                    module_id,
                    symbol_id: None,
                    kind: ExpressionKind::Allocation,
                    line_number,
                    text: trimmed.to_string(),
                    callee: Some(allocation_callee),
                    arguments: call_arguments(trimmed),
                },
            );
            add_block(store, file, "allocation", line_number, None);
        }
    }
}

fn extract_c_family_text(file_id: &str, source: &str, store: &mut EvidenceStore) {
    let mut block_comment: Option<BlockCommentBuilder> = None;
    let mut multiline_string: Option<MultilineStringState> = None;
    for (index, line) in source.lines().enumerate() {
        let line_number = index + 1;
        let trimmed = line.trim();

        if let Some(mut builder) = block_comment.take() {
            let content = clean_block_doc_line(trimmed);
            if !content.is_empty() && builder.content.is_none() {
                builder.content = Some(content.to_string());
            }
            if trimmed.contains("*/") {
                if let Some(content) = builder.content.as_deref() {
                    add_comment_or_doc_text(
                        store,
                        TextFactInput {
                            file_id,
                            is_doc: builder.is_doc,
                            module_doc: false,
                            span: SourceRange {
                                start_line: builder.start_line,
                                start_col: builder.start_col,
                                end_line: line_number,
                                end_col: char_col(line, line.trim_end().len()),
                            },
                            content,
                        },
                    );
                }
            } else {
                block_comment = Some(builder);
            }
            continue;
        }

        if advance_multiline_string_state(line, &mut multiline_string) {
            continue;
        }

        if trimmed.starts_with("/**") {
            let start_col = line.find("/**").map_or(1, |byte| char_col(line, byte));
            let content = clean_block_doc_line(trimmed.trim_start_matches("/**"));
            if trimmed.contains("*/") {
                if !content.is_empty() {
                    add_comment_or_doc_text(
                        store,
                        TextFactInput {
                            file_id,
                            is_doc: true,
                            module_doc: false,
                            span: SourceRange {
                                start_line: line_number,
                                start_col,
                                end_line: line_number,
                                end_col: char_col(line, line.trim_end().len()),
                            },
                            content,
                        },
                    );
                }
            } else {
                block_comment = Some(BlockCommentBuilder {
                    is_doc: true,
                    start_line: line_number,
                    start_col,
                    content: (!content.is_empty()).then(|| content.to_string()),
                });
            }
            continue;
        }

        if trimmed.starts_with("/*") {
            let start_col = line.find("/*").map_or(1, |byte| char_col(line, byte));
            let content = clean_block_doc_line(trimmed.trim_start_matches("/*"));
            if trimmed.contains("*/") {
                if !content.is_empty() {
                    add_comment_or_doc_text(
                        store,
                        TextFactInput {
                            file_id,
                            is_doc: false,
                            module_doc: false,
                            span: SourceRange {
                                start_line: line_number,
                                start_col,
                                end_line: line_number,
                                end_col: char_col(line, line.trim_end().len()),
                            },
                            content,
                        },
                    );
                }
            } else {
                block_comment = Some(BlockCommentBuilder {
                    is_doc: false,
                    start_line: line_number,
                    start_col,
                    content: (!content.is_empty()).then(|| content.to_string()),
                });
            }
            continue;
        }

        if trimmed.starts_with("///") {
            let content = trimmed.trim_start_matches("///").trim();
            if !content.is_empty() {
                let start_byte = line.find("///").unwrap_or(0);
                add_comment_or_doc_text(
                    store,
                    TextFactInput {
                        file_id,
                        is_doc: true,
                        module_doc: false,
                        span: SourceRange {
                            start_line: line_number,
                            start_col: char_col(line, start_byte),
                            end_line: line_number,
                            end_col: char_col(line, line.trim_end().len()),
                        },
                        content,
                    },
                );
            }
        } else if trimmed.starts_with("//!") {
            let content = trimmed.trim_start_matches("//!").trim();
            if !content.is_empty() {
                let start_byte = line.find("//!").unwrap_or(0);
                add_comment_or_doc_text(
                    store,
                    TextFactInput {
                        file_id,
                        is_doc: true,
                        module_doc: true,
                        span: SourceRange {
                            start_line: line_number,
                            start_col: char_col(line, start_byte),
                            end_line: line_number,
                            end_col: char_col(line, line.trim_end().len()),
                        },
                        content,
                    },
                );
            }
        } else if trimmed.starts_with("//") {
            let content = trimmed.trim_start_matches("//").trim();
            if !content.is_empty() {
                let start_byte = line.find("//").unwrap_or(0);
                add_comment_or_doc_text(
                    store,
                    TextFactInput {
                        file_id,
                        is_doc: false,
                        module_doc: false,
                        span: SourceRange {
                            start_line: line_number,
                            start_col: char_col(line, start_byte),
                            end_line: line_number,
                            end_col: char_col(line, line.trim_end().len()),
                        },
                        content,
                    },
                );
            }
        }
    }
}

fn advance_multiline_string_state(line: &str, state: &mut Option<MultilineStringState>) -> bool {
    if let Some(active_state) = state.as_ref() {
        if active_state.closes_on_line(line, 0) {
            *state = None;
        }
        return true;
    }

    if let Some(multiline_state) = scan_code_line_for_multiline_string(line) {
        *state = Some(multiline_state);
        return true;
    }
    false
}

fn scan_code_line_for_multiline_string(line: &str) -> Option<MultilineStringState> {
    let bytes = line.as_bytes();
    let mut index = 0;
    while index < bytes.len() {
        if starts_with_at(bytes, index, b"//") || starts_with_at(bytes, index, b"/*") {
            return None;
        }
        if bytes[index] == b'\'' {
            index = skip_closed_char_literal_or_advance(line, index);
            continue;
        }
        if bytes[index] == b'b' && bytes.get(index + 1) == Some(&b'\'') {
            index = skip_closed_char_literal_or_advance(line, index + 1);
            continue;
        }
        if let Some(raw) = raw_string_at(line, index) {
            if let Some(end_offset) = line[raw.content_start_byte..].find(&raw.terminator) {
                index = raw.content_start_byte + end_offset + raw.terminator.len();
                continue;
            }
            return Some(MultilineStringState::Raw {
                terminator: raw.terminator,
            });
        }
        if bytes[index] == b'"' {
            let end_index = skip_quoted_span(line, index, b'"');
            if end_index >= bytes.len() {
                return Some(MultilineStringState::Quoted);
            }
            index = end_index;
            continue;
        }
        index += 1;
    }
    None
}

fn skip_closed_char_literal_or_advance(line: &str, quote_byte: usize) -> usize {
    let end_index = skip_quoted_span(line, quote_byte, b'\'');
    if end_index < line.len() {
        end_index
    } else {
        quote_byte + 1
    }
}

fn starts_with_at(bytes: &[u8], index: usize, pattern: &[u8]) -> bool {
    bytes.get(index..index + pattern.len()) == Some(pattern)
}

fn skip_quoted_span(line: &str, quote_byte: usize, quote: u8) -> usize {
    let bytes = line.as_bytes();
    let mut index = quote_byte + 1;
    let mut escaped = false;
    while index < bytes.len() {
        if escaped {
            escaped = false;
        } else if bytes[index] == b'\\' {
            escaped = true;
        } else if bytes[index] == quote {
            return index + 1;
        }
        index += 1;
    }
    bytes.len()
}

struct RawStringStart {
    content_start_byte: usize,
    terminator: String,
}

fn raw_string_at(line: &str, index: usize) -> Option<RawStringStart> {
    let bytes = line.as_bytes();
    let mut marker_index = if bytes.get(index) == Some(&b'r') {
        index + 1
    } else if bytes.get(index) == Some(&b'b') && bytes.get(index + 1) == Some(&b'r') {
        index + 2
    } else {
        return None;
    };

    let hash_start = marker_index;
    while bytes.get(marker_index) == Some(&b'#') {
        marker_index += 1;
    }
    if bytes.get(marker_index) != Some(&b'"') {
        return None;
    }
    let hashes = &line[hash_start..marker_index];
    Some(RawStringStart {
        content_start_byte: marker_index + 1,
        terminator: format!("\"{hashes}"),
    })
}

enum MultilineStringState {
    Raw { terminator: String },
    Quoted,
}

impl MultilineStringState {
    fn closes_on_line(&self, line: &str, start_byte: usize) -> bool {
        match self {
            Self::Raw { terminator } => line[start_byte..].contains(terminator),
            Self::Quoted => has_unescaped_quote(&line[start_byte..]),
        }
    }
}

fn has_unescaped_quote(text: &str) -> bool {
    let mut escaped = false;
    for character in text.chars() {
        if escaped {
            escaped = false;
            continue;
        }
        if character == '\\' {
            escaped = true;
            continue;
        }
        if character == '"' {
            return true;
        }
    }
    false
}

struct BlockCommentBuilder {
    is_doc: bool,
    start_line: usize,
    start_col: usize,
    content: Option<String>,
}

fn clean_block_doc_line(line: &str) -> &str {
    line.trim_end_matches("*/")
        .trim()
        .trim_start_matches('*')
        .trim()
}

#[derive(Debug, Clone)]
struct PythonSignature {
    logical_text: String,
    start_index: usize,
    end_index: usize,
    start_line: usize,
    name: String,
}

fn python_signature_at(lines: &[&str], index: usize) -> Option<PythonSignature> {
    let first = lines.get(index)?;
    let trimmed = first.trim_start();

    if !(trimmed.starts_with("def ")
        || trimmed.starts_with("async def ")
        || trimmed.starts_with("class "))
    {
        return None;
    }

    let mut logical_text = String::from(trimmed);
    let mut balance = paren_balance(trimmed);
    let mut declaration_complete = has_top_level_declaration_colon(trimmed, 0);
    let mut end_index = index;

    while !declaration_complete || balance > 0 {
        end_index += 1;
        let Some(next) = lines.get(end_index) else {
            break;
        };
        let next_trimmed = next.trim();
        logical_text.push(' ');
        logical_text.push_str(next_trimmed);
        let previous_balance = balance;
        balance += paren_balance(next_trimmed);
        declaration_complete |= has_top_level_declaration_colon(next_trimmed, previous_balance);

        if declaration_complete && balance <= 0 {
            break;
        }
    }

    let name = symbol_name(&logical_text)?;

    Some(PythonSignature {
        logical_text,
        start_index: index,
        end_index,
        start_line: index + 1,
        name,
    })
}

fn paren_balance(text: &str) -> isize {
    let mut balance = 0;
    let mut quote = None;
    let mut escaped = false;

    for character in text.chars() {
        if let Some(active_quote) = quote {
            if escaped {
                escaped = false;
            } else if character == '\\' {
                escaped = true;
            } else if character == active_quote {
                quote = None;
            }
            continue;
        }

        match character {
            '\'' | '"' => quote = Some(character),
            '#' => break,
            '(' => balance += 1,
            ')' => balance -= 1,
            _ => {}
        }
    }

    balance
}

fn has_top_level_declaration_colon(text: &str, starting_balance: isize) -> bool {
    let mut balance = starting_balance;
    let mut quote = None;
    let mut escaped = false;

    for character in text.chars() {
        if let Some(active_quote) = quote {
            if escaped {
                escaped = false;
            } else if character == '\\' {
                escaped = true;
            } else if character == active_quote {
                quote = None;
            }
            continue;
        }

        match character {
            '\'' | '"' => quote = Some(character),
            '#' => break,
            '(' => balance += 1,
            ')' => balance -= 1,
            ':' if balance <= 0 => return true,
            _ => {}
        }
    }

    false
}

fn symbol_name(trimmed: &str) -> Option<String> {
    if let Some(rest) = trimmed
        .strip_prefix("async def ")
        .or_else(|| trimmed.strip_prefix("def "))
    {
        let name = rest.split('(').next()?.trim();
        if !name.is_empty() {
            return Some(name.to_string());
        }
    }

    let rest = trimmed.strip_prefix("class ")?;
    let name = rest
        .split(['(', ':'])
        .next()
        .map(str::trim)
        .filter(|name| !name.is_empty())?;
    Some(name.to_string())
}

fn parse_docstring(lines: &[&str], start_index: usize) -> Option<Docstring> {
    let line = *lines.get(start_index)?;
    let opening = opening_triple(line)?;
    let opening_end_byte = opening.delimiter_byte + opening.quote.len();
    let after_opening = &line[opening_end_byte..];

    if let Some(close_offset) = after_opening.find(opening.quote) {
        let content_end_byte = opening_end_byte + close_offset;
        let raw_content = &line[opening_end_byte..content_end_byte];
        let summary = raw_content.trim();
        if summary.is_empty() {
            return None;
        }
        let leading_trim_bytes = raw_content.len() - raw_content.trim_start().len();
        let trailing_trim_bytes = raw_content.len() - raw_content.trim_end().len();
        let summary_start_byte = opening_end_byte + leading_trim_bytes;
        let summary_end_byte = content_end_byte - trailing_trim_bytes;
        let end_byte = content_end_byte + opening.quote.len();
        return Some(Docstring {
            start_line: start_index + 1,
            start_col: char_col(line, opening.start_byte),
            end_line: start_index + 1,
            end_col: char_col(line, end_byte),
            summary_start_line: start_index + 1,
            summary_start_col: char_col(line, summary_start_byte),
            summary_end_line: start_index + 1,
            summary_end_col: char_col(line, summary_end_byte),
            summary: summary.to_string(),
            full_text: summary.to_string(),
        });
    }

    let mut summary =
        first_non_empty_content_after_opening(line, start_index + 1, opening_end_byte);
    for (offset, current) in lines.iter().enumerate().skip(start_index + 1) {
        if summary.is_none() {
            if let Some(span) = first_non_empty_span(current, offset + 1) {
                summary = Some(span);
            }
        }
        if let Some(close_byte) = current.find(opening.quote) {
            let summary = summary?;
            let full_text =
                collect_docstring_body(lines, start_index, opening_end_byte, offset, close_byte);
            return Some(Docstring {
                start_line: start_index + 1,
                start_col: char_col(line, opening.start_byte),
                end_line: offset + 1,
                end_col: char_col(current, close_byte + opening.quote.len()),
                summary_start_line: summary.start_line,
                summary_start_col: summary.start_col,
                summary_end_line: summary.end_line,
                summary_end_col: summary.end_col,
                summary: summary.text,
                full_text,
            });
        }
    }

    None
}

fn skip_triple_string(lines: &[&str], start_index: usize, opening: OpeningTriple<'_>) -> usize {
    let line = lines[start_index];
    if line[opening.delimiter_byte + opening.quote.len()..].contains(opening.quote) {
        return start_index + 1;
    }
    for (offset, current) in lines.iter().enumerate().skip(start_index + 1) {
        if current.contains(opening.quote) {
            return offset + 1;
        }
    }
    lines.len()
}

fn collect_docstring_body(
    lines: &[&str],
    start_index: usize,
    opening_end_byte: usize,
    end_index: usize,
    closing_byte: usize,
) -> String {
    let mut body = Vec::new();
    body.push(lines[start_index][opening_end_byte..].to_string());
    for line in &lines[start_index + 1..end_index] {
        body.push((*line).to_string());
    }
    body.push(lines[end_index][..closing_byte].to_string());
    trim_doc_body(&body.join("\n"))
}

fn trim_doc_body(body: &str) -> String {
    let lines = body.lines().collect::<Vec<_>>();
    let start = lines.iter().position(|line| !line.trim().is_empty());
    let end = lines.iter().rposition(|line| !line.trim().is_empty());
    match (start, end) {
        (Some(start), Some(end)) => lines[start..=end].join("\n"),
        _ => String::new(),
    }
}

fn opening_triple(line: &str) -> Option<OpeningTriple<'_>> {
    let leading_bytes = line.len() - line.trim_start().len();
    let trimmed = &line[leading_bytes..];
    let prefix_len = string_prefix_len(trimmed);
    let after_prefix = &trimmed[prefix_len..];
    let quote = if after_prefix.starts_with("\"\"\"") {
        "\"\"\""
    } else if after_prefix.starts_with("'''") {
        "'''"
    } else {
        return None;
    };
    Some(OpeningTriple {
        quote,
        start_byte: leading_bytes,
        delimiter_byte: leading_bytes + prefix_len,
    })
}

fn opening_triple_anywhere(line: &str) -> Option<OpeningTriple<'_>> {
    let mut state = LineStringState::Code;
    let mut escaped = false;

    for (byte_index, _) in line.char_indices() {
        let character = line[byte_index..].chars().next()?;
        match state {
            LineStringState::Code => {}
            LineStringState::SingleQuoted => {
                if escaped {
                    escaped = false;
                    continue;
                }
                if character == '\\' {
                    escaped = true;
                    continue;
                }
                if character == '\'' {
                    state = LineStringState::Code;
                }
                continue;
            }
            LineStringState::DoubleQuoted => {
                if escaped {
                    escaped = false;
                    continue;
                }
                if character == '\\' {
                    escaped = true;
                    continue;
                }
                if character == '"' {
                    state = LineStringState::Code;
                }
                continue;
            }
        }

        let rest = &line[byte_index..];
        let quote = if rest.starts_with("\"\"\"") {
            "\"\"\""
        } else if rest.starts_with("'''") {
            "'''"
        } else {
            if character == '\'' {
                state = LineStringState::SingleQuoted;
            } else if character == '"' {
                state = LineStringState::DoubleQuoted;
            } else if character == '#' {
                break;
            }
            continue;
        };
        if is_escaped(line, byte_index) {
            continue;
        }
        let prefix_start = string_prefix_start(line, byte_index);
        return Some(OpeningTriple {
            quote,
            start_byte: prefix_start,
            delimiter_byte: byte_index,
        });
    }
    None
}

#[derive(Clone, Copy)]
enum LineStringState {
    Code,
    SingleQuoted,
    DoubleQuoted,
}

fn string_prefix_len(trimmed: &str) -> usize {
    let mut bytes = 0;
    for character in trimmed.chars() {
        if matches!(character, 'r' | 'R' | 'u' | 'U' | 'b' | 'B' | 'f' | 'F') {
            bytes += character.len_utf8();
        } else {
            break;
        }
    }
    bytes
}

fn string_prefix_start(line: &str, delimiter_byte: usize) -> usize {
    let prefix = &line[..delimiter_byte];
    let mut start = delimiter_byte;
    for (byte_index, character) in prefix.char_indices().rev() {
        if matches!(character, 'r' | 'R' | 'u' | 'U' | 'b' | 'B' | 'f' | 'F') {
            start = byte_index;
        } else {
            break;
        }
    }
    start
}

fn is_escaped(line: &str, delimiter_byte: usize) -> bool {
    let mut backslashes = 0;
    for character in line[..delimiter_byte].chars().rev() {
        if character == '\\' {
            backslashes += 1;
        } else {
            break;
        }
    }
    backslashes % 2 == 1
}

fn line_comment(line: &str, line_number: usize) -> Option<CommentSpan> {
    let leading_bytes = line.len() - line.trim_start().len();
    let trimmed = &line[leading_bytes..];
    let marker_len = if trimmed.starts_with('#') {
        1
    } else if trimmed.starts_with("//") {
        2
    } else {
        return None;
    };
    let region_start_byte = leading_bytes;
    let region_end_byte = line.trim_end().len();
    let after_marker_byte = leading_bytes + marker_len;
    let raw_text = &line[after_marker_byte..region_end_byte];
    let text = raw_text.trim();
    if text.is_empty() {
        return None;
    }
    let text_start_byte = after_marker_byte + (raw_text.len() - raw_text.trim_start().len());
    let text_end_byte = region_end_byte - (raw_text.len() - raw_text.trim_end().len());

    Some(CommentSpan {
        region_start_line: line_number,
        region_start_col: char_col(line, region_start_byte),
        region_end_line: line_number,
        region_end_col: char_col(line, region_end_byte),
        text_start_line: line_number,
        text_start_col: char_col(line, text_start_byte),
        text_end_line: line_number,
        text_end_col: char_col(line, text_end_byte),
        text: text.to_string(),
    })
}

fn first_non_empty_span(line: &str, line_number: usize) -> Option<SummarySpan> {
    let text = line.trim();
    if text.is_empty() {
        return None;
    }
    let start_byte = line.len() - line.trim_start().len();
    let end_byte = line.trim_end().len();
    Some(SummarySpan {
        start_line: line_number,
        start_col: char_col(line, start_byte),
        end_line: line_number,
        end_col: char_col(line, end_byte),
        text: text.to_string(),
    })
}

fn first_non_empty_content_after_opening(
    line: &str,
    line_number: usize,
    opening_end_byte: usize,
) -> Option<SummarySpan> {
    let raw = &line[opening_end_byte..line.trim_end().len()];
    let text = raw.trim();
    if text.is_empty() {
        return None;
    }
    let start_byte = opening_end_byte + (raw.len() - raw.trim_start().len());
    let end_byte = line.trim_end().len();
    Some(SummarySpan {
        start_line: line_number,
        start_col: char_col(line, start_byte),
        end_line: line_number,
        end_col: char_col(line, end_byte),
        text: text.to_string(),
    })
}

fn char_col(line: &str, byte_index: usize) -> usize {
    line[..byte_index].chars().count() + 1
}

fn matching_bracket_end(text: &str, open_byte: usize) -> Option<usize> {
    let mut depth = 0;
    for (offset, character) in text[open_byte..].char_indices() {
        match character {
            '[' => depth += 1,
            ']' => {
                depth -= 1;
                if depth == 0 {
                    return Some(open_byte + offset);
                }
            }
            _ => {}
        }
    }
    None
}

fn code_marker_positions(text: &str, marker: &str) -> Vec<usize> {
    let mut positions = Vec::new();
    let mut quote = None;
    let mut escaped = false;
    for (byte_index, character) in text.char_indices() {
        if let Some(active_quote) = quote {
            if escaped {
                escaped = false;
            } else if character == '\\' {
                escaped = true;
            } else if character == active_quote {
                quote = None;
            }
            continue;
        }

        match character {
            '\'' | '"' => quote = Some(character),
            '#' => break,
            _ if text[byte_index..].starts_with(marker) => positions.push(byte_index),
            _ => {}
        }
    }
    positions
}

fn hash_text(text: &str) -> String {
    blake3::hash(text.as_bytes()).to_hex()[..12].to_string()
}

fn python_dependency(
    trimmed: &str,
) -> Option<(String, String, Option<String>, DependencyGroup, bool, bool)> {
    if let Some(rest) = trimmed.strip_prefix("from ") {
        let (source, imported) = rest.split_once(" import ")?;
        let source = source.trim();
        let imported = imported.split('#').next()?.trim();
        let (imported, alias) = split_alias(imported);
        let group = if source == "__future__" {
            DependencyGroup::Future
        } else {
            dependency_group_for(source.trim_start_matches('.'), Language::Python)
        };
        return Some((
            source.trim_start_matches('.').to_string(),
            imported.to_string(),
            alias.map(str::to_string),
            group,
            source.starts_with('.'),
            imported == "*",
        ));
    }

    let rest = trimmed.strip_prefix("import ")?;
    let first = rest.split(',').next()?.trim();
    let (source, alias) = split_alias(first);
    let root = source.split('.').next().unwrap_or(source).to_string();
    Some((
        root.clone(),
        source.to_string(),
        alias.map(str::to_string),
        dependency_group_for(&root, Language::Python),
        false,
        false,
    ))
}

#[derive(Clone, Copy)]
enum RustStringState {
    Code,
    Normal { escaped: bool },
    Raw { hashes: usize },
}

fn rust_code_outside_strings(line: &str, state: &mut RustStringState) -> String {
    let mut code = String::new();
    let mut byte_index = 0;

    while byte_index < line.len() {
        match *state {
            RustStringState::Code => {
                if line[byte_index..].starts_with("//") {
                    code.push_str(&line[byte_index..]);
                    break;
                }
                if let Some((opener_len, hashes)) = rust_raw_string_opener(line, byte_index) {
                    let after_opening = byte_index + opener_len;
                    let closing = rust_raw_string_closing(hashes);
                    if let Some(close_offset) = line[after_opening..].find(&closing) {
                        let end = after_opening + close_offset + closing.len();
                        code.push_str(&line[byte_index..end]);
                        byte_index = end;
                    } else {
                        *state = RustStringState::Raw { hashes };
                        byte_index += opener_len;
                    }
                    continue;
                }

                let Some(character) = line[byte_index..].chars().next() else {
                    break;
                };
                if character == '"' {
                    if let Some(end) =
                        normal_rust_string_end(line, byte_index + character.len_utf8())
                    {
                        code.push_str(&line[byte_index..end]);
                        byte_index = end;
                    } else {
                        *state = RustStringState::Normal { escaped: false };
                        byte_index += character.len_utf8();
                    }
                    continue;
                }

                code.push(character);
                byte_index += character.len_utf8();
            }
            RustStringState::Normal { mut escaped } => {
                let Some(character) = line[byte_index..].chars().next() else {
                    break;
                };
                if escaped {
                    escaped = false;
                } else if character == '\\' {
                    escaped = true;
                } else if character == '"' {
                    *state = RustStringState::Code;
                    byte_index += character.len_utf8();
                    continue;
                }
                *state = RustStringState::Normal { escaped };
                byte_index += character.len_utf8();
            }
            RustStringState::Raw { hashes } => {
                let closing = rust_raw_string_closing(hashes);
                if line[byte_index..].starts_with(&closing) {
                    *state = RustStringState::Code;
                    byte_index += closing.len();
                    continue;
                }

                let Some(character) = line[byte_index..].chars().next() else {
                    break;
                };
                byte_index += character.len_utf8();
            }
        }
    }

    code
}

fn normal_rust_string_end(line: &str, start_byte: usize) -> Option<usize> {
    let mut escaped = false;
    for (offset, character) in line[start_byte..].char_indices() {
        if escaped {
            escaped = false;
        } else if character == '\\' {
            escaped = true;
        } else if character == '"' {
            return Some(start_byte + offset + character.len_utf8());
        }
    }
    None
}

fn rust_raw_string_opener(line: &str, byte_index: usize) -> Option<(usize, usize)> {
    let mut cursor = byte_index;
    if line[cursor..].starts_with('b') {
        cursor += 1;
    }
    if !line[cursor..].starts_with('r') {
        return None;
    }
    cursor += 1;

    let hashes = line[cursor..]
        .chars()
        .take_while(|character| *character == '#')
        .count();
    cursor += hashes;

    line[cursor..]
        .starts_with('"')
        .then_some((cursor + 1 - byte_index, hashes))
}

fn rust_raw_string_closing(hashes: usize) -> String {
    format!("\"{}", "#".repeat(hashes))
}

fn rust_dependency(trimmed: &str) -> Option<(String, String, bool)> {
    let (rest, is_public) = if let Some(rest) = trimmed.strip_prefix("pub use ") {
        (rest, true)
    } else if let Some(rest) = trimmed.strip_prefix("use ") {
        (rest, false)
    } else if let Some(rest) = trimmed.strip_prefix("pub mod ") {
        (rest, true)
    } else if let Some(rest) = trimmed.strip_prefix("mod ") {
        (rest, false)
    } else {
        return None;
    };
    let cleaned = rest.trim_end_matches(';').trim();
    let source = cleaned
        .split("::")
        .next()
        .unwrap_or(cleaned)
        .trim_matches('{')
        .trim()
        .to_string();
    Some((source, cleaned.to_string(), is_public))
}

struct RustAttribute {
    name: String,
    text: String,
}

fn rust_attribute(trimmed: &str) -> Option<RustAttribute> {
    let content = trimmed
        .strip_prefix("#![")
        .or_else(|| trimmed.strip_prefix("#["))?
        .trim_end_matches(']')
        .trim();
    let name = content
        .split(['(', '='])
        .next()
        .map(str::trim)
        .filter(|name| !name.is_empty())?;
    Some(RustAttribute {
        name: name.to_string(),
        text: content.to_string(),
    })
}

fn include_source(trimmed: &str) -> Option<String> {
    let rest = trimmed.strip_prefix("#include")?.trim();
    let closing = if rest.starts_with('<') { '>' } else { '"' };
    let opening = if rest.starts_with('<') { '<' } else { '"' };
    let start = rest.find(opening)? + 1;
    let end = rest[start..].find(closing)? + start;
    let value = &rest[start..end];
    Some(
        value
            .trim_end_matches(".h")
            .trim_end_matches(".hpp")
            .to_string(),
    )
}

fn using_namespace(trimmed: &str) -> Option<String> {
    Some(
        trimmed
            .strip_prefix("using namespace ")?
            .trim_end_matches(';')
            .trim()
            .to_string(),
    )
    .filter(|namespace| !namespace.is_empty())
}

fn macro_name(trimmed: &str) -> Option<String> {
    let rest = trimmed.strip_prefix("#define ")?;
    rest.split(['(', ' ', '\t'])
        .next()
        .filter(|name| !name.is_empty())
        .map(str::to_string)
}

fn split_alias(input: &str) -> (&str, Option<&str>) {
    if let Some((source, alias)) = input.split_once(" as ") {
        (source.trim(), Some(alias.trim()))
    } else {
        (input.trim(), None)
    }
}

fn python_symbol(
    trimmed: &str,
    file: &FileUnit,
    module_id: &str,
    line_number: usize,
    store: &EvidenceStore,
) -> Option<SymbolFact> {
    if let Some(rest) = trimmed.strip_prefix("class ") {
        let name = rest.split(['(', ':']).next()?.trim();
        return Some(symbol_fact(
            SymbolInput {
                file,
                module_id,
                name,
                kind: SymbolKind::Class,
                visibility: python_visibility(name),
                line_number,
            },
            store,
            SymbolOptions::default(),
        ));
    }

    let (rest, is_async) = if let Some(rest) = trimmed.strip_prefix("async def ") {
        (rest, true)
    } else if let Some(rest) = trimmed.strip_prefix("def ") {
        (rest, false)
    } else {
        return None;
    };
    let name = rest.split('(').next()?.trim();
    let parameters = rest
        .split_once('(')
        .and_then(|(_, tail)| tail.split_once(')'))
        .map(|(parameters, _)| parameters)
        .unwrap_or_default();
    let missing_parameter_annotations = split_top_level_commas(parameters)
        .into_iter()
        .filter_map(|parameter| {
            let parameter = parameter.as_str().trim();
            if parameter.is_empty() || parameter.contains(':') {
                return None;
            }
            let name = parameter
                .trim_start_matches('*')
                .split('=')
                .next()
                .unwrap_or(parameter)
                .trim();
            if matches!(name, "" | "self" | "cls") {
                None
            } else {
                Some(name.to_string())
            }
        })
        .collect();
    let return_annotation = rest
        .split_once("->")
        .and_then(|(_, tail)| tail.split(':').next())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string);

    Some(symbol_fact(
        SymbolInput {
            file,
            module_id,
            name,
            kind: SymbolKind::Function,
            visibility: python_visibility(name),
            line_number,
        },
        store,
        SymbolOptions {
            return_annotation,
            missing_parameter_annotations,
            type_text: parameters
                .contains(':')
                .then(|| parameters.trim().to_string()),
            is_async,
            ..SymbolOptions::default()
        },
    ))
}

fn python_parameter_symbols(
    trimmed: &str,
    file: &FileUnit,
    module_id: &str,
    line_number: usize,
    store: &EvidenceStore,
    lines: &[&str],
    start_index: usize,
) -> Vec<SymbolFact> {
    let rest = trimmed
        .strip_prefix("async def ")
        .or_else(|| trimmed.strip_prefix("def "));
    let Some(rest) = rest else {
        return Vec::new();
    };
    let parameters = rest
        .split_once('(')
        .and_then(|(_, tail)| tail.split_once(')'))
        .map(|(parameters, _)| parameters)
        .unwrap_or_default();

    split_top_level_commas(parameters)
        .into_iter()
        .filter_map(|parameter| python_parameter_name_and_annotation(&parameter))
        .map(|(name, annotation)| {
            let parameter_line = python_parameter_line(lines, start_index, &name, line_number);
            symbol_fact(
                SymbolInput {
                    file,
                    module_id,
                    name: &name,
                    kind: SymbolKind::Parameter,
                    visibility: SymbolVisibility::Private,
                    line_number: parameter_line,
                },
                store,
                SymbolOptions {
                    type_text: Some(annotation),
                    ..SymbolOptions::default()
                },
            )
        })
        .collect()
}

fn python_parameter_line(lines: &[&str], start_index: usize, name: &str, fallback: usize) -> usize {
    let marker = format!("{name}:");
    for (index, line) in lines.iter().enumerate().skip(start_index) {
        let code = line.split('#').next().unwrap_or(line);
        if code.contains(&marker) {
            return index + 1;
        }
        if index > start_index && code.contains(')') {
            break;
        }
    }
    fallback
}

fn split_top_level_commas(input: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut bracket_depth = 0usize;
    let mut paren_depth = 0usize;
    let mut brace_depth = 0usize;
    let mut quote = None;
    let mut escaped = false;
    for character in input.chars() {
        if let Some(active_quote) = quote {
            current.push(character);
            if escaped {
                escaped = false;
            } else if character == '\\' {
                escaped = true;
            } else if character == active_quote {
                quote = None;
            }
            continue;
        }
        match character {
            '\'' | '"' => {
                quote = Some(character);
                current.push(character);
            }
            '[' => {
                bracket_depth += 1;
                current.push(character);
            }
            ']' => {
                bracket_depth = bracket_depth.saturating_sub(1);
                current.push(character);
            }
            '(' => {
                paren_depth += 1;
                current.push(character);
            }
            ')' => {
                paren_depth = paren_depth.saturating_sub(1);
                current.push(character);
            }
            '{' => {
                brace_depth += 1;
                current.push(character);
            }
            '}' => {
                brace_depth = brace_depth.saturating_sub(1);
                current.push(character);
            }
            ',' if bracket_depth == 0 && paren_depth == 0 && brace_depth == 0 => {
                parts.push(current.trim().to_string());
                current.clear();
            }
            _ => current.push(character),
        }
    }
    if !current.trim().is_empty() {
        parts.push(current.trim().to_string());
    }
    parts
}

fn python_parameter_name_and_annotation(parameter: &str) -> Option<(String, String)> {
    let parameter = parameter.trim();
    if parameter.is_empty() {
        return None;
    }
    let (name, annotation) = parameter.split_once(':')?;
    let name = name
        .trim()
        .trim_start_matches('*')
        .split('=')
        .next()
        .unwrap_or_default()
        .trim();
    if matches!(name, "" | "self" | "cls") {
        return None;
    }
    let annotation = annotation.split('=').next().unwrap_or(annotation).trim();
    if annotation.is_empty() {
        return None;
    }
    Some((name.to_string(), annotation.to_string()))
}

fn python_bool_annotation_symbol(
    trimmed: &str,
    file: &FileUnit,
    module_id: &str,
    line_number: usize,
    store: &EvidenceStore,
) -> Option<SymbolFact> {
    if trimmed.starts_with("def ")
        || trimmed.starts_with("async def ")
        || trimmed.starts_with("class ")
        || trimmed.starts_with("if ")
        || trimmed.starts_with("elif ")
        || trimmed.starts_with("for ")
        || trimmed.starts_with("while ")
    {
        return None;
    }
    let (name, annotation) = python_parameter_name_and_annotation(trimmed)?;
    if annotation != "bool" {
        return None;
    }
    let kind = if trimmed.trim_start().starts_with("self.") {
        SymbolKind::Field
    } else {
        SymbolKind::Variable
    };
    Some(symbol_fact(
        SymbolInput {
            file,
            module_id,
            name: &name,
            kind,
            visibility: SymbolVisibility::Private,
            line_number,
        },
        store,
        SymbolOptions {
            type_text: Some(annotation),
            ..SymbolOptions::default()
        },
    ))
}

fn python_logger_symbol(
    trimmed: &str,
    file: &FileUnit,
    module_id: &str,
    line_number: usize,
    store: &EvidenceStore,
) -> Option<SymbolFact> {
    let (name, value) = trimmed.split_once('=')?;
    if !value.trim_start().starts_with("logging.getLogger(") {
        return None;
    }
    let name = name.trim();
    if name.is_empty() {
        return None;
    }
    let kind = if name.starts_with("self.") {
        SymbolKind::Field
    } else if name.contains('.') {
        return None;
    } else if name.chars().all(|character| {
        character == '_' || character.is_ascii_digit() || character.is_ascii_uppercase()
    }) {
        SymbolKind::Constant
    } else {
        SymbolKind::Variable
    };
    Some(symbol_fact(
        SymbolInput {
            file,
            module_id,
            name,
            kind,
            visibility: SymbolVisibility::Private,
            line_number,
        },
        store,
        SymbolOptions {
            type_text: Some("logging.getLogger".to_string()),
            ..SymbolOptions::default()
        },
    ))
}

struct TypeExpression {
    text: String,
    callee: String,
}

fn python_type_expressions(trimmed: &str) -> Vec<TypeExpression> {
    let mut expressions = Vec::new();
    for callee in [
        "typing.List",
        "typing.Dict",
        "typing.Tuple",
        "typing.Set",
        "typing.Optional",
        "typing.Union",
        "List",
        "Dict",
        "Tuple",
        "Set",
        "Optional",
        "Union",
    ] {
        if let Some(expression) = python_type_expression(trimmed, callee) {
            if !expressions
                .iter()
                .any(|existing: &TypeExpression| existing.text == expression.text)
            {
                expressions.push(expression);
            }
        }
    }
    expressions
}

fn python_type_expression(trimmed: &str, callee: &str) -> Option<TypeExpression> {
    let marker = format!("{callee}[");
    let start = code_marker_positions(trimmed, &marker)
        .into_iter()
        .find(|start| {
            callee.contains('.')
                || *start == 0
                || trimmed[..*start]
                    .chars()
                    .next_back()
                    .is_none_or(|character| {
                        character != '.' && !character.is_ascii_alphanumeric() && character != '_'
                    })
        })?;
    let end = matching_bracket_end(trimmed, start + marker.len() - 1)?;
    Some(TypeExpression {
        text: trimmed[start..=end].to_string(),
        callee: callee.rsplit('.').next().unwrap_or(callee).to_string(),
    })
}

fn rust_symbol(
    trimmed: &str,
    file: &FileUnit,
    module_id: &str,
    line_number: usize,
    store: &EvidenceStore,
    attributes: &[String],
) -> Option<SymbolFact> {
    let mut rest = trimmed;
    let visibility = if let Some(value) = rest.strip_prefix("pub ") {
        rest = value.trim_start();
        SymbolVisibility::Public
    } else if let Some(value) = rest.strip_prefix("pub(") {
        rest = value.split_once(')')?.1.trim_start();
        SymbolVisibility::Internal
    } else {
        SymbolVisibility::Private
    };
    let is_async = rest.starts_with("async ");
    if is_async {
        rest = rest.trim_start_matches("async ").trim_start();
    }
    let is_unsafe = rest.starts_with("unsafe ");
    if is_unsafe {
        rest = rest.trim_start_matches("unsafe ").trim_start();
    }
    let type_text = if rest.starts_with("extern ") {
        let fn_index = rest.find("fn ")?;
        let abi = rest[..fn_index].replace('"', "").trim().to_string();
        rest = rest[fn_index..].trim_start();
        Some(abi)
    } else {
        None
    };

    let (kind, after_keyword) = if let Some(value) = rest.strip_prefix("fn ") {
        (SymbolKind::Function, value)
    } else if let Some(value) = rest.strip_prefix("struct ") {
        (SymbolKind::Struct, value)
    } else if let Some(value) = rest.strip_prefix("enum ") {
        (SymbolKind::Enum, value)
    } else if let Some(value) = rest.strip_prefix("trait ") {
        (SymbolKind::Trait, value)
    } else if let Some(value) = rest.strip_prefix("type ") {
        (SymbolKind::TypeAlias, value)
    } else if let Some(value) = rest.strip_prefix("const ") {
        (SymbolKind::Constant, value)
    } else if let Some(value) = rest.strip_prefix("mod ") {
        (SymbolKind::Module, value)
    } else {
        return None;
    };
    let name = after_keyword
        .split(['(', '<', ':', '{', ';', '='])
        .next()?
        .trim();
    let return_annotation = after_keyword
        .split_once("->")
        .and_then(|(_, tail)| tail.split(['{', ';']).next())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string);

    Some(symbol_fact(
        SymbolInput {
            file,
            module_id,
            name,
            kind,
            visibility,
            line_number,
        },
        store,
        SymbolOptions {
            return_annotation,
            type_text,
            is_async,
            is_unsafe,
            attributes: attributes.to_vec(),
            ..SymbolOptions::default()
        },
    ))
}

fn c_family_symbol(
    trimmed: &str,
    file: &FileUnit,
    module_id: &str,
    line_number: usize,
    store: &EvidenceStore,
    attributes: &[String],
) -> Option<SymbolFact> {
    if let Some(rest) = trimmed.strip_prefix("#define ") {
        let name = rest
            .split(['(', ' ', '\t'])
            .next()
            .filter(|name| !name.is_empty())?;
        return Some(symbol_fact(
            SymbolInput {
                file,
                module_id,
                name,
                kind: SymbolKind::Macro,
                visibility: SymbolVisibility::Public,
                line_number,
            },
            store,
            SymbolOptions::default(),
        ));
    }

    if !trimmed.contains('(')
        || trimmed.starts_with("if ")
        || trimmed.starts_with("for ")
        || trimmed.starts_with("while ")
        || trimmed.starts_with("switch ")
        || trimmed.starts_with("return ")
        || trimmed.starts_with("return(")
    {
        return None;
    }
    let before_paren = trimmed.split_once('(')?.0.trim();
    let name = before_paren
        .split_whitespace()
        .last()?
        .trim_start_matches('*')
        .trim();
    if name.is_empty() || name == "return" || !looks_like_declaration(trimmed) {
        return None;
    }
    if looks_like_call_statement(trimmed, before_paren, name) {
        return None;
    }
    Some(symbol_fact(
        SymbolInput {
            file,
            module_id,
            name,
            kind: SymbolKind::Function,
            visibility: SymbolVisibility::Public,
            line_number,
        },
        store,
        SymbolOptions {
            type_text: Some(before_paren.to_string()),
            attributes: attributes.to_vec(),
            ..SymbolOptions::default()
        },
    ))
}

struct SymbolInput<'a> {
    file: &'a FileUnit,
    module_id: &'a str,
    name: &'a str,
    kind: SymbolKind,
    visibility: SymbolVisibility,
    line_number: usize,
}

fn symbol_fact(
    input: SymbolInput<'_>,
    store: &EvidenceStore,
    options: SymbolOptions,
) -> SymbolFact {
    let symbol_hash = hash_text(&format!(
        "{}:{}:{}",
        input.file.relative_path, input.name, input.line_number
    ));
    let doc_region_id = store
        .doc_regions
        .iter()
        .find(|doc| doc.file_id == input.file.id && doc.symbol_name == input.name)
        .map(|doc| doc.id.clone());
    SymbolFact {
        id: stable_id(
            &input.file.id,
            "symbol",
            symbol_kind_name(input.kind),
            input.line_number,
            1,
            &symbol_hash,
        ),
        file_id: input.file.id.clone(),
        module_id: input.module_id.to_string(),
        name: input.name.to_string(),
        qualified_name: qualified_name(&input.file.relative_path, input.name),
        kind: input.kind,
        visibility: input.visibility,
        language: input.file.language,
        range: line_range(input.line_number),
        doc_region_id,
        return_annotation: options.return_annotation,
        missing_parameter_annotations: options.missing_parameter_annotations,
        type_text: options.type_text,
        is_async: options.is_async,
        is_unsafe: options.is_unsafe,
        attributes: options.attributes,
    }
}

#[derive(Default)]
struct SymbolOptions {
    return_annotation: Option<String>,
    missing_parameter_annotations: Vec<String>,
    type_text: Option<String>,
    is_async: bool,
    is_unsafe: bool,
    attributes: Vec<String>,
}

fn add_symbol(store: &mut EvidenceStore, symbol: SymbolFact) {
    if should_create_public_surface(&symbol, symbol.language) {
        store.public_surfaces.push(PublicSurfaceFact {
            id: format!("public:{}", symbol.id),
            symbol_name: symbol.name.clone(),
            visibility: visibility_name(symbol.visibility).to_string(),
            has_doc_region: symbol.doc_region_id.is_some(),
            file_id: symbol.file_id.clone(),
            range: symbol.range.clone(),
        });
    }
    store.symbols.push(symbol);
}

fn should_create_public_surface(symbol: &SymbolFact, language: Language) -> bool {
    if matches!(language, Language::C | Language::Cpp) && symbol.kind == SymbolKind::Macro {
        return false;
    }

    matches!(
        symbol.visibility,
        SymbolVisibility::Public | SymbolVisibility::Internal
    )
}

fn link_preceding_docs(file: &FileUnit, store: &mut EvidenceStore) {
    let mut symbols = store
        .symbols
        .iter()
        .filter(|symbol| symbol.file_id == file.id)
        .filter_map(|symbol| {
            Some((
                symbol.id.clone(),
                symbol.name.clone(),
                symbol.range.clone(),
                start_line(&symbol.range)?,
                symbol.attributes.len(),
            ))
        })
        .collect::<Vec<_>>();
    symbols.sort_by_key(|(_, _, _, line, _)| *line);
    let mut doc_pairs = Vec::new();
    let mut used_docs = Vec::new();
    for (symbol_id, symbol_name, symbol_range, symbol_line, attribute_count) in symbols {
        let doc = store
            .doc_regions
            .iter()
            .filter(|doc| {
                doc.file_id == file.id
                    && doc.symbol_name == "__pending_symbol__"
                    && !used_docs.contains(&doc.id)
            })
            .filter_map(|doc| Some((doc, end_line(&doc.range)?)))
            .filter(|(_, doc_end)| {
                doc_end.saturating_add(attribute_count + 1) >= symbol_line.saturating_sub(1)
            })
            .filter(|(_, doc_end)| *doc_end < symbol_line)
            .max_by_key(|(_, doc_end)| *doc_end)
            .map(|(doc, _)| {
                (
                    symbol_id.clone(),
                    doc.id.clone(),
                    symbol_name.clone(),
                    symbol_range.clone(),
                )
            });
        if let Some((_, doc_id, _, _)) = &doc {
            used_docs.push(doc_id.clone());
        }
        if let Some(pair) = doc {
            doc_pairs.push(pair);
        }
    }

    for (symbol_id, doc_id, symbol_name, symbol_range) in doc_pairs {
        if let Some(symbol) = store
            .symbols
            .iter_mut()
            .find(|symbol| symbol.id == symbol_id)
        {
            symbol.doc_region_id = Some(doc_id.clone());
        }
        if let Some(doc) = store.doc_regions.iter_mut().find(|doc| doc.id == doc_id) {
            doc.symbol_name = symbol_name.clone();
        }
        if let Some(surface) = store.public_surfaces.iter_mut().find(|surface| {
            surface.symbol_name == symbol_name
                && surface.file_id == file.id
                && surface.range == symbol_range
        }) {
            surface.has_doc_region = true;
        }
    }
}

struct DependencyInput<'a> {
    file: &'a FileUnit,
    module_id: &'a str,
    group: DependencyGroup,
    source: String,
    imported: String,
    alias: Option<String>,
    line_number: usize,
    is_glob: bool,
    is_public: bool,
    is_relative: bool,
}

fn add_dependency(store: &mut EvidenceStore, input: DependencyInput<'_>) {
    let dep_hash = hash_text(&format!(
        "{}:{}:{}:{}",
        input.file.relative_path, input.source, input.imported, input.line_number
    ));
    store.dependency_edges.push(DependencyEdgeFact {
        id: stable_id(
            &input.file.id,
            "dep",
            dependency_group_name(input.group),
            input.line_number,
            1,
            &dep_hash,
        ),
        file_id: input.file.id.clone(),
        module_id: input.module_id.to_string(),
        group: input.group,
        source: input.source,
        imported: input.imported,
        alias: input.alias,
        range: line_range(input.line_number),
        is_glob: input.is_glob,
        is_public: input.is_public,
        is_relative: input.is_relative,
    });
}

struct ExpressionInput<'a> {
    file: &'a FileUnit,
    module_id: &'a str,
    symbol_id: Option<String>,
    kind: ExpressionKind,
    line_number: usize,
    text: String,
    callee: Option<String>,
    arguments: Vec<String>,
}

fn add_expression(store: &mut EvidenceStore, input: ExpressionInput<'_>) {
    let text_hash = hash_text(&input.text);
    store.expressions.push(ExpressionFact {
        id: stable_id(
            &input.file.id,
            "expr",
            expression_kind_name(input.kind),
            input.line_number,
            1,
            &text_hash,
        ),
        file_id: input.file.id.clone(),
        module_id: input.module_id.to_string(),
        symbol_id: input.symbol_id,
        kind: input.kind,
        range: line_range(input.line_number),
        text: input.text,
        callee: input.callee,
        arguments: input.arguments,
    });
}

fn add_block(
    store: &mut EvidenceStore,
    file: &FileUnit,
    kind: &str,
    line_number: usize,
    intent_comment_id: Option<String>,
) {
    let block_hash = hash_text(&format!("{}:{kind}:{line_number}", file.relative_path));
    store.block_regions.push(BlockRegionFact {
        id: stable_id(&file.id, "block", kind, line_number, 1, &block_hash),
        file_id: file.id.clone(),
        range: line_range(line_number),
        kind: kind.to_string(),
        intent_comment_id,
    });
}

fn preceding_intent_comment_id(
    store: &EvidenceStore,
    file: &FileUnit,
    line_number: usize,
    markers: &[&str],
) -> Option<String> {
    let expected_line = line_number.saturating_sub(1);

    store
        .text_spans
        .iter()
        .rev()
        .find(|span| {
            span.file_id == file.id
                && range_starts_on_line(&span.range, expected_line)
                && matches!(span.role, TextRole::Comment)
                && markers
                    .iter()
                    .any(|marker| span.normalized_text.trim_start().starts_with(marker))
        })
        .map(|span| span.id.clone())
}

fn range_starts_on_line(range: &str, line_number: usize) -> bool {
    range
        .split_once(':')
        .and_then(|(line, _)| line.parse::<usize>().ok())
        .is_some_and(|line| line == line_number)
}

struct SourceRange {
    start_line: usize,
    start_col: usize,
    end_line: usize,
    end_col: usize,
}

struct TextFactInput<'a> {
    file_id: &'a str,
    is_doc: bool,
    module_doc: bool,
    span: SourceRange,
    content: &'a str,
}

fn add_comment_or_doc_text(store: &mut EvidenceStore, input: TextFactInput<'_>) {
    let text_hash = hash_text(input.content);
    let role = if input.is_doc {
        TextRole::DocSummary
    } else {
        TextRole::Comment
    };
    let text_id = stable_id(
        input.file_id,
        "text",
        if input.is_doc {
            "doc_summary"
        } else {
            "comment"
        },
        input.span.start_line,
        input.span.start_col,
        &text_hash,
    );
    store.text_spans.push(TextSpanFact {
        id: text_id.clone(),
        file_id: input.file_id.to_string(),
        range: format!(
            "{}:{}-{}:{}",
            input.span.start_line, input.span.start_col, input.span.end_line, input.span.end_col
        ),
        role,
        normalized_text: input.content.to_string(),
        text_hash: format!("blake3:{text_hash}"),
        terminal_punctuation: input.content.chars().last(),
    });
    if input.is_doc {
        store.doc_regions.push(DocRegionFact {
            id: stable_id(
                input.file_id,
                "doc",
                "doc_summary",
                input.span.start_line,
                input.span.start_col,
                &text_hash,
            ),
            file_id: input.file_id.to_string(),
            symbol_name: if input.module_doc {
                "__module__".to_string()
            } else {
                "__pending_symbol__".to_string()
            },
            range: format!(
                "{}:{}-{}:{}",
                input.span.start_line,
                input.span.start_col,
                input.span.end_line,
                input.span.end_col
            ),
            summary_text_id: text_id,
            full_text_id: None,
        });
    } else {
        store.comment_regions.push(CommentRegionFact {
            id: stable_id(
                input.file_id,
                "comment",
                "line_comment",
                input.span.start_line,
                input.span.start_col,
                &text_hash,
            ),
            file_id: input.file_id.to_string(),
            range: format!(
                "{}:{}-{}:{}",
                input.span.start_line,
                input.span.start_col,
                input.span.end_line,
                input.span.end_col
            ),
            kind: "line_comment".to_string(),
            text_id,
        });
    }
}

fn detect_include_boundary(source: &str) -> (Option<String>, bool) {
    let mut ifndef = None;
    let mut pragma_once = false;
    for line in source.lines().take(8) {
        let trimmed = line.trim();
        if trimmed == "#pragma once" {
            pragma_once = true;
        }
        if let Some(name) = trimmed.strip_prefix("#ifndef ") {
            ifndef = Some(name.trim().to_string());
        }
        if let Some(name) = trimmed.strip_prefix("#define ") {
            if ifndef.as_deref() == Some(name.trim()) {
                return (ifndef, pragma_once);
            }
        }
    }
    (None, pragma_once)
}

fn is_header_path(path: &str) -> bool {
    path.ends_with(".h")
        || path.ends_with(".hh")
        || path.ends_with(".hpp")
        || path.ends_with(".hxx")
}

fn dependency_group_for(source: &str, language: Language) -> DependencyGroup {
    match language {
        Language::Python => {
            if is_python_standard_dependency(source) {
                DependencyGroup::Standard
            } else {
                DependencyGroup::Unknown
            }
        }
        Language::Rust => {
            if matches!(source, "std" | "core" | "alloc") {
                DependencyGroup::Standard
            } else if matches!(source, "crate" | "self" | "super") {
                DependencyGroup::Local
            } else {
                DependencyGroup::Unknown
            }
        }
        Language::C | Language::Cpp => {
            if matches!(
                source,
                "algorithm" | "stddef" | "stdint" | "stdio" | "stdlib" | "string" | "vector"
            ) {
                DependencyGroup::Standard
            } else {
                DependencyGroup::Unknown
            }
        }
    }
}

fn is_python_standard_dependency(source: &str) -> bool {
    let root = source.split('.').next().unwrap_or(source);
    matches!(
        root,
        "abc"
            | "antigravity"
            | "argparse"
            | "array"
            | "ast"
            | "asyncio"
            | "atexit"
            | "base64"
            | "bdb"
            | "binascii"
            | "bisect"
            | "builtins"
            | "bz2"
            | "cProfile"
            | "calendar"
            | "cmath"
            | "cmd"
            | "code"
            | "codecs"
            | "codeop"
            | "collections"
            | "colorsys"
            | "compileall"
            | "concurrent"
            | "configparser"
            | "contextlib"
            | "contextvars"
            | "copy"
            | "copyreg"
            | "csv"
            | "curses"
            | "ctypes"
            | "dataclasses"
            | "datetime"
            | "dbm"
            | "decimal"
            | "difflib"
            | "dis"
            | "doctest"
            | "email"
            | "encodings"
            | "ensurepip"
            | "enum"
            | "errno"
            | "faulthandler"
            | "fcntl"
            | "filecmp"
            | "fileinput"
            | "fnmatch"
            | "fractions"
            | "ftplib"
            | "functools"
            | "gc"
            | "genericpath"
            | "getopt"
            | "getpass"
            | "gettext"
            | "glob"
            | "graphlib"
            | "grp"
            | "gzip"
            | "hashlib"
            | "heapq"
            | "hmac"
            | "html"
            | "http"
            | "idlelib"
            | "imaplib"
            | "importlib"
            | "inspect"
            | "io"
            | "ipaddress"
            | "itertools"
            | "json"
            | "keyword"
            | "linecache"
            | "locale"
            | "logging"
            | "lzma"
            | "mailbox"
            | "marshal"
            | "math"
            | "mimetypes"
            | "mmap"
            | "modulefinder"
            | "msvcrt"
            | "multiprocessing"
            | "netrc"
            | "nt"
            | "ntpath"
            | "nturl2path"
            | "numbers"
            | "opcode"
            | "operator"
            | "optparse"
            | "os"
            | "pathlib"
            | "pdb"
            | "pickle"
            | "pickletools"
            | "pkgutil"
            | "platform"
            | "plistlib"
            | "poplib"
            | "posix"
            | "posixpath"
            | "pprint"
            | "profile"
            | "pstats"
            | "pty"
            | "pwd"
            | "py_compile"
            | "pyclbr"
            | "pydoc"
            | "pydoc_data"
            | "pyexpat"
            | "queue"
            | "quopri"
            | "random"
            | "re"
            | "readline"
            | "reprlib"
            | "resource"
            | "rlcompleter"
            | "runpy"
            | "sched"
            | "secrets"
            | "select"
            | "selectors"
            | "shelve"
            | "shlex"
            | "shutil"
            | "signal"
            | "site"
            | "smtplib"
            | "socket"
            | "socketserver"
            | "sqlite3"
            | "sre_compile"
            | "sre_constants"
            | "sre_parse"
            | "ssl"
            | "stat"
            | "statistics"
            | "string"
            | "stringprep"
            | "struct"
            | "subprocess"
            | "symtable"
            | "sys"
            | "sysconfig"
            | "syslog"
            | "tabnanny"
            | "tarfile"
            | "tempfile"
            | "termios"
            | "textwrap"
            | "this"
            | "threading"
            | "time"
            | "timeit"
            | "tkinter"
            | "tomllib"
            | "token"
            | "tokenize"
            | "trace"
            | "traceback"
            | "tracemalloc"
            | "tty"
            | "turtle"
            | "turtledemo"
            | "types"
            | "typing"
            | "unicodedata"
            | "unittest"
            | "urllib"
            | "uuid"
            | "venv"
            | "warnings"
            | "wave"
            | "weakref"
            | "webbrowser"
            | "winreg"
            | "winsound"
            | "wsgiref"
            | "xml"
            | "xmlrpc"
            | "zipapp"
            | "zipfile"
            | "zipimport"
            | "zlib"
            | "zoneinfo"
    )
}

fn logging_callee(trimmed: &str) -> Option<String> {
    for marker in [
        ".debug(",
        ".info(",
        ".warning(",
        ".error(",
        ".exception(",
        ".critical(",
        ".log(",
    ] {
        if let Some(index) = code_marker_positions(trimmed, marker).into_iter().next() {
            let prefix = &trimmed[..index];
            let receiver = prefix.split_whitespace().last().unwrap_or(prefix);
            if !is_python_logger_receiver(receiver.trim()) {
                continue;
            }
            return Some(format!(
                "{}{}",
                receiver.trim(),
                marker.trim_end_matches('(')
            ));
        }
    }
    None
}

fn is_python_logger_receiver(receiver: &str) -> bool {
    if receiver.contains('(') {
        return false;
    }
    let normalized = receiver.trim().trim_matches('(');
    matches!(normalized, "logger" | "LOGGER" | "self.logger")
        || normalized
            .to_ascii_lowercase()
            .rsplit(['.', '_'])
            .next()
            .is_some_and(|tail| tail == "logger")
}

fn python_error_message(trimmed: &str) -> Option<(String, Vec<String>)> {
    let expression = trimmed.strip_prefix("raise ")?;
    let callee = expression.split_once('(')?.0.trim();
    if !callee.ends_with("Error") && !callee.ends_with("Exception") {
        return None;
    }
    let arguments = call_arguments(expression);
    if arguments
        .iter()
        .any(|argument| argument.contains('"') || argument.contains('\''))
    {
        Some((callee.to_string(), arguments))
    } else {
        None
    }
}

fn blocking_callee(trimmed: &str) -> Option<String> {
    if trimmed.contains("thread::sleep(") {
        Some("thread::sleep".to_string())
    } else if trimmed.contains("std::fs::") {
        Some("std::fs".to_string())
    } else {
        None
    }
}

fn panic_callee(trimmed: &str) -> Option<String> {
    if trimmed.contains(".unwrap(") {
        return Some("unwrap".to_string());
    }
    if trimmed.contains(".expect(") {
        return Some("expect".to_string());
    }
    for callee in ["panic!", "todo!", "unimplemented!"] {
        if trimmed.contains(&format!("{callee}(")) {
            return Some(callee.to_string());
        }
    }
    None
}

fn rust_unsafe_block(code: &str) -> bool {
    contains_keyword(code, "unsafe") && code.contains('{')
}

fn strip_rust_non_code(text: &str) -> String {
    let trimmed = text.trim_start();
    if trimmed.starts_with("//") {
        return String::new();
    }
    let code = strip_string_literals(text);
    let line_comment = code.find("//").unwrap_or(code.len());
    let block_comment = code.find("/*").unwrap_or(code.len());
    let end = line_comment.min(block_comment);
    code[..end].to_string()
}

fn allocation_callee(trimmed: &str) -> Option<String> {
    let code = strip_c_family_non_code(trimmed);
    for callee in ["malloc", "calloc", "realloc", "free"] {
        if contains_call(&code, callee) {
            return Some(callee.to_string());
        }
    }
    for keyword in ["new", "delete"] {
        if contains_keyword(&code, keyword) {
            return Some(keyword.to_string());
        }
    }
    None
}

fn strip_c_family_non_code(text: &str) -> String {
    let trimmed = text.trim_start();
    if trimmed.starts_with("//") || trimmed.starts_with("/*") || trimmed.starts_with('*') {
        return String::new();
    }
    let code = strip_string_literals(text);
    let line_comment = code.find("//").unwrap_or(code.len());
    let block_comment = code.find("/*").unwrap_or(code.len());
    let end = line_comment.min(block_comment);
    code[..end].to_string()
}

fn contains_call(code: &str, callee: &str) -> bool {
    let mut start = 0;
    while let Some(offset) = code[start..].find(callee) {
        let index = start + offset;
        let before = code[..index].chars().next_back();
        let after_index = index + callee.len();
        let after = code[after_index..].chars().next();
        let boundary_before = before.is_none_or(|character| !is_identifier_char(character));
        let boundary_after = after.is_none_or(|character| !is_identifier_char(character));
        if boundary_before && boundary_after && code[after_index..].trim_start().starts_with('(') {
            return true;
        }
        start = after_index;
    }
    false
}

fn contains_keyword(code: &str, keyword: &str) -> bool {
    let mut start = 0;
    while let Some(offset) = code[start..].find(keyword) {
        let index = start + offset;
        let before = code[..index].chars().next_back();
        let after_index = index + keyword.len();
        let after = code[after_index..].chars().next();
        if before.is_none_or(|character| !is_identifier_char(character))
            && after.is_none_or(|character| !is_identifier_char(character))
        {
            return true;
        }
        start = after_index;
    }
    false
}

fn is_identifier_char(character: char) -> bool {
    character == '_' || character.is_ascii_alphanumeric()
}

fn strip_string_literals(text: &str) -> String {
    let mut output = String::with_capacity(text.len());
    let mut quote = None;
    let mut escaped = false;
    for character in text.chars() {
        if let Some(active_quote) = quote {
            output.push(' ');
            if escaped {
                escaped = false;
            } else if character == '\\' {
                escaped = true;
            } else if character == active_quote {
                quote = None;
            }
            continue;
        }
        if character == '"' || character == '\'' {
            quote = Some(character);
            output.push(' ');
        } else {
            output.push(character);
        }
    }
    output
}

fn looks_like_declaration(trimmed: &str) -> bool {
    trimmed.ends_with(';') || trimmed.ends_with('{') || trimmed.contains(") {")
}

fn looks_like_call_statement(trimmed: &str, before_paren: &str, name: &str) -> bool {
    let before_name = before_paren.trim_end_matches(name).trim();
    before_name.is_empty()
        || before_name.ends_with('=')
        || before_name.ends_with(',')
        || before_name.ends_with('(')
        || before_name.ends_with("return")
        || trimmed.starts_with("return ")
}

fn call_arguments(trimmed: &str) -> Vec<String> {
    trimmed
        .split_once('(')
        .and_then(|(_, tail)| tail.rsplit_once(')'))
        .map(|(arguments, _)| {
            arguments
                .split(',')
                .map(str::trim)
                .filter(|argument| !argument.is_empty())
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default()
}

fn python_visibility(name: &str) -> SymbolVisibility {
    if is_python_protocol_method(name) {
        SymbolVisibility::Public
    } else if name.starts_with("__") {
        SymbolVisibility::Private
    } else if name.starts_with('_') {
        SymbolVisibility::Internal
    } else {
        SymbolVisibility::Public
    }
}

fn is_python_protocol_method(name: &str) -> bool {
    name.len() > 4 && name.starts_with("__") && name.ends_with("__")
}

fn qualified_name(path: &str, name: &str) -> String {
    let module = path
        .trim_end_matches(".py")
        .trim_end_matches(".rs")
        .trim_end_matches(".c")
        .trim_end_matches(".cc")
        .trim_end_matches(".cpp")
        .trim_end_matches(".hpp")
        .trim_end_matches(".h")
        .replace('/', ".");
    format!("{module}.{name}")
}

fn line_range(line_number: usize) -> String {
    format!("{line_number}:1-{line_number}:1")
}

fn start_line(range: &str) -> Option<usize> {
    range.split_once(':')?.0.parse().ok()
}

fn end_line(range: &str) -> Option<usize> {
    range.split_once('-')?.1.split_once(':')?.0.parse().ok()
}

fn dependency_group_name(group: DependencyGroup) -> &'static str {
    match group {
        DependencyGroup::Future => "future",
        DependencyGroup::Standard => "standard",
        DependencyGroup::ThirdParty => "third_party",
        DependencyGroup::Local => "local",
        DependencyGroup::Unknown => "unknown",
    }
}

fn symbol_kind_name(kind: SymbolKind) -> &'static str {
    match kind {
        SymbolKind::Module => "module",
        SymbolKind::Class => "class",
        SymbolKind::Struct => "struct",
        SymbolKind::Enum => "enum",
        SymbolKind::Trait => "trait",
        SymbolKind::Union => "union",
        SymbolKind::Function => "function",
        SymbolKind::Method => "method",
        SymbolKind::Field => "field",
        SymbolKind::Variable => "variable",
        SymbolKind::Parameter => "parameter",
        SymbolKind::Constant => "constant",
        SymbolKind::TypeAlias => "type_alias",
        SymbolKind::Macro => "macro",
    }
}

fn visibility_name(visibility: SymbolVisibility) -> &'static str {
    match visibility {
        SymbolVisibility::Public => "public",
        SymbolVisibility::Internal => "internal",
        SymbolVisibility::Private => "private",
    }
}

fn expression_kind_name(kind: ExpressionKind) -> &'static str {
    match kind {
        ExpressionKind::Call => "call",
        ExpressionKind::Import => "import",
        ExpressionKind::TypeExpression => "type_expression",
        ExpressionKind::LoggingCall => "logging_call",
        ExpressionKind::ErrorMessage => "error_message",
        ExpressionKind::Suppression => "suppression",
        ExpressionKind::MacroInvocation => "macro_invocation",
        ExpressionKind::MacroDefinition => "macro_definition",
        ExpressionKind::Preprocessor => "preprocessor",
        ExpressionKind::Panic => "panic",
        ExpressionKind::Await => "await",
        ExpressionKind::Lock => "lock",
        ExpressionKind::Allocation => "allocation",
    }
}

fn stable_id(
    file_id: &str,
    fact_kind: &str,
    role_or_kind: &str,
    line: usize,
    column: usize,
    hash: &str,
) -> String {
    format!("ev:{file_id}:{fact_kind}:{role_or_kind}:{line}:{column}:{hash}")
}

struct OpeningTriple<'a> {
    quote: &'a str,
    start_byte: usize,
    delimiter_byte: usize,
}

struct Docstring {
    start_line: usize,
    start_col: usize,
    end_line: usize,
    end_col: usize,
    summary_start_line: usize,
    summary_start_col: usize,
    summary_end_line: usize,
    summary_end_col: usize,
    summary: String,
    full_text: String,
}

struct SummarySpan {
    start_line: usize,
    start_col: usize,
    end_line: usize,
    end_col: usize,
    text: String,
}

struct CommentSpan {
    region_start_line: usize,
    region_start_col: usize,
    region_end_line: usize,
    region_end_col: usize,
    text_start_line: usize,
    text_start_col: usize,
    text_end_line: usize,
    text_end_col: usize,
    text: String,
}
