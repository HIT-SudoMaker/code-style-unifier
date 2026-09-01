from __future__ import annotations

from metacraft.authority.reference import reference_for
from metacraft.science.metalens.run_projection import (
    RunManifest,
    project_run_manifest,
)
from metacraft.science.result import brief_document
from metacraft.science.metalens.compiler import compile_metalens
from tests.brief_fixtures import propagation_brief


def test_run_manifest_is_a_rebuildable_projection_with_references() -> None:
    study = compile_metalens(propagation_brief())
    brief_reference = reference_for(brief_document(study.brief).to_bytes())
    study_reference = reference_for(study.document().to_bytes())
    manifest = project_run_manifest(
        study,
        authority_revision=7,
        references={"brief": brief_reference, "study": study_reference},
        warnings=("order regime remains a proof obligation",),
        next_action="await_cell_study_answer",
    )

    assert manifest.identity.startswith("sha256:")
    assert tuple(step.name for step in manifest.steps) == ("brief", "study")
    restored = RunManifest.from_document(manifest.document())
    assert restored == manifest
    assert {
        reference
        for step in manifest.steps
        for reference in step.references
    } == {brief_reference, study_reference}
    assert not any(
        hasattr(manifest, operation)
        for operation in ("advance", "resume", "restore_study")
    )
