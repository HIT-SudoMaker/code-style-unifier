from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Generic, TypeVar

from metacraft.authority import Reference


class PublishedFactStatus(str, Enum):
    """Names one closed published-fact state."""

    REPORTED = "reported"
    DERIVED = "derived"
    NOT_REPORTED = "not reported"
    UNRESOLVED = "unresolved"


class AlignmentKind(str, Enum):
    """Names one closed brief-to-reference relation."""

    MATCHED = "matched"
    ADAPTED = "adapted"
    INDEPENDENT = "independent"
    WITHHELD = "withheld"
    EXCLUDED = "excluded"


class ComparisonRuleKind(str, Enum):
    """Names the only four comparison permissions."""

    SIGNED_DIFFERENCE = "signed difference"
    CONTEXT = "context"
    NOT_REPORTED = "not reported"
    NOT_APPLICABLE = "not applicable"


class BenchmarkSubject(str, Enum):
    """Names each blind-brief or withheld-reference concern."""

    WAVELENGTH = "wavelength"
    NUMERICAL_APERTURE = "numerical aperture"
    FOCAL_LENGTH = "focal length"
    INCIDENT_POLARIZATION = "incident polarization"
    CONTROL_STRATEGY = "control strategy"
    ATOM_SHAPE = "atom shape"
    ATOM_MATERIAL = "atom material"
    SUBSTRATE_MATERIAL = "substrate material"
    APERTURE = "aperture"
    ASPECT_LIMIT = "aspect limit"
    DIMENSION_STEP = "dimension step"
    FABRICATION_ROUTE = "fabrication route"
    CELL_PERIOD = "cell period"
    ATOM_HEIGHT = "atom height"
    LATERAL_GEOMETRY = "lateral geometry"


BENCHMARK_SUBJECT_FRAME = tuple(BenchmarkSubject)


class BenchmarkMeasure(str, Enum):
    """Names the fixed ordered design and Result observation frame."""

    CELL_PERIOD = "cell period"
    ATOM_HEIGHT = "atom height"
    LATERAL_GEOMETRY = "lateral geometry"
    PHASE_COVERAGE = "phase coverage"
    TRANSMITTED_MAGNITUDE = "transmitted magnitude"
    TRANSMITTED_POWER = "transmitted power"
    SPATIAL_PHASE_SAMPLING = "spatial phase sampling"
    ORIENTATION_RELATION = "orientation relation"
    POLARIZATION_CONVERSION = "polarization conversion"
    FOCUS_EFFICIENCY = "focus efficiency"
    FOCAL_SHIFT = "focal shift"
    X_HALF_MAXIMUM_WIDTH = "x half-maximum width"
    Y_HALF_MAXIMUM_WIDTH = "y half-maximum width"
    MEAN_HALF_MAXIMUM_WIDTH = "mean half-maximum width"
    VERTICAL_CUT_HALF_MAXIMUM_WIDTH = "vertical-cut half-maximum width"
    TRANSMITTED_FRACTION = "transmitted fraction"
    FOCUSED_FRACTION = "focused fraction"
    COMPLEX_FOCAL_FIELD = "complex focal field"
    LONGITUDINAL_POWER_FRACTION = "longitudinal power fraction"


BENCHMARK_MEASURE_FRAME = tuple(BenchmarkMeasure)


class ReferenceFactName(str, Enum):
    """Names each independently traceable reviewed-source fact."""

    WAVELENGTH = "wavelength"
    NUMERICAL_APERTURE = "numerical aperture"
    FOCAL_LENGTH = "focal length"
    INCIDENT_POLARIZATION = "incident polarization"
    CONTROL_STRATEGY = "control strategy"
    ATOM_SHAPE = "atom shape"
    ATOM_MATERIAL = "atom material"
    SUBSTRATE_MATERIAL = "substrate material"
    APERTURE = "aperture"
    CELL_PERIOD = "cell period"
    ATOM_HEIGHT = "atom height"
    LATERAL_GEOMETRY = "lateral geometry"
    FEATURE_ASPECT_RATIO = "feature aspect ratio"
    MINIMUM_FEATURE = "minimum feature"
    PHASE_COVERAGE = "phase coverage"
    TRANSMITTED_MAGNITUDE = "transmitted magnitude"
    TRANSMITTED_POWER = "transmitted power"
    SPATIAL_PHASE_SAMPLING = "spatial phase sampling"
    ORIENTATION_RELATION = "orientation relation"
    POLARIZATION_CONVERSION = "polarization conversion"
    FOCUS_EFFICIENCY = "focus efficiency"
    FOCAL_SHIFT = "focal shift"
    X_HALF_MAXIMUM_WIDTH = "x half-maximum width"
    Y_HALF_MAXIMUM_WIDTH = "y half-maximum width"
    MEAN_HALF_MAXIMUM_WIDTH = "mean half-maximum width"
    VERTICAL_CUT_HALF_MAXIMUM_WIDTH = "vertical-cut half-maximum width"
    TRANSMITTED_FRACTION = "transmitted fraction"
    FOCUSED_FRACTION = "focused fraction"
    COMPLEX_FOCAL_FIELD = "complex focal field"
    LONGITUDINAL_POWER_FRACTION = "longitudinal power fraction"


@dataclass(frozen=True, slots=True)
class SourceLocator:
    """Locates one fact in one exact reviewed primary source."""

    citation: str
    location: str

    def __post_init__(self) -> None:
        if not isinstance(self.citation, str) or not isinstance(self.location, str):
            raise TypeError("source_locator_type_invalid")
        if not self.citation.strip() or not self.location.strip():
            raise ValueError("source_locator_incomplete")


@dataclass(frozen=True, slots=True)
class PublishedQuantity:
    """Carries one finite published scalar with its unit."""

    value: Decimal
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal) or not isinstance(self.unit, str):
            raise TypeError("published_quantity_type_invalid")
        if not self.value.is_finite() or not self.unit.strip():
            raise ValueError("published_quantity_invalid")


@dataclass(frozen=True, slots=True)
class MeasureMeaning:
    """Carries all semantics required before a numeric comparison."""

    unit: str
    scope: str
    normalization: str
    definition: str

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, str)
            for value in (
                self.unit,
                self.scope,
                self.normalization,
                self.definition,
            )
        ):
            raise TypeError("measure_meaning_type_invalid")
        if not all(
            value.strip()
            for value in (
                self.unit,
                self.scope,
                self.normalization,
                self.definition,
            )
        ):
            raise ValueError("measure_meaning_incomplete")


FactValue = TypeVar("FactValue", covariant=True)


@dataclass(frozen=True, slots=True)
class ReportedFact(Generic[FactValue]):
    """Carries one value directly stated by a reviewed source."""

    key: ReferenceFactName
    value: FactValue
    meaning: str
    sources: tuple[SourceLocator, ...]
    measure_meaning: MeasureMeaning | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key, ReferenceFactName)
            or not isinstance(self.meaning, str)
            or not isinstance(self.sources, tuple)
            or any(not isinstance(source, SourceLocator) for source in self.sources)
            or (
                self.measure_meaning is not None
                and not isinstance(self.measure_meaning, MeasureMeaning)
            )
        ):
            raise TypeError("reported_fact_type_invalid")
        if not self.meaning.strip():
            raise ValueError("reported_fact_meaning_missing")
        if not self.sources:
            raise ValueError("reported_fact_source_missing")

    @property
    def status(self) -> PublishedFactStatus:
        return PublishedFactStatus.REPORTED


@dataclass(frozen=True, slots=True)
class DerivedFact(Generic[FactValue]):
    """Carries one value derived from cited published inputs."""

    key: ReferenceFactName
    value: FactValue
    meaning: str
    sources: tuple[SourceLocator, ...]
    expression: str
    inputs: tuple[ReferenceFactName, ...]
    measure_meaning: MeasureMeaning | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key, ReferenceFactName)
            or not isinstance(self.meaning, str)
            or not isinstance(self.sources, tuple)
            or any(not isinstance(source, SourceLocator) for source in self.sources)
            or not isinstance(self.expression, str)
            or not isinstance(self.inputs, tuple)
            or any(not isinstance(item, ReferenceFactName) for item in self.inputs)
            or (
                self.measure_meaning is not None
                and not isinstance(self.measure_meaning, MeasureMeaning)
            )
        ):
            raise TypeError("derived_fact_type_invalid")
        if not self.meaning.strip() or not self.expression.strip():
            raise ValueError("derived_fact_meaning_missing")
        if not self.sources or not self.inputs:
            raise ValueError("derived_fact_basis_missing")

    @property
    def status(self) -> PublishedFactStatus:
        return PublishedFactStatus.DERIVED


@dataclass(frozen=True, slots=True)
class NotReportedFact:
    """States that a reviewed source does not report one fact."""

    key: ReferenceFactName
    meaning: str
    reviewed_sources: tuple[SourceLocator, ...]
    reason: str
    measure_meaning: MeasureMeaning | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key, ReferenceFactName)
            or not isinstance(self.meaning, str)
            or not isinstance(self.reviewed_sources, tuple)
            or any(
                not isinstance(source, SourceLocator)
                for source in self.reviewed_sources
            )
            or not isinstance(self.reason, str)
            or (
                self.measure_meaning is not None
                and not isinstance(self.measure_meaning, MeasureMeaning)
            )
        ):
            raise TypeError("not_reported_fact_type_invalid")
        if (
            not self.meaning.strip()
            or not self.reason.strip()
            or not self.reviewed_sources
        ):
            raise ValueError("not_reported_fact_basis_missing")

    @property
    def status(self) -> PublishedFactStatus:
        return PublishedFactStatus.NOT_REPORTED

    @property
    def value(self) -> None:
        return None


@dataclass(frozen=True, slots=True)
class UnresolvedFact:
    """States that reviewed sources cannot yet establish one fact."""

    key: ReferenceFactName
    meaning: str
    reviewed_sources: tuple[SourceLocator, ...]
    reason: str
    measure_meaning: MeasureMeaning | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key, ReferenceFactName)
            or not isinstance(self.meaning, str)
            or not isinstance(self.reviewed_sources, tuple)
            or any(
                not isinstance(source, SourceLocator)
                for source in self.reviewed_sources
            )
            or not isinstance(self.reason, str)
            or (
                self.measure_meaning is not None
                and not isinstance(self.measure_meaning, MeasureMeaning)
            )
        ):
            raise TypeError("unresolved_fact_type_invalid")
        if (
            not self.meaning.strip()
            or not self.reason.strip()
            or not self.reviewed_sources
        ):
            raise ValueError("unresolved_fact_basis_missing")

    @property
    def status(self) -> PublishedFactStatus:
        return PublishedFactStatus.UNRESOLVED

    @property
    def value(self) -> None:
        return None


PublishedFact = ReportedFact[object] | DerivedFact[object] | NotReportedFact | UnresolvedFact


@dataclass(frozen=True, slots=True)
class PublishedReference:
    """Owns one selected publication object and its reviewed facts."""

    citation: str
    selected_device: str
    facts: tuple[PublishedFact, ...]
    exclusions: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.citation, str)
            or not isinstance(self.selected_device, str)
            or not isinstance(self.facts, tuple)
            or any(
                not isinstance(
                    fact,
                    (ReportedFact, DerivedFact, NotReportedFact, UnresolvedFact),
                )
                for fact in self.facts
            )
            or not isinstance(self.exclusions, tuple)
            or any(not isinstance(exclusion, str) for exclusion in self.exclusions)
        ):
            raise TypeError("published_reference_type_invalid")
        if not self.citation.strip() or not self.selected_device.strip():
            raise ValueError("published_reference_identity_incomplete")
        facts = tuple(sorted(self.facts, key=lambda fact: fact.key.value))
        if not facts or len({fact.key for fact in facts}) != len(facts):
            raise ValueError("published_reference_fact_invalid")
        exclusions = tuple(sorted(self.exclusions))
        if (
            len(set(exclusions)) != len(exclusions)
            or any(not exclusion.strip() for exclusion in exclusions)
        ):
            raise ValueError("published_reference_exclusion_invalid")
        object.__setattr__(self, "facts", facts)
        object.__setattr__(self, "exclusions", exclusions)

    def fact(self, key: ReferenceFactName) -> PublishedFact:
        """Return one exact fact without a free-form lookup key."""

        if not isinstance(key, ReferenceFactName):
            raise TypeError("reference_fact_name_required")
        for fact in self.facts:
            if fact.key is key:
                return fact
        raise ValueError("published_reference_fact_missing")


@dataclass(frozen=True, slots=True)
class MatchedAlignment:
    subject: BenchmarkSubject
    fact: ReferenceFactName

    def __post_init__(self) -> None:
        if not isinstance(self.subject, BenchmarkSubject) or not isinstance(
            self.fact,
            ReferenceFactName,
        ):
            raise TypeError("matched_alignment_type_invalid")

    @property
    def kind(self) -> AlignmentKind:
        return AlignmentKind.MATCHED


@dataclass(frozen=True, slots=True)
class AdaptedAlignment:
    subject: BenchmarkSubject
    fact: ReferenceFactName
    rationale: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.subject, BenchmarkSubject)
            or not isinstance(self.fact, ReferenceFactName)
            or not isinstance(self.rationale, str)
        ):
            raise TypeError("adapted_alignment_type_invalid")
        if not self.rationale.strip():
            raise ValueError("adapted_alignment_rationale_missing")

    @property
    def kind(self) -> AlignmentKind:
        return AlignmentKind.ADAPTED


@dataclass(frozen=True, slots=True)
class IndependentAlignment:
    subject: BenchmarkSubject
    rationale: str

    def __post_init__(self) -> None:
        if not isinstance(self.subject, BenchmarkSubject) or not isinstance(
            self.rationale,
            str,
        ):
            raise TypeError("independent_alignment_type_invalid")
        if not self.rationale.strip():
            raise ValueError("independent_alignment_rationale_missing")

    @property
    def kind(self) -> AlignmentKind:
        return AlignmentKind.INDEPENDENT


@dataclass(frozen=True, slots=True)
class WithheldAlignment:
    subject: BenchmarkSubject
    fact: ReferenceFactName

    def __post_init__(self) -> None:
        if not isinstance(self.subject, BenchmarkSubject) or not isinstance(
            self.fact,
            ReferenceFactName,
        ):
            raise TypeError("withheld_alignment_type_invalid")

    @property
    def kind(self) -> AlignmentKind:
        return AlignmentKind.WITHHELD


@dataclass(frozen=True, slots=True)
class ExcludedAlignment:
    subject: BenchmarkSubject
    rationale: str

    def __post_init__(self) -> None:
        if not isinstance(self.subject, BenchmarkSubject) or not isinstance(
            self.rationale,
            str,
        ):
            raise TypeError("excluded_alignment_type_invalid")
        if not self.rationale.strip():
            raise ValueError("excluded_alignment_rationale_missing")

    @property
    def kind(self) -> AlignmentKind:
        return AlignmentKind.EXCLUDED


Alignment = (
    MatchedAlignment
    | AdaptedAlignment
    | IndependentAlignment
    | WithheldAlignment
    | ExcludedAlignment
)


@dataclass(frozen=True, slots=True)
class BenchmarkAlignment:
    """Owns exactly one relation for every fixed benchmark subject."""

    relations: tuple[Alignment, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.relations, tuple) or any(
            not isinstance(
                relation,
                (
                    MatchedAlignment,
                    AdaptedAlignment,
                    IndependentAlignment,
                    WithheldAlignment,
                    ExcludedAlignment,
                ),
            )
            for relation in self.relations
        ):
            raise TypeError("benchmark_alignment_type_invalid")
        if tuple(relation.subject for relation in self.relations) != (
            BENCHMARK_SUBJECT_FRAME
        ):
            raise ValueError("benchmark_alignment_frame_invalid")

    def relation(self, subject: BenchmarkSubject) -> Alignment:
        """Return one relation through the closed subject vocabulary."""

        if not isinstance(subject, BenchmarkSubject):
            raise TypeError("benchmark_subject_required")
        return self.relations[BENCHMARK_SUBJECT_FRAME.index(subject)]


ComparableFact = ReportedFact[object] | DerivedFact[object]
ContextFact = ComparableFact | UnresolvedFact


@dataclass(frozen=True, slots=True)
class SignedDifferenceRule:
    measure: BenchmarkMeasure
    fact: ReferenceFactName
    required_matched_subjects: tuple[BenchmarkSubject, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.measure, BenchmarkMeasure)
            or not isinstance(self.fact, ReferenceFactName)
            or not isinstance(self.required_matched_subjects, tuple)
            or any(
                not isinstance(subject, BenchmarkSubject)
                for subject in self.required_matched_subjects
            )
        ):
            raise TypeError("signed_difference_rule_type_invalid")
        if not self.required_matched_subjects:
            raise ValueError("signed_difference_required_matches_missing")
        if self.measure.value != self.fact.value:
            raise ValueError("signed_difference_measure_fact_mismatch")

    @property
    def kind(self) -> ComparisonRuleKind:
        return ComparisonRuleKind.SIGNED_DIFFERENCE


@dataclass(frozen=True, slots=True)
class ContextRule:
    measure: BenchmarkMeasure
    fact: ReferenceFactName
    rationale: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.measure, BenchmarkMeasure)
            or not isinstance(self.fact, ReferenceFactName)
            or not isinstance(self.rationale, str)
        ):
            raise TypeError("context_rule_type_invalid")
        if not self.rationale.strip():
            raise ValueError("context_rule_rationale_missing")

    @property
    def kind(self) -> ComparisonRuleKind:
        return ComparisonRuleKind.CONTEXT


@dataclass(frozen=True, slots=True)
class NotReportedRule:
    measure: BenchmarkMeasure
    fact: ReferenceFactName

    def __post_init__(self) -> None:
        if not isinstance(self.measure, BenchmarkMeasure) or not isinstance(
            self.fact,
            ReferenceFactName,
        ):
            raise TypeError("not_reported_rule_type_invalid")

    @property
    def kind(self) -> ComparisonRuleKind:
        return ComparisonRuleKind.NOT_REPORTED


@dataclass(frozen=True, slots=True)
class NotApplicableRule:
    measure: BenchmarkMeasure
    rationale: str

    def __post_init__(self) -> None:
        if not isinstance(self.measure, BenchmarkMeasure) or not isinstance(
            self.rationale,
            str,
        ):
            raise TypeError("not_applicable_rule_type_invalid")
        if not self.rationale.strip():
            raise ValueError("not_applicable_rule_rationale_missing")

    @property
    def kind(self) -> ComparisonRuleKind:
        return ComparisonRuleKind.NOT_APPLICABLE


ComparisonRule = (
    SignedDifferenceRule | ContextRule | NotReportedRule | NotApplicableRule
)


@dataclass(frozen=True, slots=True)
class ResultQuantityMeasure:
    """Carries one finite scalar restored from an admitted Result."""

    value: Decimal
    meaning: MeasureMeaning
    source_references: tuple[Reference, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, Decimal)
            or not isinstance(self.meaning, MeasureMeaning)
            or not isinstance(self.source_references, tuple)
            or any(
                not isinstance(reference, Reference)
                for reference in self.source_references
            )
        ):
            raise TypeError("result_quantity_measure_type_invalid")
        if not self.source_references:
            raise ValueError("result_quantity_measure_references_missing")
        if not self.value.is_finite():
            raise ValueError("result_quantity_invalid")


@dataclass(frozen=True, slots=True)
class ResultRangeMeasure:
    """Carries one finite observed range without inventing a scalar."""

    minimum: Decimal
    maximum: Decimal
    meaning: MeasureMeaning
    source_references: tuple[Reference, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.minimum, Decimal)
            or not isinstance(self.maximum, Decimal)
            or not isinstance(self.meaning, MeasureMeaning)
            or not isinstance(self.source_references, tuple)
            or any(
                not isinstance(reference, Reference)
                for reference in self.source_references
            )
        ):
            raise TypeError("result_range_measure_type_invalid")
        if not self.source_references:
            raise ValueError("result_range_measure_references_missing")
        if (
            not self.minimum.is_finite()
            or not self.maximum.is_finite()
            or self.maximum < self.minimum
        ):
            raise ValueError("result_range_invalid")


@dataclass(frozen=True, slots=True)
class ResultTextMeasure:
    """Carries one typed qualitative Result observation."""

    value: str
    definition: str
    source_references: tuple[Reference, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or not isinstance(self.definition, str)
            or not isinstance(self.source_references, tuple)
            or any(
                not isinstance(reference, Reference)
                for reference in self.source_references
            )
        ):
            raise TypeError("result_text_measure_type_invalid")
        if not self.source_references:
            raise ValueError("result_text_measure_references_missing")
        if not self.value.strip() or not self.definition.strip():
            raise ValueError("result_text_measure_invalid")


@dataclass(frozen=True, slots=True)
class CircleGeometryRange:
    minimum_diameter_nm: int
    maximum_diameter_nm: int

    def __post_init__(self) -> None:
        if type(self.minimum_diameter_nm) is not int or type(
            self.maximum_diameter_nm
        ) is not int:
            raise TypeError("circle_geometry_range_type_invalid")
        if (
            self.minimum_diameter_nm <= 0
            or self.maximum_diameter_nm < self.minimum_diameter_nm
        ):
            raise ValueError("circle_geometry_range_invalid")


@dataclass(frozen=True, slots=True)
class SquareGeometryRange:
    minimum_width_nm: int
    maximum_width_nm: int

    def __post_init__(self) -> None:
        if type(self.minimum_width_nm) is not int or type(
            self.maximum_width_nm
        ) is not int:
            raise TypeError("square_geometry_range_type_invalid")
        if (
            self.minimum_width_nm <= 0
            or self.maximum_width_nm < self.minimum_width_nm
        ):
            raise ValueError("square_geometry_range_invalid")


@dataclass(frozen=True, slots=True)
class RectangleGeometryRange:
    minimum_short_side_nm: int
    maximum_short_side_nm: int
    minimum_long_side_nm: int
    maximum_long_side_nm: int

    def __post_init__(self) -> None:
        values = (
            self.minimum_short_side_nm,
            self.maximum_short_side_nm,
            self.minimum_long_side_nm,
            self.maximum_long_side_nm,
        )
        if any(type(value) is not int for value in values):
            raise TypeError("rectangle_geometry_range_type_invalid")
        if (
            any(value <= 0 for value in values)
            or self.maximum_short_side_nm < self.minimum_short_side_nm
            or self.maximum_long_side_nm < self.minimum_long_side_nm
        ):
            raise ValueError("rectangle_geometry_range_invalid")


@dataclass(frozen=True, slots=True)
class EllipseGeometryRange:
    minimum_minor_axis_nm: int
    maximum_minor_axis_nm: int
    minimum_major_axis_nm: int
    maximum_major_axis_nm: int

    def __post_init__(self) -> None:
        values = (
            self.minimum_minor_axis_nm,
            self.maximum_minor_axis_nm,
            self.minimum_major_axis_nm,
            self.maximum_major_axis_nm,
        )
        if any(type(value) is not int for value in values):
            raise TypeError("ellipse_geometry_range_type_invalid")
        if (
            any(value <= 0 for value in values)
            or self.maximum_minor_axis_nm < self.minimum_minor_axis_nm
            or self.maximum_major_axis_nm < self.minimum_major_axis_nm
        ):
            raise ValueError("ellipse_geometry_range_invalid")


ResultGeometry = (
    CircleGeometryRange
    | SquareGeometryRange
    | RectangleGeometryRange
    | EllipseGeometryRange
)


@dataclass(frozen=True, slots=True)
class ResultGeometryMeasure:
    """Carries one closed natural-geometry range from an aperture."""

    geometry: ResultGeometry
    source_references: tuple[Reference, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.geometry,
            (
                CircleGeometryRange,
                SquareGeometryRange,
                RectangleGeometryRange,
                EllipseGeometryRange,
            ),
        ):
            raise TypeError("result_geometry_measure_geometry_invalid")
        if not isinstance(self.source_references, tuple) or any(
            not isinstance(reference, Reference)
            for reference in self.source_references
        ):
            raise TypeError("result_geometry_measure_references_invalid")
        if not self.source_references:
            raise ValueError("result_geometry_measure_references_missing")


@dataclass(frozen=True, slots=True)
class ResultMeasureUnavailable:
    """States why one fixed-frame observation is absent from this Result."""

    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.reason, str):
            raise TypeError("result_measure_absence_type_invalid")
        if not self.reason.strip():
            raise ValueError("result_measure_absence_invalid")


ResultMeasure = (
    ResultQuantityMeasure
    | ResultRangeMeasure
    | ResultTextMeasure
    | ResultGeometryMeasure
    | ResultMeasureUnavailable
)


@dataclass(frozen=True, slots=True)
class BenchmarkResultMeasures:
    """Owns the complete fixed frame restored from one admitted Result."""

    cell_period: ResultMeasure
    atom_height: ResultMeasure
    lateral_geometry: ResultMeasure
    phase_coverage: ResultMeasure
    transmitted_magnitude: ResultMeasure
    transmitted_power: ResultMeasure
    spatial_phase_sampling: ResultMeasure
    orientation_relation: ResultMeasure
    polarization_conversion: ResultMeasure
    focus_efficiency: ResultMeasure
    focal_shift: ResultMeasure
    x_half_maximum_width: ResultMeasure
    y_half_maximum_width: ResultMeasure
    mean_half_maximum_width: ResultMeasure
    vertical_cut_half_maximum_width: ResultMeasure
    transmitted_fraction: ResultMeasure
    focused_fraction: ResultMeasure
    complex_focal_field: ResultMeasure
    longitudinal_power_fraction: ResultMeasure

    def __post_init__(self) -> None:
        values = (
            self.cell_period,
            self.atom_height,
            self.lateral_geometry,
            self.phase_coverage,
            self.transmitted_magnitude,
            self.transmitted_power,
            self.spatial_phase_sampling,
            self.orientation_relation,
            self.polarization_conversion,
            self.focus_efficiency,
            self.focal_shift,
            self.x_half_maximum_width,
            self.y_half_maximum_width,
            self.mean_half_maximum_width,
            self.vertical_cut_half_maximum_width,
            self.transmitted_fraction,
            self.focused_fraction,
            self.complex_focal_field,
            self.longitudinal_power_fraction,
        )
        if any(
            not isinstance(
                value,
                (
                    ResultQuantityMeasure,
                    ResultRangeMeasure,
                    ResultTextMeasure,
                    ResultGeometryMeasure,
                    ResultMeasureUnavailable,
                ),
            )
            for value in values
        ):
            raise TypeError("benchmark_result_measure_type_invalid")

    def measure_for(self, measure: BenchmarkMeasure) -> ResultMeasure:
        """Return one typed member through one exhaustive enum dispatch."""

        if not isinstance(measure, BenchmarkMeasure):
            raise TypeError("benchmark_measure_required")
        match measure:
            case BenchmarkMeasure.CELL_PERIOD:
                return self.cell_period
            case BenchmarkMeasure.ATOM_HEIGHT:
                return self.atom_height
            case BenchmarkMeasure.LATERAL_GEOMETRY:
                return self.lateral_geometry
            case BenchmarkMeasure.PHASE_COVERAGE:
                return self.phase_coverage
            case BenchmarkMeasure.TRANSMITTED_MAGNITUDE:
                return self.transmitted_magnitude
            case BenchmarkMeasure.TRANSMITTED_POWER:
                return self.transmitted_power
            case BenchmarkMeasure.SPATIAL_PHASE_SAMPLING:
                return self.spatial_phase_sampling
            case BenchmarkMeasure.ORIENTATION_RELATION:
                return self.orientation_relation
            case BenchmarkMeasure.POLARIZATION_CONVERSION:
                return self.polarization_conversion
            case BenchmarkMeasure.FOCUS_EFFICIENCY:
                return self.focus_efficiency
            case BenchmarkMeasure.FOCAL_SHIFT:
                return self.focal_shift
            case BenchmarkMeasure.X_HALF_MAXIMUM_WIDTH:
                return self.x_half_maximum_width
            case BenchmarkMeasure.Y_HALF_MAXIMUM_WIDTH:
                return self.y_half_maximum_width
            case BenchmarkMeasure.MEAN_HALF_MAXIMUM_WIDTH:
                return self.mean_half_maximum_width
            case BenchmarkMeasure.VERTICAL_CUT_HALF_MAXIMUM_WIDTH:
                return self.vertical_cut_half_maximum_width
            case BenchmarkMeasure.TRANSMITTED_FRACTION:
                return self.transmitted_fraction
            case BenchmarkMeasure.FOCUSED_FRACTION:
                return self.focused_fraction
            case BenchmarkMeasure.COMPLEX_FOCAL_FIELD:
                return self.complex_focal_field
            case BenchmarkMeasure.LONGITUDINAL_POWER_FRACTION:
                return self.longitudinal_power_fraction
        raise AssertionError("benchmark_measure_dispatch_unreachable")


@dataclass(frozen=True, slots=True)
class ComparableMeasureComparison:
    """Carries the only comparison form permitted to hold a difference."""

    measure: BenchmarkMeasure
    observed: ResultQuantityMeasure
    reference: ComparableFact
    signed_difference: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.measure, BenchmarkMeasure)
            or not isinstance(self.observed, ResultQuantityMeasure)
            or not isinstance(self.reference, (ReportedFact, DerivedFact))
            or not isinstance(self.signed_difference, Decimal)
        ):
            raise TypeError("comparable_measure_comparison_type_invalid")
        if (
            not self.signed_difference.is_finite()
            or not isinstance(self.reference.value, PublishedQuantity)
            or self.reference.measure_meaning is None
            or self.observed.meaning != self.reference.measure_meaning
            or self.signed_difference
            != self.observed.value - self.reference.value.value
        ):
            raise ValueError("comparable_difference_invalid")


@dataclass(frozen=True, slots=True)
class ContextMeasureComparison:
    measure: BenchmarkMeasure
    observed: ResultMeasure
    reference: ContextFact
    rationale: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.measure, BenchmarkMeasure)
            or not isinstance(
                self.observed,
                (
                    ResultQuantityMeasure,
                    ResultRangeMeasure,
                    ResultTextMeasure,
                    ResultGeometryMeasure,
                    ResultMeasureUnavailable,
                ),
            )
            or not isinstance(
                self.reference,
                (ReportedFact, DerivedFact, UnresolvedFact),
            )
            or not isinstance(self.rationale, str)
        ):
            raise TypeError("context_measure_comparison_type_invalid")
        if not self.rationale.strip():
            raise ValueError("context_measure_comparison_rationale_missing")


@dataclass(frozen=True, slots=True)
class NotReportedMeasureComparison:
    measure: BenchmarkMeasure
    observed: ResultMeasure
    reference: NotReportedFact

    def __post_init__(self) -> None:
        if (
            not isinstance(self.measure, BenchmarkMeasure)
            or not isinstance(
                self.observed,
                (
                    ResultQuantityMeasure,
                    ResultRangeMeasure,
                    ResultTextMeasure,
                    ResultGeometryMeasure,
                    ResultMeasureUnavailable,
                ),
            )
            or not isinstance(self.reference, NotReportedFact)
        ):
            raise TypeError("not_reported_measure_comparison_type_invalid")


@dataclass(frozen=True, slots=True)
class NotApplicableMeasureComparison:
    measure: BenchmarkMeasure
    rationale: str

    def __post_init__(self) -> None:
        if not isinstance(self.measure, BenchmarkMeasure) or not isinstance(
            self.rationale,
            str,
        ):
            raise TypeError("not_applicable_measure_comparison_type_invalid")
        if not self.rationale.strip():
            raise ValueError("not_applicable_measure_comparison_rationale_missing")


MeasureComparison = (
    ComparableMeasureComparison
    | ContextMeasureComparison
    | NotReportedMeasureComparison
    | NotApplicableMeasureComparison
)


@dataclass(frozen=True, slots=True)
class ComparisonContract:
    """Owns one explicit permission for every fixed-frame measure."""

    rules: tuple[ComparisonRule, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.rules, tuple) or any(
            not isinstance(
                rule,
                (
                    SignedDifferenceRule,
                    ContextRule,
                    NotReportedRule,
                    NotApplicableRule,
                ),
            )
            for rule in self.rules
        ):
            raise TypeError("comparison_contract_type_invalid")
        if tuple(rule.measure for rule in self.rules) != BENCHMARK_MEASURE_FRAME:
            raise ValueError("comparison_rule_frame_invalid")

    def validate_alignment(self, alignment: BenchmarkAlignment) -> None:
        """Require every numeric comparator to name matched conditions."""

        if not isinstance(alignment, BenchmarkAlignment):
            raise TypeError("benchmark_alignment_required")
        for rule in self.rules:
            if not isinstance(rule, SignedDifferenceRule):
                continue
            for subject in rule.required_matched_subjects:
                if not isinstance(alignment.relation(subject), MatchedAlignment):
                    raise ValueError("signed_difference_required_match_invalid")

    def compare(
        self,
        measures: BenchmarkResultMeasures,
        *,
        reference: PublishedReference,
        alignment: BenchmarkAlignment,
    ) -> tuple[MeasureComparison, ...]:
        """Apply the complete frame without an implicit default branch."""

        if not isinstance(measures, BenchmarkResultMeasures):
            raise TypeError("benchmark_result_measures_required")
        if not isinstance(reference, PublishedReference):
            raise TypeError("published_reference_required")
        self.validate_alignment(alignment)
        comparisons: list[MeasureComparison] = []
        for rule in self.rules:
            observed = measures.measure_for(rule.measure)
            if isinstance(rule, SignedDifferenceRule):
                fact = reference.fact(rule.fact)
                if not isinstance(fact, (ReportedFact, DerivedFact)):
                    raise ValueError("signed_difference_fact_invalid")
                if (
                    not isinstance(fact.value, PublishedQuantity)
                    or fact.measure_meaning is None
                    or fact.measure_meaning.unit != fact.value.unit
                ):
                    raise ValueError("signed_difference_fact_invalid")
                if isinstance(observed, ResultMeasureUnavailable):
                    raise ValueError("comparable_observation_missing")
                if not isinstance(observed, ResultQuantityMeasure):
                    raise ValueError("comparable_observation_not_numeric")
                if observed.meaning != fact.measure_meaning:
                    raise ValueError("comparable_meaning_mismatch")
                comparisons.append(
                    ComparableMeasureComparison(
                        measure=rule.measure,
                        observed=observed,
                        reference=fact,
                        signed_difference=(
                            observed.value - fact.value.value
                        ),
                    )
                )
            elif isinstance(rule, ContextRule):
                fact = reference.fact(rule.fact)
                if not isinstance(fact, (ReportedFact, DerivedFact, UnresolvedFact)):
                    raise ValueError("context_fact_invalid")
                comparisons.append(
                    ContextMeasureComparison(
                        rule.measure,
                        observed,
                        fact,
                        rule.rationale,
                    )
                )
            elif isinstance(rule, NotReportedRule):
                fact = reference.fact(rule.fact)
                if not isinstance(fact, NotReportedFact):
                    raise ValueError("not_reported_rule_fact_invalid")
                comparisons.append(
                    NotReportedMeasureComparison(
                        rule.measure,
                        observed,
                        fact,
                    )
                )
            else:
                comparisons.append(
                    NotApplicableMeasureComparison(
                        rule.measure,
                        rule.rationale,
                    )
                )
        return tuple(comparisons)
