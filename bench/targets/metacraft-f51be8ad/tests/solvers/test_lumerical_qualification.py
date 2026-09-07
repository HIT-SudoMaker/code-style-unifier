from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
from typing import Any

import pytest

import metacraft.solvers.lumerical_fdtd.probe as probe_module
from metacraft.authority import Authority, Document, Proposal, Revision
from metacraft.canonical import encode_bytes
from metacraft.solvers.lumerical_fdtd import (
    LumericalConfig,
    read_lumerical_environment,
)
from metacraft.solvers.lumerical_fdtd.artifacts import RunDirectory, WorkRecord
from metacraft.solvers.lumerical_fdtd.probe import ProductProbe
from metacraft.solvers.lumerical_fdtd.lane import (
    SessionPool as NativeSessionPool,
)
from metacraft.solvers.lumerical_fdtd.qualification import (
    InstallationObservation,
    LumericalUnavailable,
    qualify,
)
from metacraft.solvers.lumerical_fdtd.session import open_engine
from tests.lumerical_fixtures import (
    fixed_planner,
    lumerical_config as _config,
    probe_facts as _facts,
    workstation_layout as _layout,
)
from tests.solver_fakes import ActiveEngines, FakeProbe, FakeSessionFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _CountingProbe:
    """
    Wrap a fake probe to record observation and construction call counts.
    """

    def __init__(self, probe: FakeProbe) -> None:
        self._inner = probe
        self.observe_calls = 0
        self.construction_calls = 0

    def observe(self, config: LumericalConfig) -> InstallationObservation:
        self.observe_calls += 1
        return self._inner.observe(config)

    def verify_periodic_responses(
        self,
        config: LumericalConfig,
    ):
        self.construction_calls += 1
        return self._inner.verify_periodic_responses(config)


def _observation(
    now: datetime,
    *,
    product_version: str = "2026 r1",
    api_identity: str = "fixture-api",
    lumerical_gui_limit: int = 2,
    lumerical_solve_limit: int = 2,
) -> InstallationObservation:
    return InstallationObservation(
        product_version=product_version,
        api_identity=api_identity,
        lumerical_gui_limit=lumerical_gui_limit,
        lumerical_solve_limit=lumerical_solve_limit,
        resource_identity="local-cpu",
        observed_at=now,
    )


# ---------------------------------------------------------------------------
# One case at every stage
# ---------------------------------------------------------------------------


def test_configuration_incomplete_reports_the_last_reached_stage(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    config = LumericalConfig(
        executable=None,
        python_api=None,
        license_utility=None,
        license_server=None,
    )

    qualification = qualify(
        config,
        FakeProbe(_observation(now)),
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.reached == ()
    assert qualification.findings == ("configuration_incomplete",)
    assert qualification.binding is None
    assert qualification.capacity is None


def test_executable_missing_reports_found_stage(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    config = _config(tmp_path)
    config = LumericalConfig(
        executable=tmp_path / "missing" / "fdtd-solutions.exe",
        python_api=config.python_api,
        license_utility=config.license_utility,
        license_server=config.license_server,
    )

    qualification = qualify(
        config,
        FakeProbe(_observation(now)),
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.reached == ("configured",)
    assert qualification.findings == ("executable_not_found",)


def test_engine_missing_reports_found_stage(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    config = _config(tmp_path)
    config = LumericalConfig(
        executable=config.executable,
        python_api=config.python_api,
        license_utility=config.license_utility,
        license_server=config.license_server,
    )
    engine = config.executable.with_name("fdtd-engine.exe")
    assert engine.is_file()
    engine.unlink()

    qualification = qualify(
        config,
        FakeProbe(_observation(now)),
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.reached == ("configured",)
    assert qualification.findings == ("engine_not_found",)


def test_python_api_missing_reports_found_stage(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    config = _config(tmp_path)
    config = LumericalConfig(
        executable=config.executable,
        python_api=tmp_path / "missing" / "lumapi.py",
        license_utility=config.license_utility,
        license_server=config.license_server,
    )

    qualification = qualify(
        config,
        FakeProbe(_observation(now)),
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.reached == ("configured",)
    assert qualification.findings == ("python_api_not_found",)


def test_product_identity_missing_reports_versioned_stage(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    qualification = qualify(
        _config(tmp_path),
        FakeProbe(_observation(now, product_version="  ", api_identity="")),
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.reached == ("configured", "found")
    assert qualification.findings == ("product_identity_missing",)


def test_license_unavailable_reports_licensed_stage(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    qualification = qualify(
        _config(tmp_path),
        FakeProbe(
            _observation(now, lumerical_gui_limit=0, lumerical_solve_limit=2),
        ),
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.reached == ("configured", "found", "versioned")
    assert qualification.findings == ("license_unavailable",)


def test_solver_execution_unverified_reports_qualified_stage(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    qualification = qualify(
        _config(tmp_path),
        FakeProbe(
            _observation(now), transmission=False, polarization=False
        ),
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.reached == (
        "configured",
        "found",
        "versioned",
        "licensed",
    )
    assert qualification.findings == ("solver_execution_unverified",)


# ---------------------------------------------------------------------------
# License-only observation performs no construction
# ---------------------------------------------------------------------------


def test_license_observation_performs_no_construction(
    tmp_path: Path,
) -> None:
    """
    A periodic-template property defect surfaces at ``qualified`` (the first
    native construction), never at install or license observation.
    """

    now = datetime.now(UTC)
    counting = _CountingProbe(
        FakeProbe(_observation(now), transmission=False, polarization=False)
    )

    qualification = qualify(
        _config(tmp_path),
        counting,
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.findings == ("solver_execution_unverified",)
    assert qualification.reached == (
        "configured",
        "found",
        "versioned",
        "licensed",
    )
    assert counting.observe_calls == 1
    assert counting.construction_calls == 1


# ---------------------------------------------------------------------------
# Qualified performs one minimal construction
# ---------------------------------------------------------------------------


def test_qualified_performs_one_minimal_construction(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    counting = _CountingProbe(FakeProbe(_observation(now)))

    qualification = qualify(
        _config(tmp_path),
        counting,
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.binding is not None
    assert qualification.reached == (
        "configured",
        "found",
        "versioned",
        "licensed",
        "qualified",
    )
    assert counting.construction_calls == 1


# ---------------------------------------------------------------------------
# Production and fake outcomes are structurally identical
# ---------------------------------------------------------------------------


def test_production_and_fake_outcomes_cross_the_same_probe_seam() -> None:
    """
    ``ProductProbe`` and ``FakeProbe`` satisfy the one ``Probe`` seam, so
    production, fake, and live callers walk the same qualification stages.
    """

    shared = {"observe", "verify_periodic_responses"}
    for implementation in (ProductProbe, FakeProbe):
        methods = {
            name
            for name in shared
            if callable(getattr(implementation, name, None))
        }
        assert methods == shared, implementation.__name__


# ---------------------------------------------------------------------------
# Capacity refresh uses only fresh license and workstation facts
# ---------------------------------------------------------------------------


def test_capacity_refresh_does_not_repeat_discovery_or_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    refreshed = probe_module._license_capacity.__name__

    def assert_no_engine_open(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "capacity refresh must not open the engine or construct geometry"
        )

    monkeypatch.setattr(probe_module, "open_engine", assert_no_engine_open)
    monkeypatch.setattr(
        probe_module,
        "verify_periodic_responses",
        assert_no_engine_open,
    )
    monkeypatch.setattr(
        probe_module,
        "_license_capacity",
        lambda _config, _feature: 4,
    )

    probe = ProductProbe()
    capacity = probe.refresh_capacity(config)

    assert capacity.lumerical_gui_limit == 4
    assert capacity.lumerical_solve_limit == 4
    assert refreshed == "_license_capacity"


def test_missing_license_utility_remains_typed_at_each_probe_seam(
    tmp_path: Path,
) -> None:
    """
    A utility that disappears after configuration keeps one exact reason.
    """

    config = _config(tmp_path)
    assert config.license_utility is not None
    config.license_utility.unlink()
    probe = ProductProbe()

    for operation in (probe.observe, probe.refresh_capacity):
        with pytest.raises(LumericalUnavailable) as raised:
            operation(config)
        assert raised.value.reason == "license_utility_not_found"


def test_exhausted_capacity_refresh_remains_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A present utility with no usable seats is expected product absence.
    """

    monkeypatch.setattr(
        probe_module,
        "_license_capacity",
        lambda _config, _feature: 0,
    )

    with pytest.raises(LumericalUnavailable) as raised:
        ProductProbe().refresh_capacity(_config(tmp_path))

    assert raised.value.reason == "license_unavailable"


# ---------------------------------------------------------------------------
# Explicitly enabled live tests remain disabled by default
# ---------------------------------------------------------------------------


def test_live_qualification_markers_stay_opt_in() -> None:
    """
    Live solver markers remain excluded from the default non-live suite.
    """

    markers = pytest.mark.lumerical_live
    assert markers.name == "lumerical_live"


# ---------------------------------------------------------------------------
# Existing behavior under the consolidated path
# ---------------------------------------------------------------------------


def test_qualification_keeps_both_native_license_limits(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    observation = _observation(
        now,
        lumerical_gui_limit=3,
        lumerical_solve_limit=1,
    )

    qualification = qualify(
        _config(tmp_path),
        FakeProbe(observation),
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.capacity is not None
    assert qualification.capacity.limit == 1
    assert qualification.capacity.as_mapping() == {
        "fresh_until": qualification.capacity.as_mapping()["fresh_until"],
        "limit": 1,
        "lumerical_gui_limit": 3,
        "lumerical_solve_limit": 1,
        "observed_at": qualification.capacity.as_mapping()["observed_at"],
        "scope": qualification.capacity.scope,
        "workstation_limit": 2,
    }


def test_lumerical_environment_is_separate_from_prohibited_secrets(
    tmp_path: Path,
) -> None:
    environment_file = tmp_path / ".env.lumerical"
    environment_file.write_text(
        "\n".join(
            (
                r"LUMERICAL_FDTD_PATH=C:\Program Files\ANSYS Inc\v252"
                r"\Lumerical\bin\fdtd-solutions.exe",
                r"LUMERICAL_PYTHON_API_PATH=C:\Program Files\ANSYS Inc\v252"
                r"\Lumerical\api\python\lumapi.py",
                "METACRAFT_CAPACITY_FRESHNESS_SECONDS=300",
            )
        ),
        encoding="utf-8",
    )

    environment = read_lumerical_environment(
        environment_file,
        inherited={
            "ANSYSLMD_LICENSE_FILE": "system-license",
            "METACRAFT_PROHIBITED_SECRET": "must-not-cross",
        },
    )
    config = LumericalConfig.from_environ(environment)

    assert config.license_server == "system-license"
    assert "METACRAFT_PROHIBITED_SECRET" not in environment


def test_lumerical_environment_rejects_retired_material_catalogue_keys(
    tmp_path: Path,
) -> None:
    """
    Keep reusable scientific selection outside product configuration.
    """

    environment_file = tmp_path / ".env.lumerical"
    environment_file.write_text(
        "LUMERICAL_MATERIAL_SILICA=SiO2 (Glass) - Palik",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="lumerical_environment_key_invalid:"
        "LUMERICAL_MATERIAL_SILICA",
    ):
        read_lumerical_environment(environment_file, inherited={})


def test_engine_launch_receives_the_configured_license_server(
    tmp_path: Path,
    monkeypatch,
) -> None:
    api = tmp_path / "lumapi.py"
    api.write_text(
        "\n".join(
            (
                "import os",
                "class FDTD:",
                "    def __init__(self, *, hide):",
                "        self.hide = hide",
                "        self.license_server = os.environ.get(",
                "            'ANSYSLMD_LICENSE_FILE'",
                "        )",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ANSYSLMD_LICENSE_FILE", "machine-license")

    engine = open_engine(
        api,
        should_hide=True,
        license_server="configured-license",
    )

    assert engine.hide
    assert engine.license_server == "configured-license"
    assert os.environ["ANSYSLMD_LICENSE_FILE"] == "machine-license"


def test_native_product_launch_failure_becomes_typed_absence(
    tmp_path: Path,
) -> None:
    api = tmp_path / "lumapi.py"
    api.write_text(
        "\n".join(
            (
                "class LumApiError(Exception):",
                "    pass",
                "class FDTD:",
                "    def __init__(self, *, hide):",
                "        raise LumApiError('license checkout failed')",
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(LumericalUnavailable) as raised:
        open_engine(api)

    assert raised.value.reason == "native_product_unavailable"
    assert raised.value.__cause__ is not None
    assert type(raised.value.__cause__).__name__ == "LumApiError"
    assert str(raised.value.__cause__) == "license checkout failed"


def test_installed_probe_follows_the_same_qualification_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)

    class Engine:
        checked_out = None
        closed = False

        def version(self):
            return "8.34.4175"

        def getresource(self, solver, *args):
            assert solver == "FDTD"
            if not args:
                return 1
            _, property_name = args
            return {
                "active": "1",
                "capacity": "2",
                "device type": "CPU",
                "name": "Local Host",
                "processes": "1",
                "threads": "4",
                "total cores": "8",
            }[property_name]

        def getlicenseestimate(self, solver, resource):
            assert (solver, resource) == ("FDTD", "1")
            return {
                "feature": "1 lumerical_solve",
                "single": "0 anshpc OR 0 anshpc_pack",
                "sweep": "0 anshpc OR 0 anshpc_pack",
            }

        def checkout(self, feature):
            self.checked_out = feature

        def close(self):
            self.closed = True

    engine = Engine()
    launch = {}

    def open_engine(*_args, **kwargs):
        launch.update(kwargs)
        return engine

    observed_features: list[str] = []

    def native_capacity(_config, feature: str) -> int:
        observed_features.append(feature)
        return {
            "lumerical_gui": 3,
            "lumerical_solve": 5,
        }[feature]

    monkeypatch.setattr(probe_module, "open_engine", open_engine)
    monkeypatch.setattr(
        probe_module,
        "_license_capacity",
        native_capacity,
    )
    monkeypatch.setattr(
        probe_module,
        "verify_periodic_responses",
        lambda _config: probe_module.PeriodicResponseProof(
            response_qualifications=(
                probe_module.PeriodicResponseQualification
                .response_not_returned(
                    probe_module.PERIODIC_TRANSMISSION_RESPONSE
                ),
                probe_module.PeriodicResponseQualification
                .response_not_returned(
                    probe_module.PERIODIC_POLARIZATION_RESPONSE
                ),
                probe_module.PeriodicResponseQualification
                .response_not_returned(
                    probe_module.PERIODIC_REFERENCE_SURFACE_RESPONSE
                ),
            )
        ),
    )
    probe = ProductProbe()

    observation = probe.observe(config)
    qualification = qualify(
        config,
        FakeProbe(observation, transmission=False, polarization=False),
        planner=fixed_planner(_layout(observation.observed_at)),
        now=observation.observed_at,
    )

    assert not qualification.is_available_at(observation.observed_at)
    assert qualification.binding is None
    assert qualification.capacity is None
    assert qualification.findings == ("solver_execution_unverified",)
    assert qualification.reached == (
        "configured",
        "found",
        "versioned",
        "licensed",
    )
    assert observation.product_version == "8.34.4175"
    assert observation.lumerical_gui_limit == 3
    assert observation.lumerical_solve_limit == 5
    assert observed_features == ["lumerical_gui", "lumerical_solve"]
    assert engine.checked_out == "lumerical_solve"
    assert engine.closed
    assert launch["license_server"] == "fixture-license"

    verified_engine = Engine()
    construction_started = None

    def verify_periodic_responses(*_args):
        nonlocal construction_started
        assert verified_engine.closed
        construction_started = datetime.now(UTC)
        return probe_module.PeriodicResponseProof(
            response_qualifications=(
                probe_module.PeriodicResponseQualification.qualified(
                    probe_module.PERIODIC_TRANSMISSION_RESPONSE
                ),
                probe_module.PeriodicResponseQualification
                .response_not_returned(
                    probe_module.PERIODIC_POLARIZATION_RESPONSE
                ),
                probe_module.PeriodicResponseQualification
                .response_not_returned(
                    probe_module.PERIODIC_REFERENCE_SURFACE_RESPONSE
                ),
            )
        )

    monkeypatch.setattr(
        probe_module,
        "open_engine",
        lambda *_args, **_kwargs: verified_engine,
    )
    monkeypatch.setattr(
        probe_module,
        "verify_periodic_responses",
        verify_periodic_responses,
    )
    verified_probe = ProductProbe()
    verified = qualify(
        config,
        verified_probe,
        planner=fixed_planner(_layout(datetime.now(UTC))),
    )

    assert verified.capacity is not None
    assert verified.is_available_at(verified.capacity.observed_at)
    assert verified.capacity.limit == 2
    assert construction_started is not None
    assert verified.capacity.observed_at <= construction_started


def test_periodic_qualification_borrows_one_native_work_vocabulary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _config(tmp_path)
    now = datetime.now(UTC)
    layout = _layout(now, physical_cores=8)
    active = ActiveEngines()
    native_result = {
        "complex_transmission": 1 + 0j,
        "output_x": 1 + 0j,
        "output_y": 0 + 0j,
        "phase_planes": "metamaterial_surfaces",
        "power_transmission": 0.9,
        "solver_status": "complete",
        "warnings": (),
    }
    factory = FakeSessionFactory(
        active=active,
        result={
            "_responses": {
                "linear_transmission": native_result,
                "propagation": native_result,
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

    proof = probe_module.verify_periodic_responses(config)

    assert proof.capabilities == (
        "periodic_transmission_response",
        "periodic_polarization_response",
    )
    assert len(factory.sessions) == 1
    assert factory.sessions[0].closed
    qualification_runs = tuple(config.runs_directory.iterdir())
    assert len(qualification_runs) == 1
    fixture_names = {"transmission", "polarization"}
    assert {path.name for path in qualification_runs[0].iterdir()} == (
        fixture_names
    )
    assert (
        qualification_runs[0]
        / "transmission"
        / artifacts["constructed_project"]
    ).is_file()
    assert (
        qualification_runs[0]
        / "polarization"
        / "x-input"
        / artifacts["constructed_project"]
    ).is_file()
    assert (
        qualification_runs[0]
        / "polarization"
        / "y-input"
        / artifacts["constructed_project"]
    ).is_file()
    fixture_directories = (
        qualification_runs[0] / "transmission",
        qualification_runs[0] / "polarization" / "x-input",
        qualification_runs[0] / "polarization" / "y-input",
    )
    for directory in fixture_directories:
        execution = RunDirectory(directory).restore_execution(directory)
        assert (directory / artifacts["execution"]).read_bytes() == (
            encode_bytes(execution.as_mapping())
        )


def test_installed_probe_rejects_an_executable_from_another_installation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    unrelated = tmp_path / "other" / "fdtd-solutions.exe"
    unrelated.parent.mkdir()
    unrelated.write_bytes(b"other")
    engine = tmp_path / "other" / "fdtd-engine.exe"
    engine.write_bytes(b"other")
    config = LumericalConfig(
        executable=unrelated,
        python_api=config.python_api,
        license_utility=config.license_utility,
        license_server=config.license_server,
    )
    opened = False

    def open_engine(*_args, **_kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("mismatched installation must not open")

    monkeypatch.setattr(probe_module, "open_engine", open_engine)
    qualification = qualify(
        config,
        ProductProbe(),
        planner=fixed_planner(_layout(datetime.now(UTC))),
    )

    assert not qualification.is_available_at(datetime.now(UTC))
    assert qualification.findings == (
        "lumerical_installation_mismatch",
    )
    assert qualification.reached == ("configured", "found")
    assert not opened


def test_exact_binding_and_tightest_capacity_are_available(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 23, tzinfo=UTC)

    qualification = qualify(
        _config(tmp_path),
        FakeProbe(_facts(now)),
        planner=fixed_planner(_layout(now, physical_cores=8)),
        now=now,
    )

    assert qualification.is_available_at(now)
    assert qualification.binding is not None
    assert qualification.capacity is not None
    assert qualification.capacity.limit == 1
    assert qualification.capacity.workstation_limit == 1
    binding = qualification.binding
    assert "materials" not in binding.as_mapping()
    assert qualification.reached == (
        "configured",
        "found",
        "versioned",
        "licensed",
        "qualified",
    )


def test_product_qualification_does_not_require_scientific_materials(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 23, tzinfo=UTC)
    config = _config(tmp_path)
    config = LumericalConfig(
        executable=config.executable,
        python_api=config.python_api,
        license_utility=config.license_utility,
        license_server=config.license_server,
        freshness_seconds=config.freshness_seconds,
        runs_directory=config.runs_directory,
    )

    qualification = qualify(
        config,
        FakeProbe(_facts(now)),
        planner=fixed_planner(_layout(now)),
        now=now,
    )

    assert qualification.is_available_at(now)
    assert qualification.findings == ()


def test_stale_capacity_is_not_available(tmp_path: Path) -> None:
    observed = datetime(2026, 7, 23, tzinfo=UTC)
    qualification = qualify(
        _config(tmp_path),
        FakeProbe(_facts(observed)),
        planner=fixed_planner(_layout(observed)),
        now=observed,
    )

    assert not qualification.is_available_at(
        observed + timedelta(seconds=301)
    )


def test_binding_and_capacity_can_be_admitted_without_scientific_rust(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 23, tzinfo=UTC)
    qualification = qualify(
        _config(tmp_path),
        FakeProbe(_facts(now)),
        planner=fixed_planner(_layout(now)),
        now=now,
    )
    assert qualification.binding is not None
    assert qualification.capacity is not None
    binding = qualification.binding
    capacity = qualification.capacity
    authority = Authority(tmp_path / "workspace")
    binding_decision = authority.decide(
        Proposal.record(
            Document(
                "metacraft.solver.lumerical_binding",
                binding.as_mapping(),
            )
        ),
        at=Revision.root(),
    )
    assert binding_decision.body_reference is not None
    capacity_decision = authority.decide(
        Proposal.capacity(
            scope=capacity.scope,
            limit=capacity.limit,
            qualification_references=(binding_decision.body_reference,),
        ),
        at=binding_decision.resulting_revision,
    )

    assert capacity_decision.admitted
    assert authority.view().current[0].key == (f"capacity:{capacity.scope}")
