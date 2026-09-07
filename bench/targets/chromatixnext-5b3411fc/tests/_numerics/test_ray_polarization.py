from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.ray_polarization import (
    derive_plane_local_jones_frame,
    embed_collimated_polarization_in_global_frame,
    reflect_polarization_direction,
    retard_ray_polarization,
    rotate_polarization_minimal,
)

_ROUNDED_NONZERO_CANCELLATION_DIRECTION = (
    0.8125095448101878,
    0.13732140544081897,
    0.5665430885644089,
)
_ROUNDED_NONZERO_CANCELLATION_AXIS = (
    0.8125095448101878,
    0.13732140544081894,
    0.566543088564409,
)


def _vector(
    values: tuple[complex | float, complex | float, complex | float],
    *,
    device: torch.device | str = "cpu",
    is_complex: bool = False,
) -> torch.Tensor:
    dtype = torch.complex128 if is_complex else torch.float64
    return torch.tensor(values, dtype=dtype, device=device)


def _scalar(value: float, *, device: torch.device | str = "cpu") -> torch.Tensor:
    return torch.tensor(value, dtype=torch.float64, device=device)


def test_embedding_uses_authored_launch_basis() -> None:
    """
    光源嵌入把 Jones 横向分量投到作者给出的两个正交发射轴
    """

    jones = torch.tensor((0.6 + 0.0j, 0.0 + 0.8j), dtype=torch.complex128)
    embedded = embed_collimated_polarization_in_global_frame(
        jones_components=jones,
        launch_tangent_x=_vector((0.0, 1.0, 0.0)),
        launch_tangent_y=_vector((0.0, 0.0, 1.0)),
        reference=torch.empty((), dtype=torch.float64),
    )

    expected = torch.tensor((0.0, 0.6, 0.8j), dtype=torch.complex128)
    assert torch.equal(embedded, expected)
    assert torch.allclose(
        embedded.abs().square().sum(),
        torch.ones((), dtype=torch.float64),
        atol=1.0e-15,
        rtol=0.0,
    )


def test_reflection_and_minimal_transport_match_geometric_images() -> None:
    """
    Householder 反射与四分之一转角最小旋转给出可独立写出的几何像
    """

    polarization = _vector((1.0, 0.0, 0.0), is_complex=True).unsqueeze(0)
    reflected = reflect_polarization_direction(
        ray_polarization=polarization,
        unit_normal=_vector((1.0, 0.0, 0.0)).unsqueeze(0),
        is_interacted=torch.tensor((True,)),
    )
    rotated = rotate_polarization_minimal(
        incident_direction=_vector((0.0, 0.0, 1.0)).unsqueeze(0),
        transmitted_direction=_vector((1.0, 0.0, 0.0)).unsqueeze(0),
        ray_polarization=polarization,
        is_refracted=torch.tensor((True,)),
    )

    assert torch.equal(
        reflected,
        _vector((-1.0, 0.0, 0.0), is_complex=True).unsqueeze(0),
    )
    assert torch.allclose(
        rotated,
        _vector((0.0, 0.0, -1.0), is_complex=True).unsqueeze(0),
        atol=1.0e-15,
        rtol=0.0,
    )


@pytest.mark.parametrize(
    (
        "direction_values",
        "plane_axis_values",
        "is_interacted",
        "is_degenerate",
        "is_resolvable",
    ),
    (
        pytest.param(
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 0.0),
            True,
            False,
            True,
            id="ordinary",
        ),
        pytest.param(
            (0.0, 1.0e-14, 1.0),
            (0.0, 0.0, 1.0),
            True,
            False,
            True,
            id="near-conditioned",
        ),
        pytest.param(
            (0.0, math.ldexp(1.0, -600), 1.0),
            (0.0, 0.0, 1.0),
            True,
            False,
            True,
            id="below-square-range",
        ),
        pytest.param(
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
            True,
            True,
            True,
            id="exact-degenerate",
        ),
        pytest.param(
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
            False,
            False,
            True,
            id="non-interacting",
        ),
        pytest.param(
            (0.7871086084148107, -0.588612612634032, 0.18437795640325058),
            (0.7871086084148108, -0.5886126126340321, 0.1843779564032506),
            True,
            False,
            False,
            id="continuous-projection-unresolvable",
        ),
        pytest.param(
            _ROUNDED_NONZERO_CANCELLATION_DIRECTION,
            _ROUNDED_NONZERO_CANCELLATION_AXIS,
            True,
            False,
            False,
            id="rounded-nonzero-cancellation-unresolvable",
        ),
        pytest.param(
            _ROUNDED_NONZERO_CANCELLATION_DIRECTION,
            _ROUNDED_NONZERO_CANCELLATION_AXIS,
            False,
            False,
            True,
            id="non-interacting-rounded-nonzero-cancellation",
        ),
    ),
)
def test_plane_local_frame_classifies_bounded_extreme_cases(
    direction_values: tuple[float, float, float],
    plane_axis_values: tuple[float, float, float],
    is_interacted: bool,
    is_degenerate: bool,
    is_resolvable: bool,
) -> None:
    """
    平面局部帧区分精确退化、连续可表示性与非交互占位
    """

    direction = _vector(direction_values).unsqueeze(0)
    tangent_x = _vector(plane_axis_values).unsqueeze(0)
    frame = derive_plane_local_jones_frame(
        ray_direction=direction,
        plane_tangent_x=tangent_x,
        is_interacted=torch.tensor((is_interacted,)),
    )

    assert torch.equal(
        frame.is_interaction_degenerate,
        torch.tensor((is_degenerate,)),
    )
    assert torch.equal(
        frame.is_projection_resolvable,
        torch.tensor((is_resolvable,)),
    )
    assert bool(torch.isfinite(frame.axis_x).all())
    assert bool(torch.isfinite(frame.axis_y).all())
    if is_interacted and not is_degenerate and is_resolvable:
        expected_unit_norm = torch.ones(1, dtype=torch.float64)
        assert torch.allclose(
            torch.linalg.norm(frame.axis_x, dim=-1),
            expected_unit_norm,
            atol=1.0e-15,
            rtol=0.0,
        )
        assert torch.allclose(
            torch.linalg.norm(frame.axis_y, dim=-1),
            expected_unit_norm,
            atol=1.0e-15,
            rtol=0.0,
        )
        calculation_direction = direction / torch.linalg.norm(
            direction,
            dim=-1,
            keepdim=True,
        )
        expected_zero = torch.zeros(1, dtype=torch.float64)
        assert torch.allclose(
            (frame.axis_x * calculation_direction).sum(dim=-1),
            expected_zero,
            atol=1.0e-15,
            rtol=0.0,
        )
        assert torch.allclose(
            (frame.axis_y * calculation_direction).sum(dim=-1),
            expected_zero,
            atol=1.0e-15,
            rtol=0.0,
        )
        assert torch.allclose(
            torch.linalg.cross(frame.axis_x, frame.axis_y),
            calculation_direction,
            atol=1.0e-15,
            rtol=0.0,
        )


def test_component_bound_rejects_rounded_nonzero_cancellation_residue() -> None:
    """
    连续投影虽舍入为非零，仍因未超过运算误差界而不可消费
    """

    direction = _vector(_ROUNDED_NONZERO_CANCELLATION_DIRECTION).unsqueeze(0)
    tangent_x = _vector(_ROUNDED_NONZERO_CANCELLATION_AXIS).unsqueeze(0)
    calculation_direction = direction / torch.linalg.norm(
        direction,
        dim=-1,
        keepdim=True,
    )
    rounded_projection = tangent_x - (
        (tangent_x * calculation_direction).sum(dim=-1, keepdim=True)
        * calculation_direction
    )
    frame = derive_plane_local_jones_frame(
        ray_direction=direction,
        plane_tangent_x=tangent_x,
        is_interacted=torch.tensor((True,)),
    )

    assert bool((rounded_projection != 0.0).any())
    assert torch.equal(
        frame.is_interaction_degenerate,
        torch.tensor((False,)),
    )
    assert torch.equal(
        frame.is_projection_resolvable,
        torch.tensor((False,)),
    )


def test_ray_retarder_preserves_norm_and_has_nontrivial_gradient() -> None:
    """
    Plane-local SU(2) 延迟保持偏振范数，并对延迟量产生有限非零梯度
    """

    retardance = _scalar(0.23).requires_grad_()
    azimuth = _scalar(0.17).requires_grad_()
    ellipticity = _scalar(0.05).requires_grad_()
    ray_polarization = _vector((1.0, 1.0j, 0.0), is_complex=True)
    ray_polarization = (ray_polarization / math.sqrt(2.0)).unsqueeze(0)

    def _retarded_observables(
        authored_retardance: torch.Tensor,
        authored_azimuth: torch.Tensor,
        authored_ellipticity: torch.Tensor,
    ) -> torch.Tensor:
        direction = _vector((0.0, 0.0, 1.0)).unsqueeze(0)
        interacted = torch.tensor((True,))
        frame = derive_plane_local_jones_frame(
            ray_direction=direction,
            plane_tangent_x=_vector((1.0, 0.0, 0.0)).unsqueeze(0),
            is_interacted=interacted,
        )
        output = retard_ray_polarization(
            ray_polarization=ray_polarization,
            plane_local_frame=frame,
            is_interacted=interacted,
            retardance_cycles=authored_retardance,
            retarded_eigenstate_azimuth_radians=authored_azimuth,
            retarded_eigenstate_ellipticity_radians=authored_ellipticity,
        )
        return torch.view_as_real(output).reshape(-1)

    inputs = (retardance, azimuth, ellipticity)
    assert torch.autograd.gradcheck(_retarded_observables, inputs)
    observables = _retarded_observables(*inputs)
    weights = torch.linspace(0.4, 1.3, observables.numel(), dtype=torch.float64)
    (observables * weights).sum().backward()
    output_norm = observables.reshape(-1, 2).square().sum()

    assert torch.allclose(
        output_norm,
        torch.ones((), dtype=torch.float64),
        atol=1.0e-15,
        rtol=0.0,
    )
    for parameter in inputs:
        assert parameter.grad is not None
        assert bool(torch.isfinite(parameter.grad))
        assert float(parameter.grad.abs()) > 0.0


@pytest.mark.cuda
def test_ray_polarization_owner_runs_on_real_cuda() -> None:
    """
    嵌入、局部帧与延迟在真实 CUDA 上保持复双精度闭合
    """

    assert torch.cuda.is_available()
    device = torch.device("cuda", torch.cuda.current_device())
    direction = _vector((0.0, 0.0, 1.0), device=device).unsqueeze(0)
    axis = _vector((1.0, 0.0, 0.0), device=device).unsqueeze(0)
    axis_x = _vector((0.0, 1.0, 0.0), device=device)
    embedded = embed_collimated_polarization_in_global_frame(
        jones_components=torch.tensor(
            (0.6 + 0.0j, 0.0 + 0.8j),
            dtype=torch.complex128,
            device=device,
        ),
        launch_tangent_x=axis.squeeze(0),
        launch_tangent_y=axis_x,
        reference=torch.empty((), dtype=torch.float64, device=device),
    )
    polarization = _vector(
        (1.0, 1.0j, 0.0),
        device=device,
        is_complex=True,
    )
    polarization = (polarization / math.sqrt(2.0)).unsqueeze(0)
    reflected_polarization = reflect_polarization_direction(
        ray_polarization=polarization,
        unit_normal=_vector((1.0, 0.0, 0.0), device=device).unsqueeze(0),
        is_interacted=torch.tensor((True,), device=device),
    )
    rotated_polarization = rotate_polarization_minimal(
        incident_direction=direction,
        transmitted_direction=_vector((1.0, 0.0, 0.0), device=device).unsqueeze(0),
        ray_polarization=polarization,
        is_refracted=torch.tensor((True,), device=device),
    )
    frame = derive_plane_local_jones_frame(
        ray_direction=direction,
        plane_tangent_x=axis,
        is_interacted=torch.tensor((True,), device=device),
    )
    tiny_projection = math.ldexp(1.0, -600)
    extreme_frame = derive_plane_local_jones_frame(
        ray_direction=_vector(
            (0.0, tiny_projection, 1.0),
            device=device,
        ).unsqueeze(0),
        plane_tangent_x=_vector((0.0, 0.0, 1.0), device=device).unsqueeze(0),
        is_interacted=torch.tensor((True,), device=device),
    )
    local_x = frame.axis_x
    local_y = frame.axis_y
    retarded = retard_ray_polarization(
        ray_polarization=polarization,
        plane_local_frame=frame,
        is_interacted=torch.tensor((True,), device=device),
        retardance_cycles=_scalar(0.23, device=device),
        retarded_eigenstate_azimuth_radians=_scalar(0.17, device=device),
        retarded_eigenstate_ellipticity_radians=_scalar(0.05, device=device),
    )
    assert retarded.device.type == "cuda"
    assert torch.equal(
        extreme_frame.is_interaction_degenerate,
        torch.tensor((False,), device=device),
    )
    assert torch.equal(
        extreme_frame.is_projection_resolvable,
        torch.tensor((True,), device=device),
    )
    assert torch.allclose(
        torch.linalg.norm(extreme_frame.axis_x, dim=-1),
        torch.ones(1, dtype=torch.float64, device=device),
        atol=1.0e-15,
        rtol=0.0,
    )
    for result in (
        embedded,
        reflected_polarization,
        rotated_polarization,
        local_x,
        local_y,
    ):
        assert result.device.type == "cuda"
    assert torch.allclose(
        retarded.abs().square().sum(-1),
        torch.ones(1, dtype=torch.float64, device=device),
        atol=1.0e-15,
        rtol=0.0,
    )
