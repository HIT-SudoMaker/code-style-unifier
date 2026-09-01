# refractiveindex.info 数据导入 Ansys Lumerical FDTD：v0.0 研究结论

日期：2026-07-12
范围：Windows 上的 Ansys Lumerical FDTD；MetaCraft v0.0 的单波长、各向同性、线性 `n,k` 材料绑定。本文只使用 Ansys/Lumerical、refractiveindex.info 数据库仓库和数据库作者的数据论文等第一方资料。

## 结论摘要

refractiveindex.info 的数据可以导入 FDTD，但需要区分三个层次：

1. **数据入库**：MetaCraft 先把来源 YAML 固定成不可变的本地 `MaterialDatasetRevision`，保留原始字节、哈希、数据库版本和原论文引用；正式求解时不联网取数。
2. **求解器材料绑定**：v0.0 的严格单频路径应从固定数据中得到工作波长处的 `n + ik`，建立 FDTD 的 `(n,k) Material`。这是 Ansys 对单频源明确推荐的最小路径；完整表仍保留在 MetaCraft 中，供审计和未来宽带使用。[Ansys：单频 `(n,k)` 模型](https://optics.ansys.com/hc/en-us/articles/360034394654-Tips-for-using-the-n-k-material-model-in-FDTD)
3. **拟合/read-back**：如果使用完整表建立 `Sampled data`，脚本接口要求 `[frequency_Hz, complex_permittivity]`；FDTD 会把表拟合为时域可用的多系数模型，不能把“原始表已写入”当成“仿真实际采用值已验证”。必须分别读取原始表插值值和 FDTD 实际拟合值。[Ansys：`setmaterial`](https://optics.ansys.com/hc/en-us/articles/360034409654-setmaterial-Script-command)；[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)

因此，v0.0 不应把 GUI 导入成功或 `set("material", name)` 视作材料资格通过。正式资格至少需要：固定来源、范围检查、唯一 solver material 名、写入后 read-back、当前 FDTD build 指纹，以及对实际求解器索引的比较结果。

## 一、官方已经确认的事实

### 1. refractiveindex.info 的数据格式、单位和许可

- 官方数据库以 YAML 保存材料记录；线性光学数据可由色散公式或 `tabulated n`、`tabulated k`、`tabulated nk` 等表格组成。表格和公式中的波长统一使用 **微米**；`n` 和 `k` 无量纲。[数据库数据论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC10796781/)
- 一个记录可以包含公式与表格的组合，也可能把 `n`、`k` 分开列出。因此“文件是 YAML”不代表它能直接交给 FDTD。[数据库数据论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC10796781/)
- 数据文件带有 `REFERENCES`、`COMMENTS`，并可能带有 `CONDITIONS`/`SPECS` 等测量条件；具体数据的原始论文引用也应保留。[数据库 README](https://github.com/polyanskiy/refractiveindex.info-database)；[数据库数据论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC10796781/)
- 数据库采用 CC0 1.0，可复制、修改和再分发，包括商业用途；数据库 README 仍建议引用数据库论文，并在适当时引用具体数据的原始论文。[数据库 README](https://github.com/polyanskiy/refractiveindex.info-database)；[CC0 LICENSE](https://github.com/polyanskiy/refractiveindex.info-database/blob/main/LICENSE)
- 典型 `tabulated nk` 的三列为 `wavelength_um, n, k`，例如官方仓库中的 Johnson–Christy 金数据。[官方数据文件示例](https://github.com/polyanskiy/refractiveindex.info-database/blob/main/database/data/main/Au/nk/Johnson.yml)

### 2. FDTD 能直接导入哪些 refractiveindex.info YAML

Ansys 的 Sampled 3D Data 导入向导可直接读取 refractiveindex.info YAML，但官方当前只声明支持：

- `tabulated n`
- `tabulated nk`

向导会自动识别 index 与波长单位 `μm`。色散公式、仅 `tabulated k` 以及其他 YAML 组合不能因为来自 refractiveindex.info 就假定可直接导入。[Ansys：创建 sampled data material](https://optics.ansys.com/hc/en-us/articles/360034915093-Creating-new-sampled-data-materials-in-FDTD)

文本文件导入则使用三列波长/频率、实部、虚部，并由用户在向导中声明单位和列含义。GUI 路径适合人工验证，但它包含人工选择步骤，不适合作为 MetaCraft 的可重放 authoritative workflow。[Ansys：创建 sampled data material](https://optics.ansys.com/hc/en-us/articles/360034915093-Creating-new-sampled-data-materials-in-FDTD)

### 3. 脚本创建 Sampled data 的实际矩阵

Lumerical 脚本可以用 `addmaterial("Sampled data")` 和 `setmaterial` 创建材料。各向同性 sampled-data 矩阵有两列：

```text
frequency_Hz, complex_relative_permittivity
```

如果来源是复折射率，Ansys 明确要求使用：

```text
epsilon_r = (n + i*k)^2
```

各向异性 sampled-data 才使用四列（频率和三个复介电常数分量），不在 v0.0 范围内。[Ansys：`setmaterial`](https://optics.ansys.com/hc/en-us/articles/360034409654-setmaterial-Script-command)；[Ansys：`getmaterial`](https://optics.ansys.com/hc/en-us/articles/360034930053-getmaterial-Script-command)

`setmaterial` 的材料名和属性名必须与当前产品接受的字符串精确匹配；不可修改写保护的内置材料。[Ansys：`setmaterial`](https://optics.ansys.com/hc/en-us/articles/360034409654-setmaterial-Script-command)

### 4. Sampled data 在 FDTD 中不是原表直接求解

FDTD 不能直接在时域中使用任意的实验频散表。Sampled data 会被自动拟合为 generalized multi-coefficient model，然后仿真使用该拟合模型。[Ansys：改善材料拟合](https://optics.ansys.com/hc/en-us/articles/360034915053-Tips-for-improving-the-quality-of-optical-material-fits)

- `Tolerance` 是拟合目标 RMS error；官方表示多数情况下推荐设为 `0`，即寻找可得到的最佳拟合。
- `Max coefficients` 限制系数数量；默认值为 6。系数过少会欠拟合，过多也可能对噪声敏感并在局部产生更差结果。
- `make fit passive` 默认防止无增益数据被拟合成有增益模型。
- `improve stability` 默认约束系数以降低仿真发散风险。
- 拟合范围默认受 source bandwidth 影响，也可以单独指定；因此拟合身份必须绑定实际 source/fit range。[Ansys：改善材料拟合](https://optics.ansys.com/hc/en-us/articles/360034915053-Tips-for-improving-the-quality-of-optical-material-fits)；[Ansys：Material Explorer](https://optics.ansys.com/hc/en-us/articles/360034915033-Using-the-Material-Explorer-to-view-and-adjust-optical-material-models)

### 5. 三种读取回答不同问题

- `getmaterial(name, "sampled data")`：读回材料库中保存的原始 `[f, epsilon]` 表，适合验证写入内容。[Ansys：`getmaterial`](https://optics.ansys.com/hc/en-us/articles/360034930053-getmaterial-Script-command)
- `getindex(name, f)`：从材料原始数据的相邻频率线性插值得到复折射率；它不是 FDTD 拟合后实际使用的值。[Ansys：`getindex`](https://optics.ansys.com/hc/en-us/articles/360034409674-getindex-Script-command)
- `getfdtdindex(name, f, fmin, fmax)`：返回指定仿真频带下 FDTD 拟合模型实际使用的复折射率，且结果依赖 `Tolerance`、`Max coefficients` 和拟合频带。[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)

更严格的网格/时间步收敛研究还可以使用 `getnumericalpermittivity` 检查有限 `dt` 下的实际数值介电常数，但它属于 solver-run 数值收敛证据，不应与材料来源绑定混为一体。[Ansys：`getnumericalpermittivity`](https://optics.ansys.com/hc/en-us/articles/360034930093-getnumericalpermittivity-Script-command)

### 6. Python 自动化接口

Ansys 的 `lumapi.FDTD()` 可启动 Windows FDTD 会话；几乎所有 Lumerical script command 都能作为 session method 调用，包括 `addmaterial`、`setmaterial` 和 `getfdtdindex`。[Ansys：Python API 安装](https://optics.ansys.com/hc/en-us/articles/39744901602707-Installation-and-Getting-Started-Python-API)；[Ansys：script commands as methods](https://optics.ansys.com/hc/en-us/articles/360041579954-Script-Commands-as-Methods-Python-API)

## 二、MetaCraft v0.0 推荐契约

以下是工程建议，不是 Ansys 已替 MetaCraft 定义的产品规则。

### 1. 输入边界

v0.0 authoritative import 只接受：

1. 单个、各向同性的 `tabulated nk` 数据块；或
2. 明确标注为无吸收用途的 `tabulated n`，并由用户/路线显式确认 `k=0` 假设。

下列输入返回 diagnostic，不自动猜测：

- formula 1–9；
- 只有 `tabulated k`；
- 分离且采样网格不同的 `tabulated n` + `tabulated k`；
- 多个相互重叠的数据块；
- 张量、温度依赖、非线性 `n2`；
- 缺失 `k` 却未明确允许无损假设。

未来可以增加公式求值器和显式重采样契约，但不应把它们偷偷塞进 v0.0 导入器。

### 2. 本地不可变材料修订

下载/导入动作与正式求解动作分离。一次导入应生成：

```text
MaterialDatasetRevision
  source_kind = refractiveindex_info
  source_url
  upstream_revision_or_release
  retrieved_at
  raw_yaml_sha256
  raw_yaml_object_ref
  database_license = CC0-1.0
  database_citation
  original_references
  comments_conditions_specs
  data_type
  wavelength_unit = micrometer
  wavelength_min/max
  canonical_points[] = (wavelength_um, n, k)
  canonical_content_hash
```

正式 workflow 只能引用该本地修订，不得在运行 FDTD 时实时请求网站。这样上游文件更新、网络中断或 URL 失效都不会改变旧证据。

### 3. 解析和规范化

导入器必须在进入 FDTD 前完成：

- YAML 安全解析和允许字段/数据类型检查；
- 所有数值 finite；波长严格为正；`n`、`k` 符合当前被动材料政策；
- 波长点严格单调且无重复；若仅顺序相反，可确定性排序并记录变换 receipt；
- 明确工作波长 `lambda0_um` 位于闭区间内；禁止外推；
- 保存原始顺序，同时生成唯一 canonical table；
- 对插值坐标作出版本化决定，不能在波长线性与频率线性之间隐式切换。

为了与 Lumerical `getindex` 的定义对照，建议 v0.0 在 solver-binding qualification 中以频率为比较坐标：

```text
lambda_m = lambda_um * 1e-6
f_Hz = c0 / lambda_m
nk = n + 1j*k
epsilon_r = nk**2
```

转换后将频率确定性排序为升序再交给脚本接口。Ansys 示例未把升序声明为硬要求，因此这里是 MetaCraft 消除输入歧义的规范，而不是对 Ansys 的事实声明。

### 4. v0.0 首选：单频 `(n,k) Material` 绑定

因为 v0.0 的正式设计路径只有一个工作波长，首选流程是：

```text
固定 MaterialDatasetRevision
→ 在 lambda0 处按登记的插值政策得到 n0,k0
→ 创建唯一命名的 `(n,k) Material`
→ 写入 Refractive Index=n0、Imaginary Refractive Index=k0
→ FDTD source start=stop=lambda0
→ getmaterial read-back
→ getindex/getfdtdindex 在 f0 复核
→ 生成 SolverMaterialBindingQualification
```

这与 Ansys 对严格单频源的建议一致，并避免为了一个工作点引入不必要的全频带拟合误差。完整 `n,k` 表仍属于材料修订，不能只保存最终的 `n0,k0`。

建议材料名使用内容寻址且可读的格式，例如：

```text
mc_riinfo__<material_slug>__<dataset_slug>__<hash12>
```

创建前用 `materialexists` 检查：同名且 binding hash 相同可以复用；同名但内容不同必须失败，禁止覆盖。[Ansys：`materialexists`](https://optics.ansys.com/hc/en-us/articles/360034930113-materialexists-Script-command)

`getfdtdindex` 文档没有明确说明 `fmin == fmax` 在每个 FDTD build 上的行为。因此，退化单频参数必须作为目标 FDTD build 的资格 fixture 实测；若该 build 无法执行该 read-back，就标记该 build/binding 不合格，不能临时发明一个隐藏带宽。

### 5. 兼容路径：完整 `Sampled data` 绑定

未来宽带或需要完整频散时，采用：

```text
sampled = [f_Hz, (n + i*k)^2]
temp_name = addmaterial("Sampled data")
setmaterial(temp_name, "name", unique_name)
setmaterial(unique_name, "sampled data", sampled)
setmaterial(unique_name, fixed_fit_policy)
```

建议 v0.0 的 sampled-data 资格 policy 初始固定 `Tolerance=0`、`Max coefficients=6`、passive/stability 开启，但这只是可复核的起点，不代表 6 对所有材料都最优。若拟合未达到路线规定的 read-back 误差，结果应为 `unqualified`；不得自动无限增加系数、修改源数据或关闭稳定性约束。

Ansys 文档中的属性显示名存在单复数写法差异（例如 set 示例的 `max coefficients` 与 get 示例的 `max coefficient`），而属性名必须精确匹配。因此 adapter 在每个 solver build 的资格测试中应枚举/查询实际属性，并把 property-name map 纳入 solver fingerprint，不能假定字符串跨版本永远不变。

### 6. 两阶段 read-back gate

Sampled data 必须通过两个不同的比较：

1. **存储一致性**：`getmaterial(..., "sampled data")` 与 MetaCraft 生成的 `[f,epsilon]` 逐点/哈希一致，证明写入未错单位、列或符号。
2. **求解器实际响应**：
   - `getindex(name, f0)` 与 canonical source interpolation 比较；
   - `getfdtdindex(name, f0, actual_fmin, actual_fmax)` 与目标 `n0+ik0` 比较；
   - sampled/broadband 情况还要在整个实际 fit range 的登记采样点比较，不能只看中心点。

Lumerical 的 `Fit tolerance` 是内部 RMS 目标；MetaCraft 的 acceptance tolerance 是科学/工程验收门，两者不是同一概念。官方没有提供适用于所有材料和路线的统一 `n,k` 误差阈值，因此具体阈值应属于版本化的 route/material binding policy，并用代表性材料 fixture 校准，而不是写成平台永久常量。

### 7. 资格包最小内容

```text
SolverMaterialBindingQualification
  qualification_id
  material_dataset_revision_ref
  working_wavelength_um
  interpolation_policy_ref
  expected_n, expected_k
  solver_family = lumerical_fdtd
  solver_version_build
  lumapi_fingerprint
  solver_material_name
  solver_material_model = nk_single_frequency | sampled_data
  source_frequency_range
  fit_policy_ref | null
  stored_material_readback_ref
  getindex_readback_ref
  getfdtdindex_readback_ref
  numerical_permittivity_ref | null
  comparison_policy_ref
  result = qualified | unqualified | inconclusive
  content_hash
```

只有 `qualified` 且 solver/build、工作波长、材料修订、插值政策和 fit policy 全部命中时，才能用于 `simulation_validated_design_candidate`。名称相同或某次旧版本曾通过，都不能代替当前 binding qualification。

## 三、自动化边界

建议责任分配如下：

- **M2 材料与加工知识**：下载/本地导入、YAML 解析、来源与许可、canonical table、范围和插值政策。
- **M5 求解器执行与数值计算**：通过 `lumapi` 创建材料、设置 source、read-back 和保存 FDTD artifact。
- **M6 Rust 权威内核**：校验不可变引用、哈希、solver/build/profile 命中和 qualification 状态；Rust 不解释材料物理，也不自行插值。

MetaCraft 应走 `lumapi` 的 script-command methods，而不是驱动 GUI 点击导入向导。GUI direct-YAML import 可作为人工诊断/对照 fixture，不能成为唯一可重放实现。

## 四、必须失败关闭的情况

以下任一情况不得产生合格 binding：

- authoritative run 才联网获取数据；
- 上游 revision 未固定，或 raw YAML hash 不匹配；
- YAML 类型不在 v0.0 白名单；
- 工作波长超出数据范围或需要外推；
- 波长单位、频率转换、`k` 符号或 `epsilon=(n+ik)^2` 转换不明确；
- NaN/Inf、重复波长、冲突数据块或未声明的重采样；
- 缺失 `k` 时偷偷填零；
- 材料名冲突、覆盖已有不同内容，或只验证了名称存在；
- 写入表 read-back 不一致；
- `getfdtdindex` 与预期响应不满足登记容差；
- source/fit range 与 qualification 使用的范围不同；
- 修改 `Tolerance`、`Max coefficients`、passivity/stability 后仍复用旧 qualification；
- solver build、lumapi 或材料属性映射变化后继续复用旧 binding；
- 拟合出现增益、发散、明显局部伪峰，或 read-back 无法完成；
- 只保存 `.fsp` 或 screenshot，没有机器可读 read-back artifact；
- 把 `getindex` 的原始数据插值误称为 FDTD 实际拟合响应。

## 五、对正式 spec 的直接建议

v0.0 的 spec 可以保持精简，只锁定以下不变量：

1. 正式材料必须先固定为本地不可变修订；
2. v0.0 authoritative importer 只支持各向同性 `tabulated nk`，以及显式无损的 `tabulated n`；
3. 单频 FDTD 首选 `(n,k) Material`，完整表仍永久保留；
4. sampled-data 通过脚本写入时必须转换为 `[Hz, complex epsilon]`；
5. 名称存在不等于绑定合格；必须 read-back；
6. `getindex` 与 `getfdtdindex` 证据必须分开保存；
7. 未确认的单位、范围、插值、拟合或 solver build 一律失败关闭；
8. 未来增加公式求值、宽带拟合、各向异性或温度依赖时，只扩展 M2/M5 的 adapter 与 qualification policy，不改变 M6 的引用/哈希/状态边界。

这条路径既满足 v0.0 的单波长简洁性，也保留了未来宽带、消色差、高 NA 和其他求解器材料绑定的兼容接口。
