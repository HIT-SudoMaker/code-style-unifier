use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::Completion;
use csu::Disposition;
use csu::DocumentSet;
use csu::FactFamily;
use csu::FactFamilyState;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SealedReview;
use csu::SourceDocument;
use csu::WorkspaceReviewer;

const AUTHORITY: &str = include_str!("../docs/fixtures/core/authority.json");
const PYTHON_PATH: &str = "src/velocity.py";
const RUST_PATH: &str = "src/velocity.rs";
const PROCEDURAL_HEADER_PATH: &str = "api/velocity.h";
const OBJECT_ORIENTED_HEADER_PATH: &str = "api/velocity.hpp";

const PYTHON_VALID: &str = r#"def calculate_velocity(distance_m: float, duration_s: float) -> float:
    """
    计算平均速度

    Args:
        distance_m: 行进距离
        duration_s: 持续时间
    Returns:
        float: 平均速度
    Raises:
        ValueError: 持续时间不大于零
    """
    return distance_m / duration_s
"#;

const RUST_VALID: &str = r#"/// 计算平均速度
///
/// # Arguments
/// - distance_m：行进距离
/// - duration_s：持续时间
/// # Returns
/// - 平均速度
/// # Errors
/// - 持续时间不大于零时返回错误
pub fn calculate_velocity(distance_m: f64, duration_s: f64) -> Result<f64, ()> {
    Ok(distance_m / duration_s)
}
"#;

const PROCEDURAL_VALID: &str = r#"/**
 * 计算平均速度
 *
 * 参数：
 * - distance_m：行进距离
 * - duration_s：持续时间
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
double calculate_velocity(double distance_m, double duration_s);
"#;

const OBJECT_ORIENTED_VALID: &str = r#"/**
 * 计算平均速度
 *
 * 参数：
 * - distance_m：行进距离
 * - duration_s：持续时间
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
double calculate_velocity(double distance_m, double duration_s);
"#;

/// 构造测试 Reviewer
fn reviewer() -> WorkspaceReviewer {
    let mut authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).expect("fixture Authority is JSON");
    authority["public_callables"] = serde_json::json!({
        PROCEDURAL_HEADER_PATH: ["calculate_velocity"],
        OBJECT_ORIENTED_HEADER_PATH: ["calculate_velocity"]
    });
    authority["header_languages"] =
        serde_json::json!({PROCEDURAL_HEADER_PATH: "c"});
    authority["token_vocabulary"]
        .as_array_mut()
        .expect("vocabulary is an array")
        .extend([
            serde_json::json!("engine"),
            serde_json::json!("inner"),
            serde_json::json!("object"),
            serde_json::json!("result"),
            serde_json::json!("value"),
        ]);
    let bytes = serde_json::to_vec(&authority).unwrap();
    WorkspaceReviewer::compile(AuthorityInput::Documents(&[
        AuthorityDocument {
            relative_path: "authority.json",
            bytes: &bytes,
        },
    ]))
    .expect("test Authority must compile")
}

/// 审查内存源码并返回封存终态
fn review<'source>(
    revision: &'source str,
    sources: &'source [(&'source str, &'source str)],
) -> SealedReview {
    let documents: Vec<_> = sources
        .iter()
        .map(|(relative_path, source)| SourceDocument {
            relative_path,
            bytes: source.as_bytes(),
        })
        .collect();
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision,
        documents: &documents,
    }));
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("direct source must produce a sealed terminal: {terminal:#?}");
    };
    review
}

/// 判断审查是否包含指定规则
fn has_rule(review: &SealedReview, path: &str, rule: &str) -> bool {
    review
        .findings()
        .iter()
        .any(|finding| finding.path() == path && finding.rule() == rule)
}

/// 验证公共审查证据场景
#[test]
fn public_roles_are_checked_in_parallel_across_four_languages() {
    let roles = [
        (
            "arguments",
            "    Args:\n",
            "/// # Arguments\n",
            " * 参数：\n",
        ),
        (
            "returns",
            "    Returns:\n",
            "/// # Returns\n",
            " * 返回：\n",
        ),
        ("failures", "    Raises:\n", "/// # Errors\n", " * 错误：\n"),
    ];
    for (revision, python_role, rust_role, native_role) in roles {
        let python = PYTHON_VALID.replace(python_role, "");
        let rust = RUST_VALID.replace(rust_role, "");
        let procedural = PROCEDURAL_VALID.replace(native_role, "");
        let object_oriented = OBJECT_ORIENTED_VALID.replace(native_role, "");
        let sources = [
            (PYTHON_PATH, python.as_str()),
            (RUST_PATH, rust.as_str()),
            (PROCEDURAL_HEADER_PATH, procedural.as_str()),
            (OBJECT_ORIENTED_HEADER_PATH, object_oriented.as_str()),
        ];
        let review = review(revision, &sources);

        for (path, _) in sources {
            assert!(
                has_rule(&review, path, "documentation.public_contract"),
                "{path}: {:#?}",
                review.findings()
            );
        }
    }
}

/// 验证公共审查证据场景
#[test]
fn return_shape_and_empty_marker_contracts_hold_in_all_languages() {
    let value_sources = [
        (
            PYTHON_PATH,
            PYTHON_VALID.replace("        float: 平均速度\n", "        无\n"),
        ),
        (
            RUST_PATH,
            RUST_VALID.replace("/// - 平均速度\n", "/// - 无\n"),
        ),
        (
            PROCEDURAL_HEADER_PATH,
            PROCEDURAL_VALID.replace(" * - 平均速度\n", " * - 无\n"),
        ),
        (
            OBJECT_ORIENTED_HEADER_PATH,
            OBJECT_ORIENTED_VALID.replace(" * - 平均速度\n", " * - 无\n"),
        ),
    ];
    for (path, source) in &value_sources {
        let review = review("value-return-empty", &[(path, source)]);
        assert!(has_rule(&review, path, "documentation.public_contract"));
    }

    let no_value_sources = [
        (
            PYTHON_PATH,
            PYTHON_VALID
                .replace(" -> float", " -> None")
                .replace("        float: 平均速度\n", "        已完成计算\n"),
        ),
        (
            RUST_PATH,
            RUST_VALID
                .replace(" -> Result<f64, ()>", "")
                .replace("    Ok(distance_m / duration_s)", "")
                .replace("/// - 平均速度\n", "/// - 已完成计算\n"),
        ),
        (
            PROCEDURAL_HEADER_PATH,
            PROCEDURAL_VALID
                .replace(
                    "double calculate_velocity",
                    "void calculate_velocity",
                )
                .replace(" * - 平均速度\n", " * - 已完成计算\n"),
        ),
        (
            OBJECT_ORIENTED_HEADER_PATH,
            OBJECT_ORIENTED_VALID
                .replace(
                    "double calculate_velocity",
                    "void calculate_velocity",
                )
                .replace(" * - 平均速度\n", " * - 已完成计算\n"),
        ),
    ];
    for (path, source) in &no_value_sources {
        let review = review("empty-return-value", &[(path, source)]);
        assert!(has_rule(&review, path, "documentation.public_contract"));
    }

    let noncanonical_empty = [
        (
            PYTHON_PATH,
            PYTHON_VALID
                .replace("distance_m: float, duration_s: float", "")
                .replace(
                    "        distance_m: 行进距离\n        duration_s: 持续时间\n",
                    "        None\n",
                ),
        ),
        (
            RUST_PATH,
            RUST_VALID
                .replace("distance_m: f64, duration_s: f64", "")
                .replace(
                    "/// - distance_m：行进距离\n/// - duration_s：持续时间\n",
                    "/// - None\n",
                ),
        ),
        (
            PROCEDURAL_HEADER_PATH,
            PROCEDURAL_VALID
                .replace("double distance_m, double duration_s", "void")
                .replace(
                    " * - distance_m：行进距离\n * - duration_s：持续时间\n",
                    " * - None\n",
                ),
        ),
        (
            OBJECT_ORIENTED_HEADER_PATH,
            OBJECT_ORIENTED_VALID
                .replace("double distance_m, double duration_s", "")
                .replace(
                    " * - distance_m：行进距离\n * - duration_s：持续时间\n",
                    " * - None\n",
                ),
        ),
    ];
    for (path, source) in &noncanonical_empty {
        let review = review("noncanonical-empty", &[(path, source)]);
        assert!(has_rule(&review, path, "documentation.public_contract"));
    }
}

/// 验证公共审查证据场景
#[test]
fn missing_carrier_is_conclusive_even_when_signature_facts_are_unknown() {
    let missing =
        "def calculate_velocity(distance_m):\n    return distance_m\n";
    let unresolved_with_carrier = r#"def calculate_velocity() -> Velocity:
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
    let missing_review =
        review("missing-unknown-signature", &[(PYTHON_PATH, missing)]);
    assert_eq!(missing_review.completion(), Completion::Complete);
    assert!(has_rule(
        &missing_review,
        PYTHON_PATH,
        "documentation.carrier"
    ));

    let unresolved_review = review(
        "carrier-unknown-signature",
        &[(PYTHON_PATH, unresolved_with_carrier)],
    );
    assert_eq!(unresolved_review.completion(), Completion::Incomplete);
    assert!(
        unresolved_review.coverage().files()[0]
            .families()
            .iter()
            .any(|(family, state)| {
                *family == FactFamily::Documentation
                    && matches!(state, FactFamilyState::Blocked(_))
            })
    );
}

/// 验证公共审查证据场景
#[test]
fn python_property_decorator_ownership_never_uses_guess() {
    let proven = r#"class Velocity:
    @property
    def value(self) -> float:
        """
        返回速度值

        Args:
            无
        Returns:
            float: 速度值
        Raises:
            无
        """
        return 1.0
"#;
    let unknown = r#"@custom.decorator
def calculate_velocity() -> float:
    """
    计算平均速度。

    Args:
        无
    Returns:
        float: 平均速度
    Raises:
        无
    """
    return 1.0
"#;
    let valid = review("property-owner", &[(PYTHON_PATH, proven)]);
    assert_eq!(valid.completion(), Completion::Complete);

    let blocked = review("unknown-decorator", &[(PYTHON_PATH, unknown)]);
    assert_eq!(blocked.completion(), Completion::Incomplete);
    assert!(has_rule(&blocked, PYTHON_PATH, "documentation.punctuation"));
}

/// 验证公共审查证据场景
#[test]
fn unsafe_rust_and_python_module_docstrings_keep_distinct_hard_evidence() {
    let unsafe_rust = RUST_VALID.replace(
        "pub fn calculate_velocity",
        "pub unsafe fn calculate_velocity",
    );
    let python_module = format!("\"\"\"\n模块文档\n\"\"\"\n{PYTHON_VALID}");
    let sources = [
        (RUST_PATH, unsafe_rust.as_str()),
        (PYTHON_PATH, python_module.as_str()),
    ];
    let review = review("special-documentation-owners", &sources);

    assert!(has_rule(&review, RUST_PATH, "documentation.safety"));
    assert!(review.findings().iter().any(|finding| {
        finding.path() == PYTHON_PATH
            && finding.rule() == "documentation.carrier"
            && finding.subject() == "<module>"
            && finding.message()
                == "documentation subject has a missing or forbidden profile carrier"
    }));
}

/// 验证公共审查证据场景
#[test]
fn terminal_disposition_never_calls_incomplete_or_hard_findings_clean() {
    let incomplete = r#"@custom.decorator
def calculate_velocity() -> float:
    return 1.0
"#;
    let terminal = reviewer().review(ReviewInput::Documents(DocumentSet {
        revision: "terminal-projection",
        documents: &[SourceDocument {
            relative_path: PYTHON_PATH,
            bytes: incomplete.as_bytes(),
        }],
    }));
    assert_eq!(terminal.disposition(), Disposition::Incomplete);
}
