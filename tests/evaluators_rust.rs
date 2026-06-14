mod support;

use support::{profile, store_from_source};
use unifier::core::evaluators::evaluate_all;
use unifier::core::evaluators::rust::evaluate;
use unifier::core::evidence::{
    BlockRegionFact, DependencyEdgeFact, DependencyGroup, EvidenceStore, ExpressionFact,
    ExpressionKind, FileUnitFact, ModuleUnitFact, SymbolFact, SymbolKind, SymbolVisibility,
};
use unifier::core::issue::{IssueKind, Language};

#[test]
fn rust_rules_emit_expected_findings() {
    let mut store = EvidenceStore::empty_for_tests();
    store.file_units.push(FileUnitFact {
        id: "file:rust".to_string(),
        path: "src/lib.rs".to_string(),
        language: Language::Rust,
        generated: false,
        excluded: false,
        fingerprint: "hash:rust".to_string(),
    });
    store.module_units.push(ModuleUnitFact {
        id: "module:rust".to_string(),
        file_id: "file:rust".to_string(),
        language: Language::Rust,
        path: "src/lib.rs".to_string(),
        range: "1:1-80:1".to_string(),
        has_module_doc_region: false,
        is_header: false,
        include_guard: None,
        pragma_once: false,
    });
    store.dependency_edges.push(DependencyEdgeFact {
        id: "dep:prelude".to_string(),
        file_id: "file:rust".to_string(),
        module_id: "module:rust".to_string(),
        group: DependencyGroup::Local,
        source: "crate".to_string(),
        imported: "{run, *}".to_string(),
        alias: None,
        block_id: "module".to_string(),
        range: "3:1-3:20".to_string(),
        is_glob: true,
        is_public: true,
        is_relative: false,
        is_deferred: false,
        is_type_checking: false,
        is_conditional: false,
    });
    store.symbols.push(SymbolFact {
        id: "symbol:prelude".to_string(),
        file_id: "file:rust".to_string(),
        module_id: "module:rust".to_string(),
        name: "prelude".to_string(),
        qualified_name: "prelude".to_string(),
        kind: SymbolKind::Module,
        visibility: SymbolVisibility::Public,
        language: Language::Rust,
        range: "3:1-3:20".to_string(),
        doc_region_id: None,
        return_annotation: None,
        missing_parameter_annotations: Vec::new(),
        type_text: None,
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });
    store.symbols.push(SymbolFact {
        id: "symbol:ffi".to_string(),
        file_id: "file:rust".to_string(),
        module_id: "module:rust".to_string(),
        name: "run_ffi".to_string(),
        qualified_name: "run_ffi".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Rust,
        range: "10:1-12:1".to_string(),
        doc_region_id: None,
        return_annotation: Some("i32".to_string()),
        missing_parameter_annotations: Vec::new(),
        type_text: Some("extern C".to_string()),
        is_async: false,
        is_unsafe: true,
        attributes: vec!["no_mangle".to_string()],
    });
    store.symbols.push(SymbolFact {
        id: "symbol:trait".to_string(),
        file_id: "file:rust".to_string(),
        module_id: "module:rust".to_string(),
        name: "reader".to_string(),
        qualified_name: "reader".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Rust,
        range: "14:1-15:1".to_string(),
        doc_region_id: None,
        return_annotation: Some("Box<dyn Read>".to_string()),
        missing_parameter_annotations: Vec::new(),
        type_text: None,
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });
    store.symbols.push(SymbolFact {
        id: "symbol:async".to_string(),
        file_id: "file:rust".to_string(),
        module_id: "module:rust".to_string(),
        name: "run".to_string(),
        qualified_name: "run".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Rust,
        range: "20:1-40:1".to_string(),
        doc_region_id: None,
        return_annotation: Some("()".to_string()),
        missing_parameter_annotations: Vec::new(),
        type_text: None,
        is_async: true,
        is_unsafe: false,
        attributes: Vec::new(),
    });
    store.block_regions.push(BlockRegionFact {
        id: "block:unsafe".to_string(),
        file_id: "file:rust".to_string(),
        range: "22:1-24:1".to_string(),
        kind: "unsafe".to_string(),
        intent_comment_id: None,
    });
    for expression in [
        ExpressionFact {
            id: "expr:feature".to_string(),
            file_id: "file:rust".to_string(),
            module_id: "module:rust".to_string(),
            symbol_id: None,
            kind: ExpressionKind::MacroInvocation,
            range: "1:1-1:18".to_string(),
            text: "#![feature(test)]".to_string(),
            callee: Some("feature".to_string()),
            arguments: Vec::new(),
        },
        ExpressionFact {
            id: "expr:cfg".to_string(),
            file_id: "file:rust".to_string(),
            module_id: "module:rust".to_string(),
            symbol_id: None,
            kind: ExpressionKind::MacroInvocation,
            range: "2:1-2:22".to_string(),
            text: "#[cfg(feature = \"x\")]".to_string(),
            callee: Some("cfg".to_string()),
            arguments: Vec::new(),
        },
        ExpressionFact {
            id: "expr:blocking".to_string(),
            file_id: "file:rust".to_string(),
            module_id: "module:rust".to_string(),
            symbol_id: None,
            kind: ExpressionKind::Call,
            range: "25:5-25:30".to_string(),
            text: "thread::sleep(duration)".to_string(),
            callee: Some("thread::sleep".to_string()),
            arguments: Vec::new(),
        },
        ExpressionFact {
            id: "expr:lock".to_string(),
            file_id: "file:rust".to_string(),
            module_id: "module:rust".to_string(),
            symbol_id: None,
            kind: ExpressionKind::Lock,
            range: "26:5-26:22".to_string(),
            text: "lock.lock()".to_string(),
            callee: Some("lock".to_string()),
            arguments: Vec::new(),
        },
        ExpressionFact {
            id: "expr:await".to_string(),
            file_id: "file:rust".to_string(),
            module_id: "module:rust".to_string(),
            symbol_id: None,
            kind: ExpressionKind::Await,
            range: "27:5-27:20".to_string(),
            text: "work.await".to_string(),
            callee: None,
            arguments: Vec::new(),
        },
        ExpressionFact {
            id: "expr:panic".to_string(),
            file_id: "file:rust".to_string(),
            module_id: "module:rust".to_string(),
            symbol_id: None,
            kind: ExpressionKind::Panic,
            range: "30:5-30:15".to_string(),
            text: "value.unwrap()".to_string(),
            callee: Some("unwrap".to_string()),
            arguments: Vec::new(),
        },
    ] {
        store.expressions.push(expression);
    }

    let issues = evaluate(&store, &profile());
    let rules = issues
        .iter()
        .map(|issue| issue.rule.as_str())
        .collect::<Vec<_>>();

    for expected in [
        "Rust001", "Rust002", "Rust003", "Rust004", "Rust005", "Rust006", "Rust007", "Rust008",
        "Rust009", "Rust010",
    ] {
        assert!(rules.contains(&expected), "missing {expected}");
    }
    assert!(issues
        .iter()
        .all(|issue| issue.kind != IssueKind::HardViolation));
}

#[test]
fn rust005_detects_full_export_attribute_text_from_source() {
    let cases = [
        (
            "export_name",
            r#"
#[export_name = "ffi_export"]
pub fn exported() -> i32 { 0 }
"#,
        ),
        (
            "unsafe export_name",
            r#"
#[unsafe(export_name = "ffi_export")]
pub fn exported() -> i32 { 0 }
"#,
        ),
        (
            "link_name",
            r#"
#[link_name = "ffi_link"]
pub fn linked() -> i32 { 0 }
"#,
        ),
        (
            "unsafe link_name",
            r#"
#[unsafe(link_name = "ffi_link")]
pub fn linked() -> i32 { 0 }
"#,
        ),
        (
            "unsafe no_mangle",
            r#"
#[unsafe(no_mangle)]
pub fn exported() -> i32 { 0 }
"#,
        ),
    ];

    for (name, source) in cases {
        let store = store_from_source("lib.rs", source);
        let issues = evaluate(&store, &profile());

        assert!(
            issues.iter().any(|issue| issue.rule == "Rust005"),
            "{name} attribute should trigger Rust005"
        );
    }
}

#[test]
fn rust007_accepts_adjacent_safety_comment() {
    let store = store_from_source(
        "bench_list.rs",
        r#"
fn sum_items(list: &List) -> usize {
    // SAFETY: `i` is always in bounds and a critical section is held
    unsafe { list.get_item_unchecked(i) }
}
"#,
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Rust007"),
        "unsafe block with adjacent SAFETY rationale must not trigger Rust007"
    );
}

#[test]
fn rust007_rejects_non_leading_or_non_adjacent_safety_comments() {
    let cases = [
        (
            "UNSAFETY",
            r#"
fn sum_items(list: &List) -> usize {
    // UNSAFETY: this is not an adjacent safety intent marker
    unsafe { list.get_item_unchecked(i) }
}
"#,
        ),
        (
            "TODO SAFETY",
            r#"
fn sum_items(list: &List) -> usize {
    // TODO SAFETY: add a real rationale later
    unsafe { list.get_item_unchecked(i) }
}
"#,
        ),
        (
            "blank line",
            r#"
fn sum_items(list: &List) -> usize {
    // SAFETY: `i` is always in bounds and a critical section is held

    unsafe { list.get_item_unchecked(i) }
}
"#,
        ),
    ];

    for (name, source) in cases {
        let store = store_from_source("bench_list.rs", source);
        let issues = evaluate_all(&store, &profile());

        assert!(
            issues.iter().any(|issue| issue.rule == "Rust007"),
            "{name} comment must not suppress Rust007"
        );
    }
}
