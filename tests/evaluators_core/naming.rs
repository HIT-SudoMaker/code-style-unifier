use crate::support::{profile, store_from_source};
use unifier::core::evaluators::core::evaluate;
use unifier::core::evaluators::evaluate_all;
use unifier::core::evidence::{
    EvidenceStore, FileUnitFact, SymbolFact, SymbolKind, SymbolVisibility,
};
use unifier::core::issue::{IssueKind, Language};

fn store_with_core014_function(
    language: Language,
    name: &str,
    type_text: Option<&str>,
    attributes: Vec<&str>,
) -> EvidenceStore {
    let mut store = EvidenceStore::empty_for_tests();
    store.file_units.push(FileUnitFact {
        id: "file:lib".to_string(),
        path: "src/lib.rs".to_string(),
        language,
        generated: false,
        excluded: false,
        fingerprint: "hash:lib".to_string(),
    });
    store.symbols.push(SymbolFact {
        id: "symbol:test".to_string(),
        file_id: "file:lib".to_string(),
        module_id: "module:lib".to_string(),
        name: name.to_string(),
        qualified_name: name.to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language,
        range: "4:1-4:1".to_string(),
        doc_region_id: None,
        return_annotation: Some("*mut PyObject".to_string()),
        missing_parameter_annotations: Vec::new(),
        type_text: type_text.map(str::to_string),
        is_async: false,
        is_unsafe: type_text.is_some_and(|text| text.contains("unsafe")),
        attributes: attributes.into_iter().map(str::to_string).collect(),
    });
    store
}

#[test]
fn core014_allows_rust_abi_name_with_explicit_reason() {
    let store = store_with_core014_function(
        Language::Rust,
        "PyInit_sequential",
        Some("pub unsafe extern \"C\" fn PyInit_sequential() -> *mut PyObject"),
        vec![
            "allow(non_snake_case, reason = \"must be named `PyInit_<module>`\")",
            "no_mangle",
        ],
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Core014"),
        "explicit ABI naming evidence must prevent Core014 hard violation"
    );
}

#[test]
fn core014_still_reports_rust_mixed_case_without_abi_evidence() {
    let store =
        store_with_core014_function(Language::Rust, "BadName", Some("pub fn BadName()"), vec![]);

    let issues = evaluate_all(&store, &profile());

    assert!(
        issues.iter().any(|issue| issue.rule == "Core014"),
        "plain mixed-case Rust function remains a naming violation"
    );
}

#[test]
fn core014_reports_incomplete_or_irrelevant_abi_evidence() {
    let cases = [
        (
            Language::Rust,
            Some("extern C"),
            vec!["no_mangle"],
            "ABI plus export is not enough without a reasoned non_snake_case allow",
        ),
        (
            Language::Rust,
            Some("extern C"),
            vec!["allow(non_snake_case, reason = \"must be named `PyInit_<module>`\")"],
            "ABI plus reasoned allow is not enough without an export attribute",
        ),
        (
            Language::Python,
            Some("extern C"),
            vec![
                "allow(non_snake_case, reason = \"must be named `PyInit_<module>`\")",
                "no_mangle",
            ],
            "Rust ABI naming evidence only applies to Rust symbols",
        ),
        (
            Language::Rust,
            Some("extern \"C\""),
            vec![
                "allow(non_snake_case, reason = \"must be named `PyInit_<module>`\")",
                "not_no_mangle",
            ],
            "export evidence must not be inferred from an arbitrary no_mangle substring",
        ),
        (
            Language::Rust,
            Some("extern \"C\""),
            vec![
                "disallow(non_snake_case, reason = \"must be named `PyInit_<module>`\")",
                "no_mangle",
            ],
            "reasoned allow evidence must come from an allow attribute",
        ),
    ];

    for (language, type_text, attributes, message) in cases {
        let store =
            store_with_core014_function(language, "PyInit_sequential", type_text, attributes);
        let issues = evaluate_all(&store, &profile());

        assert!(
            issues.iter().any(|issue| issue.rule == "Core014"),
            "{message}"
        );
    }
}

#[test]
fn core014_allows_python_qt_override_methods_with_qt_class_context() {
    let store = store_from_source(
        "widget.py",
        concat!(
            "class PreviewWidget(QWidget):\n",
            "    def paintEvent(self, event: QPaintEvent) -> None:\n",
            "        pass\n",
            "\n",
            "    def closeEvent(self, event: QCloseEvent) -> None:\n",
            "        pass\n",
        ),
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Core014"),
        "Qt framework override methods must not be treated as Python case violations"
    );
}

#[test]
fn core014_still_reports_qt_named_method_without_qt_context() {
    let store = store_from_source(
        "plain.py",
        concat!(
            "class PlainWidget:\n",
            "    def paintEvent(self, event: object) -> None:\n",
            "        pass\n",
        ),
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        issues.iter().any(|issue| issue.rule == "Core014"),
        "Qt override names only receive an exemption when Qt class context is present"
    );
}

#[test]
fn core014_reviews_unknown_camel_case_method_inside_qt_class() {
    let store = store_from_source(
        "widget.py",
        concat!(
            "class PreviewWidget(QWidget):\n",
            "    def refreshPreviewPane(self) -> None:\n",
            "        pass\n",
        ),
    );

    let issues = evaluate_all(&store, &profile());
    let core014 = issues
        .iter()
        .find(|issue| issue.rule == "Core014")
        .expect("Qt class camelCase method outside the known override set needs review");

    assert_eq!(core014.kind, IssueKind::UnderReview);
}

#[test]
fn core014_recognizes_common_qt_model_and_delegate_overrides() {
    let store = store_from_source(
        "model.py",
        concat!(
            "class Rows(QAbstractTableModel):\n",
            "    def rowCount(self, parent: QModelIndex) -> int:\n",
            "        return 0\n",
            "\n",
            "class ItemDelegate(QStyledItemDelegate):\n",
            "    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:\n",
            "        return QSize(1, 1)\n",
        ),
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Core014"),
        "common Qt model and delegate override methods must not become naming findings"
    );
}

#[test]
fn core015_allows_profile_technical_abbreviations_in_symbol_names() {
    for name in [
        "RuleMeta",
        "evaluate_cfg_complexity_policy",
        "PyInit_sequential",
    ] {
        let store = store_with_core014_function(Language::Rust, name, None, vec![]);
        let issues = evaluate(&store, &profile());

        assert!(
            !issues.iter().any(|issue| issue.rule == "Core015"),
            "{name} must be allowed by profile term policy"
        );
    }
}

#[test]
fn core015_still_blocks_unapproved_abbreviations() {
    let store = store_with_core014_function(Language::Rust, "ctx_builder", None, vec![]);
    let issues = evaluate(&store, &profile());

    assert!(
        issues.iter().any(|issue| issue.rule == "Core015"),
        "ctx is still banned unless profile explicitly allows it"
    );
}

#[test]
fn core016_ignores_docstring_and_triple_string_text() {
    let store = store_from_source(
        "fixture.py",
        r#"
def collect_items():
    """
    Returns:
        should_stop: bool
        返回True代表成功
    """
    return True

flag: bool = """enabled"""

probe = """
should_skip: bool = True
class Fake:
    pass
"""
"#,
    );

    let issues = evaluate_all(&store, &profile());
    let flag_symbol = store
        .symbols
        .iter()
        .find(|symbol| symbol.name == "flag" && symbol.type_text.as_deref() == Some("bool"))
        .expect("real bool annotation before triple string must be extracted");
    let ignored_symbol_ids = store
        .symbols
        .iter()
        .filter(|symbol| matches!(symbol.name.as_str(), "should_stop" | "should_skip"))
        .map(|symbol| symbol.id.as_str())
        .collect::<Vec<_>>();

    assert!(
        ignored_symbol_ids.is_empty(),
        "docstring and data strings must not create bool symbols: {ignored_symbol_ids:?}"
    );
    assert!(
        !issues.iter().any(|issue| {
            issue.rule == "Core016"
                && issue
                    .evidence
                    .iter()
                    .any(|evidence| ignored_symbol_ids.contains(&evidence.as_str()))
        }),
        "docstring and data strings must not create Core016 symbol findings"
    );
    assert!(
        issues.iter().any(|issue| {
            issue.rule == "Core016"
                && issue
                    .evidence
                    .iter()
                    .any(|evidence| evidence == &flag_symbol.id)
                && issue.range.as_deref() == Some(flag_symbol.range.as_str())
        }),
        "real bool annotation before a triple string must still trigger Core016"
    );
}

#[test]
fn core016_does_not_merge_triple_string_prefix_with_bool_suffix() {
    let store = store_from_source(
        "fixture.py",
        r#"
def collect() -> None:
    payload = """x"""; is_ready: bool = False
    other = """
    text
    """; has_value: bool = False
"#,
    );

    let issues = evaluate_all(&store, &profile());
    let merged_prefix_bool_ids = store
        .symbols
        .iter()
        .filter(|symbol| {
            matches!(symbol.name.as_str(), "payload" | "other")
                && symbol.type_text.as_deref() == Some("bool")
        })
        .map(|symbol| symbol.id.as_str())
        .collect::<Vec<_>>();

    assert!(
        !issues.iter().any(|issue| {
            issue.rule == "Core016"
                && issue
                    .evidence
                    .iter()
                    .any(|evidence| merged_prefix_bool_ids.contains(&evidence.as_str()))
        }),
        "triple-string prefix assignments must not receive Core016 from suffix bool annotations"
    );
    assert!(
        merged_prefix_bool_ids.is_empty(),
        "triple-string prefix assignments must not become bool symbols: {merged_prefix_bool_ids:?}"
    );
    assert!(
        store
            .symbols
            .iter()
            .any(|symbol| symbol.name == "is_ready" && symbol.type_text.as_deref() == Some("bool")),
        "same-line suffix bool annotation must still be extracted"
    );
    assert!(
        store.symbols.iter().any(|symbol| {
            symbol.name == "has_value" && symbol.type_text.as_deref() == Some("bool")
        }),
        "multi-line closer suffix bool annotation must still be extracted"
    );
}
