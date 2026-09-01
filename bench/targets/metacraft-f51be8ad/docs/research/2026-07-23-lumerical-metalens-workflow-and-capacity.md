---
record_type: research_record
date: 2026-07-23
status: proposed_architecture_input
authority_level: none
current_capability: false
scope: lumerical_metalens_workflow_python_sessions_sweeps_capacity_and_permits
---

# Lumerical metalens 工作流与容量边界

## 结论

Ansys 官方的小型 metalens 示例支持我们恢复一条完整但不固定的科学链：

```text
target phase
  → periodic unit-cell sweep
  → complex response / near-field library
  → qualified phase mapping
  → aperture assignment
  → finite-aperture field propagation
  → focusing evaluation
```

这条链是 proof dependency，不是写死的 workflow。官方示例以圆柱纳米柱和 RCWA 为主，并给出 FDTD 单元附录；它明确指出求解器选择取决于结构、材料、source 和频点数。MetaCraft 当前可以绑定 Lumerical FDTD，但不能把官方示例的半径、高度、周期、波长、11 µm 或 100 µm 口径写成通用默认值。

当前仓库并没有传播相位或 PB 相位的 Python template，也没有 run saving、Lumerical session、resource observation 或 sweep runner。`src/metacraft_next/` 目前只有 authority 的薄导出。因此这些能力不是“已经实现但需要整理”，而是旧代码删除后尚待按新 Rust core 重建。

建议当前 slice 采用一个简单边界：

- Rust 的 permit 表示一个 active solver engine slot；
- Python 拥有进程、Lumerical session、建模、保存、运行、读回和科学验证；
- 一个 propagation candidate 在一个 permit 下完成一次独立运行；
- 一个 PB candidate 在一个 permit 下顺序完成 `x`、`y` 两次独立运行，得到完整线偏振基 Jones 响应；
- 多个独立 sweep worker 可以并行，但全局 active engine 数不能超过 Rust 已接纳的 capacity；
- 当前不要在每个 worker 内再次开启 native concurrent sweep；否则 Lumerical `capacity` 与 Rust permit 会形成两层并行并导致超售；
- 每个 candidate 在运行前后都保存 exact `.fsp` 与 machine-readable manifest；任何写入只能发生在显式 workspace 内，不得在盘符根目录生成 `sequence-*`、`mcr8_*` 等临时目录。

此前的几何、坐标、source、monitor、Jones 与 read-back 契约见 [Lumerical FDTD 低 NA metalens 模板契约](2026-07-23-lumerical-fdtd-low-na-metalens-template-contract.md)。本文只补齐 metalens science flow、session、sweep、保存、资源和 permit 的关系。

## 证据口径

本文严格区分三种表述：

- **Ansys 官方事实**：Ansys/Lumerical 第一方页面明确描述的产品行为。
- **合理推论**：由多个官方行为共同推出，但官方没有替 MetaCraft 作出的架构决定。
- **MetaCraft 选择**：为了匹配当前 Rust authority 和 scientific compiler 而建议固定的 Python contract。

任何 MetaCraft 选择都不能反向表述为 Ansys 的产品限制。

## 一、官方 metalens 示例真正固定了什么

### 1. 目标相位先于几何库

**Ansys 官方事实**

Ansys 的 [Small-Scale Metalens – Field Propagation](https://optics.ansys.com/hc/en-us/articles/360042097313-Small-Scale-Metalens-Field-Propagation) 把目标相位定义为第一步。普通球面或柱面透镜可以使用解析相位；复杂系统可以在 OpticStudio 中优化相位 mask。随后才用 Lumerical 建立 meta-atom geometry 与 phase response 的映射。

因此，官方示例没有把“metalens”简化成一个固定圆柱阵列生成器。它先确定 phase demand，再选择能够满足该 demand 的物理几何。

**MetaCraft 选择**

`design` 保存 metalens aim、wavelength、focal geometry、aperture、NA、polarization 和 constraints；route compiler 再产生 target phase obligation。solver template 不能自行决定目标相位。

### 2. 单元扫参产生的是复响应与场库

**Ansys 官方事实**

官方示例扫纳米柱高度与半径，取得 transmission、phase 和 near-field；先选择合适高度，再保存 phase/field versus radius 的 library。官方还会把 radius-versus-phase 和 field-versus-phase 插值到更密的 phase samples，并为后续整口径重建下采样 field。

官方使用 RCWA 是因为它对 periodic structures 高效；附录给出 FDTD 版本。页面明确说，较合适的求解器取决于 structure shape、material、source 和 frequency points。

**合理推论**

library 的科学身份至少必须绑定 route、template、construction、material、wavelength/band、period、height、geometry parameterization、source/boundary convention、mesh、phase reference plane 与 solver product/build。缺少这些引用时，“phase versus radius”只是一列数，不是可复用 evidence。

**MetaCraft 选择**

当前 propagation-phase FDTD library 保留 complex transmission、power transmission、phase reference、monitor/read-back、warnings、solver status 和 convergence observations。不得只保留 wrapped phase。

当前 PB library 使用独立的 anisotropic geometry parameters，不复用 propagation cylinder library；每个采样点必须由两个独立线偏振输入恢复完整 Jones response，再派生 converted 与 leakage channels。

### 3. phase map 到 aperture assignment 是独立证明

**Ansys 官方事实**

官方示例在取得 phase-versus-radius library 后，把空间 target phase 转换为每个 lattice point 的 radius。页面称这一步适用于任意 target phase profile，而不只适用于它展示的球面相位。

官方示例还指出：periodic library 假设无限周期、相邻 cell 相同；真实 lens 中邻近 nanorod 半径可能突变，因而 local periodicity 会失效。大半径、强 cell interaction、粗 mesh 与 PEC aperture 也会造成 target phase 和 measured phase 的偏差。

**MetaCraft 选择**

aperture assignment 必须成为独立、可追溯的 artifact。它至少记录每个 lattice site 的 target phase、selected library entry、phase error、transmission、geometry 和 tie-break。它不能藏在 solver construction script 内。

传播相位当前使用有限 library 上的 deterministic selection。PB 当前按明确的 handedness、time sign、basis 与 orientation sign 做 deterministic orientation mapping。两条 route 不共享响应证据。

### 4. finite-aperture evaluation 不等于强制 full-lens FDTD

**Ansys 官方事实**

官方给出两种 full metalens 分析：

1. 直接构建并运行 full-lens FDTD；
2. 用 unit-cell near-field library 拼接整口径 near field，或求和 unit-cell far fields。

页面明确说，直接 FDTD 对大 metalens 会消耗大量 memory 与 simulation time；field reconstruction 避免 full-lens simulation，更高效，但依赖 local periodicity。官方只用 11 µm 小 lens 将间接重建与直接 FDTD 对照，再把重建方法应用到更大 lens。

**合理推论**

直接 full-device FDTD 是一种 validation binding，不是 metalens compiler 的永久必经步骤。有限口径 proof 仍需验证，但可以由经过 qualification 的 field reconstruction / propagation operator 完成。

**MetaCraft 选择**

当前 low-NA slice：

```text
FDTD periodic unit cell
  → qualified response library
  → traceable aperture field
  → Python scalar angular spectrum
  → focusing metrics
```

full-lens FDTD 仅作为未来小口径 reference fixture，不是当前 release 的完成条件。large-NA vector angular spectrum、Debye recovery 与 optimizer 仍不实现。

### 5. `λ / (2NA)` 是 unit-cell 上限，不是天然等号

**Ansys 官方事实**

Ansys 的 [Introduction to metalens workflows](https://optics.ansys.com/hc/en-us/articles/35797097445779-Introduction-to-metalens-workflows) 给出：

```text
NA ≤ wavelength / (2 × unit-cell size)
```

等价地：

```text
unit-cell size ≤ wavelength / (2 × NA)
```

因此 `wavelength / (2NA)` 给出的是透镜横向采样允许的最大 unit-cell size，而不是所有 metalens 都必须采用的唯一周期。官方 small-scale metalens 页面还提醒，改变 wavelength 或 period 时通常应避免 multiple grating orders。

**MetaCraft 选择**

此前讨论的：

```text
sampling_limit = reference_wavelength / (2 × numerical_aperture)
rounded_limit = floor_to(sampling_limit, 10 nm)
```

可以保留为当前 low-NA compiler 的候选上限，但在正式 specification 中必须区分：

```text
sampling_limit
unit_cell_period
```

在确认 surrounding media、允许的 grating orders 与目标 order 之前，template 不得把二者悄悄合并为一个普适等式。若当前设计明确选择上限作为实际周期，该选择必须作为 MetaCraft policy 保存，并由 `grating_s_params` 的 order observation 与相应 qualification 支撑。

### 6. 官方示例常数不是 MetaCraft 默认值

**Ansys 官方事实**

官方示例展示了特定 radius、height、period、aperture 与 lens radius，并提醒 wavelength 或 period 变化时要避免 multiple grating orders，geometry 变化时必须同时更新 unit cell 和 full-lens model/sweep。当前示例还是 single-frequency；broadband 需要增加 frequency dimension。

**MetaCraft 选择**

以下数值一律只能作为 source-specific example facts：

- 示例中的纳米柱半径区间；
- 示例中的 1.1 µm 或 1.3 µm height；
- 示例中的 11 µm 或 100 µm lens radius；
- 示例中出现的 transmission threshold、mesh、monitor offset 或 focal length。

template 只能接收设计、材料、制造与 qualification 推导出的参数；不能内置这些示例常数。

## 二、Python API、session 与 sweep 的官方边界

### 1. session 是 Lumerical 产品会话

**Ansys 官方事实**

Ansys [Lumerical Python API Reference](https://optics.ansys.com/hc/en-us/articles/38660003331859-Lumerical-Python-API-Reference) 将 `lumapi.FDTD(...)` 定义为一个 interactive product session。构造器可以加载 project 或 script，`hide=True` 会隐藏 CAD 与 popup。几乎所有 Lumerical script commands 都可以作为 session methods 调用。

官方 [Script Commands as Methods](https://optics.ansys.com/hc/en-us/articles/360041579954-Script-Commands-as-Methods-Python-API) 使用 context manager 管理 session，并提醒 construction properties 可能有设置顺序或相互覆盖的问题。官方 API reference 还警告 duplicate object names 会产生 undefined behavior。

`serverArgs` 中无效的 command-line arguments 可能既不起作用，也不产生 warning。因此传入 `threads`、`platform` 或其他 launch 参数不等于它们已生效。

**MetaCraft 选择**

只有 `lumerical_fdtd/session.py` 接触 `lumapi.FDTD`。它必须：

- 使用 context manager 或等价的 guaranteed close；
- 只接收经过 readiness observation 解析的 exact API path 与 executable path；
- 使用唯一 object names；
- 按 template 的确定顺序写入 properties；
- 对关键设置做 solver read-back；
- 把 launch arguments 与 read-back 分开记录；
- 不把 session object 泄露给 route、study、evaluator 或 Rust adapter。

### 2. Python 与 Lumerical workspace 不是同一个内存空间

**Ansys 官方事实**

Ansys [Passing Data – Python API](https://optics.ansys.com/hc/en-us/articles/360041401434-Passing-Data-Python-API) 说明 Python 与 Lumerical script workspace 是分离的，数据在两边复制并转换；dictionary 顺序也不应被当作稳定 wire representation。

**MetaCraft 选择**

所有 solver input 与 result 都通过 typed manifest 转换，不能依赖 session workspace 中残留的 variable，也不能以 unordered dictionary 的偶然顺序形成 content identity。

### 3. native parameter sweep 与 explicit jobs 都存在

**Ansys 官方事实**

Ansys 的 [`addsweep`](https://optics.ansys.com/hc/en-us/articles/360034930413-addsweep-Script-command) 可以建立 parameter sweep、optimization、Monte Carlo 或 S-parameter sweep；[`runsweep`](https://optics.ansys.com/hc/en-us/articles/360034931413-runsweep-Script-command) 可以运行全部或指定 sweep，并可在 FDTD 中选择 CPU 或 GPU resource type。

[`havesweepresult`](https://optics.ansys.com/hc/en-us/articles/360034409954-havesweepresult-Script-command) 只回答某个 sweep/result 是否有数据；它不回答数据是否满足 MetaCraft 的 scientific evidence contract。

Ansys 也提供 explicit job queue：

- [`addjob`](https://optics.ansys.com/hc/en-us/articles/360034410714-addjob-Script-command) 把一个已保存 simulation file 加入 Job Manager queue；
- [`runjobs`](https://optics.ansys.com/hc/en-us/articles/360034931373-runjobs-Script-command) 使用 Resource Manager 运行 queue；
- 官方示例先为每个 sweep point 保存独立 simulation file，再 enqueue，运行后逐个 reload 做 analysis。

`runjobs` 在 concurrent jobs 中遇到错误时，未出错的 jobs 会继续，出错 jobs 会终止；多个错误只显示最后一个。它本身不返回 result data。

**合理推论**

一次 aggregate `runjobs` 返回或异常不足以证明每个 candidate 成功或失败。每个 saved simulation 必须分别检查 solver status、required results、warnings 与 artifact identity。

**MetaCraft 选择**

当前 release 以 explicit candidate runs 为标准，而不把 Lumerical native sweep object 当作 durable scientific workflow：

- compiler 产生 immutable candidate specifications；
- runner 为每个 candidate 建立并保存 exact `.fsp`；
- worker 在 permit 内同步运行一个 active engine；
- worker 保存完成后的 `.fsp` 并提取 observation；
- Python scientific validator 决定 observation 是否具有完整形式；
- Rust 只决定 receipt 或 close 的 authority transition。

native `addsweep/runsweep` 可以用于 qualification fixture 或未来的 batch binding，但不能绕过 per-candidate task、permit、artifact 与 evidence closure。这是 MetaCraft 的 traceability 选择，不是 Lumerical 的限制。

## 三、资源、并发与许可证的官方语义

### 1. 单个 simulation 的并行和多个 simulations 的并发是两件事

**Ansys 官方事实**

Ansys [Introduction to High-Performance Computing with Lumerical](https://optics.ansys.com/hc/en-us/articles/360025589054-Introduction-to-High-Performance-Computing-with-Lumerical) 区分：

- concurrent parametric computing：多个 simulations 并行；
- distributed computing：一个 FDTD/varFDTD simulation 分布到多个 nodes；
- hybrid configuration：两者组合。

Ansys [Resource configuration elements and controls](https://optics.ansys.com/hc/en-us/articles/360058790674-Resource-configuration-elements-and-controls) 定义：

```text
cores per simulation = processes × threads
concurrent simulations per resource = capacity
```

页面还特别说明 UI 的 `Total Cores` 只反映单个 simulation，不包含 capacity。因此总的潜在 CPU envelope 需要另行考虑：

```text
processes × threads × capacity
```

parametric sweeps 会使用所有 active resources；FDTD CPU sweep 只使用 CPU resources，GPU sweep 只使用 GPU resources。单次 FDTD simulation 使用 `Run Simulation` 中选择的 resource。

**MetaCraft 选择**

当前只支持经过 qualification 的 local CPU FDTD resource。GPU、remote Interop、cluster scheduler 与 Cloud Burst 不作为当前隐式 fallback。

每个 worker 内只允许一个 active engine。跨 worker 的并发由 Rust permits 限制。一个 worker 可以给单个 FDTD job 使用多个 processes/threads，但这不会增加 permit 数。

### 2. Lumerical `capacity` 与 Rust permit 不能成为两个调度器

**Ansys 官方事实**

Lumerical 的 `capacity` 是“每个 resource 同时运行多少 simulations”的 Resource Manager 设置。它会影响 native parametric sweeps / job execution 的并发和 license estimate。

**合理推论**

如果 MetaCraft 启动 `N` 个 worker，而每个 worker 又让自己的 Job Manager 启动 `capacity=C` 个并发 jobs，实际 active engines 可能接近 `N × C`。Rust 即使只发出 `N` 个 permits，也无法代表真实 solver 占用。

**MetaCraft 选择**

当前固定：

```text
one permit = one worker = at most one active solver engine
```

因此 worker 使用同步 single-run execution。Lumerical resource `capacity` 仍作为可观测的并发上限和 license-estimation input，但当前 worker 不在 permit 内再展开 native concurrent sweep。

未来若引入 batch executor，必须另立 binding，并把“一份 permit 对应一个 batch”改为“一份 permit 对应一个 active engine child run”；在此之前不实现双层并发。

### 3. license estimate 不是 license availability

**Ansys 官方事实**

Ansys [Lumerical product components and licensing overview](https://optics.ansys.com/hc/en-us/articles/360033862333-Lumerical-product-components-and-licensing-overview) 区分 CAD/GUI license 与 solve/engine license：打开 design environment 会 checkout GUI license，运行 simulation 会 checkout solve/engine license。2021 R2 起，同一机器上的多个 CAD instances 只使用一个 GUI license；remote GUI 未关闭时仍会占用。

Ansys [`getlicenseestimate`](https://optics.ansys.com/hc/en-us/articles/41005222267923-getlicenseestimate-Script-command) 返回选定 solver/resource 的 feature 与 single/sweep 所需 license estimate。它计算“需要多少”，不证明当前“还有多少可用”。

Ansys [How to check license status and availability](https://optics.ansys.com/hc/en-us/articles/5770622400659-How-to-check-license-status-and-availability) 给出 License Management Center 与 `lmutil lmstat` 的当前 usage/availability 查询方式。这个结果是观察时刻的 snapshot，不是对未来 job 的 reservation。

**MetaCraft 选择**

readiness 必须分别保存：

```text
license demand estimate
license availability observation
observed_at
license feature
license server identity
solver build
selected resource
```

Rust permit 只保留 MetaCraft capacity，不 checkout 或保留外部 Ansys license。即使 permit 已发出，license 仍可能在 job 启动前被其他程序占用；这种 checkout failure 必须作为可解释的 run observation 返回，不能假装 readiness 永久有效。

### 4. license sharing 规则必须按版本和许可证类型观察

**Ansys 官方事实**

Ansys [solve, accelerator, and HPC license consumption](https://optics.ansys.com/hc/en-us/articles/360058577794-Ansys-optics-solve-accelerator-and-Ansys-HPC-license-consumption) 说明 license consumption 依赖 standard/enterprise license、CPU/GPU、cores/SMs、concurrent jobs、launcher 与版本。

该页面给出的 standard-license 示例中，本地 eligible configuration 在总计不超过 32 cores/threads 时可以共享一份 solve license；`processes=6, capacity=4` 共 24 cores 的示例使用一份 solve license，而 `processes=6, capacity=6` 共 36 cores 的示例需要六份。页面同时列出 Windows MPI、GUI/command line 和版本限制。

**MetaCraft 选择**

`32`、`6×4`、`6×6` 都不得写进通用 capacity algorithm。adapter 必须对 exact product build、license family、launcher 和 selected resource 使用官方 estimator/read-back；无法可靠解释时，capacity 降到已证明可行的保守值，不能猜测共享资格。

### 5. resource test 也不是完整 qualification

**Ansys 官方事实**

Resource Configuration 的 `Run Test` 用于确认 supported resource presets 是否正确配置；custom launcher 即使能实际运行，也可能显示 test failure。License estimation tab 显示 estimated license requirement。

**合理推论**

`Run Test`、`getlicenseestimate`、`lmstat` 各自只回答一个局部问题：

```text
resource launch configuration
license demand
current license availability
```

它们都不能单独证明 template geometry、materials、monitor results、phase convention 或 numerical convergence。

**MetaCraft 选择**

external solver 的心智顺序保持：

```text
configured
  → found
  → versioned
  → licensed
  → qualified
  → available
```

`available` 由 exact binding 与 fresh positive capacity 推导，不保存为独立 mutable status。

### 6. `-use-solve` 不是 sweep execution shortcut

**Ansys 官方事实**

Ansys [Using solve licenses with FDTD and MODE](https://optics.ansys.com/hc/en-us/articles/7764548882963-Using-solve-licenses-with-FDTD-and-MODE) 说明 2022 R2.1 起可以用 `-use-solve` 在没有 GUI license checkout 的情况下运行 analysis scripts，但该模式只允许 results analysis，`run` 与 `runsweep` 被禁用。

**MetaCraft 选择**

当前执行 simulation 的 session 不启用 `use-solve` analysis-only mode。未来可以为离线 result extraction 建立独立 analysis binding，但不得把它误当成 FDTD sweep runner。

## 四、MetaCraft 当前应恢复的两个模板

### 1. `periodic transmission`

用途：传播相位 unit-cell complex response。

一个 candidate 至少产生：

```text
construction manifest
pre-run .fsp
post-run .fsp
solver status
complex transmission
power transmission
reference-plane convention
near field needed by aperture reconstruction
mesh and convergence observations
warnings and logs
```

该模板由一个线偏振输入完成。若 design 声称 polarization-insensitive，必须由 symmetry/qualification 或额外 polarization evidence 支持，不能由圆柱外形自动推定。

### 2. `periodic jones`

用途：PB-phase anisotropic unit-cell response。

一个 scientific candidate 包含两个独立 solver runs：

```text
x input → Ex, Ey output
y input → Ex, Ey output
```

二者共同形成 linear-basis Jones matrix，再按显式 convention 转为 circular-basis converted/leakage channels。只读取 `Txx` 与 `Tyy` 或两个 same-polarized `S21` 不足以证明 full Jones response。

当前最简 permit 语义：

```text
one PB candidate
  → acquire one permit
  → run x input
  → save and inspect
  → run y input
  → save and inspect
  → validate the pair
  → receipt or close
```

两个 runs 顺序执行，所以始终只占一个 active engine。未来若并行执行两种输入，必须取得两个 active-engine permits；不能在一个 permit 内悄悄并行。

## 五、run saving 契约

### 1. 每次运行都有确定的归属

**MetaCraft 选择**

runner 只接受 authority workspace 给出的 explicit run root，不接受当前工作目录、盘符根目录或临时硬编码路径。

建议逻辑布局：

```text
<workspace run root>/
  <task identity>/
    <attempt identity>/
      input.json
      construction.json
      before.fsp
      after.fsp
      observation.json
      solver.log
```

目录名称来自 stable task/attempt identity，不来自全局 sequence number，不创建 repository sibling directory。相同 artifact 最终由 authority 以 immutable reference 接纳；staging directory 只是执行暂存，不是真相来源。

### 2. 保存发生在运行前后

**Ansys 官方事实**

`addjob` 接受 simulation file，Ansys 的 `runjobs` 示例先保存每个 sweep point，再入队，完成后逐个 reload 分析。

**MetaCraft 选择**

- `before.fsp` 证明实际送入 solver 的 model；
- `construction.json` 保存预期值与 solver read-back；
- `after.fsp` 保留 exact results-bearing project；
- `observation.json` 只引用已检查的 results，不以“文件存在”代替科学验证；
- 原始 solver log/warnings 不被 summary 覆盖；
- crash 后只从 authority view 重编译；staging 中的 orphan files 不自动成为 evidence。

### 3. aggregate failure 必须拆回 candidate

**MetaCraft 选择**

若未来 binding 使用 `runjobs`，即使 batch 抛出异常，也必须逐个 reload candidate：

```text
result complete and valid
  → valid observation

solver completed but scientific result failed
  → valid failure observation

missing / corrupt / identity mismatch
  → no valid observation
```

前两种可以在 Python validation 后提出 receipt；最后一种以 close 结束 permit。失败不允许留下 open permit。

## 六、capacity observation 与 permit admission

### 1. capacity 的输入

**MetaCraft 选择**

一个 Lumerical FDTD capacity observation 至少引用：

```text
exact qualification
solver product and build
selected resource identity
resource read-back
processes
threads
configured Lumerical capacity
compute budget
license demand estimate
fresh license availability snapshot
launcher and license family
observed_at and freshness policy
user ceiling
```

当前 CPU worker 的保守 compute bound：

```text
cores_per_engine = processes × threads
compute_bound = floor(allowed_compute_threads / cores_per_engine)
```

最终 admitted limit 是所有可证明上限中的最小值：

```text
min(
  user ceiling,
  selected-resource concurrency bound,
  compute bound,
  observed license bound
)
```

license bound 不能从一个过时的 `lmstat` 或硬编码 `32 cores` 推断。若 estimator 与 availability 无法共同证明正值，capacity 不得为正。

### 2. capacity scope 必须精确

**MetaCraft 选择**

scope 不能只叫 `fdtd`。它至少区分会竞争同一资源与许可证池的 binding，例如：

```text
lumerical-fdtd/local-cpu/<resource-identity>/<license-pool-identity>
```

propagation 与 PB 可以共享同一个 engine pool，因此可共享 capacity scope；它们的 templates 与 scientific evidence 仍完全分离。

### 3. permit 发放与 worker 心智顺序

**MetaCraft 选择**

```text
recompile from authority view
  → choose one ready bound task
  → fetch matching current capacity
  → propose permit
  → start one Python worker
  → open one hidden Lumerical session
  → construct and read back
  → save before.fsp
  → run one active engine
  → save after.fsp
  → extract and validate observation
  → propose receipt or close
```

Rust 不创建 thread、不启动 process、不调用 Lumerical、不解析 `.fsp`、不计算 phase，也不判断 solver result。Rust 只保证当前 capacity 下 open permits 不超限，并保证每个 permit 最终只有一个 authority closure。

### 4. freshness 与竞态

**合理推论**

license availability 会被外部进程改变；compute load 也会在 observation 后变化。因此 capacity observation 不能成为永久事实。

**MetaCraft 选择**

- capacity 引用 exact observation time 与 freshness policy；
- stale capacity 不用于新 permit；
- 已取得 permit 仍不保证外部 license checkout 成功；
- checkout/resource failure 形成 observation 后触发新的 readiness/capacity observation；
- runner 不在失败后扩大并发，也不把 retry 藏在同一 immutable task identity 中。

## 七、建议的 Lumerical FDTD deep package

这只是 Python seam 建议，不是当前已实现文件。

```text
src/metacraft_next/
  solvers/
    lumerical_fdtd/
      readiness.py
      session.py
      resources.py
      materials.py
      runs.py
      sweep.py
      constructions/
        propagation_cell.py
        pb_cell.py
      templates/
        periodic_transmission.py
        periodic_jones.py
      qualification/
```

职责边界：

- `readiness.py`：`configured → found → versioned → licensed`；
- `session.py`：唯一 `lumapi` lifecycle boundary；
- `resources.py`：resource read-back、license estimate、availability 与 capacity observation；
- `materials.py`：portable material write-in 与 exact solver-native binding；
- `constructions/`：把 solver-neutral candidate 建为 Lumerical-native geometry；
- `templates/`：simulation region、boundaries、source、monitor 与 observation contract；
- `runs.py`：一个 permit 内的一次 active-engine execution、保存与 read-back；
- `sweep.py`：Python candidate queue 与 worker coordination，不保存 durable workflow state；
- `qualification/`：exact product/build/template/construction/material fixtures。

route modules 只能看 capability、task 与 typed observation；不得 import `lumapi`。Rust adapter 也不得 import 这些 scientific modules。

## 八、尚未由官方文档决定的事项

以下问题必须由 MetaCraft spec/qualification 决定，不能假称 Ansys 已替我们决定：

1. propagation library 的具体 geometry range、sampling density、loss 和 tie-break；
2. PB anisotropic geometry 的参数化与 full Jones acceptance thresholds；
3. monitor plane、phase compensation、near-field sampling 与 ASM aperture-plane convention；
4. local-periodicity error 的 acceptance test；
5. exact compute budget 与 capacity freshness duration；
6. standard/enterprise license 的本机解析与不确定时的降级策略；
7. `.fsp` 是否作为 authority object 直接收纳，或由 immutable external artifact manifest 引用；
8. qualification fixtures 的最小规模、运行时间与数值阈值；
9. Lumerical native job queue 是否在未来成为独立 batch binding；
10. full-lens FDTD reference fixture 何时进入 release gate。

这些 gap 不阻止先实现 package skeleton、readiness、两种 periodic templates、single-engine runner 和 per-candidate artifact contract；但在 qualification 完成前，不能声明 Lumerical FDTD binding `available`。

## 官方来源

- [Small-Scale Metalens – Field Propagation](https://optics.ansys.com/hc/en-us/articles/360042097313-Small-Scale-Metalens-Field-Propagation)
- [Introduction to metalens workflows](https://optics.ansys.com/hc/en-us/articles/35797097445779-Introduction-to-metalens-workflows)
- [Lumerical Python API Reference](https://optics.ansys.com/hc/en-us/articles/38660003331859-Lumerical-Python-API-Reference)
- [Script Commands as Methods – Python API](https://optics.ansys.com/hc/en-us/articles/360041579954-Script-Commands-as-Methods-Python-API)
- [Passing Data – Python API](https://optics.ansys.com/hc/en-us/articles/360041401434-Passing-Data-Python-API)
- [Parameter sweeps, Optimization and Monte Carlo analysis overview](https://optics.ansys.com/hc/en-us/articles/360034922853-Parameter-sweeps-Optimization-and-Monte-Carlo-analysis-overview)
- [`addsweep`](https://optics.ansys.com/hc/en-us/articles/360034930413-addsweep-Script-command)
- [`runsweep`](https://optics.ansys.com/hc/en-us/articles/360034931413-runsweep-Script-command)
- [`havesweepresult`](https://optics.ansys.com/hc/en-us/articles/360034409954-havesweepresult-Script-command)
- [`addjob`](https://optics.ansys.com/hc/en-us/articles/360034410714-addjob-Script-command)
- [`runjobs`](https://optics.ansys.com/hc/en-us/articles/360034931373-runjobs-Script-command)
- [Resource configuration elements and controls](https://optics.ansys.com/hc/en-us/articles/360058790674-Resource-configuration-elements-and-controls)
- [Introduction to High-Performance Computing with Lumerical](https://optics.ansys.com/hc/en-us/articles/360025589054-Introduction-to-High-Performance-Computing-with-Lumerical)
- [Lumerical product components and licensing overview](https://optics.ansys.com/hc/en-us/articles/360033862333-Lumerical-product-components-and-licensing-overview)
- [Ansys optics solve, accelerator, and Ansys HPC license consumption](https://optics.ansys.com/hc/en-us/articles/360058577794-Ansys-optics-solve-accelerator-and-Ansys-HPC-license-consumption)
- [`getlicenseestimate`](https://optics.ansys.com/hc/en-us/articles/41005222267923-getlicenseestimate-Script-command)
- [How to check license status and availability](https://optics.ansys.com/hc/en-us/articles/5770622400659-How-to-check-license-status-and-availability)
- [Using solve licenses with FDTD and MODE](https://optics.ansys.com/hc/en-us/articles/7764548882963-Using-solve-licenses-with-FDTD-and-MODE)
