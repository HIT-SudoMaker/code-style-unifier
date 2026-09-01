from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ...authority.protocol import Document, Reference
from ...authority.reference import reference_matches
from ...field.evidence import FIELD_SCHEMA
from ...field.reference_surface import restore_reference_surface

from ..result import EvidenceOrigin, ResultClosure
from ..study import Caution, Study

from .aperture import (
    APERTURE_SCHEMA,
    Aperture,
    reference_surface_cautions,
)
from . import achromatic
from .focal_field_comparison import (
    FOCAL_FIELD_COMPARISON_SCHEMA,
    FocalFieldComparison,
)
from .focus import (
    FOCAL_REGION_SCHEMA,
    FOCUS_SCHEMA,
    Focus,
    require_complete_focus,
    restore_focus,
)
from .geometric_phase import (
    CELL_CHOICE_SCHEMA,
    ORIENTATION_RELATION_SCHEMA,
    OrientationRelation,
)
from .pointwise import (
    CELL_SURFACE_TABLE_SCHEMA,
    GEOMETRIC_SURFACE_TRANSFORM_SCHEMA,
    CellSurfaceTable,
    GeometricSurfaceTransform,
    identify_geometric_surface_cautions,
)
from .propagation_phase import (
    CELL_LIBRARY_SCHEMA,
    PHASE_SET_SCHEMA,
    PhaseSet,
    PropagationCellLibrary,
)


RESULT_SCHEMA = "metacraft.science.metalens.result"
REPLAY_PROVENANCE = "authority"

Fetch = Callable[[Reference], bytes]


@dataclass(frozen=True, slots=True, kw_only=True)
class PropagationResult:
    """
    Closes one admitted quantized fabrication output and its focus.
    """

    phase_set: PhaseSet
    phase_set_reference: Reference
    aperture: Aperture
    aperture_reference: Reference
    field_reference: Reference
    focal_region_reference: Reference
    focus: Focus
    focus_reference: Reference
    closure: ResultClosure
    execution_origin: EvidenceOrigin

    def __post_init__(self) -> None:
        """
        Require one coherent quantized fabrication closure.
        """

        require_complete_focus(self.focus)
        if not self.phase_set.reference_matches(self.phase_set_reference):
            raise ValueError("phase_set_reference_mismatch")
        if (
            self.aperture.phase_levels is None
            or len(self.aperture.states) != self.phase_set.levels
            or self.phase_set_reference not in self.aperture.evidence
            or self.phase_set.binding_reference
            not in self.closure.bindings
        ):
            raise ValueError("propagation_fabrication_mismatch")

    @property
    def phase_level_count(self) -> int:
        """
        Return this result's explicit independent phase quantization.
        """

        return self.phase_set.levels

    @property
    def phase_set_identity(self) -> str:
        """
        Return the exact admitted phase-set identity.
        """

        return self.phase_set.identity

    def as_mapping(self) -> dict[str, object]:
        """
        Return six non-overlapping facts and no copied design authority.
        """

        return _result_mapping(
            fabrication={
                "aperture": self.aperture_reference,
                "phase_set": self.phase_set_reference,
            },
            aperture_reference=self.aperture_reference,
            field_reference=self.field_reference,
            focal_region_reference=self.focal_region_reference,
            focus_reference=self.focus_reference,
            closure=self.closure,
            execution_origin=self.execution_origin,
        )

    def document(self) -> Document:
        """
        Encode the exact replayable conclusion.
        """

        return Document(RESULT_SCHEMA, self.as_mapping())

    def references(self) -> tuple[Reference, ...]:
        """
        Name each direct fabrication, evaluation, and closure source once.
        """

        return (
            self.phase_set_reference,
            self.aperture_reference,
            self.field_reference,
            self.focal_region_reference,
            self.focus_reference,
            self.closure.study.reference,
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        closure: ResultClosure,
        fetch: Fetch,
    ) -> PropagationResult:
        """
        Restore a propagation conclusion without matching or propagation.
        """

        parts = _result_parts(document, closure)
        if set(parts.fabrication) != {"aperture", "phase_set"}:
            raise ValueError("propagation_fabrication_invalid")
        phase_reference = _reference(parts.fabrication["phase_set"])
        aperture_reference = _reference(parts.fabrication["aperture"])
        facts = _closure_facts(closure)
        _require_fact(facts, "phase_set", phase_reference, PHASE_SET_SCHEMA)
        _require_fact(
            facts,
            "aperture",
            aperture_reference,
            APERTURE_SCHEMA,
        )
        phase_set = PhaseSet.from_document(
            _fetch_document(fetch, phase_reference)
        )
        aperture = Aperture.from_document(
            _fetch_document(fetch, aperture_reference)
        )
        evaluation = _evaluation(parts, facts, fetch)
        origin = _origin(parts.origin)
        _validate_propagation_origin(
            fetch,
            facts,
            phase_set,
            origin,
        )
        restored = cls(
            phase_set=phase_set,
            phase_set_reference=phase_reference,
            aperture=aperture,
            aperture_reference=aperture_reference,
            field_reference=evaluation.field,
            focal_region_reference=evaluation.focal_region,
            focus=evaluation.focus,
            focus_reference=evaluation.focus_reference,
            closure=closure,
            execution_origin=origin,
        )
        if restored.document().to_bytes() != document.to_bytes():
            raise ValueError("propagation_result_document_mismatch")
        return restored


@dataclass(frozen=True, slots=True, kw_only=True)
class GeometricResult:
    """
    Closes one admitted continuous orientation output and its focus.
    """

    orientation_relation: OrientationRelation
    orientation_relation_reference: Reference
    choice_reference: Reference
    aperture: Aperture
    aperture_reference: Reference
    field_reference: Reference
    focal_region_reference: Reference
    focus: Focus
    focus_reference: Reference
    closure: ResultClosure
    execution_origin: EvidenceOrigin

    def __post_init__(self) -> None:
        """
        Require one coherent oriented fabrication closure.
        """

        require_complete_focus(self.focus)
        if not self.orientation_relation.reference_matches(
            self.orientation_relation_reference
        ):
            raise ValueError("orientations_reference_mismatch")
        if (
            self.aperture.phase_levels is not None
            or self.orientation_relation_reference
            not in self.aperture.evidence
            or self.choice_reference not in self.aperture.evidence
            or self.orientation_relation.binding_reference
            not in self.closure.bindings
        ):
            raise ValueError("geometric_fabrication_mismatch")

    @property
    def orientation_relation_identity(self) -> str:
        """
        Return the exact continuous orientation identity.
        """

        return self.orientation_relation.identity

    def as_mapping(self) -> dict[str, object]:
        """
        Return six non-overlapping facts and no copied design authority.
        """

        return _result_mapping(
            fabrication={
                "aperture": self.aperture_reference,
                "cell_choice": self.choice_reference,
                "orientations": self.orientation_relation_reference,
            },
            aperture_reference=self.aperture_reference,
            field_reference=self.field_reference,
            focal_region_reference=self.focal_region_reference,
            focus_reference=self.focus_reference,
            closure=self.closure,
            execution_origin=self.execution_origin,
        )

    def document(self) -> Document:
        """
        Encode the exact replayable conclusion.
        """

        return Document(RESULT_SCHEMA, self.as_mapping())

    def references(self) -> tuple[Reference, ...]:
        """
        Name each direct fabrication, evaluation, and closure source once.
        """

        return (
            self.orientation_relation_reference,
            self.choice_reference,
            self.aperture_reference,
            self.field_reference,
            self.focal_region_reference,
            self.focus_reference,
            self.closure.study.reference,
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        closure: ResultClosure,
        fetch: Fetch,
    ) -> GeometricResult:
        """
        Restore a geometric conclusion without deriving orientations again.
        """

        parts = _result_parts(document, closure)
        if set(parts.fabrication) != {
            "aperture",
            "cell_choice",
            "orientations",
        }:
            raise ValueError("geometric_fabrication_invalid")
        orientation_relation_reference = _reference(
            parts.fabrication["orientations"]
        )
        choice_reference = _reference(parts.fabrication["cell_choice"])
        aperture_reference = _reference(parts.fabrication["aperture"])
        facts = _closure_facts(closure)
        _require_fact(
            facts,
            "orientations",
            orientation_relation_reference,
            ORIENTATION_RELATION_SCHEMA,
        )
        _require_fact(
            facts,
            "cell_choice",
            choice_reference,
            CELL_CHOICE_SCHEMA,
        )
        _require_fact(
            facts,
            "aperture",
            aperture_reference,
            APERTURE_SCHEMA,
        )
        orientation_relation = OrientationRelation.from_document(
            _fetch_document(fetch, orientation_relation_reference)
        )
        aperture = Aperture.from_document(
            _fetch_document(fetch, aperture_reference)
        )
        evaluation = _evaluation(parts, facts, fetch)
        origin = _origin(parts.origin)
        _validate_geometric_choice(
            fetch,
            facts,
            orientation_relation,
            choice_reference,
            origin,
        )
        restored = cls(
            orientation_relation=orientation_relation,
            orientation_relation_reference=orientation_relation_reference,
            choice_reference=choice_reference,
            aperture=aperture,
            aperture_reference=aperture_reference,
            field_reference=evaluation.field,
            focal_region_reference=evaluation.focal_region,
            focus=evaluation.focus,
            focus_reference=evaluation.focus_reference,
            closure=closure,
            execution_origin=origin,
        )
        if restored.document().to_bytes() != document.to_bytes():
            raise ValueError("geometric_result_document_mismatch")
        return restored


@dataclass(frozen=True, slots=True, kw_only=True)
class PointwisePropagationResult:
    """
    Closes one full-library pointwise propagation output and its focus.
    """

    library: PropagationCellLibrary
    surfaces: CellSurfaceTable
    surfaces_reference: Reference
    aperture: Aperture
    aperture_reference: Reference
    field_reference: Reference
    focal_region_reference: Reference
    focus: Focus
    focus_reference: Reference
    focal_comparison: FocalFieldComparison
    focal_comparison_reference: Reference
    cautions: tuple[Caution, ...]
    closure: ResultClosure
    execution_origin: EvidenceOrigin

    def __post_init__(self) -> None:
        """
        Require one unquantized HCTA-derived result with exact rich evidence.
        """

        require_complete_focus(self.focus)
        if (
            self.aperture.phase_levels is not None
            or self.library.evidence_reference
            not in self.aperture.evidence
            or self.surfaces_reference not in self.aperture.evidence
            or not self.surfaces.reference_matches(
                self.surfaces_reference
            )
            or self.surfaces.source_reference
            != self.library.evidence_reference
            or self.library.binding_reference not in self.closure.bindings
            or self.focal_comparison.observed_field_reference
            != self.focal_region_reference
            or not {
                self.focal_comparison.observed_binding_reference,
                self.focal_comparison.ideal_binding_reference,
            }
            <= set(self.closure.bindings)
            or not self.cautions
        ):
            raise ValueError("pointwise_propagation_fabrication_mismatch")

    def as_mapping(self) -> dict[str, object]:
        """
        Return assignment, evaluation, cautions, and source provenance once.
        """

        values = _result_mapping(
            fabrication={
                "aperture": self.aperture_reference,
                "cell_library": self.library.evidence_reference,
                "cell_surface_table": self.surfaces_reference,
            },
            aperture_reference=self.aperture_reference,
            field_reference=self.field_reference,
            focal_region_reference=self.focal_region_reference,
            focus_reference=self.focus_reference,
            closure=self.closure,
            execution_origin=self.execution_origin,
            cautions=self.cautions,
        )
        evaluation = dict(_mapping(values["evaluation"], "result_invalid"))
        evaluation["focal_comparison"] = (
            self.focal_comparison_reference.as_mapping()
        )
        values["evaluation"] = evaluation
        return values

    def document(self) -> Document:
        """
        Encode the exact pointwise conclusion for execution-free replay.
        """

        return Document(RESULT_SCHEMA, self.as_mapping())

    def references(self) -> tuple[Reference, ...]:
        """
        Name every direct fabrication, evaluation, and limitation source.
        """

        return tuple(
            dict.fromkeys(
                (
                    self.library.evidence_reference,
                    self.surfaces_reference,
                    self.aperture_reference,
                    self.field_reference,
                    self.focal_region_reference,
                    self.focus_reference,
                    self.focal_comparison_reference,
                    *(item.source_reference for item in self.cautions),
                    self.closure.study.reference,
                )
            )
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        closure: ResultClosure,
        fetch: Fetch,
    ) -> PointwisePropagationResult:
        """
        Restore pointwise selection and comparisons without numerical work.
        """

        parts = _result_parts(document, closure)
        if set(parts.fabrication) != {
            "aperture",
            "cell_library",
            "cell_surface_table",
        }:
            raise ValueError("pointwise_propagation_fabrication_invalid")
        facts = _closure_facts(closure)
        library_reference = _reference(
            parts.fabrication["cell_library"]
        )
        surfaces_reference = _reference(
            parts.fabrication["cell_surface_table"]
        )
        aperture_reference = _reference(
            parts.fabrication["aperture"]
        )
        _require_fact(
            facts,
            "cell_library",
            library_reference,
            CELL_LIBRARY_SCHEMA,
        )
        _require_fact(
            facts,
            "cell_surface_table",
            surfaces_reference,
            CELL_SURFACE_TABLE_SCHEMA,
        )
        _require_fact(
            facts,
            "aperture",
            aperture_reference,
            APERTURE_SCHEMA,
        )
        library = _restore_library(
            fetch,
            facts,
            library_reference,
        )
        surfaces = CellSurfaceTable.from_document(
            _fetch_document(fetch, surfaces_reference),
            fetch=fetch,
        )
        aperture = Aperture.from_document(
            _fetch_document(fetch, aperture_reference)
        )
        evaluation = _evaluation(parts, facts, fetch)
        focal_comparison_reference, focal_comparison = _focal_comparison(
            parts,
            facts,
            fetch,
        )
        restored = cls(
            library=library,
            surfaces=surfaces,
            surfaces_reference=surfaces_reference,
            aperture=aperture,
            aperture_reference=aperture_reference,
            field_reference=evaluation.field,
            focal_region_reference=evaluation.focal_region,
            focus=evaluation.focus,
            focus_reference=evaluation.focus_reference,
            focal_comparison=focal_comparison,
            focal_comparison_reference=focal_comparison_reference,
            cautions=_cautions(
                parts,
                allowed_sources=frozenset(
                    surface.admitted.reference
                    for surface in surfaces.surfaces
                ),
            ),
            closure=closure,
            execution_origin=_origin(parts.origin),
        )
        if (
            restored.execution_origin is not library.responses[0].execution_origin
            or restored.document().to_bytes() != document.to_bytes()
        ):
            raise ValueError("pointwise_propagation_result_mismatch")
        return restored


@dataclass(frozen=True, slots=True, kw_only=True)
class PointwiseGeometricResult:
    """
    Closes one continuous geometric aperture and its qualified focal evidence.
    """

    orientation_relation: OrientationRelation
    orientation_relation_reference: Reference
    choice_reference: Reference
    transform: GeometricSurfaceTransform
    transform_reference: Reference
    aperture: Aperture
    aperture_reference: Reference
    field_reference: Reference
    focal_region_reference: Reference
    focus: Focus
    focus_reference: Reference
    focal_comparison: FocalFieldComparison
    focal_comparison_reference: Reference
    cautions: tuple[Caution, ...]
    closure: ResultClosure
    execution_origin: EvidenceOrigin

    def __post_init__(self) -> None:
        """
        Require one continuous orientation law and no manufactured levels.
        """

        require_complete_focus(self.focus)
        if (
            self.aperture.phase_levels is not None
            or not self.orientation_relation.reference_matches(
                self.orientation_relation_reference
            )
            or self.orientation_relation_reference
            not in self.aperture.evidence
            or self.choice_reference not in self.aperture.evidence
            or self.transform.orientation_relation_reference
            != self.orientation_relation_reference
            or not self.transform.reference_matches(
                self.transform_reference
            )
            or self.focal_comparison.observed_field_reference
            != self.focal_region_reference
            or not {
                self.focal_comparison.observed_binding_reference,
                self.focal_comparison.ideal_binding_reference,
            }
            <= set(self.closure.bindings)
            or not self.cautions
        ):
            raise ValueError("pointwise_geometric_fabrication_mismatch")

    def as_mapping(self) -> dict[str, object]:
        """
        Return one continuous fabrication and its qualified comparisons.
        """

        values = _result_mapping(
            fabrication={
                "aperture": self.aperture_reference,
                "cell_choice": self.choice_reference,
                "geometric_surface_transform": (
                    self.transform_reference
                ),
                "orientations": self.orientation_relation_reference,
            },
            aperture_reference=self.aperture_reference,
            field_reference=self.field_reference,
            focal_region_reference=self.focal_region_reference,
            focus_reference=self.focus_reference,
            closure=self.closure,
            execution_origin=self.execution_origin,
            cautions=self.cautions,
        )
        evaluation = dict(_mapping(values["evaluation"], "result_invalid"))
        evaluation["focal_comparison"] = (
            self.focal_comparison_reference.as_mapping()
        )
        values["evaluation"] = evaluation
        return values

    def document(self) -> Document:
        """
        Encode the exact continuous conclusion for execution-free replay.
        """

        return Document(RESULT_SCHEMA, self.as_mapping())

    def references(self) -> tuple[Reference, ...]:
        """
        Name every direct fabrication, evaluation, and limitation source.
        """

        return tuple(
            dict.fromkeys(
                (
                    self.orientation_relation_reference,
                    self.choice_reference,
                    self.transform_reference,
                    self.aperture_reference,
                    self.field_reference,
                    self.focal_region_reference,
                    self.focus_reference,
                    self.focal_comparison_reference,
                    *(item.source_reference for item in self.cautions),
                    self.closure.study.reference,
                )
            )
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        closure: ResultClosure,
        fetch: Fetch,
    ) -> PointwiseGeometricResult:
        """
        Restore continuous placement and comparisons without field execution.
        """

        parts = _result_parts(document, closure)
        if set(parts.fabrication) != {
            "aperture",
            "cell_choice",
            "geometric_surface_transform",
            "orientations",
        }:
            raise ValueError("pointwise_geometric_fabrication_invalid")
        facts = _closure_facts(closure)
        orientation_relation_reference = _reference(
            parts.fabrication["orientations"]
        )
        choice_reference = _reference(
            parts.fabrication["cell_choice"]
        )
        transform_reference = _reference(
            parts.fabrication["geometric_surface_transform"]
        )
        aperture_reference = _reference(
            parts.fabrication["aperture"]
        )
        _require_fact(
            facts,
            "orientations",
            orientation_relation_reference,
            ORIENTATION_RELATION_SCHEMA,
        )
        _require_fact(
            facts,
            "cell_choice",
            choice_reference,
            CELL_CHOICE_SCHEMA,
        )
        _require_fact(
            facts,
            "geometric_surface_transform",
            transform_reference,
            GEOMETRIC_SURFACE_TRANSFORM_SCHEMA,
        )
        _require_fact(
            facts,
            "aperture",
            aperture_reference,
            APERTURE_SCHEMA,
        )
        orientation_relation = OrientationRelation.from_document(
            _fetch_document(fetch, orientation_relation_reference)
        )
        transform = GeometricSurfaceTransform.from_document(
            _fetch_document(fetch, transform_reference)
        )
        aperture = Aperture.from_document(
            _fetch_document(fetch, aperture_reference)
        )
        evaluation = _evaluation(parts, facts, fetch)
        focal_comparison_reference, focal_comparison = _focal_comparison(
            parts,
            facts,
            fetch,
        )
        origin = _origin(parts.origin)
        _validate_geometric_choice(
            fetch,
            facts,
            orientation_relation,
            choice_reference,
            origin,
        )
        restored = cls(
            orientation_relation=orientation_relation,
            orientation_relation_reference=orientation_relation_reference,
            choice_reference=choice_reference,
            transform=transform,
            transform_reference=transform_reference,
            aperture=aperture,
            aperture_reference=aperture_reference,
            field_reference=evaluation.field,
            focal_region_reference=evaluation.focal_region,
            focus=evaluation.focus,
            focus_reference=evaluation.focus_reference,
            focal_comparison=focal_comparison,
            focal_comparison_reference=focal_comparison_reference,
            cautions=_cautions(
                parts,
                allowed_sources=frozenset(
                    (
                        transform_reference,
                        transform.x_linear_response_reference,
                        transform.y_linear_response_reference,
                    )
                ),
            ),
            closure=closure,
            execution_origin=origin,
        )
        if restored.document().to_bytes() != document.to_bytes():
            raise ValueError("pointwise_geometric_result_mismatch")
        return restored


@dataclass(frozen=True, slots=True, kw_only=True)
class AchromaticResult:
    """Close one immutable continuous-compensation layout and spectral focus."""

    qualification: achromatic.SpectralLibraryQualification
    qualification_reference: Reference
    aperture: achromatic.AchromaticAperture
    aperture_reference: Reference
    spectral_field_family: achromatic.SpectralFieldFamily
    spectral_field_family_reference: Reference
    focus: achromatic.AchromaticFocus
    focus_reference: Reference
    band_verification: achromatic.BandVerificationEvidence
    band_verification_reference: Reference
    closure: ResultClosure
    execution_origin: EvidenceOrigin

    def __post_init__(self) -> None:
        if (
            not self.qualification.is_candidate
            or self.aperture.qualification_reference != self.qualification_reference
            or self.aperture_reference
            != self.spectral_field_family.aperture_reference
            or self.qualification_reference
            != self.spectral_field_family.qualification_reference
            or self.aperture.library_reference
            != self.spectral_field_family.library_reference
            or self.spectral_field_family_reference
            != self.focus.spectral_field_family_reference
            or self.aperture.selection_binding_reference not in self.closure.bindings
            or self.spectral_field_family.propagation_binding_reference
            not in self.closure.bindings
            or self.focus.evaluation_binding_reference not in self.closure.bindings
            or not self.band_verification.is_pass
            or self.band_verification.aperture_reference != self.aperture_reference
            or self.band_verification.qualification_reference
            != self.qualification_reference
            or self.band_verification.spectral_field_family_reference
            != self.spectral_field_family_reference
            or self.band_verification.focus_reference != self.focus_reference
        ):
            raise ValueError("achromatic_result_mismatch")

    def as_mapping(self) -> dict[str, object]:
        """Encode fabrication, spectral evaluation, and conclusion once."""

        return {
            "closure": self.closure.study.reference.as_mapping(),
            "conclusion": {
                "band_verification": self.band_verification_reference.as_mapping(),
                "focus": self.focus_reference.as_mapping(),
            },
            "evaluation": {
                "spectral_field_family": (
                    self.spectral_field_family_reference.as_mapping()
                )
            },
            "evidence": _evidence_identities(self.closure),
            "fabrication": {
                "achromatic_aperture": self.aperture_reference.as_mapping(),
                "qualified_spectral_library": (
                    self.qualification_reference.as_mapping()
                ),
            },
            "origin": {"execution": self.execution_origin.value},
            "provenance": {"replay": REPLAY_PROVENANCE},
        }

    def document(self) -> Document:
        """Return the canonical replayable achromatic result document."""

        return Document(RESULT_SCHEMA, self.as_mapping())

    def references(self) -> tuple[Reference, ...]:
        """Return each direct scientific source exactly once."""

        return (
            self.qualification_reference,
            self.aperture_reference,
            self.spectral_field_family_reference,
            self.focus_reference,
            self.band_verification_reference,
            self.closure.study.reference,
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        closure: ResultClosure,
        fetch: Fetch,
    ) -> AchromaticResult:
        """Restore the continuous conclusion without numerical execution."""

        parts = _result_parts(document, closure)
        if set(parts.fabrication) != {
            "achromatic_aperture",
            "qualified_spectral_library",
        } or set(parts.evaluation) != {"spectral_field_family"}:
            raise ValueError("achromatic_result_shape_invalid")
        facts = _closure_facts(closure)
        qualification_reference = _reference(
            parts.fabrication["qualified_spectral_library"]
        )
        aperture_reference = _reference(
            parts.fabrication["achromatic_aperture"]
        )
        family_reference = _reference(
            parts.evaluation["spectral_field_family"]
        )
        focus_reference = _reference(parts.conclusion["focus"])
        band_verification_reference = _reference(
            parts.conclusion["band_verification"]
        )
        origin = _origin(parts.origin)
        restored = _restore_achromatic_result(
            closure,
            facts=facts,
            qualification_reference=qualification_reference,
            aperture_reference=aperture_reference,
            family_reference=family_reference,
            focus_reference=focus_reference,
            band_verification_reference=band_verification_reference,
            expected_origin=origin,
            fetch=fetch,
        )
        if restored.document().to_bytes() != document.to_bytes():
            raise ValueError("achromatic_result_document_mismatch")
        return restored


MetalensResult = (
    PropagationResult
    | GeometricResult
    | PointwisePropagationResult
    | PointwiseGeometricResult
    | AchromaticResult
)


def conclude(
    study: Study,
    closure: ResultClosure,
    *,
    fetch: Fetch,
) -> MetalensResult:
    """
    Validate complete admitted evidence and assemble one immutable result.
    """

    closure.validate(study)
    facts = {fact.claim: fact for fact in study.evidence}
    fact_shapes = {
        name: (fact.schema, fact.reference) for name, fact in facts.items()
    }
    if {
        "achromatic_aperture",
        "qualified_spectral_library",
        "spectral_field_family",
        "achromatic_focus",
        "focus",
    } <= set(facts):
        result: MetalensResult = _achromatic_result(
            closure,
            facts=fact_shapes,
            fetch=fetch,
        )
    elif not {"aperture", "field", "focal_region", "focus"}.issubset(facts):
        raise ValueError("result_evidence_incomplete")
    elif (
        {
            "cell_library",
            "cell_surface_table",
            "focal_comparison",
        }
        <= set(facts)
    ):
        result = _pointwise_propagation_result(
            closure,
            facts=fact_shapes,
            fetch=fetch,
        )
    elif (
        {
            "geometric_surface_transform",
            "focal_comparison",
            "orientations",
        }
        <= set(facts)
    ):
        result = _pointwise_geometric_result(
            closure,
            facts=fact_shapes,
            fetch=fetch,
        )
    elif (
        "phase_set" in facts
        and facts["phase_set"].schema == PHASE_SET_SCHEMA
    ):
        phase_reference = facts["phase_set"].reference
        phase_set = PhaseSet.from_document(
            _fetch_document(fetch, phase_reference)
        )
        result = _propagation_result(
            closure,
            facts=fact_shapes,
            phase_set=phase_set,
            phase_reference=phase_reference,
            fetch=fetch,
        )
    elif (
        "orientations" in facts
        and facts["orientations"].schema == ORIENTATION_RELATION_SCHEMA
    ):
        orientation_relation_reference = facts["orientations"].reference
        orientation_relation = OrientationRelation.from_document(
            _fetch_document(fetch, orientation_relation_reference)
        )
        result = _geometric_result(
            closure,
            facts=fact_shapes,
            orientation_relation=orientation_relation,
            orientation_relation_reference=orientation_relation_reference,
            fetch=fetch,
        )
    else:
        raise ValueError("result_fabrication_unknown")
    return result


def restore_result(
    document: Document,
    *,
    closure: ResultClosure,
    fetch: Fetch,
) -> MetalensResult:
    """
    Restore one typed result from its exact fabrication shape.
    """

    parts = _result_parts(document, closure)
    fabrication = set(parts.fabrication)
    if fabrication == {
        "achromatic_aperture",
        "qualified_spectral_library",
    }:
        restored: MetalensResult = AchromaticResult.from_document(
            document,
            closure=closure,
            fetch=fetch,
        )
    elif fabrication == {"aperture", "phase_set"}:
        restored = PropagationResult.from_document(
            document,
            closure=closure,
            fetch=fetch,
        )
    elif fabrication == {
        "aperture",
        "cell_choice",
        "orientations",
    }:
        restored = GeometricResult.from_document(
            document,
            closure=closure,
            fetch=fetch,
        )
    elif fabrication == {
        "aperture",
        "cell_library",
        "cell_surface_table",
    }:
        restored = PointwisePropagationResult.from_document(
            document,
            closure=closure,
            fetch=fetch,
        )
    elif fabrication == {
        "aperture",
        "cell_choice",
        "geometric_surface_transform",
        "orientations",
    }:
        restored = PointwiseGeometricResult.from_document(
            document,
            closure=closure,
            fetch=fetch,
        )
    else:
        raise ValueError("result_fabrication_unknown")
    if restored.document().to_bytes() != document.to_bytes():
        raise ValueError("result_replay_mismatch")
    return restored


def restore_conclusion(
    document: Document,
    *,
    fetch: Fetch,
) -> MetalensResult:
    """
    Restore one metalens conclusion and its admitted Study closure.
    """

    if document.schema_identifier != RESULT_SCHEMA:
        raise ValueError("result_schema_mismatch")
    values = _mapping(document.values, "result_document_invalid")
    closure_reference = _reference(values.get("closure"))
    closure = ResultClosure.restore(closure_reference, fetch=fetch)
    return restore_result(document, closure=closure, fetch=fetch)


@dataclass(frozen=True, slots=True)
class _ResultParts:
    fabrication: Mapping[str, object]
    evaluation: Mapping[str, object]
    conclusion: Mapping[str, object]
    origin: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class _Evaluation:
    field: Reference
    focal_region: Reference
    focus: Focus
    focus_reference: Reference


def _achromatic_result(
    closure: ResultClosure,
    *,
    facts: Mapping[str, tuple[str, Reference]],
    fetch: Fetch,
) -> AchromaticResult:
    qualification_reference = _fact(
        facts,
        "qualified_spectral_library",
        achromatic.QUALIFIED_SPECTRAL_LIBRARY_SCHEMA,
    )
    aperture_reference = _fact(
        facts,
        "achromatic_aperture",
        achromatic.ACHROMATIC_APERTURE_SCHEMA,
    )
    family_reference = _fact(
        facts,
        "spectral_field_family",
        achromatic.SPECTRAL_FIELD_FAMILY_SCHEMA,
    )
    focus_reference = _fact(
        facts,
        "achromatic_focus",
        achromatic.ACHROMATIC_FOCUS_SCHEMA,
    )
    band_verification_reference = _fact(
        facts,
        "focus",
        achromatic.BAND_VERIFICATION_EVIDENCE_SCHEMA,
    )
    return _restore_achromatic_result(
        closure,
        facts=facts,
        qualification_reference=qualification_reference,
        aperture_reference=aperture_reference,
        family_reference=family_reference,
        focus_reference=focus_reference,
        band_verification_reference=band_verification_reference,
        expected_origin=None,
        fetch=fetch,
    )


def _restore_achromatic_result(
    closure: ResultClosure,
    *,
    facts: Mapping[str, tuple[str, Reference]],
    qualification_reference: Reference,
    aperture_reference: Reference,
    family_reference: Reference,
    focus_reference: Reference,
    band_verification_reference: Reference,
    expected_origin: EvidenceOrigin | None,
    fetch: Fetch,
) -> AchromaticResult:
    """Restore the sole continuous closure used by conclusion and replay."""

    for claim, reference, schema in (
        ("qualified_spectral_library", qualification_reference, achromatic.QUALIFIED_SPECTRAL_LIBRARY_SCHEMA),
        ("achromatic_aperture", aperture_reference, achromatic.ACHROMATIC_APERTURE_SCHEMA),
        ("spectral_field_family", family_reference, achromatic.SPECTRAL_FIELD_FAMILY_SCHEMA),
        ("achromatic_focus", focus_reference, achromatic.ACHROMATIC_FOCUS_SCHEMA),
        ("focus", band_verification_reference, achromatic.BAND_VERIFICATION_EVIDENCE_SCHEMA),
    ):
        _require_fact(facts, claim, reference, schema)
    qualification = achromatic.SpectralLibraryQualification.from_document(
        _fetch_document(fetch, qualification_reference)
    )
    aperture = achromatic.AchromaticAperture.from_document(
        _fetch_document(fetch, aperture_reference)
    )
    family = achromatic.SpectralFieldFamily.from_document(
        _fetch_document(fetch, family_reference)
    )
    focus = achromatic.AchromaticFocus.from_document(
        _fetch_document(fetch, focus_reference)
    )
    band_verification = achromatic.BandVerificationEvidence.from_document(
        _fetch_document(fetch, band_verification_reference)
    )
    post_freeze = achromatic.PostFreezeJonesLibrary.from_document(
        _fetch_document(fetch, band_verification.post_freeze_library_reference)
    )
    library = achromatic.SpectralJonesLibrary.from_document(
        _fetch_document(fetch, qualification.library_reference)
    )
    origins = {
        item.execution_origin
        for item in (*library.observations, *post_freeze.observations)
    }
    if len(origins) != 1:
        raise ValueError("result_origin_mismatch")
    origin = origins.pop()
    if expected_origin is not None and origin is not expected_origin:
        raise ValueError("result_origin_mismatch")
    return AchromaticResult(
        qualification=qualification,
        qualification_reference=qualification_reference,
        aperture=aperture,
        aperture_reference=aperture_reference,
        spectral_field_family=family,
        spectral_field_family_reference=family_reference,
        focus=focus,
        focus_reference=focus_reference,
        band_verification=band_verification,
        band_verification_reference=band_verification_reference,
        closure=closure,
        execution_origin=origin,
    )


def _propagation_result(
    closure: ResultClosure,
    *,
    facts: Mapping[str, tuple[str, Reference]],
    phase_set: PhaseSet,
    phase_reference: Reference,
    fetch: Fetch,
) -> PropagationResult:
    aperture_reference = _fact(facts, "aperture", APERTURE_SCHEMA)
    aperture = Aperture.from_document(
        _fetch_document(fetch, aperture_reference)
    )
    evaluation = _evaluation_from_facts(facts, fetch)
    origin = _propagation_origin(fetch, facts, phase_set)
    return PropagationResult(
        phase_set=phase_set,
        phase_set_reference=phase_reference,
        aperture=aperture,
        aperture_reference=aperture_reference,
        field_reference=evaluation.field,
        focal_region_reference=evaluation.focal_region,
        focus=evaluation.focus,
        focus_reference=evaluation.focus_reference,
        closure=closure,
        execution_origin=origin,
    )


def _geometric_result(
    closure: ResultClosure,
    *,
    facts: Mapping[str, tuple[str, Reference]],
    orientation_relation: OrientationRelation,
    orientation_relation_reference: Reference,
    fetch: Fetch,
) -> GeometricResult:
    choice_reference = _fact(facts, "cell_choice", CELL_CHOICE_SCHEMA)
    aperture_reference = _fact(facts, "aperture", APERTURE_SCHEMA)
    aperture = Aperture.from_document(
        _fetch_document(fetch, aperture_reference)
    )
    evaluation = _evaluation_from_facts(facts, fetch)
    choice = _fetch_document(fetch, choice_reference)
    origin = _choice_origin(
        choice,
        orientation_relation,
        choice_reference=choice_reference,
        facts=facts,
    )
    return GeometricResult(
        orientation_relation=orientation_relation,
        orientation_relation_reference=orientation_relation_reference,
        choice_reference=choice_reference,
        aperture=aperture,
        aperture_reference=aperture_reference,
        field_reference=evaluation.field,
        focal_region_reference=evaluation.focal_region,
        focus=evaluation.focus,
        focus_reference=evaluation.focus_reference,
        closure=closure,
        execution_origin=origin,
    )


def _pointwise_propagation_result(
    closure: ResultClosure,
    *,
    facts: Mapping[str, tuple[str, Reference]],
    fetch: Fetch,
) -> PointwisePropagationResult:
    """
    Close one admitted full-library assignment without repeating selection.
    """

    library_reference = _fact(facts, "cell_library", CELL_LIBRARY_SCHEMA)
    surfaces_reference = _fact(
        facts,
        "cell_surface_table",
        CELL_SURFACE_TABLE_SCHEMA,
    )
    aperture_reference = _fact(facts, "aperture", APERTURE_SCHEMA)
    focal_comparison_reference = _fact(
        facts,
        "focal_comparison",
        FOCAL_FIELD_COMPARISON_SCHEMA,
    )
    library = _restore_library(fetch, facts, library_reference)
    surfaces = CellSurfaceTable.from_document(
        _fetch_document(fetch, surfaces_reference),
        fetch=fetch,
    )
    aperture = Aperture.from_document(
        _fetch_document(fetch, aperture_reference)
    )
    evaluation = _evaluation_from_facts(facts, fetch)
    focal_comparison = FocalFieldComparison.from_document(
        _fetch_document(fetch, focal_comparison_reference)
    )
    cautions = tuple(
        dict.fromkeys(
            caution
            for surface in surfaces.surfaces
            for caution in reference_surface_cautions(
                surface.admitted.response,
                surface.admitted.reference,
            )
        )
    )
    return PointwisePropagationResult(
        library=library,
        surfaces=surfaces,
        surfaces_reference=surfaces_reference,
        aperture=aperture,
        aperture_reference=aperture_reference,
        field_reference=evaluation.field,
        focal_region_reference=evaluation.focal_region,
        focus=evaluation.focus,
        focus_reference=evaluation.focus_reference,
        focal_comparison=focal_comparison,
        focal_comparison_reference=focal_comparison_reference,
        cautions=cautions,
        closure=closure,
        execution_origin=library.responses[0].execution_origin,
    )


def _pointwise_geometric_result(
    closure: ResultClosure,
    *,
    facts: Mapping[str, tuple[str, Reference]],
    fetch: Fetch,
) -> PointwiseGeometricResult:
    """
    Close one admitted continuous assignment without repeating rotation.
    """

    orientation_relation_reference = _fact(
        facts,
        "orientations",
        ORIENTATION_RELATION_SCHEMA,
    )
    choice_reference = _fact(facts, "cell_choice", CELL_CHOICE_SCHEMA)
    transform_reference = _fact(
        facts,
        "geometric_surface_transform",
        GEOMETRIC_SURFACE_TRANSFORM_SCHEMA,
    )
    aperture_reference = _fact(facts, "aperture", APERTURE_SCHEMA)
    focal_comparison_reference = _fact(
        facts,
        "focal_comparison",
        FOCAL_FIELD_COMPARISON_SCHEMA,
    )
    orientation_relation = OrientationRelation.from_document(
        _fetch_document(fetch, orientation_relation_reference)
    )
    transform = GeometricSurfaceTransform.from_document(
        _fetch_document(fetch, transform_reference)
    )
    aperture = Aperture.from_document(
        _fetch_document(fetch, aperture_reference)
    )
    evaluation = _evaluation_from_facts(facts, fetch)
    focal_comparison = FocalFieldComparison.from_document(
        _fetch_document(fetch, focal_comparison_reference)
    )
    x_linear = restore_reference_surface(
        transform.x_linear_response_reference,
        fetch,
    )
    y_linear = restore_reference_surface(
        transform.y_linear_response_reference,
        fetch,
    )
    choice = _fetch_document(fetch, choice_reference)
    origin = _choice_origin(
        choice,
        orientation_relation,
        choice_reference=choice_reference,
        facts=facts,
    )
    return PointwiseGeometricResult(
        orientation_relation=orientation_relation,
        orientation_relation_reference=orientation_relation_reference,
        choice_reference=choice_reference,
        transform=transform,
        transform_reference=transform_reference,
        aperture=aperture,
        aperture_reference=aperture_reference,
        field_reference=evaluation.field,
        focal_region_reference=evaluation.focal_region,
        focus=evaluation.focus,
        focus_reference=evaluation.focus_reference,
        focal_comparison=focal_comparison,
        focal_comparison_reference=focal_comparison_reference,
        cautions=identify_geometric_surface_cautions(
            transform,
            transform_reference,
            x_linear.response,
            y_linear.response,
        ),
        closure=closure,
        execution_origin=origin,
    )


def _result_mapping(
    *,
    fabrication: Mapping[str, Reference],
    aperture_reference: Reference,
    field_reference: Reference,
    focal_region_reference: Reference,
    focus_reference: Reference,
    closure: ResultClosure,
    execution_origin: EvidenceOrigin,
    cautions: tuple[Caution, ...] = (),
) -> dict[str, object]:
    if fabrication.get("aperture") != aperture_reference:
        raise ValueError("result_fabrication_invalid")
    return {
        "closure": closure.study.reference.as_mapping(),
        "conclusion": {
            "cautions": {
                f"caution_{index:03d}": caution.as_mapping()
                for index, caution in enumerate(cautions, start=1)
            },
            "focus": focus_reference.as_mapping(),
        },
        "evaluation": {
            "field": field_reference.as_mapping(),
            "focal_region": focal_region_reference.as_mapping(),
        },
        "evidence": _evidence_identities(closure),
        "fabrication": {
            name: reference.as_mapping()
            for name, reference in fabrication.items()
        },
        "origin": {"execution": execution_origin.value},
        "provenance": {"replay": REPLAY_PROVENANCE},
    }


def _evidence_identities(
    closure: ResultClosure,
) -> dict[str, dict[str, object]]:
    """
    Name each admitted fact once without a heterogeneous reference array.
    """

    identities = {
        fact.claim: fact.reference.as_mapping()
        for fact in closure.compiled.evidence
    }
    if {
        _reference(value) for value in identities.values()
    } != set(closure.evidence):
        raise ValueError("result_evidence_identity_mismatch")
    return identities


def _result_parts(
    document: Document,
    closure: ResultClosure,
) -> _ResultParts:
    if document.schema_identifier != RESULT_SCHEMA:
        raise ValueError("result_schema_mismatch")
    values = _mapping(document.values, "result_document_invalid")
    if set(values) != {
        "closure",
        "conclusion",
        "evidence",
        "evaluation",
        "fabrication",
        "origin",
        "provenance",
    }:
        raise ValueError("result_document_invalid")
    if _reference(values["closure"]) != closure.study.reference:
        raise ValueError("result_closure_mismatch")
    evidence = _mapping(
        values["evidence"],
        "result_evidence_identity_mismatch",
    )
    if evidence != _evidence_identities(closure):
        raise ValueError("result_evidence_identity_mismatch")
    provenance = _mapping(values["provenance"], "result_document_invalid")
    if provenance != {"replay": REPLAY_PROVENANCE}:
        raise ValueError("result_provenance_invalid")
    conclusion = _mapping(values["conclusion"], "result_document_invalid")
    evaluation = _mapping(values["evaluation"], "result_document_invalid")
    fabrication = _mapping(values["fabrication"], "result_document_invalid")
    origin = _mapping(values["origin"], "result_document_invalid")
    has_standard_evaluation = (
        {"field", "focal_region"} <= set(evaluation)
        and set(evaluation)
        <= {"field", "focal_comparison", "focal_region"}
    )
    has_achromatic_evaluation = set(evaluation) == {"spectral_field_family"}
    expected_conclusion = (
        {"focus", "band_verification"}
        if has_achromatic_evaluation
        else {"focus"}
    )
    if (
        not expected_conclusion <= set(conclusion)
        or not set(conclusion) <= {*expected_conclusion, "cautions"}
        or not (has_standard_evaluation or has_achromatic_evaluation)
        or set(origin) != {"execution"}
    ):
        raise ValueError("result_document_invalid")
    return _ResultParts(
        fabrication,
        evaluation,
        conclusion,
        origin,
    )


def _closure_facts(
    closure: ResultClosure,
) -> dict[str, tuple[str, Reference]]:
    facts = {
        fact.claim: (fact.schema, fact.reference)
        for fact in closure.compiled.evidence
    }
    if {
        reference for _, reference in facts.values()
    } != set(closure.evidence):
        raise ValueError("result_evidence_closure_mismatch")
    return facts


def _evaluation(
    parts: _ResultParts,
    facts: Mapping[str, tuple[str, Reference]],
    fetch: Fetch,
) -> _Evaluation:
    field_reference = _reference(parts.evaluation["field"])
    region_reference = _reference(parts.evaluation["focal_region"])
    focus_reference = _reference(parts.conclusion["focus"])
    _require_fact(facts, "field", field_reference, FIELD_SCHEMA)
    _require_fact(
        facts,
        "focal_region",
        region_reference,
        FOCAL_REGION_SCHEMA,
    )
    _require_fact(facts, "focus", focus_reference, FOCUS_SCHEMA)
    return _restore_evaluation(
        fetch,
        field_reference=field_reference,
        region_reference=region_reference,
        focus_reference=focus_reference,
    )


def _evaluation_from_facts(
    facts: Mapping[str, tuple[str, Reference]],
    fetch: Fetch,
) -> _Evaluation:
    return _restore_evaluation(
        fetch,
        field_reference=_fact(facts, "field", FIELD_SCHEMA),
        region_reference=_fact(
            facts,
            "focal_region",
            FOCAL_REGION_SCHEMA,
        ),
        focus_reference=_fact(facts, "focus", FOCUS_SCHEMA),
    )


def _focal_comparison(
    parts: _ResultParts,
    facts: Mapping[str, tuple[str, Reference]],
    fetch: Fetch,
) -> tuple[Reference, FocalFieldComparison]:
    raw_reference = parts.evaluation.get("focal_comparison")
    if raw_reference is None:
        raise ValueError("focal_comparison_evidence_missing")
    reference = _reference(raw_reference)
    _require_fact(
        facts,
        "focal_comparison",
        reference,
        FOCAL_FIELD_COMPARISON_SCHEMA,
    )
    focal_comparison = FocalFieldComparison.from_document(
        _fetch_document(fetch, reference)
    )
    return reference, focal_comparison


def _cautions(
    parts: _ResultParts,
    *,
    allowed_sources: frozenset[Reference],
) -> tuple[Caution, ...]:
    values = parts.conclusion.get("cautions")
    if not isinstance(values, Mapping) or not values:
        raise ValueError("result_cautions_invalid")
    if tuple(values) != tuple(
        f"caution_{index:03d}"
        for index in range(1, len(values) + 1)
    ):
        raise ValueError("result_cautions_invalid")
    cautions = []
    for value in values.values():
        caution = _mapping(value, "result_cautions_invalid")
        if set(caution) != {"concern", "explanation", "source"}:
            raise ValueError("result_cautions_invalid")
        concern = str(caution["concern"])
        explanation = str(caution["explanation"])
        if not concern or not explanation:
            raise ValueError("result_cautions_invalid")
        cautions.append(
            Caution(
                concern=concern,
                explanation=explanation,
                source_reference=_reference(caution["source"]),
            )
        )
    restored = tuple(cautions)
    if any(
        caution.source_reference not in allowed_sources
        for caution in restored
    ):
        raise ValueError("result_caution_source_unreachable")
    return restored


def _restore_library(
    fetch: Fetch,
    facts: Mapping[str, tuple[str, Reference]],
    reference: Reference,
) -> PropagationCellLibrary:
    document = _fetch_document(fetch, reference)
    values = _mapping(
        document.values,
        "propagation_library_document_invalid",
    )
    binding_reference = _reference(values.get("binding_reference"))
    height_reference = _reference(values.get("height_choice_reference"))
    if height_reference != _fact(facts, "height_choice"):
        raise ValueError("propagation_library_height_choice_mismatch")
    return PropagationCellLibrary.from_document(
        document,
        evidence_reference=reference,
        binding_reference=binding_reference,
        height_choice_reference=height_reference,
    )


def _restore_evaluation(
    fetch: Fetch,
    *,
    field_reference: Reference,
    region_reference: Reference,
    focus_reference: Reference,
) -> _Evaluation:
    field = _fetch_document(fetch, field_reference)
    region = _fetch_document(fetch, region_reference)
    focus_document = _fetch_document(fetch, focus_reference)
    if (
        field.schema_identifier != FIELD_SCHEMA
        or region.schema_identifier != FOCAL_REGION_SCHEMA
        or focus_document.schema_identifier != FOCUS_SCHEMA
        or _reference(focus_document.values.get("focal_region"))
        != region_reference
    ):
        raise ValueError("result_evaluation_mismatch")
    focus = restore_focus(focus_document)
    require_complete_focus(focus)
    return _Evaluation(
        field_reference,
        region_reference,
        focus,
        focus_reference,
    )


def _propagation_origin(
    fetch: Fetch,
    facts: Mapping[str, tuple[str, Reference]],
    phase_set: PhaseSet,
) -> EvidenceOrigin:
    library_reference = _fact(facts, "cell_library", CELL_LIBRARY_SCHEMA)
    if (
        phase_set.library_reference != library_reference
        or phase_set.height_choice_reference
        != _fact(facts, "height_choice")
    ):
        raise ValueError("phase_set_evidence_mismatch")
    library = PropagationCellLibrary.from_document(
        _fetch_document(fetch, library_reference),
        evidence_reference=library_reference,
        binding_reference=phase_set.binding_reference,
        height_choice_reference=phase_set.height_choice_reference,
    )
    return library.responses[0].execution_origin


def _validate_propagation_origin(
    fetch: Fetch,
    facts: Mapping[str, tuple[str, Reference]],
    phase_set: PhaseSet,
    origin: EvidenceOrigin,
) -> None:
    if _propagation_origin(fetch, facts, phase_set) is not origin:
        raise ValueError("result_origin_mismatch")


def _validate_geometric_choice(
    fetch: Fetch,
    facts: Mapping[str, tuple[str, Reference]],
    orientation_relation: OrientationRelation,
    choice_reference: Reference,
    origin: EvidenceOrigin,
) -> None:
    choice = _fetch_document(fetch, choice_reference)
    if (
        _choice_origin(
            choice,
            orientation_relation,
            choice_reference=choice_reference,
            facts=facts,
        )
        is not origin
    ):
        raise ValueError("result_origin_mismatch")


def _choice_origin(
    choice: Document,
    orientation_relation: OrientationRelation,
    *,
    choice_reference: Reference,
    facts: Mapping[str, tuple[str, Reference]],
) -> EvidenceOrigin:
    if choice.schema_identifier != CELL_CHOICE_SCHEMA:
        raise ValueError("cell_choice_schema_invalid")
    values = _mapping(choice.values, "cell_choice_document_invalid")
    cell = _mapping(values.get("cell"), "cell_choice_document_invalid")
    if (
        orientation_relation.cell_choice_reference != choice_reference
        or orientation_relation.cell_id != cell.get("identity")
        or orientation_relation.library_reference
        != _fact(facts, "jones_library")
        or orientation_relation.convention_reference
        != _fact(facts, "polarization_convention")
    ):
        raise ValueError("orientations_evidence_mismatch")
    try:
        return EvidenceOrigin(str(values["execution_origin"]))
    except (KeyError, ValueError) as error:
        raise ValueError("cell_choice_document_invalid") from error


def _origin(values: Mapping[str, object]) -> EvidenceOrigin:
    try:
        return EvidenceOrigin(str(values["execution"]))
    except (KeyError, ValueError) as error:
        raise ValueError("result_origin_invalid") from error


def _fact(
    facts: Mapping[str, tuple[str, Reference]],
    claim: str,
    schema: str | None = None,
) -> Reference:
    try:
        actual_schema, reference = facts[claim]
    except KeyError as error:
        raise ValueError(f"{claim}_evidence_missing") from error
    if schema is not None and actual_schema != schema:
        raise ValueError(f"{claim}_evidence_schema_mismatch")
    return reference


def _require_fact(
    facts: Mapping[str, tuple[str, Reference]],
    claim: str,
    reference: Reference,
    schema: str,
) -> None:
    if _fact(facts, claim, schema) != reference:
        raise ValueError(f"{claim}_reference_mismatch")


def _fetch_document(fetch: Fetch, reference: Reference) -> Document:
    try:
        body = fetch(reference)
    except (FileNotFoundError, RuntimeError) as error:
        raise ValueError("result_reference_missing") from error
    if not reference_matches(reference, body):
        raise ValueError("result_reference_mismatch")
    try:
        return Document.from_bytes(body)
    except ValueError as error:
        raise ValueError("result_document_invalid") from error


def _reference(value: object) -> Reference:
    mapping = _mapping(value, "result_reference_invalid")
    if set(mapping) != {
        "content_hash",
        "media_type",
        "metadata_content_hash",
        "size_bytes",
    }:
        raise ValueError("result_reference_invalid")
    try:
        return Reference.from_mapping(mapping)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("result_reference_invalid") from error


def _mapping(value: object, finding: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(finding)
    return value
