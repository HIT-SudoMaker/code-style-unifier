use std::fs;
use std::path::Path;

use assert_cmd::Command;
use predicates::prelude::{predicate, PredicateBooleanExt};
use tempfile::tempdir;

#[test]
fn calibrate_writes_machine_readable_report() {
    let dir = tempdir().unwrap();
    let issues = dir.path().join("issues.json");
    let cases = dir.path().join("cases.jsonl");
    let report = dir.path().join("reports").join("calibration.json");

    copy_fixture("issues.json", &issues);
    copy_fixture("cases.jsonl", &cases);

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.arg("calibrate")
        .arg("--issues")
        .arg(&issues)
        .arg("--cases")
        .arg(&cases)
        .arg("--output")
        .arg(&report)
        .assert()
        .success()
        .stdout(predicate::str::is_empty());

    let contents = fs::read_to_string(report).unwrap();
    let report: serde_json::Value = serde_json::from_str(&contents).unwrap();
    assert_eq!(
        report["findings_count_is_optimization_goal"].as_bool(),
        Some(false)
    );
    assert!(report["actionable_case_ids"]
        .as_array()
        .unwrap()
        .iter()
        .any(|case_id| case_id.as_str() == Some("case:Core011:callback:001")));
}

#[test]
fn calibrate_rejects_count_only_cases() {
    let dir = tempdir().unwrap();
    let issues = dir.path().join("issues.json");
    let cases = dir.path().join("cases.jsonl");

    copy_fixture("issues.json", &issues);
    fs::write(&cases, format!("{}\n", core011_count_only_case())).unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.arg("calibrate")
        .arg("--issues")
        .arg(&issues)
        .arg("--cases")
        .arg(&cases)
        .assert()
        .failure()
        .code(2)
        .stderr(
            predicate::str::contains("rationale must not optimize for findings count")
                .and(predicate::str::contains("count-only calibration is not allowed").not()),
        );
}

#[test]
fn calibrate_rejects_cases_with_missing_issue_id() {
    let dir = tempdir().unwrap();
    let issues = dir.path().join("issues.json");
    let cases = dir.path().join("cases.jsonl");

    copy_fixture("issues.json", &issues);
    fs::write(&cases, format!("{}\n", core011_missing_issue_case())).unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.arg("calibrate")
        .arg("--issues")
        .arg(&issues)
        .arg("--cases")
        .arg(&cases)
        .assert()
        .failure()
        .code(2)
        .stderr(predicate::str::contains("references missing issue_id"));
}

fn copy_fixture(name: &str, target: &Path) {
    let source = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join("calibration")
        .join(name);
    fs::copy(source, target).unwrap();
}

fn core011_count_only_case() -> String {
    serde_json::json!({
        "case_id": "case:Core011:count:001",
        "rule": "Core011",
        "issue_id": "issue:Core011:public_callback",
        "label": "false_positive",
        "observed_kind": "hard_violation",
        "expected_kind": null,
        "path": "app/callbacks.py",
        "range": "14:1-14:1",
        "evidence": ["public:ev:file:abc:symbol:function:14:1:callback"],
        "rationale": "fact boundary says findings too many for this rule evidence",
        "action": "fix_fact_extraction",
    })
    .to_string()
}

fn core011_missing_issue_case() -> String {
    serde_json::json!({
        "case_id": "case:Core011:missing:001",
        "rule": "Core011",
        "issue_id": "issue:Core011:not_found",
        "label": "false_positive",
        "observed_kind": "hard_violation",
        "expected_kind": null,
        "path": "app/callbacks.py",
        "range": "14:1-14:1",
        "evidence": ["public:ev:file:abc:symbol:function:14:1:callback"],
        "rationale": "fact boundary and rule evidence support checking observed kind",
        "action": "fix_fact_extraction",
    })
    .to_string()
}
