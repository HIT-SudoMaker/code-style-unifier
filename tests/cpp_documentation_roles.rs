use csu::AuthorityDocument;
use csu::AuthorityInput;
use csu::Completion;
use csu::Disposition;
use csu::DocumentSet;
use csu::FactFamily;
use csu::FactFamilyState;
use csu::ReviewInput;
use csu::ReviewTerminal;
use csu::SourceDocument;
use csu::WorkspaceReviewer;

const AUTHORITY: &str = include_str!("../docs/fixtures/core/authority.json");
const PATH: &str = "api/velocity_roles.hpp";

/// 构造测试 Reviewer
fn reviewer(public_callables: &[&str]) -> WorkspaceReviewer {
    let mut authority: serde_json::Value =
        serde_json::from_str(AUTHORITY).unwrap();
    authority["public_callables"][PATH] = serde_json::json!(public_callables);
    authority["token_vocabulary"]
        .as_array_mut()
        .unwrap()
        .extend([
            serde_json::json!("calculator"),
            serde_json::json!("input"),
            serde_json::json!("left"),
            serde_json::json!("right"),
            serde_json::json!("sample"),
            serde_json::json!("type"),
            serde_json::json!("value"),
        ]);
    let authority = serde_json::to_vec(&authority).unwrap();
    WorkspaceReviewer::compile(AuthorityInput::Documents(&[
        AuthorityDocument {
            relative_path: "authority.json",
            bytes: &authority,
        },
    ]))
    .unwrap()
}

/// 审查内存源码并返回封存终态
fn review(source: &str, public_callables: &[&str]) -> ReviewTerminal {
    reviewer(public_callables).review(ReviewInput::Documents(DocumentSet {
        revision: "cpp-structural-documentation-roles",
        documents: &[SourceDocument {
            relative_path: PATH,
            bytes: source.as_bytes(),
        }],
    }))
}

/// 判断审查是否包含公共契约 Finding
fn has_public_contract_finding(terminal: &ReviewTerminal) -> bool {
    let ReviewTerminal::Sealed(review) = terminal else {
        panic!("documentation judgment must seal: {terminal:#?}");
    };
    review
        .findings()
        .iter()
        .any(|finding| finding.rule() == "documentation.public_contract")
}

/// 验证 C++ 文档角色证据场景
#[test]
fn manifest_owned_free_operator_requires_nonempty_effect_last() {
    let valid = r#"struct Velocity {};
/**
 * 比较速度值
 *
 * 参数：
 * - left_value：左侧速度值
 * - right_value：右侧速度值
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
        valid.replace(" * 效果：\n * - 比较两个速度值\n", ""),
        valid.replace(" * - 比较两个速度值\n", " * - 无\n"),
        valid.replace(
            " * 错误：\n * - 无\n * 效果：",
            " * 效果：\n * - 比较两个速度值\n * 错误：",
        ),
        valid
            .replace(" * 效果：", " * 效果：\n * - 比较两个速度值\n * 效果："),
    ] {
        let terminal = review(&invalid, &["operator=="]);
        assert!(
            has_public_contract_finding(&terminal),
            "terminal: {terminal:#?}"
        );
    }
}

/// 验证 C++ 文档角色证据场景
#[test]
fn manifest_owned_function_template_covers_each_direct_parameter() {
    let valid = r#"/**
 * 计算抽样速度
 *
 * 模板参数：
 * - ValueType：输入数值类型
 * - SampleCount：抽样次数类型
 * 参数：
 * - input_value：输入数值
 * - sample_count：抽样次数
 * 返回：
 * - 平均速度
 * 错误：
 * - 无
 */
template <typename ValueType, int SampleCount>
double calculate_velocity(ValueType input_value, int sample_count);
"#;
    let valid_terminal = review(valid, &["calculate_velocity"]);
    assert!(
        !has_public_contract_finding(&valid_terminal),
        "terminal: {valid_terminal:#?}"
    );

    for invalid in [
        valid.replace(" * - SampleCount：抽样次数类型\n", ""),
        valid.replace(
            " * - SampleCount：抽样次数类型\n",
            " * - ValueType：重复类型说明\n",
        ),
        valid.replace(
            concat!(
                " * 模板参数：\n",
                " * - ValueType：输入数值类型\n",
                " * - SampleCount：抽样次数类型\n",
            ),
            " * 模板参数：\n * - 无\n",
        ),
        valid.replace(
            concat!(
                " * 模板参数：\n",
                " * - ValueType：输入数值类型\n",
                " * - SampleCount：抽样次数类型\n",
                " * 参数：",
            ),
            " * 参数：",
        ),
    ] {
        let terminal = review(&invalid, &["calculate_velocity"]);
        assert!(
            has_public_contract_finding(&terminal),
            "terminal: {terminal:#?}"
        );
    }
}

/// 验证 C++ 文档角色证据场景
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
        valid.replace("     * 效果：\n     * - 释放计算器状态\n", "");
    let invalid_terminal = review(&invalid, &owners);
    assert!(
        has_public_contract_finding(&invalid_terminal),
        "terminal: {invalid_terminal:#?}"
    );
}

/// 验证 C++ 文档角色证据场景
#[test]
fn unnamed_direct_template_parameter_blocks_documentation_closure() {
    let source = r#"/**
 * 计算抽样速度
 *
 * 模板参数：
 * - ValueType：输入数值类型
 * 参数：
 * - input_value：输入数值
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

/// 验证 C++ 文档角色证据场景
#[test]
fn abbreviated_function_template_cannot_seal_without_stable_identity() {
    let carriers = [
        r#"/**
 * 计算抽样速度
 *
 * 参数：
 * - input_value：输入数值
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
 * - GuessedType：猜测模板类型
 * 参数：
 * - input_value：输入数值
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
