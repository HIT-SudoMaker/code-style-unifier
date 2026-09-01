# ChromatixNext

ChromatixNext 是面向本地工作站的精简 PyTorch 光学仿真基座。物理含义由强类型
Physical Values 承载，光学动作由小型 Components 承载，完整光路由 Assembly
承载，设备与内存边界则由 Workstation 独立拥有。

当前发布面支持 Python 3.12、Windows CPU 与显式选择的单卡 Windows CUDA。
Linux 在完成独立原生验证前仍是架构目标。系统不会自动回退设备、内存方案或传播方法。

## 安装

```text
python -m pip install .
```

运行时只依赖 PyTorch。Workstation 必须显式创建：

```python
from chromatix_next import Workstation

workstation = Workstation.cpu()
```

## 科学基座

- `chromatix_next.optics` 拥有 `OpticalField`、`Intensity`、`SpatialGrid`、
  `Spectrum`、`Polarization` 与 `Medium` 等 Physical Values。
- 五个单数角色包分别拥有 Source、Element、Propagation、Combination 与
  Detection Components。
- `Assembly` 通过 `include`、`connect`、`expose` 与 `freeze` 描述一条完整光路。
- `Workstation` 托管一个 Component 或已冻结 Assembly，并返回 `NamedOutputs`
  与不可变的 `RunRecord`。

所有公开物理量使用 SI 单位。数值核为固定双精度：实数量恒为 `torch.float64`，
复数量恒为 `torch.complex128`。系统不再有精度选择项——光源与 Workstation 工厂
都不接受精度参数，`RunRecord` 也不携带精度字段；显式的 `float32`/`complex64`
状态会在构造期与托管预检被拒绝。

## 学习

七个可执行的中英文成对教学案例列于
[`examples/README.zh-CN.md`](examples/README.zh-CN.md)。每个案例只提出一个
物理问题并只使用公开光学接口；分支案例使用 Assembly。案例进入源码分发包；
运行时 wheel 只导出 `chromatix_next`。

规范领域语言位于 [`CONTEXT.md`](CONTEXT.md)，持久架构决定位于
[`docs/adr/`](docs/adr/)。`reference/` 下的上游快照仅作为只读科学参考，运行时
从不导入它们。

English: [README.md](README.md)
