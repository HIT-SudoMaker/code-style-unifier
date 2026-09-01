# 公共 Review seam 测试合同映射

本账本记录测试瘦身后的行为合同 Owner。删除旧的逐样例测试前，等价行为必须在下表
至少有一个公共 `WorkspaceReviewer::compile -> review -> ReviewTerminal` 测试。

| 行为合同 | 当前测试 Owner |
|---|---|
| 20-cell 四语言有效/普通注释/缺公共字段/短符号/语法损坏精确终态 | `fixture_contract.rs` + `fixture-manifest.json` |
| public 三字段逐项缺失、空 role、Returns 形状 | `public_review.rs` |
| 普通注释、延迟字符串、容器字符串与 internal 摘要正例 | `python_target_calibration.rs` |
| Python property getter/setter/deleter、孤立accessor、未知decorator、receiver、闭引号和module docstring | `public_review.rs`、`documentation_regressions.rs` |
| Rust trait/foreign callable、public type/field/variant、exported macro、public use的Owner | `documentation_regressions.rs` |
| Rust literal `#[doc]`、block rustdoc、summary/contract代码块隔离、Never与Safety | `documentation_regressions.rs`、`public_review.rs` |
| 重复heading、额外参数、variadic签名、连续中文短语和受控标点 | `documentation_regressions.rs` |
| C/C++ 受控块、普通注释、public Owner 歧义、模板和 effect | `fixture_contract.rs`、`documentation_regressions.rs`、`cpp_documentation_roles.rs` |
| 四语言声明 Subject、角色词形、候选优先级与希腊/拉丁符号 | `identifier_subjects.rs`、`identifier_forms.rs` |
| 四语言直接依赖、顺序、wildcard、scope 与未知分类 | `dependency_contract.rs` |
| Authority 拒绝、四语言 Direct parseability、family closure、capture 负空间、Seal 确定性 | `terminal_contract.rs` |
| 四语言 External parseability、首个失败锚点和阻塞传播 | `fixture_contract.rs` |
| JSON/human/CLI 只读投影与退出码 | `projection_cli.rs` |
| 产品与测试宿主三个零自检、真实 Python 靶场反例 | `self_check.rs`、`python_target_calibration.rs` |

## 规则 Owner

| 规则 | 最小证据 Owner |
|---|---|
| `source.parseability` | `terminal_contract.rs` + `fixture_contract.rs` |
| `identifier.candidate` | `fixture_contract.rs` + `identifier_subjects.rs` |
| `identifier.reserved`、`identifier.canonical_form`、`identifier.representation_suffix`、`identifier.unknown_token` | `identifier_forms.rs` |
| `documentation.carrier`、`documentation.public_contract` | `fixture_contract.rs` |
| `documentation.summary`、`documentation.punctuation` | `documentation_regressions.rs` |
| `documentation.safety` | `public_review.rs` |
| `dependency.wildcard`、`dependency.module_placement`、`dependency.order` | `dependency_contract.rs` |

本轮删除了 `public_review.rs` 的重复四语言 Clean/缺载体、Python carrier/internal
摘要测试，以及 `documentation_regressions.rs` 的重复 C 普通注释测试。它们的
输入域与断言均被 20-cell 合同或真实靶场校准表严格覆盖；没有删除独立语义分支。

这里的 Owner 是行为合同映射，不要求恢复每个历史字符串变体。新增边界只有在它证明
新的语义分支时才增加测试；同一分支的多语言或多形态输入优先进入数据矩阵。
