use serde::{Deserialize, Deserializer, Serialize};

/// 标识问题对发布或维护流程的影响级别
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum IssueKind {
    /// 必须修复的硬性违例
    HardViolation,
    /// 不阻塞但需要记录的软性摩擦
    SoftFriction,
    /// 需要人工复核后再决定处置
    UnderReview,
}

impl IssueKind {
    /// 返回该级别是否阻塞检查结果
    pub fn blocks(self) -> bool {
        matches!(self, Self::HardViolation)
    }
}

/// 标识问题定位到的代码或项目范围
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Scope {
    /// 整个项目范围
    Project,
    /// 单个文件范围
    File,
    /// 单个模块范围
    Module,
    /// 单个符号范围
    Symbol,
    /// 单个代码块范围
    Block,
    /// 单个表达式范围
    Expression,
    /// 单行源码范围
    Line,
    /// 单段文本范围
    Text,
}

/// 标识规则问题所属的治理领域
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Domain {
    /// 项目结构领域
    Project,
    /// 扫描历史领域
    History,
    /// 依赖关系领域
    Dependency,
    /// 文档契约领域
    Documentation,
    /// 命名规范领域
    Naming,
    /// 风格规范领域
    Style,
    /// 可维护性领域
    Maintainability,
    /// 类型契约领域
    Typing,
    /// 日志边界领域
    Logging,
    /// 公开 API 领域
    PublicApi,
    /// 安全相邻代码领域
    SafetyAdjacent,
}

/// 标识当前规则支持的源代码语言
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Language {
    /// Python 源码
    Python,
    /// Rust 源码
    Rust,
    /// C 源码
    C,
    /// C++ 源码
    Cpp,
    /// TypeScript 源码
    Typescript,
}

/// 描述一条规则评估产生的问题
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct Issue {
    /// 稳定问题 ID
    pub id: String,
    /// 问题影响级别
    pub kind: IssueKind,
    /// 规则 ID
    pub rule: String,
    /// 规则问题名称
    pub name: String,
    /// 问题定位范围
    pub scope: Scope,
    /// 问题所属治理领域
    pub domain: Domain,
    /// 问题关联的源代码语言
    pub language: Option<Language>,
    /// 问题关联的路径
    pub path: Option<String>,
    /// 问题关联的源码范围
    pub range: Option<String>,
    /// 面向用户的诊断消息
    pub message: String,
    /// 支撑该问题的证据 ID 列表
    pub evidence: Vec<String>,
    /// 是否阻塞检查结果
    pub blocks: bool,
}

impl<'de> Deserialize<'de> for Issue {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        #[derive(Deserialize)]
        struct RawIssue {
            id: String,
            kind: IssueKind,
            rule: String,
            name: String,
            scope: Scope,
            domain: Domain,
            language: Option<Language>,
            path: Option<String>,
            range: Option<String>,
            message: String,
            evidence: Vec<String>,
            #[serde(default, rename = "blocks")]
            _blocks: Option<bool>,
        }

        let RawIssue {
            id,
            kind,
            rule,
            name,
            scope,
            domain,
            language,
            path,
            range,
            message,
            evidence,
            _blocks: _,
        } = RawIssue::deserialize(deserializer)?;

        Ok(Self {
            id,
            kind,
            rule,
            name,
            scope,
            domain,
            language,
            path,
            range,
            message,
            evidence,
            blocks: kind.blocks(),
        })
    }
}

impl Issue {
    /// 构造不含位置和证据的规则问题
    pub fn new(
        id: impl Into<String>,
        kind: IssueKind,
        rule: impl Into<String>,
        name: impl Into<String>,
        scope: Scope,
        domain: Domain,
    ) -> Self {
        Self {
            id: id.into(),
            kind,
            rule: rule.into(),
            name: name.into(),
            scope,
            domain,
            language: None,
            path: None,
            range: None,
            message: String::new(),
            evidence: Vec::new(),
            blocks: kind.blocks(),
        }
    }

    /// 为问题附加语言、路径和源码范围
    pub fn with_location(
        mut self,
        language: Language,
        path: impl Into<String>,
        range: impl Into<String>,
    ) -> Self {
        self.language = Some(language);
        self.path = Some(path.into());
        self.range = Some(range.into());
        self
    }

    /// 为问题附加面向用户的诊断消息
    pub fn with_message(mut self, message: impl Into<String>) -> Self {
        self.message = message.into();
        self
    }

    /// 为问题追加一个证据 ID
    pub fn with_evidence(mut self, evidence_ref: impl Into<String>) -> Self {
        self.evidence.push(evidence_ref.into());
        self
    }
}
