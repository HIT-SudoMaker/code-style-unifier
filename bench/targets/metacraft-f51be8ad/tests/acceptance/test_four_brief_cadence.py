from __future__ import annotations

from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from metacraft.authority import Authority, Document
from metacraft.science.conduct import ConsultationRequired, WaitingStudies, conduct
from metacraft.science.consultation import (
    ConsultationAnswer,
    GroundKind,
    Recommendation,
)
from metacraft.science.metalens.aperture import Lattice
from metacraft.science.metalens.brief import MetalensBrief
from metacraft.science.metalens.height import HeightChoice, HeightDomain
from metacraft.science.metalens.period import PeriodChoice, PeriodDomain
from tests.harness_acceptance import (
    CASE_NAMES,
    OPENING_PROMPT,
    CapsuleRequest,
    CodexAcceptanceProfile,
    PreparedCapsule,
    inspect_capsule,
)


ROOT = Path(__file__).parents[2]
_PRE_STUDY_CLAIMS = {
    "height_choice",
    "height_domain",
    "material_binding",
    "period_choice",
    "period_domain",
    "phase_envelope",
    "physical_lattice",
    "polarization_convention",
    "target_phase",
}


@pytest.mark.parametrize("case_name", CASE_NAMES)
def test_each_blind_brief_closes_its_deterministic_cadence_without_studies(
    case_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tests.harness_acceptance.shutil.which",
        lambda name: f"C:/reviewed/{name}.exe",
    )
    prepared = CodexAcceptanceProfile().prepare(
        CapsuleRequest(
            root=tmp_path / case_name,
            case_name=case_name,
            repository=ROOT,
            python_executable=Path(sys.executable),
            inherited_environment=os.environ,
            opening_prompt=OPENING_PROMPT,
        )
    )
    capsule = prepared.capsule
    brief = MetalensBrief.decode_canonical_bytes(capsule.brief_path.read_bytes())

    period_required = conduct(brief, application_root=capsule.application_root)
    assert isinstance(period_required, ConsultationRequired)
    assert period_required.request.question_kind.value == "period"
    period_answer = _answer_from_emitted_request(period_required)
    (capsule.root / "period-answer.json").write_bytes(
        period_answer.document().to_bytes()
    )

    height_required = conduct(
        brief,
        application_root=capsule.application_root,
        consultation_answer=period_answer,
    )
    assert isinstance(height_required, ConsultationRequired)
    assert height_required.request.question_kind.value == "height"
    height_answer = _answer_from_emitted_request(height_required)
    (capsule.root / "height-answer.json").write_bytes(
        height_answer.document().to_bytes()
    )

    waiting = conduct(
        brief,
        application_root=capsule.application_root,
        consultation_answer=height_answer,
    )
    assert isinstance(waiting, WaitingStudies)
    assert all(
        {evidence.claim for evidence in study.evidence} <= _PRE_STUDY_CLAIMS
        for study in waiting.studies
    )

    authority = Authority(capsule.application_root / "authority")
    assert authority.check().is_workspace_valid
    _assert_choices_belong_to_their_admitted_domains(waiting, authority)
    revision = authority.view().revision
    inspected = inspect_capsule(capsule)
    assert inspected["outcome"] == "WaitingStudies"
    assert inspected["current_question"] is None
    assert inspected["current_request_identity"] is None
    assert inspected["selected"] == {
        "height_nm": int(height_required.request.candidates[-1].quantity),
        "period_nm": int(period_required.request.candidates[-1].quantity),
    }
    assert {answer["request_identity"] for answer in inspected["answers"]} == {
        advice["request_identity"] for advice in inspected["advice"]
    }
    assert all(answer["is_canonical"] for answer in inspected["answers"])
    _assert_material_fixture_is_exact_and_honest(inspected)

    fresh = _inspect_in_fresh_process(capsule)
    assert fresh == inspected
    assert Authority(capsule.application_root / "authority").view().revision == revision


def _answer_from_emitted_request(required: ConsultationRequired) -> ConsultationAnswer:
    request = required.request
    candidate = request.candidates[-1]
    assert candidate.quantity > Decimal(0)
    decisive = tuple(
        ground.identity
        for ground in request.grounds
        if ground.kind in {GroundKind.FACT, GroundKind.CONSTRAINT}
    )
    return ConsultationAnswer(
        request_identity=request.identity,
        conclusion=Recommendation(
            candidate_identity=candidate.identity,
            reason=(
                "A deterministic interface fixture selects the greatest emitted "
                "candidate; this is not a scientific recommendation."
            ),
            decisive_ground_identities=decisive,
            external_claim_identities=(),
        ),
        external_claims=(),
    )


def _assert_material_fixture_is_exact_and_honest(
    inspected: dict[str, object],
) -> None:
    material = inspected["material"]
    assert isinstance(material, dict)
    assert material["wavelength_nm"] > 0
    assert material["source_identities"] == ["solver native"]
    for role in ("atom", "substrate"):
        bound = material[role]
        assert isinstance(bound, dict)
        assert bound["family"]
        assert bound["native_name"]
        assert Decimal(str(bound["refractive_index"])) > 1
        assert Decimal(str(bound["extinction_coefficient"])) == 0
    sample = material["sample"]
    solver_binding = material["solver_binding"]
    assert isinstance(sample, dict) and isinstance(solver_binding, dict)
    assert sample["values"]["purpose"] == (
        "interface acceptance; not physical truth"
    )
    assert solver_binding["values"]["purpose"] == (
        "interface acceptance; not physical truth"
    )
    for name in (
        "binding_reference",
        "sample_reference",
        "solver_binding_reference",
    ):
        reference = material[name]
        assert isinstance(reference, dict)
        assert str(reference["content_hash"]).startswith("sha256:")


def _assert_choices_belong_to_their_admitted_domains(
    waiting: WaitingStudies,
    authority: Authority,
) -> None:
    for study in waiting.studies:
        evidence = {item.claim: item.reference for item in study.evidence}
        period_domain = PeriodDomain.from_document(
            Document.from_bytes(authority.fetch(evidence["period_domain"])),
            evidence_reference=evidence["period_domain"],
        )
        period_choice = PeriodChoice.from_document(
            Document.from_bytes(authority.fetch(evidence["period_choice"]))
        )
        height_domain = HeightDomain.from_document(
            Document.from_bytes(authority.fetch(evidence["height_domain"])),
            evidence_reference=evidence["height_domain"],
        )
        height_choice = HeightChoice.from_document(
            Document.from_bytes(authority.fetch(evidence["height_choice"]))
        )
        lattice = Lattice.from_document(
            Document.from_bytes(authority.fetch(evidence["physical_lattice"]))
        )
        assert period_choice.period_nm % 10 == 0
        assert Decimal(period_choice.period_nm) < period_domain.sampling_ceiling_nm
        assert period_choice.order_regime == height_domain.order_regime
        assert height_choice.height_nm in height_domain.heights_nm
        assert lattice.spacing_nm == period_choice.period_nm
        assert lattice.spacing_source_reference == evidence["period_choice"]
        if period_choice.order_regime == "multi order":
            assert any(
                caution.concern == "higher orders possible"
                for caution in height_domain.cautions
            )


def _inspect_in_fresh_process(capsule: PreparedCapsule) -> dict[str, object]:
    script = """
import json
from pathlib import Path
import sys
from tests.harness_acceptance import PreparedCapsule, inspect_capsule

root = Path(sys.argv[1])
capsule = PreparedCapsule(
    root=root,
    case_name=sys.argv[2],
    application_root=root / "prepared-application-root",
    brief_path=root / "blind-brief.json",
    material_library_path=root / "reviewed-materials.toml",
    prompt_path=root / "opening-prompt.txt",
)
print(json.dumps(inspect_capsule(capsule), separators=(",", ":"), sort_keys=True))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(capsule.root), capsule.case_name],
        cwd=ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    value = json.loads(completed.stdout)
    assert isinstance(value, dict)
    return value
