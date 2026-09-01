from __future__ import annotations

from experiments.restoration.adaptive_measurement.validation.hardware_readiness import (
    HardwareEvidence,
    REQUIRED_HARDWARE_EVIDENCE,
    assess_hardware_readiness,
)


def _complete_evidence() -> HardwareEvidence:
    return HardwareEvidence(
        optical_topology_id="bench-v1",
        coherent_modality="coherent transmission",
        wavelength_m=638e-9,
        numerical_aperture=0.25,
        object_pixel_size_m=1e-6,
        reference_provenance="calibration arm before science shutter",
        safe_action_id="flat-lut-v1",
        input_amplitude_slm_lut_id="amplitude-lut-v1",
        fourier_phase_slm_lut_id="phase-lut-v1",
        pupil_registration_id="pupil-registration-v1",
        polarization_state="linear horizontal",
        fringe_visibility=0.72,
        reference_drift_radians_per_s=0.01,
        calibration_throughput=0.35,
        science_throughput=0.42,
        camera_readout_s=0.004,
        phase_slm_settling_s=0.016,
        correction_lifetime_s=2.0,
        maximum_calibration_observations=8,
        is_pupil_conjugate=True,
        is_input_amplitude_slm_held=True,
        is_reference_enabled_in_science=True,
    )


def test_empty_hardware_evidence_reports_every_required_measurement() -> None:
    report = assess_hardware_readiness(HardwareEvidence())

    assert report.status == "NOT_READY"
    assert report.missing_fields == REQUIRED_HARDWARE_EVIDENCE
    assert dict(report.invalid_fields) == {}


def test_complete_measured_hardware_evidence_is_ready() -> None:
    report = assess_hardware_readiness(_complete_evidence())

    assert report.status == "READY"
    assert report.missing_fields == ()
    assert dict(report.invalid_fields) == {}


def test_hardware_evidence_enforces_science_causality_and_probe_ceiling() -> None:
    evidence = HardwareEvidence.from_mapping(
        {
            field_name: getattr(_complete_evidence(), field_name)
            for field_name in REQUIRED_HARDWARE_EVIDENCE
        }
        | {
            "is_reference_enabled_in_science": False,
            "maximum_calibration_observations": 10,
        }
    )

    report = assess_hardware_readiness(evidence)

    assert report.status == "NOT_READY"
    assert "is_reference_enabled_in_science" in report.invalid_fields
    assert "maximum_calibration_observations" in report.invalid_fields
