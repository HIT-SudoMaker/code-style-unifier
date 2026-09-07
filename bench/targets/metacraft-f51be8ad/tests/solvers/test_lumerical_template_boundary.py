import ast
from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import metacraft.science as science
import metacraft.solvers.lumerical_fdtd as lumerical
import metacraft.solvers.lumerical_fdtd.template as template
import pytest

from metacraft.authority.reference import reference_for
from metacraft.science.periodic_response import (
    CircularCrossSection,
    PeriodicMaterials,
    PeriodicWork,
)
from tests.solver_fakes import ActiveEngines, FakeSession


ROOT = Path(__file__).parents[2]
SOLVER = ROOT / "src" / "metacraft" / "solvers" / "lumerical_fdtd"


def _periodic_work(
    *,
    wavelength_nm: int,
    height_nm: int,
) -> PeriodicWork:
    atom = reference_for(b"template atom")
    substrate = reference_for(b"template substrate")
    return PeriodicWork(
        cell_identity=(
            f"circular-pillar-height-{height_nm:04d}nm-diameter-0200nm"
        ),
        work_identity=f"sha256:template-{wavelength_nm}-{height_nm}",
        observation_schema="fixture.periodic.transmission",
        wavelength_nm=wavelength_nm,
        period_nm=660,
        height_nm=height_nm,
        geometry=CircularCrossSection(diameter_nm=200),
        materials=PeriodicMaterials(
            atom_native_identity="Si (Silicon) - Palik",
            atom_refractive_index=Decimal("3.48"),
            atom_source_reference=atom,
            substrate_native_identity="SiO2 (Glass) - Palik",
            substrate_refractive_index=Decimal("1.45"),
            substrate_source_reference=substrate,
        ),
        source_references=(atom, substrate),
        binding_reference=reference_for(b"template binding"),
        capacity_scope="solver:fixture",
        input_basis="x linear",
        output_basis="transverse linear",
        order_regime="zeroth order",
    )


def test_template_exposes_one_route_neutral_construction() -> None:
    """
    Keep product constructions distinct from scientific fabrication cells.
    """

    assert not (SOLVER / "cell.py").exists()
    construction = template.prepare_periodic_construction(
        _periodic_work(wavelength_nm=1_550, height_nm=800)
    )

    assert construction.__class__.__name__ == "PeriodicConstruction"
    assert template.PeriodicConstruction.__name__ == "PeriodicConstruction"
    assert not hasattr(template, "PeriodicResponseLayout")
    assert not hasattr(science, "PropagationConstruction")
    assert not hasattr(science, "GeometricConstruction")
    for retired_name in (
        "GeometricConstruction",
        "GratingFrame",
        "PropagationConstruction",
        "build_geometric",
        "build_propagation",
        "polarization_construction",
        "transmission_construction",
    ):
        assert not hasattr(template, retired_name)


def test_response_template_leaves_resonant_cells_time_to_reach_autoshutoff(
) -> None:
    construction = template.prepare_periodic_construction(
        _periodic_work(wavelength_nm=1_550, height_nm=900)
    )

    assert construction.mesh_accuracy == 4
    assert construction.time_budget.ordinary_maximum_fs == 2_000
    assert construction.time_budget.extended_maximum_fs == 4_000
    assert construction.time_budget.causal_floor_fs == 300


def test_response_time_budget_keeps_visible_work_on_the_shorter_tier() -> None:
    construction = template.prepare_periodic_construction(
        _periodic_work(wavelength_nm=405, height_nm=650)
    )

    assert construction.time_budget.ordinary_maximum_fs == 1_000
    assert construction.time_budget.extended_maximum_fs == 2_000
    assert construction.time_budget.causal_floor_fs == 200


@pytest.mark.parametrize(
    (
        "wavelength_nm",
        "height_nm",
        "expected_layout",
    ),
    (
        (
            400,
            500,
            {
                "atom_lower_z_nm": 0,
                "atom_upper_z_nm": 500,
                "period_nm": 660,
                "reference_plane_offset_nm": 100,
                "reflection_plane_z_nm": -900,
                "solver_lower_z_nm": -1_100,
                "solver_upper_z_nm": 700,
                "source_plane_z_nm": -1_000,
                "substrate_height_nm": 2_000,
                "substrate_interface_z_nm": 0,
                "transmission_plane_z_nm": 600,
                "wavelength_nm": 400,
            },
        ),
        (
            1_550,
            800,
            {
                "atom_lower_z_nm": 0,
                "atom_upper_z_nm": 800,
                "period_nm": 660,
                "reference_plane_offset_nm": 100,
                "reflection_plane_z_nm": -900,
                "solver_lower_z_nm": -1_100,
                "solver_upper_z_nm": 1_600,
                "source_plane_z_nm": -1_000,
                "substrate_height_nm": 2_000,
                "substrate_interface_z_nm": 0,
                "transmission_plane_z_nm": 1_500,
                "wavelength_nm": 1_550,
            },
        ),
        (
            2_050,
            800,
            {
                "atom_lower_z_nm": 0,
                "atom_upper_z_nm": 800,
                "period_nm": 660,
                "reference_plane_offset_nm": 100,
                "reflection_plane_z_nm": -1_000,
                "solver_lower_z_nm": -1_200,
                "solver_upper_z_nm": 1_900,
                "source_plane_z_nm": -1_100,
                "substrate_height_nm": 2_100,
                "substrate_interface_z_nm": 0,
                "transmission_plane_z_nm": 1_800,
                "wavelength_nm": 2_050,
            },
        ),
    ),
)
def test_periodic_response_layout_uses_the_approved_outward_coverage(
    wavelength_nm: int,
    height_nm: int,
    expected_layout: dict[str, int],
) -> None:
    construction = template.prepare_periodic_construction(
        _periodic_work(
            wavelength_nm=wavelength_nm,
            height_nm=height_nm,
        )
    )

    assert construction.layout.as_mapping() == expected_layout


def test_odd_atom_height_keeps_its_exact_half_nanometre_center() -> None:
    construction = template.prepare_periodic_construction(
        _periodic_work(wavelength_nm=1_551, height_nm=801)
    )
    session = FakeSession(active=ActiveEngines(), result={})

    manifest = construction.build_in(session)

    assert manifest.mismatches == ()
    assert session.read(
        "grating_response",
        ("meta_atom_center_nm",),
    ) == {"meta_atom_center_nm": 400.5}


def test_off_grid_meta_atom_center_remains_a_build_translation_mismatch(
) -> None:
    class OffGridCenterSession(FakeSession):
        def read(
            self,
            name: str,
            properties: tuple[str, ...],
        ) -> Mapping[str, Any]:
            observed = dict(super().read(name, properties))
            if name == "grating_response":
                observed["meta_atom_center_nm"] = 400.6
            return observed

    construction = template.prepare_periodic_construction(
        _periodic_work(wavelength_nm=1_551, height_nm=801)
    )
    session = OffGridCenterSession(active=ActiveEngines(), result={})

    manifest = construction.build_in(session)

    assert manifest.mismatches == ("grating_response.translation",)


def test_periodic_construction_rejects_a_forged_valid_layout() -> None:
    construction = template.prepare_periodic_construction(
        _periodic_work(wavelength_nm=1_550, height_nm=800)
    )
    forged_layout = replace(
        construction.layout,
        substrate_height_nm=2_200,
        solver_lower_z_nm=-1_200,
        source_plane_z_nm=-1_100,
        reflection_plane_z_nm=-1_000,
    )

    with pytest.raises(
        ValueError,
        match="periodic_construction_layout_mismatch",
    ):
        replace(construction, layout=forged_layout)


def test_production_contains_no_test_adapters_or_retired_incident_name() -> None:
    """
    Keep test adapters and the retired source-basis term out of production.
    """

    found: dict[str, set[str]] = {}
    retired = {
        "ActiveEngines",
        "FakeProbe",
        "FakeSession",
        "FakeSessionFactory",
        "fit_fmax_hz",
        "fit_fmin_hz",
        "source_basis",
        "tabulated_fmax_hz",
        "tabulated_fmin_hz",
    }
    for path in SOLVER.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
        }
        overlap = names & retired
        if overlap:
            found[path.relative_to(SOLVER).as_posix()] = overlap

    assert found == {}


def test_native_grating_language_stays_inside_the_session() -> None:
    """
    Keep vendor spellings at the sole native translation seam.

    Every product-specific spelling introduced by the ticket-05 dialect is
    confined to ``session.py``. The set spans the structural, source, grating,
    and solver-control vocabularies so a future leak in any of them is caught
    here rather than reaching a template or caller.
    """

    native_terms = (
        "S21_Gn",
        "T_Gn",
        "grating_s_params",
        '"x span"',
        '"y span"',
        '"z span"',
        '"radius 2"',
        '"mesh accuracy"',
        '"simulation time"',
        '"source offset"',
        '"start wavelength"',
        '"stop wavelength"',
        '"source_type"',
        '"suppress_warnings"',
        '"target_grating_order_out"',
        '"use relative coordinates"',
        '"metamaterial center"',
        '"metamaterial span"',
        '"propagation axis"',
        '"propagation direction"',
    )
    found: dict[str, tuple[str, ...]] = {}
    for path in SOLVER.rglob("*.py"):
        matches = tuple(
            term
            for term in native_terms
            if term in path.read_text(encoding="utf-8-sig")
        )
        if matches:
            found[path.relative_to(SOLVER).as_posix()] = matches

    assert found == {
        "session.py": native_terms,
    }


def test_root_package_loads_only_its_declared_caller_interface() -> None:
    """
    Keep construction and product translation behind explicit submodules.
    """

    assert frozenset(lumerical.__all__) == {
        "LumericalConfig",
        "LumericalMetalensEvidence",
        "LumericalMaterialVerifier",
        "LumericalPeriodicResponse",
        "read_lumerical_environment",
    }
    assert not hasattr(lumerical, "FakeProbe")
    assert not hasattr(lumerical, "PropagationConstruction")
