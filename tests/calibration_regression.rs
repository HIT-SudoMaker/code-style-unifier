use std::collections::BTreeSet;

use unifier::core::calibration::{
    read_calibration_cases_jsonl, read_issues_json, validate_cases_against_issues,
    CalibrationAction, CalibrationCase, CalibrationLabel, BANNED_COUNT_RATIONALES,
};

const CASES_JSONL: &str = include_str!("fixtures/calibration/cases.jsonl");
const RELEASE_READINESS_CASES_JSONL: &str =
    include_str!("fixtures/release_readiness/self_check_cases.jsonl");
const RELEASE_READINESS_SAMPLE_ISSUES_JSON: &str =
    include_str!("fixtures/release_readiness/self_check_sample_issues.json");

fn release_readiness_sample_issues_array() -> String {
    let value: serde_json::Value = serde_json::from_str(RELEASE_READINESS_SAMPLE_ISSUES_JSON)
        .expect("release readiness sample issues must be valid JSON");
    serde_json::to_string(
        value
            .get("issues")
            .expect("release readiness sample issues must contain issues array"),
    )
    .expect("release readiness sample issues array must serialize")
}

#[test]
fn every_actionable_case_has_regression_intent() {
    let cases = read_calibration_cases_jsonl(CASES_JSONL).unwrap();
    let required_terms = ["事实", "规则", "级别", "边界"];

    for case in cases.iter().filter(|case| {
        matches!(
            case.action,
            CalibrationAction::FixFactExtraction
                | CalibrationAction::NarrowRuleContract
                | CalibrationAction::BroadenRuleContract
                | CalibrationAction::ChangeIssueKind
        )
    }) {
        assert!(
            required_terms
                .iter()
                .any(|term| case.rationale.contains(term)),
            "case {} rationale must contain at least one regression intent term: {:?}",
            case.case_id,
            required_terms
        );
    }
}

#[test]
fn calibration_labels_cover_positive_negative_and_kind_review() {
    let cases = read_calibration_cases_jsonl(CASES_JSONL).unwrap();
    let labels = cases.iter().map(|case| case.label).collect::<BTreeSet<_>>();

    for label in [
        CalibrationLabel::TruePositive,
        CalibrationLabel::FalsePositive,
        CalibrationLabel::FalseNegative,
        CalibrationLabel::ExternalStyleMismatch,
    ] {
        assert!(
            labels.contains(&label),
            "calibration fixture labels must include {label:?}"
        );
    }
}

#[test]
fn count_only_rationale_is_rejected_even_when_long_and_evidenced() {
    let mut case = CalibrationCase::valid_for_test(
        "case:count:001",
        "Core011",
        CalibrationLabel::FalsePositive,
        CalibrationAction::FixFactExtraction,
    );
    case.rationale =
        "reduce the count because there are too many findings in the report output".to_string();
    case.evidence = vec!["public:ev:file:abc:symbol:function:14:1:callback".to_string()];

    let err = case.validate().unwrap_err();

    assert_eq!(err, "rationale must not optimize for findings count");
}

#[test]
fn factual_rule_boundary_rationale_is_valid_for_py005_false_positive() {
    let mut case = CalibrationCase::valid_for_test(
        "case:Py005:triple-quoted-data:001",
        "Py005",
        CalibrationLabel::FalsePositive,
        CalibrationAction::FixFactExtraction,
    );
    case.rationale = concat!(
        "fact and rule boundary mismatch: triple quoted data was classified as code, ",
        "so the rule input boundary is wrong for annotation completeness",
    )
    .to_string();
    case.evidence = vec!["ev:file:abc:string_literal:triple_quoted_data:7:5".to_string()];

    assert!(case.validate().is_ok());
}

#[test]
fn release_readiness_cases_validate_and_cover_dispositions() {
    let cases = read_calibration_cases_jsonl(RELEASE_READINESS_CASES_JSONL).unwrap();
    let issues = read_issues_json(&release_readiness_sample_issues_array()).unwrap();
    validate_cases_against_issues(&cases, &issues).unwrap();

    assert!(
        cases.len() >= 3,
        "release readiness cases must cover profile policy, rule narrowing, and code cleanup"
    );

    let actions = cases
        .iter()
        .map(|case| case.action)
        .collect::<BTreeSet<_>>();

    for action in [
        CalibrationAction::AddProfilePolicy,
        CalibrationAction::NarrowRuleContract,
        CalibrationAction::KeepRule,
    ] {
        assert!(
            actions.contains(&action),
            "missing release readiness action {action:?}"
        );
    }
}

#[test]
fn release_readiness_cases_are_not_count_driven() {
    let cases = read_calibration_cases_jsonl(RELEASE_READINESS_CASES_JSONL).unwrap();

    for case in cases {
        let ascii_lower = case.rationale.to_ascii_lowercase();
        for banned in BANNED_COUNT_RATIONALES {
            let contains_banned = if banned.is_ascii() {
                ascii_lower.contains(&banned.to_ascii_lowercase())
            } else {
                case.rationale.contains(banned)
            };

            assert!(
                !contains_banned,
                "{} must not use count-driven rationale phrase {:?}",
                case.case_id, banned
            );
        }
    }
}
