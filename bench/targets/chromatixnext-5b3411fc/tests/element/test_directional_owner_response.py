from __future__ import annotations

import math

import pytest
import torch

import chromatix_next._numerics.cube_response as _cube_response
from chromatix_next.errors import OpticalRuntimeError, OpticalValueError
from chromatix_next.optics.element.ideal_cube_beam_splitter import (
    CubeCoatingDiagonal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
)
import chromatix_next.optics.element.ideal_planar_mirror as _mirror_module
from chromatix_next.optics.element.ideal_planar_mirror import IdealPlanarMirror
from tests.qualification.cube_oracles import (
    OracleCoatingDiagonal,
    dense_nbs_operator,
    dense_pbs_operator,
)


def _nbs(
    diagonal: CubeCoatingDiagonal,
    angle: float | torch.nn.Parameter,
) -> IdealNonpolarizingCubeBeamSplitter:
    return IdealNonpolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=diagonal,
        mixing_angle=angle,
    )


def _pbs(
    diagonal: CubeCoatingDiagonal,
) -> IdealPolarizingCubeBeamSplitter:
    return IdealPolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=diagonal,
    )


def _mirror() -> IdealPlanarMirror:
    return IdealPlanarMirror(
        origin=(0.0, 0.0, 0.0),
        outward_normal=(-1.0, 0.0, 0.0),
        transverse_up=(0.0, 0.0, 1.0),
    )


def _oracle_diagonal(
    diagonal: CubeCoatingDiagonal,
) -> OracleCoatingDiagonal:
    return OracleCoatingDiagonal(diagonal.value)


def _random_complex_inputs() -> torch.Tensor:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(1701)
    real = torch.randn((23, 4, 2), generator=generator, dtype=torch.float64)
    imaginary = torch.randn(
        (23, 4, 2),
        generator=generator,
        dtype=torch.float64,
    )
    return torch.complex(real, imaginary)


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
@pytest.mark.parametrize(
    "mixing_angle",
    (
        -math.pi,
        -0.31,
        0.0,
        math.pi / 4.0,
        math.pi,
        2.5 * math.pi,
    ),
)
def test_private_nbs_response_matches_independent_dense_operator(
    diagonal: CubeCoatingDiagonal,
    mixing_angle: float,
) -> None:
    """
    两个对角方向与有限角上的完整多输入复响应匹配 test-owned 8x8 oracle
    """
    inputs = _random_complex_inputs()
    owner = _nbs(diagonal, mixing_angle)
    actual = owner._canonical_response(inputs)
    operator = dense_nbs_operator(
        _oracle_diagonal(diagonal),
        mixing_angle,
    )
    expected = torch.einsum(
        "ij,bj->bi",
        operator,
        inputs.reshape(inputs.shape[0], 8),
    ).reshape_as(inputs)
    torch.testing.assert_close(actual, expected, atol=5.0e-13, rtol=0.0)
    torch.testing.assert_close(
        actual.abs().square().sum(dim=(-2, -1)),
        inputs.abs().square().sum(dim=(-2, -1)),
        atol=5.0e-13,
        rtol=5.0e-13,
    )


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
def test_private_pbs_response_matches_independent_dense_operator(
    diagonal: CubeCoatingDiagonal,
) -> None:
    """
    理想 p 透射、s 反射的完整多输入响应匹配 test-owned 8x8 oracle
    """
    inputs = _random_complex_inputs()
    owner = _pbs(diagonal)
    actual = owner._canonical_response(inputs)
    operator = dense_pbs_operator(_oracle_diagonal(diagonal))
    expected = torch.einsum(
        "ij,bj->bi",
        operator,
        inputs.reshape(inputs.shape[0], 8),
    ).reshape_as(inputs)
    torch.testing.assert_close(actual, expected, atol=5.0e-13, rtol=0.0)
    torch.testing.assert_close(
        actual.abs().square().sum(dim=(-2, -1)),
        inputs.abs().square().sum(dim=(-2, -1)),
        atol=5.0e-13,
        rtol=5.0e-13,
    )


def test_nbs_gradient_reaches_the_single_mixing_angle_parameter() -> None:
    """
    闭合响应只通过一个 retained-identity Parameter 暴露混合角梯度
    """
    parameter = torch.nn.Parameter(
        torch.tensor(0.37, dtype=torch.float64),
    )
    owner = _nbs(CubeCoatingDiagonal.RISING, parameter)
    inputs = _random_complex_inputs()
    response = owner._canonical_response(inputs)
    objective = response[..., 0, 0].real.sum() + (
        0.29 * response[..., 3, 1].imag.sum()
    )
    objective.backward()
    assert owner.mixing_angle is parameter
    assert parameter.grad is not None
    assert bool(torch.isfinite(parameter.grad))
    assert bool(parameter.grad != 0.0)


def test_very_large_finite_angle_retains_lossless_response_algebra() -> None:
    """
    远超 optimizer qualification 区间的有限角仍保持闭合代数但不主张优化进展
    """
    inputs = _random_complex_inputs()
    owner = _nbs(CubeCoatingDiagonal.FALLING, 1.0e100)
    response = owner._canonical_response(inputs)
    assert bool(torch.isfinite(response).all())
    torch.testing.assert_close(
        response.abs().square().sum(dim=(-2, -1)),
        inputs.abs().square().sum(dim=(-2, -1)),
        atol=5.0e-13,
        rtol=5.0e-13,
    )


def test_missing_reflection_i_mutation_is_rejected_by_owner_invariant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    已知 all-real balanced 2 -> 4 adversary 触发精确 Cube runtime identity
    """
    def missing_quadrature_response(
        *,
        incident_terminal_p_s_values: torch.Tensor,
        mixing_angle: torch.Tensor,
        reflection_input_indices: tuple[int, int, int, int],
    ) -> torch.Tensor:
        transmission_indices = torch.tensor((2, 3, 0, 1), dtype=torch.int64)
        reflection_indices = torch.tensor(
            reflection_input_indices,
            dtype=torch.int64,
        )
        transmitted = torch.index_select(
            incident_terminal_p_s_values,
            dim=-2,
            index=transmission_indices,
        )
        reflected = torch.index_select(
            incident_terminal_p_s_values,
            dim=-2,
            index=reflection_indices,
        )
        return torch.cos(mixing_angle) * transmitted + (
            torch.sin(mixing_angle) * reflected
        )

    monkeypatch.setattr(
        _cube_response,
        "apply_closed_nonpolarizing_cube_response",
        missing_quadrature_response,
    )
    inputs = torch.zeros((4, 2), dtype=torch.complex128)
    inputs[1, 0] = 1.0
    inputs[2, 0] = 1.0
    assert float(inputs.abs().square().sum()) == 2.0
    owner = _nbs(CubeCoatingDiagonal.RISING, math.pi / 4.0)
    with pytest.raises(OpticalRuntimeError) as rejected:
        owner._canonical_response(inputs)
    assert (
        rejected.value.identity
        == "cube_beam_splitter_response_invariant_violated"
    )


def test_ideal_mirror_wave_response_is_exact_scalar_minus_one() -> None:
    """
    法向入射 Wave 的每个 transverse Jones 分量逐 bit 等于输入乘 -1
    """
    values = _random_complex_inputs()[0]
    mirror = _mirror()
    response = mirror._wave_response(values)
    assert torch.equal(response, -values)
    assert not hasattr(mirror, "distance")
    assert not hasattr(mirror, "optical_path")
    assert not hasattr(mirror, "path_reference")


def test_mirror_wave_response_mutation_uses_exact_runtime_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    省略 -1 的局部错误由 Mirror owner 而非后续 Detection 报告
    """
    monkeypatch.setattr(
        _mirror_module,
        "_ideal_wave_response",
        lambda values: values,
    )
    with pytest.raises(OpticalRuntimeError) as rejected:
        _mirror()._wave_response(_random_complex_inputs()[0])
    assert (
        rejected.value.identity
        == "ideal_planar_mirror_response_invariant_violated"
    )


def test_ideal_mirror_ray_direction_uses_householder_without_path_write() -> None:
    """
    Ray 几何只反射方向，Mirror owner 不持有或写入 Optical Path
    """
    incident = torch.tensor(
        (
            (1.0, 0.0, 0.0),
            (1.0 / math.sqrt(2.0), 1.0 / math.sqrt(2.0), 0.0),
        ),
        dtype=torch.float64,
    )
    mirror = _mirror()
    actual = mirror._ray_direction_response(
        incident,
        unit_normal=mirror.outward_normal,
    )
    expected = torch.tensor(
        (
            (-1.0, 0.0, 0.0),
            (-1.0 / math.sqrt(2.0), 1.0 / math.sqrt(2.0), 0.0),
        ),
        dtype=torch.float64,
    )
    torch.testing.assert_close(actual, expected, atol=5.0e-15, rtol=0.0)
    torch.testing.assert_close(
        actual.square().sum(dim=-1),
        incident.square().sum(dim=-1),
        atol=5.0e-15,
        rtol=0.0,
    )
    assert set(mirror.state_dict()) == {
        "origin",
        "outward_normal",
        "transverse_up",
    }


def test_mirror_basis_frontier_admits_six_ulp_and_rejects_seven() -> None:
    one = torch.tensor(1.0, dtype=torch.float64)
    toward_two = torch.tensor(2.0, dtype=torch.float64)
    scales = (one,)
    for _ in range(7):
        scales += (torch.nextafter(scales[-1], toward_two),)
    admitted_scale = scales[6]
    rejected_scale = scales[7]
    admitted_zero = admitted_scale * 0.0
    rejected_zero = rejected_scale * 0.0

    admitted = IdealPlanarMirror(
        origin=(0.0, 0.0, 0.0),
        outward_normal=torch.stack(
            (admitted_zero, admitted_zero, -admitted_scale),
        ),
        transverse_up=torch.stack(
            (admitted_zero, admitted_scale, admitted_zero),
        ),
    )
    assert set(admitted.state_dict()) == {
        "origin",
        "outward_normal",
        "transverse_up",
    }

    with pytest.raises(OpticalValueError) as normal_rejected:
        IdealPlanarMirror(
            origin=(0.0, 0.0, 0.0),
            outward_normal=torch.stack(
                (rejected_zero, rejected_zero, -rejected_scale),
            ),
            transverse_up=(0.0, 1.0, 0.0),
        )
    assert (
        normal_rejected.value.identity
        == "ideal_planar_mirror_outward_normal_not_unit"
    )

    with pytest.raises(OpticalValueError) as up_rejected:
        IdealPlanarMirror(
            origin=(0.0, 0.0, 0.0),
            outward_normal=(0.0, 0.0, -1.0),
            transverse_up=torch.stack(
                (rejected_zero, rejected_scale, rejected_zero),
            ),
        )
    assert (
        up_rejected.value.identity
        == "ideal_planar_mirror_transverse_up_not_unit"
    )
