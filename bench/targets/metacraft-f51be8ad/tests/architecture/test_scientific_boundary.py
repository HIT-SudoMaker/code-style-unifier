from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import re
from typing import cast

import pytest

import metacraft
import metacraft.field as field
import metacraft.science as science
import metacraft.science.metalens as metalens
import metacraft.science.metalens.relationship as metalens_relationship
from metacraft.field.angular_spectrum import FieldPropagation
from metacraft.science import (
    Brief,
    UnsupportedAim,
    compile_study,
)
from metacraft.science.metalens import (
    MetalensBrief,
    MetalensDesign,
    require_metalens_design,
)
from metacraft.science.metalens.focus import observe_focal_region
from metacraft.science.study import Design, Study
from tests.brief_fixtures import propagation_brief


ROOT = Path(__file__).parents[2]


def test_only_current_scientific_completion_surfaces_are_public() -> None:
    route_root = ROOT / "src" / "metacraft" / "science" / "routes"

    assert not tuple(route_root.glob("*.py"))
    assert (
        ROOT
        / "src"
        / "metacraft"
        / "science"
        / "metalens"
        / "propagation_phase.py"
    ).is_file()
    assert (
        ROOT
        / "src"
        / "metacraft"
        / "science"
        / "metalens"
        / "geometric_phase.py"
    ).is_file()
    assert (
        ROOT
        / "src"
        / "metacraft"
        / "science"
        / "metalens"
        / "result.py"
    ).is_file()
    assert "focus_metrics" not in field.__all__
    assert not hasattr(field, "focus_metrics")
    assert {
        "FocalRegion",
        "Focus",
        "FocusSurvey",
        "Leakage",
        "evaluate_focus",
    }.isdisjoint(field.__all__)
    assert {
        "FocalRegion",
        "Focus",
        "FocusSurvey",
        "Leakage",
        "evaluate_focus",
    }.issubset(metalens.__all__)


def test_shared_field_signatures_name_no_metalens_value() -> None:
    """
    Cross-aim Field operations cannot accept Aperture or return FocalRegion.
    """

    for name in field.__all__:
        exported = getattr(field, name)
        if not callable(exported):
            continue
        try:
            signature = str(inspect.signature(exported))
        except (TypeError, ValueError):
            continue
        assert "Aperture" not in signature, name
        assert "FocalRegion" not in signature, name


def test_metalens_completion_consumes_one_finished_field_propagation() -> None:
    """
    Focus assembly consumes a completed propagation through a data-only seam.
    """

    public_callables = {
        name
        for name, member in inspect.getmembers(
            FieldPropagation,
            predicate=callable,
        )
        if not name.startswith("_")
    }
    annotations = inspect.get_annotations(
        observe_focal_region,
        eval_str=True,
    )

    assert public_callables == set()
    assert annotations["propagation"] is FieldPropagation
    assert tuple(inspect.signature(observe_focal_region).parameters) == (
        "propagation",
        "field_reference",
        "expected_focus_m",
    )


def test_metalens_owns_its_aim_local_language() -> None:
    """
    Aim-local metalens intent and applicability terms live under metalens.
    """

    assert "MetalensBrief" in metalens.__all__
    assert "MetalensDesign" in metalens.__all__
    assert "ControlStrategy" in metalens.__all__
    assert issubclass(MetalensDesign, Design)
    assert "ApertureRegime" not in metalens.__all__
    assert not hasattr(metalens, "ApertureRegime")


def test_aperture_is_exported_by_metalens_not_shared_surfaces() -> None:
    """
    The metalens aperture value belongs to metalens science; it never appears
    on the shared science or field public surfaces.
    """

    assert "Aperture" in metalens.__all__
    assert "Cell" in metalens.__all__
    assert {
        "Lattice",
        "Response",
        "State",
        "aperture_document",
        "assign_quantized",
        "circular_lattice",
    }.isdisjoint(metalens.__all__)
    assert "Aperture" not in science.__all__
    assert "Aperture" not in field.__all__
    assert not hasattr(science, "Aperture")
    assert not hasattr(field, "Aperture")


def test_metalens_root_exports_values_without_schema_constants() -> None:
    """
    Stable schemas stay beside their owning values, not on the package root.
    """

    assert not {
        name for name in vars(metalens) if name.endswith("_SCHEMA")
    }


def test_generic_science_keeps_only_the_shared_lifecycle() -> None:
    """
    Generic science names the lifecycle and leaves aim-local intent to aims.

    Generic science exports only the shared lifecycle. Aim-owned consultation
    records remain behind their owning scientific Modules.
    """

    assert set(science.__all__) == {
        "Binding",
        "Brief",
        "Capability",
        "CompileOutcome",
        "CompletedResults",
        "ConsultationAnswerRejected",
        "ConsultationRequired",
        "ConductOutcome",
        "Evidence",
        "Finding",
        "FindingKind",
        "InvalidBrief",
        "Result",
        "Study",
        "UnsupportedAim",
        "WaitingStudies",
        "compile_study",
        "conduct",
    }
    # Metalens-only language is absent from the generic shared surface.
    assert "ApertureRegime" not in science.__all__
    assert "MetalensBrief" not in science.__all__
    assert "MetalensDesign" not in science.__all__
    assert "ControlStrategy" not in science.__all__
    assert "PeriodAdvice" not in science.__all__
    assert "HeightAdvice" not in science.__all__
    assert not hasattr(science, "ApertureRegime")
    assert not hasattr(science, "MetalensBrief")
    assert not hasattr(science, "MetalensDesign")
    assert not hasattr(science, "standard_propagation_brief")
    assert not hasattr(science, "standard_geometric_brief")


def test_design_keeps_the_physical_aperture_fact_without_a_regime() -> None:
    """
    Numerical aperture stays exact; a derived regime placeholder does not.
    """

    design_fields = {
        field.name for field in Design.__dataclass_fields__.values()
    }
    assert "aperture_regime" not in design_fields
    metalens_fields = {
        field.name
        for field in MetalensDesign.__dataclass_fields__.values()
    }
    assert "aperture_regime" not in metalens_fields
    assert "numerical_aperture" in metalens_fields


def test_brief_and_design_identity_exclude_decorative_names() -> None:
    """Canonical science identity contains user facts, not display labels."""

    assert "name" not in Brief.__dataclass_fields__
    assert "name" not in Design.__dataclass_fields__
    assert "name" not in MetalensBrief.__dataclass_fields__
    assert "name" not in MetalensDesign.__dataclass_fields__


def test_metalens_owns_the_only_strict_design_narrowing() -> None:
    study = compile_study(propagation_brief())

    assert isinstance(study, Study)
    assert not hasattr(study, "metalens")
    assert require_metalens_design(study) is study.design
    generic = Study.from_document(study.document())
    with pytest.raises(RuntimeError, match="metalens_design_required"):
        require_metalens_design(generic)
    assert "require_metalens_design" in metalens.__all__
    assert "require_metalens_design" not in science.__all__


def test_unimplemented_aim_returns_a_typed_refusal() -> None:
    """
    A declared but unimplemented aim refuses compilation without a fake Study.
    """

    brief = Brief(
        wording="Reconstruct one holographic field.",
        aim="holographic metasurface",
        objectives=("reconstruction",),
        budget="relationship only",
    )

    outcome = compile_study(brief)

    assert isinstance(outcome, UnsupportedAim)
    assert outcome.aim == "holographic metasurface"
    assert not hasattr(outcome, "study")
    assert not hasattr(outcome, "proof")
    assert not hasattr(outcome, "finding")


def test_aperture_above_half_selects_the_pointwise_vector_route() -> None:
    """
    High aperture keeps its requested NA and selects qualified vector work.
    """

    brief = propagation_brief().replace_numerical_aperture("0.70")
    study = compile_study(brief)
    assert isinstance(study, Study)
    choices = {
        choice.claim: choice.method for choice in study.route.choices
    }

    assert (
        cast(MetalensBrief, study.brief).numerical_aperture
        == brief.numerical_aperture
    )
    assert choices["cell_surface_table"] == "gather_cell_surfaces"
    assert choices["aperture"] == "assign_aperture"
    assert choices["focal_region"] == "propagate_field"
    assert choices["aplanatic_reference"] == "form_aplanatic_reference"
    assert choices["focal_comparison"] == "compare_focal_field"


def test_speculative_proof_graphs_are_absent() -> None:
    """
    No unimplemented aim owns claims, methods, fake evidence, or a proof graph.
    """

    relationships = (
        ROOT / "src" / "metacraft" / "science" / "relationships.py"
    ).read_text(encoding="utf-8")
    metalens_relationship = (
        ROOT
        / "src"
        / "metacraft"
        / "science"
        / "metalens"
        / "relationship.py"
    ).read_text(encoding="utf-8")
    metalens_design_source = (
        ROOT
        / "src"
        / "metacraft"
        / "science"
        / "metalens"
        / "design.py"
    ).read_text(encoding="utf-8")
    metalens_compiler = (
        ROOT
        / "src"
        / "metacraft"
        / "science"
        / "metalens"
        / "compiler.py"
    ).read_text(encoding="utf-8")
    joined = "\n".join(
        (
            relationships,
            metalens_relationship,
            metalens_design_source,
            metalens_compiler,
        )
    )

    for forbidden in (
        "ApertureRegime",
        "LARGE_NA",
        "large_na_",
        "_holographic",
        "_quasi_bic",
        "_frequency_selective",
        "holographic_target_field",
        "symmetry_analysis",
        "normalized_scattering_response",
        "form_vector_field",
        "evaluate_vector_focus",
        "large_na_field_evaluation",
        "large_na_focus_evaluation",
    ):
        assert forbidden not in joined, forbidden


def test_compiler_public_surfaces_have_contract_docs() -> None:
    for module in (field, science, metalens):
        for name in module.__all__:
            exported = getattr(module, name)
            assert inspect.getdoc(exported), (
                f"{module.__name__}.{name} lacks a public contract"
            )
            if not inspect.isclass(exported):
                continue
            for member_name, member in exported.__dict__.items():
                if member_name.startswith("_"):
                    continue
                contract = member.fget if isinstance(member, property) else member
                if callable(contract):
                    assert inspect.getdoc(contract), (
                        f"{module.__name__}.{name}.{member_name} "
                        "lacks a public contract"
                    )


def test_manual_lifecycle_examples_are_retired() -> None:
    examples = ROOT / "examples"

    assert not (examples / "propagation_phase_evaluate.py").exists()
    assert not (examples / "propagation_phase_live.py").exists()


def test_root_exposes_one_atomic_scientific_lifecycle() -> None:
    assert metacraft.__all__ == ["Authority", "compile_study", "conduct"]
    assert not (ROOT / "src" / "metacraft" / "local.py").exists()
    assert not (ROOT / "src" / "metacraft" / "_local").exists()


def test_shared_result_closure_knows_only_scientific_documents() -> None:
    source = (
        ROOT / "src" / "metacraft" / "science" / "result.py"
    ).read_text(encoding="utf-8")

    for authority_detail in (
        "from ..authority import Authority",
        "metacraft.authority.proposal",
        ".view().decisions",
        "Structure",
        "_verify_admission",
    ):
        assert authority_detail not in source


def test_scientific_relationship_language_remains_private() -> None:
    assert {
        "Method",
        "Relationship",
        "relationship_for",
        "registry",
        "plugin",
    }.isdisjoint(science.__all__)
    assert not hasattr(science, "relationship_for")
    assert "relationship_for" not in metalens.__all__
    assert {
        "APERTURE_SCHEMA",
        "TARGET_PHASE_SCHEMA",
        "PERIODIC_TRANSMISSION_SCHEMA",
    }.isdisjoint(vars(metalens_relationship))


def test_rust_tree_matches_the_committed_source_manifest() -> None:
    """
    The Rust baseline is frozen by a committed source manifest, not by Git.

    The check derives the governed set from the working tree and matches it
    against rust/SOURCE_MANIFEST.json. It needs no ``.git`` directory, so a
    source archive verifies the exact Rust baseline. Line endings are
    normalized (CRLF -> LF) before hashing so the manifest is stable on a
    Windows checkout (core.autocrlf) and in an LF source archive.
    """
    rust_root = ROOT / "rust"
    manifest = json.loads(
        (rust_root / "SOURCE_MANIFEST.json").read_text(encoding="utf-8")
    )

    governed = {
        path.relative_to(rust_root).as_posix(): _rust_source_sha256(path)
        for path in _governed_rust_paths()
    }

    stale = set(manifest) - set(governed)
    assert not stale, (
        "manifest references paths that are not governed or are missing: "
        f"{sorted(stale)}"
    )

    unlisted = set(governed) - set(manifest)
    assert not unlisted, (
        "governed Rust files are absent from the manifest "
        f"(regenerate rust/SOURCE_MANIFEST.json): {sorted(unlisted)}"
    )

    mismatches = [
        relative
        for relative in sorted(governed)
        if manifest[relative] != governed[relative]
    ]
    assert not mismatches, (
        "governed Rust files differ from the committed manifest "
        f"(regenerate rust/SOURCE_MANIFEST.json after intentional changes): "
        f"{mismatches}"
    )


def _governed_rust_paths() -> list[Path]:
    # Governance rule (must stay in sync with rust/sync_source_manifest.py):
    #   - Cargo.toml and Cargo.lock at the rust root;
    #   - every *.rs under rust/src and rust/tests;
    #   - every fixture under rust/tests/fixtures.
    # rust/target (build output) and the manifest itself are never governed;
    # they are outside the walked roots and so are naturally excluded.
    rust_root = ROOT / "rust"
    paths: list[Path] = []
    for name in ("Cargo.toml", "Cargo.lock"):
        candidate = rust_root / name
        if candidate.is_file():
            paths.append(candidate)
    for sub in ("src", "tests"):
        base = rust_root / sub
        for file_path in sorted(base.rglob("*")):
            if not file_path.is_file():
                continue
            relative = file_path.relative_to(rust_root).as_posix()
            if file_path.suffix == ".rs" or relative.startswith("tests/fixtures/"):
                paths.append(file_path)
    manifest = rust_root / "SOURCE_MANIFEST.json"
    return sorted({path for path in paths if path != manifest})


def _rust_source_sha256(path: Path) -> str:
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    return "sha256:" + hashlib.sha256(normalized).hexdigest()


def test_rust_source_names_only_authority_concerns() -> None:
    source_root = ROOT / "rust" / "src"
    sources = tuple(sorted(source_root.rglob("*.rs")))
    relative = tuple(path.relative_to(source_root).as_posix() for path in sources)
    joined = "\n".join(
        path.read_text(encoding="utf-8") for path in sources
    ).casefold()
    forbidden = {
        "advice",
        "aperture",
        "brief",
        "campaign",
        "deepseek",
        "design",
        "fdtd",
        "geometry",
        "lumerical",
        "material",
        "metalens",
        "metric",
        "optimizer",
        "pancharatnam",
        "phase",
        "polarization",
        "route",
        "scientific",
        "simulation",
        "solver",
        "study",
        "sweep",
        "task",
        "workflow",
    }

    assert all(re.search(r"(?i)v\d", name) is None for name in relative)
    assert all(name not in joined for name in forbidden)
    assert re.search(r"(?i)v\d", joined) is None


def test_normative_docs_name_the_current_scientific_chain() -> None:
    science_doc = (ROOT / "SCIENCE.md").read_text(encoding="utf-8")
    context = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")

    assert "phase set → aperture → field → focal region → focus → result" in (
        science_doc
    )
    assert "`0.8f` to `1.2f`" in science_doc
    assert "sealed public conclusion seam" in science_doc
    assert "geometric conclusion seam remains pending" not in science_doc
    assert "**phase set**" in context
    assert "**aperture**" in context
    assert "**focus**" in context
