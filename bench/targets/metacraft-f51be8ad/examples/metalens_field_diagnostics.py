from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from decimal import Decimal

import numpy
from numpy.typing import NDArray

from metacraft.authority import Document, Reference
from metacraft.canonical import canonicalize, encode_bytes
from metacraft.field.reference_surface import restore_reference_surface
from metacraft.field.sample import ComponentBasis, Field, Medium
from metacraft.science.metalens.aperture import (Aperture, Response, State,
                                                 form_field)
from metacraft.science.metalens.pointwise import (form_geometric_surface_field,
                                                  form_pointwise_surface_field)
from metacraft.science.metalens.result import (AchromaticResult,
                                               GeometricResult,
                                               PointwiseGeometricResult,
                                               PointwisePropagationResult,
                                               PropagationResult,
                                               restore_result)
from metacraft.science.result import Result

_DIAGNOSTIC_SCHEMA = "metacraft.examples.metalens_field_assumption_diagnostic"
_VARIANT_SCHEMA = "metacraft.examples.metalens_diagnostic_field"

Fetch = Callable[[Reference], bytes]


@dataclass(frozen=True, slots=True)
class DiagnosticFieldAssumptions:
    """
    Names the four optical choices varied by the external diagnostic.
    """

    phase_response: str
    useful_response: str
    polarization_response: str
    surface_response: str

    def __post_init__(self) -> None:
        """
        Require every assumption to carry explicit meaning.
        """

        if any(not self.value(name).strip() for name in self.names):
            raise ValueError("diagnostic_assumption_empty")

    @property
    def names(self) -> tuple[str, ...]:
        """
        Return the stable assumption order used for adjacent comparisons.
        """

        return (
            "phase_response",
            "useful_response",
            "polarization_response",
            "surface_response",
        )

    def value(self, name: str) -> str:
        """
        Return one named assumption without exposing storage details.
        """

        if name not in self.names:
            raise ValueError("diagnostic_assumption_unknown")
        value = getattr(self, name)
        assert isinstance(value, str)
        return value


@dataclass(frozen=True, slots=True)
class DiagnosticField:
    """
    Describes one immutable external field prescription.
    """

    name: str
    assumptions: DiagnosticFieldAssumptions
    field_signature: str
    changed_assumption: str | None
    is_different_from_previous: bool | None
    attribution: str
    source_references: tuple[Reference, ...]

    def __post_init__(self) -> None:
        """
        Require one traceable signature and coherent adjacent comparison.
        """

        if (
            not self.name.strip()
            or not self.attribution.strip()
            or not self.field_signature.startswith("sha256:")
            or not self.source_references
        ):
            raise ValueError("diagnostic_field_invalid")
        if self.changed_assumption is None:
            if self.is_different_from_previous is not None:
                raise ValueError("diagnostic_baseline_difference_invalid")
        elif (
            self.changed_assumption not in self.assumptions.names
            or self.is_different_from_previous is None
        ):
            raise ValueError("diagnostic_field_difference_invalid")

    def document(self) -> Document:
        """
        Encode one diagnostic field as a canonical external document.
        """

        return Document(_VARIANT_SCHEMA, _encode_diagnostic_field(self))


def _encode_diagnostic_field(field: DiagnosticField) -> dict[str, object]:
    """Preserve the established external name behind one encoder."""

    values = canonicalize(field)
    assert isinstance(values, dict)
    values["differs_from_previous"] = values.pop("is_different_from_previous")
    return values


@dataclass(frozen=True, slots=True)
class VectorFieldProvenance:
    """
    Retains the complete high-NA sampled-field interpretation.
    """

    component_names: tuple[str, ...]
    rectilinear_surface_references: tuple[Reference, ...]
    formation: str
    propagation: str
    longitudinal_power_reference: Reference

    def __post_init__(self) -> None:
        """
        Require complete Cartesian, formation, and propagation provenance.
        """

        if (
            self.component_names != ("x", "y", "z")
            or not self.rectilinear_surface_references
            or self.formation != "uniform"
            or self.propagation != "vector"
        ):
            raise ValueError("diagnostic_vector_provenance_invalid")


@dataclass(frozen=True, slots=True)
class FieldAssumptionDiagnostic:
    """
    Reports bounded assumption changes without changing scientific truth.
    """

    case_identity: str
    result_reference: Reference
    aperture_reference: Reference
    response_references: tuple[Reference, ...]
    field_reference: Reference
    focus_reference: Reference
    focal_region_reference: Reference
    endpoint_comparison_identity: str
    endpoint_dispositions: tuple[tuple[str, str], ...]
    assignment: str
    fixed_context: tuple[tuple[str, str], ...]
    variants: tuple[DiagnosticField, ...]
    first_divergent_step: str | None
    no_divergence_reason: str | None
    vector_provenance: VectorFieldProvenance | None
    interpretation: str = (
        "Bounded method-family diagnostic; not an exact published-case outcome. "
        "A divergent step names a changed diagnostic field, not paper disagreement."
    )

    def __post_init__(self) -> None:
        """
        Require exact sources and one honest divergence outcome.
        """

        if (
            not self.case_identity.startswith("sha256:")
            or not self.endpoint_comparison_identity.startswith("sha256:")
            or not self.response_references
            or not self.variants
            or not self.endpoint_dispositions
            or not self.assignment
        ):
            raise ValueError("field_assumption_diagnostic_invalid")
        if (self.first_divergent_step is None) == (
            self.no_divergence_reason is None
        ):
            raise ValueError("diagnostic_divergence_outcome_invalid")
        if (
            self.first_divergent_step is not None
            and self.first_divergent_step
            not in {item.name for item in self.variants}
        ):
            raise ValueError("diagnostic_divergence_step_unknown")
        if (
            self.no_divergence_reason is not None
            and not self.no_divergence_reason.strip()
        ):
            raise ValueError("diagnostic_no_divergence_reason_empty")

    def document(self) -> Document:
        """
        Encode the complete diagnostic as a canonical external document.
        """

        values = canonicalize(self)
        assert isinstance(values, dict)
        values["variants"] = [
            _encode_diagnostic_field(variant) for variant in self.variants
        ]
        return Document(_DIAGNOSTIC_SCHEMA, values)


def diagnose_field_assumptions(
    *,
    case_identity: str,
    result: Result,
    endpoint_comparison_identity: str,
    endpoint_dispositions: tuple[tuple[str, str], ...],
    fetch: Fetch,
    order: tuple[str, ...] | None = None,
) -> FieldAssumptionDiagnostic:
    """
    Read one admitted Result and isolate its field assumptions externally.
    """

    if not case_identity.startswith("sha256:"):
        raise ValueError("diagnostic_case_identity_invalid")
    if not endpoint_comparison_identity.startswith("sha256:"):
        raise ValueError("diagnostic_endpoint_identity_invalid")
    if not endpoint_dispositions:
        raise ValueError("diagnostic_endpoint_dispositions_empty")
    if fetch(result.reference) != result.document.to_bytes():
        raise ValueError("diagnostic_result_reference_mismatch")
    conclusion = restore_result(
        result.document,
        closure=result.closure,
        fetch=fetch,
    )
    if isinstance(conclusion, AchromaticResult):
        raise ValueError("achromatic_field_diagnostic_unsupported")
    variants, assignment, responses, vector = _form_diagnostic_variants(
        conclusion,
        fetch=fetch,
    )
    requested_order = order or tuple(item.name for item in variants)
    if set(requested_order) != {item.name for item in variants} or len(
        requested_order
    ) != len(variants):
        raise ValueError("diagnostic_order_invalid")
    by_name = {item.name: item for item in variants}
    ordered = tuple(by_name[name] for name in requested_order)
    first = next(
        (
            item.name
            for item in variants[1:]
            if item.is_different_from_previous
        ),
        None,
    )
    fixed_context = _fixed_context(conclusion, fetch=fetch)
    return FieldAssumptionDiagnostic(
        case_identity=case_identity,
        result_reference=result.reference,
        aperture_reference=conclusion.aperture_reference,
        response_references=responses,
        field_reference=conclusion.field_reference,
        focus_reference=conclusion.focus_reference,
        focal_region_reference=conclusion.focal_region_reference,
        endpoint_comparison_identity=endpoint_comparison_identity,
        endpoint_dispositions=endpoint_dispositions,
        assignment=assignment,
        fixed_context=fixed_context,
        variants=ordered,
        first_divergent_step=first,
        no_divergence_reason=(
            None
            if first is not None
            else "Every applicable diagnostic field is byte-for-byte equal."
        ),
        vector_provenance=vector,
    )


def _form_diagnostic_variants(
    conclusion: (
        PropagationResult
        | GeometricResult
        | PointwisePropagationResult
        | PointwiseGeometricResult
    ),
    *,
    fetch: Fetch,
) -> tuple[
    tuple[DiagnosticField, ...],
    str,
    tuple[Reference, ...],
    VectorFieldProvenance | None,
]:
    if isinstance(conclusion, PropagationResult):
        responses = tuple(
            dict.fromkeys(
                (
                    conclusion.phase_set_reference,
                    *(state.source_reference for state in conclusion.phase_set.states),
                )
            )
        )
        specifications = (
            _form_diagnostic_field(
                "ideal continuous",
                "continuous target phase",
                "unity",
                "single transmission channel",
                "cell grid",
                _continuous_signature(
                    conclusion.aperture,
                    conclusion.aperture_reference,
                ),
                (conclusion.aperture_reference,),
                None,
                "Upper reference from the fixed continuous target phase.",
            ),
            _form_diagnostic_field(
                "assigned target",
                f"finite {conclusion.phase_level_count}-level assigned target",
                "unity",
                "single transmission channel",
                "cell grid",
                _state_phase_signature(
                    conclusion.aperture,
                    conclusion.aperture_reference,
                    is_realized=False,
                ),
                (conclusion.phase_set_reference, conclusion.aperture_reference),
                "phase_response",
                "Finite phase assignment is the only changed assumption.",
            ),
            _form_diagnostic_field(
                "realized phase",
                "admitted selected-cell phase",
                "unity",
                "single transmission channel",
                "cell grid",
                _state_phase_signature(
                    conclusion.aperture,
                    conclusion.aperture_reference,
                    is_realized=True,
                ),
                responses,
                "phase_response",
                "Admitted periodic phase replaces the assigned target.",
            ),
            _form_diagnostic_field(
                "realized coefficient",
                "admitted selected-cell phase",
                "admitted useful transmission amplitude",
                "single transmission channel",
                "cell grid",
                _state_response_signature(
                    conclusion.aperture,
                    conclusion.aperture_reference,
                ),
                responses,
                "useful_response",
                "Useful amplitude from the same admitted response is added.",
            ),
        )
        return (
            _compare_adjacent_variants(specifications),
            f"finite {conclusion.phase_level_count} levels",
            responses,
            None,
        )
    if isinstance(conclusion, GeometricResult):
        responses = tuple(
            dict.fromkeys(
                (
                    conclusion.choice_reference,
                    conclusion.orientation_relation_reference,
                    *conclusion.orientation_relation.source_references,
                )
            )
        )
        specifications = _geometric_specifications(
            conclusion.aperture,
            conclusion.aperture_reference,
            responses,
        )
        return (
            _compare_adjacent_variants(specifications),
            f"finite {len(conclusion.aperture.states)} orientations",
            responses,
            None,
        )
    if isinstance(conclusion, PointwisePropagationResult):
        surface_references = tuple(
            item.admitted.reference for item in conclusion.surfaces.surfaces
        )
        rectilinear_sources = tuple(
            dict.fromkeys(
                reference
                for item in conclusion.surfaces.surfaces
                for reference in item.admitted.response.field.source_references
            )
        )
        responses = tuple(
            dict.fromkeys(
                (
                    conclusion.library.evidence_reference,
                    conclusion.surfaces_reference,
                    *surface_references,
                )
            )
        )
        specifications = (
            _form_diagnostic_field(
                "ideal continuous",
                "continuous target phase",
                "unity",
                "single transmission channel",
                "uniform sampled grid",
                _continuous_signature(
                    conclusion.aperture,
                    conclusion.aperture_reference,
                ),
                (conclusion.aperture_reference,),
                None,
                "Upper reference from the fixed continuous target phase.",
            ),
            _form_diagnostic_field(
                "realized phase",
                "pointwise admitted selected-cell phase",
                "unity",
                "single transmission channel",
                "uniform sampled grid",
                _state_phase_signature(
                    conclusion.aperture,
                    conclusion.aperture_reference,
                    is_realized=True,
                ),
                responses,
                "phase_response",
                "Pointwise admitted phase replaces the target without levels.",
            ),
            _form_diagnostic_field(
                "realized coefficient",
                "pointwise admitted selected-cell phase",
                "admitted useful transmission amplitude",
                "single transmission channel",
                "uniform sampled grid",
                _state_response_signature(
                    conclusion.aperture,
                    conclusion.aperture_reference,
                ),
                responses,
                "useful_response",
                "Useful amplitude from the same admitted response is added.",
            ),
            _form_diagnostic_field(
                "sampled surface",
                "pointwise admitted selected-cell phase",
                "admitted useful transmission amplitude",
                "single transmission channel",
                "admitted complex reference surfaces",
                _field_signature(_sampled_field(conclusion, fetch=fetch)),
                (*responses, conclusion.field_reference),
                "surface_response",
                "Complete sampled surfaces replace coefficient prescriptions.",
            ),
        )
        return (
            _compare_adjacent_variants(specifications),
            "pointwise",
            responses,
            _vector_provenance(conclusion, rectilinear_sources),
        )
    surface_references = (
        conclusion.transform.x_linear_response_reference,
        conclusion.transform.y_linear_response_reference,
    )
    restored_surfaces = tuple(
        restore_reference_surface(reference, fetch)
        for reference in surface_references
    )
    rectilinear_sources = tuple(
        dict.fromkeys(
            reference
            for surface in restored_surfaces
            for reference in surface.response.field.source_references
        )
    )
    responses = tuple(
        dict.fromkeys(
            (
                conclusion.choice_reference,
                conclusion.orientation_relation_reference,
                conclusion.transform_reference,
                *surface_references,
            )
        )
    )
    specifications = (
        *_geometric_specifications(
            conclusion.aperture,
            conclusion.aperture_reference,
            responses,
        ),
        _form_diagnostic_field(
            "sampled surface",
            "continuous admitted PB orientation",
            "carried by polarization response",
            "admitted converted and retained Jones channels",
            "admitted analytic sampled-surface transform",
            _field_signature(_sampled_field(conclusion, fetch=fetch)),
            (*responses, conclusion.field_reference),
            "surface_response",
            "The admitted sampled Jones surface replaces coefficient channels.",
        ),
    )
    return (
        _compare_adjacent_variants(specifications),
        "continuous orientation",
        responses,
        _vector_provenance(conclusion, rectilinear_sources),
    )


def _geometric_specifications(
    aperture: Aperture,
    aperture_reference: Reference,
    responses: tuple[Reference, ...],
) -> tuple[DiagnosticField, ...]:
    is_continuous = aperture.phase_levels is None
    assigned = (
        "continuous admitted PB orientation"
        if is_continuous
        else f"finite {len(aperture.states)}-orientation PB assignment"
    )
    surface = "uniform sampled grid" if is_continuous else "cell grid"
    return (
        _form_diagnostic_field(
            "ideal pb",
            "continuous analytic PB phase",
            "carried by polarization response",
            "ideal converted channel; zero retained channel",
            surface,
            _continuous_signature(
                aperture,
                aperture_reference,
                is_geometric=True,
            ),
            (aperture_reference,),
            None,
            "Upper PB reference with ideal conversion and no retained channel.",
        ),
        _form_diagnostic_field(
            "assigned orientation",
            assigned,
            "carried by polarization response",
            "ideal converted channel; zero retained channel",
            surface,
            _state_phase_signature(
                aperture,
                aperture_reference,
                is_realized=True,
                is_geometric=True,
            ),
            responses,
            "phase_response",
            "Physical orientation assignment is the only changed assumption.",
        ),
        _form_diagnostic_field(
            "realized jones",
            assigned,
            "carried by polarization response",
            "admitted converted and retained Jones channels",
            surface,
            _state_response_signature(
                aperture,
                aperture_reference,
                is_geometric=True,
            ),
            responses,
            "polarization_response",
            "Converted amplitude and retained leakage enter together as Jones response.",
        ),
    )


def _form_diagnostic_field(
    name: str,
    phase: str,
    useful: str,
    polarization: str,
    surface: str,
    signature: str,
    sources: tuple[Reference, ...],
    changed: str | None,
    attribution: str,
) -> DiagnosticField:
    return DiagnosticField(
        name=name,
        assumptions=DiagnosticFieldAssumptions(
            phase_response=phase,
            useful_response=useful,
            polarization_response=polarization,
            surface_response=surface,
        ),
        field_signature=signature,
        changed_assumption=changed,
        is_different_from_previous=None if changed is None else False,
        attribution=attribution,
        source_references=tuple(dict.fromkeys(sources)),
    )


def _compare_adjacent_variants(
    specifications: tuple[DiagnosticField, ...],
) -> tuple[DiagnosticField, ...]:
    linked = [specifications[0]]
    for previous, current in zip(specifications, specifications[1:], strict=False):
        changed = tuple(
            name
            for name in previous.assumptions.names
            if previous.assumptions.value(name) != current.assumptions.value(name)
        )
        if changed != (current.changed_assumption,):
            raise ValueError("diagnostic_assumption_change_not_single")
        linked.append(
            DiagnosticField(
                name=current.name,
                assumptions=current.assumptions,
                field_signature=current.field_signature,
                changed_assumption=current.changed_assumption,
                is_different_from_previous=(
                    current.field_signature != previous.field_signature
                ),
                attribution=current.attribution,
                source_references=current.source_references,
            )
        )
    return tuple(linked)


def _continuous_signature(
    aperture: Aperture,
    aperture_reference: Reference,
    *,
    is_geometric: bool = False,
) -> str:
    identities = numpy.full(aperture.is_occupied.shape, "", dtype="<U80")
    states = []
    cell = aperture.cells[0]
    for row, column in numpy.argwhere(aperture.is_occupied):
        phase = float(aperture.target_phase[row, column])
        identity = f"diagnostic-target-{row}-{column}"
        identities[row, column] = identity
        states.append(
            State(
                identity=identity,
                cell_identity=cell.identity,
                responses=_ideal_responses(
                    phase,
                    is_geometric=is_geometric,
                ),
                source=aperture_reference,
                target_phase=Decimal(str(phase)),
                realized_phase=Decimal(str(phase)),
                useful_power=Decimal("1"),
                leakage_power=Decimal("0"),
            )
        )
    diagnostic_aperture = replace(
        aperture,
        states=tuple(states),
        state_identities=identities,
        phase_levels=None,
    )
    return _formed_field_signature(
        diagnostic_aperture,
        aperture_reference,
        is_geometric=is_geometric,
    )


def _state_phase_signature(
    aperture: Aperture,
    aperture_reference: Reference,
    *,
    is_realized: bool,
    is_geometric: bool = False,
) -> str:
    states = tuple(
        replace(
            state,
            responses=_ideal_responses(
                float(
                    state.realized_phase
                    if is_realized
                    else state.target_phase
                ),
                is_geometric=is_geometric,
            ),
            useful_power=Decimal("1"),
            leakage_power=Decimal("0"),
        )
        for state in aperture.states
    )
    return _formed_field_signature(
        replace(aperture, states=states),
        aperture_reference,
        is_geometric=is_geometric,
    )


def _state_response_signature(
    aperture: Aperture,
    aperture_reference: Reference,
    *,
    is_geometric: bool = False,
) -> str:
    return _formed_field_signature(
        aperture,
        aperture_reference,
        is_geometric=is_geometric,
    )


def _ideal_responses(
    phase: float,
    *,
    is_geometric: bool,
) -> tuple[Response, ...]:
    coefficient = complex(math.cos(phase), math.sin(phase))
    converted = Response(
        channel="converted" if is_geometric else "transmission",
        real_part=Decimal(str(coefficient.real)),
        imaginary_part=Decimal(str(coefficient.imag)),
        power=Decimal("1"),
    )
    if not is_geometric:
        return (converted,)
    return (
        converted,
        Response(
            channel="retained",
            real_part=Decimal("0"),
            imaginary_part=Decimal("0"),
            power=Decimal("0"),
        ),
    )


def _formed_field_signature(
    aperture: Aperture,
    aperture_reference: Reference,
    *,
    is_geometric: bool,
) -> str:
    basis = (
        ComponentBasis.CIRCULAR
        if is_geometric
        else ComponentBasis.TRANSVERSE_LINEAR
    )
    channels = tuple(
        sorted(
            {
                response.channel
                for state in aperture.states
                for response in state.responses
            }
        )
    )
    if len(channels) > len(basis.components):
        raise ValueError("diagnostic_field_channels_unsupported")
    # This canonical pairing identifies complex content only. It deliberately
    # does not repeat the production incident-handedness selection rule.
    component_channels = {
        component: channels[index] if index < len(channels) else None
        for index, component in enumerate(basis.components)
    }
    field = form_field(
        aperture,
        wavelength_m=1.0,
        surface_position_m=0.0,
        medium=Medium("air"),
        basis=basis,
        component_channels=component_channels,
        aperture_reference=aperture_reference,
    )
    return _field_signature(field)


def _field_signature(field: Field) -> str:
    return _complex_signature(
        {
            component.name: component.values
            for component in (*field.electric_components, *field.magnetic_components)
        }
    )


def _complex_signature(components: Mapping[str, NDArray[numpy.complex128]]) -> str:
    digest = hashlib.sha256()
    for name in sorted(components):
        values = numpy.asarray(components[name], dtype="<c16", order="C")
        digest.update(encode_bytes({"name": name, "shape": list(values.shape)}))
        digest.update(values.tobytes(order="C"))
    return "sha256:" + digest.hexdigest()


def _fixed_context(
    conclusion: (
        PropagationResult
        | GeometricResult
        | PointwisePropagationResult
        | PointwiseGeometricResult
    ),
    *,
    fetch: Fetch,
) -> tuple[tuple[str, str], ...]:
    aperture = conclusion.aperture
    occupancy = hashlib.sha256(aperture.is_occupied.tobytes()).hexdigest()
    if isinstance(
        conclusion,
        (PointwisePropagationResult, PointwiseGeometricResult),
    ):
        field = _sampled_field(conclusion, fetch=fetch)
        sampling = (
            f"{field.surface.shape[0]}x{field.surface.shape[1]} at "
            f"{field.surface.spacing_m:.17g} m"
        )
        incident = f"{field.basis.value}; one admitted aperture"
        normalization = (
            f"incident reference power {field.incident_reference_power:.17g}"
        )
    else:
        sampling = (
            f"{aperture.is_occupied.shape[0]}x{aperture.is_occupied.shape[1]} "
            f"at {aperture.spacing_nm} nm"
        )
        incident = "one admitted aperture; recorded component field"
        normalization = f"{aperture.site_count} occupied sites"
    return (
        ("aperture occupancy", f"sha256:{occupancy}"),
        ("physical sampling", sampling),
        ("focal coordinates", conclusion.focal_region_reference.content_hash),
        (
            "propagation distance",
            f"{float(conclusion.focus.expected_focus_m):.17g} m",
        ),
        ("incident field", incident),
        ("normalization", normalization),
    )


def _sampled_field(
    conclusion: PointwisePropagationResult | PointwiseGeometricResult,
    *,
    fetch: Fetch,
) -> Field:
    if isinstance(conclusion, PointwisePropagationResult):
        return form_pointwise_surface_field(
            conclusion.aperture,
            conclusion.surfaces,
            aperture_reference=conclusion.aperture_reference,
        )
    x_linear = restore_reference_surface(
        conclusion.transform.x_linear_response_reference,
        fetch,
    )
    y_linear = restore_reference_surface(
        conclusion.transform.y_linear_response_reference,
        fetch,
    )
    return form_geometric_surface_field(
        conclusion.aperture,
        conclusion.orientation_relation,
        x_linear,
        y_linear,
        conclusion.transform,
        aperture_reference=conclusion.aperture_reference,
        transform_reference=conclusion.transform_reference,
        device="cpu",
    )


def _vector_provenance(
    conclusion: PointwisePropagationResult | PointwiseGeometricResult,
    surfaces: tuple[Reference, ...],
) -> VectorFieldProvenance:
    return VectorFieldProvenance(
        component_names=("x", "y", "z"),
        rectilinear_surface_references=surfaces,
        formation="uniform",
        propagation="vector",
        longitudinal_power_reference=conclusion.focal_comparison_reference,
    )


__all__ = [
    "DiagnosticField",
    "DiagnosticFieldAssumptions",
    "FieldAssumptionDiagnostic",
    "VectorFieldProvenance",
    "diagnose_field_assumptions",
]
