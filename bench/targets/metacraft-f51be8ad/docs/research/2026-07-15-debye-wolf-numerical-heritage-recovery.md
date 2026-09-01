---
record_type: research_record
date: 2026-07-15
status: heritage_recovery_only
authority_level: none
current_capability: false
---

# Debye–Wolf 数值遗产恢复记录

## 结论摘要

本记录恢复的是历史知识，不恢复历史 capability，也不授权任何当前产品 claim。

1. `28ce27c` 加入的 `DebyeWolfEngine` 不是 Richards–Wolf 球面 Debye 积分的离散实现。它先用标量角谱法传播，再在二维频谱上截取 `rho <= NA`，最后用平面波横向性关系补出一个纵向分量。更准确的名称应是 **scalar ASM + spectral transversality reconstruction**。
2. 该实现仍有可保留的数值意图：高 NA 路径需要复矢量场、纵向场分量、明确的孔径限制、可追溯 artifact，以及 reference/accelerator parity。但代码本身不应成为未来参考算子的 golden implementation。
3. `5f7978e` 删除前的树 `368e0fd` 中，所谓 radial-achromatic / Bessel / full-array Debye 只剩调用壳、metric taxonomy、claim guard 和 usefulness schema。核心优化器、径向数据模型、Bessel 算子与 direct Debye reference 在所有可达 Git refs 中都不存在，因此不存在可恢复的完整“径向 Bessel 加速器”。
4. “德拜加速积分恢复法”不是历史代码或文献中的标准算法名。若项目今后保留这个中文工作名，应严格解释为：**恢复 Debye–Wolf 科学契约，并为同一物理算子实现经过 direct-reference parity 资格化的 FFT/CZT、轴对称 Bessel 或 GPU 加速路径**；其中“恢复”是工程治理动作，不是现存功能，也不是 Debye 积分的逆问题。
5. 未来重实现应进入 M5 的 finite-aperture numerical backend seam；M3 拥有科学 task 与 metric 语义，M5 只执行经授权的 exact numerical contract 并产生 raw complex field/observation，M6 才能资格化 contract/device。当前 MetaCraft Next 的独立构建、测试、分发及 Debye capability 均未在本记录中验证。

本处置与历史 ADR 0026（已删除路径 `docs/adr/0026-retire-the-legacy-runtime-after-scientific-asset-recovery.md`）一致：保留紧凑、带来源的 Numerical Heritage Recovery Package，其余旧运行时可以删除；vendor-derived official-style metalens 方案仍只是 Scientific Reference Case。

## 研究范围与证据规则

本次只使用两类证据：

- 可达 Git 对象中的不可变 commit/tree/blob；
- 原始论文或出版方的一手页面。

没有执行旧运行时测试，没有恢复已删除源码到工作树，也没有验证 `metacraft_next` 的 build、test 或 distribution。下文“测试过”只表示历史 commit 中存在相应测试代码，不表示本次重新运行通过。

本地 Git 对象没有配置 remote，故历史证据采用可复现的 `commit:path` 与 blob SHA 标识，而不是伪造网页链接。例如：

```powershell
git show 28ce27c:src/metacraft/propagation/debye_wolf.py
git show 9a3d4aa:tests/unit/test_debye_wolf.py
git show 234966d:src/metacraft/stress/radial_achromatic.py
git ls-tree -r 368e0fd4d27ef4895a3108f5c0a49b5f078f09da
```

## 一、Git provenance 与文件清单

### 1. 历史链

| 时间 | Commit | 可恢复事实 |
| --- | --- | --- |
| 2026-05-25 | `28ce27ca329c4a323d009c29cb8e297180d1874e` | 首次加入名为 `DebyeWolfEngine` 的传播分支、高 NA 自动选择和单元测试。 |
| 2026-05-26 | `9a3d4aa4d282f9d2775b663afad4d478bb0ccf8d` | 增加 `validation.json`、三个内部 consistency/behavior tests，并把传播接入多波长 task。 |
| 2026-05-26 | `662f7b7168f840b378c02017217dea4ddf72a6aa` | 将独立 Debye 文件与测试 100% rename 到 `deprecated/metacraft_legacy_2026-05-26/`。 |
| 2026-06-08 | `234966d81abb74372eb4471bd4a10b606129a4e2` | 加入 radial-achromatic stress 调用壳、usefulness schema/tests 和 CPU/CUDA profile 文本；未加入它导入的算法依赖。 |
| 2026-06-08 | `23ba1e4d4039b85dc7d402e4a1afbb131e7e53bd` | ADR 明确把 low-angular-mode Fourier–Bessel production support 推迟到 v0.16；只测试设计 prompt 必须提及未来要求。 |
| 2026-06-08 | `5f39dd1ed39ebcf93c927ced98524b3c807fea0b` | 删除 `deprecated/metacraft_legacy_2026-05-26` 中的独立 Debye 文件与测试。 |
| 2026-06-19 | `43f885868a51085bea66b4dcf4b6a2919ab99e82` | 将仍存的 radial-achromatic 壳与 policy 文件移动到 `deprecated/`，同时删除 Fourier–Bessel ADR 与 prompt test。 |
| 2026-06-23 | `5f7978ed4d7daf08edbe4dde93eb6e9146cdf24b` | 删除整个 retired legacy tree。其直接父树是 `368e0fd4d27ef4895a3108f5c0a49b5f078f09da`。 |

这些 commit 全部是当前 `HEAD` 的祖先，可由 `git merge-base --is-ancestor <commit> HEAD` 验证；删除没有破坏 Historical Git Archive 的可达性。

### 2. `28ce27c` 首次实现的精确清单

| Path | Blob | 角色 |
| --- | --- | --- |
| `src/metacraft/propagation/debye_wolf.py` | `17b8cd58e62b26c968513fe663d003703c398d3d` | 93 行的名义 Debye–Wolf engine。 |
| `src/metacraft/propagation/selector.py` | `1d4c4c0180b469306bebb0cd5e6e8b01c8d0fd34` | `NA > high_na_threshold` 时选择 `debye_wolf`。 |
| `src/metacraft/skills/metalens/dag.py` | `5d6f8f771f1ec09b430eb5751cbfaace5abd4ff1` | 从量化 pupil 调用 engine，并写 propagation artifacts。 |
| `examples/metalens_high_na/input.yaml` | `2aeb04dd79b85d5ce681aa58b6a47bccc433579d` | 5 µm aperture、2 µm focal length、532 nm、linear-x 的 fake-backend 示例。 |
| `tests/unit/test_debye_wolf.py` | `f9d5d05f5a8a14f1cd2a212407414dc5888161fe` | 检查字段 artifact、shape、finite intensity 和 longitudinal fraction 的范围。 |
| `tests/unit/test_propagation_selector.py` | `df3b8278c666f3881b12bd6e7d85d2670b2868fc` | 检查高/低 NA 分支选择。 |

`debye_wolf.py` 依赖同树中的 `angular_spectrum._propagate`、`_central_window_energy_fraction`、`_fwhm` 和 `PropagationMetrics`；这一早期最小 closure 在该 commit 中存在。

### 3. `9a3d4aa` 的最终独立 Debye 形态

`9a3d4aa` 将 engine blob 更新为 `368082a0d6a806af65ec310064baee23540a1007`，测试 blob 更新为 `0b0d8cc6d94e9364b088e6c167348b33db7dded4`，并通过：

- `src/metacraft/skills/metalens/tasks/propagation.py`（blob `caf40110...`）逐波长调用；
- `tests/integration_fake/test_static_dag_fake.py`（blob `92f63b51...`）检查 high-NA run 写出 `validation.json`；
- feasibility/strategy/selector tests 检查高 NA 自动标记为 `debye_wolf`。

这是可达历史中该独立 engine 的最后实质算法版本。它在 `662f7b7` 被原样 quarantine，在 `5f39dd1` 被删除；因此 `5f7978e^` 已经没有 `debye_wolf.py`。

### 4. `234966d` 与 `5f7978e^` 的 radial-achromatic/Bessel 遗留物

`234966d` 新增的关键 blobs 是：

| Path（加入时） | Blob | 实际内容 |
| --- | --- | --- |
| `src/metacraft/stress/radial_achromatic.py` | `15cfba7bf7ad57a9c5c725c2bdbeb98dc5729286` | orchestration 壳；声明 480/550/620 nm、NA 0.85、ring grid、三阶段 optimizer、bounded direct reference。 |
| `src/metacraft/stress/high_na_radial_achromatic_usefulness.py` | `aa2877386898cc7fa5ce2d2cbd2910022c669238` | 对调用者直接提供的 baseline/review scalar lists 计算 median improvement/worst regression，并记录 backend 标签。 |
| `tests/integration_fake/test_high_na_radial_achromatic_v015_usefulness_cpu.py` | `b10f633c...` | 用手写分数检查 JSON/schema 与 `release_quality=false`。 |
| `tests/integration_fake/test_high_na_radial_achromatic_v015_usefulness_cuda.py` | `b29e8a31...` | 仅检查 `stage_b_backend=torch_cuda` 会产生 stage-B claim，final metric claim 仍为 false。 |
| 两个 regression tests | `5754f754...`, `b6abc570...` | 检查 profile family 与 baseline/review 输入约束。 |

在删除前父树 `368e0fd` 中，这些 blobs 仅移动到 `deprecated/`，内容未变；另有 release-gate YAML、metric taxonomy、report text、agent claim guards、evidence schema/tests 和 CPU/CUDA profile。它们证明当时已经意识到 claim 边界，但不证明数值算子存在。

`23ba1e4` 的两个 blobs——Fourier–Bessel ADR `7da3b744...` 与文档 test `e36832cf...`——只声明未来需要 angular-mode schema、mode truncation、polarization convention、mode-energy leakage 和 direct-vs-Fourier–Bessel regression；该 ADR 明文说 v0.15 没有 production support。

## 二、恢复出的历史算法

### 1. 第一步：标量角谱传播

令 pupil samples 为 `U0[x,y]`，采样间隔为 `d`，波长为 `lambda`。历史 `_propagate` 构造离散频率 `fx, fy`，并使用：

$$
H(f_x,f_y;z)=
\begin{cases}
\exp\!\left(i2\pi z\sqrt{\lambda^{-2}-f_x^2-f_y^2}\right),
& f_x^2+f_y^2\le \lambda^{-2},\\
0,&\text{otherwise},
\end{cases}
$$

$$
U_z=\mathcal F^{-1}\{\mathcal F\{U_0\}H\}.
$$

这就是 propagating-only scalar angular spectrum method (ASM)。它先完成到 `z_m` 的平面传播；没有参考球、焦距到 ray angle 的 sine-condition mapping 或矢量透镜变换。

### 2. 第二步：频域孔径和纵向分量重建

历史 `_vector_focal_fields` 再对 `Uz` 做 FFT，并定义归一化方向量：

$$
u=\lambda f_x,\qquad v=\lambda f_y,\qquad
r_s=\sqrt{u^2+v^2},\qquad
w=\sqrt{\max(1-u^2-v^2,0)}.
$$

它把输入 NA 静默裁剪到 `[0, 0.999999]`，并构造：

$$
S=\mathcal F\{U_z\}\,\mathbf 1(r_s\le \operatorname{clip}(NA)).
$$

对 `linear_x`：

$$
\tilde E_x=S,\qquad \tilde E_y=0,\qquad
\tilde E_z=-\frac{u}{\max(w,10^{-12})}S.
$$

对 `linear_y` 则交换 x/y：

$$
\tilde E_x=0,\qquad \tilde E_y=S,\qquad
\tilde E_z=-\frac{v}{\max(w,10^{-12})}S.
$$

最后分别 inverse FFT，并计算：

$$
I=|E_x|^2+|E_y|^2+|E_z|^2,
\qquad
\eta_z=\frac{\sum|E_z|^2}{\sum(|E_x|^2+|E_y|^2+|E_z|^2)}.
$$

这一步的正面遗产是显式保存 `Ex/Ey/Ez/I`，以及意识到高 NA 需要 longitudinal component。其物理含义只是为每个保留平面波近似施加 `k · E = 0`。它没有实现 aplanatic lens 对偏振的旋转和混合。

### 3. 真正 Debye–Wolf/Richards–Wolf 算子的参照式

Debye 1909 研究焦点/焦线附近的波场；Wolf 1959 给出不局限于低角孔径的矢量 angular-spectrum image-field 表示；Richards 与 Wolf 随后专门推导满足 aplanatic/sine condition 系统的焦区矢量场。[Debye 1909](https://doi.org/10.1002/andp.19093351406)；[Wolf 1959, Part I](https://doi.org/10.1098/rspa.1959.0199)；[Richards & Wolf 1959, Part II](https://doi.org/10.1098/rspa.1959.0200)

忽略依赖符号约定的整体相位与 normalization，核心是参考球方向上的矢量叠加：

$$
\mathbf E(\rho,\varphi,z)=C
\int_0^{\alpha}\!\int_0^{2\pi}
\mathbf E_\infty(\theta,\phi)
\exp\!\left[ik\left(z\cos\theta+\rho\sin\theta\cos(\phi-\varphi)\right)\right]
\sin\theta\,d\phi\,d\theta,
$$

其中 `alpha = asin(NA/n)`；`E_infinity` 必须包含 pupil amplitude/phase、lens-to-reference-sphere mapping、polarization transport、aplanatic apodization（常见 sine-condition 约定下含 `sqrt(cos(theta))`）以及需要时的 interface transmission。

对圆对称 pupil，可先解析完成 azimuthal integral，得到一维 Bessel kernels：

$$
I_m(\rho,z)=\int_0^\alpha
A(\theta)W_m(\theta)
J_m(k\rho\sin\theta)
e^{ikz\cos\theta}\,d\theta,
\qquad m\in\{0,1,2\},
$$

其中 `W0, W1, W2` 分别含 `(1+cos(theta))sin(theta)`、`sin^2(theta)`、`(1-cos(theta))sin(theta)` 及所选 apodization。对 x 线偏振，Richards–Wolf 结构为：

$$
E_x\propto I_0+I_2\cos 2\varphi,\qquad
E_y\propto I_2\sin 2\varphi,\qquad
E_z\propto I_1\cos\varphi.
$$

因此一般高 NA x 线偏振焦场的 `Ey` 并不恒为零。历史 engine 强制 `Ey=0`，这足以证明它不是该 aplanatic vector focusing map。

Wolf 与 Li 还说明 Debye representation 是带适用条件的近似；小 angular aperture 极限下，一个简单充分条件归结为从几何焦点看 aperture 的 Fresnel number 远大于 1。[Wolf & Li 1981](https://doi.org/10.1016/0030-4018(81)90107-3) 因此未来 contract 必须记录并 gate applicability，而不能只用 `NA > 0.6` 选择类名。

## 三、实际实现和测试到了哪里

### 1. 有实现的部分

- propagating-only scalar ASM；
- 一个以 `NA` 为半径的离散方向余弦 mask；
- linear-x/linear-y 的 `Ez = -(kx Ex + ky Ey)/kz` 型补全；
- 单输出平面的 `Ex/Ey/Ez/I`、grid-count FWHM、central-window energy fraction 和 longitudinal fraction；
- high-NA selector、artifact writing 与 manifest wiring；
- 多波长循环，但每个波长相互独立；
- `validation.json` 中的输入标签和内部代数 consistency 值。

### 2. 历史测试真正检查的内容

`9a3d4aa` 的三个 engine tests 检查：

1. `fields.npz` 含 `Ex/Ey/Ez/I`、shape 正确、intensity finite、`0 <= eta_z <= 1`；
2. 对一个二值圆 pupil，NA 0.82 的 longitudinal fraction 大于 NA 0.2，并且所谓 `energy_conservation_relative_error < 1e-12`；
3. 对 uniform pupil、NA 0.05，纵向分量和 vector-vs-scalar summed intensity error 接近零。

另外存在 selector、feasibility、strategy tests，以及一个 fake integration test 检查 high-NA run 生成 `validation.json`。这些测试确认 plumbing 和历史公式的自洽性，不确认 Richards–Wolf 正确性。

所谓 energy conservation 只是把同一个数组先按分量求和，再按 `I = |Ex|^2+|Ey|^2+|Ez|^2` 重算后比较，数学上近乎恒等；它没有比较入射/出射 Poynting flux。uniform plane-wave fixture 只激活 FFT 的 DC bin，`Ez=0` 也是构造结果，不是独立 analytic reference。

### 3. 未实现、未测试的部分

- 参考球与 aplanatic sine-condition mapping；
- `NA = n sin(alpha)` 中的介质折射率；历史代码甚至把所有 `NA > 1` 静默裁剪；
- lens-induced polarization rotation、cross-polarized transverse field 和 circular/radial/azimuthal polarization；schema 接受 `RCP/LCP`，engine 却会落入 linear-x 的 `else` 分支；
- Debye `theta/phi` quadrature、axisymmetric `J0/J1/J2` reduction、FFT/CZT Debye mapping 或 chirp-z sampling；
- immersion/interface/stratified-medium transmission；
- axial focal volume、真实 focal shift、chromatic focal shift；历史 aggregate 对缺失的 `focal_shift_m` 用 0 代替；
- padding/aliasing、quadrature error、grid convergence、normalization convention 和 near-`kz=0` stability；
- Poynting flux、reciprocity、independent reference arrays 或 full-wave/measurement comparison；
- CPU/GPU same-operator parity；早期 `propagation.device` 没有进入 engine；
- achromatic phase/group-delay/group-delay-dispersion design 与连续带宽验证。

## 四、缺失与破损的依赖闭包

`234966d:src/metacraft/stress/radial_achromatic.py` 在 import time 要求下列六个模块：

```text
metacraft.optimization.radial_achromatic
metacraft.propagation.full_array_debye
metacraft.skills.metalens.radial_achromatic_design
metacraft.skills.metalens.radial_achromatic_library
metacraft.skills.metalens.radial_achromatic_schema
metacraft.skills.metalens.radial_grid
```

对每个对应 path 执行 `git log --all -- <path>` 均为空；在 `234966d`、`43f8858` 和 `368e0fd` 树中也都不存在。因此：

- `run_high_na_radial_achromatic_v013_stress` 从加入之日起就不能在提交树中完成 import；
- 它声明的 `run_radial_achromatic_optimizer`、`run_bounded_full_array_direct_debye_reference`、ring grid、target tensor、response tensor 和 initial design 不可从可达历史恢复；
- `radial_achromatic_bessel_cpu_metric`、`...cuda_metric`、`bessel_vector_debye_design_metric` 等只存在于 taxonomy、report 和 claim-policy 字符串中；
- CPU/CUDA tests 只调用独立的 usefulness JSON writer，并向它传入手写分数；没有执行 optimizer、Bessel contraction、Debye integral 或 CUDA tensor kernel；
- Fourier–Bessel ADR 本身明确写的是 deferred requirement，不是 capability record。

因此对这部分最准确的恢复结果是 **negative provenance**：保留意图和失败闭包，不编造遗失算法。不能根据函数名、metric label、profile 名或 `pass: true` stress summary 推断数值工作曾经完成。

## 五、为什么旧实现不具备 qualification

### 1. 物理模型不匹配

历史 engine 对已传播的 scalar plane spectrum 做 transverse projection；真正 Richards–Wolf 需要 pupil 到参考球的矢量映射、angular measure 和 aplanatic weights。最明显的可观察差异是历史 x-polarized 路径令 `Ey == 0`，而 Richards–Wolf 一般产生 `I2 sin(2 phi)` cross-polarized component。

### 2. 参数域错误或未声明

- 没有 refractive index，故 `NA` 和 angular aperture 混用；
- 静默 `clip(NA, 0, 0.999999)` 排除了 immersion objectives；
- `kz` 附近用 `1e-12` 截断，未给 error bound；
- RCP/LCP 被错误当作 linear-x；
- 只有一个平面，没有焦区 volume；
- sampling、padding、FFT normalization、shift 和 coordinate origin 都未形成 immutable contract。

### 3. 指标不构成外部验证

`energy_conservation_relative_error` 是重排同一组元素平方和；central-window efficiency 随 array shape 改变；FWHM 是连续 above-half samples 的整数宽度，没有 interpolation 或 disconnected-lobe policy；没有 input power/encircled-energy aperture 的物理定义。这些值最多是 diagnostic design metrics。

### 4. 没有 reference/accelerator 分离与 parity

Leutenegger 等人的一手工作说明，矢量 Debye integral 可以用 FFT 计算整个焦区，并用 CZT 改善输出采样和速度，但其前提仍是正确建立 transmitted/apodized reference-sphere field；“用了 FFT”不自动等于 Debye–Wolf。[Leutenegger et al. 2006](https://doi.org/10.1364/OE.14.011277)

Sherif 与 Török 给出的 Bessel/圆 prolate-spheroidal eigenfunction representation 可以比 direct numerical integration 更快，也可作为 inversion 的数学基础；可见“Bessel 加速”必须明确具体 reduction 与 error control，而不是 metric 名称。[Sherif & Török 2005](https://doi.org/10.1080/09500340512331309084)

历史树既没有 direct spherical quadrature golden reference，也没有 axisymmetric Bessel/FFT/CZT/GPU parity fixture，因而任何 accelerator claim 都不合格。

### 5. 没有完成科学或产品资格化

未发现与以下任一项闭合的证据：published analytic field values、independent vector solver、full-lens full-wave simulation、measured focal field、convergence study、device parity decision、applicability decision。旧代码的测试通过与 release-quality/physical-validation claim 是不同问题。

## 六、术语边界

### Debye–Wolf focusing

这是焦区矢量电磁场的物理表示：在满足适用条件时，对参考球/方向空间上的矢量波进行积分。Richards–Wolf 是 aplanatic high-NA 系统的经典具体化。它决定应计算什么。

### Radial parameterization

这是设计或离散化选择：把近似轴对称的 aperture/meta-atom map 组织成 rings/radial coordinate，以减少设计变量。它不等于 radial polarization，也不自动保证场严格轴对称；线偏振经过高 NA 聚焦会破坏焦斑的旋转对称性，已有直接实验研究。[Dorn, Quabis & Leuchs 2003](https://doi.org/10.1080/09500340308235246)

### Bessel / Fourier–Bessel acceleration

对圆对称或低 angular-mode pupil，可解析积分 azimuth angle，把二维 angular integral 降为含 `J_m` 的一维 radial integrals；或展开少量 angular harmonics 后分别做 Hankel/Fourier–Bessel transforms。这是同一 Debye–Wolf 算子的算法优化，不是另一个物理传播模型，也不是“Bessel beam”设计。Richards–Wolf 文献中的 `I0/I1/I2` 是 diffraction-integral 名称，其 kernel 是 ordinary Bessel `J0/J1/J2`，不要误读为 modified Bessel `I_nu`。

### Radial polarization

这是 pupil polarization 随 azimuth 指向径向的矢量模式。它与 radial grid 是不同概念。高 NA 聚焦时它可产生强 on-axis longitudinal electric field，可作为未来 vector fixture；不应从旧 `radial_achromatic` 文件名推断历史实现支持它。[Quabis et al. 2000](https://doi.org/10.1016/S0030-4018(99)00729-4)

### Achromatic metalens

这是跨频率的 aperture synthesis/material-response 问题，不是 Debye 积分本身。一个常见 target phase 形式为：

$$
\phi(r,\omega)=-\frac{\omega}{c}\sqrt{r^2+f^2}+C(\omega),
$$

meta-unit library 还必须覆盖所需 phase 与 dispersion；实验性 broadband achromatic designs 会同时控制 phase、group delay，必要时还包括 group-delay dispersion。[Shrestha et al. 2018](https://www.nature.com/articles/s41377-018-0078-x)；[Chen et al. 2018](https://www.nature.com/articles/s41565-017-0034-6)

因此可以用 Debye–Wolf evaluator 评估 high-NA achromatic candidate，但 evaluator 不会替代多波长 target、library dispersion、neighbor coupling、fabrication 与 validation。

### “德拜加速积分恢复法”

可达 Git 历史中不存在这个短语，也没有一个实现同时完成“Debye + accelerator + recovery”。建议仅作为 heritage workstream 的非权威中文别名：

```text
恢复 Debye–Wolf scientific contract
-> 建立 direct reference
-> 实现 axisymmetric Bessel 或 FFT/CZT accelerator
-> 以 convergence/parity fixtures 资格化 accelerator
```

如果“恢复”意指从目标焦场反演 pupil，那是独立 inverse-design/inversion 问题；旧 MetaCraft 没有实现它，不能借用本记录的“heritage recovery”一词来声称 inversion capability。

## 七、未来在 M5 下的重实现 seam

历史 M5 本地执行与数值计算规范（已删除路径 `docs/metacraft_next/specs/modules/m5_local_execution_numerical.md`）曾给出落点 `execution/numerical/finite_aperture_propagation/`。重实现应复用历史 M3/M5/M6 Work seam（已删除路径 `docs/metacraft_next/specs/foundation/ownership_architecture.md`），而不是复活 `metacraft.propagation.debye_wolf`。

建议责任分配：

| Owner | 应拥有 | 不应拥有 |
| --- | --- | --- |
| M3 | typed `FiniteAperturePropagationTask`；pupil/reference-sphere scientific semantics；要求的 field/metric；achromatic/radial route 语义 | Torch/CUDA device、FFT library、vendor session、qualification decision |
| M5 | 深模块 `finite_aperture_propagation`；exact contract 的 reference/accelerated execution；raw complex field、convergence 与 backend observations | route acceptance、focusing claim、release claim |
| M6 | contract hash、WorkPermit、reference/device qualification、evidence admissibility | 数值 kernel 私有实现或科学 metric derivation |

未来 `VectorDebyeWolfFiniteApertureContract` 至少固定：

- coordinate system、time/phase convention、FFT sign/normalization/shift；
- vacuum wavelength、medium index、`NA = n sin(alpha)` 和 reference-sphere geometry；
- pupil-to-sphere sine-condition mapping、apodization 与 polarization transport；
- polarization basis，包括 linear/circular/radial/azimuthal 的显式 schema；
- homogeneous/immersion/interface model 与 Fresnel coefficients；
- finite aperture、sampling、padding、evanescent policy、output `(x,y,z)` coordinates；
- reference algorithm、accelerator algorithm、dtype/device、tolerance 和 convergence rule；
- raw `Ex/Ey/Ez`，需要时 raw `Hx/Hy/Hz`，以及 Poynting-flux observation；
- applicability domain、failure semantics、contract/fixture/code hashes。

M5 应暴露一个深的 operator interface，而不是 `run_solver(config)` 或 route-specific `radial_achromatic_bessel_cuda_metric`。reference CPU quadrature、axisymmetric Bessel、general FFT/CZT 与 GPU device 可以共享同一物理 contract 和 artifact schema，但每个 accelerator/device 必须分别取得与 reference 的 qualification，不能因代码路径可运行就自动 promotion。

## 八、必须建立的验证 fixtures

以下 fixtures 是未来工作的准入条件，不是本次已完成项。

| Fixture | 主要断言 | 目的 |
| --- | --- | --- |
| `low_na_uniform_x_scalar_limit` | `alpha -> 0` 时收敛到独立标量 Airy/Lommel reference；cross/longitudinal terms 按理论消失 | 校验 normalization、phase sign 与低 NA 极限 |
| `aplanatic_uniform_x_high_na` | direct `theta/phi` quadrature 产生 Richards–Wolf `I0/I1/I2` 对称性；轴上只有 `Ex`，离轴 `Ey` 一般非零；`Ex` 对 x/y 均为偶，`Ey` 对 x/y 均为奇，`Ez` 对 x 为奇、对 y 为偶（允许整体相位/符号约定） | 防止重现旧 engine 的 `Ey == 0` 错误并捕获坐标/偏振 bug |
| `radially_polarized_on_axis` | `E_phi=0`；`E_rho` 的 `J1` kernel 使其轴上为零，`Ez` 的 `J0` kernel 可在轴上达到最大；与独立 published/direct reference 对照 | 校验空间变化 polarization transport |
| `azimuthally_polarized_on_axis` | `Ez=0`，regular input 产生 central null | 与 radial polarization 形成互补 fixture |
| `axisymmetric_bessel_vs_direct` | `J0/J1/J2` 一维 reduction 与高精度二维 spherical quadrature 在 complex field 上一致 | 资格化 Bessel acceleration |
| `low_mode_fourier_bessel_vs_direct` | 每个 angular mode、truncation remainder、mode-energy leakage 均可观测 | 实现历史 ADR 曾要求但未完成的 non-axisymmetric 扩展 |
| `fft_czt_vs_direct` | FFT/CZT output grid 上的 complex amplitude/phase 与 direct reference 一致，检查 padding/aliasing | 资格化 general fast-focus path |
| `immersion_na_gt_1` | 使用 `NA=n sin(alpha)`；不裁剪 NA；与 matched-index reference 一致 | 覆盖旧代码不可表达的 immersion domain |
| `stratified_interface` | Fresnel/interface mapping 与独立 stratified-medium reference 一致 | 把 homogeneous claim 与 interface claim 分开；可参考 [Török et al. 1995](https://doi.org/10.1364/JOSAA.12.000325) |
| `multi_wavelength_achromatic_target` | 各波长使用 exact material/pupil response；focal position、spot width 和 efficiency 分波长记录，不以离散点冒充连续带宽 | 分离 achromatic synthesis 与 Debye evaluation |
| `reference_cpu_vs_accelerator_device` | complex field、derived metrics、failure semantics 在 CPU reference、CPU accelerator、CUDA accelerator 间满足 activated tolerance | 资格化 device，而非只记录 backend 名称 |

所有 numerical fixtures 还必须做至少两级 grid/quadrature refinement，保存 complex-valued golden arrays、生成脚本 hash、来源论文/方程、absolute/relative tolerance 与 near-zero policy。比较应覆盖 complex field，而不只比较 FWHM 或一个 scalar objective。

最低 invariants：

- Maxwell transversality 在所声明的 homogeneous domain 内满足 tolerance；
- focal-field symmetries/antisymmetries 与输入 polarization 相符；
- input/output power 使用明确的 Poynting-flux surface 和 aperture definition；
- reference resolution 加密后 complex field 与主要 metrics 收敛；
- accelerator 对同一 contract 的差异可归因、可界定，不以不同 normalization 抵消；
- 改变 output sampling 不得改变物理 aperture 或悄悄改变 integration measure；
- 任何不满足适用条件、contract hash、dtype/device 或 convergence rule 的 run 均失败关闭。

## 九、恢复处置

应保留：

- 本记录中的 provenance、历史公式、negative evidence 和 qualification requirements；
- Git archive 中的 commits/blobs 与已有 run evidence；
- “高 NA 必须使用合格矢量模型”“reference 与 accelerator 必须 parity”“achromatic 与 propagator 是正交问题”这三个设计约束。

不应恢复到 active source：

- `DebyeWolfEngine` 的旧类名和实现；
- dangling `radial_achromatic.py` orchestration 壳；
- 仅作为字符串存在的 Bessel/CUDA metric sources；
- 以内部代数恒等式命名的 `energy_conservation` validation；
- 把 official/vendor example 当作验收 baseline 的规则。

未来实现必须从一手方程与新 contract 重新建立，不从旧 engine 复制物理声称。完成代码、fixtures、reference parity 与 M6 qualification 之前，MetaCraft Next 只能说“保留了 Debye–Wolf 重实现 seam 与 Research Record”，不能说已经支持 high-NA vector Debye、radial/Bessel acceleration 或 achromatic high-NA design。

## 一手来源

1. P. Debye, “Das Verhalten von Lichtwellen in der Nähe eines Brennpunktes oder einer Brennlinie,” *Annalen der Physik* 335, 755–776 (1909). [Publisher/DOI](https://doi.org/10.1002/andp.19093351406)
2. E. Wolf, “Electromagnetic diffraction in optical systems. I. An integral representation of the image field,” *Proceedings of the Royal Society A* 253, 349–357 (1959). [Royal Society/DOI](https://doi.org/10.1098/rspa.1959.0199)
3. B. Richards and E. Wolf, “Electromagnetic diffraction in optical systems. II. Structure of the image field in an aplanatic system,” *Proceedings of the Royal Society A* 253, 358–379 (1959). [Royal Society/DOI](https://doi.org/10.1098/rspa.1959.0200)
4. E. Wolf and Y. Li, “Conditions for the validity of the Debye integral representation of focused fields,” *Optics Communications* 39, 205–210 (1981). [Publisher/DOI](https://doi.org/10.1016/0030-4018(81)90107-3)
5. P. Török, P. Varga, Z. Laczik, and G. R. Booker, “Electromagnetic diffraction of light focused through a stratified medium,” *Journal of the Optical Society of America A* 12, 325–332 (1995). [Optica/DOI](https://doi.org/10.1364/JOSAA.12.000325)
6. M. Leutenegger, R. Rao, R. A. Leitgeb, and T. Lasser, “Fast focus field calculations,” *Optics Express* 14, 11277–11291 (2006). [Optica/DOI](https://doi.org/10.1364/OE.14.011277)
7. S. S. Sherif and P. Török, “Eigenfunction representation of the integrals of the Debye–Wolf diffraction formula,” *Journal of Modern Optics* 52, 857–876 (2005). [Publisher/DOI](https://doi.org/10.1080/09500340512331309084)
8. K. S. Youngworth and T. G. Brown, “Focusing of high numerical aperture cylindrical-vector beams,” *Optics Express* 7, 77–87 (2000). [Optica/DOI](https://doi.org/10.1364/OE.7.000077)
9. S. Quabis, R. Dorn, M. Eberler, O. Glöckl, and G. Leuchs, “Focusing light to a tighter spot,” *Optics Communications* 179, 1–7 (2000). [Publisher/DOI](https://doi.org/10.1016/S0030-4018(99)00729-4)
10. R. Dorn, S. Quabis, and G. Leuchs, “The focus of light—linear polarization breaks the rotational symmetry of the focal spot,” *Journal of Modern Optics* 50, 1917–1926 (2003). [Publisher/DOI](https://doi.org/10.1080/09500340308235246)
11. S. Shrestha, A. C. Overvig, M. Lu, A. Stein, C. Zheng, and N. Yu, “Broadband achromatic dielectric metalenses,” *Light: Science & Applications* 7, 85 (2018). [First-party article](https://www.nature.com/articles/s41377-018-0078-x)
12. W. T. Chen et al., “A broadband achromatic metalens for focusing and imaging in the visible,” *Nature Nanotechnology* 13, 220–226 (2018). [First-party article](https://www.nature.com/articles/s41565-017-0034-6)
