use unifier::core::calibration::{
    CalibrationAction, CalibrationCase, CalibrationLabel, CalibrationReport,
};
use unifier::core::issue::IssueKind;

#[test]
fn calibration_enums_support_total_ordering() {
    let mut labels = [
        CalibrationLabel::FalseNegative,
        CalibrationLabel::TruePositive,
        CalibrationLabel::FalsePositive,
    ];
    labels.sort();
    assert_eq!(
        labels,
        [
            CalibrationLabel::TruePositive,
            CalibrationLabel::FalsePositive,
            CalibrationLabel::FalseNegative,
        ]
    );

    let mut actions = [
        CalibrationAction::NarrowRuleContract,
        CalibrationAction::KeepRule,
        CalibrationAction::FixFactExtraction,
    ];
    actions.sort();
    assert_eq!(
        actions,
        [
            CalibrationAction::KeepRule,
            CalibrationAction::FixFactExtraction,
            CalibrationAction::NarrowRuleContract,
        ]
    );
}

#[test]
fn calibration_case_requires_reasoned_judgment() {
    let case = CalibrationCase {
        case_id: "case:Core011:compound:001".to_string(),
        rule: "Core011".to_string(),
        issue_id: Some("issue:Core011:abc".to_string()),
        label: CalibrationLabel::FalsePositive,
        observed_kind: Some(IssueKind::HardViolation),
        expected_kind: None,
        path: Some("app/service.py".to_string()),
        range: Some("12:1-12:1".to_string()),
        evidence: vec!["public:ev:file:abc:symbol:function:12:1:def".to_string()],
        rationale: "事实层误把内部回调识别为公共 API，公共表面识别应收窄到模块导出边界".to_string(),
        action: CalibrationAction::FixFactExtraction,
    };

    assert!(case.validate().is_ok());
}

#[test]
fn calibration_case_rejects_count_only_reasoning() {
    let case = CalibrationCase {
        case_id: "case:Core019:bad:001".to_string(),
        rule: "Core019".to_string(),
        issue_id: Some("issue:Core019:abc".to_string()),
        label: CalibrationLabel::FalsePositive,
        observed_kind: Some(IssueKind::HardViolation),
        expected_kind: None,
        path: Some("app/service.py".to_string()),
        range: Some("12:1-12:1".to_string()),
        evidence: vec!["public:ev:file:abc:symbol:function:12:1:def".to_string()],
        rationale: "fact boundary says findings count is high".to_string(),
        action: CalibrationAction::NarrowRuleContract,
    };

    assert_eq!(
        case.validate().unwrap_err(),
        "rationale must not optimize for findings count"
    );
}

#[test]
fn calibration_case_rejects_count_only_synonyms() {
    let mut case = CalibrationCase::valid_for_test(
        "case:Core019:bad:002",
        "Core019",
        CalibrationLabel::FalsePositive,
        CalibrationAction::NarrowRuleContract,
    );
    case.rationale = "findings count is high".to_string();

    assert!(case.validate().is_err());
}

#[test]
fn calibration_case_requires_traceable_rationale_terms() {
    let mut case = CalibrationCase::valid_for_test(
        "case:Core019:bad:003",
        "Core019",
        CalibrationLabel::FalsePositive,
        CalibrationAction::NarrowRuleContract,
    );
    case.rationale = "这个判断看起来不合适，但说明只表达了主观感觉，没有给出可追踪依据".to_string();

    assert!(case.validate().is_err());
}

#[test]
fn false_negative_requires_expected_kind() {
    let mut case = CalibrationCase::valid_for_test(
        "case:Core027:missing:001",
        "Core027",
        CalibrationLabel::FalseNegative,
        CalibrationAction::BroadenRuleContract,
    );
    case.expected_kind = None;

    assert!(case.validate().is_err());
}

#[test]
fn false_negative_must_not_have_observed_kind() {
    let mut case = CalibrationCase::valid_for_test(
        "case:Core027:missing:003",
        "Core027",
        CalibrationLabel::FalseNegative,
        CalibrationAction::BroadenRuleContract,
    );
    case.observed_kind = Some(IssueKind::HardViolation);

    let err = case.validate().unwrap_err();

    assert!(err.contains("false_negative"));
    assert!(err.contains("observed_kind"));
}

#[test]
fn non_false_negative_requires_observed_kind() {
    let mut case = CalibrationCase::valid_for_test(
        "case:Core027:present:002",
        "Core027",
        CalibrationLabel::FalsePositive,
        CalibrationAction::NarrowRuleContract,
    );
    case.observed_kind = None;

    let err = case.validate().unwrap_err();

    assert!(err.contains("observed_kind"));
}

#[test]
fn evidence_entries_must_be_nonempty_after_trim() {
    let mut case = CalibrationCase::valid_for_test(
        "case:Core027:present:003",
        "Core027",
        CalibrationLabel::FalsePositive,
        CalibrationAction::NarrowRuleContract,
    );
    case.evidence = vec![
        "public:ev:file:abc:symbol:function:12:1:def".to_string(),
        " \t\n ".to_string(),
    ];

    let err = case.validate().unwrap_err();

    assert!(err.contains("evidence"));
    assert!(err.contains("empty"));
}

#[test]
fn non_false_negative_issue_id_must_be_nonempty() {
    let mut case = CalibrationCase::valid_for_test(
        "case:Core027:present:001",
        "Core027",
        CalibrationLabel::FalsePositive,
        CalibrationAction::NarrowRuleContract,
    );
    case.issue_id = Some(" \t\n ".to_string());

    assert_eq!(
        case.validate().unwrap_err(),
        "non-false_negative cases require nonempty issue_id"
    );
}

#[test]
fn false_negative_rejects_present_blank_issue_id() {
    let mut case = CalibrationCase::valid_for_test(
        "case:Core027:missing:002",
        "Core027",
        CalibrationLabel::FalseNegative,
        CalibrationAction::BroadenRuleContract,
    );
    case.issue_id = Some(" \t\n ".to_string());

    assert_eq!(
        case.validate().unwrap_err(),
        "false_negative must not have issue_id"
    );
}

#[test]
fn calibration_report_summarizes_by_rule_and_action() {
    let cases = vec![
        CalibrationCase::valid_for_test(
            "case:Core011:good:001",
            "Core011",
            CalibrationLabel::TruePositive,
            CalibrationAction::KeepRule,
        ),
        CalibrationCase::valid_for_test(
            "case:Core011:kind:001",
            "Core011",
            CalibrationLabel::WrongKind,
            CalibrationAction::ChangeIssueKind,
        ),
        CalibrationCase::valid_for_test(
            "case:Py005:missing:001",
            "Py005",
            CalibrationLabel::FalseNegative,
            CalibrationAction::BroadenRuleContract,
        ),
    ];

    let report = CalibrationReport::from_cases(&cases).unwrap();

    assert_eq!(report.case_count, 3);
    assert_eq!(report.by_rule["Core011"].case_count, 2);
    assert_eq!(
        report.by_rule["Core011"].action_counts["change_issue_kind"],
        1
    );
    assert_eq!(report.by_rule["Py005"].label_counts["false_negative"], 1);
    assert!(!report.findings_count_is_optimization_goal);
}
