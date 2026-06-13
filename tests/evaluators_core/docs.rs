use crate::support::{profile, store_from_source};
use unifier::core::evaluators::core::evaluate;
use unifier::core::evaluators::evaluate_all;
use unifier::core::evidence::{
    BlockRegionFact, DocRegionFact, EvidenceStore, ExpressionFact, ExpressionKind, FileUnitFact,
    LineSpanFact, PublicSurfaceFact, SymbolFact, SymbolKind, SymbolVisibility, TextRole,
    TextSpanFact,
};
use unifier::core::issue::Language;

fn fixture_store_with_doc_text(text: &str) -> EvidenceStore {
    let mut store = EvidenceStore::empty_for_tests();
    store.file_units.push(FileUnitFact {
        id: "file:test".to_string(),
        path: "test.py".to_string(),
        language: Language::Python,
        generated: false,
        excluded: false,
        fingerprint: "hash:test-file".to_string(),
    });
    store.doc_regions.push(DocRegionFact {
        id: "doc:test".to_string(),
        file_id: "file:test".to_string(),
        symbol_name: "run".to_string(),
        range: "1:1-1:1".to_string(),
        summary_text_id: "text:test:doc".to_string(),
        full_text_id: None,
    });
    store.text_spans.push(TextSpanFact::for_test(
        "text:test:doc",
        TextRole::DocSummary,
        text,
    ));
    store
}

fn fixture_store_with_doc_full_text(text: &str) -> EvidenceStore {
    let mut store = fixture_store_with_doc_text("执行任务");
    store.doc_regions[0].full_text_id = Some("text:test:doc:full".to_string());
    store.text_spans.push(TextSpanFact::for_test(
        "text:test:doc:full",
        TextRole::Other,
        text,
    ));
    store
}

#[test]
fn remaining_core_rules_emit_expected_findings() {
    let mut store = EvidenceStore::empty_for_tests();
    store.file_units.push(FileUnitFact {
        id: "file:py".to_string(),
        path: "api.py".to_string(),
        language: Language::Python,
        generated: false,
        excluded: false,
        fingerprint: "hash:py".to_string(),
    });
    store.public_surfaces.push(PublicSurfaceFact {
        id: "public:missing_doc".to_string(),
        symbol_name: "run".to_string(),
        visibility: "public".to_string(),
        has_doc_region: false,
        file_id: "file:py".to_string(),
        range: "2:1-3:1".to_string(),
    });
    store.public_surfaces.push(PublicSurfaceFact {
        id: "public:internal_doc".to_string(),
        symbol_name: "_helper".to_string(),
        visibility: "internal".to_string(),
        has_doc_region: true,
        file_id: "file:py".to_string(),
        range: "5:1-6:1".to_string(),
    });
    store.doc_regions.push(DocRegionFact {
        id: "doc:run".to_string(),
        file_id: "file:py".to_string(),
        symbol_name: "run_with_value".to_string(),
        range: "1:1-8:1".to_string(),
        summary_text_id: "text:doc".to_string(),
        full_text_id: None,
    });
    store.doc_regions.push(DocRegionFact {
        id: "doc:layout".to_string(),
        file_id: "file:py".to_string(),
        symbol_name: "layout".to_string(),
        range: "40:1-48:1".to_string(),
        summary_text_id: "text:layout".to_string(),
        full_text_id: None,
    });
    store.text_spans.push(TextSpanFact::for_test(
        "text:doc",
        TextRole::DocSummary,
        "Returns:\n  value",
    ));
    store.text_spans.push(TextSpanFact::for_test(
        "text:layout",
        TextRole::DocSummary,
        "Returns:\n  value: output\n    other: output\nArgs:\n    value: input\n\n\nctx",
    ));
    store.text_spans.push(TextSpanFact::for_test(
        "text:term",
        TextRole::Comment,
        "ctx should be context",
    ));
    store.symbols.push(SymbolFact {
        id: "symbol:bad".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        name: "badName".to_string(),
        qualified_name: "api.badName".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Python,
        range: "10:1-11:1".to_string(),
        doc_region_id: Some("doc:run".to_string()),
        return_annotation: Some("bool".to_string()),
        missing_parameter_annotations: vec!["value".to_string()],
        type_text: Some("bool".to_string()),
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });
    store.symbols.push(SymbolFact {
        id: "symbol:ctx".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        name: "ctx".to_string(),
        qualified_name: "api.ctx".to_string(),
        kind: SymbolKind::Variable,
        visibility: SymbolVisibility::Private,
        language: Language::Python,
        range: "12:1-12:3".to_string(),
        doc_region_id: None,
        return_annotation: None,
        missing_parameter_annotations: Vec::new(),
        type_text: None,
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });
    store.symbols.push(SymbolFact {
        id: "symbol:bool_param".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        name: "should_stop".to_string(),
        qualified_name: "api.should_stop".to_string(),
        kind: SymbolKind::Parameter,
        visibility: SymbolVisibility::Private,
        language: Language::Python,
        range: "13:1-13:1".to_string(),
        doc_region_id: None,
        return_annotation: None,
        missing_parameter_annotations: Vec::new(),
        type_text: Some("bool".to_string()),
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });
    store.block_regions.push(BlockRegionFact {
        id: "block:complex".to_string(),
        file_id: "file:py".to_string(),
        range: "20:1-40:1".to_string(),
        kind: "complex".to_string(),
        intent_comment_id: None,
    });
    store.line_spans.push(LineSpanFact {
        id: "line:suppression".to_string(),
        file_id: "file:py".to_string(),
        line: 30,
        visual_width: 20,
        line_hash: "hash:line".to_string(),
        suppression: Some("csu: ignore".to_string()),
    });
    store.text_spans.push(TextSpanFact {
        id: "text:suppression".to_string(),
        file_id: "file:py".to_string(),
        range: "30:1-30:14".to_string(),
        role: TextRole::Comment,
        normalized_text: "csu: ignore".to_string(),
        text_hash: "hash:suppression-text".to_string(),
        terminal_punctuation: Some('e'),
    });
    store.line_spans.push(LineSpanFact {
        id: "line:long".to_string(),
        file_id: "file:py".to_string(),
        line: 31,
        visual_width: 121,
        line_hash: "hash:long".to_string(),
        suppression: None,
    });
    store.expressions.push(ExpressionFact {
        id: "expr:error".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        symbol_id: None,
        kind: ExpressionKind::ErrorMessage,
        range: "50:5-50:31".to_string(),
        text: "raise ValueError(\"failed\")".to_string(),
        callee: Some("ValueError".to_string()),
        arguments: vec!["\"failed\"".to_string()],
    });

    let issues = evaluate(&store, &profile());
    let rules = issues
        .iter()
        .map(|issue| issue.rule.as_str())
        .collect::<Vec<_>>();

    for expected in [
        "Core011", "Core012", "Core013", "Core014", "Core015", "Core016", "Core017", "Core018",
        "Core019", "Core020", "Core021", "Core022", "Core026", "Core028",
    ] {
        assert!(rules.contains(&expected), "missing {expected}");
    }
    assert!(issues
        .iter()
        .any(|issue| issue.rule == "Core016" && !issue.blocks));
    assert!(issues.iter().any(|issue| issue.rule == "Core016"
        && issue
            .evidence
            .iter()
            .any(|evidence| evidence == "symbol:bool_param")));
    assert!(issues
        .iter()
        .any(|issue| issue.rule == "Core028" && !issue.blocks));
}

#[test]
fn core011_does_not_report_multiline_python_property_with_docstring() {
    let store = store_from_source(
        "fixture.py",
        r#"
class Bundle:
    @property
    def control_area_layout_configuration(
        self,
    ) -> DemonstrationControlAreaLayoutConfigProtocol:
        """
        返回控制区布局配置
        """
        return self._layout
"#,
    );

    let issues = evaluate_all(&store, &profile());

    assert!(
        !issues.iter().any(|issue| {
            issue.rule == "Core011"
                && issue
                    .path
                    .as_deref()
                    .is_some_and(|path| path.ends_with("fixture.py"))
                && issue
                    .range
                    .as_deref()
                    .is_some_and(|range| range.starts_with("4:"))
        }),
        "documented multi-line property must not trigger Core011 on its declaration range"
    );
}

#[test]
fn public_rust_api_docs_must_be_chinese_and_without_terminal_period() {
    let store = store_from_source(
        "lib.rs",
        r#"
/// 对外扫描入口
pub fn scan() {}

/// Public scanner.
pub fn bad_english() {}

/// 对外扫描入口。
pub fn bad_period() {}
"#,
    );

    let issues = evaluate(&store, &profile());

    assert!(
        issues.iter().any(|issue| issue.rule == "Core027"),
        "English public docs should remain under review"
    );
    assert!(
        issues.iter().any(|issue| issue.rule == "Core023"),
        "Chinese terminal period should be hard violation"
    );
}

#[test]
fn core011_accepts_rust_docs_before_attributes() {
    let store = store_from_source(
        "lib.rs",
        r#"
/// 对外暴露的事实记录
#[derive(Clone)]
#[serde(rename_all = "snake_case")]
pub enum ApiFact {
    Value,
}
"#,
    );

    let issues = evaluate(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Core011"),
        "Rust docs before attributes must still document the following public item"
    );
}

#[test]
fn core011_accepts_indented_rust_docs_on_public_impl_methods() {
    let store = store_from_source(
        "lib.rs",
        r#"
/// 对外暴露的 profile 配置
pub struct ProfileConfig;

impl ProfileConfig {
    /// 从 TOML 文本读取 profile 配置
    pub fn from_toml_str(_input: &str) -> Self {
        Self
    }
}

/// 对外暴露的规则配置
pub struct RuleConfig;

impl RuleConfig {
    /// 从 TOML 文本读取规则配置
    pub fn from_toml_str(_input: &str) -> Self {
        Self
    }
}
"#,
    );

    let issues = evaluate(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Core011"),
        "indented Rust docs inside impl blocks must document public methods"
    );
}

#[test]
fn core_doc_rules_use_full_doc_text() {
    let mut store = EvidenceStore::empty_for_tests();
    store.file_units.push(FileUnitFact {
        id: "file:py".to_string(),
        path: "api.py".to_string(),
        language: Language::Python,
        generated: false,
        excluded: false,
        fingerprint: "hash:py".to_string(),
    });
    store.doc_regions.push(DocRegionFact {
        id: "doc:contract".to_string(),
        file_id: "file:py".to_string(),
        symbol_name: "run".to_string(),
        range: "2:5-8:8".to_string(),
        summary_text_id: "text:contract_summary".to_string(),
        full_text_id: Some("text:contract_full".to_string()),
    });
    store.text_spans.push(TextSpanFact::for_test(
        "text:contract_summary",
        TextRole::DocSummary,
        "执行任务",
    ));
    store.text_spans.push(TextSpanFact::for_test(
        "text:contract_full",
        TextRole::Other,
        "执行任务\n\nArgs:\n    value: 输入",
    ));
    store.symbols.push(SymbolFact {
        id: "symbol:run".to_string(),
        file_id: "file:py".to_string(),
        module_id: "module:py".to_string(),
        name: "run".to_string(),
        qualified_name: "api.run".to_string(),
        kind: SymbolKind::Function,
        visibility: SymbolVisibility::Public,
        language: Language::Python,
        range: "1:1-9:1".to_string(),
        doc_region_id: Some("doc:contract".to_string()),
        return_annotation: Some("int".to_string()),
        missing_parameter_annotations: vec!["value".to_string()],
        type_text: None,
        is_async: false,
        is_unsafe: false,
        attributes: Vec::new(),
    });

    let issues = evaluate(&store, &profile());

    assert!(!issues.iter().any(|issue| issue.rule == "Core012"));

    store.doc_regions.push(DocRegionFact {
        id: "doc:layout".to_string(),
        file_id: "file:py".to_string(),
        symbol_name: "layout".to_string(),
        range: "20:5-30:8".to_string(),
        summary_text_id: "text:layout_summary".to_string(),
        full_text_id: Some("text:layout_full".to_string()),
    });
    store.text_spans.push(TextSpanFact::for_test(
        "text:layout_summary",
        TextRole::DocSummary,
        "执行布局",
    ));
    store.text_spans.push(TextSpanFact::for_test(
        "text:layout_full",
        TextRole::Other,
        concat!(
            "执行布局\n\n",
            "Returns:\n  value: output\n    other: output\n",
            "Args:\n    value: input\n\n\nctx",
        ),
    ));

    let issues = evaluate(&store, &profile());
    let rules = issues
        .iter()
        .map(|issue| issue.rule.as_str())
        .collect::<Vec<_>>();

    for expected in ["Core020", "Core021", "Core022"] {
        assert!(rules.contains(&expected), "missing {expected}");
    }
}

#[test]
fn core021_checks_only_peer_fields_inside_recognized_sections() {
    let cases = [
        (
            r#"
执行任务

Attributes:
    first: 第一项
    second: 第二项

Returns:
    bool: 结果
"#,
            false,
            false,
            "Core021 must compare peer field rows, not prose against field blocks",
        ),
        (
            r#"
执行任务

Args:
    first: 第一项
    second: 第二项

Examples:
  sample: 示例内容
"#,
            false,
            false,
            "Core021 must not compare fields from unrecognized sections with prior Args fields",
        ),
        (
            r#"
    执行任务

    Args:
        first: 第一项
        second: 第二项

    Examples:
      sample: 示例内容
"#,
            true,
            false,
            "Core021 must reset section tracking for indented docstring section boundaries",
        ),
        (
            r#"
执行任务

Args:
    first: 第一项
  second: 第二项
"#,
            false,
            true,
            "misaligned fields inside the same section remain a real layout issue",
        ),
        (
            r#"
    执行任务

    Args:
        first: 第一项
      second: 第二项
"#,
            true,
            true,
            "misaligned fields inside the same indented section remain a real layout issue",
        ),
    ];

    for (text, full_text, expect_core021, message) in cases {
        let store = if full_text {
            fixture_store_with_doc_full_text(text)
        } else {
            fixture_store_with_doc_text(text)
        };
        let issues = evaluate(&store, &profile());
        let has_core021 = issues.iter().any(|issue| issue.rule == "Core021");

        assert_eq!(has_core021, expect_core021, "{message}");
    }
}
