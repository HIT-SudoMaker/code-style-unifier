from __future__ import annotations

import math

import pytest
import torch

from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.fixed_measurement.optics.frontend import RestorationFrontend


def _constant_complex_field() -> torch.Tensor:
    """
    鏋勫缓鍏夊鍓嶇娴嬭瘯鏁版嵁
    """
    return torch.full((1, 1, 8, 8), math.sqrt(0.25), dtype=torch.complex64)


def test_phase_zero_baselines_have_expected_keys_and_shapes() -> None:
    """
    鏍￠獙鍏夊鍓嶇濂戠害
    """
    geometry = OpticalBenchConfig(input_array_resolution=(8, 8), phase_mask_resolution=8)
    frontend = RestorationFrontend(geometry)

    baselines = frontend.phase_zero_baselines(_constant_complex_field())

    assert set(baselines) == {
        "image_input_identity",
        "image_reference_arm_only",
        "image_process_arm_phase_zero",
        "image_full_frontend_phase_zero",
        "image_interference_term",
        "e_field_reference",
        "e_field_process_phase_zero",
        "e_field_full_phase_zero",
    }
    assert baselines["image_full_frontend_phase_zero"].shape == (1, 1, 8, 8)


def test_interference_term_can_be_negative() -> None:
    """
    鏍￠獙鍏夊鍓嶇濂戠害
    """
    geometry = OpticalBenchConfig(
        input_array_resolution=(8, 8),
        phase_mask_resolution=8,
        phase_offset_reference=math.pi,
    )
    frontend = RestorationFrontend(geometry)

    baselines = frontend.phase_zero_baselines(_constant_complex_field())

    assert torch.min(baselines["image_interference_term"]).item() < 0


def test_only_phase_mask_is_trainable_by_default() -> None:
    """
    鏍￠獙鍏夊鍓嶇濂戠害
    """
    geometry = OpticalBenchConfig(input_array_resolution=(8, 8), phase_mask_resolution=8)
    frontend = RestorationFrontend(geometry)

    assert frontend.trainable_parameter_names() == ["phase_mask_fourier"]


def test_phase_offset_reference_can_be_trainable() -> None:
    """
    Validate trainable reference phase offset gradients.
    """
    geometry = OpticalBenchConfig(input_array_resolution=(8, 8), phase_mask_resolution=8)
    frontend = RestorationFrontend(
        geometry,
        is_phase_offset_reference_trainable=True,
    )

    assert frontend.trainable_parameter_names() == [
        "phase_mask_fourier",
        "phase_offset_reference",
    ]

    frontend(_constant_complex_field()).mean().backward()

    assert frontend.phase_offset_reference.grad is not None


def test_trainable_phase_offset_changes_reference_interference() -> None:
    """
    Validate reference phase offset changes interference.
    """
    geometry = OpticalBenchConfig(input_array_resolution=(8, 8), phase_mask_resolution=8)
    frontend = RestorationFrontend(
        geometry,
        is_phase_offset_reference_trainable=True,
    )

    with torch.no_grad():
        output_zero = frontend.phase_zero_baselines(_constant_complex_field())[
            "image_full_frontend_phase_zero"
        ]
        frontend.phase_offset_reference.fill_(math.pi)
        output_pi = frontend.phase_zero_baselines(_constant_complex_field())[
            "image_full_frontend_phase_zero"
        ]

    assert not torch.allclose(output_zero, output_pi)


def test_forward_returns_nonnegative_camera_intensity() -> None:
    """
    鏍￠獙鍏夊鍓嶇濂戠害
    """
    geometry = OpticalBenchConfig(input_array_resolution=(8, 8), phase_mask_resolution=8)
    frontend = RestorationFrontend(geometry)

    output = frontend(_constant_complex_field())

    assert output.shape == (1, 1, 8, 8)
    assert torch.all(output >= 0)


def test_phase_mask_receives_gradient() -> None:
    """
    鏍￠獙鍏夊鍓嶇濂戠害
    """
    geometry = OpticalBenchConfig(input_array_resolution=(8, 8), phase_mask_resolution=8)
    frontend = RestorationFrontend(geometry)

    frontend(_constant_complex_field()).mean().backward()

    assert frontend.phase_mask_fourier.grad is not None


def test_one_trained_phase_value_modulates_only_its_matching_fourier_sample() -> None:
    """
    楠岃瘉鍌呴噷鍙剁浉浣嶅€间粎璋冨埗瀵瑰簲鐨勯璋遍噰鏍风偣
    """
    geometry = OpticalBenchConfig(
        input_array_resolution=(8, 8),
        phase_mask_resolution=8,
        split_ratio_reference=0.0,
        split_ratio_process=1.0,
    )
    baseline_frontend = RestorationFrontend(geometry)
    trained_frontend = RestorationFrontend(geometry)
    with torch.no_grad():
        trained_frontend.phase_mask_fourier[4, 4] = 0.25

    input_field = torch.zeros((1, 1, 8, 8), dtype=torch.complex64)
    input_field[..., 0, 0] = 1.0
    _, baseline_process_field = baseline_frontend.forward_optical_fields(input_field)
    _, trained_process_field = trained_frontend.forward_optical_fields(input_field)

    baseline_spectrum = torch.fft.fftshift(
        torch.fft.fft2(baseline_process_field),
        dim=(-2, -1),
    )
    trained_spectrum = torch.fft.fftshift(
        torch.fft.fft2(trained_process_field),
        dim=(-2, -1),
    )
    changed_samples = (
        (trained_spectrum - baseline_spectrum).abs() > 1e-5
    ).squeeze(0).squeeze(0)
    expected_changed_samples = torch.zeros((8, 8), dtype=torch.bool)
    expected_changed_samples[4, 4] = True

    assert torch.equal(changed_samples, expected_changed_samples)


@pytest.mark.parametrize(
    "input_field",
    [
        torch.ones((1, 1, 8, 8), dtype=torch.float32),
        torch.ones((1, 8, 8), dtype=torch.complex64),
        torch.ones((0, 1, 8, 8), dtype=torch.complex64),
        torch.ones((1, 0, 8, 8), dtype=torch.complex64),
        torch.ones((1, 1, 0, 8), dtype=torch.complex64),
        torch.ones((1, 1, 8, 0), dtype=torch.complex64),
        torch.tensor([[[[complex(math.nan, 0.0)]]]], dtype=torch.complex64),
        torch.tensor([[[[complex(0.0, math.inf)]]]], dtype=torch.complex64),
    ],
)
def test_forward_rejects_invalid_input_fields(input_field: torch.Tensor) -> None:
    """
    鏍￠獙鍏夊鍓嶇濂戠害
    """
    geometry = OpticalBenchConfig(input_array_resolution=(8, 8), phase_mask_resolution=8)
    frontend = RestorationFrontend(geometry)

    with pytest.raises(ValueError):
        frontend(input_field)


@pytest.mark.parametrize(
    ("input_dtype", "output_dtype"),
    [
        (torch.complex64, torch.float32),
        (torch.complex128, torch.float64),
    ],
)
def test_forward_preserves_real_precision_for_complex_input_dtype(
    input_dtype: torch.dtype,
    output_dtype: torch.dtype,
) -> None:
    """
    鏍￠獙鍏夊鍓嶇濂戠害
    """
    geometry = OpticalBenchConfig(input_array_resolution=(8, 8), phase_mask_resolution=8)
    frontend = RestorationFrontend(geometry)
    input_field = torch.full((1, 1, 8, 8), math.sqrt(0.25), dtype=input_dtype)

    output = frontend(input_field)

    assert output.dtype == output_dtype
    assert output.shape == (1, 1, 8, 8)
    assert torch.all(output >= 0)


def test_phase_zero_baselines_use_reference_and_process_names() -> None:
    """
    鏍￠獙鍏夊鍓嶇濂戠害
    """
    frontend = RestorationFrontend(OpticalBenchConfig(input_array_resolution=(512, 512)))
    field = torch.ones((1, 1, 512, 512), dtype=torch.complex64)

    baselines = frontend.phase_zero_baselines(field)

    expected_keys = {
        "image_input_identity",
        "image_reference_arm_only",
        "image_process_arm_phase_zero",
        "image_full_frontend_phase_zero",
        "image_interference_term",
        "e_field_reference",
        "e_field_process_phase_zero",
        "e_field_full_phase_zero",
    }
    assert expected_keys.issubset(set(baselines.keys()))
    assert "image_modulation_phase_zero" not in baselines
    assert "image_interference" not in baselines


def test_interference_term_matches_complex_cross_term() -> None:
    """
    鏍￠獙鍏夊鍓嶇濂戠害
    """
    frontend = RestorationFrontend(OpticalBenchConfig(input_array_resolution=(512, 512)))
    field = torch.ones((1, 1, 512, 512), dtype=torch.complex64)

    baselines = frontend.phase_zero_baselines(field)
    cross_term = 2.0 * torch.real(
        baselines["e_field_reference"] * torch.conj(baselines["e_field_process_phase_zero"])
    )

    assert torch.allclose(
        baselines["image_interference_term"],
        cross_term,
        atol=1e-5,
        rtol=1e-5,
    )
    assert torch.allclose(
        baselines["image_full_frontend_phase_zero"],
        (
            baselines["image_reference_arm_only"]
            + baselines["image_process_arm_phase_zero"]
            + baselines["image_interference_term"]
        ),
        atol=1e-5,
        rtol=1e-5,
    )
