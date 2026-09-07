from __future__ import annotations

from pathlib import Path

from metacraft.canonical import encode_bytes
from metacraft.command import encode_conduct_outcome
from metacraft.science.compile import InvalidBrief, UnsupportedAim, compile_study
from metacraft.science.conduct import (
    CompletedResults,
    ConsultationRequired,
    WaitingStudies,
    _admit_result,
)
from metacraft.science.metalens.consultation import (
    form_period_consultation_request,
)
from metacraft.science.study import Study
from tests.brief_fixtures import propagation_brief
from tests.domain_fixtures import period_domain
from tests.result_fixtures import propagation_result


def _expected(name: str, value: object) -> bytes:
    return (
        b'{"schema":"metacraft.command.conduct_outcome","outcome":"'
        + name.encode()
        + b'","value":'
        + encode_bytes(value)
        + b"}"
    )


def _result_value(result) -> dict[str, object]:
    return {
        "closure": result.closure.as_mapping(),
        "document": result.document.as_mapping(),
        "reference": result.reference.as_mapping(),
        "sources": [reference.as_mapping() for reference in result.sources],
    }


def test_all_five_conduct_outcomes_have_exact_closed_bytes(
    tmp_path: Path,
) -> None:
    study = compile_study(propagation_brief())
    assert isinstance(study, Study)
    required = ConsultationRequired(
        form_period_consultation_request(
            propagation_brief(),
            period_domain(study),
        ),
        (study,),
    )
    waiting = WaitingStudies((study,))
    recorded = propagation_result(tmp_path / "completed root", 8)
    result = _admit_result(recorded.session, recorded.study)
    completed = CompletedResults((result,))
    study_value = study.document().as_mapping()

    cases = (
        (
            InvalidBrief("brief_incomplete:fixture"),
            "invalid_brief",
            {"reason": "brief_incomplete:fixture"},
        ),
        (
            UnsupportedAim("全息超表面"),
            "unsupported_aim",
            {"aim": "全息超表面"},
        ),
        (
            required,
            "consultation_required",
            {
                "request": required.request.document().as_mapping(),
                "studies": [study_value],
            },
        ),
        (waiting, "waiting_studies", {"studies": [study_value]}),
        (
            completed,
            "completed_results",
            {
                "brief_identity": completed.brief_identity,
                "results": [_result_value(result)],
            },
        ),
    )

    for outcome, name, value in cases:
        assert encode_conduct_outcome(outcome) == _expected(name, value)
