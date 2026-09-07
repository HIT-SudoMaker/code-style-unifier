from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

import examples
from examples.metalens_benchmark.case import MetalensBenchmarkCase
from examples.metalens_benchmark.catalogue import restore_metalens_benchmark_case
from examples.metalens_benchmark.contract import (
    BENCHMARK_MEASURE_FRAME,
    AdaptedAlignment,
    BenchmarkAlignment,
    BenchmarkMeasure,
    BenchmarkResultMeasures,
    BenchmarkSubject,
    CircleGeometryRange,
    ComparableMeasureComparison,
    ComparisonContract,
    ContextMeasureComparison,
    ContextRule,
    DerivedFact,
    ExcludedAlignment,
    IndependentAlignment,
    MatchedAlignment,
    MeasureMeaning,
    NotApplicableRule,
    NotReportedFact,
    NotReportedRule,
    PublishedFactStatus,
    PublishedQuantity,
    PublishedReference,
    ReferenceFactName,
    ReportedFact,
    ResultGeometryMeasure,
    ResultMeasureUnavailable,
    ResultQuantityMeasure,
    ResultRangeMeasure,
    ResultTextMeasure,
    SignedDifferenceRule,
    SourceLocator,
    UnresolvedFact,
    WithheldAlignment,
)
from examples.metalens_benchmark.mcclung import mcclung_benchmark_case
from examples.metalens_benchmark.result_measures import (
    restore_benchmark_result_measures,
)
from metacraft.authority import Document, Reference, reference_for
from metacraft.materials import SolverMaterialLibrary
from metacraft.science.conduct import CompletedResults
from metacraft.science.metalens.result import MetalensResult
from metacraft.science.result import Result
from tests.brief_fixtures import geometric_brief, propagation_brief
from tests.domain_fixtures import select_fixture_period_nm
from tests.result_fixtures import (
    admit_result,
    geometric_results,
    pointwise_geometric_result,
    pointwise_propagation_result,
    propagation_results,
)

SOURCE = SourceLocator(
    citation="doi:10.1002/adom.202301865",
    location="Figure 2",
)
FOCUS_MEANING = MeasureMeaning(
    unit="ratio",
    scope="contract fixture",
    normalization="focused power / incident reference power",
    definition="Power in the declared focal bucket divided by incident power.",
)
RESULT_REFERENCE = reference_for(b"contract observation")
ROOT = Path(__file__).parents[2]


def test_published_fact_states_make_absence_and_derivation_explicit() -> None:
    reported = ReportedFact(
        key=ReferenceFactName.ATOM_HEIGHT,
        value=PublishedQuantity(Decimal("800"), "nm"),
        meaning="Selected comparator height.",
        sources=(SOURCE,),
    )
    derived = DerivedFact(
        key=ReferenceFactName.MINIMUM_FEATURE,
        value=PublishedQuantity(Decimal("80"), "nm"),
        meaning="Minimum feature inferred from H/w.",
        sources=(SOURCE,),
        expression="800 nm / 10",
        inputs=(
            ReferenceFactName.ATOM_HEIGHT,
            ReferenceFactName.FEATURE_ASPECT_RATIO,
        ),
    )
    not_reported = NotReportedFact(
        key=ReferenceFactName.COMPLEX_FOCAL_FIELD,
        meaning="Reusable complex focal field.",
        reviewed_sources=(SOURCE,),
        reason="The article publishes no reusable complex-field array.",
    )
    unresolved = UnresolvedFact(
        key=ReferenceFactName.CELL_PERIOD,
        meaning="Period joined to the selected 800 nm comparator.",
        reviewed_sources=(SOURCE,),
        reason="The 400 nm source belongs to another supporting library.",
    )

    assert tuple(
        fact.status for fact in (reported, derived, not_reported, unresolved)
    ) == tuple(PublishedFactStatus)
    assert not_reported.value is None
    assert unresolved.value is None
    assert derived.expression == "800 nm / 10"


def test_alignment_and_comparison_permissions_are_closed_variants() -> None:
    reported = ReportedFact(
        key=ReferenceFactName.FOCUS_EFFICIENCY,
        value=PublishedQuantity(Decimal("0.5"), "ratio"),
        meaning="Contract-fixture focus efficiency.",
        sources=(SOURCE,),
        measure_meaning=FOCUS_MEANING,
    )
    not_reported = NotReportedFact(
        key=ReferenceFactName.FOCAL_SHIFT,
        meaning="Focal shift.",
        reviewed_sources=(SOURCE,),
        reason="No focal shift is reported.",
    )

    alignments = (
        MatchedAlignment(
            BenchmarkSubject.WAVELENGTH,
            ReferenceFactName.WAVELENGTH,
        ),
        AdaptedAlignment(
            BenchmarkSubject.FOCAL_LENGTH,
            ReferenceFactName.FOCAL_LENGTH,
            "The compact contract fixture adapts the focal length.",
        ),
        IndependentAlignment(
            BenchmarkSubject.ASPECT_LIMIT,
            "The brief supplies the process input.",
        ),
        WithheldAlignment(
            BenchmarkSubject.CELL_PERIOD,
            ReferenceFactName.CELL_PERIOD,
        ),
        ExcludedAlignment(
            BenchmarkSubject.FABRICATION_ROUTE,
            "Exact paper fabrication is outside the benchmark.",
        ),
    )
    rules = (
        SignedDifferenceRule(
            BenchmarkMeasure.FOCUS_EFFICIENCY,
            reported.key,
            required_matched_subjects=(BenchmarkSubject.WAVELENGTH,),
        ),
        ContextRule(
            BenchmarkMeasure.ATOM_HEIGHT,
            reported.key,
            "The paper height is context, not a threshold.",
        ),
        NotReportedRule(BenchmarkMeasure.FOCAL_SHIFT, not_reported.key),
        NotApplicableRule(
            BenchmarkMeasure.ORIENTATION_RELATION,
            "Propagation phase has no orientation relation.",
        ),
    )

    assert tuple(item.kind.value for item in alignments) == (
        "matched",
        "adapted",
        "independent",
        "withheld",
        "excluded",
    )
    assert tuple(rule.kind.value for rule in rules) == (
        "signed difference",
        "context",
        "not reported",
        "not applicable",
    )


def test_malformed_fact_values_raise_stable_value_errors() -> None:
    with pytest.raises(ValueError, match="published_quantity_invalid"):
        PublishedQuantity(Decimal("NaN"), "ratio")
    with pytest.raises(ValueError, match="reported_fact_source_missing"):
        ReportedFact(
            key=ReferenceFactName.FOCUS_EFFICIENCY,
            value=PublishedQuantity(Decimal("0.5"), "ratio"),
            meaning="Contract-fixture focus efficiency.",
            sources=(),
        )


def test_public_value_and_case_constructors_separate_type_from_value_errors() -> None:
    case = mcclung_benchmark_case()

    with pytest.raises(TypeError, match="source_locator_type_invalid"):
        SourceLocator(cast(str, object()), "Figure 3")
    with pytest.raises(ValueError, match="source_locator_incomplete"):
        SourceLocator(" ", "Figure 3")
    with pytest.raises(TypeError, match="measure_meaning_type_invalid"):
        MeasureMeaning(
            unit=cast(str, object()),
            scope="contract fixture",
            normalization="incident power",
            definition="Focused fraction.",
        )
    with pytest.raises(ValueError, match="measure_meaning_incomplete"):
        MeasureMeaning(
            unit="ratio",
            scope=" ",
            normalization="incident power",
            definition="Focused fraction.",
        )
    with pytest.raises(TypeError, match="metalens_benchmark_case_type_invalid"):
        replace(case, name=cast(str, object()))
    with pytest.raises(
        ValueError,
        match="metalens_benchmark_case_identity_incomplete",
    ):
        replace(case, name=" ")


def test_signed_difference_requires_at_least_one_matched_subject() -> None:
    with pytest.raises(
        ValueError,
        match="signed_difference_required_matches_missing",
    ):
        SignedDifferenceRule(
            BenchmarkMeasure.FOCUS_EFFICIENCY,
            ReferenceFactName.FOCUS_EFFICIENCY,
            required_matched_subjects=(),
        )


def test_signed_difference_requires_measure_and_fact_identity() -> None:
    with pytest.raises(
        ValueError,
        match="signed_difference_measure_fact_mismatch",
    ):
        SignedDifferenceRule(
            BenchmarkMeasure.FOCUS_EFFICIENCY,
            ReferenceFactName.CELL_PERIOD,
            required_matched_subjects=(BenchmarkSubject.WAVELENGTH,),
        )


def test_result_measure_constructors_reject_arbitrary_runtime_objects() -> None:
    with pytest.raises(TypeError, match="result_quantity_measure_type_invalid"):
        ResultQuantityMeasure(
            cast(Decimal, object()),
            FOCUS_MEANING,
            (RESULT_REFERENCE,),
        )
    with pytest.raises(TypeError, match="result_range_measure_type_invalid"):
        ResultRangeMeasure(
            Decimal("0.1"),
            cast(Decimal, object()),
            FOCUS_MEANING,
            (RESULT_REFERENCE,),
        )
    with pytest.raises(TypeError, match="result_text_measure_type_invalid"):
        ResultTextMeasure(
            cast(str, object()),
            "Definition.",
            (RESULT_REFERENCE,),
        )
    with pytest.raises(
        TypeError,
        match="result_geometry_measure_geometry_invalid",
    ):
        ResultGeometryMeasure(
            cast(CircleGeometryRange, object()),
            (RESULT_REFERENCE,),
        )
    with pytest.raises(
        TypeError,
        match="result_geometry_measure_references_invalid",
    ):
        ResultGeometryMeasure(
            CircleGeometryRange(80, 120),
            cast(tuple[Reference, ...], (object(),)),
        )
    with pytest.raises(TypeError, match="result_measure_absence_type_invalid"):
        ResultMeasureUnavailable(cast(str, object()))
    with pytest.raises(
        ValueError,
        match="result_geometry_measure_references_missing",
    ):
        ResultGeometryMeasure(CircleGeometryRange(80, 120), ())


def test_result_measure_frame_rejects_arbitrary_observations() -> None:
    unavailable = ResultMeasureUnavailable("Legitimately unavailable.")
    measures = replace(_result_measures(), focus_efficiency=unavailable)

    assert measures.focus_efficiency is unavailable
    with pytest.raises(TypeError, match="benchmark_result_measure_type_invalid"):
        replace(
            measures,
            focus_efficiency=cast(ResultMeasureUnavailable, object()),
        )


def test_result_measure_frame_rejects_a_wrong_measure_runtime_type() -> None:
    with pytest.raises(TypeError, match="benchmark_measure_required"):
        _result_measures().measure_for(cast(BenchmarkMeasure, object()))


def test_comparison_contract_requires_one_explicit_rule_per_frame_measure() -> None:
    rules = tuple(
        NotApplicableRule(measure, "Not used by this contract fixture.")
        for measure in BENCHMARK_MEASURE_FRAME
    )

    contract = ComparisonContract(rules)

    assert tuple(rule.measure for rule in contract.rules) == (BENCHMARK_MEASURE_FRAME)
    with pytest.raises(ValueError, match="comparison_rule_frame_invalid"):
        ComparisonContract(rules[:-1])
    with pytest.raises(ValueError, match="comparison_rule_frame_invalid"):
        ComparisonContract(tuple(reversed(rules)))


def test_comparison_contract_rejects_a_wrong_reference_runtime_type() -> None:
    rules = tuple(
        NotApplicableRule(measure, "Not used by this contract fixture.")
        for measure in BENCHMARK_MEASURE_FRAME
    )

    with pytest.raises(TypeError, match="published_reference_required"):
        ComparisonContract(rules).compare(
            _result_measures(),
            reference=cast(PublishedReference, object()),
            alignment=mcclung_benchmark_case().alignment,
        )


def test_signed_difference_requires_matching_complete_numeric_meaning() -> None:
    published = ReportedFact(
        key=ReferenceFactName.FOCUS_EFFICIENCY,
        value=PublishedQuantity(Decimal("0.50"), "ratio"),
        meaning="Contract-fixture focus efficiency.",
        sources=(SOURCE,),
        measure_meaning=FOCUS_MEANING,
    )
    rules = tuple(
        (
            SignedDifferenceRule(
                measure,
                published.key,
                required_matched_subjects=(BenchmarkSubject.WAVELENGTH,),
            )
            if measure is BenchmarkMeasure.FOCUS_EFFICIENCY
            else NotApplicableRule(measure, "Not used by this contract fixture.")
        )
        for measure in BENCHMARK_MEASURE_FRAME
    )
    observed = ResultQuantityMeasure(
        value=Decimal("0.56"),
        meaning=FOCUS_MEANING,
        source_references=(RESULT_REFERENCE,),
    )
    measures = _result_measures(focus_efficiency=observed)

    comparisons = ComparisonContract(rules).compare(
        measures,
        reference=_comparison_reference(published),
        alignment=mcclung_benchmark_case().alignment,
    )
    focus = comparisons[
        BENCHMARK_MEASURE_FRAME.index(BenchmarkMeasure.FOCUS_EFFICIENCY)
    ]

    assert isinstance(focus, ComparableMeasureComparison)
    assert focus.observed.value == Decimal("0.56")
    assert focus.reference.value.value == Decimal("0.50")
    assert focus.signed_difference == Decimal("0.06")
    with pytest.raises(ValueError, match="comparable_difference_invalid"):
        ComparableMeasureComparison(
            measure=BenchmarkMeasure.FOCUS_EFFICIENCY,
            observed=observed,
            reference=published,
            signed_difference=Decimal("NaN"),
        )


def test_signed_difference_rejects_an_empty_or_differently_defined_observation() -> (
    None
):
    published = ReportedFact(
        key=ReferenceFactName.FOCUS_EFFICIENCY,
        value=PublishedQuantity(Decimal("0.50"), "ratio"),
        meaning="Contract-fixture focus efficiency.",
        sources=(SOURCE,),
        measure_meaning=FOCUS_MEANING,
    )
    rules = tuple(
        (
            SignedDifferenceRule(
                measure,
                published.key,
                required_matched_subjects=(BenchmarkSubject.WAVELENGTH,),
            )
            if measure is BenchmarkMeasure.FOCUS_EFFICIENCY
            else NotApplicableRule(measure, "Not used by this contract fixture.")
        )
        for measure in BENCHMARK_MEASURE_FRAME
    )
    contract = ComparisonContract(rules)

    with pytest.raises(ValueError, match="comparable_observation_missing"):
        contract.compare(
            _result_measures(),
            reference=_comparison_reference(published),
            alignment=mcclung_benchmark_case().alignment,
        )

    mismatched = ResultQuantityMeasure(
        value=Decimal("0.56"),
        meaning=MeasureMeaning(
            unit="ratio",
            scope="contract fixture",
            normalization="focused power / transmitted power",
            definition=FOCUS_MEANING.definition,
        ),
        source_references=(RESULT_REFERENCE,),
    )
    with pytest.raises(ValueError, match="comparable_meaning_mismatch"):
        contract.compare(
            _result_measures(focus_efficiency=mismatched),
            reference=_comparison_reference(published),
            alignment=mcclung_benchmark_case().alignment,
        )


@pytest.mark.parametrize("relation_kind", ["withheld", "adapted"])
def test_signed_difference_rejects_a_required_relation_that_is_not_matched(
    relation_kind: str,
) -> None:
    case = mcclung_benchmark_case()
    published = case.reference.fact(ReferenceFactName.FOCUS_EFFICIENCY)
    assert isinstance(published, ReportedFact)
    rules = tuple(
        (
            SignedDifferenceRule(
                measure,
                published.key,
                required_matched_subjects=(BenchmarkSubject.WAVELENGTH,),
            )
            if measure is BenchmarkMeasure.FOCUS_EFFICIENCY
            else NotApplicableRule(measure, "Not used by this contract fixture.")
        )
        for measure in BENCHMARK_MEASURE_FRAME
    )
    relation = (
        WithheldAlignment(
            BenchmarkSubject.WAVELENGTH,
            ReferenceFactName.WAVELENGTH,
        )
        if relation_kind == "withheld"
        else AdaptedAlignment(
            BenchmarkSubject.WAVELENGTH,
            ReferenceFactName.WAVELENGTH,
            "The wavelength differs in this contract fixture.",
        )
    )
    relations = tuple(
        relation if item.subject is BenchmarkSubject.WAVELENGTH else item
        for item in case.alignment.relations
    )
    alignment = BenchmarkAlignment(relations)

    with pytest.raises(
        ValueError,
        match="signed_difference_required_match_invalid",
    ):
        ComparisonContract(rules).compare(
            _result_measures(
                focus_efficiency=ResultQuantityMeasure(
                    value=Decimal("0.84"),
                    meaning=published.measure_meaning,
                    source_references=(RESULT_REFERENCE,),
                )
            ),
            reference=case.reference,
            alignment=alignment,
        )


def test_benchmark_case_rejects_a_signed_rule_with_an_adapted_requirement() -> None:
    case = mcclung_benchmark_case()
    rules = tuple(
        (
            SignedDifferenceRule(
                rule.measure,
                ReferenceFactName.FOCUS_EFFICIENCY,
                required_matched_subjects=(BenchmarkSubject.WAVELENGTH,),
            )
            if rule.measure is BenchmarkMeasure.FOCUS_EFFICIENCY
            else rule
        )
        for rule in case.contract.rules
    )
    relations = tuple(
        (
            AdaptedAlignment(
                BenchmarkSubject.WAVELENGTH,
                ReferenceFactName.WAVELENGTH,
                "The wavelength differs in this contract fixture.",
            )
            if item.subject is BenchmarkSubject.WAVELENGTH
            else item
        )
        for item in case.alignment.relations
    )

    with pytest.raises(
        ValueError,
        match="signed_difference_required_match_invalid",
    ):
        replace(
            case,
            alignment=BenchmarkAlignment(relations),
            contract=ComparisonContract(rules),
        )


def _result_measures(
    *,
    focus_efficiency: ResultQuantityMeasure | None = None,
) -> BenchmarkResultMeasures:
    unavailable = ResultMeasureUnavailable("Not observed by this contract fixture.")
    return BenchmarkResultMeasures(
        cell_period=unavailable,
        atom_height=unavailable,
        lateral_geometry=unavailable,
        phase_coverage=unavailable,
        transmitted_magnitude=unavailable,
        transmitted_power=unavailable,
        spatial_phase_sampling=unavailable,
        orientation_relation=unavailable,
        polarization_conversion=unavailable,
        focus_efficiency=(
            unavailable if focus_efficiency is None else focus_efficiency
        ),
        focal_shift=unavailable,
        x_half_maximum_width=unavailable,
        y_half_maximum_width=unavailable,
        mean_half_maximum_width=unavailable,
        vertical_cut_half_maximum_width=unavailable,
        transmitted_fraction=unavailable,
        focused_fraction=unavailable,
        complex_focal_field=unavailable,
        longitudinal_power_fraction=unavailable,
    )


def _comparison_reference(
    *facts: ReportedFact[PublishedQuantity],
) -> PublishedReference:
    return PublishedReference(
        citation="contract-fixture",
        selected_device="contract fixture",
        facts=facts,
        exclusions=(),
    )


def test_private_mcclung_case_preserves_blindness_and_paper_separation() -> None:
    case = mcclung_benchmark_case()
    period = case.reference.fact(ReferenceFactName.CELL_PERIOD)
    aspect = case.alignment.relation(BenchmarkSubject.ASPECT_LIMIT)

    assert case.brief.atom.material.family == "silicon nitride"
    assert case.reference.fact(ReferenceFactName.ATOM_MATERIAL).value == (
        "silicon nitride"
    )
    assert isinstance(
        case.alignment.relation(BenchmarkSubject.ATOM_SHAPE),
        AdaptedAlignment,
    )
    assert case.brief.aspect_limit == 8
    assert case.brief.cell_period_nm is None
    assert case.brief.atom_height_nm is None
    assert isinstance(period, ReportedFact)
    assert period.value == PublishedQuantity(Decimal("430"), "nm")
    assert isinstance(aspect, IndependentAlignment)
    assert tuple(rule.measure for rule in case.contract.rules) == (
        BENCHMARK_MEASURE_FRAME
    )
    blind_document = case.brief.canonical_bytes()
    for withheld_paper_value in (
        b"430",
        b"650",
        b"6 mm",
        b"14.7",
        b"triangular",
        b"hexagonal",
        b"310",
        b"120",
        b"0.902",
        b"81",
        b"89",
    ):
        assert withheld_paper_value not in blind_document
    canonical = case.document().to_bytes()
    assert canonical.count(b"0.902") == 1
    assert canonical.count(b"430") == 1
    assert examples.__all__ == [
        "MetalensBenchmarkCase",
        "metalens_benchmark_cases",
        "select_metalens_benchmark_case",
    ]


def test_private_mcclung_case_uses_the_reviewed_material_registrations() -> None:
    case = mcclung_benchmark_case()
    library = SolverMaterialLibrary.decode_bytes(
        (ROOT / "materials" / "lumerical.toml").read_bytes()
    )

    atom = library.select(case.brief.atom.material.family)
    substrate = library.select(case.brief.substrate.family)

    assert atom is not None
    assert atom.native_name == "Si3N4 (Silicon Nitride) - Luke"
    assert substrate is not None
    assert substrate.native_name == "SiO2 (Glass) - Palik"


def test_private_mcclung_case_is_canonical_and_strictly_restorable() -> None:
    case = mcclung_benchmark_case()
    document = Document.from_bytes(case.document().to_bytes())

    restored = restore_metalens_benchmark_case(document)

    assert restored is case
    assert len(case.document().to_bytes()) == 13177
    assert case.identity == (
        "sha256:dcf0c4232894817251e9e92837c869f9fa13917c7ed86e7e" "2200f0e68eec59d3"
    )
    changed = dict(document.values)
    changed["selected_device"] = "changed"
    with pytest.raises(
        ValueError,
        match="metalens_benchmark_case_document_mismatch",
    ):
        restore_metalens_benchmark_case(Document(document.schema_identifier, changed))
    with pytest.raises(
        ValueError,
        match="metalens_benchmark_case_schema_invalid",
    ):
        restore_metalens_benchmark_case(Document("foreign.case", {}))

    reordered = replace(
        case,
        reference=replace(
            case.reference,
            facts=tuple(reversed(case.reference.facts)),
            exclusions=tuple(reversed(case.reference.exclusions)),
        ),
    )
    assert reordered.document().to_bytes() == case.document().to_bytes()
    assert reordered.identity == case.identity


def test_private_mcclung_contract_fixture_restores_one_low_na_result(
    tmp_path: Path,
) -> None:
    case = _compact_mcclung_contract_fixture()
    recorded = propagation_results(
        tmp_path,
        (8,),
        brief=case.brief,
        period_nm=400,
        height_nm=500,
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

    assert comparison.case_identity == case.identity
    assert comparison.result_reference == result.reference
    assert comparison.result_measures.cell_period.value == Decimal("400")
    assert comparison.result_measures.atom_height.value == Decimal("500")
    assert tuple(item.measure for item in comparison.measures) == (
        BENCHMARK_MEASURE_FRAME
    )
    period = comparison.measures[0]
    assert isinstance(period, ContextMeasureComparison)
    assert isinstance(period.reference, ReportedFact)
    assert comparison.document().values["case_identity"] == case.identity


def test_private_case_rejects_wrong_callers_and_propagates_fetch_faults(
    tmp_path: Path,
) -> None:
    exact_case = mcclung_benchmark_case()
    fixture_case = _compact_mcclung_contract_fixture()
    recorded = propagation_results(
        tmp_path,
        (8,),
        brief=fixture_case.brief,
        period_nm=400,
        height_nm=500,
    )[0]
    result = Result(
        reference=admit_result(recorded),
        document=recorded.conclusion.document(),
        sources=recorded.conclusion.references(),
        closure=recorded.closure,
    )
    completed = CompletedResults((result,))

    with pytest.raises(TypeError, match="completed_results_required"):
        exact_case.compare(object(), fetch=recorded.authority.fetch)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="metalens_benchmark_brief_mismatch"):
        exact_case.compare(completed, fetch=recorded.authority.fetch)

    expected_fault = RuntimeError("reference_unresolvable: object missing")

    def missing_body(_reference: Reference) -> bytes:
        raise expected_fault

    with pytest.raises(RuntimeError) as raised:
        fixture_case.compare(completed, fetch=missing_body)
    assert raised.value is expected_fault


def test_typed_result_frame_accepts_all_four_current_contract_families(
    tmp_path: Path,
) -> None:
    low_propagation = _compact_mcclung_contract_fixture().brief
    low_geometric = replace(
        geometric_brief(),
        focal_length_um=Decimal("2"),
        numerical_aperture=Decimal("0.1"),
        aperture=None,
    )
    high_propagation = replace(
        propagation_brief(),
        focal_length_um=Decimal("0.25"),
        numerical_aperture=Decimal("0.8"),
        aperture=None,
    )
    high_geometric = replace(
        geometric_brief(),
        focal_length_um=Decimal("0.25"),
        numerical_aperture=Decimal("0.8"),
        aperture=None,
    )
    briefs = (
        low_propagation,
        low_geometric,
        high_propagation,
        high_geometric,
    )
    periods_nm = tuple(
        select_fixture_period_nm(brief, preferred_period_nm=400) for brief in briefs
    )
    conclusions = (
        propagation_results(
            tmp_path / "low-propagation-contract-fixture",
            (8,),
            brief=low_propagation,
            period_nm=periods_nm[0],
            height_nm=500,
        )[0].conclusion,
        geometric_results(
            tmp_path / "low-geometric-contract-fixture",
            (8,),
            brief=low_geometric,
            period_nm=periods_nm[1],
            height_nm=600,
        )[0].conclusion,
        pointwise_propagation_result(
            tmp_path / "high-propagation-contract-fixture",
            high_propagation,
            period_nm=periods_nm[2],
            height_nm=600,
        ).conclusion,
        pointwise_geometric_result(
            tmp_path / "high-geometric-contract-fixture",
            high_geometric,
            period_nm=periods_nm[3],
            height_nm=600,
        ).conclusion,
    )

    frames = tuple(restore_benchmark_result_measures(item) for item in conclusions)
    period_measures = tuple(frame.cell_period for frame in frames)

    assert all(isinstance(frame, BenchmarkResultMeasures) for frame in frames)
    assert all(isinstance(item, ResultQuantityMeasure) for item in period_measures)
    assert tuple(
        cast(ResultQuantityMeasure, item).value for item in period_measures
    ) == tuple(Decimal(period_nm) for period_nm in periods_nm)
    assert all(
        frame.measure_for(measure) is not None
        for frame in frames
        for measure in BENCHMARK_MEASURE_FRAME
    )


def test_typed_result_frame_rejects_an_unknown_result_runtime_type() -> None:
    unknown_result = cast(MetalensResult, object())

    with pytest.raises(
        TypeError,
        match="metalens_benchmark_result_type_unsupported",
    ):
        restore_benchmark_result_measures(unknown_result)


def _compact_mcclung_contract_fixture() -> MetalensBenchmarkCase:
    """Name a small contract fixture without changing reviewed paper truth."""

    case = mcclung_benchmark_case()
    brief = replace(
        case.brief,
        wording=(
            "Exercise the low-NA propagation Result contract at bounded scale; "
            "this is not the McClung benchmark outcome."
        ),
        numerical_aperture=Decimal("0.1"),
        focal_length_um=Decimal("2"),
        aperture=None,
    )
    relations = tuple(
        (
            AdaptedAlignment(
                relation.subject,
                relation.fact,
                "The bounded contract fixture adapts this optical condition.",
            )
            if (
                isinstance(relation, MatchedAlignment)
                and relation.subject
                in {
                    BenchmarkSubject.NUMERICAL_APERTURE,
                    BenchmarkSubject.FOCAL_LENGTH,
                }
            )
            or (
                isinstance(relation, WithheldAlignment)
                and relation.subject is BenchmarkSubject.APERTURE
            )
            else relation
        )
        for relation in case.alignment.relations
    )
    return replace(
        case,
        name="mcclung-low-na-propagation-contract-fixture",
        brief=brief,
        alignment=BenchmarkAlignment(relations),
    )
