from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re

from tests.architecture._python_import_facts import (
    PythonImportFactError,
    inspect_python_imports,
    read_python_imports,
)
from tests.architecture._python_symbol_facts import (
    PythonSymbolFactError,
    read_module_symbol_bindings,
    read_python_call_facts,
    resolve_expression_source,
)

PACKAGE = Path("src/chromatix_next")

RETIRED_SPLITTER_MODULE_STEMS = (
    "nonpolarizing" + "_beam_splitter",
    "polarizing" + "_beam_splitter",
    "nonpolarizing" + "_beam_splitter_at",
    "polarizing" + "_beam_splitter_at",
)

RETIRED_SPLITTER_PUBLIC_NAMES = (
    "nonpolarizing" + "_beam_splitter",
    "Nonpolarizing" + "BeamSplitter",
    "reciprocal_nonpolarizing" + "_beam_splitter",
    "ReciprocalNonpolarizing" + "BeamSplitter",
    "polarizing" + "_beam_splitter",
    "Polarizing" + "BeamSplitter",
    "reciprocal_polarizing" + "_beam_splitter",
    "ReciprocalPolarizing" + "BeamSplitter",
    "nonpolarizing" + "_beam_splitter_at",
    "Nonpolarizing" + "BeamSplitterAt",
    "polarizing" + "_beam_splitter_at",
    "Polarizing" + "BeamSplitterAt",
)

_RETIRED_PRIVATE_NAMES = (
    "_split" + "_coefficients",
    "split" + "_envelope",
    "reciprocal_split" + "_envelopes",
    "split" + "_ray_power",
    "_polarizing" + "_beam_splitter_envelopes",
    "_reciprocal_polarizing" + "_beam_splitter_envelopes",
    "polarizing" + "_ray_split",
)

_RETIRED_STATE_NAMES = (
    "power" + "_transmissivity",
    "transmitted_eigenstate" + "_azimuth_radians",
    "transmitted_eigenstate" + "_ellipticity_radians",
)

_FINDING_CONTRACTS = {
    "state_unification": (
        "Wave/Ray Physical Values",
        "Wave and Ray remain peers without a universal state or converter.",
    ),
    "field_pose": (
        "OpticalField and RayBundle",
        "Local Physical Values do not acquire a universal pose or reference plane.",
    ),
    "generic_scattering": (
        "directional owners",
        "The qualified cube algebra must not widen into caller-supplied "
        "N-port response machinery.",
    ),
    "public_governance": (
        "Assembly",
        "The small public grammar has no Root, directional base, registry, "
        "or capability family.",
    ),
    "recurrence": (
        "Assembly",
        "Routes are finite and authored; recurrence, pass policy, and route "
        "search are excluded.",
    ),
    "replay": (
        "Workstation",
        "One frozen Assembly fact reaches one private replay boundary.",
    ),
    "evidence_runtime": (
        "offline qualification",
        "Static claim evidence stays outside the production runtime.",
    ),
    "tensor_fact_state": (
        "Assembly frozen facts",
        "Route, Encounter, ancestry, and claim facts carry structure rather "
        "than Tensor state.",
    ),
    "opr_advance": (
        "Propagation",
        "Propagation is the sole production owner of Wave OPR advancement.",
    ),
    "retired_splitter": (
        "atomic public migration",
        "Retired lumped splitters have no compatibility path or persistent vocabulary.",
    ),
}


@dataclass(frozen=True, slots=True)
class NegativeSpaceFinding:
    """
    Records one falsifiable architecture-negative-space violation.

    Attributes:
        identity: Stable guard-family identity.
        owner: Architecture owner that must reject the violation.
        rationale: Contract reason for excluding the structure.
        evidence: Static coordinate that demonstrates the violation.
    """

    identity: str
    owner: str
    rationale: str
    evidence: str


def _finding(family: str, evidence: str) -> NegativeSpaceFinding:
    owner, rationale = _FINDING_CONTRACTS[family]
    return NegativeSpaceFinding(
        identity=family,
        owner=owner,
        rationale=rationale,
        evidence=evidence,
    )


def format_findings(findings: tuple[NegativeSpaceFinding, ...]) -> str:
    """
    Format guard failures with their owner, rationale, and evidence.

    Args:
        findings: Ordered negative-space violations.

    Returns:
        One deterministic diagnostic string for an assertion failure.
    """

    return "\n".join(
        f"{finding.identity} | owner={finding.owner} | "
        f"rationale={finding.rationale} | evidence={finding.evidence}"
        for finding in findings
    )


def _compact_name(name: str) -> str:
    return "".join(character for character in name.casefold() if character.isalnum())


def _expression_name(expression: ast.expr) -> str | None:
    if isinstance(expression, ast.Name):
        return expression.id
    if isinstance(expression, ast.Attribute):
        prefix = _expression_name(expression.value)
        if prefix is None:
            return None
        return f"{prefix}.{expression.attr}"
    return None


def _assignment_names(target: ast.expr) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        return tuple(
            name
            for element in target.elts
            for name in _assignment_names(element)
        )
    return ()


def _bound_name_coordinates(
    tree: ast.Module,
) -> tuple[tuple[str, int, bool], ...]:
    coordinates: list[tuple[str, int, bool]] = []
    module_level = {id(node) for node in tree.body}
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            coordinates.append((node.name, node.lineno, True))
        elif isinstance(node, ast.Assign):
            coordinates.extend(
                (name, node.lineno, id(node) in module_level)
                for target in node.targets
                for name in _assignment_names(target)
            )
        elif isinstance(node, ast.AnnAssign):
            coordinates.extend(
                (name, node.lineno, id(node) in module_level)
                for name in _assignment_names(node.target)
            )
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            coordinates.extend(
                (
                    alias.asname
                    or (
                        alias.name
                        if isinstance(node, ast.ImportFrom)
                        else alias.name.split(".")[0]
                    ),
                    node.lineno,
                    True,
                )
                for alias in node.names
                if alias.name != "*"
            )
    return tuple(coordinates)


def _export_names(tree: ast.Module) -> tuple[tuple[str, int], ...]:
    exports: list[tuple[str, int]] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else (node.target,)
        )
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in targets
        ):
            continue
        value = node.value
        if not isinstance(value, (ast.List, ast.Tuple)):
            exports.append(("<dynamic __all__>", node.lineno))
            continue
        exports.extend(
            (element.value, element.lineno)
            for element in value.elts
            if isinstance(element, ast.Constant)
            and isinstance(element.value, str)
        )
    return tuple(exports)


def _binding_family(name: str, *, is_public: bool) -> str | None:
    compact = _compact_name(name)
    if (
        "opticalstate" in compact
        or "wavetorayconverter" in compact
        or "raytowaveconverter" in compact
    ):
        return "state_unification"
    if (
        compact.startswith("nport")
        or (is_public and "nport" in compact)
        or "scatteringmatrix" in compact
        or "responsematrix" in compact
        or "scatteringlaw" in compact
    ):
        return "generic_scattering"
    if is_public and (
        compact == "base"
        or compact == "root"
        or (name[:1].isupper() and compact.endswith("root"))
        or "directionalelementbase" in compact
        or "terminalbase" in compact
        or compact.endswith("registry")
        or compact.endswith("capability")
        or compact.endswith("capabilityfamily")
    ):
        return "public_governance"
    if (
        "recurrentwave" in compact
        or "recurrentsolver" in compact
        or "passcount" in compact
        or "routesearch" in compact
        or "convergencepolicy" in compact
    ):
        return "recurrence"
    if (
        "evidencegraph" in compact
        or (is_public and compact.endswith("experiment"))
        or "callbackregistry" in compact
        or "metricregistry" in compact
        or "hostedmutation" in compact
        or "claimexecutor" in compact
    ):
        return "evidence_runtime"
    if compact in {"ancestrygraph", "routegraph"}:
        return "replay"
    return None


def _is_retired_name(name: str) -> bool:
    compact = _compact_name(name)
    retired = {
        _compact_name(value)
        for value in (
            *RETIRED_SPLITTER_MODULE_STEMS,
            *RETIRED_SPLITTER_PUBLIC_NAMES,
            *_RETIRED_PRIVATE_NAMES,
            *_RETIRED_STATE_NAMES,
        )
    }
    return compact in retired


def architecture_surface_findings(
    source: str,
    module_name: str,
    *,
    is_package: bool = False,
) -> tuple[NegativeSpaceFinding, ...]:
    """
    Inspect one production source unit for prohibited architecture surfaces.

    Args:
        source: Python source text to inspect.
        module_name: Qualified module identity represented by the source.
        is_package: Whether relative imports anchor at a package initializer.

    Returns:
        Ordered structural violations with complete adjudication coordinates.
    """

    try:
        tree = ast.parse(source)
        import_facts = inspect_python_imports(source, module_name, is_package)
    except (SyntaxError, PythonImportFactError) as error:
        return (_finding("public_governance", f"{module_name}:{error}"),)

    findings: list[NegativeSpaceFinding] = []
    coordinates = (
        *_bound_name_coordinates(tree),
        *((name, line, True) for name, line in _export_names(tree)),
    )
    for name, line, is_interface in coordinates:
        family = _binding_family(
            name,
            is_public=is_interface and not name.startswith("_"),
        )
        if family is not None:
            findings.append(_finding(family, f"{module_name}:{line}:{name}"))
        if _is_retired_name(name):
            findings.append(
                _finding("retired_splitter", f"{module_name}:{line}:{name}")
            )

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or (
            node.name.startswith("_")
        ):
            continue
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ):
            family = _binding_family(argument.arg, is_public=False)
            if family is not None:
                findings.append(
                    _finding(
                        family,
                        f"{module_name}:{argument.lineno}:argument={argument.arg}",
                    )
                )

    for dependency in sorted(
        import_facts.imported_modules | import_facts.imported_targets
    ):
        leaf = dependency.rsplit(".", 1)[-1]
        family = _binding_family(leaf, is_public=not leaf.startswith("_"))
        if family is not None:
            findings.append(
                _finding(family, f"{module_name}:import:{dependency}")
            )
        if _is_retired_name(leaf) or any(
            stem in dependency for stem in RETIRED_SPLITTER_MODULE_STEMS
        ):
            findings.append(
                _finding(
                    "retired_splitter",
                    f"{module_name}:import:{dependency}",
                )
            )

    try:
        bindings = read_module_symbol_bindings(
            tree,
            module_name,
            is_package=is_package,
        )
    except PythonSymbolFactError as error:
        if "*" not in import_facts.local_bindings:
            findings.append(
                _finding("public_governance", f"{module_name}:bindings:{error}")
            )
        bindings = None
    if bindings is not None:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Name, ast.Attribute)):
                continue
            source_name = resolve_expression_source(node, bindings)
            if source_name is None:
                continue
            leaf = source_name.rsplit(".", 1)[-1]
            family = _binding_family(
                leaf,
                is_public=not leaf.startswith("_"),
            )
            if family is not None:
                findings.append(
                    _finding(
                        family,
                        f"{module_name}:{node.lineno}:{source_name}",
                    )
                )
            if _is_retired_name(leaf) or any(
                stem in source_name for stem in RETIRED_SPLITTER_MODULE_STEMS
            ):
                findings.append(
                    _finding(
                        "retired_splitter",
                        f"{module_name}:{node.lineno}:{source_name}",
                    )
                )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if any(state_name == node.value for state_name in _RETIRED_STATE_NAMES):
            findings.append(
                _finding(
                    "retired_splitter",
                    f"{module_name}:{node.lineno}:state={node.value}",
                )
            )
        normalized = node.value.casefold()
        if "beam_splitter" in normalized and (
            normalized.startswith("nonpolarizing_")
            or normalized.startswith("polarizing_")
            or normalized.startswith("reciprocal_")
        ):
            findings.append(
                _finding(
                    "retired_splitter",
                    f"{module_name}:{node.lineno}:error={node.value}",
                )
            )

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        target_names = {
            name
            for target in targets
            for name in _assignment_names(target)
        }
        if not {"input_ports", "output_ports"}.intersection(target_names):
            continue
        if node.value is None:
            continue
        for value in ast.walk(node.value):
            if (
                isinstance(value, ast.Constant)
                and value.value in {"transmitted", "reflected"}
            ):
                findings.append(
                    _finding(
                        "retired_splitter",
                        f"{module_name}:{value.lineno}:port={value.value}",
                    )
                )
    return tuple(dict.fromkeys(findings))


def _annotation_sources(
    annotation: ast.expr,
    bindings: object,
) -> tuple[str, ...]:
    sources: list[str] = []
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            annotation = ast.parse(annotation.value, mode="eval").body
        except SyntaxError:
            return ()
    for node in ast.walk(annotation):
        if not isinstance(node, (ast.Name, ast.Attribute)):
            continue
        source = resolve_expression_source(node, bindings)  # type: ignore[arg-type]
        if source is not None:
            sources.append(source)
    return tuple(sources)


def tensor_fact_findings(
    source: str,
    module_name: str,
    *,
    is_package: bool = False,
) -> tuple[NegativeSpaceFinding, ...]:
    """
    Reject Tensor or registered state on Route, Encounter, ancestry, or claim facts.

    Args:
        source: Python source text to inspect.
        module_name: Qualified module identity represented by the source.
        is_package: Whether relative imports anchor at a package initializer.

    Returns:
        Ordered state-bearing fact violations.
    """

    tree = ast.parse(source)
    try:
        bindings = read_module_symbol_bindings(
            tree,
            module_name,
            is_package=is_package,
        )
    except PythonSymbolFactError as error:
        return (
            _finding(
                "tensor_fact_state",
                f"{module_name}:bindings:{error}",
            ),
        )
    findings: list[NegativeSpaceFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        compact = _compact_name(node.name)
        is_structural_fact = (
            compact in {"waveencounter", "rayencounter"}
            or (
                compact.endswith("fact")
                and any(
                    word in compact
                    for word in ("route", "encounter", "ancestry", "claim")
                )
            )
        )
        if not is_structural_fact:
            continue
        for base in node.bases:
            source_name = resolve_expression_source(base, bindings)
            if source_name in {"torch.nn.Module", "torch.nn.Parameter"}:
                findings.append(
                    _finding(
                        "tensor_fact_state",
                        f"{module_name}:{node.lineno}:{node.name}:base={source_name}",
                    )
                )
        for statement in node.body:
            if isinstance(statement, ast.AnnAssign):
                for source_name in _annotation_sources(
                    statement.annotation,
                    bindings,
                ):
                    if source_name in {
                        "torch.Tensor",
                        "torch.nn.Module",
                        "torch.nn.Parameter",
                    }:
                        findings.append(
                            _finding(
                                "tensor_fact_state",
                                f"{module_name}:{statement.lineno}:"
                                f"{node.name}:{source_name}",
                            )
                        )
            for call in (
                candidate
                for candidate in ast.walk(statement)
                if isinstance(candidate, ast.Call)
            ):
                call_name = _expression_name(call.func)
                if call_name is not None and call_name.rsplit(".", 1)[-1] in {
                    "register_buffer",
                    "register_parameter",
                    "add_module",
                }:
                    findings.append(
                        _finding(
                            "tensor_fact_state",
                            f"{module_name}:{call.lineno}:{node.name}:{call_name}",
                        )
                    )
                source_name = resolve_expression_source(call.func, bindings)
                if source_name in {
                    "torch.tensor",
                    "torch.as_tensor",
                    "torch.nn.Parameter",
                }:
                    findings.append(
                        _finding(
                            "tensor_fact_state",
                            f"{module_name}:{call.lineno}:{node.name}:{source_name}",
                        )
                    )
    return tuple(dict.fromkeys(findings))


def physical_value_wrapper_findings(
    source: str,
    module_name: str,
) -> tuple[NegativeSpaceFinding, ...]:
    """
    Reject universal pose or state fields on OpticalField and RayBundle.

    Args:
        source: Python source text to inspect.
        module_name: Qualified module identity represented by the source.

    Returns:
        Ordered Physical Value wrapper violations.
    """

    tree = ast.parse(source)
    bindings = read_module_symbol_bindings(tree, module_name)
    findings: list[NegativeSpaceFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name not in {
            "OpticalField",
            "RayBundle",
        }:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            names = _assignment_names(statement.target)
            for name in names:
                compact = _compact_name(name)
                if compact in {
                    "pose",
                    "referenceplane",
                    "wavereferenceplane",
                    "state",
                    "opticalstate",
                }:
                    findings.append(
                        _finding(
                            "field_pose",
                            f"{module_name}:{statement.lineno}:{node.name}.{name}",
                        )
                    )
            for source_name in _annotation_sources(statement.annotation, bindings):
                compact = _compact_name(source_name.rsplit(".", 1)[-1])
                if compact in {"pose", "referenceplane", "opticalstate"}:
                    findings.append(
                        _finding(
                            "field_pose",
                            f"{module_name}:{statement.lineno}:"
                            f"{node.name}:{source_name}",
                        )
                    )
    return tuple(dict.fromkeys(findings))


def opr_advance_findings(
    source: str,
    module_name: str,
    *,
    is_package: bool = False,
) -> tuple[NegativeSpaceFinding, ...]:
    """
    Reject Wave OPR advancement outside its two exact production authorities.

    Args:
        source: Python source text to inspect.
        module_name: Qualified module identity represented by the source.
        is_package: Whether relative imports anchor at a package initializer.

    Returns:
        Ordered OPR-authority violations.
    """

    advance_target = (
        "chromatix_next.optics.propagation._field_state."
        "_advance_path_reference"
    )
    accumulation_target = (
        "chromatix_next._numerics.optical_path_reference."
        "accumulate_optical_path_lengths"
    )
    allowed_accumulation = {
        (
            "chromatix_next.optics.propagation._field_state",
            "_advance_path_reference",
        ),
        (
            "chromatix_next.optics.element.optical_path_modulation",
            "optical_path_modulation",
        ),
    }
    findings: list[NegativeSpaceFinding] = []
    try:
        import_facts = inspect_python_imports(source, module_name, is_package)
    except PythonImportFactError as error:
        return (_finding("opr_advance", f"{module_name}:imports:{error}"),)
    for target in import_facts.imported_targets:
        if not target.endswith(".*"):
            continue
        if target.startswith(
            "chromatix_next.optics.propagation._field_state."
        ) or target.startswith(
            "chromatix_next._numerics.optical_path_reference."
        ):
            findings.append(
                _finding("opr_advance", f"{module_name}:star-import:{target}")
            )
    authority_imported = any(
        target.startswith(
            "chromatix_next.optics.propagation._field_state"
        )
        or target.startswith(
            "chromatix_next._numerics.optical_path_reference"
        )
        for target in (
            import_facts.imported_modules | import_facts.imported_targets
        )
    )
    if not authority_imported:
        return tuple(dict.fromkeys(findings))
    try:
        calls = read_python_call_facts(ast.parse(source), module_name)
    except PythonSymbolFactError as error:
        if "*" not in import_facts.local_bindings:
            findings.append(
                _finding("opr_advance", f"{module_name}:calls:{error}")
            )
        calls = ()
    for call in calls:
        if call.source == advance_target and not module_name.startswith(
            "chromatix_next.optics.propagation."
        ):
            findings.append(
                _finding(
                    "opr_advance",
                    f"{module_name}:{call.line}:{call.scope_name}:advance",
                )
            )
        if call.source == accumulation_target and (
            module_name,
            call.scope_name,
        ) not in allowed_accumulation:
            findings.append(
                _finding(
                    "opr_advance",
                    f"{module_name}:{call.line}:{call.scope_name}:accumulate",
                )
            )
    return tuple(dict.fromkeys(findings))


def replay_findings(
    source: str,
    module_name: str,
    *,
    is_package: bool = False,
) -> tuple[NegativeSpaceFinding, ...]:
    """
    Reject a second Assembly replay boundary or persisted ancestry graph.

    Args:
        source: Python source text to inspect.
        module_name: Qualified module identity represented by the source.
        is_package: Whether relative imports anchor at a package initializer.

    Returns:
        Ordered replay-ownership violations.
    """

    tree = ast.parse(source)
    allowed_replay_definitions = {
        ("chromatix_next.optics.assembly", "_replay"),
        ("chromatix_next.optics._assembly_replay", "_replay"),
    }
    findings: list[NegativeSpaceFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            node.name == "_replay"
            and (module_name, node.name) not in allowed_replay_definitions
        ):
            findings.append(
                _finding("replay", f"{module_name}:{node.lineno}:{node.name}")
            )
        if isinstance(node, ast.ClassDef) and _compact_name(node.name) in {
            "ancestrygraph",
            "routegraph",
            "evidencegraph",
        }:
            findings.append(
                _finding("replay", f"{module_name}:{node.lineno}:{node.name}")
            )
    imports = inspect_python_imports(source, module_name, is_package)
    replay_module = "chromatix_next.optics._assembly_replay"
    if replay_module in imports.imported_modules and module_name != (
        "chromatix_next.optics.assembly"
    ):
        findings.append(
            _finding("replay", f"{module_name}:import:{replay_module}")
        )
    return tuple(dict.fromkeys(findings))


def production_findings() -> tuple[NegativeSpaceFinding, ...]:
    """
    Inspect the complete production tree under all section-18 guard families.

    Returns:
        Ordered production violations with exact module coordinates.
    """

    findings: list[NegativeSpaceFinding] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        facts = read_python_imports(path, PACKAGE.parent)
        source = path.read_text(encoding="utf-8")
        findings.extend(
            architecture_surface_findings(
                source,
                facts.module_name,
                is_package=path.name == "__init__.py",
            )
        )
        findings.extend(
            tensor_fact_findings(
                source,
                facts.module_name,
                is_package=path.name == "__init__.py",
            )
        )
        findings.extend(
            opr_advance_findings(
                source,
                facts.module_name,
                is_package=path.name == "__init__.py",
            )
        )
        findings.extend(
            replay_findings(
                source,
                facts.module_name,
                is_package=path.name == "__init__.py",
            )
        )
        if path.name in {"field.py", "ray_bundle.py"}:
            findings.extend(
                physical_value_wrapper_findings(source, facts.module_name)
            )
    return tuple(dict.fromkeys(findings))
