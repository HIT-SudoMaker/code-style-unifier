from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from ...authority import Document, Reference
from ...authority.reference import reference_matches
from ...materials import MaterialObservationRequest, ObservedMaterials


MATERIAL_BINDING_SCHEMA = "metacraft.science.metalens.material_binding"


def validate_material_observation(
    request: MaterialObservationRequest,
    outcome: ObservedMaterials,
    *,
    expected_binding_reference: Reference,
) -> None:
    """
    Bind one material outcome to its exact request and solver realization.
    """

    expected_families = tuple(dict.fromkeys(request.families))
    if (
        outcome.request_identity != request.identity
        or outcome.request.observation_request != request
        or tuple(selection.material.family for selection in outcome.selections)
        != expected_families
        or tuple(material.family for material in outcome.materials) != expected_families
    ):
        raise RuntimeError("material_outcome_request_mismatch")
    if outcome.solver_binding_reference != expected_binding_reference:
        raise RuntimeError("material_outcome_binding_mismatch")


@dataclass(frozen=True, slots=True)
class BoundMaterial:
    """
    Resolves one material family to exact optical values and identity.
    """

    family: str
    source: str
    native_name: str | None
    refractive_index: Decimal
    extinction_coefficient: Decimal

    def as_mapping(self) -> dict[str, object]:
        """
        Return exact optical values without binary float loss.
        """

        return {
            "extinction_coefficient": format(
                self.extinction_coefficient,
                "f",
            ),
            "family": self.family,
            "native_name": self.native_name,
            "refractive_index": format(self.refractive_index, "f"),
            "source": self.source,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MaterialBinding:
    """
    Binds one brief's material roles to one admitted optical sample.

    Identity follows brief, wavelength, and the exact admitted optical
    values; no route name is carried.
    """

    brief_identity: str
    wavelength_nm: int
    atom: BoundMaterial
    substrate: BoundMaterial
    solver_binding_reference: Reference
    sample_reference: Reference
    evidence_reference: Reference

    def document(self) -> Document:
        """
        Rebuild the exact material-binding document.
        """

        return Document(
            MATERIAL_BINDING_SCHEMA,
            {
                "atom": self.atom.as_mapping(),
                "brief_identity": self.brief_identity,
                "sample_reference": self.sample_reference.as_mapping(),
                "solver_binding_reference": (
                    self.solver_binding_reference.as_mapping()
                ),
                "substrate": self.substrate.as_mapping(),
                "wavelength_nm": self.wavelength_nm,
            },
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        evidence_reference: Reference,
    ) -> MaterialBinding:
        """
        Restore and verify one admitted material binding.
        """

        if document.schema_identifier != MATERIAL_BINDING_SCHEMA:
            raise ValueError("material_binding_schema_mismatch")
        values = document.values
        binding = cls(
            brief_identity=str(values["brief_identity"]),
            wavelength_nm=int(values["wavelength_nm"]),
            atom=_bound_material(values["atom"]),
            substrate=_bound_material(values["substrate"]),
            solver_binding_reference=Reference.from_mapping(
                values["solver_binding_reference"]
            ),
            sample_reference=Reference.from_mapping(values["sample_reference"]),
            evidence_reference=evidence_reference,
        )
        if not reference_matches(
            evidence_reference,
            binding.document().to_bytes(),
        ):
            raise ValueError("material_binding_reference_mismatch")
        return binding

    def references(self) -> tuple[Reference, ...]:
        """
        Return the exact solver and sample sources of this binding.
        """

        return self.solver_binding_reference, self.sample_reference

    def require_sample_match(
        self,
        *,
        sample_reference: Reference,
        solver_binding_reference: Reference | None,
        observed_wavelength_nm: int,
        observed_native_names: Mapping[str, str],
        observed_refractive_indices: Mapping[str, Decimal],
        observed_extinction_coefficients: Mapping[str, Decimal],
    ) -> None:
        """
        Reject a binding that changes any exact value from its cited sample.
        """

        if self.sample_reference != sample_reference:
            raise ValueError("material_binding_sample_reference_mismatch")
        if (
            solver_binding_reference is None
            or self.solver_binding_reference != solver_binding_reference
        ):
            raise ValueError("material_binding_solver_reference_mismatch")
        if self.wavelength_nm != observed_wavelength_nm:
            raise ValueError("material_binding_wavelength_mismatch")
        for role, material in (
            ("atom", self.atom),
            ("substrate", self.substrate),
        ):
            native_name = observed_native_names.get(material.family)
            if native_name is None:
                raise ValueError(f"material_binding_family_mismatch:{role}")
            if material.native_name != native_name:
                raise ValueError(f"material_binding_native_name_mismatch:{role}")
            if material.refractive_index != observed_refractive_indices.get(
                material.family
            ):
                raise ValueError(f"material_binding_refractive_index_mismatch:{role}")
            if material.extinction_coefficient != observed_extinction_coefficients.get(
                material.family
            ):
                raise ValueError(
                    f"material_binding_extinction_coefficient_mismatch:{role}"
                )


def _bound_material(value: object) -> BoundMaterial:
    if not isinstance(value, dict):
        raise ValueError("bound_material_invalid")
    return BoundMaterial(
        family=str(value["family"]),
        source=str(value["source"]),
        native_name=(
            None if value["native_name"] is None else str(value["native_name"])
        ),
        refractive_index=Decimal(str(value["refractive_index"])),
        extinction_coefficient=Decimal(str(value["extinction_coefficient"])),
    )
