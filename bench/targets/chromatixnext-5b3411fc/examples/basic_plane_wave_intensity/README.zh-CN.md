# 平面波光强

## 物理问题

归一化、单色、线偏振平面波在横向观测面上产生怎样的光强？

## 方程

光源包络为

`E(y, x) = A exp(i (k_y y + k_x x)) e_x`。

对于沿轴、单位振幅的情形，`k_y = k_x = 0`，相对光强
`I = sum_p |E_p|^2 = 1`，且与横向位置无关。

## 约定

光源显式使用 `Polarization.linear_x()`：横向 Jones 分量顺序为 `(Ex, Ey)`，
状态为 `(1, 0)`。时间因子采用 `exp(-i omega t)`。沿 `+z` 传播时，左圆偏振为
`(1, -i)/sqrt(2)`，右圆偏振为 `(1, +i)/sqrt(2)`；明确写出的向量始终优先于
可能有歧义的旋向名称。光场轴顺序为
`[batch..., spectrum, polarization, height, width]`。公开长度均为 SI 米。

直接物理读序为 `PlaneWave -> IntensityDetection`。根模块拥有两个 Component，
模块级计算逐行调用它们，随后由 Workstation 执行唯一受检重放。

## 运行

```text
python examples/basic_plane_wave_intensity/example.py
python examples/basic_plane_wave_intensity/example.py --sample-counts 64 64 --sample-spacing 5e-7 5e-7 --wavelength 5e-7 --output plane-wave.json
```

命令行始终显式创建 `Workstation.cpu(...)`；作为模块使用时，则向 `run(...)`
传入已经创建的 `workstation`。

## 适用范围

本案例只教学光源元数据、横向偏振、Component 直接组合、托管和光强观测；
不模拟传播、传感器、噪声或改变偏振的物质。解析、梯度与 CUDA
证据归 Component 测试所有。

## 来源

- 偏振与光场约定：[`CONTEXT.md`](../../CONTEXT.md)。
- Component 定义：
  [`plane_wave.py`](../../src/chromatix_next/optics/source/plane_wave.py) 与
  [`intensity_detection.py`](../../src/chromatix_next/optics/detection/intensity_detection.py)。
- 参考公式：J. W. Goodman，*Introduction to Fourier Optics*，第 4 版，
  平面波与标量衍射相关章节。
