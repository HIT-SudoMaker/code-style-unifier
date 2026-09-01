from __future__ import annotations

import ctypes
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

import utils.devices.camera as camera_package
import utils.devices.camera.api as camera_api_module
from utils.devices.camera._bindings import ASI_CAMERA_INFO
from utils.devices.camera._bindings import ASI_CONTROL_CAPS
from utils.devices.camera._bindings import ASI_IMG_RAW8
from utils.devices.camera.api import ZWOASICameraDeviceAPI


class FakeFunction:
    """
    记录模拟函数签名与调用
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
        记录调用并模拟最小接口
        """
        self.calls.append(arguments)

        if self.name == "ASIGetNumOfConnectedCameras":
            return 2
        if self.name == "ASIGetSDKVersion":
            return b"1, 41, 0000"
        if self.name == "ASIGetCameraProperty":
            camera_info = arguments[0]._obj
            camera_info.Name = b"ASI585MM"
            camera_info.CameraID = 7
            camera_info.MaxHeight = 2160
            camera_info.MaxWidth = 3840
            camera_info.IsColorCam = 0
            camera_info.SupportedBins[0] = 1
            camera_info.SupportedBins[1] = 2
            camera_info.SupportedVideoFormat[0] = ASI_IMG_RAW8
            camera_info.SupportedVideoFormat[1] = -1
            camera_info.PixelSize = 2.9
            camera_info.BitDepth = 12
            return ZWOASICameraDeviceAPI.STATUS_SUCCESS
        if self.name == "ASIGetNumOfControls":
            arguments[1]._obj.value = 3
            return ZWOASICameraDeviceAPI.STATUS_SUCCESS
        if self.name == "ASIGetControlCaps":
            caps = arguments[2]._obj
            caps.Name = b"Exposure"
            caps.Description = b"Exposure time in microseconds"
            caps.MaxValue = 1000000
            caps.MinValue = 32
            caps.DefaultValue = 10000
            caps.IsAutoSupported = 0
            caps.IsWritable = 1
            caps.ControlType = ZWOASICameraDeviceAPI.CONTROL_EXPOSURE
            return ZWOASICameraDeviceAPI.STATUS_SUCCESS
        if self.name == "ASIGetControlValue":
            arguments[2]._obj.value = 12000
            arguments[3]._obj.value = 0
            return ZWOASICameraDeviceAPI.STATUS_SUCCESS
        if self.name == "ASIGetROIFormat":
            arguments[1]._obj.value = 4
            arguments[2]._obj.value = 2
            arguments[3]._obj.value = 1
            arguments[4]._obj.value = ASI_IMG_RAW8
            return ZWOASICameraDeviceAPI.STATUS_SUCCESS
        if self.name == "ASIGetDroppedFrames":
            arguments[1]._obj.value = 5
            return ZWOASICameraDeviceAPI.STATUS_SUCCESS
        if self.name == "ASIGetVideoData":
            if getattr(self, "force_status", None) is not None:
                return self.force_status
            buffer = arguments[1]
            for index in range(arguments[2]):
                buffer[index] = index
            return ZWOASICameraDeviceAPI.STATUS_SUCCESS

        return ZWOASICameraDeviceAPI.STATUS_SUCCESS


class FakeDLL:
    """
    按需创建模拟函数
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


class ZWOASICameraDeviceAPITests(unittest.TestCase):
    """
    验证相机绑定与接口
    """

    def _create_api(self) -> tuple[ZWOASICameraDeviceAPI, FakeDLL]:
        fake_dll = FakeDLL()
        with patch("ctypes.WinDLL", return_value=fake_dll):
            api = ZWOASICameraDeviceAPI(Path("vendor/zwo_asi_camera.dll"))
        return api, fake_dll

    def test_default_vendor_dll_uses_snake_case_name(self) -> None:
        """
        相机动态库遵循命名约定
        """
        self.assertEqual(camera_package.VENDOR_DLL_PATH.name, "zwo_asi_camera.dll")

    def test_vendor_header_uses_snake_case_name(self) -> None:
        """
        相机头文件遵循命名约定
        """
        include_path = camera_package.PACKAGE_ROOT / "vendor" / "include"
        old_vendor_header_name = "ASI" + "Camera2.h"
        if not include_path.exists():
            self.skipTest("camera vendor include directory is not bundled")

        self.assertTrue((include_path / "zwo_asi_camera.h").exists())
        self.assertFalse((include_path / old_vendor_header_name).exists())

    def test_vendor_directory_does_not_include_text_metadata(self) -> None:
        """
        相机包不附带额外文本元数据
        """
        metadata_files = list((camera_package.PACKAGE_ROOT / "vendor").glob("*.txt"))

        self.assertEqual(metadata_files, [])

    def test_api_keeps_full_zwo_asi_public_type_names(self) -> None:
        """
        公开类型保留完整厂商命名
        """
        public_names = set(camera_api_module.__all__)

        self.assertIn("ZWOASICameraDeviceAPI", public_names)
        self.assertIn("ZWOASICameraInfo", public_names)
        self.assertIn("ZWOASIControlCaps", public_names)
        self.assertNotIn("CameraInfo", public_names)
        self.assertNotIn("CameraControlCaps", public_names)

    def test_configures_core_video_capture_function_signatures(self) -> None:
        """
        配置采集所需函数
        """
        _, fake_dll = self._create_api()

        self.assertEqual(fake_dll.ASIGetNumOfConnectedCameras.argtypes, [])
        self.assertIs(fake_dll.ASIGetNumOfConnectedCameras.restype, ctypes.c_int)
        self.assertEqual(
            fake_dll.ASIGetCameraProperty.argtypes,
            [ctypes.POINTER(ASI_CAMERA_INFO), ctypes.c_int],
        )
        self.assertEqual(
            fake_dll.ASIGetControlCaps.argtypes,
            [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ASI_CONTROL_CAPS)],
        )
        self.assertEqual(
            fake_dll.ASIGetVideoData.argtypes,
            [ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_long, ctypes.c_int],
        )

    def test_public_methods_follow_device_lifecycle_order(self) -> None:
        """
        公开方法按生命周期排序
        """
        method_order = list(ZWOASICameraDeviceAPI.__dict__)
        expected_order = [
            "get_sdk_version",
            "get_camera_count",
            "get_camera_info",
            "open_camera",
            "initialize_camera",
            "close_camera",
            "get_control_count",
            "get_control_caps",
            "get_control_value",
            "set_control_value",
            "set_roi_format",
            "get_roi_format",
            "start_video_capture",
            "get_video_data",
            "capture_raw8_frame",
            "stop_video_capture",
            "get_dropped_frames",
        ]

        indexes = [method_order.index(name) for name in expected_order]
        self.assertEqual(indexes, sorted(indexes))

    def test_api_module_keeps_binding_table_private(self) -> None:
        """
        底层细节留在绑定模块
        """
        self.assertFalse(hasattr(camera_api_module, "_FUNCTION_SIGNATURES"))

    def test_public_api_methods_have_docstrings(self) -> None:
        """
        公开方法记录硬件契约
        """
        missing_docstrings = [
            name
            for name, value in ZWOASICameraDeviceAPI.__dict__.items()
            if not name.startswith("_")
            and inspect.isfunction(value)
            and not inspect.getdoc(value)
        ]

        self.assertEqual(missing_docstrings, [])

    def test_camera_info_and_control_caps_decode_sdk_structs(self) -> None:
        """
        结构体解码为数据容器
        """
        api, _ = self._create_api()

        info = api.get_camera_info(camera_index=0)
        caps = api.get_control_caps(camera_id=7, control_index=0)

        self.assertIsNotNone(info)
        self.assertEqual(info.name, "ASI585MM")
        self.assertEqual(info.camera_id, 7)
        self.assertEqual(info.max_width, 3840)
        self.assertEqual(info.max_height, 2160)
        self.assertEqual(info.supported_bins, (1, 2))
        self.assertEqual(info.supported_video_formats, (ASI_IMG_RAW8,))
        self.assertEqual(info.pixel_size_um, 2.9)
        self.assertEqual(info.bit_depth, 12)
        self.assertIsNotNone(caps)
        self.assertEqual(caps.name, "Exposure")
        self.assertEqual(caps.control_type, ZWOASICameraDeviceAPI.CONTROL_EXPOSURE)
        self.assertEqual(caps.min_value, 32)
        self.assertEqual(caps.max_value, 1000000)

    def test_capture_raw8_frame_returns_status_and_numpy_uint8_data(self) -> None:
        """
        采集返回状态和帧
        """
        api, _ = self._create_api()

        status, frame = api.capture_raw8_frame(
            camera_id=7,
            width=4,
            height=2,
            timeout_ms=100,
        )

        self.assertEqual(status, ZWOASICameraDeviceAPI.STATUS_SUCCESS)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.width, 4)
        self.assertEqual(frame.height, 2)
        self.assertEqual(frame.image_type, ASI_IMG_RAW8)
        self.assertEqual(frame.data.dtype, np.uint8)
        np.testing.assert_array_equal(
            frame.data,
            np.array([[0, 1, 2, 3], [4, 5, 6, 7]], dtype=np.uint8),
        )

    def test_capture_raw8_frame_returns_status_and_none_on_sdk_failure(self) -> None:
        """
        采集失败返回错误状态
        """
        api, fake_dll = self._create_api()
        fake_dll.ASIGetVideoData.force_status = camera_api_module.ASI_ERROR_TIMEOUT

        status, frame = api.capture_raw8_frame(
            camera_id=7,
            width=4,
            height=2,
            timeout_ms=1,
        )

        self.assertEqual(status, camera_api_module.ASI_ERROR_TIMEOUT)
        self.assertIsNone(frame)

    def test_multiline_public_signatures_use_vertical_parameters(self) -> None:
        """
        多行公开签名使用纵向参数
        """
        source_lines = inspect.getsource(ZWOASICameraDeviceAPI).splitlines()
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
