---
record_type: research_record
date: 2026-07-23
status: proposed_architecture_input
authority_level: none
current_capability: false
scope: ansys_lumerical_fdtd_low_na_metalens_unit_cell_templates
---

# Lumerical FDTD 低 NA 超透镜模板契约：建构、读回与资格验证

> 2026-08-01 update: 本文保留的 `λ/2` source/reference-plane 距离是历史案例与
> proposed input，不再是当前模板规则。当前垂直布局由
> [ADR 0017](../adr/0017-let-one-periodic-layout-place-every-reference-plane.md)
> 统一规定；`nearest mesh cell` 与世界坐标读回事据见
> [Lumerical periodic reference-plane read-back](2026-08-01-lumerical-periodic-reference-plane-readback.md)。

## 结论摘要

旧代码已经被删除，但关键科学设计并未完全消失。保留的 notebooks、`sc.py`、FDTD artifacts 和既有 research records 足以恢复以下经过实际使用的建模意图：

1. `z = 0` 被旧案例稳定地用作**基底顶面与 meta-atom 底面的界面**：基底位于 `z <= 0`，介质柱或纳米鳍位于 `z >= 0`。
2. 传播相位案例以周期圆柱单元建立复透射响应；PB 案例以可旋转矩形纳米鳍建立偏振转换响应；另有环形单元扫参案例。
3. 单元仿真使用横向周期边界、纵向 PML、从基底侧沿 `+z` 入射的平面波，以及位于结构上方的频域场/功率观察面。
4. 旧案例中的 `500 nm` 柱高、`300 nm` 周期、`λ/2` 间距、`mesh accuracy = 2`、`8` 层 PML 等都是**参考案例参数**，不是跨材料、跨波长的 MetaCraft 默认值，更不是 qualification。
5. 正确的实现不能是一个巨大的 `lumerical_fdtd.py`，也不能是一个跨 solver 的通用 geometry implementation。Lumerical FDTD 应拥有自己的 deep package；其中：
   - template module 负责 simulation region、boundaries、source、monitors 与 observation contract；
   - construction module 负责把一个 solver-neutral candidate 建成 Lumerical 原生对象；
   - material module 负责材料写入、绑定与数值读回；
   - qualification fixture 证明 exact product/build/template/construction/material 组合可用。
6. 当前至少需要两个彼此独立的模板：
   - `periodic transmission`：传播相位的复透射与 phase-library evidence；
   - `periodic jones`：PB 相位的完整线偏振基响应、圆偏振转换与 leakage evidence。
7. 模板的产物不能只是 `.fsp` 或截图。每次建构都必须生成 machine-readable construction manifest，并用 solver read-back 验证 object count、coordinates、spans、orientation、material、boundaries、source、monitors、mesh 与 phase reference。
8. 当前 scope 仍是 single-wavelength、`NA <= 0.5` 的 propagation-phase 与 PB-phase metalens。FDTD 负责 periodic vector unit-cell response；有限口径系统评价仍由 Python 的 low-NA field evaluator 完成。旧 full-lens FDTD 案例是参考与未来对照，不是当前 fixed workflow。

本记录只提出 Python/Lumerical implementation 的研究建议，不修改 Rust protocol，不激活新 capability，也不把执行排列成 M1–M7 或 fixed workflow。

## 证据标记

本文逐项区分三种口径：

- **Ansys 官方事实**：产品、script command、边界条件、source、monitor 或 read-back 的第一方行为。
- **保留参考案例事实**：当前仓库中仍可读取的 notebooks 与脚本实际做过什么；它们不是规范。
- **MetaCraft 建议**：根据官方能力、保留案例和当前 architecture 得出的 contract；需在后续 spec/ADR 中另行接纳。

## 一、Ansys 官方已经确认的事实

### 1. 坐标是模型属性，`z = 0` 没有产品内置的超透镜语义

Lumerical 的 `addrect`、`addcircle` 和 `addring` 通过位置、span、radius 等属性在 simulation space 中建立原生对象；`z = 0` 本身只是一个坐标值。analysis group 还可以拥有自己的局部 origin，组内对象位置相对该 origin 解释。因此，“`z = 0` 是基底/纳米柱界面”必须是 MetaCraft template 的显式 construction convention，而不能假设 FDTD 自动理解这一点。[Ansys `addrect`](https://optics.ansys.com/hc/en-us/articles/360034404214-addrect-Script-command)；[Ansys `addcircle`](https://optics.ansys.com/hc/en-us/articles/360034404114-addcircle-Script-command)；[Ansys analysis groups](https://optics.ansys.com/hc/en-us/articles/360034382454-Analysis-Groups-Simulation-object)

`getnamed` 可以按 exact object name 读回属性，`getnamednumber` 可以检查同名对象个数。因此，坐标、span、rotation 和 material assignment 可以在建模后被机器读回；不需要把“脚本执行无异常”冒充为建构正确。[Ansys `getnamed`](https://optics.ansys.com/hc/en-us/articles/360034408574-getnamed-Script-command)；[Ansys `getnamednumber`](https://optics.ansys.com/hc/en-us/articles/360034408594-getnamednumber-Script-command)

Lumerical 的 center/span 与 min/max 是联动属性；混合设置时，后写入的属性会改变先前结果。Python API 还明确警告 duplicate object names 会产生未定义行为。因此 template 应按确定顺序只使用一种坐标表示完成建构，并以唯一名称读回最终值。[Ansys Python API: working with simulation objects](https://optics.ansys.com/hc/en-us/articles/39744946400659-Working-with-Simulation-Objects-Python-API)

### 2. 周期单元的横向边界、纵向边界和 source 必须相互一致

Ansys 明确说明：Periodic boundary condition 只在**结构与场都周期**时成立；normal-incidence plane wave 与单周期结构是典型用途。斜入射时，每个周期之间存在相位差，应改用 Bloch boundary，宽带固定角度问题还可能需要 BFAST。周期单元通常在非周期方向使用 PML；Ansys 对 periodic simulation 推荐考虑 steep-angle PML profile。[Ansys periodic boundaries](https://optics.ansys.com/hc/en-us/articles/360034382734-Periodic-boundary-conditions-in-FDTD-and-MODE)

平面波 source 应覆盖与传播方向正交的整个 simulation span。把有限 span 的 plane wave 与横向 PML 混用会引入非物理截断衍射；因此当前 unit-cell template 应使用横向 periodic boundaries，不应把 full-aperture PML 设置复制回 unit-cell response。[Ansys plane-wave truncation](https://optics.ansys.com/hc/en-us/articles/360034382874-Understanding-field-truncation-issues-with-finite-sized-plane-wave-sources)；[Ansys plane-wave source](https://optics.ansys.com/hc/en-us/articles/360034382854-Sources-Plane-wave-and-Beam)

PML 不是一个可以固定一次后永久忽略的数字。PML proximity、PML reflection、mesh grading 与 structure extension 都会改变误差；结构进入 PML 时应完整延伸通过 boundary region。[Ansys PML structure extension](https://optics.ansys.com/hc/en-us/articles/360034382414-Always-extend-structures-through-PML-boundary-conditions)；[Ansys convergence testing](https://optics.ansys.com/hc/en-us/articles/360034915833-Convergence-testing-process-for-FDTD-simulations)

### 3. source 的方向、偏振和相位 convention 必须写入模板

FDTD plane-wave source 明确区分 injection axis、forward/backward direction、polarization angle 与 source phase。对沿 `+z` 传播的 forward plane wave，Ansys 给出的时间/空间 convention 是

```text
exp(-i ω t + i k z)
```

source phase `φ` 作为 `+iφ` 进入。Ansys 官方示例以 `x` 偏振、相位 `0°` 和 `y` 偏振、相位 `90°` 的两个 source 构造圆/椭圆偏振，并特别提醒 circular handedness 会随历史 convention 的命名而不同。[Ansys circular polarization and phase convention](https://optics.ansys.com/hc/en-us/articles/1500006150981-Circular-polarization-and-phase-convention)

所以 MetaCraft 不能只保存字符串 `RCP` 或 `LCP`。至少必须保存：

```text
time sign
propagation direction
transverse basis
relative phase
handedness definition as seen along a declared viewing direction
```

### 4. MetaCraft 只采用 S-parameter group

frequency-domain monitor 能够返回位置/频率上的场与功率，但这只是官方产品背景，不是 MetaCraft 的模板选择。[Ansys frequency-domain monitor](https://optics.ansys.com/hc/en-us/articles/360034902393-Frequency-domain-monitor-Simulation-object)

本项目的正式模板只创建 `addobject("grating_s_params")`。其内部 source、reflection plane 与 transmission plane 共同构成一个不可拆分的 observation group；Python 不再创建 `addpower`、`adddftmonitor`、独立 plane-wave source 或其他并行观测路径。下文出现的 source、monitor 和 reference plane 均指这个 group 的内部参数或历史案例事实，不代表额外对象。

Ansys 的 grating S-parameter analysis group 返回的是 complex amplitude reflection/transmission coefficients。官方明确指出：

- `S11`、`S21` 是复振幅系数，不是功率系数；
- monitors 必须离结构足够远，使被观察场已近似 propagating plane wave，不能仍包含明显 evanescent field；
- source 到结构、结构到 monitor 的额外传播相位必须补偿；
- `metamaterial center`、`metamaterial span`、source position 与 target grating order 都参与 phase reference；
- `S_polarization` 才适用于可能发生 polarization rotation 的结构；
- warnings、缺失 grating order 或非 S/P input 不能被静默忽略。

[Ansys metamaterial S-parameter extraction](https://optics.ansys.com/hc/en-us/articles/360042095873-Metamaterial-S-parameter-extraction)

因此，“取 monitor 中心点的 `angle(Ex)`”可以作为诊断，却不足以单独成为跨结构比较的 phase-library contract。正式 observation 应固定 reference planes / compensation convention，并保留 complex coefficient、power 与 warning。

### 5. mesh、simulation time 和 early shutoff 需要数值 qualification

Ansys 的 convergence guide 把 PML proximity/reflection、grid dispersion、staircasing、material fit、finite time step、non-uniform mesh 和 monitor interpolation 都列为独立误差来源。mesh refinement 或 override 可以改善局部表示，但不能用一个全局 `mesh accuracy` 数字替代 convergence evidence。[Ansys convergence testing](https://optics.ansys.com/hc/en-us/articles/360034915833-Convergence-testing-process-for-FDTD-simulations)；[Ansys mesh override](https://optics.ansys.com/hc/en-us/articles/360034901833-Mesh-override-Simulation-Object)

FDTD solver result 会报告 simulation status：run to full time、run to autoshutoff 或 diverged。模板应保存 status、autoshutoff level、实际 runtime、mesh 与 memory observations，而不是只记录 `fdtd.run()` 返回。[Ansys FDTD solver object](https://optics.ansys.com/hc/en-us/articles/360034382534-FDTD-solver-Simulation-Object)

### 6. Ansys 自己的 metalens example 也把 unit-cell library 与 full lens 分开

Ansys 的 small-scale metalens example 先扫 nanorod height/radius，建立 phase、transmission 与 near-field library，再把目标 phase map 映射成 nanorod distribution。官方同时展示 direct full-lens FDTD 与 near-field reconstruction，并明确指出 local-periodicity assumption、neighbor discontinuity、period、mesh 和 full-lens size 都会影响结果。[Ansys Small-Scale Metalens](https://optics.ansys.com/hc/en-us/articles/360042097313-Small-Scale-Metalens-Field-Propagation)

这个示例支持当前 MetaCraft 的职责划分：

```text
periodic full-wave unit-cell evidence
                     +
finite-aperture field evaluation
```

它不支持把整个 metalens 研究压成一个 `solver = lumerical` 字段。

## 二、保留参考案例恢复出的事实

### 1. propagation-phase notebook

[PropagationPhaseMetasurface.ipynb](../../reference/teamate's%20code/Metasurface-Design/notebook/PropagationPhaseMetasurface.ipynb) 的保留代码单元建立了以下 reference case：

| 项目 | 保留案例设置 |
| --- | --- |
| wavelength | `633 nm`，single frequency |
| unit cell | `300 nm × 300 nm` |
| substrate | `Al2O3 - Palik`，`z_max = 0` |
| meta-atom | TiO₂ circular post，`z_min = 0`，`z_max = 500 nm` |
| varied parameter | radius |
| source | 基底侧，沿 `+z` forward，线偏振 |
| boundaries | `x/y = Period`，`z = PML` |
| PML | `8` layers |
| mesh | automatic，`mesh accuracy = 2` |
| transmission plane | `z = height_atom + λ/2` |
| observation | `E/H/T`；library 中使用 transmission 与 transmitted-field phase |

该 notebook 还把 unit-cell radius sweep 与 finite metasurface/full-device construction 分开：单元阶段横向 periodic；full-device 阶段横向改为 PML。这一差别是应继承的科学意图。

### 2. geometric/PB notebook

[GeometricPhaseMetasurface.ipynb](../../reference/teamate's%20code/Metasurface-Design/notebook/GeometricPhaseMetasurface.ipynb) 使用相同的 `z = 0` interface convention，但把 meta-atom 换成：

```text
rectangular fin
length = 270 nm
width = 150 nm
height = 500 nm
rotation around z
```

它以 `x` source（phase `0°`）和 `y` source（phase `90°`）在同一 simulation 中构造圆偏振，并从 transmitted `Ex/Ey` 组合 converted/leakage circular channels，计算 conversion efficiency。这个实现与 Ansys 的 phase convention example 一致，但 notebook 直接称其为 `RCP/LCP`，没有保存 viewing-direction 与 handedness definition，因此只能继承“正交分量 + 相对相位”的做法，不能继承未声明的 handedness 名称。

### 3. ring sweep script

[sc.py](../../reference/teamate's%20code/sc.py) 保存了另一种实际结构：

```text
substrate: z ∈ [-3 μm, 0]
ring:      z ∈ [0, height]
period:    600 nm seed
wavelength: 641 nm
```

它使用 `addring` 扫 outer/inner radius，通过 `grating_s_params` 读取 `S21_Gn` 与 `T_Gn`，并写出 phase 与 amplitude。这证明旧实现已考虑 circular post/rectangular fin 以外的 Lumerical-native construction。不过该脚本带有绝对材料库路径、GUI 人工确认、未固定 build 的 native material、magic mesh/time 和未保存完整 read-back，不能直接升级为 qualification。

### 4. project PB sweep notebook

[PB_ap.ipynb](../../reference/teamate's%20code/PB_ap.ipynb) 保存了比教程 PB notebook 更接近完整偏振表征的一步：它对同一个 rectangular fin candidate 分别运行 `x` 与 `y` 两个线偏振输入，随高度更新 `metamaterial center/span`，并通过 `grating_s_params` 读取 phase-compensated `S21_Gn` 与 `T_Gn`。

应继承的是“两次独立线偏振输入”和“S-parameter phase reference 随 structure span 显式更新”的意图。但该 notebook 只读取 `S` 中的同偏振 `S21_Gn`，没有保存 `S_polarization` 的四个复数线偏振系数，因此仍不是 full Jones evidence。它还包含绝对路径、固定十路资源、`sleep(20)`、宽带 sampled material 和未读回对象等运行时假设，不能原样恢复。

### 5. 应继承与不应继承的内容

| 应继承 | 不应继承 |
| --- | --- |
| `z = 0` interface convention | 把 `z = 0` 当作 Ansys 内置语义 |
| unit-cell periodic 与 finite-aperture PML 的明确区分 | 把 full-lens FDTD 设成当前必经步骤 |
| circular post、rectangular fin、ring 的结构参数语义 | 一个跨 solver 的 universal geometry implementation |
| 传播相位与 PB 两条不同 observation chain | 用 propagation phase output 代替 PB Jones evidence |
| PB 的两个独立线偏振输入与显式 S-parameter phase reference | 把两个同偏振 `S21` 误称为 full Jones matrix |
| complex transmission、field 与 power 都被保留 | 只保存中心像素 phase |
| 独立 simulation artifacts 可供复核 | 依赖 GUI input、绝对路径或未审计 `.fsp` |
| resource settings 是运行事实 | 把 notebook 中的 worker 数写成科学 binding |

## 三、MetaCraft 推荐的建构标准

### 1. 统一的是 construction contract，不是 solver-native construction code

同一个 scientific candidate 在 Lumerical FDTD、CST 与 COMSOL 中可以采用完全不同的原生对象、boolean operation、mesh 与 monitor。跨 solver 只能共享“什么算建成同一个候选”的 contract：

```text
cell frame
family identity
parameter meanings and units
material roles
interface plane
lattice and periodic intent
source intent
observation intent
acceptance tolerances
```

每个 solver package 必须自己实现并资格验证：

```text
candidate
  ↓
solver-native construction
  ↓
construction manifest
  ↓
solver read-back
```

这意味着 Lumerical 的 `addcircle`、`addrect`、`addring` mapping 不能放进公共 `geometry.py`；它们只能存在于 `solvers/lumerical_fdtd/` 内部。

### 2. `z = 0` 的正式含义

MetaCraft 应把以下内容固定成 current low-NA unit-cell construction convention：

```text
                         +z

upper PML
upper homogeneous superstrate
transmission reference plane

z = h       ───────────── meta-atom top
             meta-atom
z = 0       ───────────── substrate top = meta-atom base
             substrate
source / lower reference region
substrate extended through lower PML

lower PML
```

规则：

1. `z = 0` 是 global simulation coordinate 中的 declared interface plane。
2. substrate 的上表面必须精确读回为 `z_max = 0`。
3. every meta-atom solid 的底面必须精确读回为 `z_min = 0`，除非 candidate contract 明确声明 embedded、suspended 或 multilayer structure；这些目前不在 current capability。
4. source 位于 `z < 0` 的 homogeneous incidence region，沿 `+z` forward 入射。
5. transmission reference plane 位于最高 structure 上方的 homogeneous superstrate，且与 evanescent near field 保持经过 qualification 的距离。
6. source、reference planes、structure surfaces 和 PML 之间不得重合。
7. substrate 必须延伸到 lower PML boundary region；其 exact span 与 structure extension property 必须被读回。
8. `λ/2` 只能作为保留案例的初始 separation seed。最终 source/monitor/PML distance 必须由 convergence fixture 固定。

### 3. template 与 construction 必须是两条独立 seam

Lumerical package 内部建议形成以下 locality；这是研究建议，不是本记录直接创建的 source tree：

```text
solvers/lumerical_fdtd/
├─ readiness.py
├─ session.py
├─ material.py
├─ constructions/
│  ├─ circular_post.py
│  └─ rectangular_fin.py
├─ templates/
│  ├─ periodic_transmission.py
│  └─ periodic_jones.py
└─ qualification/
   └─ fixtures.py
```

`templates` 负责：

```text
simulation region
boundaries
sources
reference planes and monitors
mesh/time policy
observation extraction
```

`constructions` 负责：

```text
native object creation
candidate parameter mapping
material-role assignment
object naming
geometry read-back
```

二者通过窄 contract 组合。新增结构不应修改 runner；新增 observation contract 也不应复制材料与 session lifecycle。

### 4. 当前 construction families

| family | scientific parameters | Lumerical-native realization | required read-back | current standing |
| --- | --- | --- | --- | --- |
| circular post | radius、height、period、center、atom/substrate roles | one `addcircle` cylinder | exact count、center、radius、`z_min/z_max`、material | propagation 首个正式 candidate |
| rectangular fin | length、width、height、orientation、period、center、roles | one `addrect` solid rotated about `z` | exact count、spans、`z_min/z_max`、axis、rotation、material | PB 首个正式 candidate |
| annular post | inner radius、outer radius、height、period、center、roles | one `addring` | exact radii order、height、center、material | 仅有保留案例；通过新 fixture 后才能注册 |
| composite family | ordered primitives、boolean/material roles、constraints | product-native structure group or multiple objects | full child manifest and topology | current scope 不支持 |

`family` 只描述 scientific candidate identity。Lumerical-native object type、object name 和 property mapping 属于 exact binding/qualification；未来 CST 或 COMSOL 不需要镜像这张 mapping 表。

## 四、两个独立 template 的最小科学契约

### 1. `periodic transmission`

用途：为 propagation-phase route 取得 periodic complex transmission response。

#### Construction inputs

```text
wavelength
cell period x/y
declared background and substrate
qualified material bindings
one registered propagation construction
candidate parameters
source basis and amplitude
reference-plane policy
mesh/time/PML policy
```

#### Native model

```text
x/y boundaries: periodic
z boundaries: PML
source: normal incidence, +z, one declared linear basis
structure: substrate + one registered native construction
observations:
  - phase-compensated zero-order complex transmission
  - transmitted power
  - transmitted E/H plane
  - warning and solver status
```

#### Required observations

```text
complex S21 for declared order and basis
power transmission
complex E/H at fixed upper plane
phase-reference metadata
grating-order warning state
solver status and autoshutoff
construction/material read-back references
```

phase library 必须从 declared complex coefficient 计算。monitor-center phase 可以作为 debug artifact，但不能成为唯一正式 coefficient。

### 2. `periodic jones`

用途：为 PB route 取得 anisotropic unit cell 的完整 polarization response。

#### Construction inputs

除公共 cell/material/convergence inputs 外，还必须包含：

```text
transverse linear basis
orientation sign and zero direction
time-harmonic sign
propagation/viewing direction
circular-basis transform
converted/leakage labels derived from that transform
```

#### Excitation contract

正式 qualification 应使用两次独立的 linear-basis excitation：

```text
run x input → first Jones column
run y input → second Jones column
```

然后在同一 phase-reference convention 下组成：

```text
J_linear =
  [ t_xx  t_xy ]
  [ t_yx  t_yy ]
```

再由明确声明的 basis transform 推导 circular converted/leakage channels。Ansys 官方允许用两个同时存在、相差 `90°` 的 source 直接生成 circular input，但该做法只得到一个输入状态的响应；它不能代替完整 Jones evidence。

#### Required observations

```text
four complex linear-basis coefficients
co-polar and cross-polar powers
declared circular-basis converted coefficient
declared circular-basis leakage coefficient
converted/leakage power normalization
orientation and handedness convention
phase-reference metadata
warnings, solver status and all read-backs
```

PB template 不能只套用理想 `2θ`。rotation law 必须由 qualified cell response 支撑；converted 与 leakage 不得在 observation 阶段合并。

## 五、source、monitor、mesh 与 time 的精确要求

### 1. source

每个 manifest 至少保存：

```text
object name and count
injection axis
direction
position and spans
wavelength start/stop
amplitude
polarization angle or basis vector
phase
plane-wave type
```

current template 只允许 normal incidence、single wavelength。若 request 出现斜入射、宽带或非周期 illumination，compiler 应给出 capability mismatch；不能由 template 静默改成 Bloch/BFAST/TFSF。

### 2. monitors

每个 template 都应明确：

- upper complex-field plane 的 exact `z` 与 `x/y span`；
- S-parameter group 的 source position、metamaterial center/span、target order 与 phase compensation settings；
- reflection/transmission monitors 的 exact locations；
- monitor frequency points 与 source range 一致；
- recorded components 与 downsampling；
- warnings 与 missing-order status；
- 所有 reference plane 在 sweep 中是否固定。

尤其是 height sweep：如果 transmission plane 跟随每个候选的 pillar top 移动，raw field phase 会混入不同自由传播距离。应优先把 reference planes 固定在覆盖整个 candidate-height envelope 的相同 global coordinates；若使用 S-parameter compensation，则必须读回并保存 exact compensation inputs。

### 3. mesh

模板不能只保存 `mesh accuracy`。最小 manifest 应同时记录：

```text
global mesh accuracy
mesh refinement mode
minimum mesh step
every mesh override region
dx/dy/dz or equivalent-index settings
mesh object target and buffer
candidate minimum feature/gap
```

qualification 至少比较 coarse/nominal/refined 三档，观察 complex coefficient、power、phase 和 PB conversion 的变化。若 geometry、material contrast、minimum gap 或 wavelength 离开 fixture domain，旧 mesh qualification 不再匹配。

### 4. time and termination

模板应同时设置 max simulation time 与 early shutoff policy，并保存：

```text
requested max time
auto shutoff threshold
actual solver status
actual autoshutoff level
actual runtime
divergence state
```

run-to-full-time 与 run-to-autoshutoff 都可以是有效运行事实；diverged 必须失败关闭。若能量未充分衰减或 coefficient 在延长 simulation time 后仍明显变化，不能产生 qualified observation。

## 六、材料绑定与 read-back

本文继承 [refractiveindex.info → Lumerical FDTD research](2026-07-12-lumerical-fdtd-refractiveindex-material-import.md) 的结论：

1. user table / refractiveindex.info-derived material 先形成 portable material record/sample，再由 Lumerical material module 写入 exact solver material；
2. solver-native material identity 只在 exact Lumerical binding 内有效；
3. material name exists 不等于 binding qualified；
4. geometry object 的 `material` property 必须逐对象读回；
5. `getmaterial`、`getindex` 与 `getfdtdindex` 回答不同问题，不能互相替代。

Ansys 官方接口分别支持 material property read-back、database interpolation 与 FDTD fitted response。[Ansys `getmaterial`](https://optics.ansys.com/hc/en-us/articles/360034930053-getmaterial-Script-command)；[Ansys `getindex`](https://optics.ansys.com/hc/en-us/articles/360034409674-getindex-Script-command)；[Ansys `getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)

每个 template run 的 material closure 至少应包含：

```text
substrate material binding
meta-atom material binding
background material identity
exact object → material-role mapping
exact solver material names
stored material read-back
database response read-back
FDTD fitted response read-back
working-frequency coverage
```

## 七、construction manifest

建模完成、run 开始之前，adapter 应生成一份不可变 manifest。建议的最小内容是：

```yaml
runtime:
  product: ansys_lumerical_fdtd
  release_or_build: "..."
  lumapi_fingerprint: "..."

template:
  identity: periodic_transmission | periodic_jones
  source_hash: "..."
  qualification_refs: [...]

frame:
  units: metre
  global_origin: [0, 0, 0]
  interface_z: 0
  propagation_axis: +z
  transverse_basis: [x, y]

cell:
  period_x: ...
  period_y: ...
  background: ...

construction:
  family: circular_post | rectangular_fin | ...
  constructor_hash: "..."
  declared_parameters: {...}
  material_roles: {...}

objects:
  - exact_name: substrate
    native_type: rectangle
    expected: {...}
    read_back: {...}
  - exact_name: meta_atom
    native_type: circle | rectangle | ring
    expected: {...}
    read_back: {...}

solver:
  region_read_back: {...}
  boundaries_read_back: {...}
  pml_read_back: {...}
  mesh_read_back: {...}
  time_read_back: {...}

sources:
  - exact_name: ...
    expected: {...}
    read_back: {...}

monitors:
  - exact_name: ...
    role: ...
    expected: {...}
    read_back: {...}

materials:
  - role: ...
    binding_ref: ...
    assigned_object_read_back: ...
    numerical_read_back_ref: ...
```

manifest 必须先完成以下比较：

```text
expected count == read-back count
expected properties ~= read-back properties under declared tolerance
all exact names unique
all spans finite and positive
substrate top == 0
meta-atom bottom == 0
meta-atom remains within cell and candidate constraints
source/monitor/PML ordering valid
all material roles resolved and read back
```

只有比较通过后，runner 才应运行 simulation。manifest、run observation 和 comparison receipt 都只是 Python observation；只有经过 Rust `decide` admitted 后才成为 evidence。

## 八、qualification fixtures

> 能力命名更新（见 ADR 0013）：Adapter 现在暴露两个 route-neutral 响应能力
> `periodic_transmission_response` 与 `periodic_polarization_response`，分别由
> 下文本节的传播 fixture 与双 linear-basis 极化 fixture 各自证明。旧的共享名
> `periodic_full_wave_response` 已退役。传播相位方法绑定前者，几何相位方法
> 绑定后者；二者独立发放，任一 fixture 失败不抑制另一个。



qualification 不能是一个 `trusted = true`。它必须绑定：

```text
product + build
lumapi
template source hash
constructor source hash
material binding
device/resource policy
fixture inputs
acceptance contract
```

建议按以下层次建立 fixtures；这是一组 evidence dependencies，不是 fixed workflow：

### 1. construction-only fixture

启动 exact FDTD build，建模但不求解：

- 检查 source、solver、monitor、substrate 与 meta-atom exact object count；
- 读回全部 coordinates、spans、rotation、boundaries、mesh、time 与 material；
- 保存 manifest；
- 重复两次，要求 canonical manifest 相同。

### 2. interface and empty-cell fixture

以已知 homogeneous/interface case 检查：

- `z = 0` interface 是否按约定构造；
- propagation direction 与 source normalization；
- S-parameter phase compensation；
- zero-order power balance；
- 无结构各向同性 case 的 cross-polar response 接近零。

### 3. propagation reference fixture

以保留的 `633 nm / 300 nm period / TiO₂ circular post / Al₂O₃ substrate` case 作为首个候选 seed，但重新固定 portable materials、exact build、reference planes 与 acceptance tolerances。fixture 应比较：

- radius perturbation 确实改变 read-back radius；
- complex transmission、power 与 phase 可重放；
- phase/reference plane 不随 radius sweep 移动；
- mesh、PML distance、monitor distance 与 time refinement 收敛；
- warning 为零，solver 不 diverge。

保留 notebook 的数值结果不能直接当 gold result；必须在新 contract 下重新生成。

### 4. PB reference fixture

以保留的 `633 nm / 300 nm period / TiO₂ rectangular fin / Al₂O₃ substrate` case 作为 seed，使用两次 independent linear excitation 取得 full Jones matrix。fixture 应检查：

- `0°` 与 `90°` orientation 的 native rotation read-back；
- `x/y` input columns 不被 source enablement 混淆；
- basis transform 在保存的 phase convention 下可重放；
- converted 与 leakage 分开；
- isotropic/zero-anisotropy control 不产生伪 conversion；
- mesh、PML、reference plane 与 time refinement 收敛。

### 5. rejection fixtures

以下任一情况必须 `unqualified` 或 `inconclusive`，不能自动修复后继续：

- object name 重复或 object count 不符；
- substrate top 或 atom bottom 不在 declared `z = 0`；
- source direction、basis、phase 或 wavelength read-back 不符；
- unit-cell 横向边界不是 periodic；
- height/radius/gap 超出 candidate domain；
- exact material name 不存在、assignment 不符或 numerical read-back 失败；
- S-parameter warning、target order 缺失或 evanescent/reference-plane condition 未通过；
- monitor/reference plane 随 sweep 非预期移动；
- simulation diverged 或未收敛；
- build、template、constructor、material 或 mesh policy 与 qualification pin 不同。

## 九、对 Python architecture 的直接建议

这项研究支持以下调用方向：

```text
route compiles proof and candidate domain
                  ↓
binding selects exact qualified realization
                  ↓
runner obtains permit
                  ↓
lumerical fdtd template
  ├─ native construction
  ├─ material binding
  ├─ source / monitor / solver
  └─ construction read-back
                  ↓
observation
                  ↓
authority proposal
```

关键 seam 是：

```text
same construction contract
different solver-native construction
```

而不是：

```text
one universal geometry implementation
different command spellings
```

Lumerical template 不直接调用 Rust，不选择 propagation/PB route，不管理 Python worker pool，也不解释 focus result。runner 不知道 `addcircle`、`addrect` 或 S-parameter group 的内部细节。Rust 只决定 manifest/observation/proposal 的结构与生命周期是否可接纳，不解释 Maxwell physics。

## 十、公开资料仍不能替我们决定的内容

以下值不能由本文猜测为永久标准，必须通过 exact build qualification 或 route acceptance contract 固定：

- source、monitor 与 PML 距离；
- PML profile 与 layer count；
- mesh accuracy、override `dx/dy/dz` 与 conformal policy；
- max simulation time 与 autoshutoff threshold；
- phase/transmission/conversion/convergence tolerances；
- S-parameter object-library implementation 是否跨 release 保持相同；
- exact property-name map 与 result attribute names；
- full Jones extraction 的 normalization tolerance；
- circular handedness display name；
- 哪些新增 construction family 已达到 release qualification。

## 参考资料

### Ansys 官方

1. [Small-Scale Metalens – Field Propagation](https://optics.ansys.com/hc/en-us/articles/360042097313-Small-Scale-Metalens-Field-Propagation)
2. [Periodic boundary conditions in FDTD and MODE](https://optics.ansys.com/hc/en-us/articles/360034382734-Periodic-boundary-conditions-in-FDTD-and-MODE)
3. [Plane wave and beam source](https://optics.ansys.com/hc/en-us/articles/360034382854-Sources-Plane-wave-and-Beam)
4. [Circular polarization and phase convention](https://optics.ansys.com/hc/en-us/articles/1500006150981-Circular-polarization-and-phase-convention)
5. [Metamaterial S-parameter extraction](https://optics.ansys.com/hc/en-us/articles/360042095873-Metamaterial-S-parameter-extraction)
6. [Frequency-domain monitor](https://optics.ansys.com/hc/en-us/articles/360034902393-Frequency-domain-monitor-Simulation-object)
7. [FDTD solver object](https://optics.ansys.com/hc/en-us/articles/360034382534-FDTD-solver-Simulation-Object)
8. [Convergence testing process for FDTD simulations](https://optics.ansys.com/hc/en-us/articles/360034915833-Convergence-testing-process-for-FDTD-simulations)
9. [Mesh override](https://optics.ansys.com/hc/en-us/articles/360034901833-Mesh-override-Simulation-Object)
10. [`addrect`](https://optics.ansys.com/hc/en-us/articles/360034404214-addrect-Script-command), [`addcircle`](https://optics.ansys.com/hc/en-us/articles/360034404114-addcircle-Script-command), [`addring`](https://optics.ansys.com/hc/en-us/articles/360034404234-addring-Script-command)
11. [`getnamed`](https://optics.ansys.com/hc/en-us/articles/360034408574-getnamed-Script-command), [`getnamednumber`](https://optics.ansys.com/hc/en-us/articles/360034408594-getnamednumber-Script-command)
12. [`getmaterial`](https://optics.ansys.com/hc/en-us/articles/360034930053-getmaterial-Script-command), [`getindex`](https://optics.ansys.com/hc/en-us/articles/360034409674-getindex-Script-command), [`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)

### 仓库中保留的参考案例

1. [PropagationPhaseMetasurface.ipynb](../../reference/teamate's%20code/Metasurface-Design/notebook/PropagationPhaseMetasurface.ipynb)
2. [GeometricPhaseMetasurface.ipynb](../../reference/teamate's%20code/Metasurface-Design/notebook/GeometricPhaseMetasurface.ipynb)
3. [MetalensDesign.ipynb](../../reference/teamate's%20code/Metasurface-Design/notebook/MetalensDesign.ipynb)
4. [PB_ap.ipynb](../../reference/teamate's%20code/PB_ap.ipynb)
5. [sc.py](../../reference/teamate's%20code/sc.py)
6. [红外介质超透镜纳米柱高度一手资料研究](2026-07-16-infrared-metalens-nanopillar-height-primary-source-study.md)
7. [超表面科学流程编译的正交关系研究](2026-07-22-metasurface-scientific-compilation-dimensions.md)
