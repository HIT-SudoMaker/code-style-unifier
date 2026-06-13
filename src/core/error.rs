use thiserror::Error;

/// 汇总核心流程可能返回的可诊断错误
#[derive(Debug, Error)]
pub enum CoreError {
    /// 文件系统操作失败并保留触发路径
    #[error("io error at {path}: {source}")]
    Io {
        /// 触发 IO 错误的路径文本
        path: String,
        /// 底层 IO 错误
        #[source]
        source: std::io::Error,
    },

    /// profile 读取或校验失败
    #[error("profile error: {0}")]
    Profile(String),

    /// 规则目录读取或校验失败
    #[error("rule catalog error: {0}")]
    RuleCatalog(String),

    /// 扫描目标不存在
    #[error("scan target does not exist: {0}")]
    MissingTarget(String),

    /// JSON、TOML 或 tree-sitter 相关序列化边界失败
    #[error("serialization error: {0}")]
    Serialization(String),
}

/// 核心模块统一使用的结果类型
pub type Result<T> = std::result::Result<T, CoreError>;
