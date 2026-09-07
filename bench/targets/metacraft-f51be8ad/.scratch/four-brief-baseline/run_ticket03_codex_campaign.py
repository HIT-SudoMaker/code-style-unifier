from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys

MODULE_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(MODULE_ROOT))

from tests.harness_acceptance import (
    CASE_NAMES,
    CapsuleRequest,
    CodexAcceptanceProfile,
    OPENING_PROMPT,
    PreparedCapsule,
    RetainedMaterialReceipt,
    audit_observation,
    redact_transcript,
)


ROOT = MODULE_ROOT
PYTHON = Path(sys.executable)
EVIDENCE_ROOT = ROOT / ".scratch" / "four-brief-baseline" / "acceptance" / "03"
COMBINED_AUTHORITY = (
    ROOT
    / "runs"
    / "evidence"
    / "lumerical-material-mcclung-yang-20260809T091740159805Z-ed5ddf5c"
    / "authority"
)
RECEIPTS = {
    "mcclung-2024-low-na-propagation": RetainedMaterialReceipt(
        COMBINED_AUTHORITY,
        "material_observation:sha256:643d27cadf51e6e0f0743a961df77f1b3fc5ba7f2c922fe8c6c1af1512c2e9ac",
    ),
    "yang-2018-low-na-geometric": RetainedMaterialReceipt(
        COMBINED_AUTHORITY,
        "material_observation:sha256:198d3476f976d265cf7bcbd0f31a7f601b4b5f2ad12fe7aa60c37582e9d1e43b",
    ),
    "arbabi-2015-high-na-propagation": RetainedMaterialReceipt(
        ROOT / "runs" / "brief-stage-arbabi-20260808-d401d0cb" / "authority",
        "material_observation:sha256:9dfdf84442fbe42144d58a17a6c5b3b04a954c2fb077b72934bdc31ac089fe6b",
    ),
    "khorasaninejad-2016-high-na-geometric": RetainedMaterialReceipt(
        ROOT
        / "runs"
        / "brief-stage-khorasaninejad-20260808-9192e76a"
        / "authority",
        "material_observation:sha256:3b819004a658f28bc266e1e38aa45123b08afaad3e95864898da4daf8bf91e8a",
    ),
}
DOSSIER = """# Case-neutral metalens consultation dossier

This dossier contains general decision principles, not a benchmark answer.
It deliberately contains no published period or height for any tested device.

1. The request's sampling ceiling is a hard legality bound, not an instruction
   to choose its largest candidate. A usable lattice also balances spatial
   sampling, unwanted diffraction risk, feature room, and simulation cost.
   Locator: https://optics.ansys.com/hc/en-us/articles/35797097445779-Introduction-to-metalens-workflows
2. A period above the request's order ceiling may retain additional propagating
   orders. Treat that as a visible risk rather than silently calling the
   response zeroth-order; prefer a lower-risk legal candidate unless the local
   phase-control grounds justify accepting the warning.
   Locator: doi:10.1186/s43593-025-00111-y
3. For propagation phase, optical path accumulation scales approximately with
   effective-index contrast times height. Use this only as a conservative
   dimensional screen for 2-pi reach; a periodic response sweep must later
   prove phase coverage and transmission.
   Locator: https://optics.ansys.com/hc/en-us/articles/360042097313-Metalens
4. For geometric phase, rotation supplies phase only when the element provides
   suitable polarization conversion. Use the request's retardance forecast as
   a ranking ground, not as completed Jones-matrix evidence.
   Locator: doi:10.1126/science.1252727
5. Respect the emitted fabrication interval, height grid, aspect limit, and
   candidate identities exactly. Prefer an interior conservative choice when
   neighboring candidates are comparably supported, and stop at WaitingStudies
   because neither this dossier nor scalar material indices prove a cell.
"""
PROMPT = OPENING_PROMPT + (
    " Read source-dossier.md and the exact reviewed-material-*.json receipts. "
    "For source_grounded consultations, copy only genuinely used general "
    "claims and their exact locators from that dossier; it supplies no "
    "case-specific period or height. Run the local metacraft conduct command, "
    "write only canonical period-answer.json then height-answer.json, and stop "
    "only at WaitingStudies. Preserve every order caution."
)


@dataclass(frozen=True, slots=True)
class HarnessCapture:
    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool


def main() -> int:
    if EVIDENCE_ROOT.exists():
        raise FileExistsError(EVIDENCE_ROOT)
    profile = CodexAcceptanceProfile()
    preflight = profile.preflight(_capture_text)
    launcher = PYTHON.parent / "Scripts" / "metacraft.exe"
    if preflight.missing_flags or not launcher.is_file():
        raise RuntimeError("codex_campaign_preflight_failed")

    EVIDENCE_ROOT.mkdir(parents=True)
    for name in (
        "answers",
        "audits",
        "capsules",
        "fresh-inspections",
        "outcomes",
        "post-hoc",
        "receipts",
        "stderr",
        "transcripts",
    ):
        (EVIDENCE_ROOT / name).mkdir()
    _write_json(
        EVIDENCE_ROOT / "preflight.json",
        {
            "schema": "metacraft.acceptance.ticket03_codex_preflight",
            "profile": "codex",
            "version": preflight.version,
            "missing_flags": list(preflight.missing_flags),
            "launcher_exists": launcher.is_file(),
            "planned_session_count": 4,
            "retry_count": 0,
        },
    )

    blind_records: list[dict[str, object]] = []
    for slot, case_name in enumerate(CASE_NAMES, start=1):
        slot_name = f"slot-{slot:02d}"
        receipt = RECEIPTS[case_name]
        prepared = profile.prepare(
            CapsuleRequest(
                root=EVIDENCE_ROOT / "capsules" / slot_name,
                case_name=case_name,
                repository=ROOT,
                python_executable=PYTHON,
                inherited_environment=os.environ,
                opening_prompt=PROMPT,
                material_receipt=receipt,
            )
        )
        (prepared.capsule.root / "source-dossier.md").write_text(
            DOSSIER,
            encoding="utf-8",
            newline="\n",
        )
        receipt_root = EVIDENCE_ROOT / "receipts" / slot_name
        receipt_root.mkdir()
        for source in sorted(prepared.capsule.root.glob("reviewed-material-*.json")):
            shutil.copyfile(source, receipt_root / source.name)

        completed = _execute_once(prepared.invocation)
        transcript = bytes(completed.stdout)
        stderr = bytes(completed.stderr)
        redacted = redact_transcript(
            transcript,
            capsule=prepared.capsule.root,
            repository=ROOT,
        )
        redacted_stderr = redact_transcript(
            stderr,
            capsule=prepared.capsule.root,
            repository=ROOT,
        )
        observation = profile.observe(redacted)
        audit = audit_observation(observation, capsule=prepared.capsule.root)
        (EVIDENCE_ROOT / "transcripts" / f"{slot_name}.jsonl").write_bytes(redacted)
        (EVIDENCE_ROOT / "stderr" / f"{slot_name}.txt").write_bytes(redacted_stderr)
        _write_json(EVIDENCE_ROOT / "audits" / f"{slot_name}.json", audit)

        inspection: dict[str, object] | None = None
        inspection_error: str | None = None
        if completed.returncode == 0 and not completed.timed_out:
            fresh = _inspect_fresh(prepared.capsule)
            (EVIDENCE_ROOT / "fresh-inspections" / f"{slot_name}.json").write_bytes(
                fresh.stdout
            )
            if fresh.returncode == 0:
                inspection = json.loads(fresh.stdout)
            else:
                inspection_error = fresh.stderr.decode(errors="replace")
        accepted_answers: list[dict[str, str]] = []
        for answer_name in ("period-answer.json", "height-answer.json"):
            source = prepared.capsule.root / answer_name
            if source.is_file():
                destination = EVIDENCE_ROOT / "answers" / f"{slot_name}-{answer_name}"
                shutil.copyfile(source, destination)
                accepted_answers.append(
                    {"name": destination.name, "sha256": _digest(destination.read_bytes())}
                )
        outcome = {
            "schema": "metacraft.acceptance.ticket03_slot_outcome",
            "slot": slot_name,
            "profile": "codex",
            "process_exit_code": completed.returncode,
            "timed_out": completed.timed_out,
            "audit": audit,
            "inspection": inspection,
            "inspection_error": inspection_error,
            "answers": accepted_answers,
            "explanation": observation.explanation,
            "acceptance": _acceptance(inspection, completed.returncode, audit),
        }
        _write_json(EVIDENCE_ROOT / "outcomes" / f"{slot_name}.json", outcome)
        blind_records.append(
            {
                "slot": slot_name,
                "brief_sha256": _digest(prepared.capsule.brief_path.read_bytes()),
                "receipt_export_sha256": _tree_digest(receipt_root),
                "transcript_sha256": _digest(redacted),
                "stderr_sha256": _digest(redacted_stderr),
                "audit_sha256": _digest(
                    (EVIDENCE_ROOT / "audits" / f"{slot_name}.json").read_bytes()
                ),
                "outcome_sha256": _digest(
                    (EVIDENCE_ROOT / "outcomes" / f"{slot_name}.json").read_bytes()
                ),
                "started_session_count": 1,
                "retry_count": 0,
                "terminal_state": (
                    "timed_out"
                    if completed.timed_out
                    else "completed" if completed.returncode == 0 else "failed"
                ),
            }
        )

    _write_json(
        EVIDENCE_ROOT / "blind-manifest.json",
        {
            "schema": "metacraft.acceptance.ticket03_blind_campaign",
            "profile": "codex",
            "opening_prompt_sha256": _digest(PROMPT.encode()),
            "source_dossier_sha256": _digest(DOSSIER.encode()),
            "planned_session_count": 4,
            "started_session_count": 4,
            "retry_count": 0,
            "slots": blind_records,
        },
    )
    _write_post_hoc()
    files = sorted(
        path.relative_to(EVIDENCE_ROOT).as_posix()
        for path in EVIDENCE_ROOT.rglob("*")
        if path.is_file() and path.name != "sealed-manifest.json"
    )
    _write_json(
        EVIDENCE_ROOT / "sealed-manifest.json",
        {
            "schema": "metacraft.acceptance.ticket03_sealed_campaign",
            "files": [
                {"path": name, "sha256": _digest((EVIDENCE_ROOT / name).read_bytes())}
                for name in files
            ],
        },
    )
    return 0


def _execute_once(invocation) -> HarnessCapture:
    try:
        completed = subprocess.run(
            invocation.argv,
            cwd=invocation.cwd,
            env=invocation.environment,
            input=None if invocation.stdin is None else invocation.stdin.encode(),
            capture_output=True,
            check=False,
            timeout=900,
        )
        return HarnessCapture(
            completed.returncode,
            completed.stdout,
            completed.stderr,
            False,
        )
    except subprocess.TimeoutExpired as error:
        return HarnessCapture(
            124,
            error.stdout or b"",
            error.stderr or b"",
            True,
        )


def _inspect_fresh(capsule: PreparedCapsule) -> subprocess.CompletedProcess[bytes]:
    script = (
        "import json,sys; from pathlib import Path; "
        "from tests.harness_acceptance import PreparedCapsule,inspect_capsule; "
        "p=Path(sys.argv[1]); c=PreparedCapsule(p,'blind-slot',"
        "p/'prepared-application-root',p/'blind-brief.json',"
        "p/'reviewed-materials.toml',p/'opening-prompt.txt'); "
        "print(json.dumps(inspect_capsule(c),sort_keys=True))"
    )
    return subprocess.run(
        [str(PYTHON), "-c", script, str(capsule.root)],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )


def _acceptance(
    inspection: dict[str, object] | None,
    returncode: int,
    audit: dict[str, object],
) -> dict[str, object]:
    forbidden = {
        "periodic_transmission",
        "periodic_polarization",
        "cell_library",
        "aperture",
        "field",
        "focal_region",
        "focus",
        "result",
    }
    evidence = set(inspection.get("evidence_claims", ())) if inspection else set()
    checks = {
        "process_completed": returncode == 0,
        "audit_confined": audit.get("is_confined") is True,
        "waiting_studies": bool(inspection and inspection.get("outcome") == "WaitingStudies"),
        "no_current_question": bool(inspection and inspection.get("current_question") is None),
        "material_visible": bool(inspection and inspection.get("material")),
        "period_and_height_visible": bool(
            inspection and inspection.get("selected")
            and set(inspection["selected"]) == {"period_nm", "height_nm"}
        ),
        "two_advice_records": bool(
            inspection
            and [item.get("kind") for item in inspection.get("advice", ())]
            == ["period", "height"]
        ),
        "two_canonical_answers": bool(
            inspection
            and len(inspection.get("answers", ())) == 2
            and all(item.get("is_canonical") for item in inspection["answers"])
        ),
        "no_downstream_evidence": not bool(evidence & forbidden),
    }
    return {"checks": checks, "passed": all(checks.values())}


def _write_post_hoc() -> None:
    from examples import select_metalens_benchmark_case
    from examples.metalens_benchmark.contract import ReferenceFactName

    lines = [
        "# Ticket 03 post-hoc comparison",
        "",
        "Published facts were opened only after blind-manifest.json was written.",
        "Paper proximity is diagnostic, not an acceptance threshold.",
        "",
        "| Slot | Revealed case | Selected period | Published period | Selected height | Published height | Blind acceptance |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for slot, case_name in enumerate(CASE_NAMES, start=1):
        slot_name = f"slot-{slot:02d}"
        outcome = json.loads(
            (EVIDENCE_ROOT / "outcomes" / f"{slot_name}.json").read_bytes()
        )
        inspection = outcome.get("inspection") or {}
        selected = inspection.get("selected") or {}
        case = select_metalens_benchmark_case(case_name)
        period = case.reference.fact(ReferenceFactName.CELL_PERIOD).value
        height = case.reference.fact(ReferenceFactName.ATOM_HEIGHT).value
        lines.append(
            f"| {slot_name} | {case_name} | {selected.get('period_nm')} nm | "
            f"{getattr(period, 'value', None)} {getattr(period, 'unit', '')} | "
            f"{selected.get('height_nm')} nm | {getattr(height, 'value', None)} "
            f"{getattr(height, 'unit', '')} | {outcome['acceptance']['passed']} |"
        )
    lines.extend(
        (
            "",
            "Differences remain the blind Adviser's traceable choices; no answer was rewritten to match a publication.",
        )
    )
    (EVIDENCE_ROOT / "post-hoc" / "comparison.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _capture_text(command: tuple[str, ...]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError("codex_preflight_command_failed")
    return (completed.stdout or completed.stderr).strip()


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
