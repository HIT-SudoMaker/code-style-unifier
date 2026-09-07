from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

from examples import select_metalens_benchmark_case
from metacraft.authority import Authority, Document, Reference, reference_for
from metacraft.authority.session import AuthoritySession
from metacraft.external_activity import ExternalActivityClosure
from metacraft.materials import (
    MaterialResponseContext,
    ObservedMaterials,
    RecordedMaterialResponse,
    SolverMaterialLibrary,
)
from metacraft.science._application_root import (
    create_authority_in_new_application_root,
)
from metacraft.science.metalens.checkpoint import StudyFrontier
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.height import HeightChoice
from metacraft.science.metalens.height_advice import HeightAdvice
from metacraft.science.metalens.brief import (
    MetalensBrief,
    require_monochromatic_wavelength,
)
from metacraft.science.metalens.material import MaterialBinding
from metacraft.science.metalens.period import derive_period_domain
from metacraft.science.metalens.period import PeriodChoice
from metacraft.science.metalens.period_advice import PeriodAdvice
from metacraft.science.conduct import ConsultationRequired, conduct
from metacraft.science.consultation import ConsultationAnswer
from metacraft.science.periodic_response import (
    PeriodicResponseContext,
    PeriodicResponseKind,
)
from metacraft.science.study import Binding, Capability, Study
from metacraft.solvers.recorded_periodic_response import RecordedPeriodicResponse
from tests.domain_fixtures import compile_with_facts, material_binding


CASE_NAMES = (
    "mcclung-2024-low-na-propagation",
    "yang-2018-low-na-geometric",
    "arbabi-2015-high-na-propagation",
    "khorasaninejad-2016-high-na-geometric",
)
OPENING_PROMPT = (
    "Design the optical device described by blind-brief.json using only the "
    "files and project guidance available in this directory. Work closed-book: "
    "do not use network, search, connectors, external files, or prior knowledge "
    "of any publication. Use prepared-application-root and "
    "reviewed-materials.toml. Follow the complete local consultation cadence, "
    "create canonical answer files as needed, and stop before any unavailable "
    "executable evidence. Explain each choice from the supplied grounds. Do not "
    "inspect or modify anything outside this directory."
)
FIXTURE_PROVENANCE = {
    "atom_refractive_index": "2.05",
    "purpose": "interface acceptance; not physical truth",
    "substrate_refractive_index": "1.48",
}

_FIXTURE_ATOM_REFRACTIVE_INDICES = {
    "amorphous titanium dioxide": "2.40",
    "silicon": "3.50",
    "silicon nitride": "2.05",
}


@dataclass(frozen=True, slots=True)
class PreparedCapsule:
    root: Path
    case_name: str
    application_root: Path
    brief_path: Path
    material_library_path: Path
    prompt_path: Path


@dataclass(frozen=True, slots=True)
class RetainedMaterialReceipt:
    """Locate one exact material observation retained by an earlier run."""

    authority_root: Path
    observation_key: str


@dataclass(frozen=True, slots=True)
class CapsuleRequest:
    root: Path
    case_name: str
    repository: Path
    python_executable: Path
    inherited_environment: Mapping[str, str]
    opening_prompt: str
    material_receipt: RetainedMaterialReceipt | None = None


@dataclass(frozen=True, slots=True)
class _RetainedMaterialEvidenceAdapter:
    """Replay one retained receipt into a fresh acceptance Authority."""

    receipt: RetainedMaterialReceipt

    def open(
        self,
        *,
        authority: Authority,
        runs_directory: Path,
    ) -> tuple[RecordedPeriodicResponse, RecordedMaterialResponse]:
        if not runs_directory.is_dir():
            raise FileNotFoundError("acceptance_runs_directory_missing")
        source = Authority(self.receipt.authority_root)
        if not source.check().is_workspace_valid:
            raise ValueError("retained_material_authority_invalid")
        current = tuple(
            item
            for item in source.view().current
            if item.key == self.receipt.observation_key
        )
        if len(current) != 1:
            raise ValueError("retained_material_observation_missing")

        index_reference = current[0].body_reference
        index_document = Document.from_bytes(source.fetch(index_reference))
        index_values = index_document.values
        if set(index_values) != {
            "binding_reference",
            "observation_reference",
            "request_identity",
        }:
            raise ValueError("retained_material_index_invalid")
        binding_reference = Reference.from_mapping(
            _require_mapping(index_values["binding_reference"])
        )
        observation_reference = Reference.from_mapping(
            _require_mapping(index_values["observation_reference"])
        )
        observation_document = Document.from_bytes(source.fetch(observation_reference))
        observation = ObservedMaterials.from_document(
            observation_document,
            reference=observation_reference,
            activity=ExternalActivityClosure.recorded(),
        )
        if observation.solver_binding_reference != binding_reference:
            raise ValueError("retained_material_binding_mismatch")

        session = AuthoritySession(authority)
        _admit_retained_document(session, source, binding_reference)
        selection_references = tuple(
            selection.reference for selection in observation.selections
        )
        for selection_reference in selection_references:
            _admit_retained_document(session, source, selection_reference)
        _admit_retained_document(
            session,
            source,
            observation.product_sample_reference,
            references=(binding_reference, *selection_references),
        )
        admitted_observation = session.admit_document(
            observation_document,
            references=tuple(
                dict.fromkeys(
                    (
                        binding_reference,
                        observation.product_sample_reference,
                        *selection_references,
                    )
                )
            ),
        )
        if admitted_observation != observation_reference:
            raise RuntimeError("retained_material_observation_changed")
        admitted_index = session.admit_current(
            index_document,
            key=self.receipt.observation_key,
            supersedes=None,
            references=(observation_reference,),
        )
        if admitted_index != index_reference:
            raise RuntimeError("retained_material_index_changed")

        capacity_scope = "acceptance:retained_material_receipt"
        return (
            RecordedPeriodicResponse(
                session,
                context=PeriodicResponseContext(
                    binding_reference=binding_reference,
                    capacity_scope=capacity_scope,
                    response_kinds=tuple(PeriodicResponseKind),
                    qualification_closure=ExternalActivityClosure.recorded(),
                ),
            ),
            RecordedMaterialResponse(
                session,
                context=MaterialResponseContext(
                    binding_reference=binding_reference,
                    capacity_scope=capacity_scope,
                ),
            ),
        )


def _require_mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("retained_material_index_invalid")
    return value


def _admit_retained_document(
    session: AuthoritySession,
    source: Authority,
    reference: Reference,
    *,
    references: tuple[Reference, ...] = (),
) -> None:
    document = Document.from_bytes(source.fetch(reference))
    if session.admit_document(document, references=references) != reference:
        raise RuntimeError("retained_material_document_changed")


@dataclass(frozen=True, slots=True)
class HarnessPreflight:
    version: str
    missing_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HarnessInvocation:
    argv: tuple[str, ...]
    cwd: Path
    environment: Mapping[str, str]
    stdin: str | None


@dataclass(frozen=True, slots=True)
class PreparedHarnessRun:
    capsule: PreparedCapsule
    invocation: HarnessInvocation


HarnessAccess: TypeAlias = tuple[Literal["path", "read", "write"], str]


@dataclass(frozen=True, slots=True)
class HarnessObservation:
    event_count: int
    accesses: tuple[HarnessAccess, ...]
    commands: tuple[str, ...]
    violations: tuple[str, ...]
    explanation: str


CaptureCommand: TypeAlias = Callable[[tuple[str, ...]], str]


@dataclass(frozen=True, slots=True)
class CodexAcceptanceProfile:
    name: Literal["codex"] = "codex"

    def preflight(self, capture: CaptureCommand) -> HarnessPreflight:
        command = _installed_command("codex")
        version = capture((command, "--version"))
        top_level_help = capture((command, "--help"))
        help_text = capture((command, "exec", "--help"))
        top_level_required = ("--ask-for-approval",)
        exec_required = (
            "--ephemeral",
            "--ignore-user-config",
            "--strict-config",
            "--skip-git-repo-check",
            "--sandbox",
            "--cd",
            "--json",
        )
        return HarnessPreflight(
            version=version,
            missing_flags=(
                *(flag for flag in top_level_required if flag not in top_level_help),
                *(flag for flag in exec_required if flag not in help_text),
            ),
        )

    def prepare(self, request: CapsuleRequest) -> PreparedHarnessRun:
        capsule = _prepare_common_capsule(request)
        _materialize_canonical_skill(
            request.repository,
            capsule.root / ".agents" / "skills" / "metacraft-design" / "SKILL.md",
        )
        return self.prepare_session(
            capsule,
            inherited_environment=request.inherited_environment,
            opening_prompt=request.opening_prompt,
        )

    def prepare_session(
        self,
        capsule: PreparedCapsule,
        *,
        inherited_environment: Mapping[str, str],
        opening_prompt: str,
    ) -> PreparedHarnessRun:
        """Prepare one fresh Codex process over an existing capsule."""

        command = _installed_command("codex")
        invocation = HarnessInvocation(
            argv=(
                command,
                "--ask-for-approval",
                "never",
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--strict-config",
                "--skip-git-repo-check",
                "-C",
                str(capsule.root),
                "-s",
                "workspace-write",
                "-c",
                'web_search="disabled"',
                "-c",
                "sandbox_workspace_write.network_access=false",
                "--json",
                "-",
            ),
            cwd=capsule.root,
            environment=_reviewed_environment(
                inherited_environment,
                capsule=capsule.root,
                authentication_names={"CODEX_HOME", "OPENAI_API_KEY"},
            ),
            stdin=opening_prompt,
        )
        return PreparedHarnessRun(capsule=capsule, invocation=invocation)

    def observe(self, transcript: bytes) -> HarnessObservation:
        events, violations = _decode_jsonl(transcript)
        accesses: list[HarnessAccess] = []
        commands: list[str] = []
        messages: list[str] = []
        for event in events:
            shape_violation = _codex_event_shape_violation(event)
            if shape_violation is not None:
                violations.append(f"event:{shape_violation}")
                continue
            assert isinstance(event, dict)
            item = event.get("item")
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "agent_message":
                text = item.get("text")
                assert isinstance(text, str)
                messages.append(text)
            elif item_type == "command_execution":
                command = item.get("command")
                assert isinstance(command, str)
                commands.append(command)
                command_paths = _codex_command_paths(command)
                if command_paths is None:
                    violations.append(f"command:{command}")
                else:
                    accesses.extend(("read", path) for path in command_paths)
            elif item_type == "file_change":
                changes = item.get("changes")
                assert isinstance(changes, list)
                accesses.extend(
                    ("write", str(change["path"]))
                    for change in changes
                    if isinstance(change, dict)
                )
        return HarnessObservation(
            event_count=len(events),
            accesses=tuple(accesses),
            commands=tuple(commands),
            violations=tuple(violations),
            explanation=(
                messages[-1]
                if messages
                else "No final harness explanation was emitted."
            ),
        )


@dataclass(frozen=True, slots=True)
class ClaudeAcceptanceProfile:
    name: Literal["claude"] = "claude"

    def preflight(self, capture: CaptureCommand) -> HarnessPreflight:
        command = _installed_command("claude")
        version = capture((command, "--version"))
        help_text = capture((command, "--help"))
        required = (
            "--no-session-persistence",
            "--no-chrome",
            "--setting-sources",
            "--strict-mcp-config",
            "--mcp-config",
            "--tools",
            "--allowedTools",
            "--disallowedTools",
            "--permission-mode",
            "--output-format",
        )
        return HarnessPreflight(
            version=version,
            missing_flags=tuple(flag for flag in required if flag not in help_text),
        )

    def prepare(self, request: CapsuleRequest) -> PreparedHarnessRun:
        capsule = _prepare_common_capsule(request)
        _materialize_canonical_skill(
            request.repository,
            capsule.root / ".claude" / "skills" / "metacraft-design" / "SKILL.md",
        )
        (capsule.root / ".claude" / "settings.json").write_text(
            json.dumps(
                {
                    "permissions": {
                        "allow": ["Read(./**)", "Write(./**)", "Bash(metacraft *)"],
                        "deny": ["WebSearch", "WebFetch"],
                    }
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            encoding="utf-8",
            newline="",
        )
        (capsule.root / "empty-mcp.json").write_text(
            '{"mcpServers":{}}', encoding="utf-8", newline=""
        )
        return self.prepare_session(
            capsule,
            inherited_environment=request.inherited_environment,
            opening_prompt=request.opening_prompt,
        )

    def prepare_session(
        self,
        capsule: PreparedCapsule,
        *,
        inherited_environment: Mapping[str, str],
        opening_prompt: str,
    ) -> PreparedHarnessRun:
        """Prepare one fresh Claude process over an existing capsule."""

        command = _installed_command("claude")
        invocation = HarnessInvocation(
            argv=(
                command,
                "-p",
                "--no-session-persistence",
                "--no-chrome",
                "--setting-sources",
                "project",
                "--strict-mcp-config",
                "--mcp-config",
                str(capsule.root / "empty-mcp.json"),
                "--tools",
                "Read,Write,Bash",
                "--allowedTools",
                "Read(./**),Write(./**),Bash(metacraft *)",
                "--disallowedTools",
                "WebSearch,WebFetch",
                "--permission-mode",
                "dontAsk",
                "--output-format",
                "stream-json",
                "--verbose",
                opening_prompt,
            ),
            cwd=capsule.root,
            environment=_reviewed_environment(
                inherited_environment,
                capsule=capsule.root,
                authentication_names={"ANTHROPIC_API_KEY", "CLAUDE_CONFIG_DIR"},
            ),
            stdin=None,
        )
        return PreparedHarnessRun(capsule=capsule, invocation=invocation)

    def observe(self, transcript: bytes) -> HarnessObservation:
        events, violations = _decode_jsonl(transcript)
        accesses: list[HarnessAccess] = []
        commands: list[str] = []
        messages: list[str] = []
        for event in events:
            shape_violation = _claude_event_shape_violation(event)
            if shape_violation is not None:
                violations.append(f"event:{shape_violation}")
                continue
            assert isinstance(event, dict)
            if event.get("type") == "result":
                result = event.get("result")
                if isinstance(result, str):
                    messages.append(result)
            message = event.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            assert isinstance(content, list)
            for block in content:
                assert isinstance(block, dict)
                if block.get("type") != "tool_use":
                    continue
                tool_name = block.get("name")
                tool_input = block.get("input")
                assert isinstance(tool_name, str)
                assert isinstance(tool_input, dict)
                if tool_name not in {"Read", "Write", "Bash"}:
                    violations.append(f"tool:{tool_name}")
                    continue
                path = next(
                    (
                        tool_input[key]
                        for key in ("file_path", "path")
                        if isinstance(tool_input.get(key), str)
                    ),
                    None,
                )
                if tool_name in {"Read", "Write"} and not isinstance(path, str):
                    violations.append(f"event:{tool_name}")
                    continue
                if tool_name == "Read":
                    assert isinstance(path, str)
                    accesses.append(("read", path))
                elif tool_name == "Write":
                    assert isinstance(path, str)
                    accesses.append(("write", path))
                command_text = tool_input.get("command")
                if tool_name == "Bash" and not isinstance(command_text, str):
                    violations.append("event:Bash")
                    continue
                if tool_name == "Bash":
                    assert isinstance(command_text, str)
                    commands.append(command_text)
                    command_paths = _metacraft_command_paths(command_text)
                    if command_paths is None:
                        violations.append(f"command:{command_text}")
                    else:
                        accesses.extend(("path", path) for path in command_paths)
        return HarnessObservation(
            event_count=len(events),
            accesses=tuple(accesses),
            commands=tuple(commands),
            violations=tuple(violations),
            explanation=(
                messages[-1]
                if messages
                else "No final harness explanation was emitted."
            ),
        )


HarnessAcceptanceProfile: TypeAlias = CodexAcceptanceProfile | ClaudeAcceptanceProfile

ACCEPTANCE_PROFILES: tuple[HarnessAcceptanceProfile, ...] = (
    CodexAcceptanceProfile(),
    ClaudeAcceptanceProfile(),
)


def _prepare_common_capsule(request: CapsuleRequest) -> PreparedCapsule:
    """Build the harness-independent facts for one fresh external capsule."""

    if request.case_name not in CASE_NAMES:
        raise ValueError("acceptance_case_unknown")
    request.root.mkdir(parents=False, exist_ok=False)
    case = select_metalens_benchmark_case(request.case_name)
    brief_path = request.root / "blind-brief.json"
    brief_path.write_bytes(case.brief.canonical_bytes())
    material_library_path = request.root / "reviewed-materials.toml"
    shutil.copyfile(
        request.repository / "materials" / "lumerical.toml", material_library_path
    )
    prompt_path = request.root / "opening-prompt.txt"
    prompt_path.write_text(request.opening_prompt, encoding="utf-8", newline="")
    atom_family = case.brief.atom.material.family
    fixture_provenance = {
        **FIXTURE_PROVENANCE,
        "atom_refractive_index": _FIXTURE_ATOM_REFRACTIVE_INDICES[atom_family],
    }
    if request.material_receipt is None:
        (request.root / "fixture-provenance.json").write_text(
            json.dumps(
                fixture_provenance,
                separators=(",", ":"),
                sort_keys=True,
            ),
            encoding="utf-8",
            newline="",
        )
    else:
        _materialize_retained_material_receipt(
            request.material_receipt,
            request.root,
        )
    launcher = request.python_executable.parent / "Scripts" / "metacraft.exe"
    if not launcher.is_file():
        raise FileNotFoundError("installed_metacraft_launcher_missing")
    shutil.copyfile(launcher, request.root / "metacraft.exe")
    application_root = request.root / "prepared-application-root"
    material_library = SolverMaterialLibrary.decode_bytes(
        material_library_path.read_bytes()
    )
    if request.material_receipt is None:
        _prepare_application_root(
            case.brief,
            application_root,
            material_library=material_library,
            fixture_provenance=fixture_provenance,
        )
    else:
        prepared = conduct(
            case.brief,
            application_root=application_root,
            evidence_adapter=_RetainedMaterialEvidenceAdapter(request.material_receipt),
        )
        if (
            not isinstance(prepared, ConsultationRequired)
            or prepared.request.question_kind.value != "period"
        ):
            raise RuntimeError("retained_material_capsule_not_ready")
    return PreparedCapsule(
        root=request.root,
        case_name=request.case_name,
        application_root=application_root,
        brief_path=brief_path,
        material_library_path=material_library_path,
        prompt_path=prompt_path,
    )


def _materialize_canonical_skill(repository: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True)
    shutil.copyfile(
        repository / "skills" / "metacraft-design" / "SKILL.md", destination
    )


def _materialize_retained_material_receipt(
    receipt: RetainedMaterialReceipt,
    destination: Path,
) -> None:
    """Expose exact source-free receipt documents to one blind capsule."""

    source = Authority(receipt.authority_root)
    current = tuple(
        item for item in source.view().current if item.key == receipt.observation_key
    )
    if len(current) != 1:
        raise ValueError("retained_material_observation_missing")
    index_document = Document.from_bytes(source.fetch(current[0].body_reference))
    observation_reference = Reference.from_mapping(
        _require_mapping(index_document.values["observation_reference"])
    )
    observation_document = Document.from_bytes(source.fetch(observation_reference))
    observation = ObservedMaterials.from_document(
        observation_document,
        reference=observation_reference,
        activity=ExternalActivityClosure.recorded(),
    )
    documents = (
        ("reviewed-material-observation-index.json", index_document),
        ("reviewed-material-observation.json", observation_document),
        (
            "reviewed-material-product-sample.json",
            Document.from_bytes(source.fetch(observation.product_sample_reference)),
        ),
        (
            "reviewed-material-solver-binding.json",
            Document.from_bytes(source.fetch(observation.solver_binding_reference)),
        ),
        *(
            (
                f"reviewed-material-selection-{position:02d}.json",
                Document.from_bytes(source.fetch(selection.reference)),
            )
            for position, selection in enumerate(observation.selections, start=1)
        ),
    )
    for name, document in documents:
        (destination / name).write_bytes(document.to_bytes())


def _reviewed_environment(
    inherited: Mapping[str, str],
    *,
    capsule: Path,
    authentication_names: set[str],
) -> Mapping[str, str]:
    """Expose the shared runtime plus one profile's reviewed authentication."""

    runtime_names = {
        "APPDATA",
        "COMSPEC",
        "HOME",
        "LOCALAPPDATA",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    }
    allowed = runtime_names | authentication_names
    environment = {
        name: value for name, value in inherited.items() if name.upper() in allowed
    }
    environment["PATH"] = f"{capsule}{os.pathsep}{environment.get('PATH', '')}"
    return MappingProxyType(environment)


def audit_observation(
    observation: HarnessObservation,
    *,
    capsule: Path,
) -> dict[str, Any]:
    """Apply one shared confinement and answer-name policy."""

    paths = [value for _, value in observation.accesses]
    read_paths = [value for kind, value in observation.accesses if kind == "read"]
    write_paths = [value for kind, value in observation.accesses if kind == "write"]
    invalid_lines = [
        int(value.removeprefix("json:"))
        for value in observation.violations
        if value.startswith("json:")
    ]
    forbidden_events = [
        value.split(":", maxsplit=1)[1]
        for value in observation.violations
        if value.startswith(("event:", "tool:"))
    ]
    invalid_commands = [
        value.removeprefix("command:")
        for value in observation.violations
        if value.startswith("command:")
    ]

    outside_paths = []
    root = capsule.resolve()
    for raw_path in paths:
        normalized_path = raw_path.replace("\\", "/")
        if normalized_path == "$CAPSULE":
            candidate = root
        elif normalized_path.startswith("$CAPSULE/"):
            candidate = root / normalized_path.removeprefix("$CAPSULE/")
        else:
            candidate = Path(raw_path)
        resolved = (
            (root / candidate).resolve()
            if not candidate.is_absolute()
            else candidate.resolve()
        )
        if not resolved.is_relative_to(root):
            outside_paths.append(raw_path)
    invalid_write_paths = [
        path
        for path in write_paths
        if Path(path).name not in {"period-answer.json", "height-answer.json"}
    ]
    violations = {
        "invalid_jsonl_lines": invalid_lines,
        "forbidden_events": forbidden_events,
        "outside_capsule_paths": outside_paths,
        "invalid_commands": invalid_commands,
        "invalid_write_paths": invalid_write_paths,
    }
    return {
        "event_count": observation.event_count,
        "paths": paths,
        "read_paths": read_paths,
        "commands": list(observation.commands),
        "answer_write_paths": write_paths,
        "violations": violations,
        "is_confined": not any(violations.values()),
    }


def redact_transcript(
    transcript: bytes,
    *,
    capsule: Path,
    repository: Path,
) -> bytes:
    """Retain complete event lines while replacing machine-specific roots."""

    text = transcript.decode("utf-8", errors="replace")
    replacements = (
        (str(capsule), "$CAPSULE"),
        (str(capsule).replace("\\", "/"), "$CAPSULE"),
        (str(repository), "$REPOSITORY"),
        (str(repository).replace("\\", "/"), "$REPOSITORY"),
        (str(Path.home()), "$USER_HOME"),
        (str(Path.home()).replace("\\", "/"), "$USER_HOME"),
    )
    for source, replacement in replacements:
        forms = {source, re.sub(r"[:\\/]", "-", source)}
        for _ in range(4):
            forms.update(
                json.dumps(form, ensure_ascii=False)[1:-1] for form in tuple(forms)
            )
        for form in sorted(forms, key=len, reverse=True):
            text = text.replace(form, replacement)
    for name, value in os.environ.items():
        if (
            value
            and len(value) >= 8
            and re.search(
                r"(?:AUTH|COOKIE|CREDENTIAL|KEY|PASSWORD|SECRET|TOKEN)",
                name,
                re.IGNORECASE,
            )
        ):
            forms = {value}
            for _ in range(4):
                forms.update(
                    json.dumps(form, ensure_ascii=False)[1:-1] for form in tuple(forms)
                )
            for form in sorted(forms, key=len, reverse=True):
                text = text.replace(form, "$REDACTED_AUTH_VALUE")
    text = re.sub(
        r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        "$SESSION_ID",
        text,
    )
    return text.encode("utf-8")


def inspect_capsule(capsule: PreparedCapsule) -> dict[str, Any]:
    """Restore the blind scientific state without benchmark comparison."""

    brief = MetalensBrief.decode_canonical_bytes(capsule.brief_path.read_bytes())
    outcome = conduct(brief, application_root=capsule.application_root)
    studies = getattr(outcome, "studies", ())
    advice_records = []
    selected: dict[str, int] = {}
    period_context: dict[str, object] | None = None
    material: dict[str, object] | None = None
    authority = create_authority_reader(capsule.application_root)
    for study in studies:
        for advice in study.advice:
            if isinstance(advice, (PeriodAdvice, HeightAdvice)):
                advice_records.append(
                    {
                        "kind": (
                            "period" if isinstance(advice, PeriodAdvice) else "height"
                        ),
                        "request_identity": advice.request_identity,
                        "advice_identity": _digest(advice.document().to_bytes()),
                        "conclusion": advice.conclusion.as_mapping(),
                        "cited_grounds": list(
                            getattr(advice.conclusion, "decisive_ground_identities", ())
                        ),
                        "external_claims": [
                            claim.as_mapping() for claim in advice.external_claims
                        ],
                        "grounds": [ground.as_mapping() for ground in advice.grounds],
                    }
                )
        for evidence in study.evidence:
            if evidence.claim == "material_binding":
                binding = MaterialBinding.from_document(
                    Document.from_bytes(authority.fetch(evidence.reference)),
                    evidence_reference=evidence.reference,
                )
                sample_document = Document.from_bytes(
                    authority.fetch(binding.sample_reference)
                )
                solver_binding_document = Document.from_bytes(
                    authority.fetch(binding.solver_binding_reference)
                )
                restored = {
                    "atom": binding.atom.as_mapping(),
                    "binding_reference": evidence.reference.as_mapping(),
                    "sample": sample_document.as_mapping(),
                    "sample_reference": binding.sample_reference.as_mapping(),
                    "solver_binding": solver_binding_document.as_mapping(),
                    "solver_binding_reference": (
                        binding.solver_binding_reference.as_mapping()
                    ),
                    "source_identities": sorted(
                        {binding.atom.source, binding.substrate.source}
                    ),
                    "substrate": binding.substrate.as_mapping(),
                    "wavelength_nm": binding.wavelength_nm,
                }
                if material is not None and material != restored:
                    raise RuntimeError("acceptance_material_binding_ambiguous")
                material = restored
            elif evidence.claim == "period_choice":
                period_choice = PeriodChoice.from_document(
                    Document.from_bytes(authority.fetch(evidence.reference))
                )
                selected["period_nm"] = period_choice.period_nm
                period_context = {
                    "cautions": [
                        caution.as_mapping() for caution in period_choice.cautions
                    ],
                    "order_regime": period_choice.order_regime,
                }
            elif evidence.claim == "height_choice":
                selected["height_nm"] = HeightChoice.from_document(
                    Document.from_bytes(authority.fetch(evidence.reference))
                ).height_nm
    current_request = getattr(outcome, "request", None)
    result_references = [
        result.reference.as_mapping() for result in getattr(outcome, "results", ())
    ]
    answers = []
    for name in ("period-answer.json", "height-answer.json"):
        path = capsule.root / name
        if not path.is_file():
            continue
        body = path.read_bytes()
        try:
            answer = ConsultationAnswer.from_document(Document.from_bytes(body))
            answers.append(
                {
                    "name": name,
                    "identity": _digest(body),
                    "request_identity": answer.request_identity,
                    "is_canonical": answer.document().to_bytes() == body,
                }
            )
        except (TypeError, ValueError):
            answers.append(
                {"name": name, "identity": _digest(body), "is_canonical": False}
            )
    return {
        "outcome": type(outcome).__name__,
        "authority_revision": authority.view().revision.value,
        "current_request_identity": (
            None if current_request is None else current_request.identity
        ),
        "current_question": (
            None if current_request is None else current_request.question_kind.value
        ),
        "result_references": result_references,
        "advice": advice_records,
        "evidence_claims": sorted(
            {evidence.claim for study in studies for evidence in study.evidence}
        ),
        "material": material,
        "period": period_context,
        "ready_claims": sorted(
            {task.claim for study in studies for task in study.ready_tasks}
        ),
        "selected": selected,
        "answers": answers,
    }


def create_authority_reader(application_root: Path):
    """Open the fixed Authority workspace for blind inspection."""

    from metacraft.authority import Authority

    return Authority(application_root / "authority")


def _decode_jsonl(
    transcript: bytes,
) -> tuple[list[object], list[str]]:
    events: list[object] = []
    violations: list[str] = []
    for line_number, line in enumerate(transcript.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            violations.append(f"json:{line_number}")
    return events, violations


def _codex_event_shape_violation(
    value: object,
) -> str | None:
    if not isinstance(value, dict):
        return "event_not_object"
    event_type = value.get("type")
    if not isinstance(event_type, str):
        return "event_type_missing"
    event = value
    if event_type == "thread.started":
        return None if isinstance(event.get("thread_id"), str) else "thread.started"
    if event_type == "turn.started":
        return None
    if event_type == "turn.completed":
        return None if isinstance(event.get("usage"), dict) else "turn.completed"
    if event_type not in {"item.started", "item.completed"}:
        return event_type
    item = event.get("item")
    if not isinstance(item, dict):
        return event_type
    item_type = item.get("type")
    if item_type == "agent_message":
        is_valid = isinstance(item.get("text"), str)
    elif item_type == "command_execution":
        is_valid = isinstance(item.get("command"), str)
    elif item_type == "file_change":
        changes = item.get("changes")
        is_valid = isinstance(changes, list) and all(
            isinstance(change, dict) and isinstance(change.get("path"), str)
            for change in changes
        )
    elif item_type == "reasoning":
        is_valid = isinstance(item.get("text"), str)
    else:
        return str(item_type) if item_type is not None else event_type
    return None if is_valid else str(item_type)


def _claude_event_shape_violation(
    value: object,
) -> str | None:
    if not isinstance(value, dict):
        return "event_not_object"
    event_type = value.get("type")
    if not isinstance(event_type, str):
        return "event_type_missing"
    event = value
    if event_type == "system":
        return None if isinstance(event.get("subtype"), str) else "system"
    if event_type == "result":
        return None if isinstance(event.get("subtype"), str) else "result"
    if event_type not in {"assistant", "user"}:
        return event_type
    message = event.get("message")
    if not isinstance(message, dict):
        return event_type
    content = message.get("content")
    if not isinstance(content, list):
        return event_type
    for block in content:
        if not isinstance(block, dict):
            return event_type
        block_type = block.get("type")
        if block_type == "text" and isinstance(block.get("text"), str):
            continue
        if (
            block_type == "tool_use"
            and isinstance(block.get("name"), str)
            and isinstance(block.get("input"), dict)
        ):
            continue
        if block_type == "tool_result" and isinstance(block.get("tool_use_id"), str):
            continue
        return str(block_type) if block_type is not None else event_type
    return None


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _installed_command(name: Literal["codex", "claude"]) -> str:
    command = shutil.which(name)
    if command is None:
        raise FileNotFoundError(f"{name}_command_missing")
    return command


def _codex_command_paths(command: str) -> list[str] | None:
    """Return capsule paths for one reviewed Codex read/command shape."""

    command = command.replace("\\\\", "\\")
    wrapper = re.fullmatch(
        r'"[^"\r\n]*[\\/]WindowsPowerShell[\\/]v1\.0[\\/]powershell\.exe" '
        r'-Command "(?P<body>.*)"',
        command.strip(),
        re.IGNORECASE,
    )
    if wrapper is None:
        return None
    body = wrapper.group("body").strip()
    if re.search(
        r"(?:\b(?:curl|env|invoke-webrequest|irm|iwr|printenv|set|ssh|scp)\b|"
        r"env:|\$(?:env|Env):|(?:secret|token|password|credential|api[_-]?key))",
        body,
        re.IGNORECASE,
    ):
        return None

    content_paths: list[str] = []
    content_parts = [part.strip() for part in body.split(";")]
    if all(
        re.fullmatch(r"Get-Content -Raw '(?P<path>[^']+)'", part, re.IGNORECASE)
        for part in content_parts
    ):
        for part in content_parts:
            match = re.fullmatch(
                r"Get-Content -Raw '(?P<path>[^']+)'", part, re.IGNORECASE
            )
            assert match is not None
            content_paths.append(match.group("path"))
        return content_paths

    if _is_capsule_file_search(body):
        return []
    child_items = re.fullmatch(
        r"Get-ChildItem -Recurse -Force '(?P<path>[^']+)' \| "
        r"Select-Object FullName,Length,LastWriteTime",
        body,
        re.IGNORECASE,
    )
    if child_items is not None:
        return [child_items.group("path")]
    if re.fullmatch(r"\.\\metacraft\.exe (?:--help|conduct --help)", body, re.I):
        return [r".\metacraft.exe"]
    if body.casefold().startswith(r".\metacraft.exe conduct "):
        paths = _metacraft_command_paths(body)
        return None if paths is None else [r".\metacraft.exe", *paths]
    resolve_help = re.fullmatch(
        r"& \(Resolve-Path '(?P<path>\.\\metacraft\.exe)'\) --help",
        body,
        re.IGNORECASE,
    )
    if resolve_help is not None:
        return [resolve_help.group("path")]
    return None


def _metacraft_command_paths(command: str) -> list[str] | None:
    if re.search(r"[;&|<>`\r\n]", command):
        return None
    try:
        parts = [part.strip("\"'") for part in shlex.split(command, posix=False)]
    except ValueError:
        return None
    if (
        len(parts) < 3
        or Path(parts[0]).name.casefold()
        not in {
            "metacraft",
            "metacraft.exe",
        }
        or parts[1] != "conduct"
    ):
        return None
    path_options = {
        "--answer",
        "--application-root",
        "--brief",
        "--lumerical-environment",
        "--material-library",
    }
    paths: list[str] = []
    index = 2
    while index < len(parts):
        option = parts[index]
        if option not in path_options or index + 1 >= len(parts):
            return None
        paths.append(parts[index + 1])
        index += 2
    required = {"--application-root", "--brief", "--material-library"}
    if not required <= set(parts):
        return None
    return paths


def _is_capsule_file_search(command: str) -> bool:
    """Accept only pathless ``rg --files`` searches rooted at the capsule cwd."""

    prefix = "rg --files"
    if command == prefix:
        return True
    if not command.startswith(prefix + " "):
        return False
    filters = (" " + command.removeprefix(prefix + " ")).split(" -g ")
    if filters[0] != "":
        return False
    for quoted_pattern in filters[1:]:
        if re.search(r"\s", quoted_pattern):
            return False
        pattern = quoted_pattern.replace("'", "").replace('"', "")
        if not pattern or re.search(r"[;&|<>`$\r\n]", pattern):
            return False
        normalized = pattern.replace("\\", "/")
        if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
            return False
        if ".." in Path(normalized).parts:
            return False
    return True


def _prepare_application_root(
    brief,
    application_root: Path,
    *,
    material_library: SolverMaterialLibrary,
    fixture_provenance: Mapping[str, str],
) -> None:
    authority = create_authority_in_new_application_root(application_root)
    session = AuthoritySession(authority)
    initial = compile_metalens(brief)
    if not isinstance(initial, Study):
        raise ValueError("acceptance_brief_invalid")

    implementation_references = {
        "optical_material": session.admit_object(
            b"fixture optical material",
            media_type="application/octet-stream",
            descriptive_metadata={"fixture": "interface acceptance"},
        ),
        "fabrication_constraint": session.admit_object(
            b"fixture fabrication",
            media_type="application/octet-stream",
            descriptive_metadata={"fixture": "interface acceptance"},
        ),
        "deterministic_selection": session.admit_object(
            b"fixture selection",
            media_type="application/octet-stream",
            descriptive_metadata={"fixture": "interface acceptance"},
        ),
    }
    capabilities = tuple(Capability(name) for name in implementation_references)
    bindings = tuple(
        Binding(name, reference)
        for name, reference in implementation_references.items()
    )

    atom_registration = material_library.select(brief.atom.material.family)
    substrate_registration = material_library.select(brief.substrate.family)
    if atom_registration is None or substrate_registration is None:
        raise ValueError("acceptance_material_registration_missing")
    solver_reference = session.admit_document(
        Document(
            "metacraft.acceptance.material_registration_set",
            {
                "atom": atom_registration.document().as_mapping(),
                "purpose": fixture_provenance["purpose"],
                "substrate": substrate_registration.document().as_mapping(),
            },
        ),
    )
    sample_document = Document(
        "metacraft.acceptance.material_sample_fixture",
        {
            "atom_extinction_coefficient": "0",
            "atom_refractive_index": fixture_provenance["atom_refractive_index"],
            "purpose": fixture_provenance["purpose"],
            "substrate_extinction_coefficient": "0",
            "substrate_refractive_index": fixture_provenance[
                "substrate_refractive_index"
            ],
            "wavelength_nm": require_monochromatic_wavelength(brief.operating_spectrum),
        },
    )
    sample_reference = session.admit_document(sample_document)
    binding = material_binding(
        initial,
        atom_index=fixture_provenance["atom_refractive_index"],
        substrate_index=fixture_provenance["substrate_refractive_index"],
    )
    binding = replace(
        binding,
        atom=replace(binding.atom, native_name=atom_registration.native_name),
        substrate=replace(
            binding.substrate,
            native_name=substrate_registration.native_name,
        ),
        solver_binding_reference=solver_reference,
        sample_reference=sample_reference,
    )
    binding = replace(
        binding,
        evidence_reference=reference_for(binding.document().to_bytes()),
    )
    binding_reference = session.admit_document(
        binding.document(), references=(solver_reference, sample_reference)
    )
    if binding.evidence_reference != binding_reference:
        raise RuntimeError("acceptance_material_binding_identity_changed")

    domain = derive_period_domain(initial, binding)
    domain_reference = session.admit_document(
        domain.document(), references=(binding_reference,)
    )
    domain = domain.bind_evidence(domain_reference)

    before_target = compile_metalens(
        brief,
        capabilities=capabilities,
        bindings=bindings,
    )
    target_task = next(
        task for task in before_target.ready_tasks if task.claim == "target_phase"
    )
    target_reference = session.admit_document(
        Document(
            target_task.schema,
            {"fixture": "interface acceptance; not physical truth"},
        )
    )
    waiting, _ = compile_with_facts(
        brief,
        {
            "target_phase": target_reference,
            "material_binding": binding_reference,
            "period_domain": domain_reference,
        },
        capabilities=capabilities,
        bindings=bindings,
    )
    frontier = StudyFrontier.start(waiting)
    session.admit_current(
        frontier.document(),
        key=frontier.key,
        supersedes=None,
        references=frontier.references(),
    )
