from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path


ROOT = Path(__file__).parents[2] / "src" / "metacraft"
FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Cpu",
        "DirectEngine",
        "LumericalAdapter",
        "RecoveredReceipt",
        "SessionFactory",
        "from_x_along_x",
        "from_x_along_y",
        "from_y_along_x",
        "from_y_along_y",
        "kx",
        "ky",
        "kz",
        "na",
        "phase_reference",
        "recovered",
        "recover_jones_library",
        "recover_material_sample",
        "recover_propagation_library",
        "r_xx",
        "r_xy",
        "r_yx",
        "r_yy",
        "t_xx",
        "t_xy",
        "t_yx",
        "t_yy",
    }
)
LUMERICAL_INTERFACE = frozenset(
    {
        "LumericalConfig",
        "LumericalMetalensEvidence",
        "LumericalMaterialVerifier",
        "LumericalPeriodicResponse",
        "read_lumerical_environment",
    }
)
PRIVATE_CALLER_PARAMETERS = frozenset(
    {
        "_open_session",
        "_planner",
        "_probe",
        "execution",
        "lanes",
        "worker_count",
    }
)


def _production_files() -> tuple[Path, ...]:
    solver = ROOT / "solvers" / "lumerical_fdtd"
    return tuple(sorted(solver.rglob("*.py"))) + tuple(
        sorted((ROOT / "workstation").glob("*.py"))
    )


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


def _callable_surfaces(value: object) -> tuple[object, ...]:
    if not inspect.isclass(value):
        return (value,) if callable(value) else ()

    surfaces: list[object] = [value.__init__]
    for name, member in inspect.getmembers_static(value):
        if name.startswith("_"):
            continue
        candidate = (
            member.__func__
            if isinstance(member, (classmethod, staticmethod))
            else member
        )
        if callable(candidate):
            surfaces.append(candidate)
    return tuple(surfaces)


def _private_caller_parameters(value: object) -> set[str]:
    leaked: set[str] = set()
    for callable_surface in _callable_surfaces(value):
        try:
            parameters = inspect.signature(callable_surface).parameters
        except (TypeError, ValueError):
            continue
        leaked.update(set(parameters) & PRIVATE_CALLER_PARAMETERS)
    return leaked


def test_solver_and_workstation_speak_the_canonical_vocabulary() -> None:
    """
    Keep retired abbreviations outside the product and placement Interfaces.
    """

    found: dict[str, list[str]] = {}
    for path in _production_files():
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        retired = sorted(_identifiers(tree) & FORBIDDEN_IDENTIFIERS)
        if retired:
            found[str(path.relative_to(ROOT))] = retired

    assert found == {}


def test_lumerical_package_exports_only_its_caller_interface() -> None:
    """
    Keep construction, fixtures, and product translation behind the package.
    """

    package = importlib.import_module("metacraft.solvers.lumerical_fdtd")

    assert frozenset(package.__all__) == LUMERICAL_INTERFACE
    assert all(
        not hasattr(package, name)
        for name in (
            "DirectEngine",
            "SessionLease",
            "SessionPool",
            "WorkstationExecution",
        )
    )
    for name in package.__all__:
        exported = getattr(package, name)
        assert _private_caller_parameters(exported) == set(), name


def test_lumerical_configuration_owns_no_scientific_material_catalogue() -> None:
    """
    Let the project material library choose while product config stays local.
    """

    qualification = ROOT / "solvers" / "lumerical_fdtd" / "qualification.py"
    source = qualification.read_text(encoding="utf-8-sig")
    package = importlib.import_module("metacraft.solvers.lumerical_fdtd")

    assert "LUMERICAL_MATERIAL_" not in source
    assert "material_catalogue" not in source
    assert (
        "material_catalogue"
        not in inspect.signature(package.LumericalConfig).parameters
    )


def test_lumerical_material_adapter_owns_no_project_selection() -> None:
    """
    Select and admit project registrations before native verification.
    """

    adapter = ROOT / "solvers" / "lumerical_fdtd" / "material_response.py"
    names = _identifiers(ast.parse(adapter.read_text(encoding="utf-8-sig")))

    assert names.isdisjoint(
        {
            "LumericalMaterialResponse",
            "SolverMaterialLibrary",
            "catalogue",
            "select",
        }
    )


def test_lumerical_signature_guard_detects_private_policy_parameters() -> None:
    """
    The class-wide signature ratchet detects every public method leak.
    """

    class Leaked:
        def open(self, *, _probe: object) -> None:
            del _probe

        @classmethod
        def plan(cls, *, _planner: object) -> None:
            del cls, _planner

        @staticmethod
        def place(*, lanes: object) -> None:
            del lanes

    assert _private_caller_parameters(Leaked) == {
        "_planner",
        "_probe",
        "lanes",
    }


def test_lumerical_work_life_contains_no_retired_containment_language() -> None:
    """
    Keep one private native-session vocabulary across both process ends.
    """

    solver = ROOT / "solvers" / "lumerical_fdtd"
    sources = {
        path.name: path.read_text(encoding="utf-8-sig")
        for path in (
            solver / "lane.py",
            solver / "_lane_worker.py",
            solver / "session.py",
        )
    }
    found = {
        name: retired
        for name, source in sources.items()
        for retired in (
            "ContainedSession",
            "contained_session",
            'getattr(session, "placement"',
        )
        if retired in source
    }

    assert found == {}


def test_periodic_execution_knows_no_artifact_directory_names() -> None:
    """
    Let RunDirectory alone translate scientific work into file names.
    """

    execution = (
        ROOT / "solvers" / "lumerical_fdtd" / "periodic_execution.py"
    ).read_text(encoding="utf-8-sig")

    assert "from-{basis}" not in execution
    assert all(
        name not in execution
        for name in (
            "after.fsp",
            "before.fsp",
            "construction.json",
            "execution.json",
            "observation.json",
            "solver.log",
            "work.json",
        )
    )


def test_probe_borrows_the_standard_native_work_vocabulary() -> None:
    """
    Keep qualification from becoming a second artifact-name owner.
    """

    probe = (ROOT / "solvers" / "lumerical_fdtd" / "probe.py").read_text(
        encoding="utf-8-sig"
    )

    assert "native_projects" in probe
    assert "archive_ordinary_attempt" in probe
    assert all(
        name not in probe
        for name in (
            "after.fsp",
            "before.fsp",
            "execution.json",
        )
    )


def test_probe_consumes_the_public_qualification_construction() -> None:
    """
    Keep periodic template facts under the construction Interface.
    """

    probe = ROOT / "solvers" / "lumerical_fdtd" / "probe.py"
    names = _identifiers(ast.parse(probe.read_text(encoding="utf-8")))

    assert "prepare_qualification_constructions" in names
    assert names.isdisjoint(
        {
            "GeometricConstruction",
            "GeometricCell",
            "GratingFrame",
            "PropagationConstruction",
            "PropagationCell",
            "build_geometric",
            "build_propagation",
        }
    )


def test_periodic_execution_prepares_one_route_neutral_construction() -> None:
    """
    Keep response callers from repeating geometry-specific template choices.
    """

    execution = ROOT / "solvers" / "lumerical_fdtd" / "periodic_execution.py"
    names = _identifiers(ast.parse(execution.read_text(encoding="utf-8")))

    assert "prepare_periodic_construction" in names
    assert names.isdisjoint(
        {
            "GeometricConstruction",
            "GratingFrame",
            "PropagationConstruction",
            "build_geometric",
            "build_propagation",
            "polarization_construction",
            "transmission_construction",
        }
    )


def test_propagation_science_uses_the_one_cell_vocabulary() -> None:
    """
    Keep pre-evidence pillars from becoming a second public cell hierarchy.
    """

    module = ROOT / "science" / "metalens" / "propagation_phase.py"
    tree = ast.parse(module.read_text(encoding="utf-8-sig"))
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}

    assert classes.isdisjoint(
        {
            "CircularPillar",
            "PropagationCell",
            "SquarePillar",
        }
    )


def test_admitted_propagation_library_restores_without_solver_candidates() -> None:
    """
    Keep replay faithful to the admitted scientific Cell aggregate.
    """

    path = ROOT / "science" / "metalens" / "propagation_execution.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    restore = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_restore_cell_library"
    )
    names = _identifiers(restore)

    assert "from_document" in names
    assert names.isdisjoint(
        {
            "_restore_library_record",
            "as_fixed_library",
            "restore_propagation_library",
        }
    )


_LUMERICAL_WORK_LIFE_IMPORTS = frozenset(
    {
        "AdmittedBasisObservation",
        "AdmittedGeometricObservation",
        "AdmittedObservation",
        "JonesReceiptsIncomplete",
        "PeriodicBatchExecution",
        "PropagationReceiptsIncomplete",
        "RestoredReceipt",
        "RunDirectory",
        "SessionLease",
        "SessionPool",
        "WorkRecord",
        "WorkstationExecution",
        "gather_geometric_cells",
        "gather_propagation_cells",
        "open_sweep",
        "restore_jones_library",
        "restore_propagation_library",
    }
)


_LUMERICAL_PACKAGE = "metacraft.solvers.lumerical_fdtd"


def _is_lumerical_module(resolved: str) -> bool:
    return resolved == _LUMERICAL_PACKAGE or resolved.startswith(
        _LUMERICAL_PACKAGE + "."
    )


def _is_type_checking_guard(node: ast.AST) -> bool:
    # ``if TYPE_CHECKING:`` and ``if typing.TYPE_CHECKING:`` are the same runtime
    # guard (both False at runtime). Recognize both spellings so a type-only
    # import under either form is excluded from runtime-leak detection.
    if isinstance(node, ast.Name):
        return node.id == "TYPE_CHECKING"
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "TYPE_CHECKING"
        and isinstance(node.value, ast.Name)
        and node.value.id == "typing"
    )


def _collect_lumerical_aliases(
    node: ast.Import | ast.ImportFrom,
    package_parts: tuple[str, ...],
    names: set[str],
) -> None:
    if isinstance(node, ast.ImportFrom):
        if node.module is None and not node.names:
            return
        base: list[str] = []
        if node.level:
            # ``package_parts`` includes the ``metacraft`` prefix and the
            # file name, so dropping ``level`` parts lands on the true ancestor
            # package and the resolved path keeps the ``metacraft.`` prefix
            # that ``_is_lumerical_module`` checks against.
            base.extend(package_parts[: max(len(package_parts) - node.level, 0)])
        if node.module:
            base.extend(node.module.split("."))
        if not _is_lumerical_module(".".join(base)):
            return
        for alias in node.names:
            if alias.name != "*":
                names.add(alias.name)
        return
    for alias in node.names:
        if not _is_lumerical_module(alias.name):
            continue
        names.add(alias.asname or alias.name.rsplit(".", 1)[-1])


def _lumerical_work_life_names(source: str, package_parts: tuple[str, ...]) -> set[str]:
    """
    Resolve every runtime name imported from the Lumerical Adapter package.

    ``package_parts`` is the module's path relative to the ``src`` directory
    (including the ``metacraft`` prefix and the file name), so a relative
    import like ``from ..solvers.lumerical_fdtd.periodic_execution import X``
    resolves with
    the ``metacraft.`` prefix. Both ``ast.ImportFrom`` and ``ast.Import``
    are walked. Imports guarded by ``if TYPE_CHECKING:`` are excluded: they are
    erased at runtime and are not a work-life reach.
    """

    tree = ast.parse(source)
    names: set[str] = set()

    def visit(node: ast.AST, in_type_checking: bool) -> None:
        if isinstance(node, (ast.ImportFrom, ast.Import)):
            if not in_type_checking:
                _collect_lumerical_aliases(node, package_parts, names)
            return
        if isinstance(node, ast.If):
            guard = _is_type_checking_guard(node.test)
            for child in node.body:
                visit(child, in_type_checking or guard)
            for child in node.orelse:
                visit(child, in_type_checking)
            return
        for child in ast.iter_child_nodes(node):
            visit(child, in_type_checking)

    visit(tree, False)
    return names


def _package_parts(path: Path) -> tuple[str, ...]:
    """
    Derive a module's ``metacraft.``-prefixed path parts for the detector.

    The parts include the ``metacraft`` prefix and the file name, so a
    relative import like
    ``from ..solvers.lumerical_fdtd.periodic_execution import X``
    resolves with that prefix and ``_is_lumerical_module`` can match it.
    """

    return path.relative_to(ROOT.parent).parts


def _lumerical_imported_names(path: Path) -> set[str]:
    """
    Resolve every runtime name imported from the Lumerical Adapter package.

    Relative and absolute spellings both resolve against the ``src`` package
    root (so ``metacraft.`` is always present in the resolved path), and
    ``ast.Import`` is walked alongside ``ast.ImportFrom`` — so a science module
    cannot smuggle a work-life type in through either import form.
    """

    return _lumerical_work_life_names(
        path.read_text(encoding="utf-8-sig"),
        _package_parts(path),
    )


def test_science_modules_import_no_lumerical_work_life() -> None:
    """
    Keep the whole product work life behind the periodic-response port.

    The propagation and geometric science modules, their evidence owner, and
    the aim conduct root reach the solver only through ``PeriodicResponse`` and
    admitted library records it returns. Lanes, sessions, permits, artifacts,
    receipts, recovery, and product execution never appear in their imports.
    """

    science_modules = (
        ROOT / "science" / "metalens" / "propagation_execution.py",
        ROOT / "science" / "metalens" / "geometric_execution.py",
        ROOT / "science" / "metalens" / "evidence.py",
        ROOT / "science" / "metalens" / "conduct.py",
    )
    leaked: dict[str, list[str]] = {}
    for path in science_modules:
        offenders = sorted(
            _lumerical_imported_names(path) & _LUMERICAL_WORK_LIFE_IMPORTS
        )
        if offenders:
            leaked[path.relative_to(ROOT).as_posix()] = offenders

    assert leaked == {}, leaked


def test_the_work_life_ratchet_catches_a_relative_banned_import() -> None:
    """
    The detector must resolve relative imports against the package root.

    Importing ``PeriodicBatchExecution`` from its product module is the natural
    in-package evasion; the resolved path must keep the ``metacraft.``
    prefix so the banned name surfaces instead of being silently dropped (the
    original helper computed ``package_parts`` without that prefix and so
    skipped every relative spelling).
    """

    source = (
        "from ..solvers.lumerical_fdtd.periodic_execution "
        "import PeriodicBatchExecution\n"
    )
    # A module at src/metacraft/_local/probe.py.
    package_parts = ("metacraft", "_local", "probe.py")
    leaked = _lumerical_work_life_names(source, package_parts)

    assert leaked == {"PeriodicBatchExecution"}
    assert leaked & _LUMERICAL_WORK_LIFE_IMPORTS == {"PeriodicBatchExecution"}


def test_the_work_life_ratchet_catches_a_plain_module_import() -> None:
    """
    A plain import of the periodic execution module
    must not evade the detector either.

    The original helper only walked ``ast.ImportFrom``, so a plain module
    import bound the whole work-life module under any alias without tripping
    the ratchet. The detector now walks ``ast.Import`` as well.
    """

    source = (
        "import metacraft.solvers.lumerical_fdtd.periodic_execution "
        "as PeriodicBatchExecution\n"
    )
    package_parts = ("metacraft", "_local", "probe.py")
    leaked = _lumerical_work_life_names(source, package_parts)

    assert leaked == {"PeriodicBatchExecution"}
    assert leaked & _LUMERICAL_WORK_LIFE_IMPORTS == {"PeriodicBatchExecution"}


def test_the_work_life_ratchet_leaves_type_checking_imports_alone() -> None:
    """
    A type-only import behind ``if TYPE_CHECKING:`` is erased at runtime.

    It is not a work-life reach, so the detector must exclude it. This keeps
    the ratchet honest about runtime leakage while permitting type hints that
    name internal work-life types (e.g. a ``RunDirectory`` annotation).
    """

    source = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from ..solvers.lumerical_fdtd.periodic_execution "
        "import PeriodicBatchExecution\n"
    )
    package_parts = ("metacraft", "_local", "probe.py")
    leaked = _lumerical_work_life_names(source, package_parts)

    assert leaked == set()


def test_the_work_life_ratchet_leaves_typing_qualified_type_checking_alone() -> None:
    """
    ``if typing.TYPE_CHECKING:`` is the same runtime guard as the bare form.

    The qualified spelling must also exclude its imports from runtime-leak
    detection. The original guard matched only the bare ``ast.Name`` form, so a
    type-only import under ``typing.TYPE_CHECKING`` was miscounted as a leak.
    """

    source = (
        "import typing\n"
        "if typing.TYPE_CHECKING:\n"
        "    from ..solvers.lumerical_fdtd.periodic_execution "
        "import PeriodicBatchExecution\n"
    )
    package_parts = ("metacraft", "_local", "probe.py")
    leaked = _lumerical_work_life_names(source, package_parts)

    assert leaked == set()


def test_the_work_life_wrapper_derives_package_parts_with_prefix() -> None:
    """
    ``_lumerical_imported_names`` must keep the ``metacraft.`` prefix.

    The unit self-tests call ``_lumerical_work_life_names`` with a hard-coded
    ``package_parts`` tuple, so they cannot catch a regression in the wrapper's
    own parts derivation. Guard the wrapper directly: for a real in-package
    path it must produce the ``metacraft``-prefixed parts the detector
    needs, and the wrapper must agree with the unit helper on the same source.
    """

    conduct = ROOT / "science" / "metalens" / "conduct.py"

    parts = _package_parts(conduct)
    assert parts == ("metacraft", "science", "metalens", "conduct.py")

    direct = _lumerical_work_life_names(
        conduct.read_text(encoding="utf-8-sig"),
        parts,
    )
    assert _lumerical_imported_names(conduct) == direct


def test_public_lumerical_package_exports_no_sweep_implementation() -> None:
    """
    The package exposes only response, config, and environment interfaces.

    Product execution, sessions, lanes, receipts, and artifact restoration
    stay Adapter-internal.
    """

    package = importlib.import_module("metacraft.solvers.lumerical_fdtd")
    assert not hasattr(package, "open_sweep")
    for internal in (
        "JonesReceiptsIncomplete",
        "PeriodicBatchExecution",
        "PropagationReceiptsIncomplete",
        "RunDirectory",
        "SessionPool",
        "WorkRecord",
        "WorkstationExecution",
        "restore_jones_library",
        "restore_propagation_library",
    ):
        assert not hasattr(package, internal), internal
