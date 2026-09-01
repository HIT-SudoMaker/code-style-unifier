use crate::authority::ReviewRejection;
use serde::Deserialize;
use serde::Serialize;
use std::collections::BTreeMap;
use std::path::Path;
/// 表示一份待审查的内存源码文档
#[derive(Clone, Copy, Debug)]
pub struct SourceDocument<'source> {
    /// 文档集合内的相对路径
    pub relative_path: &'source str,
    /// 源码文档的原始字节
    pub bytes: &'source [u8],
}
/// 表示带稳定版本身份的内存文档集合
#[derive(Clone, Copy, Debug)]
pub struct DocumentSet<'snapshot> {
    /// 调用方提供的快照版本
    pub revision: &'snapshot str,
    /// 属于该快照的源码文档
    pub documents: &'snapshot [SourceDocument<'snapshot>],
}
/// 指定源码审查的输入来源
#[derive(Clone, Copy, Debug)]
pub enum ReviewInput<'review> {
    /// 审查文件系统中的工作区
    Workspace(&'review Path),
    /// 审查调用方提供的内存文档集合
    Documents(DocumentSet<'review>),
}
/// 表示审查终态的对外处置类别
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Disposition {
    /// 审查完整且未发现问题
    Clean,
    /// 审查完整且存在 Findings
    Findings,
    /// 审查未能覆盖全部必需事实族
    Incomplete,
    /// 输入在审查开始前被拒绝
    Rejected,
    /// 审查执行失败
    Failed,
}
/// 表示审查覆盖是否完整
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
#[repr(u8)]
pub enum Completion {
    /// 全部必需事实族完成
    Complete = 0,
    /// 至少一个必需事实族被阻塞
    Incomplete = 1,
}
/// 表示 Finding 的规范等级
#[derive(
    Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize,
)]
#[serde(rename_all = "snake_case")]
#[repr(u8)]
pub enum FindingGrade {
    /// 必须修复的规范违反
    HardViolation = 0,
    /// 建议处理的轻度摩擦
    SoftFriction = 1,
    /// 需要人工判断的候选问题
    ReviewRequired = 2,
}
/// 表示一个绑定到源码声明的审查发现
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct Finding {
    pub(crate) rule: String,
    pub(crate) grade: FindingGrade,
    pub(crate) path: String,
    pub(crate) line: usize,
    pub(crate) column: usize,
    pub(crate) subject: String,
    pub(crate) observation: String,
    pub(crate) question: Option<String>,
    pub(crate) message: String,
}
impl Finding {
    /// 返回产生 Finding 的规则身份
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 稳定规则身份
    /// # Errors
    /// - 无
    pub fn rule(&self) -> &str {
        &self.rule
    }
    /// 返回 Finding 的规范等级
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 规范等级
    /// # Errors
    /// - 无
    pub fn grade(&self) -> FindingGrade {
        self.grade
    }
    /// 返回 Finding 所属源码路径
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 规范化相对路径
    /// # Errors
    /// - 无
    pub fn path(&self) -> &str {
        &self.path
    }
    /// 返回 Finding 的一基行号
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 一基行号
    /// # Errors
    /// - 无
    pub fn line(&self) -> usize {
        self.line
    }
    /// 返回 Finding 的一基列号
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 一基列号
    /// # Errors
    /// - 无
    pub fn column(&self) -> usize {
        self.column
    }
    /// 返回 Finding 对应的声明主体
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 声明主体文本
    /// # Errors
    /// - 无
    pub fn subject(&self) -> &str {
        &self.subject
    }
    /// 返回与结论分离的结构观察证据
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 审查器实际观察到的源码事实
    /// # Errors
    /// - 无
    pub fn observation(&self) -> &str {
        &self.observation
    }
    /// 返回 Review Required 需要人工回答的问题
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 需要确认的问题；确定性 Finding 返回空值
    /// # Errors
    /// - 无
    pub fn question(&self) -> Option<&str> {
        self.question.as_deref()
    }
    /// 返回便于人工理解的 Finding 说明
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - Finding 说明
    /// # Errors
    /// - 无
    pub fn message(&self) -> &str {
        &self.message
    }
}
/// 标识一次审查生命周期中的事实族
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
#[repr(u8)]
pub enum FactFamily {
    /// 输入捕获事实
    Capture = 0,
    /// 物理行扫描事实
    PhysicalLines = 1,
    /// 结构解析事实
    Structure = 2,
    /// 标识符声明事实
    Identifier = 3,
    /// 文档载体与契约事实
    Documentation = 4,
    /// 依赖声明事实
    DependencyDeclaration = 5,
    /// 声明顺序事实
    DeclarationOrder = 6,
}
/// 表示单个事实族的终态
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(tag = "state", content = "value", rename_all = "snake_case")]
pub enum FactFamilyState {
    /// 当前文件无需执行该事实族
    NotRequired,
    /// 事实族完成并记录事实数量
    Complete(u32),
    /// 事实族无法可靠完成并记录原因
    Blocked(String),
}
/// 保存按文件压缩的事实覆盖账本
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct CompactCoverage {
    pub(crate) files: Vec<FileCoverage>,
}
impl CompactCoverage {
    /// 返回全部文件的覆盖记录
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 按稳定顺序排列的文件覆盖切片
    /// # Errors
    /// - 无
    pub fn files(&self) -> &[FileCoverage] {
        &self.files
    }
}
/// 保存单个文件的事实族覆盖状态
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct FileCoverage {
    pub(crate) path: String,
    pub(crate) required_mask: u8,
    pub(crate) executed_mask: u8,
    pub(crate) families: Vec<(FactFamily, FactFamilyState)>,
}
impl FileCoverage {
    /// 返回覆盖记录所属源码路径
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 规范化相对路径
    /// # Errors
    /// - 无
    pub fn path(&self) -> &str {
        &self.path
    }
    /// 返回该文件的事实族终态
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 事实族及其终态的稠密切片
    /// # Errors
    /// - 无
    pub fn families(&self) -> &[(FactFamily, FactFamilyState)] {
        &self.families
    }
    /// 返回该文件必须执行的事实族位图
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 必需事实族位图
    /// # Errors
    /// - 无
    pub fn required_mask(&self) -> u8 {
        self.required_mask
    }
    /// 返回该文件已经执行的事实族位图
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 已执行事实族位图
    /// # Errors
    /// - 无
    pub fn executed_mask(&self) -> u8 {
        self.executed_mask
    }
}
/// 记录一次审查的生命周期工作量
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize)]
pub struct ReviewMetrics {
    /// 读取的源码文件数量
    pub files_read: u64,
    /// 完成的单次字节扫描数量
    pub byte_sweeps: u64,
    /// 完成的结构解析数量
    pub structural_parses: u64,
}
/// 表示已封存审查的输入范围身份
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", content = "value", rename_all = "snake_case")]
pub enum ReviewedScope {
    /// 调用方提供的内存文档快照
    Documents {
        /// 快照版本
        revision: String,
        /// 快照包含的规范化相对路径
        files: Vec<String>,
    },
    /// 文件系统工作区快照
    Workspace {
        /// 工作区根路径
        root: String,
        /// 快照包含的规范化相对路径
        files: Vec<String>,
    },
}
/// 表示确定性封存的完整审查结果
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct SealedReview {
    pub(crate) schema_version: u32,
    pub(crate) scope: ReviewedScope,
    pub(crate) completion: Completion,
    pub(crate) coverage: CompactCoverage,
    pub(crate) findings: Vec<Finding>,
    pub(crate) metrics: ReviewMetrics,
    pub(crate) semantic_authority_digest: String,
    pub(crate) snapshot_digest: String,
    pub(crate) seal: String,
    #[serde(skip)]
    pub(crate) presentation: PresentationPlan,
}
/// 保存单个语言画像对认知章节的证据状态
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "state", rename_all = "snake_case", deny_unknown_fields)]
pub(crate) enum PresentationCell {
    Supported { contract: String },
    NotApplicable { reason: String },
    NeedsAuthority { capability: String },
}
/// 保存一个认知章节及其规则与四语言证据
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub(crate) struct PresentationChapter {
    pub(crate) chapter: String,
    pub(crate) rules: Vec<String>,
    pub(crate) profiles: BTreeMap<String, PresentationCell>,
}
/// 保存不参与科学身份的完整认知展示关系
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct PresentationPlan {
    pub(crate) chapters: Vec<PresentationChapter>,
}
impl SealedReview {
    /// 返回本次审查的输入范围身份
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 已审查范围
    /// # Errors
    /// - 无
    pub fn scope(&self) -> &ReviewedScope {
        &self.scope
    }
    /// 返回本次审查的覆盖完成状态
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 覆盖完成状态
    /// # Errors
    /// - 无
    pub fn completion(&self) -> Completion {
        self.completion
    }
    /// 返回本次审查的紧凑覆盖账本
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 紧凑覆盖账本
    /// # Errors
    /// - 无
    pub fn coverage(&self) -> &CompactCoverage {
        &self.coverage
    }
    /// 返回本次审查产生的全部 Findings
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 按稳定顺序排列的 Finding 切片
    /// # Errors
    /// - 无
    pub fn findings(&self) -> &[Finding] {
        &self.findings
    }
    /// 返回本次审查的生命周期工作量
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 审查工作量指标
    /// # Errors
    /// - 无
    pub fn metrics(&self) -> ReviewMetrics {
        self.metrics
    }
    /// 返回本次审查的确定性 Seal
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 十六进制 Seal 文本
    /// # Errors
    /// - 无
    pub fn seal(&self) -> &str {
        &self.seal
    }
    /// 将封存结果编码为规范 JSON
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 确定性 JSON 字节
    /// # Errors
    /// - 无
    pub fn canonical_bytes(&self) -> Vec<u8> {
        serde_json::to_vec(self).expect("sealed review is serializable")
    }
}
/// 表示审查开始后发生的执行失败
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ReviewFailure {
    code: String,
    message: String,
}
impl ReviewFailure {
    /// 执行 `new` 内部逻辑
    pub(crate) fn new(code: &str, message: impl Into<String>) -> Self {
        Self {
            code: code.to_owned(),
            message: message.into(),
        }
    }
    /// 返回稳定的失败代码
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 失败代码
    /// # Errors
    /// - 无
    pub fn code(&self) -> &str {
        &self.code
    }
    /// 返回便于人工理解的失败说明
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 失败说明
    /// # Errors
    /// - 无
    pub fn message(&self) -> &str {
        &self.message
    }
}
/// 表示一次审查的唯一终态
#[derive(Clone, Debug)]
pub enum ReviewTerminal {
    /// Authority 或请求在执行前被拒绝
    Rejected(ReviewRejection),
    /// 审查生命周期执行失败
    Failed(ReviewFailure),
    /// 审查结果已确定性封存
    Sealed(SealedReview),
}
impl ReviewTerminal {
    /// 将唯一终态映射为对外处置类别
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 对外处置类别
    /// # Errors
    /// - 无
    pub fn disposition(&self) -> Disposition {
        match self {
            Self::Rejected(_) => Disposition::Rejected,
            Self::Failed(_) => Disposition::Failed,
            Self::Sealed(review) => match review.completion {
                Completion::Incomplete => Disposition::Incomplete,
                Completion::Complete if review.findings.is_empty() => {
                    Disposition::Clean
                }
                Completion::Complete => Disposition::Findings,
            },
        }
    }
}
