# MetaCraft v0.0：FDTD 与 CST 软件原生材料研究

日期：2026-07-12
范围：Ansys Lumerical FDTD 与 Dassault Systèmes SIMULIA CST Studio Suite 的软件内置、安装级和项目级原生材料。
资料边界：只使用 Ansys、Dassault Systèmes/CST 官方网页，以及本机 CST Studio Suite 2026 随安装提供的第一方 Python/VBA/产品帮助。本机帮助结论只代表该安装版本，不外推为所有 CST 版本的永久保证。

## 结论摘要

用户提出的第三类材料入口成立，但它不是一个可跨软件解释的通用材料数据源，而应被建模为两个互不相容的、带 solver 所有权的原生引用：

```text
solver_native/ansys_lumerical_fdtd
solver_native/dassault_cst_studio_suite
```

它们与“本地 YAML/CSV/TXT”和“从 refractiveindex.info 官方仓库下载并固化的数据”有本质区别：前两类由 MetaCraft 持有、解析并规范化材料数值；`solver_native` 只持有一个由指定 solver 在指定安装/项目上下文中解析的句柄。MetaCraft 不应假装拥有或理解其全部底层物理模型。

因此，v0.0 应采用以下原则：

1. 原生材料引用必须声明唯一 backend，并只能交给对应 adapter；不得把 Lumerical 名称传给 CST，反之亦然。
2. 不能只保存 `Si`、`Au` 等简称；必须保存并让用户确认 solver 显示的完整原生名称、catalog scope、项目/安装来源和适用频段。
3. 原生材料依赖 solver 版本、安装内容、用户可配置的材料库及项目状态。名称存在不是内容固定的证据。
4. Lumerical FDTD 可以分别查询数据库复折射率和 FDTD 拟合后复折射率；CST 2026 的公开/随安装 API 能力不对称，未确认有等价的通用“按频率读回求解器实际色散响应”接口。
5. v0.0 应只接受通过目标安装上的 adapter qualification 的白名单 capability；任何模型不明、版本不符、名称歧义、频段未验证或 read-back 不充分的情况都失败关闭。

## 一、推荐分类

### 1. 按来源所有权分类

```yaml
material_source_kind:
  - local_file              # MetaCraft 解析 YAML/CSV/TXT
  - refractiveindex_info    # 官方仓库记录，下载后固化
  - solver_native           # 目标 solver 自己解析
```

`solver_native` 再细分为：

```yaml
solver_native:
  backend:
    - ansys_lumerical_fdtd
    - dassault_cst_studio_suite
  catalog_scope:
    - installation_default
    - installation_configured
    - project_embedded
    - imported_native
    - installed_plugin
```

- `installation_default`：新项目由当前安装默认载入的只读/预置记录。
- `installation_configured`：安装或用户配置的材料库；可能被管理员替换、扩展或共享。
- `project_embedded`：已经进入 `.fsp` 或 `.cst` 项目的材料定义。
- `imported_native`：由 `.mdf`、CST Material Library 等原生机制导入，仍由目标 solver 解释。
- `installed_plugin`：随安装或额外安装的高级材料模型/插件。

这些 scope 不能相互替代。例如“默认库里存在”不能证明当前项目里已经加载的是同一记录；项目内同名材料也不能证明仍等于安装库版本。

### 2. 按物理/solver capability 分类

建议原生引用另外携带 capability，而不是把所有材料都降格为 `n,k`：

- `bulk_linear_sampled`：频率相关的体材料采样数据；
- `bulk_linear_analytic`：Dielectric、Conductive、Drude、Debye、Lorentz、Sellmeier、一般色散等解析/拟合模型；
- `bulk_anisotropic`：张量或对角各向异性；
- `surface_or_sheet`：二维表面电导、ohmic sheet、tabulated surface impedance；
- `ideal_or_boundary_semantics`：PEC 等求解器理想语义；
- `nonlinear_or_active`：χ²、χ³、Kerr、Raman、增益/激光等；
- `multiphysics`：热、机械、半导体、流体等与 EM 属性组合的材料；
- `unknown_native_model`：adapter 无法充分识别或验证的模型。

v0.0 的正式仿真路径建议只白名单 `bulk_linear_sampled` 和经过逐模型 fixture 验证的少量 `bulk_linear_analytic`。其余类别可被发现和展示，但不得自动作为通用线性体材料调度。

## 二、Ansys Lumerical FDTD

### 1. 官方材料库和模型能力

FDTD/MODE Material Database 可以管理材料，保存实验数据或参数化模型，并用 Material Explorer 查看随频率变化的折射率。新仿真会载入默认光学材料数据库；默认材料不能直接修改，需要复制后修改。默认库明确包含按资料来源区分的记录，例如 Palik、CRC、Johnson and Christy，同一化学材料因此可能有多条完整名称不同的记录。[Ansys：Material Database in FDTD and MODE](https://optics.ansys.com/hc/en-us/articles/360034394614-Material-Database-in-FDTD-and-MODE)

标准体/表面模型并不只有一张 `n,k` 表：官方列出 Sampled 3D、Sampled 2D、Dielectric、`(n,k)`、Conductive、Drude、Debye、Lorentz、Sellmeier、PEC 和 Analytic 等。Sampled 3D 会在指定频段自动拟合为多系数模型；拟合受 tolerance、max coefficients、passivity、stability、imaginary weight 和 fit range 影响。[Ansys：标准光学介电材料模型](https://optics.ansys.com/hc/en-us/articles/360034394634-Standard-optical-permittivity-material-models-in-FDTD-and-MODE)

高级模型还包括 χ²、χ³、Kerr/Raman、增益等，其中许多通过 Flexible Material Plugin Framework 随标准安装分发。官方明确警告 Material Explorer 经常不能显示这些模型的完整性质，网格器也可能只参考 Base Material。因此它们不能被 MetaCraft 无条件解释为普通 `n,k`。[Ansys：高级与自定义光学材料模型](https://optics.ansys.com/hc/en-us/articles/360034394734-Advanced-and-custom-optical-material-models-in-FDTD-and-MODE)

PEC 进一步说明为什么“查询到一个折射率”不等于掌握材料语义：Material Explorer/monitor 为便于报告会给出有限代理值，但 FDTD 引擎实际使用理想无限电导模型。[Ansys：标准光学介电材料模型](https://optics.ansys.com/hc/en-us/articles/360034394634-Standard-optical-permittivity-material-models-in-FDTD-and-MODE)

### 2. 脚本/Python 可查询、创建和读回什么

Lumerical 脚本接口提供：

- `materialexists(exact_name)`：确认精确名称是否存在；
- `addmaterial(type)`：列举可创建的类型并创建材料；类型字符串必须精确匹配；
- `setmaterial(name, property, value)`：设置未写保护材料，材料名和属性名必须精确匹配；
- `getmaterial(name, property)`：读取材料参数；Sampled data 可以读回 `[frequency_Hz, complex_permittivity]` 原始矩阵；
- `getindex(name, f)`：读取数据库层复折射率，官方说明在相邻频率间线性插值；
- `getfdtdindex(name, f, fmin, fmax)`：读取在指定仿真频带和拟合参数下 FDTD 实际采用的拟合复折射率；
- `exportmaterialdb` / `importmaterialdb`：用原生 `.mdf` 交换整个库、材料集合或单一材料。

来源：[addmaterial](https://optics.ansys.com/hc/en-us/articles/360034930013-addmaterial-Script-command)、[setmaterial](https://optics.ansys.com/hc/en-us/articles/360034409654-setmaterial)、[getmaterial](https://optics.ansys.com/hc/en-us/articles/360034930053-getmaterial-Script-command)、[getindex](https://optics.ansys.com/hc/en-us/articles/360034409674-getindex-Script-command)、[getfdtdindex](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)、[exportmaterialdb](https://optics.ansys.com/hc/en-us/articles/360038629273-exportmaterialdb-Script-command)。

Python `lumapi.FDTD()` 启动明确的 FDTD 产品会话，脚本命令通常可以作为 session 同名方法调用。[Ansys：Script Commands as Methods](https://optics.ansys.com/hc/en-us/articles/360041579954-Script-Commands-as-Methods-Python-API)、[Ansys：Python API 安装与启动](https://optics.ansys.com/hc/en-us/articles/39744901602707-Installation-and-Getting-Started-Python-API)

最小资格验证应同时保留两种响应：

```python
assert fdtd.materialexists(native_name) == 1
database_nk = fdtd.getindex(native_name, frequency_grid_hz)
fdtd_nk = fdtd.getfdtdindex(
    native_name,
    frequency_grid_hz,
    simulation_fmin_hz,
    simulation_fmax_hz,
)
```

`database_nk` 与 `fdtd_nk` 回答的是不同问题，不能只保存前者后声称是 FDTD 实际使用值。绑定到几何后还应读回对象的 `material` 属性，确认仍是精确完整名称。

### 3. 是否依赖版本/安装

是，而且是明确的强依赖：

- 默认数据库位于版本化安装目录的 `defaults` 下；
- 管理员可以替换默认项目/数据库，影响以后新建的项目；
- 默认材料写保护并不意味着跨安装内容不可变；
- 项目可以携带复制、修改或导入的材料；
- 插件模型及 solver 拟合实现会随安装能力和发行版变化。

官方目录与修改流程见 [Material Database in FDTD and MODE](https://optics.ansys.com/hc/en-us/articles/360034394614-Material-Database-in-FDTD-and-MODE)。因此 `native_name` 不是不可变 ID，必须与产品 release/build、安装/模板来源、项目 artifact 和数值 read-back 一起固定。

## 三、Dassault Systèmes CST Studio Suite

### 1. 官方材料库和模型能力

Dassault Systèmes 官方说明 CST Studio Suite 自带材料模型库，覆盖低频磁性材料、高频/微波介质和有损金属，并包含厂商材料；库会定期更新，也可以扩展并在团队间共享。[SIMULIA Community：CST Studio Suite Learning Resources，Material Library](https://3dswym.3dexperience.3ds.com/wiki/simulia-community/cst-studio-suite-learning-resources_zRjRyuPSQamZBLtbvTyEIQ)

官方产品页还说明 CST 的模型范围包括光子/等离激元、铁磁、二次电子发射和生物加热；光学应用页明确说材料库包含光学频率材料模型。[CST 电磁设计环境](https://www.3ds.com/products/simulia/cst-studio-suite/electromagnetic-design-environment)、[CST 光学器件仿真](https://www.3ds.com/products/simulia/electromagnetic-simulation/optical-device)

本机 CST Studio Suite 2026 第一方帮助进一步确认：高频材料支持 Normal/Anisotropic、导电/有损金属、常数损耗角、Debye/共振/一般色散、冷等离子体、偏置 ferrite/plasma、非线性、空间变化、表面阻抗、thin panel、温度相关等大量模型；而且部分模型只被特定 solver 支持。例如若干表面阻抗模型只支持 transient solver 与 tetrahedral frequency-domain solver，不同 solver 对 thin-panel 层类型、对称性和方向约束也不同。

本机第一方证据：

```text
C:\Program Files\CST Studio Suite 2026\Online Help\mergedProjects\3D\special_overview\special_overview_material_overview_hf.htm
C:\Program Files\CST Studio Suite 2026\Online Help\mergedProjects\VBA_3D\special_vbalayer\special_vbalayerolayer_object.htm
```

这意味着 CST 的“软件材料”不仅绑定 CST 产品，还可能绑定 CST 内的 problem type、active solver 和材料 set。仅凭一个库名称不能推出所有 CST solver 都可使用。

### 2. Python/VBA 可查询、创建和读回什么

CST Studio Suite 2026 随安装的 Python 教程说明：Python API 可打开/新建 MWS 项目，通过 `prj.model3d.add_to_history(header, vba_code)` 执行建模 VBA；教程给出用 `Material.Reset/Name/Folder/Type/Rho/ThermalConductivity/Epsilon/Mu/Sigma/TanD/TanDFreq/Create` 创建材料的完整示例。Python API 也能取得项目 tree、active solver name 和当前 Design Environment version。

本机第一方证据：

```text
C:\Program Files\CST Studio Suite 2026\Online Help\PythonTutorial\3d_simulation_structure_modeling.html
C:\Program Files\CST Studio Suite 2026\Online Help\Python\source\cst.interface.html
```

VBA `MaterialLibrary` 对象提供：

- `GetMaterialListFromLibrary()`：返回逗号分隔的全部库材料名称；
- `GetAllMaterialsContainingString(substr)`：按名称过滤；
- `LoadMaterialFromLibrary(matName, folderName, Replace)`：从库载入当前 Modeler，并返回成功/失败；
- `UpdateMaterialPropertiesFromLibrary(...)`、`UpdateAllMaterialsFromLibrary()`；
- `SaveMaterialToLibrary(matName, Replace)`。

VBA `Material` 对象对当前项目材料提供：

- `GetNumberOfMaterials`、`GetNameOfMaterialFromIndex`、`Exists`；
- `GetTypeOfMaterial`、`IsBackgroundMaterial`；
- `GetEpsilon`、`GetMu`、`GetSigma`、`GetSigmaM`；
- `GetCorrugation`、`GetOhmicSheetImpedance`；
- `GetRho`、热学/力学等若干多物理属性。

本机第一方证据：

```text
C:\Program Files\CST Studio Suite 2026\Online Help\mergedProjects\VBA_3D\special_vbalayer\materiallibrary_object.htm
C:\Program Files\CST Studio Suite 2026\Online Help\mergedProjects\VBA_3D\special_vbalayer\special_vbalayerolayer_object.htm
```

加载 GUI 的第一方帮助还显示：一个库材料可以包含多个面向不同 problem type 的 material set；界面展示的是当前 active problem type 对应的 type/attributes，并允许配置材料库位置。

```text
C:\Program Files\CST Studio Suite 2026\Online Help\mergedProjects\3D\common_general\common_general_load_from_material_library.htm
C:\Program Files\CST Studio Suite 2026\Online Help\mergedProjects\3D\common_general\common_general_add_to_material_library.htm
```

### 3. CST read-back 的已确认限制

本机 2026 `Material` API 的 Query 部分能读回基础配置值，但没有列出以下 Lumerical 等价能力：

- 没有确认一个公开、通用的 `getindex(material, f)`；
- 没有确认一个公开、通用的“按 active solver 和仿真频带返回求解器拟合后复介电常数/折射率”；
- 没有确认从 Material Library 直接读回稳定 UUID、官方 revision/hash、文献来源或整个色散模型的规范化机器表示；
- Query 部分没有完整对称地暴露所有色散、非线性、surface/thin-panel 设置。

因此，v0.0 不得把 `GetEpsilon/GetMu/GetSigma` 当作任意 CST 色散材料的完整等价 read-back。对于复杂材料，最可靠的最小语义是“在固定 CST 版本/项目/problem type/active solver 中，精确名称的原生材料成功载入、类型可识别、绑定读回一致”，而不是“MetaCraft 已提取了一个可移植 `n,k` 数据集”。

CST 安装目录中的 `.mtd` 文件能显示材料定义，但公开资料未确认该文件格式是稳定的跨版本 API；v0.0 不应自行解析 `.mtd` 作为 authoritative contract，也不应据此假设可自由跨 solver 复制。

### 4. 是否依赖版本/安装

是：

- 官方说明库记录会定期更新；
- 材料库可以配置位置、扩展和团队共享；
- 本机库随版本安装在 `C:\Program Files\CST Studio Suite 2026\Library\Materials`；
- 同一库记录可有多个 problem-type material set；
- 模型适用性依赖 active solver。

所以 CST 的 `native_name` 必须与 Design Environment version、install root/library path、project type、active solver、project artifact 和载入后 read-back 一起固定。

## 四、为什么只能绑定到对应 solver

这不是产品命名偏好，而是物理语义和可复现性的边界：

1. **解析器所有权不同**：`.mdf`、Lumerical plugin、CST Material Library/material set 由各自产品解释，MetaCraft 没有一个经官方保证的跨产品中间表示。
2. **模型集合不同**：两边都包含表面、理想边界、非线性和高级色散模型，不能总是无损转成体材料 `n,k`。
3. **求解器处理不同**：Lumerical Sampled data 会按仿真带宽拟合；CST 的模型支持和约束会随 transient/frequency-domain/TLM/integral-equation 等 solver 改变。
4. **查询语义不同**：Lumerical 明确区分数据库响应与 FDTD 拟合响应；CST 已确认的公开/安装 API 没有提供完全等价的通用响应查询。
5. **安装状态不同**：默认库、插件、用户扩展和配置路径都是本机/版本状态的一部分。
6. **名称空间不同**：相同显示名不意味着相同来源、模型、单位、拟合或有效频段。

因此，不允许 `backend` 回退或自动转换。若用户希望同一物理材料同时用于 FDTD 与 CST，应建立两个分别确认和资格验证的 `SolverNativeMaterialBinding`；如果要求跨 solver 数值一致性，应改用 MetaCraft 持有的本地/官方仓库数据源，并由两个 adapter 各自构建材料，而不是复用某一 solver 的原生记录。

## 五、建议的最小 v0.0 contract

```yaml
kind: solver_native
backend: ansys_lumerical_fdtd | dassault_cst_studio_suite

native_locator:
  catalog_scope: installation_default | installation_configured | project_embedded | imported_native | installed_plugin
  exact_name: "..."
  folder_or_library: null       # CST 可用；不允许作为名称猜测
  native_record_id: null        # 官方没有稳定 ID 时必须为 null，不伪造

runtime_pin:
  product: "..."
  release_or_de_version: "..."
  install_root: "..."
  project_type: "FDTD | MWS | ..."
  active_solver: "..."
  project_or_template_sha256: "..."
  library_snapshot_sha256: null # 能稳定导出/固定时填写；否则明确为 null

declared_use:
  capability: bulk_linear_sampled | bulk_linear_analytic | ...
  frequency_min_hz: ...
  frequency_max_hz: ...
  anisotropy_component: null

qualification:
  adapter_version: "..."
  exact_name_exists: true
  loaded_or_resolved: true
  resolved_type: "..."
  bound_object_material_readback: "..."
  database_response_artifact: null
  solver_response_artifact: null
  core_property_readback_artifact: null
  result: qualified | unqualified | inconclusive
  qualified_at: "..."
```

说明：

- SHA-256、qualification 状态和这些字段名是 MetaCraft 的工程建议，不是 Ansys/CST 官方 ID。
- FDTD 的 `database_response_artifact` 应记录固定频率网格的 `getindex`；`solver_response_artifact` 应记录相同网格和实际频带的 `getfdtdindex`。
- CST v0.0 若不能取得 solver 频率响应，应保持 `solver_response_artifact: null`，不得用基础 `GetEpsilon` 冒充。只有 route policy 明确允许“原生黑盒绑定”且相应 model/solver fixture 已通过时才能 `qualified`；否则为 `inconclusive` 并拒绝正式仿真。
- 用户确认的对象应是完整 `native_locator + runtime_pin + declared_use`，而不只是材料显示名。

## 六、失败关闭条件

以下任一情况不得自动回退到同名、相似或“最常用”材料：

- `backend` 与当前 adapter 不一致；
- solver 未安装、不能启动、许可证不可用或版本无法读回；
- 当前 release/build、install root、library path、项目模板或 active solver 与 qualification 不同；
- 精确完整名称不存在、存在歧义，或只有 `Si/Au/Glass` 等别名；
- catalog scope 不明确，或项目内同名材料与安装库来源未区分；
- 用户未确认具体记录和适用条件；
- 请求频段/工作波长未声明，或超出已验证频段；
- 模型类别未知，或请求把 surface、PEC、非线性、active/plugin 材料走普通线性体材料路径；
- 各向异性分量/problem type/material set 未确定；
- 材料类型不受当前 active solver 支持；
- 载入/绑定失败，`Replace` 会覆盖不同内容，或绑定后材料名 read-back 不完全一致；
- 数值 read-back 出现 NaN/Inf、明显非物理值或与固定 qualification artifact 不符；
- Lumerical 的拟合频带、max coefficients、tolerance、passivity/stability 等发生变化，或 `getfdtdindex` 未通过验收；
- CST 复杂色散材料只有基础常数 read-back，却被声称为已经验证完整频率响应；
- 试图解析未承诺稳定的原生私有文件格式来绕过 solver；
- 旧版本 qualification 被拿到新版本/新安装/新项目直接复用。

## 七、FDTD 与 CST 的关键差异

| 能力 | Lumerical FDTD | CST Studio Suite 2026（已确认） |
|---|---|---|
| 原生库定位 | Material Database，默认库随新项目载入 | Material Library，可配置、扩展、共享，并载入 Modeler |
| 精确存在性 | `materialexists(name)` | `Material.Exists(name)`；库侧可列名称后载入 |
| 创建 | `addmaterial` + `setmaterial` | Python 执行 Material VBA 或直接调用动态 VBA 对象 |
| 库名称枚举 | 公开资料未确认稳定的机器枚举 API | `GetMaterialListFromLibrary()` 已确认 |
| 原始采样表 read-back | `getmaterial(..., "sampled data")` | 未确认通用对称接口 |
| 数据库频率响应 | `getindex(name, f)` | 未确认通用等价接口 |
| 求解器实际/拟合频率响应 | `getfdtdindex(name, f, fmin, fmax)` | 未确认通用等价接口 |
| 基础 EM 常数 read-back | `getmaterial` 按精确属性名 | `GetEpsilon/GetMu/GetSigma/GetSigmaM` |
| solver 内部差异 | FDTD 拟合与其他 Lumerical solver 的拟合命令不同 | material set 和模型支持直接依赖 problem type/active solver |
| 复杂模型显示限制 | 高级/plugin 模型的 Explorer 可能不完整 | Query API 未完整对称暴露所有色散/非线性模型 |

## 八、公开资料无法确认的项目

以下内容必须保持 `unknown`，不能由 MetaCraft 猜测：

- 两个产品是否为每条原生材料提供跨版本稳定、机器可读且公开的 UUID/revision/hash；目前未找到。
- Lumerical 默认同名记录是否在所有发行版中保持逐字节/逐数值不变；官方没有此保证。
- Lumerical `.mdf` 是否确定性序列化、是否适合作为跨版本内容寻址格式；公开资料未确认。
- Lumerical 可机器返回当前完整材料名称列表和全部属性 schema 的稳定正式 API；`?getmaterial`/`?addmaterial` 主要是显示查询。
- Lumerical `getindex` 在原始有效范围外的外推规则；不应依赖未说明外推。
- CST Material Library 的稳定记录 ID、库 revision/hash 和正式 schema；公开资料与本机帮助未给出。
- CST 对任意复杂材料按频率读回数据库响应及当前 solver 实际响应的通用 Python/VBA API；本机 2026 帮助未找到。
- CST `.mtd` 格式的跨版本兼容性、稳定性和再分发权利；不应把安装文件可读等同于公共数据格式授权。
- CST Python 对 VBA `double_ref` 查询的跨版本统一调用形式；应以目标版本 adapter fixture 实测，不在 contract 中硬编码未经验证的调用约定。

## 九、对产品决策的直接建议

用户提出的“三种入口”可正式写为：

1. `local_file`：本地 YAML/CSV/TXT，由 MetaCraft 解析、规范化和固化；
2. `refractiveindex_info`：从官方仓库导入后固化，由 MetaCraft 持有原始记录、引用和 hash；
3. `solver_native`：由指定 solver 安装/项目解析，分成 `ansys_lumerical_fdtd` 与 `dassault_cst_studio_suite` 两个互斥 backend。

第三类的产品承诺应是“可审计地调度指定 solver 中的指定原生记录”，不是“把软件材料库转换成 MetaCraft 通用数据库”。v0.0 只要把 solver ownership、完整名称、runtime pin、用户确认、read-back/qualification 和失败关闭做好，就能既利用软件自带材料，又不制造跨 solver 可移植性的错误承诺。
