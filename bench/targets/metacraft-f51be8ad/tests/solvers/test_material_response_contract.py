from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from metacraft.authority import Authority, Document
from metacraft.authority.session import AuthoritySession
from metacraft.external_activity import (
    ExternalActivityClosure,
    ExternalActivityOrigin,
)
from metacraft.materials import (
    MaterialObservationRequest,
    MaterialUnavailable,
    MaterialUnavailableReason,
    ObservedMaterials,
    RecordedMaterialResponse,
    SolverMaterialLibrary,
    open_material_response,
)
from metacraft.solvers.lumerical_fdtd import (
    LumericalConfig,
    LumericalMaterialVerifier,
)
from metacraft.solvers.lumerical_fdtd.material import (
    LumericalMaterialSample,
    MaterialVerificationRefusal,
    MaterialVerificationRefusalKind,
    NativeIndexPoint,
    NativeMaterialSample,
    sample_frequency_hz,
)


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


class _FakeNativeMaterialProbe:
    def __init__(
        self,
        refusal_kind: MaterialVerificationRefusalKind | None = None,
    ) -> None:
        self.calls = 0
        self.refusal_kind = refusal_kind

    def sample_materials(
        self,
        config: LumericalConfig,
        native_names: dict[str, str],
        wavelength_nm: int,
    ) -> tuple[
        LumericalMaterialSample | MaterialVerificationRefusal,
        ExternalActivityClosure,
    ]:
        self.calls += 1
        if self.refusal_kind is not None:
            family, native_name = next(iter(native_names.items()))
            return (
                MaterialVerificationRefusal(
                    kind=self.refusal_kind,
                    family=family,
                    native_name=native_name,
                    wavelength_nm=wavelength_nm,
                ),
                _native_activity(),
            )
        frequency = Decimal(str(sample_frequency_hz(wavelength_nm)))
        return (
            LumericalMaterialSample(
                grid_wavelengths_nm=(wavelength_nm,),
                minimum_fit_frequency_hz=frequency,
                maximum_fit_frequency_hz=frequency,
                materials={
                    family: NativeMaterialSample(
                        family=family,
                        native_name=native_name,
                        fit_tolerance=Decimal("0.1"),
                        fit_maximum_coefficients=6,
                        minimum_tabulated_frequency_hz=frequency,
                        maximum_tabulated_frequency_hz=frequency,
                        points=(
                            NativeIndexPoint(
                                wavelength_nm=wavelength_nm,
                                frequency_hz=frequency,
                                refractive_index=Decimal("4.14"),
                                extinction_coefficient=Decimal("0.045"),
                                fit_residual=Decimal("0.001"),
                            ),
                        ),
                        findings=(),
                    )
                    for family, native_name in native_names.items()
                },
            ),
            _native_activity(),
        )


def _catalogue() -> SolverMaterialLibrary:
    return SolverMaterialLibrary.decode_bytes(
        b"""
solver = "lumerical fdtd"

[[materials]]
family = "silicon"
native_name = "Si (Silicon) - Palik"
provenance = "contract fixture"
"""
    )


def _config(tmp_path: Path) -> LumericalConfig:
    return LumericalConfig(
        executable=None,
        python_api=None,
        license_utility=None,
        license_server=None,
        runs_directory=tmp_path / "runs",
    )


def test_live_and_recorded_material_responses_share_exact_bytes(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "authority"
    tmp_path.mkdir(parents=True, exist_ok=True)
    authority = Authority(workspace)
    session = AuthoritySession(authority)
    binding_reference = session.admit_document(
        Document("fixture.lumerical.binding", {"qualified": True})
    )
    probe = _FakeNativeMaterialProbe()
    verifier = LumericalMaterialVerifier(
        session=session,
        config=_config(tmp_path),
        binding_reference=binding_reference,
        probe=probe,
    )
    live = open_material_response(
        session=session,
        library=_catalogue(),
        binding_reference=verifier.binding_reference,
        capacity_scope="fixture:lumerical-material",
        verify_materials=verifier.verify,
    )
    request = MaterialObservationRequest(
        families=("silicon", "silicon"),
        wavelength_nm=532,
    )

    live_outcome = live.observe(request)
    recorded_outcome = RecordedMaterialResponse(
        AuthoritySession(authority),
        context=live.context,
    ).observe(request)

    assert isinstance(live_outcome, ObservedMaterials)
    assert isinstance(recorded_outcome, ObservedMaterials)
    assert live_outcome.activity.origin is ExternalActivityOrigin.NATIVE
    assert live_outcome.activity.opened_product_session_count == 1
    assert recorded_outcome.activity == ExternalActivityClosure.recorded()
    assert recorded_outcome.sample_reference == live_outcome.sample_reference
    assert recorded_outcome.document().to_bytes() == (
        live_outcome.document().to_bytes()
    )
    assert probe.calls == 1

    missing = RecordedMaterialResponse(
        AuthoritySession(authority),
        context=live.context,
    ).observe(
        MaterialObservationRequest(
            families=("silicon",),
            wavelength_nm=633,
        )
    )
    assert isinstance(missing, MaterialUnavailable)
    assert missing.reason is MaterialUnavailableReason.RECORDED_OBSERVATION_MISSING
    assert missing.activity == ExternalActivityClosure.recorded()


@pytest.mark.parametrize(
    ("refusal_kind", "reason"),
    (
        (
            MaterialVerificationRefusalKind.NATIVE_MATERIAL_ABSENT,
            MaterialUnavailableReason.NATIVE_MATERIAL_ABSENT,
        ),
        (
            MaterialVerificationRefusalKind.WAVELENGTH_UNCOVERED,
            MaterialUnavailableReason.WAVELENGTH_UNCOVERED,
        ),
    ),
)
def test_native_material_refusal_preserves_exact_closed_activity(
    tmp_path: Path,
    refusal_kind: MaterialVerificationRefusalKind,
    reason: MaterialUnavailableReason,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    binding_reference = session.admit_document(
        Document("fixture.lumerical.binding", {"qualified": True})
    )
    verifier = LumericalMaterialVerifier(
        session=session,
        config=_config(tmp_path),
        binding_reference=binding_reference,
        probe=_FakeNativeMaterialProbe(refusal_kind),
    )
    response = open_material_response(
        session=session,
        library=_catalogue(),
        binding_reference=binding_reference,
        capacity_scope="fixture:lumerical-material",
        verify_materials=verifier.verify,
    )

    outcome = response.observe(
        MaterialObservationRequest(
            families=("silicon",),
            wavelength_nm=532,
        )
    )

    assert isinstance(outcome, MaterialUnavailable)
    assert outcome.reason is reason
    assert outcome.activity == _native_activity()
