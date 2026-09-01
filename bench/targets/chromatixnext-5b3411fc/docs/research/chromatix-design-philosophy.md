# Chromatix 设计理念对 ChromatixNext 的启示

> 调研边界：仅依据 Chromatix 正式论文、当前官方文档、工作区内的 Chromatix 0.4 源码与既有审计；未作额外推断性检索。

## 结论

ChromatixNext 应采用“**双入口、单一规范表示**”：保留直接调用 PyTorch 光学函数的探索路径；凡需保存、共享、由 GUI 编辑或宣称可复现的科学系统，一律物化为领域级、显式 `nodes + named edges` 的类型化 `Optical Graph`。Pipeline API 与 GUI 只是该图的编写方式，不是第二套语义。

这不是背离 Chromatix，而是对其三项原则的工程化延伸：保留可微分性；把“标准化、可替换的组件”提升为稳定的算子与端口契约；在执行前增加验证、资源规划和运行溯源，以补上原库留给调用者的职责。[Nature Methods 正式论文](https://www.nature.com/articles/s41592-026-03121-x) [本地工作逻辑审计](../audit/chromatix-working-logic.md)

## 从 Chromatix 应当读出的真实设计

正式论文把 **differentiability、composability、scalability** 列为三项原则；其中 composability 指标准化、可替换的光学组件。其科学模型以复数 `Field` 为中心，同时表达波长、偏振和空间采样；光学算子是场变换，系统则由这些变换组合而成。[Nature Methods 正式论文](https://www.nature.com/articles/s41592-026-03121-x)

当前官方 101 文档进一步区分了两类入口：函数式核心适合快速实验和可视化，Equinox 元件类用于约束和状态；文档还明确指出 `OpticalSystem` 以灵活性换取简洁性。[官方 Chromatix 101](https://chromatix.readthedocs.io/en/latest/101/)

因此，“系统是序列”应理解为便利接口，而不是需要永久固化的科学规范。当前 Systems API 仍将系统实现为 `Sequence[Callable]` 的顺序调用；本地 0.4 源码也只是首元素接收初始参数、后续元素逐个接收前一 `Field` 的循环。[当前 Systems API](https://chromatix.readthedocs.io/en/latest/api/systems/) [本地 0.4 `OpticalSystem`](../../reference/chromatix/src/chromatix/systems/optical_system.py)

本地审计还表明：`Field` 与可微光学算子是值得保留的科学核心，JAX 变换负责求导、编译和批处理；但完整系统验证、设备选择、显存规划、分块策略和不可变运行记录并不由 Chromatix 负责。[本地工作逻辑审计](../audit/chromatix-working-logic.md)

## Preserve / Reject / Extend

### Preserve（保留）

- 保留“带物理与采样元数据的复数场 + 可组合、可微的领域算子”这一核心模型，而不是把系统退化为裸张量流水线。[正式论文](https://www.nature.com/articles/s41592-026-03121-x) [本地审计](../audit/chromatix-working-logic.md)
- 保留轻量函数式入口。研究者应能直接调用 PyTorch 函数、立即画图和求梯度，无须先搭建注册表或图配置；这对应官方 101 所强调的快速实验路径。[官方 Chromatix 101](https://chromatix.readthedocs.io/en/latest/101/)
- 保留简洁的 Pipeline 写法，但将其定义为线性图的语法糖，而不是独立执行模型。

### Reject（拒绝）

- 不把 `Sequence[Callable]` 当作唯一规范。它很简洁，却无法自然、稳定地表达分支、合并、具名多端口、静态兼容性检查和 GUI 连线；官方文档本身已承认这种简洁存在灵活性代价。[官方 Chromatix 101](https://chromatix.readthedocs.io/en/latest/101/) [当前 Systems API](https://chromatix.readthedocs.io/en/latest/api/systems/)
- 不把 `torch.fft`、张量 reshape、padding 或逐点乘法等实现细节暴露成科学图节点。图中节点应是“角谱传播”“薄透镜”“传感器”等有物理/数值契约的算子；低层运算留在算子实现内部。否则 GUI、配置版本和溯源都会与后端实现细节耦合。
- 不自动把任意 Python callable 包装成“可复现算子”，也不从运行时调用轨迹反推规范图。任意函数可以用于探索，但其身份、参数 Schema、端口和实现版本均未被解析时，不能声称得到 resolved/reproducible run。
- 不把 Optical Graph 扩张为通用工作流引擎。训练循环、数据下载、优化器调度和任意 Python 控制流不属于第一版科学光学图。

### Extend（扩展）

- 增加唯一规范的领域级 `Optical Graph`：稳定节点 ID、注册算子 kind、具名类型化端口，以及显式 `node_id.port_name` 边。端口至少区分 `Field`、测量/张量结果和必要的领域对象；具体的波长、偏振、采样与形状约束在图解析阶段检查。
- 把“科学规范”与“执行计划”分开。规范图描述要算什么；物化阶段解析算子版本和默认值，检查契约；规划阶段再决定 device、dtype、分块、缓存与重计算。这样才能针对审计中已确认的资源规划缺口扩展，而不污染科学配置。[本地工作逻辑审计](../audit/chromatix-working-logic.md)
- Pipeline、Python builder 和 GUI 必须降低到同一规范图，再走同一验证与物化流程；不得分别维护三套解释器。
- 函数式实验要升级为正式运行时，必须显式注册或物化：确定算子 kind、实现、参数、输入资产和 Registry 指纹后，才生成 resolved run 与运行清单。函数式路径本身仍可执行、求导和作图，只是不获得可复现性声明。

## 建议的最小边界

```text
探索：PyTorch functions -> Tensor/Field -> plot / grad

正式运行：Pipeline / GUI / graph file
                  -> canonical Optical Graph
                  -> validate + materialize registered operators
                  -> execution plan
                  -> run manifest + result
```

第一版只需做好四件事：规范图数据模型、注册算子物化、Pipeline 降级、运行清单。暂不支持热加载、任意控制流、低层算子图编辑或自动捕获 Python 函数。

## 明确建议

**采纳显式 `nodes + named edges` 作为唯一持久化科学表示，同时保留直接 PyTorch 函数作为非规范探索入口。** Pipeline 与 GUI 只能生成这一规范图；图只容纳领域级科学算子；任何未注册、未物化的函数式计算都不得标记为 resolved 或 reproducible run。

这条边界同时满足稳健和简洁：普通实验不被图机制打扰，正式运行只有一套语义、验证和溯源链路。
