use std::collections::{HashMap, HashSet};

use crate::core::evidence::{
    DependencyEdgeFact, EvidenceStore, ExpressionFact, ExpressionKind, ModuleUnitFact, SymbolFact,
    SymbolKind,
};
use crate::core::issue::{Domain, Issue, IssueKind, Language, Scope};
use crate::core::profile::Profile;

const COLLECTIONS_ABC_NAMES: &[&str] = &[
    "Callable",
    "Iterable",
    "Iterator",
    "Mapping",
    "MutableMapping",
    "Sequence",
];

const OLD_STYLE_GENERICS: &[&str] = &["List", "Dict", "Tuple", "Set", "Optional", "Union"];

/// 返回已实现的 Python 规则 ID
pub fn implemented_rule_ids() -> Vec<&'static str> {
    vec![
        "Py001", "Py002", "Py003", "Py004", "Py005", "Py006", "Py007", "Py008",
    ]
}

/// 评估 Python 专属规则
pub fn evaluate(store: &EvidenceStore, _profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    issues.extend(evaluate_module_docstring_banned(store));
    issues.extend(evaluate_future_import_position(store));
    issues.extend(evaluate_future_annotations_consistency(store));
    issues.extend(evaluate_collections_abc_source(store));
    issues.extend(evaluate_annotation_completeness(store));
    issues.extend(evaluate_logging_handle_naming(store));
    issues.extend(evaluate_old_style_generics(store));
    issues.extend(evaluate_logging_lazy_formatting(store));
    issues
}

fn evaluate_module_docstring_banned(store: &EvidenceStore) -> Vec<Issue> {
    store
        .module_units
        .iter()
        .filter(|module| module.language == Language::Python && module.has_module_doc_region)
        .map(|module| {
            module_issue(
                store,
                "Py001",
                "module.docstring_banned",
                IssueKind::HardViolation,
                Domain::Documentation,
                "Python 模块级文档字符串不允许出现",
                module,
            )
        })
        .collect()
}

fn evaluate_future_import_position(store: &EvidenceStore) -> Vec<Issue> {
    let first_non_future_by_module = store
        .dependency_edges
        .iter()
        .filter(|edge| python_file(store, &edge.file_id))
        .filter(|edge| !is_future_annotations(edge))
        .fold(HashMap::<&str, usize>::new(), |mut lines, edge| {
            let line = start_line(&edge.range).unwrap_or(usize::MAX);
            lines
                .entry(edge.module_id.as_str())
                .and_modify(|current| *current = (*current).min(line))
                .or_insert(line);
            lines
        });

    let last_future_by_module = store
        .dependency_edges
        .iter()
        .filter(|edge| is_future_annotations(edge))
        .fold(HashMap::<&str, usize>::new(), |mut lines, edge| {
            let line = start_line(&edge.range).unwrap_or(usize::MAX);
            lines
                .entry(edge.module_id.as_str())
                .and_modify(|current| *current = (*current).max(line))
                .or_insert(line);
            lines
        });

    let mut issues = store
        .dependency_edges
        .iter()
        .filter(|edge| is_future_annotations(edge))
        .filter(|edge| {
            let line = start_line(&edge.range).unwrap_or(usize::MAX);
            first_non_future_by_module
                .get(edge.module_id.as_str())
                .is_some_and(|first_non_future| line > *first_non_future)
        })
        .map(|edge| {
            dependency_issue(
                store,
                "Py002",
                "future_import.position",
                IssueKind::HardViolation,
                Domain::Dependency,
                "future annotations 导入必须位于其他导入之前",
                edge,
            )
        })
        .collect::<Vec<_>>();

    for edge in store
        .dependency_edges
        .iter()
        .filter(|edge| is_future_annotations(edge))
    {
        let Some(last_future_line) = last_future_by_module.get(edge.module_id.as_str()) else {
            continue;
        };
        let Some(first_normal_line) = first_non_future_by_module.get(edge.module_id.as_str())
        else {
            continue;
        };
        let line = start_line(&edge.range).unwrap_or(usize::MAX);
        if line == *last_future_line && *first_normal_line == *last_future_line + 1 {
            issues.push(dependency_issue(
                store,
                "Py002",
                "future_import.position",
                IssueKind::HardViolation,
                Domain::Dependency,
                "future annotations 导入块后必须保留空行",
                edge,
            ));
        }
    }

    issues
}

fn evaluate_future_annotations_consistency(store: &EvidenceStore) -> Vec<Issue> {
    let future_modules = store
        .dependency_edges
        .iter()
        .filter(|edge| is_future_annotations(edge))
        .map(|edge| edge.module_id.as_str())
        .collect::<HashSet<_>>();
    if future_modules.is_empty() {
        return Vec::new();
    }

    store
        .module_units
        .iter()
        .filter(|module| module.language == Language::Python)
        .filter(|module| !future_modules.contains(module.id.as_str()))
        .filter(|module| module_has_type_annotations(store, &module.id))
        .map(|module| {
            module_issue(
                store,
                "Py003",
                "future_annotations.consistency",
                IssueKind::UnderReview,
                Domain::Typing,
                "类型标注文件需要审查 future annotations 一致性",
                module,
            )
        })
        .collect()
}

fn evaluate_collections_abc_source(store: &EvidenceStore) -> Vec<Issue> {
    store
        .dependency_edges
        .iter()
        .filter(|edge| python_file(store, &edge.file_id))
        .filter(|edge| edge.source == "typing")
        .filter(|edge| {
            imported_names(&edge.imported)
                .iter()
                .any(|name| COLLECTIONS_ABC_NAMES.contains(&name.as_str()))
        })
        .map(|edge| {
            dependency_issue(
                store,
                "Py004",
                "typing.collections_abc_source",
                IssueKind::HardViolation,
                Domain::Typing,
                "抽象集合类型必须从 collections.abc 导入",
                edge,
            )
        })
        .collect()
}

fn evaluate_annotation_completeness(store: &EvidenceStore) -> Vec<Issue> {
    store
        .symbols
        .iter()
        .filter(|symbol| symbol.language == Language::Python)
        .filter(|symbol| matches!(symbol.kind, SymbolKind::Function | SymbolKind::Method))
        .filter(|symbol| {
            symbol.return_annotation.is_none() || !symbol.missing_parameter_annotations.is_empty()
        })
        .map(|symbol| {
            symbol_issue(
                store,
                "Py005",
                "function.annotation_completeness",
                IssueKind::HardViolation,
                Domain::Typing,
                "Python 函数参数与返回值标注必须完整",
                symbol,
            )
        })
        .collect()
}

fn evaluate_logging_handle_naming(store: &EvidenceStore) -> Vec<Issue> {
    store
        .symbols
        .iter()
        .filter(|symbol| symbol.language == Language::Python)
        .filter(|symbol| symbol.type_text.as_deref() == Some("logging.getLogger"))
        .filter(|symbol| !matches!(symbol.name.as_str(), "logger" | "LOGGER" | "self.logger"))
        .map(|symbol| {
            symbol_issue(
                store,
                "Py006",
                "logging.handle_naming",
                IssueKind::HardViolation,
                Domain::Logging,
                "Python logger 句柄命名必须统一",
                symbol,
            )
        })
        .collect()
}

fn evaluate_old_style_generics(store: &EvidenceStore) -> Vec<Issue> {
    store
        .expressions
        .iter()
        .filter(|expression| expression.kind == ExpressionKind::TypeExpression)
        .filter(|expression| {
            expression
                .callee
                .as_deref()
                .is_some_and(|callee| OLD_STYLE_GENERICS.contains(&callee))
                || OLD_STYLE_GENERICS
                    .iter()
                    .any(|name| expression.text.starts_with(&format!("{name}[")))
                || OLD_STYLE_GENERICS
                    .iter()
                    .any(|name| expression.text.starts_with(&format!("typing.{name}[")))
        })
        .map(|expression| {
            expression_issue(
                store,
                "Py007",
                "typing.old_style_generics",
                IssueKind::HardViolation,
                Domain::Typing,
                "Python 类型表达式不允许使用旧式泛型",
                expression,
            )
        })
        .collect()
}

fn evaluate_logging_lazy_formatting(store: &EvidenceStore) -> Vec<Issue> {
    store
        .expressions
        .iter()
        .filter(|expression| expression.kind == ExpressionKind::LoggingCall)
        .filter(|expression| uses_eager_logging_format(expression))
        .map(|expression| {
            expression_issue(
                store,
                "Py008",
                "logging.lazy_formatting",
                IssueKind::HardViolation,
                Domain::Logging,
                "Python logging 调用必须使用 lazy formatting",
                expression,
            )
        })
        .collect()
}

fn is_future_annotations(edge: &DependencyEdgeFact) -> bool {
    edge.source == "__future__"
        && edge
            .imported
            .split(',')
            .map(str::trim)
            .any(|name| name == "annotations")
}

fn imported_names(imported: &str) -> Vec<String> {
    imported
        .split(',')
        .filter_map(|name| {
            let name = name
                .trim()
                .split_once(" as ")
                .map_or(name.trim(), |(name, _)| name.trim());
            (!name.is_empty()).then(|| name.to_string())
        })
        .collect()
}

fn module_has_type_annotations(store: &EvidenceStore, module_id: &str) -> bool {
    store.symbols.iter().any(|symbol| {
        symbol.module_id == module_id
            && (symbol.return_annotation.is_some() || symbol.type_text.is_some())
    })
}

fn python_file(store: &EvidenceStore, file_id: &str) -> bool {
    store
        .file_units
        .iter()
        .any(|file| file.id == file_id && file.language == Language::Python)
        || store
            .module_units
            .iter()
            .any(|module| module.file_id == file_id && module.language == Language::Python)
}

fn module_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    module: &ModuleUnitFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", module.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Module,
        domain,
    )
    .with_message(message)
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

fn dependency_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    edge: &DependencyEdgeFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", edge.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Module,
        domain,
    )
    .with_message(message)
    .with_evidence(edge.id.clone());
    if let Some(file) = store.file_units.iter().find(|file| file.id == edge.file_id) {
        issue = issue.with_location(file.language, file.path.clone(), edge.range.clone());
    } else {
        issue.range = Some(edge.range.clone());
    }
    issue
}

fn symbol_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    symbol: &SymbolFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", symbol.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Symbol,
        domain,
    )
    .with_message(message)
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

fn expression_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    expression: &ExpressionFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", expression.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Expression,
        domain,
    )
    .with_message(message)
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

fn uses_eager_logging_format(expression: &ExpressionFact) -> bool {
    let first_argument = expression
        .arguments
        .first()
        .map(String::as_str)
        .unwrap_or("");
    first_argument.starts_with("f\"")
        || first_argument.starts_with("f'")
        || expression.text.contains(".format(")
        || expression.text.contains(" % ")
        || is_preformatted_logging_value(first_argument)
}

fn is_preformatted_logging_value(argument: &str) -> bool {
    !argument.is_empty() && !argument.starts_with('"') && !argument.starts_with('\'')
}

fn start_line(range: &str) -> Option<usize> {
    range.split_once(':')?.0.parse().ok()
}
