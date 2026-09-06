use csu::Completion;
use csu::Disposition;
use csu::FactFamily;
use csu::FactFamilyState;
use csu::ReviewTerminal;
use csu::WorkspaceReviewer;

#[path = "../review_fixture/mod.rs"]
mod review_fixture;

use review_fixture::compile_value;
use review_fixture::review_sources;

const PATH: &str = "api/velocity_roles.hpp";

/// 创建测试审查器
fn reviewer(public_callables: &[&str]) -> WorkspaceReviewer {
    reviewer_for_path(public_callables, PATH)
}

/// 为指定原生源码设置公开归属
fn reviewer_for_path(
    public_callables: &[&str],
    path: &str,
) -> WorkspaceReviewer {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../../docs/fixtures/core/authority.json"
    ))
    .unwrap();
    authority["public_callables"][path] = serde_json::json!(public_callables);
    authority["token_vocabulary"]
        .as_array_mut()
        .unwrap()
        .extend(
            [
                "calculator",
                "count",
                "input",
                "left",
                "pack",
                "right",
                "sample",
                "type",
                "value",
            ]
            .map(serde_json::Value::from),
        );
    compile_value(&authority).unwrap()
}

/// 审查内存源码并返回封存终态
fn review(source: &str, public_callables: &[&str]) -> ReviewTerminal {
    review_sources(
        &reviewer(public_callables),
        "cpp-structural-documentation-roles",
        &[(PATH, source)],
    )
}

/// 判断审查是否包含公开文档合同违规
fn has_public_contract_finding(terminal: &ReviewTerminal) -> bool {
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("documentation judgment must seal: {terminal:#?}");
    };
    review
        .findings()
        .iter()
        .any(|finding| finding.rule() == "documentation.public_contract")
}

/// 验证每个原生函数 declarator 独立承担文档义务
#[test]
fn native_declarator_documentation_subjects() {
    for path in [PATH, "api/velocity_roles.c"] {
        for (source, count) in [
            ("int distance_m, calculate_velocity(int duration_s);", 1),
            ("int calculate_velocity(int duration_s), distance_m;", 1),
            (
                "int (*distance_m)(int duration_s), calculate_velocity(int duration_s);",
                1,
            ),
            (
                "int calculate_velocity(int duration_s), calculate_distance(int distance_m);",
                2,
            ),
            ("int (*distance_m)(int duration_s);", 0),
        ] {
            let terminal = review_sources(
                &reviewer_for_path(
                    &["calculate_velocity", "calculate_distance"],
                    path,
                ),
                "native-declarators",
                &[(path, source)],
            );
            let ReviewTerminal::Sealed(reviewed) = terminal else {
                panic!("{terminal:#?}")
            };
            assert_eq!(
                reviewed.completion(),
                Completion::Complete,
                "{source}"
            );
            assert_eq!(
                reviewed
                    .findings()
                    .iter()
                    .filter(|finding| finding
                        .rule()
                        .starts_with("documentation."))
                    .count(),
                count,
                "{path}: {source}: {:#?}",
                reviewed.findings()
            );
            assert!(
                reviewed.coverage().files()[0]
                    .families()
                    .iter()
                    .any(|(family, state)| *family
                        == FactFamily::Documentation
                        && *state == FactFamilyState::Complete(count as u32))
            );
        }
        let carrier = "/**\n * 计算距离\n *\n * 参数：\n * - distance_m： 距离值\n * 返回：\n * - 无\n * 错误：\n * - 无\n */\n";
        for declaration in [
            "void calculate_distance(int distance_m), *calculate_velocity(int distance_m);",
            "void calculate_distance(int distance_m), calculate_velocity(int duration_s);",
            "void (*duration_s)(int duration_s), calculate_distance(int distance_m), *calculate_velocity(int distance_m);",
        ] {
            let source = format!("{carrier}{declaration}");
            let terminal = review_sources(
                &reviewer_for_path(
                    &["calculate_distance", "calculate_velocity"],
                    path,
                ),
                "native-contracts",
                &[(path, &source)],
            );
            let ReviewTerminal::Sealed(reviewed) = terminal else {
                panic!("{terminal:#?}")
            };
            assert_eq!(reviewed.completion(), Completion::Complete);
            let subjects: Vec<_> = reviewed
                .findings()
                .iter()
                .filter(|finding| {
                    finding.rule() == "documentation.public_contract"
                })
                .map(|finding| finding.subject())
                .collect();
            assert_eq!(
                subjects,
                ["calculate_velocity"],
                "{source}: {:#?}",
                reviewed.findings()
            );
        }
    }
}

/// 验证公开自由运算符的文档以非空作用说明结束
#[test]
fn manifest_owned_free_operator_requires_nonempty_effect_last() {
    let valid = r#"struct Velocity {};
/**
 * 比较速度值
 *
 * 参数：
 * - left_value：  左侧速度值
 * - right_value： 右侧速度值
 * 返回：
 * - 比较结果
 * 错误：
 * - 无
 * 效果：
 * - 比较两个速度值
 */
bool operator==(const Velocity &left_value, const Velocity &right_value);
"#;
    let valid_terminal = review(valid, &["operator=="]);
    assert!(
        !has_public_contract_finding(&valid_terminal),
        "terminal: {valid_terminal:#?}"
    );

    for invalid in [
        (valid).replacen(" * 效果：\n * - 比较两个速度值\n", "", 1),
        (valid).replacen(" * - 比较两个速度值\n", " * - 无\n", 1),
        (valid).replacen(
            " * 错误：\n * - 无\n * 效果：",
            " * 效果：\n * - 比较两个速度值\n * 错误：",
            1,
        ),
        (valid).replacen(
            " * 效果：",
            " * 效果：\n * - 比较两个速度值\n * 效果：",
            1,
        ),
    ] {
        let terminal = review(&invalid, &["operator=="]);
        assert!(
            has_public_contract_finding(&terminal),
            "terminal: {terminal:#?}"
        );
    }
}

/// 验证公开函数模板的文档覆盖每个直接模板参数
#[test]
fn manifest_owned_function_template_covers_each_direct_parameter() {
    let valid = r#"/**
 * 计算抽样速度
 *
 * 模板参数：
 * - ValueType：    输入数值类型
 * - SAMPLE_COUNT： 抽样次数类型
 * 参数：
 * - input_value：  输入数值
 * - sample_count： 抽样次数
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
template <typename ValueType, int SAMPLE_COUNT>
double calculate_velocity(ValueType input_value, int sample_count);
"#;
    let valid_terminal = review(valid, &["calculate_velocity"]);
    assert!(
        !has_public_contract_finding(&valid_terminal),
        "terminal: {valid_terminal:#?}"
    );

    for invalid in [
        (valid).replacen(" * - SAMPLE_COUNT： 抽样次数类型\n", "", 1),
        (valid).replacen(
            " * - SAMPLE_COUNT： 抽样次数类型\n",
            " * - SAMPLE_COUNT： 抽样次数类型\n * - ValueType：    重复类型说明\n",
            1,
        ),
        (valid).replacen(
            concat!(
                " * 模板参数：\n",
                " * - ValueType：    输入数值类型\n",
                " * - SAMPLE_COUNT： 抽样次数类型\n",
            ),
            " * 模板参数：\n * - 无\n",
            1,
        ),
        (valid).replacen(
            " * - ValueType：    输入数值类型\n * - SAMPLE_COUNT： 抽样次数类型\n",
            " * - 不返回\n",
            1,
        ),
        (valid).replacen(
            concat!(
                " * 模板参数：\n",
                " * - ValueType：    输入数值类型\n",
                " * - SAMPLE_COUNT： 抽样次数类型\n",
                " * 参数：",
            ),
            " * 参数：",
            1,
        ),
    ] {
        let terminal = review(&invalid, &["calculate_velocity"]);
        let ReviewTerminal::Sealed(sealed) = terminal else {
            panic!("template mutation must seal: {terminal:#?}")
        };
        assert_eq!(sealed.completion(), Completion::Complete);
        let [finding] = sealed.findings() else {
            panic!("template mutation expects exactly one Finding: {sealed:#?}")
        };
        assert_eq!(finding.path(), PATH);
        assert_eq!(finding.rule(), "documentation.public_contract");
        assert_eq!(finding.grade(), csu::FindingGrade::HardViolation);
        assert_eq!(finding.subject(), "calculate_velocity");
    }
}

/// 验证公开构造和析构函数必须说明作用
#[test]
fn manifest_owned_constructor_and_destructor_require_effect() {
    let valid = r#"class VelocityCalculator {
public:
    /**
     * 初始化速度计算器
     *
     * 参数：
     * - 无
     * 返回：
     * - 无
     * 错误：
     * - 无
     * 效果：
     * - 初始化计算器状态
     */
    VelocityCalculator();

    /**
     * 销毁速度计算器
     *
     * 参数：
     * - 无
     * 返回：
     * - 无
     * 错误：
     * - 无
     * 效果：
     * - 释放计算器状态
     */
    ~VelocityCalculator();
};
"#;
    let owners = ["VelocityCalculator", "~VelocityCalculator"];
    let valid_terminal = review(valid, &owners);
    assert!(
        !has_public_contract_finding(&valid_terminal),
        "terminal: {valid_terminal:#?}"
    );

    let invalid =
        (valid).replacen("     * 效果：\n     * - 释放计算器状态\n", "", 1);
    let invalid_terminal = review(&invalid, &owners);
    assert!(
        has_public_contract_finding(&invalid_terminal),
        "terminal: {invalid_terminal:#?}"
    );
}

/// 验证未命名模板参数使文档检查保持不完整
#[test]
fn unnamed_direct_template_parameter_blocks_documentation_closure() {
    let source = r#"/**
 * 计算抽样速度
 *
 * 模板参数：
 * - ValueType： 输入数值类型
 * 参数：
 * - input_value： 输入数值
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
template <typename>
double calculate_velocity(double input_value);
"#;
    let terminal = review(source, &["calculate_velocity"]);
    assert_eq!(terminal.disposition(), Disposition::Incomplete);
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("unresolved template parameter must seal as incomplete");
    };
    assert_eq!(review.completion(), Completion::Incomplete);
    assert!(review.coverage().files()[0].families().iter().any(
        |(family, state)| {
            *family == FactFamily::Documentation
                && matches!(state, FactFamilyState::Blocked(_))
        }
    ));
    assert!(
        !review.findings().iter().any(|finding| {
            finding.rule() == "documentation.public_contract"
        })
    );
}

/// 验证无法确定参数身份的简写函数模板不能判为完整
#[test]
fn abbreviated_function_template_cannot_seal_without_stable_identity() {
    let carriers = [
        r#"/**
 * 计算抽样速度
 *
 * 参数：
 * - input_value： 输入数值
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
double calculate_velocity(auto input_value);
"#,
        r#"template <typename ValueType>
concept NumericValue = true;
/**
 * 计算抽样速度
 *
 * 模板参数：
 * - GuessedType： 猜测模板类型
 * 参数：
 * - input_value： 输入数值
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
double calculate_velocity(NumericValue auto input_value);
"#,
    ];
    for source in carriers {
        let terminal = review(source, &["calculate_velocity"]);
        assert_eq!(terminal.disposition(), Disposition::Incomplete);
        let ReviewTerminal::Sealed(review) = terminal else {
            panic!("abbreviated template must seal as incomplete");
        };
        assert!(review.coverage().files()[0].families().iter().any(
            |(family, state)| {
                *family == FactFamily::Documentation
                    && matches!(state, FactFamilyState::Blocked(_))
            }
        ));
        assert!(!review.findings().iter().any(|finding| {
            finding.rule() == "documentation.public_contract"
        }));
    }
}

/// 验证已命名参数不能掩盖其他种类的未命名参数
#[test]
fn parameter_completeness_is_monotone_across_parameter_kinds() {
    let named_then_pack = r#"/**
 * 计算抽样速度
 *
 * 模板参数：
 * - ValueType： 输入数值类型
 * - Pack：      参数包类型
 * 参数：
 * - input：  输入数值
 * - sample： 参数包
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
template <typename ValueType, typename... Pack>
double calculate_velocity(int input, Pack... sample);
"#;
    let sealed_terminal = review(named_then_pack, &["calculate_velocity"]);
    assert!(
        !has_public_contract_finding(&sealed_terminal),
        "terminal: {sealed_terminal:#?}"
    );
    let ReviewTerminal::Sealed(sealed) = sealed_terminal else {
        panic!(
            "named parameters plus named pack must seal: {sealed_terminal:#?}"
        )
    };
    assert_eq!(
        sealed.completion(),
        Completion::Complete,
        "{:#?}",
        sealed.findings()
    );

    for (before, after) in [
        ("template <typename", "template <\n// 模板说明\ntypename"),
        ("int input, Pack", "int input,\n/* 参数说明 */\nPack"),
    ] {
        let changed = named_then_pack.replace(before, after);
        let ReviewTerminal::Sealed(reviewed) =
            review(&changed, &["calculate_velocity"])
        else {
            panic!("commented parameters must seal")
        };
        assert_eq!(reviewed.completion(), Completion::Complete);
        assert!(reviewed.findings().is_empty(), "{:#?}", reviewed.findings());
    }
    let anonymous_then_pack = (named_then_pack.replacen(
        "int input,",
        "int,",
        1,
    ))
    .replacen(" * - input：  输入数值\n", "", 1);
    let terminal = review(&anonymous_then_pack, &["calculate_velocity"]);
    assert_eq!(terminal.disposition(), Disposition::Incomplete);
    let ReviewTerminal::Sealed(sealed) = terminal else {
        panic!("unnamed parameter must seal as incomplete: {terminal:#?}")
    };
    assert_eq!(sealed.completion(), Completion::Incomplete);
    assert!(sealed.coverage().files()[0].families().iter().any(
        |(family, state)| {
            *family == FactFamily::Documentation
                && matches!(state, FactFamilyState::Blocked(_))
        }
    ));
    assert!(
        !sealed.findings().iter().any(|finding| {
            finding.rule() == "documentation.public_contract"
        })
    );

    let anonymous_pack_tail =
        (named_then_pack).replacen("Pack... sample", "Pack...", 1);
    let terminal = review(&anonymous_pack_tail, &["calculate_velocity"]);
    let ReviewTerminal::Sealed(sealed) = terminal else {
        panic!("unnamed pack must seal: {terminal:#?}")
    };
    assert_eq!(sealed.completion(), Completion::Incomplete);
    assert!(sealed.coverage().files()[0].families().iter().any(
        |(family, state)| {
            *family == FactFamily::Documentation
                && matches!(state, FactFamilyState::Blocked(_))
        }
    ));
}

/// 验证 C++ 非函数文档不依赖公开函数名单
#[test]
fn cpp_non_callable_subject_does_not_require_public_tier() {
    let authority = include_bytes!("../../docs/fixtures/core/authority.json");
    let reviewer =
        compile_value(&serde_json::from_slice(authority).unwrap()).unwrap();
    for (identity, source, expected, blocked) in [
        (
            "named",
            "/**\n * 速度值类型\n */\nclass Velocity {};\n",
            Completion::Complete,
            false,
        ),
        (
            "anonymous",
            "/**\n * 速度值类型\n */\nstruct { int velocity; } state;\n",
            Completion::Incomplete,
            true,
        ),
    ] {
        let terminal = review_sources(&reviewer, identity, &[(PATH, source)]);
        let ReviewTerminal::Sealed(review) = terminal else {
            panic!("documented subject must seal: {terminal:#?}")
        };
        assert_eq!(review.completion(), expected, "{identity}");
        assert_eq!(
            review.coverage().files()[0].families().iter().any(
                |(family, state)| {
                    *family == FactFamily::Documentation
                        && matches!(state, FactFamilyState::Blocked(_))
                }
            ),
            blocked,
            "{identity}"
        );
    }
}

/// 验证确有重载歧义时不猜测文档归属
#[test]
fn genuine_overload_ambiguity_stays_conservative() {
    let source = r#"/**
 * 计算整数速度
 *
 * 参数：
 * - input： 输入整数
 * 返回：
 * - 整数速度
 * 错误：
 * - 无
 */
int calculate_velocity(int input);

/**
 * 计算浮点速度
 *
 * 参数：
 * - input： 输入浮点数
 * 返回：
 * - 浮点速度
 * 错误：
 * - 无
 */
double calculate_velocity(double input);
"#;
    let terminal = review(source, &["calculate_velocity"]);
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("genuine overload ambiguity must seal: {terminal:#?}")
    };
    assert_eq!(review.completion(), Completion::Incomplete);
    assert!(review.coverage().files()[0].families().iter().any(
        |(family, state)| {
            *family == FactFamily::Documentation
                && matches!(state, FactFamilyState::Blocked(_))
        }
    ));
}
