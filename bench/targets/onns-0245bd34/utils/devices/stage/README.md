# ACS 运动台模块

## 设计定位

本模块封装 ACS SPiiPlus 运动控制器的厂商 C 库，并提供项目使用的一维运动台高层适配器。

底层 API 保持厂商调用语义，高层适配器只加入连接参数、默认轴、速度、超时和硬件运动窗口，不负责扫描计划、标定策略或实验安全联锁。

## 架构边界

- `api.py`：底层 ACS C 库绑定，管理连接、命令、查询、运动、状态和错误文本
- `motion.py`：高层单轴适配器 `ACSMotionStage`，提供 `open`、`close`、`enable`、`move_to`、`move_by`、`halt`、`kill`
- `examples/bring_up.py`：运动台连接和基础状态检查示例
- `examples/move_axis.py`：显式确认后移动一个运动轴的示例
- `_bindings.py`：内部 ctypes 函数签名表，二次开发通常不需要直接使用

## 最小用法

```python
from utils.devices.stage import ACSMotionStage
from utils.devices.stage import VENDOR_DLL_PATH


stage = ACSMotionStage(
    dll_path=VENDOR_DLL_PATH,
    ip_address="10.0.0.100",
    axis=0,
)

handle = stage.open()
if handle is None:
    raise RuntimeError("运动控制器连接失败")

try:
    stage.enable()
    stage.move_to(position=1.0)
    position = stage.get_position()
finally:
    try:
        stage.disable()
    finally:
        stage.close()
```

## 二次开发原则

- 厂商函数封装放在 `api.py`，实验友好的单轴动作放在 `motion.py`
- 扫描路径、步进策略、图像采集同步和异常恢复应放在实验层
- 新增运动动作前应明确它是底层 ACS 语义，还是项目高层语义
- 硬件窗口默认是 `-70 mm` 到 `70 mm`，不应在实验代码里绕过

## 硬件注意

- `move_to` 和 `move_by` 默认等待运动完成
- 等待失败发生在运动命令发送之后，不代表运动轴没有移动
- 等待失败后是否 `halt` 或 `kill` 应由实验安全策略决定
- 示例移动程序默认 dry run，需要显式传入 `--run-token RUN` 才会发送运动命令

## 验证入口

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest tests\utils\devices\stage -q
```
