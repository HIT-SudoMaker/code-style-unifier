# ZWO ASI 相机模块

## 设计定位

本模块封装 ZWO ASI 相机的厂商 SDK，当前面向 RAW8 图像采集和 ASI585MM 的默认全幅参数。

它只负责相机发现、打开、初始化、ROI 配置、帧读取和连续采集流，不负责图像归一化、磁盘写入、GUI 更新或实验策略。

## 架构边界

- `api.py`：底层相机 SDK 绑定，按发现、打开、初始化、配置、采集、停止、关闭的顺序组织接口
- `frame.py`：定义 `CameraFrame`，固定 RAW8 帧数据契约和 ctypes 缓冲区转换
- `stream.py`：连续 RAW8 采集流，管理采集线程、最新帧缓存、输出队列和运行统计
- `examples/bring_up.py`：相机发现和控制项枚举示例
- `examples/capture_raw8.py`：单帧或多帧 RAW8 采集示例
- `examples/stream_raw8.py`：连续采集流示例
- `_bindings.py`：内部 ctypes 结构体和函数签名表，二次开发通常不需要直接使用

## 最小用法

```python
from utils.devices.camera import VENDOR_DLL_PATH
from utils.devices.camera._bindings import ASI_IMG_RAW8
from utils.devices.camera.api import ZWOASICameraDeviceAPI


api = ZWOASICameraDeviceAPI(VENDOR_DLL_PATH)
camera_info = api.get_camera_info(camera_index=0)
if camera_info is None:
    raise RuntimeError("未找到相机")

camera_id = camera_info.camera_id
width = camera_info.max_width
height = camera_info.max_height

api.open_camera(camera_id)
try:
    api.initialize_camera(camera_id)
    api.set_roi_format(camera_id, width, height, 1, ASI_IMG_RAW8)
    api.start_video_capture(camera_id)
    try:
        status, frame = api.capture_raw8_frame(
            camera_id=camera_id,
            width=width,
            height=height,
            timeout_ms=1000,
        )
    finally:
        api.stop_video_capture(camera_id)
finally:
    api.close_camera(camera_id)
```

连续采集可以使用 `ZWOASICameraStream`：

```python
from utils.devices.camera import VENDOR_DLL_PATH
from utils.devices.camera import ZWOASICameraStream


with ZWOASICameraStream(VENDOR_DLL_PATH, target_output_fps=30.0) as stream:
    frame = stream.get_frame(timeout=1.0)
    stats = stream.get_statistics()
```

## 二次开发原则

- 低层采集流程放在 `api.py`，连续采集策略放在 `stream.py`
- 新帧格式应先明确数据契约，再扩展 `frame.py`
- 实验层可以决定曝光、增益、保存和可视化，但不要塞进底层 API
- 流式采集只发布 `CameraFrame`，避免在采集线程中加入重计算

## 硬件注意

- 当前默认全幅尺寸为 `3840 x 2160`
- `capture_raw8_frame` 返回 SDK 状态码和帧；状态失败时帧为 `None`
- 采集启动后必须调用 `stop_video_capture`，相机打开后必须关闭
- 输出队列满时默认丢弃旧帧，以避免采集线程阻塞

## 验证入口

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest tests\utils\devices\camera -q
```
