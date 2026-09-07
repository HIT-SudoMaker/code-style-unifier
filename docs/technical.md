# CSU 技术参考

本文说明当前实现的输入、观察、结果和身份合同。规则见[编码规范](coding_standards.md)，
CLI 操作见[使用说明](usage.md)，架构取舍见[设计原理](design.md)。

## 输入合同

### Rust 入口

`WorkspaceReviewer::compile(AuthorityInput)` 接纳并编译 Authority，失败时返回 `ReviewRejection`。
已编译审查器的 `review(ReviewInput)` 返回 `ReviewTerminal`；调用者无需管理解析器或语法节点。

| 输入 | 接纳条件 |
|---|---|
| `AuthorityInput::Directory` | 从指定目录读取 `authority.json` |
| `AuthorityInput::Documents` | 恰好一份文档，相对路径为 `authority.json` |
| `ReviewInput::Workspace` | 枚举根目录下的普通文件，接纳受管语言源码 |
| `ReviewInput::Documents` | `DocumentSet` 提供非空 revision 和相对路径/字节集合；每份文档都必须属于受管语言 |

工作区中的非受管文件跳过，显式内存集合中的非受管文档拒绝。CLI 只提供工作区入口。

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

顶层 `schema_version` 必须为 4。其余字段缺省为空集合或 `null`；事实的允许影响范围由
[编码规范 §1.1](coding_standards.md#11-规则依据)规定。

| 字段 | JSON 形状 |
|---|---|
| `public_callables` | 相对源码路径 → callable 名称字符串数组 |
| `token_vocabulary` | 词元字符串数组 |
| `quantity_concepts` | 概念名 → 表示后缀字符串数组 |
| `header_languages` | 相对 `.h` 路径 → `"c"` 或 `"cpp"` |
| `external_fixed_identifiers` | `{profile, role, owner, spelling}` 数组；当前只接纳 `rust` / `function` |
| `dependency_authority` | `null` 或依赖事实对象 |

依赖对象含三个 Python 根名数组：`python_standard_library`、`python_third_party`、`python_project_roots`，
缺省为空；`python_reorder_safe`、`rust_reorder_safe` 缺省为 `false`。
根名须为原生标识符，三个分类不能重叠。字段不提供 C/C++ 目标或预处理解析能力。
配置和受阻处理示例见[依赖审查说明](usage.md#审查依赖声明)。

未知字段、原始映射重复键、路径规范化碰撞、无效事实登记和不支持的外部身份在读取源码前拒绝。
格式接纳不证明项目事实真实，内容仍由项目负责人确认。

### 路径与语言

源码路径规范化为 `/` 分隔的相对路径；拒绝绝对路径、盘符前缀、空段、`.`、`..` 和规范化重名。
Authority 中的源码路径相对审查范围，而非 Authority 目录。

| 扩展名 | 语言 |
|---|---|
| `.py` | Python |
| `.rs` | Rust |
| `.c` | C |
| `.cc`、`.cpp`、`.cxx`、`.hpp`、`.hh`、`.hxx` | C++ |
| `.h` | 由 `header_languages` 的精确路径事实决定 |

工作区遍历不跟随符号链接，也不应用 `.gitignore` 或构建目录过滤；调用者须选择合适范围。

## 捕获与观察

工作区先接纳路径，再逐文件捕获字节；哈希、物理行检查和结构解析共用这份内容。
这不是文件系统原子快照，Seal 绑定实际捕获的输入。内存文档复制后进入相同处理流程。

当前实现先持有全部捕获内容，再逐文件处理并释放源码缓冲区。语法树留在文件处理周期内；
内存占用既包括结果，也包括尚未处理的源码。无效 UTF-8 不进入解析器，有效输入至多结构解析一次。
位置从 1 开始，列号按字节计数。

| 指标 | 计数含义 |
|---|---|
| `files_read` | 成功捕获的受管文档；包括内存输入 |
| `byte_sweeps` | 物理行观察次数 |
| `structural_parses` | 结构解析次数 |

这些指标不统计哈希、UTF-8 校验或所有缓冲区访问，不能据此推断总内存读取次数。

### 语言观察

四种语言使用锁定的 Tree-sitter 语法；版本来源见 `Cargo.lock`，观察协议身份由 `ProfileLaw` 定义。
`ERROR` 或 `MISSING` 节点形成可解析性问题，依赖完整结构的判断保留受阻状态。

观察限于源码能够直接证明的声明、文档和依赖关系。可解析不等于完成名称解析、类型推导或构建目标分析。
例如，Rust 非字面量文档属性可能受阻，Python 来源追踪不展开任意赋值别名，C/C++ 依赖分析缺少目标和预处理能力。
逐类支持、排除和测试缺口统一见[声明覆盖清单](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/docs/fixtures/core/declaration-coverage.md)。

## 规则查询与完成记录

`StandardLaw` 保存固定规则，`RuleLaw` 提供规则身份、等级和 `semantic_revision`；
`project_fact_revision` 标识事实接纳及影响协议。项目输入不能修改规则等级或执行逻辑。
编译时建立事实索引，审查时复用；仅改变索引表示不应改变语义身份。

每文件固定有 Capture、PhysicalLines、Structure、Identifier、Documentation、DependencyDeclaration 六类记录。
每类为 `Complete(数量)` 或 `Blocked(原因)`；`Complete(0)` 表示已确认没有该类对象。
受阻数量按文件/类别计，原因中的多个位置不另算多个受阻项。

缺少事实或遇到未知结构时，已独立证明的问题仍保留。例如 Rust `use` 列表保留未知成员的位置，
继续检查已知相邻成员和独立子列表，不跨越未知成员进行比较。
结果存储随文件的六类状态、实际问题和受阻原因增长，不是逐语法节点保存完整义务图。

## 结果与身份

### 终态与输出

| 公共终态 | 含义 |
|---|---|
| `Rejected` | Authority 或审查请求未被接纳 |
| `Failed` | 审查生命周期发生执行失败 |
| `Sealed` | 范围、问题和完成记录已封存；可能完整，也可能不完整 |

`Sealed` 中，任一类别受阻即为 `Incomplete`；全部完成后，有问题为 `Findings`，无问题为 `Clean`。
问题等级只有 `HardViolation` 和 `ReviewRequired`；受阻是完成状态，不是问题等级。

CLI JSON 使用 schema 4，顶层为 `schema_version`、`terminal`、`disposition`，并按终态携带：

- `review`：scope、completion、finding_summary、findings、blocked_families、blocked_family_details、metrics、presentation、seal。
- `error`：code、message，供 `Rejected` 或 `Failed` 使用。

机器调用须检查终态与对应对象；错误输出不能当作零问题结果。退出码及捕获方法见[读取结果](usage.md#读取结果)。
文本与 JSON 投影只读取既有终态。文本将动态控制字符显示为可见转义；JSON 与 Seal 保留原始事实。

`SealedReview::canonical_bytes()` 是另一个序列化合同：包含完整 coverage、语义 Authority 摘要和源码快照摘要，
不能与 CLI 展示 JSON 混用。它也包含 metrics；包含于序列化不代表参与 Seal 计算。

### 摘要绑定

语义 Authority 摘要绑定固定规则与规范化项目事实。集合和映射的输入重排不改变摘要；
新增有效事实或改变规则语义可能改变它。序列化布局属于身份协议，身份生成失败不会回退为替代摘要。

Seal 进一步绑定源码快照、范围、类别记录、问题、完整性和审查 schema。
工作区的规范化根路径、内存输入的 revision 均属于范围，因此相同文件内容不保证不同范围的 Seal 相同。
时钟、展示布局及运行指标不参与 Seal；二进制身份须另核对运行记录或发布校验和。

Seal 不证明运行时正确性、业务事实真实性或当前文件仍与捕获时一致。
规则或观察含义改变时，应更新相应身份并补充公共入口行为证据。

## 实现位置

以下路径相对源码仓库根目录；公开 Rust API 文档可用 `cargo doc --no-deps` 生成。

| 文件 | 职责 |
|---|---|
| `src/lib.rs` | 公开接口 |
| `src/authority.rs` | 固定规则、输入接纳、事实索引和语义摘要 |
| `src/review.rs` | 范围接纳、捕获、语言观察、规则判断及封存 |
| `src/model.rs` | 结果模型和规范序列化 |
| `src/projection.rs` | 文本和 JSON 展示 |
| `src/main.rs` | CLI 参数、输出和退出码 |

## 验证与兼容性

[测试指南](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/tests/README.md)提供行为回归入口；
[靶场与发布验收](https://github.com/HIT-SudoMaker/code-style-unifier/blob/main/docs/fixtures/core/README.md)定义冻结语料、测量和候选校验。
收据只证明其绑定的候选与环境；历史测量不自动适用于后续修改或其他平台。

CLI 与固定规则负责判断，skill 负责调用和解释。两个平台的共享 skill 文件逐字镜像，
`agents/openai.yaml` 为 Codex 专用元数据；镜像一致不保证不同模型或权限下的 Agent 行为一致。
