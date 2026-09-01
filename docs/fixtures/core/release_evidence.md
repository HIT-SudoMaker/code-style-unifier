# CSU 正式发布性能证据

记录时间：2026-09-01 Asia/Singapore

状态：`ABSOLUTE RELEASE GATE PASSED · GENERATION-0 FROZEN`

## 输入身份

- release executable SHA-256：
  `a5a873a0b4e0700956aeb3460d3f98cea2c39425270f9b9d6880870977979c0e`
- Performance Authority SHA-256：
  `c8f9c99a2d4083bc9fef2bb7df3a11951583a06eb62e644e0878b37265c173f3`
- frozen corpus：617 files、200,000 physical LOC、6,742,933 bytes
- corpus digest：
  `fdcfa14e65efc32bc25587efe9ee6a6aa5453ba2e3eeb8b4a2b4ead5f8441703`
- inventory SHA-256：
  `b4d11370ba223527523a1bff366164f23562377940c9c5dd6007a65ffe1afe54`
- measured workspace：`target/csu-release-corpus-200k`
- parseability exclusion ledger：371 entries，逐项绑定源文件 SHA-256

`verify-inputs.ps1` 重算八个 target 的 2,402 个 accepted files，验证排除账本、
固定配额、inventory、Performance Authority 和本证据文件身份。语料按完整文件构建，
没有截断、生成或改写源码。

## 终态与规模

- 30 次 measured fresh processes，另有 1 次未计时 warmup
- 30 次均为 exit 1、`Sealed + Complete + Findings`
- blocked families：0
- 每次 617 reads、617 byte sweeps、617 structural parses
- Findings：48,176；没有以减少 Finding 数量换取性能
- 每次 Projection：18,628,970 bytes
- 唯一 Projection SHA-256：
  `3c03b2befa7d06296e4004ce801f338060af018ceea0249fadcb2cd4bb1dfa81`

Performance Authority 将 Documentation 四语言投影明确设为 `NotApplicable`，因为
本证据只判断完整生命周期吞吐量，不拥有外部项目的 public callable 语义。Structure
与 Identifier 仍完整执行；该 Authority 不能产生代码合规或 Documentation Clean
声明。

## 测量结果

- p95 方法：nearest rank `ceil(0.95 × 30)`
- p95 elapsed：`1,756.1124 ms`
- 最小 elapsed：`1,260.0708 ms`
- 最大 elapsed：`1,900.3115 ms`
- maximum peak working set：`61,071,360 bytes`
- deterministic Projection：`true`
- `diagnostic_incomplete`：`false`

因此首版 `p95 < 10,000 ms` 绝对性能 Gate、完整性 Gate、一次读取/解析 Gate 和
30 次确定性 Gate 均通过。逐次原始测量见 `release_runs.json`。

## Generation-0 裁决

CSU 2.0 是当前 Rule Map、Completion 与 Projection 的首个可比基线。Owner 于
2026-09-01 接受以下发布合同：

1. 首版以绝对性能、完整生命周期、确定性和资源记录作为 release Gate
2. 本证据冻结为同语义 Generation-0 baseline
3. 从下一版本开始，在相同 Rule Map、Projection、corpus 和 runner 下，候选 p95
   不得超过本基线 1.5 倍，peak RSS 不得超过 2 倍
4. 规则、语料或 Projection 身份变化时先建立新的可比基线，不跨语义计算比例

这不是叙事性 waiver：无法比较的首版不伪造 ratio，后续版本则具有明确机器基线。

## 外部诊断仍保留

`diagnostic_runs.json` 记录 489-file 广域投影。它以完整外部
Documentation Authority 运行并诚实得到 `Sealed + Incomplete` 与 472 个 blockers，
用于说明未知 public owner 和 grammar rejection 不会被伪装成 Clean。

该诊断继续指导 Authority 与 parser 校准，但不再阻塞已经单独定义并完成的吞吐量
证据。语义合规由 20-cell fixture 和项目自检拥有，三条证据轨不得互相冒充。
