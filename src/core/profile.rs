use std::collections::{HashMap, HashSet};

use serde::{Deserialize, Serialize};

/// 承载一次规则评估使用的 profile 配置
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct Profile {
    /// profile 名称
    pub name: String,
    /// 启用的规则 ID 列表
    pub enabled_rules: Vec<String>,
    /// 扫描时排除的目录名称
    pub exclude_dirs: Vec<String>,
    /// 扫描时排除的文件匹配模式
    pub exclude_file_patterns: Vec<String>,
    /// 规则共享阈值配置
    pub thresholds: Thresholds,
    /// 文本和命名术语策略
    pub term_policy: TermPolicy,
}

impl Profile {
    /// 从 TOML 文本读取并规范化 profile
    pub fn from_toml_str(input: &str) -> Result<Self, toml::de::Error> {
        let mut profile: Self = toml::from_str(input)?;
        profile.term_policy.normalize_tokens();
        Ok(profile)
    }
}

/// 保存规则评估使用的数值阈值
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct Thresholds {
    /// 单行最大可视宽度
    pub line_length_limit: usize,
    /// 文档摘要最大字符数
    pub doc_summary_max_chars: usize,
    /// 历史记录最多保留运行次数
    pub history_max_runs: usize,
    /// 历史记录最多保留天数
    pub history_max_days: i64,
    /// 历史记录最多占用字节数
    pub history_max_bytes: u64,
}

/// 保存术语白名单和禁用缩写策略
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TermPolicy {
    /// 允许作为缩写使用的 token
    pub allowed_abbreviation_tokens: Vec<String>,
    /// 允许保持原样的完整名称
    pub allowed_abbreviation_names: Vec<String>,
    /// 允许出现在自然语言文本中的技术片段
    pub allowed_technical_fragments: Vec<String>,
    /// 禁用缩写到建议用词的映射
    pub banned_abbreviation_tokens: HashMap<String, String>,
}

impl TermPolicy {
    fn normalize_tokens(&mut self) {
        for token in &mut self.allowed_abbreviation_tokens {
            token.make_ascii_lowercase();
        }

        self.banned_abbreviation_tokens = self
            .banned_abbreviation_tokens
            .drain()
            .map(|(key, value)| (key.to_ascii_lowercase(), value))
            .collect();
    }

    /// 判断 token 是否被缩写策略显式允许
    pub fn is_allowed_abbreviation(&self, token: &str) -> bool {
        let normalized = token.to_ascii_lowercase();
        self.allowed_abbreviation_tokens
            .iter()
            .any(|item| item == &normalized)
            || self
                .allowed_abbreviation_names
                .iter()
                .any(|item| item == token)
    }

    /// 判断 token 是否命中禁用缩写策略
    pub fn is_banned_abbreviation(&self, token: &str) -> bool {
        let normalized = token.to_ascii_lowercase();
        self.banned_abbreviation_tokens.contains_key(&normalized)
    }

    /// 返回允许的自然语言技术片段集合
    pub fn allowed_fragment_set(&self) -> HashSet<&str> {
        self.allowed_technical_fragments
            .iter()
            .map(String::as_str)
            .collect()
    }
}
