# 理想薄透镜聚焦

## 物理问题

受圆形光瞳限制的平面波经过理想薄透镜，并在自由空间传播一个焦距后，能量集中在
哪里？

## 方程

透镜给光场乘上近轴相位

`exp(-i k ((y-c_y)^2 + (x-c_x)^2) / (2 f))`。

直径为 `D` 的圆孔在夫琅禾费区的第一暗环半径近似为
`r_1 = 1.22 wavelength f / D`。

## 约定

直接计算按
`PlaneWave -> CircularPupil -> IdealThinLens -> ScalarAngularSpectrum -> IntensityDetection`
阅读；托管根拥有各 Component，模块级计算按同一物理顺序逐行调用。光源显式使用
`linear_x` 横向偏振。正 `focal_length` 同时作为向前的有符号
`axial_distance`。公开长度使用 SI 米；微米与毫米只用于本地显示换算。

## 运行

```text
python examples/basic_ideal_lens_focusing/example.py
python examples/basic_ideal_lens_focusing/example.py --sample-counts 128 128 --sample-spacing 2e-6 2e-6 --aperture-diameter 2e-4 --focal-length 2.5e-2 --output focus.json
```

## 适用范围

这里使用近轴理想薄透镜和标量辐射角谱传播，不声称矢量高 NA 聚焦、像差、有限透镜
厚度或相机模型。Airy 半径只用于解释；科学容差保留在 Component 测试中。

## 来源

- 透镜、传播与网格契约：[`CONTEXT.md`](../../CONTEXT.md)。
- 参考公式：J. W. Goodman，*Introduction to Fourier Optics*，第 4 版，
  薄透镜与夫琅禾费衍射相关章节。
- 已实现 Components：
  [`ideal_thin_lens.py`](../../src/chromatix_next/optics/element/ideal_thin_lens.py)
  与
  [`scalar_angular_spectrum.py`](../../src/chromatix_next/optics/propagation/scalar_angular_spectrum.py)。
