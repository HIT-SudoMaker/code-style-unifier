from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

import metacraft.solvers.lumerical_fdtd.probe as probe_module
import metacraft.solvers.lumerical_fdtd.periodic_response as response_module
from metacraft.authority import Authority, Document
from metacraft.authority.session import AuthoritySession
from metacraft.external_activity import (
    ExternalActivityClosure,
    ExternalActivityOrigin,
)
from metacraft.science.periodic_response import (
    CircularCrossSection,
    PeriodicMaterials,
    PeriodicResponseContext,
    PeriodicResponseKind,
    PeriodicResponseUnavailable,
    PeriodicTransmissionRequest,
    PeriodicWork,
    periodic_request_identity,
)
from metacraft.solvers.recorded_periodic_response import RecordedPeriodicResponse
from metacraft.solvers.lumerical_fdtd.artifacts import RunDirectory
from metacraft.solvers.lumerical_fdtd.periodic_response import (
    LumericalPeriodicResponse,
)
from metacraft.solvers.lumerical_fdtd.qualification import (
    InstallationObservation,
    LumericalConfig,
    LumericalUnavailable,
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseQualification,
    PeriodicResponseProof,
)
from tests.lumerical_fixtures import (
    fixed_planner,
    lumerical_config,
    workstation_layout,
)
from tests.solver_fakes import FakeProbe


def test_recorded_absence_reports_zero_current_call_activity(tmp_path: Path) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    binding = session.admit_document(Document("fixture.binding", {"name": "fixture"}))
    material = session.admit_document(Document("fixture.material", {"name": "silica"}))
    capacity_scope = "fixture:periodic"
    work = PeriodicWork(
        cell_identity="circular-pillar-height-0600nm-diameter-0180nm",
        work_identity="sha256:recorded-missing",
        observation_schema="fixture.periodic.transmission",
        wavelength_nm=400,
        period_nm=400,
        height_nm=600,
        geometry=CircularCrossSection(180),
        materials=PeriodicMaterials(
            "Si3N4",
            Decimal("2.0"),
            material,
            "SiO2",
            Decimal("1.45"),
            material,
        ),
        source_references=(material,),
        binding_reference=binding,
        capacity_scope=capacity_scope,
        input_basis="x linear",
        output_basis="transverse linear",
        order_regime="zeroth order",
    )
    request = PeriodicTransmissionRequest(
        periodic_request_identity("transmission", (work.work_identity,)),
        (work,),
    )
    qualification = ExternalActivityClosure(
        ExternalActivityOrigin.NATIVE,
        0,
        0,
        0,
        0,
        1,
        1,
        0,
        0,
    )
    response = RecordedPeriodicResponse(
        session,
        context=PeriodicResponseContext(
            binding,
            capacity_scope,
            (PeriodicResponseKind.TRANSMISSION,),
            qualification,
        ),
    )

    outcome = response.observe(request)

    assert isinstance(outcome, PeriodicResponseUnavailable)
    assert response.context.qualification_closure == (
        ExternalActivityClosure.recorded()
    )
    assert outcome.closure.request_identity == request.request_identity
    assert outcome.closure.qualification == (
        response.context.qualification_closure
    )
    assert outcome.closure.observation == ExternalActivityClosure.recorded()


def test_qualification_counts_discovery_and_three_fixture_solves(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    discovery = ExternalActivityClosure(
        ExternalActivityOrigin.NATIVE,
        0,
        0,
        0,
        0,
        1,
        1,
        0,
        0,
    )
    fixtures = ExternalActivityClosure(
        ExternalActivityOrigin.NATIVE,
        0,
        0,
        3,
        3,
        1,
        1,
        1,
        1,
    )
    probe = FakeProbe(
        InstallationObservation(
            product_version="fixture",
            api_identity="fixture-api",
            lumerical_gui_limit=1,
            lumerical_solve_limit=1,
            resource_identity="fixture-cpu",
            observed_at=now,
            activity_closure=discovery,
        ),
        proof=PeriodicResponseProof(
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
            ),
            activity_closure=fixtures,
        ),
    )

    monkeypatch.setattr(response_module, "ProductProbe", lambda: probe)
    monkeypatch.setattr(
        response_module,
        "plan",
        fixed_planner(workstation_layout(now)),
    )
    response = LumericalPeriodicResponse.open(
        authority=Authority(tmp_path / "native-authority"),
        config=lumerical_config(tmp_path),
        run=RunDirectory(tmp_path / "native-run"),
    )

    assert response.context.qualification_closure == ExternalActivityClosure(
        ExternalActivityOrigin.NATIVE,
        0,
        0,
        3,
        3,
        2,
        2,
        1,
        1,
    )


def test_qualification_cleanup_absence_preserves_primary_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    primary = LumericalUnavailable("fixture_primary_unavailable")
    cleanup = LumericalUnavailable("fixture_cleanup_unavailable")

    class CleanupFaultProbe:
        def observe(
            self,
            _config: LumericalConfig,
        ) -> InstallationObservation:
            return InstallationObservation(
                product_version="fixture",
                api_identity="fixture-api",
                lumerical_gui_limit=1,
                lumerical_solve_limit=1,
                resource_identity="fixture-cpu",
                observed_at=now,
            )

        def verify_periodic_responses(
            self,
            config: LumericalConfig,
        ) -> PeriodicResponseProof:
            return probe_module.verify_periodic_responses(config)

    class CleanupFaultSessions:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def close(self) -> None:
            raise cleanup

    def unavailable_output(*_args: object) -> object:
        raise primary

    monkeypatch.setattr(
        response_module,
        "ProductProbe",
        CleanupFaultProbe,
    )
    monkeypatch.setattr(
        probe_module,
        "plan",
        fixed_planner(workstation_layout(now)),
    )
    monkeypatch.setattr(
        probe_module,
        "WorkstationExecution",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        probe_module,
        "SessionPool",
        CleanupFaultSessions,
    )
    monkeypatch.setattr(
        probe_module,
        "_periodic_outputs",
        unavailable_output,
    )
    monkeypatch.setattr(
        probe_module,
        "_qualify_polarization_response",
        lambda *_args: PeriodicResponseQualification.response_not_returned(
            PERIODIC_POLARIZATION_RESPONSE
        ),
    )

    with pytest.raises(ExceptionGroup) as raised:
        LumericalPeriodicResponse.open(
            authority=Authority(tmp_path / "cleanup-authority"),
            config=lumerical_config(tmp_path),
            run=RunDirectory(tmp_path / "cleanup-run"),
        )

    assert raised.value.exceptions == (primary, cleanup)
