from __future__ import annotations

import ast
from collections import defaultdict
import importlib
import importlib.util
import inspect
from pathlib import Path
import re
import subprocess
from types import ModuleType
from urllib.parse import unquote

import pytest

from metacraft.solvers.lumerical_fdtd.artifacts import WorkRecord


ROOT = Path(__file__).parents[2]
PACKAGE = ROOT / "src" / "metacraft"
SCHEMA_PREFIXES = (
    "metacraft.diagnostic.",
    "metacraft.science.",
)
RETIRED_MODULES = frozenset(
    {
        "metacraft.field.focus",
        "metacraft.field.metrics",
        "metacraft.science.aperture",
        "metacraft.science.height",
        "metacraft.science.material",
        "metacraft.science.model",
        "metacraft.science.routes",
        "metacraft.solvers.lumerical_fdtd.cell",
    }
)

_RETIRED_PROVIDER_PATHS = (
    PACKAGE / "advice" / "__init__.py",
    PACKAGE / "advice" / "adviser.py",
    PACKAGE / "advice" / "environment.py",
    PACKAGE / "advice" / "model.py",
    PACKAGE / "science" / "design_advice.py",
    PACKAGE / "science" / "wording.py",
    ROOT / ".env.api.example",
    ROOT / "tests" / "advice" / "fakes.py",
    ROOT / "tests" / "advice" / "test_adviser.py",
    ROOT / "tests" / "advice" / "test_metalens_consultation.py",
    ROOT / "tests" / "advice" / "test_wording_live.py",
)
_RETIRED_PROVIDER_IDENTIFIERS = frozenset(
    {
        "AdviceStatus",
        "DesignAdvice",
        "LlmConfig",
        "OpenAICompatibleAdviser",
        "Suggestion",
        "WordingReview",
    }
)
_MODEL_TRANSPORT_MODULES = frozenset(
    {
        "anthropic",
        "google.generativeai",
        "litellm",
        "openai",
    }
)
_GENERIC_HTTP_TRANSPORT_MODULES = frozenset(
    {
        "aiohttp",
        "httpx",
        "requests",
        "urllib.request",
    }
)
_CONSULTATION_CONTRACT_PATHS = frozenset(
    {
        PACKAGE / "command.py",
        PACKAGE / "science" / "conduct.py",
        PACKAGE / "science" / "consultation.py",
        PACKAGE / "science" / "metalens" / "conduct.py",
        PACKAGE / "science" / "metalens" / "consultation.py",
        PACKAGE / "science" / "metalens" / "_closed_advice.py",
        PACKAGE / "science" / "metalens" / "period_advice.py",
        PACKAGE / "science" / "metalens" / "height_advice.py",
    }
)
_PROVIDER_FIELDS = frozenset(
    {
        "api_key",
        "base_url",
        "endpoint_identity",
        "failure",
        "model",
        "prompt",
        "provider",
        "raw_response",
        "status",
        "synthetic",
    }
)


def test_retired_provider_road_is_absent() -> None:
    """The harness cutover leaves no embedded model-transport alternative."""

    assert tuple(path for path in _RETIRED_PROVIDER_PATHS if path.exists()) == ()

    retired_names: dict[str, list[str]] = {}
    forbidden_imports: dict[str, list[str]] = {}
    forbidden_literals: dict[str, list[str]] = {}
    for path in _production_files():
        relative = path.relative_to(PACKAGE).as_posix()
        tree = _tree(path)
        names = sorted(
            {
                node.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Name)
                and node.id in _RETIRED_PROVIDER_IDENTIFIERS
            }
            | {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                and node.name in _RETIRED_PROVIDER_IDENTIFIERS
            }
        )
        if names:
            retired_names[relative] = names

        imported_modules = set(_imports(path))
        imports = sorted(
            {
                imported
                for imported in imported_modules
                if imported == "metacraft.command"
                or imported.startswith("metacraft.command.")
            }
            | _forbidden_provider_imports(path, imported_modules)
        )
        if imports:
            forbidden_imports[relative] = imports

        literals = sorted(
            {
                node.value
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and (
                    "METACRAFT_LLM_" in node.value
                    or node.value == "advice_live"
                    or node.value
                    in {
                        "metacraft.advice.design",
                        "metacraft.advice.height",
                        "metacraft.advice.period",
                        "metacraft.advice.wording",
                    }
                )
            }
        )
        if literals:
            forbidden_literals[relative] = literals

    assert retired_names == {}
    assert forbidden_imports == {}
    assert forbidden_literals == {}

    governed_text = "\n".join(
        path.read_text(encoding="utf-8-sig")
        for path in (
            ROOT / "pyproject.toml",
            ROOT / "CONTEXT.md",
            ROOT / "DESIGN.md",
            ROOT / "SCIENCE.md",
            ROOT / "DEVELOPMENT.md",
        )
    )
    assert "METACRAFT_LLM_" not in governed_text
    assert "advice_live" not in governed_text
    assert ".env` is reserved for LLM/API credentials" not in governed_text

    harness_decision = (
        ROOT / "docs" / "adr" / "0021-let-harnesses-answer-grounded-consultations.md"
    ).read_text(encoding="utf-8")
    decision_index = (ROOT / "docs" / "adr" / "README.md").read_text(encoding="utf-8")
    assert "supersedes only ADR 0003's clause reserving `.env`" in (harness_decision)
    assert "supersedes only ADR 0003's reservation of `.env`" in (decision_index)

    provider_fields: dict[str, list[str]] = {}
    for path in _CONSULTATION_CONTRACT_PATHS:
        tree = _tree(path)
        found = sorted(_provider_field_names(tree))
        if found:
            provider_fields[path.relative_to(PACKAGE).as_posix()] = found
    assert provider_fields == {}


def _forbidden_provider_imports(
    path: Path,
    imported_modules: set[str],
) -> set[str]:
    """Find embedded model transport without reserving all future HTTP use."""

    forbidden_roots = set(_MODEL_TRANSPORT_MODULES)
    if path == PACKAGE / "command.py" or PACKAGE / "science" in path.parents:
        forbidden_roots.update(_GENERIC_HTTP_TRANSPORT_MODULES)
    return {
        imported
        for imported in imported_modules
        if any(
            imported == module or imported.startswith(f"{module}.")
            for module in forbidden_roots
        )
    }


def _provider_field_names(tree: ast.AST) -> set[str]:
    """Find provider-shaped names at every consultation contract surface."""

    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.arg) and node.arg in _PROVIDER_FIELDS:
            found.add(node.arg)
        elif (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Store)
            and node.id in _PROVIDER_FIELDS
        ):
            found.add(node.id)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Store)
            and node.attr in _PROVIDER_FIELDS
        ):
            found.add(node.attr)
        elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            key = node.slice
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and key.value in _PROVIDER_FIELDS
            ):
                found.add(key.value)
        elif isinstance(node, ast.Dict):
            found.update(
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and key.value in _PROVIDER_FIELDS
            )
    return found


def test_runtime_advice_caches_are_not_science_or_release_inputs() -> None:
    governed = (
        PACKAGE / "science" / "result.py",
        PACKAGE / "science" / "metalens" / "result.py",
        PACKAGE / "science" / "metalens" / "run_projection.py",
    )
    assert all(
        "metacraft.advice" not in path.read_text(encoding="utf-8")
        and "__pycache__" not in path.read_text(encoding="utf-8")
        for path in governed
    )
    assert all("__pycache__" not in path.parts for path in _production_files())


def test_provider_field_ratchet_covers_every_contract_shape() -> None:
    tree = ast.parse(
        """
def answer(provider, *, api_key=None, base_url=None, model=None):
    endpoint_identity = "retired"
    self.prompt = "retired"
    record["raw_response"] = "retired"
    return {"failure": "retired", "status": "retired", "synthetic": False}
"""
    )

    assert _provider_field_names(tree) == {
        "api_key",
        "base_url",
        "endpoint_identity",
        "failure",
        "model",
        "prompt",
        "provider",
        "raw_response",
        "status",
        "synthetic",
    }


def test_generic_http_is_only_forbidden_inside_consultation_contracts() -> None:
    imports = {"httpx", "urllib.request"}

    assert (
        _forbidden_provider_imports(
            PACKAGE / "science" / "consultation.py",
            imports,
        )
        == imports
    )
    assert _forbidden_provider_imports(PACKAGE / "command.py", imports) == imports
    assert (
        _forbidden_provider_imports(
            PACKAGE / "science" / "metalens" / "consultation.py",
            imports,
        )
        == imports
    )
    assert (
        _forbidden_provider_imports(
            PACKAGE / "materials" / "refractive_index_source.py",
            imports,
        )
        == set()
    )
    assert _forbidden_provider_imports(
        PACKAGE / "materials" / "refractive_index_source.py",
        {"anthropic", "openai"},
    ) == {"anthropic", "openai"}


def test_closed_advice_is_private_and_points_inward() -> None:
    """Keep shared closed-record mechanics behind the two public shells."""

    closed_advice = PACKAGE / "science" / "metalens" / "_closed_advice.py"
    module_name = "metacraft.science.metalens._closed_advice"
    shell_modules = {
        "metacraft.science.metalens.height_advice",
        "metacraft.science.metalens.period_advice",
    }

    assert closed_advice.is_file()
    assert not any(
        imported == shell or imported.startswith(f"{shell}.")
        for imported in _imports(closed_advice)
        for shell in shell_modules
    )
    importers = {
        _module(path)
        for path in _production_files()
        if any(
            imported == module_name or imported.startswith(f"{module_name}.")
            for imported in _imports(path)
        )
    }
    assert importers == shell_modules

    package = importlib.import_module("metacraft.science.metalens")
    assert set(package.__all__).isdisjoint(
        {
            "RecommendationFields",
            "RestoredAdviceFields",
            "require_exact_document_bytes",
            "restore_advice_fields",
            "validate_advice_fields",
            "validate_recommendation_fields",
        }
    )


def test_one_canonical_skill_has_two_policy_free_native_routers() -> None:
    """Codex and Claude discover one behavior source through equal routers."""

    canonical = ROOT / "skills" / "metacraft-design" / "SKILL.md"
    routers = (
        ROOT / ".agents" / "skills" / "metacraft-design" / "SKILL.md",
        ROOT / ".claude" / "skills" / "metacraft-design" / "SKILL.md",
    )
    assert canonical.is_file()
    assert all(router.is_file() for router in routers)
    visible = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            *(str(path.relative_to(ROOT)) for path in (canonical, *routers)),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert len(visible) == 3
    assert not _is_ignored(routers[1])
    assert all(
        _is_ignored(ROOT / relative)
        for relative in (
            ".claude/settings.json",
            ".claude/skills/another-skill/SKILL.md",
            ".claude/skills/metacraft-design/README.md",
        )
    )
    assert routers[0].read_bytes() == routers[1].read_bytes()
    router_text = routers[0].read_text(encoding="utf-8")
    assert "../../../skills/metacraft-design/SKILL.md" in router_text
    assert all(
        word not in router_text.casefold()
        for word in (
            "candidate",
            "height",
            "material",
            "period",
            "solver",
            "wavelength",
        )
    )

    skill_text = canonical.read_text(encoding="utf-8")
    assert (
        ".\\metacraft.exe conduct --brief <brief> --application-root "
        "<application-root> --material-library <material-library>"
        in " ".join(skill_text.split())
    )
    assert tuple(
        heading in skill_text
        for heading in ("## Anchor", "## Conduct", "## Consult", "## Resume", "## Stop")
    ) == (True, True, True, True, True)
    assert all(
        outcome in skill_text
        for outcome in (
            "consultation_required",
            "waiting_studies",
            "completed_results",
            "invalid_brief",
            "unsupported_aim",
            "evidence_required",
        )
    )
    assert "exact Result references" in skill_text
    assert "immutable historical evidence" in skill_text
    assert "fresh application root" in " ".join(skill_text.split())
    assert all(
        phrase not in skill_text.casefold()
        for phrase in (
            "codex exec",
            "claude -p",
            "chat completions",
            "openai",
            "numerical ceiling",
            "provider",
            "endpoint",
            "credential",
        )
    )


def test_acceptance_profiles_are_exactly_codex_then_claude() -> None:
    """Keep the acceptance-only composition closed and ordered."""

    support = importlib.import_module("tests.harness_acceptance")

    assert tuple(type(profile) for profile in support.ACCEPTANCE_PROFILES) == (
        support.CodexAcceptanceProfile,
        support.ClaudeAcceptanceProfile,
    )
    assert tuple(profile.name for profile in support.ACCEPTANCE_PROFILES) == (
        "codex",
        "claude",
    )
    assert len({profile.name for profile in support.ACCEPTANCE_PROFILES}) == 2


def test_production_has_no_acceptance_profile_or_harness_dispatch() -> None:
    """Keep external harness conventions out of production architecture."""

    dispatch_names = {
        "acceptance_profile",
        "harness",
        "harness_name",
        "profile_name",
    }
    findings: dict[str, list[str]] = {}
    for path in _production_files():
        tree = _tree(path)
        matched: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and (
                node.name.endswith("AcceptanceProfile")
                or node.name.endswith("HarnessAdapter")
            ):
                matched.add(node.name)
            elif isinstance(node, ast.arg) and node.arg in dispatch_names:
                matched.add(node.arg)
            elif isinstance(node, ast.Name) and node.id in dispatch_names:
                matched.add(node.id)
            elif isinstance(node, ast.Attribute) and node.attr in dispatch_names:
                matched.add(node.attr)
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.casefold() in {"codex", "claude"}
            ):
                matched.add(node.value)
        if any(
            imported.startswith("tests.harness_acceptance")
            for imported in _imports(path)
        ):
            matched.add("tests.harness_acceptance")
        if matched:
            findings[path.relative_to(PACKAGE).as_posix()] = sorted(matched)

    assert findings == {}


def _is_ignored(path: Path) -> bool:
    return (
        subprocess.run(
            [
                "git",
                "check-ignore",
                "--no-index",
                "--quiet",
                "--",
                str(path.relative_to(ROOT)),
            ],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0
    )


def test_intention_revealing_modules_replace_retired_paths() -> None:
    """Every renamed responsibility has one import path and no alias."""

    replacements = {
        "science/metalens/periodic_cell_evidence.py": (
            "science/metalens/periodic_response.py"
        ),
        "science/metalens/reference_surface_evidence.py": (
            "science/metalens/periodic_surface.py"
        ),
        "science/metalens/focal_field_comparison.py": (
            "science/metalens/comparison.py"
        ),
        "solvers/lumerical_fdtd/project_execution.py": (
            "solvers/lumerical_fdtd/adapter.py"
        ),
    }

    for current, retired in replacements.items():
        assert (PACKAGE / current).is_file()
        assert not (PACKAGE / retired).exists()

    from metacraft.science.metalens.focal_field_comparison import (
        FocalFieldComparison,
    )
    from metacraft.science.metalens.periodic_cell_evidence import (
        JonesEvidenceBatch,
        PropagationEvidenceBatch,
    )
    from metacraft.solvers.lumerical_fdtd.project_execution import (
        ExecutedProject,
        ProjectExecution,
    )

    assert all(
        value is not None
        for value in (
            FocalFieldComparison,
            JonesEvidenceBatch,
            PropagationEvidenceBatch,
            ExecutedProject,
            ProjectExecution,
        )
    )


def test_behavioral_test_paths_replace_ticket_tracers() -> None:
    """Permanent tests name protected behavior rather than delivery tickets."""

    assert tuple(ROOT.joinpath("tests").rglob("test_ticket[0-9]*.py")) == ()


def test_focal_comparison_has_one_typed_unit_integral_contract() -> None:
    production = tuple((PACKAGE / "field").rglob("*.py")) + tuple(
        (PACKAGE / "science" / "metalens").rglob("*.py")
    )
    source = "\n".join(path.read_text(encoding="utf-8-sig") for path in production)

    assert "normalized_intensity_error" not in source
    assert 'str(error) == "field_agreement_grid_mismatch"' not in source
    assert "unit_integral_intensity_error" in source


def test_aplanatic_reference_formation_replaces_the_generic_road() -> None:
    metalens = PACKAGE / "science" / "metalens"
    production = "\n".join(
        path.read_text(encoding="utf-8-sig") for path in metalens.rglob("*.py")
    )
    field_execution = (metalens / "field_execution.py").read_text(encoding="utf-8-sig")

    assert '"ideal_field"' not in production
    assert '"form_ideal_field"' not in production
    assert '"aplanatic_focus_evaluation"' not in production
    assert "def admit_ideal_field" not in production
    assert '"aplanatic_reference"' in production
    assert '"form_aplanatic_reference"' in production
    assert '"aplanatic_reference_formation"' in production
    assert "AplanaticPupil" not in field_execution
    assert "FocalCoordinates" not in field_execution
    assert "CZTDebyeRealization" not in field_execution
    assert "evaluate_czt_debye" not in field_execution
    assert "torch.arange" not in field_execution
    assert "torch.meshgrid" not in field_execution

    formation = (metalens / "_aplanatic_reference.py").read_text(encoding="utf-8-sig")
    assert "form_aplanatic_reference" in formation
    assert "_prepare_aplanatic_pupil" not in formation
    assert "_evaluate_prepared_fft_debye" not in formation
    assert "_evaluate_prepared_czt_debye" not in formation
    assert "def _centered_slices" not in formation
    assert "def _centered_slices" not in field_execution

    import metacraft.science.metalens as public_metalens

    assert not hasattr(public_metalens, "admit_aplanatic_reference")


def test_external_benchmark_schemas_and_interface_are_exact() -> None:
    """The four external cases expose one strict current comparison seam."""

    import inspect

    from examples import (
        MetalensBenchmarkCase,
        metalens_benchmark_cases,
        select_metalens_benchmark_case,
    )

    cases = metalens_benchmark_cases()
    assert len(cases) == 4
    assert all(type(case) is MetalensBenchmarkCase for case in cases)
    assert all(select_metalens_benchmark_case(case.name) is case for case in cases)
    assert {case.document().schema_identifier for case in cases} == {
        "metacraft.examples.metalens_benchmark_reference_case"
    }
    assert all(
        callable(getattr(MetalensBenchmarkCase, operation, None))
        or isinstance(getattr(MetalensBenchmarkCase, operation, None), property)
        for operation in ("identity", "document", "compare")
    )
    parameters = inspect.signature(MetalensBenchmarkCase.compare).parameters
    assert tuple(parameters) == ("self", "completed_results", "fetch")
    assert parameters["fetch"].kind is inspect.Parameter.KEYWORD_ONLY
    assert not hasattr(MetalensBenchmarkCase, "from_document")
    assert not (ROOT / "examples" / "metalens_benchmark_cases.py").exists()


_PROCESS_INSPECTION_MODULES = frozenset(
    {"platform", "psutil", "subprocess", "win32process", "wmi"}
)
_OS_PROCESS_CALLS = frozenset({"getpid", "getppid", "kill", "popen", "system"})
_PROCESS_ENUMERATION_LITERALS = (
    "get-process",
    "pid_exists",
    "platform",
    "process enumeration",
    "process_iter",
    "psutil",
    "subprocess",
    "tasklist",
    "win32process",
    "wmi",
    "wmic",
)


def _production_files() -> tuple[Path, ...]:
    return tuple(sorted(PACKAGE.rglob("*.py")))


def _process_inspection_findings(source: str) -> tuple[str, ...]:
    """Find aliased imports, calls, literals, and helper definitions."""

    tree = ast.parse(source)
    os_aliases: set[str] = set()
    imported_os_calls: set[str] = set()
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".", maxsplit=1)[0]
                if module in _PROCESS_INSPECTION_MODULES:
                    findings.append(f"import:{module}:{node.lineno}")
                if alias.name == "os":
                    os_aliases.add(alias.asname or "os")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".", maxsplit=1)[0]
            if module in _PROCESS_INSPECTION_MODULES:
                findings.append(f"import-from:{module}:{node.lineno}")
            if module == "os":
                for alias in node.names:
                    if alias.name in _OS_PROCESS_CALLS or alias.name == "*":
                        imported_os_calls.add(alias.asname or alias.name)
                        findings.append(f"import-from:os.{alias.name}:{node.lineno}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name) and function.id in imported_os_calls:
                findings.append(f"call:{function.id}:{node.lineno}")
            elif (
                isinstance(function, ast.Attribute)
                and isinstance(function.value, ast.Name)
                and function.value.id in os_aliases
                and function.attr in _OS_PROCESS_CALLS
            ):
                findings.append(
                    f"call:{function.value.id}.{function.attr}:{node.lineno}"
                )
            elif isinstance(function, ast.Attribute) and function.attr in {
                "pid_exists",
                "process_iter",
            }:
                findings.append(f"call:{function.attr}:{node.lineno}")
            elif (
                isinstance(function, ast.Name)
                and function.id == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in os_aliases
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in _OS_PROCESS_CALLS
            ):
                findings.append(f"call:getattr-os:{node.lineno}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            words = tuple(part for part in node.name.casefold().split("_") if part)
            if any(word in {"pid", "pids", "process", "processes"} for word in words):
                findings.append(f"helper:{node.name}:{node.lineno}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.casefold()
            for literal in _PROCESS_ENUMERATION_LITERALS:
                if literal in lowered:
                    findings.append(f"literal:{literal}:{node.lineno}")
    return tuple(sorted(set(findings)))


def test_native_receipt_uses_closed_activity_not_process_inspection() -> None:
    """
    The external canary trusts public closure facts, never host process probes.
    """

    path = ROOT / "examples" / "native_receipt.py"
    source = path.read_text(encoding="utf-8-sig")
    assert _process_inspection_findings(source) == ()


def test_native_receipt_derives_solver_artifacts_from_one_manifest() -> None:
    """
    Producer artifact renames flow through one captured product manifest.
    """

    source = (ROOT / "examples" / "native_receipt.py").read_text(encoding="utf-8-sig")
    assert source.count("WorkRecord.artifact_manifest()") == 1
    assert source.count("native_solve_sidecar(") == 1
    assert 'native_solve_sidecar(Path("before.fsp"))' not in source
    for artifact_name in WorkRecord.artifact_manifest().values():
        assert f'"{artifact_name}"' not in source


def test_application_root_composition_stays_outside_authority() -> None:
    """
    Application layout stays outside generic Authority and is shared by conduct.
    """

    authority_root = ROOT / "src" / "metacraft" / "authority" / "_application_root.py"
    science_root = ROOT / "src" / "metacraft" / "science" / "_application_root.py"
    retired_science_root = ROOT / "src" / "metacraft" / "science" / "_workspace.py"

    assert not authority_root.exists()
    assert science_root.is_file()
    assert not retired_science_root.exists()


def test_process_inspection_ratchet_detects_alias_and_module_variants() -> None:
    fixtures = (
        "from subprocess import run as execute\nexecute(['tasklist'])\n",
        ("import os as operating_system\n" "operating_system.kill(42, 0)\n"),
        "import psutil\nlist(psutil.process_iter())\n",
        "from os import getpid as current_identity\ncurrent_identity()\n",
        "def enumerate_processes():\n    return ()\n",
    )

    assert all(_process_inspection_findings(source) for source in fixtures)


def _import_test_module(relative_path: str, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        module_name,
        ROOT / relative_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"test_module_import_unavailable:{relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pytest_marker_names(owner: object) -> frozenset[str]:
    value = getattr(owner, "pytestmark", ())
    markers = value if isinstance(value, (list, tuple)) else (value,)
    names: set[str] = set()
    for marker in markers:
        mark = getattr(marker, "mark", marker)
        name = getattr(mark, "name", None)
        if isinstance(name, str):
            names.add(name)
    return frozenset(names)


def _collected_test_marker_names(
    module: ModuleType,
) -> dict[str, frozenset[str]]:
    inherited = _pytest_marker_names(module)
    definitions: dict[str, frozenset[str]] = {"<module>": inherited}
    for name, definition in vars(module).items():
        if name.startswith("test_") and inspect.isfunction(definition):
            definitions[name] = inherited | _pytest_marker_names(definition)
            continue
        if not name.startswith("Test") or not inspect.isclass(definition):
            continue
        class_markers = inherited | _pytest_marker_names(definition)
        definitions[name] = class_markers
        for method_name, method in vars(definition).items():
            if method_name.startswith("test_") and inspect.isfunction(method):
                definitions[f"{name}.{method_name}"] = (
                    class_markers | _pytest_marker_names(method)
                )
    return definitions


def test_native_receipt_live_marker_isolated_from_ordinary_suite(request) -> None:
    """The opt-in native gate never contaminates ordinary contract tests."""

    ordinary = _import_test_module(
        "tests/examples/test_native_receipt.py",
        "_ticket09_ordinary_contract",
    )
    live = _import_test_module(
        "tests/live/test_native_receipt.py",
        "_ticket09_live_contract",
    )
    ordinary_markers = _collected_test_marker_names(ordinary)
    live_markers = _collected_test_marker_names(live)
    configured_markers = tuple(request.config.getini("markers"))
    selected_expression = str(request.config.getoption("markexpr"))

    assert request.node.get_closest_marker("lumerical_canary") is None
    assert len(ordinary_markers) > 1
    assert all(
        "lumerical_canary" not in markers for markers in ordinary_markers.values()
    )
    assert len(live_markers) > 1
    assert all(
        "lumerical_canary" in markers
        for name, markers in live_markers.items()
        if name != "<module>"
    )
    assert "not lumerical_canary" in selected_expression
    assert any(marker.startswith("lumerical_canary:") for marker in configured_markers)


def test_runtime_marker_inspection_accepts_module_and_definition_marks() -> None:
    single_module = ModuleType("single_module")
    single_module.pytestmark = pytest.mark.lumerical_canary

    def test_single_module() -> None:
        pass

    single_module.test_single_module = test_single_module

    list_module = ModuleType("list_module")
    list_module.pytestmark = [pytest.mark.lumerical_canary]

    def test_list_module() -> None:
        pass

    list_module.test_list_module = test_list_module

    definition_module = ModuleType("definition_module")

    @pytest.mark.lumerical_canary
    def test_definition() -> None:
        pass

    definition_module.test_definition = test_definition

    @pytest.mark.lumerical_canary
    class TestDefinition:
        def test_method(self) -> None:
            pass

    definition_module.TestDefinition = TestDefinition

    for module in (single_module, list_module, definition_module):
        markers = _collected_test_marker_names(module)
        assert all(
            "lumerical_canary" in names
            for name, names in markers.items()
            if name != "<module>"
        )


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"))


def _module(path: Path) -> str:
    relative = path.relative_to(ROOT / "src").with_suffix("")
    parts = relative.parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _imports(path: Path) -> set[str]:
    current = _module(path).split(".")
    if path.name != "__init__.py":
        current = current[:-1]
    imported: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        base = (node.module or "").split(".") if node.module else []
        if node.level:
            current_base = current[: len(current) - node.level + 1]
            base = [*current_base, *base]
        module = ".".join(base)
        if module:
            imported.add(module)
        imported.update(
            f"{module}.{alias.name}" if module else alias.name for alias in node.names
        )
    return imported


def _schema_declarations(
    tree: ast.Module,
    relative: str,
) -> tuple[dict[str, set[str]], list[str]]:
    declarations: set[int] = set()
    owners: dict[str, set[str]] = defaultdict(set)
    violations: list[str] = []
    for statement in tree.body:
        target: ast.Name | None = None
        value: ast.expr | None = None
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        ):
            target = statement.targets[0]
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            target = statement.target
            value = statement.value
        if target is None or not target.id.endswith("_SCHEMA"):
            continue
        if (
            isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and not value.value.startswith(SCHEMA_PREFIXES)
        ):
            continue
        if (
            not isinstance(value, ast.Constant)
            or not isinstance(value.value, str)
            or not value.value.startswith(SCHEMA_PREFIXES)
        ):
            violations.append(f"{relative}:{statement.lineno}:schema_declaration")
            continue
        declarations.add(id(value))
        owners[value.value].add(relative)
    joined_parts = {
        id(part)
        for node in ast.walk(tree)
        if isinstance(node, ast.JoinedStr)
        for part in node.values
        if isinstance(part, ast.Constant)
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith(SCHEMA_PREFIXES)
        ):
            if id(node) not in declarations and id(node) not in joined_parts:
                violations.append(f"{relative}:{node.lineno}:schema_literal")
        elif isinstance(node, ast.JoinedStr):
            literal_parts = tuple(
                part.value
                for part in node.values
                if isinstance(part, ast.Constant) and isinstance(part.value, str)
            )
            if any(
                prefix in part for prefix in SCHEMA_PREFIXES for part in literal_parts
            ):
                violations.append(f"{relative}:{node.lineno}:schema_f_string")
    return owners, violations


def test_retired_modules_have_no_import_alias() -> None:
    """
    Deleted shallow Modules cannot return through relative or absolute imports.
    """

    found: dict[str, list[str]] = {}
    for path in _production_files():
        retired = sorted(
            old
            for old in RETIRED_MODULES
            if any(
                imported == old or imported.startswith(f"{old}.")
                for imported in _imports(path)
            )
        )
        if retired:
            found[str(path.relative_to(PACKAGE))] = retired

    assert found == {}


def test_one_production_module_owns_each_schema_literal() -> None:
    """
    Only one module-level ``*_SCHEMA`` constant may declare each schema.
    """

    owners: dict[str, set[str]] = defaultdict(set)
    violations: list[str] = []
    for path in _production_files():
        relative = path.relative_to(PACKAGE).as_posix()
        declared, invalid = _schema_declarations(
            _tree(path),
            relative,
        )
        for schema, paths in declared.items():
            owners[schema].update(paths)
        violations.extend(invalid)

    duplicates = {
        schema: sorted(paths) for schema, paths in owners.items() if len(paths) > 1
    }
    assert violations == []
    assert duplicates == {}


def test_schema_guard_detects_consumer_literals_and_f_strings() -> None:
    """
    The schema owner rule is sensitive to every forbidden construction form.
    """

    tree = ast.parse(
        'OWNER_SCHEMA = "metacraft.science.owner"\n'
        "FORWARD_SCHEMA = OWNER_SCHEMA\n"
        "def literal_consumer():\n"
        '    return "metacraft.science.consumer"\n'
        "def formatted_consumer(name):\n"
        '    return f"metacraft.science.{name}"\n'
    )

    owners, violations = _schema_declarations(tree, "consumer.py")

    assert owners == {"metacraft.science.owner": {"consumer.py"}}
    assert violations == [
        "consumer.py:2:schema_declaration",
        "consumer.py:4:schema_literal",
        "consumer.py:6:schema_f_string",
    ]


def test_compiler_does_not_manufacture_scientific_schemas() -> None:
    """
    Compilation copies schemas declared by scientific value Modules.
    """

    for relative in (
        Path("science/compile.py"),
        Path("science/relationships.py"),
        Path("science/metalens/relationship.py"),
    ):
        literals = {
            node.value
            for node in ast.walk(_tree(PACKAGE / relative))
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith(SCHEMA_PREFIXES)
        }
        assert literals == set(), relative


def test_no_dotted_route_identity_or_old_result_reader_remains() -> None:
    """
    Route identity is canonical content and Result has one current restorer.
    """

    forbidden_readers = {
        "assemble_aperture",
        "interpret",
        "read_geometric_result",
        "read_propagation_result",
        "restore_geometric_result",
        "restore_propagation_result",
    }
    found: dict[str, list[str]] = {}
    for path in _production_files():
        retired: set[str] = set()
        for node in ast.walk(_tree(path)):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                if node.name in forbidden_readers:
                    retired.add(node.name)
            elif isinstance(node, ast.Constant) and isinstance(
                node.value,
                str,
            ):
                if "metalens.low_na." in node.value or ".science.routes." in node.value:
                    retired.add(node.value)
        if retired:
            found[path.relative_to(PACKAGE).as_posix()] = sorted(retired)

    assert found == {}


def test_production_has_no_retired_responsibility_identifiers() -> None:
    """
    Keep accurate short nouns while refusing old architecture abstractions.
    """

    found: dict[str, list[str]] = {}
    shorthand = re.compile(r"(^|_)(?:kx|ky|kz|n_eff|na|pb)(?:_|$)", re.I)
    allowed_processor_names = {"LogicalProcessor", "_ProcessorNumber"}
    for path in _production_files():
        retired: set[str] = set()
        for node in ast.walk(_tree(path)):
            name = None
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                name = node.name
            elif isinstance(node, ast.arg):
                name = node.arg
            elif isinstance(node, ast.AnnAssign) and isinstance(
                node.target,
                ast.Name,
            ):
                name = node.target.id
            if name is None:
                continue
            if (
                name.startswith("route_")
                or name.endswith("_operation")
                or shorthand.search(name)
            ):
                retired.add(name)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                lowered = name.casefold()
                if (
                    lowered.endswith(("manager", "handler", "processor"))
                    and name not in allowed_processor_names
                ):
                    retired.add(name)
        if retired:
            found[path.relative_to(PACKAGE).as_posix()] = sorted(retired)

    assert found == {}


_GIT_CHECK_IGNORE_PREFIX = ("git", "check-ignore", "--")
_WINDOWS_SAFE_COMMAND_LENGTH = 24_000


def _git_check_ignore_batches(
    candidates: tuple[str, ...],
    *,
    maximum_command_length: int = _WINDOWS_SAFE_COMMAND_LENGTH,
) -> tuple[tuple[str, ...], ...]:
    """Keep each rendered Windows git command below one safe bound."""

    batches: list[tuple[str, ...]] = []
    current: list[str] = []
    for candidate in candidates:
        proposed = (*current, candidate)
        if (
            len(subprocess.list2cmdline((*_GIT_CHECK_IGNORE_PREFIX, *proposed)))
            > maximum_command_length
        ):
            if not current:
                raise ValueError("git_check_ignore_candidate_too_long")
            batches.append(tuple(current))
            current = [candidate]
            if (
                len(subprocess.list2cmdline((*_GIT_CHECK_IGNORE_PREFIX, candidate)))
                > maximum_command_length
            ):
                raise ValueError("git_check_ignore_candidate_too_long")
            continue
        current.append(candidate)
    if current:
        batches.append(tuple(current))
    return tuple(batches)


def test_git_check_ignore_batches_fit_the_windows_command_line() -> None:
    candidates = tuple(f"docs/{index:04d}-{'x' * 80}.md" for index in range(40))

    batches = _git_check_ignore_batches(
        candidates,
        maximum_command_length=512,
    )

    assert len(batches) > 1
    assert tuple(candidate for batch in batches for candidate in batch) == (candidates)
    assert all(
        len(subprocess.list2cmdline((*_GIT_CHECK_IGNORE_PREFIX, *batch))) <= 512
        for batch in batches
    )


def test_every_versionable_local_markdown_link_resolves() -> None:
    """
    Tracked and untracked nonignored Markdown links resolve.

    Markdown may cite local material under the gitignored ``reference/`` tree
    (see DEVELOPMENT.md). Such links are provenance for the author's machine,
    not versionable content, so they are out of scope here. Checking untracked
    nonignored planning and closure records prevents a staged-only blind spot.
    """

    markdown = [
        name
        for name in subprocess.run(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                "*.md",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.split("\0")
        if name
    ]
    pattern = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")

    # Collect every in-repo link target once, then ask git which of them are
    # gitignored. Targets that escape the repository root or fall under an
    # ignored path are local reference material and are not verified.
    candidates: list[str] = []
    entries: list[tuple[str, int, str, str]] = []
    for name in markdown:
        path = ROOT / name
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8-sig").splitlines(),
            start=1,
        ):
            for raw in pattern.findall(line):
                stripped = raw.strip()
                if stripped.startswith("<") and ">" in stripped:
                    target = stripped[1 : stripped.index(">")]
                else:
                    target = stripped.split(maxsplit=1)[0]
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                relative = unquote(target.split("#", maxsplit=1)[0])
                if not relative:
                    continue
                resolved = (path.parent / relative).resolve()
                try:
                    under_root = resolved.relative_to(ROOT)
                except ValueError:
                    # Target escapes the repository root; local-only.
                    continue
                candidate = under_root.as_posix()
                candidates.append(candidate)
                entries.append(
                    (
                        path.relative_to(ROOT).as_posix(),
                        line_number,
                        raw,
                        candidate,
                    )
                )

    ignored: set[str] = set()
    for batch in _git_check_ignore_batches(tuple(candidates)):
        result = subprocess.run(
            [*_GIT_CHECK_IGNORE_PREFIX, *batch],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode not in {0, 1}:
            result.check_returncode()
        ignored.update(
            line.strip().replace("\\", "/")
            for line in result.stdout.splitlines()
            if line.strip()
        )

    missing: list[str] = []
    for source, line_number, raw, candidate in entries:
        if candidate in ignored:
            continue
        if not (ROOT / candidate).exists():
            missing.append(f"{source}:{line_number}:{raw}")

    assert missing == []


def test_continuous_achromatic_route_has_one_aim_owned_delegation() -> None:
    module = PACKAGE / "science" / "metalens" / "_continuous_achromatic.py"
    relationship = (PACKAGE / "science" / "metalens" / "relationship.py").read_text(
        encoding="utf-8"
    )
    conduct = (PACKAGE / "science" / "metalens" / "conduct.py").read_text(
        encoding="utf-8"
    )

    source = module.read_text(encoding="utf-8")
    assert "def relationship(" in source
    assert "def prepare(" in source
    assert "def advance(" in source
    assert relationship.count("_continuous_achromatic.relationship(") == 1
    assert conduct.count("_continuous_achromatic.prepare(") == 1
    assert conduct.count("_continuous_achromatic.advance(") == 1
    for operation in (
        "derive_achromatic_target",
        "retain_response_qualification_profile",
        "specify_spectral_campaign",
        "bind_spectral_materials",
        "plan_spectral_cell_study",
        "screen_spectral_cells",
        "observe_spectral_jones",
        "qualify_spectral_response",
        "assign_achromatic_aperture",
        "observe_post_freeze_jones",
        "form_spectral_fields",
        "evaluate_achromatic_focus",
        "verify_achromatic_band",
    ):
        assert operation not in relationship
        assert operation not in conduct
