use std::collections::HashMap;

use crate::core::evidence::{
    BlockRegionFact, DependencyEdgeFact, EvidenceStore, ExpressionFact, ExpressionKind,
    ModuleUnitFact, SymbolFact, SymbolKind, SymbolVisibility,
};
use crate::core::issue::{Domain, Issue, IssueKind, Language, Scope};
use crate::core::profile::Profile;

#[derive(Clone, Copy)]
struct RuleMeta {
    id: &'static str,
    name: &'static str,
    kind: IssueKind,
    scope: Scope,
    domain: Domain,
    message: &'static str,
}

/// 返回已实现的 C/C++ 规则 ID
pub fn implemented_rule_ids() -> Vec<&'static str> {
    vec![
        "Cpp001", "Cpp002", "Cpp003", "Cpp004", "Cpp005", "Cpp006", "Cpp007", "Cpp008", "Cpp009",
        "Cpp010",
    ]
}

/// 评估 C/C++ 专属规则
pub fn evaluate(store: &EvidenceStore, _profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    issues.extend(evaluate_header_boundary_policy(store));
    issues.extend(evaluate_include_graph_complexity(store));
    issues.extend(evaluate_include_guard_policy(store));
    issues.extend(evaluate_public_header_using_namespace(store));
    issues.extend(evaluate_abi_boundary_contract(store));
    issues.extend(evaluate_macro_contract_policy(store));
    issues.extend(evaluate_template_complexity_intent(store));
    issues.extend(evaluate_preprocessor_branch_intent(store));
    issues.extend(evaluate_ownership_lifecycle_contract(store));
    issues.extend(evaluate_macro_expansion_risk(store));
    issues
}

fn evaluate_header_boundary_policy(store: &EvidenceStore) -> Vec<Issue> {
    store
        .module_units
        .iter()
        .filter(|module| c_family_language(module.language) && module.is_header)
        .filter(|module| !module.path.starts_with("include/"))
        .map(|module| {
            issue_for_module(
                store,
                RuleMeta {
                    id: "Cpp001",
                    name: "header_boundary_policy",
                    kind: IssueKind::SoftFriction,
                    scope: Scope::Project,
                    domain: Domain::PublicApi,
                    message: "C/C++ header 边界需要显式审查",
                },
                module,
            )
        })
        .collect()
}

fn evaluate_include_graph_complexity(store: &EvidenceStore) -> Vec<Issue> {
    let mut counts = HashMap::<&str, usize>::new();
    for edge in store
        .dependency_edges
        .iter()
        .filter(|edge| c_family_file(store, &edge.file_id))
    {
        *counts.entry(edge.module_id.as_str()).or_default() += 1;
    }

    store
        .dependency_edges
        .iter()
        .filter(|edge| c_family_file(store, &edge.file_id))
        .filter(|edge| {
            counts
                .get(edge.module_id.as_str())
                .is_some_and(|count| *count >= 3)
        })
        .map(|edge| {
            issue_for_dependency(
                store,
                RuleMeta {
                    id: "Cpp002",
                    name: "include_graph_complexity",
                    kind: IssueKind::SoftFriction,
                    scope: Scope::Project,
                    domain: Domain::Dependency,
                    message: "C/C++ include 图复杂度带来维护摩擦",
                },
                edge,
            )
        })
        .take(1)
        .collect()
}

fn evaluate_include_guard_policy(store: &EvidenceStore) -> Vec<Issue> {
    store
        .module_units
        .iter()
        .filter(|module| c_family_language(module.language) && module.is_header)
        .filter(|module| module.include_guard.is_none() && !module.pragma_once)
        .map(|module| {
            issue_for_module(
                store,
                RuleMeta {
                    id: "Cpp003",
                    name: "include_guard_policy",
                    kind: IssueKind::HardViolation,
                    scope: Scope::File,
                    domain: Domain::Dependency,
                    message: "C/C++ header 必须具备 include guard 或 pragma once",
                },
                module,
            )
        })
        .collect()
}

fn evaluate_public_header_using_namespace(store: &EvidenceStore) -> Vec<Issue> {
    store
        .dependency_edges
        .iter()
        .filter(|edge| c_family_file(store, &edge.file_id))
        .filter(|edge| module_is_public_header(store, &edge.module_id))
        .filter(|edge| edge.is_glob && edge.imported == "*")
        .map(|edge| {
            issue_for_dependency(
                store,
                RuleMeta {
                    id: "Cpp004",
                    name: "public_header_using_namespace",
                    kind: IssueKind::HardViolation,
                    scope: Scope::Module,
                    domain: Domain::Dependency,
                    message: "C++ public header 不允许 broad namespace import",
                },
                edge,
            )
        })
        .collect()
}

fn evaluate_abi_boundary_contract(store: &EvidenceStore) -> Vec<Issue> {
    store
        .symbols
        .iter()
        .filter(|symbol| c_family_language(symbol.language))
        .filter(|symbol| public_or_internal(symbol.visibility))
        .filter(|symbol| {
            symbol
                .type_text
                .as_deref()
                .is_some_and(|text| text.contains("extern"))
                || symbol.attributes.iter().any(|attribute| {
                    matches!(attribute.as_str(), "dllexport" | "dllimport" | "visibility")
                })
        })
        .map(|symbol| {
            issue_for_symbol(
                store,
                RuleMeta {
                    id: "Cpp005",
                    name: "abi_boundary_contract",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Symbol,
                    domain: Domain::SafetyAdjacent,
                    message: "C/C++ ABI 边界需要契约审查",
                },
                symbol,
            )
        })
        .collect()
}

fn evaluate_macro_contract_policy(store: &EvidenceStore) -> Vec<Issue> {
    store
        .symbols
        .iter()
        .filter(|symbol| c_family_language(symbol.language))
        .filter(|symbol| symbol.kind == SymbolKind::Macro && symbol.doc_region_id.is_none())
        .filter(|symbol| macro_definition_for_symbol(store, symbol).is_some())
        .map(|symbol| {
            issue_for_symbol(
                store,
                RuleMeta {
                    id: "Cpp006",
                    name: "macro_contract_policy",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Symbol,
                    domain: Domain::Maintainability,
                    message: "C/C++ 宏需要契约审查",
                },
                symbol,
            )
        })
        .collect()
}

fn evaluate_template_complexity_intent(store: &EvidenceStore) -> Vec<Issue> {
    store
        .symbols
        .iter()
        .filter(|symbol| symbol.language == Language::Cpp)
        .filter(|symbol| {
            symbol
                .attributes
                .iter()
                .any(|attribute| attribute == "template")
                || symbol.type_text.as_deref().is_some_and(|text| {
                    ["template", "enable_if", "requires", "concept"]
                        .iter()
                        .any(|marker| text.contains(marker))
                })
        })
        .map(|symbol| {
            issue_for_symbol(
                store,
                RuleMeta {
                    id: "Cpp007",
                    name: "template_complexity_intent",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Symbol,
                    domain: Domain::Maintainability,
                    message: "C++ template 复杂度需要意图审查",
                },
                symbol,
            )
        })
        .collect()
}

fn evaluate_preprocessor_branch_intent(store: &EvidenceStore) -> Vec<Issue> {
    let mut issues = store
        .block_regions
        .iter()
        .filter(|block| c_family_file(store, &block.file_id))
        .filter(|block| block.kind == "preprocessor" && block.intent_comment_id.is_none())
        .map(|block| {
            issue_for_block(
                store,
                RuleMeta {
                    id: "Cpp008",
                    name: "preprocessor_branch_intent",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Block,
                    domain: Domain::Maintainability,
                    message: "C/C++ 预处理分支需要意图审查",
                },
                block,
            )
        })
        .collect::<Vec<_>>();

    if issues.is_empty() {
        issues.extend(
            store
                .expressions
                .iter()
                .filter(|expression| c_family_file(store, &expression.file_id))
                .filter(|expression| expression.kind == ExpressionKind::Preprocessor)
                .filter(|expression| !expression.text.starts_with("#endif"))
                .map(|expression| {
                    issue_for_expression(
                        store,
                        RuleMeta {
                            id: "Cpp008",
                            name: "preprocessor_branch_intent",
                            kind: IssueKind::UnderReview,
                            scope: Scope::Block,
                            domain: Domain::Maintainability,
                            message: "C/C++ 预处理分支需要意图审查",
                        },
                        expression,
                    )
                }),
        );
    }
    issues
}

fn evaluate_ownership_lifecycle_contract(store: &EvidenceStore) -> Vec<Issue> {
    let mut issues = store
        .block_regions
        .iter()
        .filter(|block| c_family_file(store, &block.file_id))
        .filter(|block| block.kind == "allocation" && block.intent_comment_id.is_none())
        .map(|block| {
            issue_for_block(
                store,
                RuleMeta {
                    id: "Cpp009",
                    name: "ownership_lifecycle_contract",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Block,
                    domain: Domain::SafetyAdjacent,
                    message: "C/C++ 所有权生命周期需要审查",
                },
                block,
            )
        })
        .collect::<Vec<_>>();

    if issues.is_empty() {
        issues.extend(
            store
                .expressions
                .iter()
                .filter(|expression| c_family_file(store, &expression.file_id))
                .filter(|expression| expression.kind == ExpressionKind::Allocation)
                .map(|expression| {
                    issue_for_expression(
                        store,
                        RuleMeta {
                            id: "Cpp009",
                            name: "ownership_lifecycle_contract",
                            kind: IssueKind::UnderReview,
                            scope: Scope::Block,
                            domain: Domain::SafetyAdjacent,
                            message: "C/C++ 所有权生命周期需要审查",
                        },
                        expression,
                    )
                }),
        );
    }
    issues
}

fn evaluate_macro_expansion_risk(store: &EvidenceStore) -> Vec<Issue> {
    store
        .expressions
        .iter()
        .filter(|expression| c_family_file(store, &expression.file_id))
        .filter(|expression| expression.kind == ExpressionKind::MacroDefinition)
        .filter(|expression| macro_has_expansion_risk(&expression.text))
        .map(|expression| {
            issue_for_expression(
                store,
                RuleMeta {
                    id: "Cpp010",
                    name: "macro_expansion_risk",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Expression,
                    domain: Domain::SafetyAdjacent,
                    message: "C/C++ 宏展开风险需要审查",
                },
                expression,
            )
        })
        .collect()
}

fn issue_for_module(store: &EvidenceStore, meta: RuleMeta, module: &ModuleUnitFact) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{}:{}", meta.id, module.id.replace(':', "_")),
        meta.kind,
        meta.id,
        meta.name,
        meta.scope,
        meta.domain,
    )
    .with_message(meta.message)
    .with_evidence(module.id.clone());
    if let Some(file) = store
        .file_units
        .iter()
        .find(|file| file.id == module.file_id)
    {
        issue = issue.with_location(file.language, file.path.clone(), module.range.clone());
    } else {
        issue.range = Some(module.range.clone());
    }
    issue
}

fn issue_for_dependency(store: &EvidenceStore, meta: RuleMeta, edge: &DependencyEdgeFact) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{}:{}", meta.id, edge.id.replace(':', "_")),
        meta.kind,
        meta.id,
        meta.name,
        meta.scope,
        meta.domain,
    )
    .with_message(meta.message)
    .with_evidence(edge.id.clone());
    if let Some(file) = store.file_units.iter().find(|file| file.id == edge.file_id) {
        issue = issue.with_location(file.language, file.path.clone(), edge.range.clone());
    } else {
        issue.range = Some(edge.range.clone());
    }
    issue
}

fn issue_for_symbol(store: &EvidenceStore, meta: RuleMeta, symbol: &SymbolFact) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{}:{}", meta.id, symbol.id.replace(':', "_")),
        meta.kind,
        meta.id,
        meta.name,
        meta.scope,
        meta.domain,
    )
    .with_message(meta.message)
    .with_evidence(symbol.id.clone());
    if let Some(file) = store
        .file_units
        .iter()
        .find(|file| file.id == symbol.file_id)
    {
        issue = issue.with_location(file.language, file.path.clone(), symbol.range.clone());
    } else {
        issue.range = Some(symbol.range.clone());
    }
    issue
}

fn issue_for_block(store: &EvidenceStore, meta: RuleMeta, block: &BlockRegionFact) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{}:{}", meta.id, block.id.replace(':', "_")),
        meta.kind,
        meta.id,
        meta.name,
        meta.scope,
        meta.domain,
    )
    .with_message(meta.message)
    .with_evidence(block.id.clone());
    if let Some(file) = store
        .file_units
        .iter()
        .find(|file| file.id == block.file_id)
    {
        issue = issue.with_location(file.language, file.path.clone(), block.range.clone());
    } else {
        issue.range = Some(block.range.clone());
    }
    issue
}

fn issue_for_expression(
    store: &EvidenceStore,
    meta: RuleMeta,
    expression: &ExpressionFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{}:{}", meta.id, expression.id.replace(':', "_")),
        meta.kind,
        meta.id,
        meta.name,
        meta.scope,
        meta.domain,
    )
    .with_message(meta.message)
    .with_evidence(expression.id.clone());
    if let Some(file) = store
        .file_units
        .iter()
        .find(|file| file.id == expression.file_id)
    {
        issue = issue.with_location(file.language, file.path.clone(), expression.range.clone());
    } else {
        issue.range = Some(expression.range.clone());
    }
    issue
}

fn c_family_language(language: Language) -> bool {
    matches!(language, Language::C | Language::Cpp)
}

fn c_family_file(store: &EvidenceStore, file_id: &str) -> bool {
    store
        .file_units
        .iter()
        .any(|file| file.id == file_id && c_family_language(file.language))
}

fn module_is_public_header(store: &EvidenceStore, module_id: &str) -> bool {
    store
        .module_units
        .iter()
        .any(|module| module.id == module_id && module.is_header)
}

fn public_or_internal(visibility: SymbolVisibility) -> bool {
    matches!(
        visibility,
        SymbolVisibility::Public | SymbolVisibility::Internal
    )
}

fn macro_definition_for_symbol<'a>(
    store: &'a EvidenceStore,
    symbol: &SymbolFact,
) -> Option<&'a ExpressionFact> {
    store.expressions.iter().find(|expression| {
        expression.file_id == symbol.file_id
            && expression.kind == ExpressionKind::MacroDefinition
            && expression
                .callee
                .as_deref()
                .is_some_and(|callee| callee == symbol.name)
    })
}

fn macro_has_expansion_risk(text: &str) -> bool {
    text.trim_end().ends_with('\\')
        || [" if ", " for ", " while ", " do "]
            .iter()
            .any(|marker| text.contains(marker))
}
