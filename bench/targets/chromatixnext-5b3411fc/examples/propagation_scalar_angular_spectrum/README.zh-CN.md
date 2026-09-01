# 标量角谱传播

## 物理问题

在不改变采样的前提下平移观测窗口时，受光瞳限制的光场如何在两个平行平面之间
传播？

## 方程

对于介质折射率为 `n(λ)` 的波长 `λ`，定义

`k = 2π n(λ) / λ`

以及辐射空间频率支撑上的

`k_z = sqrt(k^2 - k_y^2 - k_x^2)`。

令带符号轴向距离为 `d`、目标首样本平移为 `(Δy, Δx)`，包络传递函数为

`H_envelope = exp(i[(k_z - k)d + k_y Δy + k_x Δx])`。

残余轴向相位 `(k_z - k)d` 保留在包络中；均匀载波按光谱分量记录为
`OpticalPathReference += n(λ)d`。平移只贡献 `k_y Δy + k_x Δx` 相位，
不改变 Optical Path Reference。非辐射分量和超出角谱抗混叠安全带的分量均置零。

## 约定

直接计算按
`PlaneWave -> CircularPupil -> ScalarAngularSpectrum -> IntensityDetection`
阅读；托管根拥有各 Component，模块级计算按同一物理顺序逐行调用。光源使用
`linear_x` 横向偏振。`axial_distance` 带符号，正值表示向前。
`destination_shift` 只改变目标 `SpatialGrid.first_sample_position`，不是离轴传播方向。
目标网格的采样数、带符号采样间距和朝向必须与输入网格相同；只有首样本位置可以
发生平移。案例使用周期外部含义。公开长度使用 SI 米。

## 运行

```text
python examples/propagation_scalar_angular_spectrum/example.py
python examples/propagation_scalar_angular_spectrum/example.py --sample-counts 64 64 --sample-spacing 1.5e-6 1.5e-6 --aperture-diameter 4.5e-5 --axial-distance 5e-4 --destination-shift 6e-6 -3e-6 --output propagation.json
```

## 适用范围

当前方法支持平行平面之间的首样本平移，且两侧网格的采样数、带符号间距和朝向
必须匹配。其他几何会被拒绝，不会自动换用其他传播器。倏逝延拓、缩放变换、
矢量传播与非均匀采样不属于本案例。

## 来源

- Propagation、Destination Grid、Exterior 与 Optical Path Reference：
  [`CONTEXT.md`](../../CONTEXT.md)。
- 参考公式：J. W. Goodman，*Introduction to Fourier Optics*，第 4 版，
  角谱传播相关章节。
- 实现：
  [`scalar_angular_spectrum.py`](../../src/chromatix_next/optics/propagation/scalar_angular_spectrum.py)。
