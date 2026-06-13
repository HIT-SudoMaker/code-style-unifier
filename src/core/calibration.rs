use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::core::issue::{Issue, IssueKind};

/// 禁止作为校准依据的数量导向理由片段
pub const BANNED_COUNT_RATIONALES: &[&str] = &[
    concat!("too many ", "findings"),
    concat!("reduce ", "findings"),
    "findings too many",
    concat!("reduce the ", "count"),
    concat!("findings ", "count is high"),
    "too noisy",
    "too much noise",
    "数量太多",
    concat!("数量", "偏高"),
    concat!("减少", "数量"),
    "降低数量",
    concat!("噪音", "太多"),
];

const REQUIRED_RATIONALE_TERMS: &[&str] = &[
    "事实", "规则", "级别", "边界", "profile", "evidence", "rule", "fact", "kind", "boundary",
];

/// 记录校准样本对规则判断结果的人工标注
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CalibrationLabel {
    /// 当前判断正确
    TruePositive,
    /// 当前判断误报
    FalsePositive,
    /// 当前判断漏报
    FalseNegative,
    /// 当前判断级别错误
    WrongKind,
    /// 预期结果应进入复核
    UnderReviewExpected,
    /// 外部风格要求不匹配
    ExternalStyleMismatch,
}

/// 记录校准样本要求采取的规则维护动作
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CalibrationAction {
    /// 保持当前规则
    KeepRule,
    /// 修正事实提取
    FixFactExtraction,
    /// 收窄规则契约
    NarrowRuleContract,
    /// 扩展规则契约
    BroadenRuleContract,
    /// 修改问题级别
    ChangeIssueKind,
    /// 增加配置策略
    AddProfilePolicy,
    /// 增加回归夹具
    AddRegressionFixture,
}

/// 描述一条可验证的规则校准样本
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CalibrationCase {
    /// 校准样本标识
    pub case_id: String,
    /// 规则标识
    pub rule: String,
    /// 关联问题标识
    pub issue_id: Option<String>,
    /// 人工标注结果
    pub label: CalibrationLabel,
    /// 实际观察到的问题级别
    pub observed_kind: Option<IssueKind>,
    /// 期望的问题级别
    pub expected_kind: Option<IssueKind>,
    /// 关联文件路径
    pub path: Option<String>,
    /// 关联源码范围
    pub range: Option<String>,
    /// 支撑校准判断的证据引用
    pub evidence: Vec<String>,
    /// 可追踪的人工判断理由
    pub rationale: String,
    /// 后续维护动作
    pub action: CalibrationAction,
}

impl CalibrationCase {
    /// 校验校准样本是否具备可追踪的判断依据
    pub fn validate(&self) -> Result<(), String> {
        if self.case_id.trim().is_empty() {
            return Err("case_id must not be empty".to_string());
        }
        if self.rule.trim().is_empty() {
            return Err("rule must not be empty".to_string());
        }
        if self.rationale.chars().count() < 18 {
            return Err("rationale must be at least 18 characters".to_string());
        }
        if contains_term(&self.rationale, BANNED_COUNT_RATIONALES) {
            return Err("rationale must not optimize for findings count".to_string());
        }
        if !contains_term(&self.rationale, REQUIRED_RATIONALE_TERMS) {
            return Err(
                "rationale must include traceable fact, rule, kind, or boundary terms".to_string(),
            );
        }
        if self.evidence.is_empty() {
            return Err("evidence must not be empty".to_string());
        }
        if self.evidence.iter().any(|entry| entry.trim().is_empty()) {
            return Err("evidence entries must not be empty".to_string());
        }
        if matches!(
            self.label,
            CalibrationLabel::WrongKind
                | CalibrationLabel::UnderReviewExpected
                | CalibrationLabel::FalseNegative
        ) && self.expected_kind.is_none()
        {
            return Err("expected_kind is required for this label".to_string());
        }
        if self.label == CalibrationLabel::FalseNegative {
            if self.observed_kind.is_some() {
                return Err("false_negative must not have observed_kind".to_string());
            }
            if self.issue_id.is_some() {
                return Err("false_negative must not have issue_id".to_string());
            }
        } else {
            if self.observed_kind.is_none() {
                return Err("non-false_negative cases require observed_kind".to_string());
            }
            match self.issue_id.as_deref() {
                Some(issue_id) if !issue_id.trim().is_empty() => {}
                Some(_) => {
                    return Err("non-false_negative cases require nonempty issue_id".to_string());
                }
                None => return Err("non-false_negative cases require issue_id".to_string()),
            }
        }

        Ok(())
    }

    /// 构造用于测试的有效校准样本
    pub fn valid_for_test(
        case_id: impl Into<String>,
        rule: impl Into<String>,
        label: CalibrationLabel,
        action: CalibrationAction,
    ) -> Self {
        let case_id = case_id.into();
        let rule = rule.into();
        let expected_kind = if matches!(
            label,
            CalibrationLabel::WrongKind
                | CalibrationLabel::UnderReviewExpected
                | CalibrationLabel::FalseNegative
        ) {
            Some(IssueKind::UnderReview)
        } else {
            None
        };
        let issue_id = if label == CalibrationLabel::FalseNegative {
            None
        } else {
            Some(format!("issue:{rule}:test"))
        };
        let observed_kind = if label == CalibrationLabel::FalseNegative {
            None
        } else {
            Some(IssueKind::HardViolation)
        };

        Self {
            case_id,
            rule,
            issue_id,
            label,
            observed_kind,
            expected_kind,
            path: Some("src/example.rs".to_string()),
            range: Some("1:1-1:1".to_string()),
            evidence: vec!["ev:test:calibration".to_string()],
            rationale: "事实与规则边界已核对，issue 级别和 evidence 支持当前校准判断".to_string(),
            action,
        }
    }
}

/// 汇总一组校准样本的统计结果和后续动作
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CalibrationReport {
    /// 校准报告结构版本
    pub schema_version: String,
    /// 校准样本总数
    pub case_count: usize,
    /// 是否把发现数量作为优化目标
    pub findings_count_is_optimization_goal: bool,
    /// 需要执行维护动作的校准样本标识
    pub actionable_case_ids: Vec<String>,
    /// 按规则汇总的校准结果
    pub by_rule: BTreeMap<String, RuleCalibrationSummary>,
}

impl CalibrationReport {
    /// 从校准样本生成汇总报告
    pub fn from_cases(cases: &[CalibrationCase]) -> Result<Self, String> {
        let mut actionable_case_ids = Vec::new();
        let mut by_rule = BTreeMap::new();

        for case in cases {
            case.validate()?;

            if !matches!(
                case.action,
                CalibrationAction::KeepRule | CalibrationAction::AddRegressionFixture
            ) {
                actionable_case_ids.push(case.case_id.clone());
            }

            let summary = by_rule
                .entry(case.rule.clone())
                .or_insert_with(RuleCalibrationSummary::default);
            summary.case_count += 1;
            *summary
                .label_counts
                .entry(label_name(case.label).to_string())
                .or_insert(0) += 1;
            *summary
                .action_counts
                .entry(action_name(case.action).to_string())
                .or_insert(0) += 1;
        }

        Ok(Self {
            schema_version: "1".to_string(),
            case_count: cases.len(),
            findings_count_is_optimization_goal: false,
            actionable_case_ids,
            by_rule,
        })
    }
}

/// 从 JSON 数组读取检查输出问题
pub fn read_issues_json(input: &str) -> Result<Vec<Issue>, String> {
    serde_json::from_str(input).map_err(|err| format!("failed to parse issues json: {err}"))
}

/// 从 JSON Lines 读取并校验校准样本
pub fn read_calibration_cases_jsonl(input: &str) -> Result<Vec<CalibrationCase>, String> {
    let mut cases = Vec::new();

    for (index, line) in input.lines().enumerate() {
        let line_number = index + 1;
        let trimmed = line.trim();

        if trimmed.is_empty() {
            continue;
        }

        let case = serde_json::from_str::<CalibrationCase>(trimmed).map_err(|err| {
            format!("line {line_number}: failed to parse calibration case: {err}")
        })?;

        case.validate()
            .map_err(|err| format!("line {line_number}: invalid calibration case: {err}"))?;

        cases.push(case);
    }

    Ok(cases)
}

/// 校验非漏报样本引用的真实问题输出
pub fn validate_cases_against_issues(
    cases: &[CalibrationCase],
    issues: &[Issue],
) -> Result<(), String> {
    let issue_ids = issues
        .iter()
        .map(|issue| issue.id.as_str())
        .collect::<BTreeSet<_>>();
    let issues_by_id = issues
        .iter()
        .map(|issue| (issue.id.as_str(), issue))
        .collect::<BTreeMap<_, _>>();

    for case in cases {
        case.validate()?;

        if case.label == CalibrationLabel::FalseNegative {
            continue;
        }

        let issue_id = case
            .issue_id
            .as_deref()
            .ok_or_else(|| format!("case {} requires issue_id", case.case_id))?;

        if !issue_ids.contains(issue_id) {
            return Err(format!(
                "case {} references missing issue_id {}",
                case.case_id, issue_id
            ));
        }

        let issue = issues_by_id
            .get(issue_id)
            .expect("issue id set and map are built from the same issues");

        if case.rule != issue.rule {
            return Err(format!(
                "case {} rule {} does not match issue {} rule {}",
                case.case_id, case.rule, issue.id, issue.rule
            ));
        }

        if case.observed_kind != Some(issue.kind) {
            return Err(format!(
                "case {} observed_kind {:?} does not match issue {} kind {:?}",
                case.case_id, case.observed_kind, issue.id, issue.kind
            ));
        }

        if case.path != issue.path {
            return Err(format!(
                "case {} path {:?} does not match issue {} path {:?}",
                case.case_id, case.path, issue.id, issue.path
            ));
        }

        if case.range != issue.range {
            return Err(format!(
                "case {} range {:?} does not match issue {} range {:?}",
                case.case_id, case.range, issue.id, issue.range
            ));
        }

        if case.evidence != issue.evidence {
            return Err(format!(
                "case {} evidence does not match issue evidence for {}",
                case.case_id, issue.id
            ));
        }
    }

    Ok(())
}

/// 汇总单条规则下校准样本的标注和动作分布
#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct RuleCalibrationSummary {
    /// 当前规则的校准样本数
    pub case_count: usize,
    /// 按标注结果统计的样本数
    pub label_counts: BTreeMap<String, usize>,
    /// 按维护动作统计的样本数
    pub action_counts: BTreeMap<String, usize>,
}

fn label_name(label: CalibrationLabel) -> &'static str {
    match label {
        CalibrationLabel::TruePositive => "true_positive",
        CalibrationLabel::FalsePositive => "false_positive",
        CalibrationLabel::FalseNegative => "false_negative",
        CalibrationLabel::WrongKind => "wrong_kind",
        CalibrationLabel::UnderReviewExpected => "under_review_expected",
        CalibrationLabel::ExternalStyleMismatch => "external_style_mismatch",
    }
}

fn action_name(action: CalibrationAction) -> &'static str {
    match action {
        CalibrationAction::KeepRule => "keep_rule",
        CalibrationAction::FixFactExtraction => "fix_fact_extraction",
        CalibrationAction::NarrowRuleContract => "narrow_rule_contract",
        CalibrationAction::BroadenRuleContract => "broaden_rule_contract",
        CalibrationAction::ChangeIssueKind => "change_issue_kind",
        CalibrationAction::AddProfilePolicy => "add_profile_policy",
        CalibrationAction::AddRegressionFixture => "add_regression_fixture",
    }
}

fn contains_term(text: &str, terms: &[&str]) -> bool {
    let ascii_lower = text.to_ascii_lowercase();

    terms.iter().any(|term| {
        if term.is_ascii() {
            ascii_lower.contains(&term.to_ascii_lowercase())
        } else {
            text.contains(term)
        }
    })
}
