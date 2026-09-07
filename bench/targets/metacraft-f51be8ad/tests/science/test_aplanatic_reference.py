from __future__ import annotations

import base64
import gzip
import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from metacraft.authority import Document, Reference, reference_for
from metacraft.authority.protocol import AdmittedDecision, AuthorityView, Revision
from metacraft.authority.session import AuthoritySession
from metacraft.field.debye_qualification import (
    aplanatic_reference_binding,
    qualify_aplanatic_reference,
    qualify_czt_debye,
    qualify_fft_debye,
)
from metacraft.field.fast_debye import CZTDebyeRealization, FFTDebyeRealization
from metacraft.field.sample import Field
from metacraft.science.metalens import _aplanatic_reference
from metacraft.science.metalens.brief import ControlStrategy, MonochromaticSpectrum
from metacraft.science.metalens.checkpoint import StudyFrontier
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.focus import FocalRegion
from tests.brief_fixtures import propagation_brief
from tests.metalens_field_fixtures import (
    cartesian_focal_region,
    metalens_design,
)


def test_aplanatic_reference_formation_uses_the_joint_field_interface() -> None:
    region = cartesian_focal_region(
        found_focus_m=10e-6,
        focus_plane_position_m=13e-6,
    )
    fft = qualify_fft_debye(FFTDebyeRealization(device="cpu", pupil_samples=65))
    czt = qualify_czt_debye(CZTDebyeRealization(device="cpu", pupil_samples=65))
    fft_reference = reference_for(fft.document().to_bytes())
    czt_reference = reference_for(czt.document().to_bytes())
    joint = qualify_aplanatic_reference(
        fft,
        czt,
        fft_qualification_reference=fft_reference,
        czt_qualification_reference=czt_reference,
    )
    joint_reference = reference_for(joint.document().to_bytes())
    binding = aplanatic_reference_binding(
        joint,
        joint_qualification_reference=joint_reference,
    )
    binding_reference = reference_for(binding.to_bytes())
    documents = {
        binding_reference: binding.to_bytes(),
        fft_reference: fft.document().to_bytes(),
        czt_reference: czt.document().to_bytes(),
        joint_reference: joint.document().to_bytes(),
    }
    target_reference = reference_for(b"ticket04 target phase")
    admitted: list[Field] = []

    class EvidenceBoundary:
        def fetch(self, reference: Reference) -> bytes:
            return documents[reference]

        def restore_focal_region(self, _study: object) -> FocalRegion:
            return region

        def fact(self, _study: object, claim: str) -> object:
            assert claim == "target_phase"
            return SimpleNamespace(reference=target_reference)

        def admit_field(self, _task: object, field: Field) -> Reference:
            admitted.append(field)
            return reference_for(b"ticket04 aplanatic reference")

        def with_fact(
            self,
            study: object,
            _task: object,
            _reference: Reference,
        ) -> object:
            return study

    design = replace(
        metalens_design(ControlStrategy.PROPAGATION_PHASE),
        operating_spectrum=MonochromaticSpectrum(wavelength_nm=532),
        numerical_aperture=Decimal("0.8"),
        focal_length_um=Decimal("9"),
    )
    study = SimpleNamespace(design=design)

    returned = _aplanatic_reference.admit_aplanatic_reference(
        EvidenceBoundary(),  # type: ignore[arg-type]
        study,  # type: ignore[arg-type]
        SimpleNamespace(binding_reference=binding_reference),  # type: ignore[arg-type]
    )

    assert returned is study
    assert len(admitted) == 1
    reference = admitted[0]
    assert reference.surface.position_m == region.focus_plane_position_m
    assert {
        component.name: hashlib.sha256(component.values.tobytes(order="C")).hexdigest()
        for component in reference.electric_components
    } == {
        "x": "a0fb4b9b0a94cd4ef288907a9da28b0d4179bd91eb577450ab743c37a6f36abd",
        "y": "be39b413456d2b227d0eff57ee86f4ccf7e814267b115d2e92e9223c323ba491",
        "z": "b143948d5bd710843b3166dafc22603ccac007d78f705d40bce5822d1d9f9274",
    }


def test_retired_aplanatic_binding_fails_without_rewriting_root(
    tmp_path: Path,
) -> None:
    witness = json.loads(
        Path("tests/fixtures/aplanatic_reference/fixed-point-c46e663.json").read_text(
            encoding="utf-8"
        )
    )
    retained_binding = Document(
        witness["binding_document"]["schema_identifier"],
        witness["binding_document"]["values"],
    )
    binding_bytes = retained_binding.to_bytes()
    assert hashlib.sha256(binding_bytes).hexdigest() == (
        witness["binding_document_sha256"]
    )
    binding_reference = reference_for(binding_bytes)
    retained = tmp_path / "authority" / "objects" / "retired-binding.json"
    retained.parent.mkdir(parents=True)
    retained.write_bytes(binding_bytes)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    class HistoricalEvidence:
        def fetch(self, reference: Reference) -> bytes:
            assert reference == binding_reference
            return retained.read_bytes()

        def restore_focal_region(self, _study: object) -> FocalRegion:
            raise AssertionError("stale binding reached numerical formation")

    with pytest.raises(
        RuntimeError,
        match="aplanatic_reference_binding_mismatch",
    ):
        _aplanatic_reference.admit_aplanatic_reference(
            HistoricalEvidence(),  # type: ignore[arg-type]
            SimpleNamespace(),  # type: ignore[arg-type]
            SimpleNamespace(
                binding_reference=binding_reference,
            ),  # type: ignore[arg-type]
        )

    assert {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    } == before


def test_retired_persisted_study_fails_closed_without_rewriting_root(
    tmp_path: Path,
) -> None:
    historical_body = gzip.decompress(
        base64.b64decode(
            Path(
                "tests/fixtures/aplanatic_reference/" "pre-cutover-high-na-study.b64"
            ).read_bytes()
        )
    )
    historical_document = Document.from_bytes(historical_body)
    assert len(historical_body) == 27_821
    assert hashlib.sha256(historical_body).hexdigest() == (
        "f2ec1b6121144ad44bb961e800d3ccaf4a0f84ece947c6a3a9df713cfbface4e"
    )
    historical_values = historical_document.values
    retired_claim = next(
        obligation
        for obligation in historical_values["proof"]["obligations"].values()
        if obligation["name"] == "ideal_field"
    )
    assert retired_claim["capability"] == "ideal_field_formation"
    retired_task = next(
        choice
        for choice in historical_values["route"]["choices"].values()
        if choice["claim"] == "ideal_field"
    )
    assert retired_task["method"] == "form_ideal_field"
    retired_evidence = next(
        evidence
        for evidence in historical_values["evidence"].values()
        if evidence["obligation"] == "ideal_field"
    )
    assert retired_evidence["obligation"] == "ideal_field"
    historical_result_references = {
        Reference.from_mapping(retired_evidence["reference"]),
        Reference.from_mapping(retired_evidence["binding_reference"]),
    }
    historical_sizes = {
        reference.size_bytes for reference in historical_result_references
    }
    assert historical_sizes == {83, 87}
    application_root = tmp_path / "historical-application-root"
    application_root.mkdir()
    (application_root / "runs").mkdir()
    retained = application_root / "historical-study.json"
    retained.write_bytes(historical_body)
    replay_objects = application_root / "historical-replay-objects.b64"
    replay_objects.write_bytes(
        Path(
            "tests/fixtures/aplanatic_reference/"
            "pre-cutover-high-na-replay-objects.b64"
        ).read_bytes()
    )
    historical_objects = {
        canonical_text: base64.b64decode(body)
        for canonical_text, body in json.loads(
            gzip.decompress(base64.b64decode(replay_objects.read_bytes()))
        ).items()
    }

    class HistoricalAuthority:
        def view(self) -> AuthorityView:
            references = tuple(
                Reference.from_mapping(json.loads(canonical_text))
                for canonical_text in historical_objects
            )
            decisions = tuple(
                AdmittedDecision(
                    body_reference=reference,
                    proposal_reference=reference_for(
                        reference.canonical_text().encode(),
                        media_type=(
                            "application/vnd.metacraft.authority.proposal+json"
                        ),
                    ),
                    relation="record",
                )
                for reference in references
            )
            return AuthorityView(
                Revision("root"),
                (),
                decisions,
                (),
                "metacraft.authority.view",
            )

        def fetch(self, reference: Reference) -> bytes:
            return historical_objects[reference.canonical_text()]

    before = {
        path.relative_to(application_root): path.read_bytes()
        for path in application_root.rglob("*")
        if path.is_file()
    }
    brief = replace(
        propagation_brief(),
        numerical_aperture=Decimal("0.8"),
        focal_length_um=Decimal("0.25"),
    )
    current = compile_metalens(brief)
    with pytest.raises(ValueError, match="study_frontier_invalid"):
        StudyFrontier.from_document(
            Document(
                StudyFrontier.start(current).document().schema_identifier,
                {
                    "brief_identity": current.brief_identity,
                    "studies": {
                        "study_001": historical_document.as_mapping(),
                    },
                },
            ),
            brief=brief,
            session=AuthoritySession(HistoricalAuthority()),  # type: ignore[arg-type]
        )

    assert {
        path.relative_to(application_root): path.read_bytes()
        for path in application_root.rglob("*")
        if path.is_file()
    } == before
