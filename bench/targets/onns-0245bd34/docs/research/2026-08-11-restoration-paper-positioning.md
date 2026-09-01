# Restoration 论文定位复核：从固定测量边界到自验证时空主动光学

- 日期：2026-08-11
- 研究范围：本项目 fixed-measurement 结果、2023--2026 年学习型自适应光学、相位多样性、单次光学编码、序贯控制与高维波前整形
- 证据纪律：仅使用项目内规范记录、论文原文或出版社正式页面、官方设备页面
- 判断标签：**Established** 表示来源直接支持；**Inference** 表示由多项证据推导；**Hypothesis** 表示必须由本项目实验检验
- 总裁决：**固定测量路线封档；AO 路线 Narrow and proceed by gates**

## 1. 一句话定位

**Inference：**当前 fixed-measurement 工作证明了一个可训练的光学变换在既定测量协议中能够产生稳定增益，但没有证明它比拥有原始退化观测的强数字恢复器更有信息或更有效。因此，它不应再被包装成“光学前端击败数字后端”的独立主线，而应成为一个有用的边界结果：**学习发生在何处，比网络有多深更重要。**

主论文应由此转向一个更强、也更可证伪的命题：

> 在科学图像形成之前，系统以不超过有限预算的自适应时空相位探针获取决策所需的信息；它可以继续观测、加载校正或拒绝校正，并且只在随后独立采集的原始 science frame 上证明收益。

这里真正可能唤醒审稿人的不是“用了 8--10 帧”或“用了深度学习”，而是从**被动处理一次既定测量**转为**主动设计一次可信测量**。

## 2. 本项目现在实际处于什么位置

### 2.1 已建立的项目事实

- **Established within project：**固定测量 formal core 已按冻结协议完成 36/36 个研究单元并通过完整性门禁。[formal core summary](../../results/restoration/fixed_measurement/reports/fixed_measurement_core_formal_v1/summary.md)
- **Established within project：**在 formal core 的 light / medium / heavy 三个条件中，trained phase 相对 zero phase 的光学前端增益分别约为 (+12.579)、(+12.333) 和 (+12.290) dB；但 frozen / joint cascade 相对 matched digital NAFNet-S 分别仍低约 (0.207/0.252)、(0.030/0.076) 和 (0.023/0.071) dB。这一结果支持“受限相位变换可学习”，但不支持“混合链路优于强数字基线”。[formal experiment report](../../results/restoration/fixed_measurement/reports/fixed_measurement_core_formal_v1/experiment_report.json)
- **Established within project：**已有三种子 pilot 中，光学-only 为 (27.579\pm0.655\) dB，数字 NAFNet-S 为 (35.627\pm0.006\) dB，frozen serial 为 (34.659\pm0.041\) dB，joint serial 为 (34.551\pm0.083\) dB；相对数字-only 分别低 (0.968) 和 (1.076) dB。[Core-36 reuse report](../../results/restoration/fixed_measurement/core36_legacy_report/summary.md)
- **Established within project：**27 个 digital/frozen/joint 核心运行在 297--743 updates 已达到最佳验证 PSNR，继续训练到 6,000 updates 没有最佳模型收益；这使“只是没有训练够”的解释不成立。[ADR-0014](../adr/0014-retain-the-core-budget-and-shorten-followup-training.md)
- **Established within project：**项目已经正式将 fixed measurement 退出主动研究路线，并要求新路线结束于物理校正后的 detector output，而不是后接图像恢复网络。[ADR-0018](../adr/0018-retire-fixed-measurement-and-reset-on-adaptive-optics.md)
- **Established within project：**当前动态装置有独立 input-amplitude SLM 与 Fourier-phase SLM；一个 AO episode 内只有 phase SLM 承担时变探针和 held correction。[ADR-0017](../adr/0017-separate-input-amplitude-and-fourier-phase-slm-roles.md)
- **Established within project：**当前正式协议的观测上限是 (T\leq8)，不是固定八帧。若改成“不超过十帧”，必须先修改科学合同和 ADR，不能只在论文故事中悄悄改数值。[CONTEXT](../../CONTEXT.md)

### 2.2 fixed-measurement 的信息边界

设 (X) 为未知真值，(D) 为已经检测得到的退化数字图像，固定光学前端把 (D) 重放并形成新观测 (Z_\theta)，数字后端输出 \(\widehat X\)：

\[
X\longrightarrow D\longrightarrow Z_\theta\longrightarrow \widehat X.
\]

若 (Z_\theta) 只由 (D)、固定/学习参数 \(\theta\) 和独立器件噪声生成，则该链满足 Markov 条件，数据处理不等式给出

\[
I(X;Z_\theta)\le I(X;D).
\]

这不是说光学前端“完全无用”。它仍可能提供有利的归纳偏置、低维特征、模拟并行性或特定硬件成本优势。但它说明：

1. 它不能仅凭重编码宣称恢复了 (D) 中没有的测量信息；
2. 与能够直接读取 (D) 的强数字后端比较时，必须证明实测延迟、能量、吞吐、参数量或鲁棒性优势；
3. 如果再次检测还引入量化、散斑、shot/read noise 和对准误差，实际链路可能进一步损失信息。

NAFNet 原论文的重点恰恰是以简单、计算高效的结构获得强恢复性能，而不是一个容易击败的陈旧模型。[NAFNet, ECCV 2022](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136670017.pdf)

**Inference：**固定光学路线没有输在“网络不够新”，而是输在它介入得太晚：退化测量已经形成后，它主要是在改变表示，而不是改变可观测性。

## 3. fixed-measurement 单独成文的发表上限

### 3.1 当前缺失的爆点

**Inference：**不能从项目结果精确预测期刊分区或录用率，但可以明确判断：当前 fixed-only 证据不够支撑 PhotoniX 或 *Light: Science & Applications* 的中心论文。缺口不是再加一种网络，而是缺少至少一种不可被纯数字系统轻易替代的系统级贡献：

- 没有建立新的物理可观测量、编码容量或 pre-detection 信息收益；
- 没有证明“光学 + 小后端”在完整实测预算下优于强数字后端；
- 没有原生显微样品上的新科学观测终点；
- 没有硬件在环的能耗、吞吐、延迟、稳定性和 sim-to-real 证据链；
- fixed mask + digital decoder 的共同设计本身已经属于成熟的 deep-optics 范式。近期工作已经把该范式推进到复合镜头从零设计、真实系统校准和临床/病理应用。例如 DeepLens 展示了复合折射光学的端到端设计，[Nature Communications 2024](https://www.nature.com/articles/s41467-024-50835-7)；DeepDOF-SE 则以真实组织、临床工作流和诊断相关终点支撑深度学习显微平台，[Nature Communications 2024](https://www.nature.com/articles/s41467-024-47065-2)。

如果 fixed-measurement 主体仍主要是仿真和训练矩阵，那么“补一次测量”并不会自动使它成为一区论文。一个更现实的独立稿件需要至少形成以下之一：

1. 有边界条件的负结果/复现研究，证明后检测光学重编码何时有益、何时必然无益；
2. 真实硬件上的能效、吞吐或小后端部署优势；
3. 一个有明确任务价值、数字基线不能用同等成本复现的新测量机制。

**Inference：**用户所说“普通一区但缺少爆点”大体正确，但仍偏乐观；如果没有真实硬件成本或任务证据，fixed-only 更像扎实的内部闭环与后续论文的机制前奏，而不是已自然达到一区门槛的完整故事。

### 3.2 它对未来仍然有四种价值

固定路线不应被描述为“失败”，也不应继续吞噬主要实验预算。它的正确角色是：

1. **物理可行域证据。** 学习确实能在受限 phase-only 系统中找到优于零相位的稳定解；formal core 中 optical trained phase 相对 zero phase 的增益在三个条件下约为 (+12.29) 至 (+12.58) dB。这里的证据来自冻结工作点上的计算/数字孪生协议，尚不能替代原生显微硬件测量。
2. **信息边界证据。** 表示可被优化，不等于测量信息增加；强数字基线反而帮助识别了 intervention point 的错误。
3. **工程资产。** 已有的传播、调制、检测、数据协议、训练记录和硬件校准方法可用于新的 AO forward model，但 fixed protocol 本身保持只读。
4. **论文叙事中的转折。** 它可以占主文 Figure 1 的一个机制面板或补充材料，而不应与 AO 主结果平分篇幅。

## 4. 2023--2026 年邻近工作已经占据了什么

下表只列论文原文/出版社页面，并区分“已经占据的主张”和“仍未回答的问题”。

| 方向与一手来源 | 已经建立的能力 | 对本项目的压缩 |
|---|---|---|
| [MLAO, LSA 2023](https://www.nature.com/articles/s41377-023-01297-x) | 物理构造的小型 NN、预定义 phase diversity、多种显微模态、真实活体/组织条件；优于常用 modal sensorless AO | “物理引导 + 小网络 + 少帧 + 多模态”不是新颖性 |
| [DL-AO for SMLM, Nature Methods 2023](https://www.nature.com/articles/s41592-023-02029-0) | 直接估计并控制 28 种波前形状，在厚脑组织 SMLM 中以 3--20 次 mirror changes 改善分辨率和保真度 | “DL 控制 AO + 多模式 + 生物学终点”已占据 |
| [Sequential phase diversity, Applied Optics 2023](https://opg.optica.org/ao/abstract.cfm?uri=ao-62-30-7931) | 在存在 DM 模型误差时，通过连续 PD 估计和校正静态像差，并完成硬件实验 | “序贯 PD + 模型失配鲁棒”不是空白 |
| [Phase-diversity microscopy, Optica 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC10760184/) | 扩展荧光样品，少量观测，波前误差低于 \(\lambda/35\)，约 100 ms sensing，并与 SHWFS 校验 | 8--10 帧本身可能比经典 PD 更慢；必须证明每帧有额外决策价值 |
| [CoCoA, Nature Machine Intelligence 2024](https://www.nature.com/articles/s42256-024-00853-3) | 无外部训练集的自监督联合 3D 结构/波前估计；真实鼠脑并以直接 WFS AO 验证 | “数据不足所以用 self-supervision”也已有强先例 |
| [Model-free RL wavefront correction, arXiv 2024](https://arxiv.org/abs/2406.18143) | 将 phase-diversity wavefront control 建模为 episodic MDP；策略直接给出 DM 动作，研究 1--10 step、噪声和不可控模式 | “学习序贯控制策略”不是本项目独占；且其主要证据仍为仿真 |
| [Metasurface single-shot PD, Nature Photonics 2025](https://www.nature.com/articles/s41566-025-01772-4) | 双折射超表面并行编码 phase diversity，单次采集，在深湍流仿真和实验中实现平均约 16 倍信号提升 | “单次、紧凑、低延迟编码”已有顶刊标杆 |
| [Single-image sensorless AO, arXiv 2025](https://arxiv.org/abs/2509.17869) | 两光子显微单张图像估计，作者报告每次 correction loop 小于 1 s | 若本项目固定拍 8--10 帧，速度主张会直接受压；该来源仍是预印本 |
| [Single-shot hybrid encoder, Nature Communications 2026](https://www.nature.com/articles/s41467-026-72364-1) | 学习 phase bias + 深度 decoder，从单张 focal-plane intensity 去除相位符号歧义，预测 Zernike 并实验校正 | “学习型光学编码解除歧义 + 单帧波前估计”已被正面占据 |
| [SAFARI, LSA 2026](https://www.nature.com/articles/s41377-026-02241-5) | diffuser + 空间/傅里叶正则化，单次、无参考复杂波前恢复；覆盖 200 Zernike 和 >190,000 spatial modes | “高维、single-shot、reference-less”均不能单独作为爆点 |
| [MeNet-AO, Nature Communications 2026](https://www.nature.com/articles/s41467-026-73389-2) | 三组正负调制 image pairs、七个 Zernike 模式、最高 0.6 μm RMS、完整校正 <5 s；活体斑马鱼和鼠脑功能终点 | “三组调制 + 大像差 + 低光 + 跨结构 + 活体”构成必须正面对比的强基线 |
| [Optical gradient acquisition, Nature Communications 2026](https://www.nature.com/articles/s41467-025-68259-2) | 以光学测量同时获得全 SLM 参数梯度，优化复杂度不随参数量增长，并在相干反射共焦中验证 | “SLM 像素多/高维控制”不是优势，除非测出有效模式和观测成本 |
| [Model-based RL sequential PD, arXiv 2026](https://arxiv.org/abs/2604.00993) | 序贯 PD + model-based RL，在静态/动态 NCPA 仿真中闭环控制；约 10--15 steps 收敛 | “约十步内的学习控制”也已被占据；本项目必须依靠显微实证、风险门和独立 science frame 区分 |

补充设备事实：项目的 HDSLM80R Plus 官方标称为 (1920\times1200)、60 Hz、8/10 bit、fill factor (>95\%\)。[UPOLabs](https://www.upolabs.com/ProductsStd_683.html) 相比之下，BMC 官方 MEMS 产品列出微秒级机械响应和 kHz 至数十 kHz 驱动选项。[Boston Micromachines](https://bostonmicromachines.com/products/deformable-mirrors/standard-deformable-mirrors/)

**Inference：**项目不应与 MEMS 争夺高速动态闭环；应限定为 local、quasi-static、prescan-and-hold。60 Hz 只给出标称刷新周期，不能代替实测 settling。以 8 个探针加 1 个 correction state 计算，单纯刷新下界已约 150 ms，实际还须加入曝光、读出、传输、推断与稳定时间。

## 5. 剩余新颖性：有条件存在，但不是“十帧 AO”

### 5.1 仍可检验的组合命题

在本次检索到的代表性一手工作中，尚未发现与下面完整合同等价的显微系统：

\[
\underbrace{h_t=(y_{1:t},p_{1:t})}_{\text{probe history}}
\rightarrow
\underbrace{\{\text{continue},\text{correct},\text{abstain}\}}_{\text{risk-aware decision}}
\rightarrow
\underbrace{c_T}_{\text{held physical correction}}
\rightarrow
\underbrace{y_{\mathrm{sci}}^{\mathrm{future,raw}}}_{\text{independent endpoint}}.
\]

其区分力必须同时来自五点：

1. **变长预算。** (T_{\max}\) 是上限，不是固定 codebook；容易样本早停，困难样本继续，危险样本拒绝。
2. **面向动作的辨识。** 探针选择目标不是最小化全波前 RMSE，而是区分会导致不同安全校正的后验解释。
3. **校正风险。** 输出不仅有 correction，还要有经校准的 expected gain / harm risk；abstention 必须实际降低 harmful correction。
4. **因果分离。** calibration observations 不能充当主结果；所有主要结论来自 action 之后新采集、没有参与选择的 raw science frame。
5. **寿命与摊销。** held correction 必须在足够多后续帧/邻域内有效，使前面的探针、SLM settling 和 dose 得到摊销。

**Inference：**这是“条件性空白”，不是 global-first 证明。序贯 PD、RL 控制和 active wavefront shaping 均已存在；本项目只能主张这个组合在指定显微拓扑、预算和验证合同下带来新的可靠性或决策效率。

### 5.2 最危险的反例

任何一个反例成立，都可能拆掉主故事：

- **Fixed-codebook counterexample：**最强固定/Fisher 探针达到同样收益；则 active selection 没有增量。
- **Single-shot counterexample：**学习型单次 encoder 在同 photon/dose/time 下达到相同 correction；则多帧路线只能靠风险控制或更大适用域存活。
- **Classical-PD counterexample：**经典 phase diversity 在更少采集、更短时间下达到相同 raw science gain；则深度学习不是必要组成。
- **Optical-gradient counterexample：**物理梯度在相同硬件下以更低总成本找到更好高维 correction；则“SLM 高自由度 + learned policy”主张失效。
- **Reference-transfer counterexample：**(R=1) reference-assisted calibration 的最优 action 不能改善 (R=0) science path；则装置只证明了干涉测量，不是目标显微 AO。
- **Phase-only counterexample：**样品以 amplitude loss、multiple scattering 或 depolarization 为主，O3 delivered phase-only oracle 没有 headroom；则任何 estimator 都无从成功。
- **Digital-equivalence counterexample：**所谓改善只在配准、归一化、去噪或重建后出现，raw detector endpoint 没有变化；则不能声称 pre-detection correction。
- **Instability counterexample：**校准结束时 aberration/specimen 已漂移，correction lifetime 小于 acquisition cost；则 prescan-and-hold 没有实际价值。

## 6. 建议的 Nature-style 故事，不写成实验流水账

“我们先做 fixed，打不过 NAFNet，然后转向 AO”是实验室时间线，不是论文论证。更强的论证顺序是：

### Act I — The wrong intervention point

**Claim：**学习型固定光学表示可优化，但若它仅处理已检测的退化图像，就没有新增测量信息的普遍保证。

**Evidence：**物理 forward derivation、Markov/data-processing boundary、trained phase 对 zero phase 的增益、serial 对强数字 baseline 的负结果。

**作用：**不是证明“DL 不行”，而是证明“post-detection learned optics 的上限来自介入位置”。

### Act II — Move learning before information loss

**Claim：**真实 phase-only 硬件在科学帧形成前具有可测的 correction feasible region。

**Evidence：**理想复控制 O1、理想 phase-only O2、校准交付 phase-only O3；LUT、串扰、量化、polarization、pupil、NA、settling 均进入 O3。

### Act III — Time becomes an information dimension

**Claim：**有限时空探针逐步解除对“有用动作”的歧义；学习负责选择下一次最有决策价值的观测，而不是事后修图。

**Evidence：**Fisher rank / posterior contraction / action separability 随 prefix 增长；与相同预算固定/Fisher codebook 和 classical PD 对照。

### Act IV — A microscope that knows when not to correct

**Claim：**系统在证据充分时 correct，不充分时 continue，预计有害时 abstain。

**Evidence：**风险校准、selective risk--coverage、harm reduction、OOD、safe/sham/opposite action controls。

### Act V — The future frame is the verdict

**Claim：**最终 correction 改善的是后来独立采集的原始科学观测，而不是参与决策的校准帧或数字重建结果。

**Evidence：**冻结并 settle action 后采集 (R=0) science frame；相同 downstream evaluator 比较 corrected/uncorrected raw data；报告 lifetime 和 amortized gain。

最合适的中心句是：

> We move learning from restoring an already formed image to deciding what the microscope should measure, when the evidence is sufficient to correct, and when correction should be withheld.

## 7. PhotoniX / LSA 的最小 claim--evidence ladder

PhotoniX 官方强调由光子学促成的跨学科研究、工程进展与科学突破；LSA 官方定位是光学全谱系中的前沿、高质量基础和应用成果。[PhotoniX aims](https://link.springer.com/journal/43074/aims-and-scope)；[LSA aims](https://www.nature.com/lsa/aims)

下面不是期刊官方 checklist，而是结合其定位和上述已发表标杆得到的 **Inference**：

| 层级 | 最小 claim | 必需 evidence | 不足时的裁决 |
|---|---|---|---|
| **L0 Boundary** | fixed learned optics 可行但受 post-detection information boundary 限制 | 数学假设、对照实验、强数字 baseline、无选择性汇报 | 只能做内部/普通方法稿 |
| **L1 Hardware feasible set** | 真实 phase-only device 存在稳定可达 correction | LUT、delivered phase、pupil、cross-talk、settling、session repeatability | **Kill hardware claim** |
| **L2 Oracle headroom** | O3 oracle 可改善未来 raw science frame | O1/O2/O3、重复 session、blind known aberrations、raw endpoint | **Kill AO route** |
| **L3 Identifiability** | 在 (T\leq8)（或经正式变更后的 (T\leq10)）内能识别有用 action | action agreement、oracle regret、prefix curves、ambiguous pairs | **Kill limited-probe policy** |
| **L4 Active increment** | active probing 优于最强 fixed/Fisher/PD/RL policy | 完整匹配 photons、reads、states、settling、compute、wall time | 匹配即 **Kill active novelty** |
| **L5 Prospective causality** | correction 改善 action 之后的独立原始观测 | calibration/science 分离、safe/sham/opposite/equal-RMS controls | **Kill pre-detection claim** |
| **L6 Self-verification** | abstention 在 shift/OOD 下减少伤害 | calibrated gain/risk、risk--coverage、harm、coverage、failure strata | **Kill self-verifying claim** |
| **L7 Scientific consequence** | 改善一个原生、重要、非装饰性的 microscopy endpoint | native specimens、多 session/field/depth、独立 truth、可解释 failure boundary | 不足以支撑 PhotoniX/LSA |
| **L8 General consequence** | 原理超越单一装置或单一样品 | 至少两个结构/条件，或可移植控制接口与理论外推边界 | 更适合 specialist/Q1 而非旗舰光学期刊 |

**Inference：**PhotoniX 路线至少需要 L0--L7，并突出新的光学测量/控制原理；LSA 路线通常还需要让 L7 成为无法被普通 image-quality demo 替代的科学或成像结果，并以 L8 展示广泛后果。达到这些层级仍不构成录用保证。

## 8. 最短实验路线与 kill criteria

### E0 — topology and calibration

- 固定 amplitude SLM，确认 phase SLM 是唯一动态 actuator；
- 分别测 (R=1) calibration 和 (R=0) science transfer；
- 实测 phase LUT、settling、registration、reference drift、cross-term 和 background；
- 先决定 coherent microscopy 的原生 modality、specimen、field/depth 和 safe action。

**Kill：**若必须依赖永久 reference 才能得到改善，或动态振幅/额外 actuator 才能闭合模型，则杀死当前拓扑主张。

### E1 — delivered phase-only oracle

- 比较 O1 ideal complex、O2 ideal phase-only、O3 hardware-delivered phase-only；
- 每个 candidate action 后重新采集独立 (R=0) raw science frame；
- 先做 known injected Zernike/device-native modes，再做未知真实像差。

**Kill：**O3 没有跨 session 的稳健正 headroom，立即停止 estimator/policy 开发。

### E2 — action identifiability under the observation ceiling

- 构造“波前不同但最优 action 相同”与“观测相似但最优 action 不同”的困难对；
- 按 prefix (t=1,\ldots,T_{\max}) 报告 action agreement、oracle regret、posterior/risk calibration；
- 先比较解析/Fisher 固定探针，暂不训练大网络。

**Kill：**在当前 (T\leq8) 下仍不能区分共同有用 action，杀死有限探针策略；若只在 (T=9,10) 成立，再以新证据正式修订合同。

### E3 — calibration-to-science causal transfer

- 由 calibration frames 选择 action；冻结、load、settle；再采未来 science frame；
- 随机化 safe/sham/opposite/equal-RMS actions；
- 预先固定 raw endpoint 和 evaluator。

**Kill：**science frame 参与 action 选择、收益只存在于后处理、或 (R=1\rightarrow R=0) 迁移失败。

### E4 — learned active policy

只有 E1--E3 通过后，才训练轻量策略，并比较：

- optimized fixed codebook；
- Fisher-optimal fixed probes；
- classical phase diversity / sensorless AO；
- MLAO / MeNet-like learned estimator；
- sequential PD / RL controller；
- optical-gradient-inspired high-dimensional optimizer。

**Kill or narrow：**固定/Fisher 匹配 active，杀死 active-selection claim；经典方法匹配 learned policy，保留物理 AO、移除 DL necessity claim。

### E5 — reliability, lifetime and scientific endpoint

- specimen-by-session holdout；
- OOD、low-SNR、drift、neighboring field/depth、不可控模式；
- harm、risk--coverage、abstention benefit、correction lifetime、amortized gain；
- 至少一个原生样品上的结构或功能终点。

**Kill：**风险失准、abstain 不减伤、coverage 接近零、lifetime 无法摊销 calibration，或只有 USAF/PSNR 演示。

阈值不得现在凭感觉填写。应由 E0/E1 的重复性、效应大小和误差分布决定，然后冻结 protocol 和 stopping rules。

## 9. 最终定位建议

### 应继续的

- 将 fixed-measurement 完成必要的有界硬件复核后封档；
- 在主论文中把它压缩为“可学习但不增加测量信息”的边界证据；
- 先做 O3 oracle、action identifiability 和 calibration-to-science transfer；
- 只有三关通过后才投入 learned active policy；
- 将“8--10 帧”改写为“最多 (T_{\max}) 次、可提前停止”，并与当前 (T\leq8) 合同保持一致。

### 不应继续的

- 继续扩大 fixed-restoration 网络以追逐 NAFNet；
- 将 SLM nominal pixel count 当作有效自由度；
- 将十帧固定 codebook 称为 active sensing；
- 与 MEMS 争夺带宽或实时闭环；
- 以 calibration frame、数字重建图或 best-case 样本充当 causal science evidence；
- 在 oracle headroom 尚未建立时先写复杂 RL/Transformer 架构。

### 最终裁决

**Inference：**深度学习 fixed-only 路线的边际科研价值已经很低，但其负结果具有重要的认识价值：它指出了项目必须从“优化表示”移动到“优化测量”。真正值得未来三到五年积累的，不是另一个 restoration network，而是一套可复用的主动显微测量原则：

> 物理模型限定可行域，时空探针创造可辨识性，学习策略分配观测预算，风险门决定何时校正，未来原始帧给出最终裁决。

**Hypothesis：**若真实 O3 oracle 有稳定 headroom，active policy 在完整预算下优于 fixed/Fisher/PD 强基线，且 abstention 在 OOD/漂移条件下显著降低有害校正，那么“self-verifying spatiotemporal adaptive optics”具备 PhotoniX/LSA 级故事潜力。任何一项失败，都应按上面的 ladder 主动降级或终止主张。
