from decimal import Decimal

import examples
from examples import (
    select_metalens_benchmark_case,
)
from metacraft.science import (
    Study,
    compile_study,
)
from metacraft.science.metalens import ControlStrategy
from metacraft.science.metalens.brief import require_monochromatic_wavelength


def test_propagation_examples_keep_geometry_open_after_material_adaptation() -> None:
    """
    Keep both target-near briefs open to MetaCraft's own cell answer.
    """

    mcclung = select_metalens_benchmark_case("mcclung-2024-low-na-propagation")
    arbabi = select_metalens_benchmark_case("arbabi-2015-high-na-propagation")

    assert (
        require_monochromatic_wavelength(mcclung.brief.operating_spectrum),
        mcclung.brief.numerical_aperture,
        mcclung.brief.focal_length_um,
        mcclung.brief.atom.shape,
        mcclung.brief.atom.material.family,
        mcclung.brief.substrate.family,
        mcclung.brief.dimension_step_nm,
    ) == (
        550,
        Decimal("0.20"),
        Decimal("200"),
        "circular pillar",
        "silicon nitride",
        "fused silica",
        10,
    )
    assert (
        require_monochromatic_wavelength(arbabi.brief.operating_spectrum),
        arbabi.brief.numerical_aperture,
        arbabi.brief.focal_length_um,
        arbabi.brief.atom.shape,
        arbabi.brief.atom.material.family,
        arbabi.brief.substrate.family,
        arbabi.brief.dimension_step_nm,
    ) == (
        1550,
        Decimal("0.89"),
        Decimal("25"),
        "circular pillar",
        "silicon",
        "fused silica",
        10,
    )
    assert mcclung.brief.aspect_limit == 8
    assert arbabi.brief.aspect_limit == 8
    for case in (mcclung, arbabi):
        brief = case.brief
        assert brief.control_strategy is ControlStrategy.PROPAGATION_PHASE
        assert brief.incident_polarization.kind == "linear"
        assert brief.incident_polarization.axis == "x"
        assert brief.solver_preference == "lumerical_fdtd"
        assert brief.budget == "workstation"
        assert brief.omissions[-2:] == ("multiwavelength", "optimization")
        assert brief.cell_period_nm is None
        assert brief.atom_height_nm is None
        assert brief.aperture is None
    assert "complete single-mode-fibre incident field" in arbabi.brief.omissions
    study = compile_study(mcclung.brief)
    assert "propagation phase" in study.route.applicability
    assert tuple((task.claim, task.method) for task in study.ready_tasks) == (
        ("target_phase", "derive_target_phase"),
    )


def test_only_benchmark_cases_are_public_examples() -> None:
    """
    Keep historical test tracers out of the public examples interface.
    """

    assert examples.__all__ == [
        "MetalensBenchmarkCase",
        "metalens_benchmark_cases",
        "select_metalens_benchmark_case",
    ]
