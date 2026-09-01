---
record_type: research_record
date: 2026-07-30
status: research_finding
authority_level: none
current_capability: false
---

# Order ceiling 与 low-NA propagation 主例

## 结论

本轮不应把 `order ceiling` 从当前 G0-only 完整场方法的硬适用边界降为
warning，也不应继续使用 Zhan 2016 作为 canonical low-NA propagation
brief。

推荐替换为：

```text
yun_2025_low_na_propagation
```

具体选择 Yun 等人 2025 年论文中的 conventional full-`2π` numerical
comparator，而不是论文提出的 `4π/3` optimized design。论文事实固定器件
目标与单元平台；MetaCraft 仍独立生成 8、12、16 阶 `phase set`。因此它是
**quantized adapted reproduction**，不是原版图逐点复刻。

一句话裁决：

> 当前方法守住硬界，未来方法扩展证据；论文负责给出命题，MetaCraft 负责形成三组答案。

## 一、order ceiling 不应全局降级

### 当前方法为何需要硬边界

[ADR 0009](../adr/0009-keep-g0-only-metalens-proofs-in-the-zeroth-order-domain.md)
说明，当前 low-NA locally periodic proof 使用 Lumerical G0 complex response
构成完整 aperture field。当非零传播阶次在该保守判据下可能开放时，单独一个
G0 channel 不包含其他开放阶次，因而不足以支持“完整输出场”这一较强 claim。

当前 method 的 physical ceiling 是：

```text
physical ceiling = min(sampling ceiling, order ceiling)

sampling ceiling = wavelength / (2 numerical aperture)
order ceiling    = wavelength / (substrate index + numerical aperture)
```

其中 `order ceiling` 是 MetaCraft 的保守推导，不是文献中的通用金科玉律。
但只要 method 仍同时声称：

1. evidence 只包含 G0 complex response；
2. 该 evidence 足以建立完整 aperture field；

它就必须保留 hard applicability。把它改成 warning 会恢复已被
[ADR 0009](../adr/0009-keep-g0-only-metalens-proofs-in-the-zeroth-order-domain.md)
否决的 ADR 0007 语义：系统知道可能存在未表达通道，却仍让 G0-only proof
关闭完整场 claim。

### 何时可以只是 warning

`order ceiling` 不是所有未来 method 的硬门。以下两类能力可以在
`multi order` regime 中继续工作：

```text
order-resolved response
  -> retain every required propagating order
  -> reconstruct the declared output field

near-field response
  -> retain a qualified complex field on one reference surface
  -> propagate that field without pretending it is one G0 coefficient
```

在这些 method 中，超过 conservative order ceiling 可以成为一条可见
`caution`，因为证据形式已经表达了原先缺失的通道或参考面场。method
applicability、evidence schema 与 result claim 必须一起改变；不能只把错误级别
从 hard 改成 warning。

Ansys 的 grating projection 文档说明，周期结构的场由离散衍射阶次组成，只有
落在介质 light cone 内的阶次传播；其 S-parameter workflow 也允许选择具体
grating order。这支持“G0 是一个明确通道”，不支持“G0 在开放其他阶次时仍自动
等于总场”。[Ansys, *Grating projections in FDTD —
overview*](https://optics.ansys.com/hc/en-us/articles/360034394354-Grating-projections-in-FDTD-overview)；
[Ansys, *Metamaterial S parameter
extraction*](https://optics.ansys.com/hc/en-us/articles/360042095873-Metamaterial-S-parameter-extraction)。

因此正确的对偶是：

```text
G0-only complete-field method
  -> order ceiling is hard

order-resolved or near-field method
  -> order regime is reported
  -> completeness follows from richer evidence
```

### 不应因 canonical brief 修改物理边界

Zhan 2016 的 633 nm、443 nm period、NA 约 0.1113 器件，在 fused silica
示例折射率约 1.457 下具有：

```text
order ceiling ≈ 633 / (1.457 + 0.1113)
              ≈ 403.6 nm
```

论文 period 超过当前 G0-only applicability。它可以成为未来
order-resolved / near-field case，但不应通过放松 ADR 0009 被塞进当前
canonical route。

## 二、Yun 2025 是更合适的主例

### Paper-locked facts

Yun 等人的论文在 850 nm 比较 conventional full-`2π` metalens 与论文提出的
`4π/3` metalens。本文只选择前者：

| fact | paper value |
| --- | ---: |
| wavelength | 850 nm |
| numerical aperture | 0.35 |
| aperture diameter | 0.5 mm |
| derived focal length | about 669.1 µm |
| phase mechanism | propagation phase |
| comparator | conventional full `2π` |
| atom | cylindrical hydrogenated-amorphous-silicon pillar |
| substrate | fused silica |
| square-lattice period | 400 nm |
| comparator height | 800 nm |
| simulated focusing efficiency | 82.8% |

论文明确说明 full-`2π` comparator 的高度为 800 nm，并报告其模拟 focusing
efficiency 为 82.8%；`4π/3` 设计使用 500 nm 高度并属于论文的 limited-phase
optimization，不能与 comparator 拼接为一个 brief。[Yun et al., *Nature
Communications* 16, 7299
(2025)](https://www.nature.com/articles/s41467-025-62577-1)；
[Supplementary
information](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-025-62577-1/MediaObjects/41467_2025_62577_MOESM1_ESM.pdf)。

### 它通过当前判据

论文 supporting analysis 给出 substrate index 1.472。由此：

```text
sampling ceiling = 850 / (2 × 0.35)
                 ≈ 1214.3 nm

order ceiling    = 850 / (1.472 + 0.35)
                 ≈ 466.5 nm
```

ADR 0009 的 compiled limit 是严格小于 physical ceiling 的最大 10 nm
倍数，因此为 460 nm。论文 period 400 nm 小于该 limit，能够进入当前
G0-only proof。真实执行仍必须引用 qualification-admitted solver-native
material sample；论文数值只证明公开设计与规则相容。

### 8/12/16 是 MetaCraft 的答案，不是论文的相位阶数

论文使用完整 `2π` phase library。canonical case 应固定相同 paper platform，
再由 MetaCraft 独立形成：

```text
same admitted cell library
  -> eight-state phase set
  -> twelve-state phase set
  -> sixteen-state phase set
```

三组都是正式 result，没有“论文六阶优先”或“只用八阶主结果”。论文的
82.8% 属于作者的连续或高密度布局，只作 comparison，不是任一量化结果的硬
阈值。

这与 low-NA geometric route 形成自然对偶：

```text
propagation phase
  many admitted cells
  -> 8 / 12 / 16 cell states

geometric phase
  one admitted cell
  -> 8 / 12 / 16 orientation states
```

### Fabrication domain 与候选数量

若当前 brief 使用 height 800 nm、aspect limit 8、period 400 nm，则统一
feature / gap rule 给出约：

```text
minimum diameter = 800 / 8 = 100 nm
maximum diameter = 400 - 100 = 300 nm
```

若 `dimension step = 10 nm`，arithmetic domain 有 21 个圆柱候选，数量上能够
支持 16 个不同 state；能否得到完整、低损耗且跨越 seam 的 8/12/16 phase
sets，必须由真实 response evidence 决定，不能由候选计数或 advice 保证。

## 三、为何不选 1550 nm / 780 nm 的更大周期候选

Kim 等人 2020 的 in-fiber metalens 确实提供了一个看似更漂亮的数值组合：

```text
wavelength          = 1550 nm
numerical aperture  = 0.398
period              = 780 nm
height              = 900 nm
diameter range      = 100–500 nm
phase coverage      = full 2π
focal length        = 30 µm
meta-atom count     = 877
```

论文使用的 silica index 为 1.45，因此：

```text
sampling ceiling ≈ 1947.2 nm
order ceiling    ≈ 838.7 nm
compiled limit   = 830 nm
```

780 nm period 通过当前判据，而且计算规模很小。[Kim et al., *Scientific
Reports* 10, 20898
(2020)](https://www.nature.com/articles/s41598-020-77821-5)。

但它不是更干净的 canonical replacement：

- metalens 位于 large-mode-area photonic-crystal fiber 端面；
- incident field 是该 fiber 的 guided mode，不是当前标准 plane wave；
- substrate 不是一个均匀 silica half-space，而是包含 hexagonal air-hole
  cladding 的 PCF；
- 精确复刻会要求新增 guided-mode incident field 与 structured-substrate
  表达。

把它改成 silica substrate 上的 plane-wave metalens 会失去论文的器件身份，
只剩 adapted geometry。为得到较大的 period 而扩大 brief、field 与 solver
边界，不符合本轮 Sonnet 收敛目标。因此它适合作为未来 fiber-integrated aim
或 incident-field extension 的研究 case，不适合作为当前四 brief 之一。

## 最终推荐

```text
canonical case
  yun_2025_low_na_propagation

paper truth
  850 nm · NA 0.35 · 0.5 mm diameter
  400 nm period · 800 nm height
  cylindrical a-Si:H on fused silica
  conventional full 2π comparator

MetaCraft realization
  8 / 12 / 16 phase sets
  deterministic cyclic selection

explicit omission
  4π/3 limited-phase optimization

fidelity
  quantized adapted reproduction
```

不修改 ADR 0009。将来若实现 order-resolved 或 near-field response，再以新的
method applicability 允许 `multi order`，而不是弱化现有 method 的诚实边界。

> 边界不为论文退让，论文应为方法作证；  
> 三组相位各自成篇，一条主链始终守真。

