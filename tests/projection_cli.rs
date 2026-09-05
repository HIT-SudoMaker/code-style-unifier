use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::ReviewTerminal;
use csu::WorkspaceReviewer;
use csu::project_human;
use csu::project_javascript_object_notation;
use serde_json::Value;
use std::fs;
use std::process::Command;

mod review_fixture;

use review_fixture::review_sources;

const AUTHORITY: &str = include_str!("../docs/fixtures/core/authority.json");

const SOURCE: &str = concat!(
    "def _calculate_velocity(distance_m: float, ",
    r#"duration_s: float) -> float:
    """
    计算平均速度
    """
    return distance_m / duration_s
"#,
);

const EVIDENCE_PYTHON: &str = concat!(
    "def _calculate_velocity() -> float:\n",
    "    \"\"\"\n    计算平均速度\n    \"\"\"\n",
    "    Q = 1.0\n    return Q\n",
);

const EVIDENCE_PROCEDURAL_SOURCE: &str = concat!(
    "/**\n * 计算平均速度\n */\n",
    "double calculate_velocity(double distance_m);\n",
    "double calculate_distance(double distance_m);\n",
);

/// 根据测试 Authority 创建审查器
fn reviewer() -> WorkspaceReviewer {
    WorkspaceReviewer::compile(AuthorityInput::Documents(&[
        AuthorityDocument {
            relative_path: "authority.json",
            bytes: AUTHORITY.as_bytes(),
        },
    ]))
    .unwrap()
}

/// 构造已封存的审查结果
fn sealed_terminal() -> ReviewTerminal {
    review_sources(&reviewer(), "projection", &[("src/velocity.py", SOURCE)])
}

/// 构造带有规则问题和事实缺口的审查结果
fn evidence_terminal() -> ReviewTerminal {
    review_sources(
        &reviewer(),
        "evidence-projection",
        &[
            ("src/candidate.py", EVIDENCE_PYTHON),
            ("src/unowned.c", EVIDENCE_PROCEDURAL_SOURCE),
        ],
    )
}

/// 验证文本与 JSON 展示不改变审查终态
#[test]
fn human_and_json_are_read_only_terminal_projections() {
    let terminal = sealed_terminal();
    let human = project_human(&terminal);
    assert!(human.contains("Terminal: Sealed"));
    assert!(human.contains("Completion: Complete"));

    let structured_output: Value = serde_json::from_slice(
        &project_javascript_object_notation(&terminal).unwrap(),
    )
    .unwrap();
    assert_eq!(structured_output["schema_version"], 4);
    assert_eq!(structured_output["disposition"], "clean");
    assert_eq!(
        structured_output["review"]["finding_summary"],
        serde_json::json!({
            "total": 0, "hard_violation": 0, "review_required": 0
        })
    );
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("fixture must seal");
    };
    assert_eq!(structured_output["review"]["seal"], review.seal());
    let rejected =
        reviewer().review(csu::ReviewInput::Documents(csu::DocumentSet {
            revision: "",
            documents: &[],
        }));
    let rejected: Value = serde_json::from_slice(
        &project_javascript_object_notation(&rejected).unwrap(),
    )
    .unwrap();
    assert_eq!(rejected["schema_version"], 4);
    assert_eq!(rejected["terminal"], "rejected");
    let failure: csu::ReviewFailure = serde_json::from_value(
        serde_json::json!({"code": "runtime.test", "message": "failure"}),
    )
    .unwrap();
    let failed = ReviewTerminal::Failed(failure);
    let failed: Value = serde_json::from_slice(
        &project_javascript_object_notation(&failed).unwrap(),
    )
    .unwrap();
    assert_eq!(failed["schema_version"], 4);
    assert_eq!(failed["terminal"], "failed");
    assert_eq!(
        structured_output["review"]["findings"],
        serde_json::json!([])
    );
    assert_eq!(
        structured_output["review"]["blocked_family_details"],
        serde_json::json!([])
    );
}

/// 验证证据展示完整、稳定且不改变封存结果
#[test]
fn sealed_evidence_projection_is_complete_stable_and_read_only() {
    let terminal = evidence_terminal();
    let ReviewTerminal::Sealed(review) = &terminal else {
        panic!("evidence fixture must seal");
    };
    let before = review.canonical_bytes();
    let metrics = review.metrics();

    let first_json = project_javascript_object_notation(&terminal).unwrap();
    let second_json = project_javascript_object_notation(&terminal).unwrap();
    let first_human = project_human(&terminal);
    let second_human = project_human(&terminal);
    assert_eq!(first_json, second_json);
    assert_eq!(first_human, second_human);
    assert_eq!(review.canonical_bytes(), before);
    assert_eq!(review.metrics(), metrics);

    let structured_output: Value =
        serde_json::from_slice(&first_json).unwrap();
    let findings = structured_output["review"]["findings"].as_array().unwrap();
    let candidate = findings
        .iter()
        .find(|finding| finding["subject"] == "Q")
        .expect("candidate finding must be projected");
    assert_eq!(candidate["path"], "src/candidate.py");
    assert_eq!(candidate["rule"], "identifier.candidate");
    assert_eq!(candidate["grade"], "review_required");
    assert!(candidate["line"].as_u64().is_some());
    assert!(candidate["column"].as_u64().is_some());
    assert!(candidate["observation"].as_str().is_some());
    assert!(candidate["question"].as_str().is_some());
    assert!(candidate["message"].as_str().is_some());

    let blocked = structured_output["review"]["blocked_family_details"]
        .as_array()
        .unwrap();
    let documentation_block = blocked
        .iter()
        .find(|detail| {
            detail["file"] == "src/unowned.c"
                && detail["family"] == "documentation"
        })
        .expect("unresolved callable evidence must be projected");
    assert_eq!(
        documentation_block["reason"],
        concat!(
            "unresolved callable documentation facts: ",
            "calculate_distance@5:1[tier]; ",
            "calculate_velocity@4:1[tier]",
        )
    );
    assert_eq!(
        structured_output["review"]["finding_summary"]["total"],
        findings.len()
    );
    let summary = &structured_output["review"]["finding_summary"];
    assert_eq!(
        summary["total"],
        summary["hard_violation"].as_u64().unwrap()
            + summary["review_required"].as_u64().unwrap()
    );
    assert_eq!(
        structured_output["review"]["blocked_families"],
        blocked.len()
    );

    assert!(
        first_human.contains("src/candidate.py:5:5 identifier.candidate (Q)")
    );
    assert!(first_human.contains("Observation:"));
    assert!(first_human.contains("Question:"));
    assert!(first_human.contains(concat!(
        "src/unowned.c Documentation: unresolved callable ",
        "documentation facts: calculate_distance@5:1[tier]; ",
        "calculate_velocity@4:1[tier]",
    )));
}

/// 验证命令行遵循参数约定并为干净结果返回零
#[test]
fn cli_uses_frozen_review_command_and_clean_exit_code() {
    let temporary = tempfile::tempdir().unwrap();
    let authority = temporary.path().join("authority");
    let workspace = temporary.path().join("workspace");
    fs::create_dir_all(&authority).unwrap();
    fs::create_dir_all(workspace.join("src")).unwrap();
    fs::write(authority.join("authority.json"), AUTHORITY).unwrap();
    fs::write(workspace.join("src/velocity.py"), SOURCE).unwrap();

    let output = Command::new(env!("CARGO_BIN_EXE_csu"))
        .args([
            "review",
            "--authority",
            authority.to_str().unwrap(),
            "--workspace",
            workspace.to_str().unwrap(),
            "--format",
            "json",
        ])
        .output()
        .unwrap();
    assert_eq!(
        output.status.code(),
        Some(0),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let structured_output: Value =
        serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(structured_output["disposition"], "clean");
}

/// 验证命令行输出带定位信息的封存证据
#[test]
fn cli_projects_actionable_sealed_evidence() {
    let temporary = tempfile::tempdir().unwrap();
    let authority = temporary.path().join("authority");
    let workspace = temporary.path().join("workspace");
    fs::create_dir_all(&authority).unwrap();
    fs::create_dir_all(workspace.join("src")).unwrap();
    fs::write(authority.join("authority.json"), AUTHORITY).unwrap();
    fs::write(workspace.join("src/candidate.py"), EVIDENCE_PYTHON).unwrap();
    fs::write(workspace.join("src/unowned.c"), EVIDENCE_PROCEDURAL_SOURCE)
        .unwrap();

    let json_output = Command::new(env!("CARGO_BIN_EXE_csu"))
        .args([
            "review",
            "--authority",
            authority.to_str().unwrap(),
            "--workspace",
            workspace.to_str().unwrap(),
            "--format",
            "json",
        ])
        .output()
        .unwrap();
    assert_eq!(json_output.status.code(), Some(2));
    let structured_output: Value =
        serde_json::from_slice(&json_output.stdout).unwrap();
    assert!(
        structured_output["review"]["findings"]
            .as_array()
            .is_some_and(|findings| !findings.is_empty())
    );
    assert!(
        structured_output["review"]["blocked_family_details"]
            .as_array()
            .is_some_and(|blocked| !blocked.is_empty())
    );

    let human_output = Command::new(env!("CARGO_BIN_EXE_csu"))
        .args([
            "review",
            "--authority",
            authority.to_str().unwrap(),
            "--workspace",
            workspace.to_str().unwrap(),
            "--format",
            "human",
        ])
        .output()
        .unwrap();
    assert_eq!(human_output.status.code(), Some(2));
    let human = String::from_utf8(human_output.stdout).unwrap();
    assert!(human.contains("src/candidate.py:5:5"));
    assert!(human.contains("src/unowned.c Documentation:"));
}
