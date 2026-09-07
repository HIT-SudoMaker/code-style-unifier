from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


REPOSITORY = Path(__file__).parents[2]
sys.path.insert(0, str(REPOSITORY))

from tests.harness_acceptance import (  # noqa: E402
    CapsuleRequest,
    CodexAcceptanceProfile,
    RetainedMaterialReceipt,
    audit_observation,
    redact_transcript,
)


PYTHON = Path(sys.executable)
CASE_NAME = "mcclung-2024-low-na-propagation"
MATERIAL_AUTHORITY = (
    REPOSITORY
    / "runs"
    / "evidence"
    / "lumerical-material-mcclung-yang-20260809T091740159805Z-ed5ddf5c"
    / "authority"
)
MATERIAL_RECEIPT = RetainedMaterialReceipt(
    MATERIAL_AUTHORITY,
    "material_observation:sha256:643d27cadf51e6e0f0743a961df77f1b3fc5ba7f2c922fe8c6c1af1512c2e9ac",
)
SMOKE_PROMPT = (
    "Verify only the capsule-local executable boundary. Run exactly once: "
    r".\metacraft.exe conduct --brief blind-brief.json "
    "--application-root prepared-application-root "
    "--material-library reviewed-materials.toml. "
    "Do not create an answer file, do not retry, do not use the network, and "
    "do not inspect or modify anything outside this directory. Report the "
    "command outcome and stop."
)


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--evidence-root", type=Path)
    selected = parser.parse_args(arguments)
    if not selected.execute:
        if selected.evidence_root is not None:
            parser.error("--evidence-root requires --execute")
        print(json.dumps(smoke_plan(), sort_keys=True))
        return 0
    if selected.evidence_root is None:
        parser.error("--execute requires --evidence-root")
    return run_smoke(selected.evidence_root)


def smoke_plan() -> dict[str, object]:
    """Describe the bounded activity without preparing a capsule or session."""

    return {
        "schema": "metacraft.acceptance.ticket03_codex_executable_smoke_plan",
        "profile": "codex",
        "case": CASE_NAME,
        "planned_capsule_count": 1,
        "planned_session_count": 1,
        "retry_count": 0,
        "sandbox": "workspace-write",
        "approval_policy": "never",
        "network_access": False,
    }


def run_smoke(evidence_root: Path) -> int:
    """Consume one fresh capsule and exactly one Codex session."""

    evidence_root = evidence_root.resolve()
    if evidence_root.exists():
        raise FileExistsError(evidence_root)
    profile = CodexAcceptanceProfile()
    preflight = profile.preflight(_capture_text)
    launcher = PYTHON.parent / "Scripts" / "metacraft.exe"
    if preflight.missing_flags or not launcher.is_file():
        raise RuntimeError("codex_executable_smoke_preflight_failed")

    evidence_root.mkdir(parents=True)
    capsule_root = evidence_root / "capsule"
    prepared = profile.prepare(
        CapsuleRequest(
            root=capsule_root,
            case_name=CASE_NAME,
            repository=REPOSITORY,
            python_executable=PYTHON,
            inherited_environment=os.environ,
            opening_prompt=SMOKE_PROMPT,
            material_receipt=MATERIAL_RECEIPT,
        )
    )
    _write_json(
        evidence_root / "preflight.json",
        {
            **smoke_plan(),
            "version": preflight.version,
            "missing_flags": list(preflight.missing_flags),
            "launcher_exists": launcher.is_file(),
        },
    )

    completed = _execute_once(prepared.invocation)
    timed_out = bool(getattr(completed, "timed_out", False))
    transcript = redact_transcript(
        completed.stdout,
        capsule=prepared.capsule.root,
        repository=REPOSITORY,
    )
    stderr = redact_transcript(
        completed.stderr,
        capsule=prepared.capsule.root,
        repository=REPOSITORY,
    )
    (evidence_root / "transcript.jsonl").write_bytes(transcript)
    (evidence_root / "stderr.txt").write_bytes(stderr)
    audit = audit_observation(
        profile.observe(transcript),
        capsule=prepared.capsule.root,
    )
    command_evidence = inspect_metacraft_command(transcript)
    checks = {
        "outer_process_completed": completed.returncode == 0 and not timed_out,
        "audit_confined": audit["is_confined"] is True,
        "exactly_one_metacraft_attempt": command_evidence["attempt_count"] == 1,
        "metacraft_command_completed": command_evidence["completed_count"] == 1,
        "consultation_was_emitted": command_evidence["consultation_required_count"] == 1,
        "no_answer_was_created": not any(
            (prepared.capsule.root / name).exists()
            for name in ("period-answer.json", "height-answer.json")
        ),
    }
    outcome = {
        "schema": "metacraft.acceptance.ticket03_codex_executable_smoke",
        "planned_session_count": 1,
        "started_session_count": 1,
        "retry_count": 0,
        "process_exit_code": completed.returncode,
        "timed_out": timed_out,
        "audit": audit,
        "command_evidence": command_evidence,
        "checks": checks,
        "passed": all(checks.values()),
    }
    _write_json(evidence_root / "outcome.json", outcome)
    files = sorted(
        path.relative_to(evidence_root).as_posix()
        for path in evidence_root.rglob("*")
        if path.is_file() and path.name != "sealed-manifest.json"
    )
    _write_json(
        evidence_root / "sealed-manifest.json",
        {
            "schema": "metacraft.acceptance.ticket03_codex_executable_smoke_seal",
            "files": [
                {"path": name, "sha256": _digest((evidence_root / name).read_bytes())}
                for name in files
            ],
        },
    )
    return 0 if outcome["passed"] else 1


def inspect_metacraft_command(transcript: bytes) -> dict[str, int]:
    """Count the one reviewed executable attempt and its terminal evidence."""

    attempts = 0
    completed = 0
    consultation_required = 0
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "command_execution":
            continue
        command = item.get("command")
        if not isinstance(command, str) or "metacraft.exe conduct" not in command.casefold():
            continue
        attempts += 1
        if item.get("status") == "completed" and item.get("exit_code") == 0:
            completed += 1
            output = item.get("aggregated_output")
            if isinstance(output, str) and "consultation_required" in output:
                consultation_required += 1
    return {
        "attempt_count": attempts,
        "completed_count": completed,
        "consultation_required_count": consultation_required,
    }


def _execute_once(invocation: Any) -> subprocess.CompletedProcess[bytes] | Any:
    try:
        return subprocess.run(
            invocation.argv,
            cwd=invocation.cwd,
            env=invocation.environment,
            input=None if invocation.stdin is None else invocation.stdin.encode(),
            capture_output=True,
            check=False,
            timeout=300,
        )
    except subprocess.TimeoutExpired as error:
        return _TimedOutCapture(error.stdout or b"", error.stderr or b"")


class _TimedOutCapture:
    def __init__(self, stdout: bytes, stderr: bytes) -> None:
        self.returncode = 124
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = True


def _capture_text(command: tuple[str, ...]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError("codex_executable_smoke_preflight_command_failed")
    return (completed.stdout or completed.stderr).strip()


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
