from __future__ import annotations

import ctypes
import importlib
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

import utils.devices.slm.api as slm_api_module
from utils.devices.slm.api import UPOLabsSLMDeviceAPI


class FakeFunction:
    """
    记录 DLL 函数签名和调用参数
    """

    def __init__(self, name: str) -> None:
        """
        初始化伪函数对象
        """
        self.name = name
        self.argtypes = None
        self.restype = None
        self.calls: list[tuple[object, ...]] = []

    def __call__(self, *arguments: object) -> int:
        """
        记录调用参数并返回成功状态
        """
        self.calls.append(arguments)
        return UPOLabsSLMDeviceAPI.STATUS_OK


class FakeDLL:
    """
    按需创建伪 DLL 函数对象
    """

    def __init__(self) -> None:
        """
        初始化函数表
        """
        self.functions: dict[str, FakeFunction] = {}

    def __getattr__(self, name: str) -> FakeFunction:
        """
        返回指定名称的伪函数
        """
        function = self.functions.get(name)
        if function is None:
            function = FakeFunction(name)
            self.functions[name] = function
        return function


class UPOLabsSLMDeviceAPIBindingTests(unittest.TestCase):
    """
    校验 SLM API 的 DLL 绑定和公开方法结构
    """

    def _create_api(self) -> tuple[UPOLabsSLMDeviceAPI, FakeDLL]:
        fake_dll = FakeDLL()
        with patch("ctypes.WinDLL", return_value=fake_dll):
            api = UPOLabsSLMDeviceAPI(Path("vendor/hd_slm_function.dll"))
        return api, fake_dll

    def test_configures_core_and_0612_function_signatures(self) -> None:
        """
        配置核心函数和 0612 新增函数签名
        """
        _, fake_dll = self._create_api()

        self.assertEqual(
            fake_dll.SLM_Disp_Data.argtypes,
            [
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_void_p,
            ],
        )
        self.assertEqual(
            fake_dll.SLM_Set_Gamma.argtypes,
            [ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p],
        )
        self.assertEqual(
            fake_dll.SLM_Disp_CoordInfo.argtypes,
            [ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)],
        )
        self.assertEqual(
            fake_dll.SLM_Set_SplicingScreenEnabled.argtypes,
            [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_int],
        )
        self.assertEqual(fake_dll.SLM_Disp_Splice.argtypes, [])
        self.assertIs(fake_dll.SLM_Disp_Splice.restype, ctypes.c_int)

    def test_keeps_ctypes_binding_table_out_of_public_api_module(self) -> None:
        """
        ctypes 签名表保留在绑定模块
        """
        self.assertFalse(hasattr(slm_api_module, "_FUNCTION_SIGNATURES"))

        slm_bindings = importlib.import_module("utils.devices.slm._bindings")
        self.assertTrue(hasattr(slm_bindings, "configure_slm_dll_functions"))

    def test_api_surface_keeps_legacy_chinese_contracts(self) -> None:
        """
        公开 API 保留 legacy 中文契约风格
        """
        self.assertIn(
            "HDSLM 空间光调制器 DLL 绑定",
            inspect.getdoc(UPOLabsSLMDeviceAPI) or "",
        )

        missing_docstrings = [
            name
            for name, value in UPOLabsSLMDeviceAPI.__dict__.items()
            if not name.startswith("_")
            and inspect.isfunction(value)
            and not inspect.getdoc(value)
        ]
        self.assertEqual(missing_docstrings, [])

    def test_public_methods_follow_device_lifecycle_order(self) -> None:
        """
        公开方法按设备生命周期排序
        """
        method_order = list(UPOLabsSLMDeviceAPI.__dict__)

        expected_order = [
            "get_display_count_and_names",
            "get_display_resolution",
            "get_display_coordinate",
            "open_display",
            "close_display",
            "set_user_display_size_enabled",
            "set_user_display_size",
            "get_user_display_size_enabled",
            "get_user_display_size",
            "display_grayscale_image",
            "display_hbitmap_image",
            "display_integer_data",
            "display_normalized_float_data",
            "display_image_from_path",
            "display_image_from_ascii_path",
            "display_csv_from_path",
            "display_csv_from_ascii_path",
            "set_display_offset",
            "get_display_offset",
            "initialize_trigger",
            "set_trigger_configuration",
            "get_trigger_configuration",
            "set_gamma_file_from_path",
            "set_gamma_file_from_ascii_path",
            "set_gamma_enabled",
            "set_soft_gamma_enabled",
            "set_soft_gamma_value",
            "get_soft_gamma_enabled",
            "get_soft_gamma_value",
            "set_splicing_screen_enabled",
            "get_splicing_screen_enabled",
            "display_spliced_image",
        ]

        indexes = [method_order.index(name) for name in expected_order]
        self.assertEqual(indexes, sorted(indexes))

    def test_multiline_public_signatures_use_vertical_parameters(self) -> None:
        """
        跨行公开方法签名使用参数竖排格式
        """
        source_lines = inspect.getsource(UPOLabsSLMDeviceAPI).splitlines()
        half_expanded_signatures: list[str] = []

        for line_index, line in enumerate(source_lines[:-1]):
            stripped_line = line.strip()
            next_line = source_lines[line_index + 1].strip()
            if stripped_line.startswith("def ") and stripped_line.endswith("("):
                if next_line.startswith("self, "):
                    method_name = stripped_line.removeprefix("def ").removesuffix("(")
                    half_expanded_signatures.append(method_name)

        self.assertEqual(half_expanded_signatures, [])

    def test_set_splicing_screen_enabled_marshals_display_numbers(self) -> None:
        """
        拼接屏显示器编号转换为 ctypes 数组
        """
        api, fake_dll = self._create_api()

        status = api.set_splicing_screen_enabled([1, 0], enabled=True)

        self.assertEqual(status, UPOLabsSLMDeviceAPI.STATUS_OK)
        arguments = fake_dll.SLM_Set_SplicingScreenEnabled.calls[-1]
        self.assertIsInstance(arguments[0], ctypes.Array)
        self.assertEqual(list(arguments[0]), [1, 0])
        self.assertEqual(arguments[1], 1)
        self.assertEqual(arguments[2], 2)


if __name__ == "__main__":
    unittest.main()
