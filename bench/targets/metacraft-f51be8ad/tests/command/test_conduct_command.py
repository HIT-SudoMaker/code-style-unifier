from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import shutil
import subprocess
import sys

import metacraft.command as command
import pytest
from metacraft.science.conduct import ConsultationAnswerRejected, conduct
from metacraft.science.compile import InvalidBrief
from metacraft.science.consultation import (
    ConsultationAnswer,
    EvidenceRequired,
)
from metacraft.solvers.lumerical_fdtd.metalens_evidence import (
    LumericalMetalensEvidence,
)
from tests.brief_fixtures import propagation_brief


ROOT = Path(__file__).parents[2]
PYTHON = Path(sys.executable)
INVALID_BRIEF_OUTCOME = (
    b'{"schema":"metacraft.command.conduct_outcome",'
    b'"outcome":"invalid_brief",'
    b'"value":{"reason":"brief_incomplete:dimension_step_nm"}}'
)


def _write_inputs(root: Path) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True)
    brief_path = root / "blind brief.json"
    brief = propagation_brief()
    incomplete = replace(
        brief,
        dimension_step_nm=None,
        omissions=(
            *brief.omissions,
            "aperture",
            "atom_height_nm",
            "cell_period_nm",
            "dimension_step_nm",
        ),
    )
    brief_path.write_bytes(incomplete.canonical_bytes())
    material_library = root / "reviewed material library.toml"
    shutil.copyfile(ROOT / "materials" / "lumerical.toml", material_library)
    return brief_path, material_library, root / "application root"


def _complete_brief():
    brief = propagation_brief()
    return replace(
        brief,
        omissions=(
            *brief.omissions,
            "aperture",
            "atom_height_nm",
            "cell_period_nm",
        ),
    )


def _write_complete_brief(path: Path) -> None:
    path.write_bytes(_complete_brief().canonical_bytes())


def _run_module(
    *arguments: str,
    cwd: Path,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(PYTHON), "-m", "metacraft.command", *arguments],
        cwd=cwd,
        env={
            **os.environ,
            "PYTHONUTF8": "1",
            **({} if environment is None else environment),
        },
        capture_output=True,
        check=False,
    )


def test_command_emits_one_exact_typed_outcome_without_claiming_invalid_brief(
    tmp_path: Path,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )

    completed = _run_module(
        "conduct",
        "--brief",
        str(brief_path),
        "--application-root",
        str(application_root),
        "--material-library",
        str(material_library),
        cwd=working_directory,
    )

    assert completed.returncode == 0
    assert completed.stdout == INVALID_BRIEF_OUTCOME
    assert completed.stderr == b""
    assert not application_root.exists()


def test_command_rejects_malformed_answer_with_stderr_only(
    tmp_path: Path,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    answer_path = working_directory / "malformed answer.json"
    answer_path.write_bytes(b"{}")

    completed = _run_module(
        "conduct",
        "--brief",
        str(brief_path),
        "--application-root",
        str(application_root),
        "--material-library",
        str(material_library),
        "--answer",
        str(answer_path),
        cwd=working_directory,
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == (
        b'{"schema":"metacraft.command.input_failure",'
        b'"reason":"answer_document_invalid"}'
    )
    assert not application_root.exists()


@pytest.mark.parametrize("answer_bytes", (b"null", b"[]", b'"answer"'))
def test_command_rejects_non_mapping_answer_json_as_exact_input_failure(
    tmp_path: Path,
    answer_bytes: bytes,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    _write_complete_brief(brief_path)
    answer_path = working_directory / "non-mapping answer.json"
    answer_path.write_bytes(answer_bytes)

    completed = _run_module(
        "conduct",
        "--brief",
        str(brief_path),
        "--application-root",
        str(application_root),
        "--material-library",
        str(material_library),
        "--answer",
        str(answer_path),
        cwd=working_directory,
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == (
        b'{"schema":"metacraft.command.input_failure",'
        b'"reason":"answer_document_invalid"}'
    )
    assert not application_root.exists()


def test_command_rejects_noncanonical_brief_and_answer_bytes(
    tmp_path: Path,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    canonical_brief = _complete_brief().canonical_bytes()
    answer_path = working_directory / "answer.json"
    answer_path.write_bytes(
        b" "
        + ConsultationAnswer(
            request_identity="sha256:fixture",
            conclusion=EvidenceRequired(
                missing_fact="fixture",
                reason="fixture",
            ),
            external_claims=(),
        ).document().to_bytes()
    )

    cases = (
        (b" " + canonical_brief, None, b"brief_document_invalid"),
        (canonical_brief, answer_path, b"answer_document_invalid"),
    )
    for brief_bytes, answer, reason in cases:
        brief_path.write_bytes(brief_bytes)
        arguments = [
            "conduct",
            "--brief",
            str(brief_path),
            "--application-root",
            str(application_root),
            "--material-library",
            str(material_library),
        ]
        if answer is not None:
            arguments.extend(("--answer", str(answer)))
        completed = _run_module(*arguments, cwd=working_directory)
        assert completed.returncode == 2
        assert completed.stdout == b""
        assert completed.stderr == (
            b'{"schema":"metacraft.command.input_failure","reason":"'
            + reason
            + b'"}'
        )
        assert not application_root.exists()


def test_malformed_cli_uses_only_the_closed_input_diagnostic(
    tmp_path: Path,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    working_directory.mkdir()

    completed = _run_module(
        "conduct",
        "--unknown-option",
        cwd=working_directory,
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == (
        b'{"schema":"metacraft.command.input_failure",'
        b'"reason":"command_arguments_invalid"}'
    )


def test_cli_rejects_abbreviated_and_duplicate_singleton_options(
    tmp_path: Path,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )

    for arguments in (
        (
            "conduct",
            "--brief",
            str(brief_path),
            "--application-root",
            str(application_root),
            "--material",
            str(material_library),
        ),
        (
            "conduct",
            "--brief",
            str(brief_path),
            "--brief",
            str(brief_path),
            "--application-root",
            str(application_root),
            "--material-library",
            str(material_library),
        ),
    ):
        completed = _run_module(*arguments, cwd=working_directory)
        assert completed.returncode == 2
        assert completed.stdout == b""
        assert completed.stderr == (
            b'{"schema":"metacraft.command.input_failure",'
            b'"reason":"command_arguments_invalid"}'
        )


def test_command_validates_required_library_without_lumerical_environment(
    tmp_path: Path,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    material_library.write_text("not valid toml =", encoding="utf-8")

    completed = _run_module(
        "conduct",
        "--brief",
        str(brief_path),
        "--application-root",
        str(application_root),
        "--material-library",
        str(material_library),
        cwd=working_directory,
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == (
        b'{"schema":"metacraft.command.input_failure",'
        b'"reason":"material_library_invalid"}'
    )
    assert not application_root.exists()


def test_command_without_environment_stops_honestly_without_native_adapter(
    tmp_path: Path,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    _write_complete_brief(brief_path)

    completed = _run_module(
        "conduct",
        "--brief",
        str(brief_path),
        "--application-root",
        str(application_root),
        "--material-library",
        str(material_library),
        cwd=working_directory,
    )

    assert completed.returncode == 0
    assert completed.stderr == b""
    assert completed.stdout.startswith(
        b'{"schema":"metacraft.command.conduct_outcome",'
        b'"outcome":"waiting_studies","value":'
    )
    assert completed.stdout.endswith(b"}")
    assert (application_root / "authority").is_dir()
    assert {path.name for path in (application_root / "runs").iterdir()} == {
        ".conduct.lock"
    }


def test_subprocess_writes_utf8_when_console_encoding_is_ascii(
    tmp_path: Path,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    brief_path.write_bytes(
        replace(
            _complete_brief(),
            wording="设计一个可靠的超透镜。",
        ).canonical_bytes()
    )

    completed = _run_module(
        "conduct",
        "--brief",
        str(brief_path),
        "--application-root",
        str(application_root),
        "--material-library",
        str(material_library),
        cwd=working_directory,
        environment={"PYTHONIOENCODING": "ascii"},
    )

    assert completed.returncode == 0
    assert completed.stderr == b""
    assert "设计一个可靠的超透镜。".encode() in completed.stdout
    assert completed.stdout.endswith(b"}")


def test_command_bytes_equal_direct_conduct_encoding(tmp_path: Path) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    brief = _complete_brief()
    brief_path.write_bytes(brief.canonical_bytes())
    direct = conduct(
        brief,
        application_root=working_directory / "direct application root",
    )

    completed = _run_module(
        "conduct",
        "--brief",
        str(brief_path),
        "--application-root",
        str(application_root),
        "--material-library",
        str(material_library),
        cwd=working_directory,
    )

    assert completed.returncode == 0
    assert completed.stdout == command.encode_conduct_outcome(direct)


def test_explicit_environment_composes_the_lumerical_adapter(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    environment_path = working_directory / "Lumerical environment.env"
    environment_path.write_text(
        "LUMERICAL_FDTD_PATH=C:/Program Files/Lumerical/fdtd.exe\n",
        encoding="utf-8",
    )
    observed: list[object] = []

    def observe_conduct(brief, **keywords):
        del brief
        observed.append(keywords["evidence_adapter"])
        return InvalidBrief("fixture_invalid")

    monkeypatch.setattr(command, "conduct", observe_conduct)

    exit_code = command.main(
        (
            "conduct",
            "--brief",
            str(brief_path),
            "--application-root",
            str(application_root),
            "--material-library",
            str(material_library),
            "--lumerical-environment",
            str(environment_path),
        )
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert isinstance(observed[0], LumericalMetalensEvidence)
    assert captured.out == (
        '{"schema":"metacraft.command.conduct_outcome",'
        '"outcome":"invalid_brief",'
        '"value":{"reason":"fixture_invalid"}}'
    )


def test_typed_answer_rejection_is_an_input_failure_without_root_claim(
    tmp_path: Path,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    _write_complete_brief(brief_path)
    answer_path = working_directory / "unrequested answer.json"
    answer_path.write_bytes(
        ConsultationAnswer(
            request_identity="sha256:unrequested",
            conclusion=EvidenceRequired(
                missing_fact="an exact request",
                reason="no request has been emitted",
            ),
            external_claims=(),
        ).document().to_bytes()
    )

    completed = _run_module(
        "conduct",
        "--brief",
        str(brief_path),
        "--application-root",
        str(application_root),
        "--material-library",
        str(material_library),
        "--answer",
        str(answer_path),
        cwd=working_directory,
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == (
        b'{"schema":"metacraft.command.input_failure",'
        b'"reason":"consultation_answer_rejected:not_required"}'
    )
    assert not application_root.exists()


def test_command_translates_the_typed_invalid_reason_only_at_its_interface(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    _write_complete_brief(brief_path)
    answer_path = working_directory / "answer.json"
    answer_path.write_bytes(
        ConsultationAnswer(
            request_identity="sha256:fixture",
            conclusion=EvidenceRequired(
                missing_fact="fixture",
                reason="fixture",
            ),
            external_claims=(),
        ).document().to_bytes()
    )

    def reject_answer(*_args, **_kwargs):
        raise ConsultationAnswerRejected("invalid")

    monkeypatch.setattr(command, "conduct", reject_answer)

    exit_code = command.main(
        (
            "conduct",
            "--brief",
            str(brief_path),
            "--application-root",
            str(application_root),
            "--material-library",
            str(material_library),
            "--answer",
            str(answer_path),
        )
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == (
        '{"schema":"metacraft.command.input_failure",'
        '"reason":"consultation_answer_rejected:invalid"}'
    )


def test_storage_fault_is_not_relabelled_as_input_or_science(
    tmp_path: Path,
) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    _write_complete_brief(brief_path)
    application_root.mkdir()
    (application_root / "foreign.txt").write_text("foreign", encoding="utf-8")

    completed = _run_module(
        "conduct",
        "--brief",
        str(brief_path),
        "--application-root",
        str(application_root),
        "--material-library",
        str(material_library),
        cwd=working_directory,
    )

    assert completed.returncode not in {0, 2}
    assert completed.stdout == b""
    assert b"application_root_invalid" in completed.stderr
    assert b"metacraft.command.input_failure" not in completed.stderr
    assert b"metacraft.command.conduct_outcome" not in completed.stderr


def test_installed_launcher_handles_paths_with_spaces(tmp_path: Path) -> None:
    working_directory = tmp_path / "working directory with spaces"
    brief_path, material_library, application_root = _write_inputs(
        working_directory
    )
    launcher = PYTHON.parent / (
        "Scripts/metacraft.exe" if os.name == "nt" else "bin/metacraft"
    )
    assert launcher.is_file()

    completed = subprocess.run(
        [
            str(launcher),
            "conduct",
            "--brief",
            str(brief_path),
            "--application-root",
            str(application_root),
            "--material-library",
            str(material_library),
        ],
        cwd=working_directory,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stderr == b""
    assert completed.stdout == INVALID_BRIEF_OUTCOME
