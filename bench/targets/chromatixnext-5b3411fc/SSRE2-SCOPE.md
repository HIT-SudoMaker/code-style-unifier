# ChromatixNext 扩展准备度 SSRE2 审计范围

> **Historical / superseded (2026-08-23):** 本文件记录对封存基线的早期
> 扩展准备度调研，不再是 Scalar Multislice 的实施范围或决策权威。厚样品模型、
> Interface、证据与票据已由 [SSRE2-DESIGN.md](SSRE2-DESIGN.md) 和
> `.scratch/scalar-multislice-foundation/spec.md` 收敛；后续代理不得从本文件的
> `UNKNOWN` 项恢复旧 coordinator 或重新打开已经作出的产品选择。

## 1. Source snapshot identity

- 审计目标：`E:\Year2026_Project_ChromatixNext\code-ssre2-claude`
- Git commit：`a8dc9855c372b173380981eec477f04a65b78f47`
- Git tree：`7b65fa0a3943b8580341294cb009d1f102853c4c`
- 分支：`ssre2-admission-closure`
- 候选状态：`OBSERVED`，`git status --porcelain=v1` 为空
- 审计问题：该冻结科学基础是否为“DOE/D2NN 闭环、厚样品、可复用优化与多卡”提供了可诚实扩展的架构；本次不重新证明全部三十个 action 的全部数值正确性
- Target-code effect：`READ_ONLY`

当前工作树 `E:\Year2026_Project_ChromatixNext\code` 位于 preimage
`35573738405ecfc340bca65f4fa361c2c9934033`。本审计文档写在该规划工作树中；候选
worktree 保持只读。

## 2. Execution environment

- Python：`3.12.13`，解释器
  `C:\Users\Administrator\miniforge3\envs\research_env\python.exe`
- PyTorch：`2.12.0+cu130`
- 平台：Windows 11 `10.0.26200`
- CUDA：runtime `13.0`，available，设备数 `1`
- 规模事实：109 个 production Python 文件、158 个 test Python 文件、7 个 Example 目录
- 限制：本机不能提供 2+ GPU 或 native Linux/NCCL 证据

## 3. Source authority order

1. `OBSERVED`：冻结候选中的 production source、tests、可执行 probe 及 Git 对象
2. `DECLARED`：候选 `CONTEXT.md`、`MISSION.md`、`docs/architecture.md`、
   `docs/adr/0001-0017`
3. `DECLARED`：`.scratch/ssre2-admission-closure/spec.md` 与对应 ticket proposal；
   它们表达 closure 意图，不自动证明实现
4. `DECLARED` 且可定位：候选 worktree 的
   `.scratch/ssre2-admission-closure/reports/seal-record-r2.md`、r2 manifest、gate matrix
   与双终审。它们位于 gitignored `.scratch`，不是 candidate tree 的 managed content
5. `OBSERVED`：`reference/chromatix` 的固定本地上游源码；仅作为比较与独立模型来源，
   不作为 ChromatixNext Interface 规范
6. `PROPOSED`：`docs/research/chromatixnext-expansion-architecture.md`；该文件当前未跟踪，
   是研究输入而非已接受设计

## 4. Model scope

### 4.1 当前已声明支持

- Fixed Double 的 sampled Wave 与 polarized geometric Ray 两种独立 model account
- 强 Physical Values：`OpticalField`、`Intensity`、`RayBundle` 及其 Grid、Spectrum、
  Medium、Polarization、Optical Path 事实
- Source / Element / Propagation / Combination / Detection 五个 Optical Role
- 类型化、冻结、acyclic multi-root `Assembly`
- `construct -> freeze -> host -> run -> Named Outputs + Run Record`
- Windows CPU 与显式单 CUDA device；一次 `run` 只使用一个 device
- 普通 PyTorch autograd 与由用户拥有的 optimizer

### 4.2 当前明确排除

- volume/multislice/multiple scattering、fluorescence、Modified Born
- material-thickness / dispersive DOE / fabrication-aware device model
- project-owned optimization framework、graph-owned loss、default optimizer
- distributed Workstation、multi-device single run、distributed FFT、multi-node runtime
- Wave↔Ray conversion 或统一 Optical State

### 4.3 本轮扩展方向仍未获授权

- DOE/D2NN：连续理想薄层可表达性与 Example 闭环
- 厚样品：具体 scientific model、role、state、failure 与 evidence contract
- 优化：Example-owned workflow、可复用 support 或 installed public framework 三者的选择
- 多卡：独立实验、data parallel、state sharding、spatial/distributed FFT 四种不同问题

## 5. Scientific claim ledger

| ID | Claim | State | Source / closing path |
| --- | --- | --- | --- |
| C1 | 当前 `OpticalPathModulation` 与 `AmplitudeTransmissionMap` 可组合成连续、理想、薄、polarization-neutral 的复透射面 | `OBSERVED` | `src/chromatix_next/optics/element/{optical_path_modulation,amplitude_transmission}.py`；参数 identity 与 Fixed Double tests |
| C2 | 多个薄透射面、自由空间 Propagation 与 Detection 可在当前 `Assembly` 中形成 DOE/D2NN 层栈 | `INFERRED` | role ports、acyclic topology 与现有 action Interface 支持该组合；尚无端到端 DOE/D2NN Example，需最小 Example probe 关闭 |
| C3 | C1/C2 不等于制造级 DOE：material dispersion、height mapping、quantization、minimum feature、misalignment 与 fabrication uncertainty 尚无 semantic owner | `OBSERVED` | production 与 domain search 无对应概念；上游 Chromatix `PhaseMask`/SLM 仅作比较 |
| C4 | 候选不实现厚样品；其 active scope 明确排除 volume/multislice | `OBSERVED`，同时为 `DECLARED` exclusion | `MISSION.md`、ADR-0008/0009/0010、package-contract tests 与 production symbol search |
| C5 | 上游 `multislice_thick_sample` 证明一种可微 scalar slice recurrence，但其宽参数 Interface、可选 kernel、NA/reverse/return-stack flags 不能直接证明适合 Next | `OBSERVED` + `INFERRED` | `reference/chromatix/src/chromatix/functional/samples.py`；Next 仍需自己的 applicability 与 deep-module contract |
| C6 | 当前 optimization 是可行但 Example-owned；Workstation 保留 Parameter identity，项目不拥有 optimizer/loss/history | `OBSERVED` | `CONTEXT.md`、ADR-0004、`tests/workstation/test_host_ownership.py` |
| C7 | 当前 7 个 Examples 中没有 optimization workflow，因此还没有两个真实 caller 证明 shared optimization seam | `OBSERVED` | `examples/**/*.py` 无 `torch.optim` / optimizer / loss loop |
| C8 | 当前 Workstation 是一设备 deep module；本机无能力证明 multi-GPU numerical equivalence、failure semantics 或 scaling | `OBSERVED` | `workstation.py`、`release.toml`、环境 probe |
| C9 | Wave/Ray 共存来自分离的 Physical Values、typed connections 与禁止转换；polarization 丰富两条轨道，但不使它们计算并发 | `DECLARED` 且有结构性 `OBSERVED` 支持 | ADR-0007、Assembly role/value contract、Workstation single-device run |
| C10 | 新能力若继续受“exactly thirty actions / no new public framework”字面门约束，会触发多处 active truth 与 package-contract 修改 | `OBSERVED` | `CONTEXT.md`、`MISSION.md`、`docs/architecture.md`、ADR-0005/0009-0014、`tests/package_contract/test_public_surface.py` 等重复 claim loci |
| C11 | scalar isotropic unidirectional multislice 是否足以回答导师的“厚样品”目标 | `UNKNOWN`（blocking） | Owner 需冻结样品的 NA、index contrast、anisotropy、backscatter 与 observable；最便宜路径是回答 Grill 的 model-scope 问题 |
| C12 | “优化系统做成框架”究竟指 reusable Example support、installed public Interface，还是 distributed execution owner | `UNKNOWN`（blocking） | Owner 选择会改变 module 与 seam；通过 Grill 决定 |

## 6. First-class concepts and relations

- `OpticalField` 与 `RayBundle` 是不同 Physical Values，不互转
- Optical actions 各自属于一个 Role；`Assembly` 只拥有 topology，不拥有 optical law
- `Workstation` 拥有 device、hosting、meta/real replay、memory 与 run randomness，不拥有 optimizer
- `OpticalPathProfile` 是 OPD，不是 geometric material thickness
- `PropagationMedium` 是 Field 的 homogeneous wavelength-resolved response，不是 3D material volume
- `Example` 是当前唯一 optimization workflow owner
- 上游 thick-sample recurrence 的逻辑为 slice propagation + thin interaction；它在 Next 中应由一个 deep module 隐藏还是暴露为 authored nodes，尚未决定

## 7. Scope invariants

1. 物理模型误差与 numerical representation error 分开
2. 不适用域在拥有该事实的 Interface 处稳定拒绝，不 fallback、不 clamp、不 silent repair
3. 所有 public real/complex physical quantities 保持 `float64`/`complex128`
4. Parameter identity、autograd graph 与 state installation/hosting lifecycle 不被隐藏复制破坏
5. `workstation.py -> optics -> _numerics` 单向依赖保持；新能力若需要改变它，必须显式重开
6. Wave 与 Ray 的 faithful asymmetry 保持，不因统一优化或多卡而发明统一 Optical State
7. scientific evidence 必须能挑战 production implementation；同路径重放与 CPU/CUDA agreement 不能单独自证正确
8. 新 seam 必须有真实 variation/caller，并通过 deletion test；一个 adapter 不为 hypothetical seam 辩护

## 8. Current execution spine

```text
author Physical Values and Components
    -> include/connect/expose Assembly (when topology is branched or multi-output)
    -> freeze
    -> Workstation.host one complete module root
    -> Workstation.run: isolated meta replay -> memory check -> one-device real replay
    -> Named Outputs + Run Record
    -> user-owned loss/autograd/optimizer outside Workstation
```

## 9. Real variation axes

- Wave representation：scalar / transverse / full vector
- Optical track：sampled Wave / geometric Ray（closed, non-converting）
- Propagation equation：scalar/vector angular spectrum、Fresnel families、aplanatic focus、Ray trace
- Spatial geometry：source/destination Grid、periodic/isolated exterior、Surface adapters
- Spectrum / Medium / polarization state
- New sample axis：thin ideal transmission / scalar volume / vector-anisotropic volume（后两者未支持）
- New DOE axis：continuous OPD/amplitude / material height-dispersion / quantized/fabrication-aware（后两者未支持）
- Optimization lifecycle：Example-local / shared support / installed framework（后两者未决定）
- Execution topology：single device / independent multi-process experiments / data parallel / sharded FFT（后三者未支持）

## 10. Carry-forward debt and seal-evidence persistence

以下八项逐项继承自可定位的 r2 seal record；本轮只在与扩展路线同 locus 时复核，不把旧 seal
的 `DECLARED` 裁定自动升级为本轮 `OBSERVED`：

1. `D1`：curvature → incident-finiteness split reorder 未 pin；触发器是任何 paraxial
   admission/evidence 变更时加入 `(inf, nan, 0.0) -> curvature_invalid`
2. `D2`：meta guard 硬编码五个 consumer、三个 traversing owner 尚未迁移、BASE phase-call
   scanner 只识别 bare `ast.Name`；触发器是第六个 consumer、nested role subpackage 或
   alias/attribute phase call
3. `D3`：T07 named-target staleness、docstring count 与 legacy wording；触发器是相关 production
   rename 或 enumeration 变化
4. `D4`：main-worktree superseded follow-up 无 back-pointer；触发器是下次合法打开 main tracker
5. `D5`：incident index `-0.0` 未显式 pin；触发器是 admission seam 或 comparison 变化
6. `D6`：import-facts 看不见 bare `import chromatix_next` 后的 runtime attribute traversal；
   触发器是下一次 evidence-independence deepening
7. `D7`：SAS 两个 sensitivity counterfactual 在 float64 下都恰为 `2.0`；触发器是下次触碰
   witness 时加入 non-quarter-cycle offset
8. `D8`：四项 pre-accepted Evolvable debt：Ray derived-state reconstruction、Source projection
   facts、Workstation public overload typing、Scalable Angular Spectrum numerical plan interface；
   触发器是对应 production seam refactor

`OBSERVED`：原始 seal、manifest、gate artifacts 与双终审仍在候选 `.scratch` 中，但 `.scratch`
被 gitignore，且不属于 tree `7b65fa0a`。这不否定 r2 的本地裁定，却意味着“归档后可恢复”需要
一个独立持久化决定；最便宜 closing path 是在任何工作区清理前，建立带 hash 的只读 evidence
bundle 或在新 reopen 中把最小 seal provenance 纳入受管归档。

## 11. Unknowns and cheapest closing paths

| ID | Unknown | Blocks core architecture? | Cheapest closing path |
| --- | --- | --- | --- |
| U1 | 正式 `code-review` 的 fixed point 是 `3557373`（全部 10 commits）还是 `a716530`（最后 3 repairs） | 是，仅阻塞 diff review | Owner 在第一轮 Grill 选择；推荐 `3557373...a8dc985` |
| U2 | Wayfinder 的 destination 是最小科学 vertical slice，还是直接交付通用 distributed optimization product | 是 | Owner 选择；推荐前者，后者拆为条件触发的后续 map |
| U3 | 厚样品第一支持域的物理参数与 observable | 是 | 冻结一个代表性实验和适用域；最小候选为 scalar isotropic unidirectional multislice |
| U4 | DOE 第一闭环是 continuous ideal phase-only，还是一开始就要求制造约束 | 是，局部阻塞 DOE module shape | 选择首个真实器件/数据/observable；推荐先 continuous ideal Example，再以第二 Example 证明 material support |
| U5 | optimization “framework”的 product boundary | 是 | 用两个真实 optimization Examples 比较重复 lifecycle，再决定是否抽取 deep support |
| U6 | multi-GPU 的首个 parallel axis 与 hardware platform | 是 | 明确 independent experiments / data parallel / state sharding / spatial FFT；获得 native Linux 2+ GPU probe |
| U7 | r2 `.scratch` seal evidence 的持久化 owner 与归档位置 | 否，不阻塞方向；阻塞清理后的可恢复性声明 | 在任何清理前建立 hash-verified evidence bundle；是否纳入新受管 provenance 由 Owner 决定 |

## 12. Frozen-input statement

五个 SSRE2 dimension audit 都必须读取本文件、SSRE2 Shared Doctrine、同一候选 worktree 与各自
dimension operators；不得读取其他 dimension 的产物、旧 review 或 synthesis。目标代码未修改。
