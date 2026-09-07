from __future__ import annotations

import inspect
import unittest

from utils.devices.stage.motion import ACSMotionStage
from utils.devices.stage.motion import DEFAULT_CONTROLLER_IP
from utils.devices.stage.motion import STAGE_MAX_POSITION_MM
from utils.devices.stage.motion import STAGE_MIN_POSITION_MM


class FakeStageDeviceAPI:
    """
    运动适配器测试用模拟接口
    """

    STATUS_SUCCESS = 1
    DEFAULT_PORT = 701

    def __init__(self, failing_operation: str | None = None) -> None:
        """
        初始化模拟运动状态
        """
        self.calls: list[tuple[str, object]] = []
        self.position = 0.0
        self.is_connected = False
        self.failing_operation = failing_operation

    def open_ethernet_tcp(self, address: str, port: int) -> int:
        """
        记录模拟网络连接
        """
        self.calls.append(("open_ethernet_tcp", (address, port)))
        self.is_connected = True
        return 1234

    def close(self) -> int:
        """
        记录模拟连接关闭
        """
        self.calls.append(("close", None))
        self.is_connected = False
        return self.STATUS_SUCCESS

    def enable_axis(self, axis: int) -> int:
        """
        记录模拟轴使能
        """
        self.calls.append(("enable_axis", axis))
        return self.STATUS_SUCCESS

    def disable_axis(self, axis: int) -> int:
        """
        记录模拟轴失能
        """
        self.calls.append(("disable_axis", axis))
        return self.STATUS_SUCCESS

    def set_velocity(self, axis: int, velocity: float) -> int:
        """
        记录模拟速度写入
        """
        self.calls.append(("set_velocity", (axis, velocity)))
        if self.failing_operation == "set_velocity":
            return 0
        return self.STATUS_SUCCESS

    def move_axis_to_point(
        self,
        axis: int,
        position: float,
    ) -> int:
        """
        记录模拟绝对运动
        """
        self.calls.append(("move_axis_to_point", (axis, position)))
        self.position = position
        return self.STATUS_SUCCESS

    def move_axis_relative(
        self,
        axis: int,
        distance: float,
    ) -> int:
        """
        记录模拟相对运动
        """
        self.calls.append(("move_axis_relative", (axis, distance)))
        self.position += distance
        return self.STATUS_SUCCESS

    def wait_motion_end(
        self,
        axis: int,
        timeout_ms: int,
    ) -> int:
        """
        记录模拟等待结束
        """
        self.calls.append(("wait_motion_end", (axis, timeout_ms)))
        if self.failing_operation == "wait_motion_end":
            return 0
        return self.STATUS_SUCCESS

    def get_feedback_position(self, axis: int) -> float:
        """
        返回模拟反馈位置
        """
        self.calls.append(("get_feedback_position", axis))
        return self.position

    def halt_axis(self, axis: int) -> int:
        """
        记录模拟轴停止
        """
        self.calls.append(("halt_axis", axis))
        return self.STATUS_SUCCESS

    def kill_axis(self, axis: int) -> int:
        """
        记录模拟轴急停
        """
        self.calls.append(("kill_axis", axis))
        return self.STATUS_SUCCESS


class ACSMotionStageTests(unittest.TestCase):
    """
    验证高层运动台适配器
    """

    def test_default_motion_bounds_match_stage_hardware_window(self) -> None:
        """
        项目运动窗口为正负七十毫米
        """
        self.assertEqual(STAGE_MIN_POSITION_MM, -70.0)
        self.assertEqual(STAGE_MAX_POSITION_MM, 70.0)

    def test_open_and_close_use_default_controller_address(self) -> None:
        """
        适配器打开并关闭控制器
        """
        fake_api = FakeStageDeviceAPI()
        stage = ACSMotionStage(api=fake_api)

        handle = stage.open()
        close_status = stage.close()

        self.assertEqual(handle, 1234)
        self.assertEqual(close_status, fake_api.STATUS_SUCCESS)
        self.assertEqual(
            fake_api.calls,
            [
                ("open_ethernet_tcp", (DEFAULT_CONTROLLER_IP, fake_api.DEFAULT_PORT)),
                ("close", None),
            ],
        )

    def test_move_to_validates_position_and_waits_for_motion_end(self) -> None:
        """
        绝对运动默认等待完成
        """
        fake_api = FakeStageDeviceAPI()
        stage = ACSMotionStage(api=fake_api, axis=0)

        stage.move_to(position=12.5, velocity=0.5, timeout_ms=5000)

        self.assertEqual(
            fake_api.calls,
            [
                ("set_velocity", (0, 0.5)),
                ("move_axis_to_point", (0, 12.5)),
                ("wait_motion_end", (0, 5000)),
            ],
        )

    def test_move_to_rejects_target_outside_hardware_window(self) -> None:
        """
        绝对运动不能超出硬件窗口
        """
        stage = ACSMotionStage(api=FakeStageDeviceAPI())

        with self.assertRaisesRegex(ValueError, "hardware window"):
            stage.move_to(position=STAGE_MAX_POSITION_MM + 0.001)

    def test_move_to_raises_when_velocity_write_fails(self) -> None:
        """
        速度失败发生在运动命令前
        """
        fake_api = FakeStageDeviceAPI(failing_operation="set_velocity")
        stage = ACSMotionStage(api=fake_api, axis=0)

        with self.assertRaisesRegex(RuntimeError, "set velocity"):
            stage.move_to(position=1.0)

        self.assertEqual(
            fake_api.calls,
            [("set_velocity", (0, stage.default_velocity))],
        )

    def test_move_to_wait_failure_does_not_hide_commanded_motion(self) -> None:
        """
        等待失败发生在运动命令后
        """
        fake_api = FakeStageDeviceAPI(failing_operation="wait_motion_end")
        stage = ACSMotionStage(api=fake_api, axis=0)

        with self.assertRaisesRegex(RuntimeError, "wait motion end"):
            stage.move_to(position=1.0)

        self.assertEqual(
            fake_api.calls,
            [
                ("set_velocity", (0, stage.default_velocity)),
                ("move_axis_to_point", (0, 1.0)),
                ("wait_motion_end", (0, stage.default_timeout_ms)),
            ],
        )

    def test_move_to_docstring_declares_wait_failure_motion_semantics(self) -> None:
        """
        运动契约说明等待失败语义
        """
        docstring = inspect.getdoc(ACSMotionStage.move_to)

        self.assertIn("等待失败发生在运动命令发送之后", docstring)
        self.assertIn("保证运动轴保持静止", docstring)

    def test_move_by_validates_final_position_from_feedback(self) -> None:
        """
        相对运动先验证目标位置
        """
        fake_api = FakeStageDeviceAPI()
        fake_api.position = 69.9
        stage = ACSMotionStage(api=fake_api, axis=0)

        with self.assertRaisesRegex(ValueError, "hardware window"):
            stage.move_by(distance=0.2)

        self.assertEqual(
            fake_api.calls,
            [("get_feedback_position", 0)],
        )

    def test_enable_disable_and_stop_commands_delegate_to_low_level_api(self) -> None:
        """
        基础动作保持直接语义
        """
        fake_api = FakeStageDeviceAPI()
        stage = ACSMotionStage(api=fake_api, axis=2)

        self.assertEqual(stage.enable(), fake_api.STATUS_SUCCESS)
        self.assertEqual(stage.halt(), fake_api.STATUS_SUCCESS)
        self.assertEqual(stage.kill(), fake_api.STATUS_SUCCESS)
        self.assertEqual(stage.disable(), fake_api.STATUS_SUCCESS)
        self.assertEqual(
            fake_api.calls,
            [
                ("enable_axis", 2),
                ("halt_axis", 2),
                ("kill_axis", 2),
                ("disable_axis", 2),
            ],
        )


if __name__ == "__main__":
    unittest.main()
