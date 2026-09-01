from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import hashlib
from pathlib import Path

import pytest

from metacraft.authority import (
    Authority,
    Document,
    Proposal,
    Reference,
    Revision,
)
from metacraft.authority.reference import reference_for
from metacraft.science.consultation import ConsultationGround, GroundKind
from tests.brief_fixtures import (
    geometric_brief,
    long_focus_geometric_brief,
    long_focus_propagation_brief,
    propagation_brief,
)
from metacraft.science.compiler import MissingBriefFacts
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens import (
    ApertureExtent,
    ApertureIntent,
    ControlStrategy,
    require_metalens_design,
)
from metacraft.science.metalens.brief import require_monochromatic_wavelength
from metacraft.science.metalens.height_advice import (
    HeightAdvice,
    HeightRecommendation,
)
from metacraft.science.metalens.propagation_phase import (
    PERIODIC_TRANSMISSION_SCHEMA,
)
from metacraft.science.study import (
    Binding,
    Capability,
    Evidence,
    Finding,
    FindingKind,
)
from tests.domain_fixtures import (
    compile_with_facts,
    evidence_fact_for,
    height_advice as fixture_height_advice,
    height_domain as fixture_height_domain,
    period_advice as fixture_period_advice,
    period_domain as fixture_period_domain,
)


def _reference_hash(name: str) -> str:
    return f"sha256:{hashlib.sha256(name.encode()).hexdigest()}"


def _reference(name: str) -> Reference:
    return Reference(
        content_hash=_reference_hash(name),
        media_type="application/json",
        metadata_content_hash=_reference_hash("metadata-" + name),
        size_bytes=len(name),
    )


def _height_advice(
    brief,
    *,
    domain_reference: Reference,
    envelope_reference: Reference | None = None,
) -> HeightAdvice:
    ground = ConsultationGround(
        kind=GroundKind.CONSTRAINT,
        source_identity=domain_reference.content_hash,
        statement="The admitted height domain permits 500 nm.",
    )
    return HeightAdvice(
        brief_identity=(
            f"sha256:{hashlib.sha256(brief.canonical_bytes()).hexdigest()}"
        ),
        domain_reference=domain_reference,
        envelope_reference=envelope_reference,
        request_identity=_reference_hash("height-request"),
        conclusion=HeightRecommendation(
            height_nm=500,
            reason="fixture height",
            decisive_ground_identities=(ground.identity,),
            external_claim_identities=(),
        ),
        grounds=(ground,),
        external_claims=(),
    )


def test_compiler_keeps_science_design_free_of_solver_policy() -> None:
    """
    Keep the compiler interface scientific and the solver template private.
    """

    study = compile_metalens(propagation_brief())
    design = require_metalens_design(study)

    assert design.sampling_ceiling_nm == Decimal("666.6666666666666666666666667")
    assert design.capabilities == ()
    assert any(claim.capability == "optical_material" for claim in study.proof.claims)
    assert not hasattr(design, "allowed_capabilities")
    assert not hasattr(design, "cell_period_nm")
    assert not hasattr(study, "cell")
    assert not hasattr(study, "cell_policy")


def test_brief_and_study_modules_preserve_the_compiled_contract() -> None:
    """
    Keep the public compiler seam stable across the aim-local ownership split.
    """

    briefs = (
        propagation_brief(),
        geometric_brief(),
    )
    for brief in briefs:
        study = compile_metalens(brief)
        repeated = compile_metalens(brief)

        assert type(brief).__module__ == "metacraft.science.metalens.brief"
        assert type(study).__module__ == "metacraft.science.study"
        assert hashlib.sha256(brief.canonical_bytes()).digest()
        assert study.canonical_bytes() == repeated.canonical_bytes()


def test_metalens_brief_names_material_families_and_aperture_sites() -> None:
    """
    Brief facts expose the canonical material-family and site-count nouns.
    """

    brief = long_focus_propagation_brief()

    assert brief.atom.material.family == "silicon nitride"
    assert brief.substrate.family == "silica"
    assert brief.aperture is not None
    assert brief.aperture.site_count == 185
    assert not hasattr(brief.atom.material, "material")
    assert not hasattr(brief.aperture, "cells")


def test_height_advice_storage_remains_provider_free() -> None:
    """
    Study storage retains scientific grounds without transport provenance.
    """

    brief = propagation_brief()
    advice = _height_advice(
        brief,
        domain_reference=_reference("height-domain"),
    )

    assert not hasattr(advice, "provider")
    assert not hasattr(advice, "model")
    assert not hasattr(advice, "prompt")
    assert not hasattr(advice, "raw_response")
    stored = compile_metalens(brief, advice=(advice,)).document().values
    advice_values = stored["advice"]["advice_001"]
    assert "provider" not in advice_values
    assert "model" not in advice_values
    assert "prompt" not in advice_values
    assert "raw_response" not in advice_values


@pytest.mark.parametrize(
    "brief_factory",
    (propagation_brief, geometric_brief),
)
def test_compiler_ownership_keeps_canonical_study_bytes(
    brief_factory,
) -> None:
    study = compile_metalens(brief_factory())
    repeated = compile_metalens(brief_factory())

    assert study.canonical_bytes() == study.document().to_bytes()
    assert study.canonical_bytes() == repeated.canonical_bytes()


@pytest.mark.parametrize(
    ("brief_factory", "expected"),
    (
        (
            propagation_brief,
            # Fixed after the closed operating-spectrum Brief cutover.
            "a6d647299d87d975622071e7ea6bfcb36629bf2cac3b11f07ff1c8d4662dd795",
        ),
        (
            geometric_brief,
            # Fixed after the closed operating-spectrum Brief cutover.
            "9fea99449828fbc4822d405db7a861e82481140e611c810cce34a681ec9fef15",
        ),
    ),
)
def test_material_source_spelling_keeps_canonical_brief_bytes(
    brief_factory,
    expected: str,
) -> None:
    assert hashlib.sha256(brief_factory().canonical_bytes()).hexdigest() == expected


def test_standard_briefs_compile_as_claim_method_routes() -> None:
    propagation = compile_metalens(propagation_brief())
    geometric = compile_metalens(geometric_brief())

    assert propagation.route.applicability == (
        "declared control strategy: propagation phase; "
        "numerical aperture: at most 0.5"
    )
    assert geometric.route.applicability == (
        "declared control strategy: geometric phase; " "numerical aperture: at most 0.5"
    )
    assert tuple(
        (choice.claim, choice.method, choice.requires)
        for choice in propagation.route.choices[-6:]
    ) == (
        ("phase_set", "form_phase_set", ("cell_library",)),
        (
            "physical_lattice",
            "resolve_physical_lattice",
            ("period_choice", "height_choice"),
        ),
        (
            "aperture",
            "assign_aperture",
            ("phase_set", "physical_lattice"),
        ),
        ("field", "form_field", ("aperture",)),
        ("focal_region", "propagate_field", ("field",)),
        ("focus", "evaluate_focus", ("focal_region",)),
    )
    assert tuple(
        (choice.claim, choice.method, choice.requires)
        for choice in geometric.route.choices[-9:]
    ) == (
        (
            "jones_library",
            "observe_periodic_polarization",
            (
                "material_binding",
                "height_choice",
                "polarization_convention",
            ),
        ),
        ("cell_choice", "choose_cell", ("jones_library",)),
        ("orientations", "derive_orientations", ("cell_choice",)),
        (
            "orientation_set",
            "form_orientation_set",
            ("orientations",),
        ),
        (
            "physical_lattice",
            "resolve_physical_lattice",
            ("period_choice", "height_choice"),
        ),
        (
            "aperture",
            "assign_aperture",
            ("orientation_set", "physical_lattice"),
        ),
        ("field", "form_field", ("aperture",)),
        ("focal_region", "propagate_field", ("field",)),
        ("focus", "evaluate_focus", ("focal_region",)),
    )
    assert propagation.design.aim == "metalens"
    assert propagation.design.objectives == ("focus",)
    assert all(choice.claim != "result" for choice in propagation.route.choices)


def test_aperture_intent_must_match_the_compiled_optical_scale() -> None:
    inconsistent = replace(
        long_focus_propagation_brief(),
        aperture=ApertureIntent(
            site_count=200,
            extent=ApertureExtent.DIAMETER,
        ),
    )

    study = compile_metalens(inconsistent)
    assert any(finding.claim == "height_domain" for finding in study.findings)


def test_aperture_intent_requires_a_registered_extent() -> None:
    invalid = replace(
        long_focus_propagation_brief(),
        aperture=ApertureIntent(
            site_count=185,
            extent="nonsense",  # type: ignore[arg-type]
        ),
    )

    with pytest.raises(ValueError, match="aperture_extent_invalid"):
        compile_metalens(invalid)


def test_unresolved_brief_names_its_missing_facts() -> None:
    incomplete = replace(
        propagation_brief(),
        wording="Design a compact 400 nm low-na metalens on silica.",
        control_strategy=None,
    )

    with pytest.raises(MissingBriefFacts) as raised:
        compile_metalens(incomplete)

    assert raised.value.missing_facts == ("control_strategy",)
    assert str(raised.value) == "brief_incomplete:control_strategy"


def test_missing_inputs_are_typed_waiting_findings() -> None:
    brief = propagation_brief()
    target_fact = evidence_fact_for(
        brief,
        "target_phase",
        _reference("target"),
    )
    study = compile_metalens(
        brief,
        evidence=(target_fact,),
    )

    assert study.findings[:2] == (
        Finding(
            claim="material_binding",
            kind=FindingKind.CAPABILITY,
            needs=("optical_material",),
        ),
        Finding(
            claim="period_domain",
            kind=FindingKind.PREREQUISITE,
            needs=("material_binding",),
        ),
    )
    assert not hasattr(study, "unresolved")


def test_capability_without_binding_waits_for_a_realization() -> None:
    brief = propagation_brief()
    evidence = (
        evidence_fact_for(
            brief,
            "target_phase",
            _reference("target"),
        ),
    )
    capabilities = (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
    )
    study = compile_metalens(
        brief,
        evidence=evidence,
        capabilities=capabilities,
    )

    assert study.findings[:2] == (
        Finding(
            claim="material_binding",
            kind=FindingKind.BINDING,
            needs=("optical_material",),
        ),
        Finding(
            claim="period_domain",
            kind=FindingKind.PREREQUISITE,
            needs=("material_binding",),
        ),
    )
    assert not any(
        task.claim in {"material_binding", "height_domain"}
        for task in study.ready_tasks
    )

    bound = compile_metalens(
        brief,
        evidence=evidence,
        capabilities=capabilities,
        bindings=(
            Binding("optical_material", _reference("material-binding")),
            Binding("fabrication_constraint", _reference("domain-binding")),
        ),
    )

    assert tuple(task.claim for task in bound.ready_tasks) == ("material_binding",)


def test_study_preserves_brief_and_orders_advice_without_rewriting_facts() -> None:
    brief = geometric_brief()
    initial = compile_metalens(brief)
    period_domain = fixture_period_domain(initial)
    period_advice = fixture_period_advice(
        initial,
        period_domain,
        period_nm=period_domain.period_limit_nm,
    )
    height_domain = fixture_height_domain(initial)
    height_advice = fixture_height_advice(brief, height_domain)

    first = compile_metalens(
        brief,
        advice=(period_advice, height_advice),
    )
    second = compile_metalens(
        brief,
        advice=(height_advice, period_advice),
    )

    assert first == second
    assert first.brief == brief
    assert first.brief.objectives == ("focus",)
    assert first.brief.omissions == (
        "large_na",
        "multiwavelength",
        "optimization",
    )
    assert first.design.control_strategy is ControlStrategy.GEOMETRIC_PHASE
    assert set(first.advice) == {period_advice, height_advice}


@pytest.mark.parametrize(
    (
        "brief_factory",
        "wavelength_nm",
        "numerical_aperture",
        "focal_length_um",
        "control_strategy",
        "shape",
        "dimension_step_nm",
    ),
    [
        (
            propagation_brief,
            400,
            Decimal("0.30"),
            Decimal("30"),
            ControlStrategy.PROPAGATION_PHASE,
            "circular pillar",
            10,
        ),
        (
            geometric_brief,
            400,
            Decimal("0.30"),
            Decimal("30"),
            ControlStrategy.GEOMETRIC_PHASE,
            "rectangular fin",
            20,
        ),
        (
            long_focus_propagation_brief,
            355,
            Decimal("0.28"),
            Decimal("200"),
            ControlStrategy.PROPAGATION_PHASE,
            "circular pillar",
            10,
        ),
        (
            long_focus_geometric_brief,
            355,
            Decimal("0.28"),
            Decimal("200"),
            ControlStrategy.GEOMETRIC_PHASE,
            "rectangular fin",
            20,
        ),
    ],
)
def test_public_brief_factories_form_one_reviewable_ready_task(
    brief_factory,
    wavelength_nm: int,
    numerical_aperture: Decimal,
    focal_length_um: Decimal,
    control_strategy: ControlStrategy,
    shape: str,
    dimension_step_nm: int,
) -> None:
    brief = brief_factory()

    first = compile_metalens(brief)
    second = compile_metalens(brief)

    assert (
        require_monochromatic_wavelength(brief.operating_spectrum),
        brief.numerical_aperture,
        brief.focal_length_um,
        brief.control_strategy,
        brief.atom.shape,
        brief.dimension_step_nm,
    ) == (
        wavelength_nm,
        numerical_aperture,
        focal_length_um,
        control_strategy,
        shape,
        dimension_step_nm,
    )
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.design.control_strategy is brief.control_strategy
    assert tuple((task.claim, task.method) for task in first.ready_tasks) == (
        ("target_phase", "derive_target_phase"),
    )


def test_propagation_and_geometric_proofs_cannot_blur() -> None:
    propagation = compile_metalens(propagation_brief())
    geometric = compile_metalens(geometric_brief())
    propagation_names = {obligation.name for obligation in propagation.proof.claims}
    geometric_names = {obligation.name for obligation in geometric.proof.claims}

    assert "jones_library" not in propagation_names
    assert "periodic_transmission" not in geometric_names
    assert "polarization_convention" not in propagation_names
    assert "polarization_convention" in geometric_names


def test_geometric_jones_sweep_waits_for_its_own_height_choice() -> None:
    brief = replace(geometric_brief(), cell_period_nm=200)
    capabilities = (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
        Capability("periodic_polarization_response"),
        Capability("deterministic_selection"),
        Capability("polarization_convention"),
    )
    bindings = (
        Binding("optical_material", _reference("binding-material")),
        Binding("fabrication_constraint", _reference("binding-fabrication")),
        Binding(
            "periodic_polarization_response",
            _reference("binding-lumerical"),
            "capacity:lumerical",
        ),
        Binding("deterministic_selection", _reference("binding-selection")),
        Binding("polarization_convention", _reference("binding-polarization")),
    )
    domain_references = {
        "target_phase": _reference("target"),
        "material_binding": _reference("material"),
        "period_domain": _reference("period-domain"),
        "period_choice": _reference("period-choice"),
        "height_domain": _reference("height-domain"),
        "polarization_convention": _reference("polarization-convention"),
    }

    awaiting_advice, _ = compile_with_facts(
        brief,
        domain_references,
        capabilities=capabilities,
        bindings=bindings,
    )
    advice = _height_advice(
        brief,
        domain_reference=domain_references["height_domain"],
    )
    advice_reference = reference_for(advice.document().to_bytes())
    advised, _ = compile_with_facts(
        brief,
        domain_references,
        advice=(advice,),
        capabilities=capabilities,
        bindings=bindings,
    )

    assert (
        Finding(
            claim="height_choice",
            kind=FindingKind.ADVICE,
            needs=("height",),
        )
        in awaiting_advice.findings
    )
    assert "jones_library" not in {task.claim for task in awaiting_advice.ready_tasks}
    assert tuple(
        task.claim for task in advised.ready_tasks if task.claim == "height_choice"
    ) == ("height_choice",)
    assert advised.ready_tasks[-1].consultations == (advice_reference,)


def test_geometric_proof_names_each_admitted_scientific_meaning_once() -> None:
    study = compile_metalens(geometric_brief())

    names = tuple(obligation.name for obligation in study.proof.claims)

    assert "periodic_jones" not in names
    assert "converted_library" not in names
    assert study.proof.terminal_claims == ("focus",)
    assert names[names.index("height_choice") :] == (
        "height_choice",
        "polarization_convention",
        "jones_library",
        "cell_choice",
        "orientations",
        "orientation_set",
        "physical_lattice",
        "aperture",
        "field",
        "focal_region",
        "focus",
    )


def test_empty_fabrication_domain_is_rejected_honestly() -> None:
    impossible = replace(
        propagation_brief(),
        aspect_limit=1,
    )

    study = compile_metalens(impossible)
    domain = fixture_height_domain(study)

    assert domain.heights_nm == ()
    assert all(entry.candidate_count == 0 for entry in domain.fabrication_ranges)


def test_study_progresses_only_from_matching_evidence() -> None:
    brief = replace(propagation_brief(), cell_period_nm=200)
    capabilities = (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
        Capability("periodic_transmission_response"),
        Capability("cell_library"),
        Capability("deterministic_selection"),
        Capability("angular_spectrum_propagation"),
        Capability("focus_evaluation"),
    )
    bindings = (
        Binding("optical_material", _reference("binding-material")),
        Binding("fabrication_constraint", _reference("binding-fabrication")),
        Binding(
            "periodic_transmission_response",
            _reference("binding-lumerical"),
            "capacity:lumerical",
        ),
        Binding("cell_library", _reference("binding-cell-library")),
        Binding("deterministic_selection", _reference("binding-selection")),
        Binding(
            "angular_spectrum_propagation",
            _reference("binding-angular-spectrum"),
        ),
        Binding("focus_evaluation", _reference("binding-focus")),
    )

    first = compile_metalens(
        brief,
        capabilities=capabilities,
        bindings=bindings,
    )
    second, _ = compile_with_facts(
        brief,
        {
            "target_phase": _reference("evidence-target"),
            "material_binding": _reference("evidence-material"),
            "period_domain": _reference("evidence-period-domain"),
            "period_choice": _reference("evidence-period-choice"),
            "height_domain": _reference("evidence-height-domain"),
        },
        capabilities=capabilities,
        bindings=bindings,
    )

    assert tuple(task.claim for task in first.ready_tasks) == ("target_phase",)
    assert tuple(task.claim for task in second.ready_tasks) == ("phase_envelope",)
    assert not any(
        finding.claim == "height_choice" and finding.kind is FindingKind.ADVICE
        for finding in second.findings
    )
    assert "height_survey" not in {
        obligation.name for obligation in second.proof.claims
    }


def test_propagation_lateral_sweep_waits_for_height_choice() -> None:
    brief = replace(propagation_brief(), cell_period_nm=200)
    capabilities = (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
        Capability("periodic_transmission_response"),
        Capability("cell_library"),
        Capability("deterministic_selection"),
        Capability("angular_spectrum_propagation"),
        Capability("focus_evaluation"),
    )
    bindings = (
        Binding("optical_material", _reference("binding-material")),
        Binding("fabrication_constraint", _reference("binding-fabrication")),
        Binding(
            "periodic_transmission_response",
            _reference("binding-lumerical"),
            "capacity:lumerical",
        ),
        Binding("cell_library", _reference("binding-cell-library")),
        Binding("deterministic_selection", _reference("binding-selection")),
        Binding(
            "angular_spectrum_propagation",
            _reference("binding-angular-spectrum"),
        ),
        Binding("focus_evaluation", _reference("binding-focus")),
    )
    domain_references = {
        "target_phase": _reference("target"),
        "material_binding": _reference("material"),
        "period_domain": _reference("period-domain"),
        "period_choice": _reference("period-choice"),
        "height_domain": _reference("height-domain"),
        "phase_envelope": _reference("phase-envelope"),
    }

    awaiting_advice, _ = compile_with_facts(
        brief,
        domain_references,
        capabilities=capabilities,
        bindings=bindings,
    )
    advice = _height_advice(
        brief,
        domain_reference=domain_references["height_domain"],
        envelope_reference=domain_references["phase_envelope"],
    )
    advice_reference = reference_for(advice.document().to_bytes())
    advised, _ = compile_with_facts(
        brief,
        domain_references,
        advice=(advice,),
        capabilities=capabilities,
        bindings=bindings,
    )

    assert not awaiting_advice.ready_tasks
    assert (
        Finding(
            claim="height_choice",
            kind=FindingKind.ADVICE,
            needs=("height",),
        )
        in awaiting_advice.findings
    )
    assert tuple(task.claim for task in advised.ready_tasks) == ("height_choice",)
    assert "height_advice" not in {
        obligation.name for obligation in advised.proof.claims
    }
    assert advised.ready_tasks[0].consultations == (advice_reference,)
    assert "periodic_transmission" not in {task.claim for task in advised.ready_tasks}


def test_evidence_cannot_cross_routes_or_skip_prerequisites() -> None:
    brief = propagation_brief()

    foreign_fact = evidence_fact_for(
        geometric_brief(),
        "target_phase",
        _reference("foreign"),
    )
    with pytest.raises(ValueError, match="evidence_task_identity_mismatch"):
        compile_metalens(
            brief,
            evidence=(foreign_fact,),
        )

    with pytest.raises(ValueError, match="evidence_prerequisites_incomplete"):
        compile_metalens(
            brief,
            evidence=(
                Evidence(
                    task_identity="sha256:fixture",
                    claim="periodic_transmission",
                    schema=PERIODIC_TRANSMISSION_SCHEMA,
                    reference=_reference("downstream"),
                ),
            ),
        )


def test_compiled_study_crosses_the_public_authority_seam(
    tmp_path: Path,
) -> None:
    study = compile_metalens(propagation_brief())
    authority = Authority(tmp_path / "workspace")

    decision = authority.decide(
        Proposal.record(study.document()),
        at=Revision.root(),
    )

    assert decision.admitted
    assert decision.body_reference is not None
    assert authority.fetch(decision.body_reference)
