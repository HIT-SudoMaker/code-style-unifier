# Cube BS/PBS 四终端入射、偏振与相干散射契约研究

**研究日期：** 2026-08-24  
**状态：** 设计输入；不是已接受的领域规范或 ADR  
**依赖：** [`beam-splitter-terminal-geometry.md`](./beam-splitter-terminal-geometry.md)  
**范围：** 线性、确定性、相干 Jones 场；四个外表面近似 AR、主对角膜层只发生一次散射的 cube BS/PBS。外表面鬼像、胶层内多次反射、散射退偏、荧光、非线性和有限孔径衍射不属于本契约。

## 研究结论

BS/PBS 的可靠接口不能只回答“功率分到哪里”，而必须一次冻结四类彼此独立的事实：

1. **结构可达性：** 每个入射终端只有一个透射终端、一个反射终端，另一个相邻终端和原终端是结构零。
2. **偏振坐标：** 每个 incoming/outgoing 半边方向都有确定的右手横向基，并由传播方向与膜层法向确定局部 `s/p`；反向入射不能复用一个未定向的全局 Jones 向量。
3. **复散射响应：** 允许路径上的 `T_s/T_p/R_s/R_p` 是复场系数或 2×2 Jones 块，包含幅度、相位、泄漏和损耗；有限消光比不改变结构零。
4. **完整相干相遇：** 同一时刻抵达同一 cube 的所有合法输入必须由一个 4×4 **块**散射操作共同计算；先分开调用再叠加强度会丢失干涉项。

Finesse 的官方 BS 接口同样有四个光学端口，并说明某一输出可同时含另一路输入的反射与透射贡献；它的模型最终形成一个线性方程系统。[Finesse 官方 Beamsplitter 文档](https://finesse.ifosim.org/docs/latest/usage/model_building/elements/optics/beamsplitter.html) [Finesse 官方 model graph](https://finesse.ifosim.org/docs/latest/getting_started/model_graph.html) 但本报告进一步把物理 cube 的固定终端几何、方向化偏振基和有限 owner 复用变成 ChromatixNext 的 Assembly 可检查事实。

## 1. 冻结的几何、方向与符号约定

### 1.1 Owner 局部坐标与主路由

沿用前置研究：

- `local_x` 指向终端 3（east）；
- `local_y` 指向终端 2（north）；
- `local_z = local_x × local_y`；
- 终端 `1=west, 2=north, 3=east, 4=south`；
- 对角膜层平面为 `local_y = local_x`；
- A 侧包含终端 1、2，B 侧包含终端 3、4；
- 固定膜层法向取 `n = (local_x - local_y)/sqrt(2)`，从 A 侧指向 B 侧。

主路由为：

| 入射终端 | 入射侧 | 透射 `T(i)` | 反射 `R(i)` | 结构禁止相邻端 | 同端返回 |
|---:|:---:|---:|---:|---:|:---:|
| 1 | A | 3 | 2 | 4 | 零 |
| 2 | A | 4 | 1 | 3 | 零 |
| 3 | B | 1 | 4 | 2 | 零 |
| 4 | B | 2 | 3 | 1 | 零 |

因此，透射对是 `1↔3`、`2↔4`，反射对是 `1↔2`、`3↔4`。这是主膜层模型的结构稀疏性，不是把很小的系数近似成零。Finesse 的官方四端口 BS 也明确区分四个端口和非零耦合，而不是任意端口全连接。[Finesse 官方 Beamsplitter 文档](https://finesse.ifosim.org/docs/latest/usage/model_building/elements/optics/beamsplitter.html)

### 1.2 Terminal incoming/outgoing 右手横向基

对每个 incoming 或 outgoing 传播单位向量 `k`，定义 owner-local 横向基：

```text
V(k) = +local_z
H(k) = V(k) × k
H(k) × V(k) = k
```

这里的 `H/V` 是 **owner-horizontal / owner-vertical**，不是不随光路变化的世界坐标 `Ex/Ey`。终端的 incoming 与 outgoing 方向相反，所以同一终端的 `H` 轴反号、`V` 轴不反号。Ansys 官方说明强调，没有传播向量和表面法向给出的入射面，就不能把输入 `Jx/Jy` 直接解释成 `s/p`；Jones 输入必须先有参考方法才能转换成三维横向电场。[Ansys OpticStudio 官方偏振坐标说明](https://optics.ansys.com/hc/en-us/articles/42661755401747-Investigating-OpticStudio-s-polarization-features)

| 终端 | `k_in` | `H_in` | `V_in` | `k_out` | `H_out` | `V_out` |
|---:|---|---|---|---|---|---|
| 1 | `+x` | `+y` | `+z` | `-x` | `-y` | `+z` |
| 2 | `-y` | `+x` | `+z` | `+y` | `-x` | `+z` |
| 3 | `-x` | `-y` | `+z` | `+x` | `+y` | `+z` |
| 4 | `+y` | `-x` | `+z` | `-y` | `+x` | `+z` |

### 1.3 从 Terminal `H/V` 到膜层 `s/p`

为避免 A/B 侧和反射后的隐式符号，始终使用 owner 的同一个有向膜层法向 `n`，定义：

```text
s(k) = normalize(n × k)
p(k) = k × s(k)
s(k) × p(k) = k
```

这与 COMSOL 采用的右手 `(s,p,k)` 规约一致；COMSOL 官方文档还明确指出，若反射光改用左手基，`r_p` 会出现相反符号，说明该符号必须由基约定冻结，不能在示例里临时补负号。[COMSOL 官方 Fresnel 方程与符号说明](https://doc.comsol.com/6.4/doc/com.comsol.help.roptics/roptics_ug_optics.6.64.html)

| 终端方向 | `s` | `p` | `[E_s,E_p]^T = Q[E_H,E_V]^T` |
|---|---|---|---|
| 1 incoming；4 incoming | `+V` | `-H` | `Q+ = [[0,1],[-1,0]]` |
| 2 incoming；3 incoming | `-V` | `+H` | `Q- = [[0,-1],[1,0]]` |
| 1 outgoing；4 outgoing | `-V` | `+H` | `Q-` |
| 2 outgoing；3 outgoing | `+V` | `-H` | `Q+` |

每一条合法路径的 `Q_in` 与 `Q_out` 相同。因此若 coating 在 `s/p` 基中的块为 `J_sp`，Terminal 基中的块确定为：

```text
J_HV = Q_out^T J_sp Q_in
```

对无 `s↔p` 转换的各向同性膜层，

```text
J_sp = diag(j_s, j_p)
J_HV = diag(j_p, j_s)
```

于是所有四向合法路径都得到相同的 `H=p`、`V=s` 物理解释；反向传播需要的几何符号已由 Terminal 基吸收。A/B 侧仍保留各自的复系数和适用域，不能因几何符号已处理就强行设成相等。

## 2. 完整 4×4 Jones 块散射

令 `a_i=[a_H,a_V]^T` 为终端 `i` 的 incoming Jones 场，`b_i` 为同一终端的 outgoing Jones 场。按功率归一化的传播模态，完整主散射为：

```text
[b1]   [ 0    R_A   T_BA  0   ] [a1]
[b2] = [ R_A  0     0     T_BA] [a2]
[b3]   [ T_AB 0     0     R_B ] [a3]
[b4]   [ 0    T_AB  R_B   0   ] [a4]
```

其中每个非零项都是 2×2 复 Jones 块；矩阵整体为 8×8 复线性算子，但保留为 4×4 terminal-block 表达最能暴露结构零。对无偏振交叉耦合的 coating：

```text
T_AB = diag(t_p_AB, t_s_AB)
T_BA = diag(t_p_BA, t_s_BA)
R_A  = diag(r_p_A,  r_s_A)
R_B  = diag(r_p_B,  r_s_B)
```

Finesse 官方相位推导强调反射/透射系数一般是复数，而且能量守恒依赖相对相位；常见对称与反对称 phase convention 都可物理一致，所以 `+i` 不是脱离端口 gauge 的膜层固有事实。[Finesse 官方 BS 相位关系](https://finesse.ifosim.org/docs/develop/usage/plane-waves/beam_splitter.html)

## 3. 四终端 × 输入偏振真值表

### 3.1 适用于任一终端的通式

对任一入射终端 `i`，令该侧系数简写为 `t_p,t_s,r_p,r_s`，任意输入为：

```text
a_i = h H_in + v V_in
```

则且仅则：

```text
b_T(i) = t_p h H_out + t_s v V_out
b_R(i) = r_p h H_out + r_s v V_out
b_forbidden(i) = 0
b_i = 0
```

对应全部常用纯态：

| 输入态（Terminal incoming 基） | 透射终端 `T(i)` | 反射终端 `R(i)` |
|---|---|---|
| `H`（即局部 `p`） | `t_p H` | `r_p H` |
| `V`（即局部 `s`） | `t_s V` | `r_s V` |
| `+45°=(H+V)/sqrt(2)` | `(t_p H+t_s V)/sqrt(2)` | `(r_p H+r_s V)/sqrt(2)` |
| `-45°=(H-V)/sqrt(2)` | `(t_p H-t_s V)/sqrt(2)` | `(r_p H-r_s V)/sqrt(2)` |
| `C_sigma=(H+i sigma V)/sqrt(2)` | `(t_p H+i sigma t_s V)/sqrt(2)` | `(r_p H+i sigma r_s V)/sqrt(2)` |
| 任意 Jones `[h,v]` | `[t_p h,t_s v]` | `[r_p h,r_s v]` |

这里采用 `exp(-i omega t)` phasor，并用 `sigma=+1/-1` 表示相对于各自传播方向的两种圆偏振；在项目另行冻结观察方向约定前，不把它们命名成容易歧义的 RCP/LCP。COMSOL 的官方圆偏振案例同样在输出端分别定义 outgoing mode，并依据局部入射面处理反射和透射偏振。[COMSOL 官方圆偏振反射案例](https://doc.comsol.com/6.4/doc/com.comsol.help.models.woptics.circular_polarization/circular_polarization.html)

把上式与第 1 节的路由组合，得到四终端完整结果：

| 入射 | 透射输出 | 反射输出 | 任意 Jones 输出 |
|---:|---:|---:|---|
| 1 | 3 | 2 | `b3=T_AB a1`, `b2=R_A a1` |
| 2 | 4 | 1 | `b4=T_AB a2`, `b1=R_A a2` |
| 3 | 1 | 4 | `b1=T_BA a3`, `b4=R_B a3` |
| 4 | 2 | 3 | `b2=T_BA a4`, `b3=R_B a4` |

### 3.2 Ideal PBS

常见 cube PBS 在标称入射几何下主要透射 `p`、反射 `s`；Thorlabs 的官方资料明确写为反射 S、透射 P，并给出有限的 `T_p:T_s` 消光比而不是几何新路径。[Thorlabs 官方 PBS 数据](https://www.thorlabs.com/catalogpages/V21/855.pdf)

理想模型冻结为：

```text
T_side = t_p_side |H><H| = diag(t_p_side, 0)
R_side = r_s_side |V><V| = diag(0, r_s_side)
```

因此，对四个入射终端都成立：

| 输入态 | 透射终端 | 反射终端 | 物理含义 |
|---|---|---|---|
| `H` | `t_p H` | 零 | 全部走直通主路径 |
| `V` | 零 | `r_s V` | 全部走指定相邻反射路径 |
| `+45°` | `t_p H/sqrt(2)` | `r_s V/sqrt(2)` | 正交分解；理想功率各半 |
| `-45°` | `t_p H/sqrt(2)` | `-r_s V/sqrt(2)` | 与 `+45°` 的相对符号不同 |
| `C_sigma` | `t_p H/sqrt(2)` | `i sigma r_s V/sqrt(2)` | 两个输出分别为线偏振，保留相对相位 |
| `[h,v]` | `t_p h H` | `r_s v V` | 任意 Jones 的投影式分路 |

理想 PBS 把正交偏振合到同一空间终端时，Jones 场会相加，但未经分析器的总强度中正交分量没有交叉项。若下游偏振元件把二者投影到共同偏振，仍可出现干涉；Assembly 不能因此提前丢弃相对相位。

### 3.3 Specified PBS

指定型 PBS 必须保留：

```text
T_side = diag(t_p_side, t_s_side)
R_side = diag(r_p_side, r_s_side)
```

- `t_s` 是透射方向的 S 泄漏；
- `r_p` 是反射方向的 P 泄漏；
- 两者都不能填充结构禁止终端；
- `T_p/T_s` 只约束透射功率比，不能替代反射端的 `R_s/R_p`，更不能给出四个复相位。

Thorlabs 官方数据指出，同一 cube 的透射消光比可达 `T_p:T_s > 1000:1`，而反射光消光比通常只有约 `20:1–100:1`；这直接否定了从一个消光比推导全部四个系数的做法。[Thorlabs 官方 mounted PBS 规格与说明](https://punchout.thorlabs.com/newgrouppage9.cfm?objectgroup_id=4137) 厂商表中 `T_p`、`R_s` 等是功率规格；只有在端口模态已做功率归一化时，幅值模才可由平方根换算，且数据仍不提供复相位。COMSOL 官方文档也分别定义场振幅系数与反射率/透射率，二者不可混写。[COMSOL 官方 Fresnel 方程](https://doc.comsol.com/6.4/doc/com.comsol.help.models.woptics.fresnel_equations/fresnel_equations.html)

因此，`specified_cube_pbs` 的输入证据必须是以下之一：

- 直接提供适用波长、角度和两侧的复 Jones 块；或
- 厂商/测量功率数据加上一个被明确命名、可审计的相位模型；或
- 层系与材料处方，经资格化薄膜求解器生成复块。

任何缺失相位都必须成为显式 unknown，不能默认为零或沿用 lumped `+i`。

## 4. Ideal 与 specified NBS

### 4.1 两种不能混名的 “ideal”

“S/P 分光功率相同”并不自动推出“任意 Jones 态保持不变”。必须区分：

```text
power-nonpolarizing:
|t_p| = |t_s|, |r_p| = |r_s|

Jones-neutral ideal:
t_p = t_s, r_p = r_s
```

第一种仍允许 `arg(t_p/t_s)` 或 `arg(r_p/r_s)` 产生 retardance，使 ±45° 或圆偏振变成椭圆偏振；第二种才在允许路径上对任意 Jones 态只乘公共复标量：

```text
T_side = t_side I2
R_side = r_side I2
```

因此只有 `Jones-neutral ideal` 才保证 H、V、±45°、圆偏振和任意椭圆偏振在每个输出的 Terminal 基中保持 Jones 态，只改变公共振幅与相位。理想无损 50:50 还需 `|t|^2=|r|^2=1/2` 和完整多输入幺正相位关系，而不是单独给每条路径一个正实 `1/sqrt(2)`。原始 Jones-BS 研究也分别构造 reflection/transmission Jones matrices，并专门研究 BS 对振幅和相位的 reversibility，支持把幅度中性与相位中性分开。[Fymat, *Applied Optics* 10, 2499–2505 (1971)](https://opg.optica.org/ao/abstract.cfm?uri=ao-10-11-2499)

### 4.2 Specified / nonideal NBS

实际 “non-polarizing” 只是偏振敏感度被限制在规格范围内。Newport 的官方 broadband hybrid cube 例如给出 `R_s,R_p` 与 `T_s,T_p` 约 45%，并只承诺 S/P 分量在 10% 内匹配；这不是数学恒等。[Newport 官方 02BC17MB.1 规格](https://www.newport.com/p/02BC17MB.1)

对无交叉偏振的 specified NBS：

```text
T_side = diag(t_p_side, t_s_side)
R_side = diag(r_p_side, r_s_side)
```

因此：

- H/V 一般具有不同分光比；
- ±45° 可变成另一线偏振或椭圆偏振；
- 圆偏振可因 S/P 幅度或相位差变成椭圆偏振；
- 两侧、波长和入射角的复响应可不同；
- 金属-介质 hybrid coating 还可有不可忽略吸收，不能强制 `R+T=1`。Newport 对该产品明确称有 moderate absorption。[Newport 官方 02BC17MB.1 说明](https://www.newport.com/p/02BC17MB.1)

若 coating 或应力导致 `s↔p` 交叉耦合，必须升级为完整 2×2 Jones 块；不能把交叉项伪装成旋转后的对角块，除非该旋转基和适用域也是 owner 状态的一部分。

## 5. 多个相干输入、共同输出与 Michelson 返回

完整块矩阵展开为：

```text
b1 = R_A  a2 + T_BA a3
b2 = R_A  a1 + T_BA a4
b3 = T_AB a1 + R_B  a4
b4 = T_AB a2 + R_B  a3
```

因此只有两组输入会在共同输出中直接相干叠加：

| 同时入射对 | 共同输出 |
|---|---|
| `(a2, a3)` | `b1` 与 `b4` |
| `(a1, a4)` | `b2` 与 `b3` |

`(1,2)`、`(1,3)`、`(2,4)`、`(3,4)` 的主输出集合互不重叠，不在同一 terminal mode 中直接干涉。四路同时入射时仍只需一次矩阵乘法；每个输出各自相加两项。

Michelson 返程若两臂从终端 2、3 到达，则：

```text
b1 = R_A a2 + T_BA a3
b4 = T_AB a2 + R_B a3
```

对偏振不敏感探测，终端 1 的功率包含：

```text
||b1||^2
= ||R_A a2||^2 + ||T_BA a3||^2
  + 2 Re[(R_A a2)^H (T_BA a3)]
```

这就是返程必须合并为同一次 encounter 的可证伪理由。Finesse 官方 model graph 也明确说明，一个 BS 端口包含来自一条路径的反射光与另一条路径的透射光。[Finesse 官方 model graph](https://finesse.ifosim.org/docs/latest/getting_started/model_graph.html)

需要进一步区分：

- ideal NBS 中，同偏振分量可在亮/暗端口完全干涉；
- ideal PBS 中，`R_A` 选择 V、`T_BA` 选择 H，二者在总强度里正交，不直接产生交叉项；
- specified PBS 的 `r_p/t_s` 泄漏会让同一 H 或 V 通道出现小的干涉项；
- 臂内波片可旋转返回 Jones 态，使 ideal PBS 也在选择后的共同偏振通道中产生或抑制干涉。

只有频谱线、相干谱系、空间采样、波前参考面和时间语义兼容的场才允许按复振幅相加。不相干输入需通过相干矩阵/统计强度处理，不能假装成具有任意固定相位的 Jones 和。

## 6. 互易性、幺正性、被动性与 gauge

### 6.1 幺正与被动

对功率归一化的四终端双偏振传播模态：

```text
无损：S^H S = I
被动有损：S^H S <= I
```

这里的半正定不等式必须对任意四端口复 Jones 输入成立。只检查四个单输入的 `R+T<=1` 不足以发现多输入相位错误；列之间的正交条件会约束反射与透射的相对相位。Finesse 官方推导同样指出，BS 的 phase relationship 是能量守恒所必需的。[Finesse 官方 BS 相位关系](https://finesse.ifosim.org/docs/develop/usage/plane-waves/beam_splitter.html)

有损模型可把未建模吸收/散射视为隐含环境端口；公开四终端子矩阵只要求 contraction，不应伪造为幺正。

### 6.2 互易性不是裸 `S=S^T`

Lorentz reciprocity 依赖线性、时不变、无磁光偏置等适用条件，也依赖输入/输出模态的归一化和配对。原始偏振散射研究指出，方向反转后的 reciprocity 关系通常是转置外加前后符号矩阵，而不是在任意 Jones 坐标中直接逐项相等。[Sekera, JOSA 56, 1732 (1966)](https://opg.optica.org/josa/abstract.cfm?uri=josa-56-12-1732) 更一般的模态推导给出 `C S` 对称，其中 `C` 是模态正交/归一化矩阵。[Svendsen et al., *Reciprocity and the scattering matrix of waveguide modes*](https://arxiv.org/abs/1301.2458)

本契约的同一终端 incoming/outgoing 都要求右手基，所以传播反向时 `H` 反号、`V` 不反号。令 `G4 = I4 ⊗ diag(-1,+1)` 把所有 outgoing `[H,V]` 映射到对应 reciprocal incoming 物理电场坐标；在四端口均为相同、正交、功率归一化传播模态的本报告范围内，明确测试：

```text
G4 S = (G4 S)^T
```

而不是裸测 `S=S^T`。若未来允许不同介质、非正交模式或倏逝模式，必须使用一般的模态 overlap `C`，不能沿用这个简化。

### 6.3 Phase gauge 与参考面

以下变换不应改变可观测量：

- 对任一 terminal mode 的 incoming/outgoing 基作一致单位复相位重定义；
- 平移 terminal reference plane，并在相邻 propagation 中补偿相同光程相位；
- 在完整变换链中同时采用另一套合法的反射 `p` 轴规约。

因此，裸 `r_A` 与 `r_B` 的符号、某条支路是否带 `i`、单个端口的绝对相位都不是脱离 gauge 的可观测量。可观测的是闭合光路的相对相位、输出 Jones 态和功率。Finesse 官方文档列出对称/反对称两套物理一致的 BS 相位 convention，正说明测试应验证 gauge-invariant 结果。[Finesse 官方 BS 相位关系](https://finesse.ifosim.org/docs/develop/usage/plane-waves/beam_splitter.html)

### 6.4 适用边界

本 Jones 契约仅在下列条件内成立：

- 频域线性相干场；每个 spectral line 独立应用响应；
- 端口模态可由两个确定的横向复电场分量表示；
- coating 不产生随机退偏；
- 准直正交 cube 几何，内部膜层标称约 45° 入射；
- 单个 Jones 块足以描述该空间频率/入射角。

若高 NA 或 angular-spectrum 不同采样点具有显著不同入射面，响应必须逐空间频率构造 `s/p`，不能对全场广播一个 Jones 常数。若存在退偏或部分相干，应使用 coherency/Mueller 层；Ansys 也把 Jones 描述限定为确定性复电场变换，并区分 Mueller 表示。[Ansys 官方 Jones/Mueller 说明](https://optics.ansys.com/hc/en-us/articles/49999570536723-Using-the-Polarization-Tab-for-Jones-and-Mueller-Matrix-Setup)

## 7. Assembly 与 Element 资格化真值矩阵

### 7.1 Exhaustive 路由测试

对每个输入终端 `i∈{1,2,3,4}`：

1. `T(i)` 和 `R(i)` 两个块必须存在；
2. 另一相邻终端必须为结构零；
3. 同终端输出必须为结构零；
4. A/B 侧响应必须由 owner 固定，不得由 occurrence 改写；
5. 相反对角膜层 owner 必须改变反射邻接表，而不是只改相位。

### 7.2 Exhaustive 偏振测试

对四个输入终端分别测试 `H,V,+45°,-45°,C_+,C_-` 与随机 complex128 Jones 向量：

- ideal PBS 严格满足第 3.2 节投影路由；
- specified PBS 的 `t_s/r_p` 只出现在透射/反射主终端；
- `Jones-neutral ideal NBS` 对任意输入保持归一化偏振态；`power-nonpolarizing` 反事实若偷偷加入 S/P retardance 则不得被前者测试接受；
- specified NBS 与显式块乘法逐位一致；
- 反向入射和反射后仍满足 `E·k=0` 与右手基；
- 旋转 owner pose 后局部结果不变、世界向量协变旋转。

### 7.3 多输入与干涉测试

枚举 16 个 terminal-presence mask，并对每个 active input 生成随机 complex128 Jones 场，验证一次 `S @ a` 等于四个输出公式。特别钉住：

- `(2,3)` 只在 1、4 共同输出；
- `(1,4)` 只在 2、3 共同输出；
- equal-arm ideal NBS Michelson 的亮/暗端口极限；
- 把两臂拆成两个 encounter 再加强度必须被反事实测试击穿；
- ideal PBS 的正交输出无直接强度交叉项；加 45° analyzer 后恢复相位依赖；
- specified PBS 泄漏在同偏振通道产生预测的小交叉项；
- 不同 Source Lineage 或不兼容 spectral line 不能被 Assembly 当成固定相位复和。

### 7.4 物理不变量与失败测试

| 类别 | 必须通过 | 必须失败或显式越界 |
|---|---|---|
| 结构 | 16 个单入射非零/零块与真值表一致 | `1→4`、`2→3` 等结构零被 leakage 填充 |
| owner 复用 | 多 encounter 共享 pose、diagonal、coating side 和参数身份 | 第二次 encounter 重新编号/翻膜层/复制可训练参数 |
| 偏振基 | 八个 incoming/outgoing frame 均右手且横向 | 用固定世界 `Ex/Ey` 直接充当四向 `s/p` |
| 无损 | 随机复多输入满足 `S^H S=I` 到 complex128 预算 | 只测单输入 `R+T=1` 而多输入增能 |
| 被动 | `largest_eigenvalue(S^H S)<=1` | 有损数据组合成增益算子 |
| 互易 | 在适用域内满足 reciprocal-mode 变换后的转置关系 | 在右手反向基中裸断言所有复块相等 |
| gauge | 两套合法 port phase/reference-plane gauge 给出相同功率和闭路相位 | 只改一个 branch 的 `i` 仍被接受 |
| 数据 | wavelength/AOI/side/normalization/provenance 完整 | 从 `T_p:T_s` 推导未知 `R_p` 或复相位 |
| 数值 | float64/complex128，零块精确、被动预算明确 | float32 让小 leakage 与结构零不可分 |
| 适用域 | 越界返回命名错误 | 静默换 ideal、外推、裁剪或归一化 |

Assembly 的职责是检查终端几何、direction、owner 一致性、coherent grouping 和 finite-route 完整性；Element/Numerical Support 的职责是基变换、复块散射和物理不变量。不要把两者合成一个巨大的“万能 Optical State”。

## 8. 对竞争库表述的证据边界

### 8.1 独立审计版本与方法

独立子代理在 2026-08-24 冻结并审计：

- Chromatix 稳定版 `0.6.0`，tag commit `d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee`；[官方 release](https://github.com/chromatix-team/chromatix/releases/tag/0.6.0)
- TorchRDIT 稳定版 `v0.2.0`，tag commit `545faf690d65b498f65312ec426e40d8cadc43a9`；[官方 release](https://github.com/yi-huang-1/torchrdit/releases/tag/v0.2.0)
- 补充扫描当日公开 `main`：[Chromatix `ce1482906fc663298613bb252bbf425e3be59839`](https://github.com/chromatix-team/chromatix/commit/ce1482906fc663298613bb252bbf425e3be59839)、[TorchRDIT `9009701d2f39c5c0c4a31d3486e4845bdd1d13e5`](https://github.com/yi-huang-1/torchrdit/commit/9009701d2f39c5c0c4a31d3486e4845bdd1d13e5)；该扫描只用于检查稳定版结论是否已被公开主线推翻，不与稳定版证据混写。

方法是读取官方 tag 的完整源码、文档、测试与 examples，检索并人工核验 `beam.?split`、`polarizing.?beam`、独立 token `PBS`、`four.?port|4.?port`、`terminal`、`assembly`、`route`、`coating`，同时检查公开导出、核心场状态、system/builder、source/result 和 scattering-matrix 实现。Notebook 内嵌图片的 base64 命中被排除。零命中只支持“在该冻结版本/公开接口中未发现”，不证明用户不能自行编写底层张量程序，也不覆盖未合并分支。

### 8.2 逐项结果

| 审计项 | Chromatix 0.6.0 | TorchRDIT v0.2.0 |
|---|---|---|
| 四终端、可复用 BS/PBS 物理 owner | 在被审计版本/公开接口未发现 | 在被审计版本/公开接口未发现 |
| 带局部几何与朝向的 terminal | 在被审计版本/公开接口未发现 | 在被审计版本/公开接口未发现；它有入射 `theta/phi` 和反射/透射波矢，但不是可连接 terminal |
| BS/PBS 元件公开接口 | 在被审计版本/公开接口未发现 | 在被审计版本/公开接口未发现；其 reflection/transmission 是周期层状结构结果，不是 cube 元件 |
| 显式偏振 | 已发现：vector field 与 Jones calculus | 已发现：source/result 层的复 TE/TM 幅值与矢量场 |
| Assembly route 可实现性检查 | 在被审计版本/公开接口未发现 | 在被审计版本/公开接口未发现 |
| 完整相干 branch/join encounter 检查 | 在被审计版本/公开接口未发现 | 在被审计版本/公开接口未发现 |

Chromatix 的 `OpticalSystem` 官方源码把系统定义为按顺序执行的 optical-element 列表，每个中间 element 接收一个 `Field` 并返回一个 `Field`；这支持“公开 system interface 中未发现 terminal、branch/join 和 route checker”，但不否认用户可以自行编写 JAX 函数。[Chromatix 0.6.0 `OpticalSystem`](https://github.com/chromatix-team/chromatix/blob/0.6.0/src/chromatix/systems/optical_system.py#L11-L41) 其公开 elements 聚合为 masks、lenses、propagation、samples、sensors、sources 等类别，在被审计 tag 中没有找到 BS/PBS API。[Chromatix 0.6.0 elements exports](https://github.com/chromatix-team/chromatix/blob/0.6.0/src/chromatix/elements/__init__.py#L1-L8)

但 Chromatix 确有显式偏振：`VectorField`/`ChromaticVectorField` 携带 Jones vector，官方偏振指南说明当前使用 Jones calculus 并处理 fully polarized light。[Chromatix 0.6.0 vector field source](https://github.com/chromatix-team/chromatix/blob/0.6.0/src/chromatix/core/base.py#L73-L101) [Chromatix 0.6.0 polarizer source](https://github.com/chromatix-team/chromatix/blob/0.6.0/src/chromatix/functional/polarizers.py#L82-L128) [Chromatix 官方 polarization guide](https://chromatix.readthedocs.io/en/latest/polarization/)

TorchRDIT 的官方 `FourierBaseSolver` 面向周期边界的 layered structures，求解 reflection/transmission 与 field distributions。[TorchRDIT v0.2.0 solver](https://github.com/yi-huang-1/torchrdit/blob/v0.2.0/src/torchrdit/solver.py#L748-L806) 它通过 `theta/phi/pte/ptm` 显式定义入射方向与复 TE/TM 幅值，并返回反射/透射场与波矢，所以不能说它“没有方向或偏振”。[TorchRDIT v0.2.0 source interface](https://github.com/yi-huang-1/torchrdit/blob/v0.2.0/src/torchrdit/solver.py#L1028-L1124) [TorchRDIT v0.2.0 result interface](https://github.com/yi-huang-1/torchrdit/blob/v0.2.0/src/torchrdit/solver.py#L1564-L1630)

TorchRDIT 的 `SMatrix(S11,S12,S21,S22)` 是层栈两侧反射/透射的 two-sided scattering representation；四个 block 不是 north/east/south/west 四空间终端。[TorchRDIT v0.2.0 `SMatrix`](https://github.com/yi-huang-1/torchrdit/blob/v0.2.0/src/torchrdit/utils.py#L24-L48) [TorchRDIT v0.2.0 scattering 初始化公式](https://github.com/yi-huang-1/torchrdit/blob/v0.2.0/src/torchrdit/utils.py#L401-L440) 其 builder 公开形状是 incident/reference medium、顺序 layer stack 和 transmission medium，反向仿真通过反转层栈并交换两侧介质；这不是任意实验光路 Assembly。[TorchRDIT v0.2.0 builder](https://github.com/yi-huang-1/torchrdit/blob/v0.2.0/src/torchrdit/builder.py#L249-L297) [TorchRDIT v0.2.0 reverse builder](https://github.com/yi-huang-1/torchrdit/blob/v0.2.0/src/torchrdit/builder.py#L852-L944)

### 8.3 可以成立的比较结论

> 在 2026-08-24 审计的 Chromatix 0.6.0 与 TorchRDIT v0.2.0 公开接口中，均未发现把四终端 BS/PBS 作为可复用物理 owner，并在汇编期联合校验 terminal 几何可达性、偏振基变换以及相干 branch/join 完整性的接口。Chromatix 已有显式 Jones 偏振，TorchRDIT 已有方向化 TE/TM 分层散射；ChromatixNext 的候选差异点是把这些数值能力提升为可检查的有限光路语言。

不能据此写成“竞争者无法处理偏振/方向”“ChromatixNext 全领域首创”或“统一架构本身就是创新”。TorchRDIT 的主问题是周期分层 meta-optics/RCWA/R-DIT，并非通用实验光路 Assembly；其没有该 route DSL 是范围差异，不是核心求解器缺陷。ChromatixNext 可主张的创新应是**公开、可测试、带资格证据的四终端 owner + 方向协变偏振 + finite-route 编译检查 + 完整相干 encounter**；在实现、反事实测试和版本化对比完成前，只能称为候选差异点。

## 9. 可冻结事实与仍需 owner 决策

### 9.1 可进入 Spec 的事实

- 主 cube 是固定 pose、固定对角面和固定 coating side 的唯一物理 owner；
- 四终端结构零与有限消光泄漏属于不同层；
- incoming/outgoing Terminal 各有右手横向基，`s/p` 由 `k` 与固定膜层法向确定；
- 一次 encounter 接收全部同时到达的合法相干输入，并执行完整 4×4 Jones-block scattering；
- ideal PBS 为 H(p) 透射、V(s) 反射；specified PBS 保留四个方向化复系数；
- NBS 必须区分仅匹配 S/P 功率的 `power-nonpolarizing` 与复块为公共标量的 `Jones-neutral ideal`；specified NBS 可有 S/P 幅相差；
- reciprocity、unitarity/passivity 与 phase gauge 必须在正确的端口模态坐标中检查；
- 厂商功率/消光数据不能单独生成缺失的复相位。

### 9.2 仍需 owner 裁定

1. public 类型是否首版同时提供 `IdealCubePBS/NBS` 与 `SpecifiedCubePBS/NBS`，还是 specified 只作为内部/实验接口；
2. specified 数据最小格式：逐 wavelength/AOI 的复 Jones 表、薄膜处方，还是功率表加命名相位模型；
3. circular polarization 的项目级 RCP/LCP 命名采用哪一个观察方向/phasor 标准；本报告建议 public contract 优先使用 `helicity=±1`；
4. Wave Terminal 首版是否只支持本报告的正交共面 cube，还是立即允许任意 3D pose 与逐 `k` angular-spectrum 响应；
5. 有损/漏能结果是否必须显式返回 absorption provenance，还是只保证四端口 contraction；
6. 现有 lumped BS/PBS 是否保留为明确命名的无几何近似，还是迁移后删除；
7. 元件测量导入需要何种 phase retrieval/calibration 证据，才能把“真实测量”提升为 complex response，而不只是功率拟合。
8. public `IdealCubeNBS` 是否承诺强的 `Jones-neutral` 语义；若只承诺 S/P 功率相等，类型名必须暴露 `power-nonpolarizing`，不能让调用者误以为圆偏振保持不变。

## 10. 对 AI-native 创新主张的审慎表述

这个设计真正适合 AI-native authoring 的原因，不是它让接口更多，而是它把容易靠人脑补全的隐含事实变成机器可枚举的有限契约：固定端口方向、结构零、owner 复用、偏振基、完整相干输入集、适用域和命名错误。AI 可以在 Freeze 前证明一个光路是否可实现，并从真值表自动生成反事实测试。

在证据完成前，推荐表述为：

> ChromatixNext 拟议把 cube BS/PBS 的四终端可实现性、方向化 Jones 基和有限 owner 复用提升为 Assembly 可检查契约；这比只暴露分光比例的一入两出接口携带更强的物理结构信息。

不要表述为“Chromatix 或 TorchRDIT 无法做到”。竞争差异必须绑定被审计版本、公开接口、复现实验和发布日期。
