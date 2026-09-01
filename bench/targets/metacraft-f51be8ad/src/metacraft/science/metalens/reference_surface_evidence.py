from __future__ import annotations

from collections.abc import Callable

from ...authority import Document, Reference, reference_for
from ...field.reference_surface import (
    AdmittedReferenceSurface,
    ReferenceSurfaceResponse,
    RequestedInputBasis,
    admit_response_components,
    reference_surface_document,
)
from ...field.reference_surface_formation import (
    ReferenceSurfaceFormationInput,
    UniformReferenceSurfaceFormation,
    form_uniform_reference_surfaces,
    uniform_reference_surface_formation_qualification_document,
)
from ...field.sample import Field
from ..periodic_response import (
    AdmittedPeriodicPolarization,
    AdmittedPeriodicTransmission,
    ObservedPeriodicPolarization,
    ObservedPeriodicTransmission,
    PeriodicPolarizationRequest,
    PeriodicReferenceSurfaceObservation,
    PeriodicTransmissionRequest,
    PeriodicWork,
)
from .periodic_cell_evidence import validate_observed_batch


_PeriodicRequest = PeriodicTransmissionRequest | PeriodicPolarizationRequest
_ObservedPeriodicBatch = (
    ObservedPeriodicTransmission | ObservedPeriodicPolarization
)
_AdmittedPeriodicItem = (
    AdmittedPeriodicTransmission | AdmittedPeriodicPolarization
)


def admit_reference_surfaces(
    request: _PeriodicRequest,
    observed: _ObservedPeriodicBatch,
    *,
    cell_identity: str | None = None,
    admit_object: Callable[..., Reference],
    admit_document: Callable[..., Reference],
) -> tuple[AdmittedReferenceSurface, ...]:
    """
    Form one complete batch, then admit its results in order.

    Formation finishes before any admission callback.  The later admissions
    are content-addressed and idempotent, but they are not a transactional
    batch: a failed callback returns no apparent batch, and already admitted
    facts remain safe to reuse on retry.
    """

    selected = _select_reference_surfaces(
        request,
        observed,
        cell_identity=cell_identity,
    )
    qualification_document = (
        uniform_reference_surface_formation_qualification_document()
    )
    qualification_reference = reference_for(qualification_document.to_bytes())
    qualification = UniformReferenceSurfaceFormation(
        realization_identity="periodic_rectilinear_bilinear_v1",
        qualification_reference=qualification_reference,
    )
    formation_inputs = (
        _formation_input(
            work,
            item,
            surface,
        )
        for work, item, surface in selected
    )
    fields = form_uniform_reference_surfaces(
        tuple(formation_inputs),
        qualification,
    )
    admitted_qualification = admit_document(
        qualification_document,
        references=(),
    )
    if admitted_qualification != qualification_reference:
        raise RuntimeError("reference_surface_formation_unqualified")
    return tuple(
        _admit_formed_surface(
            field,
            surface,
            admit_object=admit_object,
            admit_document=admit_document,
        )
        for (_, _, surface), field in zip(selected, fields, strict=True)
    )


def _select_reference_surfaces(
    request: _PeriodicRequest,
    observed: _ObservedPeriodicBatch,
    *,
    cell_identity: str | None,
) -> tuple[
    tuple[PeriodicWork, _AdmittedPeriodicItem, PeriodicReferenceSurfaceObservation],
    ...,
]:
    is_matching_variant = (
        type(request) is PeriodicTransmissionRequest
        and type(observed) is ObservedPeriodicTransmission
    ) or (
        type(request) is PeriodicPolarizationRequest
        and type(observed) is ObservedPeriodicPolarization
    )
    if not is_matching_variant:
        raise TypeError("periodic_response_variant_mismatch")
    validate_observed_batch(request, observed)
    selected = []
    for work, item in zip(request.items, observed.items, strict=True):
        if cell_identity is not None and work.cell_identity != cell_identity:
            continue
        surface = item.observation.reference_surface
        if surface is None:
            raise ValueError("reference_surface_observation_missing")
        if surface.requested_input_basis != work.input_basis:
            raise ValueError("reference_surface_input_basis_mismatch")
        selected.append((work, item, surface))
    if not selected:
        finding = (
            "geometric_surface_candidate_missing"
            if cell_identity is not None
            else "reference_surface_observation_missing"
        )
        raise ValueError(finding)
    return tuple(selected)


def _formation_input(
    work: PeriodicWork,
    item: _AdmittedPeriodicItem,
    surface: PeriodicReferenceSurfaceObservation,
) -> ReferenceSurfaceFormationInput:
    if surface.requested_input_basis != work.input_basis:
        raise ValueError("reference_surface_input_basis_mismatch")
    return ReferenceSurfaceFormationInput(
        wavelength_m=float(surface.wavelength_m),
        surface=surface.surface,
        frame=surface.frame,
        medium=surface.medium,
        basis=surface.output_basis,
        electric_components=surface.electric_components,
        source_references=(item.body_reference,),
        incident_reference_power=float(surface.incident_reference_power),
    )


def _admit_formed_surface(
    field: Field,
    surface: PeriodicReferenceSurfaceObservation,
    *,
    admit_object: Callable[..., Reference],
    admit_document: Callable[..., Reference],
) -> AdmittedReferenceSurface:
    response = ReferenceSurfaceResponse(
        field=field,
        requested_input_basis=RequestedInputBasis(
            surface.requested_input_basis
        ),
        order_regime=surface.order_regime,
        transmitted_power=float(surface.transmitted_power),
    )
    electric, magnetic = admit_response_components(response, admit_object)
    document = reference_surface_document(
        response,
        electric,
        magnetic_references=magnetic,
    )
    references = tuple(
        dict.fromkeys(
            (
                *response.field.source_references,
                *electric.values(),
                *magnetic.values(),
            )
        )
    )
    reference = admit_document(document, references=references)
    return AdmittedReferenceSurface(response, reference)
