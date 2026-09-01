from __future__ import annotations

import io
from pathlib import Path
import unittest
from unittest.mock import patch

from utils.devices.slm.examples import bring_up


class FakeUPOLabsSLMDeviceAPI:
    """
    用于验证整合后的 bring-up 演示流程的伪实现
    """

    STATUS_OK = 1
    instances: list["FakeUPOLabsSLMDeviceAPI"] = []

    def __init__(self, dll_path: Path) -> None:
        """
        记录伪 DLL 初始化
        """
        self.dll_path = Path(dll_path)
        self.calls: list[tuple[str, object]] = []
        type(self).instances = []
        type(self).instances.append(self)

    def get_display_count_and_names(self) -> tuple[int, str]:
        """
        返回伪显示器清单
        """
        self.calls.append(("get_display_count_and_names", None))
        return 3, "SLM-1,SLM-2,SLM-3"

    def get_display_resolution(self, display_number: int) -> tuple[int, int]:
        """
        返回伪显示器分辨率
        """
        self.calls.append(("get_display_resolution", display_number))
        return 1920, 1080

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

    def set_display_offset(
        self,
        display_number: int,
        offset_x: int,
        offset_y: int,
    ) -> int:
        """
        记录伪显示偏移写入
        """
        self.calls.append(
            ("set_display_offset", (display_number, offset_x, offset_y))
        )
        return 1

    def get_display_offset(self, display_number: int) -> tuple[int, int]:
        """
        返回伪显示偏移
        """
        self.calls.append(("get_display_offset", display_number))
        return 12, 34

    def set_trigger_configuration(
        self,
        display_number: int,
        trigger_enabled: int,
        trigger_mode_1: int,
        trigger_mode_2: int,
        trigger_time: int,
        trigger_frame_header_enabled: int,
    ) -> int:
        """
        记录伪触发参数写入
        """
        self.calls.append(
            (
                "set_trigger_configuration",
                (
                    display_number,
                    trigger_enabled,
                    trigger_mode_1,
                    trigger_mode_2,
                    trigger_time,
                    trigger_frame_header_enabled,
                ),
            )
        )
        return 1

    def get_trigger_configuration(
        self,
        display_number: int,
    ) -> tuple[int, int, int, int, int]:
        """
        返回伪触发参数
        """
        self.calls.append(("get_trigger_configuration", display_number))
        return 1, 2, 3, 40, 1

    def close_display(self, display_number: int) -> int:
        """
        记录伪显示器关闭调用
        """
        self.calls.append(("close_display", display_number))
        return 1


class BasicDemoTests(unittest.TestCase):
    """
    测试基础演示流程
    """

    def test_run_bring_up_uses_expected_sequence(self) -> None:
        """
        测试 bring-up 演示按预期顺序执行
        """
        output_buffer = io.StringIO()

        with patch.object(bring_up, "UPOLabsSLMDeviceAPI", FakeUPOLabsSLMDeviceAPI):
            with patch("sys.stdout", new=output_buffer):
                bring_up.run_bring_up(
                    dll_path=Path("vendor/hd_slm_function.dll"),
                    display_number=2,
                    gray_level_count=256,
                    gray_scale=122,
                    offset_x=100,
                    offset_y=120,
                    trigger_enabled=1,
                    trigger_mode_1=2,
                    trigger_mode_2=3,
                    trigger_time=40,
                    trigger_frame_header_enabled=1,
                )

        self.assertEqual(len(FakeUPOLabsSLMDeviceAPI.instances), 1)
        fake_api = FakeUPOLabsSLMDeviceAPI.instances[0]
        self.assertEqual(
            fake_api.calls,
            [
                ("get_display_count_and_names", None),
                ("get_display_resolution", 2),
                ("open_display", 2),
                ("display_grayscale_image", (2, 256, 122)),
                ("set_display_offset", (2, 100, 120)),
                ("get_display_offset", 2),
                ("set_trigger_configuration", (2, 1, 2, 3, 40, 1)),
                ("get_trigger_configuration", 2),
                ("close_display", 2),
            ],
        )

        output_text = output_buffer.getvalue()
        self.assertIn("Display count: 3", output_text)
        self.assertIn("Display names: SLM-1,SLM-2,SLM-3", output_text)
        self.assertIn("Display resolution: 1920x1080", output_text)
        self.assertIn("Open status: 1", output_text)
        self.assertIn("Grayscale status: 1", output_text)
        self.assertIn("Offset status: 1", output_text)
        self.assertIn("Current offset: (12, 34)", output_text)
        self.assertIn("Trigger status: 1", output_text)
        self.assertIn("Current trigger: (1, 2, 3, 40, 1)", output_text)
        self.assertIn("Close status: 1", output_text)

    def test_parse_arguments_supports_combined_bring_up_options(self) -> None:
        """
        测试命令行参数解析支持组合的 bring-up 选项
        """
        arguments = bring_up.parse_arguments(
            [
                "--display-number",
                "3",
                "--gray-level-count",
                "1024",
                "--gray-scale",
                "511",
                "--offset-x",
                "80",
                "--offset-y",
                "90",
                "--trigger-mode-1",
                "4",
                "--dll-path",
                "vendor/custom.dll",
            ]
        )

        self.assertEqual(arguments.display_number, 3)
        self.assertEqual(arguments.gray_level_count, 1024)
        self.assertEqual(arguments.gray_scale, 511)
        self.assertEqual(arguments.offset_x, 80)
        self.assertEqual(arguments.offset_y, 90)
        self.assertEqual(arguments.trigger_mode_1, 4)
        self.assertEqual(arguments.dll_path, Path("vendor/custom.dll"))

    def test_run_bring_up_raises_when_display_inventory_lookup_fails(self) -> None:
        """
        测试显示器清单查询失败时抛出异常
        """
        class FailingDisplayInventoryApi(FakeUPOLabsSLMDeviceAPI):
            """
            显示器清单查询失败的伪 API
            """

            def get_display_count_and_names(self) -> tuple[int, str | None]:
                """
                返回失败的显示器清单结果
                """
                self.calls.append(("get_display_count_and_names", None))
                return -1, None

        with patch.object(bring_up, "UPOLabsSLMDeviceAPI", FailingDisplayInventoryApi):
            with self.assertRaisesRegex(
                RuntimeError,
                "读取SLM显示器清单失败",
            ):
                bring_up.run_bring_up()

    def test_run_bring_up_raises_when_no_display_is_available(self) -> None:
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

        with patch.object(bring_up, "UPOLabsSLMDeviceAPI", NoDisplayApi):
            with self.assertRaisesRegex(RuntimeError, "当前没有可用的SLM显示器"):
                bring_up.run_bring_up()

        fake_api = NoDisplayApi.instances[0]
        self.assertEqual(fake_api.calls, [("get_display_count_and_names", None)])

    def test_run_bring_up_raises_when_display_number_is_out_of_range(self) -> None:
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

        with patch.object(bring_up, "UPOLabsSLMDeviceAPI", SingleDisplayApi):
            with self.assertRaisesRegex(
                RuntimeError,
                "显示器编号2超出范围，当前仅检测到1个显示器",
            ):
                bring_up.run_bring_up(display_number=2)

        fake_api = SingleDisplayApi.instances[0]
        self.assertEqual(fake_api.calls, [("get_display_count_and_names", None)])

    def test_run_bring_up_raises_when_open_display_fails(self) -> None:
        """
        测试打开显示器失败时抛出异常
        """
        class FailingOpenDisplayApi(FakeUPOLabsSLMDeviceAPI):
            """
            打开显示器失败的伪 API
            """

            def open_display(self, display_number: int) -> int:
                """
                返回失败的显示器打开状态码
                """
                self.calls.append(("open_display", display_number))
                return -3

        with patch.object(bring_up, "UPOLabsSLMDeviceAPI", FailingOpenDisplayApi):
            with self.assertRaisesRegex(RuntimeError, "打开显示器失败"):
                bring_up.run_bring_up()

        fake_api = FailingOpenDisplayApi.instances[0]
        self.assertNotIn(("close_display", 0), fake_api.calls)


if __name__ == "__main__":
    unittest.main()
