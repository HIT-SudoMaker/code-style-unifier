---
record_type: research_record
date: 2026-07-26
status: research_finding
authority_level: none
current_capability: false
---

# 研究票据 02：孤立柱导模与阵列 Bloch 模——界的方向

日期：2026-07-26
文档性质：Research Record，纯文献问题，无数值仿真；不修改 `docs/metacraft_next/`，不产生 qualification。
物理域：方格晶格圆形 SiN 柱（Luke 数据，`n ≈ 2.05–2.12 @ 355–400 nm`），silica 基底（`n ≈ 1.47–1.48`），空气环境，正入射；周期 `200–220 nm`，直径 `60–180 nm`，柱高 `500–900 nm`，工作波长 `355 / 400 nm`。填充率 `f = πd²/4P² ≈ 0.06–0.64`，柱间隙 `20–160 nm ≈ 0.06–0.45 λ`，`P/λ ≈ 0.50–0.62`（两个波长下均满足基底内亚衍射条件 `P < λ/n_silica ≈ 240–272 nm`，但远非深亚波长）。

## 结论摘要

1. **子问题 1 裁决：孤立柱基模有效折射率是阵列基模（Γ 点 Bloch 模 / fundamental space-filling mode, FSM）有效折射率的下界，不是上界。**微扰直觉被文献证实且可升级为严格论证：固定传播常数 `β` 下的 Maxwell 变分（min–max）定理 + `ε` 的逐点比较 + FSM 的"固定 β 下最低频模式"定义，三个已发表的组件拼出严格不等式 `n_iso(ω) ≤ n_FSM,array(ω)`（逐直径成立，间隙有限时严格小于）。因此**把孤立柱模型当作"乐观上界"在方向上是错的**。见第二节。
2. **子问题 2 裁决：在严格的 2D 横截面本征问题里基底根本不出现，模型内偏移为零；物理上基底把柱底部附近的局域相位向上推（加入 `ε>1` 材料只会抬高相位积累，一阶微扰符号确定），并使 `n_eff < n_silica` 的小直径单元变为泄漏准导模。**基底的主要作用是端面/Fabry–Pérot 项而非 `n_eff` 本身；对总透射相位的净符号没有严格结论。已发表定理明确把基底排除在保证之外（[Lee, Avniel & Johnson 2008, Sec. 5](https://arxiv.org/abs/0803.2850)）。见第三节。
3. **子问题 3 裁决：横向 E 的圆柱 Maxwell-Garnett 在准静态极限内是严格下界（它恰是二维 Hashin–Shtrikman 下界），但在 `P ≈ 0.5–0.6 λ` 的有限频率下它连界都不是，只是一个通常偏低的近似。**Wiener 界（调和均值 ≤ ε_eff ≤ 算术均值）与 HS 界都是**准静态**严格定理；本晶格横向响应因 C4v 对称而各向同性，HS 界适用。有限周期修正按 `(Λ/λ)²` 抬高有效折射率（1D 可由 Rytov 精确解验证；2D 为数值观察），故准静态下界"通常仍然偏安全"，但这是经验观察，不是定理。见第四节。
4. **子问题 4 裁决：存在可引用的严格基础——固定 `β` 的 H 场算符 `∇β×(1/ε)∇β×` 的 Rayleigh 商 / min–max 定理蕴含"在任何地方抬高 ε 只会压低每一条本征频率"，等价地"固定 ω 下基模 n_eff 对 ε 逐点单调不减"。**该变分定理及一阶微扰公式 `Δω = −(ω/2)·∫Δε|E|²/∫ε|E|²` 均已发表（[Joannopoulos et al., *Photonic Crystals*, 2nd ed., ch. 2](http://ab-initio.mit.edu/book/)；[Johnson et al., PRE 65, 066611 (2002)](https://doi.org/10.1103/PhysRevE.65.066611)；应用形态见 [Lee, Avniel & Johnson 2008, eqs. (5),(8),(18)](https://arxiv.org/abs/0803.2850)；光纤问题的数学化 min–max 见 [Bamberger & Bonnet, SIAM J. Math. Anal. 21, 1487 (1990)](https://epubs.siam.org/doi/10.1137/0521082)）。由此可构造**可计算的双侧包络**：下界 = 孤立柱 HE11 精确解，上界 = 外接 1D lamellar 光栅 FSM 精确解（Rytov 超越方程）。见第五节。
5. **子问题 5 裁决：单向排除规则在"波导图景模型内"存活，但必须换掉当前的乐观模型。**许可的规则是 `Δn_ub = n_lam(d_max) − max(1, n_iso(d_min))`（严格、可计算、偏松）；退化选项是平凡界 `n_pillar − 1`。孤立柱模型给出的跨度 `Δn_iso` 对阵列跨度**既非上界也非下界**，不得再充当乐观包络。模型外物理（端面反射、共振相位）不受任何 `n_eff` 界约束，排除裁决必须标注为 waveguide-picture 范围。见 What this decides。

## 研究边界与证据规则

- 只回答文献问题；不运行任何求解器，不写入 `docs/research/` 以外的文件。
- 每条结论标注证据等级：**定理**（已发表的严格结果，或由已发表组件直接拼接、每一步可检验的推论）、**标准近似**（领域通用但非严格）、**经验观察**（数值/实验一致性，无一般证明）。
- 一手来源：Optica/OSA、APS、SIAM 原文，arXiv 作者稿，以及 Snyder & Love、Joannopoulos、Milton 标准专著。

## 一、为什么这个问题决定包络的合法性

设计系统预报传播相位跨度 `Δφ ≈ (2πh/λ)·Δn_eff`，并希望"仅当乐观估计也不达标时才排除某个柱高"。单向排除的前提是乐观模型**真的**是上界。候选模型有三个：孤立圆柱导模（Snyder & Love 解析解）、周期阵列 Bloch 模（真实对象，需数值）、以及某种 EMT 均质化。本票据要回答的正是这三者之间已知的严格排序。

## 二、子问题 1：孤立柱模 vs 阵列 Bloch 模

### 2.1 严格论证链（定理级，由已发表组件拼接）

固定 `β`（沿柱轴 z 的传播常数），横截面本征问题写成 H 场的 Hermitian 特征问题（[Lee, Avniel & Johnson, Opt. Express 16, 9261 (2008)](https://doi.org/10.1364/OE.16.009261)，式 (5)–(8)，该文把变分定理归于 [Joannopoulos 专著](http://ab-initio.mit.edu/book/)）：

```text
∇β × (1/ε) ∇β × H = (ω²/c²) H ,   ∇β·H = 0
ω²_min(β)/c² = inf_{∇β·H=0} ∫ |∇β×H|²/ε  /  ∫ |H|²        (Rayleigh 商)
```

三步推理：

1. **逐点比较**：阵列介电分布 `ε_array`（一根柱 + 全部邻居）与孤立柱分布 `ε_iso`（同一根柱，其余为空气）满足 `ε_array ≥ ε_iso` 处处成立，于是每个试探场的 Rayleigh 商在阵列问题里更小（`1/ε_array ≤ 1/ε_iso`）。
2. **试探场**：把孤立柱基模 `H_iso`（横向、指数衰减，属于合法试探空间）代入阵列算符的 Rayleigh 商，得 `inf spec(阵列算符) ≤ RQ_array[H_iso] ≤ RQ_iso[H_iso] = ω_iso(β)²/c²`。邻居柱覆盖了 `H_iso` 消逝尾所在区域，第二个不等号在有限间隙下严格。
3. **FSM 定义**：周期介质在固定 `β` 下的谱底恰是 fundamental space-filling mode 的频率——Lee–Avniel–Johnson 原文："*at each real β there is a fundamental (minimum-ω) space-filling mode at a frequency ωc(β)*"。因此 `ω_FSM,array(β) ≤ ω_iso(β)`，沿单调色散曲线换到固定 ω 即 `n_FSM,array(ω) ≥ n_iso(ω)`。

色散曲线单调性与谱结构的数学基础见 [Bamberger & Bonnet (1990)](https://epubs.siam.org/doi/10.1137/0521082)（全矢量光纤模的 min–max 与色散曲线单调性）。**证据等级：定理**（组合本身未以单一定理形式发表，但每一步均直接来自上引已发表结果；标注的两处"标准认定"见 2.3）。

### 2.2 文献三路佐证

- **PCF 有效折射率模型**：FSM 被定义为无缺陷二维光子晶体中**模式折射率最大**的 Bloch 模，即固定 ω 下阵列可支持的最高 `n_eff`（[Birks, Knight & Russell, Opt. Lett. 22, 961 (1997)](https://opg.optica.org/ol/abstract.cfm?uri=ol-22-13-961)；[Knight et al., JOSA A 15, 748 (1998)](https://opg.optica.org/josaa/abstract.cfm?uri=josaa-15-3-748)）。
- **波导阵列超模理论**：N 根相同单模波导的超模传播常数围绕孤立值劈裂，同相（in-phase）超模位于顶端 `β = β_iso + |劈裂|`；正入射恰好激励 Γ 点的同相组合（[Kapon, Katz & Yariv, Opt. Lett. 9, 125 (1984)](https://www.osapublishing.org/abstract.cfm?uri=ol-9-4-125)；两根波导的对称/反对称劈裂见 [Snyder & Love, *Optical Waveguide Theory* (1983)](https://link.springer.com/book/10.1007/978-1-4613-2813-1) 耦合模章节）。耦合模理论在本域的 `20 nm` 间隙下定量不可靠（**标准近似**），但方向与 2.1 的严格结果一致；变分论证不依赖弱耦合假设。
- **超表面 LPA 文献**：blazed-binary / metalens 谱系从一开始就用**周期单元**的基阶 Bloch 模而非孤立柱建库（[Lalanne et al., Opt. Lett. 23, 1081 (1998)](https://opg.optica.org/ol/abstract.cfm?uri=ol-23-14-1081)；[JOSA A 16, 1143 (1999)](https://opg.optica.org/josaa/abstract.cfm?uri=josaa-16-5-1143)；[JOSA A 16, 2517 (1999)](https://opg.optica.org/josaa/abstract.cfm?uri=josaa-16-10-2517)；[Arbabi et al., Nat. Nanotech. 10, 937 (2015)](https://doi.org/10.1038/nnano.2015.186)；[Khorasaninejad et al., Science 352, 1190 (2016)](https://doi.org/10.1126/science.aaf6644)；综述 [Lalanne & Chavel, Laser Photon. Rev. 11, 1600295 (2017)](https://doi.org/10.1002/lpor.201600295)）。低对比 SiN 使模式去局域、邻居相互作用增强，这正是本物理域所处的位置（[Zhan et al., ACS Photonics 3, 209 (2016)](https://doi.org/10.1021/acsphotonics.5b00660)，SiN 方格晶格、可见光）。

### 2.3 两处需要标注的"标准认定"

1. **FSM 位于 Γ 点**：2.1 的不等式界住的是"固定 β 下所有横向 Bloch 波矢里的最低频率"；把它等同于正入射激励的 `k_t = 0` 模式，是 PCF/超表面文献的标准做法（FSM 在单元胞上用对称边界条件计算），在标量极限可由周期 Schrödinger 算符谱底定理严格化，全矢量情形无已知反例。**证据等级：标准近似（标量极限内为定理）。**
2. **固定 β ↔ 固定 ω 的换向**：需要两条色散曲线均单调上升；孤立光纤模有严格证明（Bamberger & Bonnet），FSM 带边单调性是标准事实。**证据等级：标准近似（组件有定理支撑）。**

### 2.4 对"跨度"的推论（重要负结果）

逐直径的下界**不能**直接给出跨度的界：`Δn_iso = n_iso(d_max) − n_iso(d_min)` 低估了两个端点，两个低估相减方向不定。阵列-孤立差值随间隙缩小而增大（`d_max` 端间隙仅 `20 nm`），也随小直径端模式去局域而以不同机制增大，两种趋势竞争，方向必须逐例计算。**因此孤立柱模型对阵列跨度既非上界也非下界——它不能承担"乐观包络"角色。证据等级：定理（由 2.1 的逐点不等式与反例构造逻辑直接推出）。**

## 三、子问题 2：silica 基底的方向

1. **模型内**：`Δφ ≈ (2πh/λ)Δn_eff` 所用的 `n_eff` 来自 z 不变的 2D 横截面本征问题，横截面内只有柱与空气——基底根本不在算符里，偏移严格为零。**证据等级：定理（模型定义）。**
2. **物理方向**：真实有限高柱底部附近加入 `ε ≈ 2.16` 的 silica，替换 `ε = 1` 的空气。一阶微扰公式 `Δω = −(ω/2)·∫Δε|E|²/∫ε|E|² ≤ 0`（[Joannopoulos ch. 2](http://ab-initio.mit.edu/book/)；[Johnson et al. 2002](https://doi.org/10.1103/PhysRevE.65.066611)）给出确定符号：加介质只降频率、只抬相位积累。所以基底把局域相位**向上**推。**证据等级：定理（对本征频率）→ 标准近似（外推到有限高度柱的相位积累）。**
3. **是否显著**：偏移限于底部约一个衰减长度内，且在 `Δφ` 的两个直径端点部分相消；对比度 `1.47 vs 1.0` 下属于修正量级而非主导项。更实质的效应是：小直径端 `n_eff → 1 < n_silica ≈ 1.47`，真实柱-基底体系中该模位于基底光锥之上，变为泄漏准导模——传播相位图景在 `d_min` 端本来就已退化。[Lee–Avniel–Johnson Sec. 5](https://arxiv.org/abs/0803.2850) 明确指出基底破坏其定理前提（非对称包层可产生截止）。**证据等级：标准近似 + 文献明示的定理适用边界。**
4. **对单向排除的含义**：基底效应主要进入端面/Fabry–Pérot 反射相位（[Lalanne, JOSA A 16, 2517 (1999)](https://opg.optica.org/josaa/abstract.cfm?uri=josaa-16-10-2517)；[Arbabi et al. 2015](https://doi.org/10.1038/nnano.2015.186) 的低 Q Fabry–Pérot 图景），不受 `n_eff` 界约束；不要试图给它指定一个"安全方向"。

## 四、子问题 3：Maxwell-Garnett、Wiener 界与 Hashin–Shtrikman 界

映射：正入射、E 场横向，准静态下方格柱阵等效为单轴介质，基模看到横向张量分量 `ε_⊥`，`n_QS = √ε_⊥`。

| 命题 | 状态 | 来源 |
| --- | --- | --- |
| Wiener 界：`(f/ε_i + (1−f)/ε_h)⁻¹ ≤ ε_eff ≤ f·ε_i + (1−f)·ε_h`，任意微结构 | **准静态定理**（能量变分证明） | [Wiener 1912](https://www.biodiversitylibrary.org/bibliography/9694)；教程综述 [Markel, JOSA A 33, 1244 (2016)](https://doi.org/10.1364/JOSAA.33.001244) |
| HS 界：各向同性两相复合的更紧双侧界 | **准静态定理**（变分原理；方格晶格横向响应因 C4v 对称各向同性，适用） | [Hashin & Shtrikman, J. Appl. Phys. 33, 3125 (1962)](https://doi.org/10.1063/1.1728579)；纤维几何（2D 横向）版本 [Hashin & Rosen 1964](https://doi.org/10.1115/1.3629590)；系统化见 [Milton, *The Theory of Composites* (2002)](https://doi.org/10.1017/CBO9780511613357) |
| 圆柱横向 MG `((ε_eff−ε_h)/(ε_eff+ε_h) = f·(ε_i−ε_h)/(ε_i+ε_h))` **恰等于** 2D HS 下界——当且仅当宿主是低 ε 相（空气宿主 + SiN 柱即本例） | **准静态定理**（MG 与 HS 界重合是标准结果） | [Markel 2016](https://doi.org/10.1364/JOSAA.33.001244)；[Milton 2002](https://doi.org/10.1017/CBO9780511613357)；重合方向的明确表述另见 [Kanaun, Int. J. Appl. Mech. (2015)](https://doi.org/10.1142/S1758825115500258) |
| 方格圆柱阵的准静态**精确**解（比 MG 紧，含多极修正） | 准静态精确解（非有限频界） | [Rayleigh, Phil. Mag. 34, 481 (1892)](https://doi.org/10.1080/14786449208620364)；[Perrins, McKenzie & McPhedran, Proc. R. Soc. A 369, 207 (1979)](https://doi.org/10.1098/rspa.1979.0160) |
| 有限频率（`P ≈ 0.5–0.6 λ`）下上述任何一条仍是界 | **否——全部失效为近似。**有限周期修正按 `(Λ/λ)²` 抬高有效折射率：1D lamellar 可由 Rytov 精确色散验证（二阶展开为正修正），2D 柱阵为数值观察 | [Rytov, Sov. Phys. JETP 2, 466 (1956)](http://www.jetp.ras.ru/cgi-bin/e/index/e/2/3/p466?a=list)；[Lalanne, Appl. Opt. 35, 5369 (1996)](https://opg.optica.org/ao/abstract.cfm?uri=ao-35-27-5369)；[Lalanne & Lemercier-Lalanne, J. Mod. Opt. 43, 2063 (1996)](https://doi.org/10.1080/09500349608232871)；[Kikuta et al., JOSA A 15, 1577 (1998)](https://opg.optica.org/josaa/abstract.cfm?uri=josaa-15-6-1577)；Rytov 全解回顾 [Hemmati & Magnusson, arXiv:2006.04852](https://arxiv.org/abs/2006.04852) |

**裁决**：MG 在 `ω→0` 是有据可查的严格下界（= 2D HS 下界），不是"碰巧另一种近似"；但本物理域 `P/λ = 0.50–0.62`，远离准静态，**MG 在此只能作为通常偏低的参考值使用（经验观察），不得在排除规则中充当严格界**。若需要更好的准静态参考，用 Perrins–McKenzie–McPhedran 的方格精确解替代 MG。

## 五、子问题 4：单调性定理与可计算的双侧包络

### 5.1 定理本体

固定 `β`（或固定 Bloch k）的 Maxwell 特征问题是权重 `1/ε` 的 Hermitian 问题，Courant–Fischer/min–max 直接给出：**`ε` 逐点增大 ⇒ 每条按序数排列的本征频率单调不增 ⇒ 固定 ω 下基模 `n_eff` 单调不减。**已发表载体：

- 变分定理与微扰公式：[Joannopoulos, Johnson, Winn & Meade, *Photonic Crystals: Molding the Flow of Light*, 2nd ed., Princeton (2008), ch. 2](http://ab-initio.mit.edu/book/)（"electromagnetic variational theorem"与"the effect of small perturbations"，`Δω = −(ω/2)·∫Δε|E|²/∫ε|E|²`，符号确定；沿任意 `ε(t)` 递增路径积分该 Hellmann–Feynman 导数即得有限幅度单调性）。
- 精确一阶导数公式的期刊版本：[Johnson et al., Phys. Rev. E 65, 066611 (2002)](https://doi.org/10.1103/PhysRevE.65.066611)。
- 固定 β 变分定理在波导/周期包层的成体系应用：[Lee, Avniel & Johnson, Opt. Express 16, 9261 (2008)](https://doi.org/10.1364/OE.16.009261)。
- 数学文献的 min–max 化：[Bamberger & Bonnet, SIAM J. Math. Anal. 21, 1487 (1990)](https://epubs.siam.org/doi/10.1137/0521082)；周期介质谱理论综述 [Kuchment, *The Mathematics of Photonic Crystals*, SIAM (2001)](https://doi.org/10.1137/1.9780898717594.ch7)。

**证据等级：定理**（附 2.3 的两条标准认定，用于把结论落到 Γ 点、固定 ω 的表述上）。

### 5.2 由单调性licensed 的可计算包络

对每个直径 d（周期 P、波长 λ 固定）：

```text
max(1, n_iso(d))  ≤  n_Bloch,Γ(d)  ≤  n_lamFSM(d)  ≤  n_pillar
```

- **下界 `n_iso(d)`**：空气包层孤立圆柱 HE11 精确色散（Bessel 特征方程，[Snyder & Love 1983](https://link.springer.com/book/10.1007/978-1-4613-2813-1) step-profile 章），无截止、代价一维求根。`n ≥ 1` 一侧由 `ε_array ≥ 1` 与均匀空气比较直接得到。
- **上界 `n_lamFSM(d)`**：把每个圆柱换成**外接** 1D lamellar 板条（板宽 = d，周期 = P，沿 y 无限延伸）。因圆 ⊂ 条带，`ε_lam ≥ ε_array` 逐点成立，单调性给出 `n_lamFSM ≥ n_Bloch,Γ`。lamellar 阵列沿板面方向传播的基阶 Bloch 模有**精确**超越色散方程（[Rytov 1956](http://www.jetp.ras.ru/cgi-bin/e/index/e/2/3/p466?a=list)；[Yeh, Yariv & Hong, JOSA 67, 423 (1977)](https://doi.org/10.1364/JOSA.67.000423)；[Hemmati & Magnusson, arXiv:2006.04852](https://arxiv.org/abs/2006.04852)），同样一维求根；取两个偏振中基模折射率较大者以覆盖方格的偏振简并。
- **平凡上界 `n_pillar`**：单元胞充满柱材料，最松但零成本。

预期紧度（定性）：`d_min = 60 nm` 端下界几乎贴合（`V ≈ 0.95`，模式弱束缚，`n_iso → 1⁺`）；`d_max = 180 nm` 端外接条带填充率 `0.82–0.90` 明显高于圆柱的 `0.53–0.64`，上界偏松但显著优于 `n_pillar`。**这不是数值声明，只是几何比例的直接推断；紧度必须由下游票据用求解器标定。**

### 5.3 跨度的乐观界

```text
Δn_eff(P, λ)  ≤  Δn_ub  =  n_lamFSM(d_max) − max(1, n_iso(d_min))
```

上端取上界、下端取下界，方向正确；两个量各自来自精确特征方程，无网格、无仿真。**证据等级：定理（模型内，含 2.3 两条标准认定）。**

## 六、子问题 5：单向排除还剩下什么

1. **模型内存活**：排除规则 `(2πh/λ)·Δn_ub < 目标相位覆盖 − 裕量 ⇒ 排除 h` 是合法的单向规则——`Δn_ub` 严格不低估模型真值。
2. **必须退役的做法**：以孤立柱扫描的 `Δn_iso` 作乐观包络（方向错误，见 2.4）；以 MG 或任何准静态 EMT 在 `P/λ ≈ 0.5–0.6` 下充当界（见第四节）。
3. **模型外不存活**：`Δφ ≈ (2πh/λ)Δn_eff` 本身忽略端面相位、低 Q 共振与邻胞非局域响应；这些项不被任何 `n_eff` 界控制（[Lalanne & Chavel 2017](https://doi.org/10.1002/lpor.201600295) 对波导图景适用界限的讨论）。物理级的"绝对不可行"证明不存在于本票据检索到的文献中；排除裁决必须携带 `waveguide_picture` 范围标签，且裕量应吸收端面项的量级。

## What this decides

1. **可严格夹住 `Δn_eff` 的可计算对**：
   - 逐直径：`[max(1, n_iso(d)), n_lamFSM(d)]`——孤立柱 HE11 精确解（下）与外接 lamellar FSM 精确解（上），两者均为一维求根，无仿真依赖；
   - 跨度乐观界：`Δn_ub = n_lamFSM(d_max) − max(1, n_iso(d_min))`；退化选项 `n_pillar − 1`（更松、零实现成本）。
2. **licensed 的排除规则**：仅当 `(2πh/λ)·Δn_ub` 仍低于目标覆盖（扣除为端面/共振项预留的裕量）时排除柱高 h，并把裁决标注为 waveguide-picture 范围。`Δn_ub` 的松紧应由下游票据用一次 Bloch 求解对若干 (d, P, λ) 样本标定后再定裕量。
3. **必须修正的既有假设**：孤立柱模型是逐直径**下界**（悲观侧),其跨度对阵列跨度无界方向——任何把"isolated-rod span"当乐观包络的代码路径都应改为上式或平凡界。
4. **证据等级汇总**：`n_iso ≤ n_Bloch ≤ n_lam ≤ n_pillar` 与 `Δn_ub` ——定理（含两条标注的标准认定：FSM 取于 Γ、色散单调换向）；基底抬高局域相位——一阶微扰定理 + 有限高度外推为标准近似；MG = 2D HS 下界——准静态定理；有限频率下准静态界仍偏安全——经验观察；耦合模/超模方向——标准近似（与定理一致）。

## 参考文献（一手来源）

- T. A. Birks, J. C. Knight, P. St. J. Russell, Opt. Lett. 22, 961 (1997). https://opg.optica.org/ol/abstract.cfm?uri=ol-22-13-961
- J. C. Knight et al., JOSA A 15, 748 (1998). https://opg.optica.org/josaa/abstract.cfm?uri=josaa-15-3-748
- K. K. Y. Lee, Y. Avniel, S. G. Johnson, Opt. Express 16, 9261 (2008); arXiv:0803.2850. https://arxiv.org/abs/0803.2850
- J. D. Joannopoulos, S. G. Johnson, J. N. Winn, R. D. Meade, *Photonic Crystals: Molding the Flow of Light*, 2nd ed., Princeton Univ. Press (2008). http://ab-initio.mit.edu/book/
- S. G. Johnson et al., Phys. Rev. E 65, 066611 (2002). https://doi.org/10.1103/PhysRevE.65.066611
- A. Bamberger, A. S. Bonnet, SIAM J. Math. Anal. 21, 1487 (1990). https://epubs.siam.org/doi/10.1137/0521082
- P. Kuchment, in *Mathematical Modeling in Optical Science*, SIAM (2001).
- A. W. Snyder, J. D. Love, *Optical Waveguide Theory*, Chapman & Hall (1983).
- E. Kapon, J. Katz, A. Yariv, Opt. Lett. 9, 125 (1984). https://www.osapublishing.org/abstract.cfm?uri=ol-9-4-125
- O. Wiener, Abh. Math.-Phys. Kl. Königl. Sächs. Ges. Wiss. 32, 507 (1912).
- Z. Hashin, S. Shtrikman, J. Appl. Phys. 33, 3125 (1962). https://doi.org/10.1063/1.1728579
- Z. Hashin, B. W. Rosen, J. Appl. Mech. 31, 223 (1964). https://doi.org/10.1115/1.3629590
- G. W. Milton, *The Theory of Composites*, Cambridge Univ. Press (2002). https://doi.org/10.1017/CBO9780511613357
- V. A. Markel, JOSA A 33, 1244 (2016). https://doi.org/10.1364/JOSAA.33.001244
- Lord Rayleigh, Phil. Mag. 34, 481 (1892). https://doi.org/10.1080/14786449208620364
- W. T. Perrins, D. R. McKenzie, R. C. McPhedran, Proc. R. Soc. Lond. A 369, 207 (1979). https://doi.org/10.1098/rspa.1979.0160
- S. M. Rytov, Sov. Phys. JETP 2, 466 (1956).
- P. Yeh, A. Yariv, C.-S. Hong, JOSA 67, 423 (1977). https://doi.org/10.1364/JOSA.67.000423
- H. Hemmati, R. Magnusson, arXiv:2006.04852 (2020). https://arxiv.org/abs/2006.04852
- P. Lalanne, Appl. Opt. 35, 5369 (1996). https://opg.optica.org/ao/abstract.cfm?uri=ao-35-27-5369
- P. Lalanne, D. Lemercier-Lalanne, J. Mod. Opt. 43, 2063 (1996). https://doi.org/10.1080/09500349608232871
- H. Kikuta, Y. Ohira, H. Kubo, K. Iwata, JOSA A 15, 1577 (1998). https://opg.optica.org/josaa/abstract.cfm?uri=josaa-15-6-1577
- P. Lalanne et al., Opt. Lett. 23, 1081 (1998). https://opg.optica.org/ol/abstract.cfm?uri=ol-23-14-1081
- P. Lalanne et al., JOSA A 16, 1143 (1999). https://opg.optica.org/josaa/abstract.cfm?uri=josaa-16-5-1143
- P. Lalanne, JOSA A 16, 2517 (1999). https://opg.optica.org/josaa/abstract.cfm?uri=josaa-16-10-2517
- P. Lalanne, P. Chavel, Laser Photon. Rev. 11, 1600295 (2017). https://doi.org/10.1002/lpor.201600295
- A. Arbabi et al., Nat. Nanotech. 10, 937 (2015). https://doi.org/10.1038/nnano.2015.186
- M. Khorasaninejad et al., Science 352, 1190 (2016). https://doi.org/10.1126/science.aaf6644
- A. Zhan et al., ACS Photonics 3, 209 (2016). https://doi.org/10.1021/acsphotonics.5b00660
