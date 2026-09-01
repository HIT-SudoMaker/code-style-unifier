# Cube BS/PBS 四终端几何与散射契约研究

**研究日期：** 2026-08-24  
**状态：** 设计输入，不是已接受的领域规范或 ADR  
**首版范围：** 由两块直角棱镜构成、对角面带分束膜、外侧四面近似抗反射的 cube BS/PBS；plate、pellicle 和外表面鬼像只用于划清非声明范围。

## 结论

ChromatixNext 不应把 cube BS/PBS 表达为“一个输入，两个无方向的 `transmitted` / `reflected` 输出”。首版应把它表达为一个拥有固定姿态、对角分束面、膜层侧和四个几何终端的物理元件。每个终端均可承载入射与出射场，但一次从某终端入射只存在一条直通透射方向和一条镜面反射方向；另一相邻终端在首版主光路模型中结构性不可达。

必须冻结两类不同事实：

1. **稀疏终端拓扑**决定哪一对终端是透射、哪一对终端是反射、哪些连接不可达；这是 Assembly 的结构检查事实。
2. **复振幅散射响应**决定每条允许路径上的振幅、相位、偏振、损耗与泄漏；这是 BS/PBS Element 的物理计算事实。

不能用一个 `power_transmissivity` 同时代替这两类事实。Finesse 的官方四端口矩阵本身就是稀疏矩阵：四个输入各自只耦合到两个输出，而不是耦合到其余三个输出。[Finesse 2 官方手册，式 3.48](https://finesse.ifosim.org/finesse2_manual.pdf#page=55) 同一手册还明确给出相反两侧的反射相位符号和两条透射耦合，说明“端口拓扑”和“复系数约定”必须同时存在。[Finesse 2 官方手册，式 3.47–3.48](https://finesse.ifosim.org/finesse2_manual.pdf#page=55)

## 物理结构与首版边界

Cube beamsplitter 由两块直角棱镜组成，其中一块棱镜的斜面带分束膜，两块斜面胶合或光学接触，外侧四面通常带抗反射膜。[Newport 官方结构说明](https://www.newport.com/c/beamsplitters/) [Edmund Optics 官方棱镜应用说明](https://www.edmundoptics.com/knowledge-center/application-notes/optics/optical-prism-application-examples) Ansys 的官方 coating 示例也把 cube 模型定义为两个直角棱镜之间、玻璃内 45° 入射的对角膜层，而不是一个抽象的无方向功率节点。[Ansys Optics 官方 coating 示例](https://optics.ansys.com/hc/en-us/articles/42661834041363-Common-examples-from-Essential-Macleod-coatings)

这里要严格区分两个“朝向”事实：

- **对角分束面的几何朝向**决定镜面反射会到达哪一个相邻终端；把对角面从一条对角线旋到另一条对角线会改变可达拓扑。
- **膜层法向/薄膜层序朝向**区分从膜层哪一侧入射，影响两侧的复反射/透射系数、相位和器件资格，但在同一几何平面上翻转法向不会凭空产生另一条镜面反射方向。Newport 明确标记带膜棱镜，并建议光从带膜棱镜一侧进入以降低胶层中的能量通量；从未镀膜棱镜进入在几何上仍可工作，但胶层承受的通量会超过三倍。[Newport 官方 cube BS 使用方向说明](https://www.newport.com/f/broadband-non-polarizing-cube-beamsplitters?compatibility=METRIC) Thorlabs 的 cube PBS 资料同样以标记指出带膜棱镜，并说明光可从任一抛光面入射进行偏振分离。[Thorlabs 官方 cube PBS 资料](https://www.thorlabs.com/catalogpages/Obsolete/2020/PBS511.pdf)

因此，首版模型应把“几何允许”与“在产品规格内推荐/资格化”分开：反向入射不能被 Assembly 当成拓扑错误，但器件状态可以把某些入射侧标成超出功率、损伤阈值或标称性能范围。

Plate 不是 cube 的另一种参数。Plate 有前后两个分离表面、有限基片厚度、透射横移和潜在鬼像；厂商通过背面抗反射膜与楔角抑制这些效应。[Newport 官方 plate BS 规格](https://www.newport.com/p/10B20NP.28) Pellicle 是微米级膜，第二表面反射近乎与主光束重合，显著减小色散和鬼像，但有自己的干涉起伏和耐用性限制。[Newport 官方 pellicle BS 规格](https://www.newport.com/p/PBS-2C) 因此，plate/pellicle 不应复用首版 cube 的内部几何状态，只能在未来共享更抽象的“四终端散射结果”概念（若真实用例证明该抽象有价值）。

## 建议冻结的局部坐标与终端编号

不要继承任何未画图的“顺时针 1、2、3、4”口头编号。建议为器件定义一个右手局部坐标架：

- `local_x` 指向终端 3；
- `local_y` 指向终端 2；
- `local_z = local_x cross local_y`；
- 终端按俯视 `local_x-local_y` 平面定义：
  - 终端 1：西侧，中心位置沿 `-local_x`，入射方向为 `+local_x`；
  - 终端 2：北侧，中心位置沿 `+local_y`，入射方向为 `-local_y`；
  - 终端 3：东侧，中心位置沿 `+local_x`，入射方向为 `-local_x`；
  - 终端 4：南侧，中心位置沿 `-local_y`，入射方向为 `+local_y`。

首版规范对角面取 `local_y = local_x`。令膜层法向从包含终端 1、2 的棱镜侧 A 指向包含终端 3、4 的棱镜侧 B。该法向只确定两侧身份和薄膜层序，不替代器件完整姿态。

```text
                         terminal 2 (+local_y)
                                  ↓ input
                  side A       /       side B
                              /  coating plane
terminal 1 (-local_x)  input →/← input  terminal 3 (+local_x)
                            /
                  side A  /          side B
                                  ↑ input
                         terminal 4 (-local_y)
```

这套编号与 Finesse 官方四端口矩阵的非零模式一致，但这里的编号由 ChromatixNext 自己的局部坐标完整定义，不依赖外部软件的图示方向。[Finesse 2 官方手册，四端口示意与式 3.48](https://finesse.ifosim.org/finesse2_manual.pdf#page=55)

## 完整允许/禁止路由表

下表只描述**主分束膜的一次相互作用**。`T` 是直通，`R` 是镜面反射；有限抗反射残余、胶层鬼像和多次内部反射不在首版拓扑中。

| 入射终端 | 允许透射输出 | 允许反射输出 | 禁止的另一相邻输出 | 同终端输出 |
|---|---:|---:|---:|---:|
| 1 | 3 | 2 | 4 | 禁止 |
| 2 | 4 | 1 | 3 | 禁止 |
| 3 | 1 | 4 | 2 | 禁止 |
| 4 | 2 | 3 | 1 | 禁止 |

等价地：

- 透射对为 `1 <-> 3`、`2 <-> 4`；
- A 侧反射对为 `1 <-> 2`；
- B 侧反射对为 `3 <-> 4`；
- 交叉相邻对 `1 <-> 4`、`2 <-> 3` 在首版主光路中结构性为零；
- 任一终端到自身结构性为零。

同一器件再次被光遇到时必须复用同一张表。例如从 1 入射时反射到 2、透射到 3；光从 3 返回时只能透射回 1、反射到 4，不能因为调用者把返回过程称作“合束”就重写成另一张任意端口表。

## 4×4 稀疏散射拓扑

令 `a_j` 是从终端 `j` 入射的复横向场，`b_i` 是从终端 `i` 出射的复横向场；矩阵下标按 `S[out, in]`。每个非零项是一个复数标量（理想 NBS）或局部偏振基中的 2×2 Jones 块（PBS/非理想 NBS）：

```text
[b1]   [ 0        R_A(2→1)  T_BA(3→1)  0        ] [a1]
[b2] = [ R_A(1→2) 0          0          T_BA(4→2)] [a2]
[b3]   [ T_AB(1→3)0          0          R_B(4→3) ] [a3]
[b4]   [ 0        T_AB(2→4) R_B(3→4)   0        ] [a4]
```

这与 Finesse 官方手册给出的非零位置完全相同。[Finesse 2 官方手册，式 3.48](https://finesse.ifosim.org/finesse2_manual.pdf#page=55) 这里保留方向下标，是为了不在研究阶段越权假定实际 cube 的 A/B 侧系数数值相同。

矩阵的零模式属于几何拓扑，不能被“有限消光比”填满。PBS 的 `T_s` 或 `R_p` 泄漏仍沿原本允许的透射或反射方向离开，不会让光从终端 1 跑到终端 4。只有显式扩展到外表面残余反射、散射或多次内部鬼像模型时，才可新增路径；那应是另一个资格化模型，而不是把结构零改成小数。

当多个允许输入同时存在时，一个输出是相应复振幅的相干和。例如 `b1 = R_A(2→1)a2 + T_BA(3→1)a3`。因此 Michelson 返程必须把两臂返回场作为同一次物理相遇的两个输入处理；先各自调用一个“一入两出分束器”再对强度相加会丢失干涉项。Finesse 的模型图也明确说明一个 BS 端口可同时包含来自一个输入的反射场和另一个输入的透射场。[Finesse 官方 model graph 说明](https://finesse.ifosim.org/docs/latest/getting_started/model_graph.html)

## 相位、膜层侧与互易性

拓扑无法决定相位。即使对理想无损分束器，反射与透射复系数也必须满足能量守恒的相对相位关系；Finesse 官方推导说明常见的“对称”和“反对称”相位规约都能物理一致，并明确把其选择称为 convention。[Finesse 官方相位推导](https://finesse.ifosim.org/docs/develop/usage/plane-waves/beam_splitter.html) 因此，`transmission = real positive`、`reflection = +i times real positive` 可以作为一个完整端口 gauge 下的理想规约，却不能在没有终端参考面和偏振基定义时被宣称为膜层固有相位。

对实际多层膜，A/B 两侧具有相反的表面法向与不同的层序观察方向；反射相位还随波长、入射角、材料和参考面位置变化。Finesse 的官方推导对两侧分别使用介质折射率和折射角，并给出不同的反射相位表达式。[Finesse 官方两侧相位关系](https://finesse.ifosim.org/docs/develop/usage/plane-waves/beam_splitter.html) 原始互易性研究也只在明确的无吸收、折射率沿一维变化等条件下推导两侧复反射/透射系数关系，并非允许把四个复系数不加基变换地设置成同一个数。[Ou 与 Mandel，原始 reciprocity 论文](https://doi.org/10.1364/OAM.1988.WO5)

建议的数值契约是：

- 每个终端拥有明确的参考面、入射方向和右手横向基；
- Element 先把终端横向场转换到该次入射的局部 `s/p` 基；
- 在允许的 `R_A`、`R_B`、`T_AB`、`T_BA` Jones 块上施加复响应；
- 再把结果转换到出射终端的右手横向基；
- 所有反射符号、`p` 轴翻转和端口 gauge 都由这一套基变换统一承担，不能散落在示例里补负号。

COMSOL 官方 Fresnel 文档定义 `s` 为电场垂直入射面，`p` 为电场位于入射面。[COMSOL 官方 Fresnel 方程](https://doc.comsol.com/6.4/doc/com.comsol.help.roptics/roptics_ug_optics.6.64.html) Ansys 进一步指出，没有由传播方向与表面法向确定的入射面，就不能把全局 `Jx/Jy` 直接当作 `s/p`；反射后的右手基选择还会改变 Fresnel 系数的表面符号。[Ansys 官方偏振坐标说明](https://optics.ansys.com/hc/en-us/articles/42661755401747-Investigating-OpticStudio-s-polarization-features) 这正是 Terminal 必须拥有几何帧而 PBS 不能只保存一个全局偏振角的原因。

## PBS 的偏振路由与非理想响应

常见 dielectric cube PBS 在标称入射几何中透射 `p`、反射 `s`。[Newport 官方 broadband PBS 说明](https://www.newport.com/f/broadband-polarizing-cube-beamsplitters?compatibility=METRIC) [Thorlabs 官方 PBS 规格](https://www.thorlabs.com/catalogpages/V21/855.pdf) 在局部 `s/p` 基中，首版可将每条允许路径表示为对角 Jones 块：

```text
T_side = diag(t_s, t_p)    with |t_p| large and |t_s| small
R_side = diag(r_s, r_p)    with |r_s| large and |r_p| small
```

这里的“small”不能默认成零。厂商实际数据给出有限透射效率、有限反射率和有限消光比；例如 Edmund 的一款 780 nm cube PBS 规格为 `T_p > 95%`、`R_s > 99.5%`、消光比 1000:1，而不是数学投影器。[Edmund Optics 官方产品数据](https://www.edmundoptics.com/p/25mm-780nm-laser-line-polarizing-cube-beamsplitter/7104/?PrintPDF=true) 厂商还明确警告 `T_p/T_s` 与 `R_s/R_p` 通常不相等，反射端偏振纯度往往低于透射端。[Edmund Optics 官方 extinction-ratio 说明](https://www.edmundoptics.com/knowledge-center/application-notes/optics/what-are-beamsplitters/)

首版应提供两种**清楚命名而非静默切换**的物理资格：

- `ideal_cube_pbs`：允许路径上的理想 `p` 透射/`s` 反射，正交泄漏为精确零，仍保留终端几何和相位规约；
- `specified_cube_pbs`：由波长/入射角适用域内的复 Jones 系数或经证据支持的参数化响应给出有限泄漏与损耗。

“Nonpolarizing”也不等于完全无偏振响应。Edmund 的官方说明仅承诺某产品系列的 S/P 分光差异小于给定范围；Ansys 的多层膜示例展示了 45° cube coating 的 p 响应与波纹仍是设计难点。[Edmund Optics 官方选择说明](https://www.edmundoptics.com/knowledge-center/video/tutorials/selecting-the-right-beamsplitter/) [Ansys Optics 官方 coating 示例](https://optics.ansys.com/hc/en-us/articles/42661834041363-Common-examples-from-Essential-Macleod-coatings)

对功率归一化的 Wave 模态，理想无损完整散射矩阵应满足 `SᴴS = I`；有吸收或未建模散射的被动元件应满足不增能，而不能只检查每次单输入的 `R + T = 1`。单输入功率闭合不足以检出两路相干输入时错误的相位关系；Finesse 的官方推导正是从任意两路相干输入的能量守恒得到反射/透射相位约束。[Finesse 官方相位推导](https://finesse.ifosim.org/docs/develop/usage/plane-waves/beam_splitter.html)

## 对当前 ChromatixNext 的事实审计

当前实现已诚实限定自己的范围，因此不是“公式写错”，而是尚未拥有本研究所需的几何层：

- [`NonpolarizingBeamSplitter`](../../src/chromatix_next/optics/element/nonpolarizing_beam_splitter.py) 和 [`PolarizingBeamSplitter`](../../src/chromatix_next/optics/element/polarizing_beam_splitter.py) 是一入两出的 lumped Element，端口只有 `transmitted` / `reflected`；文档明确声明反射端不表示 Wave 三维方向、Spatial Grid 姿态或偏振坐标系改变。
- reciprocal 版本是另一个两入两出组件，其输入仍叫 `transmitted` / `reflected`；[`ADR-0012`](../adr/0012-sonnet-combination-and-evidence-contract.md) 明确拒绝引入编号端口或通用 N-port vocabulary。
- [`beam_splitting.py`](../../src/chromatix_next/_numerics/beam_splitting.py) 对所有反射统一使用 `+i`，这是当前理想 lumped gauge；它没有 A/B 膜层侧、终端参考面或方向相关 Jones 块。
- 当前 [`Assembly.include`](../../src/chromatix_next/optics/assembly.py) 拒绝同一组件实例以第二个名称纳入；冻结事实以“一个组件名 = 一个执行步骤”构造。这会迫使 Michelson 的去程分束与返程合束使用两份组件状态，无法表达“同一个 cube、同一膜层姿态、两次有限相遇”。
- Ray 的 `NonpolarizingBeamSplitterAt` / `PolarizingBeamSplitterAt` 已经使用 posed `Plane` 和真实反射方向，后者也构造 Plane-local Jones frame；这是可保留的几何证据。但它们仍是一入两出 surface encounter，没有四个 cube 外部 Terminal，也没有跨多次相遇复用同一个 cube owner。

因此，当前 Wave 版本适合作为“理想无方向分束/混合”低层科学行为，但不能原样升级成“物理 cube BS/PBS”。如果新版规范主张光路可实现性，现有 lumped pair 应被明确保留为窄近似，或由新的四终端 cube Element 原子替代；不能只把端口重命名为 `1/2/3/4` 而继续复制元件状态。

## 对 Element、Terminal 与 Assembly 的架构约束

### Element state owner

一个 cube BS/PBS owner 至少应冻结：

- 器件 pose 与右手局部坐标；
- 对角面选择（本报告首版为 `local_y = local_x`）；
- 膜层法向和带膜棱镜侧；
- 四个 Terminal 的位置、入射方向、参考面和横向基；
- NBS/PBS 响应种类、波长/角度适用域、复 Jones 系数或其证据化参数；
- 外表面/胶层被建模为显式路径、集总损耗，还是明确不声明。

同一 owner 可以在有限路线中出现多次，但 occurrence 不拥有或复制这些状态。

### Terminal

Terminal 不是 `transmitted` / `reflected` branch label。终端是器件上固定的几何位置；透射或反射只在给定 `(input_terminal, output_terminal)` 后才有意义。每个终端同时具有 inward 与 outward 半边方向，Assembly 外部连接必须是一个元件的 outward 到另一个元件的 inward。

### Encounter

一次 encounter 应声明该时刻有哪些终端输入到达同一物理 owner，并一次性计算所有四个输出的相干和。空输出可以不物化，但不能因此改变散射拓扑。Michelson 可以有：

1. 去程 encounter：终端 1 有输入，产生终端 2 和 3 输出；
2. 两臂有限传播与反射；
3. 返程 encounter：终端 2、3 同时有输入，产生终端 1、4 的相干输出。

两次 encounter 共享一个 owner；计算依赖仍是有限无环的，不需要 recurrent root。

### Assembly freeze checks

Assembly 应在执行前至少拒绝：

- 连接到结构零，例如本约定中的 `1 -> 4` 或 `2 -> 3`；
- 把一个终端的 outward 连到另一个终端的 outward，或 inward 连 inward；
- 复用 owner 时改变其对角面、膜层法向、终端编号或 pose；
- 把同一返回时刻的两路相干输入拆成两个互不相知的合束 encounter；
- 在没有显式基变换时把不同传播方向的全局 `Ex/Ey` 当成相同的 `s/p`；
- 在频谱、光源谱系、Optical Path Reference、采样、介质或偏振表示不兼容时合束；
- 请求超出器件波长、角度、功率或入射侧资格的 `specified` 响应；
- 把未建模 AR 鬼像或胶层反射解释为主散射矩阵中的泄漏终端。

Assembly 只检查几何与契约；复系数、Jones 变换和能量/被动性验证仍由 Element/Numerical Support 的单一物理 owner 负责。

## 必须钉住的反事实测试

1. **结构零：** 从终端 1 入射时，终端 4 必须不存在主路径，即使 PBS 具有有限消光泄漏。
2. **四向枚举：** 逐一从 1、2、3、4 入射，核对完整路由表，而不只测常用入射面。
3. **反向复用：** 去程 `1 -> {2,3}` 后，从 3 返回必须得到 `{1,4}`，不能沿用去程的抽象 branch 名。
4. **同一 owner：** 两个 encounter 共享同一可训练/固定 state；任何状态复制或只更新一份都应失败测试。
5. **旋转协变：** 将 cube pose 绕 `local_z` 旋转 90°，局部路由表不变，所有全局方向同步旋转。
6. **翻转膜层侧：** 保持对角几何不变而翻转 coating normal 时，结构零不变，但 A/B 系数、相位和资格侧正确交换。
7. **改变对角线：** 从 `local_y = local_x` 改成另一条对角线时，反射邻接对改变；若只改相位而拓扑不变，测试必须失败。
8. **Michelson 合束：** 终端 2、3 的两路相干返回同时进入一次 encounter，终端 1、4 的复振幅包含正确交叉项并满足亮/暗端口极限。
9. **相位 gauge：** 两套等价端口 gauge 应给出相同可观测强度；只在一个 branch 随意补 `i` 应破坏干涉测试。
10. **PBS 纯态：** 理想模型中局部纯 `p` 只走允许透射终端，纯 `s` 只走允许反射终端。
11. **PBS 泄漏：** specified 模型中 `T_s` 和 `R_p` 只出现在原允许方向，且 `T_p/T_s` 与 `R_s/R_p` 可不同。
12. **偏振基反转：** 从 A/B 两侧及四个终端分别入射，右手终端基与 `s/p` 转换不能因反射方向改变而产生非物理符号。
13. **被动性：** 对随机复四端口双偏振输入验证无损 `SᴴS = I` 或有损不增能；不能只测四个单输入功率和。
14. **规格边缘：** 波长、角度和功率正好位于资格边缘应有确定结论，越界应显式失败而不是退化为 ideal。
15. **非声明鬼像：** 首版 cube 主路径不得悄悄产生外表面反射；未来若开启 thick/ghost 模型，新增路径必须具有独立 provenance 和功率闭合。

## 冻结前仍需所有者裁定

本研究支持四终端 cube seam，但以下内容没有足够通用的一手证据替项目所有者代决：

- 首个 public cube Element 是只提供 ideal response，还是同时接受厂商/测量得到的 specified complex Jones response；
- Wave 的 Terminal 是否立即拥有完整三维 posed reference plane，还是首版只接受正交、共面、准直四路的严格资格；
- 现有 lumped BS/PBS 是保留为明确命名的低层近似，还是原子迁移删除；
- `coating_normal`、`diagonal_orientation`、Terminal 名称采用自然语言枚举还是局部编号；
- 外表面 AR 损耗首版按集总功率损失处理，还是完全不声明并要求系数已包含；
- specified response 的数据来源、插值规则、可微参数范围和序列化格式。

无论这些选择如何，以下结论不应再重开：cube owner 的物理姿态唯一；四终端拓扑稀疏；同一器件的有限复用必须保持原始几何；PBS 泄漏只改变允许路径上的 Jones 系数，不改变结构可达性；拓扑检查与相位/偏振计算不能合并成一个 `transmitted/reflected` 比例参数。
