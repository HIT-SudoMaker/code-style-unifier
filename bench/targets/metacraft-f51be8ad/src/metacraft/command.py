from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys
from typing import Any, BinaryIO, NoReturn

from .authority import Document
from .canonical import canonicalize
from .materials import SolverMaterialLibrary
from .science.compile import InvalidBrief, UnsupportedAim
from .science.conduct import (
    CompletedResults,
    ConsultationAnswerRejected,
    ConsultationRequired,
    ConductOutcome,
    WaitingStudies,
    conduct,
)
from .science.consultation import ConsultationAnswer
from .science.metalens.brief import MetalensBrief
from .science.result import Result
from .science.study import Study
from .solvers.lumerical_fdtd import (
    LumericalConfig,
    read_lumerical_environment,
)
from .solvers.lumerical_fdtd.metalens_evidence import (
    LumericalMetalensEvidence,
)


_OUTCOME_SCHEMA = "metacraft.command.conduct_outcome"
_INPUT_FAILURE_SCHEMA = "metacraft.command.input_failure"


class _InputFailure(ValueError):
    """
    Carry one stable command-input reason to the process boundary.
    """


class _ArgumentParser(argparse.ArgumentParser):
    """
    Keep argparse prose outside the machine-only command contract.
    """

    def error(self, message: str) -> NoReturn:
        """
        Convert every parser failure into one stable command-input reason.
        """

        del message
        raise _InputFailure("command_arguments_invalid")


class _StoreOnce(argparse.Action):
    """
    Reject repeated singleton options instead of taking the last value.
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        """
        Store one option value and reject a second occurrence.
        """

        if getattr(namespace, self.dest, None) is not None:
            parser.error(f"duplicate option: {option_string}")
        setattr(namespace, self.dest, values)


def main(arguments: Sequence[str] | None = None) -> int:
    """
    Translate one local command invocation to the conduct Interface.
    """

    try:
        invocation = _parse_arguments(arguments)
        brief = _decode_brief(invocation.brief)
        material_library = _decode_material_library(
            invocation.material_library
        )
        answer = _decode_answer(invocation.answer)
        evidence_adapter = _compose_evidence_adapter(
            invocation.lumerical_environment,
            material_library=material_library,
        )
    except _InputFailure as error:
        _write_input_failure(str(error))
        return 2

    try:
        outcome = conduct(
            brief,
            application_root=invocation.application_root,
            evidence_adapter=evidence_adapter,
            consultation_answer=answer,
        )
    except ConsultationAnswerRejected as error:
        _write_input_failure(f"consultation_answer_rejected:{error.reason}")
        return 2

    _write_bytes(encode_conduct_outcome(outcome), stream=sys.stdout.buffer)
    return 0


def _parse_arguments(arguments: Sequence[str] | None) -> argparse.Namespace:
    parser = _ArgumentParser(
        prog="metacraft",
        add_help=False,
        allow_abbrev=False,
    )
    parser.add_argument("operation", choices=("conduct",))
    parser.add_argument("--brief", required=True, type=Path, action=_StoreOnce)
    parser.add_argument(
        "--application-root",
        required=True,
        type=Path,
        action=_StoreOnce,
    )
    parser.add_argument(
        "--material-library",
        required=True,
        type=Path,
        action=_StoreOnce,
    )
    parser.add_argument(
        "--lumerical-environment",
        type=Path,
        action=_StoreOnce,
    )
    parser.add_argument("--answer", type=Path, action=_StoreOnce)
    return parser.parse_args(arguments)


def _decode_brief(path: Path) -> MetalensBrief:
    try:
        return MetalensBrief.decode_canonical_bytes(path.read_bytes())
    except (OSError, ValueError) as error:
        raise _InputFailure("brief_document_invalid") from error


def _decode_material_library(path: Path) -> SolverMaterialLibrary:
    try:
        return SolverMaterialLibrary.decode_bytes(path.read_bytes())
    except (OSError, ValueError) as error:
        raise _InputFailure("material_library_invalid") from error


def _decode_answer(path: Path | None) -> ConsultationAnswer | None:
    if path is None:
        return None
    try:
        document = Document.from_bytes(path.read_bytes())
        return ConsultationAnswer.from_document(document)
    except (OSError, ValueError) as error:
        raise _InputFailure("answer_document_invalid") from error


def _compose_evidence_adapter(
    path: Path | None,
    *,
    material_library: SolverMaterialLibrary,
) -> LumericalMetalensEvidence | None:
    if path is None:
        return None
    try:
        environment = read_lumerical_environment(path, inherited={})
        config = LumericalConfig.from_environ(environment)
    except (OSError, ValueError) as error:
        raise _InputFailure("lumerical_environment_invalid") from error
    return LumericalMetalensEvidence(config, material_library)


def _encode_outcome(outcome: ConductOutcome) -> tuple[str, object]:
    if isinstance(outcome, InvalidBrief):
        return "invalid_brief", {"reason": outcome.reason}
    if isinstance(outcome, UnsupportedAim):
        return "unsupported_aim", {"aim": outcome.aim}
    if isinstance(outcome, ConsultationRequired):
        return "consultation_required", {
            "request": outcome.request.document().as_mapping(),
            "studies": _studies(outcome.studies),
        }
    if isinstance(outcome, WaitingStudies):
        return "waiting_studies", {"studies": _studies(outcome.studies)}
    if isinstance(outcome, CompletedResults):
        return "completed_results", {
            "brief_identity": outcome.brief_identity,
            "results": [_result(result) for result in outcome.results],
        }
    raise TypeError("conduct_outcome_unknown")


def encode_conduct_outcome(outcome: ConductOutcome) -> bytes:
    """
    Encode one typed conduct outcome as the exact command wire object.
    """

    name, value = _encode_outcome(outcome)
    return _encode_json(
        (
            ("schema", _OUTCOME_SCHEMA),
            ("outcome", name),
            ("value", canonicalize(value)),
        )
    )


def _studies(studies: tuple[Study, ...]) -> list[dict[str, object]]:
    return [study.document().as_mapping() for study in studies]


def _result(result: Result) -> dict[str, object]:
    return {
        "closure": result.closure.as_mapping(),
        "document": result.document.as_mapping(),
        "reference": result.reference.as_mapping(),
        "sources": [reference.as_mapping() for reference in result.sources],
    }


def _write_input_failure(reason: str) -> None:
    _write_bytes(
        _encode_json(
            (("schema", _INPUT_FAILURE_SCHEMA), ("reason", reason)),
        ),
        stream=sys.stderr.buffer,
    )


def _encode_json(
    members: tuple[tuple[str, object], ...],
) -> bytes:
    return json.dumps(
        dict(members),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _write_bytes(content: bytes, *, stream: BinaryIO) -> None:
    stream.write(content)
    stream.flush()


if __name__ == "__main__":
    raise SystemExit(main())
