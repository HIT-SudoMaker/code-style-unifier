use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::DocumentSet;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SourceDocument;
use csu::WorkspaceReviewer;
use csu::project_human;
use csu::project_javascript_object_notation;
use serde_json::Value;
use std::fs;
use std::process::Command;

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

const UNRESOLVED_RETURN_PYTHON: &str = r#"def calculate_velocity() -> Velocity:
    """
    计算平均速度

    Args:
        无
    Returns:
        Velocity: 平均速度
    Raises:
        无
    """
    return Velocity()
"#;

const UNRESOLVED_CARRIER_RUST: &str = r#"#[doc = include_str!("carrier.md")]
pub fn calculate_velocity() -> f64 { 1.0 }
"#;

const UNRESOLVED_PARAMETERS_PROCEDURAL_SOURCE: &str = r#"/**
 * 计算平均速度
 *
 * 参数：
 * - 无
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
double calculate_velocity(double);
"#;

const UNRESOLVED_TEMPLATE_CPP: &str = r#"/**
 * 计算平均速度
 *
 * 参数：
 * - input_value：输入数值
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
double calculate_velocity(auto input_value);
"#;

/// 验证终态投影证据场景
fn sealed_terminal() -> ReviewTerminal {
    let authority_documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: AUTHORITY.as_bytes(),
    }];
    let reviewer = WorkspaceReviewer::compile(AuthorityInput::Documents(
        &authority_documents,
    ))
    .unwrap();
    let sources = [SourceDocument {
        relative_path: "src/velocity.py",
        bytes: SOURCE.as_bytes(),
    }];
    reviewer.review(ReviewInput::Documents(DocumentSet {
        revision: "projection",
        documents: &sources,
    }))
}

/// 验证终态投影证据场景
fn evidence_terminal() -> ReviewTerminal {
    let mut authority: Value = serde_json::from_str(AUTHORITY).unwrap();
    authority["public_callables"]["api/parameters.h"] =
        serde_json::json!(["calculate_velocity"]);
    authority["public_callables"]["api/template.hpp"] =
        serde_json::json!(["calculate_velocity"]);
    authority["header_languages"]["api/parameters.h"] = serde_json::json!("c");
    let authority = serde_json::to_vec(&authority).unwrap();
    let authority_documents = [AuthorityDocument {
        relative_path: "authority.json",
        bytes: &authority,
    }];
    let reviewer = WorkspaceReviewer::compile(AuthorityInput::Documents(
        &authority_documents,
    ))
    .unwrap();
    let sources = [
        SourceDocument {
            relative_path: "src/candidate.py",
            bytes: EVIDENCE_PYTHON.as_bytes(),
        },
        SourceDocument {
            relative_path: "src/unowned.c",
            bytes: EVIDENCE_PROCEDURAL_SOURCE.as_bytes(),
        },
        SourceDocument {
            relative_path: "src/return.py",
            bytes: UNRESOLVED_RETURN_PYTHON.as_bytes(),
        },
        SourceDocument {
            relative_path: "src/carrier.rs",
            bytes: UNRESOLVED_CARRIER_RUST.as_bytes(),
        },
        SourceDocument {
            relative_path: "api/parameters.h",
            bytes: UNRESOLVED_PARAMETERS_PROCEDURAL_SOURCE.as_bytes(),
        },
        SourceDocument {
            relative_path: "api/template.hpp",
            bytes: UNRESOLVED_TEMPLATE_CPP.as_bytes(),
        },
    ];
    reviewer.review(ReviewInput::Documents(DocumentSet {
        revision: "evidence-projection",
        documents: &sources,
    }))
}

/// 验证终态投影证据场景
#[test]
fn human_and_json_are_read_only_terminal_projections() {
    let terminal = sealed_terminal();
    let human = project_human(&terminal);
    assert!(human.contains("Terminal: Sealed"));
    assert!(human.contains("Completion: Complete"));
    assert!(human.contains("Blocked families: 0"));

    let structured_output: Value = serde_json::from_slice(
        &project_javascript_object_notation(&terminal).unwrap(),
    )
    .unwrap();
    assert_eq!(structured_output["schema_version"], 2);
    assert_eq!(structured_output["terminal"], "sealed");
    assert_eq!(structured_output["disposition"], "clean");
    assert!(structured_output.get("passed").is_none());
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("fixture must seal");
    };
    assert_eq!(structured_output["review"]["seal"], review.seal());
    assert_eq!(
        structured_output["review"]["presentation"]["chapters"][4]["profiles"]
            ["python"]["state"],
        "supported"
    );
    assert_eq!(
        structured_output["review"]["presentation"]["chapters"][2]["profiles"]
            ["cpp"]["state"],
        "needs_authority"
    );
    assert_eq!(
        structured_output["review"]["findings"],
        serde_json::json!([])
    );
    assert_eq!(
        structured_output["review"]["blocked_family_details"],
        serde_json::json!([])
    );
}

/// 验证终态投影证据场景
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
    let expected_reasons = [
        (
            "api/parameters.h",
            concat!(
                "unresolved callable documentation facts: ",
                "calculate_velocity@11:1[parameters]",
            ),
        ),
        (
            "api/template.hpp",
            concat!(
                "unresolved callable documentation facts: ",
                "calculate_velocity@11:1[template]",
            ),
        ),
        (
            "src/carrier.rs",
            concat!(
                "unresolved callable documentation facts: ",
                "calculate_velocity@2:1[carrier]",
            ),
        ),
        (
            "src/return.py",
            concat!(
                "unresolved callable documentation facts: ",
                "calculate_velocity@1:1[return]",
            ),
        ),
    ];
    for (path, reason) in expected_reasons {
        assert!(blocked.iter().any(|detail| {
            detail["file"] == path
                && detail["family"] == "documentation"
                && detail["reason"] == reason
        }));
    }
    assert_eq!(
        structured_output["review"]["finding_summary"]["total"],
        findings.len()
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

/// 验证终态投影证据场景
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

/// 验证终态投影证据场景
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
