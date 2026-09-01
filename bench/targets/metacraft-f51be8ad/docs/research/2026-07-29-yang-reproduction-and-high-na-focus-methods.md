---
record_type: research_record
date: 2026-07-29
status: research_finding
authority_level: none
current_capability: false
---

# Yang 2018 复刻与大 NA 焦场方法裁决

## 研究问题

本记录只回答四个问题：

1. Yang 2018 的 PB metalens 究竟如何计算，哪些参数必须原样保留；
2. 大 NA dielectric metalens 是否应只保留 geometric phase；
3. vector angular spectrum 与 Richards--Wolf/Debye 各自计算什么；
4. FFT、CZT 与 radial Hankel/Bessel 在架构中是方法还是加速实现。

它补充以下既有记录，不替代其完整论证：

- [经典 PB metalens 候选与复刻边界](2026-07-27-classic-pb-metalens-candidates.md)；
- [大 NA 传播相位超透镜：预判、响应证据与焦场计算](2026-07-27-large-na-propagation-metalens-method-boundaries.md)；
- [Debye--Wolf 数值遗产恢复记录](2026-07-15-debye-wolf-numerical-heritage-recovery.md)。

## 结论先行

1. **Yang 2018 不是大 NA 论文。**其单个 metalens 子单元工作在
   `1550 nm`、焦距 `30 um`、方形 footprint `22.5 um x 22.5 um`，
   名义 NA 为 `0.32`。它适合作为 low-na geometric-phase 的忠实复刻，
   不能承担 large-na 方法验证。
2. **当前 Yang brief 仍是 adapted reproduction。**它没有固定论文的
   `1500 nm` 周期、`340 nm` 高度、`1350 nm x 480 nm` 椭圆柱和方形
   footprint，并声明了论文没有给出的 `100 nm` 加工步进。
3. **不能在科学模型中废除 large-na propagation phase。**大 NA 的
   geometric phase、尺寸编码 transmission phase 以及混合 phase 都有
   一手实例。可以把 large-na propagation-phase 的实现移出近期范围，
   但不能把它写成不存在或物理上不成立。
4. **建议分成两个复刻目标。**
   - Yang 2018：忠实复刻一个 NA `0.32` 的圆偏振 PB 子透镜；
   - Khorasaninejad 2016：未来 large-na geometric-phase 标杆，
     `NA = 0.8`。
5. **实际场与理想场应各归其算子。**
   - 已知 metalens 出射平面的复矢量 `field`：vector angular spectrum；
   - 已知 aplanatic pupil/reference sphere：Richards--Wolf/Debye。
6. **FFT、CZT、GPU、Hankel/Bessel 不是新的物理方法。**它们是同一
   科学 method 的不同 realization，必须与 direct reference 做复场 parity。

## 一、Yang 2018 的论文计算

论文为 Zhenyu Yang 等人的
“Generalized Hartmann-Shack array of dielectric metalens sub-arrays for
polarimetric beam profiling”，*Nature Communications* 9, 4607 (2018),
DOI `10.1038/s41467-018-07056-6`。
[期刊全文](https://www.nature.com/articles/s41467-018-07056-6)

### 1.1 论文固定的器件事实

| 事实 | 论文值 |
| --- | ---: |
| free-space wavelength | 1550 nm |
| focal length | 30 um |
| footprint | 22.5 um x 22.5 um |
| nominal NA | 0.32 |
| lattice | square |
| period | 1500 nm |
| atom material | silicon |
| underlayer | silicon dioxide |
| atom shape | elliptical pillar |
| height | 340 nm |
| major axis | 1350 nm |
| minor axis | 480 nm |
| circular-polarization focusing efficiency | 60% theoretical, 26% measured |

论文的一个 pixel 含六个 polarization-selective metalenses，分别对应
`x/y/a/b/l/r`。忠实复刻一个 PB metalens 时，应明确选择其中一个 `l`
或 `r` 子透镜；只复刻一个子透镜不能声称重建了完整的 Hartmann--Shack
array 或 Stokes measurement。

### 1.2 单元响应

作者使用 Lumerical FDTD：

- wavelength 为 `1550 nm`；
- 正入射；
- 输入线偏振沿 `x`；
- `x/y` 使用 periodic boundary；
- `z` 使用 PML；
- 扫描椭圆柱的 `major/minor axis`，得到 intensity transmittance 与
  complex phase。

圆偏振器件不从尺寸库逐点匹配 phase。作者固定
`major = 1350 nm`、`minor = 480 nm`，令两个椭圆本征轴的 complex
transmission 近似满足半波片关系，使同手性项消失、交叉手性项最大。

在论文约定下，right-handed incidence 的交叉手性项携带
`exp(-i 2 theta)`，left-handed incidence 的交叉手性项携带
`exp(+i 2 theta)`。因此 orientation 在 `[0, pi)` 内即可覆盖完整
`[0, 2pi)` geometric phase。符号不能脱离 propagation direction、
viewing direction、circular basis 与 rotation sign 单独复制。

### 1.3 目标相位与排布

论文采用 hyperbolic target phase：

```text
phase(x, y)
  = -2 pi / wavelength
    * (sqrt(x^2 + y^2 + focal_length^2) - focal_length)
    + constant
```

随后根据选定 incident handedness，将每个 lattice site 的 target phase
转换为 orientation。科学链应是：

```text
fixed Jones cell
  -> handedness conversion
  -> analytic orientation
  -> square aperture field
  -> focus
```

它不是：

```text
orientation sweep
  -> 8/12/16 phase levels
  -> per-site solver calls
```

## 二、当前 MetaCraft 与忠实复刻之间的差距

现有 `yang_ellipse_brief` 已保留 wavelength、NA、focal length、
materials、shape 与 right-circular incidence，但仍有四个决定性差距。

### 2.1 论文 cell 没有被 brief 原样固定

当前 brief 没有结构化固定：

- period `1500 nm`；
- height `340 nm`；
- ellipse `1350 nm x 480 nm`。

若这些值仍由 period advice、height advice 或通用 geometry sweep
重新选择，结果只能叫 adapted reproduction。

### 2.2 `100 nm` dimension step 与论文尺寸不相容

两个 lateral axes `1350 nm` 与 `480 nm` 都不在 `100 nm` 生成网格上；
`340 nm` height 也必须另作 exact constraint。忠实复刻不应把论文 cell
投影到通用加工网格；应把论文 geometry 作为 explicit constraint，并只
验证其合法性。

### 2.3 论文 aperture 是方形，当前 aperture 是圆形

论文给出 `22.5 um x 22.5 um` footprint；当前 metalens aperture
实现从 `NA` 与 focal length 派生 circular mask。把方形 footprint
改成圆形会改变 site count、edge phase 与 focusing power，因此仍是
adapted reproduction。

### 2.4 论文 period 超出当前 G0-only method 的适用域

论文 period 为 `1500 nm`。在 `1550 nm`、silica substrate、NA `0.32`
下，它超过当前 conservative order ceiling；精确 ceiling 仍应由 admitted
substrate material sample 计算。

[ADR 0009](../adr/0009-keep-g0-only-metalens-proofs-in-the-zeroth-order-domain.md)
明确规定：当前 aperture field 只由 G0 complex response 构成，因此不能
在 multi-order domain 内声称 complete field。忠实复刻不能静默缩小
论文 period，也不能绕过该 gate。它需要一个经过 qualification 的
order-resolved 或 near-field response method。

## 三、大 NA 不属于某一种 phase

### 3.1 geometric phase 的大 NA 实例

Khorasaninejad 等人在 `405/532/660 nm` 使用 TiO2 rectangular nanofins，
通过旋转半波片单元赋予 PB phase；三个器件均为直径 `240 um`、焦距
`90 um`、NA `0.8`。
[Science 作者公开稿](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf)

这是一条清晰的 future large-na geometric-phase reproduction target。

### 3.2 非 geometric phase 的大 NA 实例

大 NA 尺寸编码器件同样存在：

- Arbabi 等人在 2015 年使用 glass 上的 circular silicon nano-posts，
  以 post diameter 覆盖 `0..2pi` transmission phase，制造高 NA
  high-contrast transmitarray microlenses。相位来自尺寸相关的 local
  transmission response，不来自 atom rotation。
  [Nature Communications](https://www.nature.com/articles/ncomms8069)；
  [作者预印本](https://arxiv.org/abs/1410.8261)
- Arbabi 等人在 2020 年以 square amorphous-silicon nano-post widths
  和 grating averaging 设计 `NA = 0.78` metalens，实测 focusing
  efficiency `77%`。
  [Scientific Reports](https://www.nature.com/articles/s41598-020-64198-8)
- Khalilian 等人在 2025 年同一研究中直接比较 geometric-phase 与
  propagation-phase metalenses；其 propagation-phase designs 达到
  `NA = 0.95/0.97`。
  [Optics Letters](https://doi.org/10.1364/OL.545309)

因此不能写“没有纯 propagation-phase large-na metalens”。更准确的
措辞是：

> Large NA 会放大 sampling、nonlocal coupling、angle response 与
> polarization fidelity 的压力；选择 geometric、size-encoded
> transmission phase 或 hybrid phase，取决于目标、材料、偏振与可取得
> 的 response evidence。

“纯 propagation phase”本身也容易过度简化。尺寸编码 nanopost 的
transmission phase 可能同时包含 guided propagation 与 resonant
scattering；MetaCraft 应按可观察的 control strategy 分类，不替论文
虚构单一微观成因。

### 3.3 可以收窄 roadmap，不能改写物理事实

近期范围可以只实现：

```text
low-na propagation phase
low-na geometric phase
large-na geometric phase
```

并把 `large-na propagation phase` 明确延后。但 domain language、
Research Record 与未来 method seam 应保留；不应增加“large NA 必须
geometric phase”的 compiler rule。

## 四、vector angular spectrum 与 Richards--Wolf/Debye

### 4.1 vector angular spectrum：传播真实 plane field

Vector angular spectrum 将已知 plane field 分解为 plane waves，在
homogeneous medium 中施加传播因子，再重建目标平面；vectorial
angular-spectrum representation 与 vector Rayleigh--Sommerfeld
公式具有严格联系。
[Liu & Lü 2007](https://doi.org/10.1016/j.optlastec.2006.03.006)

它适合消费：

- solver 或 aperture construction 给出的 exact complex components；
- 明确的 plane、coordinate frame、medium 与 component basis；
- 已声明的 propagating/evanescent policy。

对真实 PB candidate，尤其是离散 lattice、方形 aperture、conversion
loss 与 retained leakage 均需保留时，vector angular spectrum 是首选
actual-field evaluator。

离散 ASM 并非自动正确。Transfer-function sampling 可能产生严重误差；
band-limited ASM 通过显式带限扩大可信传播域。
[Matsushima & Shimobaba 2009](https://doi.org/10.1364/OE.17.019662)

### 4.2 Richards--Wolf/Debye：形成理想 aplanatic focus

Richards 与 Wolf 的经典积分从满足 sine condition 的 pupil/reference
sphere vector field 建立 high-NA focal field；它必须明确：

- `NA = image_medium_index * sin(maximum_angle)`；
- pupil-to-reference-sphere mapping；
- apodization；
- polarization transport；
- interface transmission；
- time/phase convention。

[Richards & Wolf 1959](https://doi.org/10.1098/rspa.1959.0200)

它适合作为 ideal aplanatic reference，或消费一个确实具有 reference
sphere semantics 的输入。它不能直接替代从真实 metasurface exit plane
到焦区的传播，也不能把“scalar ASM 后补一个 longitudinal component”
命名为 Debye--Wolf。

### 4.3 两者的 Sonnet 分工

```text
actual aperture field
  -> plane-field propagation
  -> realized focal region

ideal pupil/reference sphere
  -> aplanatic focusing
  -> reference focal region

realized focal region + reference focal region
  -> comparison
```

边界清晰，依赖单向；输入不同，结论呼应。

## 五、FFT、CZT 与 radial Hankel/Bessel

Leutenegger 等人把 vector Debye integral 写成二维 Fourier transform，
用 FFT 计算完整 focal region，并用 chirp-z transform 获得更灵活的
output sampling 与额外速度收益。
[Leutenegger et al. 2006](https://doi.org/10.1364/OE.14.011277)

因此应区分：

| 层次 | 内容 |
| --- | --- |
| physical method | plane-field propagation；aplanatic focusing |
| reference realization | direct vector angular integration |
| fast realization | FFT；CZT；GPU |
| symmetry realization | finite angular harmonics + Hankel/Bessel transforms |

- **FFT**：适合规则完整 output grid；
- **CZT**：适合只在焦区 zoom、输出 sampling 与输入 FFT grid 不同的情况；
- **Hankel/Bessel**：只在 pupil symmetry 或经过证明的有限 angular-mode
  contract 下使用。

Yang 的真实器件是 square lattice 上的 square footprint，不能为了获得
radial speedup 把它改成轴对称器件。即使理想 phase 是 radial，线偏振或
圆偏振的 high-NA vector focus 仍需要相应 angular harmonics；不能只保留
一个 `J0` transform。Radial realization 应在 direct vector reference
之后实现，并比较 complex components，而不是只比较 FWHM。

## 六、推荐的规划顺序

### A. 先做 Yang 2018 low-na 忠实复刻

1. 固定论文 period、height、ellipse geometry、square footprint、
   wavelength、focal length、NA 与 handedness；
2. 只复刻一个 `l` 或 `r` PB sublens；
3. 以论文的两本征轴 Jones response 资格化 fixed cell；
4. 用 analytic orientation 形成 aperture，不做 orientation sweep；
5. 为 `1500 nm` period 建立 order-resolved 或 near-field response method，
   不绕过 G0-only gate；
6. 首先复现 theoretical conversion/focusing trend，再把论文 `26%`
   measured efficiency 作为实验 comparison，不把制造损耗硬编码为
   simulation threshold。

### B. 再做 Khorasaninejad 2016 large-na geometric phase

1. 保留 `NA = 0.8`，不降成 low-na adapted brief；
2. 先复刻 `532 nm` fixed nanofin Jones response；
3. 形成 circular aperture 的 converted/retained vector field；
4. 用 vector angular spectrum 评估 realized field；
5. 用 Richards--Wolf 形成 ideal aplanatic reference；
6. 只有 response/coupling evidence 不足时，才增加 gradient-resolved、
   supercell 或 full-aperture evidence。

### C. 实现顺序：reference 在前，accelerator 在后

```text
direct reference
  -> qualified vector method
  -> FFT/CZT realization
  -> GPU binding
  -> optional angular-harmonic/Hankel realization
```

每一个 fast realization 都必须对同一 input contract 做 complex-field
parity。Torch/CUDA 决定 execution device，不决定物理 method。

## 最终建议

最小而完整的路线不是“删掉 propagation phase，再增加一个 high-na
solver”，而是：

> **Yang 忠实而低 NA，Khorasaninejad 忠实而大 NA；实际场走 vector
> angular spectrum，理想场走 Richards--Wolf；FFT/CZT 负责提速，不负责
> 改写物理。**

这保留了现有 `brief -> study -> result` lifecycle 与 Rust authority，
只在 Python science 中增加由真实 input semantics 支撑的 method 和
realization。控制策略各守其位，焦场算子各尽其责。
