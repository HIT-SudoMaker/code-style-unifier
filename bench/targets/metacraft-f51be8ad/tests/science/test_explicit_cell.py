from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from metacraft.authority.reference import reference_for
from tests.brief_fixtures import propagation_brief
from metacraft.science import Study
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.brief import MonochromaticSpectrum
from metacraft.science.metalens.design import require_metalens_design
from metacraft.science.metalens.height import (
    HeightConstraintBasis,
    resolve_height_choice,
)
from tests.domain_fixtures import (
    height_domain,
    phase_envelope,
)


def _brief(**changes):
    return replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(wavelength_nm=686),
        numerical_aperture=Decimal("0.4"),
        **changes,
    )


def test_conduct_keeps_one_explicit_cell_constraint() -> None:
    answer = compile_metalens(
        _brief(cell_period_nm=857, atom_height_nm=900),
    )

    assert isinstance(answer, Study)
    design = require_metalens_design(answer)
    assert design.sampling_ceiling_nm == Decimal("857.5")
    assert not hasattr(design, "cell_period_nm")
    assert answer.brief.cell_period_nm == 857
    assert answer.brief.atom_height_nm == 900


def test_open_period_waits_without_inventing_a_default() -> None:
    answer = compile_metalens(_brief())

    assert isinstance(answer, Study)
    design = require_metalens_design(answer)
    assert design.sampling_ceiling_nm == Decimal("857.5")
    assert not hasattr(design, "cell_period_nm")
    assert answer.brief.cell_period_nm is None


def test_period_validation_waits_for_material_evidence() -> None:
    answer = compile_metalens(_brief(cell_period_nm=858, atom_height_nm=900))

    assert isinstance(answer, Study)
    assert not any(
        finding.needs == ("cell_period_above_sampling_ceiling",)
        for finding in answer.findings
    )


def test_explicit_height_forms_one_cited_choice_without_advice() -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(wavelength_nm=940),
        numerical_aperture=Decimal("0.16"),
        cell_period_nm=400,
        atom_height_nm=900,
    )
    base = compile_metalens(brief)
    domain = height_domain(base, atom_index="3.5")
    envelope = phase_envelope(
        base,
        domain,
        atom_index="3.5",
    )
    target = reference_for(b"ticket01 target phase")
    material = domain.material_binding_reference
    from tests.domain_fixtures import (
        period_domain as period_domain_fixture,
        period_choice as period_choice_fixture,
    )

    pdomain = period_domain_fixture(base, atom_index="3.5")
    pchoice = period_choice_fixture(base, atom_index="3.5")
    references = {
        "target_phase": target,
        "material_binding": material,
        "period_domain": pdomain.evidence_reference,
        "period_choice": pchoice.evidence_reference,
        "height_domain": domain.evidence_reference,
        "phase_envelope": envelope.evidence_reference,
    }
    from metacraft.science.study import Binding, Capability
    from tests.domain_fixtures import compile_with_facts

    capabilities = (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
        Capability("deterministic_selection"),
    )
    bindings = (
        Binding(
            "optical_material",
            reference_for(b"optical-binding"),
        ),
        Binding(
            "fabrication_constraint",
            reference_for(b"fabrication-binding"),
        ),
        Binding(
            "deterministic_selection",
            reference_for(b"selection-binding"),
        ),
    )
    interim, facts = compile_with_facts(
        brief,
        references,
        capabilities=capabilities,
        bindings=bindings,
    )
    study = compile_metalens(
        brief,
        evidence=tuple(facts.values()),
        capabilities=capabilities,
        bindings=bindings,
    )

    choice = resolve_height_choice(
        study,
        domain,
        envelope=envelope,
    )

    assert domain.period_nm == 400
    assert domain.heights_nm == (900,)
    assert choice.height_nm == 900
    assert choice.period_nm == 400
    assert choice.basis == HeightConstraintBasis()
    assert choice.references() == (domain.evidence_reference,)
    assert "advice_reference" not in choice.document().values


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"cell_period_nm": 0}, "cell_period_invalid"),
        ({"cell_period_nm": Decimal("400")}, "cell_period_invalid"),
        ({"atom_height_nm": -1}, "atom_height_invalid"),
        ({"atom_height_nm": Decimal("500")}, "atom_height_invalid"),
    ),
)
def test_malformed_explicit_cell_values_fail_the_brief(
    changes,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        compile_metalens(replace(propagation_brief(), **changes))
