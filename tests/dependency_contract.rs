use csu::{ReviewTerminal, WorkspaceReviewer};

mod review_fixture;

use review_fixture::{compile_value, review_sources};

// 共同输入与结果读取

/// 创建测试审查器
fn reviewer(reorder_safe: bool) -> WorkspaceReviewer {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../docs/fixtures/core/authority.json"
    ))
    .unwrap();
    authority["dependency_authority"] = serde_json::json!({
        "python_standard_library": ["os", "sys"],
        "python_third_party": ["numpy"],
        "python_project_roots": ["project"],
        "python_reorder_safe": reorder_safe,
        "rust_reorder_safe": reorder_safe
    });
    compile_value(&authority).unwrap()
}

/// 审查一组依赖声明样例
fn review(revision: &str, sources: &[(&str, &str)]) -> ReviewTerminal {
    review_sources(&reviewer(true), revision, sources)
}

/// 读取文件的依赖完成记录，缺少记录立即失败
fn dependency_state(
    families: &[(csu::FactFamily, csu::FactFamilyState)],
) -> &csu::FactFamilyState {
    families
        .iter()
        .find_map(|(family, state)| {
            (*family == csu::FactFamily::DependencyDeclaration)
                .then_some(state)
        })
        .expect("dependency coverage must exist")
}

// 输入：接纳项目事实
#[path = "dependency/authority.rs"]
mod authority;

// 观察：声明身份与作用域
#[path = "dependency/observation.rs"]
mod observation;

// 判断：授权、顺序与位置
#[path = "dependency/ordering.rs"]
mod ordering;

// 完成：已知证据与受阻原因
#[path = "dependency/completion.rs"]
mod completion;
