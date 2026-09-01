---
record_type: research_record
date: 2026-07-30
status: research_finding
authority_level: none
current_capability: false
---

# 大 NA 传播相位：共性、论文选择与 MetaCraft 保真路线

本记录只回答一个问题：

> 大 NA 传播相位为何会离开低 NA 的理想结果；这是所有局部相位设计的共性，
> 还是 MetaCraft 自身的设计错误？

结论先行：

> 退化的压力来自共同物理；退化到什么程度取决于具体平台。  
> Arbabi 2020 给出了一种更强的资格化方法，不是唯一设计路线。  
> MetaCraft 应深化响应证据，而不应更换自己的编译心智链。

## 一、三栏裁决

| 共性 | 论文选择 | 我们的缺口 |
| --- | --- | --- |
| 大 NA 使目标相位在口径边缘变化更快；固定晶格会逐渐欠采样 | Arbabi 2015 缩小晶格以缓解欠采样，同时保留周期库与逐格选柱 | 当前 8/12/16 只描述可选相位状态，尚未证明空间晶格足以采样边缘相位 |
| 相邻几何快速变化会削弱“每格都处于相同单元无限周期阵列”的近似 | Arbabi 2020 用周期 blazed grating 估计扩展单元的目标衍射响应 | 当前响应主要是每个状态的局部复系数，不能单独证明邻居变化无害 |
| 大偏折角会暴露 meta-atom 方向图的离轴变化 | Arbabi 2020 比较不同偏折角、偏振和 phase origin 的复衍射系数 | 当前法向周期响应不能自动证明离轴目标方向中的复振幅仍然成立 |
| 高 NA 的效率下降不等于焦点一定消失；欠采样、非目标衍射和相位误差会先侵蚀效率 | Arbabi 2015 仍以 pointwise phase mapping 得到衍射极限高 NA 焦点，但效率随 NA 上升而下降 | 当前结果若只看 FWHM，可能把错误能量分配误判为成功 |
| 局部单元基底在更困难目标下可能不完整 | Chung 与 Miller 2019 以 inverse design 扩展设计自由度并给出 unit-cell 路线的效率上限 | 这证明需要诚实的 method qualification；它不证明每个单色高 NA brief 都必须启动 optimizer |

## 二、为什么这是共性，而不是 Arbabi 的偶然问题

对于焦距为 \(f\) 的轴上 metalens，目标相位可写为

\[
\phi(r)=-k_0\left(\sqrt{r^2+f^2}-f\right).
\]

因此口径边缘满足

\[
\left|\frac{\partial \phi}{\partial r}\right|_{\rm edge}
=k_0\,\mathrm{NA},
\]

若晶格间距为 \(p\)，相邻格点的边缘相位步长近似为

\[
\Delta\phi_{\rm edge}
\approx \frac{2\pi p\,\mathrm{NA}}{\lambda}.
\]

这意味着 NA 增大时，不论采用哪篇论文、哪种代码，都会同时出现三种压力：

1. 每个 \(2\pi\) 相位周回所拥有的空间格点变少；
2. 相邻 meta-atom 的几何变化加快；
3. 目标出射方向远离法线，单元方向图变得重要。

Arbabi 2015 直接把高 NA 效率下降归因于快速相位在 HCTA 晶格上的欠采样；
其 1550 nm HCTA 使用 800 nm 六角晶格、940 nm 高的 a-Si 圆柱，
以周期响应建立完整相位库，再在每个晶格位置选择最接近期望相位的圆柱。
这正是 MetaCraft 现有
`periodic library → phase selection → aperture`
的科学原型，而不是另一套架构。

该论文还展示了一个重要事实：同一套逐格相位映射仍可形成高 NA、
衍射极限焦点，但焦距越短、NA 越高，透射率和聚焦效率越低。论文建议减小晶格，
并用 full 3D FDTD 验证缩小后的器件。因此“高 NA 性能下降”首先是共同的采样与
响应适用域问题，不是 MetaCraft 独有的软件问题。

来源：[Arbabi et al., *Nature Communications* 6, 7069 (2015)](https://doi.org/10.1038/ncomms8069)；
[author manuscript](https://arxiv.org/abs/1410.8261)。

## 三、Arbabi 2020 解决了什么，又选择了什么

### 3.1 它处理的是普遍问题

Arbabi 2020 明确指出传统局部相位映射包含两个近似：

1. 每个 meta-atom 的响应不受不同邻居影响；
2. meta-atom 的局部透射系数不随入射和散射方向变化。

低 NA 时，结构缓变且偏折角小；大 NA 时，两项近似同时承压。
这是论文最值得吸收的部分，也是 MetaCraft 必须表达的 method applicability。

### 3.2 它采用的是特定方法

论文把 aperiodic deflector 看成缓慢变化的 periodic blazed gratings，
计算多个 grating period 和 phase origin 的**复衍射系数**，再作带相位的相干平均。
作者据此比较两个 a-Si 平台，并选择：

- 350 nm 晶格；
- 590 nm 柱高；
- 60–200 nm 方柱宽度；
- 仅 1.63π 的局部相位覆盖。

该平台低角度指标略差，却在约 15° 以上优于完整 2π 平台，并最终实现
NA 0.78 的器件。这里的 grating family、phase-origin averaging、1.63π
平台和具体 RCWA 设置都是论文的实现选择，不是“高 NA propagation”
的通用定义。

更关键的是，最终 metalens 仍然使用设计曲线逐格选择柱宽。Grating averaging
主要用于**评价和选择平台**，并没有把整片器件改成一个迭代优化问题。

来源：[Arbabi et al., *Scientific Reports* 10, 7124 (2020)](https://doi.org/10.1038/s41598-020-64198-8)；
[author manuscript](https://arxiv.org/abs/2004.06182)。

## 四、为什么也不能反向宣布“永远不需要优化”

Chung 与 Miller 2019 研究更困难的高 NA、宽带消色差目标。他们指出，
局部 unit-cell basis 对快速变化的理想出射场并不完备，并计算了这种
unit-cell 路线的效率上限；其 freeform inverse design 通过增加设计自由度，
实现了更高 NA 的宽带目标。

这项结果支持两个边界：

- **共性边界**：局部周期相位库不是任意目标的完备基底；
- **范围边界**：该论文的目标包含宽带消色差和更大的自由度，
  不能据此推断 MetaCraft 当前的单色高 NA brief 必须优化。

因此 optimizer 应由已经观察到的性能缺口、耦合证据或多目标约束触发，
不能由一个 `NA > threshold` 分支自动触发。

来源：[Chung & Miller, *Optics Express* 28, 6945–6965 (2020);
preprint 2019](https://doi.org/10.1364/OE.385583)；
[author manuscript](https://arxiv.org/abs/1905.09213)。

## 五、对 MetaCraft 最小而充分的深化

不推荐把 Arbabi 2020 的方法复制成新的固定 route。推荐保留原有心智链：

```text
brief
  → compiled proof
  → periodic response
  → deterministic selection
  → aperture
  → field
  → focus
```

只把 response 到 field 之间的证据逐层深化：

```text
complex cell response
  → resolved exit-field patch
  → assembled aperture field
  → vector field propagation
```

其中：

- `complex cell response` 保留现有快速查表；低 NA 仍可形成 8/12/16
  phase set，高 NA 则从同一 library 作 pointwise deterministic selection，
  不把有限量化硬推到快速变化的口径边缘；
- `resolved exit-field patch` 保存每个已选单元在共同参考平面上的复场分布，
  而不是把整格压缩成一个常数；
- `assembled aperture field` 仍由同一个 aperture owner 排列，不建立第二套
  high-NA workflow；
- vector field method 只消费已经形成的 `Field`，不反向控制结构选择。

这是一项 architecture recommendation，不是上述论文已经替 MetaCraft
完成的 capability。

### 5.1 资格化，而非偷换路线

每个平台先走有界资格化：

```text
phase sampling
  → periodic response
  → resolved local field
  → small-aperture full-wave comparison
```

若在目标 NA 域内通过，继续确定性选择；若失败，则返回精确的
`response method unqualified`，请求更强证据。更强证据可以是 grating、
overlapping segment 或整片 full-wave，但 compiler 不应静默切换，
更不应自动启动 optimizer。

这保留了 Rust 生命周期，也保留了 Python 的科研编译角色：

> 状态不因方法而增，证据随问题而深。  
> 设计仍由 brief 发端，前进只凭 proof 放行。

## 六、canonical brief 的重新裁决

若 canonical case 的目的，是验证 MetaCraft 自己的
`periodic library → pointwise selection` 架构，那么：

1. **high-NA propagation 主例应从 Arbabi 2020 改为 Arbabi 2015
   HCTA-derived standard。**
2. **Arbabi 2020 应降为 stress/comparison case**，用于解释大角度响应与比较
   更强的资格化证据，而不是定义 MetaCraft 的默认方法。

但不能把 HCTA-derived standard 伪称为逐项论文复刻。Arbabi 2015 的器件由
单模光纤经基底照明，论文的最优相位同时依赖输入场；当前 `MetalensBrief`
只表达偏振，没有表达完整入射场。因此现阶段应：

- 固定其材料、晶格、柱高、形状和高 NA 几何；
- 使用 MetaCraft 当前可表达的入射条件；
- 标为 `HCTA-derived high-NA propagation standard`；
- 把 exact reproduction 延后到 brief 能表达 incident field 之后。

这比“为了复刻论文而改写 route”更诚实，也比“因为当前模型不足而删除大 NA”
更稳健。

## 七、最终判断

### 共性

- 高 NA 带来边缘相位欠采样；
- 相邻单元变化与离轴方向图削弱局部常数响应；
- 相位状态更多不等于空间采样更密；
- 焦点尺寸正确不等于能量分配正确。

### 论文选择

- Arbabi 2015：保留 periodic library 与 pointwise selection，适合作为
  MetaCraft high-NA canonical baseline；
- Arbabi 2020：提供大偏角平台资格化方法，适合作为 stress/comparison；
- Chung–Miller 2019：证明 unit-cell basis 有边界，适合作为未来 optimizer
  的触发依据，不适合作为当前默认 route。

### 我们的问题

MetaCraft 的主要缺口不是“没有照抄 grating averaging”，而是：

1. phase-state quantization 与 spatial sampling 尚未分开资格化；
2. cell response 到 aperture field 的压缩仍可能过强；
3. 尚未用小口径 full-wave comparison 划定当前 response method 的适用域；
4. high-NA result 需要同时审查焦斑、功率去向和 complex-field error。

推荐收束为：

> 主链不换，证据加深；结果可差，边界须真。  
> Arbabi 用来照见缺口，不用来替换 MetaCraft。
