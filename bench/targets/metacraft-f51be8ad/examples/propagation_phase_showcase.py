from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from metacraft import conduct
from metacraft.authority import Authority, Document, Reference
from metacraft.science import CompletedResults, ConductOutcome
from metacraft.science.metalens import MetalensBrief, PropagationResult
from metacraft.science.metalens.evidence_adapter import MetalensEvidenceAdapter
from metacraft.science.metalens.result import restore_conclusion


_SCHEMA = "metacraft.examples.propagation_phase_showcase"
Fetch = Callable[[Reference], bytes]


def run_propagation_phase_showcase(
    brief: MetalensBrief,
    *,
    application_root: Path,
    evidence_adapter: MetalensEvidenceAdapter | None = None,
    phase_levels: int = 16,
) -> ConductOutcome | Document:
    """
    Conduct one real application life and expose its propagation Result.

    A typed conduct stop is returned unchanged. Only an admitted
    ``CompletedResults`` value is projected as a showcase document.
    """

    outcome = conduct(
        brief,
        application_root=application_root,
        evidence_adapter=evidence_adapter,
    )
    if not isinstance(outcome, CompletedResults):
        return outcome
    authority = Authority(Path(application_root) / "authority")
    return propagation_phase_showcase(
        outcome,
        fetch=authority.fetch,
        phase_levels=phase_levels,
    )


def propagation_phase_showcase(
    completed: CompletedResults,
    *,
    fetch: Fetch,
    phase_levels: int = 16,
) -> Document:
    """Project one explicitly selected admitted propagation Result."""

    candidates = []
    for result in completed.results:
        conclusion = restore_conclusion(result.document, fetch=fetch)
        if (
            isinstance(conclusion, PropagationResult)
            and conclusion.phase_level_count == phase_levels
        ):
            candidates.append((result, conclusion))
    if len(candidates) != 1:
        raise ValueError("propagation_showcase_result_not_unique")
    result, conclusion = candidates[0]
    cells = {cell.identity: cell for cell in conclusion.aperture.cells}
    states = []
    for state in conclusion.phase_set.states:
        cell = cells[state.cell_id]
        states.append(
            {
                "cell_identity": cell.identity,
                "cell_source": cell.source.as_mapping(),
                "geometry": {
                    "dimensions_nm": cell.geometry.as_mapping(),
                    "shape": cell.shape,
                },
                "phase_level": state.phase_level,
                "realized_phase_rad": format(state.realized_phase, "f"),
                "response_source": state.source_reference.as_mapping(),
                "target_phase_rad": format(state.target_phase, "f"),
            }
        )
    return Document(
        _SCHEMA,
        {
            "brief_identity": completed.brief_identity,
            "execution_origin": conclusion.execution_origin.value,
            "focus": conclusion.focus.as_mapping(),
            "phase_levels": phase_levels,
            "phase_states": states,
            "references": {
                "aperture": conclusion.aperture_reference.as_mapping(),
                "field": conclusion.field_reference.as_mapping(),
                "focal_region": (
                    conclusion.focal_region_reference.as_mapping()
                ),
                "focus": conclusion.focus_reference.as_mapping(),
                "phase_set": conclusion.phase_set_reference.as_mapping(),
                "result": result.reference.as_mapping(),
            },
            "showcase": "monochromatic propagation phase",
        },
    )


__all__ = [
    "propagation_phase_showcase",
    "run_propagation_phase_showcase",
]
