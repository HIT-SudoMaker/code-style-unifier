from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / ".scratch" / "harness-native-consultation" / "acceptance" / "07"
RUNNER_MODULE = "tests.harness_acceptance_runner"


def test_retained_tree_matches_frozen_whole_tree_identity() -> None:
    paths = sorted(
        (path for path in EVIDENCE.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(EVIDENCE).as_posix(),
    )

    # Canonical framing is UTF-8 without BOM: one
    # path<TAB>byte-size<TAB>lowercase-file-sha256 line per file, joined by LF
    # with no trailing newline.
    lines = []
    for path in paths:
        body = path.read_bytes()
        lines.append(
            f"{path.relative_to(EVIDENCE).as_posix()}\t{len(body)}\t"
            f"{hashlib.sha256(body).hexdigest()}"
        )
    canonical_bytes = "\n".join(lines).encode("utf-8")

    assert len(paths) == 42
    assert _digest(canonical_bytes) == (
        "sha256:50145dc009658ce518c52b57fa4ab0c6fbe4628414d8ccaa337f414df67c223b"
    )


def test_retained_matrix_proves_the_original_audit_correction() -> None:
    original_bytes, original = _read_json("sealed-manifest.original.json")
    correction_bytes, correction = _read_json("audit-correction.json")
    corrected_bytes, corrected = _read_json(
        "sealed-manifest.audit-corrected.json"
    )

    assert correction["schema"] == "metacraft.acceptance.audit_correction"
    assert correction["session_rerun_count"] == 0
    assert correction["original_manifest_sha256"] == _digest(original_bytes)
    assert corrected["amendment"] == {
        "kind": "audit_correction",
        "original_manifest_sha256": _digest(original_bytes),
        "correction_sha256": _digest(correction_bytes),
        "session_rerun_count": 0,
    }
    assert _digest(corrected_bytes) == (
        "sha256:94346824533d27524ff5bed964eedf47e067437d9a3459cf90650c73388e0f51"
    )
    assert {
        key: corrected[key]
        for key in ("schema", "versions", "opening_prompt_sha256", "run_count")
    } == {
        key: original[key]
        for key in ("schema", "versions", "opening_prompt_sha256", "run_count")
    }
    assert original["run_count"] == corrected["run_count"] == 8

    original_runs = _runs_by_id(original)
    corrected_runs = _runs_by_id(corrected)
    audit_changes = _changes_by_run(correction, "audit_changes")
    outcome_changes = _changes_by_run(correction, "outcome_changes")
    assert set(original_runs) == set(corrected_runs) == set(audit_changes) == set(
        outcome_changes
    )
    assert set(correction["unchanged_transcript_sha256"]) == set(original_runs)

    for run_id, original_run in original_runs.items():
        corrected_run = corrected_runs[run_id]
        assert corrected_run["blind_slot"] == original_run["blind_slot"]
        assert correction["unchanged_transcript_sha256"][run_id] == (
            original_run["transcript_sha256"]
        )
        assert corrected_run["transcript_sha256"] == original_run["transcript_sha256"]
        assert audit_changes[run_id] == {
            "run_id": run_id,
            "old_sha256": original_run["audit_sha256"],
            "new_sha256": corrected_run["audit_sha256"],
        }
        assert outcome_changes[run_id] == {
            "run_id": run_id,
            "old_sha256": original_run["outcome_sha256"],
            "new_sha256": corrected_run["outcome_sha256"],
        }


def test_retained_matrix_proves_every_sanitized_old_and_new_identity() -> None:
    original_bytes, _ = _read_json("sealed-manifest.original.json")
    previous_bytes, previous = _read_json(
        "sealed-manifest.audit-corrected.json"
    )
    previous_correction_bytes, _ = _read_json("audit-correction.json")
    correction_bytes, correction = _read_json("retained-evidence-correction.json")
    _, current = _read_json("sealed-manifest.json")

    assert correction["schema"] == (
        "metacraft.acceptance.retained_evidence_correction"
    )
    assert correction["session_rerun_count"] == 0
    assert correction["original_manifest_sha256"] == _digest(original_bytes)
    assert correction["previous_manifest_sha256"] == _digest(previous_bytes)
    assert correction["previous_correction_sha256"] == _digest(
        previous_correction_bytes
    )
    assert current["amendment"] == {
        "kind": "retained_evidence_correction",
        "previous_manifest_sha256": _digest(previous_bytes),
        "original_manifest_sha256": _digest(original_bytes),
        "previous_correction_sha256": _digest(previous_correction_bytes),
        "correction_sha256": _digest(correction_bytes),
        "session_rerun_count": 0,
    }
    assert previous["amendment"]["session_rerun_count"] == 0
    assert current["run_count"] == previous["run_count"] == 8

    previous_runs = _runs_by_id(previous)
    current_runs = _runs_by_id(current)
    run_changes = {
        change["run_id"]: change for change in correction["run_changes"]
    }
    assert set(previous_runs) == set(current_runs) == set(run_changes)

    old_manifest_fields = {
        "audit": "audit_sha256",
        "outcome": "outcome_sha256",
        "transcript": "transcript_sha256",
    }
    current_manifest_fields = {
        **old_manifest_fields,
        "stderr": "stderr_sha256",
    }
    artifact_paths = {
        "audit": lambda run_id: EVIDENCE / "audits" / f"{run_id}.json",
        "outcome": lambda run_id: EVIDENCE / "outcomes" / f"{run_id}.json",
        "stderr": lambda run_id: EVIDENCE / "stderr" / f"{run_id}.txt",
        "transcript": lambda run_id: EVIDENCE / "transcripts" / f"{run_id}.jsonl",
    }
    for run_id, change in run_changes.items():
        previous_run = previous_runs[run_id]
        current_run = current_runs[run_id]
        assert current_run["blind_slot"] == previous_run["blind_slot"]
        artifacts = change["artifacts"]
        assert set(artifacts) == set(artifact_paths)
        for kind, field in old_manifest_fields.items():
            assert artifacts[kind]["old_sha256"] == previous_run[field]
        assert artifacts["stderr"]["old_sha256"] == artifacts["stderr"][
            "new_sha256"
        ]
        for kind, field in current_manifest_fields.items():
            current_identity = _digest(artifact_paths[kind](run_id).read_bytes())
            assert artifacts[kind]["new_sha256"] == current_identity
            assert current_run[field] == current_identity

    post_hoc_changes = {
        change["name"]: change for change in correction["post_hoc_changes"]
    }
    assert set(post_hoc_changes) == {
        "matrix.md",
        "slot-01.md",
        "slot-02.md",
        "slot-03.md",
        "slot-04.md",
    }
    for name, change in post_hoc_changes.items():
        assert _is_identity(change["old_sha256"])
        assert change["new_sha256"] == _digest(
            (EVIDENCE / "post-hoc" / name).read_bytes()
        )


def test_current_retained_projection_is_confined_honest_and_bounded() -> None:
    _, manifest = _read_json("sealed-manifest.json")
    retained = []
    for run in manifest["runs"]:
        run_id = run["run_id"]
        transcript = (EVIDENCE / "transcripts" / f"{run_id}.jsonl").read_bytes()
        stderr = (EVIDENCE / "stderr" / f"{run_id}.txt").read_bytes()
        audit_bytes = (EVIDENCE / "audits" / f"{run_id}.json").read_bytes()
        outcome_bytes = (EVIDENCE / "outcomes" / f"{run_id}.json").read_bytes()
        audit = json.loads(audit_bytes)
        outcome = json.loads(outcome_bytes)
        retained.extend((transcript, stderr, audit_bytes, outcome_bytes))

        assert run["transcript_sha256"] == _digest(transcript)
        assert run["stderr_sha256"] == _digest(stderr)
        assert run["audit_sha256"] == _digest(audit_bytes)
        assert run["outcome_sha256"] == _digest(outcome_bytes)
        assert audit["is_confined"]
        assert not any(audit["violations"].values())
        assert outcome["is_confined"]
        assert outcome["scientific"]["outcome"] == "ConsultationRequired"
        assert outcome["scientific"]["advice"] == []
        assert outcome["scientific"]["selected"] == {}
        assert outcome["accepted_answer_files"] == []
        if run_id.startswith("codex-"):
            assert outcome["process_exit_code"] == 0
            assert outcome["process_status"] == "completed"
            assert outcome["acceptance"] == {
                "audit": "accepted",
                "state": "incomplete without advice",
            }
        else:
            assert outcome["process_exit_code"] == 1
            assert outcome["process_status"] == "failed"
            assert outcome["acceptance"] == {
                "audit": "accepted",
                "state": "process failed before advice",
            }

    assert not tuple((EVIDENCE / "answers").iterdir())
    retained_text = b"\n".join(retained)
    for forbidden in (
        b"C:\\Users\\Administrator",
        b"C:\\\\Users\\\\Administrator",
        b"C--Users-Administrator",
        b"metacraft-harness-acceptance-",
    ):
        assert forbidden not in retained_text
    assert re.search(
        rb"(?i)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        retained_text,
    ) is None

    reports = sorted((EVIDENCE / "post-hoc").glob("*.md"))
    assert len(reports) == 5
    report_text = "\n".join(path.read_text(encoding="utf-8") for path in reports)
    for forbidden in ("compare", "delta", "threshold", "result"):
        assert forbidden not in report_text.casefold()
    assert report_text.count(
        "These sections remain separate context. They make no scientific "
        "performance or paper-reproduction claim."
    ) == 4
    assert (
        "without averaging, substitution, or a winner" in report_text
    )


@pytest.mark.parametrize(
    "retired_mode", ("--correct-audits", "--correct-retained-evidence")
)
def test_runner_rejects_retired_correction_modes(
    retired_mode: str,
    tmp_path: Path,
) -> None:
    evidence_root = tmp_path / "must-not-exist"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            RUNNER_MODULE,
            retired_mode,
            "--evidence-root",
            str(evidence_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert completed.returncode == 2
    assert "unrecognized arguments" in completed.stderr
    assert not evidence_root.exists()


def test_runner_interface_names_only_the_two_fresh_modes(tmp_path: Path) -> None:
    help_result = subprocess.run(
        [sys.executable, "-m", RUNNER_MODULE, "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert help_result.returncode == 0
    assert "--preflight" in help_result.stdout
    assert "--run" in help_result.stdout
    assert "--evidence-root" in help_result.stdout
    assert "--correct" not in help_result.stdout

    missing_root = subprocess.run(
        [sys.executable, "-m", RUNNER_MODULE, "--run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert missing_root.returncode == 2
    assert "--run and --resumable-smoke require --evidence-root" in missing_root.stderr

    forbidden_root = tmp_path / "must-not-exist"
    preflight_with_root = subprocess.run(
        [
            sys.executable,
            "-m",
            RUNNER_MODULE,
            "--preflight",
            "--evidence-root",
            str(forbidden_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert preflight_with_root.returncode == 2
    assert "--evidence-root requires --run" in preflight_with_root.stderr
    assert not forbidden_root.exists()


def _read_json(name: str) -> tuple[bytes, dict[str, object]]:
    body = (EVIDENCE / name).read_bytes()
    value = json.loads(body)
    assert isinstance(value, dict)
    return body, value


def _runs_by_id(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    runs = manifest["runs"]
    assert isinstance(runs, list)
    return {str(run["run_id"]): run for run in runs if isinstance(run, dict)}


def _changes_by_run(
    correction: dict[str, object],
    key: str,
) -> dict[str, dict[str, object]]:
    changes = correction[key]
    assert isinstance(changes, list)
    return {
        str(change["run_id"]): change
        for change in changes
        if isinstance(change, dict)
    }


def _is_identity(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()
