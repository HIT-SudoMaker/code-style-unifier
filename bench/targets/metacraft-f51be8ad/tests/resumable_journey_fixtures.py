from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from metacraft.authority import Document
from metacraft.science.consultation import (
    ConsultationAnswer,
    ConsultationRequest,
    GroundKind,
    Recommendation,
)
from metacraft.science.metalens.brief import (
    ApertureExtent,
    ApertureIntent,
    MetalensBrief,
    MonochromaticSpectrum,
)
from tests.brief_fixtures import geometric_brief, propagation_brief


REPOSITORY_ROOT = Path(__file__).parents[1]
_PYTHON = Path(sys.executable)
_JOURNEY_INSTANTS: dict[Path, datetime] = {}
RESUMABLE_ROLE_NAMES = (
    "journey-low-na-propagation",
    "journey-low-na-pb",
    "journey-high-na-propagation",
    "journey-high-na-pb",
)


def resumable_role_briefs() -> tuple[MetalensBrief, ...]:
    propagation = propagation_brief()
    geometric = geometric_brief()
    propagation_omissions = tuple(
        dict.fromkeys((*propagation.omissions, "atom_height_nm", "cell_period_nm"))
    )
    geometric_omissions = tuple(
        dict.fromkeys((*geometric.omissions, "atom_height_nm", "cell_period_nm"))
    )
    return (
        replace(
            propagation,
            operating_spectrum=MonochromaticSpectrum(wavelength_nm=940),
            numerical_aperture=Decimal("0.48"),
            focal_length_um=Decimal("20"),
            dimension_step_nm=20,
            aperture=ApertureIntent(45, ApertureExtent.DIAMETER),
            omissions=propagation_omissions,
        ),
        replace(
            geometric,
            operating_spectrum=MonochromaticSpectrum(wavelength_nm=940),
            numerical_aperture=Decimal("0.48"),
            focal_length_um=Decimal("18"),
            dimension_step_nm=40,
            aperture=ApertureIntent(41, ApertureExtent.DIAMETER),
            omissions=geometric_omissions,
        ),
        replace(
            propagation,
            operating_spectrum=MonochromaticSpectrum(wavelength_nm=1550),
            numerical_aperture=Decimal("0.8"),
            focal_length_um=Decimal("10"),
            dimension_step_nm=20,
            aperture=ApertureIntent(39, ApertureExtent.DIAMETER),
            omissions=propagation_omissions,
        ),
        replace(
            geometric,
            operating_spectrum=MonochromaticSpectrum(wavelength_nm=940),
            numerical_aperture=Decimal("0.8"),
            focal_length_um=Decimal("8"),
            dimension_step_nm=40,
            aperture=ApertureIntent(41, ApertureExtent.DIAMETER),
            omissions=geometric_omissions,
        ),
    )


def run_resumable_journey(
    brief: Path,
    application_root: Path,
    materials: Path,
    *,
    evidence: str,
    answer: Path | None = None,
) -> dict[str, object]:
    completed = invoke_resumable_journey(
        brief,
        application_root,
        materials,
        evidence=evidence,
        answer=answer,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    value = json.loads(completed.stdout)
    assert isinstance(value, dict)
    return value


def run_resumable_journey_failure(*args: object, **kwargs: object) -> str:
    completed = invoke_resumable_journey(*args, **kwargs)  # type: ignore[arg-type]
    assert completed.returncode == 2
    assert completed.stdout == b""
    value = json.loads(completed.stderr)
    assert value["schema"] == "metacraft.command.input_failure"
    return str(value["reason"])


def invoke_resumable_journey(
    brief: Path,
    application_root: Path,
    materials: Path,
    *,
    evidence: str,
    answer: Path | None = None,
) -> subprocess.CompletedProcess[bytes]:
    journey_instant = _JOURNEY_INSTANTS.setdefault(
        application_root,
        datetime.now(UTC),
    )
    if len(tuple((application_root / "authority").glob("workspace.sqlite3"))) == 0:
        assert abs((datetime.now(UTC) - journey_instant).total_seconds()) < 5
    command = [
        str(_PYTHON),
        "-m",
        "tests.resumable_journey_process",
        "--journey-evidence",
        evidence,
        "--brief",
        str(brief),
        "--application-root",
        str(application_root),
        "--material-library",
        str(materials),
        "--journey-instant",
        journey_instant.isoformat(),
    ]
    if answer is not None:
        command.extend(("--answer", str(answer)))
    return subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        check=False,
        timeout=(
            150
            if evidence in {"recorded", "recorded-interrupt-after-receipt"}
            and "journey-high-na-pb" in brief.parts
            else (
                90
                if evidence in {"recorded", "recorded-interrupt-after-receipt"}
                or evidence == "poison"
                else 30
            )
        ),
    )


def consultation_request(outcome: dict[str, object]) -> ConsultationRequest:
    value = outcome["value"]
    assert isinstance(value, dict)
    mapping = value["request"]
    assert isinstance(mapping, dict)
    return ConsultationRequest.from_document(
        Document(str(mapping["schema_identifier"]), mapping["values"])
    )


def answer_consultation(outcome: dict[str, object]) -> ConsultationAnswer:
    request = consultation_request(outcome)
    if request.question_kind.value == "period":
        value = outcome["value"]
        assert isinstance(value, dict)
        studies = value["studies"]
        assert isinstance(studies, list)
        study = studies[0]
        assert isinstance(study, dict)
        study_values = study["values"]
        assert isinstance(study_values, dict)
        brief = study_values["brief"]
        assert isinstance(brief, dict)
        aperture = brief.get("aperture")
        operating_spectrum = brief.get("operating_spectrum")
        if (
            isinstance(operating_spectrum, dict)
            and operating_spectrum.get("kind") == "monochromatic"
            and operating_spectrum.get("wavelength_nm") == 940
            and brief.get("numerical_aperture") == "0.8"
            and isinstance(aperture, dict)
            and aperture.get("cells") == 41
        ):
            candidate = next(
                item for item in request.candidates if item.quantity == 520
            )
        else:
            candidate = _conservative_period_candidate(request)
    else:
        candidate = request.candidates[0]
    decisive = tuple(
        ground.identity
        for ground in request.grounds
        if ground.kind in {GroundKind.FACT, GroundKind.CONSTRAINT}
    )
    return ConsultationAnswer(
        request_identity=request.identity,
        conclusion=Recommendation(
            candidate_identity=candidate.identity,
            reason="Bounded journey fixture selects one emitted legal candidate.",
            decisive_ground_identities=decisive,
            external_claim_identities=(),
        ),
        external_claims=(),
    )


def _conservative_period_candidate(request: ConsultationRequest):
    order_ground = next(
        ground
        for ground in request.grounds
        if ground.statement.startswith("order ceiling:")
    )
    match = re.search(r"([0-9.]+) nm$", order_ground.statement)
    assert match is not None
    order_ceiling_nm = Decimal(match.group(1))
    return max(
        (item for item in request.candidates if item.quantity < order_ceiling_nm),
        key=lambda item: item.quantity,
    )
