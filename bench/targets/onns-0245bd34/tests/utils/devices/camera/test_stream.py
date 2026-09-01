from __future__ import annotations

from collections.abc import Callable
import inspect
import time
import unittest
from unittest import mock

import numpy as np

import utils.devices.camera.stream as stream_module
from utils.devices.camera._bindings import ASI_IMG_RAW8
from utils.devices.camera.frame import CameraFrame
from utils.devices.camera.stream import ASI585MM_FULL_HEIGHT
from utils.devices.camera.stream import ASI585MM_FULL_WIDTH
from utils.devices.camera.stream import DEFAULT_TARGET_OUTPUT_FPS
from utils.devices.camera.stream import ZWOASICameraStream


class ZWOASICameraStreamTests(unittest.TestCase):
    """
    验证相机八位采集流
    """

    def test_default_configuration_matches_asi585mm_raw8_stream(self) -> None:
        """
        采集流默认全幅八位输出
        """
        with mock.patch.object(stream_module, "ZWOASICameraDeviceAPI"):
            stream = ZWOASICameraStream()

        self.assertEqual(stream.camera_index, 0)
        self.assertEqual(stream.width, ASI585MM_FULL_WIDTH)
        self.assertEqual(stream.height, ASI585MM_FULL_HEIGHT)
        self.assertEqual(stream.target_output_fps, DEFAULT_TARGET_OUTPUT_FPS)

    def test_rejects_invalid_stream_configuration(self) -> None:
        """
        配置先于动态库调用校验
        """
        with self.assertRaisesRegex(ValueError, "width"):
            ZWOASICameraStream(width=0)
        with self.assertRaisesRegex(ValueError, "height"):
            ZWOASICameraStream(height=ASI585MM_FULL_HEIGHT + 1)
        with self.assertRaisesRegex(ValueError, "target_output_fps"):
            ZWOASICameraStream(target_output_fps=0.0)
        with self.assertRaisesRegex(ValueError, "target_output_fps"):
            ZWOASICameraStream(target_output_fps=float("nan"))
        with self.assertRaisesRegex(ValueError, "target_output_fps"):
            ZWOASICameraStream(target_output_fps=float("inf"))

    @mock.patch.object(stream_module, "ZWOASICameraDeviceAPI")
    def test_start_configures_raw8_video_capture_and_stop_releases_camera(
        self,
        api_class: mock.Mock,
    ) -> None:
        """
        启动和停止管理采集资源
        """
        api = _create_mock_api()
        api_class.return_value = api

        stream = ZWOASICameraStream(width=8, height=4, target_output_fps=None)
        stream.start()
        self.assertTrue(
            _wait_until(lambda: stream.get_statistics().output_frame_count > 0),
        )
        stream.stop()

        api.get_camera_info.assert_called_once_with(0)
        api.open_camera.assert_called_once_with(7)
        api.initialize_camera.assert_called_once_with(7)
        api.set_roi_format.assert_called_once_with(7, 8, 4, 1, ASI_IMG_RAW8)
        api.start_video_capture.assert_called_once_with(7)
        api.stop_video_capture.assert_called_once_with(7)
        api.close_camera.assert_called_once_with(7)

    @mock.patch.object(stream_module, "ZWOASICameraDeviceAPI")
    def test_get_latest_frame_returns_independent_copy(
        self,
        api_class: mock.Mock,
    ) -> None:
        """
        返回帧不会污染缓存帧
        """
        api = _create_mock_api()
        api_class.return_value = api
        stream = ZWOASICameraStream(width=4, height=2, target_output_fps=None)
        stream.start()
        self.assertTrue(_wait_until(lambda: stream.get_latest_frame() is not None))

        latest_frame = stream.get_latest_frame()
        self.assertIsNotNone(latest_frame)
        latest_frame.data[:, :] = 255
        latest_frame_again = stream.get_latest_frame()
        stream.stop()

        self.assertIsNotNone(latest_frame_again)
        self.assertFalse(np.all(latest_frame_again.data == 255))

    @mock.patch.object(stream_module, "ZWOASICameraDeviceAPI")
    def test_full_queue_drops_oldest_frame_when_enabled(
        self,
        api_class: mock.Mock,
    ) -> None:
        """
        满队列丢弃旧帧
        """
        api = _create_mock_api()
        api_class.return_value = api
        stream = ZWOASICameraStream(
            width=4,
            height=2,
            frame_queue_size=1,
            target_output_fps=None,
        )
        stream.start()
        self.assertTrue(
            _wait_until(lambda: stream.get_statistics().dropped_frame_count > 0),
        )
        stream.stop()

        statistics = stream.get_statistics()
        self.assertGreater(statistics.output_frame_count, 1)
        self.assertGreater(statistics.dropped_frame_count, 0)

    def test_target_output_fps_throttles_published_frames(self) -> None:
        """
        限帧器按目标间隔发布
        """
        with mock.patch.object(stream_module, "ZWOASICameraDeviceAPI"):
            stream = ZWOASICameraStream(width=4, height=2, target_output_fps=30.0)
        stream._last_output_time = 100.0

        with mock.patch.object(stream_module.time, "monotonic", return_value=100.01):
            self.assertFalse(stream._should_publish_frame())
        with mock.patch.object(stream_module.time, "monotonic", return_value=100.04):
            self.assertTrue(stream._should_publish_frame())

    def test_multiline_public_signatures_use_vertical_parameters(self) -> None:
        """
        多行公开签名保持纵向参数
        """
        source_lines = inspect.getsource(ZWOASICameraStream).splitlines()
        half_expanded_signatures: list[str] = []

        for line_index, line in enumerate(source_lines[:-1]):
            stripped_line = line.strip()
            next_line = source_lines[line_index + 1].strip()
            if stripped_line.startswith("def ") and stripped_line.endswith("("):
                if next_line.startswith("self, "):
                    method_name = stripped_line.removeprefix("def ").removesuffix("(")
                    half_expanded_signatures.append(method_name)

        self.assertEqual(half_expanded_signatures, [])


def _create_mock_api() -> mock.Mock:
    api = mock.Mock()
    api.STATUS_SUCCESS = 0
    api.get_camera_info.return_value = mock.Mock(
        camera_id=7,
        max_width=ASI585MM_FULL_WIDTH,
        max_height=ASI585MM_FULL_HEIGHT,
    )
    api.open_camera.return_value = 0
    api.initialize_camera.return_value = 0
    api.set_roi_format.return_value = 0
    api.start_video_capture.return_value = 0
    api.stop_video_capture.return_value = 0
    api.close_camera.return_value = 0
    api.get_dropped_frames.return_value = 3

    frame_index = 0

    def capture_raw8_frame(
        camera_id: int,
        width: int,
        height: int,
        timeout_ms: int,
    ) -> tuple[int, CameraFrame]:
        """
        返回确定性八位测试帧
        """
        nonlocal frame_index
        frame_index += 1
        time.sleep(0.001)
        data = np.full((height, width), frame_index % 255, dtype=np.uint8)
        return (
            api.STATUS_SUCCESS,
            CameraFrame(
                data=data,
                width=width,
                height=height,
                image_type=ASI_IMG_RAW8,
            ),
        )

    api.capture_raw8_frame.side_effect = capture_raw8_frame
    return api


def _wait_until(
    predicate: Callable[[], bool],
    *,
    timeout_seconds: float = 1.0,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


if __name__ == "__main__":
    unittest.main()
