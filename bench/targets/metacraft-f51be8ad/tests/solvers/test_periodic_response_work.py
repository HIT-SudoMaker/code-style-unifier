from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import math
from pathlib import Path

import pytest

import metacraft.solvers.lumerical_fdtd.probe as probe_module
import metacraft.solvers.lumerical_fdtd.template as template_module
from metacraft.canonical import encode_bytes
from metacraft.solvers.lumerical_fdtd.artifacts import RunDirectory, WorkRecord
from metacraft.solvers.lumerical_fdtd.lane import (
    SessionPool as NativeSessionPool,
)
from metacraft.solvers.lumerical_fdtd.qualification import (
    LumericalBinding,
    LumericalUnavailable,
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseQualification,
    PeriodicResponseProof,
    qualify,
)
from tests.lumerical_fixtures import (
    fixed_planner,
    lumerical_config as _config,
    probe_facts as _facts,
    workstation_layout as _layout,
)
from tests.solver_fakes import ActiveEngines, FakeProbe, FakeSessionFactory


def _patch_native_sessions(
    monkeypatch,
    result: dict,
    *,
    layout,
) -> FakeSessionFactory:
    active = ActiveEngines()
    configured_result = (
        result
        if callable(result) or "_responses" in result
        else {
            "_responses": {
                "linear_transmission": result,
                "propagation": result,
            }
        }
    )
    factory = FakeSessionFactory(active=active, result=configured_result)
    monkeypatch.setattr(probe_module, "plan", lambda _demand: layout)
    monkeypatch.setattr(
        probe_module,
        "SessionPool",
        lambda execution, lanes: NativeSessionPool(
            execution,
            lanes,
            _open_session=factory,
        ),
    )
    artifacts = {
        **WorkRecord.artifact_manifest(),
        "completed_project": "qualified.fsp",
        "constructed_project": "constructed.fsp",
        "execution": "qualification.json",
    }
    monkeypatch.setattr(
        WorkRecord,
        "artifact_manifest",
        classmethod(lambda _cls: dict(artifacts)),
    )
    return factory


def _now() -> datetime:
    return datetime(2026, 7, 28, tzinfo=UTC)


# ---------------------------------------------------------------------------
# One fixture proves only its own response capability
# ---------------------------------------------------------------------------


def test_transmission_only_proof_issues_only_transmission_capability(
    tmp_path: Path,
) -> None:
    """
    A probe that proves only transmission must not grant polarization.
    """

    qualification = qualify(
        _config(tmp_path),
        FakeProbe(_facts(_now()), transmission=True, polarization=False),
        planner=fixed_planner(_layout(_now())),
        now=_now(),
    )

    assert qualification.binding is not None
    assert qualification.binding.response_capabilities == (
        "periodic_transmission_response",
    )


def test_polarization_only_proof_issues_only_polarization_capability(
    tmp_path: Path,
) -> None:
    """
    A probe that proves only polarization must not grant transmission.
    """

    qualification = qualify(
        _config(tmp_path),
        FakeProbe(_facts(_now()), transmission=False, polarization=True),
        planner=fixed_planner(_layout(_now())),
        now=_now(),
    )

    assert qualification.binding is not None
    assert qualification.binding.response_capabilities == (
        "periodic_polarization_response",
    )


def test_dual_success_issues_both_capabilities(tmp_path: Path) -> None:
    """
    Both successful fixtures produce both capabilities under one binding.
    """

    qualification = qualify(
        _config(tmp_path),
        FakeProbe(_facts(_now()), transmission=True, polarization=True),
        planner=fixed_planner(_layout(_now())),
        now=_now(),
    )

    assert qualification.binding is not None
    assert qualification.binding.response_capabilities == (
        "periodic_transmission_response",
        "periodic_polarization_response",
    )


def test_dual_failure_issues_neither_capability(tmp_path: Path) -> None:
    """
    When neither fixture proves its response, qualification does not advance.
    """

    qualification = qualify(
        _config(tmp_path),
        FakeProbe(_facts(_now()), transmission=False, polarization=False),
        planner=fixed_planner(_layout(_now())),
        now=_now(),
    )

    assert qualification.binding is None
    assert qualification.findings == ("solver_execution_unverified",)
    assert qualification.reached == (
        "configured",
        "found",
        "versioned",
        "licensed",
    )


def test_one_failed_fixture_does_not_suppress_the_proven_sibling(
    tmp_path: Path,
) -> None:
    """
    Failure of one fixture does not suppress the independently proven sibling.
    """

    qualification = qualify(
        _config(tmp_path),
        FakeProbe(_facts(_now()), transmission=True, polarization=False),
        planner=fixed_planner(_layout(_now())),
        now=_now(),
    )

    assert qualification.is_available_at(_now())
    assert qualification.binding is not None
    assert qualification.binding.response_capabilities == (
        "periodic_transmission_response",
    )


# ---------------------------------------------------------------------------
# Proof facts are exact and route-neutral
# ---------------------------------------------------------------------------


def test_binding_derives_capabilities_from_complete_ordered_evidence(
    tmp_path: Path,
) -> None:
    binding = LumericalBinding(
        executable=str(tmp_path / "fdtd-solutions.exe"),
        engine=str(tmp_path / "fdtd-engine.exe"),
        python_api=str(tmp_path / "lumapi.py"),
        product_version="2026 r1",
        api_identity="fixture-api",
        license_server="fixture-license",
        resource_identity="fixture-cpu",
        response_qualifications=(
            PeriodicResponseQualification.qualified(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    assert binding.response_capabilities == (
        "periodic_transmission_response",
        "periodic_polarization_response",
    )


def test_periodic_response_proof_capabilities_route_neutral() -> None:
    """
    The proof names only physical responses, never a control strategy.
    """

    assert PeriodicResponseProof(
        response_qualifications=(
            PeriodicResponseQualification.qualified(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        )
    ).capabilities == ("periodic_transmission_response",)
    assert PeriodicResponseProof(
        response_qualifications=(
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        )
    ).capabilities == ("periodic_polarization_response",)
    assert PeriodicResponseProof(
        response_qualifications=(
            PeriodicResponseQualification.qualified(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        )
    ).capabilities == (
        "periodic_transmission_response",
        "periodic_polarization_response",
    )
    assert PeriodicResponseProof(
        response_qualifications=(
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        )
    ).capabilities == ()


@pytest.mark.parametrize(
    "response_qualifications",
    (
        (),
        (
            PeriodicResponseQualification.qualified(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
        (
            PeriodicResponseQualification.qualified(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    ),
)
def test_periodic_response_proof_requires_all_ordered_results(
    response_qualifications: tuple[PeriodicResponseQualification, ...],
) -> None:
    """
    A proof cannot omit response kinds across the qualification seam.
    """

    with pytest.raises(
        TypeError,
        match="periodic_response_qualifications_invalid",
    ):
        PeriodicResponseProof(
            response_qualifications=response_qualifications,
        )


def test_periodic_response_qualification_rejects_unknown_evidence() -> None:
    with pytest.raises(
        ValueError,
        match="periodic_response_kind_unknown",
    ):
        PeriodicResponseQualification.qualified(
            "periodic_unknown_response"
        )


def test_qualification_requires_the_exact_periodic_response_proof(
    tmp_path: Path,
) -> None:
    """
    A structurally similar probe return remains implementation drift.
    """

    class MalformedProbe:
        def observe(self, config):
            return _facts(_now())

        def verify_periodic_responses(self, config):
            return {
                "polarization": True,
                "transmission": True,
            }

    with pytest.raises(
        TypeError,
        match="periodic_response_proof_required",
    ):
        qualify(
            _config(tmp_path),
            MalformedProbe(),  # type: ignore[arg-type]
            planner=fixed_planner(_layout(_now())),
            now=_now(),
        )


# ---------------------------------------------------------------------------
# Typed Adapter outcomes carry exact reasons
# ---------------------------------------------------------------------------


def test_lumerical_unavailable_carries_one_exact_reason() -> None:
    error = LumericalUnavailable("license_unavailable")
    assert isinstance(error, RuntimeError)
    assert error.reason == "license_unavailable"
    assert "license_unavailable" in str(error)


def test_qualification_translates_observation_absence_via_typed_reason(
    tmp_path: Path,
) -> None:
    """
    A probe observation that raises the typed outcome keeps its exact reason.
    """

    class UnavailableProbe:
        def observe(self, config):
            raise LumericalUnavailable("license_unavailable")

        def verify_periodic_responses(self, config):
            raise AssertionError("qualification must not reach construction")

    qualification = qualify(
        _config(tmp_path),
        UnavailableProbe(),  # type: ignore[arg-type]
        planner=fixed_planner(_layout(_now())),
        now=_now(),
    )

    assert qualification.findings == ("license_unavailable",)
    assert qualification.binding is None


# ---------------------------------------------------------------------------
# Polarization needs both finite independent input bases
# ---------------------------------------------------------------------------


def _native_result(
    *,
    output_x: complex = 1 + 0j,
    output_y: complex = 0 + 0j,
    complex_transmission: complex = 1 + 0j,
    power_transmission: float = 0.9,
) -> dict:
    return {
        "complex_transmission": complex_transmission,
        "output_x": output_x,
        "output_y": output_y,
        "phase_planes": "metamaterial_surfaces",
        "power_transmission": power_transmission,
        "solver_status": "complete",
        "warnings": (),
    }


def test_non_finite_polarization_basis_faults_after_cleanup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A non-finite polarization basis cannot qualify the polarization response,
    but the independent transmission fixture still qualifies transmission.
    """

    layout = _layout(_now(), physical_cores=8)
    _patch_native_sessions(
        monkeypatch,
        _native_result(output_x=complex(math.nan, 0)),
        layout=layout,
    )
    config = _config(tmp_path)

    with pytest.raises(
        ValueError,
        match="periodic_polarization_response_invalid",
    ):
        probe_module.verify_periodic_responses(config)


def test_missing_polarization_basis_does_not_qualify_polarization(
    tmp_path: Path,
    monkeypatch,
) -> None:
    layout = _layout(_now(), physical_cores=8)

    active = ActiveEngines()
    result = _native_result()
    factory = FakeSessionFactory(
        active=active,
        result={
            "_responses": {
                "propagation": result,
            }
        },
    )
    monkeypatch.setattr(probe_module, "plan", lambda _demand: layout)
    monkeypatch.setattr(
        probe_module,
        "SessionPool",
        lambda execution, lanes: NativeSessionPool(
            execution,
            lanes,
            _open_session=factory,
        ),
    )
    config = _config(tmp_path)

    proof = probe_module.verify_periodic_responses(config)

    assert proof.capabilities == ("periodic_transmission_response",)


def test_non_finite_transmission_faults_after_cleanup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A non-finite transmission observation cannot qualify transmission, while
    the independent polarization fixture still qualifies polarization.
    """

    layout = _layout(_now(), physical_cores=8)
    _patch_native_sessions(
        monkeypatch,
        _native_result(complex_transmission=complex(math.inf, 0)),
        layout=layout,
    )
    config = _config(tmp_path)

    with pytest.raises(
        ValueError,
        match="periodic_transmission_response_invalid",
    ):
        probe_module.verify_periodic_responses(config)

    qualification_run = next(config.runs_directory.iterdir())
    directory = qualification_run / "transmission"
    execution = RunDirectory(directory).restore_execution(directory)
    assert (directory / "qualified.fsp").is_file()
    assert (directory / "qualification.json").read_bytes() == encode_bytes(
        execution.as_mapping()
    )


def test_dual_finite_response_qualifies_both_capabilities(
    tmp_path: Path,
    monkeypatch,
) -> None:
    layout = _layout(_now(), physical_cores=8)
    _patch_native_sessions(monkeypatch, _native_result(), layout=layout)
    config = _config(tmp_path)

    proof = probe_module.verify_periodic_responses(config)

    assert proof.capabilities == (
        "periodic_transmission_response",
        "periodic_polarization_response",
    )


@pytest.mark.parametrize("incident_axes", [("x",), ("x", "x")])
def test_polarization_requires_exactly_two_distinct_input_bases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    incident_axes: tuple[str, ...],
) -> None:
    layout = _layout(_now(), physical_cores=8)
    factory = _patch_native_sessions(
        monkeypatch,
        _native_result(),
        layout=layout,
    )
    canonical = template_module.prepare_qualification_constructions(
        atom_material="<Object defined dielectric>",
        substrate_material="<Object defined dielectric>",
    )
    geometric = tuple(
        replace(canonical.polarization[0], incident_axis=axis)
        for axis in incident_axes
    )
    monkeypatch.setattr(
        template_module,
        "prepare_qualification_constructions",
        lambda **_kwargs: replace(canonical, polarization=geometric),
    )

    with pytest.raises(
        RuntimeError,
        match="polarization_qualification_constructions_invalid",
    ):
        probe_module.verify_periodic_responses(_config(tmp_path))

    assert all(session.closed for session in factory.sessions)


def test_malformed_polarization_output_raises_after_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _layout(_now(), physical_cores=8)
    response = _native_result()
    del response["output_y"]
    factory = _patch_native_sessions(
        monkeypatch,
        response,
        layout=layout,
    )

    with pytest.raises(KeyError, match="output_y"):
        probe_module.verify_periodic_responses(_config(tmp_path))

    assert all(session.closed for session in factory.sessions)


def test_programming_failure_does_not_suppress_sibling_attempt_or_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _layout(_now(), physical_cores=8)
    observed: list[str] = []

    def result(objects):
        kind = str(objects["meta_atom"]["kind"])
        observed.append(kind)
        if kind == "circle":
            raise RuntimeError("fixture_invariant_broken")
        return _native_result()

    factory = _patch_native_sessions(
        monkeypatch,
        result,
        layout=layout,
    )

    with pytest.raises(RuntimeError, match="fixture_invariant_broken"):
        probe_module.verify_periodic_responses(_config(tmp_path))

    assert observed == ["circle", "rectangle", "rectangle"]
    assert all(session.closed for session in factory.sessions)


def test_typed_product_absence_keeps_reason_after_sibling_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _layout(_now(), physical_cores=8)
    observed: list[str] = []

    def result(objects):
        kind = str(objects["meta_atom"]["kind"])
        observed.append(kind)
        if kind == "circle":
            raise LumericalUnavailable("license_lost")
        return _native_result()

    factory = _patch_native_sessions(
        monkeypatch,
        result,
        layout=layout,
    )

    with pytest.raises(LumericalUnavailable) as raised:
        probe_module.verify_periodic_responses(_config(tmp_path))

    assert raised.value.reason == "license_lost"
    assert observed == ["circle", "rectangle", "rectangle"]
    assert all(session.closed for session in factory.sessions)


@pytest.mark.parametrize(
    ("stage", "error"),
    [
        ("observe", KeyError("observation_shape")),
        ("verify", RuntimeError("fixture_protocol_drift")),
    ],
)
def test_qualification_does_not_translate_implementation_failure(
    tmp_path: Path,
    stage: str,
    error: Exception,
) -> None:
    class BrokenProbe:
        def observe(self, config):
            if stage == "observe":
                raise error
            return _facts(_now())

        def verify_periodic_responses(self, config):
            if stage == "verify":
                raise error
            return PeriodicResponseProof(
                response_qualifications=(
                    PeriodicResponseQualification.qualified(
                        PERIODIC_TRANSMISSION_RESPONSE
                    ),
                    PeriodicResponseQualification.qualified(
                        PERIODIC_POLARIZATION_RESPONSE
                    ),
                    PeriodicResponseQualification.response_not_returned(
                        PERIODIC_REFERENCE_SURFACE_RESPONSE
                    ),
                )
            )

    with pytest.raises(type(error), match=str(error)):
        qualify(
            _config(tmp_path),
            BrokenProbe(),  # type: ignore[arg-type]
            planner=fixed_planner(_layout(_now())),
            now=_now(),
        )
