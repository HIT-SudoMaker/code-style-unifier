use std::collections::HashMap;

use crate::core::evidence::{EvidenceStore, ModuleUnitFact, SymbolFact, SymbolKind, TextRole, TextSpanFact};
use crate::core::issue::{Domain, Issue, IssueKind, Language, Scope};
use crate::core::profile::Profile;

/// 返回已实现的 TypeScript 规则 ID
pub fn implemented_rule_ids() -> Vec<&'static str> {
    vec!["Ts001", "Ts002", "Ts003"]
}

/// 评估 TypeScript 专属漂移规则
pub fn evaluate(store: &EvidenceStore, _profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    issues.extend(evaluate_export_style_consistency(store));
    issues.extend(evaluate_comment_language_consistency(store));
    issues.extend(evaluate_props_style_consistency(store));
    issues
}

/// Ts001：同一目录内导出风格（default / named）应保持一致
fn evaluate_export_style_consistency(store: &EvidenceStore) -> Vec<Issue> {
    let mut has_default: HashMap<&str, bool> = HashMap::new();
    for symbol in &store.symbols {
        if symbol.language == Language::Typescript
            && symbol.attributes.iter().any(|attr| attr == "export_default")
        {
            has_default.insert(symbol.file_id.as_str(), true);
        }
    }
    let has_surface: HashMap<&str, bool> = store
        .public_surfaces
        .iter()
        .map(|surface| (surface.file_id.as_str(), true))
        .collect();

    // 收集“对外导出”的 TS 文件，按目录分组并记录其导出风格。
    let mut by_directory: HashMap<&str, Vec<ExportingFile>> = HashMap::new();
    for file in &store.file_units {
        if file.language != Language::Typescript || file.excluded || file.generated {
            continue;
        }
        if is_framework_mandated_file(&file.path) {
            continue;
        }
        let uses_default = *has_default.get(file.id.as_str()).unwrap_or(&false);
        let exporting = uses_default || *has_surface.get(file.id.as_str()).unwrap_or(&false);
        if !exporting {
            continue;
        }
        by_directory
            .entry(directory_of(&file.path))
            .or_default()
            .push(ExportingFile {
                file_id: file.id.as_str(),
                uses_default,
            });
    }

    let mut issues = Vec::new();
    for files in by_directory.values() {
        if files.len() < 2 {
            continue;
        }
        let default_count = files.iter().filter(|file| file.uses_default).count();
        let named_count = files.len() - default_count;
        if default_count == 0 || named_count == 0 || default_count == named_count {
            continue;
        }
        let minority_default = default_count < named_count;
        for file in files.iter().filter(|file| file.uses_default == minority_default) {
            if let Some(issue) = module_issue(
                store,
                "Ts001",
                "export.style_consistency",
                IssueKind::UnderReview,
                Domain::Project,
                "目录内导出风格不一致，需要审查",
                file.file_id,
            ) {
                issues.push(issue);
            }
        }
    }
    issues
}

/// Ts002：注释语言应与项目主导语言保持一致
fn evaluate_comment_language_consistency(store: &EvidenceStore) -> Vec<Issue> {
    let spans: Vec<&TextSpanFact> = store
        .text_spans
        .iter()
        .filter(|span| matches!(span.role, TextRole::Comment | TextRole::DocSummary))
        .filter(|span| typescript_active_file(store, &span.file_id))
        .collect();

    let mut cjk = 0usize;
    let mut latin = 0usize;
    for span in &spans {
        match classify_language(&span.normalized_text) {
            CommentLanguage::Cjk => cjk += 1,
            CommentLanguage::Latin => latin += 1,
            CommentLanguage::Neutral => {}
        }
    }
    let total = cjk + latin;
    if total < 4 {
        return Vec::new();
    }
    let dominant_latin = latin >= cjk;
    let dominant_count = if dominant_latin { latin } else { cjk };
    // 主导语言需占明显多数（≥60%），否则项目本身没有统一约定，不做判断。
    if dominant_count * 10 < total * 6 {
        return Vec::new();
    }

    spans
        .iter()
        .filter(|span| match classify_language(&span.normalized_text) {
            CommentLanguage::Cjk => dominant_latin,
            CommentLanguage::Latin => !dominant_latin,
            CommentLanguage::Neutral => false,
        })
        .filter_map(|span| {
            text_issue(
                store,
                "Ts002",
                "comment.language_consistency",
                IssueKind::UnderReview,
                Domain::Style,
                "注释语言与项目主导语言不一致，需要审查",
                span,
            )
        })
        .collect()
}

/// Ts003：Props / State 对象类型的声明方式（interface / type）应保持一致
fn evaluate_props_style_consistency(store: &EvidenceStore) -> Vec<Issue> {
    let candidates: Vec<&SymbolFact> = store
        .symbols
        .iter()
        .filter(|symbol| {
            symbol.language == Language::Typescript && symbol.kind == SymbolKind::TypeAlias
        })
        .filter(|symbol| typescript_active_file(store, &symbol.file_id))
        .filter(|symbol| symbol.name.ends_with("Props") || symbol.name.ends_with("State"))
        .collect();

    let interface_count = candidates.iter().filter(|s| is_interface_style(s)).count();
    let type_object_count = candidates.iter().filter(|s| is_type_object_style(s)).count();
    let total = interface_count + type_object_count;
    if total < 3 {
        return Vec::new();
    }
    let dominant_interface = interface_count >= type_object_count;

    candidates
        .iter()
        .filter(|symbol| {
            if is_interface_style(symbol) {
                !dominant_interface
            } else if is_type_object_style(symbol) {
                dominant_interface
            } else {
                // union / 字面量类型别名只能用 type 表达，不计入漂移。
                false
            }
        })
        .map(|symbol| {
            symbol_issue(
                store,
                "Ts003",
                "type_declaration.props_style_consistency",
                IssueKind::UnderReview,
                Domain::Typing,
                "Props/State 声明方式与项目主导风格不一致，需要审查",
                symbol,
            )
        })
        .collect()
}

struct ExportingFile<'a> {
    file_id: &'a str,
    uses_default: bool,
}

enum CommentLanguage {
    Cjk,
    Latin,
    Neutral,
}

fn classify_language(text: &str) -> CommentLanguage {
    if text.chars().any(is_cjk) {
        CommentLanguage::Cjk
    } else if has_latin_word(text) {
        CommentLanguage::Latin
    } else {
        CommentLanguage::Neutral
    }
}

fn is_cjk(character: char) -> bool {
    matches!(
        character as u32,
        0x3000..=0x303F      // CJK 标点
        | 0x3400..=0x4DBF    // CJK 扩展 A
        | 0x4E00..=0x9FFF    // CJK 基本汉字
        | 0xF900..=0xFAFF    // CJK 兼容汉字
        | 0xFF01..=0xFF60    // 全角标点
    )
}

fn has_latin_word(text: &str) -> bool {
    let mut run = 0;
    for character in text.chars() {
        if character.is_ascii_alphabetic() {
            run += 1;
            if run >= 3 {
                return true;
            }
        } else {
            run = 0;
        }
    }
    false
}

fn is_interface_style(symbol: &SymbolFact) -> bool {
    symbol.attributes.iter().any(|attr| attr == "interface")
}

fn is_type_object_style(symbol: &SymbolFact) -> bool {
    symbol.attributes.iter().any(|attr| attr == "type")
        && symbol.attributes.iter().any(|attr| attr == "type_object")
}

fn directory_of(path: &str) -> &str {
    path.rsplit_once('/').map_or("", |(directory, _)| directory)
}

/// 框架强制规定导出方式的文件（Next.js 约定文件），不参与导出风格一致性判断
fn is_framework_mandated_file(path: &str) -> bool {
    let stem = path
        .rsplit('/')
        .next()
        .and_then(|name| name.split('.').next())
        .unwrap_or("");
    matches!(
        stem,
        "page"
            | "layout"
            | "route"
            | "loading"
            | "error"
            | "not-found"
            | "template"
            | "default"
            | "middleware"
            | "global-error"
            | "sitemap"
            | "robots"
            | "manifest"
            | "opengraph-image"
            | "icon"
    )
}

fn typescript_active_file(store: &EvidenceStore, file_id: &str) -> bool {
    store.file_units.iter().any(|file| {
        file.id == file_id
            && file.language == Language::Typescript
            && !file.excluded
            && !file.generated
    })
}

fn module_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    file_id: &str,
) -> Option<Issue> {
    let module: &ModuleUnitFact = store
        .module_units
        .iter()
        .find(|module| module.file_id == file_id)?;
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", module.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Module,
        domain,
    )
    .with_message(message)
    .with_evidence(module.id.clone());
    if let Some(file) = store.file_units.iter().find(|file| file.id == file_id) {
        issue = issue.with_location(file.language, file.path.clone(), module.range.clone());
    } else {
        issue.range = Some(module.range.clone());
    }
    Some(issue)
}

fn text_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    span: &TextSpanFact,
) -> Option<Issue> {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", span.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Text,
        domain,
    )
    .with_message(message)
    .with_evidence(span.id.clone());
    let file = store.file_units.iter().find(|file| file.id == span.file_id)?;
    issue = issue.with_location(file.language, file.path.clone(), span.range.clone());
    Some(issue)
}

fn symbol_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    symbol: &SymbolFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", symbol.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Symbol,
        domain,
    )
    .with_message(message)
    .with_evidence(symbol.id.clone());
    if let Some(file) = store.file_units.iter().find(|file| file.id == symbol.file_id) {
        issue = issue.with_location(file.language, file.path.clone(), symbol.range.clone());
    } else {
        issue.range = Some(symbol.range.clone());
    }
    issue
}
