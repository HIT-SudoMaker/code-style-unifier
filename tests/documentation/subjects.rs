use super::OBJECT_ORIENTED_PATH;
use super::PROCEDURAL_PATH;
use super::assert_complete_clean;
use super::assert_exact_hard;
use super::has_rule;
use super::review;
use csu::Completion;
use csu::FindingGrade;

/// 验证 Rust 公开类型、字段和枚举变体均受文档检查
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

/// 验证 Rust 公开声明分别使用其直接附属文档
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

/// 验证公开 trait 默认方法与签名共享合同但嵌套函数保留内部要求
#[test]
fn rust_public_trait_defaults_keep_direct_owner_visibility() {
    for ending in [";", " { 1.0 }"] {
        let source = format!(
            "/// 定义速度接口\npub trait Velocity {{\n    /// 计算数值\n    fn calculate_velocity(&self) -> f64{ending}\n}}\n"
        );
        assert_exact_hard(
            &review("public-trait", &[("src/value.rs", &source)], &[]),
            &[(
                "src/value.rs",
                "documentation.public_contract",
                "calculate_velocity",
            )],
        );
        let private_source = source.replace("pub trait", "trait");
        assert_complete_clean(
            &review(
                "private-trait",
                &[("src/value.rs", &private_source)],
                &[],
            ),
            "private-trait",
        );
    }
    let source = "/// 定义速度接口\npub trait Velocity {\n    /// 计算数值\n    ///\n    /// # Arguments\n    /// - 无\n    /// # Returns\n    /// - 无\n    /// # Errors\n    /// - 无\n    fn calculate_velocity(&self) {\n        /// 计算内部数值\n        fn value() {}\n    }\n}\n";
    assert_complete_clean(
        &review("trait-default-helper", &[("src/value.rs", source)], &[]),
        "trait-default-helper",
    );
}

/// 验证 Rust 公开元组字段使用位置身份及各自的文档
#[test]
fn rust_public_tuple_fields_keep_positional_documentation() {
    let source = "/// 定义速度结构\npub struct Velocity(\n    /// 保存距离\n    pub f64,\n    #[doc = r\"保存时间\"]\n    pub f64,\n    f64,\n    pub(crate) f64,\n);\n";
    let valid = review("tuple-fields", &[("src/value.rs", source)], &[]);
    assert_complete_clean(&valid, "tuple-fields");
    let undocumented = source
        .replace("    /// 保存距离\n", "")
        .replace("    #[doc = r\"保存时间\"]\n", "");
    assert_exact_hard(
        &review(
            "tuple-fields-missing",
            &[("src/value.rs", &undocumented)],
            &[],
        ),
        &[
            ("src/value.rs", "documentation.carrier", "<tuple-field:0>"),
            ("src/value.rs", "documentation.carrier", "<tuple-field:1>"),
        ],
    );
    let unknown = source.replace(
        "#[doc = r\"保存时间\"]",
        "#[doc = include_str!(\"missing.md\")]",
    );
    let result =
        review("tuple-fields-unknown", &[("src/value.rs", &unknown)], &[]);
    assert_eq!(result.completion(), Completion::Incomplete);
    assert!(!has_rule(&result, "documentation.carrier"));
}

/// 验证 Python 属性访问器仅在归属明确时共享文档
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
    assert_complete_clean(&valid, "property-owner");

    let orphan = proven.replace("    @property\n", "    @other.setter\n");
    let blocked = review(
        "orphan-property-owner",
        &[("src/property.py", orphan.as_str())],
        &[],
    );
    assert_eq!(blocked.completion(), Completion::Incomplete);
}

/// 验证 Python 接收者参数和受控字段句号均受检查
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
    let class_source = receiver
        .replace(
            "calculate_velocity(receiver) -> float",
            "__init_subclass__(cls) -> None",
        )
        .replace("float: 平均速度", "无");
    let class_review = self::review(
        "class-receiver",
        &[("src/receiver.py", &class_source)],
        &[],
    );
    assert_eq!(class_review.completion(), Completion::Complete);
    assert!(!has_rule(&class_review, "documentation.public_contract"));
    assert!(!has_rule(&class_review, "identifier.canonical_form"));
    let class_source = class_source.replace(
        "Args:\n            无",
        "Args:\n            cls: 隐式类接收者",
    );
    let class_review = self::review(
        "class-receiver-extra",
        &[("src/receiver.py", &class_source)],
        &[],
    );
    assert_eq!(class_review.completion(), Completion::Complete);
    assert!(has_rule(&class_review, "documentation.public_contract"));
}
/// 验证无法完整识别的 C/C++ 可变参数不被猜成完整
#[test]
fn variadic_native_signatures_remain_incomplete_not_guessed() {
    let carrier = r#"/**
 * 计算平均速度
 *
 * 参数：
 * - distance_m： 行进距离
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

/// 验证 C/C++ 公开声明存在归属歧义时阻止文档检查完成
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
