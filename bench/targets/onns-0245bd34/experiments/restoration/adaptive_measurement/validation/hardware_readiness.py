from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
import math
from numbers import Integral, Real
from types import MappingProxyType
from typing import Any, Literal, cast


@dataclass(frozen=True, slots=True)
class HardwareEvidence:
    """Measured E0 values required before a hardware oracle experiment."""

    optical_topology_id: str | None = None
    coherent_modality: str | None = None
    wavelength_m: float | None = None
    numerical_aperture: float | None = None
    object_pixel_size_m: float | None = None
    reference_provenance: str | None = None
    safe_action_id: str | None = None
    input_amplitude_slm_lut_id: str | None = None
    fourier_phase_slm_lut_id: str | None = None
    pupil_registration_id: str | None = None
    polarization_state: str | None = None
    fringe_visibility: float | None = None
    reference_drift_radians_per_s: float | None = None
    calibration_throughput: float | None = None
    science_throughput: float | None = None
    camera_readout_s: float | None = None
    phase_slm_settling_s: float | None = None
    correction_lifetime_s: float | None = None
    maximum_calibration_observations: int | None = None
    is_pupil_conjugate: bool | None = None
    is_input_amplitude_slm_held: bool | None = None
    is_reference_enabled_in_science: bool | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "HardwareEvidence":
        """Parse untrusted JSON values at the external Interface."""
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        values = {field.name: payload.get(field.name) for field in fields(cls)}
        return cls(**cast(dict[str, Any], values))


REQUIRED_HARDWARE_EVIDENCE = tuple(field.name for field in fields(HardwareEvidence))


@dataclass(frozen=True, slots=True)
class HardwareReadinessReport:
    """Report missing or invalid E0 evidence without inventing measurements."""

    status: Literal["READY", "NOT_READY"]
    missing_fields: tuple[str, ...]
    invalid_fields: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "invalid_fields",
            MappingProxyType(dict(self.invalid_fields)),
        )


def assess_hardware_readiness(
    evidence: HardwareEvidence,
) -> HardwareReadinessReport:
    """Evaluate whether measured E0 inputs are sufficient to start hardware E1."""
    if not isinstance(evidence, HardwareEvidence):
        raise TypeError("evidence must be HardwareEvidence")
    missing = tuple(
        field_name
        for field_name in REQUIRED_HARDWARE_EVIDENCE
        if not _is_recorded(getattr(evidence, field_name))
    )
    invalid: dict[str, str] = {}
    if not missing:
        _validate_strings(evidence, invalid)
        _validate_positive_measurements(evidence, invalid)
        _validate_bounded_measurements(evidence, invalid)
        _validate_required_states(evidence, invalid)
    status: Literal["READY", "NOT_READY"] = (
        "READY" if not missing and not invalid else "NOT_READY"
    )
    return HardwareReadinessReport(
        status=status,
        missing_fields=missing,
        invalid_fields=invalid,
    )


def _is_recorded(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _validate_strings(
    evidence: HardwareEvidence,
    invalid: dict[str, str],
) -> None:
    for field_name in (
        "optical_topology_id",
        "coherent_modality",
        "reference_provenance",
        "safe_action_id",
        "input_amplitude_slm_lut_id",
        "fourier_phase_slm_lut_id",
        "pupil_registration_id",
        "polarization_state",
    ):
        value = getattr(evidence, field_name)
        if not isinstance(value, str) or not value.strip():
            invalid[field_name] = (
                "must be a non-empty measured identifier or description"
            )


def _validate_positive_measurements(
    evidence: HardwareEvidence,
    invalid: dict[str, str],
) -> None:
    for field_name in (
        "wavelength_m",
        "numerical_aperture",
        "object_pixel_size_m",
        "calibration_throughput",
        "science_throughput",
        "camera_readout_s",
        "phase_slm_settling_s",
        "correction_lifetime_s",
    ):
        value = getattr(evidence, field_name)
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(float(value))
            or float(value) <= 0.0
        ):
            invalid[field_name] = "must be a finite positive measured value"


def _validate_bounded_measurements(
    evidence: HardwareEvidence,
    invalid: dict[str, str],
) -> None:
    visibility = evidence.fringe_visibility
    if (
        isinstance(visibility, bool)
        or not isinstance(visibility, Real)
        or not math.isfinite(float(visibility))
        or not 0.0 < float(visibility) <= 1.0
    ):
        invalid["fringe_visibility"] = "must be a measured value in (0, 1]"
    drift = evidence.reference_drift_radians_per_s
    if (
        isinstance(drift, bool)
        or not isinstance(drift, Real)
        or not math.isfinite(float(drift))
        or float(drift) < 0.0
    ):
        invalid["reference_drift_radians_per_s"] = (
            "must be a finite nonnegative measured value"
        )
    maximum_observations = evidence.maximum_calibration_observations
    if (
        isinstance(maximum_observations, bool)
        or not isinstance(maximum_observations, Integral)
        or not 1 <= int(maximum_observations) <= 8
    ):
        invalid["maximum_calibration_observations"] = (
            "must be an integer between 1 and the preregistered ceiling 8"
        )


def _validate_required_states(
    evidence: HardwareEvidence,
    invalid: dict[str, str],
) -> None:
    for field_name in (
        "is_pupil_conjugate",
        "is_input_amplitude_slm_held",
        "is_reference_enabled_in_science",
    ):
        if getattr(evidence, field_name) is not True:
            invalid[field_name] = "must be measured or demonstrated as true"
