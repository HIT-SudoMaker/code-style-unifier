use std::path::PathBuf;

use clap::{Parser, Subcommand, ValueEnum};

/// CSU 命令行入口
#[derive(Debug, Parser)]
#[command(name = "csu")]
#[command(about = "统一代码治理工具")]
pub struct Cli {
    /// 用户选择的顶层命令
    #[command(subcommand)]
    pub command: Command,
}

/// CSU 子命令
#[derive(Debug, Subcommand)]
pub enum Command {
    /// 扫描文件或目录并输出规则问题
    Check {
        /// 要扫描的文件或目录路径
        path: PathBuf,
        /// 使用的 profile 名称
        #[arg(long, default_value = "default")]
        profile: String,
        /// 直接加载 profile TOML 文件路径
        #[arg(long)]
        profile_path: Option<PathBuf>,
        /// 检查结果输出格式
        #[arg(long, value_enum, default_value_t = CheckFormat::Json)]
        format: CheckFormat,
        /// 写入检查结果的可选路径
        #[arg(long)]
        output: Option<PathBuf>,
        /// 扫描历史目录
        #[arg(long, default_value = ".csu/history")]
        history_dir: PathBuf,
        /// 跳过历史读写以便一次性自检
        #[arg(long)]
        no_history: bool,
    },
    /// 根据人工样本生成校准报告
    Calibrate {
        /// 检查输出 JSON 文件路径
        #[arg(long)]
        issues: PathBuf,
        /// 校准样本 JSON Lines 文件路径
        #[arg(long)]
        cases: PathBuf,
        /// 写入校准报告的可选路径
        #[arg(long)]
        output: Option<PathBuf>,
    },
    /// 输出规则目录契约
    Rules {
        /// 规则目录输出格式
        #[arg(long, value_enum, default_value_t = RulesFormat::Json)]
        format: RulesFormat,
    },
    /// 扫描历史记录
    History {
        /// 扫描历史目录
        #[arg(long, default_value = ".csu/history")]
        history_dir: PathBuf,
        /// 要执行的历史子命令
        #[command(subcommand)]
        command: HistoryCommand,
    },
}

/// 检查结果输出格式
#[derive(Clone, Copy, Debug, Eq, PartialEq, ValueEnum)]
pub enum CheckFormat {
    /// 输出单个 JSON 数组
    Json,
    /// 按行输出 JSON 对象
    Jsonl,
}

/// 规则目录输出格式
#[derive(Clone, Copy, Debug, Eq, PartialEq, ValueEnum)]
pub enum RulesFormat {
    /// 输出 JSON 视图
    Json,
    /// 输出原始 TOML 文本
    Toml,
}

/// 扫描历史管理子命令
#[derive(Debug, Subcommand)]
pub enum HistoryCommand {
    /// 列出已保存的扫描运行目录
    List,
    /// 按保留策略删除旧运行目录
    Prune,
    /// 删除全部扫描运行目录
    Clear,
}
