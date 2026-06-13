use unifier::core::evidence::{
    DependencyEdgeFact, DependencyGroup, EvidenceStore, ExpressionFact, ExpressionKind,
    ModuleUnitFact, SymbolFact, SymbolKind, SymbolVisibility,
};
use unifier::core::issue::Language;

#[test]
fn typed_facts_round_trip_as_json() {
    let module = ModuleUnitFact {
        id: "module:1".to_string(),
        file_id: "file:1".to_string(),
        language: Language::Python,
        path: "pkg/mod.py".to_string(),
        range: "1:1-10:1".to_string(),
        has_module_doc_region: false,
        is_header: false,
        include_guard: None,
        pragma_once: false,
    };
    let symbol = SymbolFact {
        id: "symbol:1".to_string(),
        file_id: "file:1".to_string(),
        module_id: "module:1".to_string(),
        name: "run".to_string(),
        qualified_name: "pkg.mod.run".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Python,
        range: "3:1-5:1".to_string(),
        doc_region_id: None,
        return_annotation: None,
        missing_parameter_annotations: vec!["value".to_string()],
        type_text: None,
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    };
    let edge = DependencyEdgeFact {
        id: "dep:1".to_string(),
        file_id: "file:1".to_string(),
        module_id: "module:1".to_string(),
        group: DependencyGroup::Standard,
        source: "typing".to_string(),
        imported: "List".to_string(),
        alias: None,
        range: "1:1-1:25".to_string(),
        is_glob: false,
        is_public: false,
        is_relative: false,
    };
    let expression = ExpressionFact {
        id: "expr:1".to_string(),
        file_id: "file:1".to_string(),
        module_id: "module:1".to_string(),
        symbol_id: Some("symbol:1".to_string()),
        kind: ExpressionKind::Call,
        range: "4:5-4:16".to_string(),
        text: "logger.info".to_string(),
        callee: Some("logger.info".to_string()),
        arguments: vec!["f\"value={value}\"".to_string()],
    };

    let module_json = serde_json::to_string(&module).unwrap();
    let symbol_json = serde_json::to_string(&symbol).unwrap();
    let edge_json = serde_json::to_string(&edge).unwrap();
    let expression_json = serde_json::to_string(&expression).unwrap();

    assert_eq!(module, serde_json::from_str(&module_json).unwrap());
    assert_eq!(symbol, serde_json::from_str(&symbol_json).unwrap());
    assert_eq!(edge, serde_json::from_str(&edge_json).unwrap());
    assert_eq!(expression, serde_json::from_str(&expression_json).unwrap());
    assert!(symbol_json.contains("\"kind\":\"function\""));
    assert!(edge_json.contains("\"group\":\"standard\""));
    assert!(expression_json.contains("\"kind\":\"call\""));
}

#[test]
fn evidence_store_deserializes_without_new_fact_vectors() {
    let json = r#"{
        "schema_version": "1",
        "workspace": {
            "id": "workspace:test",
            "root": ".",
            "target": ".",
            "profile_id": "default",
            "fingerprint": "hash:test"
        },
        "file_units": [],
        "doc_regions": [],
        "comment_regions": [],
        "text_spans": [],
        "line_spans": [],
        "public_surfaces": [],
        "block_regions": []
    }"#;

    let store: EvidenceStore = serde_json::from_str(json).unwrap();

    assert!(store.module_units.is_empty());
    assert!(store.dependency_edges.is_empty());
    assert!(store.symbols.is_empty());
    assert!(store.expressions.is_empty());
}
