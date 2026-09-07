from __future__ import annotations

from collections.abc import Callable, Mapping

from ..authority import Document, Reference
from ..authority.session import AuthoritySession
from ..external_activity import ExternalActivityClosure
from .solver import AdmittedSolverMaterial, SolverMaterialLibrary
from .verification import (
    MaterialObservationRequest,
    MaterialOutcome,
    MaterialResponse,
    MaterialResponseContext,
    MaterialUnavailable,
    MaterialUnavailableReason,
    MaterialVerificationOutcome,
    MaterialVerificationRequest,
    ObservedMaterials,
    VerifiedMaterialBatch,
    material_observation_key,
)


MATERIAL_OBSERVATION_INDEX_SCHEMA = "metacraft.material.observation_index"


def open_material_response(
    *,
    session: AuthoritySession,
    library: SolverMaterialLibrary,
    binding_reference: Reference,
    capacity_scope: str,
    verify_materials: Callable[
        [MaterialVerificationRequest],
        MaterialVerificationOutcome,
    ],
) -> MaterialResponse:
    """
    Open one project-owned selection and admission response.
    """

    return _VerifyingMaterialResponse(
        session=session,
        context=MaterialResponseContext(
            binding_reference=binding_reference,
            capacity_scope=capacity_scope,
        ),
        library=library,
        verify_materials=verify_materials,
    )


class _VerifyingMaterialResponse:
    """
    Select project registrations before invoking native verification.
    """

    __slots__ = (
        "_context",
        "_library",
        "_session",
        "_verify_materials",
    )

    def __init__(
        self,
        *,
        session: AuthoritySession,
        context: MaterialResponseContext,
        library: SolverMaterialLibrary,
        verify_materials: Callable[
            [MaterialVerificationRequest],
            MaterialVerificationOutcome,
        ],
    ) -> None:
        """
        Bind selection, admission, and native verification dependencies.
        """

        if not callable(verify_materials):
            raise TypeError("material_verification_not_callable")
        session.observe_admitted(context.binding_reference)
        self._session = session
        self._context = context
        self._library = library
        self._verify_materials = verify_materials

    @property
    def context(self) -> MaterialResponseContext:
        """
        Return the exact binding and capacity scope for this response.
        """

        return self._context

    def observe(
        self,
        request: MaterialObservationRequest,
    ) -> MaterialOutcome:
        """
        Select, verify, admit, and return one material observation.
        """

        selections: list[AdmittedSolverMaterial] = []
        for family in dict.fromkeys(request.families):
            material = self._library.select(family)
            if material is None:
                return MaterialUnavailable(
                    request=request,
                    reason=MaterialUnavailableReason.REGISTRATION_ABSENT,
                    family=family,
                    activity=ExternalActivityClosure.none(),
                )
            selections.append(
                AdmittedSolverMaterial(
                    material=material,
                    reference=self._session.admit_document(material.document()),
                )
            )
        verification_request = MaterialVerificationRequest(
            observation_request=request,
            binding_reference=self._context.binding_reference,
            selections=tuple(selections),
        )
        verified = self._verify_materials(verification_request)
        if isinstance(verified, MaterialUnavailable):
            if verified.request != request or verified.reason not in {
                MaterialUnavailableReason.NATIVE_MATERIAL_ABSENT,
                MaterialUnavailableReason.WAVELENGTH_UNCOVERED,
            }:
                raise ValueError("material_verification_outcome_invalid")
            return verified
        _validate_verified_batch(verification_request, verified)
        observation = ObservedMaterials.create(
            verification_request,
            product_sample_reference=(verified.product_sample_reference),
            materials=verified.materials,
            activity=verified.activity,
        )
        _admit_material_observation(
            self._session,
            context=self._context,
            observation=observation,
        )
        return observation


class RecordedMaterialResponse:
    """
    Restore an exact admitted material observation without product work.
    """

    __slots__ = ("_context", "_session")

    def __init__(
        self,
        session: AuthoritySession,
        *,
        context: MaterialResponseContext,
    ) -> None:
        """
        Bind replay to one Authority session and material context.
        """

        session.observe_admitted(context.binding_reference)
        self._session = session
        self._context = context

    @property
    def context(self) -> MaterialResponseContext:
        """
        Return the exact binding and capacity scope used for replay.
        """

        return self._context

    def observe(
        self,
        request: MaterialObservationRequest,
    ) -> MaterialOutcome:
        """
        Restore one exact admitted observation without product work.
        """

        key = material_observation_key(self._context, request)
        index_reference = self._session.current_reference(key)
        if index_reference is None:
            return MaterialUnavailable(
                request=request,
                reason=(MaterialUnavailableReason.RECORDED_OBSERVATION_MISSING),
                family=request.families[0],
                activity=ExternalActivityClosure.recorded(),
            )
        index = Document.from_bytes(self._session.fetch(index_reference))
        values = _mapping(index.values)
        if (
            index.schema_identifier != MATERIAL_OBSERVATION_INDEX_SCHEMA
            or set(values)
            != {
                "binding_reference",
                "request_identity",
                "observation_reference",
            }
            or values["request_identity"] != request.identity
            or Reference.from_mapping(_mapping(values["binding_reference"]))
            != self._context.binding_reference
        ):
            raise ValueError("material_observation_index_invalid")
        observation_reference = Reference.from_mapping(
            _mapping(values["observation_reference"])
        )
        restored = ObservedMaterials.from_document(
            Document.from_bytes(self._session.fetch(observation_reference)),
            reference=observation_reference,
            activity=ExternalActivityClosure.recorded(),
        )
        if (
            restored.observation_request != request
            or restored.solver_binding_reference != self._context.binding_reference
        ):
            raise ValueError("material_observation_request_mismatch")
        self._session.observe_admitted(restored.product_sample_reference)
        for selection in restored.selections:
            self._session.observe_admitted(selection.reference)
        return restored


def _validate_verified_batch(
    request: MaterialVerificationRequest,
    verified: VerifiedMaterialBatch,
) -> None:
    if tuple(material.family for material in verified.materials) != tuple(
        selection.material.family for selection in request.selections
    ):
        raise ValueError("material_verification_family_mismatch")
    for selection, material in zip(
        request.selections,
        verified.materials,
        strict=True,
    ):
        if material.native_name != selection.material.native_name:
            raise ValueError("material_verification_native_name_mismatch")


def _admit_material_observation(
    session: AuthoritySession,
    *,
    context: MaterialResponseContext,
    observation: ObservedMaterials,
) -> Reference:
    if observation.solver_binding_reference != context.binding_reference:
        raise ValueError("material_response_binding_mismatch")
    reference = session.admit_document(
        observation.document(),
        references=tuple(
            dict.fromkeys(
                (
                    context.binding_reference,
                    observation.product_sample_reference,
                    *(selection.reference for selection in observation.selections),
                )
            )
        ),
    )
    if reference != observation.sample_reference:
        raise RuntimeError("material_observation_admission_mismatch")
    key = material_observation_key(
        context,
        observation.observation_request,
    )
    return session.admit_current(
        Document(
            MATERIAL_OBSERVATION_INDEX_SCHEMA,
            {
                "binding_reference": (context.binding_reference.as_mapping()),
                "request_identity": observation.request_identity,
                "observation_reference": reference.as_mapping(),
            },
        ),
        key=key,
        supersedes=session.current_reference(key),
        references=(reference,),
    )


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("material_observation_index_invalid")
    return value
