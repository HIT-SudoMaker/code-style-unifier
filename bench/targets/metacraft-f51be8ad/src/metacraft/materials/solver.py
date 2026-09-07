from __future__ import annotations

from dataclasses import dataclass
import tomllib
from typing import Literal, cast

from ..authority import Document, Reference
from ..authority.reference import reference_matches
from .family import is_canonical_material_family


SOLVER_MATERIAL_SCHEMA = "metacraft.material.solver_material"
_LUMERICAL_FDTD = "lumerical fdtd"
_LIBRARY_FIELDS = {"materials", "solver"}
_MATERIAL_FIELDS = {"family", "native_name", "provenance"}
MaterialConfirmationFact = Literal["atom_material", "substrate_material"]


@dataclass(frozen=True, slots=True)
class MaterialConfirmationQuestion:
    """
    Asks whether one explicit library family is the user's intended fact.
    """

    fact: MaterialConfirmationFact
    candidate: str

    def __post_init__(self) -> None:
        """
        Keep the question vocabulary exact even before library lookup.
        """

        if self.fact not in {"atom_material", "substrate_material"}:
            raise ValueError("material_confirmation_fact_invalid")
        if not is_canonical_material_family(self.candidate):
            raise ValueError("material_confirmation_candidate_invalid")

    @property
    def wording(self) -> str:
        """
        Render the candidate as a question rather than a substitution.
        """

        return f"Did you mean {self.candidate}?"


@dataclass(frozen=True, slots=True)
class SolverMaterial:
    """
    Names one reviewed native record for one canonical material family.
    """

    solver: str
    family: str
    native_name: str
    provenance: str

    def __post_init__(self) -> None:
        """
        Preserve exact native text while rejecting invalid identities.
        """

        if not all(
            isinstance(value, str)
            for value in (
                self.solver,
                self.family,
                self.native_name,
                self.provenance,
            )
        ):
            raise ValueError("solver_material_invalid")
        if self.solver != _LUMERICAL_FDTD:
            raise ValueError("solver_material_solver_unsupported")
        if not is_canonical_material_family(self.family):
            raise ValueError("solver_material_family_invalid")
        if not self.native_name.strip():
            raise ValueError("solver_material_native_name_empty")
        if not self.provenance.strip():
            raise ValueError("solver_material_provenance_empty")

    def document(self) -> Document:
        """
        Encode this reviewed selection as one canonical document.
        """

        return Document(
            SOLVER_MATERIAL_SCHEMA,
            {
                "family": self.family,
                "native_name": self.native_name,
                "provenance": self.provenance,
                "solver": self.solver,
            },
        )

    @classmethod
    def decode_document_bytes(cls, source_bytes: bytes) -> SolverMaterial:
        """
        Restore one exact solver-material registration.
        """

        document = Document.from_bytes(source_bytes)
        if document.schema_identifier != SOLVER_MATERIAL_SCHEMA:
            raise ValueError("solver_material_schema_invalid")
        if set(document.values) != _MATERIAL_FIELDS | {"solver"}:
            raise ValueError("solver_material_fields_invalid")
        material = cls(
            solver=_require_text(
                document.values["solver"],
                "solver_material_document_invalid",
            ),
            family=_require_text(
                document.values["family"],
                "solver_material_document_invalid",
            ),
            native_name=_require_text(
                document.values["native_name"],
                "solver_material_document_invalid",
            ),
            provenance=_require_text(
                document.values["provenance"],
                "solver_material_document_invalid",
            ),
        )
        if material.document().to_bytes() != document.to_bytes():
            raise ValueError("solver_material_document_mismatch")
        return material


@dataclass(frozen=True, slots=True)
class AdmittedSolverMaterial:
    """
    Couples one reviewed solver material to its exact run reference.
    """

    material: SolverMaterial
    reference: Reference

    def __post_init__(self) -> None:
        """
        Refuse a reference that does not name this exact registration.
        """

        if not reference_matches(
            self.reference,
            self.material.document().to_bytes(),
        ):
            raise ValueError("solver_material_reference_mismatch")


@dataclass(frozen=True, slots=True)
class SolverMaterialLibrary:
    """
    Selects exact reviewed solver materials from validated project bytes.
    """

    solver: str
    _materials: tuple[SolverMaterial, ...]

    def __post_init__(self) -> None:
        if self.solver != _LUMERICAL_FDTD or any(
            material.solver != self.solver for material in self._materials
        ):
            raise ValueError("solver_material_library_invalid")

    @classmethod
    def decode_bytes(cls, source_bytes: bytes) -> SolverMaterialLibrary:
        """
        Parse one strict TOML library without opening a project file.
        """

        try:
            decoded = tomllib.loads(source_bytes.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            raise ValueError("solver_material_library_invalid") from error
        if set(decoded) != _LIBRARY_FIELDS:
            raise ValueError("solver_material_library_fields_invalid")
        solver = decoded["solver"]
        registrations = decoded["materials"]
        if not isinstance(solver, str) or not isinstance(registrations, list):
            raise ValueError("solver_material_library_invalid")
        if solver != _LUMERICAL_FDTD:
            raise ValueError("solver_material_solver_unsupported")

        materials: list[SolverMaterial] = []
        families: set[str] = set()
        for registration in registrations:
            if (
                not isinstance(registration, dict)
                or set(registration) != _MATERIAL_FIELDS
            ):
                raise ValueError("solver_material_fields_invalid")
            family = _require_text(
                registration["family"],
                "solver_material_library_invalid",
            )
            if family in families:
                raise ValueError("solver_material_family_duplicate")
            material = SolverMaterial(
                solver=solver,
                family=family,
                native_name=_require_text(
                    registration["native_name"],
                    "solver_material_library_invalid",
                ),
                provenance=_require_text(
                    registration["provenance"],
                    "solver_material_library_invalid",
                ),
            )
            families.add(family)
            materials.append(material)
        return cls(
            solver,
            tuple(sorted(materials, key=lambda item: item.family)),
        )

    def select(self, family: str) -> SolverMaterial | None:
        """
        Return one exact registration without interpreting its family.
        """

        return next(
            (material for material in self._materials if material.family == family),
            None,
        )

    def confirm_material_family(
        self,
        *,
        fact: str,
        candidate: str,
    ) -> MaterialConfirmationQuestion:
        """
        Frame one caller-proposed registered family for user confirmation.

        The library validates an exact candidate; it never searches, ranks,
        rewrites, or applies the candidate to a brief.
        """

        if fact not in {"atom_material", "substrate_material"}:
            raise ValueError("material_confirmation_fact_invalid")
        if not is_canonical_material_family(candidate):
            raise ValueError("material_confirmation_candidate_invalid")
        if self.select(candidate) is None:
            raise ValueError("material_confirmation_candidate_unregistered")
        return MaterialConfirmationQuestion(
            fact=cast(MaterialConfirmationFact, fact),
            candidate=candidate,
        )


def _require_text(value: object, finding: str) -> str:
    if not isinstance(value, str):
        raise ValueError(finding)
    return value
