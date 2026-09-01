---
record_type: research_record
date: 2026-07-23
status: proposed_architecture_input
authority_level: none
current_capability: false
scope: local_fdtd_capacity_cpu_topology_numa_memory_and_windows_placement
---

# 本地 FDTD 容量与处理器拓扑

## 结论

用户提出的方向是正确的：本地工作站不能只按“总核心数 ÷ 每个引擎线程数”计算并发；MetaCraft 必须保留交互核心，并让每个 FDTD worker 留在一个局部拓扑域内。

但需要修正一个术语：

- Ryzen 9 9900X 的两个 CCD 是两个独立的末级缓存域；
- 当前这台机器的 Windows 实际只暴露一个 NUMA node；
- 因此它有跨 CCD 的缓存与互连代价，但没有两个各自拥有本地 DRAM 的操作系统 NUMA node。把它称为“两个近端/远端内存节点”并不准确。

在当前 9900X 上，固定的本地布局是：

```text
12 个物理核心
  ├─ LLC / CCD 0: 6 cores = 2 reserved + 4 solver
  └─ LLC / CCD 1: 6 cores = 2 reserved + 4 solver

solver budget = 8 physical cores
fixed layout = 2 workers × 4 physical cores
               one worker in each LLC domain
               16 GiB hard memory limit per worker
```

这里是总共保留 4 个物理核心、每个 CCD 保留 2 个；剩余的是每个 CCD 4 个、全机 8 个 solver cores。保留核心时同时保留它们的 SMT siblings。

这并不否定此前更窄 worker 的吞吐实测。那些实验回答的是“全机饱和时怎样吞吐最高”；固定的 `4 physical cores + 16 GiB` lane 回答的是“怎样让本地执行形状始终可靠、可解释且不变形”。

在相同的 8-core solver budget 下，本机已有一组真实 FDTD 对照：

```text
2 workers × 4 threads, unpinned: 4.1755 candidates/min
2 workers × 4 threads, one worker per LLC:
                                4.5415 candidates/min
4 workers × 2 threads, two workers per LLC:
                                7.2243 candidates/min
pinning improvement for 2 × 4:  8.77%
4 × 2 gain over pinned 2 × 4:  59.07%
```

固定 `2 × 4` 用 `0x55` 与 `0x55000` 选择两个 LLC 中各四个不同物理核心的第一条 SMT logical processor。固定 `4 × 2` 用 `0x5`、`0x50`、`0x5000` 与 `0x50000` 将每个 LLC 的四个 solver cores 分成两个 worker。两种布局都在每个 LLC 留下两个完整物理核心。

这证明 locality 应进入 capacity 合同。尽管 pinned `4 × 2` 的批量吞吐更高，当前设计仍选择 pinned `2 × 4`，因为 lane 形状已经被固定为四个物理核心；吞吐差异作为证据保留，不再驱动运行时切换。

## 一、硬件事实

### Ryzen 9 9900X

AMD 给出的规格是 12 cores / 24 threads、64 MB L3、三枚 package dies、双通道 DDR5。[AMD Ryzen 9 9900X specifications](https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9900x.html)

AMD 对 Zen 5 CCD 的官方说明是：一个经典 Zen 5 CCD 最多包含 8 个核心和共享的 32 MB L3。[AMD 5th Gen EPYC architecture white paper](https://www.amd.com/content/dam/amd/en/documents/epyc-business-docs/white-papers/5th-gen-amd-epyc-processor-architecture-white-paper.pdf)

结合 9900X 的 64 MB L3、三枚 package dies 与本机操作系统枚举，可以确认当前机器为：

- 两个 6-core CCD / LLC domains；
- 一个 I/O die；
- 一个 Windows NUMA node；
- 一个 processor group；
- 每个物理核心有两个 SMT logical processors。

其中“两枚 CCD 加一枚 I/O die”是由 AMD 的公开规格和本机枚举共同得出的推断，不是 AMD 产品页逐字列出的字段。

### Ryzen Threadripper 9980X 与 Threadripper PRO 9985WX

用户所说的 `Threadripper 9980X` 是准确型号，不是 `9985WX` 的误称：

- Ryzen Threadripper 9980X：64 cores / 128 threads、256 MB L3、9 package dies、4-channel DDR5；[AMD 9980X specifications](https://www.amd.com/en/products/processors/ryzen-threadripper/9000-series/amd-ryzen-threadripper-9980x.html)
- Ryzen Threadripper PRO 9985WX：64 cores / 128 threads、256 MB L3、9 package dies、8-channel DDR5；[AMD 9985WX specifications](https://www.amd.com/en/products/processors/workstations/ryzen-threadripper/9000-wx-series/amd-ryzen-threadripper-pro-9985wx.html)

AMD 的平台表还表明：WRX90 提供 8-channel、最高 2 TB，TRX50 提供 4-channel、最高 1 TB；PRO 处理器也可落在 TRX50 上。因此 MetaCraft 不能只看 CPU 型号推断实际内存通道，必须观察实际 motherboard / firmware / OS topology。[AMD Threadripper platform comparison](https://www.amd.com/en/products/processors/workstations/ryzen-threadripper.html)

9 package dies、256 MB L3 与每个经典 Zen 5 CCD 32 MB L3 一致地指向 8 个 CCD 加一个 I/O die。这适合成为 qualification 的预期值，但调度器仍应以 Windows 实际枚举为准。

### Intel Xeon w9-3495X

Intel 给出的规格是 56 cores / 112 threads、105 MB LLC、8-channel DDR5、最高 4 TB，并且是单插槽处理器。[Intel Xeon w9-3495X specifications](https://www.intel.com/content/www/us/en/products/sku/233483/intel-xeon-w93495x-processor-105m-cache-1-90-ghz/specifications.html)

Sapphire Rapids 提供 Sub-NUMA Clustering。Intel 说明 SNC 把核心、LLC slices 和相邻内存控制器组织成局部域；SNC-2 或 SNC-4 由 BIOS 开启，要求内存对称填充，NUMA-aware 软件才能受益。[Intel 4th Gen Xeon architecture overview](https://www.intel.com/content/www/us/en/developer/articles/technical/fourth-generation-xeon-scalable-family-overview.html)

不过 w9-3495X 的产品页没有承诺某块 W790 主板一定开放 SNC。因此不能在代码中写死“四个 NUMA node”；应读取 Windows 实际报告的 NUMA node、LLC 和 processor group。

## 二、当前 9900X 的实机拓扑

2026-07-23 使用 Windows `GetSystemCpuSetInformation` 对当前工作站进行只读枚举：

```text
processor group 0
NUMA node 0

LLC 0:
  6 physical cores
  12 logical processors: 0..11

LLC 12:
  6 physical cores
  12 logical processors: 12..23
```

系统同时报告：

```text
CPU: AMD Ryzen 9 9900X
physical cores: 12
logical processors: 24
physical memory: 100,453,961,728 bytes
```

Microsoft 明确定义 `SYSTEM_CPU_SET_INFORMATION` 中的 `CoreIndex` 用来识别共享核心执行资源的硬件线程，`LastLevelCacheIndex` 用来识别共享末级缓存的 CPU sets，`NumaNodeIndex` 用来识别 NUMA node。[SYSTEM_CPU_SET_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-system_cpu_set_information)

因此这台机器的正确心智模型是：

```text
one memory locality node
  ├─ one LLC / CCD locality domain
  └─ one LLC / CCD locality domain
```

跨 CCD 迁移仍可能损失 LLC locality 并经过片间互连。上述同预算对照已经证明固定 LLC 可提高当前 workload 的吞吐，但不能把此前 `12 × 1` 的全部减速都归因于跨 CCD；调度迁移、缓存争用、SMT/后台竞争和引擎固定开销仍可能参与。

## 三、Windows 能可靠提供什么

### 1. 发现 topology

主入口应是 `GetSystemCpuSetInformation`。一次枚举即可获得：

```text
CpuSetId
ProcessorGroup
LogicalProcessorIndex
CoreIndex
LastLevelCacheIndex
NumaNodeIndex
EfficiencyClass
Parked / Allocated flags
```

需要完整 die、cache 或跨 group NUMA 关系时，再使用 `GetLogicalProcessorInformationEx` 的 `RelationProcessorDie`、`RelationCache` 与 `RelationNumaNodeEx`。[GetLogicalProcessorInformationEx](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-getlogicalprocessorinformationex)

MetaCraft 不应通过 CPU 名称表猜 CCD 数量。型号知识只用于解释和 qualification；实际 scheduling contract 来自本机枚举。

### 2. 处理超过 64 logical processors

一个 Windows processor group 最多含 64 logical processors。Windows 11 / Windows Server 2022 默认允许进程跨多个 groups，但仍保留 primary group，旧式、非 group-aware 的 affinity API 会隐式作用于 primary group。[Microsoft Processor Groups](https://learn.microsoft.com/en-us/windows/win32/procthread/processor-groups)

9980X/9985WX 有 128 logical processors，w9-3495X 有 112 logical processors，所以两者必然进入多 processor-group 场景。MetaCraft 的每个 worker 应限制在单个 affinity cell 内；不能把 `0..127` 当作一个平坦 affinity mask。

### 3. 放置 worker

`SetProcessDefaultCpuSets` 可以为进程中的新线程设置默认 CPU sets；没有单独选择 CPU sets 的线程会继承该集合。[SetProcessDefaultCpuSets](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessdefaultcpusets)

推荐启动顺序：

```text
CreateProcess(CREATE_SUSPENDED)
  → assign Job Object
  → assign selected CPU Set IDs
  → record placement
  → ResumeThread
```

这样 FDTD 用户代码和主要工作线程启动前，placement 已经存在。一个 worker 的 CPU sets 必须同时满足：

```text
same processor group
same NUMA node
same last-level-cache domain
distinct physical cores
```

初始版本把物理核心作为 capacity currency，不把第二个 SMT sibling 当作额外 solver core。是否利用 SMT 应由后续 benchmark profile 决定。

### 4. 观察 NUMA memory

Windows NUMA API 可以读取各 node 的处理器集合和可用内存；`VirtualAllocExNuma` 可以为调用者控制的分配指定 preferred node。如果首选 node 内存不足，Windows 仍可能从其他 node 提供页面。[Microsoft NUMA Support](https://learn.microsoft.com/en-us/windows/win32/procthread/numa-support)

但 Lumerical 是外部进程，MetaCraft 不能替换它内部 allocator。因此当前可保证的是：

- 在引擎启动前把进程限制到一个 NUMA / LLC domain；
- 用 node-local available memory 做 admission；
- 通过实测验证实际 local/remote memory 行为。

不能声称 MetaCraft 已经强制 Lumerical 的每个 heap page 位于指定 node。

### 5. 约束失控进程

Windows Job Object 能把进程及其默认继承的子进程作为一个资源单元。它支持 per-process / per-job committed-memory limits、peak memory accounting、CPU rate control 和 `KILL_ON_JOB_CLOSE`。[JOBOBJECT_EXTENDED_LIMIT_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information) [Job Object CPU rate control](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_cpu_rate_control_information)

MetaCraft 应把 Job Object 用作外部引擎的 containment，不把它当成吞吐调度器：

- scheduler 决定何时允许启动；
- CPU sets 决定在哪里运行；
- Job Object 防止孤儿进程和灾难性超量；
- Rust permit 只证明 active-engine slot 的生命周期。

## 四、自适应 capacity 设计

### 1. 使用 affinity cell，而不是裸核心数

定义：

```text
physical core
  = one CoreIndex and all of its SMT CPU sets

affinity cell
  = one ProcessorGroup
  ∩ one NumaNodeIndex
  ∩ one LastLevelCacheIndex
```

每个 worker 只能从一个 affinity cell 取核心。若系统只有一个 NUMA node、多个 LLC domains，像当前 9900X，仍按 LLC 分开。若系统有多个 NUMA nodes，则 worker 也绝不跨 node。

### 2. 固定核心形状

全机始终保留四个物理核心：

```text
reserved_physical_cores = 4
physical_cores_per_lane = 4
```

reserve 尽量跨 locality cells 均匀分配，但 lane 绝不为了凑满全机核心数跨 cell。可用 lane 数同时受全机 reserve 与逐 cell 完整四核块约束：

```text
core_bound =
  floor((physical_cores - 4) / 4)

cell_bound =
  sum(floor(cell.physical_cores / 4))
```

因此 9900X 得到两个 lane；64-core 9980X 在实际 cells 允许时最多得到十五个 lane；w9-3495X 若以 SNC4 暴露四个 14-core cells，则 locality 约束会得到十二个 lane，而不是跨 node 凑第十三个。

### 3. 不使用 SMT

lane 的核心货币是四个不同的 `CoreIndex`，不是四个任意 logical processors：

```text
one lane
  = 4 distinct physical CoreIndex values
  = exactly one unparked CPU Set from each core
  = 4 solver threads pinned to those 4 CPU Sets
```

同一物理核心的第二个 SMT sibling 不进入 engine affinity。不能按逻辑编号奇偶猜测 sibling；必须通过 `GetSystemCpuSetInformation` 的 `CoreIndex` 分组。启动后再读回 effective CPU sets，若少于四个不同物理核心、包含重复 `CoreIndex`，或 placement 逸出 affinity cell，任务在求解前失败并关闭 permit。

### 4. 内存 admission

Ansys 的 `runsystemcheck` 会返回 `Memory_Recommended_Bytes`、monitor/result storage 和 Yee-node 信息；官方也说明 rank 0 / result collection 可能需要额外内存。[Ansys `runsystemcheck`](https://optics.ansys.com/hc/en-us/articles/4403937981715-runsystemcheck-Script-command) [Running FDTD simulations](https://optics.ansys.com/hc/en-us/articles/360046368573-Running-FDTD-simulations-from-the-design-environment)

因此每个准备完成的 task 都应先产生：

```text
estimated_memory
estimate_source
template identity
mesh identity
observed_at
```

固定内存 admission 为：

```text
lane_memory = 16 GiB
workstation_memory_guard = 16 GiB

global_memory_slots =
  floor((available_memory - workstation_memory_guard) / 16 GiB)

node_memory_slots[n] =
  floor((available_memory_on_node[n] - node_guard[n]) / 16 GiB)
```

Lumerical system check 与历史 peak 必须在启动前证明任务可装入 `16 GiB`；超出时返回 `lane_memory_exceeded`，不会静默扩大 lane。Job Object 对整个 engine job 设置 `16 GiB` committed-memory hard limit，并记录 peak。

这里需要保持物理诚实：Job Object 能硬限制“最多使用 16 GiB”，不能为外部 Lumerical allocator 预留一段专属物理地址。MetaCraft 在进程恢复前把它限制到一个 NUMA node 内的 CPU sets，并要求该 node 当时至少有完整 `16 GiB` budget；这会使首次分配具有本地性。若 Windows 或 Lumerical 后续溢出到远端内存，MetaCraft 不能伪称已经实现 Linux `mbind` 式的逐页强绑定。

当前 9900X 只有一个 Windows NUMA node，因此两个 CCD 没有各自对应的“近端 16 GiB DRAM”。能保证的是 CCD/LLC 锁核、全机 node 0 的 16 GiB hard limit 与启动前内存准入。在真正多 NUMA node 的 Threadripper 或 Xeon 上，lane 才同时具有独立 node-local memory placement。

在多 NUMA node 系统上，调度是带 CPU 与 memory 两种资源的 cell-local bin packing；不能先算全机 worker 数，再随意撒到 nodes。

### 5. 最终 admission

一次 wave 的 worker 数是所有真实上限的交集：

```text
admitted_workers = min(
  sum(cell_local_core_slots),
  sum(node_local_memory_slots),
  fresh_license_slots,
  user_ceiling
)
```

但实现上必须逐 cell 分配，而不是只保留这个总数。

每轮启动前重新观察：

```text
CPU sets still online / unparked
available memory
license availability
unfinished permits
completed evidence
```

capacity stale 后停止启动下一轮；已经启动的 worker 正常完成或关闭 permit。

### 6. 现场解析与本地操作

配置不声明 CPU 型号、NUMA 数量、亲和性掩码或可调 profile。固定策略是代码不变量：

```text
reserved_physical_cores = 4
physical_cores_per_lane = 4
use_smt = false
lane_memory = 16 GiB
```

这些值不进入任何 solver 环境文件，也不允许用户覆盖。每次启动与每轮扫参前，
共享 workstation Module 在现场读取 Windows topology 与 node-local
available memory，并生成一次不可变 layout。产品 Adapter 独立读取自己的
system check 与 fresh license count；两组新鲜证据共同形成最终 capacity。
旧 layout 不能跨拓扑或内存变化继续授权新 worker，旧产品事实也不能跨许可
证变化继续授权。

工作站 Module 只暴露两个 Interface 操作：

```text
layout = workstation.plan(demand)
worker = workstation.start(command, layout.lane)
```

`layout.lane` 是不透明的 placement token。processor group、NUMA node、
LLC、CPU sets、Job Object、memory limit 和 read-back verification 都留在
Implementation 内部。调用者不接触裸核心编号，也不能绕过 reserve。

这里的 `command` 只包含通用进程启动事实。solver Adapter 创建 command；
workstation Implementation 挂起启动 worker，施加 CPU sets 与 Job Object，
读回 placement 后恢复。Adapter 选择产品入口并负责原生模型、许可证与结果
语义：Lumerical 当前直接使用 `fdtd-engine.exe`；需要 API 包装的产品可以在
受控进程树内打开自己的 API。未来 CST 或 COMSOL 必须复用同一个 workstation
Interface，而不是复制一套本地调度。

## 五、与 Lumerical 的关系

Ansys 把单个 simulation 的 `processes × threads` 与并发 simulations 的 `capacity` 分开，并要求：

```text
threads × processes × capacity <= machine CPU cores
```

官方同时建议在具体机器上测试不同组合，而不是假定唯一最优值。[Ansys compute resource configuration use cases](https://optics.ansys.com/hc/en-us/articles/360025161033-Compute-resource-configuration-use-cases)

当前 MetaCraft 使用 Windows direct `fdtd-engine.exe`，Ansys 对该本地 command-line 路径说明没有 MPI；独立 unit-cell jobs 的并发比让一个小任务跨 NUMA node 更合适。[Ansys license consumption and command-line behavior](https://optics.ansys.com/hc/en-us/articles/360058577794-Ansys-optics-solve-accelerator-and-Ansys-HPC-license-consumption)

一个 worker 的完整含义应保持：

```text
one Rust permit
  = one Python worker
  = at most one active fdtd-engine
  = one affinity-cell placement
  = one Job Object containment
```

PB candidate 的 x/y 输入仍在同一个 permit 和 placement 内顺序执行。

许可证仍是独立上限。Ansys 的本地 license sharing 与总 cores、并发 jobs、license family 和 launcher 有关，不能由 CPU topology 推导。[Ansys license sharing examples](https://optics.ansys.com/hc/en-us/articles/360058577794-Ansys-optics-solve-accelerator-and-Ansys-HPC-license-consumption)

## 六、对当前实现计划的影响

capacity 不再只是：

```text
license_limit
compute_limit
configured_capacity
```

而应分成四个清晰模块：

```text
topology observes where work may run
memory observes how much work may fit
license observes how much work may start
runner places and contains each engine
```

Python 负责这些外部事实、计算与进程调度；Rust 仍只接纳最终 capacity evidence，控制 permit / receipt / close。Rust 不理解 CCD、NUMA、Windows CPU sets、FDTD threads 或内存估算。

建议的实现顺序：

1. Windows topology observer；
2. fixed four-core / no-SMT lane policy；
3. suspended worker launch + CPU-set placement + Job Object；
4. fixed 16-GiB limit 与 node-local admission；
5. 让 Lumerical Adapter 在受控 worker 内打开产品 API；
6. 合并 layout 与产品许可事实，把 capacity observation 交给现有 Rust
   authority。

当前 9900X 的固定布局是 `2 workers × 4 physical cores`：每个 LLC 一个 worker，每个 worker 只使用四个不同物理核心的第一条硬件线程，并由一个 16-GiB Job Object containment 管理；每个 LLC 留下两个完整物理核心。

## 官方来源

- [AMD Ryzen 9 9900X specifications](https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9900x.html)
- [AMD 5th Gen EPYC architecture white paper](https://www.amd.com/content/dam/amd/en/documents/epyc-business-docs/white-papers/5th-gen-amd-epyc-processor-architecture-white-paper.pdf)
- [AMD Ryzen Threadripper 9980X specifications](https://www.amd.com/en/products/processors/ryzen-threadripper/9000-series/amd-ryzen-threadripper-9980x.html)
- [AMD Ryzen Threadripper PRO 9985WX specifications](https://www.amd.com/en/products/processors/workstations/ryzen-threadripper/9000-wx-series/amd-ryzen-threadripper-pro-9985wx.html)
- [AMD Threadripper platform comparison](https://www.amd.com/en/products/processors/workstations/ryzen-threadripper.html)
- [Intel Xeon w9-3495X specifications](https://www.intel.com/content/www/us/en/products/sku/233483/intel-xeon-w93495x-processor-105m-cache-1-90-ghz/specifications.html)
- [Intel 4th Gen Xeon architecture overview](https://www.intel.com/content/www/us/en/developer/articles/technical/fourth-generation-xeon-scalable-family-overview.html)
- [Microsoft Processor Groups](https://learn.microsoft.com/en-us/windows/win32/procthread/processor-groups)
- [Microsoft CPU Sets](https://learn.microsoft.com/en-us/windows/win32/procthread/cpu-sets)
- [SYSTEM_CPU_SET_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-system_cpu_set_information)
- [GetLogicalProcessorInformationEx](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-getlogicalprocessorinformationex)
- [SetProcessDefaultCpuSets](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessdefaultcpusets)
- [Microsoft NUMA Support](https://learn.microsoft.com/en-us/windows/win32/procthread/numa-support)
- [JOBOBJECT_EXTENDED_LIMIT_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)
- [Ansys resource configuration elements and controls](https://optics.ansys.com/hc/en-us/articles/360058790674-Resource-configuration-elements-and-controls)
- [Ansys compute resource configuration use cases](https://optics.ansys.com/hc/en-us/articles/360025161033-Compute-resource-configuration-use-cases)
- [Ansys `runsystemcheck`](https://optics.ansys.com/hc/en-us/articles/4403937981715-runsystemcheck-Script-command)
- [Ansys license consumption and command-line behavior](https://optics.ansys.com/hc/en-us/articles/360058577794-Ansys-optics-solve-accelerator-and-Ansys-HPC-license-consumption)
