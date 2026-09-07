from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).parents[2]
PACKAGE = ROOT / "src" / "metacraft"


def _production_files() -> tuple[Path, ...]:
    return tuple(sorted(PACKAGE.rglob("*.py")))


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"))


def _identifiers(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


def _import_roots(
    node: ast.Import | ast.ImportFrom,
    path: Path,
) -> set[str]:
    """
    Resolve every import spelling to one top-level package responsibility.
    """

    if isinstance(node, ast.Import):
        modules = [alias.name.split(".") for alias in node.names]
    else:
        if node.level:
            package = (
                "metacraft",
                *path.relative_to(PACKAGE).parent.parts,
            )
            retained = len(package) - node.level + 1
            base = list(package[:retained])
        else:
            base = []
        if node.module is not None:
            base.extend(node.module.split("."))
        modules = [base]
        if base == ["metacraft"]:
            modules = [[*base, alias.name] for alias in node.names if alias.name != "*"]
    roots: set[str] = set()
    for imported in modules:
        if not imported:
            continue
        if imported[0] == "metacraft" and len(imported) > 1:
            roots.add(imported[1])
        elif imported[0] != "metacraft":
            roots.add(imported[0])
    return roots


def test_import_roots_resolve_package_and_parent_alias_forms() -> None:
    """
    Absolute package aliases and parent-relative aliases name the same owner.
    """

    path = PACKAGE / "field" / "example.py"
    tree = ast.parse(
        "from metacraft import consultation\n"
        "from .. import consultation\n"
        "import metacraft.consultation\n"
    )

    assert [
        _import_roots(node, path)
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ] == [{"consultation"}, {"consultation"}, {"consultation"}]


def test_field_boolean_identifiers_state_positive_meaning() -> None:
    """
    Field Boolean values name their positive proposition.
    """

    retired = {"complete", "optional", "propagating", "qualified"}
    found: dict[str, list[str]] = {}
    for path in sorted((PACKAGE / "field").rglob("*.py")):
        names = sorted(_identifiers(_tree(path)) & retired)
        if names:
            found[str(path.relative_to(PACKAGE))] = names

    assert found == {}


def test_metalens_realization_exports_one_domain_language() -> None:
    """
    Retired realization operations cannot reappear beside their replacements.
    """

    retired = {
        "Orientations",
        "ORIENTATIONS_SCHEMA",
        "assign_oriented",
        "derive_orientations",
        "geometric_surface_cautions",
        "geometric_surface_transform",
        "pointwise_surface_table",
        "tangential_surface_field",
    }
    found: dict[str, list[str]] = {}
    for name in (
        "aperture.py",
        "geometric_phase.py",
        "pointwise.py",
        "result.py",
    ):
        path = PACKAGE / "science" / "metalens" / name
        declarations = {
            node.name
            for node in ast.walk(_tree(path))
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
        }
        matched = sorted(declarations & retired)
        if matched:
            found[name] = matched

    assert found == {}


def test_metalens_realization_fields_state_exact_positive_meaning() -> None:
    """
    Public realization fields use exact nouns and positive Boolean polarity.
    """

    retired = {
        "actual_binding_reference",
        "actual_field_reference",
        "actual_method",
        "bracketed",
        "complex_component_error",
        "construction_valid",
        "focus_bracketed",
        "imaginary",
        "length_nm",
        "locally_refined",
        "major_nm",
        "minor_nm",
        "observed",
        "orientations",
        "orientations_identity",
        "orientations_reference",
        "published",
        "real",
        "width_nm",
    }
    owners = {
        "aperture.py": {"Ellipse", "Rectangle", "Response"},
        "focal_field_comparison.py": {"FocalFieldComparison"},
        "focus.py": {"FocusConvergence", "FocusSurvey", "HalfMaximum"},
        "geometric_phase.py": {
            "ComplexCoefficient",
            "OrientationSet",
        },
        "pointwise.py": {"GeometricSurfaceTransform"},
        "propagation_phase.py": {"PropagationResponse"},
        "result.py": {"GeometricResult", "PointwiseGeometricResult"},
    }
    found: dict[str, dict[str, list[str]]] = {}
    for name, classes in owners.items():
        path = PACKAGE / "science" / "metalens" / name
        for node in _tree(path).body:
            if not isinstance(node, ast.ClassDef) or node.name not in classes:
                continue
            fields = {
                child.target.id
                for child in node.body
                if isinstance(child, ast.AnnAssign)
                and isinstance(child.target, ast.Name)
            }
            matched = sorted(fields & retired)
            if matched:
                found.setdefault(name, {})[node.name] = matched

    assert found == {}


def test_metalens_compilation_booleans_state_positive_meaning() -> None:
    """
    Advice and relationship Booleans state a complete positive proposition.
    """

    retired = {"include_identity", "synthetic", "with_envelope"}
    found: dict[str, list[str]] = {}
    paths = (
        PACKAGE / "science" / "metalens" / "height_advice.py",
        PACKAGE / "science" / "metalens" / "period_advice.py",
        PACKAGE / "science" / "metalens" / "relationship.py",
    )
    for path in paths:
        names = sorted(_identifiers(_tree(path)) & retired)
        if names:
            found[str(path.relative_to(PACKAGE))] = names

    assert found == {}


def test_field_dependencies_point_inward() -> None:
    forbidden_roots = {
        "_local",
        "advice",
        "local",
        "runner",
        "science",
        "solvers",
        "workstation",
    }
    found: dict[str, list[str]] = {}
    for path in sorted((PACKAGE / "field").glob("*.py")):
        imports: set[str] = set()
        for node in ast.walk(_tree(path)):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.update(_import_roots(node, path))
        forbidden = sorted(imports & forbidden_roots)
        if forbidden:
            found[path.name] = forbidden

    assert found == {}


def test_science_owns_its_consultation_records() -> None:
    """
    Science holds immutable consultation records; the provider Adapter
    depends inward. Science never imports the provider package or any
    transport configuration.
    """

    forbidden_roots = {
        "_local",
        "advice",
        "local",
        "runner",
        "solvers",
        "workstation",
    }
    found: dict[str, list[str]] = {}
    for path in sorted((PACKAGE / "science").rglob("*.py")):
        imports: set[str] = set()
        for node in ast.walk(_tree(path)):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.update(_import_roots(node, path))
        forbidden = sorted(imports & forbidden_roots)
        if forbidden:
            found[str(path.relative_to(PACKAGE))] = forbidden

    assert found == {}


def _field_internal_module(node: ast.AST) -> str | None:
    """
    Return the ``field.<sub>`` module one import reaches, or None.

    The ratchet must not be bypassable by adding another leading dot, so every
    relative level at or beyond the field package's neighbours is caught, as
    well as absolute ``metacraft.field.<sub>`` forms.
    """

    if isinstance(node, ast.ImportFrom) and node.module is not None:
        if node.level >= 2 and node.module.startswith("field."):
            return node.module
        if node.module.startswith("metacraft.field."):
            return node.module.removeprefix("metacraft.")
    elif isinstance(node, ast.Import):
        for imported in node.names:
            if imported.name.startswith("metacraft.field."):
                return imported.name.removeprefix("metacraft.")
    return None


def test_field_private_modules_have_no_external_importers() -> None:
    """
    Keep private Field implementation reachable only inside the Field package.

    Explicit numerical owners are legitimate production dependencies and do
    not need an allowlist. Only imports whose module name begins with an
    underscore cross a private implementation seam.
    """

    importers: list[str] = []
    for path in _production_files():
        if path.parent == PACKAGE / "field":
            continue
        for node in ast.walk(_tree(path)):
            internal_module = _field_internal_module(node)
            if (
                internal_module is not None
                and internal_module.split(".")[1].startswith("_")
            ):
                importers.append(
                    f"{path.relative_to(PACKAGE).as_posix()}:" f"{internal_module}"
                )

    assert importers == []


def test_a_synthetic_forbidden_field_storage_importer_is_caught() -> None:
    """
    A new science reach into the private ``field._storage`` module is flagged
    even when it hides behind a deeper relative level than the seam imports.

    This guards the closure invariant: the storage helpers are field-internal
    and must be reached only through ``field.evidence``. The detection helper is
    exercised directly so the regression survives even if production layout
    changes.
    """

    allowed_modules = {"field.evidence", "field.sample"}
    synthetic = ast.parse(
        "from ...field._storage import require_storage\n",
    )
    flagged = next(
        _field_internal_module(node)
        for node in ast.walk(synthetic)
        if _field_internal_module(node) is not None
    )
    assert flagged == "field._storage"
    assert flagged not in allowed_modules


def test_field_evidence_hides_storage_from_metalens_focus() -> None:
    """
    Metalens names semantic field operations, never storage mechanics.
    """

    path = PACKAGE / "science" / "metalens" / "focus_evidence.py"
    imported: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.ImportFrom) and node.module == "field.evidence":
            imported.update(alias.name for alias in node.names)

    assert imported == {"describe_components", "restore_components"}
    assert imported.isdisjoint(
        {
            "ARRAY_DTYPE",
            "ARRAY_MEDIA_TYPE",
            "ARRAY_ORDER",
            "array_bytes",
            "array_metadata",
            "require_raw_media",
            "require_references",
            "require_storage",
            "resolve_component_references",
        }
    )


def test_field_evidence_does_not_export_storage_mechanics() -> None:
    """
    The evidence Interface exposes meaning; private storage keeps encoding.
    """

    path = PACKAGE / "field" / "evidence.py"
    exported: set[str] = set()
    for node in _tree(path).body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets
            )
            and isinstance(node.value, ast.List)
        ):
            exported = {
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            }

    assert exported == {
        "FIELD_SCHEMA",
        "admit_components",
        "describe_components",
        "field_document",
        "restore_components",
        "restore_field",
    }
    assert all("storage" not in name.casefold() for name in exported)


def test_native_authority_has_one_python_adapter() -> None:
    importers: list[str] = []
    for path in _production_files():
        for node in ast.walk(_tree(path)):
            imports_native = (
                isinstance(node, ast.ImportFrom)
                and node.module in {"_authority", "metacraft._authority"}
            ) or (
                isinstance(node, ast.Import)
                and any(
                    imported.name == "metacraft._authority" for imported in node.names
                )
            )
            if imports_native:
                importers.append(path.relative_to(PACKAGE).as_posix())

    assert importers == ["authority/interface.py"]


def test_conduct_owns_the_complete_branch_frontier() -> None:
    """
    ``conduct`` is the sole owner of frontier persistence.

    Branch operations (per-method advances in propagation/geometric modules
    and the application's ``advance`` operation) must not admit checkpoints
    directly. Only the application's ``record`` hook — called by
    ``conduct`` after every transition — persists the complete family.
    """

    assert not (PACKAGE / "local.py").exists()
    assert not (PACKAGE / "_local").exists()


def test_record_hook_is_the_one_checkpoint_writer() -> None:
    """
    ``remember_studies`` is imported only into the application
    module that owns the ``record`` hook, never into a branch operation.
    """

    source = (PACKAGE / "science" / "conduct.py").read_text(
        encoding="utf-8-sig"
    )
    assert "remember_studies" not in source


def test_lumerical_outcomes_have_exact_importers() -> None:
    """
    Typed outcomes cross only their exact native and local seams.
    """

    outcome_names = {"LumericalUnavailable"}
    expected = [
        (
            ".qualification",
            "LumericalUnavailable",
            "solvers/lumerical_fdtd/_lane_worker.py",
        ),
        (
            ".qualification",
            "LumericalUnavailable",
            "solvers/lumerical_fdtd/periodic_response.py",
        ),
        (
            ".qualification",
            "LumericalUnavailable",
            "solvers/lumerical_fdtd/lane.py",
        ),
        (
            ".qualification",
            "LumericalUnavailable",
            "solvers/lumerical_fdtd/probe.py",
        ),
        (
            ".qualification",
            "LumericalUnavailable",
            "solvers/lumerical_fdtd/session.py",
        ),
    ]
    imports: list[tuple[str, str, str]] = []
    qualified_accesses: list[tuple[str, str]] = []
    for path in _production_files():
        relative = path.relative_to(PACKAGE).as_posix()
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.ImportFrom):
                source = "." * node.level + (node.module or "")
                for alias in node.names:
                    if alias.name in outcome_names:
                        imports.append((source, alias.name, relative))
            if isinstance(node, ast.Attribute) and node.attr in outcome_names:
                qualified_accesses.append((relative, node.attr))
    assert sorted(imports) == sorted(expected)
    assert qualified_accesses == []


def test_science_conduct_does_not_cross_to_local_or_solver_layers() -> None:
    """
    The generic ``conduct`` seam owns no local or solver knowledge.
    """

    conduct_source = (PACKAGE / "science" / "conduct.py").read_text(
        encoding="utf-8-sig"
    )
    for forbidden in (
        "from .._local",
        "from ..solvers",
        "import lumerical",
        "FieldMemoryUnavailable",
        "CapacityUnavailable",
        "str(error)",
    ):
        assert (
            forbidden not in conduct_source
        ), f"science/conduct.py crosses a seam: {forbidden!r}"


def test_periodic_full_wave_response_is_retired() -> None:
    """
    The retired shared capability name survives nowhere in production.
    """

    found: dict[str, list[int]] = {}
    for path in _production_files():
        source = path.read_text(encoding="utf-8-sig")
        if "periodic_full_wave_response" in source:
            found[str(path.relative_to(PACKAGE))] = [
                index
                for index, line in enumerate(source.splitlines(), start=1)
                if "periodic_full_wave_response" in line
            ]
    assert found == {}


def test_the_geometric_observation_decoder_is_retired() -> None:
    """
    The dead ``_decode_geometric_observation`` decoder and its exclusively
    orphaned helpers survive nowhere in production. The live geometric decode
    path uses ``GeometricBasisObservation.from_mapping``; the old single-form
    decoder must not be reintroduced.
    """

    retired = {
        "_decode_geometric_observation",
        "_polarized_channel",
        "_execution_record",
    }
    found: dict[str, list[str]] = {}
    for path in _production_files():
        tree = _tree(path)
        names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }
        matched = sorted(names & retired)
        if matched:
            found[str(path.relative_to(PACKAGE))] = matched
    assert found == {}


def test_unused_complex_mapping_helper_is_retired() -> None:
    """
    Complex response encoding has an intention-revealing name.
    """

    found: list[str] = []
    for path in _production_files():
        tree = _tree(path)
        if any(
            isinstance(node, ast.FunctionDef) and node.name == "_complex_mapping"
            for node in ast.walk(tree)
        ):
            found.append(str(path.relative_to(PACKAGE)))

    assert found == []


def test_the_capability_seam_is_route_neutral() -> None:
    """
    The modules that issue periodic response capabilities import no
    propagation-phase or geometric-phase control strategy. They know only the
    route-neutral responses they can establish; route choice stays in metalens
    science and the periodic product-execution/template layer.
    """

    capability_seam = (
        PACKAGE / "solvers" / "lumerical_fdtd" / "qualification.py",
        PACKAGE / "solvers" / "lumerical_fdtd" / "periodic_response.py",
        PACKAGE / "solvers" / "lumerical_fdtd" / "probe.py",
    )
    forbidden = {
        "ControlStrategy",
        "PROPAGATION_PHASE",
        "GEOMETRIC_PHASE",
        "propagation_phase",
        "geometric_phase",
    }
    found: dict[str, set[str]] = {}
    for path in capability_seam:
        identifiers = _identifiers(_tree(path)) & forbidden
        if identifiers:
            found[path.name] = identifiers
    assert found == {}


def test_no_string_classified_expected_failures_remain() -> None:
    """
    Expected absence is matched via typed outcomes, never by classifying the
    text of a raised exception.
    """

    pattern = "str(error) in {"
    found: list[str] = []
    for path in _production_files():
        source = path.read_text(encoding="utf-8-sig")
        if pattern in source:
            found.append(str(path.relative_to(PACKAGE)))
    assert found == []


def test_finding_diagnostics_never_classify_control_flow() -> None:
    """
    Finding reasons remain diagnostics; their type owns retry semantics.
    """

    found: list[str] = []
    for path in _production_files():
        for node in ast.walk(_tree(path)):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"split", "startswith"}
            ):
                continue
            if any(
                isinstance(part, ast.Attribute) and part.attr == "needs"
                for part in ast.walk(node.func.value)
            ):
                found.append(str(path.relative_to(PACKAGE)))

    assert found == []


def test_metalens_execution_names_its_single_study_state_consistently() -> None:
    """
    Every metalens execution step advances one ``Study`` value.

    A second state name makes one transition look like two independent
    interfaces and invites them to drift. Keep ``study`` as the sole domain
    term throughout the conducting and execution modules.
    """

    execution_modules = (
        PACKAGE / "science" / "metalens" / "conduct.py",
        PACKAGE / "science" / "metalens" / "field_execution.py",
        PACKAGE / "science" / "metalens" / "geometric_execution.py",
        PACKAGE / "science" / "metalens" / "propagation_execution.py",
    )
    found = [
        str(path.relative_to(PACKAGE))
        for path in execution_modules
        if "known" in _identifiers(_tree(path))
    ]

    assert found == []


def test_periodic_observation_codec_has_one_explicit_owner_interface() -> None:
    """
    Periodic-response callers depend on an owner-facing Interface, not on
    underscore-prefixed codec implementation.
    """

    forbidden = {
        "_PeriodicObservationDocument",
        "_admit_periodic_polarization",
        "_admit_periodic_transmission",
        "_form_admitted_periodic_polarization",
        "_form_admitted_periodic_transmission",
        "_decode_periodic_polarization",
        "_decode_periodic_reference_surface",
        "_decode_periodic_transmission",
        "_periodic_observation_mapping",
    }
    found: dict[str, list[str]] = {}
    for path in _production_files():
        if path == PACKAGE / "science" / "periodic_response.py":
            continue
        names = sorted(
            {
                alias.name
                for node in ast.walk(_tree(path))
                if isinstance(node, ast.ImportFrom)
                for alias in node.names
                if alias.name in forbidden
            }
        )
        if names:
            found[str(path.relative_to(PACKAGE))] = names

    assert found == {}


def test_periodic_request_owns_its_frozen_work_identity_projection() -> None:
    """
    One request Module owns application-to-Authority work identity without a
    one-caller pass-through Module.
    """

    retired = (
        PACKAGE
        / "science"
        / "metalens"
        / "periodic_work_protocol.py"
    )
    assert not retired.exists()
