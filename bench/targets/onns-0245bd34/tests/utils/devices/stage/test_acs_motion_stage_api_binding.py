from __future__ import annotations

import ctypes
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

import utils.devices.stage as stage_package
import utils.devices.stage.api as stage_api_module
from utils.devices.stage._bindings import ACSC_MST_MOVE
from utils.devices.stage._bindings import ACSC_SOCKET_STREAM_PORT
from utils.devices.stage.api import ACSMotionStageDeviceAPI


class FakeFunction:
    """
    记录模拟运动库函数
    """

    def __init__(self, name: str) -> None:
        """
        初始化模拟函数
        """
        self.name = name
        self.argtypes = None
        self.restype = None
        self.calls: list[tuple[object, ...]] = []

    def __call__(self, *arguments: object) -> object:
        """
        记录调用并模拟运动接口
        """
        self.calls.append(arguments)

        if self.name == "acsc_OpenCommEthernetTCP":
            return 1234
        if self.name == "acsc_GetFPosition":
            arguments[2]._obj.value = 12.5
            return ACSMotionStageDeviceAPI.STATUS_SUCCESS
        if self.name == "acsc_GetVelocity":
            arguments[2]._obj.value = 0.25
            return ACSMotionStageDeviceAPI.STATUS_SUCCESS
        if self.name == "acsc_GetAcceleration":
            arguments[2]._obj.value = 2.5
            return ACSMotionStageDeviceAPI.STATUS_SUCCESS
        if self.name == "acsc_GetDeceleration":
            arguments[2]._obj.value = 3.5
            return ACSMotionStageDeviceAPI.STATUS_SUCCESS
        if self.name == "acsc_GetRPosition":
            arguments[2]._obj.value = 12.0
            return ACSMotionStageDeviceAPI.STATUS_SUCCESS
        if self.name == "acsc_GetTargetPosition":
            arguments[2]._obj.value = 13.0
            return ACSMotionStageDeviceAPI.STATUS_SUCCESS
        if self.name == "acsc_GetMotorState":
            arguments[2]._obj.value = ACSC_MST_MOVE
            return ACSMotionStageDeviceAPI.STATUS_SUCCESS
        if self.name == "acsc_GetErrorString":
            buffer = arguments[2]
            message = b"simulated error"
            for index, value in enumerate(message):
                buffer[index] = value
            arguments[4]._obj.value = len(message)
            return ACSMotionStageDeviceAPI.STATUS_SUCCESS
        if self.name == "acsc_GetLibraryVersion":
            return 250
        if self.name == "acsc_Receive":
            buffer = arguments[1]
            message = b"12.5"
            for index, value in enumerate(message):
                buffer[index] = value
            arguments[3]._obj.value = len(message)
            return ACSMotionStageDeviceAPI.STATUS_SUCCESS

        return ACSMotionStageDeviceAPI.STATUS_SUCCESS


class FakeDLL:
    """
    按需创建模拟运动函数
    """

    def __init__(self) -> None:
        """
        初始化模拟动态库
        """
        self.functions: dict[str, FakeFunction] = {}

    def __getattr__(self, name: str) -> FakeFunction:
        """
        返回指定模拟函数
        """
        function = self.functions.get(name)
        if function is None:
            function = FakeFunction(name)
            self.functions[name] = function
        return function


class ACSMotionStageDeviceAPITests(unittest.TestCase):
    """
    验证运动台绑定与接口
    """

    def _create_api(self) -> tuple[ACSMotionStageDeviceAPI, FakeDLL]:
        fake_dll = FakeDLL()
        with patch("ctypes.WinDLL", return_value=fake_dll):
            api = ACSMotionStageDeviceAPI(Path("vendor/acs_motion_stage.dll"))
        return api, fake_dll

    def test_default_vendor_dll_uses_snake_case_name(self) -> None:
        """
        运动台动态库遵循命名约定
        """
        self.assertEqual(stage_package.VENDOR_DLL_PATH.name, "acs_motion_stage.dll")

    def test_vendor_directory_does_not_include_official_service_exe(self) -> None:
        """
        运动台包不附带服务程序
        """
        service_exe_path = stage_package.PACKAGE_ROOT / "vendor" / "ACSCSRV.exe"

        self.assertFalse(service_exe_path.exists())

    def test_vendor_header_uses_snake_case_name(self) -> None:
        """
        运动台头文件遵循命名约定
        """
        include_path = stage_package.PACKAGE_ROOT / "vendor" / "include"

        self.assertTrue((include_path / "acs_motion_stage.h").exists())
        self.assertFalse((include_path / "ACSC.h").exists())

    def test_vendor_directory_does_not_include_text_metadata(self) -> None:
        """
        运动台包不附带额外文本元数据
        """
        metadata_files = list((stage_package.PACKAGE_ROOT / "vendor").glob("*.txt"))

        self.assertEqual(metadata_files, [])

    def test_configures_core_motion_function_signatures(self) -> None:
        """
        配置基础运动所需函数
        """
        _, fake_dll = self._create_api()

        self.assertEqual(
            fake_dll.acsc_OpenCommEthernetTCP.argtypes,
            [ctypes.c_char_p, ctypes.c_int],
        )
        self.assertIs(fake_dll.acsc_OpenCommEthernetTCP.restype, ctypes.c_void_p)
        self.assertEqual(
            fake_dll.acsc_ToPoint.argtypes,
            [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_double, ctypes.c_void_p],
        )
        self.assertEqual(
            fake_dll.acsc_GetFPosition.argtypes,
            [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_double), ctypes.c_void_p],
        )
        self.assertEqual(
            fake_dll.acsc_Send.argtypes,
            [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p],
        )
        self.assertEqual(
            fake_dll.acsc_Receive.argtypes,
            [
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_int),
                ctypes.c_void_p,
            ],
        )

    def test_api_module_keeps_binding_table_private(self) -> None:
        """
        底层细节留在绑定模块
        """
        self.assertFalse(hasattr(stage_api_module, "_FUNCTION_SIGNATURES"))

    def test_public_methods_follow_stage_lifecycle_order(self) -> None:
        """
        公开方法按运动生命周期排序
        """
        method_order = list(ACSMotionStageDeviceAPI.__dict__)
        expected_order = [
            "open_ethernet_tcp",
            "close",
            "get_library_version",
            "get_firmware_version",
            "send_command",
            "receive_response",
            "query_command",
            "query_float",
            "query_int",
            "enable_axis",
            "disable_axis",
            "disable_all",
            "set_acceleration",
            "get_acceleration",
            "set_deceleration",
            "get_deceleration",
            "set_velocity",
            "get_velocity",
            "move_axis_to_point",
            "move_axis_relative",
            "halt_axis",
            "kill_axis",
            "kill_all",
            "get_feedback_position",
            "get_reference_position",
            "get_target_position",
            "get_motor_state",
            "is_axis_moving",
            "wait_motion_end",
            "get_last_error",
            "get_error_string",
        ]

        indexes = [method_order.index(name) for name in expected_order]
        self.assertEqual(indexes, sorted(indexes))

    def test_stage_methods_use_active_connection_handle(self) -> None:
        """
        运动状态调用使用连接句柄
        """
        api, fake_dll = self._create_api()

        handle = api.open_ethernet_tcp("10.0.0.100")
        enable_status = api.enable_axis(axis=0)
        move_status = api.move_axis_to_point(axis=0, position=1.5)
        position = api.get_feedback_position(axis=0)
        moving = api.is_axis_moving(axis=0)

        self.assertEqual(handle, 1234)
        self.assertEqual(enable_status, ACSMotionStageDeviceAPI.STATUS_SUCCESS)
        self.assertEqual(move_status, ACSMotionStageDeviceAPI.STATUS_SUCCESS)
        self.assertEqual(position, 12.5)
        self.assertTrue(moving)
        self.assertEqual(
            fake_dll.acsc_OpenCommEthernetTCP.calls[-1],
            (b"10.0.0.100", ACSC_SOCKET_STREAM_PORT),
        )
        self.assertEqual(fake_dll.acsc_Enable.calls[-1][0], 1234)
        self.assertEqual(fake_dll.acsc_ToPoint.calls[-1][0], 1234)

    def test_api_supports_acspl_command_round_trip(self) -> None:
        """
        通过官方库发送控制命令
        """
        api, fake_dll = self._create_api()
        api.open_ethernet_tcp("10.0.0.100")

        response = api.query_command("?FPOS(0)")

        self.assertEqual(response, "12.5")
        self.assertEqual(
            fake_dll.acsc_Send.calls[-1],
            (1234, b"?FPOS(0)\r", len(b"?FPOS(0)\r"), None),
        )

    def test_motion_parameter_accessors_use_official_api(self) -> None:
        """
        加减速度访问使用官方函数
        """
        api, fake_dll = self._create_api()
        api.open_ethernet_tcp("10.0.0.100")

        self.assertEqual(api.set_acceleration(axis=0, acceleration=2.0), 1)
        self.assertEqual(api.set_deceleration(axis=0, deceleration=3.0), 1)
        self.assertEqual(api.get_acceleration(axis=0), 2.5)
        self.assertEqual(api.get_deceleration(axis=0), 3.5)
        self.assertEqual(api.get_reference_position(axis=0), 12.0)
        self.assertEqual(api.get_target_position(axis=0), 13.0)
        self.assertEqual(fake_dll.acsc_SetAcceleration.calls[-1][0], 1234)
        self.assertEqual(fake_dll.acsc_SetDeceleration.calls[-1][0], 1234)

    def test_get_error_string_decodes_acs_error_buffer(self) -> None:
        """
        错误文本来自厂商缓冲区
        """
        api, _ = self._create_api()
        api.open_ethernet_tcp("10.0.0.100")

        message = api.get_error_string(1)

        self.assertEqual(message, "simulated error")

    def test_multiline_public_signatures_use_vertical_parameters(self) -> None:
        """
        多行公开签名使用纵向参数
        """
        source_lines = inspect.getsource(ACSMotionStageDeviceAPI).splitlines()
        half_expanded_signatures: list[str] = []

        for line_index, line in enumerate(source_lines[:-1]):
            stripped_line = line.strip()
            next_line = source_lines[line_index + 1].strip()
            if stripped_line.startswith("def ") and stripped_line.endswith("("):
                if next_line.startswith("self, "):
                    method_name = stripped_line.removeprefix("def ").removesuffix("(")
                    half_expanded_signatures.append(method_name)

        self.assertEqual(half_expanded_signatures, [])


if __name__ == "__main__":
    unittest.main()
