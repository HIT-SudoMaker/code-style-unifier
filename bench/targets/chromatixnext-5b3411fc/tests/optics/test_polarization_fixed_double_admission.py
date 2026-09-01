from __future__ import annotations

from typing import cast

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics import Polarization, PolarizationRepresentation


@pytest.mark.parametrize(
    "value",
    [
        torch.tensor(1.0, dtype=torch.float32),
        torch.tensor(1.0, dtype=torch.float64),
        torch.tensor(1.0 + 0.0j, dtype=torch.complex64),
        torch.tensor(1.0 + 0.0j, dtype=torch.complex128),
        torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float64)),
    ],
)
def test_transverse_polarization_rejects_tensor_component(
    value: torch.Tensor,
) -> None:
    """
    无张量 Polarization 不把任意 Tensor 分量折叠成 Python complex
    """

    with pytest.raises(OpticalValueError) as rejected:
        Polarization.transverse(components=(cast(complex, value), 0.0))

    assert rejected.value.identity == "polarization_state_invalid"


def test_full_polarization_rejects_tensor_component() -> None:
    """
    full classmethod 与 transverse 共用同一无张量准入契约
    """

    with pytest.raises(OpticalValueError) as rejected:
        Polarization.full(
            components=(
                1.0,
                cast(
                    complex,
                    torch.tensor(0.0, dtype=torch.float64),
                ),
                0.0,
            ),
        )

    assert rejected.value.identity == "polarization_state_invalid"


def test_direct_polarization_constructor_rejects_boolean_component() -> None:
    """
    bool 不以 Python int 子类身份冒充 Jones 分量
    """

    with pytest.raises(OpticalValueError) as rejected:
        Polarization(
            PolarizationRepresentation.TRANSVERSE,
            (True, 0.0),
        )

    assert rejected.value.identity == "polarization_state_invalid"


def test_polarization_accepts_python_numeric_components_and_normalizes() -> None:
    """
    Python int、float、complex 保持既有单位范数归一化行为
    """

    polarization = Polarization.transverse(components=(3, 4.0 + 0.0j))

    assert polarization.components == (0.6 + 0.0j, 0.8 + 0.0j)
    assert all(
        isinstance(component, complex)
        for component in polarization.components
    )


@pytest.mark.parametrize(
    ("components", "identity"),
    [
        ((1.0,), "polarization_state_component_count_invalid"),
        ((complex(float("nan"), 0.0), 1.0), "polarization_state_nonfinite"),
        ((0.0, 0.0), "polarization_state_zero"),
        ((1.0e308, 1.0e308), "polarization_state_norm_nonfinite"),
    ],
)
def test_polarization_keeps_downstream_physical_error_identities(
    components: tuple[complex, ...],
    identity: str,
) -> None:
    """
    分量类型收紧不吞并计数、有限性、零态与范数错误身份
    """

    with pytest.raises(OpticalValueError) as rejected:
        Polarization(
            PolarizationRepresentation.TRANSVERSE,
            components,
        )

    assert rejected.value.identity == identity


def test_named_polarization_constructors_keep_canonical_states() -> None:
    """
    常用 classmethod 仍给出规范化的 canonical Jones 状态
    """

    assert Polarization.scalar().components == (1.0 + 0.0j,)
    assert Polarization.linear_x().components == (1.0 + 0.0j, 0.0 + 0.0j)
    assert Polarization.linear_y().components == (0.0 + 0.0j, 1.0 + 0.0j)
