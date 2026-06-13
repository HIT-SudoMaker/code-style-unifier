use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::sync::OnceLock;

use regex::Regex;

use crate::core::evidence::{
    BlockRegionFact, DependencyEdgeFact, DependencyGroup, DocRegionFact, EvidenceStore,
    ExpressionFact, FileUnitFact, LineSpanFact, PublicSurfaceFact, SymbolFact, SymbolKind,
    TextRole, TextSpanFact,
};
use crate::core::issue::{Domain, Issue, IssueKind, Language, Scope};
use crate::core::profile::Profile;

const IMPLEMENTATION_WORDS: &[&str] = &[
    "call",
    "calling",
    "create",
    "creating",
    "initialize",
    "initializing",
    "iterate",
    "iterating",
    "loop",
    "process",
    "set",
    "setting",
    "调用",
    "创建",
    "初始化",
    "循环",
    "设置",
    "遍历",
    "转换",
];

const VAGUE_STARTS: &[&str] = &["Handle ", "Process ", "Manage ", "处理", "管理"];

/// 返回已实现的 Core 规则 ID
pub fn implemented_rule_ids() -> Vec<&'static str> {
    vec![
        "Core001", "Core002", "Core003", "Core004", "Core005", "Core006", "Core007", "Core008",
        "Core009", "Core010", "Core023", "Core024", "Core025", "Core027", "Core011", "Core012",
        "Core013", "Core014", "Core015", "Core016", "Core017", "Core018", "Core019", "Core020",
        "Core021", "Core022", "Core026", "Core028",
    ]
}

/// 评估已实现的 Core 规则
pub fn evaluate(store: &EvidenceStore, profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    issues.extend(evaluate_project_file_dependency_rules(store, profile));
    issues.extend(evaluate_symbol_documentation_rules(store, profile));
    issues.extend(evaluate_symbol_naming_rules(store, profile));
    issues.extend(evaluate_block_line_rules(store, profile));
    issues.extend(evaluate_doc_layout_rules(store, profile));
    issues.extend(evaluate_term_policy(store, profile));
    issues.extend(evaluate_raw_error_boundaries(store));
    issues.extend(evaluate_terminal_punctuation(store));
    issues.extend(evaluate_summary_concision(store));
    issues.extend(evaluate_text_natural_language(store, profile));
    issues
}

/// 评估项目文件与依赖规则
pub fn evaluate_project_file_dependency_rules(
    store: &EvidenceStore,
    profile: &Profile,
) -> Vec<Issue> {
    let mut issues = Vec::new();
    issues.extend(evaluate_language_boundary(store));
    issues.extend(evaluate_generated_boundary(store));
    issues.extend(evaluate_dependency_cycle_risk(store));
    issues.extend(evaluate_dependency_direction_policy(store));
    issues.extend(evaluate_history_health(store, profile));
    issues.extend(evaluate_file_specific_names(store));
    issues.extend(evaluate_file_role_ambiguity(store));
    issues.extend(evaluate_dependency_grouping(store));
    issues.extend(evaluate_dependency_sorting(store));
    issues.extend(evaluate_dependency_broad_import(store));
    issues
}

fn evaluate_language_boundary(store: &EvidenceStore) -> Vec<Issue> {
    let languages = store
        .file_units
        .iter()
        .filter(|file| !file.excluded)
        .map(|file| file.language)
        .collect::<HashSet<_>>();
    if languages.len() > 1 {
        vec![project_issue(
            "Core001",
            "project.language_boundary",
            IssueKind::SoftFriction,
            Domain::Project,
            "项目包含多种语言，需要明确边界",
        )
        .with_evidence(store.workspace.id.clone())]
    } else {
        Vec::new()
    }
}

fn evaluate_generated_boundary(store: &EvidenceStore) -> Vec<Issue> {
    store
        .file_units
        .iter()
        .filter(|file| file.generated && !file.excluded)
        .map(|file| {
            file_issue(
                "Core002",
                "project.generated_boundary",
                IssueKind::SoftFriction,
                Domain::Project,
                "生成代码需要明确边界",
                file,
            )
        })
        .collect()
}

fn evaluate_dependency_cycle_risk(store: &EvidenceStore) -> Vec<Issue> {
    let mut edges = HashSet::new();
    let mut issues = Vec::new();
    for edge in &store.dependency_edges {
        let left = (edge.module_id.as_str(), edge.source.as_str());
        let right = (edge.source.as_str(), edge.module_id.as_str());
        if edges.contains(&right) {
            issues.push(dependency_issue(
                store,
                "Core003",
                "dependency.cycle_risk",
                IssueKind::SoftFriction,
                "依赖图存在环风险",
                Scope::Project,
                edge,
            ));
        }
        edges.insert(left);
    }
    issues
}

fn evaluate_dependency_direction_policy(store: &EvidenceStore) -> Vec<Issue> {
    store
        .dependency_edges
        .iter()
        .filter(|edge| edge.is_relative && edge.source.contains(".."))
        .map(|edge| {
            dependency_issue(
                store,
                "Core004",
                "dependency.direction_policy",
                IssueKind::SoftFriction,
                "依赖方向需要审查",
                Scope::Project,
                edge,
            )
        })
        .collect()
}

fn evaluate_history_health(store: &EvidenceStore, profile: &Profile) -> Vec<Issue> {
    let Some(history) = store.history_health else {
        return Vec::new();
    };
    if history.run_count <= profile.thresholds.history_max_runs
        && history.oldest_run_age_days <= profile.thresholds.history_max_days
        && history.total_bytes <= profile.thresholds.history_max_bytes
    {
        return Vec::new();
    }

    vec![project_issue(
        "Core005",
        "history.health",
        IssueKind::SoftFriction,
        Domain::History,
        "扫描记录超过保留策略",
    )
    .with_evidence(store.workspace.id.clone())]
}

fn evaluate_file_specific_names(store: &EvidenceStore) -> Vec<Issue> {
    store
        .file_units
        .iter()
        .filter(|file| active_file(file))
        .filter(|file| {
            let stem = file_stem(&file.path);
            matches!(
                stem.as_str(),
                "utils" | "util" | "helpers" | "helper" | "common" | "misc" | "base"
            )
        })
        .map(|file| {
            file_issue(
                "Core006",
                "file.specific_names",
                IssueKind::HardViolation,
                Domain::Style,
                "文件名需要表达具体职责",
                file,
            )
        })
        .collect()
}

fn evaluate_file_role_ambiguity(store: &EvidenceStore) -> Vec<Issue> {
    store
        .file_units
        .iter()
        .filter(|file| active_file(file))
        .filter(|file| {
            let stem = file_stem(&file.path);
            stem.contains("manager") || stem.contains("processor") || stem.contains("handler")
        })
        .map(|file| {
            file_issue(
                "Core007",
                "file.role_ambiguity",
                IssueKind::SoftFriction,
                Domain::Project,
                "文件职责命名存在歧义",
                file,
            )
        })
        .collect()
}

fn evaluate_dependency_grouping(store: &EvidenceStore) -> Vec<Issue> {
    let mut by_module: HashMap<&str, Vec<&DependencyEdgeFact>> = HashMap::new();
    for edge in &store.dependency_edges {
        if rust_module_path_dependency(store, edge) {
            continue;
        }
        by_module.entry(&edge.module_id).or_default().push(edge);
    }

    let mut issues = Vec::new();
    for edges in by_module.values() {
        let mut previous = None;
        for edge in edges {
            let rank = dependency_rank(edge.group);
            if previous.is_some_and(|previous| rank < previous) {
                issues.push(dependency_issue(
                    store,
                    "Core008",
                    "dependency.grouping",
                    IssueKind::HardViolation,
                    "依赖分组顺序不符合要求",
                    Scope::Module,
                    edge,
                ));
                break;
            }
            previous = Some(rank);
        }
    }
    issues
}

fn evaluate_dependency_sorting(store: &EvidenceStore) -> Vec<Issue> {
    let mut by_module_group: HashMap<(&str, DependencyGroup), Vec<&DependencyEdgeFact>> =
        HashMap::new();
    for edge in &store.dependency_edges {
        by_module_group
            .entry((&edge.module_id, edge.group))
            .or_default()
            .push(edge);
    }

    let mut issues = Vec::new();
    for edges in by_module_group.values() {
        let mut previous = "";
        for edge in edges {
            if !previous.is_empty() && edge.source.as_str() < previous {
                issues.push(dependency_issue(
                    store,
                    "Core009",
                    "dependency.sorting",
                    IssueKind::HardViolation,
                    "依赖组内排序不符合要求",
                    Scope::Module,
                    edge,
                ));
                break;
            }
            previous = edge.source.as_str();
        }
    }
    issues
}

fn evaluate_dependency_broad_import(store: &EvidenceStore) -> Vec<Issue> {
    store
        .dependency_edges
        .iter()
        .filter(|edge| edge.is_glob || edge.imported == "*")
        .map(|edge| {
            dependency_issue(
                store,
                "Core010",
                "dependency.broad_import",
                IssueKind::HardViolation,
                "不允许使用宽泛导入",
                Scope::Module,
                edge,
            )
        })
        .collect()
}

fn evaluate_symbol_documentation_rules(store: &EvidenceStore, _profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    for surface in &store.public_surfaces {
        if surface.visibility == "public"
            && !surface.has_doc_region
            && active_file_by_id(store, &surface.file_id)
        {
            issues.push(public_surface_issue(
                store,
                "Core011",
                "public_surface.required_docs",
                IssueKind::HardViolation,
                Domain::Documentation,
                "公开接口必须有契约文档",
                surface,
            ));
        }
        if surface.visibility == "internal" && surface.has_doc_region {
            issues.push(public_surface_issue(
                store,
                "Core013",
                "docs.internal_api_doc.review",
                IssueKind::UnderReview,
                Domain::Documentation,
                "内部接口文档需要审查",
                surface,
            ));
        }
    }

    for symbol in &store.symbols {
        if !matches!(symbol.kind, SymbolKind::Function | SymbolKind::Method) {
            continue;
        }
        if symbol.missing_parameter_annotations.is_empty() {
            continue;
        }
        let Some(doc_id) = symbol.doc_region_id.as_deref() else {
            continue;
        };
        let doc_text = doc_full_text(store, doc_id).unwrap_or_default();
        if !doc_text.contains("Args") && !doc_text.contains("参数") {
            issues.push(symbol_issue(
                store,
                "Core012",
                "docs.field_coverage",
                IssueKind::HardViolation,
                Domain::Documentation,
                "文档字段缺少参数契约",
                symbol,
            ));
        }
    }
    issues
}

fn evaluate_symbol_naming_rules(store: &EvidenceStore, profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    for symbol in &store.symbols {
        if active_file_by_id(store, &symbol.file_id) && violates_case_convention(symbol) {
            issues.push(symbol_issue(
                store,
                "Core014",
                "naming.case_convention",
                IssueKind::HardViolation,
                Domain::Naming,
                "符号命名大小写不符合约定",
                symbol,
            ));
        }

        if symbol_tokens(&symbol.name).iter().any(|token| {
            profile.term_policy.is_banned_abbreviation(token)
                && !profile.term_policy.is_allowed_abbreviation(token)
        }) {
            issues.push(symbol_issue(
                store,
                "Core015",
                "naming.abbreviation_policy",
                IssueKind::HardViolation,
                Domain::Naming,
                "符号包含禁用缩写",
                symbol,
            ));
        }

        if is_boolean_symbol(symbol) && !has_boolean_prefix(&symbol.name) {
            issues.push(symbol_issue(
                store,
                "Core016",
                "naming.boolean_predicate",
                IssueKind::UnderReview,
                Domain::Naming,
                "布尔谓词命名需要审查",
                symbol,
            ));
        }
    }
    issues
}

fn evaluate_block_line_rules(store: &EvidenceStore, profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    for block in &store.block_regions {
        if matches!(
            block.kind.as_str(),
            "complex" | "unsafe" | "preprocessor" | "allocation"
        ) && block.intent_comment_id.is_none()
        {
            issues.push(block_issue(
                store,
                "Core017",
                "comments.block_intent.required",
                IssueKind::UnderReview,
                Domain::Maintainability,
                "复杂代码块需要意图注释",
                block,
            ));
        }
    }

    let comment_suppressions = comment_suppressions(store);
    for line in &store.line_spans {
        if comment_suppressions
            .get(&(line.file_id.as_str(), line.line))
            .is_some_and(|suppression| !has_non_empty_suppression_reason(suppression))
        {
            issues.push(line_issue(
                store,
                "Core018",
                "suppression.reason_required",
                IssueKind::HardViolation,
                Domain::Maintainability,
                "抑制标记必须包含 reason",
                line,
            ));
        }
        if line.visual_width > profile.thresholds.line_length_limit {
            issues.push(line_issue(
                store,
                "Core019",
                "layout.line_length",
                IssueKind::HardViolation,
                Domain::Style,
                "行宽超过配置限制",
                line,
            ));
        }
    }
    issues
}

fn evaluate_doc_layout_rules(store: &EvidenceStore, _profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    for doc in &store.doc_regions {
        let text = doc_full_text(store, &doc.id).unwrap_or_default();
        if section_before(&text, "Returns", "Args") {
            issues.push(doc_issue(
                store,
                "Core020",
                "docs.section_order",
                IssueKind::HardViolation,
                Domain::Documentation,
                "文档章节顺序不符合要求",
                doc,
            ));
        }
        if has_inconsistent_field_indent(&text) {
            issues.push(doc_issue(
                store,
                "Core021",
                "docs.field_alignment",
                IssueKind::HardViolation,
                Domain::Documentation,
                "文档字段缩进不一致",
                doc,
            ));
        }
        if text.contains("\n\n\n") {
            issues.push(doc_issue(
                store,
                "Core022",
                "docs.physical_layout",
                IssueKind::HardViolation,
                Domain::Documentation,
                "文档物理布局不符合约定",
                doc,
            ));
        }
    }
    issues
}

fn evaluate_term_policy(store: &EvidenceStore, profile: &Profile) -> Vec<Issue> {
    let mut issues = Vec::new();
    for text in &store.text_spans {
        if text_tokens(&text.normalized_text).iter().any(|token| {
            profile.term_policy.is_banned_abbreviation(token)
                && !profile.term_policy.is_allowed_abbreviation(token)
        }) {
            issues.push(issue_for_text(
                store,
                "Core026",
                "text.term_policy",
                IssueKind::HardViolation,
                Domain::Style,
                "文本包含禁用术语缩写",
                text,
            ));
        }
    }
    issues
}

fn evaluate_raw_error_boundaries(store: &EvidenceStore) -> Vec<Issue> {
    store
        .expressions
        .iter()
        .filter(|expression| {
            matches!(
                expression.kind,
                crate::core::evidence::ExpressionKind::ErrorMessage
            ) || expression
                .callee
                .as_deref()
                .is_some_and(|callee| callee.contains("Error"))
        })
        .filter(|expression| expression.text.contains('"') || expression.text.contains('\''))
        .map(|expression| {
            expression_issue(
                store,
                "Core028",
                "error.raw_message_boundary",
                IssueKind::UnderReview,
                Domain::Maintainability,
                "原始错误消息边界需要审查",
                expression,
            )
        })
        .collect()
}

/// 判断文本是否疑似以英文自然语言为主
pub fn appears_english(text: &str) -> bool {
    let letters = text
        .chars()
        .filter(|character| character.is_ascii_alphabetic())
        .count();
    let chinese = text.chars().filter(|character| is_cjk(*character)).count();
    if chinese > 0 && letters <= chinese * 4 {
        return false;
    }
    letters >= 8 && letters > chinese * 2
}

/// 判断摘要是否需要精炼审查
pub fn needs_concision_review(symbol_name: &str, summary: &str) -> bool {
    if summary.chars().count() > 80 {
        return true;
    }

    let lowered = summary.to_ascii_lowercase();
    let words = english_words(&lowered);
    if IMPLEMENTATION_WORDS
        .iter()
        .any(|word| words.contains(*word) || summary.contains(word))
    {
        return true;
    }

    if VAGUE_STARTS
        .iter()
        .any(|prefix| summary.starts_with(prefix))
    {
        return true;
    }

    let has_chinese = summary.chars().any(is_cjk);
    let symbol_tokens: Vec<_> = symbol_name
        .trim_matches('_')
        .to_ascii_lowercase()
        .split('_')
        .filter(|token| token.len() > 2)
        .map(str::to_string)
        .collect();
    let overlap = symbol_tokens
        .iter()
        .filter(|token| words.contains(token.as_str()))
        .count();

    !has_chinese && !symbol_tokens.is_empty() && overlap >= std::cmp::min(2, symbol_tokens.len())
}

/// 评估文档摘要结尾标点
pub fn evaluate_terminal_punctuation(store: &EvidenceStore) -> Vec<Issue> {
    store
        .text_spans
        .iter()
        .filter_map(|text| match (text.role, text.terminal_punctuation) {
            (TextRole::DocSummary, Some('。')) => Some(issue_for_text(
                store,
                "Core023",
                "docs.summary.chinese_period_forbidden",
                IssueKind::HardViolation,
                Domain::Documentation,
                "文档摘要不能以中文句号结尾",
                text,
            )),
            (TextRole::DocSummary, Some('.')) => Some(issue_for_text(
                store,
                "Core024",
                "docs.summary.english_period_review",
                IssueKind::UnderReview,
                Domain::Documentation,
                "文档摘要以英文句号结尾，需要审查",
                text,
            )),
            _ => None,
        })
        .collect()
}

/// 评估文档摘要是否需要精炼
pub fn evaluate_summary_concision(store: &EvidenceStore) -> Vec<Issue> {
    store
        .doc_regions
        .iter()
        .filter_map(|doc| {
            let text = store
                .text_spans
                .iter()
                .find(|span| span.id == doc.summary_text_id)?;
            if needs_concision_review(&doc.symbol_name, &text.normalized_text) {
                Some(issue_for_text(
                    store,
                    "Core025",
                    "docs.summary.concise_contract",
                    IssueKind::UnderReview,
                    Domain::Documentation,
                    "文档摘要需要精炼审查",
                    text,
                ))
            } else {
                None
            }
        })
        .collect()
}

/// 评估内部文本是否需要自然语言偏好审查
pub fn evaluate_text_natural_language(store: &EvidenceStore, _profile: &Profile) -> Vec<Issue> {
    store
        .text_spans
        .iter()
        .filter(|text| matches!(text.role, TextRole::Comment | TextRole::DocSummary))
        .filter(|text| appears_english(&text.normalized_text))
        .map(|text| {
            issue_for_text(
                store,
                "Core027",
                "text.natural_language.review",
                IssueKind::UnderReview,
                Domain::Style,
                "内部文本疑似使用英文，需要审查是否应改为中文",
                text,
            )
        })
        .collect()
}

fn english_words(text: &str) -> HashSet<String> {
    static WORD_RE: OnceLock<Regex> = OnceLock::new();
    WORD_RE
        .get_or_init(|| Regex::new(r"[a-zA-Z]+").expect("word regex should compile"))
        .find_iter(text)
        .map(|item| item.as_str().to_string())
        .collect()
}

fn issue_for_text(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    text: &TextSpanFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", text.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Text,
        domain,
    )
    .with_message(message)
    .with_evidence(text.id.clone());

    if let Some(file) = store.file_units.iter().find(|file| file.id == text.file_id) {
        issue = issue.with_location(file.language, file.path.clone(), text.range.clone());
    } else {
        issue.range = Some(text.range.clone());
    }

    issue
}

fn project_issue(rule: &str, name: &str, kind: IssueKind, domain: Domain, message: &str) -> Issue {
    Issue::new(
        format!("issue:{rule}:workspace"),
        kind,
        rule,
        name,
        Scope::Project,
        domain,
    )
    .with_message(message)
}

fn file_issue(
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    file: &FileUnitFact,
) -> Issue {
    Issue::new(
        format!("issue:{rule}:{}", file.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::File,
        domain,
    )
    .with_location(file.language, file.path.clone(), "1:1-1:1")
    .with_message(message)
    .with_evidence(file.id.clone())
}

fn dependency_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    message: &str,
    scope: Scope,
    edge: &DependencyEdgeFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", edge.id.replace(':', "_")),
        kind,
        rule,
        name,
        scope,
        Domain::Dependency,
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

fn public_surface_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    surface: &PublicSurfaceFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", surface.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Symbol,
        domain,
    )
    .with_message(message)
    .with_evidence(surface.id.clone());
    if let Some(file) = store
        .file_units
        .iter()
        .find(|file| file.id == surface.file_id)
    {
        issue = issue.with_location(file.language, file.path.clone(), surface.range.clone());
    } else {
        issue.range = Some(surface.range.clone());
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

fn block_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    block: &BlockRegionFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", block.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Block,
        domain,
    )
    .with_message(message)
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

fn line_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    line: &LineSpanFact,
) -> Issue {
    let range = format!("{}:1-{}:1", line.line, line.line);
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", line.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Line,
        domain,
    )
    .with_message(message)
    .with_evidence(line.id.clone());
    if let Some(file) = store.file_units.iter().find(|file| file.id == line.file_id) {
        issue = issue.with_location(file.language, file.path.clone(), range);
    } else {
        issue.range = Some(range);
    }
    issue
}

fn doc_issue(
    store: &EvidenceStore,
    rule: &str,
    name: &str,
    kind: IssueKind,
    domain: Domain,
    message: &str,
    doc: &DocRegionFact,
) -> Issue {
    let mut issue = Issue::new(
        format!("issue:{rule}:{}", doc.id.replace(':', "_")),
        kind,
        rule,
        name,
        Scope::Expression,
        domain,
    )
    .with_message(message)
    .with_evidence(doc.id.clone());
    if let Some(file) = store.file_units.iter().find(|file| file.id == doc.file_id) {
        issue = issue.with_location(file.language, file.path.clone(), doc.range.clone());
    } else {
        issue.range = Some(doc.range.clone());
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
        Scope::Text,
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

fn file_stem(path: &str) -> String {
    path.rsplit('/')
        .next()
        .unwrap_or(path)
        .split('.')
        .next()
        .unwrap_or(path)
        .to_ascii_lowercase()
}

fn active_file(file: &FileUnitFact) -> bool {
    !file.excluded && !file.generated
}

fn active_file_by_id(store: &EvidenceStore, file_id: &str) -> bool {
    store
        .file_units
        .iter()
        .find(|file| file.id == file_id)
        .is_none_or(active_file)
}

fn doc_full_text(store: &EvidenceStore, doc_id: &str) -> Option<String> {
    let doc = store.doc_regions.iter().find(|doc| doc.id == doc_id)?;
    if let Some(full_text_id) = doc.full_text_id.as_deref() {
        if let Some(text) = store.text_spans.iter().find(|text| text.id == full_text_id) {
            return Some(text.normalized_text.clone());
        }
    }
    store
        .text_spans
        .iter()
        .find(|text| text.id == doc.summary_text_id)
        .map(|text| text.normalized_text.clone())
}

fn violates_case_convention(symbol: &SymbolFact) -> bool {
    if symbol.language == Language::Rust && has_rust_abi_name_evidence(symbol) {
        return false;
    }

    match symbol.kind {
        SymbolKind::Function | SymbolKind::Method | SymbolKind::Variable | SymbolKind::Field => {
            symbol
                .name
                .chars()
                .any(|character| character.is_ascii_uppercase())
        }
        SymbolKind::Class | SymbolKind::Struct | SymbolKind::Enum | SymbolKind::Trait => false,
        _ => false,
    }
}

fn has_rust_abi_name_evidence(symbol: &SymbolFact) -> bool {
    if !matches!(symbol.kind, SymbolKind::Function | SymbolKind::Method) {
        return false;
    }

    let type_text = symbol.type_text.as_deref().unwrap_or_default();
    let has_abi = has_rust_extern_abi(type_text);
    let has_export_attr = symbol
        .attributes
        .iter()
        .any(|attribute| is_rust_export_attribute(attribute));
    let has_reasoned_allow = symbol
        .attributes
        .iter()
        .any(|attribute| is_reasoned_non_snake_case_allow(attribute));

    has_abi && has_export_attr && has_reasoned_allow
}

fn has_rust_extern_abi(type_text: &str) -> bool {
    let normalized = type_text.replace('"', "");
    let tokens = normalized.split_whitespace().collect::<Vec<_>>();
    tokens
        .windows(2)
        .any(|tokens| matches!(tokens, ["extern", "C"] | ["extern", "system"]))
}

fn is_rust_export_attribute(attribute: &str) -> bool {
    let attribute = rust_attribute_without_unsafe_wrapper(attribute);
    attribute == "no_mangle" || rust_attribute_has_name(attribute, "export_name")
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

fn is_reasoned_non_snake_case_allow(attribute: &str) -> bool {
    let Some(body) = attribute
        .trim()
        .strip_prefix("allow(")
        .and_then(|attribute| attribute.strip_suffix(')'))
    else {
        return false;
    };

    let mut has_non_snake_case = false;
    let mut has_reason = false;
    for item in body.split(',').map(str::trim) {
        if item == "non_snake_case" {
            has_non_snake_case = true;
        }
        if item
            .strip_prefix("reason")
            .is_some_and(|rest| rest.trim_start().starts_with('='))
        {
            has_reason = true;
        }
    }

    has_non_snake_case && has_reason
}

fn symbol_tokens(name: &str) -> Vec<String> {
    name.split('_')
        .flat_map(split_camel_token)
        .map(|token| token.to_ascii_lowercase())
        .filter(|token| !token.is_empty())
        .collect()
}

fn text_tokens(text: &str) -> Vec<String> {
    text.split(|character: char| !character.is_ascii_alphanumeric() && character != '_')
        .flat_map(symbol_tokens)
        .collect()
}

fn split_camel_token(token: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut current = String::new();
    for character in token.chars() {
        if character.is_ascii_uppercase() && !current.is_empty() {
            parts.push(current);
            current = String::new();
        }
        current.push(character);
    }
    if !current.is_empty() {
        parts.push(current);
    }
    parts
}

fn is_boolean_symbol(symbol: &SymbolFact) -> bool {
    symbol
        .return_annotation
        .as_deref()
        .is_some_and(is_bool_text)
        || symbol.type_text.as_deref().is_some_and(is_bool_text)
}

fn is_bool_text(value: &str) -> bool {
    matches!(value.trim(), "bool" | "Bool" | "boolean" | "Boolean")
}

fn has_boolean_prefix(name: &str) -> bool {
    [
        "is_",
        "has_",
        "can_",
        "needs_",
        "requires_",
        "allows_",
        "uses_",
    ]
    .iter()
    .any(|prefix| name.starts_with(prefix))
}

fn has_non_empty_suppression_reason(suppression: &str) -> bool {
    static REASON: OnceLock<Regex> = OnceLock::new();
    let reason = REASON.get_or_init(|| Regex::new(r"\breason\s*=\s*(?P<reason>\S.*)").unwrap());
    reason
        .captures(suppression)
        .and_then(|captures| captures.name("reason"))
        .is_some_and(|reason| !reason.as_str().trim().is_empty())
}

fn comment_suppressions(store: &EvidenceStore) -> std::collections::BTreeMap<(&str, usize), &str> {
    store
        .text_spans
        .iter()
        .filter(|text| text.role == TextRole::Comment)
        .filter(|text| text.normalized_text.contains("csu:"))
        .filter_map(|text| {
            let line = text
                .range
                .split(':')
                .next()
                .and_then(|value| value.parse::<usize>().ok())?;
            Some(((text.file_id.as_str(), line), text.normalized_text.as_str()))
        })
        .collect()
}

fn section_before(text: &str, first: &str, second: &str) -> bool {
    let Some(first_index) = text.find(first) else {
        return false;
    };
    let Some(second_index) = text.find(second) else {
        return false;
    };
    first_index < second_index
}

fn has_inconsistent_field_indent(text: &str) -> bool {
    let mut current_section: Option<&'static str> = None;
    let mut current_section_indent: Option<usize> = None;
    let mut indents_by_section: BTreeMap<&'static str, BTreeSet<usize>> = BTreeMap::new();

    for line in text.lines() {
        let trimmed = line.trim();
        let indent = line_indent(line);

        if trimmed.is_empty() {
            continue;
        }

        if let Some(section) = doc_field_section(trimmed) {
            current_section = Some(section);
            current_section_indent = Some(indent);
            continue;
        }

        if current_section_indent
            .is_some_and(|section_indent| is_doc_section_boundary(trimmed, indent, section_indent))
        {
            current_section = None;
            current_section_indent = None;
            continue;
        }

        let Some(section) = current_section else {
            continue;
        };

        if let Some(indent) = doc_field_indent(line) {
            indents_by_section
                .entry(section)
                .or_default()
                .insert(indent);
        }
    }

    indents_by_section.values().any(|indents| indents.len() > 1)
}

fn doc_field_section(trimmed: &str) -> Option<&'static str> {
    match trimmed {
        "Args:" | "Arguments:" | "Parameters:" => Some("args"),
        "Attributes:" => Some("attributes"),
        "Returns:" | "Yields:" => Some("returns"),
        "Raises:" | "Errors:" => Some("raises"),
        _ => None,
    }
}

fn is_doc_section_boundary(trimmed: &str, indent: usize, current_section_indent: usize) -> bool {
    !trimmed.is_empty() && indent <= current_section_indent
}

fn doc_field_indent(line: &str) -> Option<usize> {
    let trimmed = line.trim_start();
    let indent = line_indent(line);

    if indent == 0 || !trimmed.contains(':') {
        return None;
    }

    let (name, value) = trimmed.split_once(':')?;
    if name.is_empty() || value.trim().is_empty() {
        return None;
    }

    if name
        .chars()
        .all(|ch| ch.is_alphanumeric() || ch == '_' || ch == '-' || ch == '`')
    {
        Some(indent)
    } else {
        None
    }
}

fn line_indent(line: &str) -> usize {
    line.len().saturating_sub(line.trim_start().len())
}

fn dependency_rank(group: DependencyGroup) -> usize {
    match group {
        DependencyGroup::Future => 0,
        DependencyGroup::Standard => 1,
        DependencyGroup::ThirdParty => 2,
        DependencyGroup::Local => 3,
        DependencyGroup::Unknown => 4,
    }
}

fn rust_module_path_dependency(store: &EvidenceStore, edge: &DependencyEdgeFact) -> bool {
    matches!(edge.source.as_str(), "crate" | "self" | "super")
        && store
            .file_units
            .iter()
            .any(|file| file.id == edge.file_id && file.language == Language::Rust)
}

fn is_cjk(character: char) -> bool {
    ('\u{4e00}'..='\u{9fff}').contains(&character)
}
