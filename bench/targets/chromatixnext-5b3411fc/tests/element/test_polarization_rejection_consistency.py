
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math

import pytest
import torch

from chromatix_next.errors import AssemblyError, OpticalError
from chromatix_next.optics import (
    Assembly,
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PolarizationRepresentation,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.element import Retarder
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


@dataclass(frozen=True)
class _PolarizationRejectionCase:
    action_name: str
    component_name: str
    bare_identity: str
    make_component: Callable[[], torch.nn.Module]
    exposed_port: str | None
    is_reciprocal: bool


def _assembly_grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(8, 8),
        sample_spacing=(1.0e-6, 1.0e-6),
    )


def _wavelength() -> float:
    return 2.0e-6


def _make_retarder() -> torch.nn.Module:
    return Retarder(
        retardance_cycles=0.25,
        retarded_eigenstate_azimuth_radians=math.pi / 4.0,
        retarded_eigenstate_ellipticity_radians=0.0,
    )


_REJECTION_CASES = (
    _PolarizationRejectionCase(
        action_name="Retarder",
        component_name="retarder",
        bare_identity="retarder_polarization_representation_invalid",
        make_component=_make_retarder,
        exposed_port=None,
        is_reciprocal=False,
    ),
)

_REJECTED_REPRESENTATIONS = (
    PolarizationRepresentation.SCALAR,
    PolarizationRepresentation.FULL,
)


def _source_with_representation(
    representation: PolarizationRepresentation,
) -> PlaneWave:
    polarization = (
        Polarization.scalar()
        if representation is PolarizationRepresentation.SCALAR
        else Polarization.full(components=(1.0, 0.0, 0.0))
    )
    return PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=_wavelength()),
        polarization=polarization,
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )


def _transverse_source() -> PlaneWave:
    return PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=_wavelength()),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )


def _field_with_representation(
    representation: PolarizationRepresentation,
    *,
    device: torch.device | str | None = None,
) -> OpticalField:
    grid = _assembly_grid()
    counts_y, counts_x = grid.sample_counts
    return OpticalField(
        envelope=torch.ones(
            (1, representation.component_count, counts_y, counts_x),
            dtype=torch.complex128,
            device=device,
        ),
        grid=grid,
        spectrum=Spectrum.monochromatic(wavelength=_wavelength()),
        polarization_representation=representation,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )


def _transverse_field(
    *,
    device: torch.device | str | None = None,
) -> OpticalField:
    return _field_with_representation(
        PolarizationRepresentation.TRANSVERSE,
        device=device,
    )


def _invoke_component(
    case: _PolarizationRejectionCase,
    rejected_field: OpticalField,
    *,
    device: torch.device | str | None = None,
) -> None:
    component = case.make_component()
    if case.is_reciprocal:
        component(rejected_field, _transverse_field(device=device))
        return
    component(rejected_field)


def _build_rejection_assembly(
    case: _PolarizationRejectionCase,
    representation: PolarizationRepresentation,
) -> Assembly:
    assembly = Assembly()
    grid = _assembly_grid()
    rejected_source = _source_with_representation(representation)
    component = case.make_component()
    assembly.include(rejected_source, name="rejected_source", grid=grid)
    assembly.include(component, name=case.component_name)
    if case.is_reciprocal:
        transverse_source = _transverse_source()
        assembly.include(transverse_source, name="transverse_source", grid=grid)
        assembly.connect(
            rejected_source,
            component,
            destination_port="transmitted",
        )
        assembly.connect(
            transverse_source,
            component,
            destination_port="reflected",
        )
    else:
        assembly.connect(rejected_source, component)
    assembly.expose(
        component,
        name="rejected_output",
        port=case.exposed_port,
    )
    return assembly


def _wrapped_identity(case: _PolarizationRejectionCase) -> str:
    return (
        f"assembly_element_forward_failed:"
        f"{case.component_name}:{case.bare_identity}"
    )


@pytest.mark.parametrize(
    "case",
    _REJECTION_CASES,
    ids=[case.action_name for case in _REJECTION_CASES],
)
@pytest.mark.parametrize(
    "representation",
    _REJECTED_REPRESENTATIONS,
    ids=[representation.name for representation in _REJECTED_REPRESENTATIONS],
)
def test_direct_execution_rejects_with_action_identity(
    case: _PolarizationRejectionCase,
    representation: PolarizationRepresentation,
) -> None:
    """
    直接执行在每个动作上保留其拥有的裸身份
    """

    rejected_field = _field_with_representation(representation)
    with pytest.raises(OpticalError) as caught:
        _invoke_component(case, rejected_field)
    assert caught.value.identity == case.bare_identity


@pytest.mark.parametrize(
    "case",
    _REJECTION_CASES,
    ids=[case.action_name for case in _REJECTION_CASES],
)
@pytest.mark.parametrize(
    "representation",
    _REJECTED_REPRESENTATIONS,
    ids=[representation.name for representation in _REJECTED_REPRESENTATIONS],
)
def test_meta_execution_rejects_with_action_identity(
    case: _PolarizationRejectionCase,
    representation: PolarizationRepresentation,
) -> None:
    """
    meta 执行不读取真实值并保留同一动作裸身份
    """

    rejected_field = _field_with_representation(
        representation,
        device="meta",
    )
    with pytest.raises(OpticalError) as caught:
        _invoke_component(case, rejected_field, device="meta")
    assert caught.value.identity == case.bare_identity


@pytest.mark.parametrize(
    "case",
    _REJECTION_CASES,
    ids=[case.action_name for case in _REJECTION_CASES],
)
@pytest.mark.parametrize(
    "representation",
    _REJECTED_REPRESENTATIONS,
    ids=[representation.name for representation in _REJECTED_REPRESENTATIONS],
)
def test_assembly_check_rejects_with_action_identity(
    case: _PolarizationRejectionCase,
    representation: PolarizationRepresentation,
) -> None:
    """
    装配检查用动作名称包装其裸身份
    """

    assembly = _build_rejection_assembly(case, representation)
    with pytest.raises(AssemblyError) as caught:
        assembly.check()
    assert caught.value.identity == _wrapped_identity(case)


@pytest.mark.parametrize(
    "case",
    _REJECTION_CASES,
    ids=[case.action_name for case in _REJECTION_CASES],
)
@pytest.mark.parametrize(
    "representation",
    _REJECTED_REPRESENTATIONS,
    ids=[representation.name for representation in _REJECTED_REPRESENTATIONS],
)
def test_workstation_replay_rejects_with_action_identity(
    case: _PolarizationRejectionCase,
    representation: PolarizationRepresentation,
) -> None:
    """
    工作站 meta 预演复用装配包装身份并在真实重放前拒绝
    """

    assembly = _build_rejection_assembly(case, representation)
    workstation = Workstation.cpu()
    with pytest.raises(AssemblyError) as caught:
        assembly.freeze()
        workstation.host(assembly)
        workstation.run(assembly)
    assert caught.value.identity == _wrapped_identity(case)
