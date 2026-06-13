use unifier::core::calibration::{
    read_calibration_cases_jsonl, read_issues_json, validate_cases_against_issues,
    CalibrationReport,
};
use unifier::core::issue::IssueKind;

const CASES_JSONL: &str = include_str!("fixtures/calibration/cases.jsonl");
const ISSUES_JSON: &str = include_str!("fixtures/calibration/issues.json");
const EXPECTED_REPORT_JSON: &str = include_str!("fixtures/calibration/expected_report.json");

#[test]
fn reads_jsonl_cases_and_generates_stable_report() {
    let cases = read_calibration_cases_jsonl(CASES_JSONL).unwrap();
    let report = CalibrationReport::from_cases(&cases).unwrap();
    let expected: serde_json::Value = serde_json::from_str(EXPECTED_REPORT_JSON).unwrap();

    assert_eq!(serde_json::to_value(report).unwrap(), expected);
}

#[test]
fn reads_issue_array_from_check_output() {
    let issues = read_issues_json(ISSUES_JSON).unwrap();

    assert_eq!(issues.len(), 4);
    assert_eq!(issues[0].rule, "Core011");
    assert_eq!(issues[1].rule, "Py005");
}

#[test]
fn validates_case_issue_ids_against_real_check_output() {
    let issues = read_issues_json(ISSUES_JSON).unwrap();
    let cases = read_calibration_cases_jsonl(CASES_JSONL).unwrap();

    validate_cases_against_issues(&cases, &issues).unwrap();
}

#[test]
fn rejects_case_with_missing_issue_id() {
    let issues = read_issues_json(ISSUES_JSON).unwrap();
    let mut cases = read_calibration_cases_jsonl(CASES_JSONL).unwrap();
    cases[0].issue_id = Some("issue:Core011:not_found".to_string());

    let err = validate_cases_against_issues(&cases, &issues).unwrap_err();

    assert!(err.contains("references missing issue_id"));
}

#[test]
fn rejects_case_with_mismatched_evidence() {
    let issues = read_issues_json(ISSUES_JSON).unwrap();
    let mut cases = read_calibration_cases_jsonl(CASES_JSONL).unwrap();
    cases[0].evidence = vec!["ev:file:wrong".to_string()];

    let err = validate_cases_against_issues(&cases, &issues).unwrap_err();

    assert!(err.contains("evidence does not match issue evidence"));
}

#[test]
fn rejects_case_with_mismatched_rule_or_kind() {
    let issues = read_issues_json(ISSUES_JSON).unwrap();
    let mut cases = read_calibration_cases_jsonl(CASES_JSONL).unwrap();
    cases[0].observed_kind = Some(IssueKind::UnderReview);

    let err = validate_cases_against_issues(&cases, &issues).unwrap_err();

    assert!(err.contains("observed_kind"));
}

#[test]
fn jsonl_errors_include_line_number() {
    let valid_first_line = CASES_JSONL.lines().next().unwrap();
    let input = format!("{valid_first_line}\n{{not json");

    let err = read_calibration_cases_jsonl(&input).unwrap_err();

    assert!(err.contains("line 2"));
}
