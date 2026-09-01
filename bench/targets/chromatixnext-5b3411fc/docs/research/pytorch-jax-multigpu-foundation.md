# PyTorch/JAX 多 GPU 科学基座边界调研

日期：2026-08-23  
状态：架构输入，不是性能结论  
目标：确定 ChromatixNext 在当前原生 Windows、单 GPU 现实下，如何诚实设计 PyTorch 多 GPU 路线，以及何时才可以比较 PyTorch、JAX 与 Chromatix 的性能。

## 结论摘要

1. ChromatixNext 当前可以主张原生 Windows CUDA、显式单设备选择和固定双精度的可用性；不能据此主张多 GPU 性能。
2. 第一条正式多 GPU 路线应是 Linux/NCCL 上的一进程一卡、完整 Assembly 副本和显式 Ensemble Axis 分片。`DataParallel` 不应成为科学基座。
3. 多 GPU 必须位于光学科学模型之外的执行编排层。每个 rank 仍运行一个 device-local Workstation；输入分片、collective、失败传播和结果合并由单独 owner 管理。
4. DDP 只解决 replicated model 的梯度同步，不会自动分片输入，也不等于厚样品切片、单个大场 sharding 或 distributed FFT。
5. Chromatix 最值得学习的是“光学函数保持 transformation-compatible，执行并行由外围表达”，不是照抄其 `pmap` API。当前 JAX 已把 `pmap` 标为旧方式并推荐 `shard_map`/`smap`。
6. 没有一手资料或本地 benchmark 支持“基于 PyTorch 的光学算子不比 JAX/Chromatix 差”。这只能作为待检验假设，不能作为当前论文结论。
7. 公平比较必须在同一 Linux GPU 主机、相同物理方程、相同 `float64/complex128`、相同 shape/batch、正确同步并分别报告 cold compile 与 steady state。原生 Windows 结果应作为部署可达性证据单列。

## 证据标签

- **OBSERVED**：直接来自本地源码、实际环境探针或官方文档/源码。
- **INFERRED**：由一个或多个 observed facts 推出的架构含义；不是已经实现或验证的能力。
- **UNKNOWN**：当前证据不足，必须通过设计决定、真实硬件实验或独立 benchmark 才能回答。

## 1. 本地基线

### 1.1 代码与运行环境

**OBSERVED**

- 当前规划 worktree 是 `35573738405ecfc340bca65f4fa361c2c9934033`；SSR-E2 candidate 是 `a8dc9855c372b173380981eec477f04a65b78f47`。
- 两个 worktree 的 `src/chromatix_next/workstation.py` 和 `src/chromatix_next/_ownership.py` 内容一致，因此本节执行边界判断同时适用于 candidate。
- 使用仓库指定解释器实测：Windows 11、Python 3.12.13、PyTorch `2.12.0+cu130`、CUDA 13.0、一张 `NVIDIA GeForce RTX 5090 D`。
- `torch.distributed`、Gloo 和 `torchrun` 可用，NCCL 不可用；`torch.compile` API 存在，但环境中没有 Triton。存在 API 不等于 CUDA compiled path 已经通过资格验证。
- 当前 `Workstation.cuda(device_index)` 精确选择一张设备；架构文档明确写的是“一次 run 一张 CUDA 设备”，不在 run 内拆分跨设备 tensor。
- Windows 进程内还存在一个 live CUDA Workstation singleton。它是当前安全/ownership 约束，不是多 GPU abstraction。
- `src/`、`tests/` 和 `tools/` 中没有 `DistributedDataParallel`、`DataParallel`、`torch.distributed` 或 `torchrun` 的生产实现。

本地依据：[`workstation.py`](../../src/chromatix_next/workstation.py)、[`_ownership.py`](../../src/chromatix_next/_ownership.py)、[`architecture.md`](../architecture.md)。

**INFERRED**

- 当前产品是“device-local scientific executor”，不是尚未完成的 distributed executor。论文必须把 single-GPU support 与 multi-GPU roadmap 分开。
- Windows singleton 是进程内状态；未来的一进程一卡设计在形状上可能兼容它，但本机只有一张 GPU，尚未形成 Windows 多进程多卡证据。
- 多 GPU 不应通过让一个 Workstation 同时持有多个 device 来实现，否则会破坏当前 ownership、memory boundary、seed stream 和 Run Record 的单一责任。

**UNKNOWN**

- 当前 Assembly/Workstation 生命周期能否在不削弱 host ownership 的情况下直接由 DDP 包装。
- Gloo 在此 Windows 环境中对项目真实 `complex128` 梯度、collective 顺序、性能和失败行为是否满足要求。
- `torch.compile` 对当前全链路、固定双精度、复数 FFT 和自定义 Physical Value 的可捕获范围及收益。

### 1.2 本轮 exploratory execution probes

以下 probe 使用仓库指定解释器并以 `-B` 运行；它们只回答当前机器的执行事实，不构成 2+ GPU
或性能证据。

**OBSERVED**

- Backend inventory：`torch.distributed.is_available() == True`、Gloo available、NCCL unavailable、
  MPI unavailable、CUDA device count `1`。当前环境未安装 JAX/JAXlib/Chromatix，因此无法在原生
  Windows 上制造伪同机 GPU benchmark。
- 单 rank `torchrun` 尚未到达 worker body：standalone 与 static rendezvous 都在 TCPStore 建立时以
  `DistStoreError` 失败，错误明确指出当前 PyTorch build 没有 libuv support；在该 build/launcher
  path 下设置 `USE_LIBUV=0` 后仍得到同一失败。直接 TCP/FileStore 初始化也没有产生成功 marker。
  因此本轮结果是 `WINDOWS_DDP_NOT_QUALIFIED`，而不是“单 rank DDP 已工作”。
- 所有 throwaway probe script 与 93-byte FileStore artifact 已在定位后精确删除；candidate worktree
  未被写入。
- SI/dtype probe 使用 `wavelength=532 nm`、`baseline=1 m`、`delta=1 nm`：

  ```text
  float32: (baseline + delta) - baseline = 0
           accumulated phase delta       = 0
           direct 2*pi*delta/wavelength  = 0.011810498312115669
  float64: recovered delta               = 1.000000082740371e-09
           accumulated phase delta       = 0.011810500174760818
           direct phase delta            = 0.011810498697705988
  analytic phase delta                   = 0.011810498697705988
  ```

**INFERRED**

- Fixed Double 的最强理由不是“纳米数值本身无法由 float32 表示”，而是统一 SI 下的大动态范围、
  相近量消减和长光程相位累计会丢失科学可辨差异。公开 SI + `float64/complex128` 应继续配合局部
  Optical Path Reference 与 kernel-internal nondimensionalization，避免先形成巨大绝对相位再相减。
- Windows/Gloo 需要独立 launcher/rendezvous qualification；`distributed_available=True` 不能被解释为
  当前产品支持 DDP，更不能替代 Linux/NCCL 多卡证据。

## 2. 本地 Chromatix 源码审计

本地参考仓库位于 `reference/chromatix`，remote 为官方 `https://github.com/chromatix-team/chromatix.git`，冻结于 commit [`727d7a39e9a0054cfe3a102440fcf931d31fd11a`](https://github.com/chromatix-team/chromatix/tree/727d7a39e9a0054cfe3a102440fcf931d31fd11a)，`git describe` 为 `0.4.0`。

### 2.1 它实际怎样使用 JAX 并行

**OBSERVED**

- 官方定位是 JAX 可微波光学库，利用 JIT、多 GPU 与自动微分；光学 element 以类似神经网络 layer 的方式组合。[Chromatix README](https://github.com/chromatix-team/chromatix)
- Chromatix 没有建立自有设备调度器。其并行文档明确让应用根据问题选择 `vmap`、`pmap` 或 distributed `jax.Array`，而不是由光学库强制一种 parallelism。[冻结版本 parallelism 文档](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/docs/parallelism.md)
- 生产源码中没有 `pmap`、`NamedSharding`、`PartitionSpec`、`shard_map` 或 `pjit` 实现。生产侧实际出现的是局部 `vmap`，以及 sensor 的可选 `lax.psum` collective seam。
- `parallel_psf.py` 才在 Example 层使用 `jax.jit`、`jax.pmap` 和 `jax.device_put_sharded`，把 128 个相互独立的 defocus planes 切成 4 份。[parallel_psf.py](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/examples/parallel_psf.py)
- `parallel_imaging.py` 同样沿 volume/depth batch 切分，并通过 `reduce_parallel_axis_name="devices"` 触发 sensor 内的 `lax.psum`，把每卡 partial image 合成 replicated final image。[parallel_imaging.py](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/examples/parallel_imaging.py)、[sensor collective 实现](https://github.com/chromatix-team/chromatix/blob/727d7a39e9a0054cfe3a102440fcf931d31fd11a/src/chromatix/functional/sensors.py)
- 冻结文档报告两组 4×A100 steady-state forward 数据，均平均 10 次且排除 JIT 编译时间：
  - 独立 PSF depth planes：单卡 25.06 ms，四卡 6.45 ms，约 3.89×。
  - 需要跨设备 `psum` 的 microscope image：单卡 172.86 ms，四卡 51.71 ms，约 3.34×。
- 这些示例不是单个二维 FFT 的跨卡切分；每个 device 上的 FFT 和光学计算仍然是 device-local。

**INFERRED**

- 可借鉴的核心是：科学对象与函数对外部变换保持可组合，而 execution policy 不进入每一个 optical action。
- ChromatixNext 的对应结构不是复制 `pmap`，而是保持 Wave/Ray action 的纯 device-local 科学语义，在外部 Execution Plan 上显式命名可拆分的科学轴。
- 第一个可拆分轴应是 mutually independent 的 source、defocus、field sample、design condition 或 experiment；频谱只有在探测/损失归约语义被钉住时才能拆分。

**UNKNOWN**

- Chromatix 文档没有声明上述 A100 timing 的 dtype。示例源码没有启用 X64；官方 JAX 默认禁止 X64，但外部运行环境仍可能预先设置该 flag，因此不能把这些数字断言为 float32，也绝不能当作 `float64/complex128` 预算。
- 两个公开示例只证明特定 forward workloads；它们不证明通用优化、多卡 backward、厚样品 state sharding 或 distributed FFT。

### 2.2 JAX 当前语义已经变化

**OBSERVED**

- `vmap` 是沿数组轴的自动向量化，不自动意味着多设备复制。[JAX `vmap`](https://docs.jax.dev/en/latest/_autosummary/jax.vmap.html)
- 当前 JAX 把 `pmap` 标为旧方式：它表达 replicated SPMD，但现在基于 `jit + shard_map` 实现，官方建议新代码优先使用 `shard_map` 或 `smap`。[JAX `pmap`](https://docs.jax.dev/en/latest/_autosummary/jax.pmap.html)、[迁移指南](https://docs.jax.dev/en/latest/migrate_pmap.html)
- `pmap` 要求参与设备相同，mapped axis 不超过可用设备数，多进程 collective 要求各进程以相同顺序执行 SPMD 调用。[JAX `pmap`](https://docs.jax.dev/en/latest/_autosummary/jax.pmap.html)
- `shard_map` 使用显式 Mesh、PartitionSpec 与 per-shard program；这说明 data placement 和 collective 不是一个无语义的 `multi_gpu=True` 开关。[JAX `pmap` 迁移指南](https://docs.jax.dev/en/latest/migrate_pmap.html)

**INFERRED**

- Chromatix 的 2025 parallelism 页面在科学拆分思想上仍有价值，但具体 `pmap/device_put_sharded` API 已不是适合仿制的长期接口。
- 即使基于 JAX，多 GPU 也需要明确设备 mesh、输入 sharding 和 collective；PyTorch 方案需要同等清晰的显式契约，而不是假装后端能自动发现科学并行轴。

## 3. PyTorch 官方边界

### 3.1 `DataParallel` 与 DDP

**OBSERVED**

- `DataParallel` 是单进程、多线程：沿 batch 维切分 tensor，每次 forward 复制 module，backward 再把 gradient 汇总到原 module。官方即使在单机也推荐 DDP。[PyTorch 2.12 `DataParallel`](https://docs.pytorch.org/docs/2.12/generated/torch.nn.DataParallel.html)
- DDP 是 module-level replicated data parallel，通过 process group 同步 model replica 的 gradient。它不会自动切分输入，调用者必须显式负责 sharding。[PyTorch 2.12 DDP](https://docs.pytorch.org/docs/2.12/generated/torch.nn.parallel.DistributedDataParallel.html)
- 单机 N 张 GPU 的官方形状是 N 个进程，每个进程独占一张 GPU；官方称 DDP 的单机多卡性能显著好于 `DataParallel`。[PyTorch 2.12 DDP](https://docs.pytorch.org/docs/2.12/generated/torch.nn.parallel.DistributedDataParallel.html)
- DDP 包装时参数必须已经注册且各 rank 顺序相同，包装后不能再增删参数。这使 module placement、state installation、hosting 和 DDP wrapping 的顺序成为真实架构问题，而不是 glue code。

**INFERRED**

- `DataParallel` 不适合 ChromatixNext：它的 per-forward replication、线程共享非 tensor 对象和隐式 batch scatter 与强 Physical Value、Assembly ownership、确定性 seed 及 Run Record 相冲突。
- DDP 是未来 shared-parameter optimization 的优先官方机制，但只有在 leaf executor 生命周期与 DDP wrapper 顺序被明确设计并通过证据后，才能成为受支持路径。
- 在没有适合 DDP 的 forward seam 前，不应偷偷手写一个“近似 DDP”的 gradient protocol 并把它称为通用优化框架。

### 3.2 Windows 与 NCCL

**OBSERVED**

- PyTorch 官方提供原生 Windows CUDA 安装与验证路径。[PyTorch Start Locally](https://pytorch.org/get-started/locally/)
- PyTorch 2.12 将 `torch.distributed` 的 Linux 支持标为 stable、Windows 标为 prototype；Windows 不支持 NCCL。[PyTorch 2.12 distributed](https://docs.pytorch.org/docs/2.12/distributed.html)
- 同一官方页面建议 CUDA distributed training 使用 NCCL，并说明 GPU 上 Gloo 通常慢于 NCCL。[PyTorch 2.12 distributed](https://docs.pytorch.org/docs/2.12/distributed.html)
- JAX 官方平台表则把原生 Windows x86_64 的 NVIDIA GPU 标为 `no`，Windows WSL2 标为 `experimental`；其多 GPU CUDA 路线需要 NCCL。[JAX installation](https://docs.jax.dev/en/latest/installation.html)

**INFERRED**

- “原生 Windows CUDA 可运行”是 ChromatixNext 相对 JAX/Chromatix 的可达性与部署差异，可以验证并写入论文。
- “原生 Windows 高性能多 GPU”目前不是可靠主张。Gloo 可以作为功能 smoke path 调研，但不能替代 Linux/NCCL qualification，也不能预设性能等价。
- 跨框架主性能比较应放在双方都正式支持的 native Linux CUDA 主机；Windows 只报告 ChromatixNext 的安装、单卡正确性和单卡性能，不与无法原生运行的 JAX GPU 制造伪对照。

## 4. 推荐的多 GPU 科学基座路线

### Stage 0：保留 authoritative single-device executor

- `Workstation.cpu()` 和 `Workstation.cuda(i)` 继续是唯一 leaf execution owner。
- Wave/Ray action、Physical Value、fixed double、memory boundary、seed stream 与 Run Record 不感知 world size 或 collective backend。
- 所有多卡输出必须能用同一 scientific inputs 在单卡参考路径复现到已声明数值预算。

### Stage 1：独立 Ensemble Execution

- 新 owner 位于 Workstation 外部，暂称 `DistributedCoordinator` 或 `ExecutionGroup`；名称需要正式 domain decision。
- 每个进程只创建一个 Workstation，host 一份完整 Assembly，并绑定唯一 CUDA device。
- 输入必须通过命名 `EnsembleAxis` 显式切分；第一版只接受相互独立、结果可按稳定顺序重组的 samples。
- 该阶段不需要 gradient collective，也不切分单个 FFT、OpticalField、RayBundle 或 volume state。
- 先证明：rank-local output 与单卡串行 output 一致；失败会使全组有界退出；seed 与 sample identity 不随 world size 漂移；结果排序确定。

### Stage 2：replicated-model optimization

- 正式 qualification 平台为 native Linux + identical NVIDIA GPUs + NCCL + one process per GPU。
- 每个 rank 拥有完整、相同参数顺序的 Assembly replica，处理不同的 design/source/sample shard。
- loss reduction 语义必须先定义：global sum、global mean、sample-weighted mean 不是同一个梯度合同。
- 优先评估官方 DDP；输入仍由项目显式分片，DDP 只负责 gradient synchronization。
- checkpoint、optimizer state、Run Record 和 failure propagation 必须指定 rank owner；不能让每个 rank 竞争写同一 artifact。
- Windows/Gloo 只有在另行通过功能与数值证据后才列为 experimental profile，不进入主性能声明。

### Stage 3：coupled scientific reduction

- 只有出现真实 caller 后，才引入类似 Chromatix sensor `psum` 的 operation-owned collective seam。
- 示例包括：分片深度平面对一个探测图作物理求和，或分片 spectrum 对 incoherent intensity 作带权归约。
- collective 的位置和 reduction law 属于 scientific operation；NCCL/Gloo 和 rank topology 属于 execution implementation。
- 必须先证明归约次序在 fixed double 下满足误差预算，并记录 world size 对结果的影响。

### Stage 4：state sharding / distributed FFT

- 厚样品 volume sharding、单个大场 sharding、distributed FFT 和模型并行是另一种架构，不属于 Stage 1/2 的“多卡开关”。
- 只有单卡内存无法容纳已被科学验证的真实 workload，且 profiling 证明跨卡 state partition 值得时才重开设计。
- 每一种 sharding 都需要 halo/边界、通信、adjoint、checkpoint、recompute、determinism 与失败恢复合同。

推荐依赖关系：

```text
authoritative single-device run
            |
            v
 independent EnsembleAxis execution
            |
            v
 replicated parameters + gradient reduction
            |
            v
 operation-owned scientific collectives
            |
            v
 state sharding / distributed FFT（条件触发）
```

## 5. 性能表述：现在能写什么

### 5.1 当前可证措辞

以下措辞与现有证据相符：

> ChromatixNext uses PyTorch tensor operators and automatic differentiation as its device-local numerical substrate. Its current qualified execution profile targets native Windows CPU/CUDA and enforces float64/complex128 throughout the scientific path.

> The architecture keeps optical laws independent of device orchestration and is designed to admit process-per-GPU execution along explicitly independent scientific ensemble axes. Multi-GPU execution remains a separately qualified Linux/NCCL profile.

> Unlike JAX, whose official NVIDIA GPU packages do not support native Windows, the evaluated ChromatixNext environment executes CUDA workloads natively on Windows. This is a platform-availability result, not a cross-framework speed claim.

可用中文表述：

> ChromatixNext 以 PyTorch tensor operator 与 autograd 作为设备本地数值基座，在已验证的原生 Windows CPU/CUDA 环境中坚持 float64/complex128。其科学算子与分布式编排相分离，多 GPU 能力将按显式科学 Ensemble Axis 在 Linux/NCCL 环境中独立验证。

### 5.2 完成 benchmark 后才可能使用的措辞模板

> On [exact GPU, OS, driver, CUDA, library versions], for [exact physical workload, shape, batch, dtype and execution mode], ChromatixNext achieved a median synchronized steady-state [forward / forward+backward / optimization-step] time of X ms versus Y ms for [exact Chromatix/JAX version], with [uncertainty definition]. Both implementations satisfied the declared forward and gradient error budgets.

“不比 JAX 差”若要成立，必须预先定义可证伪阈值，例如：

> 在冻结 workload matrix 中，ChromatixNext 的 median steady-state time 不超过 Chromatix/JAX 的 `1.10×`，且所有 forward/gradient budgets 通过。

该阈值必须在看到结果前冻结；否则只能逐 workload 报告测量值，不能给总体优劣结论。

### 5.3 当前不可证措辞

以下说法目前都不应出现在摘要、结论或架构宣传中：

- “PyTorch 光学算子不比 JAX 慢。”
- “ChromatixNext 的性能达到或超过 Chromatix。”
- “ChromatixNext 支持高性能多 GPU。”
- “多卡能够近线性扩展。”
- “固定双精度同时不损失速度。”
- “Windows 多卡与 Linux/NCCL 等价。”
- “DDP 可以自动并行任意光学系统或厚样品。”

理由不是这些命题一定错误，而是当前没有 matching benchmark、2+ GPU 环境、Linux/NCCL execution evidence 或完整 backward/collective evidence。

## 6. 推荐的最小 benchmark matrix

### 6.1 资格门

任何 timing 前必须先满足：

1. 相同物理公式、phase convention、padding/exterior、FFT normalization、sampling grid、spectrum 与 detector reduction。
2. 双方显式使用 `float64/complex128`。JAX 默认 `jax_enable_x64=False`，必须在程序启动时启用并把实际 dtype 写入 manifest。[JAX X64](https://docs.jax.dev/en/latest/default_dtypes.html)
3. forward output 通过独立 reference 或预先冻结的误差预算。
4. 所有声称可微的参数通过 analytic、finite-difference 或 independent implementation gradient check。
5. 版本、commit、OS、GPU、driver、CUDA、cuFFT/XLA、environment variables 与编译选项写入 manifest。

### 6.2 Workload matrix

| ID | 科学 workload | 目的 | 最小规模 |
|---|---|---|---|
| W1 | scalar phase/OPD modulation | pointwise、launch-bound、autograd 基线 | 256²、1024²、1536² |
| W2 | scalar angular-spectrum propagation | 共同的 FFT-heavy 核心 | 同上；aligned 与 padded 各一组 |
| W3 | defocus/PSF ensemble | 对齐 Chromatix 独立 batch 示例 | 1、8、32、128 planes |
| W4 | depth-resolved image accumulation | 测试 partial image collective | 32、128 planes；sum 与 mean 分开 |
| W5 | phase-mask optimization step | 端到端 forward + loss + backward + optimizer | 1、8、32 design/source samples |

W1/W2 用于 operator-level diagnosis；论文总体性能结论至少必须以 W3-W5 的 end-to-end 数据为主，不能用一个有利 microkernel 替代真实应用。

### 6.3 Framework 与 execution modes

| 家族 | 必测模式 |
|---|---|
| ChromatixNext | PyTorch eager；Prepared execution；`torch.compile` 仅在成功 qualification 的平台列入 |
| Chromatix/JAX | 冻结 Chromatix commit + `jax.jit`; multi-device 使用与该版本相符的 `pmap`，并补测当前推荐 `jit(shard_map)` 路径（若兼容） |
| Reference | CPU 或独立高精度/analytic reference，只用于正确性，不混入 GPU throughput 排名 |

### 6.4 Platform matrix

| 平台 | 设备 | 用途 | 允许的结论 |
|---|---:|---|---|
| 当前 native Windows | 1× RTX 5090 D | ChromatixNext correctness、memory、single-GPU latency、部署可达性 | 不作 JAX GPU 同机速度比较 |
| native Linux matched host | 1× 同型号 GPU | PyTorch vs JAX/Chromatix 公平单卡比较 | 可作 workload-scoped 性能结论 |
| native Linux + NCCL | 2×、4× identical GPUs | Ensemble、DDP gradient、collective scaling | 通过后才能主张 multi-GPU |
| Windows + Gloo（可选） | 2× identical GPUs | experimental functionality | 不与 NCCL 性能合并 |

### 6.5 Timing 与统计规则

- JAX 以 `.block_until_ready()` 同步；PyTorch 使用 CUDA events 或 `torch.cuda.synchronize()`。两边都存在异步 dispatch，未同步 wall-clock 无效。[JAX benchmark guidance](https://docs.jax.dev/en/latest/benchmarking.html)、[PyTorch CUDA semantics](https://docs.pytorch.org/docs/2.12/notes/cuda.html)
- 数据预先放到 device；host-to-device、device-to-host、compile、initialization 和 steady-state 分开报告。
- cold compile、first execution、warm steady-state、完整 optimization step 分栏，不用 warm runtime 隐藏编译成本。
- 每格至少 5 次 warm-up、30 次正式测量；报告 median、IQR、p10/p90 或 bootstrap CI，不只报告均值。
- 记录 peak allocated/reserved memory、samples/s、latency、speedup `T1/TN`、scaling efficiency `T1/(N*TN)`。
- multi-GPU 另报 collective 时间和 communication fraction；不能把增大 global batch 的 throughput 当作固定问题规模 speedup。
- 每次 benchmark 先跑 numerical/gradient gate；性能更快但错误预算失败的格子记为 `DISQUALIFIED`，不进入排名。

## 7. 建议论文命题结构

把三个命题分开，避免由一个证据越权支持另一个命题：

1. **Scientific foundation claim**：Wave/Ray 双轨、显式统一偏振语义、fixed double、可微合同和强 Physical Value invariants。
2. **Platform reach claim**：PyTorch 基座使原生 Windows CUDA 成为已验证 profile；JAX 官方原生 Windows NVIDIA GPU 不可用。
3. **Performance claim**：只在冻结的 Linux matched benchmark matrix 上逐 workload 给出，不从平台可达性或架构优雅性推导速度。

multi-GPU 在论文中的当前最诚实定位是：

> The single-device execution contract is implemented and qualified on native Windows CUDA. The architecture identifies process-per-GPU ensemble and replicated-parameter execution as the first distributed profiles, while their Linux/NCCL performance and numerical equivalence remain subject to dedicated multi-device qualification.

## 8. 最终判定

**OBSERVED**：ChromatixNext 当前是可靠的原生 Windows single-GPU PyTorch 基座；Chromatix 的多卡示例依赖 JAX transformations，并沿独立 batch/depth 轴分片；PyTorch 官方 CUDA distributed 主轴是 Linux/NCCL 的 one-process-per-GPU DDP。

**INFERRED**：最符合现有 SSRE2 架构的路线，是在 Workstation 之上建立窄的 distributed execution owner，先实现独立 Ensemble Axis，再实现 replicated-parameter gradient reduction。科学 action 和单个 FFT 继续保持 device-local。

**UNKNOWN**：ChromatixNext 与 JAX/Chromatix 的 fixed-double 性能关系、2/4 GPU scaling、Windows/Gloo 多卡可行性、DDP 与当前 ownership lifecycle 的最终 seam，以及 state-sharded thick-sample/FFT 的收益。

因此，当前可以提出“PyTorch 路线具有原生 Windows 可达性，并具备可验证的多 GPU 演进路径”；不能提出“性能不比 JAX 差”。后者应登记为 benchmark hypothesis，而不是设计前提。
