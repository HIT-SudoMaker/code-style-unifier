from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path

import pytest

from examples.pb_phase_showcase import run_pb_phase_showcase
from metacraft import conduct
from metacraft.authority import Authority, Document
from metacraft.science import CompletedResults
from metacraft.science.metalens import GeometricResult, MonochromaticSpectrum
from metacraft.science.metalens.result import restore_conclusion
from metacraft.solvers.lumerical_fdtd.qualification import (
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseProof,
    PeriodicResponseQualification,
)
from tests.brief_fixtures import geometric_brief
from tests.lumerical_fixtures import jones_response
from tests.propagation_fixtures import fake_metalens_ports
from tests.reference_surface_fakes import bounded_reference_surface
from tests.solver_fakes import FakeSession


def test_public_conduct_exposes_one_traceable_pb_showcase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application_root = tmp_path / "pb-showcase"
    brief = replace(
        geometric_brief(),
        operating_spectrum=MonochromaticSpectrum(wavelength_nm=940),
        cell_period_nm=290,
        atom_height_nm=550,
        focal_length_um=Decimal("20"),
        numerical_aperture=Decimal("0.48"),
        dimension_step_nm=29,
    )
    native_result = FakeSession.result

    def routed_result(
        session: FakeSession,
        name: str,
        result_name: str,
    ) -> dict[str, object]:
        if result_name == "linear_transmission":
            return dict(jones_response(session._objects))
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

    showcase = run_pb_phase_showcase(
        brief,
        application_root=application_root,
        evidence_adapter=ports["evidence_adapter"],
        orientation_count=16,
    )

    assert isinstance(showcase, Document)
    assert showcase.schema_identifier == "metacraft.examples.pb_phase_showcase"
    values = showcase.values
    assert values["showcase"] == "monochromatic PB phase"
    assert values["execution_origin"] == "synthetic"
    assert values["orientation_count"] == 16
    assert set(values["orientation_relation"]) == {
        "converted_phase_rad",
        "phase_sign",
    }
    states = values["orientation_states"]
    assert isinstance(states, list)
    assert len(states) == 16
    assert states[0]["target_phase_rad"] == "0"
    assert all(
        state["geometry"]["shape"] == "rectangular fin"
        and set(state["geometry"]["dimensions_nm"])
        == {"length_nm", "width_nm"}
        and state["orientation_rad"] is not None
        and state["target_phase_rad"] is not None
        and state["realized_phase_rad"] is not None
        for state in states
    )

    replayed = conduct(brief, application_root=application_root)
    assert isinstance(replayed, CompletedResults)
    authority = Authority(application_root / "authority")
    selected_result, conclusion = next(
        (result, restored)
        for result in replayed.results
        if isinstance(
            (restored := restore_conclusion(result.document, fetch=authority.fetch)),
            GeometricResult,
        )
        and len(restored.aperture.states) == 16
    )
    assert values["references"] == {
        "aperture": conclusion.aperture_reference.as_mapping(),
        "cell_choice": conclusion.choice_reference.as_mapping(),
        "converted_field": conclusion.field_reference.as_mapping(),
        "focal_region": conclusion.focal_region_reference.as_mapping(),
        "focus": conclusion.focus_reference.as_mapping(),
        "orientation_relation": (
            conclusion.orientation_relation_reference.as_mapping()
        ),
        "orientation_set": conclusion.aperture.states[0].source.as_mapping(),
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
