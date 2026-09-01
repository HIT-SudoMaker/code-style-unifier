from __future__ import annotations

from functools import cache
from pathlib import Path
import re

import pytest

from metacraft.materials import SolverMaterialLibrary
from metacraft.solvers.lumerical_fdtd import (
    LumericalConfig,
    read_lumerical_environment,
)
from metacraft.solvers.lumerical_fdtd.probe import ProductProbe
from metacraft.solvers.lumerical_fdtd.qualification import qualify
from metacraft.workstation import Demand, plan
from tests.lumerical_fixtures import fixed_planner
from tests.solver_fakes import FakeProbe


GIBIBYTE = 1024**3
pytestmark = pytest.mark.lumerical_live


@cache
def _configured() -> tuple[LumericalConfig, bool]:
    root = Path(__file__).parents[2]
    path = root / ".env.lumerical"
    if not path.is_file():
        pytest.skip(".env.lumerical is absent")
    environment = read_lumerical_environment(path)
    if environment.get("METACRAFT_RUN_LUMERICAL_SMOKE") != "1":
        pytest.skip("live Lumerical smoke is disabled")
    config = LumericalConfig.from_environ(environment)
    should_hide = environment.get("METACRAFT_LUMERICAL_HEADLESS", "1") == "1"
    return config, should_hide


@cache
def _qualified_installation():
    config, should_hide = _configured()
    probe = ProductProbe()
    facts = probe.observe(config)
    layout = plan(
        Demand(
            workers=min(
                facts.lumerical_gui_limit,
                facts.lumerical_solve_limit,
            ),
            worker_memory_bytes=16 * GIBIBYTE,
        )
    )
    qualification = qualify(
        config,
        FakeProbe(facts),
        planner=fixed_planner(layout),
    )
    return config, facts, qualification, should_hide


@cache
def _registered_materials() -> SolverMaterialLibrary:
    root = Path(__file__).parents[2]
    return SolverMaterialLibrary.decode_bytes(
        (root / "materials" / "lumerical.toml").read_bytes()
    )


def _native_names(families: tuple[str, ...]) -> dict[str, str]:
    library = _registered_materials()
    return {
        family: library.select(family).native_name for family in dict.fromkeys(families)
    }


def test_configured_installation_is_lumerical_25v2() -> None:
    config, _ = _configured()

    assert config.executable is not None
    assert config.executable.is_file()
    assert "v252" in {part.casefold() for part in config.executable.resolve().parts}
    assert config.python_api is not None
    assert config.python_api.is_file()


def test_installed_license_reports_positive_capacity() -> None:
    config, facts, _, _ = _qualified_installation()

    assert facts.lumerical_gui_limit > 0
    assert facts.lumerical_solve_limit > 0
    assert config.license_server is not None
    version = facts.product_version.casefold()
    assert (
        "2025 r2" in version
        or re.search(r"\b25[.]?2\b", version)
        or version.startswith("8.34.")
    )


def test_installed_materials_are_read_back() -> None:
    config, _, _, _ = _qualified_installation()
    catalogue = _native_names(("silicon nitride", "silica"))
    sample, _activity = ProductProbe().sample_materials(
        config,
        catalogue,
        400,
    )

    assert set(sample.materials) == {"silica", "silicon nitride"}
    assert all(
        tuple(point.wavelength_nm for point in material.points) == (400,)
        and not material.findings
        for material in sample.materials.values()
    )


def test_installation_without_response_proof_remains_unavailable() -> None:
    config, facts, qualification, _ = _qualified_installation()

    assert config.executable is not None
    assert config.python_api is not None
    assert facts.product_version
    assert qualification.binding is None
    assert qualification.capacity is None
    assert qualification.findings == ("solver_execution_unverified",)
