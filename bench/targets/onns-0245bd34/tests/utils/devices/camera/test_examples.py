from __future__ import annotations

import unittest
from unittest import mock

from utils.devices.camera._bindings import ASI_IMG_RAW8
from utils.devices.camera.examples import bring_up
from utils.devices.camera.examples import capture_raw8
from utils.devices.camera.examples import stream_raw8


class CameraExampleTests(unittest.TestCase):
    """
    无需硬件验证相机示例
    """

    @mock.patch("utils.devices.camera.examples.bring_up.ZWOASICameraDeviceAPI")
    def test_bring_up_lists_camera_and_controls(
        self,
        api_class: mock.Mock,
    ) -> None:
        """
        联通示例遵循发现流程
        """
        api = api_class.return_value
        api.STATUS_SUCCESS = 0
        api.get_camera_count.return_value = 1
        api.get_camera_info.return_value = mock.Mock(camera_id=7)
        api.open_camera.return_value = 0
        api.initialize_camera.return_value = 0
        api.get_control_count.return_value = 2
        api.get_control_caps.side_effect = [
            mock.Mock(name="Gain"),
            mock.Mock(name="Exposure"),
        ]

        exit_code = bring_up.main(["--camera-index", "0"])

        self.assertEqual(exit_code, 0)
        api.get_sdk_version.assert_called_once_with()
        api.get_camera_count.assert_called_once_with()
        api.get_camera_info.assert_called_once_with(0)
        api.open_camera.assert_called_once_with(7)
        api.initialize_camera.assert_called_once_with(7)
        api.get_control_count.assert_called_once_with(7)
        api.get_control_caps.assert_any_call(7, 0)
        api.get_control_caps.assert_any_call(7, 1)
        api.close_camera.assert_called_once_with(7)

    @mock.patch("utils.devices.camera.examples.capture_raw8.ZWOASICameraDeviceAPI")
    def test_capture_raw8_runs_video_capture_flow(
        self,
        api_class: mock.Mock,
    ) -> None:
        """
        采集示例覆盖完整流程
        """
        api = api_class.return_value
        api.STATUS_SUCCESS = 0
        api.get_camera_info.return_value = mock.Mock(
            camera_id=7,
            max_width=8,
            max_height=4,
        )
        api.open_camera.return_value = 0
        api.initialize_camera.return_value = 0
        api.set_roi_format.return_value = 0
        api.start_video_capture.return_value = 0
        api.capture_raw8_frame.return_value = (
            0,
            mock.Mock(data=mock.Mock(dtype="uint8"), height=4, width=8),
        )

        exit_code = capture_raw8.main(
            [
                "--camera-index",
                "0",
                "--width",
                "8",
                "--height",
                "4",
                "--frames",
                "2",
            ],
        )

        self.assertEqual(exit_code, 0)
        api.open_camera.assert_called_once_with(7)
        api.initialize_camera.assert_called_once_with(7)
        api.set_roi_format.assert_called_once_with(7, 8, 4, 1, ASI_IMG_RAW8)
        api.start_video_capture.assert_called_once_with(7)
        self.assertEqual(api.capture_raw8_frame.call_count, 2)
        api.stop_video_capture.assert_called_once_with(7)
        api.close_camera.assert_called_once_with(7)

    @mock.patch("utils.devices.camera.examples.capture_raw8.ZWOASICameraDeviceAPI")
    def test_capture_raw8_returns_error_on_frame_capture_failure(
        self,
        api_class: mock.Mock,
    ) -> None:
        """
        采集失败返回错误码
        """
        api = api_class.return_value
        api.STATUS_SUCCESS = 0
        api.get_camera_info.return_value = mock.Mock(
            camera_id=7,
            max_width=8,
            max_height=4,
        )
        api.open_camera.return_value = 0
        api.initialize_camera.return_value = 0
        api.set_roi_format.return_value = 0
        api.start_video_capture.return_value = 0
        api.capture_raw8_frame.return_value = (11, None)

        exit_code = capture_raw8.main(
            [
                "--camera-index",
                "0",
                "--width",
                "8",
                "--height",
                "4",
            ],
        )

        self.assertEqual(exit_code, 1)
        api.stop_video_capture.assert_called_once_with(7)
        api.close_camera.assert_called_once_with(7)

    @mock.patch("utils.devices.camera.examples.stream_raw8.ZWOASICameraStream")
    def test_stream_raw8_runs_continuous_stream(
        self,
        stream_class: mock.Mock,
    ) -> None:
        """
        流式示例覆盖运行流程
        """
        stream = stream_class.return_value
        stream.get_frame.return_value = mock.Mock(
            data=mock.Mock(dtype="uint8"),
            height=4,
            width=8,
        )
        stream.get_statistics.return_value = mock.Mock(
            output_frame_count=2,
            dropped_frame_count=0,
            sdk_dropped_frame_count=0,
        )

        exit_code = stream_raw8.main(
            [
                "--width",
                "8",
                "--height",
                "4",
                "--frames",
                "2",
                "--target-output-fps",
                "24",
            ],
        )

        self.assertEqual(exit_code, 0)
        stream_class.assert_called_once()
        stream.start.assert_called_once_with()
        self.assertEqual(stream.get_frame.call_count, 2)
        stream.stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
