from __future__ import annotations

from pathlib import Path

from metacraft.science.metalens.result import (
    PropagationResult,
    conclude,
    restore_conclusion,
)
from metacraft.science.result import Result, restore_admitted_result
from tests.result_fixtures import admit_result, propagation_results


def test_result_document_contains_scientific_conclusion_only(
    tmp_path: Path,
) -> None:
    recorded = propagation_results(tmp_path)[0]
    result = recorded.conclusion

    assert isinstance(result, PropagationResult)
    assert set(result.document().values) == {
        "closure",
        "conclusion",
        "evidence",
        "evaluation",
        "fabrication",
        "origin",
        "provenance",
    }
    encoded = result.document().to_bytes()
    for project_owned_name in (
        b"case_identity",
        b"case_name",
        b"fidelity",
        b"paper_revision",
        b"published_metrics",
        b"advice_comparison",
    ):
        assert project_owned_name not in encoded
    assert conclude(
        recorded.study,
        recorded.closure,
        fetch=recorded.authority.fetch,
    ).document().to_bytes() == result.document().to_bytes()


def test_admitted_result_exposes_its_complete_scientific_study(
    tmp_path: Path,
) -> None:
    recorded = propagation_results(tmp_path)[0]
    conclusion = recorded.conclusion
    result = Result(
        reference=admit_result(recorded),
        document=conclusion.document(),
        sources=conclusion.references(),
        closure=recorded.closure,
    )

    assert (
        result.closure.compiled.canonical_bytes()
        == recorded.study.canonical_bytes()
    )
    assert result.closure.study.reference in result.sources


def test_admitted_result_restores_from_its_reference_without_recompiling(
    tmp_path: Path,
) -> None:
    recorded = propagation_results(tmp_path)[0]
    result_reference = admit_result(recorded)

    restored = restore_admitted_result(
        result_reference,
        fetch=recorded.authority.fetch,
        restore_conclusion=restore_conclusion,
    )

    assert restored.reference == result_reference
    assert (
        restored.closure.compiled.canonical_bytes()
        == recorded.study.canonical_bytes()
    )
    assert restored.document.to_bytes() == (
        recorded.conclusion.document().to_bytes()
    )
