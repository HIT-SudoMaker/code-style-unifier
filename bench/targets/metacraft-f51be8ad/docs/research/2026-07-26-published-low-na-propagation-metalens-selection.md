---
record_type: research_record
date: 2026-07-26
status: research_finding
authority_level: none
current_capability: false
---

# 首个公开传播相位超透镜：候选比较与受控复现建议

日期：2026-07-26  
文档性质：Research Record；保存一手论文事实、MetaCraft 推导与待人审建议，不构成系统裁决。

## 结论

本轮没有找到一篇可以原封不动变成当前 MetaCraft brief 的论文。最接近首批能力的是 Zhan 等人在 *ACS Photonics* 发表的 633 nm silicon-nitride 传播相位超透镜：

- 它的 500 µm 焦距器件是低 NA、小口径、单波长、圆柱传播相位设计；
- 633 nm 柱高落在当前可见光 `500–800 nm` 包络内，且与离散候选
  650 nm 接近，但 633 nm 本身不是当前高度候选；
- 圆柱、silicon nitride、quartz、标量焦场评估都与当前路线同构；
- 约 112 µm 口径使真实验证仍可在一台工作站上完成。

但论文采用 443 nm 周期、六阶相位量化和接近闭合的最大圆柱。当前 MetaCraft 的物理周期必须在材料资格样本到达后由
`min(sampling ceiling, order ceiling)` 向下取整得到；相位集合必须独立形成 8、12、16 阶；加工规则还同时约束最小柱径与最小间隙。因此推荐的是：

> **Zhan 2016 受控适配复现**：保留论文的器件目标、材料体系、相位机制、焦距与口径；让 MetaCraft 自己决定物理周期、高度选择和 8/12/16 阶相位集合。

这不是论文纳米版图的逐点复刻。它验证的是 MetaCraft 能否从一个公开器件目标，程序化地产生可追溯的单元库、阵面与焦场结果，同时不为论文放松硬边界。

## 调研口径

只比较同行评议论文原文、期刊官方页面和作者公开稿。候选必须是传播相位 metalens，并优先满足：

1. 单个设计波长；
2. low-na 标量角谱法可以诚实评估；
3. silicon nitride on silica/quartz；
4. 圆柱或方柱单元；
5. 已披露焦距、口径、单元高度或周期；
6. 不依赖大 NA、消色差、矢量场或优化器。

“可复现”在本文中分为两层：

- **结构复刻**：周期、高度、单元尺寸和相位阶数均与论文相同；
- **受控适配复现**：器件目标与材料体系来自论文，执行参数仍服从 MetaCraft 当前协议。

两者不得混称。

## 候选比较

| 候选 | 论文明确事实 | 与当前路线的契合 | 不适合作为原样 brief 的原因 |
| --- | --- | --- | --- |
| Zhan et al., *ACS Photonics* 2016 | 633 nm；silicon-nitride 圆柱位于 quartz 上；柱高 633 nm；方格周期 443 nm；半径 96–221 nm；六阶相位；镜片半径 56 µm；制作了 50 µm 至 1 mm 的五种焦距，正文展示 500 µm 器件 | 材料、圆柱传播相位、低 NA、单工作站尺度均吻合；500 µm 器件最适合首个外部验证 | 443 nm 不能绕过本地 order-regime 裁决；六阶不属于 8/12/16 契约；最大圆柱仅留下约 1 nm 名义间隙，不满足当前统一的柱径/间隙加工规则 |
| Zhao et al., *Light: Science & Applications* 2021 | 532 nm 测量；名义 NA 0.196；silicon-nitride 圆柱纳米杆位于 silica 上；柱高 640 nm；传播相位且偏振不敏感；作者以 angular spectrum method 从实测相位重建焦场；PR 样品 Strehl ratio 0.81、DOF 6 µm | 物理机制、材料、低 NA 和 ASM 评估最同构；论文还明确讨论低 NA 时最亮点与相位定义焦距可能偏离 | 可访问正文没有给出 PR 样品的周期、直径库、口径、设计焦距、FWHM 和聚焦效率；正文中的 235 µm 焦距属于另一个理想相位数值例，不能冒充该实验样品 |
| Chen et al., *Optica* 2022 | 470 nm；每个 metalens 焦距 450 µm、口径 300 µm；silicon-nitride 方柱位于 SiO2 上；薄膜厚度 1000 nm；FDTD 选出八个相位状态且各自透射率高于 90%；0° 入射聚焦效率约 65% | 方柱传播相位、八阶集合、FDTD、材料和器件尺度均接近；取阵列中的 0° lens 可得到普通轴上聚焦问题 | 1000 nm 高度超出当前可见光高度域；原始目标是 17 片离轴 lens 的广角阵列与拼接，不是当前单片轴上 route；正文没有用文字披露周期，不能从图像猜写 |

### 候选一：Zhan 2016

论文把 silicon-nitride 圆柱排列在方格上，通过圆柱半径改变传播相位。作者选择设计波长 633 nm，柱高 633 nm，周期
`0.7 wavelength = 443 nm`，圆柱半径 96–221 nm，并以六个线性相位台阶近似 `0–2π`。镜片半径为 56 µm，五个焦距分布在 50 µm 到 1 mm；正文的 SEM 明确展示 500 µm 焦距器件。[期刊官方页面](https://pubs.acs.org/doi/10.1021/acsphotonics.5b00660)；[作者公开稿](https://www2.ee.washington.edu/research/amlab/Papers_Journals/Alan_Zhan_Metasurface.pdf)

论文报告整组器件最高透射效率约 90%、最高聚焦效率约 40%，以及高 NA 样品小于 1 µm 的焦斑；正文进一步说明 500 µm
焦距器件透射效率接近 90%，而约 40% 的最高聚焦效率来自 1 mm 焦距器件。不能把这些整组最大值写成 500 µm 器件的精确指标。

论文补充材料包含 FDTD 结果，但正文和可访问说明没有证明使用的是 Lumerical。因此 `lumerical_fdtd` 只能是 MetaCraft 的本地 realization，不能写成论文事实。

### 候选二：Zhao 2021

论文实验对象包含一个传播相位、偏振不敏感的 PR metalens：532 nm、名义 NA 0.196、640 nm 高 silicon-nitride 圆柱纳米杆、silica
基底。作者从实测相位以 angular spectrum method 重建焦场，并报告 PR metalens 的 Strehl ratio 为 0.81、DOF 为 6 µm。[期刊官方全文](https://www.nature.com/articles/s41377-021-00492-y)

这篇论文对 MetaCraft 的焦场定义尤其重要：作者指出在有限尺寸、低 NA 条件下，光场最亮位置可能偏离由球面波前定义的焦距。该事实支持在
`0.8f–1.2f` 内寻找焦点，而不是只计算名义焦平面。

然而，正文没有足够的版图事实形成 exact brief。特别要避免把作者用于研究有限口径效应的“532 nm、235 µm 焦距理想相位”与实验 PR
metalens 拼接成一个并不存在的论文器件。

### 候选三：Chen 2022

论文的广角相机由 17 个 metalens 组成；每片工作在 470 nm，焦距 450 µm，口径 300 µm。单元是 SiO2 上的 silicon-nitride
方柱，silicon-nitride 薄膜厚度为 1000 nm。作者用 FDTD 选出八种方柱，使相位覆盖 `0–2π` 且每种透射率高于 90%；0° 入射时报告约
65% 的聚焦效率。[Optica 官方页面](https://doi.org/10.1364/OPTICA.446063)；[作者公开稿](https://dsl.nju.edu.cn/litao/papers/Chen_J-optica-9-4-431%282022%29.pdf)

八阶方柱与当前相位集合很接近，但论文的主要功能是离轴分区成像和后续拼接。1000 nm 柱高也不在当前可见光高度域中。为了复现它而扩展高度域或加入离轴 route，会把一次外部验证变成新能力开发，故本轮不推荐。

## Zhan 500 µm 器件的 MetaCraft 推导

以下数值不是论文原句，均由论文尺寸计算：

```text
aperture_diameter = 2 × 56 µm = 112 µm

numerical_aperture
  = 56 / sqrt(56² + 500²)
  ≈ 0.11130

sampling_ceiling
  = 633 nm / (2 × 0.11130)
  ≈ 2843.6 nm

paper_cells_across
  = 112 µm / 443 nm
  ≈ 253
```

因此它在几何上属于明确的 low-na 器件；sampling ceiling 不是限制因素。物理周期仍必须等待 qualification-admitted 的 quartz/silica
折射率样本后，由 order ceiling 决定。

若要保留论文的 443 nm 周期，样本必须满足：

```text
substrate_index
  <= 633 / 443 - 0.11130
  ≈ 1.3176
```

本文没有读取或制造 solver-native 材料样本，因此不在研究记录中宣告最终 period verdict。实际 conduct 必须让资格样本和现有
order-regime 规则裁决；不得把 443 nm 作为 brief 输入覆盖它。

## 推荐的 exact brief

这里的 “exact” 指用户目标字段完整，不表示论文纳米版图的原样复刻。

### 自然语言 brief

> Aim: metalens. Reproduce the low-na device target represented by the 500 µm focal-length lens in Zhan et al., ACS Photonics 2016. Focus 633 nm light at 500 µm with NA 0.11130. Use propagation phase, normal x-linear incidence, and circular silicon-nitride pillars on a silica substrate, both from Lumerical FDTD's solver-native material library. Keep the aspect ratio and the inter-pillar gap at the current 8:1 fabrication limit. Let MetaCraft derive the physical period from its admitted material sample and form independent 8-, 12-, and 16-state phase sets; use the eight-state result as the primary paper-adaptation comparison. Prefer Lumerical FDTD and budget execution for one local workstation. Omit large-NA evaluation, multiwavelength operation, off-axis operation, optimization, and the paper's six-state/443 nm layout.

### 结构化字段

```text
name                  = zhan-2016-adapted-propagation-633nm-f500um
aim                   = metalens
objectives            = focus
wavelength_nm         = 633
numerical_aperture     = 0.11130
focal_length_um        = 500
polarization           = linear, x
phase_method           = propagation
atom.shape             = circular pillar
atom.material          = silicon_nitride, solver_native
substrate              = silica, solver_native
aspect_limit           = 8
solver_preference      = lumerical_fdtd
budget                 = workstation
omissions              = large_na, multiwavelength, off_axis, optimization
```

高度不写入 brief。AI 只能在该 brief 编译出的有限 height domain 中推荐一个高度；确定性程序验证推荐，随后真实单元证据才可形成相位集合。

## 执行时应比较什么

### 可以直接比较

- 设计波长：633 nm；
- 器件焦距目标：500 µm；
- 器件口径：由 `f` 与 `NA` 恢复为约 112 µm；
- 材料体系与圆柱传播相位机制；
- found focus 是否落在 `400–600 µm` 的完整评估区间；
- 实现阵面的 x/y FWHM、depth 和焦移；
- MetaCraft 自己定义并完整记录的 transmission ratio 与 concentration ratio。

### 必须分开报告

- 论文六阶与 MetaCraft 8/12/16 阶的差异；
- 论文 443 nm 周期与 MetaCraft admission 后物理周期的差异；
- 论文 633 nm 柱高与 AI 最终推荐高度的差异；
- 论文效率定义与 MetaCraft transmission/concentration 两个比值的差异；
- 论文 nominal radii 与 MetaCraft 加工边界内实际圆柱直径的差异。

### 当前缺失，不能伪造

- 500 µm 论文器件的精确 FWHM 数值；
- 500 µm 论文器件的精确聚焦效率数值；
- 六个论文圆柱各自的复数透射系数和原始相位误差；
- 论文 FDTD 的产品、版本、脚本和网格；
- 论文 silicon-nitride 与 quartz 的可移植色散数据；
- 原始版图与逐点加工尺寸；
- 与 MetaCraft concentration ratio 完全相同的论文效率口径。

这些缺失意味着首次实验只能做**受控适配验证**，不能声称逐点复现论文。

## 人审门

建议用户只审核以下选择：

1. 是否接受 Zhan 2016 的 500 µm 器件作为首个外部目标；
2. 是否接受“受控适配复现”而不是“原样结构复刻”这一名称；
3. 是否接受八阶结果作为主比较，同时保留 12/16 阶诊断；
4. 是否接受论文效率只作背景，不把 90%/40% 写成该器件的验收阈值。

在用户确认前，不新增 example，不改 period law、加工规则、phase coverage law 或 Authority protocol，也不启动求解器。

## 一手来源

1. Alan Zhan et al., “Low-Contrast Dielectric Metasurface Optics,” *ACS Photonics* 3, 209–214 (2016), DOI 10.1021/acsphotonics.5b00660. [ACS official page](https://pubs.acs.org/doi/10.1021/acsphotonics.5b00660); [author manuscript](https://www2.ee.washington.edu/research/amlab/Papers_Journals/Alan_Zhan_Metasurface.pdf)
2. Maoxiong Zhao et al., “Phase characterisation of metalenses,” *Light: Science & Applications* 10, 52 (2021), DOI 10.1038/s41377-021-00492-y. [publisher full text](https://www.nature.com/articles/s41377-021-00492-y)
3. Ji Chen et al., “Planar wide-angle-imaging camera enabled by metalens array,” *Optica* 9, 431–437 (2022), DOI 10.1364/OPTICA.446063. [Optica official page](https://doi.org/10.1364/OPTICA.446063); [author manuscript](https://dsl.nju.edu.cn/litao/papers/Chen_J-optica-9-4-431%282022%29.pdf)
