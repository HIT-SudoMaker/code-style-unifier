# Lumerical 索引读取语义（getindex / getfdtdindex 及相关入口）：研究结论

日期：2026-07-26
工单：01 — Lumerical index-read semantics
范围：Ansys Lumerical FDTD 的脚本/Python API 折射率读取入口点的返回语义与可调用前提；服务于 MetaCraft 在 355 nm / 400 nm 单波长下对 "Si3N4 (Silicon Nitride) - Luke"、"SiO2 (Glass) - Palik" 类材料采集 solver-native 折射率样本的时机决策（qualification 时 vs 每 brief 时）。本文只使用 Ansys/Lumerical 第一方资料（optics.ansys.com Knowledge Base 与脚本命令参考页）。

## 问题

各 Lumerical 脚本/API 索引读取入口点分别返回什么？调用它们需要什么前提？具体分六个子问题：

1. `getindex` 与 `getfdtdindex` 谁返回材料库表格数据、谁返回 FDTD 网格实际使用的多系数拟合？
2. 两者是否需要活的 FDTD 仿真区域/已配置频率范围/打开的工程/正在运行的分析，还是可以在裸 `lumapi.FDTD(hide=True)` 会话中调用？
3. 返回形状与单位约定（复折射率还是分离 n/k、随频率的数组、Hz 还是波长）？
4. 多系数拟合是否附带可与样本一起记录的误差/RMS 指标？
5. `getfdtdindex` 的返回值是否依赖 fmin/fmax 拟合跨度，从而样本只对采样时的跨度有效？
6. 其他相关入口点（`getmaterial`、Material Explorer、grating 类查询等）。

## 结论摘要

- `getindex` 读的是**材料库原始表**（相邻频点线性插值），`getfdtdindex` 读的是**FDTD 求解实际使用的材料拟合**（在指定频率跨度上重新计算 best fit 后取值）。两者互为官方推荐的"实验数据 vs 仿真拟合"对照对。[Ansys：`getindex`](https://optics.ansys.com/hc/en-us/articles/360034409674-getindex-Script-command)；[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)
- 两者都是**材料数据库函数**：全部输入（材料名、f、fmin、fmax）由调用者显式给出，官方 Python 示例在刚创建的 `lumapi.FDTD()` 会话里、未添加任何仿真对象、未加载任何工程的情况下直接调用 `getfdtdindex`。新建仿真自动加载默认材料库，因此裸会话即可读默认材料。[Ansys：Script Commands as Methods](https://optics.ansys.com/hc/en-us/articles/360041579954-Script-Commands-as-Methods-Python-API)；[Ansys：Material Database in FDTD and MODE](https://optics.ansys.com/hc/en-us/articles/360034394614-Material-Database-in-FDTD-and-MODE)
- 返回值是**单个复数折射率序列**（对 f 逐点），频率一律为 **Hz**；要介电常数需自行平方（`eps = n^2`）。各向异性材料按可选 `component` 参数一次取一个对角分量。[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)
- 拟合的**目标 RMS（Tolerance）与 Max coefficients 是材料属性**，可经 `setmaterial`/`getmaterial` 读写；**实际达到的 RMS** 在 FDTD/MODE 侧只有 Material Explorer（GUI）文档化展示（Standard/Weighted RMS error、Number of coefficients），FDTD 脚本侧没有文档化的"读取已达 RMS"命令；只有 Finite-Element-IDE（CHARGE/HEAT/DGTD/FEEM）路径文档化了 `get("standard rms error")`。[Ansys：材料拟合技巧](https://optics.ansys.com/hc/en-us/articles/360034915053-Tips-for-improving-the-quality-of-optical-material-fits)；[Ansys：Material Explorer](https://optics.ansys.com/hc/en-us/articles/360034915033-Using-the-Material-Explorer-to-view-and-adjust-optical-material-models)；[Ansys：脚本创建/修改光学材料](https://optics.ansys.com/hc/en-us/articles/360034919193-Creating-and-modifying-optical-materials-from-a-script)
- `getfdtdindex` 的返回值**依赖 fmin/fmax**（拟合在该跨度上重算）并依赖材料当时的拟合参数；因此一个 getfdtdindex 样本只对 `(材料数据修订, Tolerance, Max coefficients 及高级拟合开关, fmin, fmax)` 这一整组条件有效。`getindex` 不含跨度参数，样本与跨度无关。[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)

## 一、按子问题的回答

### 1. getindex = 材料库表格；getfdtdindex = FDTD 实际使用的拟合

`getindex` 页原文："Returns the complex refractive index of a material in the material database. The refractive index at the specified frequency is linearly interpolated from the neighboring frequencies where the data is available."——即返回材料库中登记的原始（表格/模型）数据在指定频率处的线性插值，官方示例把它标注为 `# get experimental data`。[Ansys：`getindex`](https://optics.ansys.com/hc/en-us/articles/360034409674-getindex-Script-command)

`getfdtdindex` 页原文："Returns the complex refractive index of a material in the database with material fit that will be used in a simulation in FDTD."，并说明 "you can specify frequency range, and the fitting routine will find a best fit of the material data over that range. The refractive index evaluated at the specified frequencies is then returned."——即先在 [fmin, fmax] 上执行与仿真相同的多系数拟合，再在 f 处取值；官方示例标注为 `# get FDTD fit of experimental data`。[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)

`getnumericalpermittivity` 页进一步确认拟合链条：有限时间步 dt 下 FDTD 实际数值介电常数满足 `lim(dt→0) eps_r(w,dt) = n^2(w)`，"where n(ω) is the refractive index returned by the script function getfdtdindex, or shown in the Materials Explorer"。即 `getfdtdindex` = Material Explorer 展示的拟合 = 求解在 dt→0 极限下使用的模型；若还要包含有限 dt 的数值效应，用 `getnumericalpermittivity`。[Ansys：`getnumericalpermittivity`](https://optics.ansys.com/hc/en-us/articles/360034930093-getnumericalpermittivity-Script-command)

### 2. 可调用前提：裸 lumapi.FDTD(hide=True) 会话即可，不需要仿真区域/运行

三条第一方证据：

1. **签名自足**：两命令的全部输入都由调用者显式提供（`getindex("materialname", f)`；`getfdtdindex("materialname", f, fmin, fmax)`），命令页没有任何"需要仿真区域/光源/已运行"的前提说明；拟合跨度不是从工程里的 source 读取，而是参数传入。[Ansys：`getindex`](https://optics.ansys.com/hc/en-us/articles/360034409674-getindex-Script-command)；[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)
2. **官方裸会话示例**：Python API "Script Commands as Methods" 页的第一个示例在 `with lumapi.FDTD() as fdtd:` 里**不添加任何对象、不加载任何文件**，直接 `fdtd.getfdtdindex("Au (Gold) - CRC", f_range, np.min(f_range), np.max(f_range))`，随后用解析函数 `stackrt` 算薄膜透射——整个流程无 FDTD 区域、无求解。该页同时声明 "Almost all script commands in the Lumerical Scripting Language can be used as methods on your session object in Python."。[Ansys：Script Commands as Methods](https://optics.ansys.com/hc/en-us/articles/360041579954-Script-Commands-as-Methods-Python-API)；`hide=True`、`filename` 可选等构造参数见 [Ansys：Session Management - Python API](https://optics.ansys.com/hc/en-us/articles/360041873053-Session-Management-Python-API)
3. **默认材料库随新仿真加载**："When creating a new simulation, the default database will be loaded."——裸会话（等价于新建空工程）即含默认光学材料库，无需先打开任何 .fsp。[Ansys：Material Database in FDTD and MODE](https://optics.ansys.com/hc/en-us/articles/360034394614-Material-Database-in-FDTD-and-MODE)

旁证：同族的 `getnumericalpermittivity` 页明确 "the script function does not require a calculation being performed beforehand"（正因如此才要求用户手工指定是否 BFAST）。[Ansys：`getnumericalpermittivity`](https://optics.ansys.com/hc/en-us/articles/360034930093-getnumericalpermittivity-Script-command)

对 MetaCraft 的两种场景：**qualification 探针（有 fixture FDTD 区域）与 per-brief 材料绑定（裸会话）都满足调用前提**；fixture 区域对这两条命令没有增值——它们不读区域，也不读 source 带宽。唯一的真实前提是：材料名当时存在于该会话的材料库（默认材料天然存在；自建材料须先 `addmaterial`/`setmaterial` 写入，且拟合参数取材料当时值）。存在性用 `materialexists` 检查。[Ansys：`materialexists`](https://optics.ansys.com/hc/en-us/articles/360034930113-materialexists-Script-command)

### 3. 返回形状与单位约定

- **复折射率单值序列**，不是分离的 n/k：官方明示 "The getfdtdindex and getindex functions always return the material index, so we must apply eps = n^2 to get the permittivity."；示例用 `real(n_exp)`/`imag(n_exp)` 拆出 n、k。[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)
- **频率单位 Hz**："Frequency f is in Hz"（getindex）；"All frequency units are in Hz"（getfdtdindex）。波长须自行换算 `f = c/lambda`（示例：`source_min_f=c/700e-9`）。[Ansys：`getindex`](https://optics.ansys.com/hc/en-us/articles/360034409674-getindex-Script-command)
- **f 可为标量或向量**，返回随 f 逐点的数组（脚本示例 100 点、Python 示例 500 点）。[Ansys：`getindex`](https://optics.ansys.com/hc/en-us/articles/360034409674-getindex-Script-command)；[Ansys：Script Commands as Methods](https://optics.ansys.com/hc/en-us/articles/360041579954-Script-Commands-as-Methods-Python-API)
- **各向异性**：可选第 3/第 5 个参数 `component`（1、2、3 = x、y、z 分量，默认 1），一次调用返回一个分量，不返回张量。[Ansys：`getindex`](https://optics.ansys.com/hc/en-us/articles/360034409674-getindex-Script-command)；[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)
- Python 侧的精确 numpy 形状（行/列向量）没有文档化；官方示例把 `getfdtdindex` 的返回 `np.transpose` 后才交给 `stackrt`，提示默认是列样矩阵。adapter 不应假定形状，应按数值内容归一化。[Ansys：Script Commands as Methods](https://optics.ansys.com/hc/en-us/articles/360041579954-Script-Commands-as-Methods-Python-API)

### 4. 拟合误差/RMS 指标的可记录性

- **Tolerance 的定义就是目标 RMS**："Tolerance specifies the target RMS error between the experimental data and the calculated model."；拟合例程用最少系数使 RMS 低于 Tolerance，达不到时取 RMS 最小的模型。Sampled data 材料默认 Tolerance=0.1、Max coefficients=6。[Ansys：材料拟合技巧](https://optics.ansys.com/hc/en-us/articles/360034915053-Tips-for-improving-the-quality-of-optical-material-fits)
- 这两个拟合参数是**材料属性**，脚本可写可读：`setmaterial(matName,"max coefficients",2)`（set 侧示例）、`getmaterial(matName,"max coefficient")`（get 侧示例；注意两页单复数拼写不一致，属性名须以 `?getmaterial("name")` 实测枚举为准）。[Ansys：`setmaterial`](https://optics.ansys.com/hc/en-us/articles/360034409654-setmaterial-Script-command)；[Ansys：`getmaterial`](https://optics.ansys.com/hc/en-us/articles/360034930053-getmaterial-Script-command)
- **实际达到的 RMS**：Material Explorer 的 Fit analysis 面板文档化展示 "Standard RMS error"、"Weighted RMS error"、"Number of coefficients"——这是 GUI 展示。[Ansys：Material Explorer](https://optics.ansys.com/hc/en-us/articles/360034915033-Using-the-Material-Explorer-to-view-and-adjust-optical-material-models)
- **脚本读取已达 RMS**：只在 Finite-Element-IDE（CHARGE/HEAT/DGTD/FEEM）的 model-material 工作流里有文档：`?get("standard rms error"); ?get("weighted rms error");`。FDTD/MODE 的 `getmaterial` 命令页**没有**列出等价属性；FDTD 侧文档化的定量做法是官方示例本身——在同一 f 网格上比较 `getindex`（原始数据）与 `getfdtdindex`（拟合），自算偏差指标随样本记录。[Ansys：脚本创建/修改光学材料](https://optics.ansys.com/hc/en-us/articles/360034919193-Creating-and-modifying-optical-materials-from-a-script)；[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)

因此 MetaCraft 样本旁可记录的第一方口径是：`(tolerance, max_coefficients[, 高级拟合开关], fmin, fmax)` + 自算的 `|getfdtdindex − getindex|` 偏差；"solver 报告的已达 RMS"在 FDTD 脚本路径上不能假定可得，除非在目标 build 上实测 `?getmaterial` 枚举出此类属性。

### 5. 跨度依赖：是，样本只对采样时的 (fmin, fmax) 与拟合参数组合有效

`getfdtdindex` 页明示拟合在指定跨度上重算（"find a best fit of the material data over that range"），且 "the fit result depends on the fit parameters, Max coefficients and Tolerance set for the material, thus getfdtdindex result depends on those parameters as well."。同一 f 处，换一个 (fmin, fmax) 或改动材料拟合参数，返回值都可能不同。[Ansys：`getfdtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409694-getfdtdindex-Script-command)

与真实求解对齐时还有一层：仿真里拟合带宽默认取 source 带宽，除非启用 "specify fit range / Bandwidth range of fit" 显式解耦。所以要让样本等于求解网格实际用值，采样传入的 (fmin, fmax) 必须等于该次求解实际生效的拟合范围（source 带宽或显式 fit range）。[Ansys：材料拟合技巧](https://optics.ansys.com/hc/en-us/articles/360034915053-Tips-for-improving-the-quality-of-optical-material-fits)；[Ansys：Material Explorer](https://optics.ansys.com/hc/en-us/articles/360034915033-Using-the-Material-Explorer-to-view-and-adjust-optical-material-models)

对照：`getindex` 无跨度参数，只依赖材料库数据本身与插值，样本天然跨 brief 复用。退化单频跨度 `fmin == fmax` 的行为在 `getfdtdindex` 文档中未定义（沿袭 2026-07-12 研究结论：须在目标 build 上作为 fixture 实测，不得臆造隐藏带宽）。[本仓库：2026-07-12-lumerical-fdtd-refractiveindex-material-import.md]

### 6. 相关入口点与默认库中的 Si3N4 / SiO2

- `getmaterial("name","sampled data")`：读回材料库存储的原始 `[f_Hz, 复介电常数]` 矩阵（2 列各向同性 / 4 列各向异性）；`?getmaterial("name")` 枚举可查属性。这是确认"表里到底存了什么、覆盖到哪个频率"的入口——包括确认 355/400 nm 是否落在默认材料的表格范围内（Ansys 页面不公布各默认材料的表格范围，须运行时读表判定）。[Ansys：`getmaterial`](https://optics.ansys.com/hc/en-us/articles/360034930053-getmaterial-Script-command)
- `setmaterial` / `addmaterial`：只可改**非写保护**材料；默认材料写保护，改动需复制（"The default materials cannot be edited directly. However, if you wish to modify one of the default materials, a copy of the material needs to be created"）。[Ansys：`setmaterial`](https://optics.ansys.com/hc/en-us/articles/360034409654-setmaterial-Script-command)；[Ansys：Material Database in FDTD and MODE](https://optics.ansys.com/hc/en-us/articles/360034394614-Material-Database-in-FDTD-and-MODE)
- `getnumericalpermittivity("name", f, fmin, fmax, dt[, component[, use_bfast]])`：返回含有限 dt 效应的实际数值介电常数；dt=0 时严格等于 `getfdtdindex` 的平方；不需要事先运行仿真。[Ansys：`getnumericalpermittivity`](https://optics.ansys.com/hc/en-us/articles/360034930093-getnumericalpermittivity-Script-command)
- 其他求解器同族：`getmodeindex`（MODE 实际使用值）、`getdgtdindex`（DGTD Materials Group 拟合值，签名同样显式传跨度）。命名模式 = "get<solver>index 即该求解器实际使用值"。[Ansys：`getmodeindex`](https://optics.ansys.com/hc/en-us/articles/360034930073-getmodeindex-Script-command)；[Ansys：`getdgtdindex`](https://optics.ansys.com/hc/en-us/articles/360034409774-getdgtdindex-Script-command)
- Material Explorer（GUI）：查看/调整拟合并展示 RMS；"Save fit parameters" 会把新 Tolerance/Max coefficients 写回材料库——GUI 操作会改变后续 `getfdtdindex` 结果，qualification 后应禁止未登记的 GUI 改动。[Ansys：Material Explorer](https://optics.ansys.com/hc/en-us/articles/360034915033-Using-the-Material-Explorer-to-view-and-adjust-optical-material-models)
- grating 类查询是**消费**折射率的下游：`grating("monitorname", f, index, direction)` 的 `index` 参数是"投影所用材料折射率"，默认取 monitor 中心处的值；`gratingn`/`gratingm` 等返回的是阶次编号而非材料索引。per-brief 若做光栅/远场投影，显式传入本工单采样的 solver-native index 可消除"默认取 monitor 中心值"带来的隐式依赖。[Ansys：`grating`](https://optics.ansys.com/hc/en-us/articles/360034927213-grating-Script-command)
- 官方还在纯解析工作流中示范了同样的采样用法：`stackrt` 示例用 `getfdtdindex("SiO2 (Glass) - Palik", f, min(f), max(f))` 与 `"Si (Silicon) - Palik"` 构造多层膜索引矩阵——再次印证无需仿真区域。[Ansys：`stackrt`](https://optics.ansys.com/hc/en-us/articles/360034406254-stackrt-Script-command)
- **默认库命名**：Material Database 页的默认材料表列出 "Si3N4 (Silicon Nitride) - Luke"（引用 K. Luke et al., Opt. Lett. 40, 4823–4826 (2015)）；SiO2 在该表中写作 "SiO2 (Glass)"（Palik 手册引用节），而多份官方脚本示例（stackrt、stackfield、addimport、mie3d 等）使用字面名 "SiO2 (Glass) - Palik"。两种写法并存意味着**精确材料名必须在目标 build 上以 `materialexists` 实测确认**，不得硬编码假定。[Ansys：Material Database in FDTD and MODE](https://optics.ansys.com/hc/en-us/articles/360034394614-Material-Database-in-FDTD-and-MODE)；[Ansys：`stackrt`](https://optics.ansys.com/hc/en-us/articles/360034406254-stackrt-Script-command)；[Ansys：`materialexists`](https://optics.ansys.com/hc/en-us/articles/360034930113-materialexists-Script-command)

## 二、What this decides（本答案决定的采样时机）

**可调用性不构成约束；跨度有效性才是决定因素。**

1. 两个入口都能在裸 `lumapi.FDTD(hide=True)` 会话调用（无工程、无 FDTD 区域、无运行），qualification fixture 的 FDTD 区域对这两条命令没有作用。因此"per-brief 一次短会话"在成本与前提上完全可行，不需要为了读索引而维持 fixture。
2. `getindex`（材料库表插值）**与跨度无关**：可以在 qualification 时按登记的频率网格一次性采样，跨 brief 复用（brief-independent），只要材料库修订与插值口径不变。
3. `getfdtdindex`（求解实际拟合值）**与 (fmin, fmax) 及材料拟合参数绑定**：
   - 若在 qualification 时采样，必须同时登记频率网格策略 + 固定跨度政策（且 brief 求解须经 "specify fit range" 或 source 带宽与该跨度严格一致），样本才对 brief 有效；
   - 否则必须 **per-brief 采样**：在 brief 的精确波长（355/400 nm → `f = c/lambda`，Hz）与该 brief 求解实际生效的 (fmin, fmax) 下，用一次短裸会话取值。
4. 推荐落点：默认库材料（Si3N4 Luke / SiO2 Palik 类）走 **per-brief 短会话**采样 `getfdtdindex`，同场记录 `getindex` 对照值、`(tolerance, max coefficients)` 读回值与 `|getfdtdindex − getindex|` 偏差；`getindex` 网格样本可另存为 qualification 级证据。v0.0 单频 `(n,k) Material` 绑定路径本身不经过多系数拟合，该路径下跨度问题退化，但对默认色散材料的任何 solver-native 读数仍适用上述规则。
5. 失败关闭沿用 2026-07-12 结论：`fmin == fmax` 未文档化，禁止未经该 build fixture 实测就采用退化跨度；材料名未经 `materialexists` 确认、或工作频率落在表格范围外（经 `getmaterial(...,"sampled data")` 判定）时，样本不得判有效。

## 三、文档未覆盖 / 含糊之处（置信度说明）

1. **"无需仿真区域"没有逐字声明**：getindex/getfdtdindex 命令页未写"no simulation region required"这句话；该结论由签名自足 + 官方裸会话示例 + "新建仿真自动加载默认库"三条第一方证据合成，置信度高但属于组合推断。
2. **`fmin == fmax` 行为未定义**：文档没有说明退化单频跨度下拟合例程的行为，须按 build 实测。
3. **Python 返回的精确 numpy 形状未文档化**：仅能从官方示例的 `np.transpose` 推断为列样矩阵。
4. **FDTD 脚本侧无文档化的"已达 RMS"读取**：`get("standard rms error")` 只出现于 CHARGE/HEAT/DGTD/FEEM 工作流文档；FDTD 的 `?getmaterial` 是否枚举出等价属性须实测。
5. **默认材料的表格频率范围未公布**：Luke 数据是否覆盖 355 nm、Palik 玻璃表在 355/400 nm 的采样密度，Ansys 页面不提供，须运行时读 `sampled data` 判定；`getindex` 在表格范围外的外推行为亦未文档化。
6. **SiO2 命名两写法并存**（"SiO2 (Glass)" vs "SiO2 (Glass) - Palik"），且 `max coefficients`/`max coefficient` 属性名单复数在官方页面间不一致：精确字符串须按 build 实测，纳入 solver fingerprint。
