---
record_type: research_record
date: 2026-08-06
status: research_finding
authority_level: none
current_capability: false
---

# 四个 metalens case 的周期、深宽比与 brief 约束审计

## 研究问题与口径

本记录核对
[`examples/metalens_benchmark/`](../../examples/metalens_benchmark/)
中四个 canonical case 的论文器件事实，并回答一个功能问题：当前统一的
`aspect_limit = 8`、固定 `10 nm` period grid 和逐 case 的
`dimension_step_nm`，是否足以让 blind brief 形成与论文同量级、可制造且可工作的
cell platform。

只使用论文正文、官方补充材料和作者公开稿。下文严格区分：

- **论文事实**：来源直接给出的数值或工艺；
- **几何推导**：由论文尺寸计算，不冒充作者报告；
- **MetaCraft 规则**：当前代码行为，不冒充论文工艺；
- **未知**：正文/补充材料未提供、未能访问，或不同平台的参数不能可靠拼接。

本文使用两个不同的深宽比：

```text
feature aspect ratio = height / minimum lateral feature
gap aspect ratio     = height / minimum edge-to-edge gap
```

圆柱的 feature 是直径；椭圆和矩形 fin 的 feature 是短轴/短边。gap 对圆柱是
最近邻中心距减最大直径；对可旋转的各向异性单元，另算覆盖所有 orientation 的
几何包络。它不是论文测得的工艺极限。

## 结论先行

1. **不能先把 period 取到两种 ceiling 下的最大整十值，再讨论
   manufacturability。**正确顺序应是先同时满足 response capability、feature、
   orientation-aware gap、候选/固定 cell 语义和 fabrication grid，再在剩余可行
   domain 内取最大 grid-aligned period。
2. **统一 `aspect_limit = 8` 与四篇论文不相符。**Yun conventional comparator
   明示 feature aspect ratio 为 `10`；Khorasaninejad 532 nm fin 按短边为
   `6.32`，但旋转包络的 gap aspect ratio 可达 `10.42`。同一个数字不能同时代表
   所有 fabrication route 的 pillar feature 与 etched/fill gap。
3. **`200 nm` 仍然不是科学选择。**但把它机械替换为“物理 ceiling 下最大 period”
   也不够。四案的 paper periods 来自不同的 cell response、相位机制和制造路线，
   不是同一个 ceiling heuristic 的四次取值。
4. **当前 blind height prior 比 period 选择更早地产生冲突。**通用高度先验只允许
   Yun `450/500 nm`、Yang `800/850/900 nm`、Arbabi `800/850/900 nm`，只有 K
   包含论文的 `600 nm`。论文高度 `800/340/940/600 nm` 中有三项当前不可选。
5. 四案中，**Arbabi 的 period、feature/gap aspect 和 10 nm lateral step 与当前
   brief 最接近**；Yang 主要败在 `100 nm` dimension step 和 height prior；K
   败在 `325/95 nm` 的 5 nm 尾数以及 rotation-aware gap；Yun 则不能把不同高度
   的 supporting library 与 `800 nm` comparator 拼成一个已发表 platform。

## 一、跨 case 对照

| Case | Paper geometry | Minimum feature | Minimum gap | `h / feature` | `h / gap` | Paper process / explicit constraint | Current brief verdict |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Yun 2025 conventional full-`2π` comparator | `λ=850 nm`; circular a-Si:H; `H=800 nm`; Fig. 3a labels `H/w=10`; selected-comparator period and exact layout range are not source-joined | `80 nm`, derived from `800/10` | **not certifiable**; `50 nm` only under the unproven combination `P=400`, `w_max≈350` | `10.00` | conditionally `16.00`, not a certified paper value | comparator is numerical, not the fabricated wFoV lens; paper warns of collapse and etch nonuniformity at AR 10 | `aspect_limit=8` excludes the comparator's narrowest feature; the current `400 nm` paper-period claim is too strong |
| Yang 2018 circular-polarization sublens | `λ=1550 nm`; square `P=1500 nm`; Si ellipse `1350×480×340 nm` | `480 nm` | `150 nm`, exact orientation envelope for an ellipse | `0.708` | `2.267` | SOI, ZEP520A EBL, C4F8/SF6 ICP etch; no numeric AR ceiling | aspect 8 is ample, period is 10 nm aligned, but `100 nm` dimension step cannot express either axis and the height prior cannot express `340 nm` |
| Arbabi 2015 compact HCTA-derived standard | `λ=1550 nm`; hexagonal `P=800 nm`; circular a-Si:H posts `H=940 nm`, diameter `200–550 nm` | `200 nm` | `250 nm` | `4.70` | `3.76` | ZEP520A EBL, 70 nm Al2O3 hard mask, C4F8/SF6 dry etch; no numeric AR ceiling | aspect 8, 10 nm period grid and range endpoints are compatible; `940 nm` is outside current height prior and 10 nm is not a published layout quantization |
| Khorasaninejad 2016 532 nm device | `λ=532 nm`; square `P=325 nm`; TiO2 fin `250×95×600 nm` | `95 nm` | axis-aligned `75 nm`; all-orientation envelope `57.56 nm` | `6.316` | `8.00` axis-aligned; `10.424` envelope | EBL resist mold + conformal ALD; ALD thickness at least `W/2`; blanket RIE; near-vertical walls | `aspect_limit=8` is exactly the axis-aligned gap but misses rotated-corner clearance; `325` and `95` are off the 10 nm grids |

`minimum gap` is an arithmetic geometry result, not a measured SEM clearance. For Yang and K,
the exact minimum present in the fabricated lens would require the complete neighboring-orientation
layout, which is not published as reusable data. The table therefore reports an
**orientation envelope**: the smallest clearance permitted by the published unit cell and all
allowed PB orientations.

还必须避免三种量混桶：

- 论文已经制造某个 geometry，只证明该论文的材料、mask、etch/fill route 和局部
  layout 成功；
- `h/feature` 或 `h/gap` 是该 geometry 的比值，不是作者声明的 process capability
  ceiling；
- Ticket 13 的 `aspect_limit=8` 是本实验室对 blind brief 同时约束 feature/gap 的
  保守政策，不是从四篇论文归纳出的共同制造极限。

因此 paper-geometry 对当前 blind brief 的 expected verdict 是：**Yun
incompatible**（feature AR 10）；**Yang aspect-compatible but grid/height-incompatible**；
**Arbabi aspect/grid-compatible but height-incompatible**；**K axis-only
aspect-compatible, rotation-envelope/grid-incompatible**。这里的 incompatible 是
contract verdict，不是否认论文已经制造或模拟成功。

## 二、Yun 2025：不能把三个 library 拼成一个 comparator

Primary sources:

1. Yun et al., *Nature Communications* 16, 7299 (2025),
   [DOI/article](https://doi.org/10.1038/s41467-025-62577-1).
2. [Official Supplementary Information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-025-62577-1/MediaObjects/41467_2025_62577_MOESM1_ESM.pdf).

### 论文直接给出的事实

- 选定 comparator 是 Fig. 3 的 `850 nm`、NA `0.35`、直径 `0.5 mm` conventional
  full-`2π` numerical metalens；它把高度从 proposed device 的 `500 nm` 对照为
  `800 nm`。[正文 “Comparison between 2π and 4π/3”](https://doi.org/10.1038/s41467-025-62577-1)
- Fig. 3a 在最窄的 conventional meta-atom 旁直接标注 `H/w = 10`。结合
  `H=800 nm`，最小 diameter 是 `80 nm`。这是由两个明确标注值做的几何除法，
  不是作者发布的逐点 response table。
- 正文明确将 conventional 与 proposed 的最大 aspect ratio 描述为从 `10:1`
  降到 `5:1`，并将高 aspect ratio 与 pattern collapse、etching nonuniformity、
  mechanical robustness 联系起来。[正文 Fig. 3 讨论](https://doi.org/10.1038/s41467-025-62577-1)
- Fig. 3a 的 diameter 曲线画到约 `350 nm`，但论文没有发布 comparator 的逐点
  diameter-response 数表或完整 layout；data/code 需向作者索取。

### period 与 gap 的证据断点

当前 case 将 `P=400 nm` 编成 selected comparator 的 published fact，但一手来源中
可以直接定位的 `400 nm` 分别属于：

- Supplementary Fig. 1：angle/material study，`P=400 nm`；
- Supplementary Fig. 2：另一个 full-`2π` supporting library，
  `P=400 nm, H=900 nm, n=2.58`。

主文 Fig. 3 comparator 却是 `H=800 nm`。来源没有把 `P=400 nm` 与这个
`800 nm` comparator 明确绑定。更不能把 `900 nm` supporting library 的 period
静默移植过来，同时排除其 height。

Supplementary Note 9 又称 proposed platform 限制 `w_max=350 nm` 以保证
`100 nm` minimum gap；这个陈述对应的几何中心距应为 `450 nm`，不能与另一个
`P=400 nm` study 自动视为同一个 platform。因此：

```text
if P = 400 nm and w_max = 350 nm:
    minimum gap = 50 nm
    gap aspect  = 800 / 50 = 16

but the source does not certify that pair for the selected comparator.
```

Yun 的 comparator gap aspect ratio 必须标为 **unknown**，而不是选一个跨平台
组合后声称它是论文事实。

### fabrication scope

Fig. 3 conventional comparator 是数值对照，不是论文制造的器件。Methods 中的
PECVD a-Si:H、PMMA EBL、50 nm Cr hard mask、dry etch 和 Cr removal 描述的是
`500 nm` high 的 fabricated 4π/3 wFoV metalens，不能作为 `800 nm` comparator
已制造的证据。[Methods](https://doi.org/10.1038/s41467-025-62577-1)

### 对 brief 的裁决

- `aspect_limit=8` 要求 `800/8=100 nm` minimum feature，直接排除论文标注的
  `80 nm` conventional feature；这不是轻微 quantization，而是改变 full-`2π`
  platform。
- `dimension_step_nm=10` 可以表达 `80 nm`，但仅在 aspect limit 放宽后成立。
- 固定 period grid 是否能表达 `400 nm` 不重要；更早的问题是 `400 nm` 尚未与
  selected comparator 被来源绑定。
- 当前 height prior 对 `850 nm` 只产生 `450/500 nm`，也不可能 blind-select
  paper comparator 的 `800 nm`。

因此这个 case 应称为“在更严格 AR 约束下与 Yun comparator 比较的 blind design”，
或者取得 comparator 原始 platform 数据后再称 reproduction；二者不能同时成立。

## 三、Yang 2018：aspect 很宽松，grid 与 height 才是硬冲突

Primary sources:

1. Yang et al., *Nature Communications* 9, 4607 (2018),
   [publisher/DOI](https://doi.org/10.1038/s41467-018-07056-6).
2. [Author manuscript with Methods](https://arxiv.org/pdf/1807.06907).
3. [Official Supporting Information](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-018-07056-6/MediaObjects/41467_2018_7056_MOESM1_ESM.pdf).

### 论文直接给出的事实

圆偏振 `l/r` sublens 工作在 `1550 nm`，square lattice period `1500 nm`，固定
silicon ellipse 为 `1350×480 nm`，height `340 nm`，位于 silicon dioxide 上。
ellipse 只旋转 orientation 来形成 PB phase；尺寸不随 phase 扫描。
[正文 Fig. 2 与 Eqs. 2–3](https://doi.org/10.1038/s41467-018-07056-6)

Methods 给出的制造路线是：清洗 double-polished SOI；旋涂 `430 nm` ZEP520A；
`100 kV`, `300 pA` EBL；xylene develop/IPA fix；C4F8/SF6 ICP etch；oxygen plasma
去除残胶。[Author manuscript, Methods](https://arxiv.org/pdf/1807.06907)
论文没有声明数值化的最大允许 aspect ratio 或 fabrication grid。

### 几何推导

```text
minimum feature = minor axis = 480 nm
feature aspect  = 340 / 480 = 0.7083

minimum orientation-envelope gap
  = period - major axis
  = 1500 - 1350
  = 150 nm

gap aspect = 340 / 150 = 2.2667
```

椭圆在任意角度沿任意 lattice neighbor 方向的最大投影直径不超过 major axis，
当两个相邻 ellipse 的长轴沿该中心连线时 `150 nm` 可达到。因此这不是只适用于
未旋转 cell 的偶然结果。

### 对 brief 的裁决

- aspect 8 远比论文几何宽松，不构成障碍。
- period `1500 nm` 在 10 nm grid 上。
- `dimension_step_nm=100` 无法表达 `1350` 或 `480 nm`；当前 geometric cell
  validation 会拒绝二者。
- 当前 `1550 nm` height prior 是 `800/850/900 nm`，无法表达 `340 nm`，并且
  把 propagation-phase 的高度量级错误地施加到了 PB half-waveplate 上。

Yang case 若用于 paper-locked reproduction，应使用 exact geometry（或至少 10 nm
lateral grid）和 PB/process-specific height contract；若用于 blind design，不能把
任何不同尺寸的 ellipse 说成复现了论文 fixed Jones cell。

## 四、Arbabi 2015：四案中与当前 arithmetic domain 最接近

Primary sources:

1. Arbabi et al., *Nature Communications* 6, 7069 (2015),
   [DOI](https://doi.org/10.1038/ncomms8069).
2. [Author manuscript including Methods and Supplementary Information](https://arxiv.org/pdf/1410.8261).

### 论文直接给出的事实

HCTA library 在 `1550 nm` 使用 fused silica 上的 circular amorphous-silicon posts，
hexagonal lattice constant `800 nm`，post height `940 nm`，diameter 从
`200` 到 `550 nm`；该范围报告 transmission above `92%` 并覆盖 full phase。
[Fig. 1d and design discussion](https://arxiv.org/pdf/1410.8261)

制造采用 ZEP520A EBL；图形经 lift-off 转移到 `70 nm` Al2O3 hard mask；随后以
C4F8/SF6 plasma dry-etch `940 nm` a-Si:H film。
[Methods](https://arxiv.org/pdf/1410.8261)
论文对 high-contrast platform 的 manufacturability 有定性论述，但没有给出一个
可移植的数值 AR ceiling 或直径 quantization step。

### 几何推导

```text
minimum feature = 200 nm
feature aspect  = 940 / 200 = 4.70

minimum gap = 800 - 550 = 250 nm
gap aspect  = 940 / 250 = 3.76
```

hexagonal lattice 的最近邻中心距就是 lattice constant；圆柱无 orientation 问题，
所以该 gap 是已给 library 范围的精确几何结果。

### 对 brief 的裁决

- `aspect_limit=8` 对 feature 和 gap 都容纳 paper library。
- `P=800 nm` 在固定 10 nm period grid 上；`200` 和 `550 nm` 两个 range endpoint
  也在 10 nm lateral grid 上。
- 但论文没有说明 layout 只使用 10 nm quantization；MetaCraft step 只是 adapted
  realization，不能声称逐柱一致。
- 当前 fabrication arithmetic 在 `H=940, P=800, aspect=8, step=10` 下产生
  `120–680 nm`，比论文验证的 `200–550 nm` 宽。通过 aspect gate 不等于通过
  optical response gate。
- 当前 height prior 最高 `900 nm`，仍无法采用论文 `940 nm`。

因此 Arbabi 最适合检验“先形成可制造 arithmetic domain，再由真实 response
收窄到 optical library”，但不能用 arithmetic range 取代 Fig. 1d response evidence。

## 五、Khorasaninejad 2016：5 nm 尾数和旋转间隙都不能忽略

Primary sources:

1. Khorasaninejad et al., *Science* 352, 1190–1194 (2016),
   [author-hosted version of record](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf),
   [DOI](https://doi.org/10.1126/science.aaf6644).
2. Official Science supplementary download endpoints returned HTTP 403 on
   2026-08-06. No secondary source was used to fill inaccessible details.

### 论文直接给出的事实

532 nm device 使用 square cell `S=325 nm` 和 amorphous-TiO2 rectangular fin
`W=95, L=250, H=600 nm`；PB rotation 形成 phase，器件直径 `240 μm`、焦距
`90 μm`、NA `0.8`。[Fig. 1 and caption](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf)

制造不是 conventional top-down TiO2 etch。作者以 ZEP520A EBL 形成与
`H=600 nm` 同高的 resist mold，conformal ALD 填入 amorphous TiO2；为 void-free
fin，ALD deposition thickness 必须至少 `W/2 = 47.5 nm`；随后 blanket RIE 去除
顶层 TiO2，再 strip resist。论文将约 `90°` smooth sidewalls 归因于尺寸由 resist
定义，而非 conventional lateral dry etch。
[Planar lens design and fabrication](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf)

作者称结构为 high-aspect-ratio，但没有给出一个通用于 feature 与 gap 的最大
数值 limit。

### 两种 gap 推导必须分开

若只看未旋转、长边沿 lattice axis 的 cell：

```text
minimum feature = 95 nm
feature aspect  = 600 / 95 = 6.3158

axis-aligned gap = 325 - 250 = 75 nm
axis gap aspect  = 600 / 75 = 8.0
```

但 PB fin 会旋转。矩形在某 lattice neighbor 方向的最大投影宽度是其 diagonal：

```text
diagonal = sqrt(250^2 + 95^2) = 267.4416 nm
orientation-envelope gap
         = 325 - 267.4416
         = 57.5584 nm
gap aspect = 600 / 57.5584 = 10.4242
```

这个下界可由两个相邻、同角度 rectangle 的对向 corner 达到；然而没有完整
layout，就不能声称 fabricated device 必然包含恰好该 pair。它证明的是 generic
rotatable-cell validator 不能只检查 `period - long_axis`。

### 对 brief 的裁决

- paper period `325 nm` 不在固定 10 nm period grid。
- paper short side `95 nm` 不在 `dimension_step_nm=10` 的尺寸 grid。
- 若 exact reproduction 改用 5 nm grid，则 `H/8=75 nm`、最大 axis-aligned
  long side `325-75=250 nm`，恰好容纳 paper geometry；这解释了为什么两个
  `5 nm` 尾数都具有结构意义，不是无关紧要的 rounding noise。
- 但真实 rotation envelope 仍给出 `57.56 nm` gap；若 `aspect_limit=8` 被定义为
  对所有 orientation 的 gap hard limit，paper cell 会被拒绝。论文的 ALD resist-fill
  route 已制造该 cell，说明统一 limit 的物理含义错了，而不是论文不可靠。
- 当前 visible-band height prior 包含 `600 nm`；这是四案中唯一可直接选择 paper
  height 的 case。

## 六、MetaCraft brief 的功能审计

当前规则来源：

- case builder 对四案统一设置 `aspect_limit=8`，steps 为 `10/100/10/10 nm`：
  [`metalens_benchmark/`](../../examples/metalens_benchmark/)；
- period owner 固定 `PERIOD_GRID_NM = 10`：
  [`period.py`](../../src/metacraft/science/metalens/period.py)；
- fabrication range 以 `ceil_to_step(height/aspect_limit)` 同时作为 minimum feature
  和 minimum gap，再令 `maximum_feature = period - minimum_feature`：
  [`height.py`](../../src/metacraft/science/metalens/height.py)；
- geometric validator 只检查 short axis 与 long axis，不检查 rotated diagonal：
  [`geometric_phase.py`](../../src/metacraft/science/metalens/geometric_phase.py)；
- height prior 在 `λ≤700 nm` 给 `500–800 nm`，否则只给 `0.5λ–0.6λ` 的 50 nm
  grid：[`height.py`](../../src/metacraft/science/metalens/height.py)。

### 在 paper geometry 上现场运行 current arithmetic rule

| Case | Current arithmetic at paper `H/P` | Paper geometry outcome |
| --- | --- | --- |
| Yun | min `100`, max `300`, step `10` | paper min `80` fails; plotted high-width end may also fail; exact comparator `P` unresolved |
| Yang | min `100`, max `1400`, step `100` | `480` and `1350` both off-grid; paper `H=340` is outside prior |
| Arbabi | min `120`, max `680`, step `10` | `200–550` fits arithmetic; `H=940` is outside prior |
| K | paper `P=325` fails period grid before range; hypothetically min `80`, max `245`, step `10` | `95` off-grid and `250>245`; with exact 5 nm grid the axis-aligned geometry fits, rotated clearance still does not fit a universal gap AR 8 |

这说明 `aspect_limit`、period grid、dimension step、height prior 和 optical response
不是四个可以独立调整的旋钮。它们共同定义一个 feasibility domain。

## 七、建议

### 1. 把“最大 period”改成“最大可行 period”

确定性 default 可以保留，但必须排在所有 hard constraints 之后：

```text
physical response ceilings
  -> process-specific feature constraint
  -> orientation-aware clearance constraint
  -> lateral/height fabrication grids
  -> required fixed-cell or candidate-library semantics
  -> admitted response feasibility
  -> greatest remaining grid-aligned period
```

物理 ceiling 只回答“不会违反 sampling/order contract”，不回答“能否制造”或
“能否覆盖所需 phase/Jones response”。因此 `200 nm` 是无依据 fixture，并不推出
“最大 ceiling 值”在四案中都正确。

### 2. 终止一个 `aspect_limit` 承担两种物理含义

建议将 fabrication contract 至少拆为：

```text
maximum_feature_depth_to_width
minimum_edge_gap_nm or maximum_gap_depth_to_width
lateral_dimension_step_nm
height_step_nm
fabrication_route
orientation_clearance_policy
```

feature AR 约束柱体机械稳定性/刻蚀或填充；gap AR 约束 etch trench、resist wall、
near-field coupling 或几何碰撞。EBL+dry etch 与 resist-mold+ALD 不能共享一个无来源
的数字 8。

### 3. 各 case 的最小修订方向

- **Yun**：先撤回 comparator `P=400` 的“已验证 published fact”，补齐同一
  `H=800` platform 的 period/range provenance；若保留 aspect 8，则明确这是
  stricter-manufacturability blind comparison，不是 conventional reproduction。
- **Yang**：paper-locked path 使用 exact `1500/340/1350/480 nm`；blind path
  使用 PB-specific height prior。删除未经论文支持的 `100 nm` step，或明确它是
  独立 process intent，不能用于 paper geometry。
- **Arbabi**：保留 10 nm adapted sweep，但让 response evidence 将 arithmetic
  `120–680` 收窄至已验证 optical range；height domain 必须能表达 `940 nm`。
- **K**：exact path 使用 5 nm/literal geometry；gap validator 对 rotatable
  rectangle 使用 diagonal/support-function clearance；fabrication route 记录 ALD
  constraint，不能用 generic dry-etch AR 代替。

### 4. 用这四案测试 brief，而不是把论文答案喂给 blind selector

四案恰好覆盖四种不同失败模式：

```text
Yun     -> feature AR 与 platform provenance
Yang    -> PB height prior 与 coarse dimension grid
Arbabi  -> arithmetic domain 必须由 response evidence 收窄
K       -> exact 5 nm geometry 与 rotation-aware gap / ALD process
```

blind benchmark 应评价 selector 是否形成有来源的 feasible domain；paper-locked
reproduction 则显式固定论文 geometry。两者共享 comparison vocabulary，但不共享
选择权。

## Source-access log

- Yun Nature article and official SI: accessible 2026-08-06.
- Yang Nature article, official SI, and author manuscript: accessible 2026-08-06.
- Arbabi author manuscript containing Methods/SI: accessible 2026-08-06.
- Khorasaninejad author-hosted article: accessible 2026-08-06.
- Khorasaninejad official Science supplementary endpoints: HTTP 403 on
  2026-08-06; inaccessible claims remain explicitly unknown.
