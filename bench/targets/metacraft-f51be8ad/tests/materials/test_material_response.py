from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from metacraft.authority import Authority, Document
from metacraft.authority.reference import reference_for
from metacraft.authority.session import AuthoritySession
from metacraft.external_activity import (
    ExternalActivityClosure,
    ExternalActivityOrigin,
)
from metacraft.materials import (
    AdmittedSolverMaterial,
    MaterialObservationRequest,
    MaterialUnavailable,
    MaterialUnavailableReason,
    MaterialVerificationRequest,
    ObservedMaterials,
    SolverMaterial,
    SolverMaterialLibrary,
    VerifiedMaterial,
    VerifiedMaterialBatch,
    open_material_response,
)


def _reference(schema: str):
    document = Document(schema, {"qualified": True})
    return reference_for(document.to_bytes())


def _native_activity() -> ExternalActivityClosure:
    return ExternalActivityClosure(
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


def _observation_request(
    *families: str,
) -> MaterialObservationRequest:
    return MaterialObservationRequest(
        families=families,
        wavelength_nm=532,
    )


def _silicon_selection() -> AdmittedSolverMaterial:
    material = SolverMaterial(
        solver="lumerical fdtd",
        family="silicon",
        native_name="Si (Silicon) - Palik",
        provenance="fixture",
    )
    return AdmittedSolverMaterial(
        material=material,
        reference=reference_for(material.document().to_bytes()),
    )


def _silicon_observation() -> VerifiedMaterial:
    return VerifiedMaterial(
        family="silicon",
        native_name="Si (Silicon) - Palik",
        refractive_index=Decimal("4.14"),
        extinction_coefficient=Decimal("0.045"),
    )


def _request(*families: str) -> MaterialVerificationRequest:
    return MaterialVerificationRequest(
        observation_request=_observation_request(*families),
        binding_reference=_reference("fixture.material.binding"),
        selections=(_silicon_selection(),),
    )


def test_observation_codec_binds_typed_values_to_exact_bytes() -> None:
    observation_request = _observation_request(
        "silicon",
        "silicon dioxide",
    )
    silicon = _silicon_selection()
    silica_material = SolverMaterial(
        solver="lumerical fdtd",
        family="silicon dioxide",
        native_name="SiO2 (Glass) - Palik",
        provenance="fixture",
    )
    silica = AdmittedSolverMaterial(
        material=silica_material,
        reference=reference_for(silica_material.document().to_bytes()),
    )
    request = MaterialVerificationRequest(
        observation_request=observation_request,
        binding_reference=_reference("fixture.material.binding"),
        selections=(silicon, silica),
    )
    observed = ObservedMaterials.create(
        request,
        product_sample_reference=_reference("fixture.product.sample"),
        materials=(
            _silicon_observation(),
            VerifiedMaterial(
                family="silicon dioxide",
                native_name="SiO2 (Glass) - Palik",
                refractive_index=Decimal("1.46"),
                extinction_coefficient=Decimal("0"),
            ),
        ),
        activity=_native_activity(),
    )

    restored = ObservedMaterials.from_document(
        observed.document(),
        reference=observed.sample_reference,
        activity=ExternalActivityClosure.recorded(),
    )

    assert restored == replace(
        observed,
        activity=ExternalActivityClosure.recorded(),
    )
    assert restored.document().to_bytes() == observed.document().to_bytes()
    assert restored.sample_reference == observed.sample_reference
    with pytest.raises(
        ValueError,
        match="material_observation_reference_mismatch",
    ):
        replace(restored, sample_reference=_reference("fixture.tampered"))


def test_repeated_family_reuses_the_same_exact_observation() -> None:
    request = _request("silicon", "silicon")
    selection = _silicon_selection()
    material = _silicon_observation()

    observed = ObservedMaterials.create(
        request,
        product_sample_reference=_reference("fixture.product.sample"),
        materials=(material,),
        activity=_native_activity(),
    )

    assert observed.observation_request.families == (
        "silicon",
        "silicon",
    )
    assert observed.selections == (selection,)


def test_observation_rejects_native_identity_substitution() -> None:
    request = _request("silicon")
    selection = _silicon_selection()

    with pytest.raises(
        ValueError,
        match="observed_material_native_name_mismatch",
    ):
        ObservedMaterials.create(
            request,
            product_sample_reference=_reference("fixture.product.sample"),
            materials=(
                replace(
                    _silicon_observation(),
                    native_name="substituted silicon",
                ),
            ),
            activity=_native_activity(),
        )


def test_unavailable_reason_is_validated_against_the_exact_request() -> None:
    request = _observation_request("silicon")

    with pytest.raises(ValueError, match="material_unavailable_invalid"):
        MaterialUnavailable(
            request=request,
            reason=MaterialUnavailableReason.REGISTRATION_ABSENT,
            family="silicon dioxide",
            activity=ExternalActivityClosure.none(),
        )
    with pytest.raises(ValueError, match="material_unavailable_invalid"):
        MaterialUnavailable(
            request=request,
            reason=MaterialUnavailableReason.NATIVE_MATERIAL_ABSENT,
            family="silicon",
            activity=_native_activity(),
        )
    with pytest.raises(ValueError, match="material_unavailable_invalid"):
        MaterialUnavailable(
            request=request,
            reason="registration_absent",  # type: ignore[arg-type]
            family="silicon",
            activity=ExternalActivityClosure.none(),
        )


def test_project_response_admits_only_requested_registrations_before_verification(
    tmp_path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    binding_reference = session.admit_document(
        Document("fixture.material.binding", {"qualified": True})
    )
    library = SolverMaterialLibrary.decode_bytes(
        b"""
solver = "lumerical fdtd"

[[materials]]
family = "silicon"
native_name = "Si (Silicon) - Palik"
provenance = "fixture"

[[materials]]
family = "silicon dioxide"
native_name = "SiO2 (Glass) - Palik"
provenance = "unused fixture"
"""
    )
    requests: list[MaterialVerificationRequest] = []

    def verify(
        request: MaterialVerificationRequest,
    ) -> VerifiedMaterialBatch:
        requests.append(request)
        selection = request.selections[0]
        assert session.fetch(selection.reference) == (
            selection.material.document().to_bytes()
        )
        return VerifiedMaterialBatch(
            product_sample_reference=session.admit_document(
                Document("fixture.product.sample", {"verified": True})
            ),
            materials=(_silicon_observation(),),
            activity=_native_activity(),
        )

    response = open_material_response(
        session=session,
        library=library,
        binding_reference=binding_reference,
        capacity_scope="fixture:material",
        verify_materials=verify,
    )

    outcome = response.observe(_observation_request("silicon", "silicon"))

    assert isinstance(outcome, ObservedMaterials)
    assert len(requests) == 1
    assert tuple(selection.material.family for selection in requests[0].selections) == (
        "silicon",
    )
    assert b"silicon dioxide" not in outcome.document().to_bytes()
    assert outcome.activity == _native_activity()


def test_registration_absence_reports_zero_native_activity(tmp_path) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    binding_reference = session.admit_document(
        Document("fixture.material.binding", {"qualified": True})
    )
    response = open_material_response(
        session=session,
        library=SolverMaterialLibrary.decode_bytes(
            b'''solver = "lumerical fdtd"\nmaterials = []\n'''
        ),
        binding_reference=binding_reference,
        capacity_scope="fixture:material",
        verify_materials=lambda _request: pytest.fail(
            "registration absence invoked native verification"
        ),
    )

    outcome = response.observe(_observation_request("silicon"))

    assert isinstance(outcome, MaterialUnavailable)
    assert outcome.reason is MaterialUnavailableReason.REGISTRATION_ABSENT
    assert outcome.activity == ExternalActivityClosure.none()
