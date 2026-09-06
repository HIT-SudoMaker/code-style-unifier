# CSU 技术参考

本文描述当前实现的输入、事实流、结果及身份协议，供库调用者和维护者定位行为。
规则含义见[编码规范](coding_standards.md)，架构取舍见[设计原理](design.md)，CLI 操作见[使用说明](usage.md)。

## 实现位置

以下路径相对源码仓库根目录；公开 Rust 文档可在 checkout 中用 `cargo doc --no-deps` 生成。

| 文件 | 主要职责 |
|---|---|
| `src/lib.rs` | 公开输入、审查器、终态和投影接口 |
| `src/authority.rs` | 固定规则、Authority 接纳、事实索引和联合语义摘要 |
| `src/review.rs` | 范围接纳、源码捕获、语言观察、规则判断及封存 |
| `src/model.rs` | 范围、问题、六类完成记录、终态及规范序列化 |
| `src/projection.rs` | 已确定终态的文本与 JSON 展示 |
| `src/main.rs` | CLI 参数、输出和退出码 |

## 输入合同

### Rust 入口

`WorkspaceReviewer::compile(AuthorityInput)` 返回已编译审查器或 `ReviewRejection`。
`review(ReviewInput)` 返回 `ReviewTerminal`；解析器、语法节点和内部索引不通过公共接口暴露。

| 输入 | 形状与条件 |
|---|---|
| `AuthorityInput::Directory` | 从指定目录读取 `authority.json` |
| `AuthorityInput::Documents` | 内存集合必须恰好含一份相对路径为 `authority.json` 的文档 |
| `ReviewInput::Workspace` | 枚举指定根目录中的普通文件，按固定扩展名和路径事实接纳源码 |
| `ReviewInput::Documents` | `DocumentSet` 提供非空 revision 及相对路径/字节集合；每份文档都必须属于受管语言 |

工作区中的非受管文件跳过；显式内存集合中的非受管文档则拒绝，避免调用者误以为提交的文档已被检查。
CLI 只提供工作区入口，没有内存集合的 `--revision` 参数。

```rust
use csu::{AuthorityInput, ReviewInput, WorkspaceReviewer};
use std::path::Path;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let reviewer = WorkspaceReviewer::compile(
        AuthorityInput::Directory(Path::new(".csu/authority")),
    )?;
    let terminal = reviewer.review(ReviewInput::Workspace(Path::new("src")));
    println!("{}", csu::project_human(&terminal));
    Ok(())
}
```

### Authority 数据

顶层 `schema_version` 必须为 4；其余六个字段缺省为空集合或 `null`。
使用示例在[使用说明](usage.md#完成第一次审查)，每类事实允许影响什么由[编码规范 §1.1](coding_standards.md#11-规则依据)统一规定。

| 字段 | JSON 形状 |
|---|---|
| `public_callables` | 相对源码路径 → callable 名称字符串数组 |
| `token_vocabulary` | 词元字符串数组 |
| `quantity_concepts` | 概念名 → 表示后缀字符串数组 |
| `header_languages` | 相对 `.h` 路径 → `"c"` 或 `"cpp"` |
| `external_fixed_identifiers` | `{profile, role, owner, spelling}` 记录数组；当前只接纳 `rust` / `function` |
| `dependency_authority` | `null` 或依赖事实对象 |

依赖对象接纳 `python_standard_library`、`python_third_party`、`python_project_roots` 三个名称数组，以及
`python_reorder_safe`、`rust_reorder_safe` 两个布尔值；缺省分别为空数组和 `false`。
它没有 C/C++ 构建目标、预处理或模块解析字段，不能据此完成相应的未知依赖事实。

顶层与记录拒绝未知字段。原始映射重复键、路径规范化碰撞、重叠依赖分类、无效量值登记和不支持的外部身份在读取源码前拒绝。
`AuthorityBundle` 一次反序列化并完整解构，编译后由 `CompiledAuthority` 统一提供查询。

### 路径与语言

源码路径统一为 `/` 分隔的相对路径，拒绝绝对路径、平台盘符前缀、空段、`.`、`..` 和规范化后的重名。
工作区范围身份保留其规范化根路径；内存范围身份保留调用方提供的 revision。

| 扩展名 | 语言 |
|---|---|
| `.py` | Python |
| `.rs` | Rust |
| `.c` | C |
| `.cc`、`.cpp`、`.cxx`、`.hpp`、`.hh`、`.hxx` | C++ |
| `.h` | 由 `header_languages` 的精确路径登记决定 |

接纳由 `source_admission` 与固定语言表统一执行，不根据目录或隐藏清单选择语言或源码。
工作区遍历不跟随符号链接，仅接纳普通文件；当前没有 `.gitignore` 或构建目录过滤语义，调用者应明确选择范围。

## 捕获与观察

工作区先枚举并接纳路径，再将每个受管文件读取一次。后续哈希、物理行观察和结构解析使用读得的同一份字节。
这是逐文件捕获，不提供文件系统原子快照；Seal 绑定实际读到的内容。
内存输入也复制为同一内部文档表示，之后共用审查流程。

当前实现先持有捕获的源码集合，再逐文件处理；内存上界还包括这份集合，不能只按结果记录的大小估算。
每个文件完成后释放其源码缓冲区；语法树、游标和借用节点留在文件处理周期内。
无效 UTF-8 不进入解析器，有效输入至多进行一次结构解析。

| 指标 | 计数对象 |
|---|---|
| `files_read` | 成功捕获的受管文档 |
| `byte_sweeps` | 物理行观察次数 |
| `structural_parses` | 结构解析次数 |

指标不包含哈希、UTF-8 校验及已定位文本观察等其他缓冲区访问。
位置从 1 开始，列号按字节计数；无效 UTF-8 通过有界前缀遍历定位，当前不维护独立行索引。

### 语言观察

观察身份由 `ProfileLaw` 维护，锁定的依赖来源见 `Cargo.lock`：

| 语言 | 观察身份 |
|---|---|
| Python | `tree-sitter-python@0.25.0+direct-source-facts` |
| Rust | `tree-sitter-rust@0.24.2+direct-source-facts` |
| C | `tree-sitter-c@0.24.2+direct-source-facts` |
| C++ | `tree-sitter-cpp@8b5b49eb+direct-source-facts` |

`ERROR` 或 `MISSING` 节点构成可解析性失败。声明和文档通过 `DeclarationReview` 在同一遍历中观察，参数从共同绑定分类取得名称与完整性，普通注释不占参数位置。
升级解析器或观察协议时，同步语言身份与行为证据；版本号本身不是作者的命名要求。

| 观察主题 | 当前处理方式 | 定位 |
|---|---|---|
| C/C++ 声明列表 | 按名称附近的派生结构区分函数和函数指针对象；逐函数 declarator 读取参数、返回和位置，共用声明载体及公开上下文 | `native_family_function_declarator`、`observe_callable` |
| C++ const 结构化绑定 | 按对象层级判断 const；按值范围绑定仅用同一 compound 内紧邻此前的基础类型多维数组声明证明常量角色 | `native_family_declaration_is_constant`、`cplusplus_constant_binding_is_proven` |
| Python 原生库及内建身份 | 沿模块、类体的直接导入和先前绑定查找；赋值别名与函数局部来源不展开 | `python_import_identity` |
| Python 装饰器与 receiver | 枚举未知装饰器保留成员归属受阻；普通方法的未知装饰器保留实例 receiver 默认；裸内建拼写受遮蔽时不授予该身份 | `python_variant_member_decorator`、`python_receiver_spelling` |
| Python 属性文档 | 只在直接 getter 及同名访问器关系可证明时共享文档，与枚举成员身份判断分开 | `observe_python_decorated_visibility` |
| 返回要求 | 仅用直接声明形成 `NoValue / Never / Value / Unknown`，不返回优先，不追踪别名定义 | `callable_return_shape` |

数组证明还要求范围右侧为直接名称、范围语句无 initializer，数组派生结构中没有指针或其他未知层；允许中间只有注释。
未证明的 const 按值结构化绑定使 Identifier 受阻，引用绑定保留 Value 角色；不把这些局部证据推广为任意 tuple 或 mutable 成员的语义证明。
逐类支持、排除、受阻及专项测试缺口见源码仓库的[声明覆盖清单](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/docs/fixtures/core/declaration-coverage.md)。

## 规则查询与完成记录

`StandardLaw` 保存实际执行的固定规则、语言记录和相关算法修订。
`RuleLaw` 统一提供操作符、标识、等级、说明、负责人问题与 `semantic_revision`；展示章节和顺序在同一记录中维护，但排除在语义序列化之外。
`project_fact_revision` 标识固定事实校验及影响协议，不是运行开关。

`AuthorityIndexes` 在编译时建立按长度排序的前后缀表，以及精确量值名称和规范大写呈现的索引。
每个声明使用这些已建索引，不重新排序标记。完整词元大小写规则由规范定义，接纳与观察共用 `lowercase_token`。
改变索引表示不应改变语义摘要；改变判断含义则应更新对应规则身份及公共入口证据。

每文件固定有 Capture、PhysicalLines、Structure、Identifier、Documentation、DependencyDeclaration 六类记录。
每类只取 `Complete(数量)` 或 `Blocked(原因)`；`Complete(0)` 表示已确认没有对象。
`FamilyClosure` 构造完整类别记录，避免另一套“需要/已执行”标记与结果发生漂移。
记录空间随“文件数 × 六类状态 + 实际问题和受阻原因”增长；这不包含上文所述的源码捕获缓冲区。

## 结果与身份

### 终态与输出

| 公共终态 | 内容 |
|---|---|
| `Rejected` | Authority 或请求未被接纳，携带错误代码和说明 |
| `Failed` | 审查生命周期失败，携带错误代码和说明 |
| `Sealed` | 已确定范围、问题和覆盖记录，可完整或不完整 |

`Sealed` 的 disposition 由覆盖与问题共同决定：任一类别受阻为 Incomplete；否则有问题为 Findings，无问题为 Clean。
问题等级只有 HardViolation、ReviewRequired；受阻是完成状态，不是第三种问题等级。

CLI JSON 顶层包含 `schema_version`、`terminal`、`disposition`，随后按终态携带 `review` 或 `error`。
`review` 含 scope、completion、finding_summary、findings、blocked_families、blocked_family_details、metrics、presentation 和 seal。
错误对象含 code 与 message。机器调用应按终态检查对应对象，不把错误对象当作空的审查结果。

`project_human` 与 `project_javascript_object_notation` 只读取既有终态。
`SealedReview::canonical_bytes()` 是另一种规范序列化：它保留完整 coverage、语义 Authority 摘要和源码快照摘要，不能与 CLI 的展示 JSON 混用。
输出顺序和字段的回归位于 `tests/review/projection_cli.rs`，规范身份回归位于 `tests/review/terminal_contract.rs`。

### 摘要绑定

语义 Authority 摘要序列化实际使用的固定规则和规范化项目事实，字节直接进入 BLAKE3 derive-key。
序列化布局属于身份协议；Authority 序列化失败返回 `authority.identity`，不回退成另一种摘要。
集合和映射的输入重排不改变该摘要；新增有效事实或改变规则语义可以改变它。

Seal 进一步绑定源码快照、明确范围、类别记录、问题、完整性和审查 schema 版本。
运行指标随结果记录，但不参与 `compute_seal`；可执行文件身份需结合运行来源记录或发布校验和核对。
工作区根路径与内存 revision 属于明确范围；其他临时输出路径、时钟及展示布局不进入语义身份。
旧 Seal 不能说明当前源码，新的展示文件也不能替代原始封存证据。

## 验证与兼容性

公共入口测试、测量与候选验收见源码仓库的[靶场与发布验收](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/docs/fixtures/core/README.md)。
性能和规模以绑定候选的 manifest 与收据为准。

共享 skill 位于 `.agents/skills/csu-review`，共享文件在 `.claude/skills/csu-review` 中逐字镜像，`agents/openai.yaml` 是平台专用 UI 元数据。
`tests/self_check.rs` 检查两端共享文件一致性及产品身份；这不承诺不同主机、模型和权限下的 Agent 行为完全相同。
CLI 二进制与规则负责判断，skill 指令负责调用和解释。

## 参考依据

以下资料解释语言和工具行为；中文摘要、句末标点、对齐、单位后缀及 C/C++ 文档块格式是 CSU 的规则选择。

| 范围 | 原始参考 |
|---|---|
| 单位与表示 | [BIPM SI Brochure](https://www.bipm.org/en/publications/si-brochure/)、[NIST SP 811](https://www.nist.gov/pml/special-publication-811) |
| Python 名称与函数 | [词法](https://docs.python.org/3/reference/lexical_analysis.html#identifiers)、[函数定义](https://docs.python.org/3/reference/compound_stmts.html#function-definitions)、[ast.get_docstring](https://docs.python.org/3/library/ast.html#ast.get_docstring) |
| Python 风格与依赖 | [PEP 8](https://peps.python.org/pep-0008/)、[PEP 257](https://peps.python.org/pep-0257/)、[import 语句](https://docs.python.org/3/reference/simple_stmts.html#the-import-statement)、[TYPE_CHECKING](https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING) |
| Rust 名称与文档 | [标识符](https://doc.rust-lang.org/reference/identifiers.html)、[注释](https://doc.rust-lang.org/reference/comments.html)、[风格指南](https://doc.rust-lang.org/style-guide/)、[API 命名](https://rust-lang.github.io/api-guidelines/naming.html)、[rustdoc](https://doc.rust-lang.org/rustdoc/how-to-write-documentation.html) |
| Rust 依赖 | [use 声明](https://doc.rust-lang.org/reference/items/use-declarations.html)、[导入风格](https://doc.rust-lang.org/stable/style-guide/items.html#imports-use-statements) |
| C 与 C++ | [WG14 N3220](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n3220.pdf)、[WG21 工作草案](https://eel.is/c++draft/)、[C++ 命名指南](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-naming) |
| 解析与错误节点 | [Tree-sitter 生命周期](https://tree-sitter.github.io/tree-sitter/using-parsers/2-basic-parsing.html)、[ERROR/MISSING](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html#the-error-node)、[Rust Parser](https://docs.rs/tree-sitter/0.26.13/tree_sitter/struct.Parser.html)、[Node](https://docs.rs/tree-sitter/0.26.13/tree_sitter/struct.Node.html) |
| 确定性 | [BTreeMap](https://doc.rust-lang.org/std/collections/struct.BTreeMap.html)、[HashMap](https://doc.rust-lang.org/std/collections/struct.HashMap.html)、[SARIF Appendix F](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html#appendix-F) |
