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

const PYTHON_PATH: &str = "src/calculate_totals.py";
const RUST_PATH: &str = "src/calculate_totals.rs";
const PROCEDURAL_PATH: &str = "include/calculate_totals.h";
const CPP_PATH: &str = "include/calculate_totals.hpp";

/// 表示声明返回面证据的精确终态
#[derive(Clone, Copy)]
enum Outcome {
    /// 检查完整且没有问题
    Clean,
    /// 检查完整且仅有一条指定硬违规
    Hard(&'static str),
    /// Incomplete 且 Documentation 族 Blocked
    Blocked,
}

/// 创建支持四语言并可补充公开函数名单的测试审查器
fn reviewer(extra_public: &[(&str, &[&str])]) -> WorkspaceReviewer {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../../docs/fixtures/core/authority.json"
    ))
    .unwrap();
    for (path, names) in extra_public {
        authority["public_callables"][path] =
            serde_json::json!(names.to_vec());
    }
    if authority["public_callables"].get(PROCEDURAL_PATH).is_none() {
        authority["public_callables"][PROCEDURAL_PATH] =
            serde_json::json!(["calculate_totals"]);
    }
    if authority["public_callables"].get(CPP_PATH).is_none() {
        authority["public_callables"][CPP_PATH] =
            serde_json::json!(["calculate_totals"]);
    }
    authority["header_languages"][PROCEDURAL_PATH] = serde_json::json!("c");
    authority["token_vocabulary"]
        .as_array_mut()
        .unwrap()
        .extend(
            [
                "macro", "my", "result", "sample", "totals", "value", "width",
            ]
            .map(serde_json::Value::from),
        );
    compile_value(&authority).unwrap()
}

/// 审查内存源码并返回终态
fn review(path: &str, source: &str) -> ReviewTerminal {
    review_sources(&reviewer(&[]), "return-shape-contract", &[(path, source)])
}

/// 断言终态与期望精确一致
fn assert_outcome(label: &str, terminal: ReviewTerminal, expected: Outcome) {
    let ReviewTerminal::Sealed(sealed) = terminal else {
        panic!("{label} must seal: {terminal:#?}")
    };
    match expected {
        Outcome::Clean => {
            assert_eq!(sealed.completion(), Completion::Complete, "{label}");
            assert!(
                sealed.findings().is_empty(),
                "{label}: {:#?}",
                sealed.findings()
            );
        }
        Outcome::Hard(rule) => {
            assert_eq!(sealed.completion(), Completion::Complete);
            let [finding] = sealed.findings() else {
                panic!("{label} expects exactly one finding")
            };
            assert_eq!(finding.rule(), rule, "{label}");
            assert_eq!(finding.grade(), csu::FindingGrade::HardViolation);
        }
        Outcome::Blocked => {
            assert_eq!(sealed.completion(), Completion::Incomplete, "{label}");
            assert!(
                sealed.findings().is_empty(),
                "{label}: {:#?}",
                sealed.findings()
            );
            let reason = documentation_block_reason(&sealed);
            assert!(
                reason.contains("[return]"),
                "{label} must raise the return category: {reason}"
            );
        }
    }
}

/// 提取封存结果中文档检查受阻的原因
fn documentation_block_reason(sealed: &SealedReview) -> String {
    sealed.coverage().files()[0]
        .families()
        .iter()
        .find(|(family, _)| *family == FactFamily::Documentation)
        .and_then(|(_, state)| match state {
            FactFamilyState::Blocked(reason) => Some(reason.clone()),
            _ => None,
        })
        .expect("documentation family must be blocked")
}

/// 构造带指定返回注解和返回说明的 Python 公开函数
fn python_source(return_surface: &str, returns_entry: &str) -> String {
    let annotation = if return_surface.is_empty() {
        String::new()
    } else {
        format!(" -> {return_surface}")
    };
    format!(
        concat!(
            "def calculate_totals(duration_s: float){annotation}:\n",
            "    \"\"\"\n",
            "    计算汇总结果\n",
            "\n",
            "    Args:\n",
            "        duration_s: 持续时间\n",
            "    Returns:\n",
            "{returns_entry}",
            "    Raises:\n",
            "        无\n",
            "    \"\"\"\n",
            "    return duration_s\n",
        ),
        annotation = annotation,
        returns_entry = returns_entry,
    )
}

/// 构造带指定返回类型、函数体和返回说明的 Rust 公开函数
fn rust_source(return_type: &str, body: &str, returns_entry: &str) -> String {
    let surface = if return_type.is_empty() {
        String::new()
    } else {
        format!(" -> {return_type}")
    };
    format!(
        concat!(
            "/// 计算汇总结果\n",
            "///\n",
            "/// # Arguments\n",
            "/// - duration_s： 持续时间\n",
            "/// # Returns\n",
            "{returns_entry}",
            "/// # Errors\n",
            "/// - 无\n",
            "pub fn calculate_totals(duration_s: f64){surface} {{\n",
            "{body}",
            "}}\n",
        ),
        returns_entry = returns_entry,
        surface = surface,
        body = body,
    )
}

/// 构造带指定返回声明前缀和返回说明的 C/C++ 公开函数
fn native_source(
    path: &str,
    return_prefix: &str,
    returns_entry: &str,
) -> String {
    let parameter = if path == PROCEDURAL_PATH {
        "(void)"
    } else {
        "()"
    };
    format!(
        concat!(
            "/**\n",
            " * 计算汇总结果\n",
            " *\n",
            " * 参数：\n",
            " * - 无\n",
            " * 返回：\n",
            "{returns_entry}",
            " * 错误：\n",
            " * - 无\n",
            " */\n",
            "{return_prefix}calculate_totals{parameter};\n",
        ),
        returns_entry = returns_entry,
        return_prefix = return_prefix,
        parameter = parameter,
    )
}

/// 验证 Python 根据直接返回注解判断返回文档要求
#[test]
fn python_declared_return_surfaces_close_exact_shapes() {
    let cases = [
        (
            "list[float]",
            "        list[float]: 汇总结果序列\n",
            Outcome::Clean,
        ),
        (
            "dict[str, int]",
            "        dict[str, int]: 汇总结果映射\n",
            Outcome::Clean,
        ),
        ("MyAlias", "        MyAlias: 汇总别名结果\n", Outcome::Clean),
        (
            "MyAlias",
            "        无\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "None",
            "        value: 数值描述\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        ("None", "        无\n", Outcome::Clean),
        ("", "        无\n", Outcome::Blocked),
        (
            "NoReturn",
            "        NoReturn: 永不正常返回\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "NoReturn",
            "        无\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "typing.NoReturn",
            "        typing.NoReturn: 永不正常返回\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "Never",
            "        Never: 永不正常返回\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "typing.Never",
            "        typing.Never: 永不正常返回\n",
            Outcome::Hard("documentation.public_contract"),
        ),
    ];
    for (surface, entry, expected) in cases {
        assert_outcome(
            "python_return_shape",
            review(PYTHON_PATH, &python_source(surface, entry)),
            expected,
        );
    }
}

/// 验证 Rust 根据直接返回类型判断返回文档要求
#[test]
fn rust_declared_return_surfaces_close_exact_shapes() {
    let cases = [
        ("", "    ()\n", "/// - 无\n", Outcome::Clean),
        ("()", "    ()\n", "/// - 无\n", Outcome::Clean),
        (
            "Vec<f64>",
            "    Vec::new()\n",
            "/// - 汇总结果序列\n",
            Outcome::Clean,
        ),
        (
            "Vec<f64>",
            "    Vec::new()\n",
            "/// - 无\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "()",
            "    ()\n",
            "/// - 汇总结果值\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "answer!()",
            "    ()\n",
            "/// - 汇总结果值\n",
            Outcome::Blocked,
        ),
        (
            "!",
            "    panic!()\n",
            "/// - 无\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        ("!", "    panic!()\n", "/// - 不返回\n", Outcome::Clean),
    ];
    for (surface, body, entry, expected) in cases {
        assert_outcome(
            "rust_return_shape",
            review(RUST_PATH, &rust_source(surface, body, entry)),
            expected,
        );
    }
}

/// 验证 C 根据直接返回声明判断返回文档要求
#[test]
fn procedural_declared_return_surfaces_close_exact_shapes() {
    let cases = [
        (
            "_Noreturn void ",
            " * - 无\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "[[noreturn]] int ",
            " * - 无\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        ("MyResult ", " * - 汇总结果值\n", Outcome::Clean),
        (
            "MyResult ",
            " * - 无\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "void ",
            " * - 汇总结果值\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        ("unsigned width_t ", " * - 汇总结果值\n", Outcome::Clean),
        ("void *", " * - 汇总结果值\n", Outcome::Clean),
        ("noreturn void ", " * - 无\n", Outcome::Clean),
    ];
    for (surface, entry, expected) in cases {
        assert_outcome(
            "procedural_return_shape",
            review(
                PROCEDURAL_PATH,
                &native_source(PROCEDURAL_PATH, surface, entry),
            ),
            expected,
        );
    }
    // struct 返回面按 named/tagged 声明判 Value：类型位置的 struct_specifier
    // 显式公开名单同时证明未列出的 tag 是内部主体，因此不再留下 tier 未知
    let terminal = review(
        PROCEDURAL_PATH,
        &native_source(
            PROCEDURAL_PATH,
            "struct velocity ",
            " * - 汇总结果值\n",
        ),
    );
    let ReviewTerminal::Sealed(sealed) = terminal else {
        panic!("struct surface must seal: {terminal:#?}")
    };
    assert_eq!(sealed.completion(), Completion::Complete);
    let [finding] = sealed.findings() else {
        panic!("struct surface expects exactly the tag carrier finding");
    };
    assert_eq!(finding.rule(), "documentation.carrier");
    assert_eq!(finding.subject(), "velocity");
}

/// 验证 C++ 根据直接返回声明判断返回文档要求
#[test]
fn cpp_declared_return_surfaces_close_exact_shapes() {
    let cases = [
        (
            "auto -> void",
            "auto calculate_totals() -> void;\n",
            " * - 无\n",
            Outcome::Clean,
        ),
        (
            "auto -> int",
            "auto calculate_totals() -> int;\n",
            " * - 汇总结果值\n",
            Outcome::Clean,
        ),
        (
            "auto -> int with empty marker",
            "auto calculate_totals() -> int;\n",
            " * - 无\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "auto -> void with value marker",
            "auto calculate_totals() -> void;\n",
            " * - 汇总结果值\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "undeduced auto",
            "auto calculate_totals();\n",
            " * - 汇总结果值\n",
            Outcome::Blocked,
        ),
        (
            "argumented attribute",
            "[[noreturn(1)]] void calculate_totals();\n",
            " * - 无\n",
            Outcome::Clean,
        ),
        (
            "undeduced decltype",
            "decltype(auto) calculate_totals();\n",
            " * - 汇总结果值\n",
            Outcome::Blocked,
        ),
        (
            "attributed never",
            "[[noreturn]] void calculate_totals();\n",
            " * - 无\n",
            Outcome::Hard("documentation.public_contract"),
        ),
        (
            "namespaced attribute",
            "[[vendor::noreturn]] void calculate_totals();\n",
            " * - 无\n",
            Outcome::Clean,
        ),
    ];
    for (label, declaration, entry, expected) in cases {
        let source = native_source(CPP_PATH, "", entry).replacen(
            "calculate_totals();\n",
            declaration,
            1,
        );
        assert_outcome(label, review(CPP_PATH, &source), expected);
    }
}

/// 验证 C++ 不解析返回类型别名，按具名类型判定有返回值
#[test]
fn cpp_alias_return_surface_is_value_when_alias_is_unresolved() {
    for (entry, expected) in [
        (" * - 汇总结果值\n", Outcome::Clean),
        (" * - 无\n", Outcome::Hard("documentation.public_contract")),
    ] {
        let source = format!(
            "using SampleValue = void;\n{}",
            native_source(CPP_PATH, "SampleValue ", entry)
        );
        assert_outcome(
            "cpp_alias_surface",
            review(CPP_PATH, &source),
            expected,
        );
    }
}

/// 验证 C++ 构造函数按无返回值检查文档
#[test]
fn cpp_constructor_surface_closes_no_value() {
    let reviewer = reviewer(&[(CPP_PATH, &["Velocity", "calculate_totals"])]);
    let constructor_source = concat!(
        "/**\n",
        " * 表示速度值\n",
        " */\n",
        "class Velocity {\n",
        "public:\n",
        "    /**\n",
        "     * 初始化速度值\n",
        "     *\n",
        "     * 参数：\n",
        "     * - 无\n",
        "     * 返回：\n",
        "     * - 无\n",
        "     * 错误：\n",
        "     * - 无\n",
        "     * 效果：\n",
        "     * - 初始化速度值\n",
        "     */\n",
        "    Velocity();\n",
        "};\n",
    );
    let terminal = review_sources(
        &reviewer,
        "cpp-constructor-surface",
        &[(CPP_PATH, constructor_source)],
    );
    // 歧义判断只统计具名函数，不把同名类算作函数
    // 构造函数按无返回值检查，不要求返回值说明
    assert_outcome("cpp_constructor_no_value", terminal, Outcome::Clean);
}

/// 验证 C++ 转换函数的具名目标类型按有返回值检查文档
#[test]
fn cpp_conversion_operator_target_surface_is_value() {
    let reviewer = reviewer(&[(CPP_PATH, &["Velocity", "operator bool()"])]);
    let source = concat!(
        "/**\n",
        " * 表示速度值\n",
        " */\n",
        "class Velocity {\n",
        "public:\n",
        "    /**\n",
        "     * 转换为布尔状态\n",
        "     *\n",
        "     * 参数：\n",
        "     * - 无\n",
        "     * 返回：\n",
        "     * - 是否处于有效状态\n",
        "     * 错误：\n",
        "     * - 无\n",
        "     */\n",
        "    operator bool() { return true; }\n",
        "};\n",
    );
    let terminal = review_sources(
        &reviewer,
        "cpp-operator-target",
        &[(CPP_PATH, source)],
    );
    assert_outcome("cpp_operator_target", terminal, Outcome::Clean);
}
