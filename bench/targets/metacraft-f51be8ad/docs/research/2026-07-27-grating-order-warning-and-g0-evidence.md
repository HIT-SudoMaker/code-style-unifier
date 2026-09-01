---
record_type: research_record
date: 2026-07-27
status: research_finding
authority_level: none
current_capability: false
---

# 光栅阶次警告与 G0 证据边界

## 结论

MetaCraft 不应再用 `order ceiling` 拒绝一条设计路线，但应保留它所揭示的物理风险，并把原来混在一起的含义拆成两条自然、可追溯的警告：

1. **输出侧多阶警告**：输出介质允许非零传播阶次时，G0 仍是定义良好的一个复振幅通道，但它不再代表完整输出场，也不能独自证明总透射、聚焦效率或杂散光表现。
2. **基底侧阶次泄漏警告**：在 MetaCraft 声明的基底入射方向下，基底侧允许的非零阶次属于反射或回返泄漏通道。它们可能损失效率、在基底中全反射或形成返回路径，却不会令输出侧 G0 相位失去定义。

局部相位采样是另一件事。`period <= wavelength / (2 numerical_aperture)` 仍应是当前小 NA 局部周期近似路线的硬边界；阶次警告不应改变它，也不能被它取代。

因此，当前裁决具有清晰的物理语义：

- `sampling ceiling` 保持硬约束；
- 物理周期继续由采样上限向下取整得到；
- `order ceiling` 降为非阻塞警告；
- 不为消除警告而机械地更换主波长；
- 一旦警告出现，结果必须记录各侧允许的传播阶次以及 G0 证据的适用范围。

## 四个不应再混淆的问题

### 1. 局部相位采样

Ansys 的 metalens 工作流给出

```text
numerical_aperture <= wavelength / (2 unit_cell_period)
```

它约束的是离散超原子阵列对目标相位分布的采样，而不是“只允许零级光栅阶次”。同一官方工作流也指出，局部周期近似把每个单元当作无限周期阵列；相邻单元变化过快时，单元间耦合不能被准确表示。[Ansys, *Introduction to metalens workflows*](https://optics.ansys.com/hc/en-us/articles/35797097445779-Introduction-to-metalens-workflows)

所以采样上限回答的是：

> 这个晶格是否足够细，可以承载目标相位梯度？

它不回答输出能量最终落在哪些光栅阶次。

### 2. 输出侧非零传播阶次

周期结构的场可分解为离散平面波阶次。对于横向周期 `period_x`、`period_y`，每一阶的横向波矢由入射横向波矢与倒格矢共同决定；只有总波矢在所在介质光锥内的阶次才能传播。介质折射率因此直接决定哪些阶次开放。[Ansys, *Grating projections in FDTD — overview*](https://optics.ansys.com/hc/en-us/articles/360034394354-Grating-projections-in-FDTD-overview)

输出侧允许非零传播阶次时，完整输出场是所有开放阶次复振幅的叠加。Byrnes 等人在高偏折超表面设计中也显式地对每个传播衍射阶次求复振幅，而不是把单个阶次视作完整出射场。[Byrnes et al., 2016](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/2016_byrnes_et_al_1.pdf)

所以输出侧警告回答的是：

> G0 是否仍足以代表准备交给阵面传播模型的完整输出场？

允许非零阶次只表示这些通道在运动学上开放，并不表示它们必然获得显著功率；实际占比仍需由求解器证据给出。

### 3. 基底侧反射泄漏

一个阶次可能在高折射率基底中传播，却在低折射率输出介质中成为倏逝波。Byrnes 等人将这类基底传播、空气侧不传播的通道视为损失；它们还可能在基底背面发生全反射。[Byrnes et al., 2016](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/2016_byrnes_et_al_1.pdf)

在 MetaCraft 当前声明的“基底朝向纳米柱”入射方向中，基底侧开放的非零阶次属于反射侧泄漏。它们影响能量守恒、效率与基底返回路径，却不是输出侧 G0 相位是否存在的判据。

所以基底侧警告回答的是：

> 是否存在未被输出 G0 表述的反射或基底回返通道？

它不应被写成“相位库无效”或“路线不可行”。

### 4. G0 证据本身

Ansys 的 S 参数分析使用光栅投影，并通过 `target_grating_order_out` 隔离指定输出阶次。所得 S 参数是经过参考平面补偿的复振幅，而不是天然等同于总功率；不同入射、输出折射率下，复振幅模平方也不能直接当作功率。[Ansys, *Metamaterial S parameter extraction*](https://optics.ansys.com/hc/en-us/articles/360042095873-Metamaterial-S-parameter-extraction)

因此，指定 G0 的 `grating_s_params` 证据可以诚实地表示：

- 指定传播方向、偏振与零级通道的复振幅；
- 该通道相对于明确参考面的相位；
- 在采用正确功率归一化后，该通道的功率份额。

它不能独自表示：

- 所有阶次相加后的总透射场；
- 总透射率或总反射率；
- 非零阶次不存在；
- 完整口径的聚焦效率与杂散光；
- 局部周期近似在相邻异构单元间仍然成立。

Ansys 的小尺寸 metalens 示例也只建议在改变周期或波长时尽量避免多光栅阶次，因为它们会使设计更复杂；官方措辞不是把多阶状态定义为绝对不可行。该工作流使用单元近场库拼接整镜场，也比单独保留一个 G0 系数包含更多输出信息。[Ansys, *Small-Scale Metalens — Field Propagation*](https://optics.ansys.com/hc/en-us/articles/360042097313-Small-Scale-Metalens-Field-Propagation)

## MetaCraft 推导

以下公式和数值是由上述传播条件推导所得，不是外部文献直接给出的 MetaCraft 规则。

### 三种上限具有不同语义

对于自由空间波长 `wavelength`、数值孔径 `numerical_aperture`、输出介质折射率 `output_index = 1` 和基底折射率 `substrate_index`：

```text
sampling_ceiling
    = wavelength / (2 numerical_aperture)

output_order_warning_ceiling
    = wavelength / (output_index + numerical_aperture)

substrate_order_warning_ceiling
    = wavelength / (substrate_index + numerical_aperture)
```

第一式是相位采样上限。后两式是把全口径最大目标横向波矢与相邻倒格点光锥相比较所得的保守警告界；它们不是标准文献中的统一“可行性公式”。

对于法向入射、方形周期单元，某侧允许传播的整数阶次满足

```text
order_x² + order_y²
    <= (medium_index * unit_cell_period / wavelength)²
```

这是单元仿真中开放通道的计数。它与全口径最大相位梯度的保守警告不是同一个量，记录中必须明确使用了哪一种判断。

### 当前 brief

355 nm 与 400 nm 的二氧化硅折射率来自当前求解器材料采样记录；633 nm 使用 Malitson 的熔融石英 Sellmeier 式，计算得 `substrate_index = 1.457012`。[Malitson, 1965](https://ptacts.uspto.gov/ptacts/public-informations/petitions/1557520/download-documents?artifactId=-B8TovtlLNvhTq_vb42O3RlHQ0uxezxKGrfbCYkXCm8gsBtJDDSdvCs)

| 设计 | NA | 使用周期 | 采样上限 | 输出侧警告界 | 基底侧警告界 | 法向输出开放阶次 | 法向基底开放阶次 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 355 nm brief | 0.28 | 630 nm | 633.9 nm | 277.3 nm | 202.2 nm | 9 | 21 |
| 400 nm brief | 0.30 | 660 nm | 666.7 nm | 307.7 nm | 226.0 nm | 9 | 21 |
| Zhan 633 nm 论文结构 | ≈0.1113 | 443 nm | 2843.7 nm | 569.6 nm | 403.6 nm | 1 | 5 |
| 633 nm 若取采样上限并向下取整 | ≈0.1113 | 2840 nm | 2843.7 nm | 569.6 nm | 403.6 nm | 69 | 137 |

表中“开放阶次”包含 G0，而且只表示允许传播的通道数量，不表示各阶次实际获得的功率。

Zhan 等人的公开结构采用 633 nm、443 nm 周期、633 nm 高的氮化硅柱和石英基底；其示例焦距与口径对应约 0.1113 的 NA。[Zhan et al., 2016](https://lamarr.ece.uw.edu/research/amlab/Papers_Journals/Alan_Zhan_Metasurface.pdf) 对该几何进行阶次计数可见：

- 空气侧在法向周期单元中只有 G0 可传播；
- 石英侧在运动学上允许 G0 和四个轴向一阶通道；
- 在 MetaCraft 的基底入射约定下，后者应记为可能的反射侧泄漏，而不是输出场的额外通道；
- 这些通道是否真的获得显著功率，必须由分阶功率证据确认。

这项已发表结构说明，严格的“基底侧只允许 G0”并不是所有成功 metalens 的普适硬门槛。它也说明论文选择的 `0.7 wavelength` 周期远小于其低 NA 采样上限；把采样上限直接取为物理周期是 MetaCraft 的系统策略，不是由采样定理强制的唯一选择。

### 更换波长不能普遍消除警告

当系统始终取

```text
unit_cell_period ≈ wavelength / (2 numerical_aperture)
```

时，归一化周期近似为

```text
unit_cell_period / wavelength
    ≈ 1 / (2 numerical_aperture)
```

因此开放阶次的数量主要由 NA 和两侧折射率决定，而不是由绝对波长决定。把 355 nm brief 换成 633 nm、同时仍把周期取到采样上限，不会自动回到单阶状态；上表中的 69 与 137 个开放通道正是反例。

更换主波长只有在材料、制造、目标相位、周期选择或求解路线也随之改变时才具有设计意义。它不应被当作清除阶次警告的机械修复。

## 建议的警告语义

### 输出侧多阶

```text
multiple_output_orders_possible

当前周期允许非零输出阶次传播。所选 G0 系数仍可描述零级输出
通道，但不能代表总输出场，也不能独自证明总透射或聚焦效率。
```

### 基底侧泄漏

```text
substrate_order_leakage_possible

当前周期允许非零基底侧阶次传播。在声明的基底入射方向下，
这些通道属于反射或回返泄漏；它们可能降低效率，但不会令
输出 G0 相位失去定义。
```

两条警告可以同时出现，也可以分别出现。不得重新合并成一个含义模糊的 `order_violation`。

## 警告出现时的最小证据

每次运行至少应留下：

- 波长、物理周期与入射方向；
- 入射侧、输出侧折射率及其来源；
- 输出侧与反射侧分别允许的传播阶次列表或计数；
- 求解器实际选择的目标阶次；
- G0 的复振幅与参考平面；
- G0 功率份额及其归一化方法；
- 总透射功率与总反射功率；
- 若求解器可得，各开放阶次的功率分布与未闭合能量；
- 触发的是输出侧多阶警告、基底侧泄漏警告，还是两者；
- 下游阵面重建是否只使用 G0，以及由此排除的通道。

只有 G0 数据时，MetaCraft 仍可把它用于“零级相位候选”的比较，但产物必须自称 **G0 约化证据**，不能自称完整单元响应或完整口径场证据。

## 对当前实现方向的建议

1. 保持 `sampling ceiling` 为路线资格硬边界。
2. 继续按已裁决策略从采样上限向下取整得到当前物理周期。
3. 将输出侧和基底侧阶次条件分别作为非阻塞警告。
4. 不通过更换波长来掩盖警告。
5. 当前 355 nm 与 400 nm brief 可以继续运行，但 G0-only 结果必须明确降格为约化证据。
6. 后续若要从“G0 相位库”提升为“完整输出证据”，优先补充分阶功率或求解器近场，而不是重新发明一个硬拒阈值。
7. 将来可以允许研究路线显式选择小于采样上限的周期；这属于周期选择策略的扩展，不改变采样上限本身。

## 来源

- [Ansys — Introduction to metalens workflows](https://optics.ansys.com/hc/en-us/articles/35797097445779-Introduction-to-metalens-workflows)
- [Ansys — Small-Scale Metalens: Field Propagation](https://optics.ansys.com/hc/en-us/articles/360042097313-Small-Scale-Metalens-Field-Propagation)
- [Ansys — Grating projections in FDTD: overview](https://optics.ansys.com/hc/en-us/articles/360034394354-Grating-projections-in-FDTD-overview)
- [Ansys — Metamaterial S parameter extraction](https://optics.ansys.com/hc/en-us/articles/360042095873-Metamaterial-S-parameter-extraction)
- [Byrnes et al. — Designing large, high-efficiency, high-numerical-aperture, transmissive meta-lenses for visible light](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/2016_byrnes_et_al_1.pdf)
- [Zhan et al. — Low-contrast dielectric metasurface optics](https://lamarr.ece.uw.edu/research/amlab/Papers_Journals/Alan_Zhan_Metasurface.pdf)
- [Malitson — Interspecimen comparison of the refractive index of fused silica](https://ptacts.uspto.gov/ptacts/public-informations/petitions/1557520/download-documents?artifactId=-B8TovtlLNvhTq_vb42O3RlHQ0uxezxKGrfbCYkXCm8gsBtJDDSdvCs)
