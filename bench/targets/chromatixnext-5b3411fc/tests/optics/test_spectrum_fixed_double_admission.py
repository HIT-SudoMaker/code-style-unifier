from __future__ import annotations

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics import Spectrum


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_spectrum_rejects_tensor_wavelength_container(
    dtype: torch.dtype,
) -> None:
    """
    无张量 Spectrum 不把任意精度的作者 Tensor 容器折叠成 Python 浮点数
    """

    with pytest.raises(OpticalValueError) as rejected:
        Spectrum(
            wavelengths=torch.tensor((1.0, 2.0), dtype=dtype),
            weights=(0.5, 0.5),
        )

    assert rejected.value.identity == "spectrum_wavelengths_invalid"


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_spectrum_rejects_tensor_weight_container(dtype: torch.dtype) -> None:
    """
    权重 Tensor 容器走权重自己的稳定身份拒绝
    """

    with pytest.raises(OpticalValueError) as rejected:
        Spectrum(
            wavelengths=(1.0, 2.0),
            weights=torch.tensor((0.5, 0.5), dtype=dtype),
        )

    assert rejected.value.identity == "spectrum_weights_invalid"


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
@pytest.mark.parametrize("field_name", ["wavelengths", "weights"])
def test_spectrum_rejects_tensor_component(
    dtype: torch.dtype,
    field_name: str,
) -> None:
    """
    Python 序列中的零维 Tensor 也不得被 float 折叠
    """

    arguments: dict[str, object] = {
        "wavelengths": (1.0, 2.0),
        "weights": (0.5, 0.5),
    }
    arguments[field_name] = (
        torch.tensor(1.0, dtype=dtype),
        1.0,
    )
    with pytest.raises(OpticalValueError) as rejected:
        Spectrum(**arguments)

    assert rejected.value.identity == f"spectrum_{field_name}_invalid"


@pytest.mark.parametrize("invalid_component", [True, 1.0 + 0.0j])
@pytest.mark.parametrize("field_name", ["wavelengths", "weights"])
def test_spectrum_rejects_non_real_python_component(
    invalid_component: object,
    field_name: str,
) -> None:
    """
    bool 与 complex 不冒充 Python 实数光谱分量
    """

    arguments: dict[str, object] = {
        "wavelengths": (1.0, 2.0),
        "weights": (0.5, 0.5),
    }
    arguments[field_name] = (invalid_component, 1.0)
    with pytest.raises(OpticalValueError) as rejected:
        Spectrum(**arguments)

    assert rejected.value.identity == f"spectrum_{field_name}_invalid"


def test_spectrum_accepts_explicit_python_real_sequences() -> None:
    """
    list、tuple 及 Python int/float 仍物化为不可变浮点元组
    """

    spectrum = Spectrum(
        wavelengths=[1, 2.5],
        weights=(1, 0.25),
    )

    assert spectrum.wavelengths == (1.0, 2.5)
    assert spectrum.weights == (1.0, 0.25)
    assert all(isinstance(value, float) for value in spectrum.wavelengths)
    assert all(isinstance(value, float) for value in spectrum.weights)


@pytest.mark.parametrize(
    ("wavelengths", "weights", "identity"),
    [
        ((1.0,), (0.5, 0.5), "spectrum_length_mismatch"),
        ((float("nan"),), (1.0,), "spectrum_wavelength_nonfinite"),
        ((0.0,), (1.0,), "spectrum_wavelength_nonpositive"),
        ((1.0,), (float("inf"),), "spectrum_weight_nonfinite"),
        ((1.0,), (-1.0,), "spectrum_weight_negative"),
    ],
)
def test_spectrum_keeps_downstream_physical_error_identities(
    wavelengths: tuple[float, ...],
    weights: tuple[float, ...],
    identity: str,
) -> None:
    """
    容器准入收紧不吞并长度、有限性与符号错误身份
    """

    with pytest.raises(OpticalValueError) as rejected:
        Spectrum(wavelengths=wavelengths, weights=weights)

    assert rejected.value.identity == identity
