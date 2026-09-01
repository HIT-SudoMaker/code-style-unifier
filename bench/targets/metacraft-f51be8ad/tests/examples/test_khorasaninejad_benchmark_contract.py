from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

import examples
from examples.metalens_benchmark.case import MetalensBenchmarkCase
from examples.metalens_benchmark.catalogue import (
    metalens_benchmark_cases, restore_metalens_benchmark_case)
from examples.metalens_benchmark.contract import (BENCHMARK_MEASURE_FRAME,
                                                  AdaptedAlignment,
                                                  BenchmarkAlignment,
                                                  BenchmarkMeasure,
                                                  BenchmarkSubject,
                                                  ComparableMeasureComparison,
                                                  ContextRule,
                                                  IndependentAlignment,
                                                  MatchedAlignment,
                                                  NotReportedFact,
                                                  ReferenceFactName,
                                                  ReportedFact,
                                                  ResultGeometryMeasure,
                                                  ResultMeasureUnavailable,
                                                  ResultQuantityMeasure,
                                                  ResultRangeMeasure,
                                                  ResultTextMeasure,
                                                  WithheldAlignment)
from examples.metalens_benchmark.khorasaninejad import (
    RotationAwareRectangleGeometry, khorasaninejad_benchmark_case)
from metacraft.authority import Document, reference_for
from metacraft.science.conduct import CompletedResults
from metacraft.science.result import Result
from tests.result_fixtures import admit_result, pointwise_geometric_result


def test_private_khorasaninejad_case_keeps_rotated_geometry_outside_brief() -> None:
    case = khorasaninejad_benchmark_case()

    assert case.name == "khorasaninejad-2016-high-na-geometric"
    assert case.brief.atom.material.family == "amorphous titanium dioxide"
    assert case.brief.aspect_limit == 8
    assert case.brief.dimension_step_nm == 10
    assert case.brief.aperture is None
    assert case.brief.cell_period_nm is None
    assert case.brief.atom_height_nm is None
    assert isinstance(
        case.alignment.relation(BenchmarkSubject.ASPECT_LIMIT),
        IndependentAlignment,
    )

    period = case.reference.fact(ReferenceFactName.CELL_PERIOD)
    height = case.reference.fact(ReferenceFactName.ATOM_HEIGHT)
    geometry = case.reference.fact(ReferenceFactName.LATERAL_GEOMETRY)
    orientation = case.reference.fact(ReferenceFactName.ORIENTATION_RELATION)
    efficiency = case.reference.fact(ReferenceFactName.FOCUS_EFFICIENCY)
    vertical_width = case.reference.fact(
        ReferenceFactName.VERTICAL_CUT_HALF_MAXIMUM_WIDTH
    )
    complex_field = case.reference.fact(ReferenceFactName.COMPLEX_FOCAL_FIELD)
    longitudinal = case.reference.fact(
        ReferenceFactName.LONGITUDINAL_POWER_FRACTION
    )
    assert isinstance(period, ReportedFact)
    assert period.value.value == Decimal("325")
    assert isinstance(height, ReportedFact)
    assert height.value.value == Decimal("600")
    assert isinstance(geometry, ReportedFact)
    assert geometry.value == RotationAwareRectangleGeometry.from_cell(
        period_nm=325,
        height_nm=600,
        long_side_nm=250,
        short_side_nm=95,
    )
    assert geometry.value.minimum_feature_nm == Decimal("95")
    assert geometry.value.axis_aligned_minimum_gap_nm == Decimal("75")
    assert geometry.value.minimum_orientation_envelope_gap_nm == Decimal(
        "57.5584"
    )
    assert geometry.value.minimum_orientation_envelope_gap_nm != (
        period.value.value - Decimal("250")
    )
    with pytest.raises(
        ValueError,
        match="rotation_aware_rectangle_derivation_invalid",
    ):
        replace(
            geometry.value,
            minimum_orientation_envelope_gap_nm=Decimal("60"),
        )
    assert isinstance(orientation, ReportedFact)
    assert "+2 * orientation" in orientation.value
    assert isinstance(efficiency, ReportedFact)
    assert efficiency.value.value == Decimal("0.73")
    assert efficiency.measure_meaning is None
    assert isinstance(vertical_width, ReportedFact)
    assert vertical_width.value.value == Decimal("375")
    assert vertical_width.measure_meaning is not None
    assert "vertical" in vertical_width.measure_meaning.definition
    assert isinstance(complex_field, NotReportedFact)
    assert isinstance(longitudinal, NotReportedFact)
    assert tuple(rule.measure for rule in case.contract.rules) == (
        BENCHMARK_MEASURE_FRAME
    )
    assert isinstance(
        case.contract.rules[
            BENCHMARK_MEASURE_FRAME.index(BenchmarkMeasure.FOCUS_EFFICIENCY)
        ],
        ContextRule,
    )
    assert isinstance(
        case.contract.rules[
            BENCHMARK_MEASURE_FRAME.index(
                BenchmarkMeasure.VERTICAL_CUT_HALF_MAXIMUM_WIDTH
            )
        ],
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


def test_private_khorasaninejad_case_is_canonical_and_strictly_restorable() -> None:
    case = khorasaninejad_benchmark_case()
    document = Document.from_bytes(case.document().to_bytes())

    restored = restore_metalens_benchmark_case(document)

    assert restored is case
    assert case.identity.startswith("sha256:")
    assert len(case.identity) == 71
    changed = dict(document.values)
    changed["selected_device"] = "660 nm device"
    with pytest.raises(
        ValueError,
        match="metalens_benchmark_case_document_mismatch",
    ):
        restore_metalens_benchmark_case(
            Document(document.schema_identifier, changed)
        )


def test_private_khorasaninejad_fixture_restores_high_na_geometric_meaning(
    tmp_path: Path,
) -> None:
    case = _compact_khorasaninejad_contract_fixture()
    recorded = pointwise_geometric_result(
        tmp_path,
        case.brief,
        period_nm=320,
        height_nm=600,
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
    assert measures.cell_period.value == Decimal("320")
    assert measures.atom_height.value == Decimal("600")
    assert isinstance(measures.lateral_geometry, ResultGeometryMeasure)
    assert isinstance(measures.phase_coverage, ResultMeasureUnavailable)
    assert isinstance(measures.transmitted_power, ResultRangeMeasure)
    assert isinstance(measures.orientation_relation, ResultTextMeasure)
    assert isinstance(measures.polarization_conversion, ResultRangeMeasure)
    assert isinstance(measures.focus_efficiency, ResultQuantityMeasure)
    assert isinstance(measures.focal_shift, ResultQuantityMeasure)
    assert isinstance(measures.x_half_maximum_width, ResultQuantityMeasure)
    assert isinstance(measures.y_half_maximum_width, ResultQuantityMeasure)
    assert isinstance(measures.mean_half_maximum_width, ResultQuantityMeasure)
    assert isinstance(
        measures.vertical_cut_half_maximum_width,
        ResultMeasureUnavailable,
    )
    assert isinstance(measures.complex_focal_field, ResultQuantityMeasure)
    assert isinstance(measures.transmitted_fraction, ResultQuantityMeasure)
    assert isinstance(measures.focused_fraction, ResultQuantityMeasure)
    assert measures.complex_focal_field.value == Decimal("0.1")
    assert tuple(item.measure for item in comparison.measures) == (
        BENCHMARK_MEASURE_FRAME
    )
    assert not any(
        isinstance(item, ComparableMeasureComparison)
        for item in comparison.measures
    )


def test_private_khorasaninejad_compare_is_strict_and_all_or_nothing(
    tmp_path: Path,
) -> None:
    case = _compact_khorasaninejad_contract_fixture()
    first = pointwise_geometric_result(
        tmp_path / "first",
        case.brief,
        period_nm=320,
        height_nm=600,
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
    completed = CompletedResults((first_result, foreign_result))

    with pytest.raises(TypeError, match="completed_results_required"):
        case.compare(object(), fetch=first.authority.fetch)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="metalens_benchmark_brief_mismatch"):
        khorasaninejad_benchmark_case().compare(
            CompletedResults((first_result,)),
            fetch=first.authority.fetch,
        )
    with pytest.raises(
        ValueError,
        match="metalens_benchmark_result_body_mismatch",
    ):
        case.compare(
            CompletedResults((first_result,)),
            fetch=lambda _reference: b"wrong body",
        )

    expected_fault = RuntimeError("reference_unresolvable: object missing")
    returned = None

    def fail_on_second(reference: object) -> bytes:
        if reference == foreign_result.reference:
            raise expected_fault
        return first.authority.fetch(reference)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError) as raised:
        returned = case.compare(completed, fetch=fail_on_second)  # type: ignore[arg-type]
    assert raised.value is expected_fault
    assert returned is None


def _compact_khorasaninejad_contract_fixture() -> MetalensBenchmarkCase:
    """Bound the vector Result exercise without claiming a paper outcome."""

    case = khorasaninejad_benchmark_case()
    brief = replace(
        case.brief,
        wording=(
            "Exercise the bounded high-NA geometric Result contract; this is "
            "not the Khorasaninejad paper-device outcome."
        ),
        focal_length_um=Decimal("0.25"),
        aperture=None,
    )
    adapted_subjects = {
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
        name="khorasaninejad-high-na-geometric-contract-fixture",
        brief=brief,
        alignment=BenchmarkAlignment(relations),
    )
