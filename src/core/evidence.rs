use serde::{Deserialize, Serialize};

use crate::core::issue::Language;
use crate::core::scanner::{FileUnit, WorkspaceState};

/// 聚合一次扫描后供规则评估消费的全部证据
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct EvidenceStore {
    /// 证据结构版本
    pub schema_version: String,
    /// 当前工作区事实
    pub workspace: WorkspaceFact,
    /// 扫描记录健康事实
    #[serde(default)]
    pub history_health: Option<HistoryHealthFact>,
    /// 文件级事实列表
    pub file_units: Vec<FileUnitFact>,
    /// 模块级事实
    #[serde(default)]
    pub module_units: Vec<ModuleUnitFact>,
    /// 依赖边事实
    #[serde(default)]
    pub dependency_edges: Vec<DependencyEdgeFact>,
    /// 文档区域事实列表
    pub doc_regions: Vec<DocRegionFact>,
    /// 注释区域事实列表
    pub comment_regions: Vec<CommentRegionFact>,
    /// 文本片段事实列表
    pub text_spans: Vec<TextSpanFact>,
    /// 行级事实列表
    pub line_spans: Vec<LineSpanFact>,
    /// 公开接口事实列表
    pub public_surfaces: Vec<PublicSurfaceFact>,
    /// 代码块事实列表
    pub block_regions: Vec<BlockRegionFact>,
    /// 符号事实
    #[serde(default)]
    pub symbols: Vec<SymbolFact>,
    /// 表达式事实
    #[serde(default)]
    pub expressions: Vec<ExpressionFact>,
}

impl EvidenceStore {
    /// 空证据集合
    pub fn empty(state: &WorkspaceState) -> Self {
        Self {
            schema_version: "1".to_string(),
            workspace: WorkspaceFact {
                id: "workspace:0001".to_string(),
                root: state.root.display().to_string(),
                target: state.target.display().to_string(),
                profile_id: state.profile_id.clone(),
                fingerprint: state.fingerprint.clone(),
            },
            history_health: None,
            file_units: state.files.iter().map(FileUnitFact::from).collect(),
            module_units: Vec::new(),
            dependency_edges: Vec::new(),
            doc_regions: Vec::new(),
            comment_regions: Vec::new(),
            text_spans: Vec::new(),
            line_spans: Vec::new(),
            public_surfaces: Vec::new(),
            block_regions: Vec::new(),
            symbols: Vec::new(),
            expressions: Vec::new(),
        }
    }

    /// 测试用空证据集合
    pub fn empty_for_tests() -> Self {
        Self {
            schema_version: "1".to_string(),
            workspace: WorkspaceFact {
                id: "workspace:test".to_string(),
                root: ".".to_string(),
                target: ".".to_string(),
                profile_id: "default".to_string(),
                fingerprint: "hash:test".to_string(),
            },
            history_health: None,
            file_units: Vec::new(),
            module_units: Vec::new(),
            dependency_edges: Vec::new(),
            doc_regions: Vec::new(),
            comment_regions: Vec::new(),
            text_spans: Vec::new(),
            line_spans: Vec::new(),
            public_surfaces: Vec::new(),
            block_regions: Vec::new(),
            symbols: Vec::new(),
            expressions: Vec::new(),
        }
    }
}

/// 标识一次扫描所属的工作区和目标
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct WorkspaceFact {
    /// 工作区事实 ID
    pub id: String,
    /// 工作区根目录
    pub root: String,
    /// 用户请求扫描的目标路径
    pub target: String,
    /// 本次扫描使用的 profile ID
    pub profile_id: String,
    /// 工作区文件清单指纹
    pub fingerprint: String,
}

/// 扫描记录健康事实
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct HistoryHealthFact {
    /// 已保留运行次数
    pub run_count: usize,
    /// 最旧运行距离当前的天数
    pub oldest_run_age_days: i64,
    /// 已保留运行总字节数
    pub total_bytes: u64,
}

/// 记录单个源文件的语言、路径和指纹
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct FileUnitFact {
    /// 文件事实 ID
    pub id: String,
    /// 工作区内相对路径
    pub path: String,
    /// 源文件语言
    pub language: Language,
    /// 文件是否被识别为生成文件
    pub generated: bool,
    /// 文件是否已从评估中排除
    pub excluded: bool,
    /// 文件内容指纹
    pub fingerprint: String,
}

impl From<&FileUnit> for FileUnitFact {
    fn from(file: &FileUnit) -> Self {
        Self {
            id: file.id.clone(),
            path: file.relative_path.clone(),
            language: file.language,
            generated: file.generated,
            excluded: file.excluded,
            fingerprint: file.fingerprint.clone(),
        }
    }
}

/// 依赖来源分组
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DependencyGroup {
    /// future 导入
    Future,
    /// 标准库导入
    Standard,
    /// 第三方导入
    ThirdParty,
    /// 本地导入
    Local,
    /// 未分类导入
    Unknown,
}

/// 符号种类
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SymbolKind {
    /// 模块
    Module,
    /// 类型
    Class,
    /// 结构体
    Struct,
    /// 枚举
    Enum,
    /// trait 类型
    Trait,
    /// union 类型
    Union,
    /// 函数
    Function,
    /// 方法
    Method,
    /// 字段
    Field,
    /// 变量
    Variable,
    /// 参数
    Parameter,
    /// 常量
    Constant,
    /// 类型别名
    TypeAlias,
    /// 宏
    Macro,
}

/// 符号可见性
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SymbolVisibility {
    /// 对外公开
    Public,
    /// 项目内部
    Internal,
    /// 私有
    Private,
}

/// 表达式种类
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ExpressionKind {
    /// 执行项
    Call,
    /// 导入表达式
    Import,
    /// 类型表达式
    TypeExpression,
    /// 日志输出
    LoggingCall,
    /// 错误消息
    ErrorMessage,
    /// 抑制标记
    Suppression,
    /// 宏展开入口
    MacroInvocation,
    /// 宏定义
    MacroDefinition,
    /// 预处理表达式
    Preprocessor,
    /// panic 表达式
    Panic,
    /// await 表达式
    Await,
    /// 锁表达式
    Lock,
    /// 分配表达式
    Allocation,
}

/// 模块级事实
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ModuleUnitFact {
    /// 事实 ID
    pub id: String,
    /// 文件事实 ID
    pub file_id: String,
    /// 源码语言
    pub language: Language,
    /// 相对路径
    pub path: String,
    /// 源码范围
    pub range: String,
    /// 是否存在模块文档区域
    pub has_module_doc_region: bool,
    /// 是否为 C/C++ 头文件
    pub is_header: bool,
    /// 头文件保护宏名称
    pub include_guard: Option<String>,
    /// 是否使用 pragma once
    pub pragma_once: bool,
}

/// 依赖边事实
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DependencyEdgeFact {
    /// 事实 ID
    pub id: String,
    /// 文件事实 ID
    pub file_id: String,
    /// 模块事实 ID
    pub module_id: String,
    /// 依赖分组
    pub group: DependencyGroup,
    /// 来源模块
    pub source: String,
    /// 导入对象
    pub imported: String,
    /// 导入别名
    pub alias: Option<String>,
    /// 源码范围
    pub range: String,
    /// 是否为 glob 导入
    pub is_glob: bool,
    /// 是否重新公开
    pub is_public: bool,
    /// 是否相对导入
    pub is_relative: bool,
}

/// 符号事实
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SymbolFact {
    /// 事实 ID
    pub id: String,
    /// 文件事实 ID
    pub file_id: String,
    /// 模块事实 ID
    pub module_id: String,
    /// 符号名
    pub name: String,
    /// 限定名
    pub qualified_name: String,
    /// 符号种类
    pub kind: SymbolKind,
    /// 可见性
    pub visibility: SymbolVisibility,
    /// 源码语言
    pub language: Language,
    /// 源码范围
    pub range: String,
    /// 文档区域 ID
    pub doc_region_id: Option<String>,
    /// 返回类型标注
    pub return_annotation: Option<String>,
    /// 缺失类型标注的参数
    pub missing_parameter_annotations: Vec<String>,
    /// 类型文本
    pub type_text: Option<String>,
    /// 是否为 async 符号
    pub is_async: bool,
    /// 是否为 unsafe 符号
    pub is_unsafe: bool,
    /// 属性列表
    pub attributes: Vec<String>,
}

/// 表达式事实
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ExpressionFact {
    /// 事实 ID
    pub id: String,
    /// 文件事实 ID
    pub file_id: String,
    /// 模块事实 ID
    pub module_id: String,
    /// 所属符号 ID
    pub symbol_id: Option<String>,
    /// 表达式种类
    pub kind: ExpressionKind,
    /// 源码范围
    pub range: String,
    /// 表达式文本
    pub text: String,
    /// 目标对象
    pub callee: Option<String>,
    /// 参数文本
    pub arguments: Vec<String>,
}

/// 记录文档块和其摘要文本之间的关系
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DocRegionFact {
    /// 文档区域事实 ID
    pub id: String,
    /// 所属文件事实 ID
    pub file_id: String,
    /// 文档绑定的符号名称
    pub symbol_name: String,
    /// 文档在源码中的范围
    pub range: String,
    /// 摘要文本片段 ID
    pub summary_text_id: String,
    /// 完整文档文本片段 ID
    #[serde(default)]
    pub full_text_id: Option<String>,
}

/// 记录注释区域和其文本片段之间的关系
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CommentRegionFact {
    /// 注释区域事实 ID
    pub id: String,
    /// 所属文件事实 ID
    pub file_id: String,
    /// 注释在源码中的范围
    pub range: String,
    /// 注释区域类别
    pub kind: String,
    /// 注释文本片段 ID
    pub text_id: String,
}

/// 区分文本片段在规则评估中的角色
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TextRole {
    /// 文档摘要文本
    DocSummary,
    /// 普通注释文本
    Comment,
    /// 错误消息文本
    ErrorMessage,
    /// 其他可索引文本
    Other,
}

/// 记录一段可评估文本及其来源范围
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TextSpanFact {
    /// 文本片段事实 ID
    pub id: String,
    /// 所属文件事实 ID
    pub file_id: String,
    /// 文本在源码中的范围
    pub range: String,
    /// 文本片段角色
    pub role: TextRole,
    /// 去除语法标记后的正文
    pub normalized_text: String,
    /// 文本内容指纹
    pub text_hash: String,
    /// 文本最后一个字符
    pub terminal_punctuation: Option<char>,
}

impl TextSpanFact {
    /// 测试用文本片段事实
    pub fn for_test(id: &str, role: TextRole, text: &str) -> Self {
        Self {
            id: id.to_string(),
            file_id: "file:test".to_string(),
            range: "1:1-1:1".to_string(),
            role,
            normalized_text: text.to_string(),
            text_hash: format!("blake3:{}", blake3::hash(text.as_bytes()).to_hex()),
            terminal_punctuation: text.chars().last(),
        }
    }
}

/// 记录单行源码的宽度和抑制标记
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct LineSpanFact {
    /// 行事实 ID
    pub id: String,
    /// 所属文件事实 ID
    pub file_id: String,
    /// 一基准行号
    pub line: usize,
    /// 按 Unicode 宽度计算的可视宽度
    pub visual_width: usize,
    /// 行内容指纹
    pub line_hash: String,
    /// 行内抑制标记文本
    pub suppression: Option<String>,
}

/// 记录需要公开文档契约覆盖的接口面
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PublicSurfaceFact {
    /// 公开接口事实 ID
    pub id: String,
    /// 接口对应的符号名称
    pub symbol_name: String,
    /// 接口可见性名称
    pub visibility: String,
    /// 是否已绑定文档区域
    pub has_doc_region: bool,
    /// 所属文件事实 ID
    pub file_id: String,
    /// 接口声明在源码中的范围
    pub range: String,
}

/// 记录需要意图说明的代码块
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BlockRegionFact {
    /// 代码块事实 ID
    pub id: String,
    /// 所属文件事实 ID
    pub file_id: String,
    /// 代码块在源码中的范围
    pub range: String,
    /// 代码块类别
    pub kind: String,
    /// 解释该代码块意图的注释 ID
    pub intent_comment_id: Option<String>,
}
