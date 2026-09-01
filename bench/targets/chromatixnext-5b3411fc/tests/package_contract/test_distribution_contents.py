from __future__ import annotations

from collections.abc import Iterator
import importlib.util
from pathlib import Path
import tarfile
import tempfile
from typing import TypedDict
import zipfile

import pytest

from tests.package_contract._installed_package import (
    build_release,
    copy_installable_project_tree,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 源码分发包随产品携带完整的活跃 ADR 闭集；集合成员由当前决议文件名确定
DURABLE_ADR_FILES: frozenset[str] = frozenset(
    {
        "0001-one-pytorch-optical-core.md",
        "0002-component-and-assembly-composition.md",
        "0003-optics-numerics-workstation-boundary.md",
        "0004-example-owned-research-workflows.md",
        "0005-fixed-double-scientific-core.md",
        "0006-state-installation-and-immutable-hosting.md",
        "0007-mixed-independent-wave-ray-assembly.md",
        "0008-active-polarization-foundation.md",
        "0009-polarized-ray-foundation.md",
        "0010-exact-polarized-ray-admissibility-and-closure.md",
        "0011-assembly-topology-contract.md",
        "0012-sonnet-combination-and-evidence-contract.md",
        "0013-ssrhm-exact-topology-and-plane-local-correction.md",
        "0014-ssrhm-conic-and-sampled-wave-deepening.md",
        "0015-ssrhm-tangent-pose-migration.md",
        "0016-paraxial-ray-transfer-vocabulary-cutover.md",
    }
)

EXAMPLE_NAMES = (
    "minimal_optical_path",
    "basic_plane_wave_intensity",
    "basic_ideal_lens_focusing",
    "propagation_scalar_angular_spectrum",
    "analytic_michelson_interferometer",
)

EXPECTED_RUNTIME_PACKAGE_FILES = frozenset(
    """chromatix_next/__init__.py
chromatix_next/_execution_memory.py
chromatix_next/_numerics/__init__.py
chromatix_next/_numerics/_certified_predicates.py
chromatix_next/_numerics/_exact_binary64_sign.py
chromatix_next/_numerics/aperture.py
chromatix_next/_numerics/collimated_ray_source.py
chromatix_next/_numerics/complex_phase.py
chromatix_next/_numerics/cube_response.py
chromatix_next/_numerics/gaussian_beam.py
chromatix_next/_numerics/intensity.py
chromatix_next/_numerics/jones_calculus.py
chromatix_next/_numerics/optical_path_reference.py
chromatix_next/_numerics/plane_wave.py
chromatix_next/_numerics/point_source.py
chromatix_next/_numerics/ray_polarization.py
chromatix_next/_numerics/reflection.py
chromatix_next/_numerics/refraction.py
chromatix_next/_numerics/spatial_sampling.py
chromatix_next/_numerics/thin_transmission.py
chromatix_next/_numerics/wave_propagation/__init__.py
chromatix_next/_numerics/wave_propagation/aplanatic_focus.py
chromatix_next/_numerics/wave_propagation/chirp_z_transform.py
chromatix_next/_numerics/wave_propagation/fresnel_transform.py
chromatix_next/_numerics/wave_propagation/radiative_spectrum.py
chromatix_next/_numerics/wave_propagation/scalable_angular_spectrum.py
chromatix_next/_numerics/wave_propagation/scalar_angular_spectrum.py
chromatix_next/_numerics/wave_propagation/scaled_angular_spectrum.py
chromatix_next/_numerics/wave_propagation/scaled_fresnel.py
chromatix_next/_numerics/wave_propagation/spatial_frequency.py
chromatix_next/_numerics/wave_propagation/vector_angular_spectrum.py
chromatix_next/_numerics/wave_number.py
chromatix_next/_numerics/surface_geometry/__init__.py
chromatix_next/_numerics/surface_geometry/base_conic_roots.py
chromatix_next/_numerics/surface_geometry/conic.py
chromatix_next/_numerics/surface_geometry/conic_geometry.py
chromatix_next/_numerics/surface_geometry/conic_root_proof.py
chromatix_next/_numerics/surface_geometry/encounter.py
chromatix_next/_numerics/surface_geometry/plane.py
chromatix_next/_numerics/surface_geometry/polynomial_conic_roots.py
chromatix_next/_numerics/surface_geometry/sphere.py
chromatix_next/_ownership.py
chromatix_next/_state_installation.py
chromatix_next/_tensors.py
chromatix_next/errors.py
chromatix_next/optics/__init__.py
chromatix_next/optics/_assembly_facts.py
chromatix_next/optics/_assembly_replay.py
chromatix_next/optics/_coherence.py
chromatix_next/optics/_grid_state.py
chromatix_next/optics/_meta_inference.py
chromatix_next/optics/_mirror_directional.py
chromatix_next/optics/_orthonormal_basis.py
chromatix_next/optics/_ray_directional.py
chromatix_next/optics/_ray_surface_advance.py
chromatix_next/optics/_role_contract.py
chromatix_next/optics/_route_geometry.py
chromatix_next/optics/_sampled_wave_synthesis.py
chromatix_next/optics/_source_lifecycle.py
chromatix_next/optics/_wave_directional.py
chromatix_next/optics/paraxial_ray_transfer.py
chromatix_next/optics/assembly.py
chromatix_next/optics/combination/__init__.py
chromatix_next/optics/combination/coherent_combination.py
chromatix_next/optics/combination/intensity_combination.py
chromatix_next/optics/combination/role.py
chromatix_next/optics/detection/__init__.py
chromatix_next/optics/detection/intensity_detection.py
chromatix_next/optics/detection/role.py
chromatix_next/optics/element/__init__.py
chromatix_next/optics/element/_directional_geometry.py
chromatix_next/optics/element/amplitude_transmission.py
chromatix_next/optics/element/ideal_cube_beam_splitter.py
chromatix_next/optics/element/ideal_planar_mirror.py
chromatix_next/optics/element/ideal_thin_lens.py
chromatix_next/optics/element/optical_path_modulation.py
chromatix_next/optics/element/pupil.py
chromatix_next/optics/element/reflect_at.py
chromatix_next/optics/element/refract_at.py
chromatix_next/optics/element/retarder.py
chromatix_next/optics/element/retarder_at.py
chromatix_next/optics/element/role.py
chromatix_next/optics/field.py
chromatix_next/optics/grid.py
chromatix_next/optics/intensity.py
chromatix_next/optics/medium.py
chromatix_next/optics/polarization.py
chromatix_next/optics/propagation/__init__.py
chromatix_next/optics/propagation/_field_state.py
chromatix_next/optics/propagation/aplanatic_focus.py
chromatix_next/optics/propagation/fresnel_transform.py
chromatix_next/optics/propagation/role.py
chromatix_next/optics/propagation/scalable_angular_spectrum.py
chromatix_next/optics/propagation/scalar_angular_spectrum.py
chromatix_next/optics/propagation/scaled_angular_spectrum.py
chromatix_next/optics/propagation/scaled_fresnel.py
chromatix_next/optics/propagation/trace_to.py
chromatix_next/optics/propagation/vector_angular_spectrum.py
chromatix_next/optics/ray_bundle.py
chromatix_next/optics/source/__init__.py
chromatix_next/optics/source/collimated_ray.py
chromatix_next/optics/source/gaussian_beam.py
chromatix_next/optics/source/plane_wave.py
chromatix_next/optics/source/point_source.py
chromatix_next/optics/source/role.py
chromatix_next/optics/spectrum.py
chromatix_next/optics/surface/__init__.py
chromatix_next/optics/surface/_pose_state.py
chromatix_next/optics/surface/conic.py
chromatix_next/optics/surface/plane.py
chromatix_next/optics/surface/sphere.py
chromatix_next/release.toml
chromatix_next/workstation.py""".splitlines()
)
EXPECTED_WHEEL_METADATA_FILES = frozenset(
    {
        "chromatix_next-0.0.0.dist-info/METADATA",
        "chromatix_next-0.0.0.dist-info/RECORD",
        "chromatix_next-0.0.0.dist-info/WHEEL",
        "chromatix_next-0.0.0.dist-info/top_level.txt",
    }
)
EXPECTED_SDIST_ROOT_FILES = frozenset(
    {
        "CONTEXT.md",
        "MANIFEST.in",
        "MISSION.md",
        "PKG-INFO",
        "README.md",
        "README.zh-CN.md",
        "docs/architecture.md",
        "docs/history.md",
        "examples/README.md",
        "examples/README.zh-CN.md",
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "src/chromatix_next.egg-info/PKG-INFO",
        "src/chromatix_next.egg-info/SOURCES.txt",
        "src/chromatix_next.egg-info/dependency_links.txt",
        "src/chromatix_next.egg-info/requires.txt",
        "src/chromatix_next.egg-info/top_level.txt",
    }
)
EXPECTED_SDIST_ADR_FILES = frozenset(
    f"docs/adr/{filename}" for filename in DURABLE_ADR_FILES
)
EXPECTED_SDIST_EXAMPLE_FILES = frozenset(
    f"examples/{example_name}/{filename}"
    for example_name in EXAMPLE_NAMES
    for filename in ("README.md", "README.zh-CN.md", "example.py")
)
EXPECTED_SDIST_FILES = (
    EXPECTED_SDIST_ROOT_FILES
    | EXPECTED_SDIST_ADR_FILES
    | EXPECTED_SDIST_EXAMPLE_FILES
    | frozenset(f"src/{path}" for path in EXPECTED_RUNTIME_PACKAGE_FILES)
)


class BuiltDistributions(TypedDict):
    """
    保存临时构建的两种发布产物路径
    """

    wheel: Path
    source: Path


@pytest.fixture(scope="module")
def distributions() -> Iterator[BuiltDistributions]:
    """
    在临时目录构建一次 wheel 与源码分发包
    """

    if importlib.util.find_spec("build") is None:
        pytest.fail("distribution contract requires the release build dependency")
    with tempfile.TemporaryDirectory() as temporary:
        temporary_root = Path(temporary)
        source_copy = temporary_root / "source"
        output = temporary_root / "dist"
        copy_installable_project_tree(PROJECT_ROOT, source_copy)
        artifacts = build_release(
            source_copy,
            output,
            formats=("wheel", "sdist"),
        )
        yield {
            "wheel": next(path for path in artifacts if path.suffix == ".whl"),
            "source": next(path for path in artifacts if path.name.endswith(".tar.gz")),
        }


def _wheel_names(path: Path) -> tuple[str, ...]:
    with zipfile.ZipFile(path) as archive:
        return tuple(archive.namelist())


def _source_names(path: Path) -> tuple[str, ...]:
    with tarfile.open(path) as archive:
        return tuple(
            Path(*Path(member.name).parts[1:]).as_posix()
            for member in archive.getmembers()
            if member.isfile()
        )


def _has_suffix(names: tuple[str, ...], suffix: str) -> bool:
    return any(name == suffix or name.endswith("/" + suffix) for name in names)


def test_wheel_contains_only_runtime_package_and_metadata(
    distributions: BuiltDistributions,
) -> None:
    """
    验证 wheel 仅包含运行时包与发布元数据
    """

    names = _wheel_names(distributions["wheel"])
    assert frozenset(names) == (
        EXPECTED_RUNTIME_PACKAGE_FILES | EXPECTED_WHEEL_METADATA_FILES
    )
    assert "chromatix_next/release.toml" in names
    assert "chromatix_next/workstation.py" in names
    assert "chromatix_next/optics/__init__.py" in names
    assert "chromatix_next/_numerics/__init__.py" in names
    offenders = [
        name
        for name in names
        if not name.startswith("chromatix_next/")
        and ".dist-info/" not in name
    ]
    assert offenders == []
    assert not any("/tests/" in name or "/examples/" in name for name in names)
    assert not any(
        part in name
        for name in names
        for part in (
            ".scratch",
            "tracker",
            "migration-source",
            "__pycache__",
            ".pytest_cache",
        )
    )


def test_wheel_metadata_has_no_example_only_dependency(
    distributions: BuiltDistributions,
) -> None:
    """
    验证 wheel 元数据不携带案例专用依赖
    """

    with zipfile.ZipFile(distributions["wheel"]) as archive:
        metadata_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/METADATA")
        )
        metadata = archive.read(metadata_name).decode("utf-8")
    assert "Requires-Dist: torch" in metadata
    assert "matplotlib" not in metadata
    assert "Extra: examples" not in metadata


def test_source_distribution_contains_five_paired_examples(
    distributions: BuiltDistributions,
) -> None:
    """
    验证源码分发包包含五个中英文成对案例
    """

    names = _source_names(distributions["source"])
    assert frozenset(names) == EXPECTED_SDIST_FILES
    assert _has_suffix(names, "examples/README.md")
    assert _has_suffix(names, "examples/README.zh-CN.md")
    for example_name in EXAMPLE_NAMES:
        for filename in ("example.py", "README.md", "README.zh-CN.md"):
            assert _has_suffix(
                names,
                f"examples/{example_name}/{filename}",
            )


def test_source_distribution_contains_active_architecture_documents(
    distributions: BuiltDistributions,
) -> None:
    """
    验证源码分发包包含活跃架构文档与冻结 ADR 闭集
    """

    names = _source_names(distributions["source"])
    for filename in (
        "CONTEXT.md",
        "MISSION.md",
        "README.md",
        "README.zh-CN.md",
        "docs/architecture.md",
        "docs/history.md",
    ):
        assert _has_suffix(names, filename)
    adr_names = {
        name.rsplit("/", 1)[-1]
        for name in names
        if (
            name.startswith("docs/adr/")
            or "/docs/adr/" in name
        )
        and name.endswith(".md")
    }
    assert adr_names == DURABLE_ADR_FILES, (
        f"sdist ADR set must match the frozen durable ADR set exactly. "
        f"expected={sorted(DURABLE_ADR_FILES)} actual={sorted(adr_names)}"
    )


def test_source_distribution_excludes_inactive_and_generated_content(
    distributions: BuiltDistributions,
) -> None:
    """
    验证源码分发包排除失效与生成内容
    """

    names = _source_names(distributions["source"])
    forbidden_parts = (
        "/tests/",
        "/.scratch/",
        "/reference/",
        "/migration-source/",
        "/tracker/",
        "/__pycache__/",
        "/.pytest_cache/",
        "/lessons/",
        "/learning-records/",
        "/scenarios/",
        "/assets/",
        ".pyc",
        ".yaml",
        ".yml",
        ".png",
        ".csv",
        ".json",
    )
    offenders = [
        name
        for name in names
        if any(part in name for part in forbidden_parts)
    ]
    assert offenders == []


def test_distribution_version_comes_from_the_release_descriptor(
    distributions: BuiltDistributions,
) -> None:
    """
    wheel 与 sdist 的版本均由 Release Descriptor 投影为 0.0.0
    """

    assert "-0.0.0-" in distributions["wheel"].name
    assert distributions["source"].name.endswith("-0.0.0.tar.gz")
    with zipfile.ZipFile(distributions["wheel"]) as archive:
        metadata_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/METADATA")
        )
        metadata = archive.read(metadata_name).decode("utf-8")
    assert "Version: 0.0.0" in metadata
