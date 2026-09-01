from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from metacraft.authority import Authority, Proposal
from tests.brief_fixtures import (
    long_focus_propagation_brief,
    propagation_brief,
)
from metacraft.science import compile_study
from metacraft.science.metalens.design import require_metalens_design
from metacraft.science.metalens.height import (
    HeightDomain,
)
from metacraft.science.metalens.period import (
    PeriodDomain,
)
from tests.domain_fixtures import height_domain, period_domain


def test_height_domain_keeps_exact_ceilings_and_a_strict_period_limit(
    tmp_path: Path,
) -> None:
    """
    Keep both physical ceilings exact on the period domain and the selected
    G0 period carried by the height domain below them.
    """

    authority = Authority(tmp_path / "authority")
    study_355 = compile_study(
        replace(long_focus_propagation_brief(), aperture=None)
    )
    study_400 = compile_study(propagation_brief())

    period_355 = period_domain(
        study_355,
        substrate_index="1.48",
    )
    period_400 = period_domain(
        study_400,
        substrate_index="1.47",
    )
    domain_355 = height_domain(
        study_355,
        substrate_index="1.48",
    )
    domain_400 = height_domain(
        study_400,
        substrate_index="1.47",
    )

    assert require_metalens_design(study_355).sampling_ceiling_nm == Decimal(
        "633.9285714285714285714285714"
    )
    assert require_metalens_design(study_400).sampling_ceiling_nm == Decimal(
        "666.6666666666666666666666667"
    )
    assert period_355.order_ceiling_nm == Decimal(
        "201.7045454545454545454545455"
    )
    assert period_400.order_ceiling_nm == Decimal(
        "225.9887005649717514124293785"
    )
    assert period_355.period_limit_nm == 630
    assert period_400.period_limit_nm == 660
    assert domain_355.period_nm == 200
    assert domain_400.period_nm == 220
    assert domain_355.order_regime == "zeroth order"
    assert domain_400.order_regime == "zeroth order"
    assert domain_355.cautions == ()
    assert domain_355.dimension_step_nm == 10

    decision = authority.decide(
        Proposal.record(domain_355.document()),
        at=authority.view().revision,
    )
    assert decision.admitted and decision.body_reference is not None
    restored = HeightDomain.from_document(
        domain_355.document(),
        evidence_reference=decision.body_reference,
    )
    assert restored.document().to_bytes() == domain_355.document().to_bytes()
    assert restored.material_binding_reference == (
        domain_355.material_binding_reference
    )
    assert restored.material_sample_reference == (
        domain_355.material_sample_reference
    )

    period_decision = authority.decide(
        Proposal.record(period_355.document()),
        at=authority.view().revision,
    )
    assert (
        period_decision.admitted
        and period_decision.body_reference is not None
    )
    restored_period = PeriodDomain.from_document(
        period_355.document(),
        evidence_reference=period_decision.body_reference,
    )
    assert (
        restored_period.document().to_bytes()
        == period_355.document().to_bytes()
    )
