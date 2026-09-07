from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import subprocess
import sys

from metacraft.authority import (
    Authority,
    Document,
    Proposal,
    Revision,
    Structure,
)


def test_source_namespace_matches_the_distribution_name() -> None:
    installed = importlib.util.find_spec("metacraft")
    replaced = importlib.util.find_spec("metacraft" + "_" + "next")

    assert installed is not None
    assert replaced is None


def test_typed_record_round_trips_through_the_frozen_authority(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "workspace")
    document = Document(
        schema_identifier="metacraft.test.note",
        values={"count": 1, "name": "violet focus"},
    )

    decision = authority.decide(Proposal.record(document), at=Revision.root())

    assert decision.admitted
    assert decision.body_reference is not None
    stored = Document.from_bytes(authority.fetch(decision.body_reference))
    assert stored == document
    assert authority.view().revision == decision.resulting_revision


def test_prefix_property_names_cross_the_authority_boundary(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "workspace")
    document = Document(
        "x",
        {"silicon": 1, "silicon dioxide": 2},
    )

    decision = authority.decide(Proposal.record(document), at=Revision.root())

    assert decision.admitted
    assert decision.body_reference is not None
    assert authority.fetch(decision.body_reference) == document.to_bytes()


def test_stale_revision_is_an_explicit_rejection(tmp_path: Path) -> None:
    authority = Authority(tmp_path / "workspace")
    first = authority.decide(
        Proposal.record(Document("metacraft.test.note", {"name": "first"})),
        at=Revision.root(),
    )

    stale = authority.decide(
        Proposal.record(Document("metacraft.test.note", {"name": "second"})),
        at=Revision.root(),
    )

    assert first.admitted
    assert not stale.admitted
    assert stale.findings == ("revision_mismatch",)
    assert stale.resulting_revision == first.resulting_revision


def test_structured_record_closes_its_exact_references(tmp_path: Path) -> None:
    authority = Authority(tmp_path / "workspace")
    source = authority.decide(
        Proposal.record(Document("metacraft.test.source", {"name": "source"})),
        at=Revision.root(),
    )
    assert source.body_reference is not None
    document = Document(
        "metacraft.test.derived",
        {"source": source.body_reference.as_mapping()},
    )
    structure = Structure.for_document(
        document,
        references=(source.body_reference,),
    )
    registered = authority.decide(
        Proposal.structure(structure),
        at=source.resulting_revision,
    )
    assert registered.body_reference is not None

    recorded = authority.decide(
        Proposal.structured(
            document,
            structure_reference=registered.body_reference,
            references=(source.body_reference,),
        ),
        at=registered.resulting_revision,
    )

    assert recorded.admitted
    assert recorded.body_reference is not None
    assert authority.fetch(recorded.body_reference) == document.to_bytes()


def test_native_extension_has_one_python_import_site() -> None:
    source_root = Path(__file__).parents[2] / "src" / "metacraft"
    imports = []
    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        if any(_imports_native_authority(node) for node in ast.walk(tree)):
            imports.append(path.relative_to(source_root).as_posix())

    assert imports == ["authority/interface.py"]


def _imports_native_authority(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(
            alias.name == "metacraft._authority"
            for alias in node.names
        )
    if isinstance(node, ast.ImportFrom):
        return (
            any(alias.name == "_authority" for alias in node.names)
            or node.module == "_authority"
            or (
                node.module is not None
                and node.module.endswith("._authority")
            )
        )
    if isinstance(node, ast.Call) and node.args:
        target = node.func
        dynamic_import = (
            isinstance(target, ast.Name)
            and target.id == "__import__"
        ) or (
            isinstance(target, ast.Attribute)
            and target.attr == "import_module"
        )
        argument = node.args[0]
        return (
            dynamic_import
            and isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and (
                argument.value == "_authority"
                or argument.value.endswith("._authority")
            )
        )
    return False


def test_science_import_does_not_load_the_native_extension() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import metacraft.science; "
                "assert 'metacraft._authority' not in sys.modules"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_workstation_is_the_only_local_process_policy() -> None:
    source_root = Path(__file__).parents[2] / "src" / "metacraft"
    workstation = source_root / "workstation"
    workstation_trees = tuple(
        ast.parse(path.read_text(encoding="utf-8-sig"))
        for path in workstation.rglob("*.py")
    )
    workstation_imports = {
        alias.name.casefold()
        for tree in workstation_trees
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").casefold()
        for tree in workstation_trees
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert all(
        product not in imported
        for imported in workstation_imports
        for product in ("lumerical", "cst", "comsol")
    )

    solver_trees = tuple(
        ast.parse(path.read_text(encoding="utf-8-sig"))
        for path in (source_root / "solvers").rglob("*.py")
    )
    called = {
        (
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else node.func.id
        )
        for tree in solver_trees
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    forbidden = {
        "AssignProcessToJobObject",
        "CreateJobObjectW",
        "GetNumaAvailableMemoryNodeEx",
        "SetInformationJobObject",
        "SetProcessDefaultCpuSets",
        "SetThreadSelectedCpuSets",
    }
    assert called.isdisjoint(forbidden)
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.level == 3
        and node.module == "workstation"
        for tree in solver_trees
        for node in ast.walk(tree)
    )
