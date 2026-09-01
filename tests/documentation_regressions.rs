use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::Completion;
use csu::DocumentSet;
use csu::FindingGrade;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SealedReview;
use csu::SourceDocument;
use csu::WorkspaceReviewer;

const AUTHORITY: &str = include_str!("../docs/fixtures/core/authority.json");
const PROCEDURAL_PATH: &str = "api/contract.h";
const OBJECT_ORIENTED_PATH: &str = "api/contract.hpp";

/// 构造测试 Reviewer
fn reviewer(public_names: &[&str]) -> WorkspaceReviewer {
    let mut authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    authority["public_callables"] = if public_names.is_empty() {
        serde_json::json!({})
    } else {
        serde_json::json!({
            PROCEDURAL_PATH: public_names,
            OBJECT_ORIENTED_PATH: public_names
        })
    };
    authority["header_languages"] = serde_json::json!({PROCEDURAL_PATH: "c"});
    authority["token_vocabulary"]
        .as_array_mut()
        .unwrap()
        .extend([
            serde_json::json!("contract"),
            serde_json::json!("inner"),
            serde_json::json!("receiver"),
            serde_json::json!("value"),
        ]);
    let bytes = serde_json::to_vec(&authority).unwrap();
    WorkspaceReviewer::compile(AuthorityInput::Documents(&[
        AuthorityDocument {
            relative_path: "authority.json",
            bytes: &bytes,
        },
    ]))
    .unwrap()
}

/// 审查内存源码并返回封存终态
fn review<'source>(
    revision: &'source str,
    sources: &'source [(&'source str, &'source str)],
    public_names: &[&str],
) -> SealedReview {
    let documents: Vec<_> = sources
        .iter()
        .map(|(relative_path, source)| SourceDocument {
            relative_path,
            bytes: source.as_bytes(),
        })
        .collect();
    let terminal =
        reviewer(public_names).review(ReviewInput::Documents(DocumentSet {
            revision,
            documents: &documents,
        }));
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("regression source must seal: {terminal:#?}");
    };
    review
}

/// 判断审查是否包含指定规则
fn has_rule(review: &SealedReview, rule: &str) -> bool {
    review
        .findings()
        .iter()
        .any(|finding| finding.rule() == rule)
}

/// 验证文档规则回归场景
#[test]
fn rust_literal_doc_attribute_and_block_rustdoc_are_real_carriers() {
    let sources = [
        (
            "src/attribute.rs",
            "#[doc = \"计算平均速度\"]\nfn calculate_velocity() {}\n",
        ),
        (
            "src/block.rs",
            "/** 计算平均速度 */\nfn calculate_velocity() {}\n",
        ),
    ];
    let review = review("rust-carriers", &sources, &[]);

    assert_eq!(review.completion(), Completion::Complete);
    assert!(
        !review
            .findings()
            .iter()
            .any(|finding| { finding.rule().starts_with("documentation.") }),
        "{:#?}",
        review.findings()
    );
}

/// 验证文档规则回归场景
#[test]
fn rustdoc_code_blocks_cannot_supply_public_contract_fields() {
    let summary_source = r#"/// ```text
/// 计算平均速度
/// # Arguments
/// - distance_m：行进距离
/// # Returns
/// - 平均速度
/// # Errors
/// - 无
/// ```
pub fn calculate_velocity(distance_m: f64) -> f64 { distance_m }
"#;
    let contract_source = r#"/// 计算平均速度
///
/// ```text
/// # Arguments
/// - distance_m：行进距离
/// # Returns
/// - 平均速度
/// # Errors
/// - 无
/// ```
pub fn calculate_velocity(distance_m: f64) -> f64 { distance_m }
"#;
    let review = review(
        "rustdoc-code-block",
        &[
            ("src/summary.rs", summary_source),
            ("src/contract.rs", contract_source),
        ],
        &[],
    );

    assert!(review.findings().iter().any(|finding| {
        finding.path() == "src/summary.rs"
            && finding.rule() == "documentation.summary"
    }));
    assert!(review.findings().iter().any(|finding| {
        finding.path() == "src/contract.rs"
            && finding.rule() == "documentation.public_contract"
    }));
}

/// 验证文档规则回归场景
#[test]
fn isolated_chinese_character_cannot_validate_english_documentation() {
    let internal = "/// Return velocity 中\nfn calculate_velocity() {}\n";
    let public = r#"/// 计算平均速度
///
/// # Arguments
/// - distance_m：distance 中
/// # Returns
/// - velocity 中
/// # Errors
/// - 无
pub fn calculate_velocity(distance_m: f64) -> f64 { distance_m }
"#;
    let review = review(
        "chinese-phrase",
        &[("src/internal.rs", internal), ("src/public.rs", public)],
        &[],
    );

    assert!(review.findings().iter().any(|finding| {
        finding.path() == "src/internal.rs"
            && finding.rule() == "documentation.summary"
    }));
    assert!(review.findings().iter().any(|finding| {
        finding.path() == "src/public.rs"
            && finding.rule() == "documentation.public_contract"
    }));
}

/// 验证文档规则回归场景
#[test]
fn rust_exposure_subjects_keep_direct_documentation_owners() {
    let sources = [
        (
            "src/trait.rs",
            "/// 定义速度计算契约\npub trait Velocity {\n    fn calculate_velocity(&self);\n}\n",
            "calculate_velocity",
        ),
        (
            "src/foreign.rs",
            "unsafe extern \"C\" { fn calculate_velocity(); }\n",
            "calculate_velocity",
        ),
        (
            "src/macro.rs",
            "#[macro_export]\nmacro_rules! calculate_velocity { () => {}; }\n",
            "calculate_velocity",
        ),
        (
            "src/export.rs",
            "pub use crate::velocity::calculate_velocity;\n",
            "pub use ",
        ),
    ];
    for (path, source, subject) in sources {
        let review = review("rust-exposure", &[(path, source)], &[]);
        assert!(review.findings().iter().any(|finding| {
            finding.path() == path
                && finding.rule() == "documentation.carrier"
                && finding.subject().contains(subject)
        }));
    }
}

/// 验证文档规则回归场景
#[test]
fn rust_public_types_fields_and_variants_are_direct_subjects() {
    let source = r#"pub struct Velocity {
    pub distance_m: f64,
}
pub enum Distance { Velocity }
"#;
    let review =
        review("rust-public-subjects", &[("src/items.rs", source)], &[]);

    for subject in ["Velocity", "distance_m", "Distance"] {
        assert!(review.findings().iter().any(|finding| {
            finding.subject() == subject
                && finding.rule() == "documentation.carrier"
        }));
    }
}

/// 验证文档规则回归场景
#[test]
fn python_property_accessors_share_only_proven_direct_owner() {
    let proven = r#"class Velocity:
    """
    表示速度属性
    """

    @property
    def value(self) -> float:
        """
        读取速度数值

        Args:
            无
        Returns:
            float: 速度数值
        Raises:
            无
        """
        return 1.0

    @value.setter
    def value(self, velocity_m_per_s) -> None:
        """
        设置速度数值

        Args:
            velocity_m_per_s: 速度数值
        Returns:
            无
        Raises:
            无
        """

    @value.deleter
    def value(self) -> None:
        """
        删除速度数值

        Args:
            无
        Returns:
            无
        Raises:
            无
        """
"#;
    let valid = review("property-owner", &[("src/property.py", proven)], &[]);
    assert_eq!(valid.completion(), Completion::Complete);
    assert!(
        !valid
            .findings()
            .iter()
            .any(|finding| finding.rule().starts_with("documentation.")),
        "{:#?}",
        valid.findings()
    );

    let orphan = proven.replace("    @property\n", "    @other.setter\n");
    let blocked = review(
        "orphan-property-owner",
        &[("src/property.py", orphan.as_str())],
        &[],
    );
    assert_eq!(blocked.completion(), Completion::Incomplete);
}

/// 验证文档规则回归场景
#[test]
fn variadic_native_signatures_remain_incomplete_not_guessed() {
    let carrier = r#"/**
 * 计算平均速度
 *
 * 参数：
 * - distance_m：行进距离
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
double calculate_velocity(double distance_m, ...);
"#;
    for path in [PROCEDURAL_PATH, OBJECT_ORIENTED_PATH] {
        let review =
            review("variadic", &[(path, carrier)], &["calculate_velocity"]);
        assert_eq!(review.completion(), Completion::Incomplete, "{path}");
    }
}

/// 验证文档规则回归场景
#[test]
fn duplicate_headings_and_extra_parameters_are_hard_contract_errors() {
    let base = r#"def calculate_velocity(distance_m: float) -> float:
    """
    计算平均速度

    Args:
        distance_m: 行进距离
    Returns:
        float: 平均速度
    Raises:
        无
    """
    return distance_m
"#;
    let cases = [
        base.replace(
            "    Returns:\n",
            "    Args:\n        value: 额外值\n    Returns:\n",
        ),
        base.replace(
            "    Returns:\n",
            "        value: 额外值\n    Returns:\n",
        ),
    ];
    for source in cases {
        let review = review(
            "invalid-public-fields",
            &[("src/fields.py", source.as_str())],
            &[],
        );
        assert!(has_rule(&review, "documentation.public_contract"));
    }
}

/// 验证文档规则回归场景
#[test]
fn python_closing_quotes_must_own_their_physical_line() {
    let source = r#"def _calculate_velocity():
    """
    计算平均速度
    """  # ordinary trailing text
    return 1
"#;
    let review = review("closing-quotes", &[("src/quotes.py", source)], &[]);

    assert!(has_rule(&review, "documentation.carrier"));
}

/// 验证文档规则回归场景
#[test]
fn ambiguous_native_public_owners_block_documentation_closure() {
    let source = r#"/**
 * 计算平均速度
 *
 * 参数：
 * - 无
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
double calculate_velocity(void);
double calculate_velocity(void);
"#;
    let review = review(
        "ambiguous-owner",
        &[(PROCEDURAL_PATH, source)],
        &["calculate_velocity"],
    );

    assert_eq!(review.completion(), Completion::Incomplete);
}

/// 验证文档规则回归场景
#[test]
fn rust_never_return_uses_the_explicit_never_marker() {
    let invalid = r#"/// 停止执行
///
/// # Arguments
/// - 无
/// # Returns
/// - 无
/// # Errors
/// - 无
pub fn calculate_velocity() -> ! { panic!() }
"#;
    let invalid_review =
        review("never-invalid", &[("src/never.rs", invalid)], &[]);
    assert!(has_rule(&invalid_review, "documentation.public_contract"));

    let valid = invalid
        .replace("/// - 无\n/// # Errors", "/// - 不返回\n/// # Errors");
    let valid_review =
        review("never-valid", &[("src/never.rs", valid.as_str())], &[]);
    assert!(!has_rule(&valid_review, "documentation.public_contract"));
}

/// 验证文档规则回归场景
#[test]
fn python_receiver_role_and_controlled_punctuation_are_enforced() {
    let receiver = r#"class Velocity:
    def calculate_velocity(receiver) -> float:
        """
        计算平均速度

        Args:
            无
        Returns:
            float: 平均速度
        Raises:
            无
        """
        return 1.0
"#;
    let punctuation = r#"def _calculate_velocity():
    """
    计算平均速度。
    """
    return 1
"#;
    let review = review(
        "receiver-and-punctuation",
        &[
            ("src/receiver.py", receiver),
            ("src/punctuation.py", punctuation),
        ],
        &[],
    );

    assert!(review.findings().iter().any(|finding| {
        finding.path() == "src/receiver.py"
            && finding.grade() == FindingGrade::HardViolation
    }));
    assert!(review.findings().iter().any(|finding| {
        finding.path() == "src/punctuation.py"
            && finding.rule() == "documentation.punctuation"
    }));
}
