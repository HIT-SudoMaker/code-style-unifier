# HDSLM 空间光调制器模块

## 设计定位

本模块封装 HDSLM 系列空间光调制器的厂商 DLL 调用，提供清晰的设备生命周期、帧数据契约和常用数据转换入口。

它只负责把已经准备好的灰度图、强度图或相位图送入硬件，不负责光学传播、训练策略、标定流程或实验编排。

## 架构边界

- `api.py`：底层 DLL 绑定，按设备生命周期提供显示器查询、打开、关闭、数据显示、Gamma 和触发配置等接口
- `frame.py`：定义 `SLMFrame`，固定 10bit 硬件帧数据契约，并提供 ctypes 缓冲区转换
- `converter.py`：将归一化强度图或相位图转换为 10bit `SLMFrame`
- `examples/bring_up.py`：最小联通和控制检查流程
- `examples/display.py`：固定灰度、图像文件和数组图样显示示例
- `_bindings.py`：内部 ctypes 函数签名表，二次开发通常不需要直接使用

## 最小用法

```python
import numpy as np

from utils.devices.slm import UPOLabsSLMDeviceAPI
from utils.devices.slm import VENDOR_DLL_PATH
from utils.devices.slm import phase_to_slm_frame
from utils.devices.slm import slm_frame_to_ctypes_buffer


display_number = 0
phase = np.zeros((1200, 1920), dtype=np.float32)

api = UPOLabsSLMDeviceAPI(VENDOR_DLL_PATH)
frame = phase_to_slm_frame(phase)
buffer = slm_frame_to_ctypes_buffer(frame)

api.open_display(display_number)
try:
    status = api.display_integer_data(
        display_number=display_number,
        width=frame.width,
        height=frame.height,
        gray_level_count=frame.gray_level_count,
        data=buffer,
    )
finally:
    api.close_display(display_number)
```

## 二次开发原则

- 新的数据入口应先转换为 `SLMFrame`，再进入 `api.py`
- 强度图保持 `0..1`，相位图由 `phase_period` 控制回绕周期
- 实验策略、相位优化、光路模型和结果保存应放在 experiments 层
- 厂商函数签名只在 `_bindings.py` 维护，避免散落在业务代码中

## 硬件注意

- 发送到硬件的整数帧必须是二维 `uint16`，范围为 `0..1023`
- 显示分辨率、显示器编号和 Gamma 文件应在实验前确认
- ASCII 路径接口只接受 ASCII 文件路径；中文路径应使用宽字符路径接口
- 示例程序用于联通检查，不替代正式实验的光路标定和安全流程

## 验证入口

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest tests\utils\devices\slm -q
```
