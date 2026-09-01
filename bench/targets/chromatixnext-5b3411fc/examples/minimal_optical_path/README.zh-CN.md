# 最小光路

这个案例给出 ChromatixNext 最短的完整科学路径：依次建立空间网格、光谱与偏振
状态，采样平面波，施加圆孔光瞳和理想薄透镜，传播到焦平面，最后探测强度。

## 物理问题

法向入射平面波经过居中圆孔与理想薄透镜后，焦平面强度是否在光轴上取得最大值？

## 方程

该光路遵循标量近轴傅里叶光学结论：均匀照明圆孔在理想薄透镜后一倍焦距处形成
Airy 强度 `I(u) ∝ [2 J₁(u) / u]²`，其中央值为全局最大值。最后一条断言就是
可独立检查的 observable：网格中心强度等于全局最大强度。

## 约定

全部长度使用 SI 米；光源为单色 x 线偏振；时间约定为 `exp(-iωt)`；传播距离等于
理想薄透镜焦距。

## 运行

在仓库根目录执行：

```powershell
$env:PYTHONPATH = "src"
C:\Users\Administrator\miniforge3\envs\research_env\python.exe `
  examples\minimal_optical_path\example.py
```

## 适用范围

本案例只证明标量、单色、近轴、理想元件路径，不包含传感器采样、噪声、像差或
矢量高数值孔径聚焦。

## 来源

科学来源为 Joseph W. Goodman, *Introduction to Fourier Optics*, 3rd edition
（Roberts & Company, 2005）：§4.4.2 给出圆孔的夫琅禾费衍射，§5.2 给出薄透镜
的傅里叶变换性质。程序使用的圆孔、Goodman 薄透镜相位和单变换 Fresnel 方程，
分别由 `tests/element/test_pupil.py`、`tests/element/test_ideal_thin_lens.py`
与 `tests/propagation/test_fresnel_transform.py` 独立验证。

文件共十一条顶层逻辑语句：两条导入、严格遵循物理阅读顺序的八条具名计算语句，
以及一条科学断言。该计数不受命名实参的 CSU 展开排版影响。直接科学计算不依赖
Assembly 或 Workstation，因此本案例不引入这两个概念。
