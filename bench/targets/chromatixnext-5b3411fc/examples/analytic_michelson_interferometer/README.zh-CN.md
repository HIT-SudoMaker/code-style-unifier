# 解析 Michelson 干涉仪

## 物理问题

同一块平衡理想非偏振 Cube 在去程与回程各被 Encounter 一次时，两个 Michelson
强度比是否符合由往返光程差给出的互补解析关系？

## 方程

令折射率为 `n`、波长为 `lambda`、两臂长度为 `L_top` 和 `L_right`，则相对相位
与两个 RELATIVE 观测量为

```text
relative_phase = 4 pi n (L_top - L_right) / wavelength
left_ratio = sin^2(relative_phase / 2)
bottom_ratio = cos^2(relative_phase / 2)
```

两者之和为一。冻结的四个相位点 `0`、`pi/3`、`2*pi/3` 与 `pi` 使两个端口的
可见度均为一。

## 冻结参考卡

- Spectrum：单条 `632.8e-9 m` 谱线，权重 `1.0`。
- Medium：真空，常数折射率 `1.0`。
- Grid：`(height, width) = (8, 12)`，间距为
  `(7e-6 m, 11e-6 m)`。
- 输入：常数包络 `1 + 0i`、横向 Jones 状态 `(1 + 0i, 0 + 0i)`，采用
  RELATIVE normalization。
- Cube：原点 `(0, 0, 0) m`、route-right `(1, 0, 0)`、route-top
  `(0, 1, 0)`、rising 对角方向、mixing angle 为 `pi/4`。
- Right Mirror：原点 `(1e-3, 0, 0) m`、outward normal `(-1, 0, 0)`、
  transverse-up `(0, 0, 1)`。
- Top Mirror：原点 `(0, L_top, 0) m`、outward normal `(0, -1, 0)`、
  transverse-up `(0, 0, 1)`。
- 在非退化 `pi/3` 点，`L_right = 1e-3 m`，且
  `L_top = L_right + wavelength/12`。
- 每条臂各有一个显式、正 route-local 去程 Propagation 和一个显式、正
  route-local 回程 Propagation。只有 Propagation 推进 Optical Path Reference，
  每个 action 恰推进一次，因此一条臂累计 `2 n L`。
- 去程 Terminal 次序为 `left -> {right, top}`；回程次序为
  `{top, right} -> {left, bottom}`。按规范 contributor 次序，变换后的 top
  回程分量成为输出 Optical Path Reference。
- 每个理想 Mirror 给出精确局部标量 `-1`。等臂 gauge 下 left 为暗端，bottom
  为亮端。
- 仅有两个 Named Outputs：Detection 观测量 `left_intensity` 与
  `bottom_intensity`。

冻结的 fixed-double 接受预算为：独立 dense complex operator 的最大绝对误差不超过
`5e-13`，每个端口比、互补和、可见度的绝对误差均不超过 `2e-12`。每个必需反事实
都必须使至少一个端口比相差不小于 `0.20`。

## 单一 owner 与有限拓扑

Assembly 只注册一个名为 `cube` 的 Cube；`outward_cube` 与 `return_cube` 两个
Encounter 引用同一个对象。两面 Mirror 使两臂折返，四个显式 Propagation 拥有
距离与相位，两个回程 Terminal 分别进入 Intensity Detection。每个 directional
输出都有下游连接；return Encounter 之外不手工相加光场，也不把光路压平成伪直线
拓扑。

## 运行

在仓库根目录执行：

```powershell
$env:PYTHONPATH = "src"
C:\Users\Administrator\miniforge3\envs\research_env\python.exe `
  examples\analytic_michelson_interferometer\example.py
```

## 适用范围

本案例是单色、法向入射、理想、无损、相干 Wave 模型，只采用 RELATIVE
normalization。它只证明冻结 fixture 的无量纲端口比、互补性与可见度；不描述表征后
或真实 coating，不推断重复 Encounter 或腔递归，不提供 Ray 观测闭合，不作性能
断言，也不定义 optimizer 或 experiment runtime。同时省略两臂相同 Mirror 标量只会
产生共同全局相位，不能由本案例观测；专测因此在 `pi/3` 挑战只遗漏一臂的情形。

## 来源

- Physical Value、Optical Path Reference、Assembly、Terminal、Encounter 与
  Detection 语言由 [`CONTEXT.md`](../../CONTEXT.md) 固定。
- Example 所有权由
  [ADR-0004](../../docs/adr/0004-example-owned-research-workflows.md) 固定。
- 理想响应实现见
  [`ideal_cube_beam_splitter.py`](../../src/chromatix_next/optics/element/ideal_cube_beam_splitter.py)、
  [`ideal_planar_mirror.py`](../../src/chromatix_next/optics/element/ideal_planar_mirror.py)
  与
  [`scalar_angular_spectrum.py`](../../src/chromatix_next/optics/propagation/scalar_angular_spectrum.py)。
- 常数、gauge、相位点和数值预算逐项复现 direction-aware scientific foundation
  vNext specification 第 12 节的冻结解析 Michelson 参考卡。
