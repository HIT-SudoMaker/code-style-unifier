# CSU 测试

测试从公共审查入口进入，沿“输入接纳 → 事实观察 → 规则判断 → 完成与封存 → 展示”阅读。
目录按行为组织，同一测试可以同时证明一个事实及其完成状态。Cargo target 和测试函数名称保持稳定，
依赖与文档测试的模块前缀标明责任，例如 `completion::rust_unknown_members_preserve_known_list_evidence`。

## 阅读路线

| 阶段 | 从哪里读 | 要回答的问题 |
|---|---|---|
| 1. 输入接纳 | [terminal_contract](review/terminal_contract.rs) 的“输入”两组；[dependency authority](dependency/authority.rs) | Authority 是否有效？源码身份是否先于读取确定？ |
| 2. 事实观察 | terminal 的“观察与完成”；[identifier subjects](identifier/subjects.rs)；[native roles](documentation/native_roles.rs)、[return shape](documentation/return_shape.rs)；[dependency observation](dependency/observation.rs)；[documentation carriers](documentation/carriers.rs)、[subjects](documentation/subjects.rs) | 观察到了哪些主体、声明、文档载体和直接归属？ |
| 3. 规则判断 | [identifier forms](identifier/forms.rs)；[public documentation](documentation/public_contract.rs)、[content](documentation/content.rs)、[fields](documentation/fields.rs)；[dependency ordering](dependency/ordering.rs) | 已知事实支持哪些判断？字段、语言差异和重排授权如何影响结论？ |
| 4. 完成与封存 | [dependency completion](dependency/completion.rs)；terminal 的六类记录、“演进”和“封存”组；[fixture contract](review/fixture_contract.rs) | 缺口是否保留？已知问题是否仍可见？身份是否绑定实际规则、事实和字节？ |
| 5. 展示 | [projection CLI](review/projection_cli.rs) | 文本、JSON、等级计数和退出码是否忠实表达封存结果？输入字节是否保持？ |
| 6. 仓库验收 | [self check](self_check.rs) 及冻结语料验收 | 产品、测试和 skill 镜像是否一致？候选测量证据是否齐备？ |

`terminal_contract.rs` 内使用阶段注释；依赖测试的四个阶段已成为独立模块。
文档测试按载体、主体、内容义务和字段布局分组；表驱动样例及其构造辅助与所属行为放在同一模块。
两个测试入口只负责共享装配与结果断言，不重新实现规则，也不逐个转发测试调用。
案例内的源码、定位断言和完成性断言保留在一起；共同规则用四语言对照，各语言差异就近证明。
这条路线是阅读顺序。每个测试独立创建输入和审查器；Cargo 可以并行执行，不依赖前一个测试的状态。

## 测试入口

| 目录或文件 | Cargo target |
|---|---|
| [review/terminal_contract.rs](review/terminal_contract.rs) | `terminal_contract` |
| [identifier/subjects.rs](identifier/subjects.rs) | `identifier_subjects` |
| [documentation/native_roles.rs](documentation/native_roles.rs) | `cpp_documentation_roles` |
| [documentation/return_shape.rs](documentation/return_shape.rs) | `return_shape_contract` |
| [identifier/forms.rs](identifier/forms.rs) | `identifier_forms` |
| [documentation/public_contract.rs](documentation/public_contract.rs) | `public_review` |
| [documentation/mod.rs](documentation/mod.rs)，含 carriers / subjects / content / fields | `documentation_regressions` |
| [dependency_contract.rs](dependency_contract.rs) | `dependency_contract` |
| [review/fixture_contract.rs](review/fixture_contract.rs) | `fixture_contract` |
| [review/projection_cli.rs](review/projection_cli.rs) | `projection_cli` |
| [self_check.rs](self_check.rs) | `self_check` |

## 运行

从仓库根目录执行全部测试，或按表中 target 选择一个行为组：

```bash
cargo test --locked
cargo test --locked --test identifier_subjects
cargo test --locked --test documentation_regressions python_property_accessors
cargo test --locked --test dependency_contract completion::
cargo test --locked --test documentation_regressions carriers::
```

嵌套测试路径由 [Cargo.toml](../Cargo.toml) 的 `[[test]]` 注册；根目录两个测试由 Cargo 自动发现。
子模块由所属入口的 `mod` 声明注册；新增文件时必须确认它进入 `cargo test --locked -- --list`，
不能只创建文件而遗漏执行入口。使用函数名片段的过滤命令不受模块前缀影响；使用 `--exact` 时须带完整模块名。

## 样例和辅助

[review_fixture](review_fixture/mod.rs) 统一装配 Authority JSON 与内存源码输入；具体 Authority、变异和断言留在所属测试。
单个规则的短样例就近内联；[fixtures](fixtures/) 保存表驱动回归数据，不承载产品逻辑。

[Rust 导入树样例](fixtures/rust-use-trees.json) 每行记录源码、排序问题数和声明数；
依赖测试通过公共入口检查嵌套、别名、路径、数字平局和排版变体，另保留未知结构、通配及精确位置断言。

[四语言冻结样例](../docs/fixtures/core/README.md) 位于开发资料目录，包含故意违规或损坏的源码，用于证明工具能正确检出问题。
它们不进入安装包，也不混入 `tests` 的 Rust 源码自检范围。源文件字节和精确预期由样例 manifest 绑定。
[声明覆盖清单](../docs/fixtures/core/declaration-coverage.md) 连接语言结构与具体测试，并保留专项证据缺口。

测试通过、源码三零和冻结语料测量分别提供行为、规范和性能证据；完整候选验收按[验收指南](../docs/fixtures/core/README.md#复现与重测)执行。
