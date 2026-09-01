from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

import pytest

from tests.package_contract._installed_package import (
    build_release,
    copy_installable_project_tree,
    install_wheel,
    run_isolated_python,
)
from tests.package_contract.test_public_surface import (
    EXPECTED_ACTIONS,
    EXPECTED_DIRECTIONAL_ENUMS,
    EXPECTED_DIRECTIONAL_OWNERS,
    EXPECTED_ENCOUNTER_REFERENCES,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_isolated_installed_wheel_preserves_the_public_contract() -> None:
    """
    隔离安装后的包保留根导出、动作、状态、失败与最小公开计算
    """

    if importlib.util.find_spec("build") is None:
        pytest.fail("installed-wheel contract requires the release build dependency")

    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_root = Path(temporary_directory)
        source_copy = temporary_root / "source"
        distribution_directory = temporary_root / "dist"
        target_directory = temporary_root / "target"
        copy_installable_project_tree(PROJECT_ROOT, source_copy)
        artifacts = build_release(
            source_copy,
            distribution_directory,
            formats=("wheel",),
        )
        wheel = next(path for path in artifacts if path.suffix == ".whl")
        target_directory.mkdir()
        install_wheel(wheel, target_directory)
        script = _installed_contract_script(
            target_directory=target_directory,
            checkout=PROJECT_ROOT,
            expected_actions=EXPECTED_ACTIONS,
            expected_directional_enums=EXPECTED_DIRECTIONAL_ENUMS,
            expected_directional_owners=EXPECTED_DIRECTIONAL_OWNERS,
            expected_encounter_references=EXPECTED_ENCOUNTER_REFERENCES,
        )
        completed = run_isolated_python(
            script,
            working_directory=temporary_root,
        )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr


def _installed_contract_script(
    *,
    target_directory: Path,
    checkout: Path,
    expected_actions: frozenset[str],
    expected_directional_enums: frozenset[str],
    expected_directional_owners: frozenset[str],
    expected_encounter_references: frozenset[str],
) -> str:
    return f"""
import importlib
import inspect
from pathlib import Path
import sys

target = Path({str(target_directory)!r}).resolve()
checkout = Path({str(checkout)!r}).resolve()
sys.path[:] = [str(target)] + [
    entry for entry in sys.path
    if entry
    and Path(entry).resolve() != checkout
    and checkout not in Path(entry).resolve().parents
]

import torch
import chromatix_next
from chromatix_next.errors import OpticalValueError
from chromatix_next.optics import Polarization, SpatialGrid, Spectrum, Vacuum
from chromatix_next.optics import __all__ as optics_exports
from chromatix_next.optics import combination, detection, element, propagation, source
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.source import PlaneWave

direct_paraxial_ray_transfer = importlib.import_module(
    "chromatix_next.optics.paraxial_ray_transfer"
)
assert hasattr(
    direct_paraxial_ray_transfer,
    "compose_ray_transfer_matrices",
)
try:
    importlib.import_module("chromatix_next.optics.abcd")
except ModuleNotFoundError as error:
    assert error.name == "chromatix_next.optics.abcd"
else:
    raise AssertionError("unsupported abcd module is importable")

direct_collimated_ray = importlib.import_module(
    "chromatix_next.optics.source.collimated_ray"
)
assert direct_collimated_ray.CollimatedRaySource is source.CollimatedRaySource
try:
    importlib.import_module("chromatix_next.optics.source.collimated")
except ModuleNotFoundError as error:
    assert error.name == "chromatix_next.optics.source.collimated"
else:
    raise AssertionError("unsupported collimated module is importable")

origin = Path(chromatix_next.__file__).resolve()
assert target in origin.parents
assert checkout not in origin.parents
assert chromatix_next.__all__ == ["Workstation", "install_state"]

expected_actions = {sorted(expected_actions)!r}
expected_directional_enums = {sorted(expected_directional_enums)!r}
expected_directional_owners = {sorted(expected_directional_owners)!r}
expected_encounter_references = {sorted(expected_encounter_references)!r}
packages = (source, element, propagation, combination, detection)
actual_actions = sorted(
    name
    for package in packages
    for name in package.__all__
    if inspect.isclass(getattr(package, name))
    and name not in {{
        "Source", "Element", "Propagation", "Combination", "Detection",
        "ScalarAngularSpectrumDiagnostic",
    }}
    and name not in expected_directional_owners
    and name not in expected_directional_enums
)
assert actual_actions == expected_actions
assert sorted(
    name for name in element.__all__ if name in expected_directional_owners
) == expected_directional_owners
assert sorted(
    name for name in element.__all__ if name in expected_directional_enums
) == expected_directional_enums
assert sorted(
    name for name in optics_exports if name in expected_encounter_references
) == expected_encounter_references

source_action = PlaneWave(
    spectrum=Spectrum.monochromatic(wavelength=532.0e-9),
    polarization=Polarization.linear_x(),
    medium=Vacuum(),
    propagation_direction=(__import__(
        "chromatix_next.optics", fromlist=["PropagationDirection"]
    ).PropagationDirection.forward()),
    relative_amplitude=1.0,
)
assert "polarization_state" in source_action.state_dict()
try:
    SpatialGrid.centered(sample_counts=(0, 2), sample_spacing=(1.0, 1.0))
except OpticalValueError as error:
    assert error.identity == "spatial_grid_sample_counts_invalid"
else:
    raise AssertionError("invalid grid did not fail")

grid = SpatialGrid.centered(
    sample_counts=(2, 2),
    sample_spacing=(1.0e-6, 1.0e-6),
)
intensity = IntensityDetection()(source_action(grid))
assert intensity.values.shape == (2, 2)
assert intensity.values.dtype is torch.float64
"""
