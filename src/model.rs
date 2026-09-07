use crate::authority::ReviewRejection;
use serde::Deserialize;
use serde::Serialize;
use std::collections::BTreeMap;
use std::path::Path;

pub(crate) const REVIEW_SCHEMA_VERSION: u32 = 4;
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
    /// 审查完整且存在问题
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
/// 表示审查问题的规范等级
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
#[repr(u8)]
pub enum FindingGrade {
    /// 必须修复的规范违反
    HardViolation = 0,
    /// 需要人工判断的候选问题
    ReviewRequired = 1,
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
    /// 返回产生问题的规则身份
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
    /// 返回问题的规范等级
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
    /// 返回问题所属源码路径
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
    /// 返回问题所在行号，从一开始
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
    /// 返回问题所在列号，从一开始
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
    /// 返回问题对应的声明主体
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
    /// - 需要确认的问题；无需确认时返回空值
    /// # Errors
    /// - 无
    pub fn question(&self) -> Option<&str> {
        self.question.as_deref()
    }
    /// 返回便于人工理解的问题说明
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 问题说明
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
}
/// 表示单个事实族的终态
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(tag = "state", content = "value", rename_all = "snake_case")]
pub enum FactFamilyState {
    /// 事实族完成并记录事实数量
    Complete(u32),
    /// 事实族无法可靠完成并记录原因
    Blocked(String),
}
/// 表示单文件的读取失败、源码拒绝或事实提取结果
pub(crate) enum FamilyClosure {
    CaptureBlocked(String),
    SourceRejected {
        physical_lines: u32,
        reason: String,
    },
    Observed {
        physical_lines: u32,
        identifier: FactFamilyState,
        documentation: FactFamilyState,
        dependency: FactFamilyState,
    },
}
impl FamilyClosure {
    /// 将单一观察结果投影到指定事实族
    fn state(&self, family: FactFamily) -> FactFamilyState {
        match self {
            Self::CaptureBlocked(reason) => {
                FactFamilyState::Blocked(reason.clone())
            }
            Self::SourceRejected {
                physical_lines,
                reason,
            } => match family {
                FactFamily::Capture => FactFamilyState::Complete(1),
                FactFamily::PhysicalLines => {
                    FactFamilyState::Complete(*physical_lines)
                }
                _ => FactFamilyState::Blocked(reason.clone()),
            },
            Self::Observed {
                physical_lines,
                identifier,
                documentation,
                dependency,
            } => match family {
                FactFamily::Capture | FactFamily::Structure => {
                    FactFamilyState::Complete(1)
                }
                FactFamily::PhysicalLines => {
                    FactFamilyState::Complete(*physical_lines)
                }
                FactFamily::Identifier => identifier.clone(),
                FactFamily::Documentation => documentation.clone(),
                FactFamily::DependencyDeclaration => dependency.clone(),
            },
        }
    }
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
    /// 从唯一覆盖账本派生完成状态
    pub(crate) fn completion(&self) -> Completion {
        if self
            .files
            .iter()
            .flat_map(FileCoverage::families)
            .any(|(_, state)| matches!(state, FactFamilyState::Blocked(_)))
        {
            Completion::Incomplete
        } else {
            Completion::Complete
        }
    }
}
/// 保存单个文件的事实族覆盖状态
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct FileCoverage {
    pub(crate) path: String,
    pub(crate) families: [(FactFamily, FactFamilyState); 6],
}
impl FileCoverage {
    /// 将单一观察路径构造为六格终态账本
    pub(crate) fn close(path: String, closure: FamilyClosure) -> Self {
        let families = [
            FactFamily::Capture,
            FactFamily::PhysicalLines,
            FactFamily::Structure,
            FactFamily::Identifier,
            FactFamily::Documentation,
            FactFamily::DependencyDeclaration,
        ]
        .map(|family| (family, closure.state(family)));
        Self { path, families }
    }
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
}
#[cfg(test)]
mod coverage {
    use super::CompactCoverage;
    use super::Completion;
    use super::FactFamilyState;
    use super::FamilyClosure;
    use super::FileCoverage;

    /// 验证读取失败会将所有事实类别标记为受阻
    #[test]
    fn capture_blocked_closes_all_families() {
        let file = FileCoverage::close(
            "src/value.py".to_owned(),
            FamilyClosure::CaptureBlocked("capture failed".to_owned()),
        );
        assert_eq!(file.families().len(), 6);
        assert!(file.families().iter().all(|(_, state)| {
            matches!(state, FactFamilyState::Blocked(reason) if reason == "capture failed")
        }));
        assert_eq!(
            CompactCoverage { files: vec![file] }.completion(),
            Completion::Incomplete
        );
    }
}
/// 记录一次审查的生命周期工作量
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize)]
pub struct ReviewMetrics {
    /// 读取的源码文件数量
    pub files_read: u64,
    /// 完成的物理行观察次数，不含哈希、UTF-8 校验与错误定位的字节访问
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
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SealedReview {
    pub(crate) scope: ReviewedScope,
    pub(crate) coverage: CompactCoverage,
    pub(crate) findings: Vec<Finding>,
    pub(crate) metrics: ReviewMetrics,
    pub(crate) semantic_authority_digest: String,
    pub(crate) snapshot_digest: String,
    pub(crate) seal: String,
    pub(crate) presentation: PresentationPlan,
}
/// 保存单个语言在展示章节中的证据状态
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(tag = "state", rename_all = "snake_case", deny_unknown_fields)]
pub(crate) enum PresentationCell {
    Supported { contract: String },
}
/// 保存展示章节及其规则和四语言证据
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct PresentationChapter {
    pub(crate) chapter: String,
    pub(crate) rules: Vec<String>,
    pub(crate) profiles: BTreeMap<String, PresentationCell>,
}
/// 保存不参与语义身份计算的展示关系
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
        self.coverage.completion()
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
    /// 返回本次审查发现的全部问题
    ///
    /// # Arguments
    /// - 无
    /// # Returns
    /// - 按稳定顺序排列的问题切片
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
        #[derive(Serialize)]
        struct CanonicalReview<'review> {
            schema_version: u32,
            scope: &'review ReviewedScope,
            completion: Completion,
            coverage: &'review CompactCoverage,
            findings: &'review [Finding],
            metrics: ReviewMetrics,
            semantic_authority_digest: &'review str,
            snapshot_digest: &'review str,
            seal: &'review str,
        }
        serde_json::to_vec(&CanonicalReview {
            schema_version: REVIEW_SCHEMA_VERSION,
            scope: &self.scope,
            completion: self.completion(),
            coverage: &self.coverage,
            findings: &self.findings,
            metrics: self.metrics,
            semantic_authority_digest: &self.semantic_authority_digest,
            snapshot_digest: &self.snapshot_digest,
            seal: &self.seal,
        })
        .expect("sealed review is serializable")
    }
}
/// 表示审查开始后发生的执行失败
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ReviewFailure {
    code: String,
    message: String,
}
impl ReviewFailure {
    /// 根据错误代码和说明创建失败结果
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
            Self::Sealed(review) => match review.completion() {
                Completion::Incomplete => Disposition::Incomplete,
                Completion::Complete if review.findings.is_empty() => {
                    Disposition::Clean
                }
                Completion::Complete => Disposition::Findings,
            },
        }
    }
}
