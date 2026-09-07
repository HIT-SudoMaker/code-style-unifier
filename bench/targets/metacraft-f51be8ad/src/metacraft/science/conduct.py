from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from ..authority import Authority
from ..authority.protocol import Document, Reference
from ..authority.session import AuthoritySession, CurrentAdmissionConflict
from ..materials import MaterialResponse, MaterialResponseContext

from ._application_root import (
    lock_application_root,
    open_existing_application_root,
    open_or_create_application_root,
)
from .brief import Brief
from .compile import InvalidBrief, UnsupportedAim, compile_study
from .consultation import ConsultationAnswer, ConsultationRequest
from .metalens.checkpoint import StudyFrontier
from .metalens.evidence_adapter import MetalensEvidenceAdapter
from .periodic_response import PeriodicResponse, PeriodicResponseContext
from .result import (
    BoundDocument,
    Result,
    ResultClosure,
    brief_document,
    design_document,
    restore_admitted_result,
    study_document,
)
from .study import FindingKind, Study


_COMPLETED_RESULTS_SCHEMA = "metacraft.science.completed_results"
_FRONTIER_REOBSERVATION_LIMIT = 32


class ConsultationAnswerRejected(ValueError):
    """
    Reject caller-supplied consultation input at the public conduct seam.
    """

    def __init__(self, reason: str) -> None:
        """
        Retain one closed rejection reason for the command boundary.
        """

        if reason not in {"duplicate", "invalid", "not_required", "stale"}:
            raise ValueError("consultation_answer_rejection_reason_invalid")
        self.reason = reason
        super().__init__(f"consultation_answer_rejected:{reason}")


@dataclass(frozen=True, slots=True)
class WaitingStudies:
    """
    Return the complete ordered frontier that currently needs external facts.
    """

    studies: tuple[Study, ...]

    def __post_init__(self) -> None:
        """
        Require at least one complete waiting Study.
        """

        if not self.studies:
            raise ValueError("waiting_studies_empty")


@dataclass(frozen=True, slots=True)
class CompletedResults:
    """
    Return every separately admitted scientific conclusion.
    """

    results: tuple[Result, ...]

    def __post_init__(self) -> None:
        """
        Require distinct conclusions for one shared brief.
        """

        if not self.results:
            raise ValueError("completed_results_empty")
        references = tuple(result.reference for result in self.results)
        if len(set(references)) != len(references):
            raise ValueError("completed_result_duplicate")
        if len({result.closure.brief_identity for result in self.results}) != 1:
            raise ValueError("completed_result_brief_mixed")

    @property
    def brief_identity(self) -> str:
        """
        Return the one brief identity shared by every completed result.
        """

        return self.results[0].closure.brief_identity


@dataclass(frozen=True, slots=True)
class ConsultationRequired:
    """
    Pause one conduct life at its exact next consultation request.
    """

    request: ConsultationRequest
    studies: tuple[Study, ...]

    def __post_init__(self) -> None:
        if not self.studies:
            raise ValueError("consultation_required_studies_empty")
        if any(
            study.brief_identity != self.request.brief_identity
            for study in self.studies
        ):
            raise ValueError("consultation_required_brief_mismatch")


ConductOutcome: TypeAlias = (
    ConsultationRequired
    | WaitingStudies
    | CompletedResults
    | InvalidBrief
    | UnsupportedAim
)


def conduct(
    brief: Brief,
    *,
    application_root: Path,
    evidence_adapter: MetalensEvidenceAdapter | None = None,
    consultation_answer: ConsultationAnswer | None = None,
) -> ConductOutcome:
    """
    Own one brief's complete fresh-application-root scientific life.

    Compilation happens before application-root access. Once valid, this operation
    alone recalls the admitted frontier, advances immutable Studies,
    checkpoints every accepted transition, and admits conclusions.
    """

    compiled = compile_study(brief)
    if not isinstance(compiled, Study):
        return compiled

    root = Path(application_root).expanduser().resolve()
    if consultation_answer is None:
        opened_root = open_or_create_application_root(root)
    else:
        try:
            opened_root = open_existing_application_root(root)
        except FileNotFoundError as error:
            raise ConsultationAnswerRejected("not_required") from error
    with lock_application_root(opened_root.runs_directory):
        return _conduct_locked(
            brief,
            compiled,
            authority=opened_root.authority,
            is_fresh=opened_root.is_fresh,
            runs_directory=opened_root.runs_directory,
            evidence_adapter=evidence_adapter,
            consultation_answer=consultation_answer,
        )


def _conduct_locked(
    brief: Brief,
    compiled: Study,
    *,
    authority: Authority,
    is_fresh: bool,
    runs_directory: Path,
    evidence_adapter: MetalensEvidenceAdapter | None,
    consultation_answer: ConsultationAnswer | None,
) -> ConductOutcome:
    """
    Advance one root after its non-scientific execution lock is held.
    """

    session = AuthoritySession(authority)
    frontier, frontier_reference = _recall_frontier(
        session,
        brief=brief,
        initial=compiled,
    )
    if frontier_reference is None:
        if not is_fresh:
            _raise_unrestorable_application_root(session, compiled)
        frontier = StudyFrontier.start(compiled)
        frontier_reference = _try_admit_frontier(
            session,
            frontier,
            supersedes=None,
        )
        if frontier_reference is None:
            raise RuntimeError("application_root_initialization_conflict")

    completed = _recall_completed_results(
        session,
        compiled,
        frontier=frontier,
        frontier_reference=frontier_reference,
    )
    if completed is not None:
        if consultation_answer is not None:
            raise ConsultationAnswerRejected("duplicate")
        return completed

    periodic_response: PeriodicResponse | None = None
    materials: MaterialResponse | None = None
    answer = consultation_answer
    has_opened_evidence = False
    while True:
        pending = _first_consultation(frontier, session=session)
        if pending is not None:
            position, study, request = pending
            if answer is None:
                return ConsultationRequired(request, frontier.studies)
            if any(
                getattr(advice, "request_identity", None) == answer.request_identity
                for candidate in frontier.studies
                for advice in candidate.advice
            ):
                raise ConsultationAnswerRejected("duplicate")
            if answer.request_identity != request.identity:
                raise ConsultationAnswerRejected("stale")
            from .metalens.conduct import accept_metalens_consultation
            from .metalens.consultation import (
                InvalidMetalensConsultationAnswer,
            )

            try:
                successor = accept_metalens_consultation(
                    study,
                    answer,
                    session=session,
                )
            except InvalidMetalensConsultationAnswer as error:
                raise ConsultationAnswerRejected("invalid") from error
            proposed = frontier.replace(study.identity, (successor,))
            admitted = _try_admit_frontier(
                session,
                proposed,
                supersedes=frontier_reference,
            )
            if admitted is None:
                raise RuntimeError("consultation_frontier_conflict")
            frontier = proposed
            frontier_reference = admitted
            answer = None
            continue
        if answer is not None:
            raise ConsultationAnswerRejected("not_required")

        frontier, frontier_reference, has_waiting = _advance_frontier(
            frontier,
            frontier_reference=frontier_reference,
            session=session,
            periodic_response=periodic_response,
            materials=materials,
        )
        pending = _first_consultation(frontier, session=session)
        if pending is not None:
            continue
        if not has_waiting:
            results = tuple(_admit_result(session, study) for study in frontier.studies)
            completed = CompletedResults(results)
            _admit_completed_results(
                session,
                compiled,
                completed,
                frontier=frontier,
                frontier_reference=frontier_reference,
            )
            return completed
        if evidence_adapter is None or has_opened_evidence:
            return WaitingStudies(frontier.studies)
        periodic_response, materials = _open_metalens_evidence(
            evidence_adapter,
            authority=authority,
            session=session,
            runs_directory=runs_directory,
        )
        has_opened_evidence = True


def _first_consultation(
    frontier: StudyFrontier,
    *,
    session: AuthoritySession,
) -> tuple[int, Study, ConsultationRequest] | None:
    from .metalens.conduct import required_metalens_consultation

    for position, study in enumerate(frontier.studies):
        request = required_metalens_consultation(study, session=session)
        if request is not None:
            return position, study, request
    return None


def _raise_unrestorable_application_root(
    session: AuthoritySession,
    compiled: Study,
) -> None:
    frontier_keys = tuple(
        item.key
        for item in session.observe().current
        if item.key.startswith("study_frontier:")
    )
    if frontier_keys:
        raise ValueError("application_root_brief_mismatch")
    raise ValueError("application_root_incomplete")


def _open_metalens_evidence(
    adapter: MetalensEvidenceAdapter,
    *,
    authority: Authority,
    session: AuthoritySession,
    runs_directory: Path,
) -> tuple[PeriodicResponse, MaterialResponse]:
    """
    Admit one exact usable evidence pair before scientific preparation.
    """

    opened = adapter.open(
        authority=authority,
        runs_directory=runs_directory,
    )
    if type(opened) is not tuple or len(opened) != 2:
        raise TypeError("metalens_evidence_pair_invalid")
    periodic_response, materials = opened
    periodic_context = getattr(periodic_response, "context", None)
    if type(periodic_context) is not PeriodicResponseContext or not callable(
        getattr(periodic_response, "observe", None)
    ):
        raise TypeError("metalens_periodic_response_invalid")
    material_context = getattr(materials, "context", None)
    if type(material_context) is not MaterialResponseContext or not callable(
        getattr(materials, "observe", None)
    ):
        raise TypeError("metalens_material_response_invalid")
    session.observe_admitted(periodic_context.binding_reference)
    session.observe_admitted(material_context.binding_reference)
    return periodic_response, materials


def _advance_frontier(
    frontier: StudyFrontier,
    *,
    frontier_reference: Reference,
    session: AuthoritySession,
    periodic_response: PeriodicResponse | None,
    materials: MaterialResponse | None,
) -> tuple[StudyFrontier, Reference, bool]:
    from .metalens.conduct import advance_metalens, prepare_metalens_study

    pending = list(frontier.studies)
    visited: set[str] = set()
    has_waiting = False
    reobservations = 0
    while True:
        if not pending:
            observed_reference = session.current_reference(frontier.key)
            if observed_reference == frontier_reference:
                break
            reobservations += 1
            if reobservations >= _FRONTIER_REOBSERVATION_LIMIT:
                raise RuntimeError("frontier_checkpoint_contention")
            if observed_reference is None:
                raise RuntimeError("frontier_checkpoint_missing")
            frontier = _restore_frontier(
                session,
                brief=frontier.studies[0].brief,
                reference=observed_reference,
            )
            frontier_reference = observed_reference
            pending = list(frontier.studies)
            visited.clear()
            has_waiting = False
            continue

        study = pending.pop(0)
        if study.identity in visited:
            continue
        visited.add(study.identity)
        if _is_complete(study):
            continue
        prepared = prepare_metalens_study(
            study,
            session=session,
            periodic_response=periodic_response,
            materials=materials,
        )
        if prepared.identity != study.identity:
            successors = (prepared,)
        else:
            evolved = advance_metalens(
                study,
                session=session,
                periodic_response=periodic_response,
                materials=materials,
            )
            successors = tuple(
                successor
                for successor in evolved
                if successor.identity != study.identity
            )
            if not successors:
                has_waiting = True
                continue
        (
            frontier,
            frontier_reference,
            reobservations,
            has_reobserved_frontier,
        ) = _admit_frontier_transition(
            session,
            frontier,
            predecessor=study,
            successors=successors,
            frontier_reference=frontier_reference,
            reobservations=reobservations,
        )
        if has_reobserved_frontier:
            pending = list(frontier.studies)
            visited.clear()
            has_waiting = False
            continue
        predecessor_findings = set(study.findings)
        for successor in successors:
            has_introduced_unavailability = any(
                finding.kind is FindingKind.UNAVAILABLE
                and finding not in predecessor_findings
                for finding in successor.findings
            )
            if has_introduced_unavailability:
                has_waiting = True
            else:
                pending.append(successor)
    if any(not _is_complete(study) for study in frontier.studies):
        has_waiting = True
    return frontier, frontier_reference, has_waiting


def _recall_frontier(
    session: AuthoritySession,
    *,
    brief: Brief,
    initial: Study,
) -> tuple[StudyFrontier, Reference | None]:
    key = StudyFrontier.start(initial).key
    reference = session.current_reference(key)
    if reference is None:
        return StudyFrontier.start(initial), None
    return (
        _restore_frontier(session, brief=brief, reference=reference),
        reference,
    )


def _restore_frontier(
    session: AuthoritySession,
    *,
    brief: Brief,
    reference: Reference,
) -> StudyFrontier:
    document = Document.from_bytes(session.fetch(reference))
    return StudyFrontier.from_document(
        document,
        brief=brief,
        session=session,
    )


def _try_admit_frontier(
    session: AuthoritySession,
    frontier: StudyFrontier,
    *,
    supersedes: Reference | None,
) -> Reference | None:
    try:
        return session.admit_current(
            frontier.document(),
            key=frontier.key,
            supersedes=supersedes,
            references=frontier.references(),
        )
    except CurrentAdmissionConflict:
        return None


def _admit_frontier_transition(
    session: AuthoritySession,
    frontier: StudyFrontier,
    *,
    predecessor: Study,
    successors: tuple[Study, ...],
    frontier_reference: Reference,
    reobservations: int,
) -> tuple[StudyFrontier, Reference, int, bool]:
    has_reobserved_frontier = False
    while True:
        proposed = frontier.replace(predecessor.identity, successors)
        admitted_reference = _try_admit_frontier(
            session,
            proposed,
            supersedes=frontier_reference,
        )
        if admitted_reference is not None:
            return (
                proposed,
                admitted_reference,
                reobservations,
                has_reobserved_frontier,
            )
        reobservations += 1
        if reobservations >= _FRONTIER_REOBSERVATION_LIMIT:
            raise RuntimeError("frontier_checkpoint_contention")
        has_reobserved_frontier = True
        frontier, frontier_reference = _require_current_frontier(
            session,
            brief=predecessor.brief,
            initial=predecessor,
        )
        if all(study.identity != predecessor.identity for study in frontier.studies):
            return (
                frontier,
                frontier_reference,
                reobservations,
                has_reobserved_frontier,
            )


def _require_current_frontier(
    session: AuthoritySession,
    *,
    brief: Brief,
    initial: Study,
) -> tuple[StudyFrontier, Reference]:
    frontier, reference = _recall_frontier(
        session,
        brief=brief,
        initial=initial,
    )
    if reference is None:
        raise RuntimeError("frontier_checkpoint_missing")
    return frontier, reference


def _completed_key(study: Study) -> str:
    return f"completed_results:{study.brief_identity}"


def _result_key(study: Study) -> str:
    return f"scientific_result:{study.identity}"


def _recall_completed_results(
    session: AuthoritySession,
    study: Study,
    *,
    frontier: StudyFrontier,
    frontier_reference: Reference,
) -> CompletedResults | None:
    reference = session.current_reference(_completed_key(study))
    if reference is None:
        return None
    try:
        document = Document.from_bytes(session.fetch(reference))
        if document.schema_identifier != _COMPLETED_RESULTS_SCHEMA:
            raise ValueError("completed_results_schema_mismatch")
        values = document.values
        if set(values) != {"brief_identity", "frontier", "results"}:
            raise ValueError("completed_results_shape_invalid")
        if values["brief_identity"] != study.brief_identity:
            raise ValueError("completed_results_brief_mismatch")
        recorded_frontier = Reference.from_mapping(values["frontier"])
        if (
            recorded_frontier != frontier_reference
            or session.current_reference(frontier.key) != frontier_reference
        ):
            raise ValueError("completed_results_frontier_mismatch")
        encoded_results = values["results"]
        if not isinstance(encoded_results, dict):
            raise ValueError("completed_results_shape_invalid")
        keys = tuple(
            f"result_{index:03d}" for index in range(1, len(encoded_results) + 1)
        )
        if not keys or tuple(encoded_results) != keys:
            raise ValueError("completed_results_shape_invalid")
        restored = CompletedResults(
            tuple(
                _restore_result(
                    session,
                    Reference.from_mapping(encoded_results[key]),
                )
                for key in keys
            )
        )
        _validate_completed_frontier(frontier, restored)
        return restored
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("completed_results_invalid") from error


def _admit_completed_results(
    session: AuthoritySession,
    study: Study,
    completed: CompletedResults,
    *,
    frontier: StudyFrontier,
    frontier_reference: Reference,
) -> Reference:
    if completed.brief_identity != study.brief_identity:
        raise ValueError("completed_results_brief_mismatch")
    _validate_completed_frontier(frontier, completed)
    if session.current_reference(frontier.key) != frontier_reference:
        raise RuntimeError("completed_results_frontier_not_current")
    document = Document(
        _COMPLETED_RESULTS_SCHEMA,
        {
            "brief_identity": study.brief_identity,
            "frontier": frontier_reference.as_mapping(),
            "results": {
                f"result_{index:03d}": result.reference.as_mapping()
                for index, result in enumerate(
                    completed.results,
                    start=1,
                )
            },
        },
    )
    return session.admit_current(
        document,
        key=_completed_key(study),
        supersedes=None,
        references=(
            frontier_reference,
            *(result.reference for result in completed.results),
        ),
    )


def _validate_completed_frontier(
    frontier: StudyFrontier,
    completed: CompletedResults,
) -> None:
    if any(not _is_complete(study) for study in frontier.studies):
        raise ValueError("completed_results_frontier_incomplete")
    closed_studies = tuple(result.closure.compiled for result in completed.results)
    if tuple(study.identity for study in closed_studies) != tuple(
        study.identity for study in frontier.studies
    ):
        raise ValueError("completed_results_frontier_mismatch")
    for expected, closed in zip(
        frontier.studies,
        closed_studies,
        strict=True,
    ):
        if expected.canonical_bytes() != closed.canonical_bytes():
            raise ValueError("completed_results_frontier_mismatch")


def _restore_result(
    session: AuthoritySession,
    reference: Reference,
) -> Result:
    from .metalens.result import restore_conclusion

    return restore_admitted_result(
        reference,
        fetch=session.fetch,
        restore_conclusion=restore_conclusion,
    )


def _admit_result(
    session: AuthoritySession,
    study: Study,
) -> Result:
    from .metalens.result import conclude

    current = session.current_reference(_result_key(study))
    if current is not None:
        restored = _restore_result(session, current)
        restored.closure.validate(study)
        return restored

    closure = _bind_closure(session, study)
    conclusion = conclude(study, closure, fetch=session.fetch)
    if conclusion.closure != closure:
        raise RuntimeError("result_closure_mismatch")
    document = conclusion.document()
    sources = tuple(dict.fromkeys(conclusion.references()))
    if closure.study.reference not in sources:
        raise RuntimeError("result_provenance_incomplete")
    reference = session.admit_current(
        document,
        key=_result_key(study),
        supersedes=None,
        references=sources,
    )
    return Result(reference, document, sources, closure)


def _bind_closure(
    session: AuthoritySession,
    study: Study,
) -> ResultClosure:
    brief = brief_document(study.brief)
    brief_reference = session.admit_document(brief)
    design = design_document(study, brief_reference)
    design_reference = session.admit_document(
        design,
        references=(brief_reference,),
    )
    compiled = study_document(
        study,
        brief_reference,
        design_reference,
    )
    compiled_references = tuple(
        dict.fromkeys(
            (
                brief_reference,
                design_reference,
                *study.direct_references(),
            )
        )
    )
    study_reference = session.admit_document(
        compiled,
        references=compiled_references,
    )
    return ResultClosure.bind(
        study,
        brief=BoundDocument(brief_reference, brief),
        design=BoundDocument(design_reference, design),
        study=BoundDocument(study_reference, compiled),
    )


def _is_complete(study: Study) -> bool:
    evidence = {fact.claim for fact in study.evidence}
    return (
        not study.ready_tasks
        and not study.findings
        and all(terminal in evidence for terminal in study.proof.terminal_claims)
    )
