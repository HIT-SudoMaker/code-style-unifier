from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tests.harness_acceptance import (
    ACCEPTANCE_PROFILES,
    CASE_NAMES,
    FIXTURE_PROVENANCE,
    OPENING_PROMPT,
    CapsuleRequest,
    ClaudeAcceptanceProfile,
    CodexAcceptanceProfile,
    HarnessPreflight,
    audit_observation,
    redact_transcript,
)
from tests.harness_acceptance_runner import classify_acceptance


ROOT = Path(__file__).parents[2]
RECORDINGS = Path(__file__).parent / "fixtures" / "harness"


def test_profiles_are_one_closed_codex_then_claude_composition() -> None:
    assert tuple(type(profile) for profile in ACCEPTANCE_PROFILES) == (
        CodexAcceptanceProfile,
        ClaudeAcceptanceProfile,
    )
    assert tuple(profile.name for profile in ACCEPTANCE_PROFILES) == (
        "codex",
        "claude",
    )
    assert len({profile.name for profile in ACCEPTANCE_PROFILES}) == 2
    with pytest.raises(FrozenInstanceError):
        ACCEPTANCE_PROFILES[0].name = "claude"  # type: ignore[misc]


def test_profiles_own_exact_preflight_commands_and_flags(monkeypatch) -> None:
    monkeypatch.setattr(
        "tests.harness_acceptance.shutil.which",
        lambda name: f"C:/reviewed/{name}.exe",
    )
    calls: list[tuple[str, ...]] = []
    codex_flags = (
        "--ephemeral --ignore-user-config --strict-config --skip-git-repo-check "
        "--sandbox --cd --json"
    )
    claude_flags = (
        "--no-session-persistence --no-chrome --setting-sources "
        "--strict-mcp-config --mcp-config --tools --allowedTools "
        "--disallowedTools --permission-mode --output-format"
    )

    def capture(command: tuple[str, ...]) -> str:
        calls.append(command)
        if command[-1] == "--version":
            return f"{Path(command[0]).stem} 1.2.3"
        if command == ("C:/reviewed/codex.exe", "--help"):
            return "--ask-for-approval"
        return codex_flags if "exec" in command else claude_flags

    preflights = tuple(profile.preflight(capture) for profile in ACCEPTANCE_PROFILES)

    assert preflights == (
        HarnessPreflight("codex 1.2.3", ()),
        HarnessPreflight("claude 1.2.3", ()),
    )
    assert calls == [
        ("C:/reviewed/codex.exe", "--version"),
        ("C:/reviewed/codex.exe", "--help"),
        ("C:/reviewed/codex.exe", "exec", "--help"),
        ("C:/reviewed/claude.exe", "--version"),
        ("C:/reviewed/claude.exe", "--help"),
    ]

    incomplete = CodexAcceptanceProfile().preflight(
        lambda command: (
            "codex 1.2.3"
            if command[-1] == "--version"
            else (
                "--ask-for-approval"
                if command == ("C:/reviewed/codex.exe", "--help")
                else "--json"
            )
        )
    )
    assert incomplete.missing_flags == (
        "--ephemeral",
        "--ignore-user-config",
        "--strict-config",
        "--skip-git-repo-check",
        "--sandbox",
        "--cd",
    )


@pytest.mark.parametrize("profile", ACCEPTANCE_PROFILES)
def test_profile_prepare_owns_native_layout_environment_and_invocation(
    profile,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "tests.harness_acceptance.shutil.which",
        lambda name: f"C:/reviewed/{name}.exe",
    )
    inherited = {
        "PATH": "C:/runtime",
        "SYSTEMROOT": "C:/Windows",
        "OPENAI_API_KEY": "codex-auth",
        "CODEX_HOME": "C:/codex-home",
        "ANTHROPIC_API_KEY": "claude-auth",
        "CLAUDE_CONFIG_DIR": "C:/claude-home",
        "UNRELATED_SECRET": "must-not-cross",
    }
    prepared = profile.prepare(_request(tmp_path / profile.name, inherited=inherited))
    capsule = prepared.capsule
    invocation = prepared.invocation

    assert invocation.cwd == capsule.root
    assert invocation.environment["PATH"].startswith(str(capsule.root) + os.pathsep)
    assert invocation.environment["SYSTEMROOT"] == "C:/Windows"
    assert "UNRELATED_SECRET" not in invocation.environment
    skills = tuple(capsule.root.rglob("SKILL.md"))
    assert len(skills) == 1
    assert (
        skills[0].read_bytes()
        == (ROOT / "skills" / "metacraft-design" / "SKILL.md").read_bytes()
    )

    if profile.name == "codex":
        assert skills[0] == (
            capsule.root / ".agents" / "skills" / "metacraft-design" / "SKILL.md"
        )
        assert invocation.argv[0] == "C:/reviewed/codex.exe"
        assert invocation.argv[1:8] == (
            "--ask-for-approval",
            "never",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--strict-config",
            "--skip-git-repo-check",
        )
        assert invocation.argv[8:] == (
            "-C",
            str(capsule.root),
            "-s",
            "workspace-write",
            "-c",
            'web_search="disabled"',
            "-c",
            "sandbox_workspace_write.network_access=false",
            "--json",
            "-",
        )
        assert "--dangerously-bypass-approvals-and-sandbox" not in invocation.argv
        assert invocation.stdin == OPENING_PROMPT
        assert invocation.environment["OPENAI_API_KEY"] == "codex-auth"
        assert "ANTHROPIC_API_KEY" not in invocation.environment
        assert not (capsule.root / ".claude").exists()
    else:
        assert skills[0] == (
            capsule.root / ".claude" / "skills" / "metacraft-design" / "SKILL.md"
        )
        assert invocation.argv[0] == "C:/reviewed/claude.exe"
        assert "Read,Write,Bash" in invocation.argv
        assert "Read(./**),Write(./**),Bash(metacraft *)" in invocation.argv
        assert invocation.argv[-1] == OPENING_PROMPT
        assert invocation.stdin is None
        assert invocation.environment["ANTHROPIC_API_KEY"] == "claude-auth"
        assert "OPENAI_API_KEY" not in invocation.environment
        assert json.loads((capsule.root / "empty-mcp.json").read_text()) == {
            "mcpServers": {}
        }
        assert json.loads((capsule.root / ".claude" / "settings.json").read_text())[
            "permissions"
        ]["deny"] == ["WebSearch", "WebFetch"]


def test_profiles_prepare_the_same_blind_scientific_request(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "tests.harness_acceptance.shutil.which", lambda name: f"{name}.exe"
    )
    for index, case_name in enumerate(CASE_NAMES):
        profile = ACCEPTANCE_PROFILES[index % len(ACCEPTANCE_PROFILES)]
        prepared = profile.prepare(
            _request(tmp_path / f"capsule-{index}", case_name=case_name)
        )
        completed = subprocess.run(
            [
                str(prepared.capsule.root / "metacraft.exe"),
                "conduct",
                "--brief",
                "blind-brief.json",
                "--application-root",
                "prepared-application-root",
                "--material-library",
                "reviewed-materials.toml",
            ],
            cwd=prepared.capsule.root,
            env=prepared.invocation.environment,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        outcome = json.loads(completed.stdout)
        assert outcome["outcome"] == "consultation_required"
        request = outcome["value"]["request"]
        assert request["values"]["question_kind"] == "period"
        assert request["values"]["answer_contract"]["document_fields"] == [
            "conclusion",
            "external_claims",
            "request_identity",
        ]
    assert FIXTURE_PROVENANCE["purpose"] == "interface acceptance; not physical truth"


@pytest.mark.parametrize("profile", ACCEPTANCE_PROFILES)
def test_profiles_prepare_fresh_sessions_over_one_unchanged_capsule(
    profile,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "tests.harness_acceptance.shutil.which", lambda name: f"C:/reviewed/{name}.exe"
    )
    prepared = profile.prepare(_request(tmp_path / profile.name))
    before = {
        path.relative_to(prepared.capsule.root): path.read_bytes()
        for path in prepared.capsule.root.rglob("*")
        if path.is_file()
    }

    resumed = profile.prepare_session(
        prepared.capsule,
        inherited_environment={
            "PATH": "C:/runtime",
            "SYSTEMROOT": "C:/Windows",
            "OPENAI_API_KEY": "codex-auth",
            "ANTHROPIC_API_KEY": "claude-auth",
        },
        opening_prompt="Resume the same root through one typed transition.",
    )

    assert resumed.capsule is prepared.capsule
    assert resumed.invocation.cwd == prepared.capsule.root
    assert (
        resumed.invocation.stdin
        if profile.name == "codex"
        else resumed.invocation.argv[-1]
    ) == "Resume the same root through one typed transition."
    assert {
        path.relative_to(prepared.capsule.root): path.read_bytes()
        for path in prepared.capsule.root.rglob("*")
        if path.is_file()
    } == before


@pytest.mark.parametrize(
    ("profile", "recording_name", "event_count", "explanation_fragment"),
    (
        (
            CodexAcceptanceProfile(),
            "codex-native.jsonl",
            7,
            "Stopped at the required executable-evidence boundary.",
        ),
        (
            ClaudeAcceptanceProfile(),
            "claude-native.jsonl",
            3,
            "Failed to authenticate: OAuth session expired",
        ),
    ),
)
def test_profiles_observe_stable_real_outer_recordings(
    profile,
    recording_name: str,
    event_count: int,
    explanation_fragment: str,
    tmp_path: Path,
) -> None:
    capsule = tmp_path / "capsule"
    capsule.mkdir()
    transcript = (RECORDINGS / recording_name).read_bytes()

    observation = profile.observe(transcript)
    audit = audit_observation(observation, capsule=capsule)
    redacted_observation = profile.observe(
        redact_transcript(transcript, capsule=capsule, repository=ROOT)
    )
    redacted_audit = audit_observation(redacted_observation, capsule=capsule)

    assert observation.event_count == event_count
    assert observation.violations == ()
    assert explanation_fragment in observation.explanation
    assert audit["is_confined"]
    assert redacted_audit["is_confined"] == audit["is_confined"]
    if profile.name == "codex":
        assert observation.commands
        assert observation.accesses == (
            ("read", r".\metacraft.exe"),
            ("read", r".\metacraft.exe"),
        )
    else:
        assert observation.commands == ()
        assert observation.accesses == ()


def test_derived_claude_tool_cases_normalize_then_share_policy(tmp_path: Path) -> None:
    """Tool blocks are derived mutations, not a real Claude tool-use recording."""

    capsule = tmp_path / "capsule"
    capsule.mkdir()
    valid = _derived_claude_tools(
        [
            {
                "type": "tool_use",
                "name": "Read",
                "input": {"file_path": "blind-brief.json"},
            },
            {
                "type": "tool_use",
                "name": "Bash",
                "input": {
                    "command": (
                        "metacraft conduct --brief blind-brief.json "
                        "--application-root prepared-application-root "
                        "--material-library reviewed-materials.toml"
                    )
                },
            },
        ]
    )
    observation = ClaudeAcceptanceProfile().observe(valid)
    audit = audit_observation(observation, capsule=capsule)
    assert observation.violations == ()
    assert audit["is_confined"]
    assert audit["read_paths"] == ["blind-brief.json"]

    invalid = _derived_claude_tools(
        [
            {
                "type": "tool_use",
                "name": "write",
                "input": {"file_path": "unexpected.json"},
            },
            {"type": "tool_use", "name": "WebFetch", "input": {"file_path": "outside"}},
            {
                "type": "tool_use",
                "name": "Bash",
                "input": {"command": "python steal.py"},
            },
        ]
    )
    rejected = audit_observation(
        ClaudeAcceptanceProfile().observe(invalid), capsule=capsule
    )
    assert not rejected["is_confined"]
    assert rejected["violations"]["forbidden_events"] == ["write", "WebFetch"]
    assert rejected["violations"]["invalid_commands"] == ["python steal.py"]

    malformed = audit_observation(
        ClaudeAcceptanceProfile().observe(
            _derived_claude_tools(
                [
                    {"type": "tool_use", "name": "Read", "input": {}},
                    {"type": "tool_use", "name": "Bash", "input": {}},
                ]
            )
        ),
        capsule=capsule,
    )
    assert malformed["violations"]["forbidden_events"] == ["Read", "Bash"]
    assert not malformed["is_confined"]


def test_codex_profile_rejects_unreviewed_command_and_write(tmp_path: Path) -> None:
    capsule = tmp_path / "capsule"
    capsule.mkdir()
    transcript = (
        json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "command_execution", "command": "Get-ChildItem Env:"},
            }
        )
        + "\n"
        + json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "file_change",
                    "changes": [{"path": "unexpected.json"}],
                },
            }
        )
        + "\n"
    ).encode()

    audit = audit_observation(
        CodexAcceptanceProfile().observe(transcript), capsule=capsule
    )

    assert audit["violations"]["invalid_commands"] == ["Get-ChildItem Env:"]
    assert audit["violations"]["invalid_write_paths"] == ["unexpected.json"]
    assert not audit["is_confined"]


@pytest.mark.parametrize("profile", ACCEPTANCE_PROFILES)
def test_profile_observation_fails_closed_on_event_mutations(
    profile, tmp_path: Path
) -> None:
    capsule = tmp_path / "capsule"
    capsule.mkdir()
    cases = (
        b"not-json\n",
        b"{}\n",
        b'{"type":"future.event"}\n',
        b'{"Type":"turn.started"}\n',
    )
    for transcript in cases:
        audit = audit_observation(profile.observe(transcript), capsule=capsule)
        assert not audit["is_confined"]


def test_shared_audit_rejects_escape_and_invalid_answer_write(tmp_path: Path) -> None:
    capsule = tmp_path / "capsule"
    capsule.mkdir()
    outside = str(tmp_path.parent / "outside.json")
    transcript = _derived_claude_tools(
        [
            {"type": "tool_use", "name": "Read", "input": {"file_path": outside}},
            {
                "type": "tool_use",
                "name": "Write",
                "input": {"file_path": "$CAPSULE/../escape.json"},
            },
            {
                "type": "tool_use",
                "name": "Write",
                "input": {"file_path": "unexpected-answer.json"},
            },
        ]
    )

    audit = audit_observation(
        ClaudeAcceptanceProfile().observe(transcript), capsule=capsule
    )

    assert audit["violations"]["outside_capsule_paths"] == [
        outside,
        "$CAPSULE/../escape.json",
    ]
    assert audit["violations"]["invalid_write_paths"] == [
        "$CAPSULE/../escape.json",
        "unexpected-answer.json",
    ]
    assert not audit["is_confined"]


def test_redaction_covers_json_paths_auth_and_session_identifiers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    capsule = tmp_path / "capsule"
    session = "79a0ac44-22b2-49be-b012-a5852b9fa5bc"
    monkeypatch.setenv("ACCEPTANCE_TEST_TOKEN", "secret-value-123")
    transcript = (
        json.dumps(
            {
                "cwd": str(capsule),
                "memory_paths": {"auto": str(Path.home() / ".claude")},
                "session_id": session,
                "token": "secret-value-123",
            }
        ).encode()
        + b"\n"
    )

    redacted = redact_transcript(transcript, capsule=capsule, repository=ROOT)

    assert b"$CAPSULE" in redacted
    assert b"$USER_HOME" in redacted
    assert b"$SESSION_ID" in redacted
    assert b"$REDACTED_AUTH_VALUE" in redacted
    assert session.encode() not in redacted
    assert b"secret-value-123" not in redacted


def test_acceptance_classification_preserves_failure_position() -> None:
    before = {
        "is_confined": True,
        "process_exit_code": 1,
        "accepted_answer_files": [],
        "scientific": {"advice": [], "selected": {}, "current_question": "period"},
    }
    after = {
        **before,
        "accepted_answer_files": ["period-answer.json"],
        "scientific": {
            "advice": [{"kind": "period"}],
            "selected": {"period_nm": 400},
            "current_question": "height",
        },
    }

    assert classify_acceptance(before)["consultation"] == (
        "process_failed_before_advice"
    )
    assert classify_acceptance(after)["consultation"] == (
        "process_failed_after_period_advice"
    )


def _request(
    root: Path,
    *,
    case_name: str = CASE_NAMES[0],
    inherited: dict[str, str] | None = None,
) -> CapsuleRequest:
    return CapsuleRequest(
        root=root,
        case_name=case_name,
        repository=ROOT,
        python_executable=Path(sys.executable),
        inherited_environment=dict(os.environ) if inherited is None else inherited,
        opening_prompt=OPENING_PROMPT,
    )


def _derived_claude_tools(blocks: list[dict[str, object]]) -> bytes:
    """Derive tool blocks from the stable real Claude assistant outer envelope."""

    lines = (
        (RECORDINGS / "claude-native.jsonl").read_text(encoding="utf-8").splitlines()
    )
    event = json.loads(lines[1])
    event["message"]["content"] = blocks
    return (json.dumps(event, separators=(",", ":")) + "\n").encode()
