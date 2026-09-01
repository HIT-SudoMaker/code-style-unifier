# Flat exit field、vector ASM 与 aplanatic Debye 的一致性边界

**日期：** 2026-08-11
**问题：** 同一个 metalens 出射平面复场进入 vector angular spectrum method
(ASM) 与 Direct/FFT/CZT Debye 后，为何高 NA 复矢量场可相差约 29%；这种差距是否由
NA、padding 或快速算法造成；生产路径能否用 FFT/CZT 取代 direct quadrature。
**范围：** 一手论文、官方数值文档和当前 MetaCraft 源码；本文不修改生产代码。

## 结论先行

1. **FFT 和 CZT 可以取代 direct quadrature 成为 Debye 的生产执行器，但不能取代
   Debye 的物理模型。** 三者计算的是同一个 Richards--Wolf/Debye 算子；Direct
   应保留为小规模资格化 oracle，CZT 适合指定焦区窗口，FFT 适合完整共轭网格。
   Leutenegger 等人的原始论文正是把同一 vectorial Debye integral 改写成 Fourier
   transform，再分别用 FFT 和 CZT 加速，而不是提出两种新的聚焦理论。
   [Leutenegger et al. 2006, EPFL 作者稿](https://infoscience.epfl.ch/record/117519/files/OptExpress-14-23-11277.pdf)

2. **当前约 29% 的 ASM--Debye 复场差异首先是 input contract 混合，不是 Direct
   太慢或 FFT/CZT 不准。** 当前 `_sampled_debye.py` 按平面到焦点的直线几何使用
   `r=f tan(theta)` 取样，却把取样结果送入满足 Abbe sine condition 的 aplanatic
   polarization/apodization/integration measure。后者的 pupil 映射应是
   `r=f sin(theta)`，且由光通量守恒产生 `sqrt(cos(theta))` apodization。把 tangent
   mapping 与 sine-condition 权重拼成一个算子，在高 NA 时不是自洽的 aplanatic
   objective，也不是平面边界场的严格自由空间传播。
   [Richards & Wolf 1959](https://doi.org/10.1098/rspa.1959.0200)；
   [Visser & Wiersma 1994](https://doi.org/10.1364/JOSAA.11.000599)

3. **低 NA 下应该渐近接近，但不是“只要 NA 小就必然一样”。** 当
   `theta -> 0` 时，`sin(theta) ~ tan(theta) ~ theta`、`sqrt(cos(theta)) ~ 1`，纵向
   分量也变小，因此两个合同的差别退化；但 Debye approximation 还要求从焦点看
   aperture 的 Fresnel number 足够大，离散 ASM 还要求 source window、sampling、
   transfer-function bandwidth 和输出窗口足够。固定焦距并缩小 NA 会同时缩小
   aperture，反而可能降低 Fresnel number，不能只做单轴 NA sweep。
   [Wolf & Li 1981](https://doi.org/10.1016/0030-4018(81)90107-3)；
   [Li 2022](https://doi.org/10.1364/JOSAA.477104)

4. **`2x padding` 是合理起点，不是通用充分条件。** Leutenegger 对 Debye FFT 的
   aperture-array convolution 建议至少两倍 zero padding；Matsushima 与 Shimobaba
   则证明离散 ASM 即使连续公式没有传播距离近似，transfer function 的采样仍会
   产生严重误差，需要依传播距离、采样和窗口决定显式带限。两种“padding”解决的
   离散问题不能互相代替。
   [Leutenegger et al. 2006](https://doi.org/10.1364/OE.14.011277)；
   [Matsushima & Shimobaba 2009, 作者机构稿](https://kansai-u.repo.nii.ac.jp/record/11127/files/KU-1100-20091015-50.pdf)

因此，MetaCraft 现在应表达为 **三个执行器、两个物理合同**：

| 执行器 | 物理合同 | 建议职责 |
|---|---|---|
| Vector ASM | sampled plane field 在均匀介质中的 plane-to-plane 传播 | retained/full-wave 出射场的主评价器 |
| FFT Debye | aplanatic pupil/reference sphere 到焦区 | 完整规则焦面/焦区 |
| CZT Debye | 与 FFT 相同的 Richards--Wolf 算子 | 指定 ROI 与采样的默认快速执行器 |

仓库另有 Scalar ASM，但它没有参加这次矢量一致性比较，也不应计作高 NA
vector-field 的替代证据。

## 一、两个物理算子并不以“同一个数组对象”自动同义

### 1. Plane-field vector ASM

对于均匀介质中 `z=0` 平面上的已知切向场，angular spectrum 先取二维 Fourier
spectrum，再令每个传播平面波乘以

```text
exp(i kz z),    kz = sqrt(k^2 - kx^2 - ky^2),
```

并由 `k dot E = 0` 恢复纵向分量。这是 plane boundary value 的传播表示；连续
angular spectrum 可从 Rayleigh--Sommerfeld 表示导出。Matsushima 2009 特别区分
了连续公式的准确性与离散 transfer function 的采样误差。

当前 MetaCraft 的 vector ASM 与此一致：它先对 padded `Ex/Ey` 做 `fft2`，删除
非传播谱，再从 transversality 构造 `Ez` 并乘传播因子。默认 `padding_factor=2`，
但没有实现 Matsushima 型、依距离和窗口计算的 band-limited ASM cutoff：

- [`vector_angular_spectrum.py`](../../src/metacraft/field/vector_angular_spectrum.py)
  中的 `_propagate_tensors` 与 `_complete_spectra`；
- 默认 padding convention 同文件顶部的 `VectorAngularSpectrumConvention`。

### 2. Aplanatic Richards--Wolf/Debye

Richards 与 Wolf 研究的是满足 aplanatic/sine-condition 的成像系统焦区。输入
pupil 不是未经说明的任意平面边界值；它需要一个确定的 pupil-to-reference-sphere
映射、偏振旋转和光通量 apodization。对于轴向入射的 sine-condition 系统，

```text
r_pupil = f sin(theta),
E_reference_sphere propto sqrt(cos(theta)) E_pupil
```

第二式来自入口 pupil annulus 与球面 annulus 的能流守恒。Visser 与 Wiersma 的
原始推导明确给出这两个关系；Leutenegger 随后把 transmitted and apodized field
写成 `kx, ky` 上的 Fourier transform，并指出低 NA 时 `1/cos(theta) ~ 1` 才退化
为 Fraunhofer integral。

FFT/CZT 只改变怎样求这个积分：

```text
same aplanatic pupil
    -> same polarization/apodization/Jacobian
    -> Direct quadrature | FFT | CZT
    -> same focal field, up to discretization error
```

当前 retained-response 测试中，CZT--Direct 的 aligned complex error 为 `0.116%`，
FFT--Direct 为 `0.243%`，已经证明三条数值路径在同一 Debye contract 内收敛；它们
无法通过“换掉 Direct”消除 ASM--Debye 的跨合同差异。

## 二、已撤回 `SampledAplanaticPupil` 的关键混合

已删除的 `_sampled_debye.py` 曾做两件事：

```text
x_plane = f sx / sz = f tan(theta) cos(phi)
y_plane = f sy / sz = f tan(theta) sin(phi)

phase_advance = exp[i k f (1/sz - 1)]
```

第一组关系是从平面点到焦点的直线相交几何，适合表达 flat phase plate 的 ray
location；第二项会抵消理想 hyperbolic converging phase。随后
[`fast_debye.py`](../../src/metacraft/field/fast_debye.py) 又执行 aplanatic
polarization transport，并在均匀 `sx,sy` 网格上使用净 `1/sqrt(sz)` quadrature
weight。后者等价于 sine-condition 的 `sqrt(cos(theta))` apodization 与变量变换
Jacobian 的组合。

这形成了一个 hybrid：

```text
flat metasurface geometry:       r = f tan(theta)
aplanatic objective energy map:  r = f sin(theta), sqrt(cos(theta))
```

两者在一阶小角度相同，在高角度迅速分离。令 `NA=sin(theta_max)`（空气）：

| NA | `cos(theta_max)` | `tan/sin = 1/cos` | `sqrt(cos)` |
|---:|---:|---:|---:|
| 0.10 | 0.995 | 1.005 | 0.997 |
| 0.20 | 0.980 | 1.021 | 0.990 |
| 0.32 | 0.947 | 1.056 | 0.973 |
| 0.50 | 0.866 | 1.155 | 0.931 |
| 0.89 | 0.456 | 2.193 | 0.675 |

对 Arbabi `NA=0.89, f=25 um`，同一个边缘方向在 tangent map 中位于约
`48.8 um`，而 sine-condition pupil 中位于 `22.25 um`。这不是一个 padding 能修复
的小坐标误差，而是两种光学系统对“哪个 pupil 点生成哪个 ray”的不同定义。

偏振差异也会被放大。Richards--Wolf 的 aplanatic transport 把径向横场旋转到 ray
transverse plane；ASM 则从整个 plane field 的 Fourier spectrum 逐频率施加
transversality。二者若起点不是同一个 angular spectrum，所得 `Ez/Ex` 能量比例
没有理由一致。当前 200 nm 诊断正表现为：分别允许每个分量独立对齐时 `Ex` 误差
约 `4.27%`、`Ez` 约 `1.04%`，但一个全局复数 scale 下合并误差仍为 `17.7%`，因为
`||Ez||/||Ex||` 是 ASM `0.436`、Debye `0.243`。这是相对分量权重不同，不是单纯
global phase。

## 三、NA、采样、padding 各自解释什么

### 1. NA 是混合合同误差的放大器，但不是唯一资格轴

在保持物理 aperture contract 和充分 Fresnel number 时，低 NA 展开给出：

```text
tan(theta) / sin(theta) = 1 + theta^2/2 + O(theta^4)
sqrt(cos(theta))        = 1 - theta^2/4 + O(theta^4)
Ez / Ex                 = O(theta)
```

所以 cross-model intensity 应随 NA 降低而靠近。当前宽 zero window 的本地探针与
此一致：`NA=0.10` 的 normalized-intensity error 为 `0.051%`，`NA=0.20` 为
`0.056%`。这说明“低 NA 应相近”的直觉是对的，也反证 29% 不是 FFT/CZT 自身
不稳定。

但低 NA 本身不充分。若 flat aperture 半径 `a=f tan(theta_max)`，从焦点看的
Fresnel number 量级为

```text
N_F = a^2 / (lambda f) = f tan^2(theta_max) / lambda.
```

固定 `f` 降 NA 会降低 `N_F`；Wolf--Li 的 Debye 适用条件要求该量远大于 1。因此
正式 convergence matrix 必须同时记录 `NA` 与 `N_F`，不能把所有差异都回归到
NA。

### 2. `2x padding` 不能替代 finite-window convergence

当前同一个低-NA probe 在 source 周围留足 zero window 时误差约 `0.05%`，但把
window 收紧后，即使仍使用 `2x padding`，强度误差也可升到约 `25%`。原因是：

- zero padding 抑制 FFT 的周期卷绕，并加密离散频率采样；
- 它不恢复已经被 source window 截掉的场；
- 它不自动满足 ASM transfer function 随 `z`, `dx`, window size 变化的采样条件；
- 它也不改变 tangent/sine mapping、apodization 或 polarization contract。

Leutenegger 对 **Debye FFT aperture array** 给出的至少两倍 padding 是正确而有用的
实现规则；不能把它外推成所有 **plane-to-plane ASM** 在任意距离上的充分条件。
Matsushima 的 band-limited ASM 工作恰好表明了这种外推不成立。

### 3. 400 nm 到 200 nm 的下降说明存在数值项，但没有消除模型项

Arbabi field 从 `400 nm` 加密到 `200 nm` 后，aligned complex error 从 `29.1%`
降至 `17.7%`；这证明 piecewise-cell resampling、pupil interpolation、ASM spectrum
sampling 和输出抽样贡献显著。可是：

- 换成连续 hyperbolic phase 后仍约 `18.8%`，排除了 12-level phase quantization
  是主因；
- 分量比仍不同，说明 refinement 后剩余误差不只是 bilinear interpolation；
- PyTorch 官方文档说明 `grid_sample(..., align_corners=True)` 的归一化坐标依赖输入
  resolution，因此必须单独做 interpolation refinement，不能把一次 resampling
  当成连续极限。
  [PyTorch `grid_sample`](https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.grid_sample.html)

先前 retained-response 数值只用于定位混合合同，不能成为验收基线；对应的
same-field artifact 已随错误桥接一并删除。本文保留其数值作为诊断历史，而不把它
解释为两个物理方法的精度比较。

## 四、生产选择与验证道路

### 1. 执行器选择

- **CZT Debye：** 默认焦区 ROI 执行器。它允许输出窗口和采样与 pupil grid 解耦，
  避免为了很小的焦区生成巨大完整 FFT plane。
- **FFT Debye：** 需要完整规则共轭网格、批量横截面或 FFT grid 本身正好满足输出
  时采用。
- **资格化：** 不保留 Direct 生产或测试执行器。FFT 与 CZT 分别回答解析轴上解、
  反射对称性、纵向反对称性、圆偏振手性和设备一致性；两者再在 FFT 共轭网格上
  做复场一致性回归。
- **Vector ASM：** retained solver exit-plane field 的正式传播器。不要为了速度或
  “高 NA”把一个 plane `Field` 自动重命名成 aplanatic pupil。

这是一条 Sonnet 式的职责线：**解析事实定真，FFT 铺面，CZT 取窗；ASM 传平面，
Richards--Wolf 聚球面。**

### 2. 必须执行的归因矩阵

下一轮不应再只给一个总误差，而应按以下顺序关闭原因：

1. **Richards--Wolf 内部资格化：** FFT 与 CZT 在相同 pupil、坐标、dtype 下回答
   解析事实并做 pupil-samples refinement；共同网格上的复场差异单独记录。
2. **ASM 内部资格化：** 对同一 plane field 以 direct plane-wave sum 或 direct
   vector Rayleigh--Sommerfeld/dyadic surface integral 作小规模 oracle；分别扫
   `dx`、source zero margin、padding `1/2/4` 和 bandlimit。只改变 padding 而不改变
   physical window 的试验不得宣称收敛。
3. **低-NA 渐近试验：** 扫 NA 时保持 `N_F` 至少在同一数量级且足够大；分别报告
   `Ex/Ey/Ez`、总强度、FWHM、focus shift 和 power。目标是证明误差随角度项缩小，
   而不是拟合一个任意阈值。
4. **合同消融：** 在 research-only fixture 中依次切换 tangent/sine coordinate map、
   apodization 和 polarization transport。若 tangent-to-sine 切换主导 29% 变化，
   即确认 mapping；若 padding refinement 仍持续下降，则先关闭离散误差。
5. **高-NA 分轨：** flat metasurface retained field 只要求 ASM 对其 plane-surface
   oracle 收敛；aplanatic Debye 只要求三执行器互相收敛。除非先定义一个有一手
   方程支持的 `PlaneField -> ReferenceSphereField` 光学变换，否则不设 ASM--Debye
   强制 complex-parity gate。

### 3. 建议停止条件

- Direct--FFT/CZT aligned complex error 随 pupil refinement 收敛且低于既定门限；
- ASM 对 plane-field oracle 随 `dx/window/padding/bandlimit` refinement 收敛；
- 低 NA、固定大 `N_F` 的 cross-model normalized intensity error 进入亚百分比并呈
  稳定下降；
- 高 NA tangent/sine/apodization 消融能解释剩余误差，且结果不再随数值 refinement
  大幅漂移。

满足这些条件后，才能把剩余 ASM--Debye 差异称为“模型差异”；在此之前，它应被
记录为 **mixed physical and numerical discrepancy**，既不能用 `2x padding` 宣告
正确，也不能靠把 Direct 换成 CZT/FFT 隐去。

## 一手来源

1. E. Wolf, “Electromagnetic diffraction in optical systems. I. An integral
   representation of the image field,” *Proceedings of the Royal Society A*
   253, 349--357 (1959). [DOI](https://doi.org/10.1098/rspa.1959.0199)
2. B. Richards and E. Wolf, “Electromagnetic diffraction in optical systems.
   II. Structure of the image field in an aplanatic system,” *Proceedings of
   the Royal Society A* 253, 358--379 (1959).
   [DOI](https://doi.org/10.1098/rspa.1959.0200)
3. E. Wolf and Y. Li, “Conditions for the validity of the Debye integral
   representation of focused fields,” *Optics Communications* 39, 205--210
   (1981). [DOI](https://doi.org/10.1016/0030-4018(81)90107-3)
4. T. D. Visser and S. H. Wiersma, “Electromagnetic description of image
   formation in confocal fluorescence microscopy,” *JOSA A* 11, 599--608
   (1994). [Publisher](https://opg.optica.org/josaa/abstract.cfm?uri=josaa-11-2-599)
5. M. Leutenegger, R. Rao, R. A. Leitgeb, and T. Lasser, “Fast focus field
   calculations,” *Optics Express* 14, 11277--11291 (2006).
   [EPFL author manuscript](https://infoscience.epfl.ch/record/117519/files/OptExpress-14-23-11277.pdf)
6. K. Matsushima and T. Shimobaba, “Band-limited angular spectrum method for
   numerical simulation of free-space propagation in far and near fields,”
   *Optics Express* 17, 19662--19673 (2009).
   [Author-institution manuscript](https://kansai-u.repo.nii.ac.jp/record/11127/files/KU-1100-20091015-50.pdf)
7. Y. Li, “Disguised assumptions and the conditions for validity of Debye
   integral representation of focused fields,” *JOSA A* 39, C156--C160
   (2022). [Publisher](https://opg.optica.org/josaa/abstract.cfm?uri=josaa-39-12-C156)
8. PyTorch, [`torch.nn.functional.grid_sample`](https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.grid_sample.html)
   and [`torch.fft.fft2`](https://docs.pytorch.org/docs/stable/generated/torch.fft.fft2.html),
   official API documentation.
