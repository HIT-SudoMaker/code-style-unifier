from __future__ import annotations

import ast
from pathlib import Path


RESTORATION_ROOT = Path(__file__).resolve().parents[2] / "experiments" / "restoration"
SHARED_MODULES = (
    RESTORATION_ROOT / "degradation.py",
    RESTORATION_ROOT / "evidence.py",
    RESTORATION_ROOT / "input_protocol.py",
    RESTORATION_ROOT / "metrics.py",
    RESTORATION_ROOT / "observations.py",
    RESTORATION_ROOT / "phase_control.py",
    RESTORATION_ROOT / "pupil_aberrations.py",
    RESTORATION_ROOT / "targets.py",
    RESTORATION_ROOT / "value_contracts.py",
) + tuple(sorted((RESTORATION_ROOT / "optical_bench").glob("*.py")))
NATIVE_FIXED_RUNTIME_MODULES = (
    RESTORATION_ROOT / "fixed_measurement" / "experiment.py",
    RESTORATION_ROOT / "fixed_measurement" / "protocol" / "plan.py",
    RESTORATION_ROOT / "fixed_measurement" / "evidence" / "archive.py",
)
ROOT_FILE_ALLOWLIST = (
    "README.md",
    "__init__.py",
    "degradation.py",
    "errors.py",
    "evidence.py",
    "input_protocol.py",
    "metrics.py",
    "observations.py",
    "phase_control.py",
    "pupil_aberrations.py",
    "run_adaptive_measurement.py",
    "run_fixed_measurement.py",
    "targets.py",
    "value_contracts.py",
)


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return tuple(names)


def test_shared_restoration_modules_do_not_depend_on_experiment_protocols() -> None:
    forbidden = (
        "experiments.restoration.fixed_measurement",
        "experiments.restoration.adaptive_measurement",
        "experiments.restoration.studies",
    )

    for path in SHARED_MODULES:
        imported_modules = _imports(path)
        assert not any(
            imported.startswith(prefix)
            for imported in imported_modules
            for prefix in forbidden
        ), path.name


def test_fixed_and_adaptive_protocols_do_not_import_one_another() -> None:
    protocol_roots = {
        "fixed_measurement": RESTORATION_ROOT / "fixed_measurement",
        "adaptive_measurement": RESTORATION_ROOT / "adaptive_measurement",
    }
    for owner, protocol_root in protocol_roots.items():
        other = (
            "adaptive_measurement"
            if owner == "fixed_measurement"
            else "fixed_measurement"
        )
        forbidden = f"experiments.restoration.{other}"
        for path in protocol_root.rglob("*.py"):
            assert not any(
                imported.startswith(forbidden) for imported in _imports(path)
            ), path.relative_to(RESTORATION_ROOT).as_posix()


def test_experiment_protocols_do_not_depend_on_claim_facing_studies() -> None:
    forbidden = "experiments.restoration.studies"

    for protocol_name in ("fixed_measurement", "adaptive_measurement"):
        protocol_root = RESTORATION_ROOT / protocol_name
        for path in protocol_root.rglob("*.py"):
            assert not any(
                imported.startswith(forbidden) for imported in _imports(path)
            ), path.relative_to(RESTORATION_ROOT).as_posix()

    assert not tuple((RESTORATION_ROOT / "comparison").glob("*.py"))


def test_adaptive_episode_does_not_bypass_the_calibrated_bench_seam() -> None:
    episode_path = RESTORATION_ROOT / "adaptive_measurement" / "episode.py"
    imported_modules = _imports(episode_path)

    assert not any(
        imported.startswith("experiments.restoration.optical_bench")
        for imported in imported_modules
    )
    assert not any(
        imported.startswith("experiments.restoration.adaptive_measurement.sensing")
        for imported in imported_modules
    )


def test_adaptive_core_evidence_does_not_depend_on_validation_or_adapters() -> None:
    evidence_path = RESTORATION_ROOT / "adaptive_measurement" / "evidence.py"
    imported_modules = _imports(evidence_path)
    forbidden = (
        "experiments.restoration.adaptive_measurement.validation",
        "experiments.restoration.adaptive_measurement.adapters",
    )

    assert not any(
        imported.startswith(prefix)
        for imported in imported_modules
        for prefix in forbidden
    )


def test_native_fixed_runtime_does_not_translate_legacy_roles() -> None:
    for path in NATIVE_FIXED_RUNTIME_MODULES:
        source = path.read_text(encoding="utf-8")
        assert not any(
            "legacy" in imported or "migration" in imported
            for imported in _imports(path)
        ), path.name
        assert "compile_formal_experiment_plan" not in source, path.name
        assert "fixed_role_for_model_role" not in source, path.name


def test_restoration_root_contains_only_shared_semantics_and_entrypoints() -> None:
    root_files = tuple(
        sorted(path.name for path in RESTORATION_ROOT.iterdir() if path.is_file())
    )

    assert root_files == ROOT_FILE_ALLOWLIST


def test_fixed_and_adaptive_use_the_same_optical_bench_interface() -> None:
    consumers = (
        RESTORATION_ROOT / "fixed_measurement" / "optics" / "frontend.py",
        RESTORATION_ROOT / "adaptive_measurement" / "adapters" / "simulated_bench.py",
    )

    for path in consumers:
        imported_modules = _imports(path)
        assert "experiments.restoration.optical_bench" in imported_modules
        assert not any(
            imported.startswith("experiments.restoration.optical_bench.")
            for imported in imported_modules
        )


def test_physical_bench_is_not_owned_by_either_experiment_protocol() -> None:
    fixed_root = RESTORATION_ROOT / "fixed_measurement"
    adaptive_root = RESTORATION_ROOT / "adaptive_measurement"

    assert not (fixed_root / "optics" / "geometry.py").exists()
    assert not any(
        path.name in {"optical_config.py", "optical_topology.py"}
        for path in fixed_root.rglob("*.py")
    )
    for path in fixed_root.rglob("*.py"):
        assert not any(
            imported.startswith("experiments.restoration.optical_bench.")
            for imported in _imports(path)
        ), path.relative_to(RESTORATION_ROOT).as_posix()

    evaluator_module = "experiments.restoration.optical_bench.evaluator"
    for path in adaptive_root.rglob("*.py"):
        direct_imports = {
            imported
            for imported in _imports(path)
            if imported.startswith("experiments.restoration.optical_bench.")
        }
        relative_path = path.relative_to(adaptive_root)
        if relative_path.parts[0] == "validation":
            assert direct_imports <= {evaluator_module}, relative_path.as_posix()
        else:
            assert not direct_imports, relative_path.as_posix()
