from __future__ import annotations

import ast
import copy
import math
from pathlib import Path
from typing import Literal

import pytest
import torch

from chromatix_next.errors import AssemblyError, OpticalValueError
from chromatix_next.optics import Assembly, SpatialGrid, Spectrum, Vacuum
from chromatix_next.optics.element.ideal_planar_mirror import (
    IdealPlanarMirror,
    MirrorTerminal,
)
from chromatix_next.optics.field import (
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    _own_field_value,
    _SourceLineage,
)
from chromatix_next.optics.polarization import PolarizationRepresentation
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_VIGNETTED,
    RayBundle,
)
from chromatix_next.optics.surface.plane import Plane


class _ReplayWaveSource(torch.nn.Module):
    # 由测试张量产生同一 lineage 的 fixed-double transverse OpticalField

    envelope: torch.Tensor

    def __init__(
        self,
        envelope: torch.Tensor,
        *,
        lineage: _SourceLineage,
        corruption: Literal["complex64", "nonfinite"] | None = None,
    ) -> None:
        super().__init__()
        self.register_buffer("envelope", envelope)
        self._lineage = lineage
        self.corruption = corruption

    @property
    def role(self) -> Literal["source"]:
        """
        返回测试 Source 的封闭角色

        Returns:
            source 角色字面量

        """
        return "source"

    def forward(self, grid: SpatialGrid) -> OpticalField:
        """
        在 Assembly 锚定网格上构造测试 Wave 值

        Args:
            grid: Source 的作者采样网格

        Returns:
            保留测试 envelope 与 lineage 的 OpticalField

        """
        field = OpticalField(
            envelope=self.envelope,
            grid=grid,
            spectrum=Spectrum.monochromatic(wavelength=632.8e-9),
            polarization_representation=(
                PolarizationRepresentation.TRANSVERSE
            ),
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(2.5e-3,)),
        )
        _own_field_value(field, self._lineage)
        if self.corruption == "complex64":
            object.__setattr__(
                field,
                "envelope",
                field.envelope.to(torch.complex64),
            )
        elif self.corruption == "nonfinite":
            corrupted = field.envelope.clone()
            corrupted[..., 0, 0] = complex(float("nan"), 0.0)
            object.__setattr__(field, "envelope", corrupted)
        return field


class _ReplayRaySource(torch.nn.Module):
    # 由注册状态重建测试 RayBundle，便于 Assembly 与 Meta 共用 replay

    position: torch.Tensor
    direction: torch.Tensor
    polarization_vector: torch.Tensor
    power: torch.Tensor
    refractive_index: torch.Tensor
    optical_path: torch.Tensor
    status: torch.Tensor

    def __init__(self, bundle: RayBundle) -> None:
        super().__init__()
        self.register_buffer("position", bundle.position)
        self.register_buffer("direction", bundle.direction)
        self.register_buffer(
            "polarization_vector",
            bundle.polarization_vector,
        )
        self.register_buffer("power", bundle.power)
        self.register_buffer("refractive_index", bundle.refractive_index)
        self.register_buffer("optical_path", bundle.optical_path)
        self.register_buffer("status", bundle.status)
        self.spectrum = bundle.spectrum

    @property
    def role(self) -> Literal["source"]:
        """
        返回测试 Source 的封闭角色

        Returns:
            source 角色字面量

        """
        return "source"

    def forward(self, grid: SpatialGrid) -> RayBundle:
        """
        从注册状态重建 fixed-double RayBundle

        Args:
            grid: Assembly Source 的作者锚，本探针不消费其采样值

        Returns:
            共享注册张量的 RayBundle

        """
        del grid
        return RayBundle(
            position=self.position,
            direction=self.direction,
            polarization_vector=self.polarization_vector,
            power=self.power,
            refractive_index=self.refractive_index,
            optical_path=self.optical_path,
            status=self.status,
            spectrum=self.spectrum,
        )


def _grid() -> SpatialGrid:
    return SpatialGrid(
        sample_counts=(3, 5),
        sample_spacing=(7.0e-6, 11.0e-6),
        first_sample_position=(-9.0e-6, 17.0e-6),
    )


def _mirror() -> IdealPlanarMirror:
    return IdealPlanarMirror(
        origin=(0.0, 0.0, 0.0),
        outward_normal=(0.0, 0.0, -1.0),
        transverse_up=(0.0, 1.0, 0.0),
    )


def _nextafter_scale(steps: int) -> torch.Tensor:
    scale = torch.tensor(1.0, dtype=torch.float64)
    toward_two = torch.tensor(2.0, dtype=torch.float64)
    for _ in range(steps):
        scale = torch.nextafter(scale, toward_two)
    return scale


def _scaled_boundary_mirror(steps: int) -> IdealPlanarMirror:
    scale = _nextafter_scale(steps)
    zero = scale * 0.0
    return IdealPlanarMirror(
        origin=(0.0, 0.0, 0.0),
        outward_normal=torch.stack((zero, zero, -scale)),
        transverse_up=torch.stack((zero, scale, zero)),
    )


def _wave_envelope(
    *,
    vertical_only: bool = False,
    requires_grad: bool = False,
) -> torch.Tensor:
    sample = torch.arange(15, dtype=torch.float64).reshape(3, 5)
    horizontal = sample + 1j * (sample + 0.25)
    vertical = 2.0 * sample - 1j * (sample + 0.5)
    envelope = torch.stack((horizontal, vertical)).unsqueeze(0)
    if vertical_only:
        envelope = torch.stack(
            (
                torch.zeros_like(sample, dtype=torch.complex128),
                torch.ones_like(sample, dtype=torch.complex128),
            )
        ).unsqueeze(0)
    return envelope.to(torch.complex128).requires_grad_(requires_grad)


def _run_wave(
    source: _ReplayWaveSource,
    *,
    mirror: IdealPlanarMirror | None = None,
) -> tuple[Assembly, OpticalField]:
    owner = _mirror() if mirror is None else mirror
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include_directional(owner, name="mirror")
    encounter = assembly.wave_encounter(
        owner,
        name="mirror_turn",
        incident_terminals=(MirrorTerminal.FRONT,),
    )
    assembly.connect(
        source,
        encounter,
        destination_terminal=MirrorTerminal.FRONT,
    )
    assembly.expose(
        encounter,
        name="reflected",
        source_terminal=MirrorTerminal.FRONT,
    )
    assembly.freeze()
    outputs = assembly._replay()  # noqa: SLF001
    return assembly, outputs["reflected"]  # type: ignore[return-value]


def _frozen_ray_assembly(
    bundle: RayBundle,
    *,
    mirror: IdealPlanarMirror | None = None,
) -> Assembly:
    source = _ReplayRaySource(bundle)
    owner = _mirror() if mirror is None else mirror
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include_directional(owner, name="mirror")
    encounter = assembly.ray_encounter(
        owner,
        name="mirror_turn",
        incident_terminal=MirrorTerminal.FRONT,
    )
    assembly.connect(
        source,
        encounter,
        destination_terminal=MirrorTerminal.FRONT,
    )
    assembly.expose(
        encounter,
        name="reflected",
        source_terminal=MirrorTerminal.FRONT,
    )
    assembly.freeze()
    return assembly


def _run_ray(
    bundle: RayBundle,
    *,
    mirror: IdealPlanarMirror | None = None,
) -> tuple[Assembly, RayBundle]:
    assembly = _frozen_ray_assembly(bundle, mirror=mirror)
    outputs = assembly._replay()  # noqa: SLF001
    return assembly, outputs["reflected"]  # type: ignore[return-value]


def _ray_bundle(
    *,
    direction: torch.Tensor | None = None,
    polarization: torch.Tensor | None = None,
) -> RayBundle:
    resolved_direction = (
        torch.tensor(
            (((0.6, 0.0, 0.8), (0.0, 0.0, 1.0)),),
            dtype=torch.float64,
        )
        if direction is None
        else direction
    )
    resolved_polarization = (
        torch.tensor(
            (
                (
                    (0.8 + 0.0j, 0.0 + 0.0j, -0.6 + 0.0j),
                    (0.0 + 0.0j, 1.0j, 0.0 + 0.0j),
                ),
            ),
            dtype=torch.complex128,
        )
        if polarization is None
        else polarization
    )
    return RayBundle(
        position=torch.tensor(
            (((0.0, 0.0, 0.0), (1.0e-3, 0.0, 0.0)),),
            dtype=torch.float64,
        ),
        direction=resolved_direction,
        polarization_vector=resolved_polarization,
        power=torch.tensor(((2.0, 3.0),), dtype=torch.float64),
        refractive_index=torch.tensor(((1.0, 1.4),), dtype=torch.float64),
        optical_path=torch.tensor(((4.5e-3, 7.0e-3),), dtype=torch.float64),
        status=torch.tensor(
            ((RAY_STATUS_ACTIVE, RAY_STATUS_VIGNETTED),),
            dtype=torch.uint8,
        ),
        spectrum=Spectrum.monochromatic(wavelength=632.8e-9),
    )


def _single_ray_bundle(
    *,
    position: tuple[float, float, float],
    direction: tuple[float, float, float],
    polarization: tuple[complex, complex, complex],
    power: float = 3.0,
    refractive_index: float = 1.25,
    optical_path: float = 0.5,
    device: torch.device | str | None = None,
) -> RayBundle:
    return RayBundle(
        position=torch.tensor(
            ((position,),),
            dtype=torch.float64,
            device=device,
        ),
        direction=torch.tensor(
            ((direction,),),
            dtype=torch.float64,
            device=device,
        ),
        polarization_vector=torch.tensor(
            ((polarization,),),
            dtype=torch.complex128,
            device=device,
        ),
        power=torch.tensor(
            ((power,),),
            dtype=torch.float64,
            device=device,
        ),
        refractive_index=torch.tensor(
            ((refractive_index,),),
            dtype=torch.float64,
            device=device,
        ),
        optical_path=torch.tensor(
            ((optical_path,),),
            dtype=torch.float64,
            device=device,
        ),
        status=torch.tensor(
            ((RAY_STATUS_ACTIVE,),),
            dtype=torch.uint8,
            device=device,
        ),
        spectrum=Spectrum.monochromatic(wavelength=632.8e-9),
    )


def test_wave_mirror_keeps_exact_scalar_and_basis_transport_separate() -> None:
    source = _ReplayWaveSource(
        _wave_envelope(),
        lineage=_SourceLineage(),
    )
    owner = _mirror()
    _assembly, reflected = _run_wave(source, mirror=owner)

    # 对该 frame，incident horizontal 为 +x，outgoing horizontal 为 -x
    frame = owner._terminal_frame(MirrorTerminal.FRONT)  # noqa: SLF001
    assert torch.equal(
        frame.outgoing_direction,
        -frame.incident_direction,
    )
    assert torch.equal(
        frame.outgoing_horizontal,
        -frame.incident_horizontal,
    )
    assert torch.equal(
        frame.outgoing_vertical,
        frame.incident_vertical,
    )
    expected_horizontal = source.envelope[:, 0]
    expected_vertical = -source.envelope[:, 1]
    assert torch.equal(reflected.envelope[:, 0], expected_horizontal)
    assert torch.equal(reflected.envelope[:, 1], expected_vertical)
    assert reflected.envelope.dtype is torch.complex128
    assert reflected.grid.sample_counts == (3, 5)
    assert reflected.grid.orientation == ("increasing", "decreasing")
    assert reflected.path_reference.lengths == (2.5e-3,)


def test_direct_complex_field_evidence_rejects_missing_minus_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _ReplayWaveSource(
        _wave_envelope(vertical_only=True),
        lineage=_SourceLineage(),
    )
    _assembly, qualified = _run_wave(source)

    monkeypatch.setattr(
        IdealPlanarMirror,
        "_wave_response",
        lambda self, values: values,
    )
    _counterfactual, omitted = _run_wave(source)

    assert torch.equal(qualified.envelope, -omitted.envelope)
    assert not torch.equal(qualified.envelope, omitted.envelope)


def test_ray_mirror_reaches_plane_before_householder_response() -> None:
    bundle = _single_ray_bundle(
        position=(0.0, 0.0, -1.0),
        direction=(0.0, 0.0, 1.0),
        polarization=(1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j),
    )
    _assembly, reflected = _run_ray(bundle)

    assert torch.equal(
        reflected.position,
        torch.zeros_like(bundle.position),
    )
    assert torch.equal(reflected.direction, -bundle.direction)
    assert torch.equal(
        reflected.polarization_vector,
        bundle.polarization_vector,
    )
    assert torch.equal(
        reflected.optical_path,
        torch.tensor(((1.75,),), dtype=torch.float64),
    )
    assert torch.equal(reflected.power, bundle.power)
    assert torch.equal(reflected.refractive_index, bundle.refractive_index)
    assert torch.equal(reflected.status, bundle.status)
    assert reflected.spectrum is bundle.spectrum


def test_ray_mirror_plane_accepts_admitted_fixed_geometry_boundary() -> None:
    owner = _scaled_boundary_mirror(6)
    authored_state = {
        name: value.clone()
        for name, value in owner.state_dict().items()
    }
    bundle = _single_ray_bundle(
        position=(0.0, 0.0, -1.0),
        direction=(0.0, 0.0, 1.0),
        polarization=(1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j),
    )

    _assembly, reflected = _run_ray(bundle, mirror=owner)

    assert torch.equal(reflected.position, torch.zeros_like(bundle.position))
    assert torch.equal(reflected.direction, -bundle.direction)
    assert torch.equal(
        reflected.polarization_vector,
        bundle.polarization_vector,
    )
    assert torch.equal(
        reflected.optical_path,
        torch.tensor(((1.75,),), dtype=torch.float64),
    )
    assert torch.equal(reflected.status, bundle.status)
    assert set(owner.state_dict()) == set(authored_state)
    assert all(
        torch.equal(owner.state_dict()[name], expected)
        for name, expected in authored_state.items()
    )


def test_frozen_ray_mirror_replay_does_not_construct_plane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _single_ray_bundle(
        position=(0.0, 0.0, -1.0),
        direction=(0.0, 0.0, 1.0),
        polarization=(1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j),
    )
    assembly = _frozen_ray_assembly(bundle)
    meta_assembly = copy.deepcopy(assembly).to(device="meta")

    def reject_runtime_plane(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("runtime_plane_constructed")

    monkeypatch.setattr(Plane, "__init__", reject_runtime_plane)
    reflected = assembly._replay()["reflected"]  # noqa: SLF001
    meta_reflected = meta_assembly._replay()["reflected"]  # noqa: SLF001

    assert torch.equal(reflected.position, torch.zeros_like(bundle.position))
    assert torch.equal(reflected.direction, -bundle.direction)
    assert torch.equal(
        reflected.optical_path,
        torch.tensor(((1.75,),), dtype=torch.float64),
    )
    assert meta_reflected.position.device.type == "meta"
    assert meta_reflected.direction.dtype is torch.float64
    assert meta_reflected.polarization_vector.dtype is torch.complex128


@pytest.mark.parametrize(
    ("position", "direction", "polarization"),
    (
        (
            (0.0, 0.0, 0.0),
            (0.0, 0.0, -1.0),
            (1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j),
        ),
        (
            (0.0, 0.0, -1.0),
            (1.0, 0.0, 0.0),
            (0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j),
        ),
    ),
    ids=("rear_facing_on_plane", "parallel"),
)
def test_ray_mirror_nonforward_lane_is_surface_missed(
    position: tuple[float, float, float],
    direction: tuple[float, float, float],
    polarization: tuple[complex, complex, complex],
) -> None:
    bundle = _single_ray_bundle(
        position=position,
        direction=direction,
        polarization=polarization,
    )
    _assembly, missed = _run_ray(bundle)

    assert torch.equal(missed.position, bundle.position)
    assert torch.equal(missed.direction, bundle.direction)
    assert torch.equal(
        missed.polarization_vector,
        bundle.polarization_vector,
    )
    assert torch.equal(missed.power, bundle.power)
    assert torch.equal(missed.refractive_index, bundle.refractive_index)
    assert torch.equal(missed.optical_path, bundle.optical_path)
    assert torch.equal(
        missed.status,
        torch.full_like(bundle.status, RAY_STATUS_SURFACE_MISSED),
    )
    assert missed.spectrum is bundle.spectrum


def test_ray_mirror_heterogeneous_lanes_follow_exact_state_rules() -> None:
    bundle = RayBundle(
        position=torch.tensor(
            (
                (
                    (0.0, 0.0, -1.0),
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, -1.0),
                    (0.0, 0.0, 0.0),
                    (0.25, -0.5, -0.75),
                ),
            ),
            dtype=torch.float64,
        ),
        direction=torch.tensor(
            (
                (
                    (0.6, 0.0, 0.8),
                    (0.0, 0.0, -1.0),
                    (1.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0),
                    (0.0, 1.0, 0.0),
                ),
            ),
            dtype=torch.float64,
        ),
        polarization_vector=torch.tensor(
            (
                (
                    (0.8 + 0.0j, 0.0 + 0.0j, -0.6 + 0.0j),
                    (1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j),
                    (0.0 + 0.0j, 1.0j, 0.0 + 0.0j),
                    (0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j),
                    (1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j),
                ),
            ),
            dtype=torch.complex128,
        ),
        power=torch.tensor(
            ((2.0, 3.0, 5.0, 7.0, 11.0),),
            dtype=torch.float64,
        ),
        refractive_index=torch.tensor(
            ((1.2, 1.3, 1.4, 1.5, 1.6),),
            dtype=torch.float64,
        ),
        optical_path=torch.tensor(
            ((0.5, 0.6, 0.7, 0.8, 0.9),),
            dtype=torch.float64,
        ),
        status=torch.tensor(
            (
                (
                    RAY_STATUS_ACTIVE,
                    RAY_STATUS_ACTIVE,
                    RAY_STATUS_ACTIVE,
                    RAY_STATUS_ACTIVE,
                    RAY_STATUS_VIGNETTED,
                ),
            ),
            dtype=torch.uint8,
        ),
        spectrum=Spectrum.monochromatic(wavelength=632.8e-9),
    )
    _assembly, reflected = _run_ray(bundle)

    expected_position = bundle.position.clone()
    expected_position[0, 0] = torch.tensor(
        (0.75, 0.0, 0.0),
        dtype=torch.float64,
    )
    expected_direction = bundle.direction.clone()
    expected_direction[0, 0, 2] = -0.8
    expected_direction[0, 3, 2] = -1.0
    expected_polarization = bundle.polarization_vector.clone()
    expected_polarization[0, 0, 2] = 0.6 + 0.0j
    expected_optical_path = bundle.optical_path.clone()
    expected_optical_path[0, 0] = 2.0
    expected_status = bundle.status.clone()
    expected_status[0, 1] = RAY_STATUS_SURFACE_MISSED
    expected_status[0, 2] = RAY_STATUS_SURFACE_MISSED

    assert torch.equal(reflected.position, expected_position)
    assert torch.equal(reflected.direction, expected_direction)
    assert torch.equal(reflected.polarization_vector, expected_polarization)
    assert torch.equal(reflected.power, bundle.power)
    assert torch.equal(reflected.refractive_index, bundle.refractive_index)
    assert torch.equal(reflected.optical_path, expected_optical_path)
    assert torch.equal(reflected.status, expected_status)
    assert reflected.spectrum is bundle.spectrum
    assert reflected.direction.dtype is torch.float64
    assert reflected.polarization_vector.dtype is torch.complex128
    assert reflected.power.dtype is torch.float64


def test_ray_mirror_unrepresentable_distance_keeps_adr_0013_identity() -> None:
    c = torch.tensor(math.sqrt(0.5), dtype=torch.float64)
    tiny = torch.tensor(2.0 ** -600, dtype=torch.float64)
    zero = torch.tensor(0.0, dtype=torch.float64)
    ray_direction = torch.stack((c, c, tiny))
    transverse_up = torch.stack((c, c, zero))
    plane_tangent_x = torch.stack((-tiny * c, tiny * c, torch.ones_like(c)))
    plane_normal = torch.linalg.cross(transverse_up, plane_tangent_x)
    owner = IdealPlanarMirror(
        origin=ray_direction,
        outward_normal=-plane_normal,
        transverse_up=transverse_up,
    )
    bundle = _single_ray_bundle(
        position=(0.0, 0.0, 0.0),
        direction=tuple(float(value) for value in ray_direction),
        polarization=(
            complex(float(c), 0.0),
            complex(float(-c), 0.0),
            0.0 + 0.0j,
        ),
    )

    with pytest.raises(OpticalValueError) as rejected:
        _run_ray(bundle, mirror=owner)

    assert rejected.value.identity == "ray_surface_distance_unresolvable"


def test_equal_arm_mirror_omission_is_common_phase_but_one_arm_is_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage = _SourceLineage()
    first = _ReplayWaveSource(
        _wave_envelope(vertical_only=True),
        lineage=lineage,
    )
    second_values = _wave_envelope(vertical_only=True) * torch.exp(
        torch.tensor(1j * torch.pi / 3.0, dtype=torch.complex128)
    )
    second = _ReplayWaveSource(second_values, lineage=lineage)
    _first_assembly, first_qualified = _run_wave(first)
    _second_assembly, second_qualified = _run_wave(second)
    qualified_intensity = (
        first_qualified.envelope + second_qualified.envelope
    ).abs().square()

    monkeypatch.setattr(
        IdealPlanarMirror,
        "_wave_response",
        lambda self, values: values,
    )
    _first_omitted_assembly, first_omitted = _run_wave(first)
    _second_omitted_assembly, second_omitted = _run_wave(second)
    both_omitted_intensity = (
        first_omitted.envelope + second_omitted.envelope
    ).abs().square()
    one_arm_omitted_intensity = (
        first_omitted.envelope + second_qualified.envelope
    ).abs().square()

    assert torch.equal(qualified_intensity, both_omitted_intensity)
    assert float(
        (qualified_intensity - one_arm_omitted_intensity).abs().amax()
    ) >= 0.20


@pytest.mark.parametrize(
    ("corruption", "underlying"),
    (
        ("complex64", "optical_field_envelope_dtype_invalid"),
        ("nonfinite", "optical_field_envelope_nonfinite"),
    ),
)
def test_fixed_double_and_nonfinite_failures_are_reenterable(
    corruption: Literal["complex64", "nonfinite"],
    underlying: str,
) -> None:
    envelope = _wave_envelope(requires_grad=True)
    source = _ReplayWaveSource(
        envelope,
        lineage=_SourceLineage(),
        corruption=corruption,
    )
    owner = _mirror()
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include_directional(owner, name="mirror")
    encounter = assembly.wave_encounter(
        owner,
        name="mirror_turn",
        incident_terminals=(MirrorTerminal.FRONT,),
    )
    assembly.connect(
        source,
        encounter,
        destination_terminal=MirrorTerminal.FRONT,
    )
    assembly.expose(
        encounter,
        name="reflected",
        source_terminal=MirrorTerminal.FRONT,
    )
    expected_identity = (
        "assembly_wave_contributors_incompatible:owner=mirror:"
        "encounter=mirror_turn:incident=front:outgoing=-:route=-:"
        f"underlying={underlying}"
    )
    if corruption == "complex64":
        authored_facts = (
            assembly._encounters,  # noqa: SLF001
            assembly._plan_connections,  # noqa: SLF001
            assembly._directional_exposures,  # noqa: SLF001
            assembly._route_ends,  # noqa: SLF001
        )

        with pytest.raises(AssemblyError) as check_failure:
            assembly.check()
        with pytest.raises(AssemblyError) as freeze_failure:
            assembly.freeze()

        assert check_failure.value.identity == expected_identity
        assert freeze_failure.value.identity == expected_identity
        assert not assembly.is_frozen
        assert assembly._frozen_facts is None  # noqa: SLF001
        assert (
            assembly._encounters,  # noqa: SLF001
            assembly._plan_connections,  # noqa: SLF001
            assembly._directional_exposures,  # noqa: SLF001
            assembly._route_ends,  # noqa: SLF001
        ) == authored_facts

        source.corruption = None
        assembly.freeze()
    else:
        assembly.freeze()
        with pytest.raises(AssemblyError) as captured:
            assembly._replay()  # noqa: SLF001
        assert captured.value.identity == expected_identity

    source.corruption = None
    outputs = assembly._replay()  # noqa: SLF001
    reflected = outputs["reflected"]
    loss = reflected.envelope.real.square().sum()
    loss.backward()
    assert envelope.grad is not None
    assert bool(torch.isfinite(envelope.grad).all())
    assert float(envelope.grad.abs().amax()) > 0.0


def test_invalid_live_geometry_fails_then_replays_after_exact_repair() -> None:
    source = _ReplayWaveSource(
        _wave_envelope(),
        lineage=_SourceLineage(),
    )
    owner = _mirror()
    assembly, expected = _run_wave(source, mirror=owner)
    with torch.no_grad():
        owner.origin[0] = float("nan")
    with pytest.raises(OpticalValueError) as captured:
        assembly._replay()  # noqa: SLF001
    assert captured.value.identity == "ideal_planar_mirror_origin_nonfinite"

    with torch.no_grad():
        owner.origin[0] = 0.0
    repaired = assembly._replay()["reflected"]  # noqa: SLF001
    assert torch.equal(repaired.envelope, expected.envelope)


def test_ray_gradient_is_continuous_away_from_status_boundaries() -> None:
    direction = torch.tensor(
        (((0.0, 0.0, 1.0), (0.0, 0.0, 1.0)),),
        dtype=torch.float64,
        requires_grad=True,
    )
    polarization = torch.tensor(
        (
            (
                (1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j),
                (0.0 + 0.0j, 1.0j, 0.0 + 0.0j),
            ),
        ),
        dtype=torch.complex128,
        requires_grad=True,
    )
    _assembly, reflected = _run_ray(
        _ray_bundle(
            direction=direction,
            polarization=polarization,
        )
    )
    loss = (
        reflected.direction[..., 2].sum()
        + reflected.polarization_vector.real[..., 0].sum()
        + reflected.polarization_vector.imag[..., 1].sum()
    )
    loss.backward()
    assert direction.grad is not None
    assert polarization.grad is not None
    assert bool(torch.isfinite(direction.grad).all())
    assert bool(torch.isfinite(polarization.grad).all())
    assert float(direction.grad.abs().amax()) > 0.0
    assert float(polarization.grad.abs().amax()) > 0.0


def test_cpu_and_meta_replay_have_the_same_fixed_double_schema() -> None:
    wave_source = _ReplayWaveSource(
        _wave_envelope(),
        lineage=_SourceLineage(),
    )
    wave_assembly, wave_output = _run_wave(wave_source)
    meta_wave = wave_assembly.to(device="meta")._replay()[  # noqa: SLF001
        "reflected"
    ]
    assert isinstance(meta_wave, OpticalField)
    assert meta_wave.envelope.shape == wave_output.envelope.shape
    assert meta_wave.envelope.dtype is torch.complex128
    assert meta_wave.envelope.device.type == "meta"

    ray_assembly, ray_output = _run_ray(_ray_bundle())
    meta_ray = ray_assembly.to(device="meta")._replay()[  # noqa: SLF001
        "reflected"
    ]
    assert isinstance(meta_ray, RayBundle)
    for name in (
        "position",
        "direction",
        "polarization_vector",
        "power",
        "refractive_index",
        "optical_path",
        "status",
    ):
        real_value = getattr(ray_output, name)
        meta_value = getattr(meta_ray, name)
        assert meta_value.shape == real_value.shape
        assert meta_value.dtype is real_value.dtype
        assert meta_value.device.type == "meta"


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="需要可用 CUDA 设备验证 native fixed-double Mirror Encounter",
)
def test_native_cuda_ray_mirror_keeps_fixed_double_schema() -> None:
    device = torch.device("cuda", 0)
    bundle = _single_ray_bundle(
        position=(0.0, 0.0, -1.0),
        direction=(0.0, 0.0, 1.0),
        polarization=(1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j),
        device=device,
    )
    owner = _scaled_boundary_mirror(6).to(device=device)
    _assembly, reflected = _run_ray(bundle, mirror=owner)

    assert reflected.position.device == device
    assert reflected.direction.device == device
    assert reflected.polarization_vector.device == device
    assert reflected.power.device == device
    assert reflected.refractive_index.device == device
    assert reflected.optical_path.device == device
    assert reflected.status.device == device
    assert reflected.position.dtype is torch.float64
    assert reflected.direction.dtype is torch.float64
    assert reflected.polarization_vector.dtype is torch.complex128
    assert reflected.power.dtype is torch.float64
    assert reflected.refractive_index.dtype is torch.float64
    assert reflected.optical_path.dtype is torch.float64
    assert reflected.status.dtype is torch.uint8
    assert torch.equal(reflected.position, torch.zeros_like(bundle.position))
    assert torch.equal(
        reflected.optical_path,
        torch.tensor(((1.75,),), dtype=torch.float64, device=device),
    )


def test_private_mirror_adapter_has_no_propagation_or_second_response_state() -> None:
    source = Path(
        "src/chromatix_next/optics/_mirror_directional.py",
    ).read_text(
        encoding="utf-8",
    )
    forbidden = (
        "axial_distance",
        "Medium",
        "path_reference=",
        "optical_path +",
        "mixing_angle",
        "response_matrix",
        "scattering",
    )
    assert all(token not in source for token in forbidden)
    assert "from .surface.plane import Plane" not in source
    assert "Plane(" not in source
    assert "torch.nn.Module(" not in source
    assert source.count("plane_encounter(") == 1
    assert source.count("advance_ray_surface(") == 1
    assert source.count("._wave_response(") == 1
    assert source.count("._ray_direction_response(") == 1
    syntax = ast.parse(source)
    adapter = next(
        node
        for node in syntax.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_ray_mirror_outputs"
    )
    replay_calls = tuple(
        node
        for node in ast.walk(adapter)
        if isinstance(node, ast.Call)
    )
    assert all(
        not (
            isinstance(call.func, ast.Name)
            and call.func.id == "Plane"
        )
        for call in replay_calls
    )
