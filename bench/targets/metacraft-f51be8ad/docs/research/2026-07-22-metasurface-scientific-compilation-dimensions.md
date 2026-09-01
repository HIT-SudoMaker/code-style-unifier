---
record_type: research_record
date: 2026-07-22
status: proposed_architecture_input
authority_level: none
current_capability: false
---

# 超表面科学流程编译的正交关系研究

## 结论摘要

本记录的核心结论是：MetaCraft Next 不应继续把 `route` 当成一个同时容纳器件目标、相位机制、适用域、数值方法和 solver 产品的枚举。文献中的这些概念不是同一层级，且存在多对多关系。

1. **Aim 必须且只需命名器件类别。**MetaCraft 的规划语言采用四个清晰的 Aim：`metalens`、`frequency-selective surface`、`holographic metasurface` 与 `quasi-bic metasurface`。`focus`、`absorb`、`reconstruct field`、`target resonance` 和 `Q` 是与 Aim 关联的 Scientific Objective，不再充当 Aim 名称或字段值。
2. **传播相位与 Pancharatnam–Berry 相位是波前实现机制，不是所有器件 Aim 的共同主轴。**传播相位 metalens 由几何相关的复透射响应建立相位库；PB 元件由局部各向异性结构的方向控制几何相位，并天然绑定偏振转换。quasi-bic metasurface 与 frequency-selective surface 可以完全没有 aperture phase map；holographic metasurface 又可能需要 phase-only、amplitude-and-phase 或 polarization-multiplexed control。[Arbabi et al. 2015](https://www.nature.com/articles/ncomms8069)；[Bomzon et al. 2002](https://opg.optica.org/ol/abstract.cfm?uri=ol-27-13-1141)；[Overvig et al. 2019](https://www.nature.com/articles/s41377-019-0201-7)
3. **一个 Campaign 不只有一个 field model 或一个 solver。**当前低 NA metalens 已经同时需要 periodic unit-cell full-wave response、aperture construction 与 scalar finite-aperture propagation；未来 quasi-bic metasurface 往往同时需要 source-free eigenmode 与 driven spectrum；holographic metasurface 同时需要 inverse field synthesis、meta-atom response 和 image-plane reconstruction。因此 Field Regime、Numerical Model 与 capability 应绑定到 `Proof` 中的具体证据义务，而不是压成 Campaign 的一个全局标签。
4. **FDTD、RCWA/FMM、FEM、plane-wave eigensolver 是方法；Lumerical、COMSOL、S4、MPB 或 Python/Torch kernel 是实现。**Ansys 自己同时提供时域 FDTD 和 Fourier-layer RCWA；COMSOL 同一 Wave Optics 产品支持 frequency-domain、eigenfrequency 与 mode studies。产品名和数值方法显然不是同义词。[Ansys FDTD](https://optics.ansys.com/hc/en-us/articles/360034914633)；[Ansys RCWA](https://optics.ansys.com/hc/en-us/articles/4414575008787)；[COMSOL Wave Optics](https://www.comsol.com/wave-optics-module)
5. **科学编译应先产生能力和证据要求，再后置选择执行实现。**M3 的纯编译函数应描述“需要何种 observation、contract、依赖和 qualification”，而不写 Lumerical 命令；Python execution composition 再为每个 requirement 提出 qualified method/product/version/template/material Binding，Rust 只接纳其固定结构和生命周期关系。一个粗粒度 `solver = lumerical` 字段无法表达混合计算，也会把产品锁进科学语义。
6. 建议把顶层关系收敛为四个自然语言对象：**Aim、Route、Proof、Binding**。Scientific Objectives 是 Brief 中与 Aim 并列的事实，不膨胀为 Aim identity：

   ```text
   Brief -> Aim
         -> Scientific Objectives
   Aim + Scientific Objectives -> Route -> Proof -> Binding -> Evidence -> Result
   ```

   详细的 mechanism、control、field regime、numerical method、material 和 evaluation 不再平铺成十几个互相竞争的框架对象，而分别归入这四个关系中。`Proof` 在本记录中只是“完整证据义务”的候选关系名，不宣称科学真理，也不取代现有 `Scientific Task Graph`、`Evidence` 或 `Route Evaluation`；其最终名称仍需在 Language Standard 中收敛。
7. 本研究不扩大当前 capability。首个正式实现仍只包含 **single-wavelength、NA <= 0.5、Propagation-Phase metalens 与 Pancharatnam–Berry-Phase metalens**；frequency-selective surface、holographic metasurface 与 quasi-bic metasurface 目前只作为未来 Aim 被记录。
8. **Brief 不应要求用户先填写 compiler 应推导的 workflow 答案。**当前 `DesignBrief.workflow_intent` 已闭合为 `propagation_metalens | pb_metalens`，等于在 DeepSeek Advice 与 deterministic composition 之前预选 Route；这会阻止未来 Aim/Route 扩展。
9. **Route applicability 与 capability suitability 必须由 deterministic Python science composer 判断。**Rust 只验证 Proposal 的固定结构、引用与生命周期前提。用户批准可以作为一项 lifecycle fact 被 Rust 接纳，但 Rust 不应重放任何 Aim 的科学规则、判断某个 solver 是否科学适用，或产生具有科学含义的 `RouteCapabilityMatch`。

## 研究边界与证据规则

本记录只使用：

- 当前仓库源码、Canonical Specification 与已接受 ADR，作为当前架构的一手证据；
- 原始或代表性研究论文，作为科学关系的一手证据；
- solver 官方文档，作为具体实现能力的一手证据。

本记录不是 ADR、Canonical Specification 或 qualification。它不激活 frequency-selective surface、holographic metasurface、quasi-bic metasurface、RCWA、COMSOL 或任何新 solver capability，也不改写现有 Rust/Python protocol。

当前必须保留的 Next 原则包括：四功能七模块的 ownership、M3 pure compile/evaluate、typed task graph、backend-neutral capability、M5 realization、M6 authority，以及 propagation/PB 两条不同 Evidence chain。其历史来源现仅作为 provenance 保留：`docs/metacraft_next/specs/foundation/ownership_architecture.md`、ADR 0029、ADR 0032、ADR 0033 与 ADR 0037；这些文档路径均已从当前工作树删除。

## 一、当前模型已经暴露的层级冲突

当前 successor code 把 `propagation_phase` 和 `pancharatnam_berry_phase` 作为 Route identifier，但两个 Compilation Input 都直接包含 `aperture_diameter_metre`、`focal_length_metre`、scalar numerical contract 与 focal metric contract；它们实际编译的是 **metalens via one phase mechanism**，不是可脱离目标独立存在的通用 phase route。历史源码 provenance 为已删除路径 `src/metacraft_next/scientific/routes/propagation_phase/compilation.py` 与 `src/metacraft_next/scientific/routes/pancharatnam_berry_phase/compilation.py`。

与此同时，尚未退休的 predecessor model 使用 `propagation_metalens` 与 `pb_metalens`。其历史源码 provenance 为已删除路径 `src/metacraft_next/scientific/models.py`。这不是简单的命名不统一，而是两个相反的折叠：

- successor 名称只说 mechanism，payload 却固定 Aim；
- predecessor 名称把 Aim 与 mechanism 粘成一个枚举值。

如果继续沿用同一扁平 `route` 轴，下一步很容易出现：

```text
metalens
frequency_selective_surface
holographic_metasurface
quasi_bic_metasurface
propagation_phase
low_na
lumerical_fdtd
```

这些值分别来自 mechanism、Aim、applicability、method 和 realization，彼此既不互斥，也不能替代。这样的枚举无法形成合法的组合规则，只能继续长出 switch 与 fixed workflow。

Brief 入口也提前折叠了相同答案。`DesignBrief` 声称要在 workflow/planner/Agent 解释前保存用户事实，却公开接受 closed `workflow_intent = propagation_metalens | pb_metalens`；其历史源码 provenance 为已删除路径 `src/metacraft_next/brief.py`。对于“设计一个低 NA metalens、材料为 Si、工作在某波长”这样的 Brief，Route 恰恰应由约束、偏振、capability 和用户选择在后续收敛；先填 workflow 会把 compiler 降成字段转换器。

现有 `GeometryFamilyRecommendation` 又原子捆绑 geometry definition、`solver_family`、solver geometry realization、template bundle、parameter mapping 与 qualification decision；其历史源码 provenance 为已删除路径 `src/metacraft_next/planning/brief.py`。这些事实并不同时变化：geometry/Route recommendation 是科学建议，method/product/template 是后置 execution binding，qualification 是 exact realization 的证据。把它们做成不可分 recommendation 会导致更换已安装 solver 时连科学 Route 一起变化，也无法表达一个 Route 同时使用 Lumerical periodic response 与 Torch finite-aperture kernel。

最后，历史 `canonical_workflow.md` 写作 `M3 DesignBriefAssessment -> M6 RouteCapabilityMatch -> optional M4 RouteRecommendation -> user-approved RouteSelection`，并让 M6 重放 scientific applicability、qualification 与 Release Profile。这与后来的 accepted decisions 已发生实质冲突：历史 ADR 0042 把 campaign action derivation 交回 Python，历史 ADR 0044 更明确规定 material validity、Candidate Domain membership 与 Route applicability 全部属于 Python science。三者的已删除 provenance 路径分别为 `docs/metacraft_next/specs/foundation/canonical_workflow.md`、`docs/adr/0042-derive-campaign-progression-in-python-and-admit-transitions-in-rust.md` 与 `docs/adr/0044-validate-registered-structure-in-rust-and-scientific-meaning-in-python.md`。该冲突必须在后续 Canonical Specification 修订中原子解决；不能用 Python 新 composer 旁边再保留一个 Rust scientific match，形成双判断。

## 二、四类科学对象在文献中的真实位置

### 1. metalens：Aim 是聚焦，phase mechanism 只是实现路径

metalens 的目标是把给定输入场变换为指定焦域场。高对比 transmitarray 的原始工作明确区分：一类结构通过传播/低 Q 响应积累相位，另一类结构把局部 half-wave plate 旋转并以 PB phase 工作；二者都可以服务 lens Aim。[Arbabi et al. 2015](https://www.nature.com/articles/ncomms8069)

因此 metalens 的共同部分是：

- focal geometry 与 illumination；
- aperture response assignment；
- finite-aperture field evaluation；
- focal metric contract。

传播相位与 PB 相位不同的是局部 response/evidence：

- Propagation：geometry sweep -> complex transmission -> phase-state library；
- PB：full Jones anchor -> circular-basis conversion -> empirical rotation -> converted/leakage libraries。

PB 原始工作通过改变 subwavelength grating 的局部 orientation 构造期望 phase element；它不是“给任意结构贴一个 phase-mode flag”。[Bomzon et al. 2002](https://opg.optica.org/ol/abstract.cfm?uri=ol-27-13-1141)

### 2. quasi-bic metasurface：Aim 是可观测的有限 Q 器件，Route 再说明其 BIC 来源

MetaCraft 将 `quasi-bic metasurface` 作为未来器件 Aim：目标是设计出具有可观测有限 Q 的 quasi-BIC 特性的超表面，并围绕其目标共振与品质因数评价。Hsu 等人观测到 patterned dielectric slab 中的 embedded eigenvalue：开放辐射通道存在，但辐射幅度通过干涉同时消失。[Hsu et al. 2013](https://www.nature.com/articles/nature12289) Koshelev 等人进一步表明，破缺面内对称性的 meta-atoms 可以把 symmetry-protected BIC 扰动成 sharp high-Q/Fano resonance。[Koshelev et al. 2018](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.121.193903)；[Supplement](https://journals.aps.org/prl/supplemental/10.1103/PhysRevLett.121.193903/supplemental_final.pdf)

由此得到的架构含义是：

- `quasi-bic metasurface` 属于 Aim/device family；`symmetry-protected BIC`、`accidental BIC` 或受控对称破缺才属于 Route mechanism；
- Brief 至少应记录 Spectral Operating Scope、Target Resonance、quasi-BIC 意图、明确口径的 Quality-Factor Objective，以及入射角、偏振等工作条件；这些是未来需求事实，不在本记录中展开为 schema 或实现；
- Spectral Operating Scope、Target Resonance 与 resonance linewidth 不可混成一个“工作频段”字段：前者是研究适用区间，中者是期望共振位置，后者才参与 Q 与可观测带宽评价；
- 理想 BIC 与可由外场激发的 quasi-BIC 不能混称；前者在理想无限、无损模型下讨论辐射解耦，实际器件通常需要声明有限泄漏、材料损耗和可观测 Q 的口径；
- symmetry class、Bloch wave vector、radiation channel、asymmetry parameter、material loss 和 finite-array effects 是 applicability/control facts；
- eigenfrequency、complex frequency/Q、mode field/symmetry 与 driven spectral line shape 是不同 Evidence，不能被一个“phase coverage”指标代替；
- eigenmode calculation 与 driven scattering calculation 可以由不同 method/realization 完成，因此不能先选一个全局 solver 再让它定义科学流程。

### 3. frequency-selective surface：Aim 是器件类别，吸收只是一个 Objective

`frequency-selective surface` 是更稳定的器件 Aim，因为它允许在声明频段内分别提出 transmission、reflection、band-pass、band-stop 或 absorption Objective。`Absorber Metasurface` 不能与它互换：吸收是可能的谱响应目标，不是整个器件家族的唯一含义。已有原始工作同时展示了频率选择透射与完美吸收，也展示了吸收带两侧或中间保留透射窗口的 FSS，说明这些响应应当作为可组合 Objective，而不是不同层级混用的 Aim。[Asadchy et al. 2015](https://journals.aps.org/prx/abstract/10.1103/PhysRevX.5.031005)；[Guo et al. 2019](https://doi.org/10.1109/ACCESS.2019.2927658)

Landy 等人的原始 perfect absorber 以电、磁共振同时耦合，并通过 impedance matching 降低反射，在单层结构中获得近单位 absorbance；它可作为 frequency-selective surface 的 absorption Objective 参考，而不是把 `absorb` 重新升格为 Aim。[Landy et al. 2008](https://harvest.aps.org/v2/journals/articles/10.1103/PhysRevLett.100.207402/fulltext)

因此 frequency-selective surface 可以有多种 Scientific Objective 与 Route：

- electric/magnetic resonance + impedance matching；
- cavity or guided resonance + critical coupling；
- quasi-BIC radiation control + material loss；
- broadband/multiresonant or angle-selective variants。

当 Objective 是 absorption 时，最小 Proof 一般要求 complex S-parameters 或 power flux、`A = 1 - R - T` 的 normalization、material loss/dissipation、spectral bandwidth，以及 request 指定的 angle/polarization robustness。Ansys 官方把 S-parameters定义为 complex amplitude reflection/transmission coefficients，并在 RCWA 中分别返回 grating-order reflection/transmission 与内部 fields；这些 observation 仍需 route-owned evaluation 才能成为 absorption 结论。[Ansys S-parameter extraction](https://optics.ansys.com/hc/en-us/articles/360042095873-Metamaterial-S-parameter-extraction)；[Ansys RCWA](https://optics.ansys.com/hc/en-us/articles/4414575008787)

### 4. holographic metasurface：Aim 是重建目标场，而非必然“PB”

Ni 等人的 visible metasurface hologram先把虚拟物体在 image plane 的复场映射到 metasurface plane，再用离散 amplitude/phase states 实现，并以 reconstructed image、noise 和 efficiency 评价；其 unit cells 用 full-wave FEM 设计。[Ni et al. 2013](https://www.nature.com/articles/ncomms3807)

Zheng 等人的高效率 hologram 使用 geometric phase 与 circular-polarization conversion，证明 PB 是一种实现 Route，而不是 hologram 的定义。[Zheng et al. 2015](https://www.nature.com/articles/nnano.2015.2) Overvig 等人又用 form birefringence 与 orientation 分别控制 amplitude 和 phase，说明 `phase-only` 与 `complex-amplitude` 是不同 control policy，而不是所有 hologram 都共享一个 phase-state library。[Overvig et al. 2019](https://www.nature.com/articles/s41377-019-0201-7)

因此 holography 至少分为：target field synthesis、meta-atom encoding、finite-aperture reconstruction、image evaluation 四类 proof；其中 inverse synthesis algorithm、full-wave response method 与 reconstruction kernel 可以分别绑定。

## 三、推荐的顶层关系：Aim / Route / Proof / Binding

### 1. Aim：我们要设计哪一种器件

`Aim` 只命名器件家族。Scientific Objectives、适用条件、约束与预算是 Design Brief 中与 Aim 关联的独立事实，不进入 Aim identity：

```text
Aim
  device_family: metalens | frequency_selective_surface
               | holographic_metasurface | quasi_bic_metasurface
Related Brief facts
  scientific objectives and acceptance criteria
  excitation and output channels
  spatial / spectral / angular / polarization scope
  preserved user constraints and budget
```

当前正式范围只接受 low-NA single-wavelength `metalens`。`frequency-selective surface`、`holographic metasurface` 与 `quasi-bic metasurface` 目前只是规划语言；它们不注册未来 capability。`focus`、spectral response、field reconstruction、Target Resonance 与 Quality-Factor Objective 都是与各自 Aim 关联的 Scientific Objective，不属于 Aim identity。

### 2. Route：用什么物理路径抵达 Aim

`Route` 是拥有独立 Evidence topology 的科学路径，保留 ADR 0033 的 peer pure `compile` / `evaluate`，但其身份由 **Aim + mechanism + evidence topology** 共同限定，而不是只由一个 phase label 决定：

```text
Route
  serves Aim
  uses Physical Mechanism
  applies Wave-Control Strategy when one exists
  declares Applicability
  compiles one Evidence topology
```

示例自然语言：

- `metalens through propagation phase`
- `metalens through Pancharatnam–Berry phase`
- `frequency-selective surface through critical coupling`
- `quasi-bic metasurface through perturbed symmetry-protected BIC`
- `holographic metasurface through complex-amplitude geometric phase`

序列化 identity 可以是稳定 compound key，但公共 Python 不必把整句做成长 class 名。模块上下文给出 Aim，peer package 给出 Route；不能再让 `propagation_phase` 在类型上假装对 focal length 一无所知。

### 3. Proof：要相信结果，必须看见什么

`Proof` 是本记录对“Route 编译出的完整证据合同”的工作名，而不是一份预写 execution workflow：

```text
Proof
  required capabilities
  typed observations
  dependency edges
  scientific / numerical contracts
  convergence and applicability checks
  evaluation contract
  admissible Evidence closure
```

关键点是 Field Regime 和 Numerical Model 挂在每个 proof obligation/task 上：

- metalens unit-cell response 可以要求 periodic vector Maxwell response；
- 同一 metalens 的 system evaluation 可以要求 low-NA scalar angular spectrum；
- BIC 可以同时要求 open-boundary eigenmode 与 driven scattering；
- hologram synthesis 可以是 iterative Fourier transform，而 unit-cell validation 是 FEM/FDTD/RCWA。

这样既保留 typed task graph，也避免虚构“整个 Campaign 只有一个 field model”。

### 4. Binding：这台机器具体如何实现 Proof

`Binding` 把一个 required capability 后置映射到 qualified execution：

```text
Binding
  realizes one capability
  numerical method
  product / adapter / version
  template and geometry mapping
  material binding
  resource and device policy
  exact qualification references
```

它是逐 requirement 的多值映射，不是 Campaign 的单个 `solver` 字段。例如当前 metalens 可以把 periodic response 绑定到 Lumerical FDTD，把 scalar aperture propagation 绑定到 Python/Torch；二者仍属于一个 Route Proof。

## 四、详细维度应放在哪里

| 维度 | 正确归属 | 例子 | 不应混成 |
| --- | --- | --- | --- |
| Device Aim | Aim | metalens、frequency-selective surface、holographic metasurface、quasi-bic metasurface | performance action、phase mode、solver |
| Scientific Objective | Brief facts associated with Aim | focus、spectral transmission/reflection/absorption、field reconstruction、Target Resonance/Q | device family、method |
| Physical Mechanism | Route | propagation phase、geometric phase、BIC interference、critical coupling | product |
| Control Strategy | Route | phase library、orientation、symmetry breaking、complex amplitude、impedance tuning | universal required phase field |
| Applicability / Field Regime | Aim + Proof task | single wavelength、low NA、scalar aperture、vector periodic cell、coherent illumination | Route identity by itself |
| Numerical Model | Proof task | driven scattering、eigenproblem、angular spectrum、inverse Fourier synthesis | solver product |
| Required Capability | Proof task | periodic complex response、full Jones、open eigenmode/Q、S-spectrum、finite-aperture field | installed application name |
| Method | Binding | FDTD、RCWA/FMM、FEM、plane-wave eigensolver | Lumerical/COMSOL |
| Realization | Binding | Lumerical FDTD adapter、COMSOL eigenfrequency adapter、Torch kernel | physical mechanism |
| Material Source | Brief facts / M2 | user table、refractiveindex.info record、solver-native identity | portable solver-independent material when native |
| Evaluation Contract | Proof | focal metrics、Q/Fano、absorbance/bandwidth、image fidelity | Rust Decision |
| Evidence dependency | Proof | anchor before rotation、eigenmode before BIC claim、field before image metric | list order or fixed workflow state |
| Qualification | Binding + Evidence admission | exact method/product/build/template/material/device | trusted boolean from Python |

## 五、四类 Route 的 Evidence topology 对照

| Aim / Route | 典型 control | 必需的早期 Evidence | 系统级 Evidence | 典型评价 | 不成立的替代 |
| --- | --- | --- | --- | --- | --- |
| Low-NA metalens / propagation phase | geometry-dependent quantized phase library | periodic complex transmission sweep、fabrication facts、phase-library construction | finite aperture -> scalar field -> focal metrics | focal position、FWHM、efficiency、convergence | 只看 phase coverage；全器件 FDTD 作为当前必选 |
| Low-NA metalens / PB phase | orientation + circular conversion | full Jones anchor、basis transform、anchor selection、empirical rotation、converted/leakage libraries | channel-separated aperture -> scalar fields -> focal metrics | converted focus、leakage focus、ratio、convergence | 只套理想 `2 theta`；把 leakage 合并后再评分 |
| Future quasi-bic metasurface / perturbed BIC mechanism | symmetry, interference, controlled leakage | Spectral Operating Scope、Target Resonance、periodic geometry/symmetry、Bloch/eigenmode、complex frequency or Q、field/radiation-channel observations | driven spectrum/Fano response、loss and finite-size checks when claimed | target resonance、declared Q quantity、linewidth、mode/symmetry consistency | phase-state library；仅一个 sharp spectral dip 就宣称 quasi-BIC |
| Future frequency-selective surface / absorption Objective | impedance/coupling/resonance tuning | complex S or flux normalization、material loss、geometry and boundary | absorption spectrum、dissipation distribution、angle/polarization sweep | peak A、bandwidth、robustness、critical-coupling condition when claimed | focal FWHM；只看 `R` 很小而未检查 `T` |
| Future holographic metasurface | phase-only、complex amplitude 或 multiplexed control | target field synthesis、encoding library、channel/polarization facts | finite-aperture reconstruction at declared image planes | field/image fidelity、diffraction efficiency、noise/crosstalk | 单一 focal metric；把 PB 当作唯一 hologram mechanism |

前两行是当前 scope，并与 ADR 0037 的独立 Evidence chain 一致。后三行只是扩展性试验，不是 implementation plan。

## 六、Method 与 Product 必须是多对多关系

官方资料已经足以否定 `solver_identifier == numerical_method_identifier`：

- Ansys FDTD 在离散空间与时间网格上直接求解 Maxwell curl equations，并可通过 Fourier transform 得到频域响应。[Ansys FDTD solver introduction](https://optics.ansys.com/hc/en-us/articles/360034914633)
- Ansys RCWA 把 multilayer periodic geometry 沿传播方向分层，在每层 Fourier domain 求解并组合 S-matrix；它适合 plane-wave 入射的 layered periodic structure，不能因此替代任意 finite aperiodic aperture。[Ansys RCWA solver introduction](https://optics.ansys.com/hc/en-us/articles/4414575008787)
- S4 是 RCWA/Fourier modal method 的另一具体 realization，证明同一 method 可由不同产品实现。[Liu & Fan 2012](https://doi.org/10.1016/j.cpc.2012.04.026)
- Johnson 与 Joannopoulos 的 plane-wave block-iterative eigensolver计算 periodic dielectric structures 的 Maxwell eigenstates，适合 band/eigenmode proof；它不是 driven FDTD 的别名。[Johnson & Joannopoulos 2001](https://doi.org/10.1364/OE.8.000173)
- COMSOL Wave Optics 同一产品提供 frequency-domain、eigenfrequency 与 mode analysis；其 periodic-structure 官方说明也明确区分 driven transmission/reflection/absorption 与 source-free eigenfrequency/band-structure studies。[COMSOL Wave Optics](https://www.comsol.com/wave-optics-module)；[COMSOL periodic structures](https://doc.comsol.com/6.3/doc/com.comsol.help.woptics/woptics_ug_modeling.5.10.html)

因此正确关系是：

```text
Proof requirement
  -> Required Capability
  -> qualified Method
  -> qualified Realization
  -> exact Material Binding
  -> Evidence
```

编译器可以接受多个 eligible bindings；选择必须服从 capability、qualification、budget 与用户允许项。不能因为本机装有 Lumerical 就先选 Lumerical，再倒推 Brief 应该如何研究。

## 七、材料关系不能藏进 solver choice

Material Source、portable Material Record 与 solver Material Binding 是三个不同事实：

1. user TXT/CSV 与 refractiveindex.info-derived records 可以形成 portable M2 material data；
2. 每个 numerical method/realization 需要自己的 interpolation、dispersion、anisotropy、loss 与 readback contract；
3. solver-native material identity 只在对应 realization 内有效，不能冒充 portable material；
4. material coverage、passivity、working wavelength 与 fabrication role 是 Aim/Route applicability；成功写入 vendor library 是 Binding qualification，不是科学评价。

当前项目只允许 user table、refractiveindex.info-derived data 与 qualified Lumerical-native material，并继续排除 CST runtime/material code。这一结论与已有一手调研一致。[Lumerical material import Research Record](2026-07-12-lumerical-fdtd-refractiveindex-material-import.md)

## 八、建议的科学编译顺序

该顺序组织关系，而不预写 workflow branch：

```text
1. Preserve Brief
2. Assess Aim, applicability and missing facts deterministically in Python
3. Ask AI for separable declarative Advice over registered options
4. Compose and present registered Aim/Route candidates in Python
5. Record explicit user selection when the policy requires it
6. Compile the selected Route into Proof requirements and Candidate Domain
7. Match each Proof need to available qualified capabilities in Python
8. Bind each capability to method/product/template/material late
9. Compile the next immutable graph revision from admitted Evidence
10. Run permitted tasks in Python workers
11. Evaluate the complete Evidence closure in the Route evaluator
12. Propose Result/Claim; Rust decides lifecycle admission only
```

这里 DeepSeek 只能：

- 解释 Brief；
- 给出候选 Aim/Route 排序；
- 指出缺失事实、风险和 trade-off；
- 在 registered vocabulary 内建议材料、method 或 sampling policy。

Advice 必须可拆分：Route advice、material advice、method advice 和 realization advice 各自携带理由与缺失事实，不能再返回一个把 geometry + solver + template + qualification 锁死的推荐元组。

DeepSeek 不能创造 route identifier、宣称 capability matched、绑定未资格化 solver、生成权威 Evidence 或替代 deterministic compiler。相同 Brief、selected Aim/Route、registered rules 与 admitted Evidence 必须得到确定性的 Proof/graph；AI response 变化不应偷偷改变已选择的科学合同。

## 九、组合约束与失败关闭

以下约束应由未来 M3 relationship model/registered rules 表达，而不是写入 Rust：

- `phase_strategy` 是 optional discriminated union；quasi-bic metasurface 或 frequency-selective surface Route 没有 phase map 是合法状态，不得填 `none` 后仍执行 phase-library workflow。
- `low_na` / `high_na` 是 applicability，不是 Route。当前 `NA <= 0.5` 只允许 scalar finite-aperture evaluation；超域必须 capability mismatch。
- 一个 Proof 可以要求多个 Field Regime 和多个 Method；只有各 task 的 exact contract/qualification 全部闭合，Route 才能 evaluate。
- RCWA binding 需要 layered periodic geometry 与 supported source/material conditions；finite aperiodic hologram/metalens aperture 不能因为 unit cell 使用 RCWA 就被称为“RCWA full-device proof”。
- quasi-bic metasurface claim 需要 route-defined eigenmode/radiation/symmetry closure，并明确 Spectral Operating Scope、Target Resonance 与所使用的 Q 口径；普通 resonance dip、有限 Q 或 Fano line shape 本身不自动等于 quasi-BIC。
- frequency-selective surface 的 absorption Objective 必须闭合 R、T、normalization 和 loss；ground plane 可使 T 近零，但不能省略 transmission/boundary proof。
- Hologram evaluation 必须绑定 declared target plane、complex-field/intensity convention、normalization、efficiency window 与 channel；漂亮图片不是可重放 metric。
- PB Route 必须保留 converted/leakage channel 与 handedness；传播相位 Route 不能借用 PB orientation semantics。
- solver-native material 只能与同 solver realization 一起绑定；adapter/version/material readback 任一变化都使旧 qualification 不再命中。
- unsupported combination 返回 explicit finding；不得回退到 nearest workflow、默认 solver 或默认 material。

## 十、对 Rust/Python 边界的直接含义

本关系模型使 Rust 更小，而不是更懂科学：

### Rust 继续只看

- opaque Reference 与 canonical bytes；
- Proposal / Decision、Permit / Receipt、Open / Closed、Current / Superseded；
- schema identity、reference closure、Revision、capacity、atomic commit、replay；
- `Proof`、`Binding`、`Evidence` 的通用结构关系，而不解释其中的 scientific tags。

Rust 可以接纳“用户在某 Revision 选择了某个 exact Route proposal”这一 lifecycle fact，但不判断该 Route 是否适用于 metalens/BIC、required capability 是否足够、某 solver 是否适合该 numerical model，或 qualification 的科学含义是否成立。换言之，Rust 的 `Decision` 是 protocol admission，不是 `RouteCapabilityMatch` 的科学结论。

### Python 拥有并可后组织

- Aim registry 与 deterministic Brief assessment；
- deterministic Route applicability、Proof-need/capability matching 与 selection proposal composition；
- Route peer packages 与 pure compile/evaluate；
- mechanism/control/applicability rules；
- typed Proof/task/observation/evaluation contracts；
- method/product binding；
- materials、sampling、worker scheduling、solver adapters、numerical kernels；
- DeepSeek Advice 与 Result composition。

加入 `frequency-selective surface through critical coupling`、`holographic metasurface through geometric phase` 或 `quasi-bic metasurface` Route 时，应该只增加 Python data/types/functions、schemas-as-data、qualification Evidence 与 release selection；Rust source diff 和 native binary hash都应为零。

## 十一、对现有 ADR 0029 的精确修正方向

ADR 0029 提出的 Route、Field Model、Phase Implementation Policy、Evaluation Kernel 正交化方向是正确的，但未来规范不宜把它们都理解为 Campaign 顶层的单值 axis：

- `Phase Implementation Policy` 应推广为 Route 下的 optional `Control Strategy`；phase library 只是其一个 variant；
- `Field Model` 与 `Numerical Model` 应允许按 Proof task 声明，因为 unit-cell、system propagation、eigenmode、inverse synthesis 的模型不同；
- `Evaluation Kernel` 应属于 Proof/evaluation contract，不应等同于 execution solver；
- `Route` 继续由独立 Evidence topology 定义，但 identity 必须看得见 Aim，不能只有 `propagation_phase` 这种 mechanism-only 名称。

这不是推翻 ADR 0033。相反，它让 peer pure compiler/evaluator 的边界更深：每个 Route package负责一条完整、可解释的证据路径，shared code 只承载真正相同的数学 contracts。

## 十二、当前收敛建议

本研究建议后续语言/spec 讨论先冻结以下关系，不立即写代码：

1. 接受 `Brief -> Aim -> Route -> Proof -> Binding -> Evidence -> Result` 作为 Python 科学心智链；
2. 决定当前两个 Route 的稳定 identity 是 compound key，还是 Aim package 下的简短 peer name；无论哪种，都必须消除名称只说 phase、payload 却固定 metalens 的冲突；
3. 让 Brief 只保存 Aim、operating conditions、constraints、allowed capabilities 与 budget，不再要求用户预填 `workflow_intent`；
4. 把 Advice 拆成可独立审阅的 Route/material/method/realization suggestions，不再捆绑 Geometry + solver + template + qualification；
5. 把 deterministic Route applicability 与 capability-need matching 固定为 Python 责任；Rust只接纳选择与绑定 Proposal 的结构/lifecycle；
6. 把 phase-specific policy 收入 optional Control Strategy，不再作为全产品必填轴；
7. 把 Required Capability、Method、Realization 三层固定为不同类型；
8. 把 Field/Numerical Model 绑定到 Proof task，而不是假定 Campaign 单值；
9. 继续完整实现当前两条 low-NA metalens Evidence chain；
10. 用 frequency-selective surface、holographic metasurface 与 quasi-bic metasurface 的 golden relationship fixtures 验证“新增科学零 Rust diff”，但不实现它们的 solver code。

在这十项语言关系接受前，不宜冻结新的 Rust/Python wire field，也不宜把当前 `route_identifier` 直接扩展为更多 device labels。否则只是把当前冲突固化进长期协议。

## 一手来源索引

### 科学论文

1. Arbabi et al., “Subwavelength-thick lenses with high numerical apertures and large efficiency based on high-contrast transmitarrays,” *Nature Communications* 6, 7069 (2015). [Publisher](https://www.nature.com/articles/ncomms8069)
2. Bomzon et al., “Space-variant Pancharatnam–Berry phase optical elements with computer-generated subwavelength gratings,” *Optics Letters* 27, 1141–1143 (2002). [Publisher](https://opg.optica.org/ol/abstract.cfm?uri=ol-27-13-1141)
3. Hsu et al., “Observation of trapped light within the radiation continuum,” *Nature* 499, 188–191 (2013). [Publisher](https://www.nature.com/articles/nature12289)
4. Koshelev et al., “Asymmetric Metasurfaces with High-Q Resonances Governed by Bound States in the Continuum,” *Physical Review Letters* 121, 193903 (2018). [Publisher](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.121.193903)；[Supplement](https://journals.aps.org/prl/supplemental/10.1103/PhysRevLett.121.193903/supplemental_final.pdf)
5. Landy et al., “Perfect Metamaterial Absorber,” *Physical Review Letters* 100, 207402 (2008). [APS full text](https://harvest.aps.org/v2/journals/articles/10.1103/PhysRevLett.100.207402/fulltext)
6. Asadchy et al., “Broadband Reflectionless Metasheets: Frequency-Selective Transmission and Perfect Absorption,” *Physical Review X* 5, 031005 (2015). [Publisher](https://journals.aps.org/prx/abstract/10.1103/PhysRevX.5.031005)
7. Guo et al., “Absorptive/Transmissive Frequency Selective Surface With Wide Absorption Band,” *IEEE Access* 7, 92314–92321 (2019). [Publisher](https://doi.org/10.1109/ACCESS.2019.2927658)
8. Ni, Kildishev & Shalaev, “Metasurface holograms for visible light,” *Nature Communications* 4, 2807 (2013). [Publisher](https://www.nature.com/articles/ncomms3807)
9. Zheng et al., “Metasurface holograms reaching 80% efficiency,” *Nature Nanotechnology* 10, 308–312 (2015). [Publisher](https://www.nature.com/articles/nnano.2015.2)
10. Overvig et al., “Dielectric metasurfaces for complete and independent control of the optical amplitude and phase,” *Light: Science & Applications* 8, 92 (2019). [Publisher](https://www.nature.com/articles/s41377-019-0201-7)
11. Liu & Fan, “S4: A free electromagnetic solver for layered periodic structures,” *Computer Physics Communications* 183, 2233–2244 (2012). [Publisher](https://doi.org/10.1016/j.cpc.2012.04.026)
12. Johnson & Joannopoulos, “Block-iterative frequency-domain methods for Maxwell's equations in a planewave basis,” *Optics Express* 8, 173–190 (2001). [Publisher](https://doi.org/10.1364/OE.8.000173)

### Solver 官方文档

1. Ansys, [Finite Difference Time Domain solver introduction](https://optics.ansys.com/hc/en-us/articles/360034914633)
2. Ansys, [RCWA Solver Introduction](https://optics.ansys.com/hc/en-us/articles/4414575008787)
3. Ansys, [Metamaterial S-parameter extraction](https://optics.ansys.com/hc/en-us/articles/360042095873-Metamaterial-S-parameter-extraction)
4. COMSOL, [Wave Optics Module](https://www.comsol.com/wave-optics-module)
5. COMSOL, [Modeling Periodic Structures](https://doc.comsol.com/6.3/doc/com.comsol.help.woptics/woptics_ug_modeling.5.10.html)
