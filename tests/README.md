# CSU 测试

测试从公共审查入口进入，核对问题、完成状态、身份和展示结果。目录按行为组织；Cargo target 名称保留原有入口，定向测试命令不变。

| 目录或文件 | 验证职责 | Cargo target |
|---|---|---|
| [review/terminal_contract.rs](review/terminal_contract.rs) | Authority、输入拒绝、路径、六类完成记录、物理行与身份 | `terminal_contract` |
| [review/fixture_contract.rs](review/fixture_contract.rs) | 四语言冻结样例及语法损坏的精确预期 | `fixture_contract` |
| [review/projection_cli.rs](review/projection_cli.rs) | 文本、JSON、CLI 终态、等级计数、退出码与输入字节保持 | `projection_cli` |
| [identifier/subjects.rs](identifier/subjects.rs) | 声明主体、语言固定名称及外部归属 | `identifier_subjects` |
| [identifier/forms.rs](identifier/forms.rs) | 命名形式、前缀、量值后缀及优先级 | `identifier_forms` |
| [documentation/public_contract.rs](documentation/public_contract.rs) | 四语言公开文档的共同义务、精确硬违规与干净对照 | `public_review` |
| [documentation/layout.rs](documentation/layout.rs) | 原生载体、字段布局、叙述、标点和可见性 | `documentation_regressions` |
| [documentation/native_roles.rs](documentation/native_roles.rs) | C/C++ declarator、模板、作用说明及重载歧义 | `cpp_documentation_roles` |
| [documentation/return_shape.rs](documentation/return_shape.rs) | 直接返回声明及对应文档义务 | `return_shape_contract` |
| [dependency_contract.rs](dependency_contract.rs) | 依赖分类、分组、顺序与模块位置 | `dependency_contract` |
| [self_check.rs](self_check.rs) | 产品及测试源码三零、产品身份和 skill 镜像 | `self_check` |

## 运行

从仓库根目录执行全部测试，或按表中 target 选择一个行为组：

```bash
cargo test --locked
cargo test --locked --test identifier_subjects
cargo test --locked --test documentation_regressions python_property_accessors
```

嵌套测试路径由 [Cargo.toml](../Cargo.toml) 的 `[[test]]` 注册；根目录两个测试由 Cargo 自动发现。
新增文件时必须确认它进入 `cargo test --locked -- --list`，不能只创建文件而遗漏执行入口。

## 样例和辅助

[review_fixture](review_fixture/mod.rs) 统一装配 Authority JSON 与内存源码输入；具体 Authority、变异和断言留在所属测试。
单个规则的短样例就近内联；[fixtures](fixtures/) 保存表驱动回归数据，不承载产品逻辑。

[四语言冻结样例](../docs/fixtures/core/README.md) 位于开发资料目录，包含故意违规或损坏的源码，用于证明工具能正确检出问题。
它们不进入安装包，也不混入 `tests` 的 Rust 源码自检范围。源文件字节和精确预期由样例 manifest 绑定。
[声明覆盖清单](../docs/fixtures/core/declaration-coverage.md) 连接语言结构与具体测试，并保留专项证据缺口。

测试通过、源码三零和冻结语料测量分别提供行为、规范和性能证据；完整候选验收按[验收指南](../docs/fixtures/core/README.md#复现与重测)执行。
