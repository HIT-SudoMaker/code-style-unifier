from __future__ import annotations

import math

import torch
from torch import nn

from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.fixed_measurement.optics.frontend import RestorationFrontend
from experiments.restoration.fixed_measurement.learning.hybrid import FrozenFrontendBackend
from experiments.restoration.fixed_measurement.optics.reference_arm import (
    ReferenceArmParams,
    inject_live_reference_arm,
    reference_arm_from_frontend,
)


class _StubBackend(nn.Module):
    """
    璁板綍搴曞骇娉ㄥ叆鐨勫弬鑰冭噦
    """

    def __init__(self) -> None:
        """
        鍒濆鍖栧弬鑰冭噦璁板綍
        """
        super().__init__()
        self.received_reference_arm: ReferenceArmParams | None = None

    def set_reference_arm(self, reference_arm: ReferenceArmParams) -> None:
        """
        淇濆瓨鍔犺浇鍚庣殑瀹炴椂鍙傝€冭噦
        """
        self.received_reference_arm = reference_arm

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        鍘熸牱杩斿洖杈撳叆鍥惧儚
        """
        return image


class _NoSetterBackend(nn.Module):
    """
    妯℃嫙涓嶆帴鏀跺弬鑰冭噦鐨?NAFNet 鍚庣
    """

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        鍘熸牱杩斿洖杈撳叆鍥惧儚
        """
        return image


def _unit_model_config() -> OpticalBenchConfig:
    """
    鏋勫缓鍙傝€冭噦鍗曞厓娴嬭瘯寰瀷鍑犱綍
    """
    return OpticalBenchConfig(
        input_array_resolution=(8, 8),
        phase_mask_resolution=8,
        slm2_resolution=(16, 16),
        slm2_active_resolution=(16, 16),
    )


def test_reference_arm_reads_live_phase_offset_not_static_default() -> None:
    """
    楠岃瘉鍙傝€冭噦璇诲彇瀹炴椂鐩镐綅鍋忕疆鑰岄潪闈欐€侀粯璁ゅ€?    """
    geometry = _unit_model_config()
    assert geometry.phase_offset_reference == 0.0
    frontend = RestorationFrontend(geometry)
    with torch.no_grad():
        frontend.phase_offset_reference.data.fill_(0.75)

    params = reference_arm_from_frontend(frontend)

    assert isinstance(params, ReferenceArmParams)
    assert params.phase_offset() == 0.75
    assert params.phase_offset() != geometry.phase_offset_reference


def test_reference_arm_amplitude_from_split_ratio_and_gain() -> None:
    """
    楠岃瘉鍙傝€冭噦鎸箙鐢卞垎鏉熸瘮涓庡鐩婂叡鍚屽喅瀹?    """
    geometry = _unit_model_config()
    frontend = RestorationFrontend(geometry)

    params = reference_arm_from_frontend(frontend)

    assert params.amplitude() == math.sqrt(
        geometry.split_ratio_reference
    ) * geometry.amplitude_gain_reference


def test_inject_live_reference_arm_hands_live_phase_to_backend_setter() -> None:
    """
    楠岃瘉娉ㄥ叆鍚戝悗绔紶閫掑姞杞藉悗鐨勫疄鏃跺弬鑰冪浉浣?    """
    geometry = _unit_model_config()
    assert geometry.phase_offset_reference == 0.0
    frontend = RestorationFrontend(geometry)
    stub_backend = _StubBackend()
    model = FrozenFrontendBackend(frontend, stub_backend)

    with torch.no_grad():
        frontend.phase_offset_reference.data.fill_(0.75)

    inject_live_reference_arm(model)

    assert stub_backend.received_reference_arm is not None
    assert stub_backend.received_reference_arm.phase_offset() == 0.75
    assert (
        stub_backend.received_reference_arm.phase_offset()
        != geometry.phase_offset_reference
    )


def test_inject_live_reference_arm_is_noop_for_backend_without_setter() -> None:
    """
    楠岃瘉鏃犲弬鑰冭噦鎺ュ彛鐨勫悗绔繚鎸佷笉鍙?    """
    geometry = _unit_model_config()
    frontend = RestorationFrontend(geometry)
    model = FrozenFrontendBackend(frontend, _NoSetterBackend())

    inject_live_reference_arm(model)


def test_inject_live_reference_arm_is_noop_for_non_hybrid_model() -> None:
    """
    楠岃瘉闈炴贩鍚堟ā鍨嬬殑鍙傝€冭噦娉ㄥ叆淇濇寔涓嶅彉
    """
    inject_live_reference_arm(_NoSetterBackend())
