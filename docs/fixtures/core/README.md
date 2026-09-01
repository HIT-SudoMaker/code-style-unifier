# CSU 四语言验收与发布证据

**状态：`CURRENT · ABSOLUTE RELEASE GATE PASSED`**

本目录冻结当前 Authority、四语言精确 fixture、八靶场身份、200,000 physical LOC
正式性能语料和唯一测量口径。这里没有生产 Rust，也不复制或改写靶场源码。

## 三条证据轨

| 证据轨 | 回答的问题 | Authority 与终态 | 能否证明 |
|---|---|---|---|
| 语义靶场 | 四语言规则是否检出约定问题 | 完整 Identifier + Documentation；20 格精确 oracle | 规则正确性与反规避 |
| 正式性能 | 完整生命周期在 20 万行上是否足够快且确定 | Performance Authority；Documentation 明确 `NotApplicable`；必须 `Sealed + Complete` | 吞吐、内存、确定性与一次解析 |
| 外部诊断 | 真实项目还暴露哪些 Authority 或 grammar 缺口 | 完整外部 Authority；允许诚实 `Incomplete` | 校准问题，不能充当 release pass |

Performance Authority 的 `NotApplicable` 只限定本次证据问题，不修改
[`coding_standards.md`](../../coding_standards.md)，也不能证明外部源码符合文档规范。
正式性能运行仍执行 Structure 与 Identifier，保留全部 Findings。

## 冻结构件

| 构件 | 所有权 |
|---|---|
| `authority.json` | 语义靶场 Authority；Identifier 与 Documentation 均有四语言投影 |
| `performance-authority/authority.json` | 正式性能证据适配器；Documentation 四格均为 `NotApplicable` |
| `fixture-manifest.json`、`documents/` | 20 个源码 cell 的内容身份和精确终态 |
| `benchmark-manifest.json` | targets、语料、排除账本、runner、grammar、命令和 release evidence identity |
| `parseability-exclusions.json` | 仅从性能语料排除的固定 grammar 拒绝；逐文件绑定路径、语言、SHA-256 和原因 |
| `verify-inputs.ps1` | 重算全部身份、选择语料、核验正式绝对性能 Gate |
| `measure-release.ps1` | 1 次 warmup 与 30 次 fresh-process 测量 |
| `release_runs.json` | 当前正式性能原始测量 |
| `diagnostic_runs.json` | 广域 Incomplete 诊断；不参与 release pass |
| `self_check_evidence.md` | 产品和测试宿主双三零自检 |

## 四语言语义矩阵

| 场景 | Python | Rust | C | C++ | 精确预期 |
|---|---|---|---|---|---|
| `valid` | docstring | outer rustdoc | `/** */` | `/** */` | `Sealed + Complete + Clean` |
| `ordinary_comment` | `#` | `//` | `/* */` | `//` | carrier Hard Finding |
| `missing_field` | 缺 `Raises:` | 缺 `# Errors` | 缺 `错误：` | 缺 `错误：` | public-contract Hard Finding |
| `short_symbol` | `d` | `d` | `d` | `d` | 一个 Review Required Naming Finding |
| `syntax_damaged` | 受损语法 | 受损语法 | 受损语法 | 受损语法 | `Sealed + Incomplete`，Structure blocked |

普通注释故意紧邻 declaration，证明“位置接近”不能替代合法 Documentation Carrier。
Candidate Registry 覆盖拉丁单字母、24 个常用希腊转写、大小写字形和常见变体；
命中只产生 Review Required，不猜 Canonical Concept。

## 八靶场与正式 200k corpus

八个冻结 target 提供 2,402 个 accepted files、823,942 physical LOC 和
27,935,267 bytes。全量固定 grammar 筛查发现 371 个无法完整解析的文件：C 332、
C++ 39；Python 与 Rust 为 0。

这些文件保留在冻结 targets 和外部诊断中，只从吞吐量语料排除。排除不是代码质量
豁免：语义 fixture 继续证明语法损坏会产生 Structure blocker，账本内容变化也会使
verifier 失败。

剩余 2,031 个 parse-admissible files 按 ordinal `target/path` 执行确定性
first-reach subset-sum，选择完整文件而不截断或生成源码：

| 语言 | 文件 | physical LOC | bytes |
|---|---:|---:|---:|
| C | 282 | 50,000 | 1,598,822 |
| C++ | 34 | 2,831 | 83,170 |
| Python | 180 | 73,584 | 2,535,739 |
| Rust | 121 | 73,585 | 2,525,202 |
| 合计 | 617 | 200,000 | 6,742,933 |

C++ 配额使用全部 parse-admissible 外部 C++，而不是生成约 47,000 行重复源码制造
对称。corpus digest 为
`fdcfa14e65efc32bc25587efe9ee6a6aa5453ba2e3eeb8b4a2b4ead5f8441703`；
617-entry inventory SHA-256 为
`b4d11370ba223527523a1bff366164f23562377940c9c5dd6007a65ffe1afe54`。
`.h` 的 C/C++ 归属来自 inventory，不来自目录或语法猜测。

## 可复现命令

```powershell
pwsh -NoProfile -File docs/fixtures/core/verify-inputs.ps1

pwsh -NoProfile `
  -File docs/fixtures/core/verify-inputs.ps1 `
  -BuildCorpus `
  -OutputDirectory target/csu-release-corpus-200k

cargo build --locked --release
target/release/csu.exe review `
  --authority docs/fixtures/core/performance-authority `
  --workspace target/csu-release-corpus-200k `
  --format json

pwsh -NoProfile `
  -File docs/fixtures/core/measure-release.ps1 `
  -AuthorityDirectory docs/fixtures/core/performance-authority `
  -Workspace target/csu-release-corpus-200k
```

正式测量只接受 exit 0/1 的 `Sealed + Complete`。`-DiagnosticIncomplete` 仅用于
定位外部 Authority 缺口，永远不能形成 release pass。

## 当前正式结果

- 30 次均为 exit 1、`Sealed + Complete + Findings`；blocked families 为 0
- 每次读取 617 个文件、617 次 byte sweep、617 次 structural parse
- 48,176 个命名 Findings 被完整序列化，没有为性能缩小判断面
- nearest-rank p95：`1,756.1124 ms`
- maximum peak working set：`61,071,360 bytes`
- 30 次 Projection SHA-256 唯一
- 产品 Rust：7,114 physical LOC，低于 20,000 行门限

CSU 2.0 建立当前语义的 Generation-0 baseline。首版 release 使用
`p95 < 10,000 ms`、完整生命周期和确定性作为性能门；从下一版本开始，在相同
Rule Map、Projection、corpus 和 runner 下额外要求 p95 `<= 1.5×`、peak RSS
`<= 2×` 本基线。不同 Rule Map、Projection 或 corpus 不做伪造的比例比较。

## 证据边界

- targets 是校准输入，不是应当 Clean 的示范项目；Finding 数量不设优化目标
- 外部诊断中的 Documentation unknown 与 grammar rejection 继续保留，用于后续
  Authority 和 parser 能力校准，但不要求吞吐量证据回答代码合规问题
- materialized corpus 是可重建临时产物，不提交仓库，也不建立缓存协议
- fixture 或排除账本变化必须产生新身份并重新测量，不能沿用当前 release evidence
