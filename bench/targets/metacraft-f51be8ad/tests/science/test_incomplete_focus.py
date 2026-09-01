from __future__ import annotations

import pytest

from metacraft.authority import reference_for
from tests.brief_fixtures import propagation_brief
from metacraft.science import (
    Finding,
    FindingKind,
)
from metacraft.science.metalens.compiler import compile_metalens


def test_incomplete_focus_waits_beside_its_diagnostic_record() -> None:
    """
    Keep incomplete focus outside claim-closing evidence.
    """

    diagnostic = reference_for(b"reviewed incomplete focus")
    finding = Finding(
        claim="focus",
        kind=FindingKind.INCOMPLETE,
        needs=("focus_incomplete",),
        record_references=(diagnostic,),
    )

    study = compile_metalens(
        propagation_brief(),
        reported_findings=(finding,),
    )

    assert finding in study.findings
    assert all(fact.claim != "focus" for fact in study.evidence)
    assert all(task.claim != "focus" for task in study.ready_tasks)


@pytest.mark.parametrize(
    "finding",
    (
        Finding(
            claim="unknown claim",
            kind=FindingKind.REFUSAL,
            needs=("focus_incomplete",),
        ),
        Finding(
            claim="focus",
            kind=FindingKind.INCOMPLETE,
            needs=("wrong_need",),
            record_references=(reference_for(b"diagnostic"),),
        ),
    ),
)
def test_invalid_reported_focus_findings_are_rejected(
    finding: Finding,
) -> None:
    """
    Reject malformed externally reported focus findings.
    """

    with pytest.raises(ValueError, match="reported_finding_invalid"):
        compile_metalens(
            propagation_brief(),
            reported_findings=(finding,),
        )


def test_incomplete_focus_requires_one_diagnostic_record() -> None:
    """
    Require durable provenance for an incomplete finding.
    """

    with pytest.raises(ValueError, match="reported_finding_invalid"):
        compile_metalens(
            propagation_brief(),
            reported_findings=(
                Finding(
                    claim="focus",
                    kind=FindingKind.INCOMPLETE,
                    needs=("focus_incomplete",),
                ),
            ),
        )
