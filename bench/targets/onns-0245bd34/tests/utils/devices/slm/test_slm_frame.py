from __future__ import annotations

import ctypes
import unittest

import numpy as np

import utils.devices.slm.frame as frame_module
from utils.devices.slm.frame import SLMFrame
from utils.devices.slm.frame import slm_frame_to_ctypes_buffer


class SLMFrameTests(unittest.TestCase):
    """
    验证帧数据契约
    """

    def test_frame_public_surface_keeps_hardware_frame_contract(self) -> None:
        """
        帧模块只暴露数据和转换
        """
        self.assertEqual(
            set(frame_module.__all__),
            {
                "SLMFrame",
                "slm_frame_to_ctypes_buffer",
            },
        )

    def test_slm_frame_is_a_plain_data_container(self) -> None:
        """
        帧对象只描述硬件帧
        """
        data = np.array([[1, 2, 3]], dtype=np.uint16)

        frame = SLMFrame(data=data, width=3, height=1)

        self.assertIs(frame.data, data)
        self.assertEqual(frame.width, 3)
        self.assertEqual(frame.height, 1)
        self.assertEqual(frame.gray_level_count, 1024)

    def test_slm_frame_exports_ctypes_ushort_buffer(self) -> None:
        """
        帧可导出显示缓冲区
        """
        frame = SLMFrame(
            data=np.array([[0, 1023]], dtype=np.uint16),
            width=2,
            height=1,
        )

        buffer = slm_frame_to_ctypes_buffer(frame)

        self.assertIsInstance(buffer, ctypes.Array)
        self.assertIs(buffer._type_, ctypes.c_ushort)
        self.assertEqual(list(buffer), [0, 1023])

    def test_slm_frame_rejects_invalid_dtype(self) -> None:
        """
        缓冲区转换只接受十六位数据
        """
        frame = SLMFrame(
            data=np.array([[1.0]], dtype=np.float32),
            width=1,
            height=1,
        )

        with self.assertRaisesRegex(ValueError, "uint16"):
            slm_frame_to_ctypes_buffer(frame)


if __name__ == "__main__":
    unittest.main()
