from __future__ import annotations

import inspect
import math
import unittest

import numpy as np

import utils.devices.slm.converter as converter_module
from utils.devices.slm.converter import (
    intensity_to_slm_frame,
    phase_to_slm_frame,
)
from utils.devices.slm.frame import SLMFrame


class SLMConverterTests(unittest.TestCase):
    """
    测试 SLM 数据转换器的 10bit 硬件帧契约
    """

    def test_intensity_to_slm_frame_quantizes_unit_range_to_ten_bit(self) -> None:
        """
        归一化强度图应量化为 0 到 1023 的 uint16 硬件帧
        """
        image = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)

        frame = intensity_to_slm_frame(image)

        self.assertIsInstance(frame, SLMFrame)
        self.assertEqual(frame.gray_level_count, 1024)
        self.assertEqual(frame.width, 3)
        self.assertEqual(frame.height, 1)
        self.assertEqual(frame.data.dtype, np.uint16)
        np.testing.assert_array_equal(
            frame.data,
            np.array([[0, 512, 1023]], dtype=np.uint16),
        )

    def test_intensity_to_slm_frame_rejects_out_of_range_values_by_default(
        self,
    ) -> None:
        """
        默认策略下强度图越界应报错，避免静默改变实验数据
        """
        image = np.array([[-0.01, 0.5, 1.01]], dtype=np.float32)

        with self.assertRaisesRegex(ValueError, "range"):
            intensity_to_slm_frame(image)

    def test_converter_public_surface_keeps_only_frame_and_two_converters(
        self,
    ) -> None:
        """
        转换器接口保持聚焦
        """
        self.assertEqual(
            set(converter_module.__all__),
            {
                "intensity_to_slm_frame",
                "phase_to_slm_frame",
            },
        )

    def test_intensity_converter_has_no_extra_policy(self) -> None:
        """
        强度转换保持严格策略
        """
        signature = inspect.signature(intensity_to_slm_frame)

        self.assertEqual(list(signature.parameters), ["image"])

    def test_phase_to_slm_frame_wraps_radians_and_quantizes_to_ten_bit(
        self,
    ) -> None:
        """
        相位图应先按 2pi 回绕，再线性量化为 10bit 硬件帧
        """
        phase = np.array(
            [[0.0, math.pi, math.tau, 3.0 * math.pi]],
            dtype=np.float32,
        )

        frame = phase_to_slm_frame(phase)

        np.testing.assert_array_equal(
            frame.data,
            np.array([[0, 512, 0, 512]], dtype=np.uint16),
        )

    def test_converter_accepts_single_channel_array(self) -> None:
        """
        单通道 [1, H, W] 输入应转成二维 SLM 帧
        """
        image = np.array([[[0.0, 1.0], [0.5, 0.25]]], dtype=np.float32)

        frame = intensity_to_slm_frame(image)

        self.assertEqual(frame.width, 2)
        self.assertEqual(frame.height, 2)
        np.testing.assert_array_equal(
            frame.data,
            np.array([[0, 1023], [512, 256]], dtype=np.uint16),
        )

    def test_converter_rejects_non_finite_values(self) -> None:
        """
        NaN 或 Inf 不应进入硬件帧
        """
        image = np.array([[0.0, np.nan]], dtype=np.float32)

        with self.assertRaisesRegex(ValueError, "finite"):
            intensity_to_slm_frame(image)

if __name__ == "__main__":
    unittest.main()
