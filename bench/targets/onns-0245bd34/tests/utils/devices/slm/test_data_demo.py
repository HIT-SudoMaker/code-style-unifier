from __future__ import annotations

import ctypes
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from utils.devices.slm.examples import display


class FakeUPOLabsSLMDeviceAPI:
    """
    用于验证整合后显示演示主流程的伪实现
    """

    STATUS_OK = 1
    instances: list["FakeUPOLabsSLMDeviceAPI"] = []

    def __init__(self, dll_path: Path) -> None:
        """
        记录伪 DLL 初始化
        """
        self.dll_path = Path(dll_path)
        self.calls: list[tuple[str, object]] = []
        self.pattern_arguments: list[ctypes.Array] = []
        type(self).instances = []
        type(self).instances.append(self)

    def get_display_count_and_names(self) -> tuple[int, str]:
        """
        返回伪显示器清单
        """
        self.calls.append(("get_display_count_and_names", None))
        return 2, "SLM-1,SLM-2"

    def get_display_resolution(self, display_number: int) -> tuple[int, int]:
        """
        返回伪显示器分辨率
        """
        self.calls.append(("get_display_resolution", display_number))
        return 4, 3

    def open_display(self, display_number: int) -> int:
        """
        记录伪显示器打开调用
        """
        self.calls.append(("open_display", display_number))
        return 1

    def display_grayscale_image(
        self,
        display_number: int,
        gray_level_count: int,
        gray_scale: int,
    ) -> int:
        """
        记录伪灰度显示调用
        """
        self.calls.append(
            (
                "display_grayscale_image",
                (display_number, gray_level_count, gray_scale),
            )
        )
        return 1

    def display_image_from_path(self, display_number: int, image_path: Path) -> int:
        """
        记录伪图像文件显示调用
        """
        self.calls.append(
            ("display_image_from_path", (display_number, Path(image_path)))
        )
        return 1

    def display_integer_data(
        self,
        display_number: int,
        width: int,
        height: int,
        gray_level_count: int,
        data: ctypes.Array,
    ) -> int:
        """
        记录伪整数数据显示调用
        """
        self.pattern_arguments.append(data)
        self.calls.append(
            (
                "display_integer_data",
                (display_number, width, height, gray_level_count, len(data)),
            )
        )
        return 1

    def close_display(self, display_number: int) -> int:
        """
        记录伪显示器关闭调用
        """
        self.calls.append(("close_display", display_number))
        return 1


class DisplayDemoTests(unittest.TestCase):
    """
    测试显示演示主流程
    """

    def test_parse_arguments_supports_display_options(self) -> None:
        """
        测试命令行参数解析支持显示选项
        """
        arguments = display.parse_arguments(
            [
                "--display-number",
                "1",
                "--image-path",
                "assets/custom.bmp",
                "--grayscale-gray-level-count",
                "256",
                "--grayscale-value",
                "200",
                "--array-gray-level-count",
                "1024",
                "--pattern-seed",
                "7",
                "--dll-path",
                "vendor/custom.dll",
            ]
        )

        self.assertEqual(arguments.display_number, 1)
        self.assertEqual(arguments.image_path, Path("assets/custom.bmp"))
        self.assertEqual(arguments.grayscale_gray_level_count, 256)
        self.assertEqual(arguments.grayscale_value, 200)
        self.assertEqual(arguments.array_gray_level_count, 1024)
        self.assertEqual(arguments.pattern_seed, 7)
        self.assertEqual(arguments.dll_path, Path("vendor/custom.dll"))

    def test_build_array_pattern_is_deterministic_for_ten_bit_mode(self) -> None:
        """
        测试十位模式下数组模式生成的确定性
        """
        first_pattern = display.build_array_pattern(
            width=4,
            height=2,
            gray_level_count=1024,
            pattern_seed=11,
        )
        second_pattern = display.build_array_pattern(
            width=4,
            height=2,
            gray_level_count=1024,
            pattern_seed=11,
        )

        self.assertIsInstance(first_pattern, ctypes.Array)
        self.assertIs(first_pattern._type_, ctypes.c_ushort)
        self.assertEqual(list(first_pattern), list(second_pattern))
        self.assertEqual(len(first_pattern), 8)
        self.assertTrue(all(0 <= value < 1024 for value in first_pattern))

    def test_run_display_executes_three_display_stages_in_order(self) -> None:
        """
        测试显示演示按顺序执行四个显示阶段
        """
        output_buffer = io.StringIO()
        image_path = Path("assets/demo.bmp")

        with patch.object(display, "UPOLabsSLMDeviceAPI", FakeUPOLabsSLMDeviceAPI):
            with patch("builtins.input", side_effect=["", "", ""]) as input_mock:
                with patch("sys.stdout", new=output_buffer):
                    display.run_display(
                        dll_path=Path("vendor/hd_slm_function.dll"),
                        display_number=1,
                        image_path=image_path,
                        grayscale_gray_level_count=256,
                        grayscale_value=122,
                        array_gray_level_count=1024,
                        pattern_seed=7,
                    )

        self.assertEqual(len(FakeUPOLabsSLMDeviceAPI.instances), 1)
        fake_api = FakeUPOLabsSLMDeviceAPI.instances[0]
        self.assertEqual(
            fake_api.calls,
            [
                ("get_display_count_and_names", None),
                ("get_display_resolution", 1),
                ("open_display", 1),
                ("display_grayscale_image", (1, 256, 122)),
                ("display_image_from_path", (1, image_path)),
                ("display_integer_data", (1, 4, 3, 1024, 12)),
                ("close_display", 1),
            ],
        )

        self.assertEqual(input_mock.call_count, 3)
        self.assertEqual(len(fake_api.pattern_arguments), 1)
        self.assertIs(fake_api.pattern_arguments[0]._type_, ctypes.c_ushort)
        self.assertTrue(
            all(0 <= value < 1024 for value in fake_api.pattern_arguments[0])
        )

        output_text = output_buffer.getvalue()
        self.assertIn("Display count: 2", output_text)
        self.assertIn("Display names: SLM-1,SLM-2", output_text)
        self.assertIn("Display resolution: 4x3", output_text)
        self.assertIn("Demo asset resolution: 1920x1200", output_text)
        self.assertIn("Stage 1/3: Grayscale display", output_text)
        self.assertIn("Stage 2/3: Image file display", output_text)
        self.assertIn("Stage 3/3: Array pattern display", output_text)
        self.assertIn("Grayscale status: 1", output_text)
        self.assertIn("Image file status: 1", output_text)
        self.assertIn("Array pattern status: 1", output_text)
        self.assertIn("Close status: 1", output_text)
        self.assertNotIn("HBITMAP", output_text)

    def test_display_no_longer_exposes_hbitmap_helper_layer(self) -> None:
        """
        显示示例不暴露位图辅助层
        """
        self.assertFalse(hasattr(display, "_load_hbitmap_helpers"))
        self.assertFalse(
            hasattr(display, "convert_grayscale_image_to_hbitmap")
        )
        self.assertFalse(hasattr(display, "release_hbitmap"))

    def test_run_display_raises_when_resolution_lookup_fails(self) -> None:
        """
        测试分辨率查询失败时抛出异常
        """
        class FailingResolutionApi(FakeUPOLabsSLMDeviceAPI):
            """
            分辨率查询失败的伪 API
            """

            def get_display_resolution(
                self,
                display_number: int,
            ) -> tuple[int | None, int | None]:
                """
                返回失败的分辨率查询结果
                """
                self.calls.append(("get_display_resolution", display_number))
                return None, None

        with patch.object(display, "UPOLabsSLMDeviceAPI", FailingResolutionApi):
            with self.assertRaisesRegex(RuntimeError, "读取显示器0分辨率失败。"):
                display.run_display()

        fake_api = FailingResolutionApi.instances[0]
        self.assertNotIn(("close_display", 0), fake_api.calls)

    def test_run_display_raises_when_no_display_is_available(self) -> None:
        """
        测试没有可用显示器时抛出异常
        """
        class NoDisplayApi(FakeUPOLabsSLMDeviceAPI):
            """
            没有显示器的伪 API
            """

            def get_display_count_and_names(self) -> tuple[int, str]:
                """
                返回空显示器清单
                """
                self.calls.append(("get_display_count_and_names", None))
                return 0, ""

        with patch.object(display, "UPOLabsSLMDeviceAPI", NoDisplayApi):
            with self.assertRaisesRegex(RuntimeError, "当前没有可用的SLM显示器。"):
                display.run_display()

        fake_api = NoDisplayApi.instances[0]
        self.assertEqual(fake_api.calls, [("get_display_count_and_names", None)])

    def test_run_display_raises_when_display_number_is_out_of_range(self) -> None:
        """
        测试显示器编号超出范围时抛出异常
        """
        class SingleDisplayApi(FakeUPOLabsSLMDeviceAPI):
            """
            单显示器伪 API
            """

            def get_display_count_and_names(self) -> tuple[int, str]:
                """
                返回一个伪显示器
                """
                self.calls.append(("get_display_count_and_names", None))
                return 1, "SLM-1"

        with patch.object(display, "UPOLabsSLMDeviceAPI", SingleDisplayApi):
            with self.assertRaisesRegex(
                RuntimeError,
                "显示器编号3超出范围，当前仅检测到1个显示器。",
            ):
                display.run_display(display_number=3)

        fake_api = SingleDisplayApi.instances[0]
        self.assertEqual(fake_api.calls, [("get_display_count_and_names", None)])

    def test_run_display_skips_close_when_open_fails(self) -> None:
        """
        测试打开显示器失败时跳过关闭操作
        """
        class FailingOpenApi(FakeUPOLabsSLMDeviceAPI):
            """
            打开显示器失败的伪 API
            """

            def open_display(self, display_number: int) -> int:
                """
                返回失败的显示器打开状态码
                """
                self.calls.append(("open_display", display_number))
                return -3

        with patch.object(display, "UPOLabsSLMDeviceAPI", FailingOpenApi):
            with self.assertRaisesRegex(RuntimeError, "打开显示器失败，状态码为-3。"):
                display.run_display()

        fake_api = FailingOpenApi.instances[0]
        self.assertNotIn(("close_display", 0), fake_api.calls)


if __name__ == "__main__":
    unittest.main()
