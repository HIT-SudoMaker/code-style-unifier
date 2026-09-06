use csu::Completion;
use csu::FactFamily;
use csu::FactFamilyState;
use csu::ReviewTerminal;
use csu::SealedReview;
use csu::WorkspaceReviewer;

#[path = "../review_fixture/mod.rs"]
mod review_fixture;

use review_fixture::compile_value;
use review_fixture::review_sources;

const PYTHON_PATH: &str = "src/velocity.py";
const RUST_PATH: &str = "src/velocity.rs";
const PROCEDURAL_HEADER_PATH: &str = "api/velocity.h";
const OBJECT_ORIENTED_HEADER_PATH: &str = "api/velocity.hpp";

const PYTHON_VALID: &str = include_str!(
    "../../docs/fixtures/core/documents/valid/python/calculate_velocity.py"
);
const RUST_VALID: &str = include_str!(
    "../../docs/fixtures/core/documents/valid/rust/calculate_velocity.rs"
);
const PROCEDURAL_VALID: &str = include_str!(
    "../../docs/fixtures/core/documents/valid/c/calculate_velocity.h"
);
const OBJECT_ORIENTED_VALID: &str = include_str!(
    "../../docs/fixtures/core/documents/valid/cpp/calculate_velocity.hpp"
);

/// 创建测试审查器
fn reviewer() -> WorkspaceReviewer {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../../docs/fixtures/core/authority.json"
    ))
    .unwrap();
    authority["public_callables"] = serde_json::json!({
        PROCEDURAL_HEADER_PATH: ["calculate_velocity"],
        OBJECT_ORIENTED_HEADER_PATH: ["calculate_velocity"]
    });
    authority["header_languages"] =
        serde_json::json!({PROCEDURAL_HEADER_PATH: "c"});
    authority["token_vocabulary"]
        .as_array_mut()
        .expect("vocabulary is an array")
        .extend(
            ["engine", "inner", "object", "result", "value"]
                .map(serde_json::Value::from),
        );
    compile_value(&authority).expect("test Authority must compile")
}

/// 审查内存源码并返回封存终态
fn review<'source>(
    revision: &'source str,
    sources: &'source [(&'source str, &'source str)],
) -> SealedReview {
    let terminal = review_sources(&reviewer(), revision, sources);
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("direct source must produce a sealed terminal: {terminal:#?}");
    };
    review
}

/// 断言每份源码恰有一条公开文档硬违规且检查完整
fn assert_contract(review: &SealedReview, paths: &[&str]) {
    assert_eq!(review.completion(), Completion::Complete);
    assert_eq!(review.findings().len(), paths.len(), "{review:#?}");
    for path in paths {
        let findings: Vec<_> = review
            .findings()
            .iter()
            .filter(|finding| finding.path() == *path)
            .collect();
        let [finding] = findings.as_slice() else {
            panic!("{path}: {review:#?}");
        };
        assert_eq!(finding.rule(), "documentation.public_contract");
        assert_eq!(finding.grade(), csu::FindingGrade::HardViolation);
        assert_eq!(finding.subject(), "calculate_velocity");
    }
}

/// 验证四语言分别检查公开文档的必需部分
#[test]
fn public_roles_are_checked_in_parallel_across_four_languages() {
    let baseline = review(
        "public-control",
        &[
            (PYTHON_PATH, PYTHON_VALID),
            (RUST_PATH, RUST_VALID),
            (PROCEDURAL_HEADER_PATH, PROCEDURAL_VALID),
            (OBJECT_ORIENTED_HEADER_PATH, OBJECT_ORIENTED_VALID),
        ],
    );
    assert_eq!(baseline.completion(), Completion::Complete);
    assert!(baseline.findings().is_empty(), "{baseline:#?}");
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
        let python = (PYTHON_VALID).replacen(python_role, "", 1);
        let rust = (RUST_VALID).replacen(rust_role, "", 1);
        let procedural = (PROCEDURAL_VALID).replacen(native_role, "", 1);
        let object_oriented =
            (OBJECT_ORIENTED_VALID).replacen(native_role, "", 1);
        let sources = [
            (PYTHON_PATH, python.as_str()),
            (RUST_PATH, rust.as_str()),
            (PROCEDURAL_HEADER_PATH, procedural.as_str()),
            (OBJECT_ORIENTED_HEADER_PATH, object_oriented.as_str()),
        ];
        let review = review(revision, &sources);

        assert_contract(&review, &sources.map(|(path, _)| path));
    }
}

/// 验证四语言均拒绝不规范的空参数标记
#[test]
fn noncanonical_empty_parameter_markers_stay_hard_in_all_profiles() {
    let noncanonical_empty = [
        (
            PYTHON_PATH,
            ((PYTHON_VALID).replacen("distance_m: float, duration_s: float", "", 1)).replacen("        distance_m: 行进距离\n        duration_s: 持续时间\n", "        None\n", 1),
        ),
        (
            RUST_PATH,
            ((RUST_VALID).replacen("    distance_m: f64,\n    duration_s: f64,\n", "", 1)).replacen("/// - distance_m： 行进距离\n/// - duration_s： 持续时间\n", "/// - None\n", 1),
        ),
        (
            PROCEDURAL_HEADER_PATH,
            ((PROCEDURAL_VALID).replacen("    double distance_m,\n    double duration_s,\n    double *velocity_m_per_s\n", "    void\n", 1)).replacen(" * - distance_m：       行进距离\n * - duration_s：       持续时间\n * - velocity_m_per_s： 平均速度输出位置\n", " * - None\n", 1),
        ),
        (
            OBJECT_ORIENTED_HEADER_PATH,
            ((OBJECT_ORIENTED_VALID).replacen("double distance_m, double duration_s", "", 1)).replacen(" * - distance_m： 行进距离\n * - duration_s： 持续时间\n", " * - None\n", 1),
        ),
    ];
    for (path, source) in &noncanonical_empty {
        let review = review("noncanonical-empty", &[(path, source)]);
        assert_contract(&review, &[path]);
    }
}

/// 验证文档缺失与函数签名未知分别记录
#[test]
fn missing_carrier_and_unknown_signature_remain_independent() {
    let missing =
        "def calculate_velocity(distance_m):\n    return distance_m\n";
    let unresolved_with_carrier = r#"def calculate_velocity():
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
    assert_eq!(missing_review.completion(), Completion::Incomplete);
    let [finding] = missing_review.findings() else {
        panic!("{missing_review:#?}");
    };
    assert_eq!(finding.path(), PYTHON_PATH);
    assert_eq!(finding.rule(), "documentation.carrier");
    assert_eq!(finding.grade(), csu::FindingGrade::HardViolation);

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

/// 验证四语言均拒绝文档尾部的未知标题
#[test]
fn unknown_tail_headings_close_hard_in_all_four_profiles() {
    let python = (PYTHON_VALID).replacen(
        "    Raises:\n        ValueError: 持续时间不大于零\n",
        concat!(
            "    Raises:\n        ValueError: 持续时间不大于零\n",
            "    Attributes:\n        engine: 引擎描述\n",
        ),
        1,
    );
    let rust = (RUST_VALID).replacen(
        "/// # Errors\n/// - 持续时间不大于零时返回错误\n",
        concat!(
            "/// # Errors\n/// - 持续时间不大于零时返回错误\n",
            "/// # Examples\n/// - 演示基本用法\n",
        ),
        1,
    );
    let procedural = (PROCEDURAL_VALID).replacen(" * 错误：\n * - duration_s不大于零时返回false\n", " * 错误：\n * - duration_s不大于零时返回false\n * 所有权：\n * - 调用方持有结果\n", 1);
    let object_oriented = (OBJECT_ORIENTED_VALID).replacen(" * 错误：\n * - duration_s不大于零时抛出std::invalid_argument\n", " * 错误：\n * - duration_s不大于零时抛出std::invalid_argument\n * 所有权：\n * - 调用方持有结果\n", 1);
    let sources = [
        (PYTHON_PATH, python.as_str()),
        (RUST_PATH, rust.as_str()),
        (PROCEDURAL_HEADER_PATH, procedural.as_str()),
        (OBJECT_ORIENTED_HEADER_PATH, object_oriented.as_str()),
    ];
    let review = review("unknown-tail-headings", &sources);
    assert_contract(&review, &sources.map(|(path, _)| path));
}

/// 验证四语言均拒绝次序错误的必需标题
#[test]
fn reordered_required_headings_stay_hard_in_all_profiles() {
    let python = (PYTHON_VALID).replacen(
        concat!(
            "    Args:\n",
            "        distance_m: 行进距离\n",
            "        duration_s: 持续时间\n",
            "    Returns:\n",
            "        float: 平均速度\n",
        ),
        concat!(
            "    Returns:\n",
            "        float: 平均速度\n",
            "    Args:\n",
            "        distance_m: 行进距离\n",
            "        duration_s: 持续时间\n",
        ),
        1,
    );
    let rust = (RUST_VALID).replacen("/// # Arguments\n/// - distance_m： 行进距离\n/// - duration_s： 持续时间\n/// # Returns\n/// - 平均速度\n", "/// # Returns\n/// - 平均速度\n/// # Arguments\n/// - distance_m： 行进距离\n/// - duration_s： 持续时间\n", 1);
    let native_reordered = (PROCEDURAL_VALID).replacen(" * 参数：\n * - distance_m：       行进距离\n * - duration_s：       持续时间\n * - velocity_m_per_s： 平均速度输出位置\n * 返回：\n * - 计算是否成功\n", " * 返回：\n * - 计算是否成功\n * 参数：\n * - distance_m：       行进距离\n * - duration_s：       持续时间\n * - velocity_m_per_s： 平均速度输出位置\n", 1);
    let object_oriented_reordered = (OBJECT_ORIENTED_VALID).replacen(" * 参数：\n * - distance_m： 行进距离\n * - duration_s： 持续时间\n * 返回：\n * - 平均速度\n", " * 返回：\n * - 平均速度\n * 参数：\n * - distance_m： 行进距离\n * - duration_s： 持续时间\n", 1);
    let sources = [
        (PYTHON_PATH, python.as_str()),
        (RUST_PATH, rust.as_str()),
        (PROCEDURAL_HEADER_PATH, native_reordered.as_str()),
        (
            OBJECT_ORIENTED_HEADER_PATH,
            object_oriented_reordered.as_str(),
        ),
    ];
    let review = review("heading-order", &sources);
    assert_contract(&review, &sources.map(|(path, _)| path));
}
