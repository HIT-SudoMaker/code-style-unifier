from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import hashlib
from typing import Protocol, TypeAlias

from ..authority import Document, Reference
from ..authority.reference import reference_for, reference_matches
from ..canonical import encode_bytes
from ..external_activity import ExternalActivityClosure
from .family import is_canonical_material_family
from .solver import AdmittedSolverMaterial, SolverMaterial


MATERIAL_OBSERVATION_SCHEMA = "metacraft.material.observation"


@dataclass(frozen=True, slots=True)
class MaterialResponseContext:
    """
    Identify the exact product binding used by material work.
    """

    binding_reference: Reference
    capacity_scope: str

    def __post_init__(self) -> None:
        """
        Require a non-empty product capacity scope.
        """

        if not isinstance(self.capacity_scope, str) or not self.capacity_scope.strip():
            raise ValueError("material_response_capacity_scope_invalid")


@dataclass(frozen=True, slots=True)
class MaterialObservationRequest:
    """
    State the scientific families and wavelength that need native evidence.

    Repeated families are intentional: atom and substrate may share one
    requested family while retaining distinct scientific roles.
    """

    families: tuple[str, ...]
    wavelength_nm: int

    def __post_init__(self) -> None:
        """
        Require canonical families and one positive integer wavelength.
        """

        if (
            not isinstance(self.families, tuple)
            or not self.families
            or any(not is_canonical_material_family(family) for family in self.families)
        ):
            raise ValueError("material_observation_request_families_invalid")
        if type(self.wavelength_nm) is not int or self.wavelength_nm <= 0:
            raise ValueError("material_observation_request_wavelength_invalid")

    @property
    def identity(self) -> str:
        """
        Return the stable identity of this scientific request.
        """

        return (
            "sha256:" + hashlib.sha256(encode_bytes(self.canonical_value())).hexdigest()
        )

    def canonical_value(self) -> dict[str, object]:
        """
        Return the route-neutral request value used for identity.
        """

        return {
            "families": self.families,
            "wavelength_nm": self.wavelength_nm,
        }


@dataclass(frozen=True, slots=True)
class MaterialVerificationRequest:
    """
    Bind one observation request to exact Authority-admitted registrations.
    """

    observation_request: MaterialObservationRequest
    binding_reference: Reference
    selections: tuple[AdmittedSolverMaterial, ...]

    def __post_init__(self) -> None:
        """
        Require exact, unique selections for every requested family.
        """

        selected_families = tuple(
            selection.material.family for selection in self.selections
        )
        if (
            not isinstance(
                self.observation_request,
                MaterialObservationRequest,
            )
            or not isinstance(self.selections, tuple)
            or not self.selections
            or selected_families
            != tuple(dict.fromkeys(self.observation_request.families))
            or len({selection.material.solver for selection in self.selections}) != 1
        ):
            raise ValueError("material_verification_request_invalid")

    def canonical_value(self) -> dict[str, object]:
        """
        Return the admitted registrations bound to this request.
        """

        return {
            "binding_reference": self.binding_reference.as_mapping(),
            "observation_request": (self.observation_request.canonical_value()),
            "selections": {
                f"selection_{index:03d}": {
                    "material": selection.material.document().values,
                    "reference": selection.reference.as_mapping(),
                }
                for index, selection in enumerate(
                    self.selections,
                    start=1,
                )
            },
        }


@dataclass(frozen=True, slots=True)
class VerifiedMaterial:
    """
    Preserve one exact solver-native optical observation.
    """

    family: str
    native_name: str
    refractive_index: Decimal
    extinction_coefficient: Decimal

    def __post_init__(self) -> None:
        """
        Require one finite passive optical observation.
        """

        if (
            not is_canonical_material_family(self.family)
            or not self.native_name.strip()
            or not self.refractive_index.is_finite()
            or not self.extinction_coefficient.is_finite()
            or self.refractive_index <= 0
            or self.extinction_coefficient < 0
        ):
            raise ValueError("verified_material_invalid")

    def canonical_value(self) -> dict[str, str]:
        """
        Return one canonical solver-native material value.
        """

        return {
            "extinction_coefficient": format(
                self.extinction_coefficient,
                "f",
            ),
            "family": self.family,
            "native_name": self.native_name,
            "refractive_index": format(self.refractive_index, "f"),
        }


@dataclass(frozen=True, slots=True)
class VerifiedMaterialBatch:
    """
    Return one product sample and its route-neutral exact values.
    """

    product_sample_reference: Reference
    materials: tuple[VerifiedMaterial, ...]
    activity: ExternalActivityClosure

    def __post_init__(self) -> None:
        """
        Require a non-empty unique batch and its closed activity.
        """

        families = tuple(material.family for material in self.materials)
        if (
            not isinstance(self.materials, tuple)
            or not self.materials
            or len(families) != len(set(families))
            or not isinstance(self.activity, ExternalActivityClosure)
        ):
            raise ValueError("verified_material_batch_invalid")


@dataclass(frozen=True, slots=True)
class ObservedMaterials:
    """
    Return selected registrations and one canonical admitted observation.
    """

    request: MaterialVerificationRequest
    product_sample_reference: Reference
    sample_reference: Reference
    materials: tuple[VerifiedMaterial, ...]
    activity: ExternalActivityClosure

    def __post_init__(self) -> None:
        """
        Verify selection order, native identity, and canonical reference.
        """

        selected_families = tuple(
            selection.material.family for selection in self.selections
        )
        observed_families = tuple(material.family for material in self.materials)
        solvers = {selection.material.solver for selection in self.selections}
        if (
            selected_families != observed_families
            or len(solvers) != 1
            or not isinstance(self.activity, ExternalActivityClosure)
        ):
            raise ValueError("observed_materials_invalid")
        for family, selection, material in zip(
            selected_families,
            self.selections,
            self.materials,
            strict=True,
        ):
            if material.native_name != selection.material.native_name:
                raise ValueError("observed_material_native_name_mismatch")
        if not reference_matches(
            self.sample_reference,
            self.document().to_bytes(),
        ):
            raise ValueError("material_observation_reference_mismatch")

    @property
    def observation_request(self) -> MaterialObservationRequest:
        """
        Return the scientific request behind native verification.
        """

        return self.request.observation_request

    @property
    def request_identity(self) -> str:
        """
        Return the stable identity of the scientific request.
        """

        return self.observation_request.identity

    @property
    def selections(self) -> tuple[AdmittedSolverMaterial, ...]:
        """
        Return the exact Authority-admitted solver registrations.
        """

        return self.request.selections

    @property
    def solver_binding_reference(self) -> Reference:
        """
        Return the product binding used for native verification.
        """

        return self.request.binding_reference

    def document(self) -> Document:
        """
        Return the canonical material observation without activity.
        """

        return _observation_document(
            self.request,
            product_sample_reference=self.product_sample_reference,
            materials=self.materials,
        )

    @classmethod
    def create(
        cls,
        request: MaterialVerificationRequest,
        *,
        product_sample_reference: Reference,
        materials: tuple[VerifiedMaterial, ...],
        activity: ExternalActivityClosure,
    ) -> ObservedMaterials:
        """
        Create an observation and derive its canonical reference.
        """

        document = _observation_document(
            request,
            product_sample_reference=product_sample_reference,
            materials=materials,
        )
        return cls(
            request=request,
            product_sample_reference=product_sample_reference,
            sample_reference=reference_for(document.to_bytes()),
            materials=materials,
            activity=activity,
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        reference: Reference,
        activity: ExternalActivityClosure,
    ) -> ObservedMaterials:
        """
        Restore exact observation bytes with call-local activity.
        """

        if document.schema_identifier != MATERIAL_OBSERVATION_SCHEMA:
            raise ValueError("material_observation_schema_mismatch")
        values = _mapping(document.values, "material_observation_invalid")
        if set(values) != {
            "materials",
            "product_sample_reference",
            "request",
        }:
            raise ValueError("material_observation_invalid")
        request = _restore_request(values["request"])
        materials = tuple(
            _restore_material(value)
            for value in _sequence(
                _indexed_values(
                    values["materials"],
                    "material",
                    "material_observation_invalid",
                ),
                "material_observation_invalid",
            )
        )
        restored = cls(
            request=request,
            product_sample_reference=Reference.from_mapping(
                _mapping(
                    values["product_sample_reference"],
                    "material_observation_invalid",
                )
            ),
            sample_reference=reference,
            materials=materials,
            activity=activity,
        )
        if restored.document().to_bytes() != document.to_bytes():
            raise ValueError("material_observation_document_mismatch")
        return restored


class MaterialUnavailableReason(str, Enum):
    """
    Name each expected material-observation absence.
    """

    REGISTRATION_ABSENT = "registration_absent"
    NATIVE_MATERIAL_ABSENT = "native_material_absent"
    WAVELENGTH_UNCOVERED = "wavelength_uncovered"
    RECORDED_OBSERVATION_MISSING = "recorded_observation_missing"


@dataclass(frozen=True, slots=True)
class MaterialUnavailable:
    """
    Return one expected absence for one exact request.
    """

    request: MaterialObservationRequest
    reason: MaterialUnavailableReason
    family: str
    activity: ExternalActivityClosure
    native_name: str | None = None

    def __post_init__(self) -> None:
        """
        Require an absence consistent with its request and reason.
        """

        if not isinstance(self.reason, MaterialUnavailableReason):
            raise ValueError("material_unavailable_invalid")
        has_native_name_requirement = self.reason in {
            MaterialUnavailableReason.NATIVE_MATERIAL_ABSENT,
            MaterialUnavailableReason.WAVELENGTH_UNCOVERED,
        }
        if (
            self.family not in self.request.families
            or not isinstance(self.activity, ExternalActivityClosure)
            or (has_native_name_requirement and self.native_name is None)
            or (not has_native_name_requirement and self.native_name is not None)
            or (self.native_name is not None and not self.native_name.strip())
        ):
            raise ValueError("material_unavailable_invalid")

    @property
    def request_identity(self) -> str:
        """
        Return the stable identity of the refused request.
        """

        return self.request.identity


MaterialOutcome: TypeAlias = ObservedMaterials | MaterialUnavailable
MaterialVerificationOutcome: TypeAlias = VerifiedMaterialBatch | MaterialUnavailable


class MaterialResponse(Protocol):
    """
    Observe material values against one immutable product binding.
    """

    @property
    def context(self) -> MaterialResponseContext:
        """
        Return the exact product context used by this response.
        """

        ...

    def observe(
        self,
        request: MaterialObservationRequest,
    ) -> MaterialOutcome:
        """
        Observe or refuse materials for one exact request.
        """

        ...


def material_observation_key(
    context: MaterialResponseContext,
    request: MaterialObservationRequest,
) -> str:
    """
    Derive the current-observation key from context and request.
    """

    identity = hashlib.sha256(
        encode_bytes(
            {
                "binding_reference": context.binding_reference.as_mapping(),
                "request": request.canonical_value(),
            }
        )
    ).hexdigest()
    return f"material_observation:sha256:{identity}"


def _observation_document(
    request: MaterialVerificationRequest,
    *,
    product_sample_reference: Reference,
    materials: tuple[VerifiedMaterial, ...],
) -> Document:
    return Document(
        MATERIAL_OBSERVATION_SCHEMA,
        {
            "materials": {
                f"material_{index:03d}": material.canonical_value()
                for index, material in enumerate(materials, start=1)
            },
            "product_sample_reference": (product_sample_reference.as_mapping()),
            "request": request.canonical_value(),
        },
    )


def _restore_request(value: object) -> MaterialVerificationRequest:
    mapping = _mapping(value, "material_verification_request_invalid")
    if set(mapping) != {
        "binding_reference",
        "observation_request",
        "selections",
    }:
        raise ValueError("material_verification_request_invalid")
    request_values = _mapping(
        mapping["observation_request"],
        "material_verification_request_invalid",
    )
    if set(request_values) != {"families", "wavelength_nm"}:
        raise ValueError("material_verification_request_invalid")
    selection_values = _indexed_values(
        mapping["selections"],
        "selection",
        "material_verification_request_invalid",
    )
    return MaterialVerificationRequest(
        observation_request=MaterialObservationRequest(
            families=tuple(
                _text(
                    family,
                    "material_verification_request_invalid",
                )
                for family in _sequence(
                    request_values["families"],
                    "material_verification_request_invalid",
                )
            ),
            wavelength_nm=_positive_int(
                request_values["wavelength_nm"],
                "material_verification_request_invalid",
            ),
        ),
        binding_reference=Reference.from_mapping(
            _mapping(
                mapping["binding_reference"],
                "material_verification_request_invalid",
            )
        ),
        selections=tuple(_restore_selection(value) for value in selection_values),
    )


def _restore_selection(value: object) -> AdmittedSolverMaterial:
    mapping = _mapping(value, "material_observation_invalid")
    if set(mapping) != {"material", "reference"}:
        raise ValueError("material_observation_invalid")
    material_values = _mapping(
        mapping["material"],
        "material_observation_invalid",
    )
    material = SolverMaterial.decode_document_bytes(
        Document(
            "metacraft.material.solver_material",
            dict(material_values),
        ).to_bytes()
    )
    return AdmittedSolverMaterial(
        material=material,
        reference=Reference.from_mapping(
            _mapping(
                mapping["reference"],
                "material_observation_invalid",
            )
        ),
    )


def _restore_material(value: object) -> VerifiedMaterial:
    mapping = _mapping(value, "material_observation_invalid")
    if set(mapping) != {
        "extinction_coefficient",
        "family",
        "native_name",
        "refractive_index",
    }:
        raise ValueError("material_observation_invalid")
    return VerifiedMaterial(
        family=_text(mapping["family"], "material_observation_invalid"),
        native_name=_text(
            mapping["native_name"],
            "material_observation_invalid",
        ),
        refractive_index=_decimal_text(
            mapping["refractive_index"],
            "material_observation_invalid",
        ),
        extinction_coefficient=_decimal_text(
            mapping["extinction_coefficient"],
            "material_observation_invalid",
        ),
    )


def _mapping(value: object, reason: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(reason)
    return value


def _sequence(value: object, reason: str) -> tuple[object, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(reason)
    return tuple(value)


def _indexed_values(
    value: object,
    prefix: str,
    reason: str,
) -> tuple[object, ...]:
    mapping = _mapping(value, reason)
    expected = tuple(f"{prefix}_{index:03d}" for index in range(1, len(mapping) + 1))
    if tuple(mapping) != expected:
        raise ValueError(reason)
    return tuple(mapping[key] for key in expected)


def _positive_int(value: object, reason: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(reason)
    return value


def _text(value: object, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    return value


def _decimal_text(value: object, reason: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(reason)
    try:
        return Decimal(value)
    except ArithmeticError as error:
        raise ValueError(reason) from error
