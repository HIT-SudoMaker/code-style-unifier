from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
import hashlib
from typing import TYPE_CHECKING

from metacraft.authority import Document, Reference
from metacraft.canonical import canonicalize
from metacraft.science.metalens.brief import (
    MetalensBrief,
    require_monochromatic_wavelength,
)

from .contract import (
    AdaptedAlignment,
    BenchmarkAlignment,
    BenchmarkMeasure,
    BenchmarkResultMeasures,
    BenchmarkSubject,
    ComparisonContract,
    ComparableMeasureComparison,
    ContextMeasureComparison,
    ContextRule,
    DerivedFact,
    IndependentAlignment,
    MatchedAlignment,
    MeasureComparison,
    NotReportedFact,
    NotApplicableMeasureComparison,
    NotReportedMeasureComparison,
    NotReportedRule,
    PublishedQuantity,
    PublishedReference,
    ReportedFact,
    SignedDifferenceRule,
    UnresolvedFact,
    WithheldAlignment,
)

if TYPE_CHECKING:
    from metacraft.science.conduct import CompletedResults
    from metacraft.science.result import Result


_BENCHMARK_CASE_SCHEMA = "metacraft.examples.metalens_benchmark_reference_case"
_BENCHMARK_COMPARISON_SCHEMA = (
    "metacraft.examples.metalens_benchmark_reference_comparison"
)


@dataclass(frozen=True, slots=True)
class MetalensBenchmarkComparison:
    """Retains one complete external comparison and its exact provenance."""

    case_identity: str
    result_reference: Reference
    result_measures: BenchmarkResultMeasures
    measures: tuple[MeasureComparison, ...]
    reference: PublishedReference
    alignment: BenchmarkAlignment

    def __post_init__(self) -> None:
        if (
            not isinstance(self.case_identity, str)
            or not isinstance(self.result_reference, Reference)
            or not isinstance(self.result_measures, BenchmarkResultMeasures)
            or not isinstance(self.measures, tuple)
            or any(
                not isinstance(
                    item,
                    (
                        ComparableMeasureComparison,
                        ContextMeasureComparison,
                        NotReportedMeasureComparison,
                        NotApplicableMeasureComparison,
                    ),
                )
                for item in self.measures
            )
            or not isinstance(self.reference, PublishedReference)
            or not isinstance(self.alignment, BenchmarkAlignment)
        ):
            raise TypeError("metalens_benchmark_comparison_type_invalid")
        if not self.case_identity.startswith("sha256:") or tuple(
            item.measure for item in self.measures
        ) != tuple(BenchmarkMeasure):
            raise ValueError("metalens_benchmark_comparison_invalid")

    def document(self) -> Document:
        """Encode one comparison without changing production Result bytes."""

        values = canonicalize(self)
        assert isinstance(values, dict)
        return Document(_BENCHMARK_COMPARISON_SCHEMA, values)


@dataclass(frozen=True, slots=True)
class MetalensBenchmarkCase:
    """Own one blind brief and every external comparison meaning."""

    name: str
    brief: MetalensBrief
    reference: PublishedReference
    alignment: BenchmarkAlignment
    contract: ComparisonContract

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not isinstance(self.brief, MetalensBrief)
            or not isinstance(self.reference, PublishedReference)
            or not isinstance(self.alignment, BenchmarkAlignment)
            or not isinstance(self.contract, ComparisonContract)
        ):
            raise TypeError("metalens_benchmark_case_type_invalid")
        if not self.name.strip():
            raise ValueError("metalens_benchmark_case_identity_incomplete")
        if (
            self.brief.cell_period_nm is not None
            or self.brief.atom_height_nm is not None
        ):
            raise ValueError("metalens_benchmark_geometry_leaked")
        self._validate_alignment()
        self._validate_contract()

    @property
    def identity(self) -> str:
        """Return the content identity of every case-owned meaning."""

        return "sha256:" + hashlib.sha256(self.document().to_bytes()).hexdigest()

    def document(self) -> Document:
        """Encode every fact, source, relation, rule, and brief input."""

        values = canonicalize(self)
        assert isinstance(values, dict)
        values["brief"] = self.brief.canonical_value()
        return Document(_BENCHMARK_CASE_SCHEMA, values)

    def compare(
        self,
        completed_results: CompletedResults,
        *,
        fetch: Callable[[Reference], bytes],
    ) -> tuple[MetalensBenchmarkComparison, ...]:
        """Compare only exact completed Results through one read-only seam."""

        from metacraft.science.conduct import CompletedResults

        if not isinstance(completed_results, CompletedResults):
            raise TypeError("completed_results_required")
        expected_brief = (
            "sha256:" + hashlib.sha256(self.brief.canonical_bytes()).hexdigest()
        )
        if completed_results.brief_identity != expected_brief:
            raise ValueError("metalens_benchmark_brief_mismatch")
        return tuple(
            self._compare_result(result, fetch=fetch)
            for result in completed_results.results
        )

    def _compare_result(
        self,
        result: Result,
        *,
        fetch: Callable[[Reference], bytes],
    ) -> MetalensBenchmarkComparison:
        from metacraft.science.metalens.result import restore_result

        from .result_measures import restore_benchmark_result_measures

        result_body = fetch(result.reference)
        if result_body != result.document.to_bytes():
            raise ValueError("metalens_benchmark_result_body_mismatch")
        conclusion = restore_result(
            result.document,
            closure=result.closure,
            fetch=fetch,
        )
        result_measures = restore_benchmark_result_measures(conclusion)
        measures = self.contract.compare(
            result_measures,
            reference=self.reference,
            alignment=self.alignment,
        )
        return MetalensBenchmarkComparison(
            case_identity=self.identity,
            result_reference=result.reference,
            result_measures=result_measures,
            measures=measures,
            reference=self.reference,
            alignment=self.alignment,
        )

    def _validate_alignment(self) -> None:
        for relation in self.alignment.relations:
            if isinstance(
                relation,
                (MatchedAlignment, AdaptedAlignment, WithheldAlignment),
            ):
                fact = self.reference.fact(relation.fact)
            else:
                fact = None
            brief_value = _brief_value(self.brief, relation.subject)
            if isinstance(relation, MatchedAlignment):
                if not isinstance(fact, (ReportedFact, DerivedFact)):
                    raise ValueError("matched_alignment_fact_invalid")
                if fact.value != brief_value:
                    raise ValueError("matched_alignment_value_mismatch")
            elif isinstance(relation, IndependentAlignment):
                if brief_value is None:
                    raise ValueError("independent_alignment_input_missing")
            elif isinstance(relation, WithheldAlignment):
                if brief_value is not None:
                    raise ValueError("withheld_alignment_value_leaked")

    def _validate_contract(self) -> None:
        self.contract.validate_alignment(self.alignment)
        for rule in self.contract.rules:
            if isinstance(
                rule,
                (SignedDifferenceRule, ContextRule, NotReportedRule),
            ):
                fact = self.reference.fact(rule.fact)
                if isinstance(rule, SignedDifferenceRule):
                    if (
                        not isinstance(fact, (ReportedFact, DerivedFact))
                        or not isinstance(fact.value, PublishedQuantity)
                        or fact.measure_meaning is None
                    ):
                        raise ValueError("signed_difference_fact_invalid")
                elif isinstance(rule, ContextRule):
                    if not isinstance(
                        fact,
                        (ReportedFact, DerivedFact, UnresolvedFact),
                    ):
                        raise ValueError("context_fact_invalid")
                elif not isinstance(fact, NotReportedFact):
                    raise ValueError("not_reported_rule_fact_invalid")


def _brief_value(
    brief: MetalensBrief,
    subject: BenchmarkSubject,
) -> object | None:
    match subject:
        case BenchmarkSubject.WAVELENGTH:
            return PublishedQuantity(
                Decimal(require_monochromatic_wavelength(brief.operating_spectrum)),
                "nm",
            )
        case BenchmarkSubject.NUMERICAL_APERTURE:
            return PublishedQuantity(brief.numerical_aperture, "ratio")
        case BenchmarkSubject.FOCAL_LENGTH:
            return PublishedQuantity(brief.focal_length_um, "um")
        case BenchmarkSubject.INCIDENT_POLARIZATION:
            return brief.incident_polarization
        case BenchmarkSubject.CONTROL_STRATEGY:
            return brief.control_strategy
        case BenchmarkSubject.ATOM_SHAPE:
            return brief.atom.shape
        case BenchmarkSubject.ATOM_MATERIAL:
            return brief.atom.material.family
        case BenchmarkSubject.SUBSTRATE_MATERIAL:
            return brief.substrate.family
        case BenchmarkSubject.APERTURE:
            return brief.aperture
        case BenchmarkSubject.ASPECT_LIMIT:
            return PublishedQuantity(Decimal(brief.aspect_limit), "ratio")
        case BenchmarkSubject.DIMENSION_STEP:
            return (
                None
                if brief.dimension_step_nm is None
                else PublishedQuantity(
                    Decimal(brief.dimension_step_nm),
                    "nm",
                )
            )
        case BenchmarkSubject.CELL_PERIOD:
            return (
                None
                if brief.cell_period_nm is None
                else PublishedQuantity(Decimal(brief.cell_period_nm), "nm")
            )
        case BenchmarkSubject.ATOM_HEIGHT:
            return (
                None
                if brief.atom_height_nm is None
                else PublishedQuantity(Decimal(brief.atom_height_nm), "nm")
            )
        case BenchmarkSubject.LATERAL_GEOMETRY:
            return None
        case BenchmarkSubject.FABRICATION_ROUTE:
            return None
