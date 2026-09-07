from collections.abc import Callable, Mapping
from pathlib import Path
import threading
from typing import Any

from metacraft.external_activity import (
    ExternalActivityClosure,
    ExternalActivityOrigin,
)
from metacraft.solvers.lumerical_fdtd.material import (
    LumericalMaterialSample,
)
from metacraft.solvers.lumerical_fdtd.project_execution import ProjectExecution
from metacraft.solvers.lumerical_fdtd.qualification import (
    InstallationObservation,
    LicenseCapacity,
    LumericalConfig,
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseQualification,
    PeriodicResponseProof,
)
from metacraft.solvers.lumerical_fdtd.session import (
    _GratingResponsePlanes,
    _OptionalResult,
)
from metacraft.workstation import Lane


class ActiveEngines:
    """
    Count concurrently active test sessions.
    """

    def __init__(self) -> None:
        """
        Start with no active test engines.
        """

        self._lock = threading.Lock()
        self.current = 0
        self.maximum = 0

    def enter(self) -> None:
        """
        Record one test engine becoming active.
        """

        with self._lock:
            self.current += 1
            self.maximum = max(self.maximum, self.current)

    def leave(self) -> None:
        """
        Record one test engine leaving active execution.
        """

        with self._lock:
            self.current -= 1


class FakeSession:
    """
    Record product-neutral constructions without external software.
    """

    def __init__(
        self,
        *,
        active: ActiveEngines,
        result: (
            Mapping[str, Any]
            | Callable[[Mapping[str, Mapping[str, Any]]], Mapping[str, Any]]
        ),
        before_run: Callable[[], None] | None = None,
    ) -> None:
        """
        Retain one deterministic result and optional run hook.
        """

        self._active = active
        self._result = result if callable(result) else dict(result)
        self._before_run = before_run
        self._objects: dict[str, dict[str, Any]] = {}
        self._closed = False
        self._solve_count = 0
        self.placement: Mapping[str, object] | None = None

    @property
    def closed(self) -> bool:
        """
        Report the observable native-session lifetime.
        """

        return self._closed

    def create(
        self,
        kind: str,
        name: str,
        properties: Mapping[str, Any],
    ) -> None:
        """
        Retain one declared product-neutral object.
        """

        if self._closed:
            raise RuntimeError("session_closed")
        self._objects[name] = {"kind": kind, **properties}

    def read(
        self,
        name: str,
        properties: tuple[str, ...],
    ) -> Mapping[str, Any]:
        """
        Return deterministic construction read-back.
        """

        observed = self._objects[name]
        return {
            property_name: observed[property_name]
            for property_name in properties
        }

    def save(self, path: Path) -> None:
        """
        Save a deterministic project placeholder.
        """

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake-fsp")

    def run(self) -> None:
        """
        Execute the optional synchronized test hook.
        """

        self._active.enter()
        try:
            if self._before_run is not None:
                self._before_run()
        finally:
            self._active.leave()

    def solve(self, before: Path, after: Path) -> ProjectExecution:
        """
        Complete one deterministic project through the private native seam.
        """

        if self.placement is None:
            raise RuntimeError("fake_session_placement_missing")
        self.save(before)
        self.run()
        self.save(after)
        self._solve_count += 1
        return ProjectExecution(
            source="deterministic_test",
            is_native=False,
            project=after.name,
            return_code=0,
            placement=self.placement,
        )

    def result(self, name: str, result_name: str) -> Any:
        """
        Return the configured deterministic solver response.
        """

        if name not in self._objects:
            raise KeyError(f"result_missing:{name}:{result_name}")
        if name == "solver" and result_name == "termination":
            if not callable(self._result):
                named = self._result.get("_responses")
                if isinstance(named, Mapping) and "termination" in named:
                    configured = named["termination"]
                    if isinstance(configured, (list, tuple)):
                        return configured[self._solve_count - 1]
                    return configured
            maximum_time_fs = self._objects["solver"]["simulation_time_fs"]
            return {
                "autoshutoff_threshold": "0.00001",
                "native_status": 2,
                "outcome": "autoshutoff",
                "simulated_time_fs": str(maximum_time_fs // 2),
                "terminal_autoshutoff": "0.000009",
            }
        if callable(self._result):
            return self._result(self._objects)
        named = self._result.get("_responses")
        if isinstance(named, Mapping):
            if result_name not in named:
                raise KeyError(f"result_missing:{name}:{result_name}")
            configured = named[result_name]
            if isinstance(configured, (list, tuple)):
                return configured[self._solve_count - 1]
            return configured
        return self._result

    def optional_result(
        self,
        name: str,
        result_name: str,
    ) -> _OptionalResult:
        """
        Mirror native inventory absence without translating result faults.
        """

        if not callable(self._result):
            named = self._result.get("_responses")
            if isinstance(named, Mapping) and result_name not in named:
                return _OptionalResult.response_not_returned()
        return _OptionalResult.returned(self.result(name, result_name))

    def prepare_grating_response(self, name: str) -> _GratingResponsePlanes:
        """
        Derive physical planes from the declared grating placement.
        """

        group = self._objects[name]
        center = int(group["position_z_nm"])
        span = int(group["span_z_nm"])
        offset = int(group["source_offset_nm"])
        return _GratingResponsePlanes(
            reflection_plane_z_nm=center - span // 2 + 2 * offset,
            source_plane_z_nm=center - span // 2 + offset,
            transmission_plane_z_nm=center + span // 2,
        )

    def change_maximum_time(
        self,
        name: str,
        maximum_time_fs: int,
    ) -> None:
        """
        Apply one deterministic maximum-time extension.
        """

        if self._objects[name]["kind"] != "fdtd":
            raise ValueError("solver_time_owner_invalid")
        self._objects[name]["simulation_time_fs"] = maximum_time_fs

    def reset(self) -> None:
        """
        Clear one completed fake construction for the next candidate.
        """

        if self._closed:
            raise RuntimeError("session_closed")
        self._objects.clear()

    def close(self) -> None:
        """
        Mark this test session closed.
        """

        self._closed = True


class FakeSessionFactory:
    """
    Create independent test sessions over one shared counter.
    """

    def __init__(
        self,
        *,
        active: ActiveEngines,
        result: (
            Mapping[str, Any]
            | Callable[[Mapping[str, Mapping[str, Any]]], Mapping[str, Any]]
        ),
        before_run: Callable[[], None] | None = None,
    ) -> None:
        """
        Retain the shared counter and deterministic response.
        """

        self._active = active
        self._result = result
        self._before_run = before_run
        self.sessions: list[FakeSession] = []

    def __call__(self, lane: Lane) -> FakeSession:
        """
        Create one fresh test session for one admitted lane.
        """

        session = FakeSession(
            active=self._active,
            result=self._result,
            before_run=self._before_run,
        )
        session.placement = {
            "effective_cpu_sets": 4,
            "job_memory_bytes": 16 * 1024**3,
            "lane": lane.as_mapping(),
        }
        self.sessions.append(session)
        return session


class FakeProbe:
    """
    Return deterministic qualification facts at the shared probe seam.
    """

    def __init__(
        self,
        observation: InstallationObservation,
        *,
        proof: PeriodicResponseProof | None = None,
        transmission: bool = True,
        polarization: bool = True,
        material_sample: LumericalMaterialSample | None = None,
    ) -> None:
        """
        Retain one exact observation and periodic-response proof.
        """

        self.observation = observation
        self.proof = (
            proof
            if proof is not None
            else PeriodicResponseProof(
                response_qualifications=(
                    (
                        PeriodicResponseQualification.qualified(
                            PERIODIC_TRANSMISSION_RESPONSE
                        )
                        if transmission
                        else (
                            PeriodicResponseQualification
                            .response_not_returned(
                                PERIODIC_TRANSMISSION_RESPONSE
                            )
                        )
                    ),
                    (
                        PeriodicResponseQualification.qualified(
                            PERIODIC_POLARIZATION_RESPONSE
                        )
                        if polarization
                        else (
                            PeriodicResponseQualification
                            .response_not_returned(
                                PERIODIC_POLARIZATION_RESPONSE
                            )
                        )
                    ),
                    PeriodicResponseQualification.response_not_returned(
                        PERIODIC_REFERENCE_SURFACE_RESPONSE
                    ),
                )
            )
        )
        self.material_sample = material_sample

    def observe(self, config: LumericalConfig) -> InstallationObservation:
        """
        Return the configured fixture observation.
        """

        return self.observation

    def verify_periodic_responses(
        self,
        config: LumericalConfig,
    ) -> PeriodicResponseProof:
        """
        Return the configured periodic-response proof.
        """

        return self.proof

    def refresh_capacity(self, config: LumericalConfig) -> LicenseCapacity:
        """
        Return the deterministic momentary limits carried by the observation.
        """

        return LicenseCapacity(
            lumerical_gui_limit=self.observation.lumerical_gui_limit,
            lumerical_solve_limit=self.observation.lumerical_solve_limit,
            observed_at=self.observation.observed_at,
        )

    def sample_materials(
        self,
        config: LumericalConfig,
        catalogue: Mapping[str, str],
        wavelength_nm: int,
    ) -> tuple[LumericalMaterialSample, ExternalActivityClosure]:
        """
        Return an explicitly supplied task-scoped sample.
        """

        if self.material_sample is None:
            raise RuntimeError("fake_material_sample_missing")
        return self.material_sample, ExternalActivityClosure(
            origin=ExternalActivityOrigin.NATIVE,
            acquired_authority_work_count=0,
            settled_authority_work_count=0,
            started_external_execution_count=0,
            settled_external_execution_count=0,
            opened_product_session_count=1,
            closed_product_session_count=1,
            opened_local_placement_count=0,
            closed_local_placement_count=0,
        )
