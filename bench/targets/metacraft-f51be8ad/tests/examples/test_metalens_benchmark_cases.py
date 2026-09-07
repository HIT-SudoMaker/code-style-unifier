from __future__ import annotations

from pathlib import Path
import ast
import subprocess
import sys

import pytest

import examples
from examples import (
    MetalensBenchmarkCase,
    metalens_benchmark_cases,
    select_metalens_benchmark_case,
)
from examples.metalens_benchmark.catalogue import restore_metalens_benchmark_case
from metacraft.authority import Document


ROOT = Path(__file__).parents[2]


def test_public_catalogue_has_one_stable_four_case_order() -> None:
    cases = metalens_benchmark_cases()

    assert tuple(case.name for case in cases) == (
        "mcclung-2024-low-na-propagation",
        "yang-2018-low-na-geometric",
        "arbabi-2015-high-na-propagation",
        "khorasaninejad-2016-high-na-geometric",
    )
    assert tuple(select_metalens_benchmark_case(case.name) for case in cases) == cases
    assert tuple(case.brief.aspect_limit for case in cases) == (8, 8, 8, 8)


def test_public_selection_rejects_wrong_and_unknown_names() -> None:
    with pytest.raises(TypeError, match="benchmark_case_name_required"):
        select_metalens_benchmark_case(1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="benchmark_case_name_invalid"):
        select_metalens_benchmark_case("unknown-case")


def test_public_cases_round_trip_only_exact_canonical_documents() -> None:
    cases = metalens_benchmark_cases()
    for case in cases:
        restored = restore_metalens_benchmark_case(
            Document.from_bytes(case.document().to_bytes())
        )
        assert restored is case
        assert restored.identity == case.identity

        changed = dict(case.document().values)
        changed["selected_device"] = "retired duplicate"
        with pytest.raises(
            ValueError,
            match="metalens_benchmark_case_document_mismatch",
        ):
            restore_metalens_benchmark_case(
                Document(case.document().schema_identifier, changed)
            )

    retired = dict(cases[0].document().values)
    retired["name"] = "yun-2025-low-na-propagation"
    with pytest.raises(
        ValueError,
        match="metalens_benchmark_case_document_mismatch",
    ):
        restore_metalens_benchmark_case(
            Document(cases[0].document().schema_identifier, retired)
        )


def test_public_codec_rejects_retired_and_foreign_schemas() -> None:
    case = metalens_benchmark_cases()[0]
    for schema in (
        "metacraft.examples.metalens_benchmark_case",
        "metacraft.examples.metalens_benchmark_comparison",
        "metacraft.science.metalens.case",
    ):
        with pytest.raises(
            ValueError,
            match="metalens_benchmark_case_schema_invalid",
        ):
            restore_metalens_benchmark_case(
                Document(schema, case.document().values)
            )


def test_public_surface_exposes_only_the_case_cadence() -> None:
    assert examples.__all__ == [
        "MetalensBenchmarkCase",
        "metalens_benchmark_cases",
        "select_metalens_benchmark_case",
    ]
    assert not hasattr(examples, "restore_metalens_benchmark_case")
    assert not hasattr(MetalensBenchmarkCase, "from_document")
    assert not {
        "PublishedPlatform",
        "PublishedComparison",
        "PublishedMetric",
        "PublishedMeasureDefinition",
        "ComparisonDisposition",
    }.intersection(vars(examples))
    assert all(
        callable(getattr(MetalensBenchmarkCase, operation, None))
        or isinstance(getattr(MetalensBenchmarkCase, operation, None), property)
        for operation in ("identity", "document", "compare")
    )


def test_case_document_keeps_blind_brief_and_new_reference_contract() -> None:
    for case in metalens_benchmark_cases():
        values = case.document().values
        assert case.document().schema_identifier == (
            "metacraft.examples.metalens_benchmark_reference_case"
        )
        assert case.brief.cell_period_nm is None
        assert case.brief.atom_height_nm is None
        assert set(values) == {
            "alignment",
            "brief",
            "contract",
            "name",
            "reference",
        }


def test_case_interface_has_no_shadow_paper_or_result_classification() -> None:
    assert "selected_device" not in MetalensBenchmarkCase.__dataclass_fields__
    assert "result_family" not in MetalensBenchmarkCase.__dataclass_fields__


def test_offline_inspection_loads_no_execution_dependency(tmp_path: Path) -> None:
    source = ROOT / "src"
    script = (
        "from pathlib import Path; import sys; sys.dont_write_bytecode = True; "
        f"sys.path[:0] = [{str(ROOT)!r}, {str(source)!r}]; "
        "before = tuple(Path.cwd().iterdir()); "
        "from examples import metalens_benchmark_cases; "
        "assert len(metalens_benchmark_cases()) == 4; "
        "forbidden = ('torch', 'metacraft._authority', "
        "'metacraft.authority.interface', 'metacraft.field', "
        "'metacraft.science.compile', 'metacraft.science.conduct', "
        "'metacraft.science.metalens.result', 'metacraft.solvers', "
        "'metacraft.workstation'); "
        "loaded = tuple(name for name in sys.modules if any("
        "name == item or name.startswith(item + '.') for item in forbidden)); "
        "assert loaded == (), loaded; assert tuple(Path.cwd().iterdir()) == before"
    )

    completed = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_inspection_script_prints_four_canonical_documents() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "inspect_metalens_benchmarks.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert len(completed.stdout.splitlines()) == 4


def test_production_imports_no_example_module() -> None:
    importers: list[str] = []
    production = ROOT / "src" / "metacraft"
    for path in production.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            names: tuple[str, ...]
            if isinstance(node, ast.Import):
                names = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = () if node.module is None else (node.module,)
            else:
                continue
            if any(name == "examples" or name.startswith("examples.") for name in names):
                importers.append(path.relative_to(production).as_posix())
    assert importers == []


def test_retired_benchmark_owners_and_staging_package_are_absent() -> None:
    assert not (ROOT / "examples" / "metalens_benchmark_cases.py").exists()
    assert not tuple((ROOT / "examples" / "_metalens_benchmark").glob("*.py"))
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "examples").rglob("*.py")
    )
    for retired in (
        "class PublishedPlatform",
        "class PublishedComparison",
        "class PublishedMetric",
        "class PublishedMeasureDefinition",
        "fidelity_notes",
        "private_metalens_benchmark_cases",
    ):
        assert retired not in source
