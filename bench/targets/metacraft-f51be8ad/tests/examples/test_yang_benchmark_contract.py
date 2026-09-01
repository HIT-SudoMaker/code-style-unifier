from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import examples
import pytest

from examples.metalens_benchmark.case import MetalensBenchmarkCase
from examples.metalens_benchmark.catalogue import restore_metalens_benchmark_case
from examples.metalens_benchmark.contract import (
    AdaptedAlignment,
    BENCHMARK_MEASURE_FRAME,
    BenchmarkAlignment,
    BenchmarkSubject,
    ComparableMeasureComparison,
    ContextRule,
    EllipseGeometryRange,
    IndependentAlignment,
    MatchedAlignment,
    ReferenceFactName,
    ReportedFact,
    ResultGeometryMeasure,
    ResultMeasureUnavailable,
    ResultQuantityMeasure,
    ResultRangeMeasure,
    ResultTextMeasure,
)
from examples.metalens_benchmark.yang import yang_benchmark_case
from metacraft.authority import Document
from metacraft.science.conduct import CompletedResults
from metacraft.science.metalens.aperture import Ellipse
from metacraft.science.metalens.brief import ApertureExtent, ApertureFootprint, ApertureIntent
from metacraft.science.result import Result
from tests.result_fixtures import admit_result, geometric_results


def test_private_yang_case_keeps_paper_geometry_outside_the_blind_brief() -> None:
    case = yang_benchmark_case()

    assert case.name == "yang-2018-low-na-geometric"
    assert case.brief.aspect_limit == 8
    assert case.brief.cell_period_nm is None
    assert case.brief.atom_height_nm is None
    assert case.brief.dimension_step_nm == 10
    assert isinstance(
        case.alignment.relation(BenchmarkSubject.ASPECT_LIMIT),
        IndependentAlignment,
    )
    period = case.reference.fact(ReferenceFactName.CELL_PERIOD)
    height = case.reference.fact(ReferenceFactName.ATOM_HEIGHT)
    geometry = case.reference.fact(ReferenceFactName.LATERAL_GEOMETRY)
    assert isinstance(period, ReportedFact)
    assert period.value.value == Decimal("1500")
    assert isinstance(height, ReportedFact)
    assert height.value.value == Decimal("340")
    assert isinstance(geometry, ReportedFact)
    assert geometry.value == EllipseGeometryRange(
        minimum_minor_axis_nm=480,
        maximum_minor_axis_nm=480,
        minimum_major_axis_nm=1350,
        maximum_major_axis_nm=1350,
    )
    assert all(
        isinstance(case.contract.rules[index], ContextRule)
        for index in range(3)
    )
    assert tuple(rule.measure for rule in case.contract.rules) == (
        BENCHMARK_MEASURE_FRAME
    )
    assert examples.__all__ == [
        "MetalensBenchmarkCase",
        "metalens_benchmark_cases",
        "select_metalens_benchmark_case",
    ]


def test_private_yang_case_is_canonical_and_strictly_restorable() -> None:
    case = yang_benchmark_case()
    document = Document.from_bytes(case.document().to_bytes())

    restored = restore_metalens_benchmark_case(document)

    assert restored is case
    assert case.identity.startswith("sha256:")
    assert len(case.identity) == 71
    changed = dict(document.values)
    changed["selected_device"] = "complete Hartmann-Shack array"
    with pytest.raises(
        ValueError,
        match="metalens_benchmark_case_document_mismatch",
    ):
        restore_metalens_benchmark_case(
            Document(document.schema_identifier, changed)
        )


def test_private_yang_contract_fixture_restores_low_na_geometric_meaning(
    tmp_path: Path,
) -> None:
    case = _compact_yang_contract_fixture()
    recorded = geometric_results(
        tmp_path,
        (8,),
        brief=case.brief,
        period_nm=800,
        height_nm=600,
        cell_geometry=Ellipse(minor_axis_nm=200, major_axis_nm=400),
    )[0]
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
    assert measures.atom_height.value == Decimal("600")
    assert isinstance(measures.lateral_geometry, ResultGeometryMeasure)
    assert isinstance(measures.lateral_geometry.geometry, EllipseGeometryRange)
    assert isinstance(measures.phase_coverage, ResultMeasureUnavailable)
    assert isinstance(measures.transmitted_power, ResultRangeMeasure)
    assert isinstance(measures.orientation_relation, ResultTextMeasure)
    assert isinstance(measures.polarization_conversion, ResultRangeMeasure)
    assert isinstance(measures.focus_efficiency, ResultQuantityMeasure)
    assert tuple(item.measure for item in comparison.measures) == (
        BENCHMARK_MEASURE_FRAME
    )
    assert not any(
        isinstance(item, ComparableMeasureComparison)
        for item in comparison.measures
    )
    assert comparison.document().values["case_identity"] == case.identity


def test_private_yang_compare_rejects_wrong_cases_and_propagates_fetch_faults(
    tmp_path: Path,
) -> None:
    case = _compact_yang_contract_fixture()
    recorded_results = geometric_results(
        tmp_path,
        (8, 12),
        brief=case.brief,
        period_nm=800,
        height_nm=600,
        cell_geometry=Ellipse(minor_axis_nm=200, major_axis_nm=400),
    )
    recorded = recorded_results[0]
    result = Result(
        reference=admit_result(recorded),
        document=recorded.conclusion.document(),
        sources=recorded.conclusion.references(),
        closure=recorded.closure,
    )
    completed = CompletedResults((result,))

    with pytest.raises(TypeError, match="completed_results_required"):
        case.compare(object(), fetch=recorded.authority.fetch)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="metalens_benchmark_brief_mismatch"):
        yang_benchmark_case().compare(completed, fetch=recorded.authority.fetch)
    expected_fault = RuntimeError("reference_unresolvable: object missing")

    def missing_body(_reference: object) -> bytes:
        raise expected_fault

    with pytest.raises(RuntimeError) as raised:
        case.compare(completed, fetch=missing_body)  # type: ignore[arg-type]
    assert raised.value is expected_fault
    with pytest.raises(
        ValueError,
        match="metalens_benchmark_result_body_mismatch",
    ):
        case.compare(completed, fetch=lambda _reference: b"wrong body")

    second_recorded = recorded_results[1]
    second_result = Result(
        reference=admit_result(second_recorded),
        document=second_recorded.conclusion.document(),
        sources=second_recorded.conclusion.references(),
        closure=second_recorded.closure,
    )
    failing_reference = second_result.reference
    mixed = CompletedResults((result, second_result))
    returned = None

    def fail_on_second(reference: object) -> bytes:
        if reference == failing_reference:
            raise expected_fault
        return recorded.authority.fetch(reference)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError) as raised_all_or_nothing:
        returned = case.compare(mixed, fetch=fail_on_second)  # type: ignore[arg-type]
    assert raised_all_or_nothing.value is expected_fault
    assert returned is None


def _compact_yang_contract_fixture() -> MetalensBenchmarkCase:
    """Bound the Result exercise without claiming one exact Yang outcome."""

    case = yang_benchmark_case()
    brief = replace(
        case.brief,
        wording=(
            "Exercise the bounded low-NA geometric Result contract; this is "
            "not the Yang paper-device outcome."
        ),
        aperture=ApertureIntent(
            site_count=5,
            extent=ApertureExtent.DIAMETER,
            footprint=ApertureFootprint.SQUARE,
        ),
    )
    relations = tuple(
        AdaptedAlignment(
            relation.subject,
            relation.fact,
            "The bounded contract fixture adapts the paper aperture.",
        )
        if (
            isinstance(relation, MatchedAlignment)
            and relation.subject is BenchmarkSubject.APERTURE
        )
        else relation
        for relation in case.alignment.relations
    )
    return replace(
        case,
        name="yang-low-na-geometric-contract-fixture",
        brief=brief,
        alignment=BenchmarkAlignment(relations),
    )
