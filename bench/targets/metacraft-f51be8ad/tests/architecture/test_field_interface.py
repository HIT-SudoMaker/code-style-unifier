from __future__ import annotations

import ast
import importlib
import subprocess
import sys
from importlib.util import resolve_name
from pathlib import Path

import numpy

import metacraft.field as field
from metacraft.authority import reference_for

ROOT = Path(__file__).parents[2]
SHARED_FIELD_LANGUAGE = [
    "ComponentBasis",
    "CoordinateFrame",
    "Field",
    "FieldComponent",
    "Medium",
    "PlaneSurface",
]
REMOVED_FIELD_ROOT_NAMES = (
    "AplanaticPupil",
    "AplanaticSurface",
    "ANGULAR_SPECTRUM_REALIZATION",
    "AngularSpectrumConvention",
    "AngularSpectrumQualification",
    "AngularSpectrumRealization",
    "AxialObservation",
    "CZT_DEBYE_REALIZATION",
    "CZTDebyeRealization",
    "DIRECT_DEBYE_REALIZATION",
    "AplanaticFocusQualification",
    "AplanaticReferenceQualification",
    "DebyeConvention",
    "DebyeObservation",
    "DirectDebyeQualification",
    "DirectDebyeRealization",
    "ElectromagneticPropagation",
    "FieldMemoryUnavailable",
    "FieldPropagation",
    "FFT_DEBYE_REALIZATION",
    "FFTDebyeRealization",
    "FocalCoordinates",
    "LongitudinalPowerPlane",
    "PupilPolarization",
    "VECTOR_ANGULAR_SPECTRUM_CAPABILITY",
    "VECTOR_ANGULAR_SPECTRUM_REALIZATION",
    "VectorAngularSpectrumConvention",
    "VectorAngularSpectrumQualification",
    "VectorAngularSpectrumRealization",
    "evaluate_czt_debye",
    "evaluate_direct_debye",
    "evaluate_fft_debye",
    "fft_focal_axis",
    "observe_angular_spectrum",
    "observe_czt_debye",
    "observe_direct_debye",
    "observe_fft_debye",
    "observe_vector_angular_spectrum",
    "propagate_electromagnetic_field",
    "propagate_field",
    "qualify_angular_spectrum",
    "qualify_aplanatic_reference",
    "qualify_czt_debye",
    "qualify_direct_debye",
    "qualify_fft_debye",
    "qualify_vector_angular_spectrum",
    "restore_vector_angular_spectrum_binding",
    "vector_angular_spectrum_binding",
)


def test_field_root_exports_only_shared_language_in_canonical_order() -> None:
    assert field.__all__ == SHARED_FIELD_LANGUAGE
    assert all(not hasattr(field, name) for name in REMOVED_FIELD_ROOT_NAMES)


def test_shared_field_language_forms_one_complete_field() -> None:
    samples = numpy.ones((2, 2), dtype="<c16")
    samples.setflags(write=False)
    zero_samples = numpy.zeros((2, 2), dtype="<c16")
    zero_samples.setflags(write=False)

    basis = field.ComponentBasis.TRANSVERSE_LINEAR
    frame = field.CoordinateFrame()
    medium = field.Medium("air")
    surface = field.PlaneSurface(
        position_m=0.0,
        spacing_m=100e-9,
        shape=(2, 2),
    )
    electric_components = (
        field.FieldComponent("x", samples),
        field.FieldComponent("y", zero_samples),
    )
    sampled_field = field.Field(
        wavelength_m=500e-9,
        surface=surface,
        frame=frame,
        medium=medium,
        basis=basis,
        electric_components=electric_components,
        source_references=(reference_for(b"shared field"),),
        incident_reference_power=1.0,
    )

    assert sampled_field.component_names == ("x", "y")
    assert sampled_field.surface is surface
    assert sampled_field.frame is frame
    assert sampled_field.medium is medium
    assert sampled_field.electric("x").shape == (2, 2)


def test_clean_field_root_import_loads_no_numerical_or_product_module() -> None:
    source = f"""
import sys
sys.path.insert(0, {str(ROOT / "src")!r})
import metacraft.field as field
assert field.__all__ == {SHARED_FIELD_LANGUAGE!r}
forbidden = (
    "torch",
    "lumapi",
    "metacraft.solvers.lumerical_fdtd",
    "metacraft.field.angular_spectrum",
    "metacraft.field.vector_angular_spectrum",
    "metacraft.field.debye",
    "metacraft.field.direct_debye",
    "metacraft.field.fast_debye",
    "metacraft.field.debye_qualification",
    "metacraft.field.reference_surface",
)
loaded = tuple(
    module
    for module in sys.modules
    if any(
        module == prefix or module.startswith(prefix + ".")
        for prefix in forbidden
    )
)
assert not loaded, loaded
"""

    completed = subprocess.run(
        [sys.executable, "-I", "-c", source],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_specialized_field_language_stays_with_its_exact_owner() -> None:
    contracts = {
        "metacraft.field.angular_spectrum": (
            "ANGULAR_SPECTRUM_REALIZATION",
            "AngularSpectrumConvention",
            "AngularSpectrumQualification",
            "AngularSpectrumRealization",
            "AxialObservation",
            "FieldMemoryUnavailable",
            "FieldPropagation",
            "observe_angular_spectrum",
            "propagate_field",
            "qualify_angular_spectrum",
        ),
        "metacraft.field.vector_angular_spectrum": (
            "VECTOR_ANGULAR_SPECTRUM_CAPABILITY",
            "VECTOR_ANGULAR_SPECTRUM_REALIZATION",
            "ElectromagneticPropagation",
            "LongitudinalPowerPlane",
            "VectorAngularSpectrumConvention",
            "VectorAngularSpectrumQualification",
            "VectorAngularSpectrumRealization",
            "observe_vector_angular_spectrum",
            "propagate_electromagnetic_field",
            "qualify_vector_angular_spectrum",
            "restore_vector_angular_spectrum_binding",
            "vector_angular_spectrum_binding",
        ),
        "metacraft.field.debye": (
            "AplanaticPupil",
            "AplanaticSurface",
            "DebyeConvention",
            "DebyeObservation",
            "FocalCoordinates",
            "PupilPolarization",
        ),
        "metacraft.field.fast_debye": (
            "CZT_DEBYE_REALIZATION",
            "FFT_DEBYE_REALIZATION",
            "CZTDebyeRealization",
            "FFTDebyeRealization",
            "evaluate_czt_debye",
            "evaluate_fft_debye",
            "fft_focal_axis",
            "observe_czt_debye",
            "observe_fft_debye",
        ),
        "metacraft.field.debye_qualification": (
            "APLANATIC_REFERENCE_BINDING_SCHEMA",
            "AplanaticFocusQualification",
            "AplanaticReferenceQualification",
            "aplanatic_reference_binding",
            "form_aplanatic_reference",
            "qualify_aplanatic_reference",
            "qualify_czt_debye",
            "qualify_fft_debye",
            "restore_aplanatic_reference_binding",
        ),
        "metacraft.field.evidence": (
            "FIELD_SCHEMA",
            "admit_components",
            "describe_components",
            "field_document",
            "restore_components",
            "restore_field",
        ),
        "metacraft.field.reference_surface": (
            "AdmittedReferenceSurface",
            "ReferenceSurfaceComparison",
            "ReferenceSurfaceResponse",
            "RequestedInputBasis",
            "admit_response_components",
            "compare_reference_surfaces",
            "reference_surface_document",
            "restore_reference_surface",
        ),
    }

    for owner, names in contracts.items():
        module = importlib.import_module(owner)
        assert not set(names) - set(vars(module)), owner


def test_production_imports_only_shared_names_from_field_root() -> None:
    violations = []
    source_root = ROOT / "src" / "metacraft"
    for path in source_root.rglob("*.py"):
        module_parts = path.relative_to(ROOT / "src").with_suffix("").parts
        is_package = module_parts[-1] == "__init__"
        module = ".".join(module_parts[:-1] if is_package else module_parts)
        package = module if is_package else module.rpartition(".")[0]
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            target = _resolved_import(node, package=package)
            if target != "metacraft.field":
                continue
            removed = tuple(
                alias.name
                for alias in node.names
                if alias.name not in SHARED_FIELD_LANGUAGE
            )
            if removed:
                violations.append(
                    (
                        path.relative_to(ROOT).as_posix(),
                        node.lineno,
                        removed,
                    )
                )

    assert not violations, violations


def test_available_memory_observation_has_one_private_field_owner() -> None:
    field_root = ROOT / "src" / "metacraft" / "field"
    sources = {
        path.name: path.read_text(encoding="utf-8") for path in field_root.glob("*.py")
    }

    for platform_detail in (
        "mem_get_info(",
        "GlobalMemoryStatusEx(",
        'sysconf("SC_PAGE_SIZE")',
        'sysconf("SC_AVPHYS_PAGES")',
        "ctypes.Structure",
    ):
        owners = [name for name, source in sources.items() if platform_detail in source]
        assert owners == ["_device_memory.py"]

    assert all(
        "def _available_memory_bytes" not in source for source in sources.values()
    )
    assert all("class _MemoryStatus" not in source for source in sources.values())


def _resolved_import(node: ast.ImportFrom, *, package: str) -> str:
    if node.level == 0:
        return node.module or ""
    relative = "." * node.level + (node.module or "")
    return resolve_name(relative, package)
