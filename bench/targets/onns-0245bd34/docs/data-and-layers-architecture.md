# Data 与 Layers：两种积木架构

**状态：** 2026-07-24 起作为当前架构依据。

项目的共享底座由两套积木组成，但它们不是同一种架构：

- `data` 是数据积木，采用有方向的串行架构；
- `layers` 是物理积木，采用无预设拓扑的平铺架构。

Task experiment 不进入这两套积木内部。当前 restoration 以及未来的其他 experiment 都在自己的目录中组装 task dataset 与 optical system。

```text
数据积木：   load -> prepare -> perturb -> encode
                         │
                         └─ experiment 组装 task dataset

物理积木：   Diffraction   Lens   Modulation   Detection
                   \         |         |         /
                    └─ experiment 组装 optical system
```

这一区别是整个设计的起点。`data` 有固定的语义方向；`layers` 没有固定的物理拓扑。

## 1. 两套积木的共同点与不同点

共同点是二者都只提供可复用的 building blocks，而不提供任何 task experiment 成品。它们通过窄 interface 隐藏重复 implementation，为多个 experiment 提供 leverage。

不同点是它们拥有不同的 composition grammar：

| 维度 | `data` | `layers` |
|---|---|---|
| 处理对象 | dataset 与 sample | complex field 与 intensity |
| 架构形态 | 串行、单向 | 平铺、无预设拓扑 |
| composition 规则 | 按语义阶段向前演进 | 由 experiment 决定顺序、数量和连接 |
| state 的意义 | provenance、reference、阶段结果 | 物理参数、训练参数、buffer、cache |
| 最终产物 | task dataset 的通用素材 | optical system 的物理 primitive |
| 不负责 | task target、split、paired-sample 解释 | ONN topology、readout、loss |

因此，不能用统一 factory 管理 data 和 layers，也不能因为它们都是“积木”就强迫它们拥有相同目录或相同组装方式。

## 2. Data：串行的数据积木

Data 的 architecture 是一条语义链：

```text
RawSample -> PreparedSample -> PerturbedSample -> EncodedSample
```

每个 block 都接收上一阶段的 dataset，并返回语义更具体的新 dataset：

```python
source = load(source_config)
prepared = prepare(source, preparation_config)
perturbed = perturb(prepared, perturbation_config)
encoded = encode(perturbed, encoding_config)
```

这不是为了制造统一 pipeline object，而是为了让每次转换都保持可见。调用顺序本身就是数据语义：

- `load` 回答数据从哪里来；
- `prepare` 回答数据使用什么标准计算画布；
- `perturb` 回答施加了什么实验变化；
- `encode` 回答图像如何成为光学输入场。

### Prepared 与 Perturbed 为什么必须分开

Preparation 建立比较基准：normalization、resize、padding 和 edge taper 都在这里完成。Perturbation 在这个基准上施加有意的实验条件，并保留 prepared image 作为 `reference_image`。

两者分开后，可以明确追踪：

```text
计算画布是怎样建立的
        ≠
科学条件是怎样施加的
```

如果把它们合并，padding、resize、blur、noise 和 edge transform 会落入同一个不透明过程，sample 的变化原因也会失去 locality。

### 为什么 stage wrapper 属于 data

`PreparedDataset`、`PerturbedDataset` 和 `EncodedDataset` 是数据积木的 lazy implementation。它们统一索引、转换和 provenance 传播。若删除这些 module，相同规则会重新散落到 restoration、validation 和未来 experiment，因此这些 wrapper 具有真实 depth。

### 为什么完整 dataset 不属于 data

Data block 只知道中性 sample，不知道 task meaning。同一个 `reference_image` 在 restoration 中可以成为 clean target，在另一个 task 中则可能只是诊断参考或完全不参与监督。

所以 experiment 负责最后一步组装：

```text
通用 data blocks
        +
task target / split / sample naming
        =
RestorationDataset 或其他 task dataset
```

`create_dataset` 会把这些 task choice 拉回共享 module，最终形成由 output mode 和 task flag 驱动的宽 interface。项目选择显式组装，接受几行局部 composition code，换取清楚的语义与 provenance。

### Raw 是输入证据，不是可清理缓存

`data/raw/**` 位于串行架构的起点。后续 block 只能读取并派生新表示，不能回写或清理来源。这样任何 prepared、perturbed 或 encoded sample 都能够追溯并重新生成。

## 3. Layers：平铺的物理积木

Layers 的 architecture 不定义光路，只定义单个物理操作：

```text
DiffractionLayer
LensLayer
ModulationLayer
DetectionLayer
```

这些 class 在 package 中是平级的，因为“传播、透镜、调制、探测”之间没有固定的先后关系。不同 experiment 可以重复、跳过或重新排列它们：

```text
串行衍射系统：
Diffraction -> Modulation -> Diffraction -> Detection

4F 系统：
Diffraction -> Lens -> Diffraction -> Modulation
            -> Diffraction -> Lens -> Diffraction -> Detection

restoration：
由 restoration frontend 明确声明自己的物理路径与 readout
```

拓扑不进入 `layers`，因为拓扑不是单个物理 block 的知识。若 package 提供 ONN factory 或 topology compiler，新的实验结构就会不断扩大共享 interface，experiment 反而无法在本地清楚表达自己的科学条件。

### 平铺不等于浅

平铺描述的是 module 之间没有预设 hierarchy，不代表 module 自身 shallow：

- `DiffractionLayer` 隐藏频率网格、倏逝波过滤、传播函数、dtype/device 和 cache；
- `LensLayer` 隐藏理想薄透镜的坐标与相位；
- `ModulationLayer` 隐藏训练参数到有效物理相位的映射；
- `DetectionLayer` 隐藏 field 到 intensity 的域转换与可选 peak normalization。

每个 block 的 interface 都小于其 implementation，调用方不必理解内部数值细节。这使 layers 在保持 flat organization 的同时仍然具备 depth。

### 物理 block 的职责到哪里结束

`DiffractionLayer` 传播传入的 padded canvas，但不决定 padding 是否足够。padding 属于 data preparation 与 experiment geometry 的联合设计。

`LensLayer` 表示支持正负焦距的固定理想薄透镜，但不包含 aperture、可训练焦距或硬件误差。

`ModulationLayer` 表示单位振幅的可训练相位面。direct 与 sigmoid 是同一物理 block 的不同参数化，不是不同 layer。

`DetectionLayer` 完成 `abs(field)²`。是否执行通用 peak normalization 固定在 constructor；区域聚合、dataset-level normalization、noise 和 quantization 仍由 experiment 所有。

这些 seam 让一个物理变化只在一个 module 中实现和验证，同时避免把完整 optical system 藏进某个“高级 layer”。

## 4. Experiment 同时组装两套积木

Experiment 是两种 composition 的交汇点，但两条组装线仍然独立：

```text
data composition
    -> task dataset
    -> 提供 input_field / target / provenance

layer composition
    -> optical system
    -> 产生 field / intensity / task readout
```

当前 restoration 决定 paired sample、restoration frontend、intensity policy、connection 和 loss。未来 task experiment 也应在自己的目录中明确声明 dataset meaning、optical topology 与 readout。

显式 composition 会比一个统一 factory 多一些代码，但阅读 experiment 时可以直接看到完整科学条件。这里优先的是 evidence locality，而不是最短调用。

## 5. Validation 服从各自的积木架构

Data validation 沿串行阶段验证：

```text
source contract
  -> prepared contract
  -> perturbed contract
  -> encoded contract
```

Layers validation 按平铺 primitive 独立验证：

```text
Diffraction   Modulation   Lens   Detection
     |             |        |        |
     └────────── 每个 block 独立的物理与数值证据
```

这里的运行顺序只是阅读顺序，不是 optical topology。每个 validator 都只公开 `run` 与 `main`，只清理自己的输出目录，并生成同一种结果结构：`status`、`checks`、`metrics`、`figures` 与 `output_dir`。

Layer validation 是源代码能力的证据页，不是每层一张论文主图。每个 validator 依照同一心智顺序组织证据：

```text
layer state / physical definition
  -> forward response
  -> information / forward consistency
  -> device agreement
  -> layer-specific evidence
```

共同顺序不强迫不同 layer 拥有相同图像；各自的公开能力决定特有证据：

| Layer | Evidence figures | 对齐的 layer 能力 |
|---|---|---|
| Diffraction | `propagation_response`、`transfer_evolution`、`device_agreement`、`cache_performance` | circular-aperture propagation、distance-dependent transfer phase、CPU/GPU error、1000-call cold/warm forward and training latency |
| Modulation | `phase_construction`、`trainable_phase_action`、`device_agreement` | three initializations × two parameterizations、phase-only forward、CPU/GPU error |
| Lens | `lens_phase`、`fixed_phase_action`、`device_agreement` | positive/negative fixed phase、phase-only forward、CPU/GPU error |
| Detection | `intensity_response`、`device_agreement` | `I=|E|²`、bool-controlled peak normalization、CPU/GPU error |

图像只负责让物理行为、公开 information 与设备差异可见；`metrics.csv` 保存精确数值，`summary.md` 保存 PASS、FAIL 或 SKIPPED 结论。解析公式、能量与振幅守恒、gradient、invalid input、shape、dtype、repr 和 cache 数值透明性仍由 checks、tests 与 metrics 覆盖，不为了凑图而转成没有信息量的面板。Diffraction 的 cache 是唯一需要可视化的实现特例，因为它具有明确的 CPU/GPU 计算成本；图中展示性能而不展示没有科学结论的 hit/miss state。

这里的共享 `_validation.py` 特指 `data/_validation.py` 与 `layers/_validation.py`；它们只负责 cheap、deterministic 的 interface checks，例如 value、shape、dtype 和 device。`experiments/validation/layers/_shared.py` 则只保存验证实验共用的物理常量、探针、指标与摘要小工具，绘图规则统一留在 `experiments/validation/style.py`。padding convergence、sampling adequacy、detector calibration、dataset fairness 和 task metrics 需要完整上下文，因此留在 experiment validation。

## 6. Sonnet 化服务于两种架构

Data 的 Sonnet 化体现在动词式 stage interface 与单向语义：`load -> prepare -> perturb -> encode`。

Layers 的 Sonnet 化体现在名词式 primitive interface 与统一的内部心智顺序：

```text
__init__
  -> state initialization
  -> input validation
  -> core computation
  -> framework lifecycle
  -> forward
  -> information
  -> repr
```

二者不追求表面一致，而是让各自的代码形态忠实表达各自的 architecture。

## 7. 扩展时先判断是哪一种积木

| 新需求 | 应放置的位置 |
|---|---|
| 新 source 或 source adapter | `data/data_source` |
| 新 preparation、perturbation 或 encoding | 对应 data stage |
| 新 task target、split 或 sample pairing | 对应 experiment |
| 新的单一光学物理操作 | `layers` |
| 新 optical topology、ONN 或 readout | 对应 experiment |
| 新 detector hardware model | 先在所属 experiment 验证，再判断是否形成可复用 physical block |

建立新共享 module 前应满足 deletion test：删除它以后，非平凡知识会在至少两个真实调用方中重新出现。否则它更可能是一个假想 seam。

## 8. 当前公共 interface

两种积木架构目前收敛为：

```python
from data import load, prepare, perturb, encode

from layers import (
    DiffractionLayer,
    LensLayer,
    ModulationLayer,
    DetectionLayer,
)
```

具体 data 使用方式见 [`data/README.md`](../data/README.md)。冻结的是这两种 composition grammar 与职责，不是禁止未来根据新证据修复或扩展 implementation。
