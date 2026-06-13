use std::fs;

use assert_cmd::Command;
use predicates::prelude::{predicate, PredicateBooleanExt};
use tempfile::tempdir;

#[test]
fn binary_prints_help() {
    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("Usage:"));
}

#[test]
fn check_returns_exit_one_for_hard_violation_and_json_output() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("module.py"),
        "def run():\n    \"\"\"返回结果。\"\"\"\n    return 1\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(dir.path())
        .arg("--no-history")
        .assert()
        .failure()
        .code(1)
        .stdout(predicate::str::contains("\"rule\":\"Core023\""));

    assert!(!dir.path().join(".csu/history/runs").exists());
}

#[test]
fn check_returns_exit_zero_for_under_review_only() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("module.py"),
        "def run() -> int:\n    \"\"\"Return result.\"\"\"\n    return 1\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(dir.path())
        .arg("--no-history")
        .assert()
        .success()
        .stdout(predicate::str::contains("\"kind\":\"under_review\""));
}

#[test]
fn check_writes_json_output_file_when_requested() {
    let dir = tempdir().unwrap();
    let output = dir.path().join("findings.json");
    fs::write(
        dir.path().join("module.py"),
        "def run() -> int:\n    \"\"\"Return result.\"\"\"\n    return 1\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(dir.path())
        .arg("--no-history")
        .arg("--output")
        .arg(&output)
        .assert()
        .success()
        .stdout(predicate::str::is_empty());

    let contents = fs::read_to_string(output).unwrap();
    assert!(contents.contains("\"rule\":\"Core024\""));
    assert!(contents.starts_with('['));
}

#[test]
fn check_writes_history_archive_without_source_text() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("target_project");
    fs::create_dir_all(&target).unwrap();
    fs::write(
        target.join("module.py"),
        "def run() -> int:\n\
    \"\"\"Return result.\"\"\"\n\
    # This comment needs review\n\
    return 1\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(&target)
        .assert()
        .success();

    let runs = dir.path().join(".csu/history/runs");
    let run_dirs: Vec<_> = fs::read_dir(&runs)
        .unwrap()
        .collect::<Result<_, _>>()
        .unwrap();
    assert_eq!(run_dirs.len(), 1);
    let run_dir = run_dirs[0].path();
    assert!(run_dir.join("run.json").exists());
    assert!(run_dir.join("summary.json").exists());
    assert!(run_dir.join("issues.jsonl").exists());
    assert!(run_dir.join("evidence_index.jsonl").exists());

    let evidence_index = fs::read_to_string(run_dir.join("evidence_index.jsonl")).unwrap();
    assert!(evidence_index.contains("\"type\":\"text_span\""));
    assert!(!evidence_index.contains("This comment needs review"));
}

#[test]
fn history_evidence_index_omits_raw_expression_text() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("module.py"),
        "import logging\n\
LOGGER = logging.getLogger(__name__)\n\
def run(value) -> Literal[\"secret\"]:\n\
    logger_for(\"secret\").error(f\"secret={value}\")\n",
    )
    .unwrap();
    fs::write(
        dir.path().join("lib.rs"),
        "pub use crate::{secret_module};\npub fn run() { panic!(\"secret\"); }\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    let _ = cmd
        .current_dir(dir.path())
        .arg("check")
        .arg(dir.path())
        .assert();

    let runs = dir.path().join(".csu/history/runs");
    let run_dirs: Vec<_> = fs::read_dir(&runs)
        .unwrap()
        .collect::<Result<_, _>>()
        .unwrap();
    assert_eq!(run_dirs.len(), 1);
    let evidence_index =
        fs::read_to_string(run_dirs[0].path().join("evidence_index.jsonl")).unwrap();

    assert!(evidence_index.contains("\"type\":\"expression\""));
    assert!(evidence_index.contains("\"text_hash\""));
    assert!(!evidence_index.contains("secret={value}"));
    assert!(!evidence_index.contains("logger_for"));
    assert!(!evidence_index.contains("Literal"));
    assert!(!evidence_index.contains("secret_module"));
    assert!(!evidence_index.contains("panic!"));
}

#[test]
fn check_no_history_does_not_evaluate_history_health() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("target_project");
    fs::create_dir_all(&target).unwrap();
    fs::write(
        target.join("module.py"),
        "def run() -> int:\n    \"\"\"返回结果\"\"\"\n    return 1\n",
    )
    .unwrap();
    let runs = dir.path().join(".csu/history/runs");
    fs::create_dir_all(&runs).unwrap();
    for index in 0..31 {
        let run = runs.join(format!("200001{:02}T000000Z", index + 1));
        fs::create_dir_all(&run).unwrap();
        fs::write(run.join("summary.json"), "{}").unwrap();
    }

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(&target)
        .arg("--no-history")
        .assert()
        .success()
        .stdout(predicate::str::contains("Core005").not());
}

#[test]
fn check_accepts_profile_path_outside_profiles_directory() {
    let dir = tempdir().unwrap();
    let profile = dir.path().join("project-profile.toml");
    fs::write(&profile, include_str!("../profiles/default.toml")).unwrap();
    fs::write(
        dir.path().join("module.py"),
        "def run() -> int:\n    \"\"\"Return result.\"\"\"\n    return 1\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(dir.path())
        .arg("--profile-path")
        .arg(&profile)
        .arg("--no-history")
        .assert()
        .success()
        .stdout(predicate::str::contains("\"kind\":\"under_review\""));
}

#[test]
fn check_writes_history_to_explicit_directory() {
    let dir = tempdir().unwrap();
    let history_dir = dir.path().join("history-out");
    fs::write(
        dir.path().join("module.py"),
        "def run() -> int:\n    \"\"\"Return result.\"\"\"\n    return 1\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(dir.path())
        .arg("--history-dir")
        .arg(&history_dir)
        .assert()
        .success();

    assert!(history_dir.join("runs").exists());
    assert!(!dir.path().join(".csu/history/runs").exists());
}

#[test]
fn check_reports_raw_python_error_message_boundary() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("module.py"),
        "def run() -> None:\n    \"\"\"返回结果\"\"\"\n    raise ValueError(\"failed\")\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(dir.path())
        .arg("--no-history")
        .assert()
        .success()
        .stdout(predicate::str::contains("\"rule\":\"Core028\""));
}

#[test]
fn check_reports_future_import_missing_blank_line() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("module.py"),
        "from __future__ import annotations\n\
import os\n\
\n\
def run() -> None:\n\
    \"\"\"返回结果\"\"\"\n\
    return None\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(dir.path())
        .arg("--no-history")
        .assert()
        .failure()
        .stdout(predicate::str::contains("\"rule\":\"Py002\""));
}

#[test]
fn check_python_logging_receiver_boundaries() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("module.py"),
        "def run(value: int) -> None:\n\
    \"\"\"返回结果\"\"\"\n\
    client.info(f\"skip={value}\")\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(dir.path())
        .arg("--no-history")
        .assert()
        .success()
        .stdout(predicate::str::contains("\"rule\":\"Py008\"").not());
}

#[test]
fn check_python_logging_critical_is_checked() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("module.py"),
        "def run(value: int) -> None:\n\
    \"\"\"返回结果\"\"\"\n\
    logger.critical(f\"value={value}\")\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.current_dir(dir.path())
        .arg("check")
        .arg(dir.path())
        .arg("--no-history")
        .assert()
        .failure()
        .stdout(predicate::str::contains("\"rule\":\"Py008\""));
}

#[test]
fn rules_command_prints_catalog() {
    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.arg("rules")
        .assert()
        .success()
        .stdout(predicate::str::contains("Core027"));
}
