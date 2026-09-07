from __future__ import annotations

from typing import Protocol

from ...authority import Reference
from ...authority.session import AuthoritySession
from ...external_activity import ExternalActivityClosure
from ...materials import (
    MaterialUnavailable,
    MaterialUnavailableReason,
    MaterialVerificationOutcome,
    MaterialVerificationRequest,
    VerifiedMaterial,
    VerifiedMaterialBatch,
)
from .material import (
    LumericalMaterialSample,
    MaterialVerificationRefusal,
    MaterialVerificationRefusalKind,
)
from .probe import ProductProbe
from .qualification import LumericalConfig


class NativeMaterialProbe(Protocol):
    """
    Read native material values without choosing scientific families.
    """

    def sample_materials(
        self,
        config: LumericalConfig,
        native_names: dict[str, str],
        wavelength_nm: int,
    ) -> tuple[
        LumericalMaterialSample | MaterialVerificationRefusal,
        ExternalActivityClosure,
    ]:
        """
        Sample exact native names and return their closed activity.
        """

        ...


class LumericalMaterialVerifier:
    """
    Verify already-selected registrations against one Lumerical product.
    """

    __slots__ = (
        "_binding_reference",
        "_config",
        "_probe",
        "_session",
    )

    def __init__(
        self,
        *,
        session: AuthoritySession,
        config: LumericalConfig,
        binding_reference: Reference,
        probe: NativeMaterialProbe | None = None,
    ) -> None:
        """
        Bind native verification to one admitted product configuration.
        """

        session.observe_admitted(binding_reference)
        self._session = session
        self._config = config
        self._binding_reference = binding_reference
        self._probe = ProductProbe() if probe is None else probe

    @property
    def binding_reference(self) -> Reference:
        """
        Return the exact admitted product binding used for verification.
        """

        return self._binding_reference

    def verify(
        self,
        request: MaterialVerificationRequest,
    ) -> MaterialVerificationOutcome:
        """
        Verify selected registrations through one native product session.
        """

        if request.binding_reference != self._binding_reference:
            raise ValueError("material_verification_binding_mismatch")
        native_names: dict[str, str] = {}
        references: dict[str, Reference] = {}
        for selection in request.selections:
            material = selection.material
            if material.solver != "lumerical fdtd":
                raise ValueError("solver_material_solver_mismatch")
            if self._session.fetch(selection.reference) != (
                material.document().to_bytes()
            ):
                raise ValueError("solver_material_admission_mismatch")
            native_names[material.family] = material.native_name
            references[material.family] = selection.reference
        observed, activity = self._probe.sample_materials(
            self._config,
            native_names,
            request.observation_request.wavelength_nm,
        )
        if isinstance(observed, MaterialVerificationRefusal):
            return _unavailable(request, observed, activity=activity)
        sample = observed.with_sources(
            binding_reference=self._binding_reference,
            registration_references=references,
        )
        refusal = sample.verify_readback(
            native_names=native_names,
            wavelength_nm=request.observation_request.wavelength_nm,
        )
        if refusal is not None:
            return _unavailable(request, refusal, activity=activity)
        product_reference = self._session.admit_document(
            sample.to_document(),
            references=(
                self._binding_reference,
                *(selection.reference for selection in request.selections),
            ),
        )
        return VerifiedMaterialBatch(
            product_sample_reference=product_reference,
            materials=tuple(
                VerifiedMaterial(
                    family=family,
                    native_name=resolved.native_name,
                    refractive_index=resolved.refractive_index,
                    extinction_coefficient=(resolved.extinction_coefficient),
                )
                for family in native_names
                for resolved in (
                    sample.resolve(
                        family,
                        request.observation_request.wavelength_nm,
                    ),
                )
            ),
            activity=activity,
        )


def _unavailable(
    request: MaterialVerificationRequest,
    refusal: MaterialVerificationRefusal,
    *,
    activity: ExternalActivityClosure,
) -> MaterialUnavailable:
    if refusal.kind is MaterialVerificationRefusalKind.NATIVE_MATERIAL_ABSENT:
        reason = MaterialUnavailableReason.NATIVE_MATERIAL_ABSENT
    elif refusal.kind is MaterialVerificationRefusalKind.WAVELENGTH_UNCOVERED:
        reason = MaterialUnavailableReason.WAVELENGTH_UNCOVERED
    else:
        raise RuntimeError(f"material_refusal_unbound:{refusal.kind.value}")
    return MaterialUnavailable(
        request=request.observation_request,
        reason=reason,
        family=refusal.family,
        activity=activity,
        native_name=refusal.native_name,
    )
