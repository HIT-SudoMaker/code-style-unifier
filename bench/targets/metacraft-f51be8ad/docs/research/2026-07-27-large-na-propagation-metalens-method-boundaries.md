---
record_type: research_record
date: 2026-07-27
status: research_finding
authority_level: none
current_capability: false
---

# 大 NA 传播相位超透镜：预判、响应证据与焦场计算

日期：2026-07-27  
文档性质：Research Record；只保存一手文献事实、可复核推导与待裁决的方法选择，不修改现有 capability，不授权任何 high-na claim。

## 结论摘要

1. **大 NA 不是第二种相位机制。**目标仍是 `metalens + propagation phase`；大 NA 改变的是口径所需横向动量、单元证据的适用域、焦场模型与恢复方法，而不是把 brief 改编成另一条器件路线。
2. **不存在一个由文献支持的全局 NA 阈值，可以在阈值上方自动拒绝 brief、自动判定局部周期近似失效，或自动要求 optimizer。**大 NA 使边缘相位梯度增大、相邻单元变化加快，并暴露邻近耦合与方向图误差；失效位置仍取决于晶格、周期、材料、几何、偏振和局部偏转角。[Arbabi et al. 2020](https://doi.org/10.1038/s41598-020-64198-8)；[Egede Johansen et al. 2024](https://doi.org/10.1038/s42005-024-01598-6)
3. **solver-free 预判只能硬拒“已严格定义的方法域”，不能把粗略模型的失败冒充器件不可能。**几何自洽性、非空加工域、采样/倒格矢条件可以在调用求解器前裁决；相位包络、透射效率、局部周期精度和邻近耦合通常只能形成 forecast 或提出 evidence request。
4. **“相位不足 `2π`”不能作为大 NA 传播相位 brief 的一般硬拒。**Arbabi 等人的高角度优选平台只覆盖 `1.63π`，低 NA 指标较差，却在大偏转角优于完整 `2π` 平台，并实现 NA `0.78`、实测聚焦效率 `77%` 的 metalens。[Arbabi et al. 2020](https://doi.org/10.1038/s41598-020-64198-8)
5. **确定性设计与全局优化之间存在真实的中间层。**除了逐点周期单元查表，还可以使用按局部相位梯度/偏转角建立的 blazed-grating 或 extended-cell 证据；grating averaging 已证明这种方法无需整片 optimizer 也能设计高 NA 器件。optimizer 应由性能缺口、多目标约束或耦合证据触发，不能由 `NA > 某数` 触发。
6. **vector angular spectrum 与 Richards–Wolf/Debye 不是互斥的“高 NA solver”。**前者适合把求解器给出的真实复矢量出射平面传播到焦区；后者描述满足 aplanatic/sine-condition 的参考球或 pupil 如何形成理想高 NA 焦场。实际候选与理想基准应分别使用与输入证据相符的算子。
7. **数值提速的关键不是把 Python 循环换成另一种循环，而是避免计算不需要的三维体。**出射场 FFT、波矢网格与传播 mask 只建立一次；先批量计算轴向 scout，再只在候选焦点附近重建少量全平面。若确实要求 `N_z` 个完整平面，数学上仍需要 `N_z` 组逆变换，只能批处理与分块，不能声称“向量化后工作量消失”。

## 证据口径

下文严格区分三类内容：

- **已发表事实**：原始论文或官方求解器文档直接报告的公式、方法、仿真或实验；
- **可复核推导**：从目标相位、采样和加工不等式直接推出，公式逐步给出；
- **方法建议**：为 MetaCraft 候选架构提供的选择，不构成 ADR 或当前 capability。

与本记录互补的现有记录：

- [零级衍射周期规则](2026-07-26-zeroth-order-period-rule.md)；
- [传播相位包络的认证边界](2026-07-26-phase-envelope-certified-roots.md)；
- [Debye–Wolf 数值遗产恢复记录](2026-07-15-debye-wolf-numerical-heritage-recovery.md)。

## 一、求解器之前，什么可以诚实地拦截

### 1.1 目标几何的硬矛盾

单波长、均匀像方介质中，轴上 metalens 的 hyperbolic target phase 为

```text
phase(r) = -k0 [sqrt(r² + f²) - f]
```

空气像方时，

```text
NA = R / sqrt(R² + f²)
```

其中 `R` 为口径半径。该相位与几何定义被高 NA metalens 原始工作直接采用。[Arbabi et al. 2020](https://doi.org/10.1038/s41598-020-64198-8)

因此以下情况无需任何电磁求解即可硬拒或要求 brief 修正：

- `f <= 0`、`R <= 0`、`NA <= 0`；
- 均匀像方介质内 `NA > n_image`；
- brief 同时给出 `f`、`R`、`NA`，三者却不满足同一几何关系；
- 口径单元数、周期和物理口径互相矛盾。

这类裁决否定的是 brief 自身，而不是某个数值方法。

### 1.2 相位梯度、采样与每周相位的单元数

由上式直接求导：

```text
|d phase / dr|
  = k0 r / sqrt(r² + f²)

edge gradient
  = k0 NA
```

若晶格步长为 `p`，边缘相邻格点的一阶相位步长约为

```text
edge phase step = 2π p NA / lambda0

cells per phase turn = lambda0 / (p NA)
```

所以 `p = lambda0 / (2 NA)` 时，口径边缘每个 `2π` 只剩约两个采样点。这解释了大 NA 为什么同时压缩物理周期和局部变化尺度；它不是一个额外 workflow。

对“把连续相位逐点采到固定晶格”的方法，Nyquist 必要条件是

```text
p <= lambda0 / (2 NA)
```

但二维 metalens 不能只看一维标量上限。离散晶格把目标谱复制到各倒格矢处；alias-free 条件应直接检查：

```text
for every nonzero reciprocal vector G
for every target transverse momentum kt
for every radiating surrounding medium j:

    |kt + G| > n_j k0
```

Kim 等人的二维实验表明，square 与 hexagonal 晶格即便具有相同 sampling level，也会出现不同的 aliasing 区域；高 NA metalens 的目标谱近似覆盖整个 light cone，边缘尤其容易耦合到 aliasing order。[Kim et al. 2025](https://doi.org/10.1038/s41467-024-55095-z)

这里必须保留一个边界：

> 倒格矢检查失败，可以硬拒“alias-free pointwise lattice method”；它不能证明 Maxwell 方程下不存在 grating-aware、integrated-lattice 或 inverse-designed 解。

同一篇工作使用晶格选择和耦合 meta-dimer 抑制了传统采样法的 aliasing，正好证明“方法不可用”不等于“brief 不可行”。

### 1.3 加工域是否为空

设：

```text
minimum_feature = fabrication 给出的最小特征
minimum_gap     = fabrication 给出的最小间隙
aspect_limit    = height / lateral_feature 的最大值
height          = 已选柱高
```

则最小允许横向尺寸至少为

```text
smallest_atom = max(
  minimum_feature,
  height / aspect_limit
)
```

单柱单元的必要非空条件为

```text
smallest_atom + minimum_gap <= period
```

再把 `period` 的采样、衍射与晶格上限合并；若所有允许 period 与所有允许 height 都使该不等式失败，当前传播相位单柱方法可以在求解器前硬拒。这是纯算术与加工几何，不依赖有效折射率猜测。

高 NA 的“设计空间变窄”应精确表述为：

```text
available lateral interval
  = [smallest_atom, period - minimum_gap]
```

NA 增大使 period ceiling 下移；柱高和宽高比又抬高 `smallest_atom`。两端相遇时域为空；没有相遇时，仍不能仅凭“区间较窄”推断相位覆盖或效率失败。

### 1.4 相位包络只能在声明的模型内裁决

传播图景常写作

```text
phase delay ≈ k0 * height * effective-index contrast
```

但有限高度 pillar-on-substrate 的真实透射相位还受端面、Fabry–Pérot、局域共振和邻近耦合影响。现有 Research Record 已说明：即使 HE11 与 Rytov 模型可求根，尚无一手证明把它们无条件升级为真实二维柱阵列的认证夹界。

更重要的是，高 NA 最优平台不一定追求完整的局部 `2π` 查表。Arbabi 等人的两个平台中，第二个平台删去大截面柱，只覆盖 `1.63π`，按低 NA 单元表看更差，却在偏转角大于约 `15°` 后更高效；作者把收益归因于更小周期以及排除具有不利离轴方向图的高阶共振柱。[Arbabi et al. 2020](https://doi.org/10.1038/s41598-020-64198-8)

因此 solver-free 相位预报可以：

- 报告几何域、材料条件和乐观/保守的 phase-turn estimate；
- 在一个明确限定为“非共振逐点 waveguide lookup”的模型内拒绝该模型；
- 请求真实 complex response evidence。

它不能：

- 因估计跨度小于 `2π` 就拒绝整个 propagation-phase brief；
- 因 NA 大于经验阈值就宣告物理不可行；
- 用预测透射率替代求解器的复透射系数。

### 1.5 预判结果的诚实分类

| 结果 | 例子 | 应否启动求解器 |
| --- | --- | --- |
| brief contradiction | `f/R/NA` 不自洽，或 `NA > n_image` | 否；要求修正 brief |
| method inadmissible | alias-free pointwise method 无可行 period；加工域为空 | 否；换方法或返回理由 |
| evidence missing | 材料样本、angle-resolved response、method qualification 缺失 | 否；先编译 evidence task |
| forecast weak | 相位包络看似不足、效率可能偏低 | 不据此裁决；是否求解由预算与方法选择决定 |
| candidate admissible | 算术域非空且所选 method 已有适用证据 | 是；获取响应或验证证据 |

license、软件路径和 workstation capacity 只决定“现在能否执行”，不决定科学 brief 是否可行。

## 二、大 NA 如何改变单元响应

### 2.1 pointwise library 的两个近似

传统传播相位设计把每个 meta-atom 的局部复透射系数近似为“相同 meta-atom 无限周期排列”时的透射系数，然后逐格选择最接近期望相位的几何。Arbabi 等人把其两项近似写得很清楚：

1. 局部周期近似忽略非周期排列引起的邻近耦合变化；
2. 局部系数近似忽略 meta-atom radiation pattern 对入射与出射方向的依赖。

低 NA 时几何缓慢变化且偏转角小，这两项可能足够好；NA 增大后，两项误差同时上升。[Arbabi et al. 2020](https://doi.org/10.1038/s41598-020-64198-8)

实验与高保真计算也给出同一方向：

- Egede Johansen 等人从 NA `0.08` 扫到 `0.93`；低 NA 可由 constant-phase/local-periodic 模型描述，高 NA 需要保留单元内 resolved field 才能提高聚焦效率预测精度。[Egede Johansen et al. 2024](https://doi.org/10.1038/s42005-024-01598-6)
- Lin、Wang 与 Hsu 对毫米宽、NA `0.86`/`0.71` 的二维 metalens 做全波 transmission-matrix 计算；两种 LPA 在不同入射角下的焦平面强度误差可达 `366%`，而压缩后的全波方法平均误差低于 `0.01%`。[Lin et al. 2022](https://doi.org/10.1038/s43588-022-00370-6)

这些结果证明高 NA 是压力源，但没有给出跨平台通用的失效阈值。

### 2.2 三层响应方法，而不是二选一

| 方法 | 最小证据 | 能看见什么 | 看不见什么 |
| --- | --- | --- | --- |
| pointwise periodic lookup | `complex transmission(atom, wavelength, polarization)` | 单元自身的周期响应；极快的逐点形成 | 不同邻居、局部梯度、离轴方向图 |
| gradient-aware deterministic lookup | `diffraction response(supercell, gradient vector, phase origin, polarization)` | 大偏转角、相邻状态组合、目标 diffraction order | 远距离非局部耦合、patch stitching 与整片误差 |
| coupled aperture design | overlapping-domain、distributed full-wave 或整片求解及其梯度 | 显式邻近/跨域耦合和全局 objective | 受计算规模、近似域和 optimizer 收敛限制 |

中间层有直接实验依据。Grating averaging 把高 NA surface 看成局部缓变的 periodic blazed gratings，用多个 phase origin 的复 diffraction coefficient 做相干平均；其 workstation 示例把 grating calculations 并行化，随后用整片 FDTD 与实验验证。[Arbabi et al. 2020](https://doi.org/10.1038/s41598-020-64198-8)

所以大 NA 传播相位的响应 key 不应天然只剩 `width`：

```text
(wavelength,
 polarization,
 local gradient vector / target direction,
 phase origin,
 atom or extended-cell geometry)
```

是否需要全部维度，应由选定方法的 qualification 决定。圆柱的旋转对称性可以减少 atom orientation 维度，却不会消除 square lattice 的 azimuthal dependence。

## 三、何时查表足够，何时才需要 optimizer

### 3.1 确定性恢复足够的条件

逐点或 gradient-aware 确定性恢复在下列条件同时成立时具有科学闭环：

1. 已有响应证据覆盖目标的波长、偏振、局部梯度和加工域；
2. 每个目标状态都有可制造候选，且 phase 是循环距离而不是线性 `0`/`2π` 距离；
3. 该响应方法已在所需梯度域内通过较高保真模型验证；
4. 形成后的 aperture 通过 vector focal evaluation 和预先定义的性能标准。

此时 hash/index lookup 仍是合适的高性能实现；高 NA 不会自动把一个可分离的离散匹配问题变成全局优化问题。

### 3.2 optimizer 有科学理由的触发条件

optimizer 的理由来自 objective 与耦合，而不是一个 NA 常数：

- 没有任何确定性候选同时满足相位、幅度、偏振与加工约束；
- pointwise 或 gradient-aware 候选在独立高保真验证中出现不可接受的效率、aliasing、Strehl 或焦场缺口；
- 目标包含多波长、多角度、多偏振或多焦点，局部最优不能组合成全局最优；
- 需要利用邻近耦合、位置变化或自由形状，而这些自由度不在 library 中；
- 需要在同一全局 objective 中权衡性能与加工鲁棒性。

Lin 与 Johnson 的 overlapping-domain 方法把邻居区域纳入每个局部求解，在相近成本下相对 LPA 获得约 `10×` 的精度改善，并用于 NA `0.71` 的大口径多色/消色差设计。[Lin & Johnson 2019](https://doi.org/10.1364/OE.27.032445) Skarda 等人的分布式 T-matrix/adjoint 实例则从传统周期库初值出发，对 NA `>0.996` 的 metalens 同时优化柱位置和半径，35 次迭代后效率约翻倍；这证明 optimizer 可以修复强耦合缺口，不证明所有高 NA 设计都必须优化。[Skarda et al. 2022](https://doi.org/10.1038/s41524-022-00774-y)

现有一手证据支持 adjoint sensitivity 对大量连续自由度的可扩展性：对一个标量 objective，所有参数的梯度成本可与约两次电磁求解同阶。[Skarda et al. 2022](https://doi.org/10.1038/s41524-022-00774-y) 文献不支持预先把 genetic algorithm 或 simulated annealing 指定为大 NA 的默认 optimizer；optimizer family、变量表示和停止规则仍是待裁决的方法选择。

### 3.3 optimizer 不能替代响应真值

若 objective evaluator 仍使用未经资格化的 pointwise LPA，optimizer 只会更充分地优化近似误差。任何 approximate/overlapping optimizer 的最终候选都应由更高保真、独立或收敛后的 full-wave evidence 验证。Lin 与 Johnson、Arbabi 等人的工作均在设计模型之外使用 full FDTD 或实验作最终核验。

## 四、vector angular spectrum 与 Richards–Wolf/Debye 的分工

### 4.1 已发表的物理对象

Richards 与 Wolf 推导的是 **aplanatic optical system** 的 image-space 矢量焦场；其解覆盖整个 angular semi-aperture `0 <= alpha <= 90°`，并在 `alpha -> 0` 时退化到标量经典理论。[Richards & Wolf 1959](https://doi.org/10.1098/rspa.1959.0200)

vector angular spectrum 把一个已知平面上的电磁场分解为平面波，逐个乘以传播因子，再在另一平面重建；它与 vectorial Rayleigh–Sommerfeld 表示存在严格联系。[Liu & Lü 2007](https://doi.org/10.1016/j.optlastec.2006.03.006)

两者的输入语义不同：

| 算子 | 正确输入 | 主要用途 | 关键适用条件 |
| --- | --- | --- | --- |
| vector angular spectrum | 均匀介质中某一平面的 complex `E`，最好同时有 `H` | 传播真实 solver exit field；保存非理想幅相和偏振 | 平面与坐标明确；sampling/padding/bandlimit/evanescent policy 明确 |
| Richards–Wolf/Debye | pupil 或 reference sphere 上的矢量场 | 理想 aplanatic 高 NA 基准；已知 pupil-to-sphere mapping 的焦场 | sine condition、`NA=n sin(alpha)`、apodization、polarization transport 与 interface transmission 明确 |

方法建议：

- **实际候选**：从 full-wave/stitched evidence 的出射 reference plane 使用 qualified vector angular spectrum；
- **理想基准**：从编译出的理想 pupil/reference-sphere field 使用 qualified Richards–Wolf；
- **交叉区间**：在相同 pupil semantics 下做 complex-field parity，不能只比较 FWHM。

Debye 名称不能赋给“标量 ASM 后补一个 `Ez`”的实现；相关历史误用已在 [Debye–Wolf 数值遗产恢复记录](2026-07-15-debye-wolf-numerical-heritage-recovery.md) 中审计。

### 4.2 两种算子的 qualification

vector angular spectrum 至少应固定并验证：

- 坐标、time/phase convention、FFT normalization 与 reference-plane `z`；
- 像方介质折射率、`kx/ky/kz` branch、propagating/evanescent policy；
- `Ex/Ey/Ez` 与需要时 `Hx/Hy/Hz` 的横向性和 Poynting-flux 定义；
- input padding、transfer-function bandlimit、output sampling；
- grid refinement、反向传播/可逆性和 direct vector Rayleigh–Sommerfeld parity。

Matsushima 与 Shimobaba 证明：连续 angular spectrum 公式本身不依赖传播距离近似，但离散 transfer function 会因 sampling 产生严重误差；band-limited ASM 用显式带限扩大可信传播域。[Matsushima & Shimobaba 2009](https://doi.org/10.1364/OE.17.019662)

Richards–Wolf/Debye 至少应固定并验证：

- `NA = n sin(alpha)`，不得把 immersion `NA > 1` 静默裁剪；
- pupil 到 reference sphere 的 sine-condition mapping；
- amplitude、phase、polarization transport、apodization 与界面 Fresnel 系数；
- direct angular quadrature reference；
- 低 NA 标量极限、已发表焦场对称性、complex-field convergence；
- FFT/CZT/Bessel/GPU accelerator 对同一物理 contract 的 parity。

Leutenegger 等人已把 vector Debye integral 重写为二维 Fourier transform，并用 FFT/CZT 计算整个焦区；速度来自同一积分的快速实现，不是另一个物理模型。[Leutenegger et al. 2006](https://doi.org/10.1364/OE.14.011277)

## 五、高 NA 所需的求解器证据

建议把证据强度理解为逐层递进，而不是“一次 sweep 就证明整片 lens”。

### 5.1 periodic cell evidence

只足以支持 pointwise method：

- 求解器/版本、材料模型及工作波长样本；
- period、height、shape、加工范围和 mesh；
- 入射方向、偏振基、复 transmission/reflection；
- 各传播 diffraction order 与功率闭合；
- reference plane、phase origin 和复场 normalization；
- mesh、domain 与 monitor-placement convergence。

Ansys 官方 small-scale workflow 同样把 phase、transmission 与 near-field 一并建库，并在整片 direct FDTD 与 stitched field 之间比较；官方文档还明确指出 abrupt neighboring radii 会破坏 local periodicity。[Ansys Small-Scale Metalens](https://optics.ansys.com/hc/en-us/articles/360042097313-Small-Scale-Metalens-Field-Propagation)

### 5.2 gradient / extended-cell evidence

高 NA 确定性方法还需要：

- local target gradient vector 或 deflection angle；
- grating/supercell 内的有序 atom sequence；
- phase-origin sweep；
- TE/TM 或完整 polarization scattering basis；
- 目标 order 与 aliasing orders 的 complex diffraction coefficients；
- supercell length、边界与邻近组合的收敛。

Arbabi 等人对每个 grating period 计算多个 phase origin，并对复 diffraction coefficient 作相干平均；只平均功率会丢失相位信息，不能复现该方法。

### 5.3 aperture / coupled evidence

要对最终高 NA 器件作性能 claim，还需要：

- 形成后 aperture 的真实 complex vector field 或等价 scattering operator；
- 至少一个比设计模型更高保真的整片、overlapping-domain 或 distributed full-wave verification；
- 与目标波前的 complex error、非目标 diffraction、反射与吸收分账；
- 焦区 `Ex/Ey/Ez`、Poynting flux、found focus、FWHM、depth 和明确口径下的 focusing efficiency；
- numerical convergence 与运行证据的可重放 identity。

“只保存理想 phase map 后用 scalar ASM 聚焦”可以作目标 sanity check，不能作为高 NA 传播相位器件的 solver evidence。

## 六、避免 ASM 过度计算的数值路线

### 6.1 先明确不会消失的工作量

对一个出射平面 spectrum：

```text
field_spectrum = FFT2(exit_field)

field(z) = IFFT2(
  field_spectrum * exp(i * kz * z)
)
```

`field_spectrum`、`kx/ky/kz`、bandlimit 与 vector projection 对同一 grid/wavelength 只应建立一次。对一批 `z`，传播因子可以广播，inverse FFT 可以 batched dispatch。

但若需求真的是 `N_z` 个完整的 `(x,y)` complex planes，仍需计算 `N_z` 个逆变换；向量化只能减少解释器与调度开销，不能改变输出数据量。一次性构造 `N_z × N_y × N_x` 又可能超过内存，因此生产实现应按 memory budget 分块。

### 6.2 先问 metric 需要什么

当前 `z in [0.8f, 1.2f]` 的评估不必一开始生成完整三维场：

1. **axial scout**：对所有候选 `z`，直接从 spectrum 批量求光轴或少量中心点的复场；无需为每个 `z` 重建完整平面；
2. **peak refinement**：在 scout 的峰值附近加密 `z`；
3. **selected planes**：只在最佳焦面及少量 depth 边界平面执行 batched inverse FFT；
4. **metrics**：在这些平面上求横向 FWHM、encircled/concentrated power 与 vector-field ratios；
5. **artifact policy**：保存轴向 trace、最终焦面复场和可重放 contract，不默认保存整个三维体。

若 depth 的正式定义要求每个 `z` 的 encircled power 或二维 FWHM，则该 metric 本身确实要求更多平面；这应作为显式 cost，而不是在底层 kernel 里暗自过算。

### 6.3 实现应保留的高性能不变量

- 不在 Python 中逐 pixel、逐 atom 或逐 `z` 调用 FFT；
- spectrum、波矢、mask 和 immutable response table 按 contract identity 复用；
- component 与 `z_batch` 作为数组维度，kernel 对其广播或 batched；
- batch 大小由 memory budget 决定，不把整片焦区强制常驻内存；
- CPU、GPU、FFT、CZT 或轴对称 Bessel 只是同一科学 contract 的 execution binding；
- accelerator 必须对 direct/reference path 做 complex-field parity；
- 性能 benchmark 与物理 qualification 分开记录。

## 七、已知事实、方法选择与未决研究

### 已知事实

- 大 NA 增大局部 phase gradient，削弱 normal-periodic pointwise library 的两个核心近似；
- 高 NA 不蕴含 optimizer 必需；grating-aware deterministic design 已有实验成功；
- 不完整 `2π` 的平台仍可能在大角度更优；
- scalar/constant-phase propagation 对高 NA 性能预测不够；
- full-wave 或显式 coupled method 是最终高 NA claim 的更高保真证据；
- vector Debye 与 vector ASM 都可 FFT 加速，但输入物理语义不同。

### 需要系统裁决的方法选择

- 第一版 high-na propagation 是否止于“完整编译 + 假/参考 evidence”，还是必须产生真实候选；
- pointwise、gradient-aware、coupled 三层中，首版实现到哪一层；
- square、hexagonal 或其他晶格是否进入首版设计域；
- actual-field evaluator 是否固定为 vector ASM，Richards–Wolf 是否作为理想 reference；
- optimizer 的触发证据、objective、变量表示、加工投影与停止规则；
- full-wave verification 使用整片 FDTD、overlapping domain 还是另一种可资格化方法；
- 何种性能缺口允许从确定性 design 升级为 optimization。

### 未解决的研究问题

1. 没有跨平台通用的 `NA` 或 `edge phase step` 数值阈值来认证 LPA；它必须由具体 platform 的 angle/gradient-resolved evidence 建立。
2. 当前 SiN-on-silica、目标波长与加工域是否存在高效的大角度 propagation-phase platform，仍需真实求解器数据。
3. 有效折射率 phase-envelope 能否对有限高度二维柱阵列形成 solver-free 严格上界，现有一手证据仍不足。
4. 对实际大口径三维 metalens，哪种 coupled solver/optimizer 在当前 workstation 与 license 上可接受，不能从二维或异材料论文直接外推。
5. 轴对称 Bessel/Hankel acceleration 对线偏振高 NA 焦场需要保留有限 angular modes；其 truncation 与 direct parity 尚未建立。

## 对后续设计树的直接提示

本记录支持把第一层决策写成：

```text
brief remains propagation phase
        |
        +-- arithmetic domain impossible
        |
        +-- pointwise method admissible
        |
        +-- gradient-aware method required
        |
        +-- coupled optimization justified
```

它不支持：

```text
if NA > 0.5:
    route = large_na
    solver = debye
    optimizer = required
```

更诚实的心智顺序是：

```text
target
  -> preflight
  -> response method
  -> evidence
  -> recovery
  -> vector focus
  -> verification
```

其中 optimizer 是 `recovery` 的一种可选 binding；Debye/ASM 是 `vector focus` 中由输入语义决定的 method；二者都不是新的 Authority 状态。

## 一手来源

1. A. Arbabi et al., “Increasing efficiency of high numerical aperture metasurfaces using the grating averaging technique,” *Scientific Reports* 10, 7124 (2020). [DOI](https://doi.org/10.1038/s41598-020-64198-8)
2. V. Egede Johansen et al., “Nanoscale precision brings experimental metalens efficiencies on par with theoretical promises,” *Communications Physics* 7, 123 (2024). [DOI](https://doi.org/10.1038/s42005-024-01598-6)
3. S. Kim, J. Kim, K. Kim, M. Jeong, and J. Rho, “Anti-aliased metasurfaces beyond the Nyquist limit,” *Nature Communications* (2025). [DOI](https://doi.org/10.1038/s41467-024-55095-z)
4. H.-C. Lin, Z. Wang, and C. W. Hsu, “Fast multi-source nanophotonic simulations using augmented partial factorization,” *Nature Computational Science* 2, 815–822 (2022). [DOI](https://doi.org/10.1038/s43588-022-00370-6)
5. Z. Lin and S. G. Johnson, “Overlapping domains for topology optimization of large-area metasurfaces,” *Optics Express* 27, 32445–32453 (2019). [DOI](https://doi.org/10.1364/OE.27.032445)
6. J. Skarda et al., “Low-overhead distribution strategy for simulation and optimization of large-area metasurfaces,” *npj Computational Materials* 8, 78 (2022). [DOI](https://doi.org/10.1038/s41524-022-00774-y)
7. R. Pestourie et al., “Inverse design of large-area metasurfaces,” *Optics Express* 26, 33732–33747 (2018). [DOI](https://doi.org/10.1364/OE.26.033732)
8. B. Richards and E. Wolf, “Electromagnetic diffraction in optical systems. II. Structure of the image field in an aplanatic system,” *Proceedings of the Royal Society A* 253, 358–379 (1959). [DOI](https://doi.org/10.1098/rspa.1959.0200)
9. P. Liu and B. Lü, “The vectorial angular-spectrum representation and Rayleigh–Sommerfeld diffraction formulae,” *Optics & Laser Technology* 39, 741–744 (2007). [DOI](https://doi.org/10.1016/j.optlastec.2006.03.006)
10. M. Leutenegger, R. Rao, R. A. Leitgeb, and T. Lasser, “Fast focus field calculations,” *Optics Express* 14, 11277–11291 (2006). [DOI](https://doi.org/10.1364/OE.14.011277)
11. K. Matsushima and T. Shimobaba, “Band-limited angular spectrum method for numerical simulation of free-space propagation in far and near fields,” *Optics Express* 17, 19662–19673 (2009). [DOI](https://doi.org/10.1364/OE.17.019662)
12. Ansys Optics, “Small-Scale Metalens – Field Propagation.” [Official documentation](https://optics.ansys.com/hc/en-us/articles/360042097313-Small-Scale-Metalens-Field-Propagation)
