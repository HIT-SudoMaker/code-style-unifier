use csu::Completion;
use csu::FindingGrade;
use csu::ReviewTerminal;
use csu::SealedReview;
use csu::WorkspaceReviewer;

#[path = "../review_fixture/mod.rs"]
mod review_fixture;

use review_fixture::compile_value;
use review_fixture::review_sources;

const VALID_PYTHON: &str = include_str!(
    "../../docs/fixtures/core/documents/valid/python/calculate_velocity.py"
);
const VALID_RUST: &str = include_str!(
    "../../docs/fixtures/core/documents/valid/rust/calculate_velocity.rs"
);
const VALID_PROCEDURAL: &str = include_str!(
    "../../docs/fixtures/core/documents/valid/c/calculate_velocity.h"
);
const VALID_CPP: &str = include_str!(
    "../../docs/fixtures/core/documents/valid/cpp/calculate_velocity.hpp"
);
const PROCEDURAL_PATH: &str = "api/contract.h";
const OBJECT_ORIENTED_PATH: &str = "api/contract.hpp";

/// 创建测试审查器
fn reviewer(public_names: &[&str]) -> WorkspaceReviewer {
    let mut authority: serde_json::Value = serde_json::from_str(include_str!(
        "../../docs/fixtures/core/authority.json"
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
    compile_value(&authority).unwrap()
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

// 观察：原生文档载体
mod carriers;

// 观察：主体与直接归属
mod subjects;

// 判断：内容与角色义务
mod content;

// 判断：字段布局与完整合同
mod fields;
