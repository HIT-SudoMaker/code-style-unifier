from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

import examples
from examples.metalens_benchmark.arbabi import arbabi_benchmark_case
from examples.metalens_benchmark.case import MetalensBenchmarkCase
from examples.metalens_benchmark.catalogue import (
    metalens_benchmark_cases, restore_metalens_benchmark_case)
from examples.metalens_benchmark.contract import (BENCHMARK_MEASURE_FRAME,
                                                  AdaptedAlignment,
                                                  BenchmarkAlignment,
                                                  BenchmarkMeasure,
                                                  BenchmarkSubject,
                                                  CircleGeometryRange,
                                                  ComparableMeasureComparison,
                                                  ContextRule,
                                                  IndependentAlignment,
                                                  MatchedAlignment,
                                                  NotReportedFact,
                                                  ReferenceFactName,
                                                  ReportedFact,
                                                  ResultGeometryMeasure,
                                                  ResultQuantityMeasure,
                                                  ResultRangeMeasure,
                                                  ResultTextMeasure,
                                                  UnresolvedFact,
                                                  WithheldAlignment)
from metacraft.authority import Document, reference_for
from metacraft.science.conduct import CompletedResults
from metacraft.science.result import Result
from tests.result_fixtures import admit_result, pointwise_propagation_result


def test_private_arbabi_case_keeps_fibre_family_truth_outside_the_blind_brief() -> None:
    case = arbabi_benchmark_case()

    assert case.name == "arbabi-2015-high-na-propagation"
    assert case.brief.atom.material.family == "silicon"
    assert case.reference.fact(ReferenceFactName.ATOM_MATERIAL).value == (
        "hydrogenated amorphous silicon"
    )
    assert isinstance(
        case.alignment.relation(BenchmarkSubject.ATOM_MATERIAL),
        AdaptedAlignment,
    )
    assert case.brief.aspect_limit == 8
    assert case.brief.dimension_step_nm == 10
    assert case.brief.aperture is None
    assert case.brief.cell_period_nm is None
    assert case.brief.atom_height_nm is None
    assert isinstance(
        case.alignment.relation(BenchmarkSubject.ASPECT_LIMIT),
        IndependentAlignment,
    )
    assert isinstance(
        case.alignment.relation(BenchmarkSubject.INCIDENT_POLARIZATION),
        AdaptedAlignment,
    )
    assert isinstance(
        case.alignment.relation(BenchmarkSubject.APERTURE),
        WithheldAlignment,
    )

    period = case.reference.fact(ReferenceFactName.CELL_PERIOD)
    height = case.reference.fact(ReferenceFactName.ATOM_HEIGHT)
    geometry = case.reference.fact(ReferenceFactName.LATERAL_GEOMETRY)
    efficiency = case.reference.fact(ReferenceFactName.FOCUS_EFFICIENCY)
    complex_field = case.reference.fact(ReferenceFactName.COMPLEX_FOCAL_FIELD)
    transmitted_magnitude = case.reference.fact(
        ReferenceFactName.TRANSMITTED_MAGNITUDE
    )
    assert isinstance(period, ReportedFact)
    assert period.value.value == Decimal("800")
    assert "hexagonal" in period.meaning
    assert isinstance(height, ReportedFact)
    assert height.value.value == Decimal("940")
    assert isinstance(geometry, ReportedFact)
    assert geometry.value == CircleGeometryRange(200, 550)
    assert isinstance(efficiency, ReportedFact)
    assert efficiency.value.value == Decimal("0.82")
    assert efficiency.measure_meaning is not None
    assert "400 um" in efficiency.measure_meaning.scope
    assert efficiency.sources[0].location == "Methods and Figure 4d"
    assert isinstance(complex_field, NotReportedFact)
    assert isinstance(transmitted_magnitude, UnresolvedFact)
    assert case.reference.exclusions == (
        "complete single-mode-fibre incident field reproduction",
        "fabricated 400 um lens family as the compact benchmark result",
        "paper-selected cell geometry as a production constraint",
    )
    assert tuple(rule.measure for rule in case.contract.rules) == (
        BENCHMARK_MEASURE_FRAME
    )
    assert isinstance(
        case.contract.rules[BENCHMARK_MEASURE_FRAME.index(BenchmarkMeasure.FOCUS_EFFICIENCY)],
        ContextRule,
    )
    assert examples.__all__ == [
        "MetalensBenchmarkCase",
        "metalens_benchmark_cases",
        "select_metalens_benchmark_case",
    ]
    assert tuple(item.name for item in metalens_benchmark_cases()) == (
        "mcclung-2024-low-na-propagation",
        "yang-2018-low-na-geometric",
        "arbabi-2015-high-na-propagation",
        "khorasaninejad-2016-high-na-geometric",
    )


def test_private_arbabi_case_is_canonical_and_strictly_restorable() -> None:
    case = arbabi_benchmark_case()
    document = Document.from_bytes(case.document().to_bytes())

    restored = restore_metalens_benchmark_case(document)

    assert restored is case
    assert case.identity.startswith("sha256:")
    assert len(case.identity) == 71
    changed = dict(document.values)
    changed["selected_device"] = "fabricated fibre-illuminated family"
    with pytest.raises(
        ValueError,
        match="metalens_benchmark_case_document_mismatch",
    ):
        restore_metalens_benchmark_case(
            Document(document.schema_identifier, changed)
        )


def test_private_arbabi_contract_fixture_restores_high_na_vector_meaning(
    tmp_path: Path,
) -> None:
    case = _compact_arbabi_contract_fixture()
    recorded = pointwise_propagation_result(
        tmp_path,
        case.brief,
        period_nm=800,
        height_nm=800,
    )
    result = Result(
        reference=admit_result(recorded),
        document=recorded.conclusion.document(),
        sources=recorded.conclusion.references(),
        closure=recorded.closure,
    )

    comparison = case.compare(
        CompletedResults((result,)),
        fetch=recorded.authority.fetch,
    )[0]

    measures = comparison.result_measures
    assert measures.cell_period.value == Decimal("800")
    assert measures.atom_height.value == Decimal("800")
    assert isinstance(measures.lateral_geometry, ResultGeometryMeasure)
    assert isinstance(measures.lateral_geometry.geometry, CircleGeometryRange)
    assert isinstance(measures.phase_coverage, ResultTextMeasure)
    assert isinstance(measures.transmitted_power, ResultRangeMeasure)
    assert isinstance(measures.focus_efficiency, ResultQuantityMeasure)
    assert isinstance(measures.focal_shift, ResultQuantityMeasure)
    assert isinstance(measures.x_half_maximum_width, ResultQuantityMeasure)
    assert isinstance(measures.y_half_maximum_width, ResultQuantityMeasure)
    assert isinstance(measures.complex_focal_field, ResultQuantityMeasure)
    assert measures.complex_focal_field.value == Decimal("0.1")
    assert (
        measures.complex_focal_field.meaning.normalization
        == "phase-and-amplitude-aligned vector-field L2 error"
    )
    assert tuple(item.measure for item in comparison.measures) == (
        BENCHMARK_MEASURE_FRAME
    )
    assert not any(
        isinstance(item, ComparableMeasureComparison)
        for item in comparison.measures
    )


def test_private_arbabi_compare_is_strict_and_all_or_nothing(tmp_path: Path) -> None:
    case = _compact_arbabi_contract_fixture()
    first = pointwise_propagation_result(
        tmp_path / "first",
        case.brief,
        period_nm=800,
        height_nm=800,
    )
    first_result = Result(
        reference=admit_result(first),
        document=first.conclusion.document(),
        sources=first.conclusion.references(),
        closure=first.closure,
    )
    foreign_document = Document("contract.fixture.foreign_result", {"order": 2})
    foreign_result = Result(
        reference=reference_for(foreign_document.to_bytes()),
        document=foreign_document,
        sources=first_result.sources,
        closure=first_result.closure,
    )
    results = (first_result, foreign_result)
    completed = CompletedResults(results)

    with pytest.raises(TypeError, match="completed_results_required"):
        case.compare(object(), fetch=first.authority.fetch)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="metalens_benchmark_brief_mismatch"):
        arbabi_benchmark_case().compare(completed, fetch=first.authority.fetch)
    with pytest.raises(
        ValueError,
        match="metalens_benchmark_result_body_mismatch",
    ):
        case.compare(
            CompletedResults((results[0],)),
            fetch=lambda _reference: b"wrong body",
        )
    expected_fault = RuntimeError("reference_unresolvable: object missing")
    returned = None

    def fetch_until_second(reference: object) -> bytes:
        if reference == results[1].reference:
            raise expected_fault
        try:
            return first.authority.fetch(reference)  # type: ignore[arg-type]
        except RuntimeError:
            raise

    with pytest.raises(RuntimeError) as raised:
        returned = case.compare(completed, fetch=fetch_until_second)  # type: ignore[arg-type]
    assert raised.value is expected_fault
    assert returned is None


def _compact_arbabi_contract_fixture() -> MetalensBenchmarkCase:
    """Bound the vector Result exercise without claiming an Arbabi outcome."""

    case = arbabi_benchmark_case()
    brief = replace(
        case.brief,
        wording=(
            "Exercise the bounded high-NA propagation Result contract; this "
            "is not the Arbabi paper-device outcome."
        ),
        focal_length_um=Decimal("0.25"),
        numerical_aperture=Decimal("0.8"),
        aperture=None,
    )
    adapted_subjects = {
        BenchmarkSubject.NUMERICAL_APERTURE,
        BenchmarkSubject.FOCAL_LENGTH,
        BenchmarkSubject.APERTURE,
    }
    relations = tuple(
        AdaptedAlignment(
            relation.subject,
            relation.fact,
            "The bounded contract fixture adapts this optical condition.",
        )
        if relation.subject in adapted_subjects
        and isinstance(relation, (MatchedAlignment, WithheldAlignment))
        else relation
        for relation in case.alignment.relations
    )
    return replace(
        case,
        name="arbabi-high-na-propagation-contract-fixture",
        brief=brief,
        alignment=BenchmarkAlignment(relations),
    )
