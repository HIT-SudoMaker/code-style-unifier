---
record_type: research_record
date: 2026-07-27
status: research_finding
authority_level: none
current_capability: false
---

# 低 NA 红外传播相位 metalens：候选与复刻边界

## 后续决策

本记录完成后，[ADR 0008](../adr/0008-honor-explicit-cell-constraints-before-advice.md)
接受了 brief 明示的论文 cell period 与 atom height。下文“当前物理
周期”及其比较表描述的是 ADR 0007 在 brief
未指定 period 时的默认路径，不再表示编译器会覆盖一个合法的论文
约束。本轮 Johansen 与 Pi 标准 brief 因而保留各自论文的 period 与
height；它们仍因器件口径、材料细节、量化相位集合和评价约定等差异
被称为 adapted reproduction。

## 结论

四项一手工作都可以检验 MetaCraft 的传播相位路线，但在当前协议下，没有一项应被称为 **exact reproduction**。

推荐顺序是：

1. **Johansen 2024 的 940 nm、NA 0.16 器件**作为方法回归。它与当前的“周期单元响应 → 阵面场 → ASM”关系最接近，而且论文明确指出 constant-phase approximation 在这一 NA 附近仍能与实验吻合。
2. **Yun 2025 的 conventional `2π` 对照器件**作为紧凑全流程压力测试。它的口径、NA、材料折射率和论文周期最完整，且约 0.5 mm 口径适合单工作站；但 NA 0.35 已高于 Johansen 给出的简单 constant-phase approximation 定量可靠区间，不能把论文的 82.8% 数值效率直接当作当前 ASM 结果的验收阈值。
3. **Pi 2025 的 1550 nm 方柱单元**作为方柱模板参照。原器件 NA 0.953 超出当前能力，但论文给出的 600 nm 周期、800 nm 高度和 110–440 nm 边长足以形成一个明确的 low-na adapted reproduction。
4. **She 2018 的 1550 nm 大口径器件**暂作布局边界参照。它使用固定边缘间距而不是固定晶格周期，精确复刻需要当前 aperture contract 尚未表达的可变中心距。

系统性差异有两项，必须先写在“复刻”一词前面：

- 论文采用的周期或局部中心距远小于当前 `floor_10nm(sampling ceiling)` 选出的物理周期；
- 论文以连续或高密度直径映射实现相位，而当前传播路线独立形成 8、12、16 阶 phase set。

因此，保留论文波长、NA、材料和器件目标，而让 MetaCraft 重新决定周期、加工域和相位集合，是有价值的 **adapted reproduction**；它不是论文纳米版图的原样复刻。

## 调研口径

本文只使用论文原文、期刊官方全文、作者公开稿和论文补充材料。所有 MetaCraft 数值均由论文参数和现行 ADR 0007 推导，不冒充论文事实。

本文使用两个严格不同的名称：

- **exact reproduction**：波长、材料数据、基底、单元形状、周期或布局规则、高度、横向尺寸映射、相位映射、口径、焦距、照明、边界条件和指标定义均与论文一致。
- **adapted reproduction**：保留论文的科学目标与物理机制，但至少一个执行事实由 MetaCraft 当前协议重新裁决。

现行关系为：

```text
sampling ceiling = wavelength / (2 × numerical aperture)
physical period  = floor_10nm(sampling ceiling)
order ceiling    = wavelength / (substrate index + numerical aperture)
```

`order ceiling` 只产生 `higher orders possible` caution，不拒绝工作。它也不能把只含 G0 的阵面场改称为总透射场。

## 四项候选的周期比较

| 候选 | 论文周期或局部中心距 | sampling ceiling | 当前物理周期 | order ceiling | 直接含义 |
| --- | ---: | ---: | ---: | ---: | --- |
| Johansen 2024，940 nm，NA 0.16 | 400 nm | 2937.5 nm | 2930 nm | 论文未给 D263T glass 在 940 nm 的折射率 | 论文周期与当前周期相差约 7.3 倍 |
| Yun 2025，850 nm，NA 0.35 | 400 nm | 1214.3 nm | 1210 nm | 466.5 nm，使用论文 `n_sub = 1.472` | 论文单元为 `zeroth order`；当前周期为 `multi order` |
| Pi 2025，1550 nm，adapted NA 0.30 | 600 nm | 2583.3 nm | 2580 nm | 等待 glass material sample | 论文方柱平台可适配为约 210 格点跨径的 low-na 器件 |
| She 2018，1550 nm，nominal NA 0.2 | 1480–1640 nm | 3875.0 nm | 3870 nm | 约 945.2 nm，见下文推导 | 论文布局和当前布局都落在保守 `multi order` 区间 |
| She 2018，7 mm illumination，effective NA 0.07 | 1480–1640 nm | 11071.4 nm | 11070 nm | 约 1026.6 nm，见下文推导 | 用 effective NA 编译会把周期进一步放大 |

Johansen 的原文没有给出 D263T glass 的目标波长折射率，故不能从一手论文伪造数值 order ceiling。其 400 nm 周期若要满足当前保守条件，只要求：

```text
substrate index <= 940 / 400 - 0.16 = 2.19
```

最终分类仍应由 qualification-admitted material sample 产生。无论该玻璃的精确值为何，只要 `substrate index >= 1`，其 order ceiling 就不超过 `810.3 nm`；因此当前 `2930 nm` 周期必然被标为 `multi order`。

She 报告未计入 air–silica 界面的 3.25% Fresnel loss。仅为比较论文几何，可由

```text
reflection = ((substrate index - 1) / (substrate index + 1))²
```

反推 `substrate index ≈ 1.4399`，进而得到表中的 indicative order ceiling。这个反推值不是 material sample，不得进入 qualification 或替代真实色散数据。

## 候选一：Johansen 2024，940 nm / NA 0.16

论文：Villads Egede Johansen et al., “Nanoscale precision brings experimental metalens efficiencies on par with theoretical promises,” *Communications Physics* 7, 123 (2024), DOI 10.1038/s42005-024-01598-6。  
一手来源：[期刊全文](https://www.nature.com/articles/s42005-024-01598-6)，[期刊补充材料](https://static-content.springer.com/esm/art%3A10.1038%2Fs42005-024-01598-6/MediaObjects/42005_2024_1598_MOESM1_ESM.pdf)

### 论文事实

```text
wavelength          = 940 nm
numerical aperture  = 0.16
lens diameter       = 2.5 mm
illuminated diameter= 2.4 ± 0.1 mm
design focal length = 7.348 mm
atom shape          = cylindrical pillar
atom material       = amorphous silicon
substrate           = D263T Eco glass
atom height         = 500 nm
square period       = 400 nm
backside            = anti-reflection coating
```

作者先用 RCWA 在周期边界下建立圆柱直径到复透射响应的单元库，再以两种近似构造阵面：

- constant-phase approximation：每个单元由一个复振幅和相位表示；
- resolved-field approximation：每个单元用 `5 × 5` 的同偏振场采样表示。

两者最后都通过 ASM 传播到焦区。这个方法关系与当前传播相位路线最接近。

论文报告 NA 0.16 器件的 absolute focusing efficiency 为 91.3%；跨晶圆和测量配置的重复结果为 91–94%。补充材料中的 940 nm 波长扫描给出 93.0%。这些数值使用论文自身的 ARC、连续直径映射、400 nm 周期和效率口径。

更重要的科学边界是：作者认为 constant-phase approximation 的定量吻合大致保持到 NA 0.16，粗略趋势可延伸到约 0.2；resolved-field approximation 才把定量适用范围扩展到约 0.6。

### 对 MetaCraft 的意义

它是首选的方法回归，因为：

- 圆柱传播相位、正入射、偏振不敏感单元与当前模板同构；
- 单元库、阵面构造和 ASM 的职责关系明确；
- NA 0.16 落在论文实证支持的 constant-phase approximation 区间；
- 论文同时给出实验效率、重复性和制造公差，能够约束结果解释。

它目前只能叫 adapted reproduction：

- 当前周期为 2930 nm，而不是 400 nm；
- 当前产生独立 8/12/16 阶相位集合，而论文按连续相位曲线映射直径；
- 当前材料资格没有论文 D263T glass 的目标波长折射率；
- 若不建模 backside ARC，就不能比较论文的 absolute focusing efficiency。

因此第一轮应把它用于验证“完整 conduct 能否诚实闭合”，而不是要求聚焦效率复现到 91.3%。

## 候选二：Yun 2025 conventional `2π` comparator

论文：Jeong-Geun Yun et al., “Compact eye camera with two-third wavelength phase-delay metalens,” *Nature Communications* 16, 7299 (2025), DOI 10.1038/s41467-025-62577-1。  
一手来源：[期刊全文](https://www.nature.com/articles/s41467-025-62577-1)，[期刊 PDF](https://www.nature.com/articles/s41467-025-62577-1.pdf)，[期刊补充材料](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-025-62577-1/MediaObjects/41467_2025_62577_MOESM1_ESM.pdf)

### 论文事实

论文把 conventional full-`2π` metalens 与其新提出的 `4π/3` limited-phase metalens 分开比较。当前路线只对应前者。

```text
wavelength          = 850 nm
numerical aperture  = 0.35
lens diameter       = 0.5 mm
derived focal length= 669.1 µm
atom shape          = cylindrical pillar
atom material       = hydrogenated amorphous silicon
substrate           = fused silica
square period       = 400 nm
```

焦距由论文的直径和 NA 推导：

```text
focal length
  = radius × sqrt(1 - NA²) / NA
  ≈ 669.1 µm
```

正文 Fig. 3 的直接比较写明 conventional `2π` 单元高度为 800 nm，`4π/3` 单元高度为 500 nm；两者的模拟 focusing efficiency 分别为 82.8% 和 87.2%，MTF 均接近理论衍射极限。

补充材料 Note 3 另有一个用于超单元衍射分析的 full-`2π` library：

```text
period          = 400 nm
height          = 900 nm
atom index      = 2.58 at 850 nm
substrate index = 1.472 at 850 nm
```

这两个高度属于不同的图和分析对象。复刻正文 comparator 应遵循正文的 800 nm，不能把补充材料 Note 3 的 900 nm 无说明地拼接进去；若原始库数据不可得，就应把这一来源分裂写成缺口，而不是伪造一套“完整参数”。

作者用 RCWA 建立单元库，并用 scalar diffraction theory 评价 metalens。论文的新颖贡献是 limited-phase optimization；它不属于当前传播相位的固定 8/12/16 阶选择，首轮不得顺带实现。

### 对 MetaCraft 的意义

这一候选的优势是器件紧凑。按当前 1210 nm 周期，0.5 mm 口径约有 413 个格点跨径，适合验证完整 brief、材料资格、height advice、扫参、phase set、aperture 和 focus 返回。

但这会成为新的 MetaCraft 器件，而不是论文单元的复刻：

- 1210 nm 周期不是论文的 400 nm；
- 当前 aspect limit 与论文讨论的最高约 10:1 制造比例不同；
- 8/12/16 阶集合不等于论文的直径映射；
- 1210 nm 周期超过 466.5 nm order ceiling，必须保留 `higher orders possible`；
- NA 0.35 超出 Johansen 对简单 constant-phase approximation 给出的定量吻合区间，因此论文的 82.8% 只能作为背景，不能作为当前 G0-only ASM 结果的数值验收。

它适合作为第二个、较强的低 NA 压力测试。若未来的 period-selection strategy 能在 sampling ceiling 以下选择并冻结论文的 400 nm 周期，再配合论文专属 material sample 和相位映射，才有资格讨论更接近 exact 的 comparator reproduction。

## 候选三：Pi 2025，1550 nm 方柱平台

论文：Hailong Pi et al., “Levitation and controlled MHz rotation of a nanofabricated rod by a high-NA metalens,” *Microsystems & Nanoengineering* 11, 67 (2025), DOI 10.1038/s41378-025-00886-7。  
一手来源：[期刊全文](https://www.nature.com/articles/s41378-025-00886-7)

### 论文事实

```text
wavelength          = 1550 nm
design focal length = 200 µm
atom shape          = square pillar
atom material       = amorphous silicon
substrate           = glass
atom height         = 800 nm
square period       = 600 nm
pillar width        = 110–440 nm
phase coverage      = 2π
unit transmission   > 85.3%
```

论文在大于 metalens 口径的光束下形成近似平面波入射。原器件直径为
1.2 mm，设计 NA 0.95，实测 NA 0.953；这不属于当前 `low na`
能力，因此原器件不能进入当前完整路线。

### 对 MetaCraft 的意义

它为与圆柱平级的方柱传播相位模板提供了完整单元事实。保留论文焦距
200 µm，把 adapted device 的 NA 设为 0.30，可推导：

```text
adapted radius
  = focal length × NA / sqrt(1 - NA²)
  ≈ 62.90 µm

adapted diameter
  ≈ 125.79 µm

cells across at the paper period
  ≈ 125.79 µm / 0.60 µm
  ≈ 210
```

这恰好形成一个可在单工作站上评估的 low-na 方柱主例。它必须称为
adapted reproduction，因为口径和 NA 已改变，当前 8/12/16 phase set
也不同于论文的连续映射。若仍使用 ADR 0007 的默认 2580 nm 周期，
则连论文的单元平台也没有保留；因此它与圆柱候选共同支持在
sampling ceiling 内接受明确的论文周期约束。

## 候选四：She 2018，1550 nm 大口径 metalens

论文：Alan She et al., “Large area metalenses: design, characterization, and mass manufacturing,” *Optics Express* 26, 1573–1585 (2018), DOI 10.1364/OE.26.001573。  
一手来源：[作者公开稿](https://clarke.seas.harvard.edu/sites/g/files/omnuum2996/files/clarke/files/she_et_al_2018.pdf)，[作者实验室记录](https://capasso.seas.harvard.edu/publications/large-area-metalenses-design-characterization-and-mass-manufacturing)

### 论文事实

```text
wavelength          = 1550 nm
lens diameter       = 20 mm
design focal length = 50 mm
nominal NA          = 0.2
illuminated diameter= 7 mm
effective NA        = 0.07
atom shape          = cylindrical pillar
atom material       = amorphous silicon
substrate           = fused silica
atom height         = 600 nm
pillar diameter     = 830–990 nm
edge-to-edge gap    = 650 nm
local center pitch  = 1480–1640 nm
```

论文不是在固定方形周期上改变直径，而是固定柱间边缘距离。因此中心距随直径从 1480 nm 变到 1640 nm。相位由连续直径映射，布局通过 METAC 的径向层级引用压缩。

作者用 Lumerical FDTD 模拟一个保持 effective NA 0.07 的 100 µm 小口径版本，得到 `17.1 µm` 的 full `1/e²` beam waist。实验中，20 mm 器件只被 7 mm 光束照亮：

- measured focal length：`50.159 ± 0.023 mm`；
- measured full `1/e²` beam waist：`20.9 µm`；
- focusing efficiency：`91.8 ± 4.1%`，不含 3.25% air–silica Fresnel loss。

### 对 MetaCraft 的意义

这篇论文证明了三个重要事实：

- 低 effective NA 的传播相位器件可以用较小的全波模型和标量传播相互校验；
- 大口径版图需要利用径向对称和层级引用，而不是保存数十亿个独立对象；
- 多阶通道在运动学上开放，并不自动意味着论文器件不能获得高效率。

它不适合作为当前首个完整复刻：

- 当前固定 period 的 aperture 不能表达论文的 fixed-edge-gap 布局；
- nominal NA 与 effective NA 分属器件和照明，brief 必须明确选择，不能混成一个值；
- 用 effective NA 0.07 编译会选出 11070 nm 周期，与论文 1480–1640 nm 中心距相差过大；
- 论文连续直径映射和 METAC 布局不属于当前 8/12/16 阶方格阵面；
- 20 mm 原器件不适合作为首轮单工作站全流程回归。

未来若 aperture contract 支持可变中心距或明确的 fixed-edge-gap strategy，这篇论文才适合作为大口径布局与压缩测试。

## 推荐的执行口径

### 第一轮：方法回归

以 Johansen 2024 的 940 nm、NA 0.16 目标运行传播相位 conduct，保留论文波长、NA、圆柱 a-Si 与 glass 材料关系。若当前规则重新决定周期、相位阶数、材料数据或 ARC，则结果名必须写：

```text
Johansen-2024-inspired adapted reproduction
```

首轮比较完整性、焦点是否落在 `0.8f–1.2f`、x/y half-maximum width、depth、相位圆闭合和证据引用；不以 91.3% 作为硬阈值。

### 第二轮：紧凑压力测试

以 Yun 2025 conventional `2π` comparator 的 850 nm、NA 0.35、0.5 mm 口径目标验证约 413 格点跨径的完整阵面。保持 `4π/3` optimizer 明确省略，只运行当前 full-phase propagation route。

若使用当前 1210 nm 周期，应把 `higher orders possible` 和 G0 channel limitation 带到 run manifest 与 result。只有未来固定 400 nm 论文周期时，才可把 82.8% 和论文 MTF 当作更直接的比较对象。

### 平级方柱回归

以 Pi 2025 的 1550 nm 方柱单元为结构参照，固定论文的 600 nm 周期、
800 nm 高度和 110–440 nm 边长范围，把器件目标适配为 200 µm 焦距、
NA 0.30、约 126 µm 口径。该结果用于验证方柱与圆柱经过同一
propagation route 闭合，不与原论文 NA 0.953 器件的焦斑和效率做数值
等同。

### 延后：布局边界

She 2018 暂不转成标准 brief。它应等待以下任一能力：

- 可变中心距 / fixed-edge-gap aperture strategy；
- 一个明确允许从 sampling ceiling 以下选择较小物理周期的 period-selection strategy；
- 面向大口径径向布局的压缩与分块 ASM 证据。

## 对后续设计的最小结论

本研究不要求撤销 ADR 0007，也不要求把论文周期变成用户可随意覆盖的字段。它只提供一条清晰证据：

> sampling ceiling 是上界；公开论文中的可靠低 NA 红外 metalens 普遍选择远小于该上界的周期或局部中心距。

因此未来若增加 period-selection strategy，应由 Python 科学模块在 sampling ceiling 内基于论文约束、加工域、材料样本和求解证据选择更小周期；Rust authority、生命周期和协议无需改变。

在该策略出现以前，传播相位论文验证均应标为 **adapted reproduction**，并把周期、order regime、相位阶数、材料差异和效率口径逐项列出。
