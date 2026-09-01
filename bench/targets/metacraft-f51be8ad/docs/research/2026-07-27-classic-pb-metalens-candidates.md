---
record_type: research_record
date: 2026-07-27
status: research_finding
authority_level: none
current_capability: false
---

# 经典 PB metalens 候选与复刻边界

## 后续决策

本记录完成后，[ADR 0008](../adr/0008-honor-explicit-cell-constraints-before-advice.md)
接受了合法的论文 cell period、atom height 与固定 geometry。
Khorasaninejad 与 Yang 标准 brief 因而可以保留
下文披露的单元事实，不再由默认 period 或 height advice 覆盖。两者
仍分别因为 low-na 器件适配、孔径形状和评价约定等差异被称为
adapted reproduction。

## 结论

经典 rectangular nanofin 与 elliptical pillar 都已有足够的一手参数，可分别成为 MetaCraft 的 PB 单元回归对象。

- **rectangular nanofin**：Khorasaninejad 等人在 *Science* 2016 给出了三组完整的 TiO2 单元尺寸、器件焦距与口径、偏振转换约定及实测焦斑和效率。
- **elliptical pillar**：Yang 等人在 *Nature Communications* 2018 给出了 silicon 椭圆柱的长短轴、高度、周期、焦距、口径、NA、Jones 两个本征通道和圆偏振效率。

但“论文参数充分”不等于“当前 MetaCraft 可以宣称 exact reproduction”。当前编译流程会自行裁决周期、高度、材料资格和评估方法；只要这些值没有逐项固定为论文事实，结果就只能叫 **adapted reproduction**。

本轮推荐：

> **以 Yang 2018 的单个圆偏振子透镜作为第一个 low-na PB 全流程回归，以 Khorasaninejad 2016 的 532 nm rectangular nanofin 作为第二个单元级回归。**

前者在 NA、单波长、旋转单元和 Jones `x/y` 基态求解上最接近当前路线；后者是更经典、参数最完整的 rectangular nanofin 标杆，但论文器件的 NA 0.8 不属于当前 low-na 能力。

## 调研口径

本文只使用论文原文、期刊页面、作者公开稿和论文补充材料，不采用综述或二手参数表。

本文使用两个严格不同的名称：

- **exact reproduction**：波长、材料及其色散来源、单元形状、尺寸、周期、高度、器件口径、焦距、偏振手性与坐标约定、数值边界和指标定义均与论文一致。
- **adapted reproduction**：保留论文的科学目标和物理机制，但至少一个执行参数由 MetaCraft 当前协议重新裁决。

若论文只披露了器件目标、却没有披露足以重建版图的单元事实，就不能称为 exact reproduction。反过来，即使论文披露完整，当前编译器若不允许固定其周期或高度，也不能把适配结果称为 exact。

## 候选一：Khorasaninejad 2016 rectangular nanofin

论文：Mohammadreza Khorasaninejad et al., “Metalenses at visible wavelengths: Diffraction-limited focusing and subwavelength resolution imaging,” *Science* 352, 1190–1194 (2016), DOI 10.1126/science.aaf6644。  
一手来源：[作者公开稿](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf)，[Harvard DASH 记录](https://dash.harvard.edu/entities/publication/2dfb243e-ba2a-43ea-b20b-b9ee9dbd1467)

### 论文事实

所有单元均为 glass substrate 上的 TiO2 rectangular nanofin，高度固定为 600 nm，并排列在方形晶格上。论文用 Lumerical FDTD 的周期 `x/y` 边界和 `z` 向 PML 求解单元；偏振转换效率定义为相反手性透射功率与入射圆偏振功率之比。

| 设计波长 | width | length | height | period |
| --- | ---: | ---: | ---: | ---: |
| 405 nm | 40 nm | 150 nm | 600 nm | 200 nm |
| 532 nm | 95 nm | 250 nm | 600 nm | 325 nm |
| 660 nm | 85 nm | 410 nm | 600 nm | 430 nm |

三个聚焦器件均为直径 240 µm、焦距 90 µm、NA 0.8。论文采用 RCP 入射；转换后的 LCP 分量获得 `+2 × orientation` 的几何相位。

| 设计波长 | 实测 FWHM | 实测聚焦效率 |
| --- | ---: | ---: |
| 405 nm | 280 nm | 86% |
| 532 nm | 375 nm | 73% |
| 660 nm | 450 nm | 66% |

三组实测 Strehl ratio 均接近 0.8。

### 对 MetaCraft 的意义

532 nm 版本最适合作为 rectangular nanofin 的单元级基准：其几何尺寸、材料、周期、半波片目标和手性变换均已明确，能够直接检验：

1. 两个正交线偏振基态是否只求解一次；
2. 同手性泄漏和交叉手性透射是否由同一 Jones 证据推导；
3. `orientation -> geometric phase` 的符号是否与所声明坐标系一致；
4. 后续阵面是否只旋转已选单元，而不为每个角度重复求解。

它不适合作为当前第一个完整器件复刻，因为论文器件 NA 0.8，超出本轮 low-na 路线。把 NA 降低，或把 TiO2 换成 silicon nitride，均已构成 adapted reproduction。

## 候选二：Yang 2018 elliptical pillar

论文：Zhenyu Yang et al., “Generalized Hartmann-Shack array of dielectric metalens sub-arrays for polarimetric beam profiling,” *Nature Communications* 9, 4607 (2018), DOI 10.1038/s41467-018-07056-6。  
一手来源：[KIT 作者公开稿](https://publikationen.bibliothek.kit.edu/1000087431/19372759)，[期刊 DOI 页面](https://doi.org/10.1038/s41467-018-07056-6)

### 论文事实

圆偏振子透镜采用 silicon elliptical pillar，位于 silicon dioxide 层上。单元及器件参数完整：

```text
wavelength       = 1550 nm
major axis       = 1350 nm
minor axis       = 480 nm
height           = 340 nm
period           = 1500 nm
focal length     = 30 µm
aperture         = 22.5 µm × 22.5 µm
nominal NA       = 0.32
```

论文用 Lumerical FDTD、`x/y` 周期边界和 `z` 向 PML 计算未旋转椭圆柱。两个复透射系数分别对应沿椭圆长轴和短轴的线偏振入射；选择 `1350 nm × 480 nm` 是为了让同手性项消失，使入射圆偏振尽量转换到相反手性。

在论文自身的 Jones 与手性约定中：

- right-handed 入射的交叉手性项携带 `-2 × orientation`；
- left-handed 入射的交叉手性项携带 `+2 × orientation`。

因此 MetaCraft 不能只复制一个正负号；它必须同时记录传播方向、观察方向、圆偏振基底和角度正方向，然后从坐标契约推导符号。

圆偏振子透镜的理论聚焦效率为 60%，实测为 26%；论文将聚焦效率定义为焦斑功率与照射到 metalens 上的功率之比。

### 对 MetaCraft 的意义

这一候选同时满足：

- 单波长；
- NA 0.32，最接近当前 low-na 路线；
- 单一椭圆柱，仅通过旋转形成相位；
- 明确的长轴/短轴 Jones 基态；
- Lumerical FDTD；
- 完整的器件目标与实验指标。

它来自 polarimetric metalens array，但每个圆偏振子透镜本身是独立的 PB metalens；首轮只复刻一个子透镜，不实现整套 Hartmann-Shack 阵列。

当前仍应标记为 adapted reproduction。论文的 1500 nm 周期会触发当前的衍射阶次警告，340 nm 高度也不应被一般红外经验域暗中改写。若编译器不能显式固定这些论文参数，就只能保留它的器件目标和物理机制，让当前规则重新裁决执行参数。

## 候选三：Lin 2014 历史基准

论文：Dianmin Lin et al., “Dielectric gradient metasurface optical elements,” *Science* 345, 298–302 (2014), DOI 10.1126/science.1253213。  
一手来源：[作者公开稿](https://hasman.technion.ac.il/files/2017/04/298.full_.pdf)，[作者公开补充材料](https://hasman.technion.ac.il/files/2017/11/Lin.SM_.pdf)

### 论文事实

该工作在 quartz 上使用 100 nm 厚 poly-silicon nanobeam waveplate；典型 nanobeam 宽 120 nm、排列间距 200 nm。550 nm 时达到接近半波片的相位延迟。metalens 的焦距为 100 µm、口径约 96 µm、NA 约 0.43，报告焦斑 FWHM 为 670 nm。

样品从 substrate side 入射。在论文补充材料的约定中，LCP 获得 `+2 × orientation`，RCP 获得相反符号；设计使用八个取向覆盖 `0–2π`。

### 复刻边界

它是 PB dielectric metalens 的重要历史原点，但单元是纳米梁波片及其截断组合，不是当前模板所表达的独立 rectangular nanofin 或 elliptical pillar。用当前单柱模板近似它只能叫 adapted reproduction，不能用“矩形看起来相似”掩盖拓扑差异。

## 候选四：Zhao 2021 low-na 科学参照

论文：Maoxiong Zhao et al., “Phase characterisation of metalenses,” *Light: Science & Applications* 10, 52 (2021), DOI 10.1038/s41377-021-00492-y。  
一手来源：[期刊全文](https://www.nature.com/articles/s41377-021-00492-y)，[PMC 全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC7947014/)

### 论文事实

论文测量的 PB metalens 工作于 532 nm，名义 NA 为 0.106，由 sapphire 上的 GaN nanofin 通过旋转提供相位。论文报告 PB 样品的 Strehl ratio 为 0.92、depth of focus 为 40 µm，并特别证明：low-na metalens 的最亮轴向位置可能偏离由球面波前定义的焦距。

### 复刻边界

可访问正文明示了 low-na 器件、材料、旋转机制和评价指标，但没有在正文文字中完整列出周期、长宽和设计焦距。它非常适合成为 `0.8f–1.2f` 焦区搜索及 Strehl/DOF 语义的科学参照，却不足以单独生成 exact layout。不得把论文中的理想有限口径算例与实验 PB 样品拼接成一套虚构参数。

## shape 必须由复刻目标固定

论文复刻与一般设计具有不同的权限关系。

### 论文复刻

`shape` 是论文身份的一部分，必须由复刻目标固定：

```text
paper atom says rectangular nanofin
    -> shape = rectangular nanofin

paper atom says elliptical pillar
    -> shape = elliptical pillar
```

LLM 不得把 rectangular nanofin 改成 elliptical pillar，也不得以“更容易扫参”为由改成另一模板。形状改变会同时改变：

- 两个线偏振本征通道；
- 半波延迟条件；
- 可加工尺寸域；
- 邻近耦合；
- 相位符号与效率证据的可比性。

因此论文复刻中的 LLM 只能解释已知事实、指出缺失字段和建议是否值得执行，不能替论文选择 shape。

### 一般 brief

一般 brief 若没有指定 shape，LLM 可以在编译阶段提出一个有理由的建议，例如在 fabrication、material、wavelength 和 route 已知后建议 rectangular nanofin 或 elliptical pillar。但建议仍不是事实：

1. 建议必须保留来源和理由；
2. deterministic compiler 必须验证该 shape 属于当前 route 的受支持模板；
3. fabrication bounds、period、height domain 和 solver capacity 必须独立通过；
4. 只有真实 `x/y` 证据证明近似半波延迟与可接受的转换表现后，单元才能被选择；
5. 后续阵面只消费被选择的单元，不重新让 LLM 改形状。

这保持了清晰边界：**论文固定身份，LLM 提供建议，程序裁决资格，求解器提供证据。**

## 推荐的执行顺序

1. 用 Khorasaninejad 2016 的 532 nm 单元做 rectangular nanofin 的 Jones 回归，但不运行其 NA 0.8 整镜。
2. 用 Yang 2018 的单个圆偏振子透镜做 elliptical pillar 的 low-na 全流程 adapted reproduction。
3. 用 Lin 2014 检查八取向和手性符号的历史语义，不把 nanobeam 阵列伪装成单柱模板。
4. 用 Zhao 2021 检查焦区搜索、Strehl 与 depth of focus 的报告语义，不用缺失参数生成版图。

首轮验收应明确写出 `adapted reproduction`。只有未来提供一个能够冻结论文全部执行事实、同时保存材料来源和坐标约定的 reproduction profile，才可以升级为 exact reproduction。
