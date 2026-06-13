use std::fs;

use assert_cmd::Command;
use predicates::prelude::predicate;
use tempfile::tempdir;

#[test]
fn check_reports_python_core_and_python_specific_rules() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("module.py"),
        "\"\"\"模块文档\"\"\"\n\
from typing import List\n\
\n\
def run(value) -> List[str]:\n\
    \"\"\"Return run value.\"\"\"\n\
    return []\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.arg("check")
        .arg(dir.path())
        .arg("--no-history")
        .assert()
        .failure()
        .stdout(predicate::str::contains("\"rule\":\"Py001\""))
        .stdout(predicate::str::contains("\"rule\":\"Py005\""))
        .stdout(predicate::str::contains("\"rule\":\"Py007\""));
}

#[test]
fn check_reports_rust_and_cpp_rules() {
    let dir = tempdir().unwrap();
    fs::write(
        dir.path().join("lib.rs"),
        "#![feature(test)]\npub use crate::*;\nunsafe fn raw() {}\n",
    )
    .unwrap();
    fs::write(
        dir.path().join("api.hpp"),
        "#include <vector>\nusing namespace std;\nextern \"C\" int run(int* value);\n",
    )
    .unwrap();

    let mut cmd = Command::cargo_bin("csu").unwrap();
    cmd.arg("check")
        .arg(dir.path())
        .arg("--no-history")
        .assert()
        .failure()
        .stdout(predicate::str::contains("\"rule\":\"Rust001\""))
        .stdout(predicate::str::contains("\"rule\":\"Cpp003\""))
        .stdout(predicate::str::contains("\"rule\":\"Cpp004\""));
}
