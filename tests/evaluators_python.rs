mod support;

use support::{profile, store_from_source};
use unifier::core::evaluators::evaluate_all;
use unifier::core::evaluators::python::evaluate;
use unifier::core::evidence::{
    DependencyEdgeFact, DependencyGroup, EvidenceStore, ExpressionFact, ExpressionKind,
    ModuleUnitFact, SymbolFact, SymbolKind, SymbolVisibility,
};
use unifier::core::issue::{IssueKind, Language, Scope};

#[test]
fn python_module_and_typing_rules_emit_expected_findings() {
    let mut store = EvidenceStore::empty_for_tests();
    store.module_units.push(ModuleUnitFact {
        id: "module:py".to_string(),
        file_id: "file:py".to_string(),
        language: Language::Python,
        path: "module.py".to_string(),
        range: "1:1-20:1".to_string(),
        has_module_doc_region: true,
        is_header: false,
        include_guard: None,
        pragma_once: false,
    });
    store.module_units.push(ModuleUnitFact {
        id: "module:plain".to_string(),
        file_id: "file:plain".to_string(),
        language: Language::Python,
        path: "plain.py".to_string(),
        range: "1:1-10:1".to_string(),
        has_module_doc_region: false,
        is_header: false,
        include_guard: None,
        pragma_once: false,
    });
    store.dependency_edges.push(DependencyEdgeFact {
        id: "dep:future".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        group: DependencyGroup::Future,
        source: "__future__".to_string(),
        imported: "annotations".to_string(),
        alias: None,
        range: "5:1-5:35".to_string(),
        is_glob: false,
        is_public: false,
        is_relative: false,
    });
    store.dependency_edges.push(DependencyEdgeFact {
        id: "dep:typing".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        group: DependencyGroup::Standard,
        source: "typing".to_string(),
        imported: "Iterable".to_string(),
        alias: None,
        range: "1:1-1:28".to_string(),
        is_glob: false,
        is_public: false,
        is_relative: false,
    });
    store.dependency_edges.push(DependencyEdgeFact {
        id: "dep:typing_multi".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        group: DependencyGroup::Standard,
        source: "typing".to_string(),
        imported: "Mapping, Sequence".to_string(),
        alias: None,
        range: "2:1-2:37".to_string(),
        is_glob: false,
        is_public: false,
        is_relative: false,
    });
    store.symbols.push(SymbolFact {
        id: "symbol:run".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        name: "run".to_string(),
        qualified_name: "module.run".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Python,
        range: "8:1-10:1".to_string(),
        doc_region_id: Some("doc:run".to_string()),
        return_annotation: None,
        missing_parameter_annotations: vec!["value".to_string()],
        type_text: None,
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });
    store.symbols.push(SymbolFact {
        id: "symbol:annotated".to_string(),
        file_id: "file:plain".to_string(),
        module_id: "module:plain".to_string(),
        name: "annotated".to_string(),
        qualified_name: "plain.annotated".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Python,
        range: "2:1-3:1".to_string(),
        doc_region_id: Some("doc:annotated".to_string()),
        return_annotation: Some("str".to_string()),
        missing_parameter_annotations: Vec::new(),
        type_text: None,
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });

    let issues = evaluate(&store, &profile());
    let rules = issues
        .iter()
        .map(|issue| issue.rule.as_str())
        .collect::<Vec<_>>();

    for expected in ["Py001", "Py002", "Py003", "Py004", "Py005"] {
        assert!(rules.contains(&expected), "missing {expected}");
    }
    assert!(issues.iter().any(|issue| {
        issue.rule == "Py005"
            && issue.kind == IssueKind::HardViolation
            && issue.scope == Scope::Symbol
    }));
    assert!(issues
        .iter()
        .any(|issue| issue.rule == "Py003" && !issue.blocks));
    assert!(issues.iter().filter(|issue| issue.rule == "Py004").count() >= 2);
}

#[test]
fn py005_ignores_functions_inside_triple_quoted_data() {
    let store = store_from_source(
        "fixture.py",
        r#"
def build_probe() -> str:
    return textwrap.dedent("""
        class FakeQtSignal:
            def connect(self, callback):
                self.callback = callback
    """)
"#,
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Py005"),
        "embedded data must not trigger Python method rule checks"
    );
}

#[test]
fn python_logging_and_expression_rules_emit_expected_findings() {
    let mut store = EvidenceStore::empty_for_tests();
    store.symbols.push(SymbolFact {
        id: "symbol:logger".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        name: "log".to_string(),
        qualified_name: "module.log".to_string(),
        kind: SymbolKind::Variable,
        visibility: SymbolVisibility::Private,
        language: Language::Python,
        range: "3:1-3:35".to_string(),
        doc_region_id: None,
        return_annotation: None,
        missing_parameter_annotations: Vec::new(),
        type_text: Some("logging.getLogger".to_string()),
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });
    store.expressions.push(ExpressionFact {
        id: "expr:type".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        symbol_id: None,
        kind: ExpressionKind::TypeExpression,
        range: "8:20-8:29".to_string(),
        text: "List[str]".to_string(),
        callee: Some("List".to_string()),
        arguments: Vec::new(),
    });
    store.expressions.push(ExpressionFact {
        id: "expr:logging".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        symbol_id: None,
        kind: ExpressionKind::LoggingCall,
        range: "9:5-9:38".to_string(),
        text: "logger.info(f\"value={value}\")".to_string(),
        callee: Some("logger.info".to_string()),
        arguments: vec!["f\"value={value}\"".to_string()],
    });

    let issues = evaluate(&store, &profile());
    let rules = issues
        .iter()
        .map(|issue| issue.rule.as_str())
        .collect::<Vec<_>>();

    for expected in ["Py006", "Py007", "Py008"] {
        assert!(rules.contains(&expected), "missing {expected}");
    }
    assert!(issues.iter().any(|issue| {
        issue.rule == "Py006"
            && issue.kind == IssueKind::HardViolation
            && issue.scope == Scope::Symbol
    }));
}
