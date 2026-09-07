use super::OBJECT_ORIENTED_PATH;
use super::PROCEDURAL_PATH;
use super::VALID_CPP;
use super::VALID_PROCEDURAL;
use super::VALID_RUST;
use super::assert_complete_clean;
use super::assert_exact_hard;
use super::has_rule;
use super::review;
use csu::Completion;

/// 验证 Python 首语句忽略模块注释但不跳过可执行语句
#[test]
fn python_module_documentation_ignores_leading_comment_trivia() {
    for (prefix, expected) in [
        ("", true),
        ("# 模块说明\n", true),
        ("#!/usr/bin/env python\n# 编码说明\n\n", true),
        ("value = 1\n# 模块说明\n", false),
    ] {
        let source = format!("{prefix}\"\"\"\n模块文档\n\"\"\"\n");
        let result =
            review("module-trivia", &[("src/value.py", &source)], &[]);
        assert_eq!(result.completion(), Completion::Complete);
        assert_eq!(
            result.findings().iter().any(|finding| {
                finding.rule() == "documentation.carrier"
                    && finding.subject() == "<module>"
            }),
            expected,
            "{source}"
        );
    }
    let source = "def _value():\n    # 说明注释\n    \"\"\"\n    计算数值\n    \"\"\"\n    pass\n";
    assert_complete_clean(
        &review("callable-trivia", &[("src/value.py", source)], &[]),
        "callable-trivia",
    );
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

/// 验证 Rust 原生字符串字面量和非字面量载体保持区别
#[test]
fn rust_documentation_attributes_decode_native_text_literals() {
    for attribute in [
        "#[doc = \"计算数值\"]",
        "#[doc = r\"计算数值\"]",
        "#[doc = r###\"计算数值\"###]",
        "#[doc = \"\\u{8ba1}\\u{7b97}数值\"]",
        "#[doc = \"计算数值\\x20\"]",
        "#[doc = \"计算\\\n    数值\"]",
        "#[doc = \"计算数值\\n\"]",
    ] {
        let source = format!("{attribute}\nfn calculate_velocity() {{}}\n");
        assert_complete_clean(
            &review("native-doc-literal", &[("src/value.rs", &source)], &[]),
            attribute,
        );
    }
    for attribute in [
        "#[doc = include_str!(\"missing.md\")]",
        "#[doc = b\"text\"]",
    ] {
        let source = format!(
            "/// 计算数值\n{attribute}\nfn calculate_velocity() {{}}\n"
        );
        let result =
            review("nonliteral-doc", &[("src/value.rs", &source)], &[]);
        assert_eq!(result.completion(), Completion::Incomplete, "{attribute}");
        assert!(!has_rule(&result, "documentation.carrier"), "{attribute}");
    }
}

/// 验证 Rust 附属文档片段按源码顺序合并且不跨声明借用
#[test]
fn rust_documentation_fragments_keep_source_order_and_attachment() {
    for prefix in [
        "/// 计算数值\n#[doc = \"\"]\n",
        "#[doc = \"计算数值\"]\n///\n",
        "/** 计算数值 */\n#[doc = \"\"]\n",
        "/// 计算数值\n#[inline]\n#[doc = \"\"]\n/// 补充说明\n",
        "/// 计算数值\n// 附着说明\n",
        "#[doc = \"计算数值\"]\n/* 附着说明 */\n",
    ] {
        let source = format!("{prefix}fn calculate_velocity() {{}}\n");
        assert_complete_clean(
            &review("mixed-rustdoc", &[("src/value.rs", &source)], &[]),
            prefix,
        );
    }
    let source = VALID_RUST.replacen(
        "/// 计算平均速度\n",
        "#[doc = \"计算平均速度\"]\n",
        1,
    );
    assert_complete_clean(
        &review("mixed-public-rustdoc", &[("src/value.rs", &source)], &[]),
        "mixed-public-rustdoc",
    );
    let source = "/// 计算数值\nfn value() {}\n#[doc = \"\"]\nfn calculate_velocity() {}\n";
    assert_exact_hard(
        &review("separate-rustdoc", &[("src/value.rs", source)], &[]),
        &[(
            "src/value.rs",
            "documentation.summary",
            "calculate_velocity",
        )],
    );
    let source = "//! 计算数值\nfn calculate_velocity() {}\n";
    assert_exact_hard(
        &review("inner-rustdoc", &[("src/value.rs", source)], &[]),
        &[(
            "src/value.rs",
            "documentation.carrier",
            "calculate_velocity",
        )],
    );
}

/// 验证普通注释不能替代文档且内层文档隔断外层归属
#[test]
fn rust_documentation_trivia_cannot_supply_or_reassign_carriers() {
    for prefix in [
        "// 普通说明\n",
        "/* 普通说明 */\n",
        "//// 普通说明\n",
        "/// 前方摘要\n//! 内层文档\n",
        "/// 前方摘要\n/*! 内层文档 */\n",
    ] {
        let source = format!("{prefix}fn calculate_velocity() {{}}\n");
        assert_exact_hard(
            &review("rustdoc-trivia-owner", &[("src/value.rs", &source)], &[]),
            &[(
                "src/value.rs",
                "documentation.carrier",
                "calculate_velocity",
            )],
        );
    }
}

/// 验证原生参数和模板列表中的普通注释不改变文档事实
#[test]
fn native_parameter_comments_keep_documentation_facts() {
    for (path, source) in [
        ("src/parameters.rs", VALID_RUST.to_owned()),
        (PROCEDURAL_PATH, VALID_PROCEDURAL.to_owned()),
        (OBJECT_ORIENTED_PATH, VALID_CPP.replace("calculate_velocity(double distance_m, double duration_s)", "calculate_velocity(\n    double distance_m,\n    double duration_s\n)")),
    ] {
        let reviewed = review("comment-control", &[(path, &source)], &["calculate_velocity"]);
        assert_complete_clean(&reviewed, path);
        let marker = if path.ends_with(".rs") { "    distance_m:" } else { "    double distance_m" };
        for comment in ["    /* 输入距离 */\n", "    // 输入距离\n"] {
            let changed = source.replacen(marker, &format!("{comment}{marker}"), 1);
            assert_ne!(source, changed);
            let reviewed = review("parameter-comment", &[(path, &changed)], &["calculate_velocity"]);
            assert_complete_clean(&reviewed, path);
        }
    }
}

/// 验证参数列表中的独立注释不阻塞公开文档事实
#[test]
fn python_parameter_comments_keep_documentation_completeness() {
    let source = "def calculate_velocity(\n    # 参数说明\n    distance_m: float,\n    *,\n    duration_s: float,\n) -> float:\n    \"\"\"\n    计算速度\n\n    Args:\n        distance_m: 输入距离\n        duration_s: 输入时间\n\n    Returns:\n        velocity_m_per_s: 输出速度\n\n    Raises:\n        无\n    \"\"\"\n    return distance_m / duration_s\n";
    let review =
        review("parameter-comment", &[("src/parameters.py", source)], &[]);
    assert_complete_clean(&review, "parameter-comment");
    let changed = source.replace(
        "def calculate_velocity(\n",
        "def calculate_velocity(  # 参数说明\n",
    );
    let reviewed = self::review(
        "parameter-inline-comment",
        &[("src/parameters.py", &changed)],
        &[],
    );
    assert_eq!(reviewed.completion(), Completion::Complete);
    assert!(has_rule(&reviewed, "source.trailing_comment"));
    let changed = source.replace("        duration_s: 输入时间\n", "");
    let reviewed = self::review(
        "parameter-missing-field",
        &[("src/parameters.py", &changed)],
        &[],
    );
    assert_eq!(reviewed.completion(), Completion::Complete);
    assert!(has_rule(&reviewed, "documentation.public_contract"));
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
