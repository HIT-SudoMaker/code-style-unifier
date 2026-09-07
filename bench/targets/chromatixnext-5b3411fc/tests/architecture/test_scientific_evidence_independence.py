from __future__ import annotations

from pathlib import Path

from tests.architecture._python_import_facts import read_python_imports

# 清单命名独立科学证据所有者，而不是测试用例



PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = PROJECT_ROOT / "tests"

ORACLE_PATHS: tuple[str, ...] = (
    "source/test_source_polarization_authoring.py",
    "element/test_retarder.py",
    "element/test_polarization_rejection_consistency.py",
    "element/test_polarization_neutrality.py",
    "element/test_directional_owner_geometry.py",
    "propagation/test_polarization_applicability.py",
    "propagation/test_polarization_rejection_consistency.py",
    "combination/test_combination.py",
    "detection/test_intensity_detection.py",
    "assembly/test_polarization_composition.py",
    "optics/test_polarized_ray_admission_boundaries.py",
    "optics/test_polarized_ray_transport_chain.py",
    "qualification/test_cube_oracles.py",
)
FORBIDDEN_NUMERICS_PREFIX = "chromatix_next._numerics"
FORBIDDEN_RAY_BUNDLE_TARGETS = frozenset(
    f"chromatix_next.optics.ray_bundle.{name}"
    for name in (
        "_DIRECTION_SQUARED_NORM_BUDGET",
        "_POLARIZATION_NORM_SQUARED_BUDGET",
        "_TRANSVERSALITY_SCALE_FACTOR",
        "_RAY_GAMMA_5",
        "_RAY_GAMMA_11",
        "_RAY_UNIT_ROUND_OFF",
    )
)
RAY_ADMISSION_ORACLE_PATHS = frozenset(
    {
        "optics/test_polarized_ray_admission_boundaries.py",
        "optics/test_polarized_ray_transport_chain.py",
    },
)


def test_wave_and_ray_oracles_are_present_and_independent() -> None:
    """
    全部 Wave/Ray oracle 存在且不从生产数值所有者派生期望值
    """

    failures: list[str] = []
    for relative_path in ORACLE_PATHS:
        path = TEST_ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing oracle: {relative_path}")
            continue
        facts = read_python_imports(path, PROJECT_ROOT)
        forbidden_modules = sorted(
            module_name
            for module_name in facts.imported_modules
            if (
                module_name == FORBIDDEN_NUMERICS_PREFIX
                or module_name.startswith(FORBIDDEN_NUMERICS_PREFIX + ".")
            )
        )
        if forbidden_modules:
            failures.append(
                f"{relative_path} imports production numerics "
                f"{forbidden_modules}",
            )
        leaked_targets = sorted(
            facts.imported_targets & FORBIDDEN_RAY_BUNDLE_TARGETS,
        )
        if leaked_targets:
            failures.append(
                f"{relative_path} imports production admission constants "
                f"{leaked_targets}",
            )
        if relative_path in RAY_ADMISSION_ORACLE_PATHS:
            source = path.read_text(encoding="utf-8")
            if "2.0 ** -53" not in source:
                failures.append(
                    f"{relative_path} does not derive binary64 round-off "
                    "from the ADR formula",
                )

    assert not failures, "; ".join(failures)
