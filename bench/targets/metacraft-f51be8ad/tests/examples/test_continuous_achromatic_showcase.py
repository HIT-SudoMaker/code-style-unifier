from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path

import pytest

from examples.continuous_achromatic_showcase import (
    continuous_achromatic_showcase,
    run_continuous_achromatic_showcase,
)
from metacraft.authority import Document, Reference
from metacraft.authority.reference import reference_for
from metacraft.science import CompletedResults, WaitingStudies
from metacraft.science.metalens import AchromaticResult
from metacraft.science.metalens.achromatic import (
    AchromaticFocusEntry,
    SpectralFieldEntry,
    SpectralFieldFamily,
    form_achromatic_focus,
    form_band_verification_evidence,
    form_post_freeze_jones_library,
)
from metacraft.science.metalens.aperture import resolve_lattice
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.design import resolve_metalens_design
from metacraft.science.metalens.result import conclude, restore_conclusion
from metacraft.science.result import (
    BoundDocument,
    Result,
    ResultClosure,
    brief_document,
    design_document,
    study_document,
)
from metacraft.science.study import (
    Binding,
    Capability,
    Evidence,
    Study,
    Task,
)
from tests.brief_fixtures import continuous_achromatic_publication_brief
from tests.achromatic_fixtures import (
    achromatic_target as _target,
    assigned_aperture as _assigned_aperture,
    blind_observations as _blind_observations,
    complete_focus as _complete_focus,
    qualification_profile as _profile,
    qualify_candidate_library as _qualification,
    spectral_binding as _binding,
    spectral_specification as _specification,
)


def test_run_preserves_public_conduct_stop_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = continuous_achromatic_publication_brief()
    stopped = WaitingStudies((compile_metalens(brief),))
    monkeypatch.setattr(
        "examples.continuous_achromatic_showcase.conduct",
        lambda *_args, **_kwargs: stopped,
    )

    observed = run_continuous_achromatic_showcase(
        brief,
        application_root=tmp_path / "continuous-showcase",
    )

    assert observed is stopped


def test_projector_exposes_fixed_layout_spectral_roles_and_exact_refs() -> None:
    completed, fetch = _admitted_achromatic_result()

    showcase = continuous_achromatic_showcase(completed, fetch=fetch)

    assert isinstance(showcase, Document)
    assert showcase.schema_identifier == (
        "metacraft.examples.continuous_achromatic_showcase"
    )
    values = showcase.values
    assert values["showcase"] == "continuous achromatic compensation"
    assert values["execution_origin"] == "synthetic"
    assert values["physical_semantics"] == {
        "pb_orientation_group_delay": "none",
        "realized_phase_composition": (
            "geometry-controlled phase + PB phase modulo 2 pi"
        ),
        "response_coupling": (
            "geometry-controlled and PB responses belong to the same "
            "anisotropic structure"
        ),
    }

    result = completed.results[0]
    conclusion = restore_conclusion(result.document, fetch=fetch)
    assert isinstance(conclusion, AchromaticResult)
    aperture_values = conclusion.aperture.document().values
    assert values["fixed_aperture"] == {
        "coordinates_nm": aperture_values["coordinates_nm"],
        "geometries": aperture_values["geometries"],
        "geometry_indices": aperture_values["geometry_indices"],
        "height_nm": aperture_values["height_nm"],
        "occupied": aperture_values["occupied"],
        "orientations_rad": aperture_values["orientations_rad"],
        "period_nm": aperture_values["period_nm"],
        "site_count": conclusion.aperture.site_count,
    }
    assert values["phase_maps"] == {
        "geometry_controlled_phase_rad": aperture_values[
            "propagation_reference_phase_rad"
        ],
        "pb_phase_rad": aperture_values["geometric_phase_rad"],
        "realized_composition_phase_rad": aperture_values[
            "realized_reference_phase_rad"
        ],
        "target_phase_rad": aperture_values["target_reference_phase_rad"],
    }

    focus_by_role = values["spectral_focus_by_role"]
    assert set(focus_by_role) == {
        "blind_verification",
        "design",
        "interleaved_validation",
    }
    assert focus_by_role["design"]["wavelengths_nm"] == list(
        conclusion.focus.design_wavelengths_nm
    )
    assert focus_by_role["interleaved_validation"]["wavelengths_nm"] == list(
        conclusion.focus.holdout_wavelengths_nm
    )
    assert focus_by_role["blind_verification"]["wavelengths_nm"] == list(
        conclusion.focus.blind_verification_wavelengths_nm
    )
    assert all(
        {entry["strategy"] for entry in role["field_and_focus"]}
        == {"continuous compensation", "pb-only baseline"}
        and all(
            set(entry) == {
                "field_reference",
                "focal_region_reference",
                "focus",
                "focus_reference",
                "strategy",
                "wavelength_nm",
            }
            for entry in role["field_and_focus"]
        )
        for role in focus_by_role.values()
    )
    assert values["band_verification"] == (
        conclusion.band_verification.document().values
    )
    assert values["band_verification"]["status"] == "pass"
    assert values["references"] == {
        "achromatic_aperture": conclusion.aperture_reference.as_mapping(),
        "achromatic_focus": conclusion.focus_reference.as_mapping(),
        "band_verification": (
            conclusion.band_verification_reference.as_mapping()
        ),
        "qualified_spectral_library": (
            conclusion.qualification_reference.as_mapping()
        ),
        "result": result.reference.as_mapping(),
        "spectral_field_family": (
            conclusion.spectral_field_family_reference.as_mapping()
        ),
    }
    assert "application_root" not in json.dumps(values, sort_keys=True)


def _admitted_achromatic_result() -> tuple[
    CompletedResults,
    Callable[[Reference], bytes],
]:
    brief = continuous_achromatic_publication_brief()
    initial = compile_metalens(brief)
    aperture, plan, library = _assigned_aperture()
    target = _target()
    profile = _profile()
    specification = _specification()
    material_binding = _binding(specification.full_band_wavelengths_nm)
    qualification = _qualification(target, plan, library)
    lattice = resolve_lattice(
        resolve_metalens_design(brief),
        spacing_nm=plan.period_nm,
        spacing_source_reference=reference_for(plan.document().to_bytes()),
    )
    assert lattice is not None
    post_freeze = form_post_freeze_jones_library(
        plan,
        aperture,
        library,
        _blind_observations(),
        profile=profile,
        qualification_reference=aperture.qualification_reference,
        solver_binding_reference=library.solver_binding_reference,
    )
    post_freeze_reference = reference_for(post_freeze.document().to_bytes())
    field_entries = tuple(
        SpectralFieldEntry(
            strategy=strategy,
            wavelength_nm=wavelength_nm,
            field_reference=reference_for(
                f"field:{strategy}:{wavelength_nm}".encode()
            ),
            focal_region_reference=reference_for(
                f"region:{strategy}:{wavelength_nm}".encode()
            ),
        )
        for strategy in ("continuous compensation", "pb-only baseline")
        for wavelength_nm in plan.full_band_wavelengths_nm
    )
    family = SpectralFieldFamily(
        aperture_reference=reference_for(aperture.document().to_bytes()),
        qualification_reference=aperture.qualification_reference,
        library_reference=aperture.library_reference,
        propagation_binding_reference=reference_for(b"propagation"),
        post_freeze_library_reference=post_freeze_reference,
        design_wavelengths_nm=plan.design_wavelengths_nm,
        holdout_wavelengths_nm=plan.holdout_wavelengths_nm,
        blind_verification_wavelengths_nm=(
            plan.blind_verification_wavelengths_nm
        ),
        entries=field_entries,
    )
    family_reference = reference_for(family.document().to_bytes())
    focus = form_achromatic_focus(
        family,
        tuple(
            AchromaticFocusEntry(
                strategy=entry.strategy,
                wavelength_nm=entry.wavelength_nm,
                focus_reference=reference_for(
                    f"focus:{entry.strategy}:{entry.wavelength_nm}".encode()
                ),
                focus=_complete_focus(
                    focal_shift_m=(
                        1e-7
                        if entry.strategy == "continuous compensation"
                        else 8e-7
                    ),
                    leakage_fraction=0.01,
                ),
            )
            for entry in field_entries
        ),
        family_reference=family_reference,
        evaluation_binding_reference=reference_for(b"focus evaluation"),
    )
    focus_reference = reference_for(focus.document().to_bytes())
    verification = form_band_verification_evidence(
        plan,
        aperture,
        library,
        post_freeze,
        family,
        focus,
        profile=profile,
        qualification_reference=aperture.qualification_reference,
        family_reference=family_reference,
        focus_reference=focus_reference,
    )

    bodies: dict[Reference, bytes] = {}

    def record(document: Document) -> Reference:
        body = document.to_bytes()
        reference = reference_for(body)
        bodies[reference] = body
        return reference

    exact_documents = {
        "achromatic_target": target.document(),
        "response_qualification_profile": profile.document(),
        "spectral_study_specification": specification.document(),
        "spectral_material_binding": material_binding.document(),
        "spectral_cell_study_plan": plan.document(),
        "physical_lattice": lattice.document(),
        "spectral_jones_library": library.document(),
        "qualified_spectral_library": qualification.document(),
        "achromatic_aperture": aperture.document(),
        "post_freeze_jones_library": post_freeze.document(),
        "spectral_field_family": family.document(),
        "achromatic_focus": focus.document(),
        "focus": verification.document(),
    }
    claim_references = {
        claim: record(document) for claim, document in exact_documents.items()
    }
    screen_body = b"spectral cell screen"
    claim_references["spectral_cell_screen"] = reference_for(screen_body)
    bodies[claim_references["spectral_cell_screen"]] = screen_body

    binding_bodies = {
        "fabrication_constraint": b"fabrication constraint",
        "periodic_polarization_response": b"spectral periodic solver",
        "spectral_optical_material": b"spectral material solver",
        "deterministic_selection": b"deterministic selection",
        "angular_spectrum_propagation": b"propagation",
        "focus_evaluation": b"focus evaluation",
    }
    capabilities = tuple(Capability(name) for name in binding_bodies)
    bindings = tuple(
        Binding(name, reference_for(body), f"fixture:{name}")
        for name, body in binding_bodies.items()
    )
    for binding, body in zip(bindings, binding_bodies.values(), strict=True):
        bodies[binding.reference] = body
    bindings_by_capability = {
        binding.capability: binding for binding in bindings
    }
    choices = {choice.claim: choice for choice in initial.route.choices}
    facts: list[Evidence] = []
    facts_by_claim: dict[str, Evidence] = {}
    design_identity = initial.ready_tasks[0].design_identity
    for claim in initial.proof.claims:
        binding = (
            None
            if claim.capability is None
            else bindings_by_capability[claim.capability]
        )
        task = Task(
            proof_identity=initial.proof.identity,
            claim=claim.name,
            method=choices[claim.name].method,
            schema=claim.schema,
            brief_identity=initial.brief_identity,
            design_identity=design_identity,
            prerequisite_evidence=tuple(
                facts_by_claim[name].reference for name in claim.requires
            ),
            consultations=(),
            binding_reference=None if binding is None else binding.reference,
            capacity_scope=None if binding is None else binding.capacity_scope,
        )
        fact = Evidence(
            task_identity=task.identity,
            claim=claim.name,
            schema=claim.schema,
            reference=claim_references[claim.name],
            binding_reference=None if binding is None else binding.reference,
        )
        facts.append(fact)
        facts_by_claim[claim.name] = fact
    ready = Study(
        brief=initial.brief,
        brief_identity=initial.brief_identity,
        advice=(),
        design=initial.design,
        route=initial.route,
        proof=initial.proof,
        evidence=tuple(facts),
        capabilities=capabilities,
        bindings=bindings,
        ready_tasks=(),
        findings=(),
    )

    brief_value = brief_document(ready.brief)
    brief_reference = record(brief_value)
    design_value = design_document(ready, brief_reference)
    design_reference = record(design_value)
    study_value = study_document(ready, brief_reference, design_reference)
    study_reference = record(study_value)
    closure = ResultClosure.bind(
        ready,
        brief=BoundDocument(brief_reference, brief_value),
        design=BoundDocument(design_reference, design_value),
        study=BoundDocument(study_reference, study_value),
    )
    conclusion = conclude(ready, closure, fetch=bodies.__getitem__)
    result_document = conclusion.document()
    result_reference = record(result_document)
    sources = tuple(dict.fromkeys(conclusion.references()))
    completed = CompletedResults(
        (Result(result_reference, result_document, sources, closure),)
    )
    return completed, bodies.__getitem__
