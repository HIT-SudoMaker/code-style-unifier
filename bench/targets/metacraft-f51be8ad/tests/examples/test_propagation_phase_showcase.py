from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path

import pytest

from examples.propagation_phase_showcase import (
    run_propagation_phase_showcase,
)
from metacraft import conduct
from metacraft.authority import Authority, Document
from metacraft.science import CompletedResults
from metacraft.science.metalens import (
    MonochromaticSpectrum,
    PropagationResult,
)
from metacraft.science.metalens.result import restore_conclusion
from metacraft.solvers.lumerical_fdtd.qualification import (
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseProof,
    PeriodicResponseQualification,
)
from tests.brief_fixtures import propagation_brief
from tests.propagation_fixtures import fake_metalens_ports
from tests.reference_surface_fakes import bounded_reference_surface
from tests.solver_fakes import FakeSession


def test_public_conduct_exposes_one_traceable_propagation_showcase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application_root = tmp_path / "propagation-showcase"
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(wavelength_nm=940),
        cell_period_nm=290,
        atom_height_nm=550,
        focal_length_um=Decimal("20"),
        numerical_aperture=Decimal("0.48"),
    )
    native_result = FakeSession.result

    def routed_result(
        session: FakeSession,
        name: str,
        result_name: str,
    ) -> dict[str, object]:
        if result_name == "reference_surface":
            return bounded_reference_surface(session)
        return dict(native_result(session, name, result_name))

    monkeypatch.setattr(FakeSession, "result", routed_result)
    ports = fake_metalens_ports(
        brief,
        application_root,
        monkeypatch,
        response_proof=_complete_response_proof(),
    )

    showcase = run_propagation_phase_showcase(
        brief,
        application_root=application_root,
        evidence_adapter=ports["evidence_adapter"],
        phase_levels=16,
    )

    assert isinstance(showcase, Document)
    assert showcase.schema_identifier == (
        "metacraft.examples.propagation_phase_showcase"
    )
    values = showcase.values
    assert values["showcase"] == "monochromatic propagation phase"
    assert values["execution_origin"] == "synthetic"
    assert values["phase_levels"] == 16
    phase_states = values["phase_states"]
    assert isinstance(phase_states, list)
    assert tuple(state["phase_level"] for state in phase_states) == tuple(
        range(16)
    )
    assert phase_states[0]["target_phase_rad"] == "0"
    assert all(
        state["geometry"]["shape"] == "circular pillar"
        and set(state["geometry"]["dimensions_nm"]) == {"diameter_nm"}
        and state["target_phase_rad"] is not None
        and state["realized_phase_rad"] is not None
        for state in phase_states
    )

    replayed = conduct(brief, application_root=application_root)
    assert isinstance(replayed, CompletedResults)
    authority = Authority(application_root / "authority")
    selected_result, conclusion = next(
        (result, restored)
        for result in replayed.results
        if isinstance(
            (restored := restore_conclusion(result.document, fetch=authority.fetch)),
            PropagationResult,
        )
        and restored.phase_level_count == 16
    )
    assert values["references"] == {
        "aperture": conclusion.aperture_reference.as_mapping(),
        "field": conclusion.field_reference.as_mapping(),
        "focal_region": conclusion.focal_region_reference.as_mapping(),
        "focus": conclusion.focus_reference.as_mapping(),
        "phase_set": conclusion.phase_set_reference.as_mapping(),
        "result": selected_result.reference.as_mapping(),
    }
    assert values["focus"] == conclusion.focus.as_mapping()

    encoded = json.dumps(values, sort_keys=True)
    assert str(application_root) not in encoded
    assert application_root.as_posix() not in encoded
    assert "application_root" not in encoded


def _complete_response_proof() -> PeriodicResponseProof:
    return PeriodicResponseProof(
        response_qualifications=(
            PeriodicResponseQualification.qualified(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        )
    )
