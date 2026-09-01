---
record_type: research_record
date: 2026-07-26
status: research_finding
authority_level: none
current_capability: false
---

# 零级衍射周期规则的科学依据

日期：2026-07-26  
文档性质：Research Record；只保存外部事实、推导和适用边界，不作系统裁决。

## 结论

文献给出两个不同的上限：

- 采样上限来自 Nyquist 条件，
  `P <= lambda / (2 NA)`；它限制目标波前的空间采样，但不能单独排除落入光锥的高阶副本。
- 衍射上限来自光锥或光栅条件；它必须检查结构两侧的传播介质，不能只检查空气侧。

MetaCraft 采用的

```text
order ceiling = lambda / (n_substrate + NA)
```

不是文献中的标准公式，而是下述条件在当前物理域内的直接推导。将它与采样上限取较小值、再向下取整到 10 nm，均属于 MetaCraft 的系统政策，不属于外部事实。

## 文献事实

1. Ansys 的 metalens workflow 给出
   `NA <= lambda / (2 * unit-cell size)`，等价于
   `P <= lambda / (2 NA)`。Kim、Kim 与 Rho 又在动量空间写成
   `G >= 2k`，并明确指出 Nyquist 条件只防止频谱副本彼此重叠，不能保证副本不落入自由空间光锥。[Ansys metalens workflow](https://optics.ansys.com/hc/en-us/articles/35797097445779-Introduction-to-metalens-workflows)；[Kim et al., *eLight* 5, 28 (2025)](https://doi.org/10.1186/s43593-025-00111-y)
2. 同一篇 *eLight* 文章对一维晶格给出更严格的光锥条件
   `G >= k + k0`：只有光锥内的平面波分量可以辐射，因而高阶频谱副本也必须留在光锥之外。[Kim et al. 2025](https://doi.org/10.1186/s43593-025-00111-y)
3. Delacroix 等从光栅方程给出的零级光栅条件为
   `P/lambda <= 1 / [max(n_i, n_t) + n_i sin(theta)]`。在正入射时，它退化为
   `P <= lambda / max(n_i, n_t)`，同时约束入射侧与透射侧。[Delacroix et al., Proc. SPIE 7731, 77314W (2010), Eq. 1](https://doi.org/10.1117/12.858278)
4. Arbabi 等明确要求像素在 silica 与 air 中都保持亚波长，并说明其晶格倒格矢大于两侧介质中的光波矢时，近正入射不出现一级衍射。这是“检查两侧介质”的 metalens 实例，而不是只检查空气侧。[Arbabi et al., *Nature Nanotechnology* 10, 937–943 (2015)](https://doi.org/10.1038/nnano.2015.186)
5. Byrnes 等区分了在空气中倏逝、却能在玻璃中传播的横向波矢分量，并把这些分量在基底背面全反射所携带的能量按保守约定计为损失。这证明忽略基底侧传播通道是一项性能口径选择，不等于该通道不存在。[Byrnes et al., *Optics Express* 24, 5110–5124 (2016)](https://doi.org/10.1364/OE.24.005110)

## MetaCraft 的推导

令：

```text
k0       = 2 pi / lambda
G        = 2 pi / P
k_target = NA * k0
```

其中 `lambda` 是真空波长，`P` 是方格晶格的物理周期，
`k_target` 是整个口径所需的最大横向波矢。对折射率为 `n_j` 的任一均匀包围介质，其辐射光锥半径为 `n_j k0`。要使距离原点最近的非零频谱副本在最坏方向上仍位于该光锥之外，需要

```text
G >= k_target + n_j k0 .
```

当前空气—基底体系满足 `n_substrate >= n_air`，因此基底侧给出最紧条件：

```text
2 pi / P >= (NA + n_substrate) * 2 pi / lambda
P <= lambda / (n_substrate + NA) .
```

这条链把已发表的光锥条件推广到当前的基底光锥，并以整个口径的最大横向波矢作保守输入。以上每一步均可复核，但组合后的最终公式是 MetaCraft 的推导，不得写成外部文献的原公式。

采样与衍射回答不同问题，因此物理周期同时服从两者：

```text
P <= min(
  lambda / (2 NA),
  lambda / (n_substrate + NA)
)
```

如何选择等号、如何向下取整，以及由哪个证据对象保存材料样本，属于 ADR 与实现契约的职责。

## 适用边界

该推导只适用于：

- 当前单波长、低 NA、局部周期的 metalens 物理域；
- 正入射建立的周期单元证据，以及由目标波前产生的最大横向偏转；
- 等周期的方格晶格与各向同性口径需求；
- 空气上包层、均匀且近似无损的基底；`n_substrate` 取工作波长处经过资格确认的相位折射率。

以下情况必须重新推导，不能机械复用该式：

- 斜入射、浸没式环境、多个包围层或强吸收/各向异性介质；
- 矩形、六角或方向相关的晶格与频谱；
- 多波长设计、宽带最坏情况或大 NA 矢量设计；
- 有意利用非零衍射级次的 metagrating。

零级衍射只关闭“无非零传播级次”这一项适用性判断。它不保证高透射、完整相位覆盖、局部周期近似成立、足够的候选单元数量，也不代替全波响应证据。

## 来源

1. S. Kim, J. Kim, and J. Rho, “Invited commentary: metaphotonic interpretation of Nyquist sampling criterion,” *eLight* 5, 28 (2025). [DOI](https://doi.org/10.1186/s43593-025-00111-y)
2. C. Delacroix et al., “Annular Groove Phase Mask coronagraph in diamond for mid-IR wavelengths: manufacturing assessment and performance analysis,” Proc. SPIE 7731, 77314W (2010). [DOI](https://doi.org/10.1117/12.858278)；[author manuscript](https://orbi.uliege.be/bitstream/2268/81723/1/ProcSPIE_CD_final.pdf)
3. A. Arbabi et al., “Dielectric metasurfaces for complete control of phase and polarization with subwavelength spatial resolution and high transmission,” *Nature Nanotechnology* 10, 937–943 (2015). [DOI](https://doi.org/10.1038/nnano.2015.186)；[author manuscript](https://arxiv.org/abs/1411.1494)
4. S. J. Byrnes et al., “Designing large, high-efficiency, high-numerical-aperture, transmissive meta-lenses for visible light,” *Optics Express* 24, 5110–5124 (2016). [DOI](https://doi.org/10.1364/OE.24.005110)；[author manuscript](https://arxiv.org/abs/1511.04781)
5. Ansys Optics, “Introduction to metalens workflows.” [Official documentation](https://optics.ansys.com/hc/en-us/articles/35797097445779-Introduction-to-metalens-workflows)
