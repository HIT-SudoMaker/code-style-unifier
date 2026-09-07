from __future__ import annotations

import builtins
import importlib
from dataclasses import replace
from decimal import Decimal

import metacraft
import pytest
from metacraft.science.brief import Brief
from metacraft.science.compile import (
    InvalidBrief,
    UnsupportedAim,
    compile_study,
)
from metacraft.science.metalens.brief import (
    ApertureExtent,
    ApertureFootprint,
    ApertureIntent,
    ControlStrategy,
    ContinuousBandSpectrum,
    MetalensBrief,
    MonochromaticSpectrum,
    Polarization,
)
from metacraft.science.metalens.design import (
    MethodApplicability,
    resolve_metalens_design,
)
from metacraft.science.metalens.achromatic import AchromaticTarget
from metacraft.science.study import Finding, FindingKind, Study
from tests.brief_fixtures import (
    continuous_achromatic_brief,
    geometric_brief,
    propagation_brief,
)


compile_module = importlib.import_module("metacraft.science.compile")


def test_one_metalens_brief_encodes_a_closed_operating_spectrum() -> None:
    monochromatic = propagation_brief()
    continuous = replace(
        geometric_brief(),
        operating_spectrum=ContinuousBandSpectrum(
            lower_wavelength_nm=470,
            upper_wavelength_nm=590,
        ),
        omissions=(
            "aperture",
            "atom_height_nm",
            "cell_period_nm",
            "large_na",
            "optimization",
        ),
    )

    assert monochromatic.operating_spectrum == MonochromaticSpectrum(400)
    assert MetalensBrief.decode_canonical_bytes(continuous.canonical_bytes()) == (
        continuous
    )
    assert "wavelength_nm" not in continuous.canonical_value()
    assert continuous.canonical_value()["operating_spectrum"] == {
        "kind": "continuous band",
        "lower_wavelength_nm": 470,
        "upper_wavelength_nm": 590,
    }


def test_continuous_user_intent_selects_one_aim_owned_method_assessment() -> None:
    design = resolve_metalens_design(continuous_achromatic_brief())

    assert design.capabilities == ()
    assert len(design.method_assessments) == 1
    assessment = design.method_assessments[0]
    assert assessment.method == "transmissive pb dispersion single rectangle"
    assert assessment.applicability is MethodApplicability.SELECTED
    assert assessment.grounds == (
        "continuous operating spectrum",
        "circular incident polarization",
        "anisotropic primitive rectangle",
        "single-rectangle material response decided by spectral evidence",
    )


def test_continuous_intent_compiles_a_delay_bounded_achromatic_proof() -> None:
    outcome = compile_study(continuous_achromatic_brief())

    assert isinstance(outcome, Study)
    design = resolve_metalens_design(continuous_achromatic_brief())
    target = AchromaticTarget.from_design(design)
    assert target.reference_wavelength_nm == 530
    assert target.lower_wavelength_nm == 470
    assert target.upper_wavelength_nm == 590
    assert Decimal("3.36") < target.required_relative_delay_fs < Decimal("3.38")
    assert tuple(claim.name for claim in outcome.proof.claims) == (
        "achromatic_target",
        "response_qualification_profile",
        "spectral_study_specification",
        "spectral_material_binding",
        "spectral_cell_study_plan",
        "physical_lattice",
        "spectral_cell_screen",
        "spectral_jones_library",
        "qualified_spectral_library",
        "achromatic_aperture",
        "post_freeze_jones_library",
        "spectral_field_family",
        "achromatic_focus",
        "focus",
    )
    assert tuple(task.claim for task in outcome.ready_tasks) == ("achromatic_target",)


def test_continuous_method_is_refused_from_user_facts_before_solver_work() -> None:
    brief = continuous_achromatic_brief()
    incompatible = replace(
        brief,
        atom=replace(brief.atom, shape="circular pillar"),
    )

    outcome = compile_study(incompatible)

    assert isinstance(outcome, Study)
    assert outcome.ready_tasks == ()
    assert outcome.findings[0] == Finding(
        claim="achromatic_target",
        kind=FindingKind.REFUSAL,
        needs=("continuous_method_requires_anisotropic_rectangle",),
    )
    assert all(
        finding.kind is FindingKind.PREREQUISITE for finding in outcome.findings[1:]
    )


def test_continuous_structure_does_not_refuse_an_explicit_alternative_by_name() -> None:
    brief = continuous_achromatic_brief()
    alternative = replace(
        brief,
        atom=replace(
            brief.atom,
            material=replace(brief.atom.material, family="silicon nitride"),
        ),
    )

    design = resolve_metalens_design(alternative)

    assert design.method_assessments[0].applicability is MethodApplicability.SELECTED
    assert "silicon nitride" not in design.method_assessments[0].grounds


def test_root_exposes_only_the_three_application_entries() -> None:
    assert metacraft.__all__ == [
        "Authority",
        "compile_study",
        "conduct",
    ]


def test_supported_brief_compiles_to_one_deterministic_study() -> None:
    brief = replace(
        propagation_brief(),
        cell_period_nm=200,
        atom_height_nm=600,
    )

    first = compile_study(brief)
    repeated = compile_study(brief)

    assert isinstance(first, Study)
    assert isinstance(repeated, Study)
    assert repeated.canonical_bytes() == first.canonical_bytes()


def test_compile_study_performs_no_file_or_process_work(
    monkeypatch,
) -> None:
    brief = replace(
        propagation_brief(),
        cell_period_nm=200,
        atom_height_nm=600,
    )

    def reject_file_work(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("compile_performed_file_work")

    monkeypatch.setattr(builtins, "open", reject_file_work)

    outcome = compile_study(brief)

    assert isinstance(outcome, Study)


@pytest.mark.parametrize(
    ("aim", "wording", "objectives"),
    (
        (
            "holographic metasurface",
            "Reconstruct one holographic field and assess its quality.",
            ("reconstruction", "fidelity", "efficiency", "crosstalk"),
        ),
        (
            "quasi-bic metasurface",
            "Characterize one quasi-BIC resonance and its radiation.",
            ("resonance", "quality_factor", "linewidth"),
        ),
        (
            "frequency selective surface",
            "Resolve angle- and polarization-aware spectral response.",
            ("reflection", "transmission", "absorption"),
        ),
    ),
)
def test_known_unimplemented_aim_is_typed_unsupported(
    aim: str,
    wording: str,
    objectives: tuple[str, ...],
) -> None:
    brief = Brief(
        wording=wording,
        aim=aim,
        objectives=objectives,
        budget="relationship only",
        omissions=("solver", "fabrication"),
    )

    outcome = compile_study(brief)

    assert outcome == UnsupportedAim(aim)


def test_unknown_aim_is_an_invalid_brief() -> None:
    brief = Brief(
        wording="Attempt an unknown device.",
        aim="beam deflector",
        objectives=("deflection",),
        budget="bounded",
    )

    outcome = compile_study(brief)

    assert outcome == InvalidBrief("aim_unknown")


@pytest.mark.parametrize("brief", (propagation_brief(), geometric_brief()))
def test_monochromatic_route_places_only_an_authoritative_physical_lattice(
    brief: MetalensBrief,
) -> None:
    outcome = compile_study(brief)
    assert isinstance(outcome, Study)
    choices = {choice.claim: choice for choice in outcome.route.choices}

    assert choices["physical_lattice"].requires == (
        "period_choice",
        "height_choice",
    )
    assert "physical_lattice" in choices["aperture"].requires


def test_malformed_metalens_brief_is_invalid() -> None:
    malformed = Brief(
        wording="Focus light.",
        aim="metalens",
        objectives=("focus",),
        budget="bounded",
    )

    outcome = compile_study(malformed)

    assert outcome == InvalidBrief("metalens_facts_missing")


def test_aim_specific_brief_cannot_claim_another_known_aim() -> None:
    mismatched = replace(
        propagation_brief(),
        aim="holographic metasurface",
    )

    outcome = compile_study(mismatched)

    assert outcome == InvalidBrief("brief_aim_mismatch")


def test_empty_common_brief_wording_is_invalid() -> None:
    malformed = replace(propagation_brief(), wording=" ")

    outcome = compile_study(malformed)

    assert outcome == InvalidBrief("brief_wording_invalid")


def test_non_brief_value_is_invalid() -> None:
    assert compile_study(object()) == InvalidBrief(  # type: ignore[arg-type]
        "brief_type_invalid"
    )


@pytest.mark.parametrize(
    ("changes", "reason"),
    (
        ({"wording": 1}, "brief_wording_invalid"),
        ({"aim": ""}, "brief_aim_invalid"),
        ({"budget": None}, "brief_budget_invalid"),
        ({"objectives": ["focus"]}, "brief_objectives_invalid"),
        ({"objectives": ("focus", "focus")}, "brief_objectives_duplicate"),
        ({"objectives": ()}, "brief_objectives_missing"),
        ({"omissions": ["solver"]}, "brief_omissions_invalid"),
        ({"omissions": ("solver", "solver")}, "brief_omissions_duplicate"),
    ),
)
def test_each_common_brief_finding_is_exact(
    changes: dict[str, object],
    reason: str,
) -> None:
    malformed = replace(propagation_brief(), **changes)

    assert compile_study(malformed) == InvalidBrief(reason)


def test_plain_metalens_brief_reports_missing_aim_facts() -> None:
    incomplete = Brief(
        wording="Focus light.",
        aim="metalens",
        objectives=("focus",),
        budget="bounded",
    )

    assert compile_study(incomplete) == InvalidBrief("metalens_facts_missing")


def test_metalens_brief_cannot_claim_another_aim() -> None:
    mismatched = replace(
        propagation_brief(),
        aim="frequency selective surface",
    )

    assert compile_study(mismatched) == InvalidBrief("brief_aim_mismatch")


def test_invalid_metalens_fact_is_an_invalid_brief() -> None:
    malformed = replace(propagation_brief(), operating_spectrum=object())

    outcome = compile_study(malformed)

    assert outcome == InvalidBrief("operating_spectrum_invalid")


def test_missing_metalens_fact_is_an_invalid_brief() -> None:
    incomplete = replace(propagation_brief(), control_strategy=None)

    outcome = compile_study(incomplete)

    assert outcome == InvalidBrief("brief_incomplete:control_strategy")


@pytest.mark.parametrize(
    ("changes", "reason"),
    (
        ({"operating_spectrum": True}, "operating_spectrum_invalid"),
        ({"focal_length_um": 1}, "focal_length_invalid"),
        ({"numerical_aperture": Decimal("NaN")}, "numerical_aperture_invalid"),
        ({"control_strategy": "unknown"}, "control_strategy_invalid"),
        ({"atom": object()}, "atom_intent_invalid"),
        (
            {"atom": replace(propagation_brief().atom, shape=" ")},
            "atom_geometry_invalid",
        ),
        ({"substrate": object()}, "material_intent_invalid"),
        ({"incident_polarization": object()}, "incident_polarization_invalid"),
        ({"aspect_limit": True}, "aspect_limit_invalid"),
        ({"solver_preference": " "}, "solver_preference_invalid"),
        ({"dimension_step_nm": Decimal("10")}, "dimension_step_invalid"),
        ({"cell_period_nm": True}, "cell_period_invalid"),
        ({"atom_height_nm": Decimal("600")}, "atom_height_invalid"),
        ({"aperture": object()}, "aperture_intent_invalid"),
        (
            {
                "aperture": ApertureIntent(
                    site_count=-1,
                    extent=ApertureExtent.DIAMETER,
                )
            },
            "aperture_intent_invalid",
        ),
        (
            {
                "aperture": ApertureIntent(
                    site_count=5,
                    extent="unknown",  # type: ignore[arg-type]
                )
            },
            "aperture_extent_invalid",
        ),
        (
            {
                "aperture": ApertureIntent(
                    site_count=5,
                    extent=ApertureExtent.DIAMETER,
                    footprint="unknown",  # type: ignore[arg-type]
                )
            },
            "aperture_footprint_invalid",
        ),
        (
            {
                "aperture": ApertureIntent(
                    site_count=4,
                    extent=ApertureExtent.DIAMETER,
                    footprint=ApertureFootprint.SQUARE,
                )
            },
            "square_aperture_intent_invalid",
        ),
    ),
)
def test_each_explicit_metalens_input_finding_is_exact(
    changes: dict[str, object],
    reason: str,
) -> None:
    malformed = replace(propagation_brief(), **changes)

    assert compile_study(malformed) == InvalidBrief(reason)


def test_missing_dimension_step_is_an_invalid_brief() -> None:
    incomplete = replace(propagation_brief(), dimension_step_nm=None)

    assert compile_study(incomplete) == InvalidBrief(
        "brief_incomplete:dimension_step_nm"
    )


@pytest.mark.parametrize(
    ("strategy", "shape"),
    (
        (ControlStrategy.PROPAGATION_PHASE, "circular pillar"),
        (ControlStrategy.PROPAGATION_PHASE, "square pillar"),
        (ControlStrategy.GEOMETRIC_PHASE, "rectangular fin"),
        (ControlStrategy.GEOMETRIC_PHASE, "elliptical pillar"),
    ),
)
def test_each_control_strategy_accepts_only_its_canonical_atom_shapes(
    strategy: ControlStrategy,
    shape: str,
) -> None:
    base = (
        propagation_brief()
        if strategy is ControlStrategy.PROPAGATION_PHASE
        else geometric_brief()
    )
    brief = replace(
        base,
        atom=replace(base.atom, shape=shape),
    )

    assert isinstance(compile_study(brief), Study)


@pytest.mark.parametrize(
    ("strategy", "shape", "reason"),
    (
        (
            ControlStrategy.PROPAGATION_PHASE,
            "triangle",
            "propagation_atom_shape_unsupported",
        ),
        (
            ControlStrategy.PROPAGATION_PHASE,
            "rectangular fin",
            "propagation_atom_shape_unsupported",
        ),
        (
            ControlStrategy.GEOMETRIC_PHASE,
            "banana",
            "geometric_atom_shape_unsupported",
        ),
        (
            ControlStrategy.GEOMETRIC_PHASE,
            "circular pillar",
            "geometric_atom_shape_unsupported",
        ),
    ),
)
def test_noncanonical_atom_shape_is_an_exact_invalid_brief(
    strategy: ControlStrategy,
    shape: str,
    reason: str,
) -> None:
    base = (
        propagation_brief()
        if strategy is ControlStrategy.PROPAGATION_PHASE
        else geometric_brief()
    )
    malformed = replace(base, atom=replace(base.atom, shape=shape))

    assert compile_study(malformed) == InvalidBrief(reason)


@pytest.mark.parametrize(
    "polarization",
    (
        Polarization(kind="linear", axis="x"),
        Polarization(kind="linear", axis="y"),
        Polarization(kind="circular", handedness="left"),
        Polarization(kind="circular", handedness="right"),
    ),
)
def test_closed_polarization_vocabulary_compiles(
    polarization: Polarization,
) -> None:
    brief = replace(
        propagation_brief(),
        incident_polarization=polarization,
    )

    assert isinstance(compile_study(brief), Study)


@pytest.mark.parametrize(
    "polarization",
    (
        Polarization(kind="banana", axis="x"),
        Polarization(kind="linear"),
        Polarization(kind="linear", axis="z"),
        Polarization(kind="linear", axis="x", handedness="left"),
        Polarization(kind="linear", axis=[]),  # type: ignore[arg-type]
        Polarization(kind="circular"),
        Polarization(kind="circular", handedness="clockwise"),
        Polarization(kind="circular", handedness={}),  # type: ignore[arg-type]
        Polarization(kind="circular", axis="x", handedness="left"),
    ),
)
def test_noncanonical_polarization_is_an_exact_invalid_brief(
    polarization: Polarization,
) -> None:
    malformed = replace(
        propagation_brief(),
        incident_polarization=polarization,
    )

    assert compile_study(malformed) == InvalidBrief("incident_polarization_invalid")


def test_geometric_strategy_rejects_valid_linear_polarization() -> None:
    malformed = replace(
        geometric_brief(),
        incident_polarization=Polarization(kind="linear", axis="x"),
    )

    assert compile_study(malformed) == InvalidBrief("geometric_polarization_invalid")


@pytest.mark.parametrize("error_type", (TypeError, ValueError))
def test_compiler_defect_propagates(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[TypeError] | type[ValueError],
) -> None:
    injected = error_type("compiler_defect")

    def fail_compilation(_brief: Brief) -> Study:
        raise injected

    monkeypatch.setattr(compile_module, "compile_metalens", fail_compilation)

    with pytest.raises(error_type) as raised:
        compile_study(propagation_brief())

    assert raised.value is injected
