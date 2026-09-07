from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


ROOT = Path(__file__).parents[2]
SCRIPT = (
    ROOT
    / ".scratch"
    / "four-brief-baseline"
    / "run_ticket03_codex_executable_smoke.py"
)


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("ticket03_codex_smoke", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_defaults_to_a_non_executing_one_session_plan(capsys) -> None:
    smoke = _load_smoke_module()

    assert smoke.main([]) == 0

    plan = json.loads(capsys.readouterr().out)
    assert plan == {
        "approval_policy": "never",
        "case": "mcclung-2024-low-na-propagation",
        "network_access": False,
        "planned_capsule_count": 1,
        "planned_session_count": 1,
        "profile": "codex",
        "retry_count": 0,
        "sandbox": "workspace-write",
        "schema": "metacraft.acceptance.ticket03_codex_executable_smoke_plan",
    }


def test_smoke_accepts_only_one_completed_consultation_command() -> None:
    smoke = _load_smoke_module()
    event = {
        "type": "item.completed",
        "item": {
            "type": "command_execution",
            "command": (
                '"powershell.exe" -Command ".\\metacraft.exe conduct '
                '--brief blind-brief.json --application-root '
                'prepared-application-root --material-library reviewed-materials.toml"'
            ),
            "aggregated_output": '{"outcome":"consultation_required"}',
            "exit_code": 0,
            "status": "completed",
        },
    }
    transcript = (json.dumps(event) + "\n").encode()

    assert smoke.inspect_metacraft_command(transcript) == {
        "attempt_count": 1,
        "completed_count": 1,
        "consultation_required_count": 1,
    }
    assert smoke.inspect_metacraft_command(transcript + transcript)["attempt_count"] == 2


def test_smoke_resolves_a_relative_evidence_root_before_preparing_codex(
    tmp_path: Path,
    monkeypatch,
) -> None:
    smoke = _load_smoke_module()
    captured = {}
    original_prepare = smoke.CodexAcceptanceProfile.prepare

    def prepare(profile, request):
        captured["request"] = request
        return original_prepare(profile, request)

    def execute(invocation):
        captured["invocation"] = invocation
        event = {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": (
                    '"powershell.exe" -Command ".\\metacraft.exe conduct '
                    '--brief blind-brief.json --application-root '
                    'prepared-application-root --material-library '
                    'reviewed-materials.toml"'
                ),
                "aggregated_output": '{"outcome":"consultation_required"}',
                "exit_code": 0,
                "status": "completed",
            },
        }
        return subprocess.CompletedProcess(
            invocation.argv,
            0,
            stdout=(json.dumps(event) + "\n").encode(),
            stderr=b"",
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(smoke.CodexAcceptanceProfile, "prepare", prepare)
    monkeypatch.setattr(
        smoke.CodexAcceptanceProfile,
        "preflight",
        lambda self, capture: SimpleNamespace(
            version="codex-test",
            missing_flags=(),
        ),
    )
    monkeypatch.setattr(smoke, "_execute_once", execute)

    smoke.run_smoke(Path("relative-evidence"))

    request = captured["request"]
    invocation = captured["invocation"]
    expected_capsule = (tmp_path / "relative-evidence" / "capsule").resolve()
    assert request.root == expected_capsule
    assert request.root.is_absolute()
    assert invocation.cwd == expected_capsule
    assert invocation.cwd.is_absolute()
    codex_root = Path(invocation.argv[invocation.argv.index("-C") + 1])
    assert codex_root == expected_capsule
    assert codex_root.is_absolute()
