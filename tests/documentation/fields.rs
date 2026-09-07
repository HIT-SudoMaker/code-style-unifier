use super::OBJECT_ORIENTED_PATH;
use super::PROCEDURAL_PATH;
use super::VALID_CPP;
use super::VALID_PROCEDURAL;
use super::VALID_PYTHON;
use super::VALID_RUST;
use super::assert_complete_clean;
use super::assert_exact_hard;
use super::has_rule;
use super::review;
use csu::Completion;
use csu::FindingGrade;

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
        "../fixtures/python_target_cases.json"
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
