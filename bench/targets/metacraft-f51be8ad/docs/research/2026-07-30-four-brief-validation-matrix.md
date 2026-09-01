---
record_type: research_record
date: 2026-07-30
status: research_finding
authority_level: none
current_capability: false
---

# 四个 metalens brief 的验证矩阵

## 研究问题

为 MetaCraft 选择一组科学上诚实、计算上可承受的 canonical cases，覆盖：

| | propagation phase | geometric phase |
| --- | --- | --- |
| low na | low-na propagation | low-na geometric |
| high na | high-na propagation | high-na geometric |

本记录只核对论文事实、原始计算方法、可复刻范围，以及 brief、advice 与论文
约束之间的权限关系。它不改变当前能力，也不替代后续 ADR、spec 或验证证据。

## 结论先行

推荐矩阵如下：

1. **low-na propagation：Johansen 2024 平台上的 MetaCraft compact standard。**
   论文原器件直径 2.5 mm，且精确直径映射数据未随正文公开，不适合作为默认
   live reproduction；但其 940 nm、400 nm 周期、500 nm 高圆柱及
   CPA/RFA--ASM 方法，是当前低 NA 方法最清楚的外部基准。
2. **low-na geometric：Yang 2018 的一个 `l` 或 `r` 子透镜。**
   22.5 µm 方形口径、15 × 15 个格点，参数完整，适合忠实复刻。
3. **high-na propagation：Arbabi 2020 的 50 µm 数值器件。**
   它比 400 µm 实验器件更适合工作站，并且正面检验 gradient-aware response，
   而不是把低 NA 的 8/12/16 phase set 硬推到高 NA。
4. **high-na geometric：Khorasaninejad 2016 的 532 nm 器件。**
   单元和整镜参数完整；周期单元 FDTD 加 Torch 矢量传播可承受，但 240 µm
   整镜的 full-device FDTD 不应成为 canonical gate。

这四项并不意味着四条固定 workflow。它们是四组输入和参考事实；compiler
仍按 method applicability 组合 proof。

## 一、low-na propagation：Johansen 2024

一手来源：[Communications Physics 7, 123 (2024)](https://www.nature.com/articles/s42005-024-01598-6)。

### 论文固定事实

| 事实 | 论文值 |
| --- | ---: |
| wavelength | 940 nm |
| selected low NA | 0.16 |
| physical lens diameter | 2.5 mm |
| illuminated diameter | 2.4 ± 0.1 mm |
| focal length at NA 0.16 | 7.348 mm |
| atom | circular amorphous-silicon pillar |
| designed / measured height | 500 / 499 nm |
| square-lattice period | 400 nm |
| substrate | D263T Eco glass, backside ARC |
| measured silicon index at 940 nm | 3.55 |
| illumination | unpolarized TEM00 in experiment |

### 原始计算

- Python RCWA 和 lateral PBC 建立 periodic cell library；
- 从 zeroth-order complex transmission 得到一个 cell 的 constant field
  （CPA），或 cell 内 5 × 5 sampled field（RFA）；
- 将完整 aperture field 交给自研 scalar ASM；
- 在焦面半径 45 µm 的圆内积分，以对应实验探测器；
- 对能量积分逐步 oversample 到收敛。

论文明确报告：NA 0.16 时 measured absolute focusing efficiency 为 91.3%，
不同晶圆和测量配置得到 91–94%；CPA 与 RFA 在这一 NA 下接近。论文同时指出
CPA 只到约 NA 0.2 可靠，而 RFA 将定量一致性延伸到约 NA 0.6。

### 复刻裁决

Lumerical FDTD 可以重建同一 periodic response，Torch 可以重建 CPA/RFA
aperture 并运行 ASM；这属于**物理方法复刻**，不是原 RCWA realization 的
逐位复刻。论文的 diameter-to-response 原始数据只声明可向作者索取，因此
仅凭正文重新求出的 library 也不能声称拥有原版版图。

原 2.5 mm 器件横跨约 6250 个格点。普通全平面 2× padding 会让默认验证过重。
因此 canonical brief 应使用同一材料平台和 NA 的 compact MetaCraft standard，
明确标注为标准例；论文原尺寸只用于离线 CZT/ROI 或专门的 paper comparison。

## 二、low-na geometric：Yang 2018

一手来源：[Nature Communications 9, 4607 (2018)](https://www.nature.com/articles/s41467-018-07056-6)。

### 论文固定事实

| 事实 | 论文值 |
| --- | ---: |
| wavelength | 1550 nm |
| focal length | 30 µm |
| footprint | 22.5 µm × 22.5 µm |
| nominal NA | 0.32 |
| square-lattice period | 1500 nm |
| atom | silicon elliptical pillar |
| underlayer | silicon dioxide |
| height | 340 nm |
| major / minor axes | 1350 / 480 nm |
| circular sublens | one of `l` or `r` |

周期与口径恰好形成 15 × 15 个 lattice sites。论文用 Lumerical FDTD，
`x/y` PBC、`z` PML，在 1550 nm 正入射下求两个本征轴的 complex
transmission。固定椭圆柱近似半波片；相位只由 orientation 在 `[0, π)`
连续产生，不扫 orientation，也不构造 8/12/16 phase set。

论文报告 circular-polarization sublens 的 theoretical / measured focusing
efficiency 为 60% / 26%，定义为 focal-spot power 与入射到 metalens 的功率之比。

### 复刻裁决

这是四项中最适合忠实 full-device reproduction 的一项。Lumerical 可复刻
paper-native unit response，15 × 15 aperture 也足以做 full-device FDTD；
Torch 可消费导出的 exit-plane `field` 并传播。

但 1500 nm 周期不属于当前 G0-only proof 的 zeroth-order domain。不得把周期
静默缩小，也不得只用 G0 宣称建立了完整 aperture field。忠实复刻应使用：

- full-device near-field，或
- 经过 qualification 的 order-resolved / near-field response。

这也是为什么 paper reproduction 的周期和尺寸必须固定，不能交给 advice
重新选择。

## 三、high-na propagation：Arbabi 2020

一手来源：[Scientific Reports 10, 7124 (2020)](https://www.nature.com/articles/s41598-020-64198-8)。

### 论文固定事实

| 事实 | 论文值 |
| --- | ---: |
| wavelength | 915 nm |
| numerical device diameter | 50 µm |
| focal length | 20 µm |
| NA | 0.78 |
| incident field | normal x-linear plane wave |
| atom | square amorphous-silicon nano-post |
| substrate | fused silica |
| refractive indices used | 3.65 / 1.45 |
| square-lattice period | 350 nm |
| height | 590 nm |
| width range | 60–200 nm |
| available phase coverage | 1.63π |

### 原始计算

论文没有把高 NA 视为普通 local library 的加长版。它：

1. 用 periodic cell transmission 建立 350 nm platform 的 design curve；
2. 针对多个 grating periods，每个 period 计算 40 个 phase origins；
3. 用 RCWA 提取目标 transmitted diffraction order 的 complex coefficient；
4. 对同一 deflection angle 的 grating family 做 coherent averaging；
5. 用该结论选择仅覆盖 1.63π、但大角度效率更好的 platform；
6. 对 50 µm 器件做 full-wave FDTD；
7. 在 pillars 上方四分之一波长处取 transmitted `Ex`，再用 plane-wave
   expansion 得到焦区。

数值器件报告 89% transmission 和 79% focusing efficiency；后者是在焦点周围
半径 5 µm 的圆内积分，并除以入射到 aperture 的功率。对照设计分别为 75%
和 63%。400 µm 实验器件报告 77% focusing efficiency。

### 复刻裁决

50 µm 数值器件是合理的 canonical high-na propagation target。Lumerical 的
periodic supercell FDTD 可以求同一 grating diffraction coefficients，尽管论文
使用 RCWA；Torch 可以实现 coherent averaging、deterministic layout 与
plane-field propagation。

正文没有提供原 design curve 的逐点数表。因此可以忠实复刻论文的**方法、平台
与公开指标**，但不能在没有作者原始数据时声称版图逐位相同。验收应比较：

- phase-gradient / deflection response；
- 89% transmission 与 79% simulated focusing efficiency 的趋势和误差；
- complex focal field；

而不是要求重新求出的每个 post width 与论文内部版图逐点相等。

该案例不能复用低 NA 的完整 `2π` 与 8/12/16 phase-set contract；论文的关键
结论恰恰是 1.63π platform 在大角度下优于传统 2π platform。

## 四、high-na geometric：Khorasaninejad 2016

一手来源：[Science 352, 1190–1194 (2016) 作者公开稿](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf)。

### 论文固定事实（选 532 nm 器件）

| 事实 | 论文值 |
| --- | ---: |
| wavelength | 532 nm |
| diameter | 240 µm |
| focal length | 90 µm |
| NA | 0.8 |
| incident polarization | right circular |
| atom | amorphous-TiO₂ rectangular nanofin |
| substrate | glass |
| width / length / height | 95 / 250 / 600 nm |
| center-to-center spacing | 325 nm |

论文用 Lumerical FDTD、`x/y` PBC、`z` PML 计算 half-waveplate conversion；
RCP 通过 rotation 获得 `+2 × orientation` 的 geometric phase并转为 LCP。
论文报告 532 nm 器件的 measured FWHM 为 375 nm、focusing efficiency 为
73%，三种波长器件的 measured Strehl ratios 均接近 0.8。

### 复刻裁决

periodic Jones response 和约 738 格点直径的 analytic aperture 可以由
Lumerical + Torch 承担；它适合作为 vector focal-region 与 polarization
conversion 的高 NA 回归。240 µm 整镜 full-device FDTD 不适合作为工作站
canonical gate，因此只能诚实区分：

- **paper-layout / response-method reproduction**：可以；
- **whole-device Maxwell reproduction**：本轮不承诺；
- **experimental efficiency reproduction**：不能由无制造误差的计算硬验收。

主要可比量应为 converted / retained handedness、焦点位置、x/y FWHM、
longitudinal-field fraction、Strehl-like field comparison；73% 只作为实验
comparison，不作为模拟硬阈值。

## brief 与 advice 的权限

同一个文本不能既“故意隐去 period/height 来考 Adviser”，又声称“忠实复刻
论文”。应把一个 case 分成两种用途，而不是混成一个模糊 brief。

### 盲测 design brief

用于测试 Adviser 是否从 wavelength、NA、focal length、material families、
shape、polarization 和 fabrication intent 推断出合理量级：

- period recommendation；
- height recommendation；
- lateral range 或固定-cell geometry recommendation；
- response method 与计算预算建议。

这些输出只是 advice。论文值放在不可见的 reference 中评分，不能反向伪装成
Adviser 自己知道的事实。该阶段只评估量级、物理理由和是否诚实报告不确定性。

### paper-locked reproduction brief

用于后续 sweep、response 和 field calculation 时，必须固定：

- paper identity 与选择的器件/子透镜；
- wavelength、NA、focal length、aperture shape 和 size；
- incident side、polarization 和 coordinate convention；
- material families / paper material values；
- period、height、cell geometry 和论文给出的 lateral range；
- source plane 与论文 metric definition。

Adviser只能建议执行预算、求解精度与缺失证据，不能改写这些 paper facts。
solver 重新建立 response；Advice 不得替代 evidence。

## 分段验证顺序

```text
blind brief
  -> advice comparison

paper-locked facts
  -> periodic or grating response
  -> aperture field

same admitted field
  -> reference propagation
  -> FFT/CZT realization
  -> complex-field parity

qualified focal region
  -> paper-aligned metrics
```

因此 sweep 不是四篇论文共同的核心：Johansen 和 Arbabi 需要 width library，
Yang 与 Khorasaninejad 各自只需一个固定 Jones cell。真正共同的验收面是
`field -> focal region -> focus`，且必须先对 complex field 做 parity，再比较
FWHM 或 efficiency。

## 最终建议

四个 case 应命名为用途，而不是把 `inspired` 与 `reproduce` 混在一起：

```text
compact_low_na_propagation
yang_2018_low_na_geometric
arbabi_2020_high_na_propagation
khorasaninejad_2016_high_na_geometric
```

第一项是 MetaCraft standard；后三项是有明确 paper reference 的 reproduction
targets。若未来取得 Johansen 原始 response/layout 数据，再把第一项升级为
`johansen_2024_low_na_propagation`。在此之前，诚实的标准例优于虚假的精确复刻。

> 低 NA 验近似，高 NA 验边界；传播以响应成场，几何以旋转成相。  
> Advice 只作建议，论文事实必须固定；加速只换 realization，结论必须复场对齐。
