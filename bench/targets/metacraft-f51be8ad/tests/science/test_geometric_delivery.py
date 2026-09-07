from decimal import Decimal

from examples import (
    select_metalens_benchmark_case,
)
from examples.metalens_benchmark.contract import ReferenceFactName
from metacraft.science.metalens.aperture import Ellipse, Rectangle
from metacraft.science.metalens.brief import (
    ApertureExtent,
    ApertureFootprint,
    ControlStrategy,
    require_monochromatic_wavelength,
)
from metacraft.science.metalens.periodic_request import (
    PeriodicCellCandidate,
)
from metacraft.science.periodic_response import (
    EllipticalCrossSection,
    RectangularCrossSection,
)


def test_public_geometric_briefs_keep_their_exact_reproduction_facts() -> None:
    khorasaninejad = select_metalens_benchmark_case(
        "khorasaninejad-2016-high-na-geometric"
    )
    yang = select_metalens_benchmark_case("yang-2018-low-na-geometric")

    assert (
        require_monochromatic_wavelength(khorasaninejad.brief.operating_spectrum),
        khorasaninejad.brief.numerical_aperture,
        khorasaninejad.brief.focal_length_um,
        khorasaninejad.brief.control_strategy,
        khorasaninejad.brief.atom.shape,
        khorasaninejad.brief.dimension_step_nm,
    ) == (
        532,
        Decimal("0.8"),
        Decimal("90"),
        ControlStrategy.GEOMETRIC_PHASE,
        Rectangle(80, 160).shape,
        10,
    )
    assert (
        require_monochromatic_wavelength(yang.brief.operating_spectrum),
        yang.brief.numerical_aperture,
        yang.brief.focal_length_um,
        yang.brief.control_strategy,
        yang.brief.atom.shape,
        yang.brief.dimension_step_nm,
    ) == (
        1550,
        Decimal("0.32"),
        Decimal("30"),
        ControlStrategy.GEOMETRIC_PHASE,
        Ellipse(100, 200).shape,
        10,
    )
    assert yang.brief.aperture is not None
    assert (
        yang.brief.aperture.site_count,
        yang.brief.aperture.extent,
        yang.brief.aperture.footprint,
    ) == (
        15,
        ApertureExtent.DIAMETER,
        ApertureFootprint.SQUARE,
    )
    for case in (khorasaninejad, yang):
        brief = case.brief
        assert brief.aspect_limit == 8
        assert brief.solver_preference == "lumerical_fdtd"
        assert brief.budget == "workstation"
        assert brief.omissions[-2:] == ("multiwavelength", "optimization")
        assert brief.cell_period_nm is None
        assert brief.atom_height_nm is None
        assert case.reference.fact(ReferenceFactName.CELL_PERIOD).value is not None
        assert case.reference.fact(ReferenceFactName.ATOM_HEIGHT).value is not None
    assert "paper-selected cell geometry" in khorasaninejad.brief.omissions


def test_geometric_candidates_retain_their_typed_geometry() -> None:
    rectangle = PeriodicCellCandidate(
        height_nm=600,
        geometry=RectangularCrossSection(80, 160),
    )
    ellipse = PeriodicCellCandidate(
        height_nm=900,
        geometry=EllipticalCrossSection(100, 300),
    )

    assert rectangle.shape == "rectangular fin"
    assert rectangle.maximum_dimension_nm == 160
    assert rectangle.minimum_dimension_nm == 80
    assert rectangle.as_mapping()["geometry"] == {
        "length_nm": 160,
        "width_nm": 80,
    }
    assert ellipse.shape == "elliptical pillar"
    assert ellipse.maximum_dimension_nm == 300
    assert ellipse.minimum_dimension_nm == 100
    assert ellipse.as_mapping()["geometry"] == {
        "major_nm": 300,
        "minor_nm": 100,
    }
