from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from examples import (
    metalens_benchmark_cases,
    select_metalens_benchmark_case,
)
from examples.metalens_benchmark.case import MetalensBenchmarkCase
from examples.metalens_benchmark.contract import (
    ReferenceFactName,
    UnresolvedFact,
)
from examples.recorded_metalens_evidence import (
    RecordedMetalensEvidenceAdapter,
)
from metacraft.authority import Authority, Document
from metacraft.science.conduct import (
    CompletedResults,
    WaitingStudies,
    conduct,
)
from metacraft.science.metalens.evidence_adapter import (
    MetalensEvidenceAdapter,
)


EXACT_CASES = (
    ("mcclung-2024-low-na-propagation", 8),
    ("yang-2018-low-na-geometric", 8),
    ("arbabi-2015-high-na-propagation", 8),
    ("khorasaninejad-2016-high-na-geometric", 8),
)


def test_recorded_adapter_opens_replay_ports_without_current_activity(
    tmp_path: Path,
) -> None:
    application_root = tmp_path / "application-root"
    runs_directory = application_root / "runs"
    runs_directory.mkdir(parents=True)
    authority = Authority(application_root / "authority")
    adapter: MetalensEvidenceAdapter = RecordedMetalensEvidenceAdapter()

    periodic, materials = adapter.open(
        authority=authority,
        runs_directory=runs_directory,
    )

    assert periodic.context.binding_reference == materials.context.binding_reference
    activity = periodic.context.qualification_closure
    assert activity.acquired_authority_work_count == 0
    assert activity.started_external_execution_count == 0
    assert activity.opened_product_session_count == 0
    assert activity.opened_local_placement_count == 0
    assert authority.fetch(periodic.context.binding_reference)
    assert authority.view().permits == ()


def test_recorded_adapter_requires_one_explicit_runs_directory(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")

    with patch.object(
        Authority,
        "fetch",
        side_effect=AssertionError("adapter must stop before Authority reads"),
    ):
        try:
            RecordedMetalensEvidenceAdapter().open(
                authority=authority,
                runs_directory=tmp_path / "missing-runs",
            )
        except ValueError as error:
            assert str(error) == "recorded_runs_directory_missing"
        else:
            raise AssertionError("missing recorded runs must remain explicit")


def test_exact_four_case_catalogue_stops_at_truthful_recorded_boundary(
    tmp_path: Path,
) -> None:
    cases = metalens_benchmark_cases()
    assert tuple((case.name, case.brief.aspect_limit) for case in cases) == EXACT_CASES
    assert tuple(select_metalens_benchmark_case(case.name) for case in cases) == cases

    blind_inputs = tuple(
        (case.name, case.brief, case.identity)
        for case in cases
    )
    assert len({identity for _, _, identity in blind_inputs}) == len(EXACT_CASES)

    original_attribute = MetalensBenchmarkCase.__getattribute__

    def reject_published_truth(
        case: MetalensBenchmarkCase,
        attribute: str,
    ) -> object:
        if attribute in {"reference", "alignment", "contract"}:
            raise AssertionError(
                f"published benchmark meaning read before Results: {attribute}"
            )
        return original_attribute(case, attribute)

    outcomes = []
    roots = []
    with patch.object(
        MetalensBenchmarkCase,
        "__getattribute__",
        reject_published_truth,
    ):
        for name, brief, _identity in blind_inputs:
            application_root = tmp_path / name
            roots.append(application_root)
            outcomes.append(
                conduct(
                    brief,
                    application_root=application_root,
                    evidence_adapter=RecordedMetalensEvidenceAdapter(),
                )
            )

    comparison_batches = []
    for case, application_root, outcome in zip(
        cases,
        roots,
        outcomes,
        strict=True,
    ):
        if isinstance(outcome, CompletedResults):
            comparison_batches.append(
                case.compare(
                    outcome,
                    fetch=Authority(application_root / "authority").fetch,
                )
            )
            continue

        assert isinstance(outcome, WaitingStudies)
        assert any(
            finding.claim == "material_binding"
            and finding.needs[0].startswith(
                "material_unavailable:recorded_observation_missing:"
            )
            for study in outcome.studies
            for finding in study.findings
        )
        assert Authority(application_root / "authority").view().permits == ()

    assert comparison_batches == []
    assert all(isinstance(outcome, WaitingStudies) for outcome in outcomes)
    assert tuple(path.name for path in roots) == tuple(
        name for name, _aspect_limit in EXACT_CASES
    )

    mcclung_period = cases[0].reference.fact(ReferenceFactName.CELL_PERIOD)
    assert not isinstance(mcclung_period, UnresolvedFact)
    assert mcclung_period.value is not None


def test_waiting_cadence_never_needs_a_borrowed_result_document(
    tmp_path: Path,
) -> None:
    case = select_metalens_benchmark_case(EXACT_CASES[0][0])
    application_root = tmp_path / case.name

    outcome = conduct(
        case.brief,
        application_root=application_root,
        evidence_adapter=RecordedMetalensEvidenceAdapter(),
    )

    assert isinstance(outcome, WaitingStudies)
    assert not isinstance(outcome, CompletedResults)
    authority = Authority(application_root / "authority")
    view = authority.view()
    current_schemas = tuple(
        Document.from_bytes(
            authority.fetch(record.body_reference)
        ).schema_identifier
        for record in view.current
    )
    assert all(
        not record.key.startswith("completed_results:")
        for record in view.current
    )
    assert "metacraft.science.completed_results" not in current_schemas
    assert all("benchmark" not in schema for schema in current_schemas)
