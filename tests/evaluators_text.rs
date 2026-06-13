use unifier::core::evaluators::{
    appears_english, evaluate_summary_concision, evaluate_terminal_punctuation,
    evaluate_text_natural_language, needs_concision_review,
};
use unifier::core::evidence::{DocRegionFact, EvidenceStore, TextRole, TextSpanFact};
use unifier::core::issue::{Domain, IssueKind, Scope};
use unifier::core::profile::Profile;

#[test]
fn natural_language_review_matches_reference_heuristic() {
    assert!(appears_english("This comment needs review"));
    assert!(!appears_english("这里是中文注释"));
    assert!(!appears_english("SSIM 指标"));
}

#[test]
fn summary_concision_matches_reference_conditions() {
    assert!(needs_concision_review(
        "load_image",
        "Return load image result"
    ));
    assert!(needs_concision_review("run", "Handle request"));
    assert!(needs_concision_review("run", "创建并初始化内部状态"));
    assert!(needs_concision_review("run", &"a".repeat(81)));
    assert!(!needs_concision_review("run", "返回训练指标"));
}

#[test]
fn terminal_punctuation_only_checks_doc_summaries() {
    let mut store = EvidenceStore::empty_for_tests();
    store.text_spans.push(TextSpanFact::for_test(
        "text:1",
        TextRole::DocSummary,
        "返回结果。",
    ));
    store.text_spans.push(TextSpanFact::for_test(
        "text:2",
        TextRole::DocSummary,
        "Return result.",
    ));
    store.text_spans.push(TextSpanFact::for_test(
        "text:3",
        TextRole::Comment,
        "Comment with period.",
    ));

    let issues = evaluate_terminal_punctuation(&store);

    let chinese = issues
        .iter()
        .find(|issue| issue.rule == "Core023")
        .expect("Chinese period issue should exist");
    assert_eq!(chinese.kind, IssueKind::HardViolation);
    assert_eq!(chinese.scope, Scope::Text);
    assert_eq!(chinese.domain, Domain::Documentation);

    let english = issues
        .iter()
        .find(|issue| issue.rule == "Core024")
        .expect("English period issue should exist");
    assert_eq!(english.kind, IssueKind::UnderReview);
    assert_eq!(english.scope, Scope::Text);
    assert_eq!(english.domain, Domain::Documentation);
    assert!(!english.blocks);

    assert_eq!(issues.len(), 2);
}

#[test]
fn summary_concision_uses_doc_region_summary_text() {
    let mut store = EvidenceStore::empty_for_tests();
    store.text_spans.push(TextSpanFact::for_test(
        "text:summary",
        TextRole::DocSummary,
        "Return load image result",
    ));
    store.doc_regions.push(DocRegionFact {
        id: "doc:1".to_string(),
        file_id: "file:test".to_string(),
        symbol_name: "load_image".to_string(),
        range: "1:1-1:1".to_string(),
        summary_text_id: "text:summary".to_string(),
        full_text_id: None,
    });

    let issues = evaluate_summary_concision(&store);

    assert_eq!(issues.len(), 1);
    assert_eq!(issues[0].rule, "Core025");
    assert_eq!(issues[0].kind, IssueKind::UnderReview);
    assert_eq!(issues[0].scope, Scope::Text);
    assert_eq!(issues[0].domain, Domain::Documentation);
    assert!(!issues[0].blocks);
}

#[test]
fn core027_is_under_review_and_never_blocks() {
    let profile = Profile::from_toml_str(include_str!("../profiles/default.toml")).unwrap();
    let mut store = EvidenceStore::empty_for_tests();
    store.text_spans.push(TextSpanFact::for_test(
        "text:1",
        TextRole::Comment,
        "This comment needs review",
    ));
    store.text_spans.push(TextSpanFact::for_test(
        "text:2",
        TextRole::DocSummary,
        "This summary needs review",
    ));
    store.text_spans.push(TextSpanFact::for_test(
        "text:3",
        TextRole::Other,
        "This external text is ignored",
    ));

    let issues = evaluate_text_natural_language(&store, &profile);

    assert_eq!(issues.len(), 2);
    assert!(issues.iter().all(|issue| issue.rule == "Core027"));
    assert!(issues
        .iter()
        .all(|issue| issue.kind == IssueKind::UnderReview));
    assert!(issues.iter().all(|issue| issue.scope == Scope::Text));
    assert!(issues.iter().all(|issue| issue.domain == Domain::Style));
    assert!(issues.iter().all(|issue| !issue.blocks));
}
