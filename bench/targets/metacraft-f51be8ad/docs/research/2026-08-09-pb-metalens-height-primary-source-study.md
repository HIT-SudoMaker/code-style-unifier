---
record_type: research_record
date: 2026-08-09
status: research_finding
authority_level: none
current_capability: false
---

# 局域介质 PB 透射型超透镜高度：一手文献核验

## 研究问题

本记录回答两个窄问题：

1. 已实验实现的局域介质 Pancharatnam--Berry（PB）/几何相位透射型超透镜，其纳米鳍、纳米梁或各向异性柱高度处于什么量级？
2. MetaCraft 为 `1550 nm` silicon PB 单元生成 `800--900 nm` 高度候选，是否有物理与文献上的合理性？

本文优先采用论文正文、正式补充材料、作者公开稿或出版社全文。综述只用于发现论文，不作为尺寸参数的最终依据。归一化高度均由本文用论文给出的真空波长计算：

```text
normalized_height = meta_atom_height / vacuum_wavelength
```

## 结论先行

1. **`800--900 nm` 对 `1550 nm` silicon PB 是合理的保守搜索带，但不是文献证明的唯一或最优带。** 它对应 `h/lambda = 0.516--0.581`，处在已实验验证的局域高折射率介质 PB 设计空间内部。本文样本中，高折射率 Si/a-Si/c-Si PB 单元从约 `0.21 lambda`（Yang 2018、Liu et al. 2024）到 `0.75 lambda`（Chantakit 2020），甚至 `0.94 lambda`（Liang 2018）均有实验实现。
2. **Yang 的 `340 nm` 与 MetaCraft 的 `800--900 nm` 不是一真一假的关系。** Yang 用 `1350 nm x 480 nm` 的强横向各向异性，在很短的传播长度内获得所需 Jones 本征通道差异；较高的柱允许用较小的有效双折射取得近半波延迟，可能扩大横向几何搜索余量，但会增加刻蚀、纵模、Fabry--Perot 振荡与邻近耦合风险。
3. **现有样本不支持把 `0.2--0.6 lambda` 写成 PB 的普适允许范围。** 该区间覆盖 Yang、Liu 2024 和三组 Ge 中红外样本，却排除了本文大量 TiO2、c-Si、a-Si 与 SiNx 实验器件。材料折射率、基底、横截面、period、目标偏振转换率和加工能力必须进入高度先验的上下文。
4. **高度没有独立的物理硬门槛。** PB 单元的资格门应是由完整 Jones 响应证明的交叉手性转换、同手性泄漏、总透射与带宽/角度稳定性；`h/lambda` 只能生成和排序候选，不能单独证明单元合格。
5. **样本频数不能冒充规则。** 表中多个 `600 nm` TiO2 结果来自同一 Harvard ALD 工艺平台，彼此不是独立的统计抽样；中位数或直方图会被研究平台重复使用严重偏置。

## 可比范围

纳入：

- 透射型；
- 介质或半导体各向异性 meta-atom；
- 旋转相同横截面主要提供 `2 theta` 几何相位；
- 论文实际制造并测量了聚焦、成像或对应偏振转换；
- 每个采样点有明确高度。

单列而不用于核心判断：反射型、金属/等离激元、非局域/高 Q、纯传播相位、纯 Huygens、逆设计 metagrating、宽带消色差或同时用尺寸编码传播相位的混合路线。

### Pure PB / hybrid 分类

| 分类 | 本文判据 | 核心表中的样本 |
| --- | --- | --- |
| pure local PB | 横截面与高度固定，位置间主要改变面内旋转角，以 `2 theta` 编码相位 | #1--4、#6--17，共 16 个器件点 |
| composite pure-PB cell | 一个 cell 内组合多个固定 PB 子单元，但各子单元仍以旋转角编码几何相位 | #5，共 1 个器件点；单列解释，不与单 fin 效率直接合并 |
| hybrid propagation + PB | 同时改变横向尺寸与旋转角，以传播相位和几何相位共同编码 | 核心表 0 项；排除在 `1550 nm / 800--900 nm` 裁决之外 |

因此，下表 17 个器件点均可用于观察局域 PB 高度尺度；其中 #5 是复合 cell，统计解释时不能假装成独立的单鳍 PB 样本。混合相位器件只作为不可直接比较边界记录。

## 一手样本表

`NR` 表示可访问的一手正文没有以可复用数值披露该字段；本文不从 SEM 比例尺反推。

| # | 论文与器件 | lambda | 材料 / 基底 | period | height | 关键横向尺寸 | h/lambda | 控制机制 | 论文的性能口径 | 参数原文位置 |
| ---: | --- | ---: | --- | ---: | ---: | --- | ---: | --- | --- | --- |
| 1 | Lin et al., *Science* (2014), dielectric gradient metalens | 550 nm | poly-Si / quartz | 约 200 nm nanobeam spacing | 100 nm | beam width 120 nm；连续 nanobeam，不是孤立柱 | 0.182 | 旋转纳米梁的 geometric phase | 论文展示 RCP→LCP 聚焦；本记录未提取到与后续论文同口径的 focusing efficiency | [作者稿正文与补充材料，metalens 及 waveplate 设计](https://hasman.technion.ac.il/files/2017/04/298.full_.pdf)，DOI [10.1126/science.1253213](https://doi.org/10.1126/science.1253213) |
| 2 | Khorasaninejad et al., *Science* (2016), blue metalens | 405 nm | TiO2 / glass | 200 nm square | 600 nm | W 40 nm, L 150 nm | 1.481 | 单一 nanofin 旋转，近半波片 | focusing efficiency 86%；论文也定义 unit conversion 为反手性透射功率 / 入射功率 | [正文 Fig. 1F caption、Fig. 2、Fig. 3](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf)，DOI [10.1126/science.aaf6644](https://doi.org/10.1126/science.aaf6644) |
| 3 | 同论文，green metalens | 532 nm | TiO2 / glass | 325 nm square | 600 nm | W 95 nm, L 250 nm | 1.128 | 同上 | focusing efficiency 73% | 同上，Fig. 1F caption 明列 `W/L/H/S` |
| 4 | 同论文，red metalens | 660 nm | TiO2 / glass | 430 nm square | 600 nm | W 85 nm, L 410 nm | 0.909 | 同上 | focusing efficiency 66% | 同上，Fig. 1F caption 明列 `W/L/H/S` |
| 5 | Khorasaninejad et al., *Nano Letters* (2016), multispectral chiral lens | 530 nm design point | TiO2 / glass | building block Sx 300 nm, Sy 600 nm，含两根 fin | 600 nm | W 80 nm, L 250 nm | 1.132 | 两根局域 PB nanofin 分别编码两种手性 | 论文展示手性分离成像；其复合 cell 口径不可与单 fin focusing efficiency 直接合并 | [出版社正文 Fig. 1 caption](https://pubs.acs.org/doi/10.1021/acs.nanolett.6b01897)，DOI [10.1021/acs.nanolett.6b01897](https://doi.org/10.1021/acs.nanolett.6b01897) |
| 6 | Chen et al., *Nano Letters* (2017), 405-nm oil-immersion metalens | 405 nm | TiO2 / cover glass | 150 nm | 600 nm | W 60 nm, L 120 nm | 1.481 | rotated half-wave nanofin | 论文用 diffraction-limited spot 与 Strehl > 0.8 评价油浸镜；不要把 Strehl 当效率 | [作者公开稿 Results，design parameters paragraph](https://projects.iq.harvard.edu/files/capasso/files/acs.nanolett.7b00717.pdf)，DOI [10.1021/acs.nanolett.7b00717](https://doi.org/10.1021/acs.nanolett.7b00717) |
| 7 | 同论文，532-nm water/oil-immersion metalens | 532 nm | TiO2 / cover glass | 240 nm | 600 nm | W 80 nm, L 220 nm | 1.128 | 同上 | water-immersion Strehl 约 0.9；论文明确指出 period 减小时可增加 `L/W` 或高度以维持 conversion | 同上，design paragraph 与 Fig. 2/3 |
| 8 | Groever et al., *Nano Letters* (2017), visible meta-lens doublet | 532 nm | TiO2 / fused-silica double-sided substrate | 320 nm hexagonal spacing | 600 nm | W 95 nm, L 250 nm | 1.128 | 两层均由旋转 nanofin 实现局域 PB phase | doublet 最大 focusing efficiency 约 50% | [作者公开稿 Fig. 1 caption 与正文结论](https://murimetasurfaces.hsites.harvard.edu/sites/g/files/omnuum8691/files/muri_metasurfaces/files/acs.nanolett.7b01888.pdf)，DOI [10.1021/acs.nanolett.7b01888](https://doi.org/10.1021/acs.nanolett.7b01888) |
| 9 | Liang et al., *Nano Letters* (2018), ultra-high-NA c-Si metalens | 532 nm | c-Si / sapphire | 220 nm | 500 nm | W 20 nm, L 160 nm | 0.940 | 相同 c-Si nanobrick 旋转；HOA 优化固定 cell | measured focusing efficiency 67% in air；front-oil immersion 48% | [作者稿 p. 8 optimized geometry 与 p. 10--12 fabrication/results](https://eprints.whiterose.ac.uk/id/eprint/134118/1/Ultrahigh_Numerical_Aperture_Metalens_at_Visible_Wavelengths.pdf)，DOI [10.1021/acs.nanolett.8b01570](https://doi.org/10.1021/acs.nanolett.8b01570) |
| 10 | Yang et al., *Nature Communications* (2018), circular-polarization sub-metalens | 1550 nm | silicon / silicon dioxide | 1500 nm square | 340 nm | ellipse major 1350 nm, minor 480 nm | 0.219 | 固定椭圆柱旋转；两本征轴 Jones 通道近半波关系 | circular-polarization focusing：theoretical 60%，measured 26%；整套阵列平均口径另有差异 | [出版社正文 Results、Fig. 2](https://www.nature.com/articles/s41467-018-07056-6)，[PMC 全文与 SI](https://pmc.ncbi.nlm.nih.gov/articles/PMC6214988/)，DOI [10.1038/s41467-018-07056-6](https://doi.org/10.1038/s41467-018-07056-6) |
| 11 | Wang et al., *AIP Advances* (2019), Ge PB lens | 3 um | Ge / Ge substrate | 1.3 um | 1.5 um | W 0.427 um, L 1 um | 0.500 | etched Ge nanofin 旋转，half-wave retardance | 三个设计模拟 focusing efficiency 约 80%；实验绝对效率的详细光谱只对 5-um lens 展示 | [出版社全文 Table I、Fig. 1](https://doi.org/10.1063/1.5124074) |
| 12 | 同论文 | 5 um | Ge / Ge substrate | 3 um | 1.5 um | W 0.55 um, L 2.5 um | 0.300 | 同上 | 5 um 实测 absolute focusing 约 33%；以未镀膜 Ge wafer 45% transmittance 归一后约 73% | 同上，Table I 与 Fig. 5 discussion |
| 13 | 同论文 | 8 um | Ge / Ge substrate | 5 um | 2.5 um | W 0.85 um, L 4 um | 0.313 | 同上 | simulated focusing 约 80%；实测 diffraction-limited trend | 同上，Table I 与 Fig. 4 |
| 14 | Chantakit et al., *Photonics Research* (2020), metalens optical tweezers | 800 nm | a-Si / glass | 360 nm | 600 nm | L 200 nm, W 120 nm | 0.750 | 固定 a-Si nanofin 旋转，RCP↔LCP PB focusing | diffraction efficiency 82.1/83.7% 定义为反手性一阶 / 总透射；乘 transmission 后 overall conversion 70.8% | [作者预印本 Methods §2.1 与 efficiency paragraph](https://arxiv.org/pdf/2009.10382)，DOI [10.1364/PRJ.389200](https://doi.org/10.1364/PRJ.389200) |
| 15 | Wang et al., *Nanomaterials* (2021), metalens eyepiece | 532 nm | Si3N4 / quartz | 400 nm | 400 nm | L 300 nm, W 105 nm | 0.752 | fixed nanofin PB phase | measured focusing efficiency 15.7%，定义为直径 `3 x FWHM` 圆内功率 / 入射功率；simulated PCE 24.3% | [出版社全文 §2.1 与 §3](https://www.mdpi.com/2079-4991/11/8/1920)，DOI [10.3390/nano11081920](https://doi.org/10.3390/nano11081920) |
| 16 | Fan et al., *Advanced Photonics* (2022), chip-scale metalens microscope | 470 nm | SiNx / fused silica | 300 nm | 1000 nm | L 240 nm, W 95 nm | 2.128 | fixed high-aspect-ratio nanofin PB phase | unit-cell simulated PCR 99%；PCR 定义为反手性透射功率 / 入射功率，不是整镜 focusing efficiency | [出版社全文 Eq. (1) 后的 unit-cell paragraph](https://www.spiedigitallibrary.org/journals/advanced-photonics/volume-4/issue-04/046006/Chip-scale-metalens-microscope-for-wide-field-and-depth-of/10.1117/1.AP.4.4.046006.full)，DOI [10.1117/1.AP.4.4.046006](https://doi.org/10.1117/1.AP.4.4.046006) |
| 17 | Liu et al., *Light: Science & Applications* (2024), NIR phase-characterization metalens | 1560 nm | a-Si / silica | NR | 327 nm | crescent pillar；正文未给可复用 lateral dimensions | 0.210 | crescent pillar rotation supplies geometric phase | defect-free sample focusing efficiency 0.51，defective sample 0.27；正文未把该值与其他论文的积分孔径统一 | [出版社全文 Experiment 与 Methods: Design and fabrication of NIR metalens](https://www.nature.com/articles/s41377-024-01530-1)，DOI [10.1038/s41377-024-01530-1](https://doi.org/10.1038/s41377-024-01530-1) |

## 如何读这张表

### 绝对高度不是跨波段指标

同样是 `600 nm`：

- 对 405-nm TiO2 PB 是 `1.48 lambda`；
- 对 532-nm TiO2 PB 是 `1.13 lambda`；
- 对 660-nm TiO2 PB 是 `0.91 lambda`；
- 对 800-nm a-Si PB 是 `0.75 lambda`。

所以“PB 柱通常高 600 nm”不是可迁移规则。波长归一化更好，但仍需材料与横截面上下文。

### `0.2--0.6 lambda` 只描述一种紧凑 PB 分支

本文 17 个明确器件点的跨度约为 `0.18--2.13 lambda`。其中：

- 约 `0.18--0.22 lambda`：Lin、Yang、Liu 2024，依赖连续纳米梁或强各向异性/复杂 crescent 横截面；
- 约 `0.30--0.50 lambda`：Ge 中红外 PB；
- 约 `0.75--0.94 lambda`：a-Si、Si3N4、c-Si 的多个可见/NIR PB；
- 约 `0.91--1.48 lambda`：Harvard TiO2 visible PB 平台；
- `2.13 lambda`：低折射率 SiNx、470-nm 高转换的高纵横比实现。

这些是不同材料、工艺与器件目标下的优化值，不是一个连续分布的随机样本。特别是多个 TiO2 点共享材料堆栈与 ALD 工艺，不能用样本中位数建立默认规则。

## Yang 340 nm 与 MetaCraft 800--900 nm 的物理比较

对理想化双折射波导，近半波延迟的一阶估算为：

```text
delta_phase ≈ (2 pi / lambda) * height * delta_n_eff ≈ pi

therefore

required_delta_n_eff ≈ lambda / (2 * height)
```

在 `lambda = 1550 nm` 时：

| height | h/lambda | 一阶所需 delta_n_eff |
| ---: | ---: | ---: |
| 340 nm | 0.219 | 2.28 |
| 800 nm | 0.516 | 0.97 |
| 850 nm | 0.548 | 0.91 |
| 900 nm | 0.581 | 0.86 |

这张表只是一阶解释，不是 qualification。它揭示了两个不同设计姿态：

```text
Yang compact branch
  short height
  + strong lateral anisotropy (1350 x 480 nm)
  + paper-optimized Jones response

MetaCraft conservative branch
  longer height
  + lower required effective birefringence
  + potentially broader lateral geometry room
  - higher etch and longitudinal-mode risk
```

因此：

- `800--900 nm` 并不“过高到明显错误”；对 silicon 它是可信的初始搜索带。
- `340 nm` 也不“过低到不可靠”；它是论文实际联合优化出的紧凑解。
- 没有同波长、同材料、同基底、同 period、同横截面、同加工约束的一手比较，不能声称 `800--900 nm` 比 `340 nm` 更优。
- MetaCraft 当前只提供 `800, 850, 900 nm` 时，问题不是这些点不合理，而是它没有同时表达“这是一条保守分支”，也没有允许 compact branch 或让 Jones evidence 申请扩大候选域。

## 对 MetaCraft 高度先验的最小建议

### 不应写成物理门

```text
height prior
  -> generate feasible candidates
  -> estimate fabrication and modal risk
  -> run sparse Jones qualification
  -> select or request domain expansion
```

高度候选不能直接产出“PB 有效”结论。真正的 PB 资格至少需要：

- 两本征轴复透射 `t_x`, `t_y`；
- retardance 是否接近奇数阶 `pi`；
- cross-helicity conversion；
- co-helicity leakage；
- total transmission；
- 对 width/length、波长、角度与加工扰动的稳定性。

### 对 1550-nm silicon 的可实施表达

不建议把 universal PB prior 从 `0.2--0.6 lambda` 简单改成另一个单区间。更清楚的是两段候选：

```text
compact branch
  about 0.2--0.4 lambda
  only when large lateral anisotropy and fabrication geometry are feasible

conservative branch
  about 0.45--0.8 lambda
  favors lower required effective birefringence

both branches
  remain recommendations until Jones-qualified
```

对当前 Yang-like brief：

- 保留 `800, 850, 900 nm` 作为 conservative candidates 是合理的；
- 如果目标是现实案例覆盖而不是论文参数复刻，可把较低候选作为一次 domain-expansion option，而不是强行把 `340 nm` 注入 blind brief；
- 若用户明确提交论文 cell，则按 reproduction contract 固定 `340 nm`，不应由通用建议覆盖。

## 不可直接比较路线

以下工作能说明更广的 metasurface 高度空间，但没有进入上表核心判断：

- **传播相位尺寸库**：例如 Arbabi 2015 的 `1550 nm / 940 nm` a-Si circular nanopost。高度用于尺寸相关 transmission phase，不是旋转产生 PB phase。
- **宽带/消色差**：例如 Wang 2018、Shrestha 2018；height 同时承担 group-delay/dispersion 自由度，不能回填单色 PB 默认值。
- **混合 propagation + geometric phase**：每个位置同时换尺寸与旋转角，height 的角色不再是固定 half-wave cell 的单一资格。
- **非局域、高 Q、metagrating/inverse-designed outer zones**：响应依赖多单元协同或长程耦合，不满足 MetaCraft 当前 local periodic cell 假设。
- **反射型、金属/等离激元**：ground plane、cavity 或 ohmic resonance 改变了高度语义。

## 可审计结论

> 文献支持“更高的 PB 柱可能通过更长传播距离降低所需有效双折射”，也支持 `1550 nm silicon` 采用 `800--900 nm` 作为保守搜索起点；文献不支持“越高越好”，更不支持把该区间当成硬门。Yang 的 `340 nm` 是强横向各向异性的论文优化紧凑解，MetaCraft 的 `800--900 nm` 是另一条合理但尚待 Jones 证据裁决的设计分支。正确的改进不是替换一个经验数字，而是让候选分支、物理理由、加工代价与最终资格证据前后呼应。

## 一手来源清单

1. Lin et al., “Dielectric gradient metasurface optical elements,” *Science* 345, 298–302 (2014), DOI [10.1126/science.1253213](https://doi.org/10.1126/science.1253213).
2. Khorasaninejad et al., “Metalenses at visible wavelengths: Diffraction-limited focusing and subwavelength resolution imaging,” *Science* 352, 1190–1194 (2016), DOI [10.1126/science.aaf6644](https://doi.org/10.1126/science.aaf6644).
3. Khorasaninejad et al., “Multispectral Chiral Imaging with a Metalens,” *Nano Letters* 16, 3732–3737 (2016), DOI [10.1021/acs.nanolett.6b01897](https://doi.org/10.1021/acs.nanolett.6b01897).
4. Chen et al., “Immersion Meta-Lenses at Visible Wavelengths for Nanoscale Imaging,” *Nano Letters* 17, 3188–3194 (2017), DOI [10.1021/acs.nanolett.7b00717](https://doi.org/10.1021/acs.nanolett.7b00717).
5. Groever et al., “Meta-Lens Doublet in the Visible Region,” *Nano Letters* 17, 4902–4907 (2017), DOI [10.1021/acs.nanolett.7b01888](https://doi.org/10.1021/acs.nanolett.7b01888).
6. Liang et al., “Ultrahigh Numerical Aperture Metalens at Visible Wavelengths,” *Nano Letters* 18, 4460–4466 (2018), DOI [10.1021/acs.nanolett.8b01570](https://doi.org/10.1021/acs.nanolett.8b01570).
7. Yang et al., “Generalized Hartmann–Shack array of dielectric metalens sub-arrays for polarimetric beam profiling,” *Nature Communications* 9, 4607 (2018), DOI [10.1038/s41467-018-07056-6](https://doi.org/10.1038/s41467-018-07056-6).
8. Wang et al., “Planar metalenses in the mid-infrared,” *AIP Advances* 9, 085327 (2019), DOI [10.1063/1.5124074](https://doi.org/10.1063/1.5124074).
9. Chantakit et al., “All-dielectric silicon metalens for two-dimensional particle manipulation in optical tweezers,” *Photonics Research* 8, 1435–1440 (2020), DOI [10.1364/PRJ.389200](https://doi.org/10.1364/PRJ.389200).
10. Wang et al., “Metalens Eyepiece for 3D Holographic Near-Eye Display,” *Nanomaterials* 11, 1920 (2021), DOI [10.3390/nano11081920](https://doi.org/10.3390/nano11081920).
11. Fan et al., “Chip-scale metalens microscope for wide-field and depth-of-field imaging,” *Advanced Photonics* 4, 046006 (2022), DOI [10.1117/1.AP.4.4.046006](https://doi.org/10.1117/1.AP.4.4.046006).
12. Liu et al., “Metalenses phase characterization by multi-distance phase retrieval,” *Light: Science & Applications* 13, 182 (2024), DOI [10.1038/s41377-024-01530-1](https://doi.org/10.1038/s41377-024-01530-1).
