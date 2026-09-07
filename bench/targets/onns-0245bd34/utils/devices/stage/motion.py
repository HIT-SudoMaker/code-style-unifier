from __future__ import annotations

import math
from pathlib import Path
from types import TracebackType

from .api import ACSMotionStageDeviceAPI


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_VENDOR_DLL_PATH = PACKAGE_ROOT / "vendor" / "acs_motion_stage.dll"
DEFAULT_CONTROLLER_IP = "10.0.0.100"
DEFAULT_STAGE_AXIS = 0
DEFAULT_STAGE_PORT = ACSMotionStageDeviceAPI.DEFAULT_PORT
DEFAULT_STAGE_VELOCITY_MM_PER_SECOND = 0.01
DEFAULT_STAGE_TIMEOUT_MS = 30000
STAGE_MIN_POSITION_MM = -70.0
STAGE_MAX_POSITION_MM = 70.0


class ACSMotionStage:
    """
    单轴运动台适配器
    """

    def __init__(
        self,
        dll_path: str | Path = DEFAULT_VENDOR_DLL_PATH,
        *,
        ip_address: str = DEFAULT_CONTROLLER_IP,
        port: int = DEFAULT_STAGE_PORT,
        axis: int = DEFAULT_STAGE_AXIS,
        min_position: float = STAGE_MIN_POSITION_MM,
        max_position: float = STAGE_MAX_POSITION_MM,
        default_velocity: float = DEFAULT_STAGE_VELOCITY_MM_PER_SECOND,
        default_timeout_ms: int = DEFAULT_STAGE_TIMEOUT_MS,
        api: ACSMotionStageDeviceAPI | None = None,
    ) -> None:
        """
        初始化运动台适配器

        参数:
            dll_path:           ACS C 库 DLL 路径
            ip_address:         控制器 IPv4 地址或主机名
            port:               控制器 TCP 端口
            axis:               默认 ACS 轴号
            min_position:       允许运动台最小位置，单位为 mm
            max_position:       允许运动台最大位置，单位为 mm
            default_velocity:   默认运动速度，单位为 mm/s
            default_timeout_ms: 默认运动等待超时时间，单位为毫秒
            api:                可选底层 API 实例，用于测试

        抛出:
            ValueError:   适配器配置无效时抛出
            RuntimeError: DLL 加载失败时抛出
        """
        _validate_axis(axis)
        _validate_motion_window(min_position, max_position)
        _validate_positive_finite(default_velocity, "default_velocity")
        if int(default_timeout_ms) <= 0:
            message = "default_timeout_ms must be positive"
            raise ValueError(message)

        self.dll_path = Path(dll_path)
        self.ip_address = str(ip_address)
        self.port = int(port)
        self.axis = int(axis)
        self.min_position = float(min_position)
        self.max_position = float(max_position)
        self.default_velocity = float(default_velocity)
        self.default_timeout_ms = int(default_timeout_ms)
        self.api = api if api is not None else ACSMotionStageDeviceAPI(self.dll_path)

    def open(self) -> int | None:
        """
        打开控制器连接
        """
        return self.api.open_ethernet_tcp(self.ip_address, self.port)

    def close(self) -> int:
        """
        关闭控制器连接
        """
        return self.api.close()

    def enable(self, axis: int | None = None) -> int:
        """
        使能运动轴

        参数:
            axis: ACS 轴号；None 表示使用配置的默认轴

        返回:
            ACS 状态码
        """
        axis_number = self._resolve_axis(axis)
        return self.api.enable_axis(axis_number)

    def disable(self, axis: int | None = None) -> int:
        """
        失能运动轴

        参数:
            axis: ACS 轴号；None 表示使用配置的默认轴

        返回:
            ACS 状态码
        """
        axis_number = self._resolve_axis(axis)
        return self.api.disable_axis(axis_number)

    def get_position(self, axis: int | None = None) -> float | None:
        """
        返回反馈位置

        参数:
            axis: ACS 轴号；None 表示使用配置的默认轴

        返回:
            成功时返回反馈位置，否则返回 None
        """
        axis_number = self._resolve_axis(axis)
        return self.api.get_feedback_position(axis_number)

    def move_to(
        self,
        position: float,
        *,
        axis: int | None = None,
        velocity: float | None = None,
        wait: bool = True,
        timeout_ms: int | None = None,
    ) -> int:
        """
        移动到绝对位置

        参数:
            position:   绝对目标位置，单位为 mm
            axis:       ACS 轴号；None 表示使用配置的默认轴
            velocity:   运动速度，单位为 mm/s；None 表示使用默认速度
            wait:       为 True 时等待运动完成
            timeout_ms: 运动等待超时时间；None 表示使用默认超时

        返回:
            ACS 运动命令状态码

        抛出:
            ValueError:   目标位置或速度无效时抛出
            RuntimeError: 必需 ACS 调用失败时抛出

        说明:
            等待失败发生在运动命令发送之后，不能
            保证运动轴保持静止；调用方应根据
            实验安全策略决定是否 halt 或 kill
        """
        axis_number = self._resolve_axis(axis)
        target_position = self._validate_position(position)
        motion_velocity = self._resolve_velocity(velocity)
        wait_timeout_ms = self._resolve_timeout(timeout_ms)

        self._raise_on_status(
            self.api.set_velocity(axis_number, motion_velocity),
            "set velocity",
        )
        status = self.api.move_axis_to_point(axis_number, target_position)
        self._raise_on_status(status, "move axis to point")

        if wait:
            self._raise_on_status(
                self.api.wait_motion_end(axis_number, wait_timeout_ms),
                "wait motion end",
            )
        return status

    def move_by(
        self,
        distance: float,
        *,
        axis: int | None = None,
        velocity: float | None = None,
        wait: bool = True,
        timeout_ms: int | None = None,
    ) -> int:
        """
        按相对距离移动

        参数:
            distance:   相对运动距离，单位为 mm
            axis:       ACS 轴号；None 表示使用配置的默认轴
            velocity:   运动速度，单位为 mm/s；None 表示使用默认速度
            wait:       为 True 时等待运动完成
            timeout_ms: 运动等待超时时间；None 表示使用默认超时

        返回:
            ACS 运动命令状态码

        抛出:
            ValueError:   最终位置或速度无效时抛出
            RuntimeError: 位置读回或必需 ACS 调用失败时抛出

        说明:
            等待失败发生在运动命令发送之后，不能
            保证运动轴保持静止；调用方应根据
            实验安全策略决定是否 halt 或 kill
        """
        axis_number = self._resolve_axis(axis)
        motion_distance = _validate_finite(distance, "distance")
        current_position = self.api.get_feedback_position(axis_number)
        if current_position is None:
            message = "read feedback position failed"
            raise RuntimeError(message)
        self._validate_position(float(current_position) + motion_distance)

        motion_velocity = self._resolve_velocity(velocity)
        wait_timeout_ms = self._resolve_timeout(timeout_ms)

        self._raise_on_status(
            self.api.set_velocity(axis_number, motion_velocity),
            "set velocity",
        )
        status = self.api.move_axis_relative(axis_number, motion_distance)
        self._raise_on_status(status, "move axis relative")

        if wait:
            self._raise_on_status(
                self.api.wait_motion_end(axis_number, wait_timeout_ms),
                "wait motion end",
            )
        return status

    def halt(self, axis: int | None = None) -> int:
        """
        减速停止运动轴

        参数:
            axis: ACS 轴号；None 表示使用配置的默认轴

        返回:
            ACS 状态码
        """
        axis_number = self._resolve_axis(axis)
        return self.api.halt_axis(axis_number)

    def kill(self, axis: int | None = None) -> int:
        """
        立即停止运动轴

        参数:
            axis: ACS 轴号；None 表示使用配置的默认轴

        返回:
            ACS 状态码
        """
        axis_number = self._resolve_axis(axis)
        return self.api.kill_axis(axis_number)

    def __enter__(self) -> ACSMotionStage:
        """
        进入上下文时打开连接
        """
        self.open()
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: TracebackType | None,
    ) -> None:
        """
        离开上下文时关闭连接

        参数:
            exception_type:      托管代码块抛出的异常类型
            exception_value:     托管代码块抛出的异常值
            exception_traceback: 托管代码块抛出的异常回溯
        """
        self.close()

    def _resolve_axis(self, axis: int | None) -> int:
        axis_number = self.axis if axis is None else int(axis)
        _validate_axis(axis_number)
        return axis_number

    def _resolve_velocity(self, velocity: float | None) -> float:
        motion_velocity = self.default_velocity if velocity is None else float(velocity)
        _validate_positive_finite(motion_velocity, "velocity")
        return motion_velocity

    def _resolve_timeout(self, timeout_ms: int | None) -> int:
        wait_timeout_ms = (
            self.default_timeout_ms if timeout_ms is None else int(timeout_ms)
        )
        if wait_timeout_ms <= 0:
            message = "timeout_ms must be positive"
            raise ValueError(message)
        return wait_timeout_ms

    def _validate_position(self, position: float) -> float:
        position_value = _validate_finite(position, "position")
        if (
            position_value < self.min_position
            or position_value > self.max_position
        ):
            raise ValueError(
                "position %.9f is outside hardware window %.9f..%.9f"
                % (position_value, self.min_position, self.max_position)
            )
        return position_value

    def _raise_on_status(self, status: int, operation_name: str) -> None:
        if status != self.api.STATUS_SUCCESS:
            message = "%s failed: status=%s" % (operation_name, status)
            raise RuntimeError(message)


def _validate_axis(axis: int) -> None:
    if int(axis) < 0:
        message = "axis must be non-negative"
        raise ValueError(message)


def _validate_motion_window(
    min_position: float,
    max_position: float,
) -> None:
    min_position_value = _validate_finite(min_position, "min_position")
    max_position_value = _validate_finite(max_position, "max_position")
    if min_position_value >= max_position_value:
        message = "min_position must be less than max_position"
        raise ValueError(message)


def _validate_positive_finite(value: float, name: str) -> None:
    value = _validate_finite(value, name)
    if value <= 0.0:
        message = "%s must be positive" % name
        raise ValueError(message)


def _validate_finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        message = "%s must be finite" % name
        raise ValueError(message)
    return value


__all__ = [
    "ACSMotionStage",
    "DEFAULT_CONTROLLER_IP",
    "DEFAULT_STAGE_AXIS",
    "DEFAULT_STAGE_PORT",
    "DEFAULT_STAGE_TIMEOUT_MS",
    "DEFAULT_STAGE_VELOCITY_MM_PER_SECOND",
    "DEFAULT_VENDOR_DLL_PATH",
    "STAGE_MAX_POSITION_MM",
    "STAGE_MIN_POSITION_MM",
]
