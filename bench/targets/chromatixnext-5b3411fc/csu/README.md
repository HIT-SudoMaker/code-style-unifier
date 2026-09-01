# CSU - 语义级代码风格检查器

CSU（Code Style Unifier）是一个面向 agent 时代大型代码库的语义级代码风格检查器。它不处理空格、缩进和括号这些格式问题，而是检查更高一层的约定：命名是否统一，公开 API 是否有文档，术语是否漂移，注释语言是否混乱，依赖和安全相邻边界是否仍然清楚。

它的工作方式很简单：先把 Python / Rust / C / C++ 源码提取成统一的 evidence layer，再让 56 条规则契约只基于这层证据做判断，最后输出 JSON / JSONL，交给 Codex、Claude Code 或脚本继续修正、校准与复核。

当前规则集包含 Core 28 条、Python 8 条、Rust 10 条、C/C++ 10 条。命令行二进制名为 `csu`。

## 为什么有 CSU

这个项目来自我维护大型科研代码库时反复遇到的一个问题：代码规模增长到几万行、十几万行之后，困难不只在于“还能不能写得动”，更在于“写完之后是否还看得清、管得住、改得动”。

LLM 和 Codex、Claude Code 这类 agent 工具让个人和小团队获得了过去难以想象的代码生产能力。以前一个人长期维护几万行代码已经很吃力；现在，借助 agent，开发和管理 10 万行、20 万行，甚至更大规模的项目，已经不再遥不可及。但代码生成变便宜之后，项目并不会自动变清晰。相反，当更多代码由不同人、不同 agent、不同会话连续写入时，项目表面还能运行，局部也都说得过去，整体表达却会慢慢变散。

大型项目的劣化通常有两类。第一类是架构耦合：模块互相纠缠，依赖方向混乱，改一处牵动一片。这类问题棘手，但通常足够显眼。第二类更隐蔽，我把它称为语义退化：命名风格、文档习惯、术语取舍、注释语言在多轮修改后逐渐漂移。到了这个时候，即便翻出项目初期的约定文档，那套约定也可能已经名存实亡。

举例来说，同样是表达“是否就绪”，模块 A 写成 `is_ready`，模块 B 写成 `ready_flag`，模块 C 又写成 `check_ready`；同样是专业术语，有的模块保留 `SSIM`、`ABI`、`NCHW`，有的模块却把它们当成不规范缩写；同样是公开接口，有的地方认真写好了文档契约，有的地方完全裸露在外。这些写法单独看未必有错，也未必影响程序运行，但放在同一个项目里，理解成本会持续升高。

换言之，LLM 把“写代码”变便宜了，却把“让大量代码彼此一致”变贵了。CSU 要解决的就是这个中间层问题。

## CSU 的位置

传统工具各自有清楚边界。Formatter 处理空格、换行和缩进，比如 black、rustfmt、clang-format；compiler 和 type checker 处理语法、类型与生命周期，比如 rustc、mypy、TypeScript；linter 处理常见错误、局部质量和语言习惯，比如 Ruff、Clippy、ESLint。它们都很重要，但通常不会回答这些问题：这个模块的命名是否与项目其他部分一致？这个公开接口是否符合文档约定？这段注释的语言是否和整体表达风格发生了漂移？

只依赖 LLM 也不稳。长上下文不等于全局理解；当项目约定分散在大量文件、模块和历史修改中时，模型容易遗漏局部约束、混淆相似语义，甚至给出看似合理却难以追溯的判断。Agent 很适合执行明确任务，但不应该被迫独自承担跨文件、跨模块、跨历史版本的语义一致性审查。

CSU 位于 formatter / compiler / linter 之上、架构审查之下：

| 层次 | 关心的问题 | 典型工具 |
|------|------------|----------|
| 格式层 | 空格、换行、缩进、括号 | black、rustfmt、clang-format |
| 语法/类型层 | 语法错误、类型错误、生命周期 | 编译器、mypy、clippy |
| 语义风格层 | 命名一致性、文档契约、术语策略、public surface 边界 | CSU |
| 架构层 | 模块划分、依赖方向、分层 | 架构审查工具 |

它不重新发明格式化，也不替代架构判断。它做的是更窄的一件事：用可复现、可追溯、可校准的规则契约，检查那些“格式对、程序也能跑，但语义风格正在漂移”的问题。

## 快速开始

在源码仓库里可以直接运行：

```powershell
cargo run --release -- check src --format json --output .csu/csu_src.json --no-history
```

发布包解压后直接调用：

```powershell
bin\csu.exe check src --format json --output .csu/csu_src.json --no-history
```

常用命令如下：

```powershell
csu check src --format jsonl --no-history
csu check tests --format json --output .csu/csu_tests.json --no-history
csu rules --format json
csu calibrate --issues .csu/csu_src.json --cases calibration/cases.jsonl --output .csu/calibration.json
csu history --history-dir .csu/history list
```

`check` 的退出码和阻塞状态一致：只要存在 `blocks: true` 的 issue，退出码就是 `1`；否则退出码为 `0`。

## 核心设计

CSU 的可靠性主要来自一个设计选择：所有规则都只读 evidence layer，不反复读源码。

```text
源码文件（.py / .rs / .c / .h / .cc / .cpp / .hpp / ...）
  -> scanner        扩展名过滤、排除目录、blake3 指纹、C/C++ 生成标记判定
  -> frontend       tree-sitter 解析，提取统一证据
  -> EvidenceStore  13 类事实
  -> evaluators     Core / Python / Rust / C/C++ 规则，只读证据
  -> profile        启用集、阈值、术语策略
  -> calibration    人工标注交叉验证
  -> JSON / JSONL   agent 可读输出
```

scanner 和 frontend 负责把源码变成事实；evaluators 只根据事实判定规则。这让事实提取和规则判断解耦：新增规则通常不需要改解析逻辑，规则本身也更容易测试和回归。给定相同源码、profile 与 history 开关，证据层应当稳定；只有证据稳定，后面的人工校准才有意义。

当前 evidence layer 包含 13 类事实：

| 事实类型 | 含义 | 典型规则 |
|----------|------|----------|
| `workspace` | 工作区元信息、语言边界、指纹 | Core001、Core005 |
| `file_unit` | 文件单元信息 | Core006、Core007 |
| `module_unit` | 模块级结构、import、prelude | Core008、Rust003 |
| `dependency_edge` | import / include / use 依赖边 | Core003、Core009、Core010 |
| `doc_region` | docstring / doc comment 文档区域 | Core011、Core012、Core022 |
| `comment_region` | 普通注释区域 | Core017 |
| `text_span` | 摘要、术语、内部文本 | Core023、Core026、Core027 |
| `line_span` | 行文本、行长、suppression | Core018、Core019 |
| `public_surface` | 公开 API 面 | Core011 |
| `block_region` | unsafe、async、模板、预处理块 | Rust007、Cpp008 |
| `symbol` | 函数、类型、变量等符号 | Core014、Core015、Core016 |
| `expression` | 错误消息、日志、宏调用 | Core028、Py008 |
| `history_health` | 扫描历史健康度 | Core005 |

Frontend 基于 tree-sitter 做语法解析，并对文本做确定性归一化，例如大小写、空白和术语切分。C/C++ 生成文件有单独的性能取舍：CSU 只读取前 8192 字节判断是否存在 `do not edit`、`automatically generated`、`.pb.cc` / `.pb.h`、`amalgamation` 等生成标记。生成代码动辄数十万行，逐行检测既慢又没有意义；它们的“风格”由生成器决定，不由人控制。

我选择 Rust 实现 CSU，也是因为它适合这种基础工具：单二进制分发方便，启动和扫描性能稳定；类型系统、枚举和 `Result` 能把 evidence、issue kind、规则边界表达得更明确；内存安全和所有权模型也适合长期演进。

目前 CSU 只覆盖 Python、Rust、C、C++。这不是因为别的语言不重要，而是因为语义风格规则需要理解语言生态、命名传统、文档习惯、FFI/ABI/类型边界。对不了解的语言，强行写规则只会制造看起来覆盖广、实际不懂边界的误判。

## Profile 与校准

`profiles/default.toml` 控制一次扫描的边界，包括启用哪些规则、排除哪些目录和文件、行长与摘要长度阈值、术语白名单与禁用缩写映射。可以按名称加载 profile，也可以直接指定 TOML 文件：

```powershell
csu check src --profile default
csu check src --profile-path profiles/default.toml
```

校准是 CSU 能长期演进的关键。`csu calibrate` 会用人工样本交叉验证 `check` 输出：某个 issue 是否真实存在，`rule`、`kind`、`path`、`range`、`evidence` 是否一致，人工判断是否有足够清楚的依据。

这里有一条硬约束：禁止以“减少 findings 数量”为优化目标。数量不是目标，规则边界才是目标。校准样本必须基于事实、规则、级别或边界给出理由。如果一条 case 证明规则需要收窄、扩展或防回退，就应该把它沉淀成回归测试，让规则不会无声地忘记已经被纠正过的边界。

## 规则体系

CSU 的规则分成四个族：Core 规则处理跨语言通用契约，例如命名、文档、依赖、术语和 suppression；Python 规则处理 docstring、future import、typing、logging；Rust 规则处理 FFI、unsafe、async、cfg、panic；C/C++ 规则处理 include、宏、ABI、模板和所有权。C/C++ 规则族目录名为 `cpp`，但规则覆盖 C 与 C++ 两种语言。

每条 issue 都有一个 `kind`：

- `hard_violation` 表示契约明确被破坏，通常会阻塞；
- `under_review` 表示规则有依据，但需要 agent 或人结合上下文判断；
- `soft_friction` 表示轻摩擦提示，默认不阻塞。

Core 规则 ID 按 scope 大致从大到小组织：项目、文件、模块、依赖、文档、符号、文本、表达式。即便同属一个 domain，也会按粒度放在合适位置。

Core022 `docs.physical_layout` 是 1.2.0 的关键变化。它负责文档物理布局：Python inline docstring 会被视为 `hard_violation`。

```python
def run():
    """Return result."""
```

应写成：

```python
def run():
    """
    Return result.
    """
```

这个子契约只作用于 Python 三引号 docstring。Rust / C / C++ 常用的 `///` doc comment 不套用该约束。Core021 与 Core022 放在相邻位置也是有意的：Core021 关注布局一致性，Core022 关注文档物理形态，它们都属于较小粒度的文本/文档布局约束，符合 Core 规则从大 scope 到小 scope 的排序。

## Agent 如何使用 CSU

CSU 的输出是给 agent 和脚本消费的结构化 JSON。一个 issue 大致长这样：

```json
{
  "id": "issue:Core016:ev_file_<hash>_symbol_function_391_1_<hash>",
  "kind": "under_review",
  "rule": "Core016",
  "name": "naming.boolean_predicate",
  "scope": "symbol",
  "domain": "naming",
  "language": "rust",
  "path": "core/calibration.rs",
  "range": "391:1-391:1",
  "message": "布尔谓词命名需要审查",
  "evidence": ["ev:file:<hash>:symbol:function:391:1:<hash>"],
  "blocks": false
}
```

实际调度时，agent 通常先按 `kind` 分流：`hard_violation` 直接修，`under_review` 结合上下文判断，`soft_friction` 记录或延后处理。`rule` 和 `name` 用来定位契约，`path` 和 `range` 用来跳到代码位置，`evidence` 用来回溯证据层，`blocks` 决定流程是否失败。

CSU 不替 agent 决定怎么改。它只负责指出问题在哪、依据是什么、是否阻塞；具体修复由 agent 或人完成。改完之后重新运行 `check`，确认 issue 消失，或确认级别与契约一致。

## 使用与打包

构建本机二进制：

```powershell
cargo build --release
```

产物路径：

- Windows：`target\release\csu.exe`
- Linux / macOS：`target/release/csu`

本地打包当前平台：

```powershell
pwsh ./scripts/package-release.ps1
```

发布包保持解压即用：

```text
csu-<version>-<platform>/
  bin/csu(.exe)
  profiles/default.toml
  agent-skills/csu/SKILL.md
  examples/commands.md
  README.md
  LICENSE
```

常用子命令包括 `check`、`calibrate`、`rules` 和 `history`。其中 `check` 支持 `--profile`、`--profile-path`、`--history-dir`、`--format`、`--output`、`--no-history`。扫描历史默认写入 `.csu/history`，可用 `history list` 查看，用 `prune` 清理过期记录，用 `clear` 清空。

## 内部发布门槛

发布前至少通过：

```powershell
cargo test
cargo run --quiet -- check src --format json --output .codex_tmp\csu-src-gate.json --no-history
cargo run --quiet -- check tests --format json --output .codex_tmp\csu-tests-gate.json --no-history
cargo run --quiet -- check . --format json --output .codex_tmp\csu-project-gate.json --no-history
```

涉及规则契约变化时，还要用真实项目靶场做 smoke scan：

```powershell
cargo run --quiet -- check E:\Year2026_Project_CompoundEyeONN\code --format json --output .codex_tmp\compoundeyeonn-gate.json --no-history
cargo run --quiet -- check E:\Year2026_Project_ONNs\code --format json --output .codex_tmp\onns-gate.json --no-history
```

外部扫描允许因为真实问题而以退出码 `1` 结束。关键不是“没有 findings”，而是确认 findings 与规则契约一致，没有 parser panic、误挂语言边界或明显错误归因。

## 边界

CSU 的价值建立在明确边界上。它不是 formatter，不处理空格、缩进、括号和普通换行风格；它不替代编译器、类型检查器或普通 linter；它也不把所有 findings 都当作失败，是否阻塞由 `blocks` 决定。

有些规则也刻意收窄了作用范围。例如导入排序只检查同一语义导入块内的契约，不跨延迟导入、`TYPE_CHECKING` 或条件边界替 formatter 重排。阈值与术语依赖 profile 配置，不内置一个放之四海而皆准的裁决。

`check` 当前只输出 JSON / JSONL，没有额外的人类友好 report 格式。这也是有意的：CSU 负责提供稳定证据和机器可读判断，人类友好呈现交给上层工具。

新增规则时，需要同步更新 `rules/<族>/`、`rules/catalog.toml`，并补充测试或 calibration case。

## 项目结构

```text
src/
  main.rs              # 入口、check/calibrate 输出、退出码
  core/
    scanner.rs         # 扫描、扩展名过滤、排除、blake3、生成标记
    frontend.rs        # tree-sitter 解析，提取证据
    evidence.rs        # EvidenceStore 统一证据层
    evaluators/
      core.rs          # Core 规则
      python.rs        # Python 规则
      rust.rs          # Rust 规则
      cpp.rs           # C/C++ 规则
    issue.rs           # Issue / IssueKind / Scope / Domain / Language
    profile.rs         # profile、阈值、术语策略
    calibration.rs     # 校准样本与交叉验证
    history.rs         # 扫描历史
    rules.rs           # 规则目录 TOML 解析
rules/
  catalog.toml
  core/
  python/
  rust/
  cpp/
profiles/
  default.toml
agent-skills/
  csu/SKILL.md
scripts/
  package-release.ps1
examples/
  commands.md
```

## 参考资料

- [1] *A Survey of Large Language Models*. https://arxiv.org/abs/2303.18223
- [2] 中山大学软件工程学院，LLM 与软件工程任务综述. https://sse.sysu.edu.cn/article/658
- [3] *Science China Information Sciences*, LLM4SE 综述. https://link.springer.com/article/10.1007/s11432-025-4670-0
- [4] *A Survey on Large Language Models for Code Generation*. https://arxiv.org/abs/2406.00515
- [5] *Stack Overflow 2025 Developer Survey*. https://survey.stackoverflow.co/2025/ai

## 许可证与贡献

许可证：MIT，见 `LICENSE`。

欢迎通过 calibration 样本、profile、规则契约扩展 CSU。新增规则需在 `rules/<族>/` 下登记契约 `.toml` 并汇总到 `rules/catalog.toml`，建议配套测试或校准样本。
