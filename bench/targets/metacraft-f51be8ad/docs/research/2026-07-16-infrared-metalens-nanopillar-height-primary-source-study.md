# 红外介质超透镜纳米柱高度：一手资料调研与 MetaCraft 建模建议

日期：2026-07-16
文档性质：Research Record，非权威规格，不直接修改 `docs/metacraft_next/`。
范围：介质纳米柱/纳米鳍超透镜，重点考察传播相位；用 PB 几何相位和宽带消色差案例说明为什么不能维护一个统一的“红外默认柱高”。

## 结论摘要

1. **不存在跨波段、跨材料、跨相位机制通用的固定柱高。** 高度必须至少绑定工作波长、材料/基底、横截面、周期与间隙、相位机制、单色或消色差目标，以及加工宽高比。
2. 在本文有限样本中，多数实验性单色传播相位设计的高度落在约 `0.5–1.1 × vacuum_wavelength`，但 MWIR 大口径实验也出现约 `1.76 × wavelength` 的设计；前一范围只能作为核心候选先验，不能作为物理定律或资格门。
3. PB 几何相位的 `2π` 相位主要来自各向异性单元旋转产生的 `2 × rotation_angle`。高度主要用于获得足够的双折射/近半波片响应和交叉偏振转换，因此不能沿用传播相位的高度先验；实验案例可低至约 `0.21 × wavelength`。
4. 宽带消色差为了获得更大的相位色散自由度，可能需要明显更高的柱子。本文 MWIR 数值案例达到约 `1.8–2.2 × wavelength`，横向最小尺寸对应的几何宽高比可超过 20；它不适合作为单波长首板默认值。
5. 对 MetaCraft v0.0：在单个可见光设计波长附近，把 `500–800 nm` 写成人工批准的允许范围是合理的；程序应离散化候选，AI 只排序并解释，最终柱高由小规模 FDTD 高度资格扫描固定。

## 调研口径

本文为方便组织案例，采用以下工程分桶：NIR `0.75–1.4 µm`、SWIR `1.4–3 µm`、MWIR `3–5 µm`、LWIR `8–12 µm`。不同领域对 NIR/SWIR 边界并不完全一致，例如 1550 nm 也常被论文称作 NIR，因此文档同时保留实际波长，不以波段标签代替数值。

尺寸只采用论文原文、补充材料、期刊官方全文或作者/机构托管的原始论文。表中 `height / lateral` 对圆柱按高度除以直径，对矩形或纳米鳍按高度除以较小横向尺寸；原文未给可靠横向范围时不反推。

## 一手案例

| 波段与来源 | 工作波长 | 材料、基底与几何 | 高度、周期与横向尺寸 | 高度比例与可推导宽高比 | 相位机制与验证状态 |
| --- | --- | --- | --- | --- | --- |
| NIR：[Johansen et al., *Communications Physics* 2024](https://www.nature.com/articles/s42005-024-01598-6) | 940 nm | 玻璃上的 a-Si 圆柱 | 高度 500 nm，方格周期 400 nm；正文图注未给完整直径范围 | `height / wavelength ≈ 0.53`；横向宽高比不强算 | 截断波导/传播相位；实验，覆盖 NA 0.08–0.93 |
| SWIR：[Arbabi et al., *Nature Communications* 2015](https://www.nature.com/articles/ncomms8069) | 1550 nm | 熔融石英上的 a-Si 圆柱 | 高度 940 nm，六角周期 800 nm，直径 200–550 nm | `height / wavelength ≈ 0.61`；`height / diameter ≈ 1.71–4.70` | 高对比透射阵列，直径调传播相位；实验，聚焦效率最高 82% |
| SWIR 边界宽带：[Shrestha et al., *Light: Science & Applications* 2018](https://www.nature.com/articles/s41377-018-0078-x) | 1200–1650 nm | 石英上的 a-Si，多种实心、环形和复合横截面 | 第一代高度 800 nm；扩展色散库高度 1400 nm；横向尺寸依具体 archetype 变化，正文无单一区间 | 1400 nm 对应 `height / wavelength ≈ 0.85–1.17` | 传播相位与结构色散共同设计；实验宽带消色差。原文明确指出增高会扩大相位-色散覆盖，但增加加工难度 |
| SWIR/PB 对照：[Zhao et al., *Light: Science & Applications* 2024](https://www.nature.com/articles/s41377-024-01530-1) | 1560 nm | 石英上的 a-Si 新月形纳米柱 | a-Si 膜厚/柱高 327 nm；正文未给单一横向范围与周期 | `height / wavelength ≈ 0.21` | 旋转新月柱取得几何相位；实验相位恢复和聚焦。此例只用于证明 PB 高度不可与传播相位混桶 |
| MWIR：[Zuo et al., *Advanced Optical Materials* 2017；ANU 作者稿](https://openresearch-repository.anu.edu.au/bitstreams/803dccb8-7497-406f-ae5b-4d85378a40c0/download) | 4.0 µm，实验还在 3.7–4.2 µm 测量 | MgF2 上的 a-Si:H 圆柱 | 高度 2.0 µm，六角周期 2.0 µm，半径 0.1–0.6 µm（直径 0.2–1.2 µm） | `height / wavelength = 0.50`；`height / diameter ≈ 1.67–10` | 直径调传播相位；实验，聚焦效率约 78%。补充材料显示更高柱可用更小半径获得 `2π`，但需更高加工宽高比 |
| MWIR/PB：[Wang et al., *AIP Advances* 2019](https://doi.org/10.1063/1.5124074) | 3、5、8 µm | 单片 Ge 纳米鳍/Ge 基底 | 3 µm：`W=0.427 µm, L=1 µm, H=1.5 µm, P=1.3 µm`；5 µm：`W=0.55 µm, L=2.5 µm, H=1.5 µm, P=3 µm`；8 µm：`W=0.85 µm, L=4 µm, H=2.5 µm, P=5 µm` | `height / wavelength = 0.50, 0.30, 0.31`；按较小横向尺寸，宽高比约 3.51、2.73、2.94 | 旋转纳米鳍的 PB 相位；高度/截面先满足近半波片相位延迟；三个器件均制造并实验聚焦 |
| MWIR 宽带数值：[Zhang et al., *Sensors* 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9460807/) | 4.0–4.8 µm | 熔融石英上的 Si 圆柱 | 高度 8.7 µm，周期 2.4 µm，直径 0.4–2.2 µm | `height / wavelength ≈ 1.81–2.18`；`height / diameter ≈ 3.95–21.75` | 直径库提供多重 `2π` 和异常色散；FDTD 数值设计，未实验制造 |
| MWIR 大口径实验：[Li et al., *Nature Communications* 2025](https://www.nature.com/articles/s41467-025-65188-y) | 4.5 µm（4.25–4.75 µm 滤光波段） | Si 基底上的 Si 纳米柱 | 高度 7.9 µm，周期 5.6 µm；正文报告最小间隔 3.67 µm，未给可可靠统一的柱宽范围 | `height / wavelength ≈ 1.76`；横向宽高比不强算 | 传播相位库；实验 Golay 稀疏孔径远距热成像 |
| LWIR：[Huang et al., *Optical Materials Express* 2021；作者实验室原文](https://labs.ece.uw.edu/amlab/Papers_Journals/Luocheng_LWIR.pdf) | 标称 10 µm，实验还考察 12 µm | 300 µm Si 晶圆上直接刻蚀的方形 Si 柱 | 高度 10 µm，方格周期 4 µm；正文图中给宽度扫描但文本未列区间 | `height / wavelength = 1.0`；横向宽高比不从图像猜测 | 宽度调传播相位；实验，2 cm 口径环境热辐射成像 |
| LWIR：[Hou et al., *Science Advances* 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11225786/) | 10.6 µm，系统工作在 8–12 µm | Si 基底上的 Si 圆柱，六角晶格 | 高度 5.8 µm，中心距 4.6 µm，直径 1.5–4.1 µm | `height / wavelength ≈ 0.55`；`height / diameter ≈ 1.41–3.87` | 直径调传播相位；实验，5 cm 口径热成像相机 |
| LWIR：[《红外与毫米波学报》2024 原文](https://journal.sitp.ac.cn/hwyhmb/hwyhmben/article/html/2023288) | 9–11.5 µm | Si 晶圆上的 Si 圆柱 | 高度 6 µm，周期 6 µm，半径 1–2.5 µm（直径 2–5 µm） | `height / wavelength ≈ 0.52–0.67`；`height / diameter ≈ 1.2–3.0` | 直径调传播相位；实验制造并成像 |

## 为什么高度随波长缩放，却不是固定比例

### 传播相位

传播相位单元常可近似理解为一段有限高度的介质波导。忽略复杂共振和界面项时，不同横向尺寸之间的相对相位覆盖大致满足：

```text
relative_phase_span ≈ (2π / vacuum_wavelength)
                      × meta_atom_height
                      × effective_index_span
```

因此，为获得接近 `2π` 的相位覆盖，需要的高度量级约为：

```text
meta_atom_height × effective_index_span ≳ vacuum_wavelength
```

这解释了“高度通常随波长增大”这一趋势，也同时说明不能只按波长线性缩放：`effective_index_span` 会随材料折射率、基底、横截面、周期、最小间隙、耦合和共振策略改变。Shrestha 等人的原文直接用频率相关有效折射率和厚度计算相位，并展示从 800 nm 增至 1400 nm 会显著扩大色散覆盖；Zuo 等人的补充材料则显示，更高的柱可以用更小半径取得 `2π`，代价是更高的加工宽高比。

### PB 几何相位

PB 路线中，旋转角为 `orientation_angle` 的各向异性单元对转换手性分量提供 `2 × orientation_angle` 的几何相位。[Wang et al.](https://doi.org/10.1063/1.5124074) 的原文明确给出该关系，并先调整纳米鳍宽度、长度和高度使其接近半波片，再通过旋转排布相位。

所以 PB 的高度选择问题是：

```text
能否在目标波段获得足够的 cross-polarization conversion
+ 是否保持可接受的 co-polarized leakage
+ 加工与带宽是否可行
```

它不是“高度本身是否扫出 `0–2π` 传播相位”。因此 MetaCraft 必须为 PB 与传播相位维护不同的高度候选策略与证据字段。

### 宽带/消色差

宽带消色差不仅匹配中心频率相位，还需要匹配群延迟或更一般的相位色散。更高结构会增加可用传播长度和色散自由度，因此可能远高于单色设计；但与此同时，邻近耦合、侧壁误差、深刻蚀难度和计算成本都会增加。`8.7 µm` 高、最小直径 `0.4 µm` 的 MWIR 案例应被理解为复杂色散设计的搜索点，而不是“4 µm 红外柱子的普遍高度”。

## 对 v0.0 可见光 benchmark 的判断

在一个明确的可见光工作波长（例如 550 nm 附近）、高折射率低损耗介质和传播相位路线下，`500–800 nm` 是合理的**人工批准候选范围**：

- 550 nm 时对应 `height / wavelength ≈ 0.91–1.45`；
- 可见光实验已有约 600 nm 厚 TiO2 传播相位金属透镜，以及 800 nm 高 GaN 可见光单元，说明该量级具备文献可行性：[Khorasaninejad et al., *Nano Letters* 2016](https://pubs.acs.org/doi/10.1021/acs.nanolett.6b03626)、[Chen et al., *Light: Science & Applications* 2019](https://www.nature.com/articles/s41377-019-0208-0)；
- 这仍不证明 `500–800 nm` 对所有可见光材料、整个 400–700 nm 波段或任意周期都能获得合格相位库。

因此 Brief 应把“可见光”作为设计语境，把实际设计波长、材料候选和 `500–800 nm` 作为不可被 AI 修改的输入边界。若未来目标改成整个可见光宽带消色差，必须建立新的 benchmark，而不是沿用这一单波长范围。

## MetaCraft 的候选生成建议

### 1. 不保存“红外默认柱高”

建议保存归一化和上下文完整的先验：

```text
HeightSearchPrior
  phase_mechanism
  spectral_objective
  material_binding_ref
  substrate_binding_ref
  reference_wavelength
  permitted_height_to_wavelength_ratio
  fabrication_rule_ref
  evidence_source_refs
```

其中 `permitted_height_to_wavelength_ratio` 只用于生成候选，不产生 qualification 或 claim。

### 2. 首轮候选包络

以下范围是本文样本导出的保守搜索起点，不是验收阈值：

| 路线 | 建议的初始高度包络 | 说明 |
| --- | --- | --- |
| 单色传播相位，NIR/SWIR | `0.45–1.2 × reference_wavelength` | 覆盖本文 940/1550 nm 代表性单色实验；消色差任务另行分桶 |
| 单色传播相位，MWIR | 核心候选 `0.45–1.2 × wavelength`；扩展候选最高约 `1.8 × wavelength` | 高端只在核心候选不能覆盖相位、且加工/预算允许时启用 |
| 单色传播相位，LWIR | `0.45–1.2 × reference_wavelength` | 与本文 5.8、6、10、12 µm 级深硅刻蚀实验一致 |
| PB 几何相位 | 初始可探索 `0.2–0.6 × wavelength`，但必须由半波片/转换效率条件重新筛选 | 不以传播相位 `2π` 覆盖作为高度验收 |
| 宽带消色差传播/混合路线 | 默认不继承单色范围；单独 opt-in，可探索到约 `2.2 × wavelength` | 必须同时绑定色散目标、加工上限和更高仿真预算 |

### 3. AI 与确定性程序的职责

推荐保持以下边界：

```text
用户或 Benchmark Brief
  -> 给定波长、材料候选、相位机制、允许高度范围和预算

确定性程序
  -> 按高度步进生成离散候选
  -> 对每个高度推导最小特征、最大横向尺寸、合法格点和仿真成本
  -> 删除违反周期、间隙、宽高比或预算的候选

AI
  -> 只对合法候选排序
  -> 解释相位积累、加工风险、预期计算成本和材料损耗权衡
  -> 可以提出“申请扩大范围”的声明式建议，但不能直接写入执行计划

FDTD 证据
  -> 以少量横向尺寸预扫描判断每个高度的相位覆盖、透射响应和共振风险
  -> 固定一个或少数高度
  -> 再执行完整横向尺寸扫参
```

对当前 `500–800 nm` 可见光 benchmark，可先生成 `500, 550, 600, 650, 700, 750, 800 nm`。更节省许可证预算的两阶段方案是：先用 `500, 600, 700, 800 nm` 做粗筛，再只对证据最好的一个或两个区间以 50 nm 步进细化。AI 的排序不能替代这轮 FDTD 高度资格扫描。

## 对后续规格的最小影响

本调研不要求现在修改 active specs。后续治理修订时，只需把以下原则落入各 owner：

- Brief/用户输入拥有允许高度范围，AI 不得修改；
- M2 拥有材料与加工规则；
- M3 拥有按相位机制区分的 route-scoped height search contract；
- M4/AI 只产生声明式排序和理由；
- M5 执行候选扫描，不决定科学资格；
- M6 校验范围、离散格点、预算、引用与证据闭包；
- propagation、PB、achromatic 必须使用不同的高度先验/资格包，不能共享一个“常用红外柱高”。

## 一手来源清单

1. Johansen et al., “Nanoscale precision brings experimental metalens efficiencies on par with theoretical promises,” *Communications Physics* 7, 123 (2024). [Publisher](https://www.nature.com/articles/s42005-024-01598-6)
2. Arbabi et al., “Subwavelength-thick lenses with high numerical apertures and large efficiency based on high-contrast transmitarrays,” *Nature Communications* 6, 7069 (2015). [Publisher](https://www.nature.com/articles/ncomms8069)
3. Shrestha et al., “Broadband achromatic dielectric metalenses,” *Light: Science & Applications* 7, 85 (2018). [Publisher](https://www.nature.com/articles/s41377-018-0078-x)
4. Zhao et al., “Metalenses phase characterization by multi-distance phase retrieval,” *Light: Science & Applications* 13 (2024). [Publisher](https://www.nature.com/articles/s41377-024-01530-1)
5. Zuo et al., “High-Efficiency All-Dielectric Metalenses for Mid-Infrared Imaging,” *Advanced Optical Materials* 5, 1700585 (2017). [ANU author manuscript](https://openresearch-repository.anu.edu.au/bitstreams/803dccb8-7497-406f-ae5b-4d85378a40c0/download)
6. Wang, Chen, and Dan, “Planar metalenses in the mid-infrared,” *AIP Advances* 9, 085327 (2019). [Publisher](https://doi.org/10.1063/1.5124074)
7. Zhang et al., “Robust Achromatic All-Dielectric Metalens for Infrared Detection in Intelligent Inspection,” *Sensors* 22, 6590 (2022). [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC9460807/)
8. Li et al., “A Golay metalens for long-range, large-aperture thermal imaging via sparse aperture computational imaging,” *Nature Communications* (2025). [Publisher](https://www.nature.com/articles/s41467-025-65188-y)
9. Huang et al., “Long wavelength infrared imaging under ambient thermal radiation via an all-silicon metalens,” *Optical Materials Express* 11, 2907–2918 (2021). [Author-hosted paper](https://labs.ece.uw.edu/amlab/Papers_Journals/Luocheng_LWIR.pdf)
10. Hou et al., “Single 5-centimeter-aperture metalens enabled intelligent lightweight mid-infrared thermographic camera,” *Science Advances* 10, eado4847 (2024). [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC11225786/)
11. “Long wavelength infrared metalens fabricated by photolithography,” *Journal of Infrared and Millimeter Waves* (2024). [Journal full text](https://journal.sitp.ac.cn/hwyhmb/hwyhmben/article/html/2023288)
12. Khorasaninejad et al., “Polarization-Insensitive Metalenses at Visible Wavelengths,” *Nano Letters* 16, 7229–7234 (2016). [Publisher](https://pubs.acs.org/doi/10.1021/acs.nanolett.6b03626)
13. Chen et al., “Spectral tomographic imaging with aplanatic metalens,” *Light: Science & Applications* 8, 99 (2019). [Publisher](https://www.nature.com/articles/s41377-019-0208-0)
