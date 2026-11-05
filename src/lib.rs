//! CSU 的 Authority 编译、源码审查与结果投影接口

mod authority;
mod model;
mod projection;
mod review;
/// 内存 Authority 文档
pub use authority::AuthorityDocument;
/// Authority 的目录或内存输入
pub use authority::AuthorityInput;
/// Authority 或审查请求的拒绝证据
pub use authority::ReviewRejection;
/// 编译 Authority 后执行单次审查
pub use authority::WorkspaceReviewer;
/// 按文件保存六类事实的覆盖账本
pub use model::CompactCoverage;
/// 全部必需事实族是否完成
pub use model::Completion;
/// 审查终态对应的对外处置类别
pub use model::Disposition;
/// 带版本身份的内存源码集合
pub use model::DocumentSet;
/// 审查生命周期中的事实类别
pub use model::FactFamily;
/// 单个事实类别的完成或受阻状态
pub use model::FactFamilyState;
/// 绑定到源码位置的审查发现
pub use model::Finding;
/// 硬违规或待确认等级
pub use model::FindingGrade;
/// 审查开始后的执行失败证据
pub use model::ReviewFailure;
/// 工作区或内存源码输入
pub use model::ReviewInput;
/// 读取、物理行观察和结构解析次数
pub use model::ReviewMetrics;
/// 拒绝、失败或封存结果之一
pub use model::ReviewTerminal;
/// 封存结果绑定的输入范围
pub use model::ReviewedScope;
/// 包含覆盖、发现和 Seal 的封存结果
pub use model::SealedReview;
/// 带相对路径的内存源码
pub use model::SourceDocument;
/// 生成人工可读的终态文本
pub use projection::project_human;
/// 生成稳定的 JSON 终态投影
pub use projection::project_javascript_object_notation;
