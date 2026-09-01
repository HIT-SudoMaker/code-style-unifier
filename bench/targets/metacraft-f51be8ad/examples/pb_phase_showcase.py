from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from metacraft import conduct
from metacraft.authority import Authority, Document, Reference
from metacraft.science import CompletedResults, ConductOutcome
from metacraft.science.metalens import GeometricResult, MetalensBrief
from metacraft.science.metalens.evidence_adapter import MetalensEvidenceAdapter
from metacraft.science.metalens.result import restore_conclusion


_SCHEMA = "metacraft.examples.pb_phase_showcase"
Fetch = Callable[[Reference], bytes]


def run_pb_phase_showcase(
    brief: MetalensBrief,
    *,
    application_root: Path,
    evidence_adapter: MetalensEvidenceAdapter | None = None,
    orientation_count: int = 16,
) -> ConductOutcome | Document:
    """
    Conduct one real application life and expose its admitted PB Result.

    Waiting, consultation, invalid, and unsupported outcomes cross this source
    example unchanged. No Result is manufactured when evidence is incomplete.
    """

    outcome = conduct(
        brief,
        application_root=application_root,
        evidence_adapter=evidence_adapter,
    )
    if not isinstance(outcome, CompletedResults):
        return outcome
    authority = Authority(Path(application_root) / "authority")
    return pb_phase_showcase(
        outcome,
        fetch=authority.fetch,
        orientation_count=orientation_count,
    )


def pb_phase_showcase(
    completed: CompletedResults,
    *,
    fetch: Fetch,
    orientation_count: int = 16,
) -> Document:
    """Project one explicitly selected admitted PB Result."""

    candidates = []
    for result in completed.results:
        conclusion = restore_conclusion(result.document, fetch=fetch)
        if (
            isinstance(conclusion, GeometricResult)
            and len(conclusion.aperture.states) == orientation_count
        ):
            candidates.append((result, conclusion))
    if len(candidates) != 1:
        raise ValueError("pb_showcase_result_not_unique")
    result, conclusion = candidates[0]
    cell = conclusion.aperture.cells[0]
    ordered_states = sorted(
        conclusion.aperture.states,
        key=lambda state: state.target_phase,
    )
    states = [
        {
            "cell_identity": cell.identity,
            "cell_source": cell.source.as_mapping(),
            "geometry": {
                "dimensions_nm": cell.geometry.as_mapping(),
                "shape": cell.shape,
            },
            "orientation_index": index,
            "orientation_rad": format(state.orientation_rad, "f"),
            "orientation_source": state.source.as_mapping(),
            "realized_phase_rad": format(state.realized_phase, "f"),
            "target_phase_rad": format(state.target_phase, "f"),
        }
        for index, state in enumerate(ordered_states)
    ]
    orientation_set_reference = ordered_states[0].source
    return Document(
        _SCHEMA,
        {
            "brief_identity": completed.brief_identity,
            "execution_origin": conclusion.execution_origin.value,
            "focus": conclusion.focus.as_mapping(),
            "orientation_count": orientation_count,
            "orientation_relation": {
                "converted_phase_rad": format(
                    conclusion.orientation_relation.converted_phase,
                    "f",
                ),
                "phase_sign": conclusion.orientation_relation.phase_sign,
            },
            "orientation_states": states,
            "references": {
                "aperture": conclusion.aperture_reference.as_mapping(),
                "cell_choice": conclusion.choice_reference.as_mapping(),
                "converted_field": conclusion.field_reference.as_mapping(),
                "focal_region": (
                    conclusion.focal_region_reference.as_mapping()
                ),
                "focus": conclusion.focus_reference.as_mapping(),
                "orientation_relation": (
                    conclusion.orientation_relation_reference.as_mapping()
                ),
                "orientation_set": orientation_set_reference.as_mapping(),
                "result": result.reference.as_mapping(),
            },
            "showcase": "monochromatic PB phase",
        },
    )


__all__ = ["pb_phase_showcase", "run_pb_phase_showcase"]
