from dataclasses import replace
from decimal import Decimal

import pytest

from tests.brief_fixtures import geometric_brief, propagation_brief
from metacraft.science import compile_study
from metacraft.science.metalens import (
    ControlStrategy,
    require_metalens_design,
)


def test_control_strategy_compiles_one_supported_propagation_route() -> None:
    """
    One supported propagation brief compiles without a derived regime label.
    """

    brief = propagation_brief().replace_numerical_aperture("0.50")
    study = compile_study(brief)

    assert brief.control_strategy is ControlStrategy.PROPAGATION_PHASE
    design = require_metalens_design(study)
    assert design.control_strategy is (
        ControlStrategy.PROPAGATION_PHASE
    )
    assert design.numerical_aperture == Decimal("0.50")
    assert not hasattr(design, "aperture_regime")
    assert "propagation phase" in study.route.applicability
    assert "numerical aperture: at most 0.5" in (
        study.route.applicability
    )
    assert study.route.identity.startswith("sha256:")


@pytest.mark.parametrize(
    "control_strategy",
    (
        ControlStrategy.PROPAGATION_PHASE,
        ControlStrategy.GEOMETRIC_PHASE,
    ),
)
def test_high_na_metalens_selects_one_pointwise_route(
    control_strategy: ControlStrategy,
) -> None:
    """
    Both current strategies select their qualified pointwise relationship.
    """

    if control_strategy is ControlStrategy.PROPAGATION_PHASE:
        base = propagation_brief()
    else:
        base = geometric_brief()
    brief = replace(
        base,
        wording=f"Design a high-NA {control_strategy.value} metalens.",
        numerical_aperture=base.numerical_aperture.__class__("0.70"),
    )

    study = compile_study(brief)
    obligations = {
        obligation.name for obligation in study.proof.claims
    }

    assert study.route.applicability == (
        f"declared control strategy: {control_strategy.value}; "
        "numerical aperture: above 0.5 and below 1"
    )
    assert "focal_comparison" in obligations
    if control_strategy is ControlStrategy.PROPAGATION_PHASE:
        assert "cell_surface_table" in obligations
        assert "phase_set" not in obligations
    else:
        assert "geometric_surface_transform" in obligations
        assert "orientation_set" not in obligations
    assert brief.numerical_aperture == Decimal("0.70")
