# 干涉式自适应 Restoration：公式主线、创新边界与仿真判据

- 日期：2026-08-12
- 状态：研究设计草案；不代表实验结论
- 范围：类迈克尔逊双臂相干系统、Fourier-plane phase-only SLM、四步相移、Zernike/器件原生模态、有限帧主动测量与后续物理校正

## 1. 结论先行

本项目不应再把中心贡献写成“用 8--10 帧四步相移和 Zernike 估计像差”。四步相移、Zernike 展开、自参考干涉波前传感、SLM 相位共轭校正、Fisher 探针设计和单帧学习型波前感知都已有强先例。帧数较少是工程属性，不是足以支撑旗舰论文的物理新意。

更有潜力的中心命题是：

> **同一参考臂的相干偏置，既使未知校正动作可被干涉观测，又把 phase-only SLM 的逐频率可达集合从原点圆变为平移圆；因此参考臂、探针序列与最终校正不能分别设计，而应围绕未来科学观测的动作效用联合设计。**

一句更适合论文开场的表达是：

> The same coherent bias that makes a phase-only action observable also makes its optical transfer expressive.

中文可写为：

> 同一束参考光，既照亮应该选择哪个校正动作，也打开相位型器件能够实现的复传递函数可达域。

这条“传感--执行对偶性”可以把现有 Fixed Measurement 的可行域证据、四步干涉读出、Zernike/器件模态估计、主动探针和未来物理帧串成一条公式链。真正需要证明的不是“网络能回归 Zernike”，而是：联合设计是否在相同 photons、camera reads、SLM states、settling、compute 和 wall time 下，比经典四步 PSI、固定/Fisher codebook、传统相位共轭和单帧学习型 WFS 获得更小的**未来动作 regret**与更低的**有害校正率**。

同时，当前研究文档存在一个必须先裁决的物理分叉：若最终科学帧令参考臂关闭（`R=0`），参考臂就不再参与最终复传递函数合成，主张只能是“干涉感知后进行传统 phase-only AO”；若要保留“参考臂扩展可达域并进行 task-aware transfer control”这一更强主张，最终的因果后续科学帧应保持参考臂开启，`R=0` 应降为消融和安全对照。

## 2. 不能再混淆的三个系统

### 2.1 Fixed Measurement 历史系统

当前 `experiments/restoration/frontend.py` 的真实计算路径是双臂相干叠加：参考臂近似传递输入场，处理臂执行 4f Fourier-plane phase filtering，探测器测量两臂复场之和的强度。这不是普通的单臂相干强度成像。

Fixed 结果证明了两件事：

1. 受限 phase-only 光学变换具有显著可学习性；
2. 当输入已经是探测后的 degraded intensity 并被重新编码时，光学前端没有自动获得强数字后端不可见的新信息。

因此 Fixed 应提供可行域、器件先验、固定掩模强基线和“干预过晚”的边界，不应被丢弃，也不应被冒充为原生未知像差自适应实验。

### 2.2 目标原生系统

目标系统应在科学图像形成之前，对未知样品场和未知系统像差施加已知时空探针，依据实际相机读数选择 delivered correction，再采集因果上更晚的原始科学帧。

### 2.3 当前 Adaptive 仿真原型

此前 `adaptive_measurement/coherent_bench.py` 只实现了单臂 pupil propagation，因而不能支撑四步相移、参考臂相位或 translated-circle 可达域。该阻断项现已修复：Fixed 与 Adaptive 都通过公共 `optical_bench.propagate_interferometric_bench` 形成参考臂与处理臂的相干叠加强度，并共享 638 nm 波长、100 mm 焦距、Fourier 面采样、SLM2 有效口径和分束参数；Adaptive 主科学帧默认保留参考臂。现有 oracle 仍只属于 actuator-headroom sanity check，不能替代 measurement-only Adaptive 证据。

## 3. 第一层公式：双臂干涉物理

令未知样品/入射复场为 (x(\mathbf r))，频谱为 (X(\mathbf k))。在 path-matched、窄带、标量、局部 shift-invariant 的理想起点下，参考臂与处理臂可写为

\[
E_r(\mathbf r)
=
\alpha e^{i\delta_0}x(\mathbf r),
\]

\[
E_{p,t}(\mathbf r)
=
\beta\,\mathcal F^{-1}\!\left\{
P(\mathbf k)
e^{i[\phi_{\mathrm{ab}}(\mathbf k)+d_t(\mathbf k)+c_t]}
X(\mathbf k)
\right\}.
\]

其中：

- (\delta_0) 是预设参考臂相位；
- (\phi_{\mathrm{ab}}) 是未知像差；
- (d_t) 是第 (t) 帧的空间探针；
- (c_t) 是由 phase SLM 施加的全局 piston；
- (P) 是 pupil/support 和固定幅度响应；
- (\alpha,\beta) 包含两臂的复增益。

相机读数为

\[
Y_t(\mathbf r)
\sim
p\!\left(y\mid
\mu_t(\mathbf r),\eta_t
\right),
\qquad
\mu_t
=
\left|E_r+E_{p,t}\right|^2+b_t,
\]

也即

\[
\mu_t-b_t
=
|E_r|^2+|E_{p,t}|^2
+2\operatorname{Re}\!\left(E_r^*E_{p,t}\right).
\]

这里的计算资源是交叉项，而不仅是“相干照明”。全局 SLM piston 会改变处理臂相对于参考臂的有效相位，因此机械延迟线可以预设并保持不动；但每一个 piston 状态仍必须计入 SLM 切换和 settling 预算。

## 4. 第二层公式：phase-only 可达域与校正能力

在理想 path-matched 频域模型下，合成后的复场传递函数是

\[
G_t(\mathbf k)
=
c(\mathbf k)
+
\rho(\mathbf k)
e^{i[\phi_{\mathrm{ab}}(\mathbf k)+u_t(\mathbf k)]},
\]

其中

\[
c(\mathbf k)=\alpha e^{i\delta_0},
\qquad
\rho(\mathbf k)=|\beta|P(\mathbf k),
\]

并把 (\beta) 的固定相位吸收到 (u_t) 中。对每个空间频率，理想连续 phase-only 动作的可达集合是

\[
\mathcal A_{\mathbf k}
=
\left\{
c(\mathbf k)+\rho(\mathbf k)e^{i\theta}:\theta\in[0,2\pi)
\right\}.
\]

它是复平面中以 (c) 为圆心、以 (\rho) 为半径的平移圆，而不是任意复平面。相应的可达幅度范围为

\[
\big||c|-\rho\big|
\le |G_t|\le
|c|+\rho.
\]

这条几何关系给出了原有推导中“为什么 phase-only 加参考臂能够同时改变有效幅度与相位”的干净物理解释。

### 4.1 纯像差补偿是可证明的特例

若目标只是平坦化处理臂 pupil phase，在理想连续器件下取

\[
u_{\mathrm{pc}}(\mathbf k)
=
-\phi_{\mathrm{ab}}(\mathbf k)+\phi_0
\pmod{2\pi},
\]

则处理臂残余相位变为常数。这个公式证明理想系统具有 phase-conjugate correction 能力，但它不是项目的新意；经典 AO 已经长期采用该思想。

### 4.2 对 task-optimal 复传递函数的闭式投影

令 (G_\star(\mathbf k)) 是由任务、样品统计与噪声共同定义的目标复传递函数。对理想平移圆，逐频率最近点为

\[
u_\star(\mathbf k)
=
\arg\!\left[G_\star(\mathbf k)-c(\mathbf k)\right]
-\phi_{\mathrm{ab}}(\mathbf k)
\pmod{2\pi},
\]

\[
G_\star^{\mathrm{proj}}(\mathbf k)
=
c(\mathbf k)
+\rho(\mathbf k)
e^{i\arg[G_\star(\mathbf k)-c(\mathbf k)]}.
\]

不可避免的几何残差是

\[
\varepsilon_{\mathrm{proj}}(\mathbf k)
=
\left(
|G_\star(\mathbf k)-c(\mathbf k)|-\rho(\mathbf k)
\right)^2.
\]

积分后的加权投影损失为

\[
\mathcal L_{\mathrm{proj}}
=
\int_{\Omega}
w(\mathbf k)
\varepsilon_{\mathrm{proj}}(\mathbf k)
\,d\mathbf k.
\]

这比只写 (u=-\phi_{\mathrm{ab}}) 更强：它把“恢复到衍射极限”推广为“在真实硬件可达域中逼近任务最优传递函数”。Wiener/LMMSE 形式可作为一个理论 target，

\[
G_{\mathrm W}(\mathbf k)
=
\frac{H^*(\mathbf k)S_x(\mathbf k)}
{|H(\mathbf k)|^2S_x(\mathbf k)+S_n(\mathbf k)},
\]

但只有在线性场模型、统计量定义和任务一致时才成立，不能把它直接当作所有相机强度任务的最优解。

### 4.3 delivered-action 空间

真实动作满足

\[
u_t^{\mathrm{del}}
=
\mathcal D_h\!\left(u_t^{\mathrm{cmd}}\right),
\]

其中 (\mathcal D_h) 包括 wavelength/polarization-dependent LUT、量化、串扰、空间非均匀性、配准和漂移。论文必须分别报告：

- O1：理想任意复控制；
- O2：理想连续 phase-only 平移圆投影；
- O3：真实 delivered phase-only 动作。

O1--O2 是可达域损失，O2--O3 是器件交付损失。Adaptive 策略只能在 O3 留有稳健正 headroom 后开始。

## 5. 第三层公式：四步相移到底恢复了什么

对一个固定空间探针 (d_q)，只改变全局 piston

\[
c_m\in\left\{0,\frac{\pi}{2},\pi,\frac{3\pi}{2}\right\},
\]

并定义

\[
I_{q,m}
=
\left|E_r+e^{ic_m}E_{p,q}\right|^2.
\]

令 (\Gamma_q=E_r^*E_{p,q})，则在相移准确且四帧中的两臂场不漂移时，

\[
\operatorname{Re}\Gamma_q
=
\frac{I_{q,0}-I_{q,\pi}}{4},
\]

\[
\operatorname{Im}\Gamma_q
=
\frac{I_{q,3\pi/2}-I_{q,\pi/2}}{4},
\]

\[
\Gamma_q
=
\frac{I_{q,0}-I_{q,\pi}}{4}
+i\frac{I_{q,3\pi/2}-I_{q,\pi/2}}{4}.
\]

符号会随 piston 加在哪一臂和复指数约定改变，但物理量始终是复交叉项，而不是“直接得到理想像差”。若 (E_r) 的复场由独立标定已知且在有效像素上非零，可由 (E_{p,q}=\Gamma_q/E_r^*) 恢复处理臂场；若参考臂本身来自同一个未知样品场，四步法只给出自参考乘积，不能自动分离未知样品与 pupil aberration。

### 5.1 最容易犯的曝光错误

标准四步闭式公式要求同一组四帧中的 (E_{p,q}) 保持不变，只允许全局 piston 改变。若四帧分别加载四个不同 Zernike 空间探针，则不存在同一个 (\Gamma_q)，不能再套上述闭式公式。

因此：

- 两个空间探针各做完整四步 PSI = 8 个 calibration reads；后续 correction science 至少是第 9 个独立 read；
- 若总预算必须包含 8 个 reads，则“7 个 coded calibration reads + 1 个 held science read”不能称为标准四步 PSI，必须用统一的非线性 likelihood 解释；
- 可选择“4 帧基准 PSI + 3 帧条件化主动探针 + 1 帧 held science”，但后三帧的可辨识性依赖已校准模型，必须通过 Fisher/Jacobian 和盲测验证；
- 60 Hz 下 8、9、10 个裸帧周期分别约为 133、150、167 ms，尚未包含曝光、读出、传输、SLM settling、推理、上传和确认。

五步误差补偿 PSI 应作为 phase-step error 与漂移下的鲁棒性基线，而不是只与理想四步法比较。

### 5.2 为什么 quadrature 有用但不一定全局最优

若局部干涉相位误差为 (\Delta\phi)，在 quadrature 附近

\[
\cos\!\left(\frac{\pi}{2}+\Delta\phi\right)
\approx-\Delta\phi,
\]

而在同相点附近

\[
\cos(\Delta\phi)
\approx1-\frac{\Delta\phi^2}{2}.
\]

quadrature 提供一阶符号灵敏度；但参考臂相位与功率还会改变可达圆几何、动态范围、shot noise 和饱和风险。因此 (\delta_0=\pi/2) 是局部 sensing 起点，不应未经联合优化就宣称为整个系统最优工作点。

## 6. 第四层公式：Zernike 是基，不是传感器

把低阶未知像差写为

\[
\phi_{\mathrm{ab}}(\mathbf k)
=
\sum_{j=1}^{J}a_jZ_j(\mathbf k),
\]

把已知 delivered probe 写为

\[
d_t(\mathbf k)
=
\sum_{j=1}^{J}b_{tj}Z_j(\mathbf k),
\]

只是选择了参数坐标。实际器件还应比较 influence-function basis、PCA modes 和 device-native modes；若后者用更少参数表达 delivered correction，就不应为了图形熟悉度强行坚持 Zernike。

### 6.1 直接拟合 raw interferograms

在 Poisson 主导的起点下，未知状态可记为 (z=(a,O,h,\eta))，负对数似然为

\[
\mathcal L(z)
=
\sum_{t,\mathbf r}
\left[
\mu_t(\mathbf r;z)
-Y_t(\mathbf r)\log\mu_t(\mathbf r;z)
\right]
+\mathcal R(z).
\]

若同时存在显著 read noise，应采用 Poisson--Gaussian likelihood 或经标定的近似，而不是把所有噪声写成同方差 MSE。

对 Zernike 系数，处理臂场的一阶导数为

\[
\frac{\partial E_{p,t}}{\partial a_j}
=
i\beta\,\mathcal F^{-1}\!\left\{
PZ_j
e^{i(\phi_{\mathrm{ab}}+d_t+c_t)}X
\right\},
\]

相应的强度导数为

\[
\frac{\partial\mu_t}{\partial a_j}
=
2\operatorname{Re}\!\left[
(E_r+E_{p,t})^*
\frac{\partial E_{p,t}}{\partial a_j}
\right].
\]

Poisson Fisher 信息为

\[
F_{j\ell}
=
\sum_{t,\mathbf r}
\frac{1}{\mu_t(\mathbf r)}
\frac{\partial\mu_t}{\partial a_j}
\frac{\partial\mu_t}{\partial a_\ell}.
\]

未知样品、参考臂漂移、两臂功率、背景、配准和 delivery mismatch 都是 nuisance parameters。若把目标像差参数记为 (a)，nuisance 记为 (\eta)，有效信息应使用 Schur complement：

\[
F_{\mathrm{eff}}
=
F_{aa}
-F_{a\eta}F_{\eta\eta}^{-1}F_{\eta a}.
\]

必须检查 (F_{\mathrm{eff}}) 的 rank、最小奇异值和条件数。一个相机帧包含很多像素，因此“帧数小于 Zernike 数”并不自动意味着不可辨识；反过来，像素很多也不保证可辨识。真正的判据是去除 nuisance 后的 Jacobian/Fisher rank。

### 6.2 未知样品的边界

若参考臂是独立已知 local oscillator，四步 PSI 能给出处理场相对于该参考的复信息。若两臂都由同一未知复样品场派生，参考臂只提供自参考，样品相位与 pupil phase 仍可能存在 gauge 或近退化。正式实验应按以下顺序推进：

1. 已知 point/bead/USAF 或独立 wavefront calibration；
2. held-out 已知复杂场与器件失配；
3. 未知强度样品但受控 phase/statistical prior；
4. 未知真实 specimen，且 nuisance-projected observability 通过。

任何使用 simulator true aberration、diffraction-limited target 或 ideal image 选动作的实现都是 oracle，而不是 Adaptive estimator。truth 只能在策略冻结后评分。

## 7. 第五层公式：真正可能新颖的传感--执行联合设计

令离线物理设计变量为

\[
\Theta
=
(\rho_r,\rho_p,\delta_0,\mathcal B),
\]

其中 (\mathcal B=\{(d_t,c_t)\}_{t=1}^{T}) 是时空探针 codebook。推荐的联合目标不是单独最大化 Fisher 信息，而是

\[
\Theta^*
=
\arg\min_{\Theta}
\lambda_{\mathrm{act}}
\mathbb E_z[\mathcal L_{\mathrm{proj}}(z;\Theta)]
+
\lambda_{\mathrm{est}}
\mathbb E_z\!\left[
\operatorname{tr}
\big(F_{\mathrm{eff}}(z;\Theta)+\epsilon I\big)^{-1}
\right]
+
\lambda_{\mathrm{harm}}\mathcal R_{\mathrm{harm}}(\Theta)
+
\lambda_{\mathrm{budget}}\mathcal C(\Theta).
\]

四项分别约束：

1. 最终 task transfer 在 delivered feasible domain 中的投影误差；
2. 在样品和硬件 nuisance 下的有效估计不确定度；
3. 错误校正的 prospective harm；
4. photons、reads、states、settling、compute 与 wall time。

这一式子表达了本项目最值得追求的物理新意：参考臂不是测量模块外接的附件，而是同时控制 observability 和 actuation geometry 的 coherent bias。

## 8. 第六层公式：action-space tomography，而非强制重建完整波前

论文不必把“准确恢复所有 (a_j)”设为唯一目标。若多个潜在像差状态对应同一个或近似同一个最佳 delivered action，就应直接识别动作等价类。

令历史为

\[
\mathcal H_t
=
\{(d_s,c_s,Y_s)\}_{s=1}^{t},
\]

潜在状态后验为 (q_t(z)=p(z\mid\mathcal H_t))。对硬件动作 (a\in\mathcal A_{\mathrm{hw}})，定义未来效用

\[
U(a,z)
=
M[Y_{\mathrm{sci}}(a;z)]
-M[Y_{\mathrm{sci}}(a_{\mathrm{safe}};z)].
\]

运行时选择

\[
a_t^*
=
\arg\max_{a\in\mathcal A_{\mathrm{hw}}}
\mathbb E_{q_t}[U(a,z)]
-\lambda_h
\Pr_{q_t}\!\left[U(a,z)<-\tau_{\mathrm{harm}}\right].
\]

下一探针按 correction decision 的价值选择，而不是只按 coefficient RMSE：

\[
d_{t+1}^*
=
\arg\max_d
\mathbb E_{Y\sim p(Y\mid d,\mathcal H_t)}
\left[
V(\mathcal H_t\cup\{d,Y\})-V(\mathcal H_t)
\right]
-\lambda_c C(d).
\]

当可信状态集合共享一个低 regret 动作且 harm gate 通过时 `correct`；信息仍可增加时 `continue`；没有共同安全动作时 `abstain`。这比“先把 Zernike 全部估准再取负号”更贴合有限帧、硬件可达域和科学风险。

## 9. 两条互斥的最终光路路线

### Route A：reference-on science，推荐用于旗舰主张

参考臂在 calibration 和因果后续 science acquisition 中都保持开启。最终 action 被 held、settled 后重新采集原始干涉科学帧；该帧绝不参与 action selection。

优点：

- translated-circle 复传递函数是最终成像算子的真实可达域；
- sensing--actuation duality 成立；
- 可以主张 adaptive interferometric transfer control，而不仅是传统 AO；
- Fixed 的双臂计算机制与 Adaptive 之间存在真正物理桥梁。

代价：

- 论文必须明确这是干涉式相干显微/光学处理器，不是任意显微模态通用 AO；
- 对相干长度、路径漂移、偏振、speckle 和 arm balance 的稳定性要求更高；
- 最终指标首先应称 coherent complex transfer response、PSF、Strehl、CTF 或 empirical spatial-frequency response。只有验证 intensity-LSI 条件后才能称 MTF。

### Route B：reference-assisted sensing，reference-off science

参考臂只在 calibration 使用，随后关闭，phase SLM 对处理臂执行传统 phase-only correction。

优点：与普通 AO science path 更接近，也更容易和已有 AO 文献对照。

代价：

- 最终算子退化为以原点为中心、模长受 (P) 限制的 phase-only response；
- 不能再把参考臂扩展的复可达域写成最终 correction mechanism；
- 四步自参考 WFS + SLM phase conjugation 已有直接先例，创新更依赖 action-space decision、风险控制和 matched-budget adaptive probing。

当前 `docs/restoration-research-design.md` 冻结的是 Route B，而原有 Fixed 光路与用户提出的“类迈克尔逊干涉计算”更自然地指向 Route A。二者不能在同一主张中模糊混用。建议下一轮 ADR 明确选择 Route A，并把 `R=0` 改为重要消融；若硬件/应用必须 `R=0`，则主动收窄论文故事，不再宣称参考臂参与最终 complex transfer synthesis。

## 10. 创新审计：哪些不是爆点

| 候选表述 | 裁决 | 原因 |
|---|---|---|
| 四步相移恢复复场 | 已占据 | phase-shifting digital holography 已直接恢复 complex amplitude |
| 自参考干涉测波前后用 LC-SLM 校正 | 已占据 | 2010 年已有四相移 interferograms、SLM phase conjugation 与闭环实验 |
| 同一个 SLM 同时用于感知和校正 | 已占据 | 2011 年已有 single-element sensing/correction 实验 |
| Zernike 差分探针 | 已占据 | 经典 sensorless AO、MLAO、MeNet 等均大量使用 |
| Fisher-optimal 固定 probes | 已占据/拥挤 | 2025 年已有 Fisher-information-guided sensorless AO framework |
| 单帧学习型 WFS | 已占据 | 2026 年已有 hybrid optical encoder + learned single-shot correction |
| 高维、single-shot、reference-less complex WFS | 已占据 | SAFARI 已占据 reference-less single-shot 高维路线 |
| 8--10 帧、约 1/6 s | 工程指标 | 必须报告 end-to-end latency，且不能单独构成物理新意 |
| 网络预测 Zernike | 算法增量 | 只有在改变物理 measurement/control frontier 时才可能成为主贡献 |

## 11. 三个可证伪的旗舰候选

### Candidate 1：Interferometric sensing--actuation duality

**主张：** 联合设计 coherent bias 与时空探针，比“先把 WFS 设计好、再做 phase conjugation”在相同资源预算下同时降低 nuisance-projected uncertainty 和 task-transfer projection regret。

**关键对照：** 固定 quadrature、经典 grouped four-step PSI、独立 Fisher codebook、reference-off phase conjugation、只优化 sensing、只优化 actuation。

**Kill：** 联合设计不优于独立设计，或收益只来自更多 photons/reads。

### Candidate 2：Action-space interferometric tomography

**主张：** 不完整重建未知波前，而用有限 coded interferograms 直接缩小 hardware-feasible correction equivalence class，在相同帧数下获得更低 delivered-action regret 和 harmful-correction rate。

**关键对照：** Zernike-MLE 后取负号、MLAO/MeNet 式 coefficient regression、固定/Fisher probe、随机 probe、always-correct 和 never-correct。

**Kill：** coefficient reconstruction 达到同样动作效用，或 adaptive probe 不优于最佳固定 codebook。

### Candidate 3：Task-aware adaptive optical transfer steering

**主张：** 双臂 coherent bias 使 phase-only SLM 不仅能够 flatten pupil phase，还能把任务/噪声相关的目标复传递函数投影到真实可达圆，在未来原始科学帧上优于纯相位共轭和固定 learned phase。

**关键对照：** no AO、zero phase、固定 learned phase、oracle phase conjugation、O2/O3 feasible projection、reference-off science、数字 NAFNet-S。

**Kill：** task-aware target 不优于简单 phase conjugation，或所谓频率响应增益只来自后处理/归一化。

推荐把 Candidate 1 作为中心物理命题，Candidate 2 作为有限帧算法机制，Candidate 3 作为科学后果。三者形成“为什么能看见动作 → 为什么少量帧够用 → 为什么最终图像更好”的递进，而不是三篇互不相干的小论文。

## 12. 仿真阶梯

### S0：代数与实现同一性

- 零像差、单 Zernike、随机复场下验证四步公式恢复 (\Gamma)；
- 验证空间探针不变时闭式公式成立、变化时明确失败；
- 验证 (G=c+\rho e^{i\theta}) 平移圆、幅度上下界和最近点闭式投影；
- 验证 quadrature 的一阶灵敏度；
- 数值 Jacobian、autograd Jacobian 与解析导数相符；
- 建立真正的 `DualArmInterferometricBench`，reference flag 必须进入前向模型。

### S1：O1/O2/O3 可行域与桥梁

- 扫描 arm ratio、参考相位、像差 RMS、空间频率、SNR 与 delivery mismatch；
- 比较 ideal complex、ideal phase-only、delivered phase-only；
- 同时测 Route A 与 Route B，量化 reference 打开后可达域和 task utility 的增量；
- 使用 Fixed learned phase、zero phase 和 matched digital NAFNet-S 作为历史桥梁，而不是重新训练大网络。

### S2：blind low-order identifiability

- simulator 隐藏 Zernike/device-native truth；算法只见 commands、delivered probes 和 noisy intensities；
- 比较 grouped four-step PSI、五步误差补偿 PSI、正负 Zernike、Hadamard/composite probes、固定 Fisher codebook、广义 coded likelihood；
- 分别报告 coefficient RMSE、action agreement、delivered-action regret、(F_{\mathrm{eff}}) rank/condition、reprojection residual；
- 已知目标通过后再逐步引入未知样品 nuisance。

### S3：有限帧主动决策

- 允许 `continue/correct/abstain`；
- 比较 1--7 calibration prefixes，并以第 8 帧作为 held science 的严格版本；
- 另做 8 calibration + 第 9 science 的经典公平对照；
- 主指标为未来 utility、harm rate、risk--coverage、expected reads 和完整 latency，而非训练 loss。

### S4：物理失配与失败边界

- phase-step error、reference drift、arm imbalance、相干性下降；
- LUT、量化、crosstalk、phase--amplitude coupling、偏振、温度、配准、settling；
- shot/read noise、饱和、背景、样品运动、speckle decorrelation；
- unknown amplitude aberration 与 out-of-basis phase；
- OOD specimens、OOD aberrations 与仿真到实物偏移。

### S5：prospective science protocol

动作选择完成后冻结 policy，加载并 settle 校正，再获取全新的原始 science frame。随机/交叉比较：

- safe/no correction；
- selected correction；
- sham；
- opposite sign；
- equal-RMS random action；
- classical phase conjugation；
- strongest fixed/Fisher policy。

Route A 的主科学帧保持 reference-on，Route B/R=0 作为消融；若最终选择 Route B，则反过来写，但不得同时声称 reference 参与最终 transfer synthesis。

## 13. 8--10 帧协议建议

推荐同时保留两个预注册协议：

### Protocol P0：经典物理校验

- 8 个 calibration reads：两个固定 spatial states，每个完整四步；
- 第 9 个 read：selected correction 下的因果后续 science；
- 第 10 个 read：预注册的 safe/sham/validation，不得事后挑选。

P0 用于证明公式和硬件，不承担“8 帧完成全部闭环”的宣传。

### Protocol P1：旗舰有限预算

- 第 1--7 帧：广义 coded/adaptive interferograms；
- 第 8 帧：held-and-settled science observation；
- 若不确定度未过 gate，系统 abstain，而不是偷偷追加帧。

P1 不套用标准四步闭式公式，使用经 S0--S2 验证的 raw-likelihood/action-space estimator。只有当 P1 在完整预算下胜过 P0 的截断版本和最佳固定/Fisher codebook，才能把“时空主动测量”写成核心创新。

## 14. 论文故事与公式出现顺序

1. **Hero capability：** 一张完整 episode，展示参考臂、phase SLM、coded probe、decision、held science 和 raw improvement。
2. **Fixed paradox：** trained phase 明显优于 zero phase，但 post-detection hybrid 不胜 NAFNet-S，说明问题不是“光学不会学”，而是“光学介入太晚”。
3. **Physical theorem：** 用平移圆和闭式投影证明 reference-biased phase-only correction 的能力与边界。
4. **Interrogation theorem：** 用四步复交叉项、raw likelihood 与 nuisance-projected Fisher 说明未知动作怎样变得可观测。
5. **Duality：** 用联合目标把可达域和可辨识性合为一个物理设计问题。
6. **Finite-frame mechanism：** action-space posterior、value-of-probe、correct/continue/abstain。
7. **Prospective verdict：** 因果后续原始科学帧、harm 和完整 budget 作最终裁决。

建议暂用题目：

> **A self-interrogating phase-only interferometer for adaptive optical transfer control**

或更偏物理：

> **Sensing--actuation duality in a programmable interferometric optical processor**

在实验完成前不要把 `self-verifying`、`sub-200-ms`、`MTF control` 或 `unknown-specimen universal` 写入最终题目。

## 15. 最小成功标准与 kill rules

旗舰故事至少需要同时通过：

1. O3 在宽于单一目标/单一像差的区域有稳健 headroom；
2. 双臂模型和相移公式在 delivered hardware 下成立；
3. nuisance-projected information 支持所声明的动作维度；
4. P1 在完整资源预算下优于最佳固定/Fisher/classical baseline；
5. task-aware projection 优于纯 phase conjugation；
6. 后续原始 science frame 显示 prospective gain；
7. abstention 在 OOD/漂移下实质降低 harmful correction；
8. end-to-end timing 支持而不是只用 (N/60\) 推算速度。

出现以下任一情况应降级或终止主张：truth 泄漏；reference flag 只存在于 metadata；四帧空间探针变化却使用标准 PSI；`R=0` 结果被解释为 reference-biased transfer；固定/Fisher codebook 与 active policy 持平；收益来自数字后处理；MTF 使用条件不成立；纠正动作在新科学帧上无稳定收益。

## 16. 一手来源与创新边界

1. I. Yamaguchi and T. Zhang, “Phase-shifting digital holography,” *Optics Letters* 22, 1268--1270 (1997). 通过 phase-shifting interferometry 测量复振幅：<https://opg.optica.org/ol/abstract.cfm?uri=ol-22-16-1268>
2. P. Hariharan, B. F. Oreb and T. Eiju, “Digital phase-shifting interferometry: a simple error-compensating phase calculation algorithm,” *Applied Optics* 26, 2504--2506 (1987). 五帧 phase-step error compensation：<https://doi.org/10.1364/AO.26.002504>
3. J. Bai and C. Rao, “Experimental validation of closed-loop adaptive optics based on a self-referencing interferometer wavefront sensor and a liquid-crystal spatial light modulator,” *Optics Communications* 283, 2782--2786 (2010). 四个 phase-shifted interferograms、自参考 WFS、LC-SLM 校正和闭环验证：<https://doi.org/10.1016/j.optcom.2010.03.032>
4. R. Martínez-Cuenca et al., single spatial-light-modulator wavefront sensing/correction experiment, *Optics Letters* 36, 3702--3704 (2011): <https://opg.optica.org/ol/abstract.cfm?uri=ol-36-18-3702>
5. C. Johnson et al., “Phase-diversity-based wavefront sensing for fluorescence microscopy,” *Optica* 11, 806--820 (2024). 五图像 incoherent fluorescence phase-diversity 边界：<https://doi.org/10.1364/OPTICA.518559>
6. Q. Hu et al., “Universal adaptive optics for microscopy through embedded neural network control,” *Light: Science & Applications* 12, 270 (2023). 正负 bias images 与 physics-informed learned AO：<https://www.nature.com/articles/s41377-023-01297-x>
7. B. Zhang, M. J. Booth and Q. Hu, “Information-guided optimization of image-based sensorless adaptive optics methods” (2025 preprint). Fisher-information-guided probe optimization：<https://arxiv.org/abs/2506.07482>
8. Single-shot hybrid optical encoder and learned wavefront correction, *Nature Communications* (2026): <https://www.nature.com/articles/s41467-026-72364-1>
9. SAFARI, single-shot reference-less complex wavefront sensing, *Light: Science & Applications* (2026): <https://www.nature.com/articles/s41377-026-02241-5>
10. Optical-gradient wavefront sensing, *Nature Communications* (2026): <https://www.nature.com/articles/s41467-025-68259-2>
11. MeNet-AO, modulation-encoded learned adaptive optics, *Nature Communications* (2026): <https://www.nature.com/articles/s41467-026-73389-2>
12. Q. Song et al., phase-only encoding of complex modulation in Fourier optics, *Optics Express* 20, 29844--29853 (2012): <https://doi.org/10.1364/OE.20.029844>

## 17. 最终裁决

公式主线应从“已知像差取负号”升级为：

\[
\boxed{
\text{dual-arm physics}
\rightarrow
\text{complex feasible domain}
\rightarrow
\text{coded interferometric observability}
\rightarrow
\text{action-space decision}
\rightarrow
\text{delivered projection}
\rightarrow
\text{future raw science}
}
\]

四步相移负责建立可信复交叉项，Zernike/器件模态负责压缩未知状态，Fisher/Jacobian 负责证明信息够不够，phase-only projection 负责证明动作能不能实现，decision-value probing 负责决定下一帧是否值得，未来原始帧负责裁决物理收益。

爆点不应是“我们也能用几帧估像差”，而应是：

> **这个干涉系统不先重建世界再被动补偿；它利用同一相干偏置，主动询问哪一个真实可交付的光学动作最值得执行，并在新的物理观测中验证该动作。**
