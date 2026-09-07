from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
from pathlib import Path


ROOT = Path(__file__).parents[2]
PACKAGE = ROOT / "src" / "metacraft"

AUDITED_RETIRED_IDENTIFIERS = frozenset(
    {
        "AcceptFinding",
        "AdvisedHeight",
        "AdvisedPeriod",
        "BriefHeightConstraint",
        "BriefIncomplete",
        "BriefPeriodConstraint",
        "CellPolicy",
        "ConsiderAdvice",
        "EvidenceFact",
        "FieldObservation",
        "FieldPlane",
        "FieldQualification",
        "FocalEvaluation",
        "ORIENTATIONS_SCHEMA",
        "Orientations",
        "PhaseMethod",
        "ProofObligation",
        "RESULT_CONVENTION",
        "ScientificTask",
        "StudyMethodView",
        "_closed",
        "_enough_candidates",
        "_replacing",
        "_tree_stopped",
        "added",
        "allowed_capabilities",
        "assign_oriented",
        "assigned",
        "capability_for",
        "certified",
        "check_period_advice",
        "close_study",
        "compile_proof",
        "derive_orientations",
        "exact_evidence",
        "force",
        "form_study",
        "geometric_surface_cautions",
        "geometric_surface_transform",
        "holds",
        "is_vector",
        "job_closed",
        "kx",
        "ky",
        "kz",
        "matching_distance_m",
        "matching_field",
        "metalens_design",
        "metalens_relationship_for",
        "method_view",
        "obligation",
        "obligations",
        "optional",
        "orientations",
        "orientations_reference",
        "period_limits",
        "phase_method",
        "pointwise_surface_table",
        "propagate_channel_fields",
        "propagate_scalar_field",
        "range_for",
        "renewal_required",
        "tangential_surface_field",
        "terminals",
        "validate_objectives",
        "verify_sample",
        "with_envelope",
        "with_numerical_aperture",
    }
)

FORBIDDEN_RESPONSIBILITY_IMPORTS = {
    "conduct": frozenset(
        {
            "_local",
            "advice",
            "local",
            "solvers",
            "work_execution",
            "workstation",
        }
    ),
    "advice": frozenset(
        {"_local", "local", "work_execution", "solvers", "workstation"}
    ),
    "local": frozenset({"advice", "work_execution", "workstation"}),
    "work_execution": frozenset(
        {"_local", "advice", "local", "solvers", "workstation"}
    ),
    # Product adapters may coordinate work execution and must delegate
    # placement to workstation. They may not depend on composition or advice.
    "solvers": frozenset({"_local", "advice", "local"}),
    "workstation": frozenset(
        {
            "_local",
            "advice",
            "local",
            "work_execution",
            "science",
            "solvers",
        }
    ),
}


def _production_files() -> tuple[Path, ...]:
    return tuple(sorted(PACKAGE.rglob("*.py")))


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"))


def _import_roots(
    node: ast.Import | ast.ImportFrom,
    path: Path,
) -> set[str]:
    """
    Resolve absolute and relative imports to package responsibilities.
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


def _responsibility_imports(tree: ast.Module, path: Path) -> set[str]:
    return {
        root
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for root in _import_roots(node, path)
    }


def _source_identifiers(tree: ast.AST) -> set[str]:
    """
    Return source-language names without inspecting constants or mapping keys.
    """

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef),
        ):
            names.add(node.name)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.keyword) and node.arg is not None:
            names.add(node.arg)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.rsplit(".", 1)[-1])
    return names


def _annotation_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_scalar_bool_annotation(node: ast.AST | None) -> bool:
    if node is None:
        return False
    if _annotation_name(node) == "bool":
        return True
    if isinstance(node, ast.Constant):
        return node.value == "bool"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _is_scalar_bool_annotation(node.left) or _is_scalar_bool_annotation(
            node.right
        )
    if isinstance(node, ast.Subscript) and _annotation_name(node.value) in {
        "Annotated",
        "Optional",
        "Union",
    }:
        return any(
            _is_scalar_bool_annotation(child)
            for child in (
                node.slice,
                *ast.iter_child_nodes(node.slice),
            )
        )
    return False


def _is_numpy_bool_array_annotation(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    if _annotation_name(node.value) != "NDArray":
        return False
    return any(_annotation_name(child) == "bool_" for child in ast.walk(node.slice))


def _is_positive_boolean_name(name: str) -> bool:
    return name.lstrip("_").startswith(("is_", "has_", "can_", "should_"))


def _assigned_names(target: ast.AST) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, ast.Attribute):
        return (target.attr,)
    if isinstance(target, (ast.List, ast.Tuple)):
        return tuple(name for item in target.elts for name in _assigned_names(item))
    return ()


def _is_boolean_expression(
    node: ast.AST,
    bool_callables: frozenset[str],
) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, bool)
    if isinstance(node, ast.Compare):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return True
    if isinstance(node, ast.BoolOp):
        return all(
            _is_boolean_expression(value, bool_callables) for value in node.values
        )
    if isinstance(node, ast.BinOp) and isinstance(
        node.op,
        (ast.BitAnd, ast.BitOr, ast.BitXor),
    ):
        return all(
            _is_boolean_expression(value, bool_callables)
            for value in (node.left, node.right)
        )
    if isinstance(node, ast.Name):
        return _is_positive_boolean_name(node.id)
    if isinstance(node, ast.Attribute):
        return _is_positive_boolean_name(node.attr)
    if isinstance(node, ast.Call):
        called = _annotation_name(node.func)
        return called in {"all", "any", "bool"} or (
            called is not None
            and (called in bool_callables or _is_positive_boolean_name(called))
        )
    return False


@dataclass(frozen=True, order=True)
class _BooleanFinding:
    line: int
    kind: str
    name: str

    def label(self) -> str:
        return f"{self.kind}:{self.name}@{self.line}"


def _is_frozen_authority_admission(
    path: Path,
    classes: tuple[str, ...],
    name: str,
) -> bool:
    """
    Preserve only the exact Authority protocol predicate frozen by the spec.
    """

    return (
        path.as_posix().endswith("authority/protocol.py")
        and classes == ("Decision",)
        and name == "admitted"
    )


def _boolean_findings(
    tree: ast.Module,
    *,
    path: Path,
) -> tuple[_BooleanFinding, ...]:
    """
    Find Boolean values whose source names do not state positive polarity.

    The inference is deliberately bounded to annotations, Boolean literals,
    explicit Boolean expressions, reviewed mask names, and the three ambiguous
    predicate names called out by the migration audit.
    """

    findings: set[_BooleanFinding] = set()
    classes: list[str] = []
    scopes: list[str] = ["module"]
    bool_callables = frozenset(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
        and _is_scalar_bool_annotation(node.returns)
    )

    def remember(name: str, kind: str, line: int) -> None:
        if not _is_positive_boolean_name(name):
            findings.add(_BooleanFinding(line, kind, name))

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            classes.append(node.name)
            scopes.append("class")
            for statement in node.body:
                self.visit(statement)
            scopes.pop()
            classes.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_function(node)

        def visit_AsyncFunctionDef(
            self,
            node: ast.AsyncFunctionDef,
        ) -> None:
            self._visit_function(node)

        def _visit_function(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> None:
            if (
                node.name in {"admitted", "complete", "fresh_at"}
                and _is_scalar_bool_annotation(node.returns)
                and not _is_frozen_authority_admission(
                    path,
                    tuple(classes),
                    node.name,
                )
            ):
                remember(node.name, "predicate", node.lineno)

            arguments = (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
            for argument in arguments:
                if _is_scalar_bool_annotation(argument.annotation):
                    remember(argument.arg, "parameter", argument.lineno)
                if _is_numpy_bool_array_annotation(argument.annotation):
                    remember(argument.arg, "mask_parameter", argument.lineno)
                if argument.arg == "mask":
                    remember(argument.arg, "reviewed_mask", argument.lineno)

            scopes.append("function")
            for statement in node.body:
                self.visit(statement)
            scopes.pop()

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            if scopes[-1] not in {"class", "function"}:
                return
            names = _assigned_names(node.target)
            if _is_scalar_bool_annotation(node.annotation):
                kind = "field" if scopes[-1] == "class" else "local_annotation"
                for name in names:
                    remember(name, kind, node.lineno)
            if _is_numpy_bool_array_annotation(node.annotation):
                kind = "mask_field" if scopes[-1] == "class" else "mask_local"
                for name in names:
                    remember(name, kind, node.lineno)

        def visit_Assign(self, node: ast.Assign) -> None:
            if scopes[-1] != "function":
                return
            names = tuple(
                name for target in node.targets for name in _assigned_names(target)
            )
            for name in names:
                if _is_boolean_expression(node.value, bool_callables):
                    kind = (
                        "private_attribute"
                        if name.startswith("_")
                        else "reviewed_local"
                    )
                    remember(name, kind, node.lineno)
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "mask":
                    remember(target.id, "reviewed_mask", node.lineno)

    Visitor().visit(tree)
    return tuple(sorted(findings))


def test_identifier_audit_reads_source_names_not_durable_strings() -> None:
    """
    Names in expressions are governed; strings and wire keys remain opaque.
    """

    tree = ast.parse(
        "retired_identifier = 1\n"
        "owner.retired_attribute\n"
        "operation(retired_keyword=True)\n"
        "payload = {'stable_wire_key': 'retired_identifier'}\n"
        "native_name = 'retired_attribute'\n"
    )
    governed = {
        "retired_identifier",
        "retired_attribute",
        "retired_keyword",
        "stable_wire_key",
    }

    assert _source_identifiers(tree) & governed == {
        "retired_identifier",
        "retired_attribute",
        "retired_keyword",
    }


def test_boolean_audit_is_sensitive_to_types_and_reviewed_scopes() -> None:
    """
    Scalar flags and masks are governed without treating every noun as a flag.
    """

    tree = ast.parse(
        "from dataclasses import dataclass\n"
        "from numpy.typing import NDArray\n"
        "import numpy\n"
        "@dataclass\n"
        "class Flags:\n"
        "    complete: bool\n"
        "    occupied: NDArray[numpy.bool_]\n"
        "    is_ready: bool\n"
        "def inspect(optional: bool, is_present: bool, allowed: set[str]):\n"
        "    assigned = False\n"
        "    self._closed = True\n"
        "    pupil = radius <= 1\n"
        "    selected = (radius <= 1) & (radius >= 0)\n"
        "    mask = occupied\n"
        "    payload = {'complete': True, 'admitted': False}\n"
    )

    findings = _boolean_findings(
        tree,
        path=PACKAGE / "science" / "synthetic.py",
    )

    assert {finding.name for finding in findings} == {
        "_closed",
        "assigned",
        "complete",
        "mask",
        "occupied",
        "optional",
        "pupil",
        "selected",
    }
    assert "allowed" not in {finding.name for finding in findings}
    assert "is_present" not in {finding.name for finding in findings}
    assert "is_ready" not in {finding.name for finding in findings}


def test_ambiguous_predicates_are_scoped_by_type_and_owner() -> None:
    """
    Authority admission stays frozen; other Boolean admission/freshness does not.
    """

    authority = ast.parse(
        "class Decision:\n" "    def admitted(self) -> bool:\n" "        return True\n"
    )
    solver = ast.parse(
        "class Receipt:\n"
        "    def admitted(self) -> bool:\n"
        "        return True\n"
        "def fresh_at(value: object) -> bool:\n"
        "    return True\n"
        "def complete(value: object) -> bool | None:\n"
        "    return None\n"
        "allowed = {'not': 'a boolean'}\n"
    )

    assert (
        _boolean_findings(
            authority,
            path=PACKAGE / "authority" / "protocol.py",
        )
        == ()
    )
    assert {
        finding.name
        for finding in _boolean_findings(
            solver,
            path=PACKAGE / "solvers" / "synthetic.py",
        )
    } == {"admitted", "complete", "fresh_at"}


def test_production_contains_no_audited_retired_identifier() -> None:
    """
    The final migration has one source vocabulary and no compatibility names.
    """

    found: dict[str, list[str]] = {}
    for path in _production_files():
        retired = sorted(_source_identifiers(_tree(path)) & AUDITED_RETIRED_IDENTIFIERS)
        if retired:
            found[path.relative_to(PACKAGE).as_posix()] = retired

    assert found == {}


def test_production_booleans_state_positive_meaning() -> None:
    """
    Typed flags, reviewed locals/private attributes, masks, and ambiguous
    predicates all name a complete positive proposition.
    """

    found: dict[str, list[str]] = {}
    for path in _production_files():
        findings = _boolean_findings(_tree(path), path=path)
        if findings:
            found[path.relative_to(PACKAGE).as_posix()] = [
                finding.label() for finding in findings
            ]

    assert found == {}


def test_production_does_not_depend_on_external_examples() -> None:
    """
    Concrete cases depend on MetaCraft; production never imports them back.
    """

    importers = {
        path.relative_to(PACKAGE).as_posix()
        for path in _production_files()
        if "examples" in _responsibility_imports(_tree(path), path)
    }

    assert importers == set()
    assert not (PACKAGE / "examples").exists()


def test_external_examples_keep_the_four_case_identity_seam() -> None:
    """
    External benchmark cases retain their exact Brief identities.
    """

    from examples import (
        metalens_benchmark_cases,
    )

    cases = metalens_benchmark_cases()
    assert tuple(case.name for case in cases) == (
        "mcclung-2024-low-na-propagation",
        "yang-2018-low-na-geometric",
        "arbabi-2015-high-na-propagation",
        "khorasaninejad-2016-high-na-geometric",
    )
    assert tuple(
        "sha256:" + hashlib.sha256(case.brief.canonical_bytes()).hexdigest()
        for case in cases
    ) == (
        "sha256:8a1f85002e8f36bc96fac9d17bc69faf996234a83eb342d368bdf2f592dcc9bb",
        "sha256:db9f07d76dc877beecd1bd6abcfd0614b67ce0e808aa1fab243b907d7d373822",
        "sha256:4acb432c89ed7bc49165ea22610b5177618e286897a88e7483be48dba210bdc0",
        "sha256:a57356b070cc403fbb63e6ebc4d6d703b2a06f79e49a6de80a732a0f527cf825",
    )


def test_dependency_rule_allows_solver_to_use_workstation_only_one_way() -> None:
    """
    A solver may borrow host placement; workstation may not import a product.
    """

    solver_path = PACKAGE / "solvers" / "synthetic.py"
    workstation_path = PACKAGE / "workstation" / "synthetic.py"
    solver_imports = _responsibility_imports(
        ast.parse("from ..workstation import plan\n"),
        solver_path,
    )
    workstation_imports = _responsibility_imports(
        ast.parse("from ..solvers import product\n"),
        workstation_path,
    )

    assert (solver_imports & FORBIDDEN_RESPONSIBILITY_IMPORTS["solvers"]) == set()
    assert (workstation_imports & FORBIDDEN_RESPONSIBILITY_IMPORTS["workstation"]) == {
        "solvers"
    }


def test_composition_and_adapter_dependencies_keep_one_direction() -> None:
    """
    Each outer owner names the inward responsibilities it must not import.
    """

    owned_paths = {
        "conduct": (
            PACKAGE / "science" / "conduct.py",
            PACKAGE / "science" / "metalens" / "conduct.py",
        ),
        "advice": tuple(sorted((PACKAGE / "advice").rglob("*.py"))),
        "work_execution": (PACKAGE / "work_execution.py",),
        "solvers": tuple(sorted((PACKAGE / "solvers").rglob("*.py"))),
        "workstation": tuple(sorted((PACKAGE / "workstation").rglob("*.py"))),
    }
    found: dict[str, list[str]] = {}
    for owner, paths in owned_paths.items():
        forbidden = FORBIDDEN_RESPONSIBILITY_IMPORTS[owner]
        for path in paths:
            crossed = sorted(_responsibility_imports(_tree(path), path) & forbidden)
            if crossed:
                found[path.relative_to(PACKAGE).as_posix()] = crossed

    assert found == {}


def test_root_authority_surface_remains_exact() -> None:
    """
    Naming convergence cannot enlarge or rename the installed root seam.
    """

    import metacraft
    from metacraft.authority.interface import Authority

    public_callables = {
        name
        for name, member in Authority.__dict__.items()
        if not name.startswith("_") and callable(member)
    }

    assert metacraft.__all__ == ["Authority", "compile_study", "conduct"]
    assert public_callables == {"check", "view", "fetch", "decide"}
