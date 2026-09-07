"""Prepare one fresh, response-ready propagation pilot root."""

from __future__ import annotations

from pathlib import Path
import sys

from examples import select_metalens_benchmark_case
from metacraft.materials import SolverMaterialLibrary
from metacraft.science.conduct import ConsultationRequired, WaitingStudies, conduct
from metacraft.science.consultation import (
    ConsultationAnswer,
    ExternalClaim,
    Recommendation,
)
from metacraft.solvers.lumerical_fdtd import (
    LumericalConfig,
    read_lumerical_environment,
)
from metacraft.solvers.lumerical_fdtd.metalens_evidence import (
    LumericalMetalensEvidence,
)
from propagation_cases import PropagationPilotCase, propagation_case


REPOSITORY = Path(__file__).parents[2]
PILOT = Path(__file__).parent


def main(arguments: list[str] | None = None) -> None:
    values = sys.argv[1:] if arguments is None else arguments
    if len(values) != 1:
        raise ValueError("propagation_pilot_case_required")
    case = propagation_case(values[0])
    application_root = PILOT / "acceptance" / f"{case.stem}-live-root"
    brief = select_metalens_benchmark_case(case.benchmark_name).brief
    environment = read_lumerical_environment(REPOSITORY / ".env.lumerical")
    config = LumericalConfig.from_environ(environment)
    library = SolverMaterialLibrary.decode_bytes(
        (REPOSITORY / "materials" / "lumerical.toml").read_bytes()
    )
    adapter = LumericalMetalensEvidence(config, library)

    if application_root.exists():
        height_wait = conduct(brief, application_root=application_root)
    else:
        period_wait = conduct(
            brief,
            application_root=application_root,
            evidence_adapter=adapter,
        )
        if not isinstance(period_wait, ConsultationRequired):
            raise RuntimeError("propagation_period_consultation_not_required")
        period_candidate = _candidate(period_wait, case.period_nm)
        period_claim = ExternalClaim(
            statement=(
                "A usable lattice balances spatial sampling, unwanted "
                "diffraction risk, feature room, and simulation cost."
            ),
            locator=(
                "https://optics.ansys.com/hc/en-us/articles/"
                "35797097445779-Introduction-to-metalens-workflows"
            ),
        )
        period_answer = _recommend(
            period_wait,
            period_candidate.identity,
            reason=case.period_reason,
            claim=period_claim,
        )
        _write(
            case,
            "period-request.json",
            period_wait.request.document().to_bytes(),
        )
        _write(case, "period-answer.json", period_answer.document().to_bytes())
        height_wait = conduct(
            brief,
            application_root=application_root,
            consultation_answer=period_answer,
        )

    if not isinstance(height_wait, ConsultationRequired):
        raise RuntimeError("propagation_height_consultation_not_required")
    height_candidate = _candidate(height_wait, case.height_nm)
    height_claim = ExternalClaim(
        statement=(
            "Propagation-phase optical path accumulation scales approximately "
            "with effective-index contrast and atom height and must later be "
            "verified by a periodic response sweep."
        ),
        locator=(
            "https://optics.ansys.com/hc/en-us/articles/"
            "360042097313-Metalens"
        ),
    )
    height_answer = _recommend(
        height_wait,
        height_candidate.identity,
        reason=case.height_reason,
        claim=height_claim,
        ground_identities=_height_grounds(height_wait, case.height_nm),
    )
    _write(
        case,
        "height-request.json",
        height_wait.request.document().to_bytes(),
    )
    _write(case, "height-answer.json", height_answer.document().to_bytes())

    waiting = conduct(
        brief,
        application_root=application_root,
        consultation_answer=height_answer,
    )
    if not isinstance(waiting, WaitingStudies):
        raise RuntimeError("propagation_did_not_stop_before_periodic_response")
    print("outcome=waiting_studies")
    print(f"case={case.stem}")
    print(f"study_count={len(waiting.studies)}")


def _candidate(waiting: ConsultationRequired, quantity: int):
    matches = tuple(
        candidate
        for candidate in waiting.request.candidates
        if int(candidate.quantity) == quantity
    )
    if len(matches) != 1:
        raise RuntimeError(f"consultation_candidate_missing:{quantity}")
    return matches[0]


def _height_grounds(
    waiting: ConsultationRequired,
    height_nm: int,
) -> tuple[str, ...]:
    prefixes = (
        "working wavelength:",
        "control strategy:",
        "selected period:",
        f"height {height_nm} nm fabrication range:",
        f"height {height_nm} nm certified standings:",
    )
    identities = tuple(
        ground.identity
        for ground in waiting.request.grounds
        if ground.statement.startswith(prefixes)
    )
    if not identities:
        raise RuntimeError("propagation_height_decisive_grounds_missing")
    return identities


def _recommend(
    waiting: ConsultationRequired,
    candidate_identity: str,
    *,
    reason: str,
    claim: ExternalClaim,
    ground_identities: tuple[str, ...] | None = None,
) -> ConsultationAnswer:
    return ConsultationAnswer(
        request_identity=waiting.request.identity,
        conclusion=Recommendation(
            candidate_identity=candidate_identity,
            reason=reason,
            decisive_ground_identities=(
                tuple(ground.identity for ground in waiting.request.grounds)
                if ground_identities is None
                else ground_identities
            ),
            external_claim_identities=(claim.identity,),
        ),
        external_claims=(claim,),
    )


def _write(case: PropagationPilotCase, suffix: str, content: bytes) -> None:
    (PILOT / "acceptance" / f"{case.stem}-{suffix}").write_bytes(content)


if __name__ == "__main__":
    main()
