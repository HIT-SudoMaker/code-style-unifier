from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).parents[2]
PACKAGE = ROOT / "src" / "metacraft"
AUTHORITY_PACKAGE = PACKAGE / "authority"

# Raw view-mapping keys that only the authority Adapter may parse. Every other
# caller reads typed ``Current``, ``AdmittedDecision``, and ``Permit`` values.
RETIRED_VIEW_KEYS = frozenset(
    {
        "state",
        "close_reason",
        "key",
        "body_reference",
        "receipt_body_reference",
        "superseded",
    }
)


def _production_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in PACKAGE.rglob("*.py")
            if AUTHORITY_PACKAGE not in path.parents
        )
    )


def _retired_key_violations(tree: ast.Module) -> list[str]:
    """
    Detect subscript and ``.get()`` access on retired raw view keys.
    """

    violations: list[str] = []
    for node in ast.walk(tree):
        literal = _string_literal(node)
        if literal is None or literal not in RETIRED_VIEW_KEYS:
            continue
        if _is_subscript_key(node) or _is_get_call_key(node):
            violations.append(literal)
    return violations


def _string_literal(node: ast.AST) -> str | None:
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
    ):
        return node.value
    return None


def _is_subscript_key(node: ast.AST) -> bool:
    parent_context = getattr(node, "_parent", None)
    return isinstance(parent_context, ast.Subscript) and parent_context.slice is node


def _is_get_call_key(node: ast.AST) -> bool:
    parent_context = getattr(node, "_parent", None)
    return (
        isinstance(parent_context, ast.Call)
        and isinstance(parent_context.func, ast.Attribute)
        and parent_context.func.attr == "get"
        and bool(parent_context.args)
        and parent_context.args[0] is node
    )


def _annotate_parents(tree: ast.Module) -> None:
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child._parent = parent  # type: ignore[attr-defined]


def test_no_caller_outside_the_authority_adapter_parses_raw_view_keys() -> None:
    """
    View mappings decode once inside the Adapter; callers use typed values.
    """

    found: dict[str, list[str]] = {}
    for path in _production_files():
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        _annotate_parents(tree)
        violations = _retired_key_violations(tree)
        if violations:
            found[path.relative_to(PACKAGE).as_posix()] = violations

    assert found == {}, found


def test_retired_key_detector_recognizes_every_forbidden_form() -> None:
    """
    The ratchet is sensitive to every forbidden view-key access form.
    """

    tree = ast.parse(
        "def consumer(permit, decision):\n"
        '    return permit["state"], decision.get("body_reference")\n'
    )
    _annotate_parents(tree)

    assert sorted(_retired_key_violations(tree)) == [
        "body_reference",
        "state",
    ]
