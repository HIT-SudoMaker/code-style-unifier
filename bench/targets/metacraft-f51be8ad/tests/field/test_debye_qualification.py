from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import torch

from metacraft.authority import Authority, Document, Reference, reference_for
from metacraft.field.debye_qualification import (AplanaticFocusQualification,
                                                 AplanaticReferenceQualification,
                                                 aplanatic_reference_binding,
                                                 qualify_aplanatic_reference,
                                                 qualify_czt_debye,
                                                 qualify_fft_debye,
                                                 restore_aplanatic_reference_binding)
from metacraft.field.fast_debye import CZTDebyeRealization, FFTDebyeRealization


def test_fft_and_czt_bind_only_after_answering_to_physical_invariants() -> None:
    """
    Qualify both accelerations against low- and high-NA complex vector fields.
    """

    qualifications = (
        qualify_fft_debye(
            FFTDebyeRealization(device="cpu", pupil_samples=129)
        ),
        qualify_czt_debye(
            CZTDebyeRealization(device="cpu", pupil_samples=129)
        ),
    )

    for qualification in qualifications:
        assert isinstance(qualification, AplanaticFocusQualification)
        assert qualification.is_qualified
        assert qualification.binding == qualification.realization
        assert qualification.reference_method == (
            "analytic Richards--Wolf invariants"
        )
        assert qualification.reference_fixtures == (
            "low na analytic on-axis field",
            "high na analytic on-axis field",
            "transverse reflection symmetry",
            "longitudinal reflection antisymmetry",
            "positive quadrature handedness",
            "selected device",
        )
        assert set(qualification.fixture_errors) == set(
            qualification.reference_fixtures
        )
        assert qualification.as_mapping()["realization"] == (
            qualification.realization.as_mapping()
        )


def test_fast_debye_qualification_keeps_capacity_out_of_identity() -> None:
    """
    Let two batching capacities bind the same scientific realization.
    """

    realization = CZTDebyeRealization(
        device="cpu",
        pupil_samples=65,
        axial_plane_batch_size=1,
    )

    first = qualify_czt_debye(realization)
    second = qualify_czt_debye(
        replace(realization, axial_plane_batch_size=4)
    )

    assert first.is_qualified
    assert second.is_qualified
    assert first.binding == second.binding
    assert first.as_mapping()["realization"] == (
        second.as_mapping()["realization"]
    )


def test_failed_selected_device_produces_no_fast_debye_binding() -> None:
    """
    Preserve a selected CUDA failure without CPU or alternate-method fallback.
    """

    qualification = qualify_fft_debye(
        FFTDebyeRealization(
            device="cuda:999",
            pupil_samples=65,
        )
    )

    assert not qualification.is_qualified
    assert qualification.binding is None
    assert qualification.realization.device == "cuda:999"
    assert qualification.reason is not None


def test_fft_and_czt_jointly_qualify_on_the_frozen_matched_grid() -> None:
    fft = qualify_fft_debye(FFTDebyeRealization(device="cpu", pupil_samples=65))
    czt = qualify_czt_debye(CZTDebyeRealization(device="cpu", pupil_samples=65))

    joint = qualify_aplanatic_reference(
        fft,
        czt,
        fft_qualification_reference=reference_for(fft.document().to_bytes()),
        czt_qualification_reference=reference_for(czt.document().to_bytes()),
    )

    assert isinstance(joint, AplanaticReferenceQualification)
    assert joint.is_qualified
    assert len(joint.fixture_agreements) == 12
    assert max(
        error
        for agreement in joint.fixture_agreements.values()
        for error in agreement.values()
    ) <= 1e-10


def test_joint_binding_closes_both_independent_facts_and_matched_grid() -> None:
    fft = qualify_fft_debye(FFTDebyeRealization(device="cpu", pupil_samples=65))
    czt = qualify_czt_debye(CZTDebyeRealization(device="cpu", pupil_samples=65))
    fft_reference = reference_for(fft.document().to_bytes())
    czt_reference = reference_for(czt.document().to_bytes())
    joint = qualify_aplanatic_reference(
        fft,
        czt,
        fft_qualification_reference=fft_reference,
        czt_qualification_reference=czt_reference,
    )
    joint_reference = reference_for(joint.document().to_bytes())
    binding = aplanatic_reference_binding(
        joint,
        joint_qualification_reference=joint_reference,
    )
    objects = {
        fft_reference: fft.document().to_bytes(),
        czt_reference: czt.document().to_bytes(),
        joint_reference: joint.document().to_bytes(),
    }

    restored_fft, restored_czt = restore_aplanatic_reference_binding(
        binding,
        objects.__getitem__,
    )

    assert restored_fft == fft.realization
    assert restored_czt == czt.realization
    retired = Document(
        binding.schema_identifier,
        {
            "operations": ["form_aplanatic_reference"],
            "qualified": True,
            "realization": czt.realization.as_mapping(),
        },
    )
    with pytest.raises(ValueError, match="aplanatic_reference_binding_mismatch"):
        restore_aplanatic_reference_binding(retired, objects.__getitem__)


def test_joint_binding_normalizes_a_missing_authority_qualification(
    tmp_path: Path,
) -> None:
    fft = qualify_fft_debye(FFTDebyeRealization(device="cpu", pupil_samples=65))
    czt = qualify_czt_debye(CZTDebyeRealization(device="cpu", pupil_samples=65))
    joint = qualify_aplanatic_reference(
        fft,
        czt,
        fft_qualification_reference=reference_for(fft.document().to_bytes()),
        czt_qualification_reference=reference_for(czt.document().to_bytes()),
    )
    binding = aplanatic_reference_binding(
        joint,
        joint_qualification_reference=reference_for(joint.document().to_bytes()),
    )
    authority = Authority(tmp_path / "authority")

    with pytest.raises(ValueError, match="aplanatic_reference_binding_mismatch"):
        restore_aplanatic_reference_binding(binding, authority.fetch)


def test_joint_binding_does_not_hide_an_authority_implementation_failure() -> None:
    fft = qualify_fft_debye(FFTDebyeRealization(device="cpu", pupil_samples=65))
    czt = qualify_czt_debye(CZTDebyeRealization(device="cpu", pupil_samples=65))
    joint = qualify_aplanatic_reference(
        fft,
        czt,
        fft_qualification_reference=reference_for(fft.document().to_bytes()),
        czt_qualification_reference=reference_for(czt.document().to_bytes()),
    )
    binding = aplanatic_reference_binding(
        joint,
        joint_qualification_reference=reference_for(joint.document().to_bytes()),
    )

    def fail_fetch(_reference: Reference) -> bytes:
        raise RuntimeError("authority_database_failed")

    with pytest.raises(RuntimeError, match="authority_database_failed"):
        restore_aplanatic_reference_binding(binding, fail_fetch)


@pytest.mark.parametrize(
    ("fixture_name", "mutated_error"),
    (
        ("low na analytic on-axis field", "0.0050000001"),
        ("high na analytic on-axis field", "0.0050000001"),
        ("transverse reflection symmetry", "0.00000000011"),
        ("longitudinal reflection antisymmetry", "0.00000000011"),
        ("positive quadrature handedness", "0.00000000011"),
        ("selected device", "0.000000000001"),
        ("low na analytic on-axis field", "nan"),
        ("low na analytic on-axis field", "-0.1"),
    ),
)
def test_joint_binding_rejects_rehashed_unearned_independent_qualification(
    fixture_name: str,
    mutated_error: str,
) -> None:
    fft = qualify_fft_debye(FFTDebyeRealization(device="cpu", pupil_samples=65))
    czt = qualify_czt_debye(CZTDebyeRealization(device="cpu", pupil_samples=65))
    original_fft_reference = reference_for(fft.document().to_bytes())
    czt_reference = reference_for(czt.document().to_bytes())
    joint = qualify_aplanatic_reference(
        fft,
        czt,
        fft_qualification_reference=original_fft_reference,
        czt_qualification_reference=czt_reference,
    )
    mutated_fft_values = dict(fft.document().values)
    mutated_errors = dict(mutated_fft_values["fixture_errors"])
    mutated_errors[fixture_name] = mutated_error
    mutated_fft_values["fixture_errors"] = mutated_errors
    mutated_fft = Document(fft.document().schema_identifier, mutated_fft_values)
    mutated_fft_reference = reference_for(mutated_fft.to_bytes())
    joint_values = dict(joint.document().values)
    joint_values["fft_qualification_reference"] = (
        mutated_fft_reference.as_mapping()
    )
    mutated_joint = Document(joint.document().schema_identifier, joint_values)
    mutated_joint_reference = reference_for(mutated_joint.to_bytes())
    binding = aplanatic_reference_binding(
        joint,
        joint_qualification_reference=reference_for(joint.document().to_bytes()),
    )
    binding_values = dict(binding.values)
    qualification_references = dict(binding_values["qualification_references"])
    qualification_references["fft"] = mutated_fft_reference.as_mapping()
    qualification_references["joint"] = mutated_joint_reference.as_mapping()
    binding_values["qualification_references"] = qualification_references
    mutated_binding = Document(binding.schema_identifier, binding_values)
    objects = {
        mutated_fft_reference: mutated_fft.to_bytes(),
        czt_reference: czt.document().to_bytes(),
        mutated_joint_reference: mutated_joint.to_bytes(),
    }

    with pytest.raises(ValueError, match="aplanatic_reference_binding_mismatch"):
        restore_aplanatic_reference_binding(mutated_binding, objects.__getitem__)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_joint_qualification_stays_on_the_selected_cuda_device() -> None:
    device = f"cuda:{torch.cuda.current_device()}"
    fft = qualify_fft_debye(FFTDebyeRealization(device=device, pupil_samples=65))
    czt = qualify_czt_debye(CZTDebyeRealization(device=device, pupil_samples=65))
    joint = qualify_aplanatic_reference(
        fft,
        czt,
        fft_qualification_reference=reference_for(fft.document().to_bytes()),
        czt_qualification_reference=reference_for(czt.document().to_bytes()),
    )

    assert joint.is_qualified
    assert joint.fft_realization.device == joint.czt_realization.device == device
