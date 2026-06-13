use unifier::core::issue::{Domain, Issue, IssueKind, Language, Scope};

#[test]
fn hard_violation_blocks_and_under_review_does_not() {
    let hard = Issue::new(
        "issue:Core019:000001",
        IssueKind::HardViolation,
        "Core019",
        "layout.line_length",
        Scope::Line,
        Domain::Style,
    );
    let review = Issue::new(
        "issue:Core027:000001",
        IssueKind::UnderReview,
        "Core027",
        "text.natural_language.review",
        Scope::Text,
        Domain::Style,
    );

    assert!(hard.blocks);
    assert!(!review.blocks);
}

#[test]
fn serializes_minimal_issue_schema() {
    let issue = Issue::new(
        "issue:Core027:000001",
        IssueKind::UnderReview,
        "Core027",
        "text.natural_language.review",
        Scope::Text,
        Domain::Style,
    )
    .with_location(Language::Python, "src/example.py", "12:5-12:28")
    .with_message("内部文本疑似使用英文，需要审查是否应改为中文")
    .with_evidence("ev:file:0001:text:0003");

    let json = serde_json::to_value(issue).unwrap();

    assert_eq!(json["kind"], "under_review");
    assert_eq!(json["blocks"], false);
    assert_eq!(json["language"], "python");
    assert_eq!(json["evidence"][0], "ev:file:0001:text:0003");
}

#[test]
fn deserialization_derives_blocks_from_kind() {
    let issue: Issue = serde_json::from_value(serde_json::json!({
        "id": "issue:Core027:000001",
        "kind": "under_review",
        "rule": "Core027",
        "name": "text.natural_language.review",
        "scope": "text",
        "domain": "style",
        "language": null,
        "path": null,
        "range": null,
        "message": "",
        "evidence": [],
        "blocks": true
    }))
    .unwrap();

    assert_eq!(issue.kind, IssueKind::UnderReview);
    assert!(!issue.blocks);
}
