# CSU — 语义级代码风格检查器

> **CSU**（Code Style Unifier）是一个面向 agent 时代大型代码库的语义级代码风格检查器。它不处理空格、换行和缩进，而是检查更高一层的问题：命名是否统一，公开 API 是否有契约文档，术语是否漂移，注释语言是否混乱，依赖和安全边界是否仍然可维护。CSU 用 Rust 实现，先把 Python / Rust / C / C++ 源码提取成统一 evidence layer，再基于 **56 条规则契约** 输出机器可读 JSON，供 Codex、Claude Code 或其他 agent 继续修正、校准与复核。

---

## 目录

- [1. 研究背景](#1-研究背景)
- [2. CSU 是什么](#2-csu-是什么)
- [3. 快速开始](#3-快速开始)
- [4. 工程设计](#4-工程设计)
- [5. 规则体系](#5-规则体系)
- [6. Agent 调度](#6-agent-调度)
- [7. 使用方法](#7-使用方法)
- [8. 设计取舍与边界](#8-设计取舍与边界)
- [9. 项目结构](#9-项目结构)
- [10. 参考资料](#10-参考资料)
- [11. 许可证与贡献](#11-许可证与贡献)

---

## 1. 研究背景

### 1.1 个人与小团队正在获得更大的代码生产能力

这个项目来自我维护大型科研代码库时反复遇到的一个问题：当代码规模增长到几万行、十几万行之后，困难不只在于“还能不能写得动”，更在于“写完之后是否还看得清、管得住、改得动”。

LLM 和 Codex、Claude Code 这类 agent 工具让个人和小团队获得了过去难以想象的代码生产能力。以前一个人长期维护几万行代码已经相当吃力；现在，借助 agent，开发和管理 10 万行、20 万行，甚至更大规模的项目，已经不再遥不可及。根据 Stack Overflow 2025 开发者调查，**84% 的受访者正在使用或计划使用 AI 开发工具** [5]。LLM 与软件工程的结合，也已经从代码生成扩展到代码摘要、漏洞检测、代码管理等任务 [1][2][3][4]。

但生产能力提高之后，项目并不会自动变得更清晰。相反，当更多代码由不同人、不同 agent、不同会话连续写入时，维护者很快会遇到一种新的压力：项目表面还能运行，局部也都说得过去，但整体表达开始变散，统一约定开始失效。

### 1.2 两类劣化：架构耦合与语义退化

大型项目膨胀时，常见的劣化大致有两类。

第一类是**架构上的耦合化**，也就是大家常说的“屎山化”：模块互相纠缠，依赖方向混乱，改一处牵动一片。这类问题当然棘手，但它通常足够显眼，也比较容易通过模块拆分、深度重构，甚至推倒重来加以缓解。

第二类更隐蔽，我把它称为**语义上的退化**：项目经过多次重构，由不同的人、不同的 agent 经手之后，命名风格、文档习惯、术语取舍、注释语言都可能逐渐漂移。到了这个时候，即便翻出项目初期约定的文档，那套统一约定也可能已经名存实亡。

举例来说，同样是表达“是否就绪”，模块 A 写成 `is_ready`，模块 B 写成 `ready_flag`，模块 C 又写成 `check_ready`；同样是专业术语，有的模块保留 `SSIM`、`ABI`、`NCHW`，有的模块却把它们当成不规范缩写；同样是公开接口，有的地方认真写好了文档契约，有的地方完全裸露在外。这些写法单独看未必有错，也未必影响程序运行；但一旦放在同一个项目里，代码就会越来越散。人类读者和 agent 都要不断在不同作者、不同语境、不同习惯之间切换，理解成本随之升高。

换言之，LLM 把“写代码”变便宜了，却把“让大量代码彼此一致”变贵了。

### 1.3 为什么现有工具不够

语义退化难处理，是因为它不像格式问题那样边界清楚。

传统工具各自有明确边界。Formatter 处理空格、换行和缩进，比如 black、rustfmt、clang-format；compiler 和 type checker 处理语法、类型与生命周期，比如 rustc、mypy、TypeScript；linter 处理常见错误、局部质量和语言习惯，比如 Ruff、Clippy、ESLint。但这些工具通常不会告诉我们：这个模块的命名是否与项目其他部分一致，这个公开接口是否符合项目文档约定，这段注释的语言是否与整体表达风格发生漂移。

只依赖 LLM 也不稳。长上下文并不等于全局理解：当项目约定分散在大量文件、模块和历史修改中时，模型容易遗漏局部约束、混淆相似语义，甚至给出看似合理却难以追溯的判断。Agent 很适合执行明确任务，但不应该被迫独自承担跨文件、跨模块、跨历史版本的语义一致性审查。

可以用一个层次模型来理解 CSU 的定位：

| 层次 | 关心的问题 | 典型工具 |
|------|-----------|----------|
| 格式层 | 空格、换行、缩进、括号 | black、rustfmt、clang-format |
| 词法/语法层 | 语法错误、类型错误 | 编译器、mypy、clippy |
| **语义风格层** | **命名一致性、文档契约、术语策略、public surface 边界** | **CSU** |
| 架构层 | 模块划分、依赖方向、分层 | 架构 lint（更高层，CSU 不覆盖）|

语义风格层的典型问题，formatter、compiler、普通 linter 都不会稳定解决：

- 模块 A 把公开 API 写成详细中文契约，模块 B 却只有英文短句；
- 模块 A 用 `is_ready` 表示布尔语义，模块 B 用 `ready_flag`，模块 C 用 `check_ready`；
- 模块 A 把 `cfg`、`ABI`、`SSIM` 当作专业术语，模块 B 却把它们当成违规缩写；
- Python、Rust、C/C++ 在不同 agent 生成的模块里有不同的注释、命名、错误消息边界和 public surface 习惯。

### 1.4 CSU 的定位

CSU 针对的正是这一层——**语义级风格统一**。它不重新发明格式化，也不试图替代架构审查；它做的是一件更窄的事：用可复现、可追溯、可校准的规则契约，检查那些“格式对、程序也能跑，但语义风格正在漂移”的问题。

CSU 的定位是传统工具与 agent 的中间层：底层用确定性的扫描与规则引擎建立事实，输出结构化 findings；上层让 agent 或人基于这些 findings 做修正、校准或复核。这样一来，agent 不需要凭印象在整个项目里“猜”哪里不一致，而是可以从具体 evidence、rule、path、range 开始工作。

---

## 2. CSU 是什么

CSU（Code Style Unifier）是一个面向多模块代码库的**语义级风格检查器**。它扫描 Python / Rust / C / C++ 源码，建立**统一 evidence layer**，再让规则只基于这层证据进行判断，而不是反复读取源码。每一条 finding 都记录它依据的 evidence、违反的 rule、所在文件与范围，并通过 blake3 为文件和 workspace 生成指纹，方便人或 agent 反向核对。

一句话概括：**56 条规则**（Core 28 / Python 8 / Rust 10 / C/C++ 10），覆盖 Python、Rust、C、C++ 四种语言；二进制名 `csu`；输出 JSON / JSONL 供 agent 调度；每条规则都支持人工标注交叉验证。

我选择 Rust 实现 CSU，不只是因为它有挑战性，而是因为它的语言特性适合这类工具：单二进制分发方便，启动和扫描性能稳定；类型系统、枚举和 `Result` 能把 evidence、issue kind、规则边界表达得更明确；内存安全和所有权模型也适合写一个需要长期演进、反复扫大项目的基础工具。CSU 要处理的是“信任边界”，实现语言本身也应该尽量减少隐式状态和运行时不确定性。

目前只支持 Python、Rust、C、C++，原因也很朴素：这些是我自己常用、也相对理解其工程习惯的语言。语义风格规则不是“按语法树找几个节点”那么简单，它要求对语言生态、命名传统、文档习惯、FFI/ABI/类型边界有足够直觉。对我不了解的语言，我很难形成可信的个人风格判断；与其做一个看起来覆盖广、实际不懂边界的规则集，不如先把熟悉语言里的规则做扎实。

**v1.1.1 文档更新**：README 重新组织了 CSU 的设计动机、个人背景与边界说明。功能层面的 v1.1 更新包括：Core009 只在同一语义导入块内检查排序，避免把顶层导入、延迟导入、`TYPE_CHECKING` 和条件导入混排；Core014 对 Python Qt/PySide override 采用三态判定——确定框架 override 不报，Qt 类中的未知 camelCase 进入 `under_review`，非 Qt 上下文仍保持 `hard_violation`。这次更新不以减少发现数量为目标，而是收紧 hard 的契约纯度。

---

## 3. 快速开始

源码仓库内可以直接运行：

```
cargo run --release -- check src --format json --output .csu/csu.json --no-history
```

发布包解压后直接调用 `bin/csu`（Windows 为 `bin\csu.exe`）。平台二进制路径与打包方式见 [§7.1 安装](#71-安装)，详细使用见 [§7 使用方法](#7-使用方法)。

---

## 4. 工程设计

CSU 的可靠来自架构本身，而不是口号。

### 4.1 处理管线

```
源码文件（.py / .rs / .c / .h / .cc / .cpp / .hpp / ...）
   │  scanner   按扩展名过滤 · 排除目录 · blake3 指纹 · C/C++ 生成标记判定
   ▼
WorkspaceState（文件单元）
   │  frontend  tree-sitter 解析 → 提取证据
   ▼
EvidenceStore（统一证据层，13 类事实）
   │  evaluators  Core / Python / Rust / C/C++ 规则，只读证据
   ▼
issues（结构化问题）
   │  profile（启用集 / 阈值 / 术语策略）· calibration（人工标注交叉验证）
   ▼
JSON / JSONL（agent 可读输出）
```

### 4.2 统一证据层（EvidenceStore）

核心设计是**统一证据层**：scanner 与 frontend 把源码解析为一次性的 `EvidenceStore`，包含 13 类事实。代码内部以 `XxxFact` 结构承载这些 evidence，本文档叙事统一称为"证据"。

| 事实类型 | 含义 | 典型消费规则 |
|----------|------|--------------|
| `workspace` | 整个工作区的元信息（语言边界、指纹）| Core001 语言边界 · Core005 history 健康 |
| `file_unit` | 单个文件的单元信息 | Core006 文件命名 · Core007 文件角色 |
| `module_unit` | 模块/文件级结构（import、prelude）| Core008 依赖分组 · Rust003 pub prelude |
| `dependency_edge` | 依赖边（import / include / use，含导入块与条件/延迟上下文）| Core003 依赖环 · Core010 宽导入 |
| `doc_region` | 文档区域（docstring / doc comment）| Core011 公开面文档 · Core012 字段覆盖 |
| `comment_region` | 注释区域 | Core017 块意图注释 |
| `text_span` | 文本片段（摘要、术语）| Core023 中文句号 · Core026 术语策略 |
| `line_span` | 行片段（行长、suppression）| Core018 suppression · Core019 行长 |
| `public_surface` | 公开 API 面 | Core011 公开面文档 |
| `block_region` | 代码块（unsafe、async、模板）| Rust007 unsafe · Cpp008 预处理分支 |
| `symbol` | 符号（函数、类型、变量）| Core014 命名 · Core015 缩写策略 |
| `expression` | 表达式（错误消息、宏调用）| Core028 错误消息 · Py008 lazy logging |
| `history_health` | 扫描历史健康度 | Core005 history 健康 |

关键约束是：**所有规则只读证据层，不反复读源码**。这带来两个直接好处：

- **判定确定性**：规则的判定只依赖证据层，给定相同输入结果可复现；
- **职责分离**：事实提取（frontend）与规则判定（evaluators）解耦，新增规则无需触碰解析逻辑。

**事实提取的确定性**：frontend 基于 tree-sitter 做语法解析，并对文本做确定性归一化（大小写、空白、术语切分）。在相同源码、profile 与 history 开关下，多次扫描产出的证据层一致——规则判定因此可复现、可回归。这也是校准能成立的前提：证据本身不确定，人工标注就失去了长期意义。

### 4.3 扫描加速设计

- **纯 Rust 实现**：单二进制分发，启动成本低；类型系统、枚举和 `Result` 让 evidence、issue kind、规则边界更容易保持显式，适合大项目递归扫描；
- **按扩展名过滤**：只处理 Python / Rust / C / C++ 源文件，其余跳过。当前语言覆盖来自作者实际维护经验；不了解语言生态时不强行写语义风格规则；
- **排除目录**：通过 profile 配置，默认排除 `.git` / `.venv` / `build` / `dist` / `target` / `vendor`；
- **C/C++ 生成文件判定**：对 C/C++ 文件仅读取前 **8192 字节** 判断是否为生成代码（匹配 `do not edit`、`automatically generated`、`.pb.cc`/`.pb.h`、`amalgamation` 等标记），避免对整文件做无意义检测；
- **blake3 指纹**：为每个文件生成 `blake3:{hex}` 指纹，并聚合为 workspace 指纹，保证扫描记录可追溯。

**设计权衡**：为什么 C/C++ 生成文件只读前 8192 字节？因为生成代码（protobuf、amalgamation、bootstrap）动辄数十万行，逐行检测既慢又无意义——它们的"风格"由生成器决定，不由人控制。8192 字节足以覆盖生成标记头部，超出部分直接跳过——只检查值得检查的代码。

### 4.4 profile 与 calibration

**profile**（`profiles/default.toml`）控制一次扫描的边界：

- `enabled_rules`：启用的规则集；
- `exclude_dirs` / `exclude_file_patterns`：排除目录与文件模式；
- 阈值：`line_length_limit`、`doc_summary_max_chars`、history 保留参数；
- 术语策略：`allowed_*` 白名单 + `banned_abbreviation_tokens` 禁用缩写映射。

可通过 `--profile` 按名称加载自定义配置，也可通过 `--profile-path` 直接加载 TOML 文件。

**calibration** 让每条规则的判定都可被人工标注验证。一个校准样本（`cases.jsonl`，每行一条）描述"某个 issue 的人工判断"：

```json
{
  "case_id": "core016-fn-is-ready-2026",
  "rule": "Core016",
  "issue_id": "issue:Core016:ev_file_<hash>_symbol_function_391_1_<hash>",
  "label": "false_positive",
  "observed_kind": "under_review",
  "expected_kind": null,
  "path": "core/calibration.rs",
  "range": "391:1-391:1",
  "evidence": ["ev:file:<hash>:symbol:function:391:1:<hash>"],
  "rationale": "该符号属于事实提取层，命名沿用既有契约，级别边界无需调整",
  "action": "keep_rule"
}
```

标注类型：`TruePositive` / `FalsePositive` / `FalseNegative` / `WrongKind` / `UnderReviewExpected` / `ExternalStyleMismatch`；后续动作：`KeepRule` / `FixFactExtraction` / `NarrowRuleContract` / `BroadenRuleContract` / `ChangeIssueKind` / `AddProfilePolicy` / `AddRegressionFixture`。

`csu calibrate` 会读取 `check` 输出的 issues 与人工 cases，**交叉验证**每条 case 引用的 issue 是否真实存在、`rule`/`kind`/`path`/`range`/`evidence` 是否一致，并生成校准报告。

CSU 的校准有一条硬约束：**禁止以"减少问题数量"为优化目标**。校准样本的 `rationale` 若出现"数量太多""减少 findings""too noisy"等数量导向表述，会被直接拒绝；必须基于**事实、规则、级别或边界**给出可追踪的判断。这条约束确保 CSU 不会被"调到不报"。

**校准 → 回归测试闭环**：校准不止于标注。当一条 case 判定规则需要收窄或扩展契约（`NarrowRuleContract` / `BroadenRuleContract`），或需要防回退（`AddRegressionFixture`）时，校准结论会被固化为回归夹具——把该 case 的输入样本沉淀进测试套件，确保规则后续不会重新引入已被认定的问题。这样一来，规则的演进**只会收敛、不会回退**：每一条人工判断都留下永久证据，规则不会无声地“忘记”曾经被纠正过的边界。

### 4.5 机器可读输出

CSU 当前默认面向**机器可读输出**：`check` 命令支持 `json`（JSON 数组）与 `jsonl`（JSON Lines，每行一个 issue）两种格式，**没有额外的人类友好 report 格式**。这是有意为之——CSU 的设计假设输出由 agent（Codex / Claude Code）或脚本消费，人类友好的呈现交给上层工具。

---

## 5. 规则体系

### 5.1 四规则族概览

| 规则族 | 条数 | 覆盖范围 | 代表规则 |
|--------|------|----------|----------|
| **Core** | 28 | 跨语言通用（命名、文档契约、依赖、术语、suppression）| Core014 命名 · Core018 suppression · Core026 术语 |
| **Python** | 8 | Python 特定（docstring、future、typing、logging）| Py005 注解完整性 · Py008 lazy formatting |
| **Rust** | 10 | Rust 特定（FFI、unsafe、async、cfg、panic）| Rust005 FFI 边界 · Rust007 unsafe 契约 |
| **C/C++** | 10 | C/C++ 特定（ABI、宏、include、模板、所有权）| Cpp005 ABI 边界 · Cpp006 宏契约 |
| **合计** | **56** | | |

> C/C++ 规则族的目录名为 `cpp`，但规则覆盖 **C 与 C++** 两种语言（少数规则仅 C++，如 Cpp004、Cpp007）。每条规则的契约是一个独立 `.toml` 文件（见 [§9](#9-项目结构)），并汇总于 `rules/catalog.toml`。

### 5.2 规则领域

56 条规则覆盖 11 个领域：

| 领域 | 关心的问题 | 代表规则 |
|------|-----------|----------|
| `project` | 项目级边界与角色 | Core001 语言边界 · Core007 文件角色 |
| `dependency` | 依赖图与导入 | Core003 依赖环 · Core009 导入排序 |
| `history` | 扫描历史健康 | Core005 history 健康 |
| `style` | 文本与文件风格 | Core006 文件命名 · Core026 术语策略 |
| `documentation` | 文档契约 | Core011 公开面文档 · Core021 字段对齐 |
| `naming` | 命名约定 | Core014 大小写 · Core016 布尔谓词 |
| `maintainability` | 可维护性 | Core017 块意图 · Rust002 cfg 复杂度 |
| `public_api` | 公开 API 面 | Rust003 pub prelude · Cpp001 头文件边界 |
| `typing` | 类型标注（Python）| Py004 collections.abc · Py007 旧式泛型 |
| `logging` | 日志约定（Python）| Py006 handle 命名 · Py008 lazy formatting |
| `safety_adjacent` | 安全相关边界 | Rust005 FFI · Rust007 unsafe · Cpp005 ABI |

### 5.3 三种 issue kind

每个 issue 有一个 `kind`，决定它如何被处理：

- **`hard_violation`**：硬违规，契约明确被破坏（如普通符号的 Core014 命名大小写、Core018 suppression 缺原因）；
- **`under_review`**：需复核，判定有依据但需 agent 或人确认（如 Core016 布尔谓词命名、Qt 类中未知 camelCase 方法、Core027 内部文本疑似英文）；
- **`soft_friction`**：轻摩擦，建议关注但不强制（如 Core001 语言边界、Rust002 cfg 复杂度）。

### 5.4 规则示例

按 `kind` 举例，展示三种严重级别各自长什么样：

- **Core014 `naming.case_convention`**（通常为 `hard_violation`）：普通符号名必须遵循大小写约定。Python Qt/PySide 框架 override 是例外：确定 override 不报，Qt 类里的未知 camelCase 方法进入 `under_review`，避免把框架回调误当成可机械修复的 hard。
- **Core018 `suppression.reason_required`**（`hard_violation`）：抑制标记必须带原因。裸 `// csu:allow` 会触发；必须写 `// csu:allow reason = "..."`。
- **Core016 `naming.boolean_predicate`**（`under_review`）：布尔谓词命名需要审查——规则能识别"疑似布尔但命名不规范"的符号，但是否真要改交给 agent 或人判断。
- **Core026 `text.term_policy`**（`hard_violation`）：文本必须遵循确定性术语策略。`cfg` / `ABI` / `SSIM` 等专业术语在术语白名单内不报，否则按禁用缩写映射处理。
- **Rust002 `cfg_complexity_policy`**（`soft_friction`）：Rust `cfg` 条件组合复杂时提示摩擦，不强制改动。

---

## 6. Agent 调度

> 本节聚焦 **agent 如何基于 CSU 输出做调度**；原始命令与输出片段见 [§7.3](#73-check-实战)。

CSU 的 issue 结构就是为 agent 调度设计的。一个 issue 的完整字段（来自真实 `csu check src` 输出，hash 已脱敏）：

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

每个字段都对应一个调度判断：

| 字段 | agent 如何用 |
|------|--------------|
| `kind` | 决定动作优先级：`hard_violation` 必修 / `under_review` 需判断 / `soft_friction` 提示 |
| `rule` + `name` | 定位契约，决定修复策略 |
| `path` + `range` | 精确跳转到代码位置 |
| `evidence` | 追溯到证据层，验证问题真实性，避免盲改 |
| `blocks` | 是否阻断（影响退出码）|
| `message` | 给 agent 的中文人话描述 |

### issue kind 到 agent 动作的映射

| `kind` | `blocks` | 建议 agent 动作 |
|--------|----------|-----------------|
| `hard_violation` | 多数 `true` | 立即修复，契约明确 |
| `under_review` | `false` | 结合上下文判断，多数情况需人或 agent 推理确认 |
| `soft_friction` | `false` | 记录或忽略，不阻塞 |

### 典型工作流

```
cargo run --release -- check src --format json --output .csu/csu.json --no-history
# agent 读取 .csu/csu.json
# 按 kind 分流：hard_violation → 立即修；under_review → 结合上下文判断；soft_friction → 记录
# 用 evidence 字段回溯验证，再动手
```

**跨 agent 通用**：CSU 的输出是 agent 无关的结构化 JSON，Codex、Claude Code 等都按同一份契约消费。不同 agent 的区别只在于怎么把 issue 落成具体编辑，CSU 不掺和这一层。退出码也参与调度：有 `blocks: true` 的 issue 时退出码为 1，否则为 0，agent 据此决定是否阻塞。

**一次完整的协作过程**：agent 先跑 `check` 拿到 JSON，按 `kind` 分流——`hard_violation` 直接按 `path` + `range` 修复；`under_review` 用 `evidence` 回溯到证据层，结合上下文判断是不是真问题；改完重跑 `check`，看那条 issue 是否消失、退出码是否归 0。从头到尾，CSU 只负责“指出问题在哪、依据是什么”，不替 agent 决定怎么改。

---

## 7. 使用方法

### 7.1 安装

```
cargo build --release
```

产物路径：

- Windows：`target\release\csu.exe`
- Linux / macOS：`target/release/csu`

为方便，可加入 `PATH`，或直接用 `cargo run --release --` 调用（见 [§3](#3-快速开始)）。

发布包结构保持解压即用：

```
csu-1.1.1-<platform>/
  bin/csu(.exe)
  profiles/default.toml
  agent-skills/csu/SKILL.md
  examples/commands.md
  README.md
  LICENSE
```

本地打包当前平台：

```
pwsh ./scripts/package-release.ps1
```

### 7.2 子命令速查

| 命令 | 用途 |
|------|------|
| `csu check <path>` | 扫描文件/目录，输出 issue（支持 `--profile` / `--profile-path` / `--history-dir` / `--format` / `--output` / `--no-history`）|
| `csu calibrate --issues <issues.json> --cases <cases.jsonl>` | 根据人工样本与 check 输出生成校准报告 |
| `csu rules` | 输出规则目录契约（`--format json` / `toml`）|
| `csu history --history-dir <dir> <list\|prune\|clear>` | 管理扫描历史（list 列出 / prune 清理过期 / clear 清空）|

### 7.3 check 实战

扫描 `src`（JSONL 格式，每行一个 issue）：

```
csu check src --format jsonl --no-history
```

输出（真实输出，hash 已脱敏）：

```json
{"id":"issue:Core016:ev_file_<hash>_symbol_function_391_1_<hash>","kind":"under_review","rule":"Core016","name":"naming.boolean_predicate","scope":"symbol","domain":"naming","language":"rust","path":"core/calibration.rs","range":"391:1-391:1","message":"布尔谓词命名需要审查","evidence":["ev:file:<hash>:symbol:function:391:1:<hash>"],"blocks":false}
```

扫描整个项目并写文件：

```
csu check src          --format json --output .csu/csu.json        --no-history
csu check tests        --format json --output .csu/csu_tests.json  --no-history
csu check agent-skills --format json --output .csu/csu_skills.json --no-history
```

### 7.4 profile 配置

默认 profile（`profiles/default.toml`）节选：

```toml
exclude_dirs = [".git", ".venv", "build", "dist", "target", "vendor"]
# enabled_rules, thresholds, term policy ...
```

自定义一个项目级 profile 时，典型调整包括：

- **收窄规则集**：`enabled_rules` 只保留本项目关心的规则；
- **调整阈值**：放宽或收紧 `line_length_limit`、`doc_summary_max_chars`；
- **术语白名单**：把项目专有术语（如 `ABI`、`SSIM`）加入 `allowed_technical_fragments`，避免被缩写策略误报；
- **排除第三方产物**：补充 `exclude_dirs`（如 `node_modules`、`third_party`）。

加载：`csu check src --profile my_profile`（按名称，对应 `profiles/my_profile.toml`），或 `csu check src --profile-path profiles/default.toml`（直接指定文件）。

### 7.5 扫描历史

扫描历史用于 workspace 健康追踪，默认写入 `.csu/history`。`--no-history` 跳过写入；`csu history --history-dir .csu/history list` 查看、`prune` 清理过期记录、`clear` 清空。

### 7.6 校准实战

用 `calibrate` 交叉验证规则判断：

```
csu check src --format json --output .csu/csu.json --no-history
csu calibrate --issues .csu/csu.json --cases calibration/cases.jsonl --output .csu/calibration.json
```

`cases.jsonl` 每行一条人工标注（格式见 [§4.4](#44-profile-与-calibration)）。`calibrate` 会：

1. 逐条校验样本的 `rationale` 不含数量导向表述、且包含可追踪术语；
2. 交叉验证每条 case 引用的 issue 真实存在、字段一致；
3. 汇总各规则的 TP/FP/FN 分布与建议动作，输出校准报告。

报告用于决定下一步：保持规则、收窄/扩展契约、调整 profile，或沉淀回归夹具。

---

## 8. 设计取舍与边界

CSU 的价值建立在**明确的边界**和**可校准机制**上。

- **不是 formatter**：CSU 不处理空格、换行、缩进、括号；导入排序只检查同一语义导入块内的契约，不跨延迟导入、`TYPE_CHECKING` 或条件边界替 formatter 重排。CSU 检查的是 formatter 之上的语义层。
- **当前不把并行扫描 / 增量缓存作为核心能力**：架构（统一证据层 + 单次扫描）天然适合后续扩展到缓存与并行，但目前未落地为已实现能力，不当作既成事实陈述。
- **`check` 输出仅 JSON / JSONL**：没有人类友好 report 格式。CSU 假设输出由 agent 或脚本消费。
- **阈值与术语依赖 profile 配置**：CSU 不内置"默认裁决"，行长限制、术语白名单等都由 profile 决定，项目可定制。
- **判定与阻塞分离**：56 条规则中既有明确阻断项（`hard_violation`），也有复核项（`under_review`）与轻摩擦项（`soft_friction`）；`under_review` 与 `soft_friction` 默认不阻塞，流程是否失败由 `blocks` 决定。CSU 提供结构化判断，不把所有发现都等同于失败。

---

## 9. 项目结构

```
src/
  main.rs              # 入口、check/calibrate 输出、退出码
  core/
    mod.rs             # 模块组织
    scanner.rs         # 扫描 · 扩展名过滤 · 排除 · blake3 · 8192 生成标记
    frontend.rs        # tree-sitter 解析 → 证据提取
    evidence.rs        # EvidenceStore 统一证据层（13 类事实）
    evaluators/
      mod.rs           # evaluate_all 入口
      core.rs          # Core 规则（28）
      python.rs        # Python 规则（8）
      rust.rs          # Rust 规则（10）
      cpp.rs           # C/C++ 规则（10）
    issue.rs           # Issue / IssueKind / Scope / Domain / Language
    profile.rs         # profile · 阈值 · 术语策略
    python_qt.rs       # Python Qt/PySide override 上下文与名单
    calibration.rs     # 校准样本 · 交叉验证 · 数量约束
    history.rs         # 扫描历史读写与保留
    rules.rs           # 规则目录 TOML 解析
    cli.rs             # clap 子命令定义
    syntax.rs          # tree-sitter 语法入口
    error.rs           # 统一错误类型
rules/
  catalog.toml         # 56 条规则契约汇总
  core/                # Core001–Core028，每条一个 .toml
  python/              # Py001–Py008
  rust/                # Rust001–Rust010
  cpp/                 # Cpp001–Cpp010
profiles/
  default.toml         # 默认 profile
agent-skills/
  csu/SKILL.md         # CSU 的 agent skill 定义
scripts/
  package-release.ps1  # 本地与 CI 共用的发布包脚本
examples/
  commands.md          # 发布包命令示例
```

---

## 10. 参考资料

- **[1]** 中国人民大学等团队. *A Survey of Large Language Models*. https://arxiv.org/abs/2303.18223 —— LLM 的定义、发展与影响。
- **[2]** 中山大学软件工程学院. *LLM 与软件工程任务综述*. https://sse.sysu.edu.cn/article/658 —— 代码生成、代码摘要、漏洞检测、代码管理等任务。
- **[3]** *Science China Information Sciences*, LLM4SE 综述. https://link.springer.com/article/10.1007/s11432-025-4670-0 —— 软件工程中 LLM 的任务谱系、模型、挑战与机会。
- **[4]** *A Survey on Large Language Models for Code Generation*. https://arxiv.org/abs/2406.00515 —— 代码生成已成为学术与工业共同关注的方向。
- **[5]** *Stack Overflow 2025 Developer Survey*. https://survey.stackoverflow.co/2025/ai —— 84% 受访者正在使用或计划使用 AI 开发工具。

---

## 11. 许可证与贡献

**许可证**：MIT（见 `LICENSE`）。

**贡献**：欢迎通过 calibration 样本、profile、规则契约扩展 CSU。新增规则需在 `rules/<族>/` 下登记契约 `.toml` 并汇总到 `rules/catalog.toml`，建议配校准样本。
