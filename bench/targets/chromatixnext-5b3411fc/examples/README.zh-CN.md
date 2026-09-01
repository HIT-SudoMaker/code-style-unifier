# 教学案例

这五个可执行案例单向使用公开光学基座。最小路径教学不依赖执行外壳的直接科学
组合；四个系统案例接收一个预先选定的 Workstation，并返回少量可序列化摘要。
科学正确性的完整证据仍归 Component 测试所有，每个案例提供一个可独立检查的量。

## 索引

1. [`minimal_optical_path`](minimal_optical_path/README.zh-CN.md) —
   从网格到探测强度的八概念直接路径。
2. [`basic_plane_wave_intensity`](basic_plane_wave_intensity/README.zh-CN.md) —
   横向偏振与光强。
3. [`basic_ideal_lens_focusing`](basic_ideal_lens_focusing/README.zh-CN.md) —
   受光瞳限制的理想薄透镜聚焦。
4. [`propagation_scalar_angular_spectrum`](propagation_scalar_angular_spectrum/README.zh-CN.md) —
   到目标网格的辐射角谱传播。
5. [`analytic_michelson_interferometer`](analytic_michelson_interferometer/README.zh-CN.md)
   — 同一理想 Cube 在有限 Michelson 干涉仪去程与回程被 Encounter 后产生的互补
   RELATIVE 输出。

请使用 Python 3.12，从仓库根目录运行案例。所有命令行物理量均为 SI 值；源码中
仅用局部常量改善微米和毫米的显示可读性。

案例不增加配置系统、运行时注册表、notebook、benchmark、绘图库依赖或第二套
验证框架。

English: [README.md](README.md)
