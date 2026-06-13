/// 读取校准样本并生成规则校准报告
pub mod calibration;
/// 定义 csu 命令行参数与子命令
pub mod cli;
/// 统一扫描、解析和序列化错误类型
pub mod error;
/// 汇总各语言与通用规则的 evaluator
pub mod evaluators;
/// 承载扫描后供规则消费的结构化证据
pub mod evidence;
/// 从源码文本提取规则评估所需证据
pub mod frontend;
/// 读写扫描历史并计算保留策略健康度
pub mod history;
/// 定义规则问题、范围、领域和语言模型
pub mod issue;
/// 读取 profile 中的阈值与术语策略
pub mod profile;
/// 读取并验证规则目录契约
pub mod rules;
/// 工作区文件清单
pub mod scanner;
/// 提供 tree-sitter 语法解析入口
pub mod syntax;
