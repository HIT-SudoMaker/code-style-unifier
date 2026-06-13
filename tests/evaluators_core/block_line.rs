use crate::support::{profile, store_from_source};
use unifier::core::evaluators::core::evaluate;
use unifier::core::evaluators::evaluate_all;
use unifier::core::evidence::{EvidenceStore, FileUnitFact, LineSpanFact, TextRole, TextSpanFact};
use unifier::core::issue::Language;

#[test]
fn core017_accepts_adjacent_safety_comment_for_unsafe_block() {
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
        !issues.iter().any(|issue| issue.rule == "Core017"),
        "Core017 must use the same block intent evidence as Rust007"
    );
}

#[test]
fn core017_rejects_non_leading_or_non_adjacent_safety_comments() {
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
            issues.iter().any(|issue| issue.rule == "Core017"),
            "{name} comment must not suppress Core017"
        );
    }
}

#[test]
fn core_suppression_requires_non_empty_reason() {
    let mut store = EvidenceStore::empty_for_tests();
    store.file_units.push(FileUnitFact {
        id: "file:py".to_string(),
        path: "api.py".to_string(),
        language: Language::Python,
        generated: false,
        excluded: false,
        fingerprint: "hash:py".to_string(),
    });
    store.line_spans.push(LineSpanFact {
        id: "line:suppression".to_string(),
        file_id: "file:py".to_string(),
        line: 8,
        visual_width: 20,
        line_hash: "hash:line".to_string(),
        suppression: Some("csu: ignore reason=   ".to_string()),
    });
    store.text_spans.push(TextSpanFact {
        id: "text:suppression".to_string(),
        file_id: "file:py".to_string(),
        range: "8:1-8:23".to_string(),
        role: TextRole::Comment,
        normalized_text: "csu: ignore reason=   ".to_string(),
        text_hash: "hash:suppression-text".to_string(),
        terminal_punctuation: Some(' '),
    });

    let issues = evaluate(&store, &profile());

    assert!(issues.iter().any(|issue| issue.rule == "Core018"));
}

#[test]
fn core018_ignores_suppression_markers_inside_strings() {
    let cases = [
        (
            r#"
pub fn render() -> &'static str {
    "suppression text mentions csu:allow but is not a comment"
}
"#,
            "Core018 must not trigger from string literal contents",
        ),
        (
            r##"
pub fn render() -> &'static str {
    r#"
/* csu:allow */
"#
}
"##,
            "raw string block-comment marker must not become comment evidence",
        ),
        (
            r#"
pub fn render() -> &'static str {
    "text with escaped quote \"
/* csu:allow */
"
}
"#,
            "multiline string block-comment marker must not become comment evidence",
        ),
        (
            r#"
pub fn render() -> &'static str {
    let text: &'static str = "
/* csu:allow */
";
    text
}
"#,
            "multiline string after lifetime must not create comment evidence",
        ),
    ];

    for (source, message) in cases {
        let store = store_from_source("lib.rs", source);
        let issues = evaluate(&store, &profile());

        assert!(
            !store.text_spans.iter().any(|text| {
                text.role == TextRole::Comment && text.normalized_text.contains("csu:allow")
            }),
            "{message}"
        );
        assert!(
            !issues.iter().any(|issue| issue.rule == "Core018"),
            "{message}"
        );
    }
}

#[test]
fn core018_reports_block_comment_after_quote_character_literal() {
    let store = store_from_source(
        "lib.rs",
        r#"
pub fn render() -> char {
    let quote = '"';
/* csu:allow */
    quote
}
"#,
    );

    let issues = evaluate(&store, &profile());

    assert!(
        store.text_spans.iter().any(|text| {
            text.role == TextRole::Comment && text.normalized_text.contains("csu:allow")
        }),
        "real block comment after quote character literal must become comment evidence"
    );
    assert!(
        issues.iter().any(|issue| issue.rule == "Core018"),
        "Core018 must report real block comment suppression without reason"
    );
}

#[test]
fn core018_reports_comment_suppression_without_reason() {
    // 拆开抑制标记，避免自检把夹具源码当成真实抑制注释
    let cases = [
        (
            concat!(
                "\n",
                "// csu:",
                "allow\n",
                "pub fn render() -> &'static str {\n",
                "    \"ok\"\n",
                "}\n",
            ),
            "Core018 must still trigger on line comment suppression without reason",
        ),
        (
            concat!(
                "\n",
                "/* csu:",
                "allow */\n",
                "pub fn render() -> &'static str { \"ok\" }\n",
            ),
            "Core018 must trigger on block comment suppression without reason",
        ),
    ];

    for (source, message) in cases {
        let store = store_from_source("lib.rs", source);
        let issues = evaluate(&store, &profile());

        assert!(
            issues.iter().any(|issue| issue.rule == "Core018"),
            "{message}"
        );
    }
}

#[test]
fn core018_allows_comment_suppression_with_reason() {
    let store = store_from_source(
        "lib.rs",
        r#"
// csu:allow reason = "generated fixture keeps external spelling"
pub fn render() -> &'static str {
    "ok"
}
"#,
    );

    let issues = evaluate(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Core018"),
        "Core018 must accept comment suppression with non-empty reason"
    );
}

#[test]
fn core019_history_serialization_lines_stay_within_default_width() {
    let store = store_from_source("history.rs", include_str!("../../src/core/history.rs"));

    let issues = evaluate(&store, &profile());

    assert!(
        !issues.iter().any(|issue| issue.rule == "Core019"),
        "history serialization source must stay within configured line width"
    );
}
