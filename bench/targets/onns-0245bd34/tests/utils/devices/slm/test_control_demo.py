from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from utils.devices.slm.examples import bring_up


class FakeUPOLabsSLMDeviceAPI:
    """
    用于验证控制路径错误处理的伪实现
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
        return 2, "SLM-1,SLM-2"

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


class ControlDemoTests(unittest.TestCase):
    """
    测试控制演示路径的错误处理
    """

    def test_run_bring_up_raises_when_grayscale_display_fails(self) -> None:
        """
        测试灰度显示失败时抛出异常
        """
        class FailingGrayscaleDisplayApi(FakeUPOLabsSLMDeviceAPI):
            """
            灰度显示失败的伪 API
            """

            def display_grayscale_image(
                self,
                display_number: int,
                gray_level_count: int,
                gray_scale: int,
            ) -> int:
                """
                返回失败的灰度显示状态码
                """
                self.calls.append(
                    (
                        "display_grayscale_image",
                        (display_number, gray_level_count, gray_scale),
                    )
                )
                return -4

        with patch.object(bring_up, "UPOLabsSLMDeviceAPI", FailingGrayscaleDisplayApi):
            with self.assertRaisesRegex(RuntimeError, "灰度显示失败"):
                bring_up.run_bring_up()

        fake_api = FailingGrayscaleDisplayApi.instances[0]
        self.assertIn(("close_display", 0), fake_api.calls)

    def test_run_bring_up_raises_when_offset_configuration_fails(self) -> None:
        """
        测试设置显示偏移失败时抛出异常
        """
        class FailingOffsetApi(FakeUPOLabsSLMDeviceAPI):
            """
            显示偏移写入失败的伪 API
            """

            def set_display_offset(
                self,
                display_number: int,
                offset_x: int,
                offset_y: int,
            ) -> int:
                """
                返回失败的显示偏移状态码
                """
                self.calls.append(
                    ("set_display_offset", (display_number, offset_x, offset_y))
                )
                return -4

        with patch.object(bring_up, "UPOLabsSLMDeviceAPI", FailingOffsetApi):
            with self.assertRaisesRegex(RuntimeError, "设置显示偏移失败"):
                bring_up.run_bring_up()

        fake_api = FailingOffsetApi.instances[0]
        self.assertIn(("close_display", 0), fake_api.calls)

    def test_run_bring_up_raises_when_offset_readback_fails(self) -> None:
        """
        测试读取显示偏移失败时抛出异常
        """
        class FailingOffsetReadbackApi(FakeUPOLabsSLMDeviceAPI):
            """
            显示偏移读取失败的伪 API
            """

            def get_display_offset(self, display_number: int) -> tuple[None, None]:
                """
                返回失败的显示偏移读取结果
                """
                self.calls.append(("get_display_offset", display_number))
                return None, None

        with patch.object(bring_up, "UPOLabsSLMDeviceAPI", FailingOffsetReadbackApi):
            with self.assertRaisesRegex(RuntimeError, "读取显示偏移失败"):
                bring_up.run_bring_up()

        fake_api = FailingOffsetReadbackApi.instances[0]
        self.assertIn(("close_display", 0), fake_api.calls)

    def test_run_bring_up_raises_when_trigger_configuration_fails(self) -> None:
        """
        测试设置触发参数失败时抛出异常
        """
        class FailingTriggerApi(FakeUPOLabsSLMDeviceAPI):
            """
            触发参数写入失败的伪 API
            """

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
                返回失败的触发参数状态码
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
                return -5

        with patch.object(bring_up, "UPOLabsSLMDeviceAPI", FailingTriggerApi):
            with self.assertRaisesRegex(RuntimeError, "设置触发参数失败"):
                bring_up.run_bring_up()

        fake_api = FailingTriggerApi.instances[0]
        self.assertIn(("close_display", 0), fake_api.calls)

    def test_run_bring_up_raises_when_trigger_readback_fails(self) -> None:
        """
        测试读取触发参数失败时抛出异常
        """
        class FailingTriggerReadbackApi(FakeUPOLabsSLMDeviceAPI):
            """
            触发参数读取失败的伪 API
            """

            def get_trigger_configuration(
                self,
                display_number: int,
            ) -> tuple[int, int, None, int, int]:
                """
                返回失败的触发参数读取结果
                """
                self.calls.append(("get_trigger_configuration", display_number))
                return 1, 2, None, 40, 1

        with patch.object(bring_up, "UPOLabsSLMDeviceAPI", FailingTriggerReadbackApi):
            with self.assertRaisesRegex(RuntimeError, "读取触发参数失败"):
                bring_up.run_bring_up()

        fake_api = FailingTriggerReadbackApi.instances[0]
        self.assertIn(("close_display", 0), fake_api.calls)


if __name__ == "__main__":
    unittest.main()
