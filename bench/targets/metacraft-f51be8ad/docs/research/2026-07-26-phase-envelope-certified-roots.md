---
record_type: research_record
date: 2026-07-26
status: research_finding
authority_level: none
current_capability: false
---

# 传播相位包络：精确方程、根区间与认证边界

日期：2026-07-26
文档性质：Research Record；只保存一手文献事实、可复核推导与 blocker，不作系统裁决。

## 结论

Ticket 21 所需的两个一维本征问题都有无歧义的精确方程：

- 空气包层、无限长、均匀介质圆柱的 `HE11` 模可由完整矢量特征方程求得；
- 实、无损一维 lamellar 周期介质的 Rytov 对称 `TE` / `TM` 基本根可由实数超越方程求得。

这足以实现两个**具名模型的数值结果**，但不足以把它们直接升级为真实二维周期柱阵列的严格上下界。现有一手来源没有证明

```text
isolated HE11 <= 2D pillar-array Bloch index <= 1D circumscribed-lamellar index
```

这条完整单侧关系。尤其是 Rytov 方程对一维无限周期 half-space 精确，不是对二维方格圆柱阵列精确。因此，在补齐独立的单调性证明之前，两个模型可以进入 `forecast`，不能单凭本记录支持 `hard refusal`。

即使补齐物理单侧性，普通双精度浮点的 Bessel、`tan` 与 `tanh` 求值也不自动构成“认证符号”。可拒绝的界必须使用带外向舍入的区间/球算术，或在符号无法认证时只报数、不裁决。

## 一、空气包层介质圆柱的 HE11 精确根

### 1.1 模型与变量

令：

```text
a       = 圆柱半径
n1      = 圆柱实折射率
n2      = 无限均匀包层实折射率，空气时 n2 = 1
k0      = 2 pi / lambda
beta    = 轴向传播常数
h       = sqrt(n1^2 k0^2 - beta^2)
q       = sqrt(beta^2 - n2^2 k0^2)
u       = h a
w       = q a
V       = k0 a sqrt(n1^2 - n2^2)
```

导模必须满足

```text
n2 k0 < beta < n1 k0
u^2 + w^2 = V^2 .
```

Le Kien 等在 Appendix C 给出空气包层超细光纤的完整矢量模方程；其 Eq. (C1) 对混合模写成

```text
[J_l'(u)/(u J_l(u)) + K_l'(w)/(w K_l(w))]
[n1^2 J_l'(u)/(u J_l(u)) + n2^2 K_l'(w)/(w K_l(w))]

= l^2 (beta/k0)^2 (1/u^2 + 1/w^2)^2 .
```

其中 `J_l` 是第一类 Bessel 函数，`K_l` 是第二类修正 Bessel 函数。[Le Kien et al., *Physical Review A* 97, 013821 (2018), Appendix C, Eqs. C1–C4](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.97.013821)；同一方程及物理传播区间也见 [Castillo-Pérez et al., *Journal of Computational Electronics* 22 (2023), Eq. 13](https://doi.org/10.1007/s10825-023-02006-y)。

Eq. (C1) 同时包含 `HE` 与 `EH` 分支，不能在它的任意零点上贴 `HE11` 标签。Le Kien 等的 Eq. (C2) 将 `HE` 分支显式写为

```text
J_(l-1)(u) / [u J_l(u)]

= -(n1^2 + n2^2)/(2 n1^2) * K_l'(w)/[w K_l(w)]
   + l/u^2
   - R
```

其中

```text
R^2 =
  [(n1^2 - n2^2)/(2 n1^2) * K_l'(w)/(w K_l(w))]^2
  + [l beta/(n1 k0)]^2 (1/w^2 + 1/u^2)^2 .
```

`HE11` 必须取 `l = 1`、径向第一根与上式的负平方根分支。这是实现时应使用的标量残差；只求 Eq. (C1) 的“某个根”不够。

### 1.2 根区间与单模条件

Snitzer 对圆柱介质波导给出的 cutoff 表表明：

- `HE11` 对应 `V = 0` 的零根，没有非零 cutoff；
- 首批高阶 `TE01` / `TM01` 模在 `J0(V) = 0` 处出现；
- `J0` 的第一正零点为 `j_0,1 = 2.404825557...`；
- `HE11` 的 `u` 从长波极限的 `0` 连续趋向短波极限 `j_0,1`。

因此，隔离 `HE11` 的物理区间可写成

```text
0 < u < min(V, j_0,1)
w = sqrt(V^2 - u^2)
```

且

```text
0 < V < j_0,1
```

是该理想圆柱模型的严格单模区间；`V = j_0,1` 是首批高阶模的 cutoff，而不只是弱导近似。[Snitzer, “Cylindrical Dielectric Waveguide Modes,” *JOSA* 51, 491–498 (1961), Tables I–II](https://opg.optica.org/josa/abstract.cfm?uri=josa-51-5-491)；[Tong, Lou, and Mazur, *Optics Express* 12, 1025–1035 (2004), Eqs. 3–9](https://opg.optica.org/oe/abstract.cfm?uri=oe-12-6-1025)。

上述端点都是开端点，且残差含 `u = 0`、`w = 0` 与 Bessel 比值奇点。数值程序不得直接在端点求值；它必须在该物理区间内找到一个经区间算术验证、残差符号相反的闭区间 `[u_lo, u_hi]`，再作外向舍入的二分。

当 `V < j_0,1` 时，系统中只有 `HE11` 一个导模，因而该符号括区间中的导模根身份无歧义。当 `V >= j_0,1` 时，`HE11` 仍存在，但仅凭“在完整传播区间找到一个根”不能证明取到了基本分支；此时必须使用上述 `HE` 分支、`u < j_0,1` 和连续分支身份共同认证。认证失败时只能返回 `uncertified`。

### 1.3 适用性

该方程只对以下模型精确：

- 无限长、截面恒定的圆柱；
- 圆柱与无限包层均为线性、各向同性、实折射率介质；
- 没有基底、有限高度端面、周期邻居与材料损耗。

所以它不直接适用于方柱，也不直接给出有限高度 pillar-on-substrate 单元的相位。把它用作二维周期阵列的下界，需要另行证明阵列介电函数增加所诱导的本征值单调性以及固定频率换向；该证明不是圆柱特征方程自身的内容。

## 二、一维 lamellar 周期介质的 Rytov 精确基本根

### 2.1 模型与精确方程

把坐标重命名为 MetaCraft 的几何口径：

```text
x                  = 周期方向
y                  = grating lines 方向
z                  = 沿柱轴的传播方向
Lambda             = 周期
F Lambda           = 高折射率条带宽度
(1-F) Lambda       = 低折射率间隙宽度
nH > nL > 0        = 两种实折射率
N = beta/k0        = 轴向有效折射率
0 < F < 1
```

Rytov 从每层内的 Maxwell 精确解、界面连续性与周期性出发，得到沿层传播的精确色散方程及对称/反对称分解。[Rytov, “Electromagnetic Properties of a Finely Stratified Medium,” *Soviet Physics JETP* 2, 466–475 (1956), Eqs. 9–10, 15, 18](https://www.jetp.ras.ru/cgi-bin/dn/e_002_03_0466.pdf)。

Hemmati 与 Magnusson 以现代符号重写了 Rytov 的对称根。对 `TE`（电场平行 grating lines）：

```text
sqrt(nL^2 - N_TE^2)
tan[(pi Lambda/lambda)(1-F) sqrt(nL^2 - N_TE^2)]

= -sqrt(nH^2 - N_TE^2)
   tan[(pi Lambda/lambda)F sqrt(nH^2 - N_TE^2)] .
```

对 `TM`（磁场平行 grating lines）：

```text
sqrt(nL^2 - N_TM^2)/nL^2
tan[(pi Lambda/lambda)(1-F) sqrt(nL^2 - N_TM^2)]

= -sqrt(nH^2 - N_TM^2)/nH^2
   tan[(pi Lambda/lambda)F sqrt(nH^2 - N_TM^2)] .
```

这是无限厚一维周期 half-space、法向对称场的精确 Rytov 方程，不是截断级次的 EMT 展开。[Hemmati and Magnusson, *ACS Photonics* 7, 3177–3187 (2020), Eqs. 1–3](https://doi.org/10.1021/acsphotonics.0c01244)；[author manuscript](https://arxiv.org/pdf/2006.04852)。

该论文还明确区分通常均匀化所用的 zeroth root `n_0^EMT` 与更高的 tangent roots，并通过 Eqs. (4)–(6) 将这些根解释为周期区内各空间谐波的轴向波矢分量。MetaCraft 所需的是 zeroth symmetric root；其余根不得混入“fundamental”结果。

### 2.2 实数形式与 principal-root 区间

对所需的实根 `nL < N < nH`，令

```text
p(N) = sqrt(nH^2 - N^2)
q(N) = sqrt(N^2 - nL^2)
A    = pi (1-F) Lambda / lambda
B    = pi F Lambda / lambda .
```

利用 `tan(i x) = i tanh(x)`，精确方程可改写为全实形式：

```text
TE: q tanh(A q) = p tan(B p)

TM: [q/nL^2] tanh(A q) = [p/nH^2] tan(B p) .
```

这是对上述一手方程的代数改写，不是新的近似。

zeroth symmetric root 位于第一个 `tan` 分支。定义

```text
N_pole^2 = nH^2 - [lambda/(2 F Lambda)]^2
N_lo     = max(nL, sqrt(max(0, N_pole^2))) .
```

则 principal root 位于

```text
N_lo < N_0 < nH .
```

若

```text
B sqrt(nH^2 - nL^2) < pi/2 ,
```

区间简化为 `(nL, nH)`。

这一区间是 MetaCraft 从 Eqs. (2)–(3) 作出的可复核推导，不是论文逐字给出的 bracket：

1. 在该区间内 `0 < Bp < pi/2`，避开所有 tangent pole；
2. 当 `N` 增大时，`q tanh(Aq)` 严格增大；
3. `p tan(Bp)` 随 `p` 严格增大，而 `p` 随 `N` 严格减小，因此右侧随 `N` 严格减小；
4. 残差在左端内侧为负，在 `nH` 端为正，故 TE、TM 各有且仅有一个 principal root。

实现不得在 `N_pole` 的 pole 上求值，应取一个可表示的内缩点并认证其残差严格为负。`nH` 端可用解析极限或内缩点认证正号。

### 2.3 “Rytov fundamental”与“space-filling mode”不是同一个文献名词

Rytov 与 Hemmati–Magnusson 证明的是一维 lamellar half-space 的对称周期根。`fundamental space-filling mode` 通常指完整无缺陷周期包层的 Bloch 基模。把 Rytov zeroth root 记为

```text
lamellar_fundamental_index
```

或

```text
rytov_fundamental_index
```

是清楚的；直接把它命名为二维柱阵列的 `space_filling_mode` 会混淆两个物理对象。

同理，“把圆柱外接成一维条带，因此该根是二维柱阵列的上界”依赖介电函数逐点增加下的 Maxwell 本征值单调性、Γ 点基本支与固定频率换向。Rytov 方程本身不证明这条跨几何关系。本记录检索到的一手来源不足以把该跨几何推断无条件升级为 hard bound。

### 2.4 适用性

上述实根和符号二分只适用于：

- 一维 lamellar 周期介质；
- 无限厚 half-space 与法向对称激发；
- `0 < F < 1`；
- `nH > nL > 0` 且两者为实数；
- 每个波长单独求值；色散可逐波长进入，损耗不可进入实根符号裁决。

若材料样本含非零消光系数、各向异性或复折射率，根进入复平面，不存在可排序的实括区间，也不存在“向柱材料折射率方向外舍入”的同一规则。此时必须把 bounded verdict 降级为 unavailable，而不是把虚部丢掉。

## 三、认证数值与外向舍入

### 3.1 认证的是输入模型，不是材料真值

材料数据库或求解器返回的折射率本身有测量、拟合和插值误差。若输入只是一对浮点数，数值认证最多证明：

> 对由这对输入数定义的理想、无损模型，根位于给定区间。

它不能证明真实材料的折射率也在该区间内。若系统要声称物理材料界，`MaterialSample` 必须提供经资格确认的不确定度区间；否则输出应明确标为 `conditional_on_sampled_index`。

### 3.2 可拒绝结果的最小数值契约

对每个根，只有同时满足以下条件才可称为 certified：

1. 所有输入先转换为包含原始值的闭区间；
2. `sqrt`、Bessel 比值、`tan`、`tanh` 与每次四则运算均使用外向舍入；
3. 括区间避开函数 pole，且两端残差区间严格分居零两侧；
4. 二分的每一步保留该符号不变量；
5. 达到文档精度后，仍保存未舍入的根区间作为证据。

普通 `float` 计算后调用 `nextafter` 只能外扩最终存储值，不能补回特殊函数内部未知的近似误差。HE11 的 Bessel 比值尤其需要支持 Bessel 函数的 interval/ball arithmetic，或一套有明确误差界的独立验证器。没有这样的后端时，正确行为是：

```text
numbers may be reported
certified = false
bounded refusal = forbidden
```

### 3.3 对相位跨度最有利的外向方向

若后续定义的乐观跨度是

```text
delta_n_upper =
  lamellar_index_at_largest_cell
  - max(ambient_index, isolated_index_at_smallest_cell)
```

则为避免错误低估该跨度：

- lamellar ceiling 取其根区间的**上端**，并向 `nH` 方向舍入；
- isolated floor 取其根区间的**下端**，并向 `n2` 方向舍入；
- 相减继续向增大 `delta_n_upper` 的方向舍入；
- 若相位 turns 为 `height * delta_n / lambda`，则使用 `height` 上端、`delta_n` 上端和 `lambda` 下端。

只有最终的 turns 上界仍严格小于目标时，才具备单向排除的数值形式。等号、零包含、pole 邻域、未认证材料样本或任一失败的 bound check 都必须保留数字但取消 verdict。

这套舍入方向是由“只允许无假阴性的排除”推导出的系统规则，不是 Rytov 或光纤文献中的原句。

## 四、对 Ticket 21 的直接结论

### 可以无歧义实现

- `HE11` 的精确 `HE` 分支残差、变量和物理根区间；
- `V < 2.404825557...` 的理想圆柱单模资格；
- Rytov-exact TE/TM zeroth symmetric roots；
- Rytov principal branch 的无 pole 区间与唯一性推导；
- 对两个具名模型的数值 forecast；
- 无损、实折射率、几何与模型适用性检查。

### 尚不能诚实实现为 hard refusal

1. **跨几何单侧性 blocker**：一手来源没有直接证明孤立圆柱根与外接一维 lamellar 根分别夹住真实二维周期柱阵列的轴向基本 Bloch 指数。
2. **认证特殊函数 blocker**：若实现只使用普通浮点 Bessel/三角函数，则“符号检查二分”仍不是严格数值证书。
3. **材料不确定度 blocker**：单值材料样本只能得到对输入模型有条件成立的数值，不能自动成为真实材料界。
4. **复材料 blocker**：非零消光系数使实根顺序、实括区间和现有外向舍入规则失效。

因此，Ticket 21 若坚持“bounded tier 可以 hard-refuse”，必须先补齐第 1 项证明并选择能满足第 2 项的认证数值后端；否则应把当前精确根放在 `forecast`，把 bounded verdict 保持 unavailable。退化的平凡界 `nH - n2` 虽然宽松，却不依赖这两个 blocker，仍是更诚实的硬上界。

## 来源

1. Fam Le Kien et al., “Enhancement of the quadrupole interaction of an atom with the guided light of an ultrathin optical fiber,” *Physical Review A* 97, 013821 (2018), Appendix C. [APS official page](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.97.013821)
2. E. Snitzer, “Cylindrical Dielectric Waveguide Modes,” *Journal of the Optical Society of America* 51, 491–498 (1961). [Optica official page](https://opg.optica.org/josa/abstract.cfm?uri=josa-51-5-491)
3. L. Tong, J. Lou, and E. Mazur, “Single-mode guiding properties of subwavelength-diameter silica and silicon wire waveguides,” *Optics Express* 12, 1025–1035 (2004). [Optica official page](https://opg.optica.org/oe/abstract.cfm?uri=oe-12-6-1025)
4. A. W. Snyder and J. D. Love, *Optical Waveguide Theory*, Springer (1983), “Waveguides with exact solutions” and “Circular fibers.” [Springer official page](https://link.springer.com/book/10.1007/978-1-4613-2813-1)
5. S. M. Rytov, “Electromagnetic Properties of a Finely Stratified Medium,” *Soviet Physics JETP* 2, 466–475 (1956). [JETP official PDF](https://www.jetp.ras.ru/cgi-bin/dn/e_002_03_0466.pdf)
6. H. Hemmati and R. Magnusson, “Applicability of Rytov’s Full Effective-Medium Formalism to the Physical Description and Design of Resonant Metasurfaces,” *ACS Photonics* 7, 3177–3187 (2020). [ACS official page](https://doi.org/10.1021/acsphotonics.0c01244)；[author manuscript](https://arxiv.org/pdf/2006.04852)
