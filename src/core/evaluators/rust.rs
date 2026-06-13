use crate::core::evidence::{
    BlockRegionFact, DependencyEdgeFact, EvidenceStore, ExpressionFact, ExpressionKind, SymbolFact,
    SymbolKind, SymbolVisibility,
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

/// 返回已实现的 Rust 规则 ID
pub fn implemented_rule_ids() -> Vec<&'static str> {
    vec![
        "Rust001", "Rust002", "Rust003", "Rust004", "Rust005", "Rust006", "Rust007", "Rust008",
        "Rust009", "Rust010",
    ]
}

/// 评估 Rust 专属规则
pub fn evaluate(store: &EvidenceStore, _profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    issues.extend(evaluate_feature_gate_policy(store));
    issues.extend(evaluate_cfg_complexity_policy(store));
    issues.extend(evaluate_pub_prelude_policy(store));
    issues.extend(evaluate_use_tree_shape_policy(store));
    issues.extend(evaluate_ffi_boundary_contract(store));
    issues.extend(evaluate_trait_object_boundary_clarity(store));
    issues.extend(evaluate_unsafe_contract(store));
    issues.extend(evaluate_async_blocking_policy(store));
    issues.extend(evaluate_await_holding_lock_policy(store));
    issues.extend(evaluate_panic_context_policy(store));
    issues
}

fn evaluate_feature_gate_policy(store: &EvidenceStore) -> Vec<Issue> {
    store
        .expressions
        .iter()
        .filter(|expression| rust_expression(store, expression))
        .filter(|expression| {
            expression.callee.as_deref() == Some("feature")
                || expression.text.starts_with("#![feature")
        })
        .map(|expression| {
            issue_for_expression(
                store,
                RuleMeta {
                    id: "Rust001",
                    name: "feature_gate_policy",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Project,
                    domain: Domain::Maintainability,
                    message: "Rust feature gate 使用需要审查",
                },
                expression,
            )
        })
        .collect()
}

fn evaluate_cfg_complexity_policy(store: &EvidenceStore) -> Vec<Issue> {
    store
        .expressions
        .iter()
        .filter(|expression| rust_expression(store, expression))
        .filter(|expression| matches!(expression.callee.as_deref(), Some("cfg" | "cfg_attr")))
        .map(|expression| {
            issue_for_expression(
                store,
                RuleMeta {
                    id: "Rust002",
                    name: "cfg_complexity_policy",
                    kind: IssueKind::SoftFriction,
                    scope: Scope::Module,
                    domain: Domain::Maintainability,
                    message: "Rust cfg 条件会增加维护摩擦",
                },
                expression,
            )
        })
        .collect()
}

fn evaluate_pub_prelude_policy(store: &EvidenceStore) -> Vec<Issue> {
    let mut issues = store
        .symbols
        .iter()
        .filter(|symbol| symbol.language == Language::Rust)
        .filter(|symbol| symbol.kind == SymbolKind::Module && symbol.name == "prelude")
        .filter(|symbol| public_or_internal(symbol.visibility))
        .map(|symbol| {
            issue_for_symbol(
                store,
                RuleMeta {
                    id: "Rust003",
                    name: "pub_prelude_policy",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Module,
                    domain: Domain::PublicApi,
                    message: "Rust prelude 公开暴露需要审查",
                },
                symbol,
            )
        })
        .collect::<Vec<_>>();

    issues.extend(
        store
            .dependency_edges
            .iter()
            .filter(|edge| rust_file(store, &edge.file_id))
            .filter(|edge| edge.is_public && (edge.is_glob || edge.imported.contains('*')))
            .map(|edge| {
                issue_for_dependency(
                    store,
                    RuleMeta {
                        id: "Rust003",
                        name: "pub_prelude_policy",
                        kind: IssueKind::UnderReview,
                        scope: Scope::Module,
                        domain: Domain::PublicApi,
                        message: "Rust 公开 glob re-export 需要审查",
                    },
                    edge,
                )
            }),
    );
    issues
}

fn evaluate_use_tree_shape_policy(store: &EvidenceStore) -> Vec<Issue> {
    store
        .dependency_edges
        .iter()
        .filter(|edge| rust_file(store, &edge.file_id))
        .filter(|edge| edge.is_glob || edge.imported.contains('{'))
        .map(|edge| {
            issue_for_dependency(
                store,
                RuleMeta {
                    id: "Rust004",
                    name: "use_tree_shape_policy",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Module,
                    domain: Domain::Dependency,
                    message: "Rust use tree 形状需要审查",
                },
                edge,
            )
        })
        .collect()
}

fn evaluate_ffi_boundary_contract(store: &EvidenceStore) -> Vec<Issue> {
    store
        .symbols
        .iter()
        .filter(|symbol| symbol.language == Language::Rust)
        .filter(|symbol| public_or_internal(symbol.visibility))
        .filter(|symbol| {
            symbol
                .type_text
                .as_deref()
                .is_some_and(|text| text.contains("extern"))
                || symbol
                    .attributes
                    .iter()
                    .any(|attribute| is_ffi_boundary_attribute(attribute))
        })
        .map(|symbol| {
            issue_for_symbol(
                store,
                RuleMeta {
                    id: "Rust005",
                    name: "ffi_boundary_contract",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Symbol,
                    domain: Domain::SafetyAdjacent,
                    message: "Rust FFI 边界需要契约审查",
                },
                symbol,
            )
        })
        .collect()
}

fn is_ffi_boundary_attribute(attribute: &str) -> bool {
    let attribute = rust_attribute_without_unsafe_wrapper(attribute);
    attribute == "no_mangle"
        || rust_attribute_has_name(attribute, "export_name")
        || rust_attribute_has_name(attribute, "link_name")
}

fn rust_attribute_without_unsafe_wrapper(attribute: &str) -> &str {
    let attribute = attribute.trim();
    let Some(rest) = attribute.strip_prefix("unsafe") else {
        return attribute;
    };
    let rest = rest.trim_start();
    let Some(body) = rest
        .strip_prefix('(')
        .and_then(|rest| rest.strip_suffix(')'))
    else {
        return attribute;
    };
    body.trim()
}

fn rust_attribute_has_name(attribute: &str, name: &str) -> bool {
    let attribute = attribute.trim();
    if attribute == name {
        return true;
    }
    let Some(rest) = attribute.strip_prefix(name) else {
        return false;
    };
    let rest = rest.trim_start();
    rest.starts_with('(') || rest.starts_with('=')
}

fn evaluate_trait_object_boundary_clarity(store: &EvidenceStore) -> Vec<Issue> {
    store
        .symbols
        .iter()
        .filter(|symbol| symbol.language == Language::Rust)
        .filter(|symbol| public_or_internal(symbol.visibility))
        .filter(|symbol| {
            symbol
                .return_annotation
                .as_deref()
                .is_some_and(|text| text.contains("dyn "))
                || symbol
                    .type_text
                    .as_deref()
                    .is_some_and(|text| text.contains("dyn "))
        })
        .map(|symbol| {
            issue_for_symbol(
                store,
                RuleMeta {
                    id: "Rust006",
                    name: "trait_object_boundary_clarity",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Symbol,
                    domain: Domain::Maintainability,
                    message: "Rust trait object 边界需要清晰性审查",
                },
                symbol,
            )
        })
        .collect()
}

fn evaluate_unsafe_contract(store: &EvidenceStore) -> Vec<Issue> {
    let mut issues = store
        .block_regions
        .iter()
        .filter(|block| rust_file(store, &block.file_id))
        .filter(|block| block.kind == "unsafe" && block.intent_comment_id.is_none())
        .map(|block| {
            issue_for_block(
                store,
                RuleMeta {
                    id: "Rust007",
                    name: "unsafe_contract",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Block,
                    domain: Domain::SafetyAdjacent,
                    message: "Rust unsafe 代码块需要契约审查",
                },
                block,
            )
        })
        .collect::<Vec<_>>();

    issues.extend(
        store
            .symbols
            .iter()
            .filter(|symbol| symbol.language == Language::Rust && symbol.is_unsafe)
            .map(|symbol| {
                issue_for_symbol(
                    store,
                    RuleMeta {
                        id: "Rust007",
                        name: "unsafe_contract",
                        kind: IssueKind::UnderReview,
                        scope: Scope::Block,
                        domain: Domain::SafetyAdjacent,
                        message: "Rust unsafe 函数需要契约审查",
                    },
                    symbol,
                )
            }),
    );
    issues
}

fn evaluate_async_blocking_policy(store: &EvidenceStore) -> Vec<Issue> {
    store
        .expressions
        .iter()
        .filter(|expression| rust_expression(store, expression))
        .filter(|expression| expression.kind == ExpressionKind::Call)
        .filter(|expression| {
            expression
                .callee
                .as_deref()
                .is_some_and(|callee| matches!(callee, "thread::sleep" | "std::fs"))
        })
        .filter(|expression| async_symbol_contains(store, expression))
        .map(|expression| {
            issue_for_expression(
                store,
                RuleMeta {
                    id: "Rust008",
                    name: "async_blocking_policy",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Block,
                    domain: Domain::SafetyAdjacent,
                    message: "Rust async 区域中的阻塞调用需要审查",
                },
                expression,
            )
        })
        .collect()
}

fn evaluate_await_holding_lock_policy(store: &EvidenceStore) -> Vec<Issue> {
    let locks = store
        .expressions
        .iter()
        .filter(|expression| rust_expression(store, expression))
        .filter(|expression| expression.kind == ExpressionKind::Lock)
        .collect::<Vec<_>>();
    store
        .expressions
        .iter()
        .filter(|expression| rust_expression(store, expression))
        .filter(|expression| expression.kind == ExpressionKind::Await)
        .filter(|await_expression| {
            locks.iter().any(|lock| {
                lock.module_id == await_expression.module_id
                    && start_line(&lock.range) < start_line(&await_expression.range)
                    && same_async_symbol_contains(store, lock, await_expression)
            })
        })
        .map(|expression| {
            issue_for_expression(
                store,
                RuleMeta {
                    id: "Rust009",
                    name: "await_holding_lock_policy",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Block,
                    domain: Domain::SafetyAdjacent,
                    message: "Rust 持锁 await 形态需要审查",
                },
                expression,
            )
        })
        .collect()
}

fn evaluate_panic_context_policy(store: &EvidenceStore) -> Vec<Issue> {
    store
        .expressions
        .iter()
        .filter(|expression| rust_expression(store, expression))
        .filter(|expression| expression.kind == ExpressionKind::Panic)
        .filter(|expression| !test_like_path(store, &expression.file_id))
        .map(|expression| {
            issue_for_expression(
                store,
                RuleMeta {
                    id: "Rust010",
                    name: "panic_context_policy",
                    kind: IssueKind::UnderReview,
                    scope: Scope::Expression,
                    domain: Domain::Maintainability,
                    message: "Rust panic 上下文需要审查",
                },
                expression,
            )
        })
        .collect()
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

fn rust_expression(store: &EvidenceStore, expression: &ExpressionFact) -> bool {
    rust_file(store, &expression.file_id)
}

fn rust_file(store: &EvidenceStore, file_id: &str) -> bool {
    store
        .file_units
        .iter()
        .any(|file| file.id == file_id && file.language == Language::Rust)
}

fn public_or_internal(visibility: SymbolVisibility) -> bool {
    matches!(
        visibility,
        SymbolVisibility::Public | SymbolVisibility::Internal
    )
}

fn async_symbol_contains(store: &EvidenceStore, expression: &ExpressionFact) -> bool {
    store
        .symbols
        .iter()
        .filter(|symbol| symbol.language == Language::Rust && symbol.is_async)
        .any(|symbol| {
            symbol.file_id == expression.file_id && range_contains(&symbol.range, &expression.range)
        })
}

fn same_async_symbol_contains(
    store: &EvidenceStore,
    left: &ExpressionFact,
    right: &ExpressionFact,
) -> bool {
    store
        .symbols
        .iter()
        .filter(|symbol| symbol.language == Language::Rust && symbol.is_async)
        .any(|symbol| {
            symbol.file_id == left.file_id
                && symbol.file_id == right.file_id
                && range_contains(&symbol.range, &left.range)
                && range_contains(&symbol.range, &right.range)
        })
}

fn range_contains(container: &str, nested: &str) -> bool {
    let container_start = start_line(container);
    let container_end = end_line(container);
    let nested_start = start_line(nested);
    matches!(
        (container_start, container_end, nested_start),
        (Some(start), Some(end), Some(line)) if start <= line && line <= end
    )
}

fn test_like_path(store: &EvidenceStore, file_id: &str) -> bool {
    store
        .file_units
        .iter()
        .find(|file| file.id == file_id)
        .is_some_and(|file| {
            let path = file.path.replace('\\', "/");
            path.contains("/tests/")
                || path.starts_with("tests/")
                || path.ends_with("_test.rs")
                || path.ends_with("/test.rs")
        })
}

fn start_line(range: &str) -> Option<usize> {
    range.split_once(':')?.0.parse().ok()
}

fn end_line(range: &str) -> Option<usize> {
    range.split_once('-')?.1.split_once(':')?.0.parse().ok()
}
