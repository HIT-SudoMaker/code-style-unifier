from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.jones_calculus import (
    _eigenstate_jones_vector,
    _eigenstate_projector_from_jones_vector,
    _retarder_matrix,
)


def _real_scalar(value: float, *, device: torch.device | str = "cpu") -> torch.Tensor:
    return torch.tensor(value, dtype=torch.float64, device=device)


def test_eigenstates_match_linear_and_circular_reference_states() -> None:
    """
    本征态在水平线偏振与圆偏振极点退化为独立可知的标准 Jones 向量
    """

    horizontal = _eigenstate_jones_vector(
        azimuth_radians=_real_scalar(0.0),
        ellipticity_radians=_real_scalar(0.0),
    )
    circular = _eigenstate_jones_vector(
        azimuth_radians=_real_scalar(0.0),
        ellipticity_radians=_real_scalar(math.pi / 4.0),
    )

    assert torch.equal(
        horizontal,
        torch.tensor((1.0, 0.0), dtype=torch.complex128),
    )
    expected_circular = torch.tensor(
        (1.0, 1j),
        dtype=torch.complex128,
    ) / math.sqrt(2.0)
    assert torch.allclose(circular, expected_circular, atol=1.0e-15, rtol=0.0)


def test_projector_is_hermitian_idempotent_and_rank_one() -> None:
    """
    归一化 Jones 本征态的外积是迹为一的厄米幂等投影
    """

    eigenstate = _eigenstate_jones_vector(
        azimuth_radians=_real_scalar(0.37),
        ellipticity_radians=_real_scalar(-0.19),
    )
    projector = _eigenstate_projector_from_jones_vector(
        eigenstate=eigenstate,
    )

    assert torch.allclose(projector, projector.mH, atol=1.0e-15, rtol=0.0)
    assert torch.allclose(
        projector @ projector,
        projector,
        atol=1.0e-15,
        rtol=0.0,
    )
    assert torch.allclose(
        torch.trace(projector),
        torch.ones((), dtype=torch.complex128),
        atol=1.0e-15,
        rtol=0.0,
    )


def test_retarder_is_su2_with_exact_cycle_boundaries() -> None:
    """
    零均值延迟矩阵保持酉性与单位行列式，并在整周期边界给出精确相位
    """

    eigenstate = _eigenstate_jones_vector(
        azimuth_radians=_real_scalar(0.31),
        ellipticity_radians=_real_scalar(0.11),
    )
    projector = _eigenstate_projector_from_jones_vector(
        eigenstate=eigenstate,
    )
    identity = torch.eye(2, dtype=torch.complex128)

    zero = _retarder_matrix(
        retardance_cycles=_real_scalar(0.0),
        retarded_eigenstate_projector=projector,
    )
    one_cycle = _retarder_matrix(
        retardance_cycles=_real_scalar(1.0),
        retarded_eigenstate_projector=projector,
    )
    two_cycles = _retarder_matrix(
        retardance_cycles=_real_scalar(2.0),
        retarded_eigenstate_projector=projector,
    )
    general = _retarder_matrix(
        retardance_cycles=_real_scalar(0.37),
        retarded_eigenstate_projector=projector,
    )

    assert torch.equal(zero, identity)
    assert torch.allclose(one_cycle, -identity, atol=1.0e-15, rtol=0.0)
    assert torch.allclose(two_cycles, identity, atol=1.0e-15, rtol=0.0)
    assert torch.allclose(general.mH @ general, identity, atol=1.0e-15, rtol=0.0)
    assert torch.allclose(
        torch.linalg.det(general),
        torch.ones((), dtype=torch.complex128),
        atol=1.0e-15,
        rtol=0.0,
    )


@pytest.mark.cuda
def test_jones_owner_runs_on_real_cuda() -> None:
    """
    Jones 本征态、投影与 SU(2) 权威在真实 CUDA 上保持复双精度不变量
    """

    assert torch.cuda.is_available()
    device = torch.device("cuda", torch.cuda.current_device())
    eigenstate = _eigenstate_jones_vector(
        azimuth_radians=_real_scalar(0.31, device=device),
        ellipticity_radians=_real_scalar(0.08, device=device),
    )
    projector = _eigenstate_projector_from_jones_vector(eigenstate=eigenstate)
    matrix = _retarder_matrix(
        retardance_cycles=_real_scalar(0.23, device=device),
        retarded_eigenstate_projector=projector,
    )
    identity = torch.eye(2, dtype=torch.complex128, device=device)
    assert matrix.device.type == "cuda"
    assert torch.allclose(matrix.mH @ matrix, identity, atol=1.0e-15, rtol=0.0)
    assert torch.allclose(
        torch.linalg.det(matrix),
        torch.ones((), dtype=torch.complex128, device=device),
        atol=1.0e-15,
        rtol=0.0,
    )
