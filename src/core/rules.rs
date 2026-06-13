use std::collections::HashSet;

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::core::issue::{Domain, IssueKind, Language, Scope};

/// 读取后的规则目录及其规则契约列表
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuleCatalog {
    /// 规则目录结构版本
    pub catalog_version: String,
    /// 目录中的规则契约列表
    pub rules: Vec<RuleContract>,
}

impl RuleCatalog {
    /// 从 TOML 文本读取并校验规则目录
    pub fn from_toml_str(input: &str) -> Result<Self, RuleCatalogError> {
        let catalog: Self = toml::from_str(input)?;
        catalog.validate()?;
        Ok(catalog)
    }

    /// 按规则 ID 查找目录中的规则契约
    pub fn get(&self, id: &str) -> Option<&RuleContract> {
        self.rules.iter().find(|rule| rule.id == id)
    }

    /// 规则目录输出视图
    pub fn to_view(&self) -> RuleCatalogView {
        RuleCatalogView {
            catalog_version: self.catalog_version.clone(),
            findings_count_is_optimization_goal: false,
            rules: self.rules.clone(),
        }
    }

    fn validate(&self) -> Result<(), RuleCatalogError> {
        let mut ids = HashSet::new();
        let mut names = HashSet::new();

        for rule in &self.rules {
            if !ids.insert(rule.id.as_str()) {
                return Err(RuleCatalogError::Validation(format!(
                    "duplicate rule id: {}",
                    rule.id
                )));
            }
            if !names.insert(rule.name.as_str()) {
                return Err(RuleCatalogError::Validation(format!(
                    "duplicate rule name: {}",
                    rule.name
                )));
            }
            rule.validate()?;
        }

        Ok(())
    }
}

/// 承载规则目录命令输出的稳定视图
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct RuleCatalogView {
    /// 规则目录版本
    pub catalog_version: String,
    /// 是否把发现数量作为优化目标
    pub findings_count_is_optimization_goal: bool,
    /// 规则契约列表
    pub rules: Vec<RuleContract>,
}

/// 描述规则目录中可执行规则的公共契约
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuleContract {
    /// 规则 ID
    pub id: String,
    /// 规则名称
    pub name: String,
    /// 规则默认问题级别
    pub kind: IssueKind,
    /// 规则定位范围
    pub scope: Scope,
    /// 规则所属治理领域
    pub domain: Domain,
    /// 规则适用的语言集合
    pub languages: Vec<Language>,
    /// 规则是否默认启用
    pub default_enabled: bool,
    /// 规则来源说明
    pub origin: String,
    /// 支撑规则的来源 ID 列表
    pub source_ids: Vec<String>,
    /// 规则消费的证据类型列表
    pub evidence_types: Vec<String>,
    /// 规则命中时的诊断消息
    pub message: String,
}

impl RuleContract {
    fn validate(&self) -> Result<(), RuleCatalogError> {
        if self.languages.is_empty() {
            return Err(RuleCatalogError::Validation(format!(
                "rule {} has no languages",
                self.id
            )));
        }
        if self.evidence_types.is_empty() {
            return Err(RuleCatalogError::Validation(format!(
                "rule {} has no evidence types",
                self.id
            )));
        }

        match RuleFamily::from_id(&self.id)? {
            RuleFamily::Core => self.validate_languages(&[
                Language::Python,
                Language::Rust,
                Language::C,
                Language::Cpp,
            ]),
            RuleFamily::Py => self.validate_languages(&[Language::Python]),
            RuleFamily::Rust => self.validate_languages(&[Language::Rust]),
            RuleFamily::Cpp => {
                if self
                    .languages
                    .iter()
                    .all(|language| matches!(language, Language::C | Language::Cpp))
                {
                    Ok(())
                } else {
                    Err(RuleCatalogError::Validation(format!(
                        "Cpp rule {} has non-C/C++ languages",
                        self.id
                    )))
                }
            }
        }
    }

    fn validate_languages(&self, expected: &[Language]) -> Result<(), RuleCatalogError> {
        if self.languages.len() == expected.len()
            && expected
                .iter()
                .all(|expected_language| self.languages.contains(expected_language))
        {
            Ok(())
        } else {
            Err(RuleCatalogError::Validation(format!(
                "rule {} has invalid languages",
                self.id
            )))
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum RuleFamily {
    Core,
    Py,
    Rust,
    Cpp,
}

impl RuleFamily {
    fn from_id(id: &str) -> Result<Self, RuleCatalogError> {
        for (prefix, family) in [
            ("Core", Self::Core),
            ("Rust", Self::Rust),
            ("Cpp", Self::Cpp),
            ("Py", Self::Py),
        ] {
            if let Some(suffix) = id.strip_prefix(prefix) {
                return if suffix.len() == 3 && suffix.bytes().all(|byte| byte.is_ascii_digit()) {
                    Ok(family)
                } else {
                    Err(RuleCatalogError::Validation(format!(
                        "rule id {id} must be {prefix} followed by exactly 3 ASCII digits"
                    )))
                };
            }
        }

        Err(RuleCatalogError::Validation(format!(
            "unknown rule family for id: {id}"
        )))
    }
}

/// 保存规则定义源文件中的完整配置
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuleDefinition {
    /// 规则 ID
    pub id: String,
    /// 规则名称
    pub name: String,
    /// 规则默认问题级别
    pub kind: IssueKind,
    /// 规则定位范围
    pub scope: Scope,
    /// 规则所属治理领域
    pub domain: Domain,
    /// 规则适用的语言集合
    pub languages: Vec<Language>,
    /// 规则是否默认启用
    pub default_enabled: bool,
    /// 规则来源说明
    pub origin: String,
    /// 支撑规则的来源 ID 列表
    pub source_ids: Vec<String>,
    /// 规则消费的证据类型列表
    pub evidence_types: Vec<String>,
    /// 规则命中时的诊断消息
    pub message: String,
    /// 规则读取的阈值键列表
    #[serde(default)]
    pub threshold_keys: Vec<String>,
    /// 规则读取的术语策略键列表
    #[serde(default)]
    pub term_policy_keys: Vec<String>,
    /// 规则维护备注
    #[serde(default)]
    pub notes: Option<String>,
}

impl RuleDefinition {
    /// 从 TOML 文本读取单条规则定义
    pub fn from_toml_str(input: &str) -> Result<Self, RuleCatalogError> {
        Ok(toml::from_str(input)?)
    }

    /// 提取运行时规则目录需要的契约视图
    pub fn contract(&self) -> RuleContract {
        RuleContract {
            id: self.id.clone(),
            name: self.name.clone(),
            kind: self.kind,
            scope: self.scope,
            domain: self.domain,
            languages: self.languages.clone(),
            default_enabled: self.default_enabled,
            origin: self.origin.clone(),
            source_ids: self.source_ids.clone(),
            evidence_types: self.evidence_types.clone(),
            message: self.message.clone(),
        }
    }
}

/// 描述规则目录读取和校验失败的原因
#[derive(Debug, Error)]
pub enum RuleCatalogError {
    /// TOML 解析失败
    #[error("rule TOML error: {0}")]
    Toml(#[from] toml::de::Error),

    /// 规则契约校验失败
    #[error("rule validation error: {0}")]
    Validation(String),
}
