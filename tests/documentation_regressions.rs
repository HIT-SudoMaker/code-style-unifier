use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::Completion;
use csu::FindingGrade;
use csu::ReviewTerminal;
use csu::SealedReview;
use csu::WorkspaceReviewer;

mod review_fixture;

use review_fixture::review_sources;

const VALID_PYTHON: &str = include_str!(
    "../docs/fixtures/core/documents/valid/python/calculate_velocity.py"
);
const VALID_RUST: &str = include_str!(
    "../docs/fixtures/core/documents/valid/rust/calculate_velocity.rs"
);
const VALID_PROCEDURAL: &str = include_str!(
    "../docs/fixtures/core/documents/valid/c/calculate_velocity.h"
);
const VALID_CPP: &str = include_str!(
    "../docs/fixtures/core/documents/valid/cpp/calculate_velocity.hpp"
);
const PROCEDURAL_PATH: &str = "api/contract.h";
const OBJECT_ORIENTED_PATH: &str = "api/contract.hpp";

/// 创建测试审查器
fn reviewer(public_names: &[&str]) -> WorkspaceReviewer {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../docs/fixtures/core/authority.json"
    ))
    .unwrap();
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
        .extend(
            [
                "contract", "count", "inner", "receiver", "sample", "totals",
                "value", "values",
            ]
            .map(serde_json::Value::from),
        );
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
    let terminal = review_sources(&reviewer(public_names), revision, sources);
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

/// 断言封存结果完整且没有问题
fn assert_complete_clean(review: &SealedReview, identity: &str) {
    assert_eq!(review.completion(), Completion::Complete, "{identity}");
    assert!(
        review.findings().is_empty(),
        "{identity}: {:#?}",
        review.findings()
    );
}

/// 断言封存结果只含指定硬违规
fn assert_exact_hard(review: &SealedReview, expected: &[(&str, &str, &str)]) {
    assert_eq!(review.completion(), Completion::Complete);
    let findings = review.findings();
    assert_eq!(findings.len(), expected.len(), "{findings:#?}");
    for &(path, rule, subject) in expected {
        assert!(
            findings.iter().any(|finding| {
                (
                    finding.path(),
                    finding.rule(),
                    finding.grade(),
                    finding.subject(),
                ) == (path, rule, FindingGrade::HardViolation, subject)
            }),
            "missing {path} {rule} {subject}"
        );
    }
}

/// 验证 Rust 属性不妨碍识别声明和原生块文档
#[test]
fn rust_attribute_identity_and_block_rustdoc_use_native_carriers() {
    let attribute_source = concat!(
        "#[doc = \"计算平均速度\"]\nfn calculate_velocity() {}\n",
        "#[ doc = \"计算持续时间\" ]\nfn calculate_duration() {}\n",
        "#[doctor]\nfn calculate_distance() {}\n",
        "#[macro_export]\nmacro_rules! calculate_velocity { () => {}; }\n",
        "#[ macro_export ]\nmacro_rules! calculate_duration { () => {}; }\n",
        "#[macro_exported]\nmacro_rules! calculate_distance { () => {}; }\n",
        "/** 计算平均速度 */\nfn calculate_value() {}\n",
    );
    let sources = [("src/attribute.rs", attribute_source)];
    let review = review("rust-attribute-identity", &sources, &[]);
    let subjects = [
        "calculate_distance",
        "calculate_velocity",
        "calculate_duration",
    ];
    let expected = subjects
        .map(|subject| ("src/attribute.rs", "documentation.carrier", subject));
    assert_exact_hard(&review, &expected);
}

/// 验证 Rust 安全文档与 Python 模块文档的问题分别记录
#[test]
fn unsafe_rust_and_python_module_docstrings_keep_distinct_hard_evidence() {
    let unsafe_rust = (VALID_RUST).replacen(
        "pub fn calculate_velocity",
        "pub unsafe fn calculate_velocity",
        1,
    );
    let python_module = format!("\"\"\"\n模块文档\n\"\"\"\n{VALID_PYTHON}");
    let sources = [
        ("src/velocity.rs", unsafe_rust.as_str()),
        ("src/velocity.py", python_module.as_str()),
    ];
    let review = review("special-documentation-owners", &sources, &[]);
    assert_exact_hard(
        &review,
        &[
            (
                "src/velocity.rs",
                "documentation.safety",
                "calculate_velocity",
            ),
            ("src/velocity.py", "documentation.carrier", "<module>"),
        ],
    );
}

/// 验证 Rust 文档代码块不能代替公开合同字段
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
/// # Returns
///     value.
pub fn calculate_velocity(distance_m: f64) -> f64 { distance_m }
"#;
    let sealed = review(
        "rustdoc-code-block",
        &[
            ("src/summary.rs", summary_source),
            ("src/contract.rs", contract_source),
        ],
        &[],
    );

    assert!(sealed.findings().iter().any(|finding| {
        finding.path() == "src/summary.rs"
            && finding.rule() == "documentation.summary"
    }));
    assert!(sealed.findings().iter().any(|finding| {
        finding.path() == "src/contract.rs"
            && finding.rule() == "documentation.public_contract"
    }));
    assert!(!sealed.findings().iter().any(|finding| {
        finding.path() == "src/contract.rs"
            && finding.rule() == "documentation.punctuation"
    }));
}

/// 验证 Rust 异常说明可选且安全函数禁止安全调用说明
#[test]
fn rust_native_panics_role_stays_optional_and_clean() {
    let panics = (VALID_RUST).replacen(
        "/// # Errors\n/// - 持续时间不大于零时返回错误\n",
        concat!(
            "/// # Errors\n/// - 持续时间不大于零时返回错误\n",
            "/// # Panics\n/// - 输入为零时触发恐慌\n",
        ),
        1,
    );
    let clean = review("panics", &[("src/velocity.rs", panics.as_str())], &[]);
    assert_complete_clean(&clean, "panics");
    let safety = panics.replacen("# Panics", "# Safety", 1);
    let rejected =
        review("rust-safe-safety", &[("src/velocity.rs", &safety)], &[]);
    assert_exact_hard(
        &rejected,
        &[(
            "src/velocity.rs",
            "documentation.public_contract",
            "calculate_velocity",
        )],
    );
}

/// 验证单个孤立汉字不能使英文说明通过中文要求
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
    let baseline = review(
        "chinese-phrase",
        &[("src/internal.rs", internal), ("src/public.rs", public)],
        &[],
    );

    assert!(baseline.findings().iter().any(|finding| {
        finding.path() == "src/internal.rs"
            && finding.rule() == "documentation.summary"
    }));
    assert!(baseline.findings().iter().any(|finding| {
        finding.path() == "src/public.rs"
            && finding.rule() == "documentation.public_contract"
    }));
    for (label, path, source) in [
        (
            "ownership",
            "src/ownership.c",
            "/**\n * 所有权：\n */\nstatic void calculate_velocity(void) {}\n",
        ),
        (
            "rust",
            "src/heading.rs",
            "/// # 示例\nfn calculate_velocity() {}\n",
        ),
        (
            "effect",
            "src/effect.c",
            "/**\n * 效果：\n */\nstatic void calculate_velocity(void) {}\n",
        ),
        (
            "template",
            "src/template.c",
            "/**\n * 模板参数：\n */\nstatic void calculate_velocity(void) {}\n",
        ),
        (
            "python",
            "src/heading.py",
            "def calculate_velocity():\n    \"\"\"\n    Args:\n    \"\"\"\n",
        ),
    ] {
        let review = review(label, &[(path, source)], &[]);
        assert!(has_rule(&review, "documentation.summary"), "{label}");
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

/// 验证文档多写参数触发合同违规
#[test]
fn extra_parameters_are_hard_contract_errors() {
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
    let source = base
        .replace("    Returns:\n", "        value: 额外值\n    Returns:\n");
    let review = review(
        "invalid-public-fields",
        &[("src/fields.py", source.as_str())],
        &[],
    );
    assert!(has_rule(&review, "documentation.public_contract"));
}

/// 验证 Python 文档结束引号必须独占物理行
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
}

/// 验证 Rust 具名可变参数可通过检查，匿名参数仍不完整
#[test]
fn rust_named_variadic_signature_cleans_with_safety_role() {
    let named = concat!(
        "/// 计算合计值\n",
        "///\n",
        "/// # Arguments\n",
        "/// - distance_m：  样本数量\n",
        "/// - distance_mm： 可变数值序列\n",
        "/// # Returns\n",
        "/// - 合计值\n",
        "/// # Errors\n",
        "/// - 无\n",
        "/// # Safety\n",
        "/// - 读取调用方提供的可变缓冲区\n",
        "pub unsafe extern \"C\" fn calculate_totals(\n",
        "    distance_m: usize,\n",
        "    mut distance_mm: ...,\n",
        ") -> f64 {\n",
        "    0.0\n",
        "}\n",
    );
    let sealed =
        review("rust-named-variadic", &[("src/totals.rs", named)], &[]);
    assert_complete_clean(&sealed, "rust-named-variadic");
}

/// 表示一个画像的规范源码与叙述区变异锚点
struct NarrativeProfile {
    path: &'static str,
    source: &'static str,
    anchor: &'static str,
    double_gap: &'static str,
    narrative: &'static str,
    separated: &'static str,
    missing: &'static str,
    heading: &'static str,
    final_entry: &'static str,
    tail: &'static str,
    clean_entry: &'static str,
    punctuated_entry: &'static str,
}

const NARRATIVE_PROFILES: [NarrativeProfile; 4] = [
    NarrativeProfile {
        path: "src/narrative.py",
        source: VALID_PYTHON,
        anchor: "    计算平均速度\n\n    Args:\n",
        double_gap: "    计算平均速度\n\n\n    Args:\n",
        narrative: "    计算平均速度\n\n    本函数按行进距离与持续时间计算平均值。\n    输入不合法时抛出数值错误\n\n    Args:\n",
        separated: "    计算平均速度\n\n    本函数",
        missing: "    计算平均速度\n    本函数",
        heading: "    Args:\n",
        final_entry: "        ValueError: 持续时间不大于零\n    \"\"\"\n",
        tail: "        ValueError: 持续时间不大于零\n        补充叙述说明\n    \"\"\"\n",
        clean_entry: "        float: 平均速度\n",
        punctuated_entry: "        float: 平均速度.\n",
    },
    NarrativeProfile {
        path: "src/narrative.rs",
        source: VALID_RUST,
        anchor: "/// 计算平均速度\n///\n/// # Arguments\n",
        double_gap: "/// 计算平均速度\n///\n///\n/// # Arguments\n",
        narrative: "/// 计算平均速度\n///\n/// 本函数按行进距离与持续时间计算平均值。\n/// 输入不合法时返回错误\n///\n/// # Arguments\n",
        separated: "/// 计算平均速度\n///\n/// 本函数",
        missing: "/// 计算平均速度\n/// 本函数",
        heading: "/// # Arguments\n",
        final_entry: "/// - 持续时间不大于零时返回错误\npub fn",
        tail: "/// - 持续时间不大于零时返回错误\n/// 补充叙述说明\npub fn",
        clean_entry: "/// - 平均速度\n",
        punctuated_entry: "/// - 平均速度.\n",
    },
    NarrativeProfile {
        path: PROCEDURAL_PATH,
        source: VALID_PROCEDURAL,
        anchor: " * 计算平均速度\n *\n * 参数：\n",
        double_gap: " * 计算平均速度\n *\n *\n * 参数：\n",
        narrative: " * 计算平均速度\n *\n * 本函数按行进距离与持续时间计算平均值。\n * 输入不合法时返回错误\n *\n * 参数：\n",
        separated: " * 计算平均速度\n *\n * 本函数",
        missing: " * 计算平均速度\n * 本函数",
        heading: " * 参数：\n",
        final_entry: " * - duration_s不大于零时返回false\n */\n",
        tail: " * - duration_s不大于零时返回false\n * 补充叙述说明\n */\n",
        clean_entry: " * - 计算是否成功\n",
        punctuated_entry: " * - 计算是否成功.\n",
    },
    NarrativeProfile {
        path: OBJECT_ORIENTED_PATH,
        source: VALID_CPP,
        anchor: " * 计算平均速度\n *\n * 参数：\n",
        double_gap: " * 计算平均速度\n *\n *\n * 参数：\n",
        narrative: " * 计算平均速度\n *\n * 本函数按行进距离与持续时间计算平均值。\n * 输入不合法时返回错误\n *\n * 参数：\n",
        separated: " * 计算平均速度\n *\n * 本函数",
        missing: " * 计算平均速度\n * 本函数",
        heading: " * 参数：\n",
        final_entry: " * - duration_s不大于零时抛出std::invalid_argument\n */\n",
        tail: " * - duration_s不大于零时抛出std::invalid_argument\n * 补充叙述说明\n */\n",
        clean_entry: " * - 平均速度\n",
        punctuated_entry: " * - 平均速度.\n",
    },
];

/// 构造包含叙述区的规范源码
fn narrative_source(profile: &NarrativeProfile) -> String {
    (profile.source).replacen(profile.anchor, profile.narrative, 1)
}

/// 验证四语言叙述区仅位于摘要与首个受控标题之间
#[test]
fn bounded_narrative_region_closes_per_profile() {
    let names = ["calculate_velocity"];
    for profile in &NARRATIVE_PROFILES {
        let path = profile.path;
        let hard =
            [(path, "documentation.public_contract", "calculate_velocity")];
        let clean_source = narrative_source(profile);
        let clean =
            review("narrative-clean", &[(path, &clean_source)], &names);
        assert_complete_clean(&clean, path);

        let replace =
            |source: &str, anchor, value| source.replacen(anchor, value, 1);
        let double_gap =
            replace(profile.source, profile.anchor, profile.double_gap);
        let unseparated =
            replace(&clean_source, profile.separated, profile.missing);
        let heading = format!("{0}{0}", profile.heading);
        let duplicated = replace(&clean_source, profile.heading, &heading);
        let tailed = replace(&clean_source, profile.final_entry, profile.tail);
        for (revision, source) in [
            ("narrative-double-gap", double_gap),
            ("narrative-unseparated", unseparated),
            ("narrative-duplicated", duplicated),
            ("narrative-tail", tailed),
        ] {
            let rejected =
                review(revision, &[(path, source.as_str())], &names);
            assert_exact_hard(&rejected, &hard);
        }
    }
}

/// 表示结构化字段条目的填充布局变体
#[derive(Clone, Copy)]
enum FieldLayout {
    /// 最短规范对齐：最长身份之后恰有一个空格
    Canonical,
    /// 分隔符紧邻身份之前多出一个空白
    PreDelimiterSpace,
    /// 每行填充都恰为一个空格
    OneSpace,
    /// 填充末位空格被替换为 Tab
    TabPad,
    /// 字段身份起始列不一致
    Offset,
    /// 分隔符后没有任何填充
    EmptyPad,
}

/// 表示结构化字段使用的语法画像
#[derive(Clone, Copy)]
enum FieldProfile {
    Python,
    Rust,
    Native,
}

/// 按指定格式生成字段条目，区分 `- x：p` 与 `x:p`
fn structured_entries(
    native: bool,
    layout: FieldLayout,
    entries: &[(&str, &str)],
) -> String {
    let target_width = entries
        .iter()
        .map(|(identity, _)| identity.chars().count())
        .max()
        .unwrap_or(0);
    entries
        .iter()
        .enumerate()
        .map(|(index, (identity, description))| {
            let identity_width = identity.chars().count();
            let padding = match layout {
                FieldLayout::Canonical
                | FieldLayout::PreDelimiterSpace
                | FieldLayout::Offset => {
                    " ".repeat(target_width - identity_width + 1)
                }
                FieldLayout::OneSpace => " ".to_owned(),
                FieldLayout::TabPad => {
                    let mut padding =
                        " ".repeat(target_width - identity_width + 1);
                    padding.pop();
                    format!("{padding}\t")
                }
                FieldLayout::EmptyPad => String::new(),
            };
            let left_padding = match (layout, index) {
                (FieldLayout::Offset, 1) => "    ",
                _ => "",
            };
            let identity_text = match layout {
                FieldLayout::PreDelimiterSpace => format!("{identity} "),
                _ => (*identity).to_owned(),
            };
            let (prefix, delimiter) = if native { ("- ", "：") } else { ("", ":") };
            format!(
                "{left_padding}{prefix}{identity_text}{delimiter}{padding}{description}\n"
            )
        })
        .collect()
}

/// 构造指定语言的文档字段布局样例
fn layout_source(profile: FieldProfile, layout: FieldLayout) -> String {
    match profile {
        FieldProfile::Python => {
            let mut source = String::from(concat!(
                "def calculate_velocity(distance_m: float, value: float) -> float:\n",
                "    \"\"\"\n",
                "    计算平均速度\n",
                "\n",
                "    Args:\n",
            ));
            for (label, entries) in [
                ("", &[("distance_m", "行进距离"), ("value", "数值输入")][..]),
                (
                    "    Returns:\n",
                    &[("float", "平均速度"), ("str", "单位文本")][..],
                ),
                (
                    "    Raises:\n",
                    &[
                        ("ValueError", "输入不合法"),
                        ("TimeoutError", "采样超时"),
                    ][..],
                ),
            ] {
                source.push_str(label);
                for line in structured_entries(false, layout, entries).lines()
                {
                    source.push_str(&format!("        {line}\n"));
                }
            }
            source.push_str("    \"\"\"\n    return distance_m / value\n");
            source
        }
        FieldProfile::Rust => {
            let mut source = String::from(concat!(
                "/// 计算平均速度\n",
                "///\n",
                "/// # Arguments\n",
            ));
            for line in structured_entries(
                true,
                layout,
                &[("distance_m", "行进距离"), ("sample_count", "样本数量")],
            )
            .lines()
            {
                source.push_str(&format!("/// {line}\n"));
            }
            source.push_str(concat!(
                "/// # Returns\n",
                "/// - 平均速度\n",
                "/// # Errors\n",
                "/// - 无\n",
                "pub fn calculate_velocity(\n",
                "    distance_m: f64,\n",
                "    sample_count: f64,\n",
                ") -> Result<f64, String> {\n",
                "    Ok(distance_m / sample_count)\n",
                "}\n",
            ));
            source
        }
        FieldProfile::Native => {
            let mut source =
                String::from("/**\n * 计算平均速度\n *\n * 参数：\n");
            for line in structured_entries(
                true,
                layout,
                &[
                    ("distance_m", "行进距离"),
                    ("duration_s", "持续时间"),
                    ("velocity_m_per_s", "平均速度输出位置"),
                ],
            )
            .lines()
            {
                source.push_str(&format!(" * {line}\n"));
            }
            source.push_str(concat!(
                " * 返回：\n",
                " * - 计算是否成功\n",
                " * 错误：\n",
                " * - duration_s不大于零时返回false\n",
                " */\n",
                "bool calculate_velocity(\n",
                "    double distance_m,\n",
                "    double duration_s,\n",
                "    double *velocity_m_per_s\n",
                ");\n",
            ));
            source
        }
    }
}

/// 验证最短空格对齐通过，各类字段布局缺陷被拒绝
#[test]
fn structured_field_layouts_are_exact_or_hard() {
    let names = ["calculate_velocity"];
    for (path, profile) in [
        ("src/layout.py", FieldProfile::Python),
        ("src/layout.rs", FieldProfile::Rust),
        (PROCEDURAL_PATH, FieldProfile::Native),
        (OBJECT_ORIENTED_PATH, FieldProfile::Native),
    ] {
        let source = layout_source(profile, FieldLayout::Canonical);
        let canonical = review("layout-canonical", &[(path, &source)], &names);
        assert_complete_clean(&canonical, path);
        for layout in [
            FieldLayout::PreDelimiterSpace,
            FieldLayout::OneSpace,
            FieldLayout::TabPad,
            FieldLayout::Offset,
            FieldLayout::EmptyPad,
        ] {
            let source = layout_source(profile, layout);
            let defective =
                review("layout-defect", &[(path, &source)], &names);
            assert!(
                has_rule(&defective, "documentation.public_contract"),
                "{path}: {:#?}",
                defective.findings()
            );
        }
    }
    // 单条目也检查对齐：一空格通过，零空格和双空格违规
    for (padding, clean) in [(" ", true), ("", false), ("  ", false)] {
        let source = format!(
            concat!(
                "def calculate_velocity(distance_m: float) -> float:\n",
                "    \"\"\"\n    计算平均速度\n\n",
                "    Args:\n        distance_m:{padding}行进距离\n",
                "    Returns:\n        float: 平均速度\n",
                "    Raises:\n        ValueError: 持续时间不大于零\n",
                "    \"\"\"\n    return distance_m\n",
            ),
            padding = padding
        );
        let sealed = review(
            "layout-single",
            &[("src/single.py", source.as_str())],
            &names,
        );
        assert_eq!(sealed.completion(), Completion::Complete);
        assert_eq!(sealed.findings().is_empty(), clean, "{padding:?}");
    }
    for (path, source) in [
        ("src/wrong-args.py", VALID_PYTHON.replacen("        distance_m: 行进距离\n        duration_s: 持续时间", "        - 不返回", 1)),
        ("src/wrong-failures.py", VALID_PYTHON.replacen("        ValueError: 持续时间不大于零", "        - 不返回", 1)),
        ("src/wrong-args.rs", VALID_RUST.replacen("/// - distance_m： 行进距离\n/// - duration_s： 持续时间", "/// - 不返回", 1)),
        (PROCEDURAL_PATH, VALID_PROCEDURAL.replacen(" * - distance_m：       行进距离\n * - duration_s：       持续时间\n * - velocity_m_per_s： 平均速度输出位置", " * - 不返回", 1)),
        (OBJECT_ORIENTED_PATH, VALID_CPP.replacen(" * - distance_m： 行进距离\n * - duration_s： 持续时间", " * - 不返回", 1)),
        ("src/wrong-return.rs", VALID_RUST.replacen("/// - 平均速度\n", "/// - value： 平均速度\n", 1)),
        (PROCEDURAL_PATH, VALID_PROCEDURAL.replacen(" * - 计算是否成功\n", " * - value： 计算是否成功\n", 1)),
        (OBJECT_ORIENTED_PATH, VALID_CPP.replacen(" * - 平均速度\n", " * - value： 平均速度\n", 1)),
    ] {
        let sealed = review("wrong-role-never", &[(path, source.as_str())], &names);
        assert!(has_rule(&sealed, "documentation.public_contract"), "{path}");
    }
}

/// 验证四语言公开方法要求完整合同，内部方法只需摘要
#[test]
fn public_and_internal_method_tiers_close_per_profile() {
    let cases = [
        (
            "src/method.py",
            &[][..],
            "_calculate_totals",
            concat!(
                "class Velocity:\n    \"\"\"\n    表示速度类型\n    \"\"\"\n\n    def calculate_velocity(self) -> None:\n        \"\"\"\n        计算平均速度\n",
                "\n        Args:\n            无\n        Returns:\n            无\n        Raises:\n            无\n        \"\"\"\n        return None\n\n    def _calculate_totals(self) -> None:\n",
                "        \"\"\"\n        计算汇总结果\n        \"\"\"\n        return None\n",
            ),
            "\n\n        Args:\n            无\n        Returns:\n            无\n        Raises:\n            无",
            "        \"\"\"\n        计算汇总结果\n        \"\"\"\n",
        ),
        (
            "src/method.rs",
            &[][..],
            "calculate_totals",
            concat!(
                "struct Velocity;\n\nimpl Velocity {\n    /// 计算平均速度\n    ///\n    /// # Arguments\n    /// - 无\n",
                "    /// # Returns\n    /// - 无\n    /// # Errors\n    /// - 无\n    pub fn calculate_velocity(&self) {}\n\n",
                "    /// 计算汇总结果\n    fn calculate_totals(&self) {}\n}\n",
            ),
            "\n    ///\n    /// # Arguments\n    /// - 无\n    /// # Returns\n    /// - 无\n    /// # Errors\n    /// - 无",
            "    /// 计算汇总结果\n",
        ),
        (
            PROCEDURAL_PATH,
            &["calculate_velocity"][..],
            "calculate_totals",
            concat!(
                "/**\n * 计算平均速度\n *\n * 参数：\n * - 无\n * 返回：\n * - 无\n * 错误：\n * - 无\n */\nvoid calculate_velocity(void);\n\n",
                "/**\n * 计算汇总结果\n */\nstatic void calculate_totals(void) {}\n",
            ),
            " *\n * 参数：\n * - 无\n * 返回：\n * - 无\n * 错误：\n * - 无\n",
            "/**\n * 计算汇总结果\n */\n",
        ),
        (
            OBJECT_ORIENTED_PATH,
            &["calculate_velocity"][..],
            "calculate_totals",
            concat!(
                "/**\n * 表示速度类型\n */\nclass Velocity {\npublic:\n    /**\n     * 计算平均速度\n",
                "     *\n     * 参数：\n     * - 无\n     * 返回：\n     * - 无\n     * 错误：\n     * - 无\n     */\n    void calculate_velocity();\n\nprivate:\n",
                "    /**\n     * 计算汇总结果\n     */\n    void calculate_totals();\n};\n",
            ),
            "     *\n     * 参数：\n     * - 无\n     * 返回：\n     * - 无\n     * 错误：\n     * - 无\n",
            "    /**\n     * 计算汇总结果\n     */\n",
        ),
    ];
    for (path, public_names, internal_name, baseline, roles, carrier) in cases
    {
        let clean = review("method-clean", &[(path, baseline)], public_names);
        assert_complete_clean(&clean, path);

        let summary_only = baseline.replacen(roles, "", 1);
        let missing_carrier = baseline.replacen(carrier, "", 1);
        let public_name = "calculate_velocity";
        for (source, rule, subject) in [
            (summary_only, "documentation.public_contract", public_name),
            (missing_carrier, "documentation.carrier", internal_name),
        ] {
            assert_ne!(source, baseline, "{path}: mutation anchor");
            let sealed =
                review("method-negative", &[(path, &source)], public_names);
            assert_exact_hard(&sealed, &[(path, rule, subject)]);
        }
    }
}

/// 验证各语言只在规定的文档位置检查句号
#[test]
fn sentence_punctuation_is_owned_per_profile() {
    for profile in &NARRATIVE_PROFILES {
        let path = profile.path;
        let base = narrative_source(profile).replacen(
            profile.clean_entry,
            profile.punctuated_entry,
            1,
        );
        let sealed = review(
            "punctuation",
            &[(path, base.as_str())],
            &["calculate_velocity"],
        );
        assert!(has_rule(&sealed, "documentation.punctuation"), "{path}");
    }
}

/// 验证从真实项目提取的 Python 样例不能绕过文档检查
#[test]
fn target_derived_python_cases_cannot_evade_documentation_rules() {
    let fixture: serde_json::Value = serde_json::from_str(include_str!(
        "fixtures/python_target_cases.json"
    ))
    .expect("target fixture must be valid JSON");
    for case in fixture["cases"].as_array().expect("cases must be an array") {
        let identity = case["id"].as_str().expect("case id must be text");
        let source = case["source"].as_str().expect("source must be text");
        let path = format!("target_cases/{identity}.py");
        let review = review(identity, &[(&path, source)], &[]);
        let expected_completion = match case["expected_completion"].as_str() {
            Some("incomplete") => Completion::Incomplete,
            _ => Completion::Complete,
        };
        assert_eq!(review.completion(), expected_completion, "{identity}");
        let subject = case["expected_subject"].as_str().unwrap();
        let expected = case["expected_rule"]
            .as_str()
            .map(|rule| (rule, FindingGrade::HardViolation));
        assert_eq!(
            review
                .findings()
                .iter()
                .find(|item| {
                    item.subject() == subject
                        && item.rule().starts_with("documentation.")
                })
                .map(|finding| (finding.rule(), finding.grade())),
            expected,
            "{identity}"
        );
    }
}
