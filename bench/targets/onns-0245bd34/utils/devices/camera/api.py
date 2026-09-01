from __future__ import annotations

import ctypes
from dataclasses import dataclass
from pathlib import Path

from ._bindings import (
    ASI_CAMERA_INFO,
    ASI_CONTROL_CAPS,
    ASI_BANDWIDTHOVERLOAD,
    ASI_EXPOSURE,
    ASI_GAIN,
    ASI_GAMMA,
    ASI_HIGH_SPEED_MODE,
    ASI_ERROR_TIMEOUT,
    ASI_IMG_RAW16,
    ASI_IMG_RAW8,
    ASI_IMG_RGB24,
    ASI_IMG_Y8,
    ASI_OFFSET,
    ASI_SUCCESS,
    configure_camera_dll_functions,
)
from .frame import CameraFrame
from .frame import raw8_buffer_to_camera_frame


@dataclass(frozen=True)
class ZWOASICameraInfo:
    """
    相机信息

    参数:
        name:                    相机型号名称
        camera_id:               SDK 调用使用的相机 ID
        max_width:               传感器最大宽度
        max_height:              传感器最大高度
        is_color_camera:         是否为彩色相机
        supported_bins:          支持的 binning 系数
        supported_video_formats: 支持的 ASI 图像类型
        pixel_size_um:           像元尺寸，单位为微米
        bit_depth:               传感器位深
        is_trigger_camera:       是否支持触发模式
    """

    name: str
    camera_id: int
    max_width: int
    max_height: int
    is_color_camera: bool
    supported_bins: tuple[int, ...]
    supported_video_formats: tuple[int, ...]
    pixel_size_um: float
    bit_depth: int
    is_trigger_camera: bool


@dataclass(frozen=True)
class ZWOASIControlCaps:
    """
    控制能力

    参数:
        name:              控制项名称
        description:       厂商说明
        min_value:         最小允许值
        max_value:         最大允许值
        default_value:     默认值
        is_auto_supported: 是否支持自动模式
        is_writable:       控制项是否可写
        control_type:      ZWO ASI 控制类型
    """

    name: str
    description: str
    min_value: int
    max_value: int
    default_value: int
    is_auto_supported: bool
    is_writable: bool
    control_type: int


class ZWOASICameraDeviceAPI:
    """
    相机底层绑定
    """

    STATUS_SUCCESS = ASI_SUCCESS

    IMAGE_TYPE_RAW8 = ASI_IMG_RAW8
    IMAGE_TYPE_RGB24 = ASI_IMG_RGB24
    IMAGE_TYPE_RAW16 = ASI_IMG_RAW16
    IMAGE_TYPE_Y8 = ASI_IMG_Y8

    CONTROL_GAIN = ASI_GAIN
    CONTROL_EXPOSURE = ASI_EXPOSURE
    CONTROL_GAMMA = ASI_GAMMA
    CONTROL_OFFSET = ASI_OFFSET
    CONTROL_BANDWIDTH_OVERLOAD = ASI_BANDWIDTHOVERLOAD
    CONTROL_HIGH_SPEED_MODE = ASI_HIGH_SPEED_MODE

    def __init__(self, dll_path: str | Path) -> None:
        """
        加载相机动态库

        参数:
            dll_path: ZWO ASI 相机 DLL 完整路径

        抛出:
            RuntimeError: DLL 加载失败时抛出
        """
        self._dll_path = Path(dll_path)
        self._last_dll_load_error: Exception | None = None

        try:
            self._dll = ctypes.WinDLL(str(self._dll_path))
        except Exception as error:
            self._last_dll_load_error = error
            message = "Failed to load ZWO ASI DLL: %s" % self._dll_path
            raise RuntimeError(message) from error

        self._configure_functions()

    def _configure_functions(self) -> None:
        configure_camera_dll_functions(self._dll)

    def get_sdk_version(self) -> str:
        """
        读取软件库版本
        """
        raw_version = self._dll.ASIGetSDKVersion()
        if raw_version is None:
            return ""
        if isinstance(raw_version, bytes):
            return _decode_c_string(raw_version)
        return _decode_c_string(ctypes.cast(raw_version, ctypes.c_char_p).value or b"")

    def get_camera_count(self) -> int:
        """
        读取已连接相机数量
        """
        return int(self._dll.ASIGetNumOfConnectedCameras())

    def get_camera_info(
        self,
        camera_index: int,
    ) -> ZWOASICameraInfo | None:
        """
        读取相机信息

        参数:
            camera_index: 从零开始的已连接相机索引

        返回:
            成功时返回相机信息，否则返回 None
        """
        camera_info = ASI_CAMERA_INFO()
        status = self._dll.ASIGetCameraProperty(
            ctypes.byref(camera_info),
            int(camera_index),
        )
        if status != self.STATUS_SUCCESS:
            return None
        return _decode_camera_info(camera_info)

    def open_camera(self, camera_id: int) -> int:
        """
        打开相机

        参数:
            camera_id: SDK 相机 ID

        返回:
            SDK 状态码
        """
        return self._dll.ASIOpenCamera(int(camera_id))

    def initialize_camera(self, camera_id: int) -> int:
        """
        初始化相机

        参数:
            camera_id: SDK 相机 ID

        返回:
            SDK 状态码
        """
        return self._dll.ASIInitCamera(int(camera_id))

    def close_camera(self, camera_id: int) -> int:
        """
        关闭相机

        参数:
            camera_id: SDK 相机 ID

        返回:
            SDK 状态码
        """
        return self._dll.ASICloseCamera(int(camera_id))

    def get_control_count(self, camera_id: int) -> int | None:
        """
        读取控制项数量

        参数:
            camera_id: SDK 相机 ID

        返回:
            成功时返回控制项数量，否则返回 None
        """
        control_count = ctypes.c_int()
        status = self._dll.ASIGetNumOfControls(
            int(camera_id),
            ctypes.byref(control_count),
        )
        if status == self.STATUS_SUCCESS:
            return control_count.value
        return None

    def get_control_caps(
        self,
        camera_id: int,
        control_index: int,
    ) -> ZWOASIControlCaps | None:
        """
        读取控制项能力

        参数:
            camera_id:      SDK 相机 ID
            control_index:  从零开始的控制项索引

        返回:
            成功时返回控制项能力，否则返回 None
        """
        control_caps = ASI_CONTROL_CAPS()
        status = self._dll.ASIGetControlCaps(
            int(camera_id),
            int(control_index),
            ctypes.byref(control_caps),
        )
        if status != self.STATUS_SUCCESS:
            return None
        return _decode_control_caps(control_caps)

    def get_control_value(
        self,
        camera_id: int,
        control_type: int,
    ) -> tuple[int | None, int | None]:
        """
        读取控制值

        参数:
            camera_id:    SDK 相机 ID
            control_type: ZWO ASI 控制类型

        返回:
            成功时返回控制值和自动标志，否则返回 None
        """
        value = ctypes.c_long()
        auto_enabled = ctypes.c_int()
        status = self._dll.ASIGetControlValue(
            int(camera_id),
            int(control_type),
            ctypes.byref(value),
            ctypes.byref(auto_enabled),
        )
        if status == self.STATUS_SUCCESS:
            return int(value.value), int(auto_enabled.value)
        return None, None

    def set_control_value(
        self,
        camera_id: int,
        control_type: int,
        value: int,
        auto_enabled: int = 0,
    ) -> int:
        """
        设置控制值

        参数:
            camera_id:     SDK 相机 ID
            control_type:  ZWO ASI 控制类型
            value:         控制值
            auto_enabled:  自动模式标志

        返回:
            SDK 状态码
        """
        return self._dll.ASISetControlValue(
            int(camera_id),
            int(control_type),
            int(value),
            int(auto_enabled),
        )

    def set_roi_format(
        self,
        camera_id: int,
        width: int,
        height: int,
        binning: int = 1,
        image_type: int = ASI_IMG_RAW8,
    ) -> int:
        """
        设置采集区域

        参数:
            camera_id:  SDK 相机 ID
            width:      binning 后的 ROI 宽度
            height:     binning 后的 ROI 高度
            binning:    binning 系数
            image_type: ZWO ASI 图像类型

        返回:
            SDK 状态码
        """
        return self._dll.ASISetROIFormat(
            int(camera_id),
            int(width),
            int(height),
            int(binning),
            int(image_type),
        )

    def get_roi_format(
        self,
        camera_id: int,
    ) -> tuple[int | None, int | None, int | None, int | None]:
        """
        读取采集区域

        参数:
            camera_id: SDK 相机 ID

        返回:
            成功时返回宽度、高度、binning 和图像类型
        """
        width = ctypes.c_int()
        height = ctypes.c_int()
        binning = ctypes.c_int()
        image_type = ctypes.c_int()
        status = self._dll.ASIGetROIFormat(
            int(camera_id),
            ctypes.byref(width),
            ctypes.byref(height),
            ctypes.byref(binning),
            ctypes.byref(image_type),
        )
        if status == self.STATUS_SUCCESS:
            return width.value, height.value, binning.value, image_type.value
        return None, None, None, None

    def start_video_capture(self, camera_id: int) -> int:
        """
        开始视频采集

        参数:
            camera_id: SDK 相机 ID

        返回:
            SDK 状态码
        """
        return self._dll.ASIStartVideoCapture(int(camera_id))

    def get_video_data(
        self,
        camera_id: int,
        buffer: ctypes.Array,
        timeout_ms: int,
    ) -> int:
        """
        读取下一帧

        参数:
            camera_id:  SDK 相机 ID
            buffer:     调用方持有的 c_ubyte 缓冲区
            timeout_ms: 等待超时时间，单位为毫秒

        返回:
            SDK 状态码
        """
        return self._dll.ASIGetVideoData(
            int(camera_id),
            buffer,
            len(buffer),
            int(timeout_ms),
        )

    def capture_raw8_frame(
        self,
        camera_id: int,
        width: int,
        height: int,
        timeout_ms: int = 1000,
    ) -> tuple[int, CameraFrame | None]:
        """
        采集一帧八位图像

        参数:
            camera_id:  SDK 相机 ID
            width:      帧宽度，单位为像素
            height:     帧高度，单位为像素
            timeout_ms: 等待超时时间，单位为毫秒

        返回:
            返回 SDK 状态码和采集帧；SDK 采集失败时帧为 None
        """
        buffer_type = ctypes.c_ubyte * (int(width) * int(height))
        buffer = buffer_type()
        status = self.get_video_data(
            camera_id=int(camera_id),
            buffer=buffer,
            timeout_ms=int(timeout_ms),
        )
        if status != self.STATUS_SUCCESS:
            return status, None
        frame = raw8_buffer_to_camera_frame(buffer, width=int(width), height=int(height))
        return status, frame

    def stop_video_capture(self, camera_id: int) -> int:
        """
        停止视频采集

        参数:
            camera_id: SDK 相机 ID

        返回:
            SDK 状态码
        """
        return self._dll.ASIStopVideoCapture(int(camera_id))

    def get_dropped_frames(self, camera_id: int) -> int | None:
        """
        读取丢帧计数

        参数:
            camera_id: SDK 相机 ID

        返回:
            成功时返回丢帧计数，否则返回 None
        """
        dropped_frames = ctypes.c_int()
        status = self._dll.ASIGetDroppedFrames(
            int(camera_id),
            ctypes.byref(dropped_frames),
        )
        if status == self.STATUS_SUCCESS:
            return dropped_frames.value
        return None


def _decode_camera_info(camera_info: ASI_CAMERA_INFO) -> ZWOASICameraInfo:
    return ZWOASICameraInfo(
        name=_decode_c_string(bytes(camera_info.Name)),
        camera_id=int(camera_info.CameraID),
        max_width=int(camera_info.MaxWidth),
        max_height=int(camera_info.MaxHeight),
        is_color_camera=bool(camera_info.IsColorCam),
        supported_bins=_collect_nonzero_ints(camera_info.SupportedBins),
        supported_video_formats=_collect_until_sentinel(
            camera_info.SupportedVideoFormat,
            sentinel=-1,
        ),
        pixel_size_um=float(camera_info.PixelSize),
        bit_depth=int(camera_info.BitDepth),
        is_trigger_camera=bool(camera_info.IsTriggerCam),
    )


def _decode_control_caps(control_caps: ASI_CONTROL_CAPS) -> ZWOASIControlCaps:
    return ZWOASIControlCaps(
        name=_decode_c_string(bytes(control_caps.Name)),
        description=_decode_c_string(bytes(control_caps.Description)),
        min_value=int(control_caps.MinValue),
        max_value=int(control_caps.MaxValue),
        default_value=int(control_caps.DefaultValue),
        is_auto_supported=bool(control_caps.IsAutoSupported),
        is_writable=bool(control_caps.IsWritable),
        control_type=int(control_caps.ControlType),
    )


def _collect_nonzero_ints(values: object) -> tuple[int, ...]:
    collected: list[int] = []
    for value in values:
        int_value = int(value)
        if int_value == 0:
            break
        collected.append(int_value)
    return tuple(collected)


def _collect_until_sentinel(
    values: object,
    *,
    sentinel: int,
) -> tuple[int, ...]:
    collected: list[int] = []
    for value in values:
        int_value = int(value)
        if int_value == sentinel:
            break
        collected.append(int_value)
    return tuple(collected)


def _decode_c_string(raw_value: bytes) -> str:
    text = raw_value.split(b"\x00", 1)[0]
    for encoding in ("utf-8", "mbcs"):
        try:
            return text.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return text.decode("utf-8", errors="replace")


__all__ = [
    "ASI_ERROR_TIMEOUT",
    "ZWOASICameraDeviceAPI",
    "ZWOASICameraInfo",
    "ZWOASIControlCaps",
]
