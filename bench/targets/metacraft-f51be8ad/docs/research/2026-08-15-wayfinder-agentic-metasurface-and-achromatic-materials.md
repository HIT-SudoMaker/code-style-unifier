---
record_type: research_record
date: 2026-08-15
status: research_finding
authority_level: none
current_capability: false
scope: wayfinder AFK pre-research; agentic metasurface competitors and visible continuous-achromatic material routes
source_policy: primary sources only
---

# Wayfinder 预研：三套 agentic metasurface 系统与可见光连续消色差材料路线

## 0. 结论先行

截至 2026-08-15，最近三项最直接的 agentic metasurface / metalens 工作准确标题为：

1. Yi Huang et al., **“A Self-Evolving Agentic Framework for Metasurface Inverse Design”**, *Laser & Photonics Reviews* e71739 (2026), DOI [10.1002/lpor.71739](https://doi.org/10.1002/lpor.71739)，预印本 [arXiv:2604.01480v2](https://arxiv.org/abs/2604.01480)。
2. Robert Lupoiu et al., **“A multi-agentic framework for real-time, autonomous freeform metasurface design”**, *Science Advances* 11, eadx8006 (2025), DOI [10.1126/sciadv.adx8006](https://doi.org/10.1126/sciadv.adx8006)，系统名为 **MetaChat**，预印本 [arXiv:2503.20479](https://arxiv.org/abs/2503.20479)。
3. Bei Wu et al., **“Agentic metasurface design with self-correcting language-model systems”**, [arXiv:2605.22647v2](https://arxiv.org/abs/2605.22647) (2026)，系统名为 **MetaDesigner**；截至本记录日期仍是预印本。

三者不是同一层级的对手：

- **Self-Evolving** 的闭环止于参数化单元胞/光栅的求解器代码与确定性物理判据；它没有完整金属透镜。
- **MetaChat** 的闭环到达二维自由形态超级像素、拼接孔径与角谱焦场，是三者中自由形态和速度最强的直接竞争者；但整片金属透镜没有独立 FDFD/实验闭环。
- **MetaDesigner** 已覆盖自然语言规划、CST 单元响应、可微角谱优化、512×512 RGB 器件及 LLM Verifier 纠错；但它使用三个离散频率和经验相位关系，没有连续波段群时延闭环、整器件 Maxwell 验证或制备。

**事实与推断的核心区分：** MetaChat 和 MetaDesigner 都做了多波长/RGB metalens，但这不等于可见光**连续消色差** metalens。前者优化 480/680 nm 或 450/540/670 nm，后者优化 480/560/640 THz 三点；连续消色差要求同一版图在完整带宽内同时逼近相位、群时延，宽带时还要控制群时延色散与更高阶项。该区别由连续消色差的一手论文明确给出，而不是术语偏好（[Chen et al., 2018](https://doi.org/10.1038/s41565-017-0034-6); [Presutti & Monticone, 2020](https://doi.org/10.1364/OPTICA.389404)）。

## 1. 范围、证据标记与本地库存

本文只使用正式论文、arXiv 原始预印本、出版社正式页面、作者官方仓库、官方数据/权重存储库和当前仓库文件。检索发现使用了 OpenAlex/Crossref，但没有用聚合站或综述支撑科学结论。

- **[事实]**：来源直接陈述、数据或代码可核验。
- **[推断]**：由多个事实推出的竞争或证据边界判断。
- **[未核实]**：当前官方页面不足以确定，不能写成不存在。

下载门禁下没有新增任何 PDF、Supporting Information 或附件。本地库存为：

- `reference/` 中有 Self-Evolving 的正式出版 PDF；
- `reference/metachat-main/` 是官方 MetaChat 仓库的五提交本地副本，远端为 [jonfanlab/metachat](https://github.com/jonfanlab/metachat)，本地最新提交日期为 2025-12-22；
- `.codex_tmp/2605.22647.pdf` 是此前研究已存在的 MetaDesigner v2 临时副本，不是 `reference/` 下的持久归档。

**下载待办：** 若按三篇竞争论文建立持久参考集，需在用户确认 SI/附件选择后处理 MetaChat 正式论文与 MetaDesigner v2；其中应被明确标记为“第三篇/第三份竞争论文 PDF”的是 **MetaDesigner，arXiv:2605.22647v2**。当前 `reference/` 严格意义上只有第一篇 PDF，因此不能写成另外两篇已经正式归档。

## 2. 七维对比总表

| 维度 | Self-Evolving | MetaChat | MetaDesigner |
|---|---|---|---|
| 任务范围 | 6 个主任务族 G1–G6 + 1 个辅助族；固定 50/15/50 train/val/test；参数化、已知可行的单元胞/光栅任务 | 101 道 photonics agent benchmark；设计 API 演示限制为 lens 与 deflector；二维自由形态、多目标、多波长超级像素 | 3 个长链案例：RGB metalens、六平面全彩 hologram、光电混合风格迁移 |
| 物理闭环 | LLM 写 `solve_inverse_design()` → TorchRDIT 可微 RCWA → 冻结判据评分 | FDFD 生成数据 → FiLM WaveY-Net 近场代理 → Stratton–Chu 远场 → Adam 优化 SDF 几何 → 超级像素拼接 → ASM 器件焦场 | CST 单元响应 → 经验跨频相位关系 → ASM → 反向传播优化相位图 → Verifier 审计报告/代码/结果 |
| 完整器件验证 | **无**。没有孔径、传播、焦点、成像或制备 | **部分器件级**。金属透镜有拼接布局与焦场；五超级像素 deflector 有独立 FDFD；未报告整片 metalens 独立 Maxwell 或制备 | **器件级传播但非完整物理闭环**。512×512 RGB 布局和焦场由 ASM 得到；未报告整器件 Maxwell、跨求解器或制备 |
| 材料/结构 | G1–G4 反射介质光栅；G5 等离激元反射；G6 PbTe/CaF₂ 矩形柱；Gaux TiO₂/SiO₂ 矩形柱 | 玻璃基底上的二维介质脊状自由形态超级像素；metalens 请求实例为 TiO₂；40 nm 最小特征 | TiO₂ 圆柱 / SiO₂；周期与半径固定 160/50 nm，高度 200–800 nm；512×512 单元 |
| 优化方式 | 代码代理生成梯度优化程序；TorchRDIT 提供正演与梯度；两层重试；外层元代理改写技能文件 | 可微 FiLM 代理 + Stratton–Chu；隐式 SDF/neuroparameterization；Adam 局部优化；多随机初始化/批量选择 | 相位目标经 ASM 建模，损失反向传播；单元响应来自 CST，另外两个频率由 480 THz 相位的经验线性关系估计 |
| 可靠性/证据治理 | 最强点是冻结、确定性 `gt_eval` 和逐条件余量；技能是显式可审计文本；但仅一个求解器、一个基础模型和固定小划分 | 代理模型有 30k 独立测试和 FiLM 消融；agent benchmark 有工具/材料代理消融；发布代码显示最终答题评分由 GPT-4o grader 完成，不是纯确定性验收 | 独立 Solver/Verifier，Verifier 可重新调用代理/工具交叉检查；发现频率映射、NA、衍射极限和报告一致性错误；但没有冻结的机器可判定验收、重复运行或架构消融 |
| 代码/数据/权重 | MIT 代码公开；核心 runtime、确定性 evaluator、IID split、一个配置；完整论文实验、OOD 数据/轨迹和绘图不公开 | 代码、AIM、WaveY-Net 训练/推理、web app 公开；训练/验证数据公开；权重在 Zenodo | [未核实] 预印本及 arXiv 页面未给官方代码、数据、权重或运行轨迹链接；精确标题与作者检索也未定位到作者标记仓库 |

表中事实来源：[Self-Evolving 全文](https://arxiv.org/html/2604.01480) 与 [官方仓库](https://github.com/yi-huang-1/evo-metaoptics)；[MetaChat 全文](https://arxiv.org/html/2503.20479)、[官方仓库](https://github.com/jonfanlab/metachat)、[数据](https://purl.stanford.edu/dq123fg9049) 与 [权重](https://doi.org/10.5281/zenodo.15802727)；[MetaDesigner v2](https://arxiv.org/abs/2605.22647)。

## 3. Self-Evolving：真正证明的是“技能演化改善单元胞程序生成”

### 3.1 任务与物理闭环

**[事实]** 基准包含 G1–G6 和 Gaux 七个参数化任务族。作者刻意选择有可达最优解的低维参数化，而不是开放式自由形态拓扑优化，使成功率主要测代理能否正确使用求解器。每种协议采用固定 50/15/50 划分；Claude Sonnet 4.6 同时作为代码代理和元代理，演化四轮（[论文 §3.1](https://arxiv.org/html/2604.01480)）。

**[事实]** G1–G4 为不同条件的反射介质光栅，G5 为等离激元反射，G6 为 5.2 μm 下 PbTe/CaF₂ 矩形柱的透射率和相位目标，Gaux 为 480 nm 下 TiO₂/SiO₂ 矩形柱的透射率和相位目标。每个任务只要求局部响应满足冻结阈值；没有把单元排成完整孔径再传播到焦场（[论文 Appendix S2–S3](https://arxiv.org/html/2604.01480)）。

闭环是：自然语言任务 + 结构化 `gt_eval` → 代码代理写优化函数 → TorchRDIT 可微 RCWA 执行 → 确定性 evaluator 返回执行成功、逐条件余量和物理成败 → 元代理依据训练/验证反馈改写显式技能。求解器、评价器和模型权重固定（[论文方法](https://arxiv.org/html/2604.01480)）。

### 3.2 可靠性与结论边界

**[事实]** Same-type SG 从 38% 提升到 74%，CPF 从 0.510 到 0.870，平均尝试从 4.10 降到 2.30。New-type-A 为 92%→90%，有一例挽救、两例回退；New-type-B 为 20%→90%，但验证族 G4 与测试族同属反射介质光栅，因此作者明确称其为从 validation 获得的类内惯例，而非完全未见类别迁移。作者同时承认一个求解器栈、一个 benchmark 设计、一个基础模型，广泛跨类泛化尚未建立（[结果与讨论](https://arxiv.org/html/2604.01480)）。

**[推断]** 它的“证据治理”在三者中最接近可审计科研：成功由固定物理模拟和冻结判据决定，技能文件可版本化检查。但它治理的是**单元胞程序结果**，没有材料来源、同一版图全波段响应、孔径焦场、制备误差和跨求解器一致性。

### 3.3 开源状态（2026-08-15）

**[事实]** [官方仓库](https://github.com/yi-huang-1/evo-metaoptics) 当前公开核心 MCE runtime、逆设计环境、确定性 `gt_eval`、一个完整 IID 50/15/50 split 和示例配置；README 明确说 plotting、publication reports 和完整实验套件不在公开范围，只公开 IID 数据。官方页面显示 3 次提交，许可证为 MIT。

**[推断]** 核心机制可以审阅和重跑 IID 示例，但论文全部 OOD 主结果不能仅凭公开包端到端复现。

## 4. MetaChat：速度和自由形态最强，但代理域与整器件证据要分开

### 4.1 任务、材料与优化

**[事实]** AIM Design Agent、Materials Expert Agent、工具和用户通过 Agentic Iterative Monologue 交互。101 道 Stanford nanophotonics benchmark 分为直接计算、多步计算、材料检索、直接函数调用和多步函数调用；使用 GPT-4o 时，AIM + tools + Materials Agent 得到 81%，相应消融为 71%、75% 和 78%（[论文 agent benchmark](https://arxiv.org/html/2503.20479)）。

**[事实]** FiLM WaveY-Net 训练于 270,000 个二维 FDFD 样本，结构为玻璃基底上的介质脊状超级像素，波长 400–700 nm，并有 30,000 个测试样本。测试平均 normalized MAE 约 0.06；随波长由 0.098 降到 0.043；90% 样本误差低于 0.10（[论文 surrogate evaluation](https://arxiv.org/html/2503.20479)）。

**[事实]** 几何由神经 SDF/neuroparameterization 表示，FiLM 代理输出磁近场，Ampère 定律恢复电场，Stratton–Chu 形成远场；全部可微并用 Adam 优化。优化器是局部的、依赖初始化，因此批量优化多个初值后选择最佳。40 nm 最小特征由几何表示约束（[论文优化方法](https://arxiv.org/html/2503.20479)）。

### 4.2 完整器件程度

**[事实]** 双波长实例是 180 μm 宽 TiO₂ metalens，目标 680/480 nm、焦距 100 μm，含 100 个 1.8 μm 超级像素。300,000 次代理仿真用 8 GPU 在 10 min 完成，两个焦点主瓣占各自总远场能量的 57.1% 和 49.7%。RGB 实例为 200 μm、111 个超级像素，目标 450/540/670 nm（[论文 metalens results](https://arxiv.org/html/2503.20479)）。

**[事实]** 每个超级像素独立优化后拼接，整片 metalens 用角谱法形成远场。论文对五超级像素 deflector 给出独立 FDFD 近场验证，但 metalens 图中没有等价的整片 FDFD 或实验制备；讨论把机器人实验验证列为未来可接入方向（[论文 Fig. 6 与 Discussion](https://arxiv.org/html/2503.20479)）。

**[推断]** 这已经是器件级设计，不应贬为“只会聊天”；但它仍是**域内代理散射 + 分块独立优化 + 拼接传播**的证据。超级像素内部考虑邻近耦合，不等于自动证明超级像素之间的全部耦合、代理域外几何、三维结构或实际制备。

### 4.3 可靠性与开源

**[事实]** 物理代理有大规模测试集和模型结构消融，这是 MetaChat 最扎实的可靠性证据。另一方面，官方代码的 [`grader.py`](https://github.com/jonfanlab/metachat/blob/main/metachat-aim/experiments/eval_framework/grader.py) 和 [`eval_runner.py`](https://github.com/jonfanlab/metachat/blob/main/metachat-aim/experiments/runners/eval_runner.py) 显示 agent benchmark 的答案/方法匹配由 temperature 0 的 GPT-4o grader 判断，再对提取数值做 2% 确定性容差；所以 81% 不能等同于完全机器确定性的物理验收。

**[事实]** [官方仓库](https://github.com/jonfanlab/metachat) 当前包含 AIM、FiLM WaveY-Net 训练/推理、web app；本地官方副本与在线页面均为 5 次提交。训练和验证数据发布于 [Stanford Digital Repository](https://purl.stanford.edu/dq123fg9049)，`best_model.pt` 发布于 Zenodo record [15802727](https://doi.org/10.5281/zenodo.15802727)，该记录题为 *Data and Code for MetaChat*。

## 5. MetaDesigner：系统链完整，物理验收仍主要由 LLM Verifier 和近似模型承担

### 5.1 系统与任务

**[事实]** 系统由 Solver、Verifier、Researcher、Optimizer、Programmer 五个代理组成；前四个使用 DeepSeek-V3，Programmer 使用 Claude Sonnet 4.5。工具包括 CST、电磁/衍射计算、arXiv/Tavily 检索、RAG、虚拟文件系统和 PostgreSQL 持久记忆。Solver 与 Verifier 共享轨迹，其他代理只返回汇总结论（[arXiv v2](https://arxiv.org/abs/2605.22647)）。

**[事实]** 三个案例分别需要 74、136 和 90 个 reasoning steps：RGB metalens；六平面全彩 hologram，masked-region 平均 SSIM 0.97；光电混合神经网络风格迁移。Verifier 抓到频率—颜色映射、NA、超越衍射极限、通道次序、参数量和损失函数说明等错误（[arXiv abstract](https://arxiv.org/abs/2605.22647)）。

### 5.2 RGB metalens 的物理闭环

**[事实]** 目标为 512×512 个单元，周期 160 nm，在离器件 80 μm 平面把 480、560、640 THz（约 625、536、469 nm）聚焦到三个位置。单元是 SiO₂ 上 TiO₂ 圆柱，半径 50 nm 固定，高度 200–800 nm 可变。CST 计算单元散射；以 480 THz 相位为参考拟合跨频经验线性关系，Optimizer 再用 ASM 和强度损失反向传播优化相位分布。报告 16 min 14 s、1.89M tokens 和三频平均聚焦效率 20%（[arXiv v2](https://arxiv.org/abs/2605.22647)）。

**[推断]** 该案例证明代理能组合一个长链并纠正报告/推理错误，但没有证明：

- 连续 469–625 nm 波段消色差；
- 经验相位关系在未采样波长的群时延/GDD 准确；
- 512×512 实际高度版图的整器件 Maxwell 响应；
- 制备公差或实验器件性能。

作者也明确把更高保真仿真、实验反馈、制备约束和领域专用验证标准列为未来工作，并称 MetaDesigner 不是自主光学设计的最终答案（[arXiv v2 Discussion](https://arxiv.org/abs/2605.22647)）。

### 5.3 可靠性与开源

**[事实]** Verifier 会检查轨迹、代码、数值结果和报告，并可重新调用代理/工具；虚拟文件系统带冲突检查，降低误覆盖风险。这比单纯让 Solver 自我反思强。

**[推断]** Verifier 仍是模型驱动判断，不是冻结 schema + 确定性物理 evaluator。论文以三个精选长链案例展示纠错，没有报告重复运行方差、Verifier 消融、错误接受率或独立审计基准。因此“发现过错误”不能推出“不会放过未观察的错误”。

**[未核实]** 截至 2026-08-15，arXiv v2 正文、arXiv record 和精确标题/作者的官方检索没有给出代码、数据、权重或完整 run traces。应表述为“当前未定位到作者公开链接”，不能绝对写成“没有代码”。

## 6. 为什么连续消色差必须同时覆盖 phase 与 group delay

理想焦距固定为 $F$ 的金属透镜需要

$$
\phi(r,\omega)=-\frac{\omega}{c}\left(\sqrt{r^2+F^2}-F\right)+C(\omega),
$$

其中 $C(\omega)$ 是孔径范围内共享的谱相位 gauge，不改变聚焦。对频率展开：

$$
\phi(r,\omega)=\phi(r,\omega_0)+\tau_g(r)\Delta\omega+\frac{1}{2}\mathrm{GDD}(r)\Delta\omega^2+\cdots.
$$

因此：

- 参考频率相位形成球面波前；
- $\tau_g=\partial\phi/\partial\omega$ 使孔径不同位置的波包同时到达焦点；
- GDD 和更高阶项控制宽带内剩余波包畸变。

边缘与中心所需相对群时延量级为

$$
\Delta\tau_{\mathrm{req}}=\frac{\sqrt{R^2+F^2}-F}{c},
$$

所以口径 $R$ 或 NA 增大时，所需延迟跨度上升。任何线性时不变薄器件又受 delay–bandwidth product 限制，因此材料/几何不是只要“有 2π 相位”就能任意增大带宽、口径与 NA（[Chen et al., 2018](https://doi.org/10.1038/s41565-017-0034-6); [Presutti & Monticone, 2020](https://doi.org/10.1364/OPTICA.389404)）。

## 7. TiO₂ 纳米鳍/纳米柱为何适合

### 7.0 “适合”“匹配”和“唯一”的证据边界

**[事实]** TiO₂、GaN 和 SiN/Si₃N₄ 都已有可见光连续消色差器件的一手实验，因此现有证据不支持“TiO₂ 是唯一适合材料”。Chen 系列论文支持的是其**特定 ALD TiO₂、600 nm 高一/双鳍、玻璃基底与 PB 转换通道**能够形成有用的 phase–GD(/GDD) 库；它没有证明任意 TiO₂ 薄膜、圆柱、厚度或工艺都匹配任意 lens brief（[Chen et al., 2018](https://doi.org/10.1038/s41565-017-0034-6); [Chen et al., 2019](https://doi.org/10.1038/s41467-019-08305-y)）。

**[推断]** 本项目中只应把“matching TiO₂ route”定义为：在**本地材料谱、具体 period/height/geometry、最小特征与 solver binding**下，合格库同时覆盖 brief 所需 phase、GD、带内残差和功率门槛。材料名相同、折射率大或文献中曾成功，都只能作为候选依据，不能替代本地匹配证据。若该库不足，正确结果是 realization-specific refusal，而不是否定 TiO₂ 材料本身。

### 7.1 波导真时延，而不只是单点共振相位

**[事实]** Chen et al. 把 TiO₂ nanofin 视作截断波导：

$$
\phi_{\mathrm{wg}}\approx\frac{\omega n_{\mathrm{eff}}(\omega)h}{c},\qquad
\tau_g\approx\frac{h}{c}\left(n_{\mathrm{eff}}+\omega\frac{\partial n_{\mathrm{eff}}}{\partial\omega}\right)=\frac{h n_g}{c}.
$$

改变长度、宽度、鳍间距或材料会改变 $n_{\mathrm{eff}}$ 和 $n_g$；固定高度下仍能获得多种相位斜率。论文用一根或两根耦合 TiO₂ 鳍增加几何自由度，600 nm 高、400 nm 方形单元、60 nm 鳍间隙，设计带宽 120 nm（[作者组正式 PDF 页面](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf); [DOI](https://doi.org/10.1038/s41565-017-0034-6)）。

**[事实]** 高折射率和可见光低损耗使亚波长高度内能积累较大传播相位并保持透射/转换；论文用 eigenmode 与 FDTD 对照验证短波导近似。这里“适合”是材料光学性质与可制造高纵横比结构的组合，不是只由化学式决定。

### 7.2 PB 相位与色散可近似解耦

对圆偏振转换通道，nanofin 的交叉偏振项含

$$
(t_L-t_S)e^{i2\alpha}.
$$

几何/本征传输 $t_L-t_S$ 控制转换效率和频谱斜率，旋转角 $\alpha$ 加入近似与频率无关的 $2\alpha$ 参考相位，因此不改变 GD/GDD。几何先满足群时延，旋转再补相位，比一个几何同时硬凑 phase 和 GD 更有自由度（[Chen et al., 2018](https://doi.org/10.1038/s41565-017-0034-6)）。

**[事实]** 2019 年工作又利用复合各向异性 TiO₂ nanofin 的多几何参数以及旋转 90° 提供的 $\pi$ 相位而不改变 GD/GDD，建立更密的 phase–GD–GDD 库，实现 460–700 nm、NA 0.2、直径 26.4 μm、偏振不敏感、近衍射极限的制备器件（[Chen et al., 2019](https://doi.org/10.1038/s41467-019-08305-y)）。

### 7.3 一手实验证明它不是纸面机制

**[事实]** 2018 年器件按 120 nm 带宽设计，但因焦移相对景深很小，在 470–670 nm 仍保持近衍射极限焦斑；NA 0.2 器件做了焦距扫描，NA 0.02、220 μm 器件做了白光成像。作者还对 6 μm、NA 0.6 的小型整片透镜做了 FDTD 检查（[Chen et al., 2018](https://doi.org/10.1038/s41565-017-0034-6)）。

## 8. TiO₂ 何时并不适合

### 8.1 所需群时延超过可制造库

**[事实]** 600 nm 高 TiO₂ nanofin 的可用 GD 范围约 5 fs；2019 论文明确把小口径归因于高度/群速度及制造约束。增大高度可提高 GD，但也提高纵横比和邻近耦合。2018 论文举出约 4.5 μm 高结构可达约 37 fs，说明“更多延迟”不是免费参数（[Chen et al., 2019](https://doi.org/10.1038/s41467-019-08305-y); [Chen et al., 2018](https://doi.org/10.1038/s41565-017-0034-6)）。

**[推断]** 如果给定 $R,F,$ 带宽要求的 $\Delta\tau_{\mathrm{req}}$ 超出实际材料、最小特征和高度限定下的库，TiO₂ 单层单鳍不是“优化得不够”，而是该 realization 应拒绝；应增加高度、耦合单元、层数或更换体系，而不是偷偷缩小孔径/NA/带宽。

### 8.2 phase、GD、GDD 与效率并非任意独立

**[事实]** 2018 器件在约 500 nm 的实测效率约 20%，理论约 50%；作者归因于制备误差和周期单元模型忽略不同相邻元素耦合，并指出为了扩大 GD 范围选择了一些低转换效率元素。2019 论文也明确观察到宽色散覆盖会纳入低转换效率结构（[Chen et al., 2018](https://doi.org/10.1038/s41565-017-0034-6); [Chen et al., 2019](https://doi.org/10.1038/s41467-019-08305-y)）。

**[推断]** 因此以“相位/GD 最近邻”选单元但不把复振幅、转换/泄漏功率和 holdout 波长纳入损失，会产生看似消色差但低效率或带内失真的透镜。

### 8.3 单一等方柱与 PB 鳍不是同一种自由度

**[事实]** 圆柱旋转不产生可用 PB 相位；它只能依靠直径/高度/复合截面改变传播相位与色散。各向异性鳍可用旋转补相位，但通常要求圆偏振转换通道；要对任意入射偏振工作，需像 2019 工作那样用成组各向异性结构恢复偏振对称响应（[Chen et al., 2019](https://doi.org/10.1038/s41467-019-08305-y)）。

**[推断]** 对要求偏振不敏感、非 PB 或极简单柱的 brief，TiO₂ 材料仍可能合适，但“相位与群时延解耦”不能直接继承，必须重新证明库覆盖。

### 8.4 工艺/集成目标可能优先于最高折射率

**[事实]** 2025 年 Si₃N₄ 集成论文指出，其目标流程中传统 TiO₂/GaN 膜制备与商业 CMOS 顶层集成存在高温兼容问题，而 200 °C PECVD Si₃N₄ 可直接面向封装传感器。该结论针对论文比较的工艺路线，不应扩展成“所有 ALD TiO₂ 都必须高温”（[Zhang et al., 2025](https://doi.org/10.1038/s41467-025-62539-7)）。

## 9. GaN 与 SiN/Si₃N₄ 替代路线的一手证据

| 材料路线 | 一手演示 | 为什么可替代 TiO₂ | 明确代价/边界 |
|---|---|---|---|
| **GaN integrated-resonant unit elements** | 400–660 nm transmissive continuous achromat，NA 0.106，平均效率约 40%，全彩成像 | 可见光透明、高折射率；PB 基相位与 integrated resonance 补偿频谱相位；实验证据覆盖整个可见带 | 不是简单圆柱库：使用 GaN 实/反结构 IRUE、GaN/sapphire、细小 hexagonal lattice；结构/制造复杂，强共振设计需严控效率与带宽 |
| **单层薄 SiN nanopost（2019）** | 430–780 nm；60×60 metalens array；单层 400 nm；平均效率 47%；白光 integral imaging | 低损耗、偏振不敏感、CMOS 兼容；通过零 effective material dispersion 和不同 $n_{eff}$ 实现近线性谱相位 | $d\Delta n_{eff}$ 有限；论文示例说明给定 0.8 μm 厚度与 $n=2$ 时可用 OPD 限制口径/焦距；当波长接近周期，透射骤降 |
| **SiN antenna + dispersion-matched SiN/SU8 layers（2024）** | 400–700 nm；口径 16/66/200/400 μm，NA 0.27/0.11/0.04/0.02；大多 Strehl >0.9；白光成像 | 上层纳米天线做细 GD，底部材料对用厚度差做粗 GD；突破单纳米天线 GD 点云太窄的问题 | 多材料、多层和厚度版图；依赖 SiN 与 SU8 跨带折射率色散匹配；工艺与平坦化显著更复杂 |
| **高纵横比 Si₃N₄（2025）** | 460–650 nm；h=1300 nm，最小特征 40 nm，最高演示纵横比 43.33；NA 0.155；平均效率 80.39%；集成 CMOS sensor | 低温 PECVD、近零消光、CMOS 兼容；用高度补偿较低折射率造成的 GD 不足 | 低折射率意味着普通 10–17 纵横比库不足；1300 nm 高柱仍限制尺寸与 NA；<20 nm 脊发生明显倒塌；GDD 也随高度增加 |

来源：[Wang et al., 2018](https://doi.org/10.1038/s41565-017-0052-4) 与其 [官方 Supplementary Information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf)；[Fan et al., 2019](https://doi.org/10.1038/s41377-019-0178-2)；[Chang et al., 2024](https://doi.org/10.1038/s41467-024-53701-8)；[Zhang et al., 2025](https://doi.org/10.1038/s41467-025-62539-7)。本轮未下载该 SI；结构细节来自此前已核验记录，链接仅作待确认访问入口。

### 9.1 GaN 的结论

**[事实]** Wang et al. 使用 GaN-based integrated-resonant unit elements，在透射下使焦距从 400 到 660 nm 基本不变，NA 0.106 器件全带平均效率约 40%，并演示全彩成像（[正式页面](https://www.nature.com/articles/s41565-017-0052-4)）。其方法继承 2017 年“PB 基相位 + 与波长相关的补偿相位”原则（[Wang et al., 2017](https://doi.org/10.1038/s41467-017-00166-7)）。

**[推断]** GaN 是 TiO₂ 的真实可见光替代，不是较低性能的备选；但如果当前 solver/template 只有方格单矩形柱，则迁移成本高于 Chen 型 TiO₂ 路线，因为被实验验证的是具体 IRUE family，而不是任意 GaN 柱。

### 9.2 SiN/Si₃N₄ 的结论

**[事实]** 2019 单层 SiN 方案用 400 nm 厚、320 nm hexagonal lattice 的带孔/对称 nanopost，获得 430–780 nm 的有效消色差折射率分布、36–55% 测量效率和 47% 平均值。论文也直接指出有效 OPD $d\Delta n_{eff}$ 限制 lens radius 和 focal length（[Fan et al., 2019](https://doi.org/10.1038/s41377-019-0178-2)）。

**[事实]** 2024 方案说明普通 600 nm 高 SiN antenna 虽有 2π phase，GD 点云仍太窄；加入色散匹配 SiN/SU8 底层后才能粗细两级扩展 GD，并完成 400–700 nm 的 400 μm 口径实验（[Chang et al., 2024](https://doi.org/10.1038/s41467-024-53701-8)）。

**[事实]** 2025 方案走另一条路：把 Si₃N₄ 高度提高到 1300 nm，以纵横比 43.33 增加 GD；材料在 460–650 nm 折射率 >2.02、消光近零，实验平均效率 80.39%，还能低温集成到商业 sensor（[Zhang et al., 2025](https://doi.org/10.1038/s41467-025-62539-7)）。

**[推断]** SiN 的首要优势是工艺、低损耗、偏振对称和集成，而不是单位厚度群时延。若制造能力不能支撑超高纵横比或多层色散匹配，较低折射率反而让 phase–GD 库更窄。它更适合“CMOS integration 是硬约束”的 brief，不应仅因材料便宜就默认优于 TiO₂。

## 10. 对 Wayfinder / MetaCraft 的可执行研究判断

### 10.1 可形成的差异化

**[推断]** 三篇竞争工作没有关闭以下组合：

> 自然语言连续消色差 brief → 真实材料谱 → phase/GD/GDD 可行性 → 同一固定几何在 design + blind-holdout wavelengths 的复 Jones 响应 → 孔径 → 每波长焦场 → 拒绝或结果 → 全链精确回放。

Self-Evolving 提供可借鉴的确定性 evaluator 和显式技能演化；MetaChat 提供必须正视的自由形态/速度基线；MetaDesigner 提供长链 Verifier 基线。MetaCraft 的可发表差异不是多加 agent，而是把以下失败变成类型化、可重放的科学结论：

- phase 有 2π 但 GD 不足；
- GD 覆盖足但转换/透射低；
- design wavelengths 合格但 holdout 失真；
- 单元周期模型合格但整器件/邻近耦合失败；
- 代理或 Verifier 宣称成功，但证据链缺了一环。

### 10.2 材料路线选择建议

1. **首个可证伪 slice：TiO₂ 单矩形鳍。** 与当前方格、单层、Jones/PB 和 Lumerical 结构最接近；先测 phase–GD–power–holdout 覆盖，不预设成功。
2. **第一次升级：一/双耦合 TiO₂ 鳍。** 只有单鳍库被证据拒绝后才增加 compound geometry；这是 Chen 2018 真正使用的自由度。
3. **GaN 作为独立 benchmark，而非材料替换开关。** 需要独立 GaN/sapphire、IRUE family、格点和制造约束，不能把 TiO₂ 几何换材料名后沿用结论。
4. **SiN 分两条实验。** 低温 CMOS 集成路线用高纵横比 Si₃N₄；大口径全可见 GD 路线用 dispersion-matched layers。两者不应合并成一个模糊的“SiN 支持”。
5. **预先计算拒绝边界。** 用 $\Delta\tau_{\mathrm{req}}$ 与库的 admissible GD span、效率和 holdout residual 比较，再允许 aperture assignment。

### 10.3 与三篇对手的最小公平基线

- Self-Evolving-like：相同模型、相同 solver budget、固定技能 vs 演化技能，使用冻结单元胞判据；
- MetaChat-like：快速 surrogate/freeform proposal，但将 surrogate 域、超级像素拼接和整器件验证分层；
- MetaDesigner-like：Solver + LLM Verifier；另加 deterministic evidence validator，测量 Verifier 的漏报与误报；
- agent-free：确定性库筛选/分配；证明收益来自 agent，而非更多 solver calls。

主指标必须同时含物理成功、错误接受率、正确拒绝率、重放一致性、solver calls、墙钟/token 成本；仅报告“成功案例的推理步数”不足以证明可靠性。

## 11. 检索与访问限制

- Academic-search MCP 未挂载；按技能规定使用仓库内 OpenAlex/Crossref 脚本作发现和 BibTeX 元数据补全，所有正文论证回到一手来源。
- GitHub API 匿名请求返回 403；仓库状态改由官方 GitHub 页面与本地官方 MetaChat clone 交叉核对。
- Zenodo网页曾返回 429，但官方 Zenodo API 成功返回 record 15802727 的题名、DOI 和 2025-07-04 创建日期。
- Stanford 数据页面一次超时；数据存在性同时由 MetaChat 官方仓库 Data availability 指向，未在本轮下载数据。
- MetaDesigner 仍可能在本记录之后发布代码、数据或正式论文，投稿定位前必须重查。

## 12. 引用与一手来源

去重 BibTeX：[`2026-08-15-wayfinder-agentic-metasurface-and-achromatic-materials.bib`](2026-08-15-wayfinder-agentic-metasurface-and-achromatic-materials.bib)。去重主键为标准化 DOI；MetaDesigner 以 arXiv ID 唯一化。

### Agentic metasurface

- [Huang et al., 2026, DOI](https://doi.org/10.1002/lpor.71739); [arXiv full text](https://arxiv.org/html/2604.01480); [official code](https://github.com/yi-huang-1/evo-metaoptics).
- [Lupoiu et al., 2025, DOI](https://doi.org/10.1126/sciadv.adx8006); [arXiv full text](https://arxiv.org/html/2503.20479); [official code](https://github.com/jonfanlab/metachat); [official data](https://purl.stanford.edu/dq123fg9049); [official weights](https://doi.org/10.5281/zenodo.15802727).
- [Wu et al., 2026, arXiv:2605.22647v2](https://arxiv.org/abs/2605.22647).

### Continuous-achromatic physics and materials

- [Chen et al., 2018, TiO₂ PB/dispersion metalens](https://doi.org/10.1038/s41565-017-0034-6); [author-group published PDF page](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf); [arXiv precursor](https://arxiv.org/abs/1711.09343).
- [Chen et al., 2019, polarization-insensitive TiO₂ nanofins](https://doi.org/10.1038/s41467-019-08305-y).
- [Wang et al., 2017, broadband achromatic phase-compensation principle](https://doi.org/10.1038/s41467-017-00166-7).
- [Wang et al., 2018, visible GaN achromatic metalens](https://doi.org/10.1038/s41565-017-0052-4).
- [Fan et al., 2019, single-layer visible SiN achromatic metalens array](https://doi.org/10.1038/s41377-019-0178-2).
- [Chang et al., 2024, SiN/SU8 dispersion-matched layers](https://doi.org/10.1038/s41467-024-53701-8).
- [Zhang et al., 2025, high-aspect-ratio Si₃N₄ on-chip achromatic arrays](https://doi.org/10.1038/s41467-025-62539-7).
- [Shrestha et al., 2018, phase-dispersion-space library and tradeoffs](https://doi.org/10.1038/s41377-018-0078-x).
- [Presutti & Monticone, 2020, delay-bandwidth limits](https://doi.org/10.1364/OPTICA.389404); [author preprint](https://arxiv.org/abs/2001.10899).
