---
record_type: research_record
date: 2026-08-08
status: research_finding
authority_level: none
current_capability: false
---

# 相位控制 brief 的物理判断框架：传播、几何与谐振

## 研究问题与裁决范围

本记录回答一个比“柱高取多少”更深的问题：MetaCraft 面向普通设计人员时，如何在
外部求解器启动前，对下列三类超表面作有物理依据、但不冒充全波证据的判断？

1. 以介质柱模态光程为主的传播相位单元；
2. 以旋转各向异性单元为主的局域 Pancharatnam–Berry（PB）几何相位单元；
3. 以局域共振、Huygens 响应或非局域 q-BIC 为主的谐振型单元，包括微波频段。

重点不是建立一个万能经验式，而是确定：

- 哪些条件可以作硬排除；
- 哪些数字只能作 forecast 或排序；
- 哪些结论必须等待 eigenmode、Jones、Floquet/S 参数或全波场证据；
- 哪些事实应由用户声明、程序推导、AI 建议或求解器建立；
- 非专业用户在何处应当停下、确认或升级证据。

本文只形成 Research Record，不修改 production code、ticket、ADR 或
[`CONTEXT.md`](../../CONTEXT.md)。系统决策仍应沿
`Research Record -> ADR -> specification -> ticket -> test` 落地。

## 结论先行

### 1. `effective index × height` 是传播相位的好量纲，不是通用判官

对一个由单一主导轴向模传播、界面项缓慢变化的柱单元，横向几何扫描带来的相对
传播相位可写成

```text
phase_span ≈ (2π / vacuum_wavelength)
             × height
             × effective_index_span .
```

一圈传播相位的量纲条件因此是

```text
height × effective_index_span / vacuum_wavelength ≳ 1 .
```

这个关系适合解释、粗排和选择预扫描高度。它不自动包含端面相位、Fabry–Pérot
干涉、模态交叉、周期邻居耦合、材料损耗或高 Q 共振。高对比 transmitarray 的
原始论文也把柱子描述为弱耦合、低 Q 的截断波导/谐振器，而不是均匀体材料薄膜。
[Arbabi et al., *Nature Communications* 6, 7069 (2015)](https://www.nature.com/articles/ncomms8069)

因此：

- 体材料折射率跨度可以给**传播贡献**一个乐观上界；
- 估算的有效折射率跨度只能形成 forecast 或候选排序；
- 最终的相位跨度、振幅与损耗必须来自周期复响应；
- 一旦设计有意利用共振相位，不能再用该式拒绝整个设计。

### 2. 普通 PB 单元判断的是 Jones 变换，不是柱高扫出 `2π`

对本征轴复透射系数为 `t_x`、`t_y` 的旋转各向异性单元，圆偏振基中的同手性与
反手性项分别正比于

```text
same-handed amplitude      = (t_x + t_y) / 2
opposite-handed amplitude  = (t_x - t_y) / 2 × exp(±i 2 orientation)
```

Yang 的原始论文直接给出这一 Jones 分解；`±2 × orientation` 只乘在转换手性
通道上。[Yang et al., *Nature Communications* 9, 4607 (2018), Eqs. 2–3](https://www.nature.com/articles/s41467-018-07056-6)

接近半波片时，`t_x ≈ -t_y`，同手性泄漏被抑制、反手性转换增强。若进一步把
本征通道近似为两段传播模，才得到软性的延迟量估算：

```text
retardance ≈ (2π / wavelength) × height
             × (effective_index_x - effective_index_y)

half-wave forecast: retardance ≈ π  (mod 2π) .
```

Khorasaninejad 的论文明确说明：高度、宽度和长度共同产生双折射，并用 FDTD
验证转换效率；532 nm 单元的 `95 × 250 × 600 nm` 与 `325 nm` 周期不是由一个
高度公式选出的。[Khorasaninejad et al., *Science* 352, 1190–1194 (2016)](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf)

所以 PB 高度不能继承传播相位的 full-`2π` 高度门槛。求解前最多检查旋转对称性、
偏振/输出通道与加工域；半波片质量必须由两个独立输入基的 Jones 或完整 Floquet
散射证据建立。

### 3. “几何相位”不能默认等于 `±2θ`

局域半波片 PB 单元常得到 `±2θ`，但相位系数和出现在哪个输出通道取决于散射
对称性、旋转对象和端口约定。非局域 q-BIC 实例中，dimerizing perturbation 的
方向 `α` 先控制可耦合偏振方向 `φ ≈ 2α`，谐振辐射的几何相位再成为
`Φ = 2φ ≈ 4α`；该响应只在窄带 q-BIC 附近出现。
[Malek et al., *Light: Science & Applications* 11, 246 (2022)](https://www.nature.com/articles/s41377-022-00905-6)

这意味着未来的 resonant geometric phase 不能只在现有 `geometric phase`
标签后复用普通 PB 规则。系统至少要先区分：

- 局域还是非局域响应；
- 旋转的是完整各向异性单元还是共振扰动；
- 目标是透射、反射、同手性还是转换手性通道；
- 相位在宽带存在，还是只在一个共振线宽内存在。

### 4. order ceiling 应按证据能力分流，而不是全局降级

开放非零 Floquet 阶次是运动学事实；它是否阻塞设计取决于下游声称使用了什么
响应：

```text
sampling ceiling
  -> 对声明依赖该空间采样方法的路线保持硬约束

order regime
  -> G0 coefficient 被当作完整输出：method refusal
  -> 所有开放 Floquet 通道、完整 S-matrix 或 sampled reference surface：caution
     + 必须升级响应证据
```

Ansys RCWA 官方文档把每个 propagating grating order 的复 S 参数、偏振与功率
分别返回；HFSS Floquet port 同样以 S-matrix 关联所有纳入的 Floquet modes。
[Ansys Optics RCWA](https://optics.ansys.com/hc/en-us/articles/12959229278611-RCWA-Solver-Simulation-Object)；
[Ansys HFSS Floquet Ports](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v252/en/Subsystems/HFSS/Content/HFSS/FloquetPorts.htm)

因此当前 [`ADR 0009`](../adr/0009-keep-g0-only-metalens-proofs-in-the-zeroth-order-domain.md)
与 [`ADR 0015`](../adr/0015-let-reference-surfaces-prove-their-own-response.md) 的对偶
语义应保留。Yang 的 paper period 超出 G0-only 适用域，不证明论文不可行；它
证明 G0 coefficient 不能承担完整输出。Khorasaninejad 的 high-NA reference-surface
路线则不应因为 order ceiling 被 AI 静默压低 period。

### 5. 当前最大的架构问题是 pre-brief circularity

当前 wording review 把 `control_strategy`、`atom_shape`、`aspect_limit`、
`dimension_step_nm` 等都列为必须由用户补齐的
`BriefFact`（cutover 前位于 `src/metacraft/science/wording.py`），同时 prompt 明令“只提问，
不得推断、修复或推荐缺失事实”
（cutover 前位于 `src/metacraft/advice/adviser.py`）。而 broad design advice 又只
接受已经完整构造的 `MetalensBrief`。

结果是：非专业用户必须先知道相位机制、meta-atom 形状和工艺数字，才能得到
本应帮助其选择这些内容的建议。这不是 brief 不够严格，而是建议出现得太晚。

修复方向不是让 AI 直接写 brief，而是在 immutable brief **之前**允许一次受约束
的科学询问与方案建议；用户确认后，选择才成为 brief 事实。此后仍严格保持

```text
immutable brief -> study -> evidence -> result .
```

AI 不获得修改 brief、制造 evidence 或绕开 deterministic validation 的权限。

## 一、三类物理机制需要三种判断语言

### 1.1 传播相位：光程 forecast 与周期响应必须分开

把单元传输写成

```text
t(geometry) = amplitude(geometry)
              × exp[i phase(geometry)]
```

若由一个主导模近似有限高柱，传播项约为

```text
phase_propagation ≈ k0 × effective_index × height .
```

但实际总相位还包含入射/出射界面、有限高度多次反射、模式耦合与参考面选择。
金属 V 天线的经典相位不连续工作已经证明：亚波长薄的 resonator array 可以通过
空间变化的散射相位形成波前，所需相位不是由厚度光程产生。
[Yu et al., *Science* 334, 333–337 (2011)](https://capasso.seas.harvard.edu/publications/light-propagation-phase-discontinuities-generalized-laws-reflection-and)

因此简单模型有四个不同等级：

1. **体材料跨度**：`height × (n_atom - n_ambient) / wavelength`。它只是在
   lossless propagation picture 内故意乐观的上界。
2. **孤立柱导模**：能改善量级判断，但不等于周期 Bloch 模；邻居改变介电分布与
   模态。[本仓库既有一手证据审计](2026-07-26-isolated-mode-versus-bloch-bound-direction.md)
   已说明其方向不足以支撑 hard refusal。
3. **周期 eigenmode/Bloch mode**：能给轴向传播常数，但仍不自动给有限高度
   复透射和端面相位。
4. **周期 complex response**：在明确 period、边界、材料、偏振与参考面下，才是
   cell library 的实际证据。

由此得到的安全规则是：

- 体材料上界失败，可以排除“该高度满足声明的非谐振传播相位方法”，不能排除
  “任何结构都不可能工作”；
- 估算根只排序，不裁决；
- 上界通过只表示 `not ruled out`；
- 只有周期 complex response 才能建立可用相位状态、传输和损耗。

### 1.2 局域 PB：先固定通道，再谈高度

局域 PB 单元的求解前判断顺序应当是：

```text
declared incident polarization
  -> declared output channel and handedness convention
  -> anisotropic cell whose rotation is physically distinct
  -> fabricable fixed geometry domain
  -> two-basis Jones evidence
  -> rotation law spot-check
  -> aperture orientation assignment .
```

可在求解前硬排除的典型情况包括：

- 纯 rotation-only PB 方案却选择连续旋转不改变结构的圆形/四重对称单元；
- brief 要求 polarization-insensitive output，却只允许一个单手性转换通道且没有
  另一机制补偿；
- 加工域内没有任何非退化的长短轴组合；
- 目标 orientation quantization 与声明的相位级数在代数上不可能对应。

不能在求解前硬判的内容包括：

- 半波片条件是否真正满足；
- 转换手性功率、同手性泄漏和吸收；
- `t_x`、`t_y` 的相对幅值和相位；
- 旋转后邻居间隙、近场耦合与大角度响应是否仍可接受。

Yang 的 Jones 公式还说明，AI 不应只说“几何相位覆盖 `2π`”，而应同时说明：
哪一个 incident spin、哪一个 output spin、相位符号和转换幅度来自什么证据。

### 1.3 谐振型与微波：高度只是几何变量之一

谐振型 metasurface 的相位可来自散射极点/零点、electric/magnetic resonance
配平、ground-backed reflection、局域 Mie resonance 或非局域 lattice mode。
这些机制不存在统一的 `index × height` 判据。

微波 Huygens surface 的实验工作以 electric 与 magnetic polarization currents
共同合成 reflectionless wavefront；其设计对象是表面响应，而不是一段等效介质
光程。[Pfeiffer and Grbic, *Physical Review Letters* 110, 197401 (2013)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.110.197401)

另一个 8–22 GHz 的 ground-backed N-shaped PB 单元使用 `5.2 mm` period；作者
对不同旋转角计算 co-polarized reflection，得到 `Δφ = ±2α`，并在
`9.5–18 GHz` 报告大于 `0.97` 的反射幅度。这里相位行为来自旋转后的 resonant
surface current 与反射通道，不来自 substrate thickness 的简单光程。
[Liu et al., *Scientific Reports* 7, 43543 (2017)](https://www.nature.com/articles/srep43543)

非局域 q-BIC 更进一步：mode 延伸跨越多个 unit cells，扰动强度控制
`Q ∝ 1/δ²`，空间扰动方向控制谐振辐射的几何相位。Malek 等还直接报告，小的
系统性孔径误差会让器件不同区域在不同频率共振，严重时单色光不能在整个 footprint
同时激发 q-BIC。[Malek et al. 2022](https://www.nature.com/articles/s41377-022-00905-6)

所以谐振型预判断必须至少问：

- 目标频段与允许带宽；
- transmission/reflection 与输入、输出端口；
- local resonance 还是 collective lattice resonance；
- 目标相位通道、幅度、偏振与容许泄漏；
- 导体、介质损耗和基底/ground stack；
- 入射角域、有限阵列尺寸和制造容差；
- 使用 specular response、全部 Floquet modes、supercell 还是 finite-aperture field。

LC、Mie 或 temporal coupled-mode model 可用于解释与拟合。Fan、Suh 与
Joannopoulos 的 temporal coupled-mode theory 本身描述的是 Fano resonator 的端口
耦合模型；只有在极点、线宽、direct pathway 和端口归一化由数据拟合或独立验证后，
它才可预测具体器件响应。
[Fan et al., *JOSA A* 20, 569–572 (2003)](https://opg.optica.org/josaa/abstract.cfm?URI=josaa-20-3-569)

## 二、硬排除、软预测与证据升级

| 判断 | 传播相位 | 局域 PB | 谐振/微波 | 允许的结论 |
| --- | --- | --- | --- | --- |
| 单位、正值、`f/NA/aperture` 几何矛盾 | 适用 | 适用 | 适用 | 硬停止，修 brief |
| 工艺 feature/gap/厚度域为空 | 适用 | 适用，且需 rotation-aware clearance | 适用，含层叠与导体厚度 | 硬方法拒绝 |
| sampling rule 被选定 method 明确要求且失败 | 适用 | 适用 | 仅当该 method 声明需要 | 硬方法拒绝，不宣称器件不可能 |
| 非零 Floquet order 运动学开放 | G0 complete-field 时硬拒 | 同左 | 同左 | 对 order-resolved/S-matrix/reference-surface 路线只 warning + 升级 |
| 体材料 optical-path upper bound 失败 | 只对非谐振 propagation contribution 有效 | 不适用 | 不适用 | 排除该传播高度/方法，不排除其他机制 |
| 有效折射率或双折射估计 | 候选排序 | retardance 排序 | 通常误导 | 永不单独 hard-refuse |
| rotation-group/Jones 代数矛盾 | 不适用 | 可硬排方法 | 对已声明对称性可硬排 selection rule | 只排除精确声明的方法/通道 |
| eigenmode / Bloch / resonance frequency | 辅助 | 辅助 | 必需的中层证据 | 未含端口散射时不能宣称效率 |
| 两基 Jones 或完整 Floquet S-matrix | periodic transmission 证据 | PB 必需 | resonant cell 必需 | 可筛 cell，仍不自动证明 aperture |
| angle/gradient/supercell response | 高 NA/快速变化时升级 | 高 NA/rotation coupling 时升级 | nonlocal/resonant array 通常必需 | 可建立 method applicability |
| sampled aperture/reference surface/full device | 最终场证据 | 最终场与偏振证据 | 有限阵列、feed 和边缘效应证据 | 才支持器件级结果 |

表中“硬”始终有作用域：`method inapplicable` 不等于 `aim impossible`。系统必须
保留这个差异，否则一个近似模型的失败会被误报成 Maxwell 方程下的不可能。

## 三、用户、程序、AI 与求解器的责任分配

### 3.1 用户应声明“想要什么”，不应被迫先解出“如何实现”

普通设计人员能够可靠声明的内容应优先成为 pre-brief 输入：

- aim 与使用场景；
- wavelength/frequency、bandwidth 和工作环境；
- incident side、polarization（含 unknown/any 的诚实状态）与角度范围；
- 目标输出：focus、beam direction、polarization、transmission/reflection、带宽与
  性能偏好；
- aperture、focal length、NA、系统尺度中其真正知道的项；
- 可用材料、基底、制造路线、最小 feature/gap、层数、总厚度或已有 process
  profile；
- 预算、solver 可用性、是否允许 optimization 和是否允许改变材料/机制。

用户不应被要求凭空给出有效折射率、Q、Floquet mode 数、Jones matrix、period、
height 或精确 aspect limit。若用户确实声明 period/height/geometry，它们仍是不可被
advice 覆盖的显式约束，符合 [`ADR 0008`](../adr/0008-honor-explicit-cell-constraints-before-advice.md)。

### 3.2 程序拥有所有可重复推导

确定性程序应独占：

- 单位与几何一致性；
- 从已确认材料/环境得到的 wavelength-specific material samples；
- 倒格矢、sampling 与开放 Floquet order 的运动学；
- fabrication grid、feature、gap、rotation envelope、candidate count 与成本；
- Jones/circular-basis 变换、phase wrapping、功率归一化与能量余额；
- 候选是否属于已限定 method 的 applicability domain；
- evidence request、引用、identity、重放与 stop reason。

确定性不等于硬编码一个经验答案。应硬编码的是公式、资格条件和证据语义；不同
波段/材料/工艺的经验范围应有来源、版本和适用条件。

### 3.3 AI 负责受约束的科学判断，不负责制造事实

AI 最适合做三件事：

1. 在 pre-brief 阶段把普通语言翻译为候选 mechanism hypotheses，并解释每个方案
   需要用户确认什么；
2. 在程序生成的合法 domain 内排序 period、height、cell family 与下一项 evidence；
3. 当 evidence 不足、模型相互冲突或预算不够时，选择最小升级路径并解释 trade-off。

AI 每次建议都应能区分：

```text
declared fact
derived fact
qualified evidence
forecast
assumption
unknown
requested next evidence .
```

AI 不得：

- 把 forecast 写成 evidence；
- 静默补齐材料、工艺、控制机制或输出通道；
- 越过 deterministic domain 推荐不存在的候选；
- 因自己“通常认为”某高度合适而 hard-refuse；
- 把 paper reference 反向泄漏给 blind benchmark advice；
- 在用户未确认时把建议写进 immutable brief。

### 3.4 求解器建立数值事实

求解器至少分别承担：

- **propagation**：周期复 transmission/reference-surface response，必要时 modal
  诊断；
- **local PB**：两个独立线偏振输入基的完整输出 Jones components，并在少数旋转
  角验证 amplitude invariance 与 phase law；
- **resonant/microwave**：frequency/angle sweep、全部相关 Floquet-port S 参数、
  resonance tracking、Q/linewidth、loss 和 energy balance；
- **nonlocal**：band/eigenmode 与 supercell/finite-patch response，不能用一个
  独立 unit-cell coefficient 代替 collective mode；
- **device**：aperture/reference-surface/full-device field 与 metric-specific
  evaluation。

无论使用 Lumerical、HFSS、CST 或其他产品，product qualification 只证明软件能
观察该响应；每个具体结果仍须绑定 exact geometry、materials、frequency、ports、
mesh/convergence 与 reference planes。

### 3.5 科学政策必须 caller-neutral

MetaCraft 的未来调用者可能是直接使用 Python 的设计人员、交互式应用，也可能是
Codex/Claude Code 一类受委托的 agent。调用表面可以不同，物理判断不能因此分叉：

- **agent/tool Adapter** 只负责把调用者输入、确认和结果搬过边界，不拥有材料、
  phase、order、fabrication 或 evidence 的含义；
- **external AI adviser provider** 只产生带 exact request/response identity 的不可信
  recommendation；它不是调用 Adapter，也不是 evidence source；
- **deterministic science** 对所有调用者形成同一 legal domain、grounds、stop reason
  与 evidence request；
- **确认权**属于 human user 或其预先明确授权的调用 policy。一个 AI adviser 不能
  把自己的 recommendation 再冒充用户确认；一个 agent 只有在调用授权明确包含该
  选择时才能采用它，否则必须返回待确认状态；
- **brief identity** 由最终被采纳的事实决定，不由 Python、CLI、agent 或某家模型
  的入口身份决定。

因此可靠性来自“同一科学内核、多个窄 Adapter”，而不是为 human、Python 与 agent
各写一套 heuristic。本文不裁决 MCP、CLI 或 agent protocol；它只要求未来这些
入口服从同一 evidence ladder 和 authority separation。

## 四、解决 pre-brief circularity 的心智顺序

本记录不提出代码 Interface，只给出应由后续 Wayfinder 裁决的责任顺序：

```text
natural-language intent
  -> deterministic extraction of explicit facts
  -> AI asks only consequential missing questions
  -> program presents legal mechanism/process alternatives
  -> AI recommends among those alternatives with reasons and evidence needs
  -> human or explicitly delegated caller accepts, rejects, or supplies another fact
  -> one immutable brief is formed

immutable brief
  -> study
  -> deterministic feasibility screens
  -> AI ranks only legal candidates / evidence requests
  -> solver observations
  -> admitted evidence
  -> result .
```

这条顺序保留现有 `brief -> study -> result`，但承认 brief 之前需要一次真正的
elicitation。该阶段的停止条件是“用户是否已确认会改变科学路线的选择”，不是“LLM
是否能猜到一个答案”。

应优先让用户确认的高影响选择包括：

- transmission 还是 reflection；
- output polarization/channel；
- broadband 还是 resonance-selected；
- 是否允许 polarization-dependent operation；
- fabrication process 或 registered process profile；
- 是否允许 multi-order evidence、supercell、full-device 或 optimization 成本。

period、height 的确切数字通常应晚于材料与 process facts，并由合法 domain、forecast
与证据共同决定。

## 五、面向非专家的 evidence ladder

### Level 0 — 意图与来源完整性

**输入：**自然语言、已知 process/material facts。
**动作：**区分 explicit fact、preference、omission 和 ambiguity。
**硬停止：**工作频段、目标输出或安全相关工艺事实互相矛盾；关键选择无法由用户确认。
**不得做：**AI 自行选择一个物理机制后假装用户已声明。

### Level 1 — 确定性可行域

**动作：**单位/系统几何、材料覆盖、fabrication arithmetic、sampling、Floquet-order
运动学、rotation clearance、candidate count。
**硬停止：**算术域为空；明确 method 的必要条件失败。
**升级：**存在另一 mechanism/response method 时，返回替代路线，不宣布 aim impossible。

### Level 2 — 零求解器 physics forecast

**propagation：**体材料光程上界和命名清楚的有效折射率 forecast。
**local PB：**retardance/birefringence 量纲、rotation/Jones algebra。
**resonant：**来源明确的 LC/Mie/TCMT 初值或 scaling hypothesis。
**允许输出：**rank、uncertainty、expected risk、下一项 evidence。
**硬停止：**只限经证明的必要条件；否则一律 `not ruled out` 或 `forecast insufficient`。

### Level 3 — 单元级资格

**propagation：**少量 height × lateral probes 的 complex periodic response。
**local PB：**two-basis Jones response、handedness conversion、frequency/angle margin。
**resonant：**eigenmode/band、frequency/angle S-matrix、Q/linewidth、loss 与 modal
identity。
**停止：**没有候选满足预先声明的 amplitude/phase/polarization/process targets。
**升级：**response 对 mesh、angle、period、rotation 或制造扰动敏感；证据未覆盖 brief band。

### Level 4 — 阶次、梯度与邻居

**动作：**所有开放 Floquet orders、gradient-aware supercell、phase origin、rotation
neighbors 或 finite patch。
**强制升级条件：**

- 非零阶次开放且下游需要完整场；
- 高 NA/快速相位梯度使 pointwise local periodic assumption 未被 qualification 覆盖；
- q-BIC/collective response；
- 单元旋转或几何变化显著移动 resonance；
- Level 3 与 forecast 的趋势相反。

### Level 5 — aperture field 与 device result

**动作：**从 exact admitted cell/surface evidence 形成 aperture field，随后用与输入语义
匹配的 vector propagation/full-wave method 评价。
**停止：**field provenance 不完整、reference surface/channel 不匹配或数值未收敛。
**结论：**只有该层才能支持 focus、efficiency、polarization purity、stray orders 或
finite-array claims。

### Level 6 — robustness / experimental closure

对高 Q、宽带、多角度、大口径或制造敏感设计，进一步执行 material/process
uncertainty、critical-dimension、sidewall、thickness、finite-feed 与 measurement
comparison。q-BIC 的原始实验说明小的系统性尺寸变化即可使 footprint 各区 resonance
失配，因此这不是可选的“美化测试”。[Malek et al. 2022](https://www.nature.com/articles/s41377-022-00905-6)

## 六、显式停止与升级规则

面向非专家时，系统不应只返回“成功/失败”，而应返回作用域明确的四种结论：

1. **brief needs confirmation**：缺少会改变机制、端口、材料或工艺的用户选择；
2. **method ruled out**：一个已命名方法的必要条件确定失败，并列出仍可能的替代方法；
3. **evidence required**：算术允许，但 forecast 不能裁决，明确下一项最小求解任务；
4. **candidate qualified for next level**：仅表示可以继续，不表示 device 成功。

以下情况不得靠 AI 自由裁量，必须升级证据：

- 候选位于任何 hard bound 或 process limit 附近，而输入不确定度足以跨越该界；
- effective-index、retardance、TCMT/LC 等两个 forecast 给出相反排序；
- 目标依赖高 Q、窄带、mode crossing 或 collective mode；
- order regime 为 multi order，而当前 observation 只含 G0；
- 需要输出完整偏振却只有一个输入基；
- 高 NA、斜入射或宽角度超出 method qualification；
- AI 无法引用 exact domain/evidence 来解释推荐；
- 所需 evidence 超出预算。最后一种应返回 honest waiting，不得降低证据标准。

## 七、四个 benchmark case 对框架的校验

四案不是四个答案，而是四种诊断。

| Case | paper platform | 简单高度判断 | 正确证据问题 | 当前 brief 启示 |
| --- | --- | --- | --- | --- |
| Yun 2025 | 850 nm, propagation, reported comparator height 800 nm, feature AR 10 | full-turn 量纲要求 `effective_index_span ≳ 1.06`；可能但不证明 | exact comparator period 尚未与同一 platform source-joined；需 complex library | `aspect_limit=10` 是用户给定的近论文 process intent；不能由 AI 改写 |
| Yang 2018 | 1550 nm, local PB, Si ellipse `1350×480×340 nm`, period 1500 nm | half-wave 量纲要求 modal birefringence 约 `1550/(2×340)=2.28`；高但需 Jones 验证 | `t_x≈-t_y`、conversion、完整 multi-order/reference field | wavelength-only `800/850/900 nm` prior 方向错误；order 问题是 response-method mismatch |
| Arbabi 2015 | 1550 nm, propagation, circular post height 940 nm, period 800 nm | 与当前 900 nm 同量级；光程可排序，不能替代 sweep | high-NA angle/gradient 与 complete field | current prior 差 40 nm 不是主要物理矛盾；应关注 method applicability |
| Khorasaninejad 2016 | 532 nm, local PB, TiO2 fin `95×250×600 nm`, period 325 nm | half-wave 量纲只需 modal birefringence 约 `0.443`；与 Yang 完全不同 | two-basis Jones、converted handedness、rotation-aware gap、high-NA field | height prior 恰含 600 nm；period 不应被 G0-only order preference 压到约 230 nm |

论文事实与 fabrication 推导详见既有
[四案 period/aspect audit](2026-08-06-four-case-period-aspect-ratio-audit.md)。以上
`effective_index_span` 和 modal birefringence 数字是由公开 wavelength/height 做的
**量纲反推**，不是论文报告的 modal index，也不能成为 benchmark threshold。

这张表反驳“柱子普遍偏低”的统一诊断：Yun 偏低、Arbabi 接近、K 正好、Yang 的
当前 prior 反而远高于论文。共同缺陷是 wavelength-only candidate policy 在机制进入
推理前先裁掉候选，而不是所有 case 需要一起增加高度。

## 八、对当前架构的研究性建议

### 8.1 保留的部分

- brief 一旦形成，继续作为 immutable user-approved facts；
- `phase envelope` 继续只作 one-way exclusion，不宣称 coverage；
- advice 继续不构成 evidence；
- sampling ceiling 与 order regime 分开；
- G0-only 与 reference-surface response 继续使用不同 order applicability；
- benchmark paper truth 继续只解释、不指导 blind advice，符合
  [`ADR 0020`](../adr/0020-let-benchmark-truth-explain-without-directing.md)。

### 8.2 必须深度调整的部分

1. **把 scientific elicitation 放到 immutable brief 之前。**当前 wording review
   只能指出缺失，broad advice 又要求完整 brief，形成循环。
2. **把机制问题拆成正交判断。**`propagation/geometric` 只描述相位编码还不够；
   future design 必须另外识别 local/nonlocal、resonant/nonresonant 与 response channel。
3. **深化 height candidate policy。**先依据 mechanism、spectral objective、material、
   process 与 budget 形成有来源的 candidate envelope，再运行对应 feasibility forecast。
4. **为 local PB 建立独立的 Jones/retardance grounds。**它与 propagation phase
   envelope 对偶，但不共用公式、不伪造统一 envelope。
5. **为 resonant methods 强制 evidence escalation。**未经 mode/S-parameter 扫描，
   LC、Mie、TCMT、几何 scaling 均只能排序。
6. **让 order caution 只有一个 owner。**period module 判定 order regime；下游只按
   response capability 将它映射为 refusal 或 caution，不重复发明含义。
7. **不要让一个 `aspect_limit` 同时代表 feature 与 gap。**Yun/K 的论文工艺已经
   证明 dry-etch feature、rotated clearance、resist-mold/ALD gap 不是一个数字。

### 8.3 AI prompt 应获得的 grounds，而不是自由发挥的背景知识

每次候选建议前，AI 应看到一个由程序形成的、可审计的 grounds packet，其内容至少
包括：

- immutable user facts 与 explicit omissions；
- 已确认 mechanism hypotheses 及各自 applicability；
- material/process provenance；
- deterministic legal candidates、ceilings、order regime 与 fabrication margins；
- forecast 数值及其证据等级；
- 已有 solver evidence 与缺口；
- 预算允许的下一层 evidence；
- 明令禁止声称的结论。

AI 的输出应解释“为什么推荐、依赖什么、仍未知什么、下一步证明什么”。程序只接纳
合法候选与注册的 evidence request；自然语言理由不改变事实。

## 九、建议 Wayfinder 下一阶段先裁决的一个 destination

本记录支持把 destination 定为：

> 形成一个 source-grounded 的 pre-brief scientific judgment policy，使普通设计人员
> 或受委托 agent 能在明确确认权下选择相位机制、响应方法与工艺语境；随后由 mechanism-specific
> feasibility screens、AI ranking 和逐级 solver evidence 共同确定 period/height，
> 同时保留 `brief -> study -> result` 与 route-dependent order semantics。

这个 destination 在可实施规格前至少还需要依次裁决：

1. 哪些内容是 user outcome facts，哪些是 user-approved design choices；
2. 哪些 fabrication facts 来自用户，哪些必须来自 registered process evidence；
3. control strategy 如何与 locality、resonance character 和 response channel 正交；
4. propagation、local PB、resonant local、resonant nonlocal 各自最小 grounds；
5. evidence ladder 的 exact stop/escalation vocabulary；
6. AI 建议必须携带哪些 grounds 与 unknowns；
7. 四个 benchmark 的 blind-brief scoring 如何只评价判断质量，而不泄漏 paper truth。

不建议现在直接实施一个新的 height formula。先决定责任与证据，再决定字段与代码；
否则只会把当前 wavelength-only heuristic 换成另一个更复杂、同样无资格的 heuristic。

## 十、仍未解决的科学问题

1. 现有一手来源没有给出跨横截面、跨周期、跨材料的 effective-index span 严格界；
   `n_atom - n_ambient` 只适合作为极宽的 propagation upper bound。
2. local PB 的 retardance forecast 是否足以稳定排序不同 height，仍需对现有四案及
   更多平台用 periodic Jones evidence 校准。
3. 没有跨平台通用的 Q、NA、period/wavelength 或 coupling 数值阈值，能自动区分
   local 与 nonlocal response。
4. q-BIC 的 `4α` 是特定 p2 perturbation/channel 的结果，不是 future resonant
   geometric phase 的通用常数。
5. 微波 conductor roughness、via/stackup、feed illumination、finite array 与 connector
   calibration 尚未进入 MetaCraft 当前材料/工艺语言；不能从光学 pillar brief 直接外推。
6. 当前 solver portfolio 是否能独立 qualify Floquet S-matrix、eigenmode/band 与
   finite-patch response，是 implementation planning 前必须另行盘点的能力事实。

## 一手来源与本地决策依据

### Primary scientific sources

1. A. Arbabi et al., “Subwavelength-thick lenses with high numerical apertures and large efficiency based on high-contrast transmitarrays,” *Nature Communications* 6, 7069 (2015). [Publisher](https://www.nature.com/articles/ncomms8069)
2. A. Arbabi et al., “Dielectric metasurfaces for complete control of phase and polarization with subwavelength spatial resolution and high transmission,” *Nature Nanotechnology* 10, 937–943 (2015). [DOI](https://doi.org/10.1038/nnano.2015.186)；[author manuscript](https://arxiv.org/abs/1411.1494)
3. Z. Yang et al., “Generalized Hartmann-Shack array of dielectric metalens sub-arrays for polarimetric beam profiling,” *Nature Communications* 9, 4607 (2018). [Publisher](https://www.nature.com/articles/s41467-018-07056-6)
4. M. Khorasaninejad et al., “Metalenses at visible wavelengths: Diffraction-limited focusing and subwavelength resolution imaging,” *Science* 352, 1190–1194 (2016). [Author-hosted article](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf)；[DOI](https://doi.org/10.1126/science.aaf6644)
5. N. Yu et al., “Light propagation with phase discontinuities: generalized laws of reflection and refraction,” *Science* 334, 333–337 (2011). [Capasso Group record and article](https://capasso.seas.harvard.edu/publications/light-propagation-phase-discontinuities-generalized-laws-reflection-and)
6. C. Pfeiffer and A. Grbic, “Metamaterial Huygens’ surfaces: tailoring wave fronts with reflectionless sheets,” *Physical Review Letters* 110, 197401 (2013). [APS](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.110.197401)
7. A. C. Overvig et al., “Selection rules for quasibound states in the continuum,” *Physical Review B* 102, 035434 (2020). [APS](https://doi.org/10.1103/PhysRevB.102.035434)
8. S. C. Malek et al., “Multifunctional resonant wavefront-shaping meta-optics based on multilayer and multi-perturbation nonlocal metasurfaces,” *Light: Science & Applications* 11, 246 (2022). [Publisher](https://www.nature.com/articles/s41377-022-00905-6)
9. X. Ouyang et al., “Ultra narrowband geometric-phase resonant metasurfaces,” *PNAS* 122, e2420830122 (2025). [PMC full record](https://pmc.ncbi.nlm.nih.gov/articles/PMC12012505/)；[DOI](https://doi.org/10.1073/pnas.2420830122)
10. S. Fan, W. Suh, and J. D. Joannopoulos, “Temporal coupled-mode theory for the Fano resonance in optical resonators,” *JOSA A* 20, 569–572 (2003). [Optica](https://opg.optica.org/josaa/abstract.cfm?URI=josaa-20-3-569)
11. X. Liu et al., “Wideband, wide-angle coding phase gradient metasurfaces based on Pancharatnam-Berry phase,” *Scientific Reports* 7, 43543 (2017). [Publisher](https://www.nature.com/articles/srep43543)
12. N. Byrnes and M. R. Foreman, “Symmetry constraints for vector scattering and transfer matrices containing evanescent components: Energy conservation, reciprocity, and time reversal,” *Physical Review Research* 3, 013129 (2021). [APS](https://journals.aps.org/prresearch/abstract/10.1103/PhysRevResearch.3.013129)

### Official solver sources

13. Ansys Optics, “RCWA Solver — Simulation Object.” [Official documentation](https://optics.ansys.com/hc/en-us/articles/12959229278611-RCWA-Solver-Simulation-Object)
14. Ansys Optics, “rcwa — Script command.” [Official documentation](https://optics.ansys.com/hc/en-us/articles/4414567929235-rcwa-Script-command)
15. Ansys HFSS, “Floquet Ports.” [Official documentation](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v252/en/Subsystems/HFSS/Content/HFSS/FloquetPorts.htm)
16. Ansys HFSS, “Floquet Port: Mode Setup.” [Official documentation](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v251/en/Subsystems/HFSS/Content/HFSS/FloquetPortModeSetup.htm)

### Local decision and evidence context

- [`CONTEXT.md`](../../CONTEXT.md): brief、phase envelope、height advice、feasibility screen、order regime、caution。
- [`ADR 0008`](../adr/0008-honor-explicit-cell-constraints-before-advice.md): explicit brief constraints precede advice。
- [`ADR 0009`](../adr/0009-keep-g0-only-metalens-proofs-in-the-zeroth-order-domain.md): G0-only response remains in zeroth-order domain。
- [`ADR 0013`](../adr/0013-let-each-periodic-response-prove-itself.md): transmission and polarization responses qualify independently。
- [`ADR 0015`](../adr/0015-let-reference-surfaces-prove-their-own-response.md): sampled reference surface is an independent response capability。
- [`ADR 0020`](../adr/0020-let-benchmark-truth-explain-without-directing.md): benchmark truth does not direct blind production science。
- [红外柱高一手资料调研](2026-07-16-infrared-metalens-nanopillar-height-primary-source-study.md)
- [phase-envelope roots 与认证边界](2026-07-26-phase-envelope-certified-roots.md)
- [孤立柱与周期 Bloch 模的界方向](2026-07-26-isolated-mode-versus-bloch-bound-direction.md)
- [零级衍射周期规则](2026-07-26-zeroth-order-period-rule.md)
- [经典 PB metalens 候选与复刻边界](2026-07-27-classic-pb-metalens-candidates.md)
- [大 NA 传播相位 method boundaries](2026-07-27-large-na-propagation-metalens-method-boundaries.md)
- [四案 period/aspect audit](2026-08-06-four-case-period-aspect-ratio-audit.md)

## Source-access log

- Yang、Malek、Liu、Arbabi publisher pages：2026-08-08 可访问。
- Khorasaninejad author-hosted version of record：2026-08-08 可访问；官方 Science
  supplementary endpoint 的既有访问限制未用二手来源填补。
- APS Pfeiffer–Grbic、Fan–Suh–Joannopoulos、Ansys RCWA/HFSS official docs：
  2026-08-08 可访问。
- PNAS/PMC 页面在本次抓取中部分触发 recaptcha；只采用检索页可直接核验的论文摘要、
  结论与 DOI，不用它支撑 MetaCraft 的独占决策。
- 所有 MetaCraft-specific allocation、evidence ladder 与 stop/escalation rules 均明确
  是本记录从上述来源和本地 ADR 作出的架构推论，不冒充论文原句。
