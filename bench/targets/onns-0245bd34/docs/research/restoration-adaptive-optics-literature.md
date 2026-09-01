# Restoration 转向自适应光学：文献边界与最小路线

- 日期：2026-08-11
- 状态：研究备忘录；不是新颖性声明
- 裁决：`Narrow and proceed by gates`
- 标签：**Established** = 来源直接支持；**Inference** = 跨来源判断；**Hypothesis** = 待本项目验证
- 本地依据：[DONN handbook](../../reference_projects/donn_research/DONN_research_handbook.md)、[restoration design](../restoration-research-design.md)、[competitive gap](2026-07-26_adaptive-restoration-competitive-gap.md)

## 结论

**Inference：**固定光学前端加数字恢复的路线应迅速完成剩余测量并封档为机制/负结果基线，主线转向准静态显微场景中的**自验证主动 AO**：系统在有限校准观测内决定下一探针，并只在有证据支持未来独立原始科学帧获益时校正，否则继续测量或拒绝校正。

**Inference：**本装置不与 MEMS DM 竞争闭环带宽。可竞争的是相位可编程性、实测有效空间自由度、有限观测的决策效率和“何时不校正”的风险控制。

**Hypothesis：**在未知样品、硬件失配和有限剂量下，主动相位多样性与拒绝机制能否比最强固定/Fisher 探针、传统相位多样性和学习型 AO，以更少观测或更低有害校正率，改善一个因果上更晚、未参与决策的原始科学帧？这是条件性空白；固定探针若达到同等效用，主张即失败。

## 为什么固定 DL 路线只能收尾

- **Established：**NAFNet 是有竞争力的数字恢复基线，不是容易击败的“旧模型”。[NAFNet](https://doi.org/10.1007/978-3-031-20071-7_2)
- **Established within project record：**27 个 digital、frozen 和 joint NAFNet-S 核心运行早期即达到最佳验证 PSNR；继续训练没有最佳模型收益。固定光学变换有可复现作用，但未建立“光学前端 + 小后端”对强数字恢复的绝对优势。[ADR-0014](../adr/0014-retain-the-core-budget-and-shorten-followup-training.md)
- **Established：**传播快不等于系统快；输入编码、SLM 更新/稳定、曝光、读出、A/D、计算和校准均须入账。[DONN handbook](../../reference_projects/donn_research/DONN_research_handbook.md)
- **Inference：**显微数据不足只限制学习方法的泛化主张，不能替代数字基线。应补齐承诺测量，报告 matched-budget 结果与区间，将固定路线封档；不要再靠放大网络追逐主叙事。

## 相邻工作与被压缩的主张

| 来源 | Established | 对本项目的 Inference |
|---|---|---|
| [Fan review](https://doi.org/10.1002/lpor.202501566) | 超表面可多维调控并同步取得多个已知不相关编码的强度；方向仍早期，受设计/制造精度限制。 | “紧凑、并行编码”不能单独承载新颖性。 |
| [Metasurface WFS](https://doi.org/10.1038/s41566-025-01772-4) | 双折射超表面单次 phase-diversity WFS；深湍流 FSO 仿真+实验，Rytov 0.2–0.6，校正后平均约 16× signal。 | single-shot 已被占据，但它不是显微、未来科学帧或风险控制证据。 |
| [MLAO](https://doi.org/10.1038/s41377-023-01297-x) | 预定义偏置、pseudo-PSF 和小型物理网络；部分配置只需 2/4 图像。 | “少帧 + 小网络 + 校正”不够。 |
| [Optica phase diversity](https://doi.org/10.1364/OPTICA.518559) | 扩展荧光样品波前估计，低于 \(\lambda/35\) RMS，约 100 ms 感知。 | 必须证明主动选择/拒绝相对固定 diversity 的增量。 |
| [MeNet-AO](https://doi.org/10.1038/s41467-026-73389-2) | 三组图像对解码七个 Zernike 模式，含大像差和体内验证，报告校正低于 5 s。 | 多探针、高阶、频域与跨结构泛化均已拥挤。 |
| [SAFARI](https://doi.org/10.1038/s41377-026-02241-5) | DOE/薄扩散片实现单次无参考复波前恢复；\(1000^2\) 在 RTX 3080 Ti 约 5–10 s，DOE 原位标定用 \(9^2=81\) 次平移。 | single-shot 不等于高速；“单次、无参考、高分辨”不够。 |
| [Physical optical gradient](https://doi.org/10.1038/s41467-025-68259-2) | 相干反射共焦、两块 phase SLM；闭式测量 score 对全部 SLM 参数的梯度，复杂度不随参数数增长；先用 5 张离焦图恢复出射波前，再物理采梯度。 | 是高维控制基线/启发，不是通用显微或单帧证据。 |
| [NAFNet](https://doi.org/10.1007/978-3-031-20071-7_2) | 简洁数字网络即可成为强恢复基线。 | 轻量后端优势必须匹配算力、延迟、数据和输出后实测。 |

## MEMS 与 60 Hz LC-SLM 的边界

**Established：**HDSLM80R Plus 为 \(1920\times1200\)、8 μm、60 Hz、8/10 bit、fill factor >95%。[UPOLabs](https://www.upolabs.com/ProductsStd_683.html) BMC 连续面 DM 机械响应依型号约 <40–100 μs，标准驱动可达 2 kHz，高速选项可达 20/45/60/100 kHz。[BMC mirrors](https://bostonmicromachines.com/products/deformable-mirrors/standard-deformable-mirrors/)；[BMC FAQ](https://bostonmicromachines.com/products/deformable-mirrors/deformable-mirror-faq/)

**Inference：**60 Hz 仅对应 16.7 ms 标称帧周期，不是实测稳定时间；8 探针加 1 校正仅状态更新的理想下界已约 150 ms，尚未计相机和计算。因此只做 local、quasi-static、narrowband coherent transmission/phase microscopy 的 prescan–load–hold，不声称优于高速 DM。

**Hypothesis：**名义像素数不等于有效模式数。必须测 pupil、串扰、LUT、量化、偏振、NA 和噪声约束下的有效校正秩/频带；速度劣势只有在主动策略减少读数且 held lifetime 足够长时才可能摊销。

## 条件性空白：self-verifying active AO

**Inference：**邻近工作已分别覆盖少帧估计、固定 phase diversity、学习型校正、single-shot sensing 和高维物理优化；剩余可检验组合是：

\[
\text{probe history}\rightarrow
\{\text{continue, correct, abstain}\}\rightarrow
\text{held action}\rightarrow
\text{future independent raw science frame}\rightarrow
\text{risk/lifetime audit}.
\]

探针应按未来校正的决策价值选择，而非只最小化相位 RMSE；\(T\leq8\)；校准 \(R=1\) 与科学观测 \(R=0\) 分离；置信度针对有害校正校准；比较匹配 photons、reads、SLM states、settling、compute 和 wall time。

## 最小 E0–E5 与 kill criteria

| Gate | 最小证据 | Kill / Narrow |
|---|---|---|
| **E0 拓扑/相干** | 固定 amplitude SLM，确认 phase SLM 是唯一动态 actuator；测 \(R=1/R=0\)、交叉项、漂移、LUT、配准和 settling。 | 必须增加可调 delay、动态振幅或永久 science reference：**Kill topology**。 |
| **E1 O1/O2/O3 headroom** | 比较理想复控制、理想 phase-only、实际交付 phase-only；每种 held action 新采 \(R=0\) 原始帧。 | O3 无稳健正 headroom：**Kill**；只在窄域成立：`Narrow`。 |
| **E2 action identifiability** | 盲化 Zernike/device-native 像差 + 未知纹理；逐前缀 1–8 测 action agreement、oracle regret、correct/continue/abstain。 | \(T=8\) 仍无共同有用 action：**Kill policy**。 |
| **E3 因果转移** | 仅校准帧选 action；冻结、加载、稳定、阻断参考，再采新科学帧；含 safe/sham/opposite/equal-RMS。 | 科学帧参与选参，或增益只在校准/后处理：**Kill**。 |
| **E4 主动增量** | 对比固定/Fisher codebook、传统 diversity、经典 sensorless AO、MLAO/MeNet；逐前缀 matched budget。 | 固定/Fisher 匹配：**Kill active novelty**，但不否定一般 AO。 |
| **E5 风险/OOD/寿命** | specimen-by-session 留出；报告 harm、risk–coverage、abstention、probe count、邻域伤害和 lifetime。 | 风险失准、拒绝不减害、覆盖近零或无法摊销：**Kill self-verifying claim**。 |

阈值须由 E0/E1 pilot 的重复性与科学效应确定后预注册，不能先编数字。

## PhotoniX / LSA 级 evidence bar

**Inference（必要但非期刊官方清单）：**

1. 中心问题必须是 prospective correction-risk control，而非又一个 Zernike 网络。
2. 给出观测模型、phase-only 可达域、action identifiability、有效自由度和交付相位误差。
3. 真实硬件跨 specimen-by-session、像差族和重启；已知注入或独立 WFS/干涉作 truth。
4. 主结论来自决策后新采的 \(R=0\) 原始帧，不能由归一化、配准、去噪或反卷积提供。
5. 击败 O3 oracle 下可比方法、固定/Fisher codebook、传统 diversity、经典 sensorless AO 和 MLAO/MeNet，并做 sham/sign/trivial-policy 消融。
6. 完整匹配光子、读数、切换、稳定、曝光、传输、计算、墙钟、剂量和 correction lifetime。
7. episode 是统计单位；预注册 endpoint，报告效应区间、harm、risk–coverage、coverage、失效分层与负例。
8. 明确只覆盖准静态相干显微，不宣称普遍优于 MEMS、快速动态、荧光、非线性激发或强散射。

## 最终建议

**Inference：**立即执行 E0→E1→E2→E3；四关通过后才实现 E4 主动策略，再由 E5 判断论文资格。潜在高水平贡献不是“SLM 比 MEMS 快”，而是证明慢速、高维相位器件能在合适的准静态窗口，用更少且更有决策价值的观测可靠改善未来原始科学帧，并在证据不足时拒绝伤害样品。
