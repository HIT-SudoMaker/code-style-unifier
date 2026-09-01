---
record_type: research_record
date: 2026-07-30
status: research_finding
authority_level: none
current_capability: false
---

# Low-NA propagation brief：最终论文选择

## 结论

最终建议用以下 case 取代 `compact_low_na_propagation`：

```text
yun_2025_low_na_propagation
```

它选择 Yun 等人 2025 年论文中的 **conventional full-`2π` numerical
comparator**，不选择论文提出的 `4π/3` optimized design。case fidelity
应记录为 **quantized adapted reproduction**：论文固定的器件与单元事实原样
保留，MetaCraft 独立形成 8、12、16 阶 `phase set`。

这个选择比 Zhan 2016 更适合作为当前 canonical brief，决定性原因不是论文更新，
而是论文的 400 nm 周期落在 ADR 0009 的 G0-only applicability 内；Zhan 的
443 nm 周期不在。Yun 器件更大，但 0.5 mm 口径、约 1250 个格点横跨阵面，仍可在
本地工作站上用 Torch 分块和焦区传播验证。

一手来源：
[Yun et al., *Nature Communications* 16, 7299
(2025)](https://doi.org/10.1038/s41467-025-62577-1)；
[期刊补充材料](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-025-62577-1/MediaObjects/41467_2025_62577_MOESM1_ESM.pdf)。

## Paper-locked facts

### 器件事实

| fact | paper value |
| --- | ---: |
| design wavelength | 850 nm |
| numerical aperture | 0.35 |
| aperture diameter | 0.5 mm |
| derived focal length | about 669.1 µm |
| phase mechanism | propagation phase |
| selected comparator | conventional full `2π` |
| atom | cylindrical hydrogenated-amorphous-silicon pillar |
| substrate | fused silica |
| square-lattice period | 400 nm |
| comparator height | 800 nm |
| simulated focusing efficiency | 82.8% |

焦距由论文的口径和 NA 推导：

```text
focal length
  = radius × sqrt(1 - NA²) / NA
  ≈ 669.1 µm
```

正文明确把 conventional `2π` comparator 与论文的新方法分开：前者高度
800 nm，后者使用 `4π/3` phase range、高度 500 nm，并经过 limited-phase
optimization。两者不能拼成一个 brief。正文还报告 conventional comparator
的模拟 focusing efficiency 为 82.8%，MTF 接近理论衍射极限。

### 必须保留的来源缺口

补充材料 Note 3 另有一个用于 supercell diffraction study 的 full-`2π`
library：period 400 nm、height 900 nm、atom index 2.58、substrate index
1.472。它不是正文 Fig. 3 中高度 800 nm 的 comparator 本身。

因此：

- canonical comparator 锁定正文的 800 nm；
- 900 nm 只属于独立的 supporting analysis；
- material index 可作为论文参考值，但真实执行仍由 solver-native material
  evidence 资格化；
- 原始逐点 diameter-to-response 数据未公开，不能声称重建了作者的原版库。

这不会妨碍 MetaCraft 重新求解一个同平台 cell library，却把结果限定为
adapted reproduction。

## ADR 0009：为什么 Yun 可执行

论文给出 `substrate_index = 1.472`，器件 NA 为 0.35。于是：

```text
sampling ceiling = 850 / (2 × 0.35)
                 ≈ 1214.3 nm

order ceiling    = 850 / (1.472 + 0.35)
                 ≈ 466.5 nm
```

根据 ADR 0009，compiled period limit 是严格小于物理 ceiling 的最大 10 nm
倍数，因此该论文条件下的 limit 为 460 nm。论文 period 400 nm：

```text
400 nm < 460 nm
```

故它同时满足 sampling ceiling 和 order ceiling，可以使用当前 G0-only
propagation proof。最终 order verdict 仍必须引用真实 solver-native substrate
sample；上述计算只证明论文公开参数与当前规则相容。

这与 Zhan 2016 形成关键区别。Zhan 的 500 µm 器件具有：

```text
wavelength = 633 nm
NA         = 0.111304
period     = 443 nm
```

采用 Malitson fused-silica 数据的示例 `substrate_index ≈ 1.457012` 时，
order ceiling 约为 403.6 nm，ADR 0009 的 strict 10 nm limit 为 400 nm。
论文 443 nm 周期超出当前 G0-only route。Fused-silica 色散依据
[Malitson, *JOSA* 55, 1205–1209
(1965)](https://doi.org/10.1364/JOSA.55.001205)。

不能为了选择更小的论文器件而放松这条边界。

## 8/12/16 与论文 `2π` 的关系

Yun conventional comparator 使用完整 `2π` phase range，但不是 MetaCraft
当前 8、12、16 阶 phase sets 的原版图。canonical case 应并列形成：

```text
same paper-locked cell platform
  → eight-state phase set
  → twelve-state phase set
  → sixteen-state phase set
```

三组结果均通过 cyclic phase distance 做确定性选择，并分别报告：

- phase coverage 与 seam continuity；
- transmitted magnitude；
- selected cell identities；
- aperture state map；
- focal-region metrics。

论文 82.8% 是连续/高密度作者设计的 numerical comparison，只作 paper
comparison，不是任一 MetaCraft 量化结果的硬阈值。

该安排也与 low-NA geometric case 对偶：

```text
low-na propagation
  many admitted cells
  → 8 / 12 / 16 phase states

low-na geometric
  one admitted cell
  → 8 / 12 / 16 orientation states
```

二者都降低加工自由度，但前者离散 cell identity，后者离散 orientation；
不得用一个 generic quantizer 抹去两种物理含义。

## 工作站负担

论文 400 nm period 下：

```text
sites across diameter
  = 500 µm / 0.4 µm
  = 1250

occupied circular sites
  ≈ π / 4 × 1250²
  ≈ 1.23 million
```

这比 Zhan 2016 的约 253 格点跨径显著更大，但仍不是 whole-device FDTD
任务。合理交付是：

1. periodic cell response 有界求解；
2. vectorized aperture placement；
3. Torch field propagation；
4. focal ROI 和 z batching；
5. full live run 最后人工放行。

不得为追求论文复现而启动 0.5 mm whole-device FDTD，也不需要修改 Rust 或引入
optimizer。

## 候选对照

| candidate | parameter completeness | ADR 0009 | workstation load | verdict |
| --- | --- | --- | --- | --- |
| **Yun 2025 conventional `2π`** | 波长、NA、口径、period、正文 height、材料关系和数值指标充分；原始响应表缺失 | 400 nm 小于 460 nm limit，可进入当前 G0-only proof | 1250 格点跨径；Torch 分块可承受，whole-device FDTD 不可取 | **canonical** |
| Zhan 2016, f=500 µm | 633 nm、56 µm radius、443 nm period、633 nm height、96–221 nm radius、六阶非常完整 | 443 nm 大于约 400 nm limit，当前 G0-only proof 不可执行 | 约 253 格点跨径，最轻 | 保留为 order-resolved / near-field future case |
| Zhao 2021 PR metalens | 532 nm、NA 0.196、640 nm 高 SiN 圆柱，且有 Strehl/DOF | period、口径、焦距和完整 diameter library 未在公开正文形成可移植 case | 未能可靠界定 | 不选 |

Zhan 一手来源：
[Zhan et al., *ACS Photonics* 3, 209–214
(2016)](https://doi.org/10.1021/acsphotonics.5b00660)；
[作者公开稿](https://www2.ee.washington.edu/research/amlab/Papers_Journals/Alan_Zhan_Metasurface.pdf)。  
Zhao 一手来源：
[Light: Science & Applications 10, 52
(2021)](https://doi.org/10.1038/s41377-021-00492-y)。

## 最终边界

```text
name
  yun_2025_low_na_propagation

paper truth
  850 nm · NA 0.35 · diameter 0.5 mm
  period 400 nm · height 800 nm
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

一句话收束：

> 周期守界，论文可验；三组离散，各自成篇。

