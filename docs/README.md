# CSU 文档

[项目介绍](../README.md) 说明 CSU 的科研软件定位、审查职责，以及安装和调用入口。
详细内容按问题分工：

| 任务 | 文档 | 负责回答 |
|---|---|---|
| 首次审查、接入自动化 | [使用说明](usage.md) | 准备哪些输入，运行什么命令，怎样处理结果 |
| 编写或审查 Python、Rust、C、C++ 源码 | [编码规范](coding_standards.md) | 必须遵守什么，哪些内容由作者另行核验 |
| 理解或调整架构 | [设计原理](design.md) | 为什么采用当前方案，承担了什么取舍 |
| 修改实现、定位行为或调用 Rust 库 | [技术参考](technical.md) | 输入、观察、判断、身份和输出怎样连接 |

规则含义以编码规范为准。设计原理记录选择的理由，技术参考说明当前实现；这两份说明不能增减规则。
命令和项目输入示例放在使用说明，运行数据留在其实际证据中。

## 源码仓库中的维护资料

发布包包含上述四份说明及本索引。以下开发资料通过源码仓库访问，避免将测试样例和验收环境混入安装目录。

| 需要核对的内容 | 入口 |
|---|---|
| 测试分组、运行入口和共享样例 | [测试指南](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/tests/README.md) |
| 声明类别、结构排除、受阻条件和专项测试缺口 | [声明覆盖清单](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/docs/fixtures/core/declaration-coverage.md) |
| 本地检查、冻结语料、性能测量与候选验收 | [靶场与发布验收](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/docs/fixtures/core/README.md) |
| 冻结项目来源及许可证 | [bench/targets](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/bench/targets/README.md) |
| Agent 审查和证据处理 | [CSU Review](../.agents/skills/csu-review/SKILL.md) |
| 已授权的源码修复与项目事实登记 | [修复指引](../.agents/skills/csu-review/references/remediation.md) |

验收收据描述所绑定的候选与运行环境；文档中的示例和边界说明不代表当前候选已通过验收或发布。
