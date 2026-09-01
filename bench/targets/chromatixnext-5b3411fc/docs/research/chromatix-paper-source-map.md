# Chromatix 论文来源地图与仿真迁移预评估

> 调研日期：2026-07-16（Asia/Singapore）  
> 调研边界：只使用本地正式论文、工作区中的官方 `0.4.0` 标签源码、Chromatix 官方 GitHub/官方文档，以及论文明确指向的原作者数据或代码仓库。  
> 结论性质：这是进入代码复现与本课题模型试跑之前的来源核验和可行性预评估，不是最终的算力验收或数值精度认证。

## 1. 一页结论

**Chromatix 值得作为课题组未来波动光学仿真的候选底座，但应先做有验收指标的小型迁移试验，不能仅凭论文中的加速比直接批准全面迁移。** 它与以下任务高度匹配：可微分的标量/矢量波传播、4f 显微系统、PSF 工程、像差反演、全息、多个波长/偏振，以及基于 multislice 的三维散射正向模型；其核心优势是 JAX 自动微分、JIT 编译和单/多 GPU 并行。[论文 PDF，第 1–4 页](../../reference/s41592-026-03121-x.pdf#page=1) [官方 0.4.0 README](https://github.com/chromatix-team/chromatix/tree/0.4.0#chromatix--differentiable-wave-optics-using-jax)

主要保留意见有四项：

1. **复现包并不完整。** 论文公开的是 Chromatix 库和外部数据来源，未在 Code availability 中给出每幅图的冻结运行脚本、配置、权重、随机种子或完整环境锁；`0.4.0` 的公开示例中有 Holoscope、CGH、Zernike/Seidel fitting 等通用 notebook，但没有明显按论文 Fig. 2–5 命名的一套端到端复现实验。[论文 PDF，第 14 页](../../reference/s41592-026-03121-x.pdf#page=14) [0.4.0 文档示例目录](https://github.com/chromatix-team/chromatix/tree/0.4.0/docs/examples) [0.4.0 顶层示例目录](https://github.com/chromatix-team/chromatix/tree/0.4.0/examples)
2. **版本必须双轨管理。** 论文只写“version 0.4”，没有 commit SHA；本地拉取的自然候选是标签 `0.4.0`、commit `727d7a39e9a0054cfe3a102440fcf931d31fd11a`。但是官方 `0.5.0` 随后整体改造了 `Field`、光谱类型和 Flax/Equinox 接口，当前 `0.6.0` 不能默认视作论文代码的即插即用替代品。[0.4.0 release](https://github.com/chromatix-team/chromatix/releases/tag/0.4.0) [0.5.0 release](https://github.com/chromatix-team/chromatix/releases/tag/0.5.0) [0.6.0 release](https://github.com/chromatix-team/chromatix/releases/tag/0.6.0)
3. **论文性能数字不是本组机器的承诺。** 多数缩放实验使用 NVIDIA H100，snapshot PSF 工程因旧 PyTorch 限制使用 RTX 8000；结果主要是优化“单次迭代”计时，部分基准使用合成点源而非图中实验数据，折射率重建计时还不含正则化。计时中超过均值 3 个标准差的高离群值被丢弃，而这些高值可能来自 JAX 编译、驱动或调度。[论文 PDF，第 12–14 页](../../reference/s41592-026-03121-x.pdf#page=12)
4. **物理模型边界需要与本组课题逐项对齐。** 论文版对真实镜片几何/镀膜、传感器固定噪声与像素响应、复杂镜组的高效光线模型、RCWA 元表面、部分相干传播及传播导致的光谱变化支持不足；厚镜片采用近轴 Collins 积分，在大镜组视场边缘不如光线追迹或 beamlet propagation 准确。[论文 PDF，第 9 页与第 20 页](../../reference/s41592-026-03121-x.pdf#page=9)

因此建议把下一阶段拆成两个隔离环境：**A 环境固定论文版做复现；B 环境固定当前版做新课题开发**，用同一批小型 golden cases 检查强度、相位、能量、梯度和边界伪影后再决定迁移。

## 2. 本地资料盘点与版本身份

`reference/` 当前只有一份附件：[`s41592-026-03121-x.pdf`](../../reference/s41592-026-03121-x.pdf)，共 23 个 PDF 页面，包含正式文章、Methods、Extended Data figures 和 Extended Data Table 1；没有 supplementary ZIP、作者提供的 wavefront、数据集或逐图复现脚本。

工作区中的 `reference/chromatix/` 是官方仓库标签 `0.4.0`，HEAD 为 `727d7a39e9a0054cfe3a102440fcf931d31fd11a`（2025-05-27）。论文只给出“0.4”而非 SHA，因此“论文实际运行提交 = 该标签”仍是合理候选而非已被论文文本证明的事实。[论文 Code availability，第 14 页](../../reference/s41592-026-03121-x.pdf#page=14) [官方 0.4.0 commit](https://github.com/chromatix-team/chromatix/commit/727d7a39e9a0054cfe3a102440fcf931d31fd11a)

还有一个需要在复现日志中显式记录的版本异常：官方 `0.4.0` 标签的 `pyproject.toml` 内部仍声明 `version = "0.3.0"`。不能只依赖安装后的包版本字符串判断是否拿到了论文候选代码，应同时记录 tag 和完整 commit SHA。[0.4.0 `pyproject.toml`](https://github.com/chromatix-team/chromatix/blob/0.4.0/pyproject.toml#L325-L369)

## 3. 论文书目信息

- **题目：** *Chromatix: a differentiable, GPU-accelerated wave-optics library*。
- **期刊与页码：** *Nature Methods*, Volume 23, July 2026, pp. 1388–1398；DOI [`10.1038/s41592-026-03121-x`](https://doi.org/10.1038/s41592-026-03121-x)。收稿 2025-05-24，接收 2026-05-06，在线发表 2026-06-08。[论文 PDF，第 1 页](../../reference/s41592-026-03121-x.pdf#page=1)
- **作者：** Diptodip Deb、Gert-Jan Both、Eric Bezzam、Amit Kohli、Siqi Yang、Amey Chaware、Cédric Allier、Changjia Cai、Geneva Anderberg、M. Hossein Eybposh、Magdalena C. Schneider、Rainer Heintzmann、Fabrizio A. Rivera-Sanchez、Corey Simmerer、Guanghan Meng、Jovan Tormes-Vaquerano、SeungYun Han、Sibi Chakravarthy Shanmugavel、Teja Maruvada、Xi Yang、Yewon Kim、Benedict Diederich、Chulmin Joo、Laura Waller、Nicholas J. Durr、Nicolas C. Pégard、Patrick J. La Rivière、Roarke Horstmeyer、Shwetadwip Chowdhury、Srinivas C. Turaga；Deb 与 Both 为共同第一作者。[论文 PDF，第 1、11 页](../../reference/s41592-026-03121-x.pdf#page=1)
- **贡献归属：** 全体作者参与库开发；Deb 与 Both 主导库开发和论文中的计算实验；Deb、Both、Turaga 主笔论文。[论文 PDF，第 14 页](../../reference/s41592-026-03121-x.pdf#page=14)
- **许可区别：** Chromatix 代码为 MIT License；论文本身为 CC BY 4.0。二者不要混用。[论文 PDF，第 11、14 页](../../reference/s41592-026-03121-x.pdf#page=11) [0.4.0 LICENSE](https://github.com/chromatix-team/chromatix/blob/0.4.0/LICENSE)

## 4. 研究目标与核心方法

### 4.1 研究目标

论文针对计算光学中反复从零实现正向模型带来的三个问题：代码和约定不统一、复用与复现困难、GPU/自动微分/多卡性能难以正确实现。目标是提供一个开放的、可微分、GPU 加速的标准波动光学库，让光学系统像深度网络一样由标准“层/元件”组合，并可直接进入梯度优化、深度学习或硬件控制流程。[论文 PDF，第 1–3 页](../../reference/s41592-026-03121-x.pdf#page=1)

### 4.2 三个设计支柱

- **Differentiability：** 正向模型用 JAX 编写，自动得到对样品、像差、相位掩模或网络参数的梯度，可连接 Adam 等优化器和自校准反问题。[论文 PDF，第 2 页](../../reference/s41592-026-03121-x.pdf#page=2)
- **Composability：** 光学系统由可替换的标准元件组成，降低每个项目独立实现传播、镜片、SLM、样品和传感器的成本。[论文 PDF，第 2–3 页](../../reference/s41592-026-03121-x.pdf#page=2)
- **Scalability：** 借助 JAX/XLA，同一实现可在 CPU、GPU、TPU 上运行，并用 `vmap`、`pmap` 或 sharded `jax.Array` 做单卡批处理和多卡并行；官方也强调并行策略依赖具体应用，并不由 Chromatix 自动固定一种方案。[论文 PDF，第 3 页](../../reference/s41592-026-03121-x.pdf#page=3) [官方 Parallelism 文档](https://chromatix.readthedocs.io/en/latest/parallelism/)

### 4.3 数据模型与光学模型

核心状态是复光场 `Field`：除复振幅外，还携带波长/光谱、偏振和空间采样等信息；光学元件是 `Field -> Field` 的变换，系统是这些变换的序列。这一接口有利于模块组合，但迁移时必须统一坐标顺序、单位、采样间隔、归一化、频谱约定和 batch/wavelength 维度。[论文 PDF，第 4 页](../../reference/s41592-026-03121-x.pdf#page=4) [0.4.0 `Field` 源码](https://github.com/chromatix-team/chromatix/blob/0.4.0/src/chromatix/field.py)

论文版覆盖薄/实验性厚镜片、DMD/SLM、标量和矢量传播、离轴传播、Fresnel/角谱/带限角谱/可缩放角谱、偏振、三维 multislice 散射与双折射样品、基础传感器及 shot noise 等构件。[论文 PDF，第 3 页与第 20 页](../../reference/s41592-026-03121-x.pdf#page=3) [0.4.0 源码树](https://github.com/chromatix-team/chromatix/tree/0.4.0/src/chromatix)

## 5. 各图—数据—代码来源地图

| 图 | 任务与论文中实际展示 | 外部数据/原实现来源 | 可复现性备注 |
|---|---|---|---|
| Fig. 1 | Chromatix 构件和潜在应用的概念图 | 无实验数据；Chromatix 官方库 [`0.4.0`](https://github.com/chromatix-team/chromatix/tree/0.4.0) | 是能力示意，不是准确性实验。[论文 PDF，第 3 页](../../reference/s41592-026-03121-x.pdf#page=3) |
| Fig. 2a–f | Ring deconvolution；UCLA Miniscope 兔肝图像，空间变化 Seidel 像差 | [`apsk14/rdmpy`](https://github.com/apsk14/rdmpy) 同时是原作者公开实现和论文指向的数据入口 | 论文使用 1,024×1,024、550 nm 数据；性能基准改用合成点源。`rdmpy` 当前主分支持续更新且没有 release，论文未固定其 commit。[论文 PDF，第 4、12、14 页](../../reference/s41592-026-03121-x.pdf#page=4) |
| Fig. 2g–n | CoCoA；INR 表示三维荧光样品，并联合反演 Zernike 像差 | [`iksungk/CoCoA`](https://github.com/iksungk/CoCoA)；公开仓库含 PyTorch 代码和 bead 数据 | Fig. 2l 的实测 wavefront **不是公开下载项**，是作者向 ref. 43 团队索取；完整复现该 panel 需要再次申请。当前 CoCoA 仓库自述会持续更新，原环境为 Python 3.6/PyTorch 1.8。[论文 PDF，第 4、12、14 页](../../reference/s41592-026-03121-x.pdf#page=4) |
| Fig. 2o–u | 多角度强度测量反演 24 hpf 斑马鱼尾部三维折射率；multislice 正向模型 | 数据：[`DMD-MLA-01 Dataverse`](https://dataverse.tdl.org/dataverse/DMD-MLA-01)；原 multislice 方法代码可参照 [`Waller-Lab/multi-slice`](https://github.com/Waller-Lab/multi-slice)，但论文正式 Data availability 把该 GitHub 链接明确分配给 Fig. 4g–m | 论文重建 FOV 1 为 400×800×800 voxels，使用 168 张图；部分测量需按原设置人工剔除，前处理下采样到 80%。[论文 PDF，第 5、12、14 页](../../reference/s41592-026-03121-x.pdf#page=5) |
| Fig. 3a–e | Holoscope snapshot PSF 与 FourierNet 联合设计/重建 | 数据：[`Janelia Figshare 25277269 v1`](https://janelia.figshare.com/articles/dataset/Zebrafish_volumes_dataset_for_FourierNets_enable_the_design_of_highly_non-local_optical_encoders_for_computational_imaging_/25277269)；原 PyTorch 实现：[`TuragaLab/snapshotscope`](https://github.com/TuragaLab/snapshotscope) | 数据下载约 13.86 GB，论文使用 58 个斑马鱼三维 volume。原仓库仅测试 Python 3.7/PyTorch 1.7，并明确说新版 PyTorch FFT 接口不受支持，复现 baseline 需要独立旧环境。[论文 PDF，第 6–8、13 页](../../reference/s41592-026-03121-x.pdf#page=6) |
| Fig. 3f–l | DeepCGH：网络从三平面目标图直接生成全息相位 | 目标 pattern 为程序生成；论文未在 Data availability 中给出额外数据或冻结的原实现链接 | 2,048×2,048、三个轴向平面、batch 16；论文把 Chromatix 与原 TensorFlow 实现比较。属于合成 benchmark，适合作为第一批 smoke/golden test。[论文 PDF，第 6、8、13–14 页](../../reference/s41592-026-03121-x.pdf#page=6) |
| Fig. 4a–f | 25 个波长（400–650 nm，10 nm 间隔）的单通道光谱 PSF 工程 | 稀疏多色点源完全程序生成；Chromatix 官方代码是唯一统一 Code availability 项 | 是“模块可组合性”的 in-silico 演示，不是实测光谱系统验证。[论文 PDF，第 7–8、13–14 页](../../reference/s41592-026-03121-x.pdf#page=7) |
| Fig. 4g–m | 穿过散射介质的三维全息优化，把 Fig. 3f 的全息模型与 Fig. 2p 的 multislice 模型组合 | 数据/方法来源：[`Waller-Lab/multi-slice`](https://github.com/Waller-Lab/multi-slice) | 使用 50×1,200×1,200 voxels 的 *C. elegans* 头部折射率重建，但人为把折射率值放大 5 倍以突出散射，论文明确说这不是现实样品；不能把结果当作实验可行性验证。[论文 PDF，第 7–8、13–14 页](../../reference/s41592-026-03121-x.pdf#page=7) |
| Fig. 5 | Ring、CoCoA、RI、snapshot PSF、DeepCGH 的相对迭代速度 | 使用上述任务；ring 与 CoCoA 的缩放测试改用合成点源，DeepCGH pattern 为合成 | 汇总结论为单 GPU 约 2–6×、8 GPU 最好约 22×；必须按本组 GPU、张量形状和通信方式重新测。[论文 PDF，第 8–9、12–14 页](../../reference/s41592-026-03121-x.pdf#page=8) |
| Extended Data Fig. 1 | 三种并行模式的高层代码示意 | Chromatix/JAX | 图注明代码故意省略，不是完整运行代码；仅证明不同并行方案的模拟结果一致。[论文 PDF，第 15 页](../../reference/s41592-026-03121-x.pdf#page=15) |
| Extended Data Fig. 2–5 | Ring 无 vignetting 展示修正；CoCoA beads；Holoscope；DeepCGH | 分别沿用 rdmpy、CoCoA、Figshare、程序生成 pattern | 与主图来源相同；Extended Data Fig. 3 的 imposed-aberration bead ground truth 可公开获取，但主图 Fig. 2l 实测 wavefront 仍需索取。[论文 PDF，第 16–19 页](../../reference/s41592-026-03121-x.pdf#page=16) |
| Extended Data Table 1 | 与 dO、Optiland、dLux、Zemax、CODE V、Lumerical FDTD、XLumina 的功能比较 | 论文作者整理 | 表格是功能存在性比较，不是统一准确度验证；厚镜片支持有近轴近似脚注。[论文 PDF，第 20 页](../../reference/s41592-026-03121-x.pdf#page=20) |

论文的总原则是：上表未单列外部数据的展示，均为程序仿真生成。[论文 Data availability，第 14 页](../../reference/s41592-026-03121-x.pdf#page=14)

## 6. 对迁移成本最有用的实验尺度

| 任务 | 关键张量/优化规模 | 迁移含义 |
|---|---|---|
| Ring deconvolution | 1,024×1,024 图像；沿半径分 ring 并行；Adam 更新样品像素 | 可作为单图/空间变化 PSF 的首个真实数据试验；原仓库提醒全尺寸 miniscope 任务通常需要 >25 GB 显存。[论文 PDF，第 12 页](../../reference/s41592-026-03121-x.pdf#page=12) [rdmpy README](https://github.com/apsk14/rdmpy#usage) |
| CoCoA | INR 输入 x–y，输出 200 个 z plane；第二阶段同时更新 INR 参数和 ANSI 3–14 的 Zernike 系数 | 适合测试“神经表示 + 光学正向模型”的联合梯度；模型近似和 Zernike 归一化必须与原程序严格对齐。[论文 PDF，第 4、12 页](../../reference/s41592-026-03121-x.pdf#page=4) |
| 折射率显微 | 400×800×800 voxels，168 个入射角；每个角度 multislice + 反传；TV/Nesterov | 单个 float32 体本身约 0.95 GiB，实际还要容纳复光场、中间层和梯度，显存需求远高于体素数组；应先缩小 volume/角度数做梯度与收敛验证。[论文 PDF，第 12 页](../../reference/s41592-026-03121-x.pdf#page=12) |
| Snapshot PSF | 64 planes × 2,560×2,560 = 0.419 Gvoxels PSF；相位掩模 2,560×2,560；重建 64×512×512 | 是高显存、多卡切 plane 和通信的压力测试，不适合作为安装后的第一个运行用例。[论文 PDF，第 13 页](../../reference/s41592-026-03121-x.pdf#page=13) |
| DeepCGH | batch 16；2,048×2,048；三个 z 面 | 数据完全合成且指标明确，最适合作为第一批端到端 JIT/梯度/多卡测试。[论文 PDF，第 13 页](../../reference/s41592-026-03121-x.pdf#page=13) |
| 散射全息 | 50×1,200×1,200 折射率体；直接优化相位掩模 | 展示组合能力，但 5× 折射率缩放是人为的；本组必须换成真实物性和校准数据再判断效果。[论文 PDF，第 13 页](../../reference/s41592-026-03121-x.pdf#page=13) |

## 7. 适配性矩阵

| 本组未来仿真特征 | 初步适配度 | 理由/边界 |
|---|---|---|
| 标量傅里叶光学、4f、PSF、相位/振幅掩模、SLM/DMD | 高 | 是库和论文所有主要实验的中心路径。[论文 PDF，第 2–8 页](../../reference/s41592-026-03121-x.pdf#page=2) |
| 需要对样品、像差、掩模或网络参数求梯度 | 高 | JAX 自动微分是设计主轴，可接 Optax/Optimistix；需另做有限差分/伴随梯度抽检。[官方 FAQ](https://chromatix.readthedocs.io/en/latest/FAQ/) |
| 多波长、偏振、离轴传播、双折射或 multislice 前向散射 | 中高 | 论文版明确覆盖，但高 NA、强散射和采样边界需按目标系统做数值收敛试验。[论文 PDF，第 3、20 页](../../reference/s41592-026-03121-x.pdf#page=3) |
| 大体积/多角度/多深度、可自然切 batch 或 plane 的任务 | 中高 | `vmap`/`pmap`/sharding 可扩展；官方说明并行方式高度依赖任务，跨卡求和会降低缩放效率，当前仍建议显式并行。[官方 Parallelism 文档](https://chromatix.readthedocs.io/en/latest/parallelism/) |
| Windows 原生 NVIDIA GPU | 低；WSL2/Linux 中高 | 当前官方文档称 GPU 只支持 Linux 或 Windows 上的 WSL2；原生 Windows 可安装但不应预期 GPU 路径。[官方安装文档](https://chromatix.readthedocs.io/en/latest/installing/) |
| 复杂真实镜组、镀膜、视场边缘像差，且需光线级精度 | 低到中 | 厚镜片路径是近轴近似；论文建议未来结合 ray-based model。[论文 PDF，第 9、20 页](../../reference/s41592-026-03121-x.pdf#page=9) |
| 元表面 RCWA、部分相干、传播中的光谱变化、精细像素响应/固定噪声 | 低（论文版） | 论文将这些列为缺口；不能在没有自行扩展和验证时用 Chromatix 单独承诺。[论文 PDF，第 9 页](../../reference/s41592-026-03121-x.pdf#page=9) |
| 含明显后向散射的严格全波模型 | 低到中 | 标准主线以单向传播/multislice 为主；`0.4.0` 有 experimental modified Born 模块，但其“experimental”状态本身要求独立验证。[0.4.0 release](https://github.com/chromatix-team/chromatix/releases/tag/0.4.0) [实验模块](https://github.com/chromatix-team/chromatix/tree/0.4.0/src/chromatix/experimental/modified_born_series) |

## 8. 复现与数值风险清单

### 8.1 官方 `0.4.0` 示例的实际覆盖范围

- `holoscope.ipynb` 明确说明它只演示 Holoscope 的**正向仿真**，不做“从数据完整优化 PSF”的联合训练；后文仅指出可与 FourierNet 组合，而没有提供论文 Fig. 3a–e 的完整训练、重建和评估流水线。[本地 `holoscope.ipynb`](../../reference/chromatix/docs/examples/holoscope.ipynb) [官方 `0.4.0` notebook](https://github.com/chromatix-team/chromatix/blob/0.4.0/docs/examples/holoscope.ipynb)
- `cgh.ipynb` 明确说明它只在理想仿真系统中对一个**固定目标全息图**直接优化光学参数，**不演示 DeepCGH 的深度学习方法**，因此不能把它当作论文 Fig. 3f–l 的 DeepCGH benchmark 复现脚本。[本地 `cgh.ipynb`](../../reference/chromatix/docs/examples/cgh.ipynb) [官方 `0.4.0` notebook](https://github.com/chromatix-team/chromatix/blob/0.4.0/docs/examples/cgh.ipynb)
- 对本地精确标签做文件名和文本盘点时，精确名称 `rdmpy`、`ring deconvolution`、`CoCoA`、`refractive-index microscopy` 没有命中相应论文工作流；`DeepCGH` 只在上述 CGH notebook 的引用和范围说明中出现。顶层 `examples/` 也只有两个并行化示例，通用 notebook 位于 `docs/examples/`。因此，**Chromatix 库和官方通用示例不等于论文 Fig. 2–5 的完整逐图复现包**。这是对公开 `0.4.0` 标签的仓库盘点结论，不排除作者另有未公开或未链接的实验脚本。[官方文档示例目录](https://github.com/chromatix-team/chromatix/tree/0.4.0/docs/examples) [官方顶层示例目录](https://github.com/chromatix-team/chromatix/tree/0.4.0/examples)

### 8.2 版本和环境

- `0.4.0` 声明 Python `>=3.11`，核心依赖只给下界（例如 `jax>=0.4.1`、Flax、Chex、Optax、SciPy、Jaxopt、Equinox、Optimistix），没有上界或论文环境 lock；该标签 CI 只测试 Python 3.11。直接在 2026 年解析“最新可满足版本”未必得到论文环境。[0.4.0 `pyproject.toml`](https://github.com/chromatix-team/chromatix/blob/0.4.0/pyproject.toml) [0.4.0 test workflow](https://github.com/chromatix-team/chromatix/blob/0.4.0/.github/workflows/test.yaml)
- 当前 `0.6.0` 要求 Python `>=3.12`；当前官方安装建议先装匹配 CUDA 的 JAX，Linux/WSL2 + NVIDIA GPU，文档当下写明 JAX 支持 CUDA 12/13。该要求是“当前版”信息，不能倒推论文运行环境。[0.6.0 `pyproject.toml`](https://github.com/chromatix-team/chromatix/blob/0.6.0/pyproject.toml) [官方安装文档](https://chromatix.readthedocs.io/en/latest/installing/)
- `0.5.0` release 明确称其 overhaul 了 `Field`、引入 `Spectrum`/`MonoSpectrum`、切换 Equinox 并更新接口；从论文版迁到当前版应按一次正式 API migration 管理，而非简单升级依赖。[0.5.0 release](https://github.com/chromatix-team/chromatix/releases/tag/0.5.0)

### 8.3 数据和 baseline 是移动目标

- `rdmpy` 无正式 release，README 鼓励持续 `git pull`；CoCoA 也写明仓库持续更新；`Waller-Lab/multi-slice` 明确说公开代码是相对原论文更新后的版本。论文没有记录它们用于比较时的 commit，因此重跑 baseline 前必须补做 commit 冻结。[rdmpy](https://github.com/apsk14/rdmpy) [CoCoA](https://github.com/iksungk/CoCoA) [multi-slice](https://github.com/Waller-Lab/multi-slice)
- Snapshot 原实现固定在 Python 3.7/PyTorch 1.7，当前依赖栈不能直接共用；数据归档约 13.86 GB。它应与 Chromatix/JAX 环境隔离，以容器或独立环境运行。[snapshotscope](https://github.com/TuragaLab/snapshotscope) [Figshare dataset](https://janelia.figshare.com/articles/dataset/Zebrafish_volumes_dataset_for_FourierNets_enable_the_design_of_highly_non-local_optical_encoders_for_computational_imaging_/25277269)
- Fig. 2l 实测 wavefront 需向原作者申请，是完整主图复现的明确外部阻塞项。[论文 PDF，第 14 页](../../reference/s41592-026-03121-x.pdf#page=14)

### 8.4 模型等价性比语法翻译更重要

CoCoA 对比已经展示了典型风险：Chromatix 使用完全近轴的 pupil-plane 模型，而原实现混用了 exact pupil field 与第二镜片近轴模型；两者重建差异并非单纯“库更快”，还包含 forward-model mismatch。未来迁移必须记录并测试传播近似、FFT 归一化、频域采样、padding、边界条件、折射率/波长单位、像差基底与归一化，而不是只对照 API 名称。[论文 PDF，第 4–5 页](../../reference/s41592-026-03121-x.pdf#page=4)

当前 `Propagate` 文档还提醒：默认 `pad_width=0` 会形成 circular convolution 和边缘伪影；默认传播方法/带限选项也会影响结果。虽然这是当前版接口说明，但它准确说明了迁移验收必须覆盖 padding 和 aliasing。[官方 `Propagate` 文档](https://chromatix.readthedocs.io/en/latest/api/elements/#chromatix.elements.Propagate)

### 8.5 性能口径

- 论文报告单 GPU 约 2–6×、8 GPU 最好约 22×，但这是相对不同原始 MATLAB/PyTorch/TensorFlow 实现的迭代速度，不是统一硬件上的绝对吞吐或端到端完成时间。[论文 PDF，第 8–9 页](../../reference/s41592-026-03121-x.pdf#page=8)
- JIT 首次编译、数据载入、预处理、保存、全部正则化和多卡通信应分别计时；论文 RI benchmark 明确不含 regularization，论文又会丢弃超过均值 3σ 的高计时离群值。[论文 PDF，第 12、14 页](../../reference/s41592-026-03121-x.pdf#page=12)
- 官方并行示例显示，完全独立的 plane 更接近线性缩放，需要跨卡求和的成像任务缩放较弱；这与本组算法的数据依赖结构直接相关。[官方 Parallelism 文档](https://chromatix.readthedocs.io/en/latest/parallelism/)

### 8.6 论文 Discussion 明确声明的模型缺口

以下不是由仓库盘点推测出的缺陷，而是论文作者在 Discussion 中直接给出的边界；评估本组课题时应逐项设置 gate：

1. 镜片模型仍以理想化元件为主；厚透镜能力属于实验性/近轴路线，不能替代复杂高性能镜组的工程建模。
2. 传感器模型尚未覆盖一些真实噪声图样和像素响应。
3. 没有用于复杂镜片序列的 ray-based 模型；作者把混合 ray–wave 建模列为未来方向。
4. 没有 RCWA，因而不应直接承担需要严格电磁求解的亚波长光栅或元表面设计。
5. 当前传播假设是完全相干光；部分相干传播以及传播过程中光谱发生变化尚未支持。

这些边界意味着：若本组问题主要是标量/矢量波动传播、PSF、SLM 和可微逆问题，Chromatix 很有吸引力；若关键误差来自真实镜组、像素级传感器响应、部分相干或亚波长结构，则需要额外模型、外部求解器和独立校准，不能仅凭 Chromatix 完成物理验收。[论文 PDF，第 9 页](../../reference/s41592-026-03121-x.pdf#page=9)

## 9. 建议的下一阶段验收路径

### 9.1 两个隔离环境

**论文复现环境 A**

- 固定候选源码：`0.4.0` / `727d7a39e9a0054cfe3a102440fcf931d31fd11a`；同时注明论文没有给 SHA。
- 从 Python 3.11 和该标签 CI 起步；显式锁定 Python、JAX/JAXLIB、CUDA、cuDNN、XLA 相关包和全部 Python 依赖，保存 lock、容器摘要和 `jax.devices()` 输出。
- 不因 `pyproject.toml` 报告 `0.3.0` 就误判源码；以完整 SHA 为身份。

**未来开发环境 B**

- 固定当前 release（调研时为 `0.6.0`），使用 Python 3.12+ 和官方当前安装流程；Windows GPU 放在 WSL2/Linux 内。
- 把 A 中验证过的物理算子用小型 golden tests 迁到 B；不要让论文 notebook 直接承担长期 API 兼容责任。

### 9.2 从低风险到高风险的试跑顺序

1. **安装与基础算子：** CPU 跑官方 tests；GPU 跑平面波→孔径→传播→透镜→强度，核对能量、相位和设备选择。
2. **梯度：** 用小尺寸 Zernike fitting 或合成 DeepCGH，对随机参数做自动微分与中心有限差分抽检。
3. **采样收敛：** 对 `dx`、padding、grid size、传播方法、float32/float64 做网格加密；要求感兴趣区域和目标指标收敛。
4. **首个真实数据：** 优先选 ring deconvolution 的裁剪数据，验证输入约定、PSF、损失下降、视觉结果和峰值显存。
5. **本组 tracer model：** 只移植课题组最小可代表链路，先不用全尺寸；与现有 MATLAB/PyTorch/自研代码比较强度/相位/梯度/收敛。
6. **扩容：** 单卡测 warm iteration、首次 compile、端到端时间和峰值显存，再逐步到 2/4/8 卡，报告通信比例与并行效率。
7. **最终 gate：** 物理误差、梯度误差、目标重建指标、端到端时间、显存、可维护性六项同时达标后，才批准全面迁移。

### 9.3 在决定“能否运行”前仍需课题组给出的最小需求

- 光源：波长/带宽、相干性、偏振、入射角分布。
- 系统：镜片/NA/焦距/介质折射率、DMD/SLM/传感器几何和采样、是否需要真实镜组/镀膜/像素响应。
- 样品：2D/3D、体素大小、折射率范围、散射强度、是否有明显后向散射或双折射。
- 目标：只做 forward simulation，还是反演样品/像差/相位掩模；损失函数、先验与正则化。
- 规模：空间尺寸、z planes、角度数、波长数、batch、预期迭代次数。
- 算力：操作系统、GPU 型号/数量/显存、驱动、WSL2/Linux 条件、CPU RAM 和数据盘吞吐。
- 验收：允许的数值误差、目标图像指标、最长运行时间和最大显存。

没有这些信息，目前只能给出“**框架层面可行，工程和物理精度需通过目标模型试跑确认**”的结论。

## 10. 核心一手来源索引

- 本地正式论文：[`reference/s41592-026-03121-x.pdf`](../../reference/s41592-026-03121-x.pdf)
- Nature 正式页面：<https://www.nature.com/articles/s41592-026-03121-x>
- Chromatix 官方仓库：<https://github.com/chromatix-team/chromatix>
- 论文候选版本：<https://github.com/chromatix-team/chromatix/tree/0.4.0>
- 当前官方文档：<https://chromatix.readthedocs.io>
- Ring deconvolution：<https://github.com/apsk14/rdmpy>
- CoCoA：<https://github.com/iksungk/CoCoA>
- Refractive-index microscopy data：<https://dataverse.tdl.org/dataverse/DMD-MLA-01>
- Snapshot zebrafish data：<https://doi.org/10.25378/janelia.25277269.v1>
- Snapshot baseline code：<https://github.com/TuragaLab/snapshotscope>
- Multislice/C. elegans：<https://github.com/Waller-Lab/multi-slice>
