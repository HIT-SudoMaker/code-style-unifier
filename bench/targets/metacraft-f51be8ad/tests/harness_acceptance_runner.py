from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any, TypeAlias

from examples import select_metalens_benchmark_case
from examples.metalens_benchmark.contract import ReferenceFactName
from tests.harness_acceptance import (
    ACCEPTANCE_PROFILES,
    CASE_NAMES,
    CapsuleRequest,
    HarnessAcceptanceProfile,
    HarnessInvocation,
    PreparedHarnessRun,
    OPENING_PROMPT,
    audit_observation,
    inspect_capsule,
    redact_transcript,
)


ROOT = Path(__file__).parents[1]
PYTHON = Path(sys.executable)
RUNS = tuple(
    (slot, profile, case_name)
    for slot, case_name in enumerate(CASE_NAMES, start=1)
    for profile in ACCEPTANCE_PROFILES
)
TERMINAL_PROCESS_STATES = ("completed", "failed", "timed_out")

ProcessCapture: TypeAlias = dict[str, Any]
ExecuteHarness: TypeAlias = Callable[
    [HarnessAcceptanceProfile, HarnessInvocation], ProcessCapture
]
AdvanceRecordedEvidence: TypeAlias = Callable[[Path, Path, Path], bytes]
CaptureCommand: TypeAlias = Callable[[tuple[str, ...]], str]


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resumable-smoke", action="store_true")
    parser.add_argument("--evidence-root", type=Path)
    selected = parser.parse_args(arguments)
    if sum((selected.preflight, selected.run, selected.resumable_smoke)) != 1:
        parser.error("choose exactly one of --preflight, --run or --resumable-smoke")
    if (selected.run or selected.resumable_smoke) and selected.evidence_root is None:
        parser.error("--run and --resumable-smoke require --evidence-root")
    if selected.preflight and selected.evidence_root is not None:
        parser.error("--evidence-root requires --run or --resumable-smoke")

    facts = preflight()
    print(json.dumps(facts, sort_keys=True), flush=True)
    if selected.preflight:
        return 0
    assert selected.evidence_root is not None
    if selected.run:
        run_matrix(selected.evidence_root, preflight_facts=facts)
    else:
        run_resumable_smoke(selected.evidence_root, preflight_facts=facts)
    return 0


def preflight(
    capture: CaptureCommand = lambda command: _capture(command),
    *,
    python_executable: Path = PYTHON,
) -> dict[str, object]:
    """Observe both profiles without creating or consuming a campaign root."""

    launcher = python_executable.parent / "Scripts" / "metacraft.exe"
    profiles: list[dict[str, object]] = []
    for profile in ACCEPTANCE_PROFILES:
        try:
            result = profile.preflight(capture)
            missing_flags = list(result.missing_flags)
            if missing_flags or not launcher.is_file():
                failure = (
                    "missing_required_flags"
                    if missing_flags
                    else "missing_metacraft_launcher"
                )
                profiles.append(
                    {
                        "profile": profile.name,
                        "availability": "unavailable_preflight",
                        "version": result.version,
                        "missing_flags": missing_flags,
                        "failure": failure,
                    }
                )
            else:
                profiles.append(
                    {
                        "profile": profile.name,
                        "availability": "available",
                        "version": result.version,
                        "missing_flags": [],
                        "failure": None,
                    }
                )
        except (OSError, RuntimeError) as error:
            profiles.append(
                {
                    "profile": profile.name,
                    "availability": "unavailable_preflight",
                    "version": None,
                    "missing_flags": [],
                    "failure": f"{type(error).__name__}:{error}",
                }
            )
    return {
        "schema": "metacraft.acceptance.harness_preflight",
        "installed_launcher": launcher.name,
        "launcher_exists": launcher.is_file(),
        "profiles": profiles,
    }


def _run_once(
    _profile: HarnessAcceptanceProfile,
    invocation: HarnessInvocation,
) -> ProcessCapture:
    try:
        completed = subprocess.run(
            invocation.argv,
            cwd=invocation.cwd,
            env=invocation.environment,
            input=(invocation.stdin.encode() if invocation.stdin is not None else None),
            capture_output=True,
            check=False,
            timeout=900,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "returncode": 124,
            "stdout": error.stdout or b"",
            "stderr": error.stderr or b"",
            "timed_out": True,
        }


def run_matrix(
    evidence_root: Path,
    *,
    preflight_facts: dict[str, object],
    execute: ExecuteHarness = _run_once,
) -> None:
    """Consume one fixed 2x4 campaign and seal every terminal observation."""

    preflight_by_profile = _validated_preflight(preflight_facts)
    evidence_root.mkdir(parents=True, exist_ok=False)
    for name in ("transcripts", "audits", "outcomes", "answers", "stderr", "post-hoc"):
        (evidence_root / name).mkdir()
    campaign_preflight = {
        **preflight_facts,
        "profiles": [
            {**entry, "campaign_opportunity_consumed": True}
            for entry in preflight_facts["profiles"]  # type: ignore[union-attr]
        ],
    }
    _write_json(evidence_root / "preflight.json", campaign_preflight)

    plan: list[dict[str, object]] = []
    records: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(
        prefix="metacraft-harness-acceptance-"
    ) as temporary:
        temporary_root = Path(temporary)
        for slot, profile, case_name in RUNS:
            run_id = f"{profile.name}-{slot:02d}"
            profile_preflight = preflight_by_profile[profile.name]
            if profile_preflight["availability"] != "available":
                plan.append(
                    {
                        "run_id": run_id,
                        "blind_slot": slot,
                        "profile": profile.name,
                        "eligible": False,
                        "started": False,
                        "attempt": "not_started_preflight",
                        "not_started_preflight_reason": profile_preflight["failure"],
                    }
                )
                continue

            prepared = profile.prepare(
                CapsuleRequest(
                    root=temporary_root / run_id,
                    case_name=case_name,
                    repository=ROOT,
                    python_executable=PYTHON,
                    inherited_environment=os.environ,
                    opening_prompt=OPENING_PROMPT,
                )
            )
            completed = execute(profile, prepared.invocation)
            transcript = completed["stdout"]
            stderr = completed["stderr"]
            if not isinstance(transcript, bytes) or not isinstance(stderr, bytes):
                raise TypeError("harness_capture_streams_must_be_bytes")
            attempt = _attempt(completed)
            plan_entry = {
                "run_id": run_id,
                "blind_slot": slot,
                "profile": profile.name,
                "eligible": True,
                "started": True,
                "attempt": attempt,
            }
            plan.append(plan_entry)

            raw_audit = audit_observation(
                profile.observe(transcript), capsule=prepared.capsule.root
            )
            redacted = redact_transcript(
                transcript, capsule=prepared.capsule.root, repository=ROOT
            )
            redacted_stderr = redact_transcript(
                stderr, capsule=prepared.capsule.root, repository=ROOT
            )
            retained_observation = profile.observe(redacted)
            retained_audit = audit_observation(
                retained_observation, capsule=prepared.capsule.root
            )
            if (
                retained_audit["is_confined"] != raw_audit["is_confined"]
                or retained_audit["violations"] != raw_audit["violations"]
            ):
                raise RuntimeError("acceptance_redaction_changed_audit")
            (evidence_root / "transcripts" / f"{run_id}.jsonl").write_bytes(redacted)
            (evidence_root / "stderr" / f"{run_id}.txt").write_bytes(redacted_stderr)
            _write_json(evidence_root / "audits" / f"{run_id}.json", retained_audit)

            inspection = "completed"
            try:
                scientific = inspect_capsule(prepared.capsule)
            except Exception as error:
                inspection = "failed"
                scientific = {
                    "inspection_error": _redacted_text(
                        f"{type(error).__name__}:{error}", capsule=prepared.capsule.root
                    )
                }
            accepted_answers: list[str] = []
            if inspection == "completed" and retained_audit["is_confined"]:
                for answer in scientific.get("answers", []):
                    if not isinstance(answer, dict) or not answer.get("is_canonical"):
                        continue
                    source = prepared.capsule.root / str(answer["name"])
                    destination = evidence_root / "answers" / f"{run_id}-{source.name}"
                    shutil.copyfile(source, destination)
                    accepted_answers.append(destination.name)

            record: dict[str, object] = {
                "run_id": run_id,
                "blind_slot": slot,
                "profile": profile.name,
                "harness_version": profile_preflight["version"],
                "process_exit_code": completed["returncode"],
                "timed_out": completed["timed_out"],
                "scientific": scientific,
                "accepted_answer_files": accepted_answers,
                "explanation": retained_observation.explanation,
            }
            record["classification"] = classify_acceptance(
                record,
                attempt=attempt,
                audit="accepted" if retained_audit["is_confined"] else "rejected",
                inspection=inspection,
            )
            _write_json(evidence_root / "outcomes" / f"{run_id}.json", record)
            records.append(record)

    if len(plan) != 8:
        raise RuntimeError("campaign_plan_not_2x4")
    terminal_counts = {
        state: sum(entry["attempt"] == state for entry in plan)
        for state in TERMINAL_PROCESS_STATES
    }
    eligible_count = sum(bool(entry["eligible"]) for entry in plan)
    started_count = sum(bool(entry["started"]) for entry in plan)
    blind_manifest = {
        "schema": "metacraft.acceptance.blind_campaign",
        "opening_prompt_sha256": _digest(OPENING_PROMPT.encode()),
        "preflight_sha256": _digest((evidence_root / "preflight.json").read_bytes()),
        "planned_cell_count": 8,
        "eligible_cell_count": eligible_count,
        "started_session_count": started_count,
        "terminal_process_counts": terminal_counts,
        "session_rerun_count": 0,
        "plan": plan,
        "runs": [_blind_identity(evidence_root, record) for record in records],
    }
    _write_json(evidence_root / "blind-manifest.json", blind_manifest)
    _generate_post_hoc(evidence_root, plan, records)
    reports = [f"slot-{slot:02d}.md" for slot in range(1, 5)] + ["matrix.md"]
    final_seal = {
        "schema": "metacraft.acceptance.sealed_campaign",
        "blind_manifest_sha256": _digest(
            (evidence_root / "blind-manifest.json").read_bytes()
        ),
        "reports": [
            {
                "name": name,
                "sha256": _digest((evidence_root / "post-hoc" / name).read_bytes()),
            }
            for name in reports
        ],
    }
    _write_json(evidence_root / "sealed-manifest.json", final_seal)


def run_resumable_smoke(
    evidence_root: Path,
    *,
    preflight_facts: dict[str, object],
    execute: ExecuteHarness = _run_once,
    advance_recorded_evidence: AdvanceRecordedEvidence | None = None,
) -> None:
    """Prove the fixed Codex-then-Claude cadence over fresh sessions."""

    preflight_by_profile = _validated_preflight(preflight_facts)
    evidence_root.mkdir(parents=True, exist_ok=False)
    (evidence_root / "transcripts").mkdir()
    (evidence_root / "audits").mkdir()
    (evidence_root / "stderr").mkdir()
    records: list[dict[str, object]] = []
    has_prior_incomplete = False
    active_record: dict[str, object] | None = None
    try:
        with tempfile.TemporaryDirectory(
            prefix="metacraft-resumable-smoke-"
        ) as temporary:
            temporary_root = Path(temporary)
            for profile in ACCEPTANCE_PROFILES:
                if has_prior_incomplete:
                    records.append(
                        {
                            "profile": profile.name,
                            "acceptance": "incomplete_policy_or_harness",
                            "reason": "prior_profile_incomplete",
                            "session_count": 0,
                            "sessions": [],
                        }
                    )
                    continue
                availability = preflight_by_profile[profile.name]
                if availability["availability"] != "available":
                    records.append(
                        {
                            "profile": profile.name,
                            "acceptance": "unavailable_preflight",
                            "reason": availability["failure"],
                            "session_count": 0,
                            "sessions": [],
                        }
                    )
                    continue
                prepared = profile.prepare(
                    CapsuleRequest(
                        root=temporary_root / profile.name,
                        case_name="mcclung-2024-low-na-propagation",
                        repository=ROOT,
                        python_executable=PYTHON,
                        inherited_environment=os.environ,
                        opening_prompt=_RESUME_ONE_TRANSITION,
                    )
                )
                original_brief = prepared.capsule.brief_path.read_bytes()
                session_records: list[dict[str, object]] = []
                active_record = {
                    "profile": profile.name,
                    "acceptance": "attempted",
                    "session_count": 0,
                    "sessions": session_records,
                }
                records.append(active_record)
                before = inspect_capsule(prepared.capsule)
                for session_number, expected_question in ((1, "height"), (2, None)):
                    session: dict[str, object] = {
                        "session": session_number,
                        "status": "attempted",
                    }
                    session_records.append(session)
                    active_record["session_count"] = len(session_records)
                    state = _run_smoke_session(
                        profile,
                        prepared,
                        before=before,
                        session_number=session_number,
                        session_record=session,
                        opening_prompt=_RESUME_ONE_TRANSITION,
                        execute=execute,
                        evidence_root=evidence_root,
                    )
                    if session["status"] != "complete":
                        active_record["acceptance"] = session["status"]
                        active_record["reason"] = f"session_{session_number}"
                        has_prior_incomplete = True
                        break
                    if state["current_question"] != expected_question:
                        raise RuntimeError(
                            f"resumable_smoke_transition_incomplete:{profile.name}:"
                            f"{session_number}"
                        )
                    if prepared.capsule.brief_path.read_bytes() != original_brief:
                        raise RuntimeError("resumable_smoke_brief_changed")
                    before = state
                if has_prior_incomplete:
                    continue
                advance = (
                    advance_recorded_evidence or _advance_recorded_receipt_boundary
                )
                completed_bytes = advance(
                    prepared.capsule.brief_path,
                    prepared.capsule.application_root,
                    prepared.capsule.material_library_path,
                )
                completed_mapping = json.loads(completed_bytes)
                if (
                    not isinstance(completed_mapping, dict)
                    or completed_mapping.get("outcome") != "completed_results"
                ):
                    raise RuntimeError("resumable_smoke_recorded_outcome_invalid")
                (prepared.capsule.root / "completed-results.json").write_bytes(
                    completed_bytes
                )
                before = inspect_capsule(prepared.capsule)
                session = {"session": 3, "status": "attempted"}
                session_records.append(session)
                active_record["session_count"] = len(session_records)
                terminal = _run_smoke_session(
                    profile,
                    prepared,
                    before=before,
                    session_number=3,
                    session_record=session,
                    opening_prompt=_REPORT_COMPLETION,
                    execute=execute,
                    evidence_root=evidence_root,
                )
                if session["status"] != "complete":
                    active_record["acceptance"] = session["status"]
                    active_record["reason"] = "session_3"
                    has_prior_incomplete = True
                    continue
                if terminal["outcome"] != "CompletedResults":
                    raise RuntimeError(f"resumable_smoke_not_completed:{profile.name}")
                active_record["acceptance"] = "complete"
                active_record["result_references"] = terminal["result_references"]
                active_record = None
    except Exception as error:
        if active_record is not None:
            active_record["acceptance"] = "implementation_fault"
            active_record["reason"] = f"{type(error).__name__}:{error}"
        raise
    finally:
        _write_json(
            evidence_root / "resumable-smoke.json",
            {
                "schema": "metacraft.acceptance.resumable_smoke",
                "profiles": records,
            },
        )


_RESUME_ONE_TRANSITION = (
    "Use the metacraft-design skill. Resume prepared-application-root through "
    "exactly one typed transition. Invoke this literal command: "
    ".\\metacraft.exe conduct --brief blind-brief.json --application-root "
    "prepared-application-root --material-library reviewed-materials.toml. "
    "If consultation_required, write only its canonical answer, repeat that "
    "same literal command once with --answer, then stop at the next outcome."
)

_REPORT_COMPLETION = (
    "Use the metacraft-design skill. Read completed-results.json, report its "
    "exact Result references, and stop. The application is already complete; "
    "do not invoke metacraft conduct."
)


def _run_smoke_session(
    profile: HarnessAcceptanceProfile,
    prepared: PreparedHarnessRun,
    *,
    before: Mapping[str, object],
    session_number: int,
    session_record: dict[str, object],
    opening_prompt: str,
    execute: ExecuteHarness,
    evidence_root: Path,
) -> dict[str, Any]:
    capsule = prepared.capsule
    resumed = profile.prepare_session(
        capsule,
        inherited_environment=os.environ,
        opening_prompt=opening_prompt,
    )
    completed = execute(profile, resumed.invocation)
    transcript = completed["stdout"]
    stderr = completed["stderr"]
    returncode = completed["returncode"]
    timed_out = completed["timed_out"]
    if not isinstance(transcript, bytes) or not isinstance(stderr, bytes):
        raise TypeError("harness_capture_streams_must_be_bytes")
    if not isinstance(returncode, int) or not isinstance(timed_out, bool):
        raise TypeError("harness_capture_status_invalid")
    observation = profile.observe(transcript)
    redacted = redact_transcript(transcript, capsule=capsule.root, repository=ROOT)
    redacted_stderr = redact_transcript(stderr, capsule=capsule.root, repository=ROOT)
    retained_observation = profile.observe(redacted)
    audit = audit_observation(retained_observation, capsule=capsule.root)
    after = inspect_capsule(capsule)
    cadence_violations = audit_resumable_cadence(
        retained_observation,
        before=before,
        after=after,
        expected_application_root=capsule.application_root.name,
    )
    audit["cadence_violations"] = list(cadence_violations)
    audit["is_confined"] = bool(audit["is_confined"]) and not cadence_violations
    name = f"{profile.name}-{session_number:02d}"
    (evidence_root / "transcripts" / f"{name}.jsonl").write_bytes(redacted)
    (evidence_root / "stderr" / f"{name}.txt").write_bytes(redacted_stderr)
    _write_json(evidence_root / "audits" / f"{name}.json", audit)
    status = _smoke_session_status(
        returncode=returncode,
        timed_out=timed_out,
        is_confined=bool(audit["is_confined"]),
        stderr=redacted_stderr,
        explanation=retained_observation.explanation,
    )
    session_record.update(
        {
            "status": status,
            "returncode": returncode,
            "timed_out": timed_out,
            "audit": "accepted" if audit["is_confined"] else "rejected",
        }
    )
    return after


def _smoke_session_status(
    *,
    returncode: int,
    timed_out: bool,
    is_confined: bool,
    stderr: bytes,
    explanation: str,
) -> str:
    if timed_out:
        return "incomplete_timeout"
    failure_text = stderr.decode("utf-8", errors="replace") + "\n" + explanation
    if returncode != 0 and re.search(
        r"\b(?:auth(?:entication)?|oauth|login|credential|api[ _-]?key)\b",
        failure_text,
        re.IGNORECASE,
    ):
        return "incomplete_authentication"
    if returncode != 0 or not is_confined:
        return "incomplete_policy_or_harness"
    return "complete"


def audit_resumable_cadence(
    observation: object,
    *,
    before: Mapping[str, object],
    after: Mapping[str, object],
    expected_application_root: str,
) -> tuple[str, ...]:
    """Reject mutations of one acceptance-only typed conduct cadence."""

    commands = tuple(dict.fromkeys(getattr(observation, "commands", ())))
    violations: list[str] = []
    conduct_arguments: list[dict[str, str]] = []
    for command in commands:
        if re.search(r"\b(?:FFT|CZT|ASM|VASM)\b", command, re.IGNORECASE):
            violations.append("realization_selected")
        if "metacraft" not in command.casefold() or " conduct " not in command:
            continue
        arguments = _conduct_arguments(command)
        if arguments is None:
            violations.append("conduct_command_invalid")
            continue
        conduct_arguments.append(arguments)
        if arguments.get("--application-root") != expected_application_root:
            violations.append("application_root_changed")
    if before.get("outcome") == "CompletedResults" and conduct_arguments:
        violations.append("conduct_after_completion")
    if (
        before.get("outcome") == "WaitingStudies"
        and before.get("authority_revision") == after.get("authority_revision")
        and conduct_arguments
    ):
        violations.append("waiting_fact_unchanged")
    before_answers = {
        item.get("identity") for item in _mapping_items(before.get("answers"))
    }
    for answer in _mapping_items(after.get("answers")):
        if answer.get("identity") in before_answers:
            continue
        if answer.get("request_identity") != before.get("current_request_identity"):
            violations.append("answer_request_changed")
    return tuple(dict.fromkeys(violations))


def _mapping_items(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _conduct_arguments(command: str) -> dict[str, str] | None:
    normalized = command.replace("\\\\", "\\")
    match = re.search(
        r"(?:\.\\)?metacraft(?:\.exe)? conduct (?P<body>[^\r\n]+)",
        normalized,
        re.I,
    )
    if match is None:
        return None
    body = match.group("body").rstrip("\"'")
    try:
        parts = [part.strip("\"'") for part in shlex.split(body, posix=False)]
    except ValueError:
        return None
    if len(parts) % 2 != 0:
        return None
    arguments: dict[str, str] = {}
    for index in range(0, len(parts), 2):
        option = parts[index]
        if option not in {
            "--answer",
            "--application-root",
            "--brief",
            "--lumerical-environment",
            "--material-library",
        }:
            return None
        arguments[option] = parts[index + 1]
    return arguments


def _advance_recorded_receipt_boundary(
    brief: Path,
    application_root: Path,
    material_library: Path,
) -> bytes:
    instant = datetime.now(UTC).isoformat()
    base = [
        str(PYTHON),
        "-m",
        "tests.resumable_journey_process",
        "--brief",
        str(brief),
        "--application-root",
        str(application_root),
        "--material-library",
        str(material_library),
        "--journey-instant",
        instant,
    ]
    interrupted = subprocess.run(
        [*base, "--journey-evidence", "recorded-interrupt-after-receipt"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if interrupted.returncode != 75:
        raise RuntimeError("resumable_smoke_receipt_boundary_missing")
    completed = subprocess.run(
        [*base, "--journey-evidence", "recorded"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError("resumable_smoke_recorded_evidence_failed")
    return completed.stdout


def classify_acceptance(
    record: dict[str, object],
    *,
    attempt: str | None = None,
    audit: str | None = None,
    inspection: str = "completed",
) -> dict[str, str]:
    attempt = attempt or _attempt(record)
    audit = audit or ("accepted" if record.get("is_confined") else "rejected")
    classification = {"attempt": attempt, "audit": audit, "inspection": inspection}
    if audit == "accepted" and inspection == "completed":
        classification["consultation"] = _consultation_position(record)
    return classification


def _consultation_position(record: dict[str, object]) -> str:
    scientific = record.get("scientific")
    advice = scientific.get("advice", []) if isinstance(scientific, dict) else []
    advice_kinds = (
        [item.get("kind") for item in advice if isinstance(item, dict)]
        if isinstance(advice, list)
        else []
    )
    answers = record.get("accepted_answer_files", [])
    if record.get("process_exit_code") != 0 or record.get("timed_out"):
        if advice_kinds:
            return f"process_failed_after_{advice_kinds[-1]}_advice"
        if isinstance(answers, list) and answers:
            return "process_failed_after_canonical_answer"
        return "process_failed_before_advice"
    if not advice_kinds:
        return "incomplete_without_advice"
    if (
        advice_kinds == ["period", "height"]
        and isinstance(scientific, dict)
        and scientific.get("current_question") is None
    ):
        return "consultation_cadence_complete"
    return f"advice_retained_through_{advice_kinds[-1]}"


def _generate_post_hoc(
    evidence_root: Path,
    plan: list[dict[str, object]],
    records: list[dict[str, object]],
) -> None:
    records_by_id = {str(record["run_id"]): record for record in records}
    rows: list[tuple[int, str, dict[str, object]]] = []
    for slot, case_name in enumerate(CASE_NAMES, start=1):
        case = select_metalens_benchmark_case(case_name)
        lines = [
            f"# Blind slot {slot}: {case_name}",
            "",
            "## Sealed campaign observations",
            "",
        ]
        slot_states: dict[str, object] = {}
        for entry in (item for item in plan if item["blind_slot"] == slot):
            profile = str(entry["profile"])
            if not entry["started"]:
                state = {
                    "availability": "unavailable_preflight",
                    "attempt": "not_started_preflight",
                }
            else:
                record = records_by_id[str(entry["run_id"])]
                classification = record["classification"]
                assert isinstance(classification, dict)
                state = {"availability": "available", **classification}
            slot_states[profile] = state
            lines.append(f"- {profile}: `{json.dumps(state, sort_keys=True)}`.")
        lines.extend(
            (
                "",
                "## Reviewed published design facts",
                "",
                f"- Cell period: `{json.dumps(_fact(case.reference.fact(ReferenceFactName.CELL_PERIOD)), sort_keys=True)}`.",
                f"- Atom height: `{json.dumps(_fact(case.reference.fact(ReferenceFactName.ATOM_HEIGHT)), sort_keys=True)}`.",
                "",
                "These sections remain separate context. They make no scientific performance or paper-reproduction claim.",
            )
        )
        (evidence_root / "post-hoc" / f"slot-{slot:02d}.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        rows.append((slot, case_name, slot_states))
    matrix = [
        "# Harness matrix",
        "",
        f"Planned cells: `{len(plan)}`; eligible cells: `{sum(bool(item['eligible']) for item in plan)}`; "
        f"started sessions: `{len(records)}`; session reruns: `0`.",
        "",
        "| Blind slot | Revealed case | Orthogonal campaign states |",
        "|---:|---|---|",
        *(
            f"| {slot} | {case_name} | `{json.dumps(states, sort_keys=True)}` |"
            for slot, case_name, states in rows
        ),
        "",
        "The matrix reports both profiles without averaging, substitution, an overall pass, or a winner.",
    ]
    (evidence_root / "post-hoc" / "matrix.md").write_text(
        "\n".join(matrix) + "\n", encoding="utf-8"
    )


def _validated_preflight(facts: dict[str, object]) -> dict[str, dict[str, object]]:
    if facts.get("schema") != "metacraft.acceptance.harness_preflight":
        raise ValueError("invalid_preflight_schema")
    entries = facts.get("profiles")
    if not isinstance(entries, list):
        raise ValueError("invalid_preflight_profiles")
    by_name = {
        str(entry.get("profile")): entry for entry in entries if isinstance(entry, dict)
    }
    if tuple(by_name) != tuple(profile.name for profile in ACCEPTANCE_PROFILES):
        raise ValueError("preflight_profiles_not_fixed_codex_claude")
    if any(
        entry.get("availability") not in ("available", "unavailable_preflight")
        for entry in by_name.values()
    ):
        raise ValueError("invalid_profile_availability")
    return by_name


def _attempt(capture: dict[str, object]) -> str:
    if capture.get("timed_out"):
        return "timed_out"
    return "completed" if capture.get("returncode") == 0 else "failed"


def _blind_identity(
    evidence_root: Path, record: dict[str, object]
) -> dict[str, object]:
    run_id = str(record["run_id"])
    accepted_answers = record.get("accepted_answer_files")
    answer_names = accepted_answers if isinstance(accepted_answers, list) else []
    return {
        "run_id": run_id,
        "blind_slot": record["blind_slot"],
        "profile": record["profile"],
        "transcript_sha256": _digest(
            (evidence_root / "transcripts" / f"{run_id}.jsonl").read_bytes()
        ),
        "stderr_sha256": _digest(
            (evidence_root / "stderr" / f"{run_id}.txt").read_bytes()
        ),
        "audit_sha256": _digest(
            (evidence_root / "audits" / f"{run_id}.json").read_bytes()
        ),
        "outcome_sha256": _digest(
            (evidence_root / "outcomes" / f"{run_id}.json").read_bytes()
        ),
        "answers": [
            {
                "name": name,
                "sha256": _digest((evidence_root / "answers" / name).read_bytes()),
            }
            for name in answer_names
            if isinstance(name, str)
        ],
    }


def _fact(fact: object) -> dict[str, object]:
    value: Any = getattr(fact, "value", None)
    if hasattr(value, "value") and hasattr(value, "unit"):
        encoded_value: object = {"value": str(value.value), "unit": value.unit}
    elif hasattr(value, "value"):
        encoded_value = str(value.value)
    else:
        encoded_value = None if value is None else str(value)
    return {
        "status": str(getattr(getattr(fact, "status", None), "value", "unknown")),
        "value": encoded_value,
        "meaning": str(getattr(fact, "meaning", "")),
    }


def _redacted_text(text: str, *, capsule: Path) -> str:
    return redact_transcript(text.encode(), capsule=capsule, repository=ROOT).decode()


def _capture(command: tuple[str, ...]) -> str:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"harness_preflight_command_failed:{command[0]}")
    return (completed.stdout or completed.stderr).strip()


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(_json_bytes(value))


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
