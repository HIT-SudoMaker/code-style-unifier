from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import re
from typing import Protocol

from ..._environment import read_allowed_environment
from ...external_activity import (
    ExternalActivityClosure,
    _combine_external_activity,
)
from ...workstation import Demand, LANE_MEMORY_BYTES, Layout

_LUMERICAL_ENVIRONMENT_KEYS = frozenset(
    {
        "ANSYSLMD_LICENSE_FILE",
        "LUMERICAL_FDTD_PATH",
        "LUMERICAL_LICENSE_UTILITY_PATH",
        "LUMERICAL_PYTHON_API_PATH",
        "METACRAFT_CAPACITY_FRESHNESS_SECONDS",
        "METACRAFT_LUMERICAL_HEADLESS",
        "METACRAFT_RUNS_DIR",
        "METACRAFT_RUN_LUMERICAL_SMOKE",
        "METACRAFT_RUN_LUMERICAL_SOLVE",
    }
)


def read_lumerical_environment(
    path: Path,
    *,
    inherited: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """
    Read only Lumerical settings and inherit matching machine facts.
    """

    values = read_allowed_environment(
        path,
        allowed=_LUMERICAL_ENVIRONMENT_KEYS,
        family="lumerical",
        inherited=inherited,
    )
    return values


@dataclass(frozen=True, slots=True)
class LumericalConfig:
    """
    Holds exact product paths, license facts, and run settings.
    """

    executable: Path | None
    python_api: Path | None
    license_utility: Path | None
    license_server: str | None
    freshness_seconds: int = 300
    runs_directory: Path = Path("runs")

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> LumericalConfig:
        """
        Read explicit Lumerical facts without machine-wide discovery.
        """

        return cls(
            executable=_path_or_none(environ.get("LUMERICAL_FDTD_PATH")),
            python_api=_path_or_none(environ.get("LUMERICAL_PYTHON_API_PATH")),
            license_utility=_path_or_none(
                environ.get("LUMERICAL_LICENSE_UTILITY_PATH"),
            ),
            license_server=environ.get("ANSYSLMD_LICENSE_FILE"),
            freshness_seconds=int(
                environ.get("METACRAFT_CAPACITY_FRESHNESS_SECONDS", "300")
            ),
            runs_directory=Path(
                environ.get("METACRAFT_RUNS_DIR", "runs")
            ).expanduser().resolve(),
        )

    def has_required_settings(self) -> bool:
        """
        Report whether every required user setting is present.
        """

        return bool(
            self.executable
            and self.python_api
            and self.license_utility
            and self.license_server
            and self.freshness_seconds > 0
            and str(self.runs_directory)
        )

@dataclass(frozen=True, slots=True)
class InstallationObservation:
    """
    Records version, identity, license, and resource facts with no construction.

    The observation stages (``configured``, ``found``, ``versioned``,
    ``licensed``) construct no scientific geometry: a periodic-template
    property defect cannot surface here. Construction evidence belongs to the
    ``qualified`` stage through ``Probe.verify_periodic_responses``.
    """

    product_version: str
    api_identity: str
    lumerical_gui_limit: int
    lumerical_solve_limit: int
    resource_identity: str
    observed_at: datetime
    activity_closure: ExternalActivityClosure = ExternalActivityClosure.none()


# ---------------------------------------------------------------------------
# Route-neutral periodic response capabilities
#
# Each periodic response is a distinct scientific ability established by its
# own native fixture. ``periodic_transmission_response`` is proven by one
# propagation construction, engine execution, and finite complex-transmission
# observation. ``periodic_polarization_response`` is proven by both independent
# input bases needed to establish one finite Jones response.
# ``periodic_reference_surface_response`` is proven by one finite sampled field
# with its complete physical context. No fixture qualifies either sibling; the
# Adapter knows only the responses it can establish.
# ---------------------------------------------------------------------------

PERIODIC_TRANSMISSION_RESPONSE = "periodic_transmission_response"
PERIODIC_POLARIZATION_RESPONSE = "periodic_polarization_response"
PERIODIC_REFERENCE_SURFACE_RESPONSE = (
    "periodic_reference_surface_response"
)
_RESPONSE_CAPABILITY_ORDER: tuple[str, ...] = (
    PERIODIC_TRANSMISSION_RESPONSE,
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
)
_QUALIFIED_RESPONSE = "qualified"
_RESPONSE_NOT_RETURNED = "response_not_returned"
_RESPONSE_QUALIFICATION_STATUSES = frozenset(
    {_QUALIFIED_RESPONSE, _RESPONSE_NOT_RETURNED}
)


@dataclass(frozen=True, slots=True)
class PeriodicResponseQualification:
    """
    Records the closed qualification result for one exact response kind.

    The result deliberately carries no native payload, exception, placement,
    process, or session fact. Malformed observations never become a third
    status: they raise directly after native activity has closed.
    """

    response_kind: str
    status: str

    def __post_init__(self) -> None:
        if self.response_kind not in _RESPONSE_CAPABILITY_ORDER:
            raise ValueError(
                f"periodic_response_kind_unknown:{self.response_kind}"
            )
        if self.status not in _RESPONSE_QUALIFICATION_STATUSES:
            raise ValueError(
                f"periodic_response_status_unknown:{self.status}"
            )

    @classmethod
    def qualified(cls, response_kind: str) -> PeriodicResponseQualification:
        """
        Return the positive closed result for one response kind.
        """

        return cls(response_kind=response_kind, status=_QUALIFIED_RESPONSE)

    @classmethod
    def response_not_returned(
        cls,
        response_kind: str,
    ) -> PeriodicResponseQualification:
        """
        Return the sole unqualified result accepted by this module.
        """

        return cls(
            response_kind=response_kind,
            status=_RESPONSE_NOT_RETURNED,
        )

    @property
    def is_qualified(self) -> bool:
        """
        Report whether this exact response was qualified.
        """

        return self.status == _QUALIFIED_RESPONSE

    def as_mapping(self) -> dict[str, str]:
        """
        Return the complete redacted result document.
        """

        return {
            "response_kind": self.response_kind,
            "status": self.status,
        }

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
    ) -> PeriodicResponseQualification:
        """
        Restore one exact redacted result document.
        """

        if set(value) != {"response_kind", "status"}:
            raise ValueError("periodic_response_qualification_fields_invalid")
        response_kind = value["response_kind"]
        status = value["status"]
        if not isinstance(response_kind, str) or not isinstance(status, str):
            raise TypeError("periodic_response_qualification_values_invalid")
        return cls(response_kind=response_kind, status=status)


@dataclass(frozen=True, slots=True)
class PeriodicResponseProof:
    """
    Reports one ordered closed result for every periodic response kind.

    ``response_not_returned`` is the only unqualified status. Malformed,
    non-finite, mismatched, or drifting observations raise directly instead of
    being collapsed into qualification evidence.
    """

    response_qualifications: tuple[PeriodicResponseQualification, ...]
    activity_closure: ExternalActivityClosure = ExternalActivityClosure.none()

    def __post_init__(self) -> None:
        """
        Accept exactly one result for each response kind in canonical order.
        """

        if (
            type(self.response_qualifications) is not tuple
            or any(
                type(result) is not PeriodicResponseQualification
                for result in self.response_qualifications
            )
            or tuple(
                result.response_kind
                for result in self.response_qualifications
            )
            != _RESPONSE_CAPABILITY_ORDER
        ):
            raise TypeError("periodic_response_qualifications_invalid")

    @property
    def capabilities(self) -> tuple[str, ...]:
        """
        Return exactly the response capabilities this proof established.
        """

        return tuple(
            result.response_kind
            for result in self.response_qualifications
            if result.is_qualified
        )


class Probe(Protocol):
    """
    Defines the one read-only seam shared by production, fake, and live calls.

    ``observe`` records version, identity, license, and resource facts without
    constructing scientific geometry. ``verify_periodic_responses`` performs
    each periodic response's own native fixture and reports exactly the
    capabilities it proven (empty when the engine refused work).
    """

    def observe(self, config: LumericalConfig) -> InstallationObservation:
        """
        Observe version, license, and resource facts of one installation.
        """

        ...

    def verify_periodic_responses(
        self,
        config: LumericalConfig,
    ) -> PeriodicResponseProof:
        """
        Prove each periodic response through its own native fixture.
        """

        ...


@dataclass(frozen=True, slots=True)
class CapacityObservation:
    """
    Records one fresh bounded engine count and its contributing limits.
    """

    scope: str
    limit: int
    observed_at: datetime
    fresh_until: datetime
    lumerical_gui_limit: int
    lumerical_solve_limit: int
    workstation_limit: int

    def is_fresh_at(self, value: datetime) -> bool:
        """
        Report whether this observation may admit new permits.
        """

        return self.observed_at <= value <= self.fresh_until

    def as_mapping(self) -> dict[str, object]:
        """
        Return the complete capacity observation.
        """

        return {
            "fresh_until": _timestamp(self.fresh_until),
            "limit": self.limit,
            "lumerical_gui_limit": self.lumerical_gui_limit,
            "lumerical_solve_limit": self.lumerical_solve_limit,
            "observed_at": _timestamp(self.observed_at),
            "scope": self.scope,
            "workstation_limit": self.workstation_limit,
        }

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
    ) -> CapacityObservation:
        """
        Restore one exact production capacity observation.
        """

        if set(value) != {
            "fresh_until",
            "limit",
            "lumerical_gui_limit",
            "lumerical_solve_limit",
            "observed_at",
            "scope",
            "workstation_limit",
        }:
            raise RuntimeError("capacity_observation_fields_invalid")
        scope = value["scope"]
        if not isinstance(scope, str) or not scope.strip():
            raise RuntimeError("capacity_observation_invalid")
        observation = cls(
            scope=scope,
            limit=_capacity_limit(value["limit"]),
            observed_at=_parse_timestamp(value["observed_at"]),
            fresh_until=_parse_timestamp(value["fresh_until"]),
            lumerical_gui_limit=_capacity_limit(
                value["lumerical_gui_limit"]
            ),
            lumerical_solve_limit=_capacity_limit(
                value["lumerical_solve_limit"]
            ),
            workstation_limit=_capacity_limit(
                value["workstation_limit"]
            ),
        )
        if observation.as_mapping() != dict(value):
            raise RuntimeError("capacity_observation_invalid")
        return observation


@dataclass(frozen=True, slots=True)
class LicenseCapacity:
    """
    Records both momentary native Lumerical feature limits.
    """

    lumerical_gui_limit: int
    lumerical_solve_limit: int
    observed_at: datetime


class LumericalUnavailable(RuntimeError):
    """
    Expected solver absence as one narrow typed Adapter outcome.

    Discovery, qualification, license, and execution absence cross the Adapter
    seam as this single typed value carrying an exact ``reason``. Callers match
    via ``isinstance``; they never parse exception text. Malformed protocol,
    impossible lifecycle, invariant violation, and implementation drift are not
    expected absence and continue to raise directly.
    """

    def __init__(self, reason: str) -> None:
        """
        Retain the exact reason this product could not become available.
        """

        self.reason = reason
        super().__init__(f"lumerical_unavailable:{reason}")


def _lumerical_absences(
    error: BaseException,
) -> tuple[LumericalUnavailable, ...] | None:
    """
    Flatten one ordered failure made exclusively of typed product absence.
    """

    if isinstance(error, LumericalUnavailable):
        return (error,)
    if not isinstance(error, BaseExceptionGroup):
        return None
    gathered: list[LumericalUnavailable] = []
    for child in error.exceptions:
        absences = _lumerical_absences(child)
        if absences is None:
            return None
        gathered.extend(absences)
    return tuple(gathered)


@dataclass(frozen=True, slots=True)
class LumericalBinding:
    """
    Holds one exact qualified solver implementation.

    ``response_qualifications`` persists one ordered, redacted result for each
    route-neutral response kind. Capabilities are derived from those results;
    the binding never stores a second, potentially conflicting truth.
    """

    executable: str
    engine: str
    python_api: str
    product_version: str
    api_identity: str
    license_server: str
    resource_identity: str
    response_qualifications: tuple[PeriodicResponseQualification, ...]

    def __post_init__(self) -> None:
        """
        Require the same complete ordered result set as the native proof.
        """

        if (
            type(self.response_qualifications) is not tuple
            or any(
                type(result) is not PeriodicResponseQualification
                for result in self.response_qualifications
            )
            or tuple(
                result.response_kind
                for result in self.response_qualifications
            )
            != _RESPONSE_CAPABILITY_ORDER
        ):
            raise TypeError("binding_response_qualifications_invalid")

    @property
    def response_capabilities(self) -> tuple[str, ...]:
        """
        Derive the route-neutral responses this binding proved.
        """

        return tuple(
            result.response_kind
            for result in self.response_qualifications
            if result.is_qualified
        )

    def as_mapping(self) -> dict[str, object]:
        """
        Return the immutable binding evidence.
        """

        return {
            "api_identity": self.api_identity,
            "engine": self.engine,
            "executable": self.executable,
            "license_server": self.license_server,
            "native_license_features": (
                "lumerical_gui",
                "lumerical_solve",
            ),
            "product_version": self.product_version,
            "python_api": self.python_api,
            "resource_identity": self.resource_identity,
            "response_qualifications": tuple(
                result.as_mapping()
                for result in self.response_qualifications
            ),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> LumericalBinding:
        """
        Restore one canonical immutable binding document.
        """

        expected_fields = {
            "api_identity",
            "engine",
            "executable",
            "license_server",
            "native_license_features",
            "product_version",
            "python_api",
            "resource_identity",
            "response_qualifications",
        }
        if set(value) != expected_fields:
            raise ValueError("lumerical_binding_fields_invalid")
        text_fields: dict[str, str] = {
            name: _binding_text(value[name])
            for name in (
                "api_identity",
                "engine",
                "executable",
                "license_server",
                "product_version",
                "python_api",
                "resource_identity",
            )
        }
        license_features = value["native_license_features"]
        if (
            not isinstance(license_features, (list, tuple))
            or tuple(license_features)
            != ("lumerical_gui", "lumerical_solve")
        ):
            raise ValueError("lumerical_binding_license_features_invalid")
        qualifications = value["response_qualifications"]
        if not isinstance(qualifications, (list, tuple)):
            raise TypeError("binding_response_qualifications_invalid")
        restored = cls(
            executable=text_fields["executable"],
            engine=text_fields["engine"],
            python_api=text_fields["python_api"],
            product_version=text_fields["product_version"],
            api_identity=text_fields["api_identity"],
            license_server=text_fields["license_server"],
            resource_identity=text_fields["resource_identity"],
            response_qualifications=tuple(
                PeriodicResponseQualification.from_mapping(result)
                if isinstance(result, Mapping)
                else _raise_response_qualification_type()
                for result in qualifications
            ),
        )
        if restored.as_mapping() != {
            **dict(value),
            "native_license_features": tuple(license_features),
            "response_qualifications": tuple(
                dict(result)
                if isinstance(result, Mapping)
                else result
                for result in qualifications
            ),
        }:
            raise ValueError("lumerical_binding_invalid")
        return restored


@dataclass(frozen=True, slots=True)
class LumericalQualification:
    """
    Separates immutable binding facts from momentary capacity.
    """

    reached: tuple[str, ...]
    findings: tuple[str, ...]
    binding: LumericalBinding | None
    capacity: CapacityObservation | None
    activity_closure: ExternalActivityClosure = ExternalActivityClosure.none()

    def is_available_at(self, value: datetime) -> bool:
        """
        Derive availability from a qualified binding and fresh capacity.
        """

        return (
            self.binding is not None
            and self.capacity is not None
            and self.capacity.limit > 0
            and self.capacity.is_fresh_at(value)
        )


def qualify(
    config: LumericalConfig,
    probe: Probe,
    *,
    planner: Callable[[Demand], Layout],
    now: datetime | None = None,
) -> LumericalQualification:
    """
    Walk one ordered qualification shared by production, fake, and live calls.

    Stages advance ``configured -> found -> versioned -> licensed ->
    qualified -> available``. The first four stages observe configuration,
    product paths, version, and license without constructing scientific
    geometry; ``qualified`` performs each periodic response's own native
    fixture through the probe and issues exactly the capabilities each
    fixture proved; ``available`` derives from the qualified binding plus
    fresh positive capacity planned from the same observation.
    """

    reached, finding = _locate(config)
    if finding is not None:
        return _failed(reached, finding)
    try:
        observation = probe.observe(config)
    except LumericalUnavailable as error:
        return _failed(reached, error.reason)
    activity_closure = observation.activity_closure
    if (
        not observation.product_version.strip()
        or not observation.api_identity.strip()
    ):
        return _failed(
            reached,
            "product_identity_missing",
            activity_closure=activity_closure,
        )
    reached += ("versioned",)
    if (
        observation.lumerical_gui_limit <= 0
        or observation.lumerical_solve_limit <= 0
    ):
        return _failed(
            reached,
            "license_unavailable",
            activity_closure=activity_closure,
        )
    reached += ("licensed",)
    try:
        proof = probe.verify_periodic_responses(config)
    except LumericalUnavailable as error:
        return _failed(
            reached,
            error.reason,
            activity_closure=activity_closure,
        )
    if type(proof) is not PeriodicResponseProof:
        raise TypeError("periodic_response_proof_required")
    activity_closure = _combine_external_activity(
        activity_closure,
        proof.activity_closure,
    )
    capabilities = proof.capabilities
    if not capabilities:
        return _failed(
            reached,
            "solver_execution_unverified",
            activity_closure=activity_closure,
        )
    reached += ("qualified",)
    binding = _binding(
        config,
        observation,
        proof.response_qualifications,
    )
    layout = planner(
        Demand(
            workers=min(
                observation.lumerical_gui_limit,
                observation.lumerical_solve_limit,
            ),
            worker_memory_bytes=LANE_MEMORY_BYTES,
        )
    )
    capacity = bounded_capacity(
        config,
        binding,
        LicenseCapacity(
            lumerical_gui_limit=observation.lumerical_gui_limit,
            lumerical_solve_limit=observation.lumerical_solve_limit,
            observed_at=observation.observed_at,
        ),
        layout,
    )
    return _complete(
        reached,
        binding,
        capacity,
        now or datetime.now(UTC),
        activity_closure=activity_closure,
    )


def _complete(
    reached: tuple[str, ...],
    binding: LumericalBinding,
    capacity: CapacityObservation | None,
    now: datetime,
    *,
    activity_closure: ExternalActivityClosure,
) -> LumericalQualification:
    """
    Derive the available outcome from a qualified binding and fresh capacity.
    """

    if capacity is None:
        return LumericalQualification(
            reached=reached,
            findings=("capacity_not_positive",),
            binding=binding,
            capacity=None,
            activity_closure=activity_closure,
        )
    if not capacity.is_fresh_at(now):
        return LumericalQualification(
            reached=reached,
            findings=("capacity_stale",),
            binding=binding,
            capacity=capacity,
            activity_closure=activity_closure,
        )
    return LumericalQualification(
        reached=reached,
        findings=(),
        binding=binding,
        capacity=capacity,
        activity_closure=activity_closure,
    )


def _locate(
    config: LumericalConfig,
) -> tuple[tuple[str, ...], str | None]:
    """
    Establish the configured and found qualification facts.
    """

    if not config.has_required_settings():
        return (), "configuration_incomplete"
    reached = ("configured",)
    assert config.executable is not None
    assert config.python_api is not None
    if not config.executable.is_file():
        return reached, "executable_not_found"
    engine = config.executable.with_name("fdtd-engine.exe")
    if not engine.is_file():
        return reached, "engine_not_found"
    if not config.python_api.is_file():
        return reached, "python_api_not_found"
    return reached + ("found",), None


def bounded_capacity(
    config: LumericalConfig,
    binding: LumericalBinding,
    license_capacity: LicenseCapacity,
    layout: Layout,
) -> CapacityObservation | None:
    """
    Bind fresh license and workstation facts to one qualified solver.
    """

    if config.license_server != binding.license_server:
        raise RuntimeError("lumerical_license_server_changed")
    limit = min(
        license_capacity.lumerical_gui_limit,
        license_capacity.lumerical_solve_limit,
        layout.limit,
    )
    if limit <= 0:
        return None
    observed_at = max(license_capacity.observed_at, layout.observed_at)
    return CapacityObservation(
        scope=(
            "lumerical-fdtd/"
            f"{layout.host_identity}/"
            f"{binding.resource_identity}/"
            f"{binding.license_server}"
        ),
        limit=limit,
        observed_at=observed_at,
        fresh_until=min(
            license_capacity.observed_at
            + timedelta(seconds=config.freshness_seconds),
            layout.fresh_until,
        ),
        lumerical_gui_limit=license_capacity.lumerical_gui_limit,
        lumerical_solve_limit=license_capacity.lumerical_solve_limit,
        workstation_limit=layout.limit,
    )


def _failed(
    reached: tuple[str, ...],
    finding: str,
    *,
    activity_closure: ExternalActivityClosure | None = None,
) -> LumericalQualification:
    return LumericalQualification(
        reached=reached,
        findings=(finding,),
        binding=None,
        capacity=None,
        activity_closure=(
            ExternalActivityClosure.none()
            if activity_closure is None
            else activity_closure
        ),
    )


def _binding(
    config: LumericalConfig,
    observation: InstallationObservation,
    response_qualifications: tuple[PeriodicResponseQualification, ...],
) -> LumericalBinding:
    assert config.executable is not None
    assert config.python_api is not None
    assert config.license_server is not None
    return LumericalBinding(
        executable=str(config.executable.resolve()),
        engine=str(
            config.executable.with_name("fdtd-engine.exe").resolve(),
        ),
        python_api=str(config.python_api.resolve()),
        product_version=observation.product_version,
        api_identity=observation.api_identity,
        license_server=config.license_server,
        resource_identity=observation.resource_identity,
        response_qualifications=response_qualifications,
    )


def _raise_response_qualification_type() -> PeriodicResponseQualification:
    raise TypeError("binding_response_qualification_invalid")


def _binding_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError("lumerical_binding_values_invalid")
    return value


def _path_or_none(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser().resolve()


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _capacity_limit(value: object) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
    ):
        raise RuntimeError("capacity_observation_invalid")
    return value


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise RuntimeError("capacity_timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise RuntimeError("capacity_timestamp_invalid") from error
    if parsed.tzinfo is None:
        raise RuntimeError("capacity_timestamp_invalid")
    return parsed.astimezone(UTC)
