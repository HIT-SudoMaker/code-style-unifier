use super::VALID_PYTHON;
use super::VALID_RUST;
use super::assert_complete_clean;
use super::assert_exact_hard;
use super::has_rule;
use super::review;

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

/// 验证安全函数的 Safety 禁令不依赖公开层级且不误读代码示例
#[test]
fn rust_safe_internal_documentation_rejects_real_safety_sections() {
    let source = "/// 计算数值\n///\n/// # Safety\n/// - 调用条件\nfn calculate_velocity() {}\n";
    assert_exact_hard(
        &review("internal-safe", &[("src/value.rs", source)], &[]),
        &[(
            "src/value.rs",
            "documentation.public_contract",
            "calculate_velocity",
        )],
    );
    let unsafe_source = source
        .replace("fn calculate_velocity", "unsafe fn calculate_velocity");
    assert_complete_clean(
        &review("internal-unsafe", &[("src/value.rs", &unsafe_source)], &[]),
        "internal-unsafe",
    );
    for example in [
        "/// ```text\n/// # Safety\n/// ```\n",
        "/// ~~~~text\n/// # Safety\n/// ~~~~\n",
        "///     # Safety\n",
    ] {
        let source = format!(
            "/// 计算数值\n///\n{example}fn calculate_velocity() {{}}\n"
        );
        assert_complete_clean(
            &review("safety-example", &[("src/value.rs", &source)], &[]),
            example,
        );
    }
}

/// 验证安全禁令和必要安全契约共享真实标题位置但保留完整正文约束
#[test]
fn rust_safety_obligations_use_real_markdown_headings() {
    for (body, unsafe_complete, real_safety) in [
        ("///     # Safety\n///     - 调用条件\n", false, false),
        ("/// ```rust\n/// # Safety\n/// - 调用条件\n", false, false),
        (
            "/// ```rust\n///     ```\n/// # Safety\n/// - 调用条件\n",
            false,
            false,
        ),
        ("/// ```r`ust\n/// # Safety\n/// - 调用条件\n", true, true),
        ("/// # Safety\n/// - 调用条件\n", true, true),
        ("/// # Safety\n///     - 调用条件\n", false, true),
        (
            "/// ```text\n/// # Safety\n/// - 示例内容\n/// ```\n/// # Safety\n/// - 调用条件\n",
            true,
            true,
        ),
        (
            "/// ```text\n/// 示例内容\n///   ```\n/// # Safety\n/// - 调用条件\n",
            true,
            true,
        ),
        (
            "/// # Safety\n/// - 调用条件\n/// ```text\n/// # Errors\n/// - 无\n/// ```\n",
            false,
            true,
        ),
    ] {
        for unsafe_callable in [false, true] {
            let modifier = if unsafe_callable { "unsafe " } else { "" };
            let source = format!(
                "/// 计算数值\n///\n{body}{modifier}fn calculate_velocity() {{}}\n"
            );
            let result = review(
                "safety-heading-visibility",
                &[("src/value.rs", &source)],
                &[],
            );
            let rule = if unsafe_callable && !unsafe_complete {
                Some("documentation.safety")
            } else if !unsafe_callable && real_safety {
                Some("documentation.public_contract")
            } else {
                None
            };
            if let Some(rule) = rule {
                assert_exact_hard(
                    &result,
                    &[("src/value.rs", rule, "calculate_velocity")],
                );
            } else {
                assert_complete_clean(&result, &source);
            }
        }
    }
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
