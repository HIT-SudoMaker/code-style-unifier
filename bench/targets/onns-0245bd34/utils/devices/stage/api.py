from __future__ import annotations

import ctypes
from pathlib import Path

from ._bindings import (
    ACSC_AMF_RELATIVE,
    ACSC_INVALID,
    ACSC_MST_MOVE,
    ACSC_SOCKET_STREAM_PORT,
    configure_stage_dll_functions,
)


_TEXT_BUFFER_SIZE = 1024


class ACSMotionStageDeviceAPI:
    """
    运动台底层绑定
    """

    STATUS_SUCCESS = 1
    STATUS_FAILURE = 0

    DEFAULT_PORT = ACSC_SOCKET_STREAM_PORT
    MOVE_STATE_BIT = ACSC_MST_MOVE
    RELATIVE_MOVE_FLAG = ACSC_AMF_RELATIVE

    def __init__(self, dll_path: str | Path) -> None:
        """
        加载运动台动态库

        参数:
            dll_path: ACS 运动台 DLL 完整路径

        抛出:
            RuntimeError: DLL 加载失败时抛出
        """
        self._dll_path = Path(dll_path)
        self._last_dll_load_error: Exception | None = None
        self._handle: int | None = None

        try:
            self._dll = ctypes.WinDLL(str(self._dll_path))
        except Exception as error:
            self._last_dll_load_error = error
            raise RuntimeError(
                "Failed to load ACS stage DLL: %s" % self._dll_path
            ) from error

        self._configure_functions()

    def _configure_functions(self) -> None:
        configure_stage_dll_functions(self._dll)

    def open_ethernet_tcp(
        self,
        address: str,
        port: int = ACSC_SOCKET_STREAM_PORT,
    ) -> int | None:
        """
        打开网络连接

        参数:
            address: 控制器 IPv4 地址或主机名
            port:    TCP 端口；ACS 流端口默认 701

        返回:
            成功时返回通信句柄，否则返回 None

        抛出:
            ValueError: 地址无法编码为 ASCII 时抛出
        """
        encoded_address = address.encode("ascii")
        handle = self._dll.acsc_OpenCommEthernetTCP(encoded_address, int(port))
        handle_value = _normalize_handle(handle)
        if handle_value in (None, ACSC_INVALID):
            self._handle = None
            return None

        self._handle = handle_value
        return handle_value

    def close(self) -> int:
        """
        关闭当前连接
        """
        handle = self._require_handle()
        status = self._dll.acsc_CloseComm(handle)
        if status == self.STATUS_SUCCESS:
            self._handle = None
        return status

    def get_library_version(self) -> int:
        """
        读取库版本
        """
        return int(self._dll.acsc_GetLibraryVersion())

    def get_firmware_version(self) -> str | None:
        """
        读取固件版本
        """
        handle = self._require_handle()
        buffer = ctypes.create_string_buffer(_TEXT_BUFFER_SIZE)
        received = ctypes.c_int()
        status = self._dll.acsc_GetFirmwareVersion(
            handle,
            buffer,
            _TEXT_BUFFER_SIZE,
            ctypes.byref(received),
            None,
        )
        if status != self.STATUS_SUCCESS:
            return None
        return _decode_buffer(buffer, received.value)

    def send_command(self, command: str) -> int:
        """
        发送控制命令

        参数:
            command: ACSPL 命令文本，不包含末尾回车

        返回:
            ACS 状态码

        抛出:
            ValueError: 命令无法编码为 ASCII 时抛出
        """
        command_text = command if command.endswith("\r") else command + "\r"
        encoded_command = command_text.encode("ascii")
        return self._dll.acsc_Send(
            self._require_handle(),
            encoded_command,
            len(encoded_command),
            None,
        )

    def receive_response(self, buffer_size: int = _TEXT_BUFFER_SIZE) -> str | None:
        """
        接收控制响应

        参数:
            buffer_size: 接收缓冲区大小，单位为字节

        返回:
            成功时返回响应文本，否则返回 None
        """
        buffer = ctypes.create_string_buffer(int(buffer_size))
        received = ctypes.c_int()
        status = self._dll.acsc_Receive(
            self._require_handle(),
            buffer,
            int(buffer_size),
            ctypes.byref(received),
            None,
        )
        if status != self.STATUS_SUCCESS:
            return None
        return _decode_buffer(buffer, received.value)

    def query_command(
        self,
        command: str,
        buffer_size: int = _TEXT_BUFFER_SIZE,
    ) -> str | None:
        """
        发送查询并读取响应

        参数:
            command:     ACSPL 查询命令文本
            buffer_size: 接收缓冲区大小，单位为字节

        返回:
            成功时返回响应文本，否则返回 None
        """
        status = self.send_command(command)
        if status != self.STATUS_SUCCESS:
            return None
        return self.receive_response(buffer_size=buffer_size)

    def query_float(self, expression: str) -> float | None:
        """
        查询浮点表达式

        参数:
            expression: ACSPL 表达式，不包含开头问号

        返回:
            成功时返回解析出的浮点值，否则返回 None
        """
        response = self.query_command("?" + expression)
        if response is None:
            return None
        return _parse_first_float(response)

    def query_int(self, expression: str) -> int | None:
        """
        查询整型表达式

        参数:
            expression: ACSPL 表达式，不包含开头问号

        返回:
            成功时返回解析出的整数值，否则返回 None
        """
        value = self.query_float(expression)
        if value is None:
            return None
        return int(value)

    def enable_axis(self, axis: int) -> int:
        """
        使能运动轴

        参数:
            axis: ACS 轴号

        返回:
            ACS 状态码
        """
        return self._dll.acsc_Enable(self._require_handle(), int(axis), None)

    def disable_axis(self, axis: int) -> int:
        """
        失能运动轴

        参数:
            axis: ACS 轴号

        返回:
            ACS 状态码
        """
        return self._dll.acsc_Disable(self._require_handle(), int(axis), None)

    def disable_all(self) -> int:
        """
        失能全部运动轴
        """
        return self._dll.acsc_DisableAll(self._require_handle(), None)

    def set_acceleration(
        self,
        axis: int,
        acceleration: float,
    ) -> int:
        """
        设置默认加速度

        参数:
            axis:         ACS 轴号
            acceleration: 控制器工程单位下的加速度

        返回:
            ACS 状态码
        """
        return self._dll.acsc_SetAcceleration(
            self._require_handle(),
            int(axis),
            float(acceleration),
            None,
        )

    def get_acceleration(self, axis: int) -> float | None:
        """
        读取默认加速度

        参数:
            axis: ACS 轴号

        返回:
            成功时返回加速度，否则返回 None
        """
        acceleration = ctypes.c_double()
        status = self._dll.acsc_GetAcceleration(
            self._require_handle(),
            int(axis),
            ctypes.byref(acceleration),
            None,
        )
        if status == self.STATUS_SUCCESS:
            return acceleration.value
        return None

    def set_deceleration(
        self,
        axis: int,
        deceleration: float,
    ) -> int:
        """
        设置默认减速度

        参数:
            axis:         ACS 轴号
            deceleration: 控制器工程单位下的减速度

        返回:
            ACS 状态码
        """
        return self._dll.acsc_SetDeceleration(
            self._require_handle(),
            int(axis),
            float(deceleration),
            None,
        )

    def get_deceleration(self, axis: int) -> float | None:
        """
        读取默认减速度

        参数:
            axis: ACS 轴号

        返回:
            成功时返回减速度，否则返回 None
        """
        deceleration = ctypes.c_double()
        status = self._dll.acsc_GetDeceleration(
            self._require_handle(),
            int(axis),
            ctypes.byref(deceleration),
            None,
        )
        if status == self.STATUS_SUCCESS:
            return deceleration.value
        return None

    def set_velocity(
        self,
        axis: int,
        velocity: float,
    ) -> int:
        """
        设置默认速度

        参数:
            axis:     ACS 轴号
            velocity: 控制器工程单位下的速度

        返回:
            ACS 状态码
        """
        return self._dll.acsc_SetVelocity(
            self._require_handle(),
            int(axis),
            float(velocity),
            None,
        )

    def get_velocity(self, axis: int) -> float | None:
        """
        读取默认速度

        参数:
            axis: ACS 轴号

        返回:
            成功时返回速度，否则返回 None
        """
        velocity = ctypes.c_double()
        status = self._dll.acsc_GetVelocity(
            self._require_handle(),
            int(axis),
            ctypes.byref(velocity),
            None,
        )
        if status == self.STATUS_SUCCESS:
            return velocity.value
        return None

    def move_axis_to_point(
        self,
        axis: int,
        position: float,
        flags: int = 0,
    ) -> int:
        """
        下发绝对点位运动

        参数:
            axis:     ACS 轴号
            position: 控制器工程单位下的目标位置
            flags:    ACS 运动标志

        返回:
            ACS 状态码
        """
        return self._dll.acsc_ToPoint(
            self._require_handle(),
            int(flags),
            int(axis),
            float(position),
            None,
        )

    def move_axis_relative(
        self,
        axis: int,
        distance: float,
    ) -> int:
        """
        下发相对点位运动

        参数:
            axis:     ACS 轴号
            distance: 相对运动距离

        返回:
            ACS 状态码
        """
        return self.move_axis_to_point(
            axis=axis,
            position=float(distance),
            flags=ACSC_AMF_RELATIVE,
        )

    def halt_axis(self, axis: int) -> int:
        """
        减速停止运动轴

        参数:
            axis: ACS 轴号

        返回:
            ACS 状态码
        """
        return self._dll.acsc_Halt(self._require_handle(), int(axis), None)

    def kill_axis(self, axis: int) -> int:
        """
        立即停止运动轴

        参数:
            axis: ACS 轴号

        返回:
            ACS 状态码
        """
        return self._dll.acsc_Kill(self._require_handle(), int(axis), None)

    def kill_all(self) -> int:
        """
        立即停止全部运动轴
        """
        return self._dll.acsc_KillAll(self._require_handle(), None)

    def get_feedback_position(self, axis: int) -> float | None:
        """
        读取反馈位置

        参数:
            axis: ACS 轴号

        返回:
            成功时返回反馈位置，否则返回 None
        """
        position = ctypes.c_double()
        status = self._dll.acsc_GetFPosition(
            self._require_handle(),
            int(axis),
            ctypes.byref(position),
            None,
        )
        if status == self.STATUS_SUCCESS:
            return position.value
        return None

    def get_reference_position(self, axis: int) -> float | None:
        """
        读取参考位置

        参数:
            axis: ACS 轴号

        返回:
            成功时返回参考位置，否则返回 None
        """
        position = ctypes.c_double()
        status = self._dll.acsc_GetRPosition(
            self._require_handle(),
            int(axis),
            ctypes.byref(position),
            None,
        )
        if status == self.STATUS_SUCCESS:
            return position.value
        return None

    def get_target_position(self, axis: int) -> float | None:
        """
        读取目标位置

        参数:
            axis: ACS 轴号

        返回:
            成功时返回目标位置，否则返回 None
        """
        position = ctypes.c_double()
        status = self._dll.acsc_GetTargetPosition(
            self._require_handle(),
            int(axis),
            ctypes.byref(position),
            None,
        )
        if status == self.STATUS_SUCCESS:
            return position.value
        return None

    def get_motor_state(self, axis: int) -> int | None:
        """
        读取电机状态位

        参数:
            axis: ACS 轴号

        返回:
            成功时返回电机状态位掩码，否则返回 None
        """
        state = ctypes.c_int()
        status = self._dll.acsc_GetMotorState(
            self._require_handle(),
            int(axis),
            ctypes.byref(state),
            None,
        )
        if status == self.STATUS_SUCCESS:
            return state.value
        return None

    def is_axis_moving(self, axis: int) -> bool | None:
        """
        判断运动轴是否在运动

        参数:
            axis: ACS 轴号

        返回:
            成功时返回 True 或 False，否则返回 None
        """
        state = self.get_motor_state(axis)
        if state is None:
            return None
        return bool(state & ACSC_MST_MOVE)

    def wait_motion_end(
        self,
        axis: int,
        timeout_ms: int,
    ) -> int:
        """
        等待运动结束

        参数:
            axis:       ACS 轴号
            timeout_ms: 超时时间，单位为毫秒

        返回:
            ACS 状态码
        """
        return self._dll.acsc_WaitMotionEnd(
            self._require_handle(),
            int(axis),
            int(timeout_ms),
        )

    def get_last_error(self) -> int:
        """
        读取最后错误码
        """
        return int(self._dll.acsc_GetLastError())

    def get_error_string(
        self,
        error_code: int,
    ) -> str | None:
        """
        读取错误文本

        参数:
            error_code: ACS 错误码

        返回:
            成功时返回错误文本，否则返回 None
        """
        buffer = ctypes.create_string_buffer(_TEXT_BUFFER_SIZE)
        received = ctypes.c_int()
        status = self._dll.acsc_GetErrorString(
            self._require_handle(),
            int(error_code),
            buffer,
            _TEXT_BUFFER_SIZE,
            ctypes.byref(received),
        )
        if status != self.STATUS_SUCCESS:
            return None
        return _decode_buffer(buffer, received.value)

    def _require_handle(self) -> int:
        if self._handle is None:
            message = "ACS controller is not connected"
            raise RuntimeError(message)
        return self._handle


def _normalize_handle(handle: object) -> int | None:
    if isinstance(handle, ctypes.c_void_p):
        return handle.value
    if handle is None:
        return None
    return int(handle)


def _decode_buffer(
    buffer: ctypes.Array,
    received_count: int,
) -> str:
    raw_value = bytes(buffer.raw[: max(0, int(received_count))])
    raw_value = raw_value.split(b"\x00", 1)[0]
    for encoding in ("utf-8", "mbcs"):
        try:
            return raw_value.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw_value.decode("utf-8", errors="replace")


def _parse_first_float(response: str) -> float | None:
    fields = response.replace("\r", " ").replace("\n", " ").split()
    if not fields:
        return None
    try:
        return float(fields[0])
    except ValueError:
        return None


__all__ = ["ACSMotionStageDeviceAPI"]
