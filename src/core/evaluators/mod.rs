/// 实现跨语言共享的 Core 规则评估
pub mod core;
/// 实现 C/C++ 专属规则评估
pub mod cpp;
/// 实现 Python 专属规则评估
pub mod python;
/// 实现 Rust 专属规则评估
pub mod rust;
/// 实现 TypeScript 专属规则评估
pub mod typescript;

use crate::core::evidence::EvidenceStore;
use crate::core::issue::Issue;
use crate::core::profile::Profile;

pub use self::core::{
    appears_english, evaluate_summary_concision, evaluate_terminal_punctuation,
    evaluate_text_natural_language, needs_concision_review,
};

/// 汇总全部已登记 evaluator 的规则 ID
pub fn implemented_rule_ids() -> Vec<&'static str> {
    let mut ids = Vec::new();
    ids.extend(core::implemented_rule_ids());
    ids.extend(python::implemented_rule_ids());
    ids.extend(rust::implemented_rule_ids());
    ids.extend(cpp::implemented_rule_ids());
    ids.extend(typescript::implemented_rule_ids());
    ids
}

/// 对证据集运行全部已登记 evaluator
pub fn evaluate_all(store: &EvidenceStore, profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    issues.extend(core::evaluate(store, profile));
    issues.extend(python::evaluate(store, profile));
    issues.extend(rust::evaluate(store, profile));
    issues.extend(cpp::evaluate(store, profile));
    issues.extend(typescript::evaluate(store, profile));
    issues
}
