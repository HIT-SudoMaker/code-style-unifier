from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tests.harness_acceptance import (
    ACCEPTANCE_PROFILES,
    HarnessObservation,
    HarnessAcceptanceProfile,
    HarnessInvocation,
    PreparedCapsule,
    PreparedHarnessRun,
)
from tests.harness_acceptance_runner import (
    _smoke_session_status,
    audit_resumable_cadence,
    classify_acceptance,
    preflight,
    run_matrix,
    run_resumable_smoke,
)


RECORDINGS = Path(__file__).parent / "fixtures" / "harness"


class RecordedHarnessExecution:
    """One-way test adapter from native recordings to terminal captures."""

    def __init__(self, captures: list[dict[str, object]] | None = None) -> None:
        self.captures = captures or []
        self.calls: list[tuple[HarnessAcceptanceProfile, HarnessInvocation]] = []

    def __call__(
        self,
        profile: HarnessAcceptanceProfile,
        invocation: HarnessInvocation,
    ) -> dict[str, Any]:
        self.calls.append((profile, invocation))
        override = self.captures[len(self.calls) - 1] if self.captures else {}
        transcript = (RECORDINGS / f"{profile.name}-native.jsonl").read_bytes()
        return {
            "returncode": override.get("returncode", 0),
            "stdout": override.get("stdout", transcript),
            "stderr": override.get("stderr", b""),
            "timed_out": override.get("timed_out", False),
        }


def test_resumable_smoke_is_fixed_codex_then_claude_with_fresh_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions: list[str] = []
    inspections = iter(
        (
            {
                "current_question": "period",
                "outcome": "ConsultationRequired",
                "authority_revision": 1,
                "answers": [],
            },
            {"current_question": "height", "outcome": "ConsultationRequired"},
            {"current_question": None, "outcome": "WaitingStudies"},
            {
                "current_question": None,
                "outcome": "CompletedResults",
                "result_references": [{"content_hash": "codex"}],
            },
            {
                "current_question": None,
                "outcome": "CompletedResults",
                "result_references": [{"content_hash": "codex"}],
            },
            {
                "current_question": "period",
                "outcome": "ConsultationRequired",
                "authority_revision": 1,
                "answers": [],
            },
            {"current_question": "height", "outcome": "ConsultationRequired"},
            {"current_question": None, "outcome": "WaitingStudies"},
            {
                "current_question": None,
                "outcome": "CompletedResults",
                "result_references": [{"content_hash": "claude"}],
            },
            {
                "current_question": None,
                "outcome": "CompletedResults",
                "result_references": [{"content_hash": "claude"}],
            },
        )
    )

    def prepare(profile, request):
        request.root.mkdir()
        brief = request.root / "blind-brief.json"
        brief.write_bytes(b"brief")
        materials = request.root / "reviewed-materials.toml"
        materials.write_bytes(b"materials")
        application_root = request.root / "prepared-application-root"
        application_root.mkdir()
        capsule = PreparedCapsule(
            request.root,
            request.case_name,
            application_root,
            brief,
            materials,
            request.root / "opening-prompt.txt",
        )
        invocation = HarnessInvocation((profile.name,), request.root, {}, None)
        return PreparedHarnessRun(capsule, invocation)

    def prepare_session(profile, capsule, **_keywords):
        sessions.append(profile.name)
        return PreparedHarnessRun(
            capsule,
            HarnessInvocation((profile.name,), capsule.root, {}, None),
        )

    for profile in ACCEPTANCE_PROFILES:
        monkeypatch.setattr(type(profile), "prepare", prepare)
        monkeypatch.setattr(type(profile), "prepare_session", prepare_session)
        monkeypatch.setattr(
            type(profile),
            "observe",
            lambda self, transcript: HarnessObservation(1, (), (), (), "complete"),
        )
    monkeypatch.setattr(
        "tests.harness_acceptance_runner.inspect_capsule",
        lambda capsule: next(inspections),
    )
    advances: list[str] = []

    run_resumable_smoke(
        tmp_path / "evidence",
        preflight_facts=_preflight({"codex", "claude"}),
        execute=lambda profile, invocation: {
            "returncode": 0,
            "stdout": b"{}\n",
            "stderr": b"",
            "timed_out": False,
        },
        advance_recorded_evidence=lambda brief, root, materials: (
            advances.append(root.parent.name) or b'{"outcome":"completed_results"}'
        ),
    )

    assert sessions == ["codex", "codex", "codex", "claude", "claude", "claude"]
    assert advances == ["codex", "claude"]
    report = _read(tmp_path / "evidence" / "resumable-smoke.json")
    assert [item["profile"] for item in report["profiles"]] == ["codex", "claude"]
    assert all(item["acceptance"] == "complete" for item in report["profiles"])


def test_resumable_smoke_prompt_names_the_one_literal_command() -> None:
    from tests.harness_acceptance_runner import _RESUME_ONE_TRANSITION

    assert (
        ".\\metacraft.exe conduct --brief blind-brief.json --application-root "
        "prepared-application-root --material-library reviewed-materials.toml"
    ) in _RESUME_ONE_TRANSITION
    assert "FFT" not in _RESUME_ONE_TRANSITION


@pytest.mark.parametrize(
    ("commands", "before", "after", "expected"),
    (
        (
            (
                ".\\metacraft.exe conduct --brief blind-brief.json --application-root other-root --material-library reviewed-materials.toml",
            ),
            {
                "outcome": "ConsultationRequired",
                "current_request_identity": "period",
                "authority_revision": 1,
                "answers": [],
            },
            {
                "outcome": "ConsultationRequired",
                "current_request_identity": "height",
                "authority_revision": 2,
                "answers": [],
            },
            "application_root_changed",
        ),
        (
            (),
            {
                "outcome": "ConsultationRequired",
                "current_request_identity": "period",
                "authority_revision": 1,
                "answers": [],
            },
            {
                "outcome": "ConsultationRequired",
                "current_request_identity": "height",
                "authority_revision": 2,
                "answers": [
                    {
                        "identity": "answer",
                        "request_identity": "other",
                        "is_canonical": True,
                    }
                ],
            },
            "answer_request_changed",
        ),
        (
            (
                ".\\metacraft.exe conduct --brief blind-brief.json --application-root prepared-application-root --material-library reviewed-materials.toml",
            ),
            {
                "outcome": "WaitingStudies",
                "current_request_identity": None,
                "authority_revision": 4,
                "answers": [],
            },
            {
                "outcome": "WaitingStudies",
                "current_request_identity": None,
                "authority_revision": 4,
                "answers": [],
            },
            "waiting_fact_unchanged",
        ),
        (
            (
                ".\\metacraft.exe conduct --brief blind-brief.json --application-root prepared-application-root --material-library reviewed-materials.toml --realization FFT",
            ),
            {
                "outcome": "WaitingStudies",
                "current_request_identity": None,
                "authority_revision": 4,
                "answers": [],
            },
            {
                "outcome": "CompletedResults",
                "current_request_identity": None,
                "authority_revision": 5,
                "answers": [],
            },
            "realization_selected",
        ),
        (
            (
                ".\\metacraft.exe conduct --brief blind-brief.json --application-root prepared-application-root --material-library reviewed-materials.toml",
            ),
            {
                "outcome": "CompletedResults",
                "current_request_identity": None,
                "authority_revision": 5,
                "answers": [],
            },
            {
                "outcome": "CompletedResults",
                "current_request_identity": None,
                "authority_revision": 5,
                "answers": [],
            },
            "conduct_after_completion",
        ),
    ),
)
def test_resumable_cadence_mutations_fail_closed(
    commands: tuple[str, ...],
    before: dict[str, object],
    after: dict[str, object],
    expected: str,
) -> None:
    observation = HarnessObservation(1, (), commands, (), "observed")

    assert expected in audit_resumable_cadence(
        observation,
        before=before,
        after=after,
        expected_application_root="prepared-application-root",
    )


def test_resumable_smoke_seals_authentication_failure_and_stops_fixed_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def observe(self, transcript):
        return HarnessObservation(1, (), (), (), "authentication required")

    monkeypatch.setattr(type(ACCEPTANCE_PROFILES[0]), "observe", observe)
    monkeypatch.setattr(type(ACCEPTANCE_PROFILES[1]), "observe", observe)

    run_resumable_smoke(
        tmp_path / "auth-failure",
        preflight_facts=_preflight({"codex", "claude"}),
        execute=lambda profile, invocation: (
            calls.append(profile.name)
            or {
                "returncode": 1,
                "stdout": b"{}\n",
                "stderr": b"OAuth authentication expired",
                "timed_out": False,
            }
        ),
        advance_recorded_evidence=lambda brief, root, materials: b"",
    )

    assert calls == ["codex"]
    report = _read(tmp_path / "auth-failure" / "resumable-smoke.json")
    assert report["profiles"][0]["acceptance"] == "incomplete_authentication"
    assert report["profiles"][1]["acceptance"] == "incomplete_policy_or_harness"
    session = report["profiles"][0]["sessions"][0]
    assert session == {
        "audit": "accepted",
        "returncode": 1,
        "session": 1,
        "status": "incomplete_authentication",
        "timed_out": False,
    }
    assert (
        tmp_path / "auth-failure" / "stderr" / "codex-01.txt"
    ).read_bytes() == b"OAuth authentication expired"


@pytest.mark.parametrize(
    ("returncode", "timed_out", "is_confined", "stderr", "expected"),
    (
        (124, True, True, b"", "incomplete_timeout"),
        (1, False, True, b"authentication expired", "incomplete_authentication"),
        (1, False, True, b"execution declined", "incomplete_policy_or_harness"),
        (0, False, False, b"", "incomplete_policy_or_harness"),
        (0, False, True, b"", "complete"),
    ),
)
def test_resumable_session_status_preserves_each_terminal_truth(
    returncode: int,
    timed_out: bool,
    is_confined: bool,
    stderr: bytes,
    expected: str,
) -> None:
    assert (
        _smoke_session_status(
            returncode=returncode,
            timed_out=timed_out,
            is_confined=is_confined,
            stderr=stderr,
            explanation="",
        )
        == expected
    )


def test_resumable_smoke_seals_attempted_session_before_transition_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = ACCEPTANCE_PROFILES[0]

    def prepare(self, request):
        request.root.mkdir()
        brief = request.root / "blind-brief.json"
        brief.write_bytes(b"brief")
        materials = request.root / "reviewed-materials.toml"
        materials.write_bytes(b"materials")
        application_root = request.root / "prepared-application-root"
        application_root.mkdir()
        capsule = PreparedCapsule(
            request.root,
            request.case_name,
            application_root,
            brief,
            materials,
            request.root / "opening-prompt.txt",
        )
        return PreparedHarnessRun(
            capsule,
            HarnessInvocation((self.name,), capsule.root, {}, None),
        )

    monkeypatch.setattr(type(profile), "prepare", prepare)
    monkeypatch.setattr(
        type(profile),
        "prepare_session",
        lambda self, capsule, **keywords: PreparedHarnessRun(
            capsule,
            HarnessInvocation((self.name,), capsule.root, {}, None),
        ),
    )
    monkeypatch.setattr(
        type(profile),
        "observe",
        lambda self, transcript: HarnessObservation(1, (), (), (), "observed"),
    )
    states = iter(
        (
            {
                "outcome": "ConsultationRequired",
                "current_question": "period",
                "current_request_identity": "period",
                "authority_revision": "revision-1",
                "answers": [],
            },
            {
                "outcome": "ConsultationRequired",
                "current_question": "period",
                "current_request_identity": "period",
                "authority_revision": "revision-1",
                "answers": [],
            },
        )
    )
    monkeypatch.setattr(
        "tests.harness_acceptance_runner.inspect_capsule",
        lambda capsule: next(states),
    )
    evidence = tmp_path / "transition-fault"

    with pytest.raises(RuntimeError, match="resumable_smoke_transition_incomplete"):
        run_resumable_smoke(
            evidence,
            preflight_facts=_preflight({"codex"}),
            execute=lambda selected, invocation: {
                "returncode": 0,
                "stdout": b"{}\n",
                "stderr": b"",
                "timed_out": False,
            },
        )

    manifest = _read(evidence / "resumable-smoke.json")
    record = manifest["profiles"][0]
    assert record["acceptance"] == "implementation_fault"
    assert record["reason"].startswith(
        "RuntimeError:resumable_smoke_transition_incomplete"
    )
    assert record["sessions"] == [
        {
            "audit": "accepted",
            "returncode": 0,
            "session": 1,
            "status": "complete",
            "timed_out": False,
        }
    ]
    assert (evidence / "transcripts" / "codex-01.jsonl").is_file()
    assert (evidence / "stderr" / "codex-01.txt").is_file()
    assert (evidence / "audits" / "codex-01.json").is_file()


@pytest.mark.parametrize(
    ("available", "eligible"),
    (({"codex", "claude"}, 8), ({"codex"}, 4), ({"claude"}, 4), (set(), 0)),
)
def test_recorded_campaigns_seal_every_availability_without_fictitious_sessions(
    available: set[str],
    eligible: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tests.harness_acceptance.shutil.which", lambda name: f"C:/reviewed/{name}.exe"
    )
    root = tmp_path / "fresh-campaign"
    execution = RecordedHarnessExecution()

    assert not root.exists()
    run_matrix(root, preflight_facts=_preflight(available), execute=execution)

    blind = _read(root / "blind-manifest.json")
    seal = _read(root / "sealed-manifest.json")
    assert blind["planned_cell_count"] == 8
    assert blind["eligible_cell_count"] == eligible
    assert blind["started_session_count"] == eligible == len(execution.calls)
    assert blind["session_rerun_count"] == 0
    assert len(blind["plan"]) == 8
    assert len(blind["runs"]) == eligible
    assert sum(blind["terminal_process_counts"].values()) == eligible
    assert (
        sum(entry["attempt"] == "not_started_preflight" for entry in blind["plan"])
        == 8 - eligible
    )
    for kind in ("transcripts", "stderr", "audits", "outcomes"):
        assert len(tuple((root / kind).iterdir())) == eligible
    assert not tuple((root / "answers").iterdir())
    _assert_hash_closure(root, blind, seal)
    reports = tuple((root / "post-hoc").glob("*.md"))
    assert len(reports) == 5
    report_text = "\n".join(path.read_text(encoding="utf-8") for path in reports)
    for profile in {"codex", "claude"} - available:
        assert report_text.count(f'"availability": "unavailable_preflight"') >= 4
        assert profile in report_text
    calls_before_reuse = list(execution.calls)
    with pytest.raises(FileExistsError):
        run_matrix(root, preflight_facts=_preflight(available), execute=execution)
    assert execution.calls == calls_before_reuse


def test_runner_passes_each_same_profile_object_through_the_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tests.harness_acceptance.shutil.which", lambda name: f"C:/reviewed/{name}.exe"
    )
    python = tmp_path / "runtime" / "python.exe"
    launcher = python.parent / "Scripts" / "metacraft.exe"
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes(b"recorded launcher fact")
    observed: dict[str, list[HarnessAcceptanceProfile]] = {
        "preflight": [],
        "prepare": [],
        "observe": [],
    }

    for profile in ACCEPTANCE_PROFILES:
        profile_type = type(profile)
        original_preflight = profile_type.preflight
        original_prepare = profile_type.prepare
        original_observe = profile_type.observe

        def tracked_preflight(self, capture, *, _call=original_preflight):
            observed["preflight"].append(self)
            return _call(self, capture)

        def tracked_prepare(self, request, *, _call=original_prepare):
            observed["prepare"].append(self)
            return _call(self, request)

        def tracked_observe(self, transcript, *, _call=original_observe):
            observed["observe"].append(self)
            return _call(self, transcript)

        monkeypatch.setattr(profile_type, "preflight", tracked_preflight)
        monkeypatch.setattr(profile_type, "prepare", tracked_prepare)
        monkeypatch.setattr(profile_type, "observe", tracked_observe)

    def capture(command: tuple[str, ...]) -> str:
        if command[-1] == "--version":
            return f"{Path(command[0]).stem} recorded"
        return (
            "--ask-for-approval --ephemeral --ignore-user-config --strict-config "
            "--skip-git-repo-check --sandbox --cd --json "
            "--no-session-persistence --no-chrome --setting-sources "
            "--strict-mcp-config --mcp-config --tools --allowedTools "
            "--disallowedTools --permission-mode --output-format"
        )

    facts = preflight(capture, python_executable=python)
    execution = RecordedHarnessExecution()
    run_matrix(tmp_path / "identity-campaign", preflight_facts=facts, execute=execution)

    expected_runs = [profile for _slot in range(4) for profile in ACCEPTANCE_PROFILES]
    expected_observations = [
        profile for profile in expected_runs for _raw_or_redacted in range(2)
    ]
    assert all(
        actual is expected
        for actual, expected in zip(
            observed["preflight"], ACCEPTANCE_PROFILES, strict=True
        )
    )
    assert all(
        actual is expected
        for actual, expected in zip(observed["prepare"], expected_runs, strict=True)
    )
    assert all(
        actual is expected
        for (actual, _invocation), expected in zip(
            execution.calls, expected_runs, strict=True
        )
    )
    assert all(
        actual is expected
        for actual, expected in zip(
            observed["observe"], expected_observations, strict=True
        )
    )


def test_preflight_observes_both_profiles_without_claiming_a_campaign_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    python = tmp_path / "runtime" / "python.exe"
    launcher = python.parent / "Scripts" / "metacraft.exe"
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes(b"recorded launcher fact")
    monkeypatch.setattr(
        "tests.harness_acceptance.shutil.which", lambda name: f"C:/reviewed/{name}.exe"
    )
    calls: list[tuple[str, ...]] = []

    def capture(command: tuple[str, ...]) -> str:
        calls.append(command)
        if "claude" in command[0]:
            raise RuntimeError("recorded claude preflight failure")
        if command[-1] == "--version":
            return "codex recorded"
        return "--ask-for-approval --ephemeral --ignore-user-config --strict-config --skip-git-repo-check --sandbox --cd --json"

    campaign_root = tmp_path / "must-remain-absent"
    facts = preflight(capture, python_executable=python)

    assert not campaign_root.exists()
    assert [entry["availability"] for entry in facts["profiles"]] == [
        "available",
        "unavailable_preflight",
    ]
    assert any("codex" in command[0] for command in calls)
    assert any("claude" in command[0] for command in calls)


def test_recorded_campaign_terminal_states_are_final_and_orthogonal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tests.harness_acceptance.shutil.which", lambda name: f"C:/reviewed/{name}.exe"
    )
    captures = [
        {},
        {"returncode": 1},
        {"returncode": 124, "timed_out": True},
        {"stdout": b"not-json\n"},
        {},
        {"returncode": 1},
        {"returncode": 124, "timed_out": True},
        {},
    ]
    execution = RecordedHarnessExecution(captures)
    real_inspect = __import__(
        "tests.harness_acceptance_runner", fromlist=["inspect_capsule"]
    ).inspect_capsule

    def inspect_with_one_failure(capsule):
        if capsule.root.name == "codex-03":
            raise RuntimeError("recorded inspection failure")
        return real_inspect(capsule)

    monkeypatch.setattr(
        "tests.harness_acceptance_runner.inspect_capsule", inspect_with_one_failure
    )
    root = tmp_path / "terminal-campaign"
    run_matrix(root, preflight_facts=_preflight({"codex", "claude"}), execute=execution)

    blind = _read(root / "blind-manifest.json")
    assert len(execution.calls) == 8
    assert blind["terminal_process_counts"] == {
        "completed": 4,
        "failed": 2,
        "timed_out": 2,
    }
    rejected = _read(root / "outcomes" / "claude-02.json")["classification"]
    assert rejected == {
        "attempt": "completed",
        "audit": "rejected",
        "inspection": "completed",
    }
    inspection_failed = _read(root / "outcomes" / "codex-03.json")["classification"]
    assert inspection_failed == {
        "attempt": "completed",
        "audit": "accepted",
        "inspection": "failed",
    }
    timed_out = _read(root / "outcomes" / "codex-02.json")["classification"]
    assert timed_out["attempt"] == "timed_out"
    assert timed_out["consultation"] == "process_failed_before_advice"


def test_consultation_axis_names_every_frozen_position() -> None:
    base = {"is_confined": True, "process_exit_code": 0, "accepted_answer_files": []}
    cases = (
        (
            {**base, "process_exit_code": 1, "scientific": {"advice": []}},
            "process_failed_before_advice",
        ),
        (
            {
                **base,
                "process_exit_code": 1,
                "accepted_answer_files": ["answer.json"],
                "scientific": {"advice": []},
            },
            "process_failed_after_canonical_answer",
        ),
        (
            {
                **base,
                "process_exit_code": 1,
                "scientific": {"advice": [{"kind": "period"}]},
            },
            "process_failed_after_period_advice",
        ),
        (
            {
                **base,
                "process_exit_code": 1,
                "scientific": {"advice": [{"kind": "period"}, {"kind": "height"}]},
            },
            "process_failed_after_height_advice",
        ),
        ({**base, "scientific": {"advice": []}}, "incomplete_without_advice"),
        (
            {
                **base,
                "scientific": {
                    "advice": [{"kind": "period"}],
                    "current_question": "height",
                },
            },
            "advice_retained_through_period",
        ),
        (
            {
                **base,
                "scientific": {
                    "advice": [{"kind": "period"}, {"kind": "height"}],
                    "current_question": "period",
                },
            },
            "advice_retained_through_height",
        ),
        (
            {
                **base,
                "scientific": {
                    "advice": [{"kind": "period"}, {"kind": "height"}],
                    "current_question": None,
                },
            },
            "consultation_cadence_complete",
        ),
    )
    assert [classify_acceptance(record)["consultation"] for record, _ in cases] == [
        expected for _, expected in cases
    ]


def _preflight(available: set[str]) -> dict[str, object]:
    return {
        "schema": "metacraft.acceptance.harness_preflight",
        "installed_launcher": "metacraft.exe",
        "launcher_exists": True,
        "profiles": [
            {
                "profile": name,
                "availability": (
                    "available" if name in available else "unavailable_preflight"
                ),
                "version": f"{name} recorded",
                "missing_flags": [] if name in available else ["recorded-unavailable"],
                "failure": None if name in available else "recorded_unavailable",
            }
            for name in ("codex", "claude")
        ],
    }


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    assert isinstance(value, dict)
    return value


def _digest(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _assert_hash_closure(
    root: Path, blind: dict[str, Any], seal: dict[str, Any]
) -> None:
    assert blind["preflight_sha256"] == _digest((root / "preflight.json").read_bytes())
    for run in blind["runs"]:
        run_id = run["run_id"]
        for field, directory, suffix in (
            ("transcript_sha256", "transcripts", ".jsonl"),
            ("stderr_sha256", "stderr", ".txt"),
            ("audit_sha256", "audits", ".json"),
            ("outcome_sha256", "outcomes", ".json"),
        ):
            assert run[field] == _digest(
                (root / directory / f"{run_id}{suffix}").read_bytes()
            )
        for answer in run["answers"]:
            assert answer["sha256"] == _digest(
                (root / "answers" / answer["name"]).read_bytes()
            )
    assert seal["blind_manifest_sha256"] == _digest(
        (root / "blind-manifest.json").read_bytes()
    )
    assert len(seal["reports"]) == 5
    for report in seal["reports"]:
        assert report["sha256"] == _digest(
            (root / "post-hoc" / report["name"]).read_bytes()
        )
