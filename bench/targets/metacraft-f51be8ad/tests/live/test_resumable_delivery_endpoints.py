from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from metacraft.science.metalens.brief import MetalensBrief
from tests.resumable_journey_fixtures import (
    REPOSITORY_ROOT,
    answer_consultation,
    resumable_role_briefs,
    run_resumable_journey,
)


pytestmark = pytest.mark.lumerical_delivery


@pytest.mark.parametrize(
    ("brief", "root_variable"),
    (
        (resumable_role_briefs()[0], "METACRAFT_LOW_NA_PROPAGATION_DELIVERY_ROOT"),
        (resumable_role_briefs()[3], "METACRAFT_HIGH_NA_PB_DELIVERY_ROOT"),
    ),
    ids=("low-na-propagation", "high-na-pb"),
)
def test_resumable_native_delivery_endpoint(
    brief: MetalensBrief,
    root_variable: str,
    tmp_path: Path,
) -> None:
    application_root = _required_fresh_root(root_variable)
    brief_path = tmp_path / "brief.json"
    brief_path.write_bytes(brief.canonical_bytes())
    material_path = tmp_path / "materials.toml"
    shutil.copyfile(REPOSITORY_ROOT / "materials" / "lumerical.toml", material_path)

    period = _run_native(brief_path, application_root, material_path)
    assert period["outcome"] == "consultation_required"
    period_answer = tmp_path / "period-answer.json"
    period_answer.write_bytes(answer_consultation(period).document().to_bytes())
    waiting = run_resumable_journey(
        brief_path,
        application_root,
        material_path,
        evidence="none",
        answer=period_answer,
    )
    assert waiting["outcome"] == "consultation_required"
    height_answer = tmp_path / "height-answer.json"
    height_answer.write_bytes(answer_consultation(waiting).document().to_bytes())
    waiting = run_resumable_journey(
        brief_path,
        application_root,
        material_path,
        evidence="none",
        answer=height_answer,
    )
    assert waiting["outcome"] == "waiting_studies"

    # Each invocation owns one bounded native-evidence boundary. A complete
    # endpoint is requested repeatedly until its durable frontier terminates.
    completed = waiting
    for _boundary in range(16):
        completed = _run_native(brief_path, application_root, material_path)
        if completed["outcome"] == "completed_results":
            break
        assert completed["outcome"] == "waiting_studies"
    assert completed["outcome"] == "completed_results"
    assert (
        run_resumable_journey(
            brief_path,
            application_root,
            material_path,
            evidence="poison",
        )
        == completed
    )


def _run_native(
    brief: Path,
    application_root: Path,
    materials: Path,
) -> dict[str, object]:
    completed = subprocess.run(
        (
            sys.executable,
            "-m",
            "metacraft.command",
            "conduct",
            "--brief",
            str(brief),
            "--application-root",
            str(application_root),
            "--material-library",
            str(materials),
            "--lumerical-environment",
            str(REPOSITORY_ROOT / ".env.lumerical"),
        ),
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        timeout=900,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    outcome = json.loads(completed.stdout)
    assert isinstance(outcome, dict)
    return outcome


def _required_fresh_root(variable: str) -> Path:
    if os.environ.get("METACRAFT_RUN_LUMERICAL_DELIVERY") != "1":
        pytest.fail("lumerical_delivery_incomplete:not_enabled")
    if not (REPOSITORY_ROOT / ".env.lumerical").is_file():
        pytest.fail("lumerical_delivery_incomplete:environment_absent")
    raw_root = os.environ.get(variable)
    if raw_root is None:
        pytest.fail(f"lumerical_delivery_incomplete:{variable.lower()}_absent")
    application_root = Path(raw_root)
    if not application_root.is_absolute():
        pytest.fail("lumerical_delivery_incomplete:application_root_not_absolute")
    if application_root.exists():
        pytest.fail("lumerical_delivery_incomplete:application_root_not_fresh")
    return application_root
