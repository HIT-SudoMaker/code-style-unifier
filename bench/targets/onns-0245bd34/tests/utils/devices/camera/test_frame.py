from __future__ import annotations

import ctypes
import unittest

import numpy as np

from utils.devices.camera._bindings import ASI_IMG_RAW16
from utils.devices.camera._bindings import ASI_IMG_RAW8
from utils.devices.camera.frame import CameraFrame
from utils.devices.camera.frame import camera_frame_to_ctypes_buffer
from utils.devices.camera.frame import raw8_buffer_to_camera_frame


class CameraFrameTests(unittest.TestCase):
    """
    验证相机帧数据契约
    """

    def test_raw8_buffer_to_camera_frame_uses_uint8_shape(self) -> None:
        """
        八位缓冲区转二维帧
        """
        buffer_type = ctypes.c_ubyte * 6
        buffer = buffer_type(0, 1, 2, 3, 4, 5)

        frame = raw8_buffer_to_camera_frame(buffer, width=3, height=2)

        self.assertIsInstance(frame, CameraFrame)
        self.assertEqual(frame.width, 3)
        self.assertEqual(frame.height, 2)
        self.assertEqual(frame.image_type, ASI_IMG_RAW8)
        np.testing.assert_array_equal(
            frame.data,
            np.array([[0, 1, 2], [3, 4, 5]], dtype=np.uint8),
        )

    def test_raw8_buffer_rejects_invalid_dimensions(self) -> None:
        """
        帧尺寸必须描述二维图像
        """
        buffer_type = ctypes.c_ubyte * 1
        buffer = buffer_type(0)

        with self.assertRaisesRegex(ValueError, "width"):
            raw8_buffer_to_camera_frame(buffer, width=0, height=1)

    def test_camera_frame_to_ctypes_buffer_rejects_non_raw8_frame(self) -> None:
        """
        首个帧工具只支持八位契约
        """
        frame = CameraFrame(
            data=np.array([[1]], dtype=np.uint16),
            width=1,
            height=1,
            image_type=ASI_IMG_RAW16,
        )

        with self.assertRaisesRegex(ValueError, "RAW8"):
            camera_frame_to_ctypes_buffer(frame)

    def test_camera_frame_to_ctypes_buffer_rejects_float_data(self) -> None:
        """
        帧工具拒绝归一化浮点数据
        """
        frame = CameraFrame(
            data=np.array([[0.0, 1.0]], dtype=np.float32),
            width=2,
            height=1,
            image_type=ASI_IMG_RAW8,
        )

        with self.assertRaisesRegex(ValueError, "uint8"):
            camera_frame_to_ctypes_buffer(frame)


if __name__ == "__main__":
    unittest.main()
