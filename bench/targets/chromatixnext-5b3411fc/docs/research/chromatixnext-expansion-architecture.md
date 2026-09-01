# ChromatixNext 科学架构扩展调研：厚样品、DOE/D2NN 与多卡优化

> 调研日期：2026-08-20
> 证据原则：外部技术事实只采用论文原文、官方文档或作者维护代码；仓库事实来自本地源码、`CONTEXT.md`、`docs/architecture.md`、ADR 与 Git 对象。本文提出研究路线和候选，不设计最终方法/参数 Interface，也不授权清理、合并、推送或生产代码变更。

## 0. 结论先行

导师对 ChromatixNext 的评价抓住了真正有研究价值的方向，但有三点必须校准，才能避免用错误的“独特性”启动一次大而散的重构。

1. **显式 polarization 不是 ChromatixNext 相对上游的独占能力。** 上游 Chromatix 当前明确使用 Jones calculus，区分 Scalar/Vector Field，并已有偏振元件和三分量矢量场；它还已有标量、荧光和 `3×3` tensor birefringent multislice。ChromatixNext 的可论证差异是：Polarization State/Representation/Action Contract 被写成强领域契约，同时 Ray Bundle 也携带显式、归一、横向的复 polarization direction。[Chromatix polarization 文档](https://chromatix.readthedocs.io/en/latest/polarization/)、[Chromatix 厚样品源码（固定 main SHA）](https://github.com/chromatix-team/chromatix/blob/ce1482906fc663298613bb252bbf425e3be59839/src/chromatix/functional/samples.py)
2. **“Wave/Ray 双轨并行不悖”是 Next 的真实架构优势，但不是由偏振单独造成，也不表示当前会并行执行。** 保证两轨不混淆的是 Optical Field 与 Ray Bundle 的 Physical Value 分离、Assembly 的类型化连接、显式禁止 Wave↔Ray 转换，以及同一冻结事实/同一 replay；偏振使两条轨道都具有更完整的物理状态。当前 Workstation 仍是一设备、一次 run，不应把结构共存写成计算并发。
3. **厚样品、DOE 与多卡都不是上游 Chromatix 的空白。** 上游已有这些具体能力；Next 的机会是以 SSR-E2 把模型近似域、梯度证据、状态/失败 owner、Assembly 组合和执行证据重新做深，而不是逐项照搬功能。[Chromatix Nature Methods 论文](https://doi.org/10.1038/s41592-026-03121-x)明确把其定位为 differentiable、GPU-accelerated wave-optics library，并报告特定工作负载在单 GPU 上约 `2–6×`、8 GPU 上最高 `22×`；这些是论文负载结果，不是一般缩放保证。

由此得到的首要建议是：

- **先做零新增 production action 的 DOE/D2NN Example 证据闭环**，验证现有 Optical Path Modulation、Amplitude Transmission Map、Propagation、Assembly、Detection 和 Parameter 生命周期已经能走通连续理想薄层的设计；
- **第一个新科学能力只切标量、各向同性、单向的 multislice 厚样品**，把它做成一个通过 deletion test 的 deep module；
- **矢量/双折射厚样品是下一阶段研究亮点，不与第一刀捆绑**；
- **多卡先做独立实验与 batch/波长轴，Linux+NCCL 为首个可验收路径**；FSDP 和空间域 distributed FFT 分别是后续条件触发项；
- **现在不要建立通用优化框架、通用 Sample/Layer 基类、统一 solver selector 或 distributed-FFT seam。** 这些目前都没有足够 adapter 和真实调用方，属于 speculative seam。

## 1. 证据快照与版本范围

### 1.1 本仓库

本报告读取时，根工作树位于 `scientific-foundation-final-seal@3557373`。`ssre2-admission-closure@a8dc985` 是候选分支：`main...a8dc985 = 0/34`，即 `main` 是候选祖先；候选尚未合并或推送，本仓库没有 Git remote。SSR-E2 ADR 位于候选提交链中的 `docs/adr/0017-ssre2-admission-contract.md`，因此本文把它作为**已形成并经候选验证的治理合同**，不把它误写成当前根分支已合并事实。

当前领域与架构事实的主要 owner 是 [CONTEXT.md](../../CONTEXT.md)、[architecture.md](../architecture.md)、[ADR-0003](../adr/0003-optics-numerics-workstation-boundary.md)、[ADR-0004](../adr/0004-example-owned-research-workflows.md)、[ADR-0005](../adr/0005-fixed-double-scientific-core.md)、[ADR-0007](../adr/0007-mixed-independent-wave-ray-assembly.md)、[ADR-0008](../adr/0008-active-polarization-foundation.md)、[ADR-0009](../adr/0009-polarized-ray-foundation.md)、[ADR-0011](../adr/0011-assembly-topology-contract.md) 和 [ADR-0014](../adr/0014-ssrhm-conic-and-sampled-wave-deepening.md)。

### 1.2 上游 Chromatix

版本不能混写：2026 年 Nature Methods 论文说明实验使用 Chromatix `0.4`；当前在线文档标识 `0.6.0`；本次源码核验固定在上游 `main@ce1482906fc663298613bb252bbf425e3be59839`。报告中的“上游已有”主要指 `0.6/main`，论文性能数字只指论文工作负载和论文版本。

### 1.3 PyTorch 与本机证据

项目 [release.toml](../../src/chromatix_next/release.toml) 固定 Python 3.12、PyTorch 2.12、Windows、Fixed Double，并明确 `windows_multi_gpu = false`。本机是 `torch 2.12.0+cu130` 且只有 1 块 GPU，因此本报告没有、也不能声称取得任何 native multi-GPU 实证。PyTorch distributed 的当前上游状态会变化；涉及实施的判断必须在真正重开时重新固定文档版本和硬件清单。

## 2. 传统 Chromatix 的真实优势、限制与 Next 的差异

### 2.1 上游真正做深的地方

Chromatix 的核心思路是：把复光场、wavelength、polarization 和 spatial sampling 编入 Field，再把 optical system 写成 Field transformation 的组合。论文把 differentiability、composability、scalability 作为三项核心要求；官方 `OpticalSystem` 则按序调用 Callable/Equinox module，通常是 `Field -> Field`。[论文](https://doi.org/10.1038/s41592-026-03121-x)、[OpticalSystem 官方文档](https://chromatix.readthedocs.io/en/latest/api/systems/)

其优势是真实而具体的：

- JAX automatic differentiation、JIT、vectorization 与多设备变换可以直接作用于 optical model；
- functional core 与 element module 可以混用，研究者能快速组成 wave-optics 实验；
- 已覆盖 scalar/vectorial free-space propagation、scattering samples、phase/amplitude masks、SLM、sensor 和多波长；
- optimization 不被一个项目 optimizer 垄断：对象是 PyTree/JAX-transformable function，可由 Optax、Optimistix 或自写过程优化；参数选择可经函数、Equinox/Flax module 或 `partition/combine` 完成。[Chromatix FAQ](https://chromatix.readthedocs.io/en/latest/FAQ/)

### 2.2 不应夸大的“Next 独特性”

上游已经显式处理 polarization：Jones calculus 只覆盖 fully polarized light，Scalar Field 与 Vector Field 分开，Vector Field 携带三个电场分量，并有 polarizer/waveplate 等元件。[官方 polarization 文档](https://chromatix.readthedocs.io/en/latest/polarization/)

上游也并非完全没有“ray”术语，但其当前 [`functional/rays.py`](https://github.com/chromatix-team/chromatix/blob/ce1482906fc663298613bb252bbf425e3be59839/src/chromatix/functional/rays.py) 提供 ABCD matrix helper 和 `ray_transfer`；后者传播的仍是 Field，依据 Collins diffraction integral 通过 FFT/IFFT 得到输出波场。它不是携带独立 ray state、surface encounter、aperture hit、termination status 的通用 geometric ray tracer。

因此，准确比较是：

| 维度 | 上游 Chromatix 0.6/main | ChromatixNext 当前/候选 |
|---|---|---|
| 核心状态 | 结构化 Scalar/Vector Field | 统一 Optical Field 轴契约 + 独立 Ray Bundle |
| Polarization | 显式 Jones；fully polarized；Mueller 未覆盖 | Source-authored Polarization State；Wave 表示与 Ray polarization direction 分别有明确 frame/适用域 |
| Ray | ABCD/Collins 驱动的波场传播，不是通用 ray state | 精确 Surface encounter、Ray Status、per-ray Optical Path、polarization transport |
| 组合 | 序列 OpticalSystem 为主 | 类型化、冻结、multi-root DAG Assembly；Wave/Ray 独立子图可共存但禁止互转 |
| 执行 | JAX transformations 提供设备/并行能力 | Workstation 单一执行 seam，meta/real 同一 replay，当前每次 run 一设备 |
| 数值治理 | 广而快、研究组合友好 | Fixed Double、exact topology decisions、stable error identity、claim-family budget |
| 证据治理 | 论文/测试/示例共同支撑 | Component Evidence + CSU + SSR-E2 admission，可追到 claim/failure/oracle owner |

### 2.3 ChromatixNext 已有成果的可论证优势

Next 的优势不应表述为“功能更全”或“性能更快”，而应表述为更高的 **locality、leverage 与可审计性**：

- 三个 production seam 保持 `workstation.py -> optics -> _numerics` 单向依赖；物理意义不依赖设备策略。
- Physical Value、Optical Role、Assembly 和 Workstation 分别拥有自己的失败与状态；删除这些 deep module 会把单位、轴、dtype、适用域、ownership 和重放复杂度重新散回调用方，因此通过 deletion test。
- Wave/Ray 的 controlled asymmetry 被保留：它们共享 Assembly 语法与执行 seam，却不伪造转换、不强制镜像相同 Interface。
- Fixed Double 与 exact-sign predicate 把“浮点近似误差”和“物理模型近似”分开；这为厚样品的 Stated-Domain Approximation 留出了清晰位置。
- Candidate ADR-0017 把 SSR-E2 定义为 Sonnet、Simple、Reliable、Evidenced、Evolvable，并要求 Reliable/Evidenced 硬通过、所有债带 owner 和 reopening trigger。这比一次性覆盖率或“测试很多”更适合科学代码封档。

“CSU 双级架构”可防守地解释为两级治理，而不是两个 production seam：第一级是 `tools/check_csu.py` 与 isort 的机械 floor；第二级是 owner/rationale/evidence adjudication 加 SSR-E2 语义审查，覆盖 real correspondence、controlled asymmetry、mental order、locality 和 claim-to-evidence navigation。CSU 本身必要但不充分；这正是候选 ADR-0017 的明确立场。

## 3. 厚样品模型谱系：不要用一个 “BPM” 标签抹平

“Multislice”首先是一种轴向离散与递推结构；“BPM”是一类传播近似；“split-step”是算子分裂策略。三者有交集，但不是同义词。模型选择必须由 Physical Question 与 Stated-Domain Approximation 决定，而不是由一个 runtime selector 决定。

| 模型谱系 | 物理/数值形状 | 明确适用域与排除 | Polarization | 梯度与内存 | 对 Next 的建议 |
|---|---|---|---|---|---|
| Scalar isotropic multislice + ASM | 3D absorption/RI contrast 切成薄层；层间角谱传播，层上乘 thin transmission；递推包含前向多次散射 | 薄层离散、单向传播；不自动包含后向反射；sampling、padding、evanescent/bandlimit 都是模型事实 | 标量或 polarization-neutral | ordinary autograd 可穿过层循环；未 checkpoint 时 activation 随层数增长 | **第一项新科学能力** |
| Paraxial split-step/BPM | 对 Helmholtz/慢变包络作轴向步进，常在频域处理 diffraction、实域处理 index modulation | paraxial/slowly varying、单向；高角度与强轴向变化可能越界 | 可有 scalar 或专门 vector extension | 有成熟手推 adjoint/反传；适合独立梯度对照 | 作为近轴分支或证据，不先做 selector |
| Split-step non-paraxial (SSNP) | 同时推进 field 与轴向导数，避免 BPM 的 paraxial decoupling | 非近轴、高角度更强；仍需固定其 forward/backscatter 与离散假设 | 现有主要来源是标量 tomography | 可在 modular autodiff 中优化，但状态与通信量更大 | 第二轮以后，作为独立模型决策 |
| Tensor/vector multislice | `3×3` scattering-potential tensor 耦合三分量；每层 vectorial first-order scattering 后递推 | birefringent/anisotropic 的特定 multislice 近似；不是通用 Mueller、FDTD 或任意 Maxwell material | 显式三分量 | 反传可行，显存与证据面显著扩大 | 标量闭环后最有研究价值的扩展 |
| Modified/convergent Born 或 full-wave FDTD | 迭代 Lippmann–Schwinger 或时域 Maxwell | 计算成本更高；材料、边界和收敛条件不同 | scalar/vector 取决于 solver | 可用 adjoint/autodiff，但不应成为首刀 | 高保真 oracle/未来独立 initiative |

谱系的一手证据如下：

- Feit 与 Fleck 的早期 FFT propagating-beam 工作给出 BPM 谱系来源；它不能替代现代 multislice tomography 的适用域说明。[Applied Optics 1978](https://doi.org/10.1364/AO.17.003990)
- Chowdhury 等把 3D RI 切片，用 MSBP 从多角度 intensity-only measurements 反演多散射样品；作者仓库同时给出前向和梯度材料。[Optica 2019 论文](https://doi.org/10.1364/OPTICA.6.001211)、[Waller-Lab/multi-slice](https://github.com/Waller-Lab/multi-slice)
- SSNP 通过同时推进 field 与轴向导数消除 BPM 的关键 paraxial approximation，在高角 illumination 的 diffraction tomography 中获得更高保真。[Light: Science & Applications 2019](https://doi.org/10.1038/s41377-019-0195-1)、[作者 SSNP-IDT 代码](https://github.com/bu-cisl/SSNP-IDT)
- Mu 等的 tensor multislice 用完整 scattering-potential tensor，逐层 vector first-order scattering 并递推，论文与 FDTD、VBPM 和实验 Mueller measurement 比较。[Optica 2023](https://doi.org/10.1364/OPTICA.472077)
- 上游 Chromatix 当前已经实现 scalar、fluorescent 和 polarized multislice；其中 polarized 版本明确引用 Mu 模型，并沿切片 `jax.lax.scan`。[固定 SHA 源码](https://github.com/chromatix-team/chromatix/blob/ce1482906fc663298613bb252bbf425e3be59839/src/chromatix/functional/samples.py)、[官方复现](https://chromatix.readthedocs.io/en/latest/examples/polarized_multislice/)
- Meep 是独立 FDTD Maxwell solver，网格加密时逼近连续方程；它及其 adjoint 文档可为小型案例提供与 Next implementation 不同源的场/梯度证据。[Meep introduction](https://meep.readthedocs.io/en/latest/Introduction/)、[Adjoint solver](https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/)

### 3.1 第一刀的 evidence logic

标量各向同性 multislice 之所以是合适的最小 production 切口，不是因为它最“先进”，而是它能以最小 Interface 暴露一个真实 deep module：若删除它，slice ordering、volume admission、RI/absorption 语义、propagation kernel、slice refinement、cache/checkpoint 和梯度知识会重新散到 N 个 Assembly 调用或 Example 中，复杂度不会消失，故通过 deletion test。

首轮至少需要以下彼此独立的证据：

- 零 contrast 退化到同距离 homogeneous propagation；
- 单 slice 退化到现有 Optical Path Modulation/Amplitude Transmission Map 的 thin action；
- uniform slab 给出可解析的 phase/attenuation，且 Optical Path Reference 不被重复计数；
- slice thickness 减半时，在预先声明的域内向更细离散或独立 solver 收敛；
- 小网格与作者 MSBP 或 Meep/FDTD 的独立结果比较，不能从 production kernel 生成 expected value；
- real loss 对 volume parameter 的 PyTorch autograd 与 finite-difference/`gradcheck` 一致；PyTorch `gradcheck` 的官方定义正是以有限差分核对浮点/复数输入的解析梯度，并针对复数使用 Wirtinger 导数。[PyTorch gradcheck](https://docs.pytorch.org/docs/2.12/generated/torch.autograd.gradcheck.gradcheck.html)

反事实必须至少击穿：交换“propagate/interaction”顺序、翻转 phase sign、漏掉某一 slice 的 scatter update、detach 中间场、让 `float32` volume 偷渡、让 NaN 延迟到 FFT 后失败。若这些变异不能被既有证据检出，不能 admission。

## 4. DOE/D2NN：现有能力足以先做 Example，缺口在物理约束

### 4.1 当前能表达什么

[Optical Path Modulation](../../src/chromatix_next/optics/element/optical_path_modulation.py) 已接收逐点 `float64` Optical Path variation，可保留用户 `Parameter` identity，并按 wavelength 形成 `exp(i 2π OPD/λ)`；[Amplitude Transmission Map](../../src/chromatix_next/optics/element/amplitude_transmission.py) 已接收逐点、被动区间 `[0,1]` 的 trainable `float64` amplitude map。两者组合可表达一个连续、理想、薄、polarization-neutral 的复透射平面。

Assembly 已能把多个这类薄层与自由空间 Propagation 组成无环层栈，Intensity Detection/Named Outputs 可形成 D2NN 输出读出。原始 D2NN 的基本物理形状正是：训练每个 passive diffractive layer 上的 phase，自由空间衍射把输入逐层映射到检测面，制造后由被动层栈执行学到的功能。[Lin et al., Science 2018](https://doi.org/10.1126/science.aat8084)

因此，**连续 phase-only DOE、连续 passive amplitude mask 和理想 D2NN 多数已经是 Assembly + Example 能力**。现在新增 `PhasePlane`、`DOEElement` 或 `D2NNLayer` production action 会制造 Mysterious Name/duplicated capability，并降低 locality。

这一判断也与上游事实一致：Chromatix 已有逐像素 trainable `PhaseMask`、SLM 和 CGH Example；官方 CGH 示例明确只模拟 ideal system，未覆盖 simulation-to-reality mismatch。[Chromatix elements](https://chromatix.readthedocs.io/en/latest/api/elements/)、[CGH Example](https://chromatix.readthedocs.io/en/latest/examples/cgh/)

### 4.2 当前不能诚实表达什么

现有两张 map 不等于制造级 DOE/material model。真实缺口包括：

- surface height 到多波长 phase 的 material dispersion；当前 OPD map 在 spectral channels 间共享同一 OPD，不能自行表达 `n(λ)` 导致的 wavelength-dependent height response；
- phase levels/height levels、bit-depth、最小特征、pixel fill factor、etch/deposition 可制造区间；
- quantization 的不可微点与 surrogate/straight-through 选择；
- phase-amplitude coupling、dichroism、diattenuation、anisotropic Jones/tensor response；
- layer misalignment、thickness/spacing tolerance、fabrication noise 和 robust objective；
- 输入数据、loss、optimizer、scheduler、checkpoint、history 和 evaluation 的统一研究生命周期。

前三类可以先在两个真实 Example 中作为研究约束出现；只有多个 Example 证明同一 durable need 后，才有资格讨论新的 material/fabrication module。LightRidge 是可信的 PyTorch D2NN 参考实现，可用于比较 layer-stack、训练和 quantization，而不是作为 Next 的 Interface 模板。[LightRidge 官方文档](https://lightridge.github.io/lightridge/)、[D2NN tutorial](https://lightridge.github.io/lightridge/tutorials/tutorial_01_d2nn_training.html)、[作者论文](https://arxiv.org/abs/2306.11268)

## 5. 优化与多卡：三条并行轴必须分开

当前 Next 并不是“不可优化”：Component 可持有用户 Parameter，Assembly 注册完整 Parameter tree，Workstation hosting 保留 identity，Example 可使用普通 PyTorch optimizer。缺的是 project-owned optimizer lifecycle，而 [ADR-0004](../adr/0004-example-owned-research-workflows.md) 正是有意把 loss、optimizer、history 留在 Example，并规定“多个真实 Example 建立同一 durable need”之前不得抽取 shared optimization support。

### 5.1 轴 A：独立实验 / batch / wavelength 并行

这是最高优先级、最符合 locality 的轴。

- **独立实验**：不同 initialization、target、illumination 或超参数完全独立，不需要 gradient synchronization；可由外部 launcher 分配一 GPU 一进程，失败隔离最好。
- **batch 并行**：每 rank 完整复制 optical model，处理不同 batch，反向后归约 gradient。PyTorch DDP 的官方契约就是同步各 model replica 的 gradient；它不会自动切 input，调用方必须显式 sharding，CUDA 训练的推荐形状是一进程一卡。[DDP 2.12 文档](https://docs.pytorch.org/docs/2.12/generated/torch.nn.parallel.DistributedDataParallel.html)
- **wavelength 并行**：只有当 objective 的 spectral reduction 可分解且权重/normalization 一致时才成立；跨波长耦合的 loss、material dispersion 或 coherence claim 需要单独证明，不能把 Spectrum 轴机械等同 batch。

优势是每个 rank 仍运行现有单设备 optical implementation，production physics 不需要知道 process group。代价是每卡仍持有完整 field/FFT activation，无法解决单个超大网格的显存问题。

### 5.2 轴 B：parameter / gradient / optimizer-state sharding

FSDP `FULL_SHARD` 切分 parameters、gradients 和 optimizer states，并在 forward/backward 周围 all-gather/reshard；它不自动切分 Optical Field activation 或 FFT workspace。[FSDP 2.12 文档](https://docs.pytorch.org/docs/2.12/fsdp.html)

这条轴只有在 profile 证明 state memory 是主导者时才有 leverage。普通 2D DOE phase map 往往远小于各层 complex128 field activation；FSDP 可能增加通信却不解除真正瓶颈。大型 trainable RI volume 或与大 reconstruction network 联合优化时，它才可能成为真实候选。Activation checkpointing 是另一条“计算换显存”措施；官方说明 backward 会重跑 forward segment，若重算与原 forward 不同可能产生错误梯度，因此它也必须进入 SSR-E2 evidence，而不能当透明开关。[PyTorch checkpoint](https://docs.pytorch.org/docs/2.12/checkpoint.html)

### 5.3 轴 C：空间域 / FFT decomposition

这是完全不同的 scientific-computing 问题。二维/三维 distributed FFT 通常需要 slab/pencil decomposition 和跨 rank transpose/all-to-all；DDP 的 model replication 与 FSDP 的 state sharding 都不会自动完成它。

DTensor 用 DeviceMesh 加 `Shard`/`Replicate`/`Partial` 描述 global tensor placement，但 PyTorch 2.12 文档把它标为 alpha；建立在其上的 Tensor Parallel 文档也标为 experimental。两者的文档都没有承诺 distributed FFT，当前 PyTorch source tests 对多项 FFT 仍有 skip/xfail。因此“采用 DTensor/TP”不等于“得到稳定的分布式 FFT”。[DTensor 2.12](https://docs.pytorch.org/docs/2.12/distributed.tensor.html)、[Tensor Parallel 2.12](https://docs.pytorch.org/docs/2.12/distributed.tensor.parallel.html)、[PyTorch DTensor operator tests](https://github.com/pytorch/pytorch/blob/main/test/distributed/tensor/test_dtensor_ops.py)、[`torch.fft` 2.12](https://docs.pytorch.org/docs/2.12/fft.html)

这一轴必须单独证明：global Spatial Grid 的 shard identity、padding/cropping、frequency ordering、normalization、complex128 gradient、collective failure、meta Memory Estimate 和单卡等价性。若 batch/wavelength 并行尚未耗尽，或通信使预注册 strong-scaling target 失败，就应停止，不建立 adapter。

## 6. Windows / Linux、NCCL / Gloo 的当前官方事实

PyTorch 官方 `torch.distributed` 页面将 Linux 标为 stable、Windows 标为 prototype；Linux 默认构建 Gloo，并在 CUDA build 中包含 NCCL。官方经验规则是 CUDA distributed training 使用 NCCL、CPU 使用 Gloo；Windows 不支持 NCCL。[PyTorch distributed 2.12](https://docs.pytorch.org/docs/2.12/distributed.html)

这意味着：

- “原生 Windows 支持 PyTorch CUDA”成立，但不能推出“原生 Windows 支持 NCCL 多卡”或“与 Linux/NCCL 同等稳定”；
- Windows + Gloo 的 CUDA/FSDP/DTensor 组合没有足够官方 production guarantee，应标为 UNPROVEN，并逐项实测；
- 通用多卡的首个可封档环境应是 **Linux + CUDA + NCCL + 至少 2 块真实 GPU**；Windows 保留现有 CPU/单 CUDA Workstation 证据，直到独立 Windows distributed initiative 证明更多；
- 当前本机 1 GPU 只能做 process/control-path 负探针，不能为 scaling、collective、rank failure 或多卡 numerical consistency 提供证据。

## 7. 与现有 ADR 的冲突：哪些决定必须显式重开

| ADR/事实 | 冲突或兼容性 | 必须采取的治理动作 |
|---|---|---|
| ADR-0001 one PyTorch optical core | 厚样品与多卡仍可使用 PyTorch，原则兼容 | 不新建第二科学 runtime |
| ADR-0003 三 production seam；单 run 一设备；Windows singleton | multi-GPU 直接改变 execution seam 与 ownership/memory/replay | multi-GPU 前显式重开；不能在 Example 中暗中绕过 hosted-root ownership 后称为 product 能力 |
| ADR-0004 Example-owned optimization | “把优化系统做成框架”与当前拒绝 project optimizer framework 直接冲突 | 先完成至少两个真实 optimization Examples；只有同一 durable need 被重复证明后，单独 ADR 讨论抽取 |
| ADR-0005 Fixed Double | 多卡不必然要求 mixed precision；但 complex128 显存/通信成本高 | 首轮保持 Fixed Double；若要改 precision，必须是另一项科学决定，不能夹带在多卡重构中 |
| ADR-0007 Mixed Wave/Ray Assembly | Wave volume sample 可作为独立 Wave 子图，兼容；Wave↔Ray converter 仍禁止 | 不借厚样品发明转换或统一 optical state |
| ADR-0008/0009 polarization foundation | 明确排除了 volume samples、multislice、multiple scattering、fluorescence 等 | 厚样品必须显式部分 supersession/新 ADR，准确列出只重开的排除项 |
| ADR-0011 Assembly DAG | D2NN/DOE 层栈是无环，原则兼容；巨量 slice 不应暴露成巨量 authored nodes | 厚样品循环应藏在 deep implementation；复核 freeze/meta/memory facts，不新建第二 topology truth |
| ADR-0014 deepening | 证明 private deep module + public adapter 的方法可复用，但其 capability freeze 不授权新模型 | 不修改旧 ADR 历史；新 initiative 自有 acceptance barrier |
| Candidate ADR-0017 | admission closure 明确冻结 capability；本次属于新科学能力 | 先完成候选正式封档/合并，再以新 ADR 说明为何重开；SSR-E2 是 rubric，不是隐式授权 |
| `release.toml` Windows-only、`windows_multi_gpu=false` | 与 Linux/NCCL 首个多卡路径直接冲突 | 多卡 admission 必须更新 release scope，并提供 native Linux evidence；不能只改配置文本 |

## 8. 分阶段路线：每阶段都有 admission、反事实与停止条件

### Phase 0 — 成果收束与 r3 封档卫生

**产物**：当前候选的唯一可追溯 seal、ADR-0017 正式状态、工作区/refs/artifacts inventory；不新增科学能力。

**SSR-E2 admission**：受管 tree、manifest、gates、review verdict 和 debt list 指向同一 commit；所有验证在隔离 clone/worktree 运行；候选 ignored cache 不再破坏“seal 后零写入”的字面事实。

**反事实**：更换一个受管文件、更新一个 cache、丢失一个 ref 或重放错误 Python 环境，manifest/流程必须失败。

**停止条件**：没有 remote/bundle 备份、`rescue/ticket-04-interrupted-20260726` 的独有提交未判定、或 r2/r3 seal 事实仍冲突时，不删除任何 branch/worktree/artifact。

### Phase 1 — DOE/D2NN 可表达性证明（不加 production action）

**产物**：至少两个 source-distributed Examples：一个单平面 DOE/CGH 物理问题，一个多平面 D2NN/DOE stack 物理问题；都只使用现有 action inventory。

**SSR-E2 admission**：phase/amplitude 被动性、grid、Spectrum、polarization neutrality、Optical Path Reference 与 gradients 有独立证据；训练过程可重放；Examples 不把 loss/optimizer/history 写入 production。

**反事实**：phase sign 反转、Parameter detach、spectral weight 丢失、量化 bypass、把 amplitude 越界 clamp 而非 reject，均被测试击穿。

**停止条件**：两个 Example 没有产生同一个 durable optimization need，则不抽取 shared support；若研究目标要求 material dispersion/fabrication，先写清物理合同，不新增含糊 `PhasePlane`。

### Phase 2 — 标量、各向同性、单向 multislice

**产物**：一个 concrete thick-sample deep module 及其 private numerical implementation；不做 universal Sample framework，不做 solver selector。

**SSR-E2 admission**：第 3.1 节的解析极限、slice refinement、独立 solver、gradient、CPU/CUDA、Fixed Double、failure identity 与 Memory Estimate 全部通过；应用域明确排除 back-reflection、vector anisotropy、fluorescence 和 full-wave exactness。

**反事实**：顺序、phase、scatter recurrence、gradient graph、dtype、non-finite admission 变异均被检出。

**停止条件**：在预注册适用域内不随 slice refinement 收敛、与独立 FDTD/MSBP reference 的误差无法由模型/离散预算解释、或 meta memory 低估 real peak，则不进入 vector/multi-GPU。

### Phase 3 — 矢量/双折射 multislice

**产物**：单独 scientific decision，复用现有 Wave Polarization Frame，不创建通用 Mueller framework。

**SSR-E2 admission**：isotropic limit 收敛到 Phase 2；坐标旋转与 component order 有独立证据；cross-polarization、能量/被动性和 tensor symmetry 的物理合同明确；复现 Mu 论文小型 FDTD/VBPM case，gradient 另有 finite-difference 或 adjoint 证据。

**反事实**：转置 tensor coupling、交换 component order、漏 longitudinal component、错误 frame rotation 必须被击穿。

**停止条件**：无法在 `CONTEXT.md` 中给出唯一 frame/material vocabulary，或独立 full-wave 对照在声明域内不收敛，则保留 Phase 2，不用 tolerance 掩盖。

### Phase 4 — Linux/NCCL 的实验/batch/wavelength 多卡

**产物**：先是 Example/launcher evidence，再判断 execution seam 是否有两个真实 adapter；不直接许诺通用 distributed Workstation。

**SSR-E2 admission**：至少 2 块 native GPU；rank-sharded input 与 global reduction 有一个 owner；单卡与多卡 loss/gradient/update 在预推导预算内一致；checkpoint 可恢复；rank/device errors 稳定；吞吐、峰值显存和 communication 比例均记录。性能目标必须在运行前按具体 workload 注册，失败后不得放宽。

**反事实**：每 rank 重复完整 batch、spectral weight 重复归约、seed stream 碰撞、少一个 rank、错误 world size、错误 device placement 均被检出。

**停止条件**：无 2+ GPU 原生环境即 UNPROVEN；若通信主导且不能达到预注册收益，则停在独立实验并行，不进入 FSDP/DTensor。

### Phase 5 — 条件触发的 state sharding 与 optimization support

只有 profile 证明 parameter/optimizer state 是主要内存瓶颈，才评估 FSDP；只有至少两个真实 Example 重复同一 lifecycle/checkpoint/history need，才重开 ADR-0004。两者不是同一 seam，也不应同票实现。

**停止条件**：若 activation/FFT workspace 主导，FSDP 没有 leverage；若抽取 support 只是把 Example 代码搬进 production，deletion test 失败。

### Phase 6 — 条件触发的 spatial/distributed FFT

只有 batch/wavelength/independent-experiment 轴耗尽且单个 global field 仍无法容纳时，才启动独立 research initiative。先做 throwaway prototype，证明 decomposition、collective、autograd、Fixed Double 和 meta memory，再讨论 seam。

**停止条件**：DTensor operator coverage 不足、all-to-all 抵消收益、单卡等价性或 gradient 证据失败，均立即停止；不得用 DDP/FSDP 的存在替代 distributed FFT 证明。

## 9. 工作区清理与封档策略（建议，不执行）

2026-08-20 本地盘点显示：根工作树有未 ignore 的 `?? .agents/`（644 文件，约 35.6 MiB）；`.scratch/` 约 1.14 GiB，其中 `upstream-environments` 约 846.7 MiB、`ssre2-group-meeting` 约 173.9 MiB；`.venv/` 约 498.1 MiB，而项目 AGENTS 明确要求 miniforge `research_env`；`nature-skills` 是 ignored nested repo，约 73.9 MiB。旧 ticket branches 均已进入 candidate，只有 `rescue/ticket-04-interrupted-20260726` 仍有 1 个独有提交。candidate 还存在两个 ignored test-cache 写入。以上都是本地实况，不是本报告执行了清理。

建议顺序：

1. **冻结清理前 inventory**：记录所有 refs、worktrees、porcelain、ignored/untracked 分类、目录大小和重要 evidence hash。先证明是什么，再决定是否删。
2. **先完成 r3 seal，再清理**：候选注释/缓存/manifest/terminal review 指向同一新 commit；所有门在候选之外执行。封档与清理是两个不同动作。
3. **先建立可恢复性**：当前无 remote，不能先删 branches 或 `git gc`。至少创建一个受控 remote 和一个离线 Git bundle/镜像，并验证 clone/restore；再给 sealed commit、ADR 和 manifest 建不可歧义的 tag/ref。
4. **分类处置**：
   - 永久保留：受管源码、ADR、spec、seal record、manifest、最终 review、`rescue` 独有提交的判定记录；
   - 归档后移出工作区：`.scratch` 中历史调查、组会证据、上游环境；环境本体可由 lock/版本/脚本重建时，只保留 provenance 和必要 patch；
   - 验证后可再生：pytest/pyc cache、重复 `.venv`；删除前确认没有唯一 checkpoint/data；
   - 外置依赖：`.agents`、`nature-skills` 等不应混成产品源码；先确定 owner、版本和安装方式，再移到明确的 agent/plugin/cache 位置或形成 ignore 决定。
5. **最后删除已合并 refs/worktrees**：先审阅 `rescue` 独有提交；仅在 remote/bundle 可恢复、candidate 已正式合并且 tag 可解引用后，才删除旧 ticket branches 和 worktrees。
6. **清理后重验**：使用规定的 `research_env` 执行 CSU、isort 和与清理范围成比例的 tests；确认 tracked tree、sealed manifest、release descriptor 和 Example provenance 未改变。

这套策略的核心是 locality：源码、科学证据、可再生环境和 agent tooling 各归其 owner；不要用一次递归删除把四种生命周期混在一起。

## 10. 架构候选与最终建议

### Strong：标量各向同性厚样品 deep module

它有真实 scientific seam，删除后复杂度会散回调用方，通过 deletion test；一个 concrete implementation 足够，暂不建立 Sample family 或 solver adapter。它是第一项值得显式重开 ADR-0008/0009 exclusions 的新 production 能力。

### Worth exploring：Example-owned optimization support

现有 DOE/D2NN 与未来 RI-volume reconstruction 可形成两个真实 Examples。若它们重复 checkpoint、history、objective reduction、distributed launch 等同一 durable need，再从 source-distributed Examples 中提取小而深的 module；在此之前 seam 只是 hypothetical。

### Speculative：distributed optical execution / distributed FFT

当前只有单 GPU，本地 release 又是 Windows-only；DTensor alpha、FFT coverage 不完整，尚无第二 adapter、性能证据或 failure contract。现在设计其 Interface 会把未知的 communication、layout、autograd 和 platform 事实泄漏给整个 optical core，显著降低 depth 和 locality。

## 11. 最小科学切口与明确不做项

**总体第一步**不是写新 production code，而是用现有 Optical Path Modulation + Amplitude Transmission Map + Propagation + Assembly 完成 DOE/D2NN 双 Example，借此建立真实 optimization workload 和 gradient/memory baseline。

**第一项新科学切口**是标量、各向同性、单向 multislice 厚样品：Fixed Double、一个明确传播模型、一个 slice rule、无 back-reflection、无 fluorescence、无 vector anisotropy、无 solver selector。它先证明 Volume Sample 的领域词、近似域、梯度和 evidence logic，再决定是否进入 Mu tensor multislice。

现在不应建立：

- 通用 `Sample`/`Layer`/`DOE` 基类或 registry；
- 新的 phase-plane production action；
- `BPM|SSNP|MBS` runtime selector 或自动 fallback；
- project-owned optimizer/loss/history runtime；
- Wave↔Ray converter 或统一 Optical State；
- distributed Workstation 抽象、DTensor adapter 或 distributed-FFT interface；
- 为多卡夹带 mixed precision，或为性能放宽 Fixed Double/error budget；
- 在没有两个真实 adapter 前建立 backend seam。

最稳健的“重上井冈山”不是大爆炸重构，而是按 SSR-E2 逐层扩大已封存科学基础：**先用已有能力产出真实问题，再为被问题证明的复杂度建立 deep module；每次只重开一个科学决定，每次都以独立 evidence 和停止条件收口。**

## 12. 一手来源清单与不确定项

### Chromatix

- Deb et al., [Chromatix: a differentiable, GPU-accelerated wave-optics library](https://doi.org/10.1038/s41592-026-03121-x), Nature Methods 23, 1388–1398 (2026)。
- [Chromatix polarization](https://chromatix.readthedocs.io/en/latest/polarization/)、[FAQ](https://chromatix.readthedocs.io/en/latest/FAQ/)、[OpticalSystem](https://chromatix.readthedocs.io/en/latest/api/systems/)、[CGH Example](https://chromatix.readthedocs.io/en/latest/examples/cgh/)。
- 固定源码：[samples.py](https://github.com/chromatix-team/chromatix/blob/ce1482906fc663298613bb252bbf425e3be59839/src/chromatix/functional/samples.py)、[rays.py](https://github.com/chromatix-team/chromatix/blob/ce1482906fc663298613bb252bbf425e3be59839/src/chromatix/functional/rays.py)。

### 厚样品与独立证据

- Feit & Fleck, [Light propagation in graded-index optical fibers](https://doi.org/10.1364/AO.17.003990), Applied Optics 17, 3990–3998 (1978)。
- Chowdhury et al., [High-resolution 3D refractive index microscopy of multiple-scattering samples from intensity images](https://doi.org/10.1364/OPTICA.6.001211), Optica 6, 1211–1219 (2019)；[作者代码](https://github.com/Waller-Lab/multi-slice)。
- Zhu et al./相关 SSNP 线：[High-fidelity optical diffraction tomography of multiple scattering samples](https://doi.org/10.1038/s41377-019-0195-1)；[SSNP-IDT 作者代码](https://github.com/bu-cisl/SSNP-IDT)。
- Mu et al., [Multislice computational model for birefringent scattering](https://doi.org/10.1364/OPTICA.472077), Optica 10, 81–89 (2023)。
- [Meep FDTD](https://meep.readthedocs.io/en/latest/Introduction/) 与 [adjoint solver](https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/)。

### DOE/D2NN

- Lin et al., [All-optical machine learning using diffractive deep neural networks](https://doi.org/10.1126/science.aat8084), Science 361, 1004–1008 (2018)。
- [LightRidge 官方文档](https://lightridge.github.io/lightridge/)、[D2NN training tutorial](https://lightridge.github.io/lightridge/tutorials/tutorial_01_d2nn_training.html)、[作者预印本](https://arxiv.org/abs/2306.11268)。

### PyTorch

- [torch.distributed 2.12](https://docs.pytorch.org/docs/2.12/distributed.html)、[DDP 2.12](https://docs.pytorch.org/docs/2.12/generated/torch.nn.parallel.DistributedDataParallel.html)、[FSDP 2.12](https://docs.pytorch.org/docs/2.12/fsdp.html)。
- [DTensor 2.12](https://docs.pytorch.org/docs/2.12/distributed.tensor.html)、[Tensor Parallel 2.12](https://docs.pytorch.org/docs/2.12/distributed.tensor.parallel.html)、[`torch.fft` 2.12](https://docs.pytorch.org/docs/2.12/fft.html)、[DTensor operator test source](https://github.com/pytorch/pytorch/blob/main/test/distributed/tensor/test_dtensor_ops.py)。
- [gradcheck 2.12](https://docs.pytorch.org/docs/2.12/generated/torch.autograd.gradcheck.gradcheck.html)、[activation checkpoint](https://docs.pytorch.org/docs/2.12/checkpoint.html)。

### 尚未解决的不确定项

- 上游 Chromatix 的论文 `0.4`、文档 `0.6.0` 与 main 固定 SHA 不是同一快照；比较时必须继续逐事实固定版本。
- 没有找到可确认由 2018 Science 原始 Ozcan 团队维护的正式公共训练仓库；本文把原论文作为模型来源，把 LightRidge 作为可信、但不同团队的官方框架实现。
- PyTorch DTensor/FFT 与 Windows distributed 支持持续变化；任何 implementation ticket 必须重新核验项目锁定版本，不能把本文链接当永久兼容保证。
- 本机没有 2+ GPU 和 native Linux 证据；所有 multi-GPU 性能、稳定性、数值一致性仍是 UNPROVEN。
- scalar multislice、tensor multislice、SSNP 与 Modified Born 的 applicability 不能仅靠论文名称决定；正式 spec 仍需根据目标样品的 NA、index contrast、anisotropy、backscatter 与 observable 预注册模型域。
