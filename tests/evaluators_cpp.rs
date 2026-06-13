mod support;

use support::{profile, store_from_source};
use unifier::core::evaluators::cpp::evaluate;
use unifier::core::evaluators::evaluate_all;
use unifier::core::evidence::{
    BlockRegionFact, DependencyEdgeFact, DependencyGroup, EvidenceStore, ExpressionFact,
    ExpressionKind, FileUnitFact, ModuleUnitFact, SymbolFact, SymbolKind, SymbolVisibility,
};
use unifier::core::issue::{IssueKind, Language};

#[test]
fn cpp006_remains_responsible_for_macro_contract_review() {
    let store = store_from_source(
        "feature_flags.h",
        r#"
#define FEATURE_ENABLED 1
"#,
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        issues.iter().any(|issue| issue.rule == "Cpp006"),
        "macro-specific contract review remains active"
    );
    assert!(
        !issues.iter().any(|issue| issue.rule == "Core011"),
        "Core011 must not duplicate macro contract review as a hard public-doc issue"
    );
}

#[test]
fn cpp_rules_emit_expected_findings() {
    let mut store = EvidenceStore::empty_for_tests();
    store.file_units.push(FileUnitFact {
        id: "file:hpp".to_string(),
        path: "src/api.hpp".to_string(),
        language: Language::Cpp,
        generated: false,
        excluded: false,
        fingerprint: "hash:hpp".to_string(),
    });
    store.module_units.push(ModuleUnitFact {
        id: "module:hpp".to_string(),
        file_id: "file:hpp".to_string(),
        language: Language::Cpp,
        path: "src/api.hpp".to_string(),
        range: "1:1-80:1".to_string(),
        has_module_doc_region: false,
        is_header: true,
        include_guard: None,
        pragma_once: false,
    });
    for (index, imported) in ["vector", "string", "map"].iter().enumerate() {
        store.dependency_edges.push(DependencyEdgeFact {
            id: format!("dep:include:{index}"),
            file_id: "file:hpp".to_string(),
            module_id: "module:hpp".to_string(),
            group: DependencyGroup::Standard,
            source: (*imported).to_string(),
            imported: (*imported).to_string(),
            alias: None,
            range: format!("{}:1-{}:20", index + 2, index + 2),
            is_glob: false,
            is_public: true,
            is_relative: false,
        });
    }
    store.dependency_edges.push(DependencyEdgeFact {
        id: "dep:namespace".to_string(),
        file_id: "file:hpp".to_string(),
        module_id: "module:hpp".to_string(),
        group: DependencyGroup::Standard,
        source: "std".to_string(),
        imported: "*".to_string(),
        alias: None,
        range: "8:1-8:21".to_string(),
        is_glob: true,
        is_public: true,
        is_relative: false,
    });
    store.symbols.push(SymbolFact {
        id: "symbol:abi".to_string(),
        file_id: "file:hpp".to_string(),
        module_id: "module:hpp".to_string(),
        name: "run".to_string(),
        qualified_name: "run".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Cpp,
        range: "10:1-10:30".to_string(),
        doc_region_id: None,
        return_annotation: None,
        missing_parameter_annotations: Vec::new(),
        type_text: Some("extern C int run".to_string()),
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });
    store.symbols.push(SymbolFact {
        id: "symbol:macro".to_string(),
        file_id: "file:hpp".to_string(),
        module_id: "module:hpp".to_string(),
        name: "WRAP".to_string(),
        qualified_name: "WRAP".to_string(),
        kind: SymbolKind::Macro,
        visibility: SymbolVisibility::Public,
        language: Language::Cpp,
        range: "12:1-12:30".to_string(),
        doc_region_id: None,
        return_annotation: None,
        missing_parameter_annotations: Vec::new(),
        type_text: None,
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });
    store.symbols.push(SymbolFact {
        id: "symbol:template".to_string(),
        file_id: "file:hpp".to_string(),
        module_id: "module:hpp".to_string(),
        name: "convert".to_string(),
        qualified_name: "convert".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Cpp,
        range: "14:1-14:30".to_string(),
        doc_region_id: None,
        return_annotation: None,
        missing_parameter_annotations: Vec::new(),
        type_text: Some("T convert".to_string()),
        is_async: false,
        is_unsafe: false,
        attributes: vec!["template".to_string()],
    });
    store.block_regions.push(BlockRegionFact {
        id: "block:preprocessor".to_string(),
        file_id: "file:hpp".to_string(),
        range: "20:1-24:1".to_string(),
        kind: "preprocessor".to_string(),
        intent_comment_id: None,
    });
    store.block_regions.push(BlockRegionFact {
        id: "block:allocation".to_string(),
        file_id: "file:hpp".to_string(),
        range: "30:1-32:1".to_string(),
        kind: "allocation".to_string(),
        intent_comment_id: None,
    });
    for expression in [
        ExpressionFact {
            id: "expr:macro".to_string(),
            file_id: "file:hpp".to_string(),
            module_id: "module:hpp".to_string(),
            symbol_id: Some("symbol:macro".to_string()),
            kind: ExpressionKind::MacroDefinition,
            range: "12:1-12:60".to_string(),
            text: "#define WRAP(x) do { if (x) { (x); } } while (0) \\".to_string(),
            callee: Some("WRAP".to_string()),
            arguments: Vec::new(),
        },
        ExpressionFact {
            id: "expr:allocation".to_string(),
            file_id: "file:hpp".to_string(),
            module_id: "module:hpp".to_string(),
            symbol_id: None,
            kind: ExpressionKind::Allocation,
            range: "30:5-30:20".to_string(),
            text: "new int".to_string(),
            callee: Some("new".to_string()),
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
        "Cpp001", "Cpp002", "Cpp003", "Cpp004", "Cpp005", "Cpp006", "Cpp007", "Cpp008", "Cpp009",
        "Cpp010",
    ] {
        assert!(rules.contains(&expected), "missing {expected}");
    }
    assert!(issues
        .iter()
        .any(|issue| { issue.rule == "Cpp003" && issue.kind == IssueKind::HardViolation }));
    assert!(issues
        .iter()
        .any(|issue| { issue.rule == "Cpp004" && issue.kind == IssueKind::HardViolation }));
}
