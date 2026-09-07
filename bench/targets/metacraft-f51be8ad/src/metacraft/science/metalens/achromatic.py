from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import hashlib
import math
from typing import cast

import numpy
from numpy.typing import NDArray

from ...authority import Document, Reference
from ...authority.reference import reference_for, reference_matches
from ...canonical import encode_bytes
from ...external_activity import ExternalActivityOrigin
from ..periodic_response import (
    AdmittedPeriodicObservationIncomplete,
    AdmittedPeriodicPolarization,
    ObservedPeriodicPolarization,
    PeriodicMaterials,
    PeriodicPolarizationRequest,
    PeriodicPolarizationIncomplete,
    PeriodicObservationIncompleteReason,
    PeriodicResponseClosure,
    PeriodicReferenceSurfaceObservation,
    PeriodicWork,
    RectangularCrossSection,
    periodic_request_identity,
)
from ..result import EvidenceOrigin
from ..study import Task

from ...field import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)

from .brief import ContinuousBandSpectrum
from .aperture import Lattice
from .brief import ApertureFootprint
from .design import MetalensDesign
from .geometric_phase import (
    ComplexCoefficient,
    JonesResponse,
    PolarizationConvention,
    project_circular_channels,
)
from .focus import Focus, require_complete_focus
from .periodic_cell_evidence import validate_observed_batch


ACHROMATIC_TARGET_SCHEMA = "metacraft.science.metalens.achromatic_target"
RESPONSE_QUALIFICATION_PROFILE_REVIEW_SCHEMA = (
    "metacraft.science.metalens.response_qualification_profile_review"
)
SPECTRAL_MATERIAL_BINDING_SCHEMA = (
    "metacraft.science.metalens.spectral_material_binding"
)
RESPONSE_QUALIFICATION_PROFILE_SCHEMA = (
    "metacraft.science.metalens.response_qualification_profile"
)
SPECTRAL_STUDY_SPECIFICATION_SCHEMA = (
    "metacraft.science.metalens.spectral_study_specification"
)
SPECTRAL_CELL_STUDY_PLAN_SCHEMA = "metacraft.science.metalens.spectral_cell_study_plan"
SPECTRAL_CELL_SCREEN_SCHEMA = "metacraft.science.metalens.spectral_cell_screen"
SPECTRAL_JONES_LIBRARY_SCHEMA = "metacraft.science.metalens.spectral_jones_library"
QUALIFIED_SPECTRAL_LIBRARY_SCHEMA = (
    "metacraft.science.metalens.qualified_spectral_library"
)
ACHROMATIC_APERTURE_SCHEMA = "metacraft.science.metalens.achromatic_aperture"
BAND_VERIFICATION_EVIDENCE_SCHEMA = (
    "metacraft.science.metalens.band_verification_evidence"
)
POST_FREEZE_JONES_LIBRARY_SCHEMA = (
    "metacraft.science.metalens.post_freeze_jones_library"
)
SPECTRAL_FIELD_FAMILY_SCHEMA = "metacraft.science.metalens.spectral_field_family"
ACHROMATIC_FOCUS_SCHEMA = "metacraft.science.metalens.achromatic_focus"

__all__ = [
    "AchromaticTarget",
    "AchromaticAperture",
    "ApertureAdjacencyDiagnostics",
    "AchromaticFocus",
    "AchromaticFocusEntry",
    "AchromaticFocusSummary",
    "AchromaticFocusRoleSummary",
    "BAND_VERIFICATION_EVIDENCE_SCHEMA",
    "BandVerificationEvidence",
    "BandVerificationStatus",
    "POST_FREEZE_JONES_LIBRARY_SCHEMA",
    "PostFreezeJonesLibrary",
    "SpectralFieldEntry",
    "SpectralFieldFamily",
    "SpectralCellAssessment",
    "SpectralCellScreen",
    "SpectralCellStudyPlan",
    "SpectralCampaignStop",
    "SpectralEvidenceRequirement",
    "SpectralJonesLibrary",
    "SpectralJonesObservation",
    "SpectralLibraryQualification",
    "SpectralMaterialBinding",
    "SpectralMaterialPoint",
    "ResponseQualificationProfile",
    "SpectralStudySpecification",
    "SpectralQualificationStatus",
    "SpectralRectangle",
    "assign_continuous_achromatic_aperture",
    "achromatic_strategies",
    "form_achromatic_aperture_field",
    "form_achromatic_focus",
    "form_band_verification_evidence",
    "form_post_freeze_jones_library",
    "form_spectral_cell_study_plan",
    "form_spectral_study_specification",
    "form_spectral_cell_screen",
    "form_spectral_jones_library",
    "form_spectral_observations",
    "project_spectral_periodic_requests",
    "project_post_freeze_blind_requests",
    "project_spectral_reference_request",
    "qualify_spectral_jones_library",
    "require_spectral_material_binding",
    "spectral_wavelength_grid",
]

_LIGHT_SPEED_UM_PER_FS = Decimal("0.299792458")
_LIGHT_SPEED_NM_PER_FS = 299.792458
_PAPER_PERIOD_CEILING_NM = 400
_PAPER_HEIGHT_NM = 600


@dataclass(frozen=True, slots=True, kw_only=True)
class AchromaticTarget:
    """
    Own the fixed-focus spectral phase and delay requirement.
    """

    lower_wavelength_nm: int
    upper_wavelength_nm: int
    reference_wavelength_nm: int
    numerical_aperture: Decimal
    focal_length_um: Decimal
    required_relative_delay_fs: Decimal
    phase_convention: str

    def __post_init__(self) -> None:
        """
        Require a finite physical target and one explicit phase convention.
        """

        if (
            self.lower_wavelength_nm <= 0
            or self.upper_wavelength_nm <= self.lower_wavelength_nm
            or not (
                self.lower_wavelength_nm
                <= self.reference_wavelength_nm
                <= self.upper_wavelength_nm
            )
            or not self.numerical_aperture.is_finite()
            or not Decimal(0) < self.numerical_aperture < Decimal(1)
            or not self.focal_length_um.is_finite()
            or self.focal_length_um <= 0
            or not self.required_relative_delay_fs.is_finite()
            or self.required_relative_delay_fs <= 0
            or not self.phase_convention.strip()
        ):
            raise ValueError("achromatic_target_invalid")

    @classmethod
    def from_design(cls, design: MetalensDesign) -> AchromaticTarget:
        """
        Derive the method-owned gauge and exact delay-span requirement.
        """

        spectrum = design.operating_spectrum
        if not isinstance(spectrum, ContinuousBandSpectrum):
            raise ValueError("continuous_spectrum_required")
        handedness = design.incident_polarization.handedness
        if handedness not in {"left", "right"}:
            raise ValueError("achromatic_circular_polarization_required")
        path_difference_um = design.focal_length_um * (
            Decimal(1) / (Decimal(1) - design.numerical_aperture**2).sqrt() - Decimal(1)
        )
        return cls(
            lower_wavelength_nm=spectrum.lower_wavelength_nm,
            upper_wavelength_nm=spectrum.upper_wavelength_nm,
            reference_wavelength_nm=(
                spectrum.lower_wavelength_nm + spectrum.upper_wavelength_nm
            )
            // 2,
            numerical_aperture=design.numerical_aperture,
            focal_length_um=design.focal_length_um,
            required_relative_delay_fs=(path_difference_um / _LIGHT_SPEED_UM_PER_FS),
            phase_convention=(
                "exp(-i omega t); converted PB phase "
                f"{2 * PolarizationConvention(circular_input=handedness).phase_sign:+d} theta"
            ),
        )

    def document(self) -> Document:
        """
        Encode the target under its exact scientific schema.
        """

        return Document(
            ACHROMATIC_TARGET_SCHEMA,
            {
                "focal_length_um": format(self.focal_length_um, "f"),
                "lower_wavelength_nm": self.lower_wavelength_nm,
                "numerical_aperture": format(self.numerical_aperture, "f"),
                "phase_convention": self.phase_convention,
                "reference_wavelength_nm": self.reference_wavelength_nm,
                "required_relative_delay_fs": format(
                    self.required_relative_delay_fs,
                    "f",
                ),
                "upper_wavelength_nm": self.upper_wavelength_nm,
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> AchromaticTarget:
        """
        Restore one exact target without repairing its Method choices.
        """

        if document.schema_identifier != ACHROMATIC_TARGET_SCHEMA:
            raise ValueError("achromatic_target_schema_mismatch")
        values = document.values
        if set(values) != {
            "focal_length_um",
            "lower_wavelength_nm",
            "numerical_aperture",
            "phase_convention",
            "reference_wavelength_nm",
            "required_relative_delay_fs",
            "upper_wavelength_nm",
        }:
            raise ValueError("achromatic_target_document_invalid")
        try:
            target = cls(
                lower_wavelength_nm=int(values["lower_wavelength_nm"]),
                upper_wavelength_nm=int(values["upper_wavelength_nm"]),
                reference_wavelength_nm=int(values["reference_wavelength_nm"]),
                numerical_aperture=Decimal(str(values["numerical_aperture"])),
                focal_length_um=Decimal(str(values["focal_length_um"])),
                required_relative_delay_fs=Decimal(
                    str(values["required_relative_delay_fs"])
                ),
                phase_convention=str(values["phase_convention"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("achromatic_target_document_invalid") from error
        if target.document().to_bytes() != document.to_bytes():
            raise ValueError("achromatic_target_document_mismatch")
        return target


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralMaterialPoint:
    """
    Retain both constituent indices at one exact spectral sample.
    """

    wavelength_nm: int
    atom_refractive_index: Decimal
    atom_extinction_coefficient: Decimal
    substrate_refractive_index: Decimal
    substrate_extinction_coefficient: Decimal

    def __post_init__(self) -> None:
        """
        Require one finite passive material pair at a positive wavelength.
        """

        values = (
            self.atom_refractive_index,
            self.atom_extinction_coefficient,
            self.substrate_refractive_index,
            self.substrate_extinction_coefficient,
        )
        if (
            type(self.wavelength_nm) is not int
            or self.wavelength_nm <= 0
            or any(not value.is_finite() for value in values)
            or self.atom_refractive_index <= 0
            or self.substrate_refractive_index <= 0
            or self.atom_extinction_coefficient < 0
            or self.substrate_extinction_coefficient < 0
        ):
            raise ValueError("spectral_material_point_invalid")

    def as_mapping(self) -> dict[str, object]:
        """
        Encode one material sample under its closed mapping contract.
        """

        atom_extinction = format(self.atom_extinction_coefficient, "f")
        atom_index = format(self.atom_refractive_index, "f")
        substrate_extinction = format(self.substrate_extinction_coefficient, "f")
        substrate_index = format(self.substrate_refractive_index, "f")
        return {
            "atom_extinction_coefficient": atom_extinction,
            "atom_refractive_index": atom_index,
            "substrate_extinction_coefficient": substrate_extinction,
            "substrate_refractive_index": substrate_index,
            "wavelength_nm": self.wavelength_nm,
        }

    @classmethod
    def from_mapping(cls, value: object) -> SpectralMaterialPoint:
        """
        Restore one exact material sample from a closed mapping.
        """

        values = _closed_mapping(
            value,
            {
                "atom_extinction_coefficient",
                "atom_refractive_index",
                "substrate_extinction_coefficient",
                "substrate_refractive_index",
                "wavelength_nm",
            },
            "spectral_material_point_invalid",
        )
        try:
            return cls(
                wavelength_nm=_integer(values["wavelength_nm"]),
                atom_refractive_index=Decimal(_text(values["atom_refractive_index"])),
                atom_extinction_coefficient=Decimal(
                    _text(values["atom_extinction_coefficient"])
                ),
                substrate_refractive_index=Decimal(
                    _text(values["substrate_refractive_index"])
                ),
                substrate_extinction_coefficient=Decimal(
                    _text(values["substrate_extinction_coefficient"])
                ),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("spectral_material_point_invalid") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralMaterialBinding:
    """
    Bind one complete material pair to the Method-owned spectral grid.
    """

    atom_family: str
    atom_native_name: str
    substrate_family: str
    substrate_native_name: str
    points: tuple[SpectralMaterialPoint, ...]
    solver_binding_reference: Reference
    source_references: tuple[Reference, ...]

    def __post_init__(self) -> None:
        """
        Require ordered spectral samples with exact provenance references.
        """

        wavelengths = tuple(point.wavelength_nm for point in self.points)
        if (
            not self.atom_family.strip()
            or not self.atom_native_name.strip()
            or not self.substrate_family.strip()
            or not self.substrate_native_name.strip()
            or not self.points
            or wavelengths != tuple(sorted(set(wavelengths)))
            or not self.source_references
            or len(self.source_references) != len(self.points)
            or len(set(self.source_references)) != len(self.source_references)
        ):
            raise ValueError("spectral_material_binding_invalid")

    def document(self) -> Document:
        return Document(
            SPECTRAL_MATERIAL_BINDING_SCHEMA,
            {
                "atom_family": self.atom_family,
                "atom_native_name": self.atom_native_name,
                "points": {
                    f"point_{index:03d}": point.as_mapping()
                    for index, point in enumerate(self.points, start=1)
                },
                "source_references": {
                    f"source_{index:03d}": reference.as_mapping()
                    for index, reference in enumerate(self.source_references, start=1)
                },
                "solver_binding_reference": self.solver_binding_reference.as_mapping(),
                "substrate_family": self.substrate_family,
                "substrate_native_name": self.substrate_native_name,
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> SpectralMaterialBinding:
        if document.schema_identifier != SPECTRAL_MATERIAL_BINDING_SCHEMA:
            raise ValueError("spectral_material_binding_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {
                "atom_family",
                "atom_native_name",
                "points",
                "source_references",
                "solver_binding_reference",
                "substrate_family",
                "substrate_native_name",
            },
            "spectral_material_binding_document_invalid",
        )
        try:
            binding = cls(
                atom_family=_text(values["atom_family"]),
                atom_native_name=_text(values["atom_native_name"]),
                substrate_family=_text(values["substrate_family"]),
                substrate_native_name=_text(values["substrate_native_name"]),
                points=tuple(
                    SpectralMaterialPoint.from_mapping(item)
                    for item in _indexed_values(values["points"], "point")
                ),
                source_references=tuple(
                    Reference.from_mapping(_mapping(item))
                    for item in _indexed_values(values["source_references"], "source")
                ),
                solver_binding_reference=Reference.from_mapping(
                    _mapping(values["solver_binding_reference"])
                ),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("spectral_material_binding_document_invalid") from error
        if binding.document().to_bytes() != document.to_bytes():
            raise ValueError("spectral_material_binding_document_mismatch")
        return binding


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralEvidenceRequirement:
    """
    Name an absent spectral fact without turning absence into refusal.
    """

    claim: str
    missing_wavelengths_nm: tuple[int, ...]
    reason: str

    def __post_init__(self) -> None:
        """
        Require one named claim and a canonical nonempty wavelength set.
        """

        if (
            not self.claim.strip()
            or not self.missing_wavelengths_nm
            or self.missing_wavelengths_nm
            != tuple(sorted(set(self.missing_wavelengths_nm)))
            or not self.reason.strip()
        ):
            raise ValueError("spectral_evidence_requirement_invalid")


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralCampaignStop:
    """Retain a pre-execution campaign-policy refusal without inventing evidence."""

    claim: str
    reason: str
    projected_work_count: int
    authorized_work_ceiling: int

    def __post_init__(self) -> None:
        if (
            not self.claim.strip()
            or not self.reason.strip()
            or self.projected_work_count <= 0
            or self.authorized_work_ceiling <= 0
            or self.projected_work_count <= self.authorized_work_ceiling
        ):
            raise ValueError("spectral_campaign_stop_invalid")


@dataclass(frozen=True, slots=True, kw_only=True)
class ResponseQualificationProfile:
    """Own every numerical gate used by the continuous spectral Method."""

    version: str
    provenance: tuple[str, ...]
    source_references: tuple[Reference, ...]
    minimum_reference_converted_power: Decimal
    minimum_full_band_converted_power: Decimal
    maximum_full_band_leakage_power: Decimal
    minimum_design_r_squared: Decimal
    maximum_interleaved_phase_residual_rad: Decimal
    maximum_reference_phase_gap_rad: Decimal
    maximum_dense_phase_residual_rad: Decimal
    maximum_phase_curvature_rad: Decimal

    def __post_init__(self) -> None:
        bounded = (
            self.minimum_reference_converted_power,
            self.minimum_full_band_converted_power,
            self.maximum_full_band_leakage_power,
            self.minimum_design_r_squared,
        )
        residuals = (
            self.maximum_interleaved_phase_residual_rad,
            self.maximum_reference_phase_gap_rad,
            self.maximum_dense_phase_residual_rad,
            self.maximum_phase_curvature_rad,
        )
        if (
            not self.version.strip()
            or not self.provenance
            or not self.source_references
            or len(set(self.source_references)) != len(self.source_references)
            or any(not item.strip() for item in self.provenance)
            or any(not item.is_finite() or not Decimal(0) <= item <= Decimal(1) for item in bounded)
            or any(not item.is_finite() or item < 0 for item in residuals)
        ):
            raise ValueError("response_qualification_profile_invalid")

    def document(self) -> Document:
        return Document(
            RESPONSE_QUALIFICATION_PROFILE_SCHEMA,
            {
                "maximum_dense_phase_residual_rad": format(self.maximum_dense_phase_residual_rad, "f"),
                "maximum_full_band_leakage_power": format(self.maximum_full_band_leakage_power, "f"),
                "maximum_interleaved_phase_residual_rad": format(self.maximum_interleaved_phase_residual_rad, "f"),
                "maximum_phase_curvature_rad": format(self.maximum_phase_curvature_rad, "f"),
                "maximum_reference_phase_gap_rad": format(self.maximum_reference_phase_gap_rad, "f"),
                "minimum_design_r_squared": format(self.minimum_design_r_squared, "f"),
                "minimum_full_band_converted_power": format(self.minimum_full_band_converted_power, "f"),
                "minimum_reference_converted_power": format(self.minimum_reference_converted_power, "f"),
                "provenance": list(self.provenance),
                "source_references": [
                    item.as_mapping() for item in self.source_references
                ],
                "version": self.version,
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> ResponseQualificationProfile:
        if document.schema_identifier != RESPONSE_QUALIFICATION_PROFILE_SCHEMA:
            raise ValueError("response_qualification_profile_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {
                "maximum_dense_phase_residual_rad",
                "maximum_full_band_leakage_power",
                "maximum_interleaved_phase_residual_rad",
                "maximum_phase_curvature_rad",
                "maximum_reference_phase_gap_rad",
                "minimum_design_r_squared",
                "minimum_full_band_converted_power",
                "minimum_reference_converted_power",
                "provenance",
                "source_references",
                "version",
            },
            "response_qualification_profile_document_invalid",
        )
        try:
            profile = cls(
                version=_text(values["version"]),
                provenance=tuple(_text(item) for item in _sequence(values["provenance"])),
                source_references=tuple(
                    Reference.from_mapping(_mapping(item))
                    for item in _sequence(values["source_references"])
                ),
                minimum_reference_converted_power=Decimal(_text(values["minimum_reference_converted_power"])),
                minimum_full_band_converted_power=Decimal(_text(values["minimum_full_band_converted_power"])),
                maximum_full_band_leakage_power=Decimal(_text(values["maximum_full_band_leakage_power"])),
                minimum_design_r_squared=Decimal(_text(values["minimum_design_r_squared"])),
                maximum_interleaved_phase_residual_rad=Decimal(_text(values["maximum_interleaved_phase_residual_rad"])),
                maximum_reference_phase_gap_rad=Decimal(_text(values["maximum_reference_phase_gap_rad"])),
                maximum_dense_phase_residual_rad=Decimal(_text(values["maximum_dense_phase_residual_rad"])),
                maximum_phase_curvature_rad=Decimal(_text(values["maximum_phase_curvature_rad"])),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("response_qualification_profile_document_invalid") from error
        if profile.document().to_bytes() != document.to_bytes():
            raise ValueError("response_qualification_profile_document_mismatch")
        return profile


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralStudySpecification:
    """Freeze the provenance, wavelength roles, geometry extent, and budget."""

    version: str
    provenance: tuple[str, ...]
    preferred_atom_family: str
    period_ceiling_nm: int
    height_nm: int
    minimum_feature_nm: int
    maximum_feature_nm: int
    dimension_step_nm: int
    design_wavelengths_nm: tuple[int, ...]
    holdout_wavelengths_nm: tuple[int, ...]
    blind_verification_wavelengths_nm: tuple[int, ...]
    qualification_profile_reference: Reference
    assignment_policy: str
    authorized_work_ceiling: int

    def __post_init__(self) -> None:
        roles = (
            *self.design_wavelengths_nm,
            *self.holdout_wavelengths_nm,
            *self.blind_verification_wavelengths_nm,
        )
        if (
            not self.version.strip()
            or not self.provenance
            or not self.preferred_atom_family.strip()
            or self.period_ceiling_nm <= 0
            or self.height_nm <= 0
            or self.dimension_step_nm <= 0
            or self.minimum_feature_nm <= 0
            or self.maximum_feature_nm <= self.minimum_feature_nm
            or not self.design_wavelengths_nm
            or not self.holdout_wavelengths_nm
            or not self.blind_verification_wavelengths_nm
            or len(roles) != len(set(roles))
            or not self.assignment_policy.strip()
            or self.authorized_work_ceiling <= 0
        ):
            raise ValueError("spectral_study_specification_invalid")
        if self.full_band_wavelengths_nm != tuple(range(min(roles), max(roles) + 1, 5)):
            raise ValueError("spectral_study_specification_grid_invalid")

    @property
    def full_band_wavelengths_nm(self) -> tuple[int, ...]:
        return tuple(sorted((*self.design_wavelengths_nm, *self.holdout_wavelengths_nm, *self.blind_verification_wavelengths_nm)))

    @property
    def geometry_count(self) -> int:
        count = (self.maximum_feature_nm - self.minimum_feature_nm) // self.dimension_step_nm + 1
        return count * (count - 1) // 2

    @property
    def maximum_reference_work_count(self) -> int:
        return self.geometry_count * 2

    @property
    def maximum_candidate_followup_work_count(self) -> int:
        return self.geometry_count * 8 * 2

    @property
    def maximum_post_freeze_work_count(self) -> int:
        return self.geometry_count * len(self.blind_verification_wavelengths_nm) * 2

    @property
    def maximum_work_count(self) -> int:
        return self.maximum_reference_work_count + self.maximum_candidate_followup_work_count + self.maximum_post_freeze_work_count

    def document(self) -> Document:
        return Document(
            SPECTRAL_STUDY_SPECIFICATION_SCHEMA,
            {
                "assignment_policy": self.assignment_policy,
                "authorized_work_ceiling": self.authorized_work_ceiling,
                "blind_verification_wavelengths_nm": list(self.blind_verification_wavelengths_nm),
                "design_wavelengths_nm": list(self.design_wavelengths_nm),
                "dimension_step_nm": self.dimension_step_nm,
                "height_nm": self.height_nm,
                "holdout_wavelengths_nm": list(self.holdout_wavelengths_nm),
                "maximum_candidate_followup_work_count": self.maximum_candidate_followup_work_count,
                "maximum_feature_nm": self.maximum_feature_nm,
                "maximum_post_freeze_work_count": self.maximum_post_freeze_work_count,
                "maximum_reference_work_count": self.maximum_reference_work_count,
                "maximum_work_count": self.maximum_work_count,
                "period_ceiling_nm": self.period_ceiling_nm,
                "preferred_atom_family": self.preferred_atom_family,
                "provenance": list(self.provenance),
                "qualification_profile_reference": self.qualification_profile_reference.as_mapping(),
                "minimum_feature_nm": self.minimum_feature_nm,
                "version": self.version,
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> SpectralStudySpecification:
        if document.schema_identifier != SPECTRAL_STUDY_SPECIFICATION_SCHEMA:
            raise ValueError("spectral_study_specification_schema_mismatch")
        values = document.values
        try:
            specification = cls(
                version=_text(values["version"]),
                provenance=tuple(_text(item) for item in _sequence(values["provenance"])),
                preferred_atom_family=_text(values["preferred_atom_family"]),
                period_ceiling_nm=_integer(values["period_ceiling_nm"]),
                height_nm=_integer(values["height_nm"]),
                minimum_feature_nm=_integer(values["minimum_feature_nm"]),
                maximum_feature_nm=_integer(values["maximum_feature_nm"]),
                dimension_step_nm=_integer(values["dimension_step_nm"]),
                design_wavelengths_nm=tuple(_integer(item) for item in _sequence(values["design_wavelengths_nm"])),
                holdout_wavelengths_nm=tuple(_integer(item) for item in _sequence(values["holdout_wavelengths_nm"])),
                blind_verification_wavelengths_nm=tuple(_integer(item) for item in _sequence(values["blind_verification_wavelengths_nm"])),
                qualification_profile_reference=Reference.from_mapping(_mapping(values["qualification_profile_reference"])),
                assignment_policy=_text(values["assignment_policy"]),
                authorized_work_ceiling=_integer(values["authorized_work_ceiling"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("spectral_study_specification_document_invalid") from error
        if specification.document().to_bytes() != document.to_bytes():
            raise ValueError("spectral_study_specification_document_mismatch")
        return specification


def form_spectral_study_specification(
    target: AchromaticTarget,
    *,
    qualification_profile_reference: Reference,
) -> SpectralStudySpecification:
    design, holdout = spectral_wavelength_grid(target)
    dense = tuple(range(target.lower_wavelength_nm, target.upper_wavelength_nm + 1, 5))
    if dense != tuple(range(470, 591, 5)):
        raise ValueError("continuous_band_sampling_unsupported")
    blind = tuple(item for item in dense if item not in {*design, *holdout})
    return SpectralStudySpecification(
        version="visible-single-rectangle-campaign-v1",
        provenance=(
            "ADR 0028 continuous PB and spectral response",
            "reviewed TiO2 rectangular-fin first slice",
        ),
        preferred_atom_family="amorphous titanium dioxide",
        period_ceiling_nm=320,
        height_nm=600,
        minimum_feature_nm=80,
        maximum_feature_nm=240,
        dimension_step_nm=10,
        design_wavelengths_nm=design,
        holdout_wavelengths_nm=holdout,
        blind_verification_wavelengths_nm=blind,
        qualification_profile_reference=qualification_profile_reference,
        assignment_policy=(
            "minimum absolute relative-delay error; maximum converted power; "
            "minimum interleaved residual; lexical geometry"
        ),
        authorized_work_ceiling=6800,
    )


def spectral_wavelength_grid(
    target: AchromaticTarget,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """
    Derive disjoint design and holdout samples from one continuous band.
    """

    lower = target.lower_wavelength_nm
    upper = target.upper_wavelength_nm
    span = upper - lower
    design = tuple((lower * (4 - index) + upper * index + 2) // 4 for index in range(5))
    holdout = tuple(
        (lower * (8 - index) + upper * index + 4) // 8 for index in (1, 3, 5, 7)
    )
    if span < 8 or len(set((*design, *holdout))) != 9:
        raise ValueError("continuous_band_sampling_unsupported")
    return design, holdout


def require_spectral_material_binding(
    target: AchromaticTarget,
    binding: SpectralMaterialBinding,
    *,
    specification: SpectralStudySpecification | None = None,
) -> SpectralMaterialBinding | SpectralEvidenceRequirement:
    """
    Require exact material values at every design and blind holdout wavelength.
    """

    if specification is None:
        return SpectralEvidenceRequirement(
            claim="spectral_study_specification",
            missing_wavelengths_nm=(target.reference_wavelength_nm,),
            reason="response_qualification_profile_missing",
        )
    observed = {point.wavelength_nm for point in binding.points}
    missing = tuple(
        sorted(
            wavelength
            for wavelength in specification.full_band_wavelengths_nm
            if wavelength not in observed
        )
    )
    if missing:
        return SpectralEvidenceRequirement(
            claim="spectral_material_binding",
            missing_wavelengths_nm=missing,
            reason="spectral_material_samples_incomplete",
        )
    return binding


@dataclass(frozen=True, slots=True, order=True)
class SpectralRectangle:
    """
    Name one primitive anisotropic fin in the square-cell template.
    """

    short_side_nm: int
    long_side_nm: int

    def __post_init__(self) -> None:
        """
        Require one positive anisotropic rectangular cross section.
        """

        if (
            type(self.short_side_nm) is not int
            or type(self.long_side_nm) is not int
            or self.short_side_nm <= 0
            or self.long_side_nm <= self.short_side_nm
        ):
            raise ValueError("spectral_rectangle_invalid")

    def as_mapping(self) -> dict[str, int]:
        """
        Encode the rectangle under its closed mapping contract.
        """

        return {
            "long_side_nm": self.long_side_nm,
            "short_side_nm": self.short_side_nm,
        }

    @classmethod
    def from_mapping(cls, value: object) -> SpectralRectangle:
        """
        Restore one exact rectangle from a closed mapping.
        """

        values = _closed_mapping(
            value,
            {"long_side_nm", "short_side_nm"},
            "spectral_rectangle_invalid",
        )
        try:
            return cls(
                short_side_nm=_integer(values["short_side_nm"]),
                long_side_nm=_integer(values["long_side_nm"]),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("spectral_rectangle_invalid") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralCellStudyPlan:
    """
    Own one square-period, single-rectangle, bounded two-stage work extent.
    """

    lower_wavelength_nm: int
    upper_wavelength_nm: int
    design_wavelengths_nm: tuple[int, ...]
    holdout_wavelengths_nm: tuple[int, ...]
    reference_wavelength_nm: int
    period_nm: int
    height_nm: int
    geometries: tuple[SpectralRectangle, ...]
    material_binding_reference: Reference
    specification_reference: Reference
    qualification_profile_reference: Reference
    blind_verification_wavelengths_nm: tuple[int, ...]
    input_bases: tuple[str, str] = ("x", "y")
    template: str = "single rectangular fin in square periodic cell"

    def __post_init__(self) -> None:
        """
        Require disjoint grids, bounded work, and one exact material binding.
        """

        all_wavelengths = (
            *self.design_wavelengths_nm,
            *self.holdout_wavelengths_nm,
            *self.blind_verification_wavelengths_nm,
        )
        if (
            self.lower_wavelength_nm <= 0
            or self.upper_wavelength_nm <= self.lower_wavelength_nm
            or not self.design_wavelengths_nm
            or not self.holdout_wavelengths_nm
            or not self.blind_verification_wavelengths_nm
            or len(set(all_wavelengths)) != len(all_wavelengths)
            or min(all_wavelengths) < self.lower_wavelength_nm
            or max(all_wavelengths) > self.upper_wavelength_nm
            or self.reference_wavelength_nm not in self.design_wavelengths_nm
            or self.period_nm <= 0
            or self.height_nm <= 0
            or not self.geometries
            or len(set(self.geometries)) != len(self.geometries)
            or any(
                geometry.long_side_nm >= self.period_nm for geometry in self.geometries
            )
            or self.input_bases != ("x", "y")
            or self.template != "single rectangular fin in square periodic cell"
        ):
            raise ValueError("spectral_cell_study_plan_invalid")

    @property
    def wavelengths_nm(self) -> tuple[int, ...]:
        """
        Return the canonical union of design and holdout wavelengths.
        """

        return tuple(
            sorted((*self.design_wavelengths_nm, *self.holdout_wavelengths_nm))
        )

    @property
    def full_band_wavelengths_nm(self) -> tuple[int, ...]:
        """Return all predeclared roles without making blind samples candidates."""

        return tuple(sorted((*self.wavelengths_nm, *self.blind_verification_wavelengths_nm)))

    @property
    def reference_screen_work_count(self) -> int:
        """
        Count the bounded reference-wavelength polarization works.
        """

        return len(self.geometries) * len(self.input_bases)

    @property
    def maximum_followup_work_count(self) -> int:
        """
        Count the largest screened non-reference work extent.
        """

        return (
            len(self.geometries)
            * (len(self.wavelengths_nm) - 1)
            * len(self.input_bases)
        )

    @property
    def maximum_work_count(self) -> int:
        """
        Count the complete two-stage work ceiling.
        """

        return (
            self.reference_screen_work_count
            + self.maximum_followup_work_count
            + self.maximum_post_freeze_work_count
        )

    @property
    def maximum_post_freeze_work_count(self) -> int:
        return (
            len(self.geometries)
            * len(self.blind_verification_wavelengths_nm)
            * len(self.input_bases)
        )

    def document(self) -> Document:
        """
        Encode the plan under its exact scientific schema.
        """

        return Document(
            SPECTRAL_CELL_STUDY_PLAN_SCHEMA,
            {
                "design_wavelengths_nm": list(self.design_wavelengths_nm),
                "blind_verification_wavelengths_nm": list(
                    self.blind_verification_wavelengths_nm
                ),
                "geometries": [geometry.as_mapping() for geometry in self.geometries],
                "height_nm": self.height_nm,
                "holdout_wavelengths_nm": list(self.holdout_wavelengths_nm),
                "input_bases": list(self.input_bases),
                "lower_wavelength_nm": self.lower_wavelength_nm,
                "material_binding_reference": self.material_binding_reference.as_mapping(),
                "maximum_followup_work_count": self.maximum_followup_work_count,
                "maximum_post_freeze_work_count": self.maximum_post_freeze_work_count,
                "maximum_work_count": self.maximum_work_count,
                "period_nm": self.period_nm,
                "reference_wavelength_nm": self.reference_wavelength_nm,
                "reference_screen_work_count": self.reference_screen_work_count,
                "qualification_profile_reference": (
                    self.qualification_profile_reference.as_mapping()
                ),
                "specification_reference": self.specification_reference.as_mapping(),
                "template": self.template,
                "upper_wavelength_nm": self.upper_wavelength_nm,
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> SpectralCellStudyPlan:
        if document.schema_identifier != SPECTRAL_CELL_STUDY_PLAN_SCHEMA:
            raise ValueError("spectral_cell_study_plan_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {
                "design_wavelengths_nm",
                "blind_verification_wavelengths_nm",
                "geometries",
                "height_nm",
                "holdout_wavelengths_nm",
                "input_bases",
                "lower_wavelength_nm",
                "material_binding_reference",
                "maximum_followup_work_count",
                "maximum_post_freeze_work_count",
                "maximum_work_count",
                "period_nm",
                "reference_wavelength_nm",
                "reference_screen_work_count",
                "qualification_profile_reference",
                "specification_reference",
                "template",
                "upper_wavelength_nm",
            },
            "spectral_cell_study_plan_document_invalid",
        )
        try:
            input_bases = tuple(
                _text(item) for item in _sequence(values["input_bases"])
            )
            if len(input_bases) != 2:
                raise ValueError("spectral_cell_study_plan_document_invalid")
            plan = cls(
                lower_wavelength_nm=_integer(values["lower_wavelength_nm"]),
                upper_wavelength_nm=_integer(values["upper_wavelength_nm"]),
                design_wavelengths_nm=tuple(
                    _integer(item)
                    for item in _sequence(values["design_wavelengths_nm"])
                ),
                holdout_wavelengths_nm=tuple(
                    _integer(item)
                    for item in _sequence(values["holdout_wavelengths_nm"])
                ),
                blind_verification_wavelengths_nm=tuple(
                    _integer(item)
                    for item in _sequence(values["blind_verification_wavelengths_nm"])
                ),
                period_nm=_integer(values["period_nm"]),
                reference_wavelength_nm=_integer(values["reference_wavelength_nm"]),
                height_nm=_integer(values["height_nm"]),
                geometries=tuple(
                    SpectralRectangle.from_mapping(item)
                    for item in _sequence(values["geometries"])
                ),
                material_binding_reference=Reference.from_mapping(
                    _mapping(values["material_binding_reference"])
                ),
                specification_reference=Reference.from_mapping(
                    _mapping(values["specification_reference"])
                ),
                qualification_profile_reference=Reference.from_mapping(
                    _mapping(values["qualification_profile_reference"])
                ),
                input_bases=(input_bases[0], input_bases[1]),
                template=_text(values["template"]),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("spectral_cell_study_plan_document_invalid") from error
        if (
            values["reference_screen_work_count"] != plan.reference_screen_work_count
            or values["maximum_followup_work_count"] != plan.maximum_followup_work_count
            or values["maximum_work_count"] != plan.maximum_work_count
            or values["maximum_post_freeze_work_count"]
            != plan.maximum_post_freeze_work_count
            or plan.document().to_bytes() != document.to_bytes()
        ):
            raise ValueError("spectral_cell_study_plan_document_mismatch")
        return plan


def form_spectral_cell_study_plan(
    target: AchromaticTarget,
    binding: SpectralMaterialBinding,
    *,
    material_binding_reference: Reference,
    dimension_step_nm: int,
    aspect_limit: int,
    specification: SpectralStudySpecification | None = None,
    specification_reference: Reference | None = None,
) -> SpectralCellStudyPlan | SpectralEvidenceRequirement | SpectralCampaignStop:
    """
    Compile the Chen seed into one locally order-safe square-cell plan.
    """

    if specification is None:
        return SpectralEvidenceRequirement(
            claim="spectral_study_specification",
            missing_wavelengths_nm=(target.reference_wavelength_nm,),
            reason="response_qualification_profile_missing",
        )
    expected_specification_reference = reference_for(specification.document().to_bytes())
    if specification_reference is None:
        specification_reference = expected_specification_reference
    if (
        specification_reference != expected_specification_reference
        or dimension_step_nm != specification.dimension_step_nm
    ):
        raise ValueError("spectral_study_specification_reference_mismatch")
    if specification.maximum_work_count > specification.authorized_work_ceiling:
        return SpectralCampaignStop(
            claim="spectral_cell_study_plan",
            reason="spectral_campaign_work_budget_exceeded",
            projected_work_count=specification.maximum_work_count,
            authorized_work_ceiling=specification.authorized_work_ceiling,
        )
    complete = require_spectral_material_binding(
        target,
        binding,
        specification=specification,
    )
    if isinstance(complete, SpectralEvidenceRequirement):
        return complete
    if not reference_matches(material_binding_reference, binding.document().to_bytes()):
        raise ValueError("spectral_material_binding_reference_mismatch")
    if dimension_step_nm <= 0 or aspect_limit <= 0:
        raise ValueError("spectral_fabrication_constraint_invalid")
    design = specification.design_wavelengths_nm
    holdout = specification.holdout_wavelengths_nm
    point_by_wavelength = {point.wavelength_nm: point for point in binding.points}
    order_limits = tuple(
        Decimal(wavelength) / point_by_wavelength[wavelength].substrate_refractive_index
        for wavelength in specification.full_band_wavelengths_nm
    )
    strict_limit = min(order_limits)
    period_nm = min(
        specification.period_ceiling_nm,
        int(strict_limit // Decimal(dimension_step_nm)) * dimension_step_nm,
    )
    while period_nm > 0 and any(
        Decimal(period_nm) * point_by_wavelength[wavelength].substrate_refractive_index
        >= Decimal(wavelength)
        for wavelength in specification.full_band_wavelengths_nm
    ):
        period_nm -= dimension_step_nm
    derived_minimum_feature_nm = (
        ((_PAPER_HEIGHT_NM + aspect_limit - 1) // aspect_limit + dimension_step_nm - 1)
        // dimension_step_nm
        * dimension_step_nm
    )
    minimum_feature_nm = max(
        derived_minimum_feature_nm,
        specification.minimum_feature_nm,
    )
    maximum_feature_nm = min(
        period_nm - minimum_feature_nm,
        specification.maximum_feature_nm,
    )
    legal = tuple(range(minimum_feature_nm, maximum_feature_nm + 1, dimension_step_nm))
    if period_nm <= 0 or len(legal) < 5:
        return SpectralEvidenceRequirement(
            claim="spectral_cell_study_plan",
            missing_wavelengths_nm=(target.reference_wavelength_nm,),
            reason="single_rectangle_fabrication_domain_empty",
        )
    geometries = tuple(
        SpectralRectangle(short_side_nm=short, long_side_nm=long)
        for index, short in enumerate(legal)
        for long in legal[index + 1 :]
    )
    return SpectralCellStudyPlan(
        lower_wavelength_nm=target.lower_wavelength_nm,
        upper_wavelength_nm=target.upper_wavelength_nm,
        design_wavelengths_nm=design,
        holdout_wavelengths_nm=holdout,
        blind_verification_wavelengths_nm=(
            specification.blind_verification_wavelengths_nm
        ),
        reference_wavelength_nm=target.reference_wavelength_nm,
        period_nm=period_nm,
        height_nm=specification.height_nm,
        geometries=geometries,
        material_binding_reference=material_binding_reference,
        specification_reference=specification_reference,
        qualification_profile_reference=(
            specification.qualification_profile_reference
        ),
    )


def project_spectral_periodic_requests(
    plan: SpectralCellStudyPlan,
    binding: SpectralMaterialBinding,
    screen: SpectralCellScreen,
    *,
    task: Task,
) -> tuple[PeriodicPolarizationRequest, ...]:
    """
    Project only screened cells into non-reference spectral requests.
    """

    plan_reference = reference_for(plan.document().to_bytes())
    screen_reference = reference_for(screen.document().to_bytes())
    if not reference_matches(
        plan.material_binding_reference,
        binding.document().to_bytes(),
    ):
        raise ValueError("spectral_plan_material_binding_mismatch")
    if (
        task.claim != "spectral_jones_library"
        or task.method != "observe_spectral_jones"
        or task.binding_reference is None
        or task.capacity_scope is None
        or task.prerequisite_evidence != (plan_reference, screen_reference)
        or not screen.eligible_geometries
    ):
        raise ValueError("spectral_periodic_task_mismatch")
    assert task.binding_reference is not None
    _require_spectral_screen_context(
        plan,
        screen,
        solver_binding_reference=task.binding_reference,
    )
    points = {point.wavelength_nm: point for point in binding.points}
    sources = {
        point.wavelength_nm: source
        for point, source in zip(
            binding.points,
            binding.source_references,
            strict=True,
        )
    }
    if set(points) != set(plan.full_band_wavelengths_nm):
        raise ValueError("spectral_periodic_material_grid_mismatch")
    requests = []
    for wavelength_nm in plan.wavelengths_nm:
        if wavelength_nm == plan.reference_wavelength_nm:
            continue
        point = points[wavelength_nm]
        material_source = sources[wavelength_nm]
        materials = PeriodicMaterials(
            atom_native_identity=binding.atom_native_name,
            atom_refractive_index=point.atom_refractive_index,
            atom_source_reference=material_source,
            substrate_native_identity=binding.substrate_native_name,
            substrate_refractive_index=point.substrate_refractive_index,
            substrate_source_reference=material_source,
        )
        items = tuple(
            _spectral_periodic_work(
                plan,
                geometry,
                wavelength_nm=wavelength_nm,
                basis=basis,
                materials=materials,
                material_source=material_source,
                plan_reference=plan_reference,
                task=task,
            )
            for geometry in screen.eligible_geometries
            for basis in plan.input_bases
        )
        requests.append(
            PeriodicPolarizationRequest(
                request_identity=periodic_request_identity(
                    "polarization",
                    tuple(item.work_identity for item in items),
                ),
                items=items,
            )
        )
    return tuple(requests)


def project_post_freeze_blind_requests(
    plan: SpectralCellStudyPlan,
    binding: SpectralMaterialBinding,
    aperture: AchromaticAperture,
    *,
    profile: ResponseQualificationProfile,
    task: Task,
) -> tuple[PeriodicPolarizationRequest, ...]:
    """Project the predeclared blind role only after one aperture freezes."""

    plan_reference = reference_for(plan.document().to_bytes())
    aperture_reference = reference_for(aperture.document().to_bytes())
    profile_reference = reference_for(profile.document().to_bytes())
    if (
        aperture.plan_reference != plan_reference
        or plan.qualification_profile_reference != profile_reference
        or not reference_matches(
            plan.material_binding_reference,
            binding.document().to_bytes(),
        )
        or task.claim != "post_freeze_jones_library"
        or task.method != "observe_post_freeze_jones"
        or task.schema != POST_FREEZE_JONES_LIBRARY_SCHEMA
        or task.prerequisite_evidence != (aperture_reference, profile_reference)
        or task.binding_reference is None
        or task.capacity_scope is None
    ):
        raise ValueError("post_freeze_band_verification_context_mismatch")
    points = {point.wavelength_nm: point for point in binding.points}
    sources = {
        point.wavelength_nm: source
        for point, source in zip(
            binding.points,
            binding.source_references,
            strict=True,
        )
    }
    if set(points) != set(plan.full_band_wavelengths_nm):
        raise ValueError("spectral_periodic_material_grid_mismatch")
    requests = []
    for wavelength_nm in plan.blind_verification_wavelengths_nm:
        point = points[wavelength_nm]
        material_source = sources[wavelength_nm]
        materials = PeriodicMaterials(
            atom_native_identity=binding.atom_native_name,
            atom_refractive_index=point.atom_refractive_index,
            atom_source_reference=material_source,
            substrate_native_identity=binding.substrate_native_name,
            substrate_refractive_index=point.substrate_refractive_index,
            substrate_source_reference=material_source,
        )
        items = tuple(
            _spectral_periodic_work(
                plan,
                geometry,
                wavelength_nm=wavelength_nm,
                basis=basis,
                materials=materials,
                material_source=material_source,
                plan_reference=plan_reference,
                task=task,
                extra_source_references=(aperture_reference, profile_reference),
            )
            for geometry in aperture.used_geometries
            for basis in plan.input_bases
        )
        requests.append(
            PeriodicPolarizationRequest(
                request_identity=periodic_request_identity(
                    "polarization",
                    tuple(item.work_identity for item in items),
                ),
                items=items,
            )
        )
    return tuple(requests)


def project_spectral_reference_request(
    plan: SpectralCellStudyPlan,
    binding: SpectralMaterialBinding,
    *,
    task: Task,
    lattice_reference: Reference | None = None,
) -> PeriodicPolarizationRequest:
    """
    Project the cheap reference-wavelength screen before full-band work.
    """

    plan_reference = reference_for(plan.document().to_bytes())
    if not reference_matches(
        plan.material_binding_reference,
        binding.document().to_bytes(),
    ):
        raise ValueError("spectral_plan_material_binding_mismatch")
    if (
        task.claim != "spectral_cell_screen"
        or task.method != "screen_spectral_cells"
        or task.schema != SPECTRAL_CELL_SCREEN_SCHEMA
        or task.binding_reference is None
        or task.capacity_scope is None
        or task.prerequisite_evidence
        != (
            (plan_reference,)
            if lattice_reference is None
            else (plan_reference, lattice_reference)
        )
    ):
        raise ValueError("spectral_reference_screen_task_mismatch")
    points = {point.wavelength_nm: point for point in binding.points}
    sources = {
        point.wavelength_nm: source
        for point, source in zip(
            binding.points,
            binding.source_references,
            strict=True,
        )
    }
    if set(points) != set(plan.full_band_wavelengths_nm):
        raise ValueError("spectral_periodic_material_grid_mismatch")
    wavelength_nm = plan.reference_wavelength_nm
    point = points[wavelength_nm]
    material_source = sources[wavelength_nm]
    materials = PeriodicMaterials(
        atom_native_identity=binding.atom_native_name,
        atom_refractive_index=point.atom_refractive_index,
        atom_source_reference=material_source,
        substrate_native_identity=binding.substrate_native_name,
        substrate_refractive_index=point.substrate_refractive_index,
        substrate_source_reference=material_source,
    )
    items = tuple(
        _spectral_periodic_work(
            plan,
            geometry,
            wavelength_nm=wavelength_nm,
            basis=basis,
            materials=materials,
            material_source=material_source,
            plan_reference=plan_reference,
            task=task,
        )
        for geometry in plan.geometries
        for basis in plan.input_bases
    )
    return PeriodicPolarizationRequest(
        request_identity=periodic_request_identity(
            "polarization",
            tuple(item.work_identity for item in items),
        ),
        items=items,
    )


def _spectral_periodic_work(
    plan: SpectralCellStudyPlan,
    geometry: SpectralRectangle,
    *,
    wavelength_nm: int,
    basis: str,
    materials: PeriodicMaterials,
    material_source: Reference,
    plan_reference: Reference,
    task: Task,
    extra_source_references: tuple[Reference, ...] = (),
) -> PeriodicWork:
    if basis not in {"x", "y"}:
        raise ValueError("spectral_periodic_basis_invalid")
    cell_identity = (
        f"rectangular-fin-height-{plan.height_nm:04d}nm-"
        f"length-{geometry.long_side_nm:04d}nm-"
        f"width-{geometry.short_side_nm:04d}nm"
    )
    identity = encode_bytes(
        {
            "basis": basis,
            "geometry": geometry.as_mapping(),
            "material_source": material_source,
            "plan": plan_reference,
            "task": task.identity,
            "wavelength_nm": wavelength_nm,
        }
    )
    assert task.binding_reference is not None
    assert task.capacity_scope is not None
    return PeriodicWork(
        cell_identity=cell_identity,
        work_identity="sha256:" + hashlib.sha256(identity).hexdigest(),
        observation_schema=task.schema,
        wavelength_nm=wavelength_nm,
        period_nm=plan.period_nm,
        height_nm=plan.height_nm,
        geometry=RectangularCrossSection(
            geometry.short_side_nm,
            geometry.long_side_nm,
        ),
        materials=materials,
        source_references=(
            plan_reference,
            material_source,
            *extra_source_references,
        ),
        binding_reference=task.binding_reference,
        capacity_scope=task.capacity_scope,
        input_basis=f"{basis} linear",
        output_basis="cartesian",
        order_regime="zeroth order",
    )


def form_spectral_jones_library(
    plan: SpectralCellStudyPlan,
    screen: SpectralCellScreen,
    requests: tuple[PeriodicPolarizationRequest, ...],
    outcomes: tuple[ObservedPeriodicPolarization, ...],
    *,
    convention: PolarizationConvention,
    solver_binding_reference: Reference,
) -> SpectralJonesLibrary:
    """
    Form one atomic spectral fact from exact wavelength batches.
    """

    followup_wavelengths = tuple(
        wavelength
        for wavelength in plan.wavelengths_nm
        if wavelength != plan.reference_wavelength_nm
    )
    if (
        len(requests) != len(followup_wavelengths)
        or len(outcomes) != len(requests)
        or not screen.eligible_geometries
    ):
        raise ValueError("spectral_periodic_batch_incomplete")
    _require_spectral_screen_context(
        plan,
        screen,
        solver_binding_reference=solver_binding_reference,
    )
    observations = [
        item
        for item in screen.observations
        if item.geometry in screen.eligible_geometries
    ]
    for wavelength_nm, request, outcome in zip(
        followup_wavelengths,
        requests,
        outcomes,
        strict=True,
    ):
        observations.extend(
            form_spectral_observations(
                screen.eligible_geometries,
                wavelength_nm=wavelength_nm,
                request=request,
                outcome=outcome,
                solver_binding_reference=solver_binding_reference,
            )
        )
    return SpectralJonesLibrary(
        plan_reference=reference_for(plan.document().to_bytes()),
        screen_reference=reference_for(screen.document().to_bytes()),
        solver_binding_reference=solver_binding_reference,
        selected_geometries=screen.eligible_geometries,
        observations=tuple(observations),
        convention=convention,
    )


def form_spectral_observations(
    geometries: tuple[SpectralRectangle, ...],
    *,
    wavelength_nm: int,
    request: PeriodicPolarizationRequest,
    outcome: ObservedPeriodicPolarization,
    solver_binding_reference: Reference,
) -> tuple[SpectralJonesObservation, ...]:
    validate_observed_batch(request, outcome)
    if any(
        work.wavelength_nm != wavelength_nm
        or work.binding_reference != solver_binding_reference
        for work in request.items
    ):
        raise ValueError("spectral_periodic_batch_context_mismatch")
    by_cell: dict[
        str,
        dict[str, tuple[PeriodicWork, AdmittedPeriodicPolarization]],
    ] = {}
    for work, admitted in zip(request.items, outcome.items, strict=True):
        basis = work.input_basis.removesuffix(" linear")
        if basis not in {"x", "y"}:
            raise ValueError("spectral_periodic_basis_invalid")
        if basis in by_cell.setdefault(work.cell_identity, {}):
            raise ValueError("spectral_periodic_basis_duplicate")
        by_cell[work.cell_identity][basis] = (work, admitted)
    if len(by_cell) != len(geometries) or any(
        set(pair) != {"x", "y"} for pair in by_cell.values()
    ):
        raise ValueError("spectral_periodic_geometry_incomplete")
    observations = []
    for geometry, pair in zip(geometries, by_cell.values(), strict=True):
        work_x, admitted_x = pair["x"]
        work_y, admitted_y = pair["y"]
        expected_geometry = RectangularCrossSection(
            geometry.short_side_nm,
            geometry.long_side_nm,
        )
        if work_x.geometry != expected_geometry or work_y.geometry != expected_geometry:
            raise ValueError("spectral_periodic_geometry_mismatch")
        observation_x = admitted_x.observation
        observation_y = admitted_y.observation
        if (
            observation_x.input_basis != "x"
            or observation_y.input_basis != "y"
            or observation_x.cell != observation_y.cell
            or observation_x.phase_planes != observation_y.phase_planes
        ):
            raise ValueError("spectral_periodic_jones_pair_mismatch")
        response = JonesResponse(
            output_x_from_input_x=ComplexCoefficient(
                real_part=observation_x.output_x.real_part,
                imaginary_part=observation_x.output_x.imaginary_part,
            ),
            output_y_from_input_x=ComplexCoefficient(
                real_part=observation_x.output_y.real_part,
                imaginary_part=observation_x.output_y.imaginary_part,
            ),
            output_x_from_input_y=ComplexCoefficient(
                real_part=observation_y.output_x.real_part,
                imaginary_part=observation_y.output_x.imaginary_part,
            ),
            output_y_from_input_y=ComplexCoefficient(
                real_part=observation_y.output_y.real_part,
                imaginary_part=observation_y.output_y.imaginary_part,
            ),
        )
        observations.append(
            SpectralJonesObservation(
                geometry=geometry,
                wavelength_nm=wavelength_nm,
                response=response,
                transmitted_power_per_squared_amplitude=(
                    _transmitted_power_per_squared_amplitude(
                        response,
                        observation_x.reference_surface,
                        observation_y.reference_surface,
                    )
                ),
                source_references=(
                    admitted_x.body_reference,
                    admitted_y.body_reference,
                ),
                execution_origin=_spectral_execution_origin(
                    admitted_x,
                    admitted_y,
                ),
            )
        )
    return tuple(observations)


def _spectral_execution_origin(
    x_observation: AdmittedPeriodicPolarization,
    y_observation: AdmittedPeriodicPolarization,
) -> EvidenceOrigin:
    origins = {x_observation.execution_origin, y_observation.execution_origin}
    if len(origins) != 1:
        raise ValueError("spectral_periodic_execution_origin_mismatch")
    origin = origins.pop()
    return (
        EvidenceOrigin.NATIVE
        if origin is ExternalActivityOrigin.NATIVE
        else EvidenceOrigin.SYNTHETIC
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralJonesObservation:
    """
    Retain one complete complex Jones matrix for one geometry and wavelength.
    """

    geometry: SpectralRectangle
    wavelength_nm: int
    response: JonesResponse
    transmitted_power_per_squared_amplitude: Decimal
    source_references: tuple[Reference, Reference]
    execution_origin: EvidenceOrigin = EvidenceOrigin.SYNTHETIC

    def __post_init__(self) -> None:
        """
        Require one physical normalization and two independent source facts.
        """

        if (
            type(self.wavelength_nm) is not int
            or self.wavelength_nm <= 0
            or type(self.transmitted_power_per_squared_amplitude) is not Decimal
            or not self.transmitted_power_per_squared_amplitude.is_finite()
            or self.transmitted_power_per_squared_amplitude <= 0
            or len(set(self.source_references)) != 2
            or not isinstance(self.execution_origin, EvidenceOrigin)
        ):
            raise ValueError("spectral_jones_observation_invalid")

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the spectral Jones observation with exact provenance.
        """

        return {
            "geometry": self.geometry.as_mapping(),
            "execution_origin": self.execution_origin.value,
            "response": _jones_mapping(self.response),
            "source_references": {
                "x": self.source_references[0].as_mapping(),
                "y": self.source_references[1].as_mapping(),
            },
            "transmitted_power_per_squared_amplitude": format(
                self.transmitted_power_per_squared_amplitude,
                "f",
            ),
            "wavelength_nm": self.wavelength_nm,
        }

    @classmethod
    def from_mapping(cls, value: object) -> SpectralJonesObservation:
        """
        Restore one exact spectral Jones observation.
        """

        values = _closed_mapping(
            value,
            {
                "geometry",
                "execution_origin",
                "response",
                "source_references",
                "transmitted_power_per_squared_amplitude",
                "wavelength_nm",
            },
            "spectral_jones_observation_invalid",
        )
        try:
            encoded_sources = _closed_mapping(
                values["source_references"],
                {"x", "y"},
                "spectral_jones_observation_invalid",
            )
            return cls(
                geometry=SpectralRectangle.from_mapping(values["geometry"]),
                execution_origin=EvidenceOrigin(_text(values["execution_origin"])),
                wavelength_nm=_integer(values["wavelength_nm"]),
                response=_jones_from_mapping(values["response"]),
                transmitted_power_per_squared_amplitude=Decimal(
                    _text(values["transmitted_power_per_squared_amplitude"])
                ),
                source_references=(
                    Reference.from_mapping(_mapping(encoded_sources["x"])),
                    Reference.from_mapping(_mapping(encoded_sources["y"])),
                ),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("spectral_jones_observation_invalid") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralCellIncompletion:
    """
    Retain why one reference-wavelength geometry remains unresolved.
    """

    geometry: SpectralRectangle
    work_identities: tuple[str, ...]
    reasons: tuple[PeriodicObservationIncompleteReason, ...]
    source_references: tuple[Reference, ...]

    def __post_init__(self) -> None:
        count = len(self.work_identities)
        if (
            count == 0
            or len(set(self.work_identities)) != count
            or len(self.reasons) != count
            or len(self.source_references) != count
            or any(not identity.strip() for identity in self.work_identities)
            or any(
                type(reason) is not PeriodicObservationIncompleteReason
                for reason in self.reasons
            )
            or len(set(self.source_references)) != count
        ):
            raise ValueError("spectral_cell_incompletion_invalid")

    def as_mapping(self) -> dict[str, object]:
        return {
            "geometry": self.geometry.as_mapping(),
            "reasons": [reason.value for reason in self.reasons],
            "source_references": [
                reference.as_mapping() for reference in self.source_references
            ],
            "work_identities": list(self.work_identities),
        }

    @classmethod
    def from_mapping(cls, value: object) -> SpectralCellIncompletion:
        values = _closed_mapping(
            value,
            {
                "geometry",
                "reasons",
                "source_references",
                "work_identities",
            },
            "spectral_cell_incompletion_invalid",
        )
        try:
            return cls(
                geometry=SpectralRectangle.from_mapping(values["geometry"]),
                work_identities=tuple(
                    _text(item) for item in _sequence(values["work_identities"])
                ),
                reasons=tuple(
                    PeriodicObservationIncompleteReason(_text(item))
                    for item in _sequence(values["reasons"])
                ),
                source_references=tuple(
                    Reference.from_mapping(_mapping(item))
                    for item in _sequence(values["source_references"])
                ),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("spectral_cell_incompletion_invalid") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralCellScreen:
    """
    Retain the reference-wavelength screen and its eligible geometries.
    """

    plan_reference: Reference
    solver_binding_reference: Reference
    profile_reference: Reference
    minimum_reference_converted_power: Decimal
    reference_wavelength_nm: int
    observations: tuple[SpectralJonesObservation, ...]
    eligible_geometries: tuple[SpectralRectangle, ...]
    filtered_geometries: tuple[SpectralRectangle, ...]
    incompletions: tuple[SpectralCellIncompletion, ...]
    convention: PolarizationConvention

    def __post_init__(self) -> None:
        """
        Recompute and require the exact eligible geometry sequence.
        """

        observed_geometries = tuple(item.geometry for item in self.observations)
        expected_eligible = tuple(
            item.geometry
            for item in self.observations
            if _converted_power(item, self.convention)
            >= float(self.minimum_reference_converted_power)
        )
        expected_filtered = tuple(
            item.geometry
            for item in self.observations
            if item.geometry not in expected_eligible
        )
        unresolved_geometries = tuple(item.geometry for item in self.incompletions)
        if (
            self.reference_wavelength_nm <= 0
            or not self.minimum_reference_converted_power.is_finite()
            or self.minimum_reference_converted_power < 0
            or (not self.observations and not self.incompletions)
            or len(set(observed_geometries)) != len(observed_geometries)
            or len(set(unresolved_geometries)) != len(unresolved_geometries)
            or set(observed_geometries) & set(unresolved_geometries)
            or any(
                item.wavelength_nm != self.reference_wavelength_nm
                for item in self.observations
            )
            or len(set(self.eligible_geometries)) != len(self.eligible_geometries)
            or self.eligible_geometries != expected_eligible
            or self.filtered_geometries != expected_filtered
        ):
            raise ValueError("spectral_cell_screen_invalid")

    @property
    def unresolved_geometries(self) -> tuple[SpectralRectangle, ...]:
        """
        Return geometries lacking a complete reference Jones pair.
        """

        return tuple(item.geometry for item in self.incompletions)

    def document(self) -> Document:
        return Document(
            SPECTRAL_CELL_SCREEN_SCHEMA,
            {
                "convention": self.convention.as_mapping(),
                "eligible_geometries": [
                    geometry.as_mapping() for geometry in self.eligible_geometries
                ],
                "filtered_geometries": [
                    geometry.as_mapping() for geometry in self.filtered_geometries
                ],
                "incompletions": {
                    f"incompletion_{index:03d}": item.as_mapping()
                    for index, item in enumerate(self.incompletions, start=1)
                },
                "observations": {
                    f"observation_{index:03d}": item.as_mapping()
                    for index, item in enumerate(self.observations, start=1)
                },
                "plan_reference": self.plan_reference.as_mapping(),
                "profile_reference": self.profile_reference.as_mapping(),
                "reference_wavelength_nm": self.reference_wavelength_nm,
                "solver_binding_reference": self.solver_binding_reference.as_mapping(),
                "minimum_reference_converted_power": format(
                    self.minimum_reference_converted_power, "f"
                ),
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> SpectralCellScreen:
        if document.schema_identifier != SPECTRAL_CELL_SCREEN_SCHEMA:
            raise ValueError("spectral_cell_screen_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {
                "convention",
                "eligible_geometries",
                "filtered_geometries",
                "incompletions",
                "observations",
                "plan_reference",
                "profile_reference",
                "reference_wavelength_nm",
                "solver_binding_reference",
                "minimum_reference_converted_power",
            },
            "spectral_cell_screen_document_invalid",
        )
        try:
            screen = cls(
                plan_reference=Reference.from_mapping(
                    _mapping(values["plan_reference"])
                ),
                solver_binding_reference=Reference.from_mapping(
                    _mapping(values["solver_binding_reference"])
                ),
                profile_reference=Reference.from_mapping(
                    _mapping(values["profile_reference"])
                ),
                minimum_reference_converted_power=Decimal(
                    _text(values["minimum_reference_converted_power"])
                ),
                reference_wavelength_nm=_integer(values["reference_wavelength_nm"]),
                observations=tuple(
                    SpectralJonesObservation.from_mapping(item)
                    for item in _indexed_values(values["observations"], "observation")
                ),
                eligible_geometries=tuple(
                    SpectralRectangle.from_mapping(item)
                    for item in _sequence(values["eligible_geometries"])
                ),
                filtered_geometries=tuple(
                    SpectralRectangle.from_mapping(item)
                    for item in _sequence(values["filtered_geometries"])
                ),
                incompletions=tuple(
                    SpectralCellIncompletion.from_mapping(item)
                    for item in _indexed_values(
                        values["incompletions"],
                        "incompletion",
                    )
                ),
                convention=_convention_from_mapping(values["convention"]),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("spectral_cell_screen_document_invalid") from error
        if screen.document().to_bytes() != document.to_bytes():
            raise ValueError("spectral_cell_screen_document_mismatch")
        return screen


def form_spectral_cell_screen(
    plan: SpectralCellStudyPlan,
    request: PeriodicPolarizationRequest,
    outcome: ObservedPeriodicPolarization | PeriodicPolarizationIncomplete,
    *,
    convention: PolarizationConvention,
    solver_binding_reference: Reference,
    profile: ResponseQualificationProfile,
    profile_reference: Reference,
) -> SpectralCellScreen:
    """
    Filter reference-wavelength cells before paying for full-band sweeps.
    """

    plan_reference = reference_for(plan.document().to_bytes())
    if (
        not reference_matches(profile_reference, profile.document().to_bytes())
        or plan.qualification_profile_reference != profile_reference
    ):
        raise ValueError("spectral_screen_profile_reference_mismatch")
    observations, incompletions = _partition_reference_outcome(
        plan,
        request,
        outcome,
        solver_binding_reference=solver_binding_reference,
    )
    eligible = tuple(
        item.geometry
        for item in observations
        if _converted_power(item, convention)
        >= float(profile.minimum_reference_converted_power)
    )
    filtered = tuple(
        item.geometry for item in observations if item.geometry not in eligible
    )
    return SpectralCellScreen(
        plan_reference=plan_reference,
        solver_binding_reference=solver_binding_reference,
        profile_reference=profile_reference,
        minimum_reference_converted_power=(
            profile.minimum_reference_converted_power
        ),
        reference_wavelength_nm=plan.reference_wavelength_nm,
        observations=observations,
        eligible_geometries=eligible,
        filtered_geometries=filtered,
        incompletions=incompletions,
        convention=convention,
    )


def _partition_reference_outcome(
    plan: SpectralCellStudyPlan,
    request: PeriodicPolarizationRequest,
    outcome: ObservedPeriodicPolarization | PeriodicPolarizationIncomplete,
    *,
    solver_binding_reference: Reference,
) -> tuple[
    tuple[SpectralJonesObservation, ...],
    tuple[SpectralCellIncompletion, ...],
]:
    if isinstance(outcome, ObservedPeriodicPolarization):
        return (
            form_spectral_observations(
                plan.geometries,
                wavelength_nm=plan.reference_wavelength_nm,
                request=request,
                outcome=outcome,
                solver_binding_reference=solver_binding_reference,
            ),
            (),
        )
    if outcome.request_identity != request.request_identity:
        raise ValueError("periodic_response_request_identity_mismatch")
    expected_identities = tuple(item.work_identity for item in request.items)
    completed_by_identity = {item.work_identity: item for item in outcome.items}
    incomplete_by_identity = {
        item.work_identity: item for item in outcome.incomplete_items
    }
    settled_identities = (
        *completed_by_identity,
        *incomplete_by_identity,
    )
    if len(set(settled_identities)) != len(settled_identities) or set(
        settled_identities
    ) != set(expected_identities):
        raise ValueError("spectral_periodic_batch_incomplete")
    complete_geometries: list[SpectralRectangle] = []
    complete_works: list[PeriodicWork] = []
    complete_items: list[AdmittedPeriodicPolarization] = []
    incompletions: list[SpectralCellIncompletion] = []
    for geometry in plan.geometries:
        expected = RectangularCrossSection(
            geometry.short_side_nm,
            geometry.long_side_nm,
        )
        works = tuple(item for item in request.items if item.geometry == expected)
        if len(works) != len(plan.input_bases):
            raise ValueError("spectral_periodic_geometry_incomplete")
        incomplete_items = tuple(
            incomplete_by_identity[item.work_identity]
            for item in works
            if item.work_identity in incomplete_by_identity
        )
        if incomplete_items:
            incompletions.append(
                SpectralCellIncompletion(
                    geometry=geometry,
                    work_identities=tuple(
                        item.work_identity for item in incomplete_items
                    ),
                    reasons=tuple(item.outcome.reason for item in incomplete_items),
                    source_references=tuple(
                        item.body_reference for item in incomplete_items
                    ),
                )
            )
            continue
        complete_geometries.append(geometry)
        complete_works.extend(works)
        complete_items.extend(
            completed_by_identity[item.work_identity] for item in works
        )
    if not complete_works:
        return (), tuple(incompletions)
    identity = periodic_request_identity(
        "polarization",
        tuple(item.work_identity for item in complete_works),
    )
    complete_request = PeriodicPolarizationRequest(
        request_identity=identity,
        items=tuple(complete_works),
    )
    complete_outcome = ObservedPeriodicPolarization(
        request_identity=identity,
        items=tuple(complete_items),
        closure=PeriodicResponseClosure(
            identity,
            outcome.closure.qualification,
            outcome.closure.observation,
        ),
    )
    return (
        form_spectral_observations(
            tuple(complete_geometries),
            wavelength_nm=plan.reference_wavelength_nm,
            request=complete_request,
            outcome=complete_outcome,
            solver_binding_reference=solver_binding_reference,
        ),
        tuple(incompletions),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralJonesLibrary:
    """
    Keep one atomic full-band Jones sweep under one exact plan and binding.
    """

    plan_reference: Reference
    screen_reference: Reference
    solver_binding_reference: Reference
    selected_geometries: tuple[SpectralRectangle, ...]
    observations: tuple[SpectralJonesObservation, ...]
    convention: PolarizationConvention

    def __post_init__(self) -> None:
        """
        Require one complete screened geometry-by-wavelength evidence matrix.
        """

        keys = tuple(
            (observation.geometry, observation.wavelength_nm)
            for observation in self.observations
        )
        if (
            not self.observations
            or not self.selected_geometries
            or len(set(self.selected_geometries)) != len(self.selected_geometries)
            or len(set(keys)) != len(keys)
            or any(
                observation.geometry not in self.selected_geometries
                for observation in self.observations
            )
            or len({item.execution_origin for item in self.observations}) != 1
        ):
            raise ValueError("spectral_jones_library_invalid")

    def document(self) -> Document:
        return Document(
            SPECTRAL_JONES_LIBRARY_SCHEMA,
            {
                "convention": self.convention.as_mapping(),
                "observations": {
                    f"observation_{index:03d}": item.as_mapping()
                    for index, item in enumerate(self.observations, start=1)
                },
                "plan_reference": self.plan_reference.as_mapping(),
                "screen_reference": self.screen_reference.as_mapping(),
                "selected_geometries": [
                    geometry.as_mapping() for geometry in self.selected_geometries
                ],
                "solver_binding_reference": self.solver_binding_reference.as_mapping(),
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> SpectralJonesLibrary:
        if document.schema_identifier != SPECTRAL_JONES_LIBRARY_SCHEMA:
            raise ValueError("spectral_jones_library_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {
                "convention",
                "observations",
                "plan_reference",
                "screen_reference",
                "selected_geometries",
                "solver_binding_reference",
            },
            "spectral_jones_library_document_invalid",
        )
        try:
            library = cls(
                plan_reference=Reference.from_mapping(
                    _mapping(values["plan_reference"])
                ),
                screen_reference=Reference.from_mapping(
                    _mapping(values["screen_reference"])
                ),
                solver_binding_reference=Reference.from_mapping(
                    _mapping(values["solver_binding_reference"])
                ),
                observations=tuple(
                    SpectralJonesObservation.from_mapping(item)
                    for item in _indexed_values(values["observations"], "observation")
                ),
                selected_geometries=tuple(
                    SpectralRectangle.from_mapping(item)
                    for item in _sequence(values["selected_geometries"])
                ),
                convention=_convention_from_mapping(values["convention"]),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("spectral_jones_library_document_invalid") from error
        if library.document().to_bytes() != document.to_bytes():
            raise ValueError("spectral_jones_library_document_mismatch")
        return library


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralCellAssessment:
    """
    Report one geometry's independently checked spectral behaviour.
    """

    geometry: SpectralRectangle
    relative_delay_fs: Decimal
    reference_phase_rad: Decimal
    design_r_squared: Decimal
    design_maximum_residual_rad: Decimal
    holdout_maximum_residual_rad: Decimal
    minimum_converted_power: Decimal
    maximum_leakage_power: Decimal
    is_eligible: bool
    ineligibility_reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """
        Require finite bounded spectral metrics for one geometry.
        """

        values = (
            self.relative_delay_fs,
            self.reference_phase_rad,
            self.design_r_squared,
            self.design_maximum_residual_rad,
            self.holdout_maximum_residual_rad,
            self.minimum_converted_power,
            self.maximum_leakage_power,
        )
        if (
            any(not value.is_finite() for value in values)
            or self.design_r_squared < 0
            or self.design_r_squared > 1
            or self.holdout_maximum_residual_rad < 0
            or self.design_maximum_residual_rad < 0
            or self.minimum_converted_power < 0
            or self.maximum_leakage_power < 0
            or self.is_eligible != (not self.ineligibility_reasons)
        ):
            raise ValueError("spectral_cell_assessment_invalid")

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the assessment under its closed mapping contract.
        """

        holdout_residual = format(self.holdout_maximum_residual_rad, "f")
        return {
            "design_r_squared": format(self.design_r_squared, "f"),
            "design_maximum_residual_rad": format(
                self.design_maximum_residual_rad, "f"
            ),
            "geometry": self.geometry.as_mapping(),
            "holdout_maximum_residual_rad": holdout_residual,
            "minimum_converted_power": format(self.minimum_converted_power, "f"),
            "maximum_leakage_power": format(self.maximum_leakage_power, "f"),
            "is_eligible": self.is_eligible,
            "ineligibility_reasons": list(self.ineligibility_reasons),
            "reference_phase_rad": format(self.reference_phase_rad, "f"),
            "relative_delay_fs": format(self.relative_delay_fs, "f"),
        }

    @classmethod
    def from_mapping(cls, value: object) -> SpectralCellAssessment:
        """
        Restore one exact spectral cell assessment.
        """

        values = _closed_mapping(
            value,
            {
                "design_r_squared",
                "design_maximum_residual_rad",
                "geometry",
                "holdout_maximum_residual_rad",
                "minimum_converted_power",
                "maximum_leakage_power",
                "is_eligible",
                "ineligibility_reasons",
                "reference_phase_rad",
                "relative_delay_fs",
            },
            "spectral_cell_assessment_invalid",
        )
        try:
            return cls(
                geometry=SpectralRectangle.from_mapping(values["geometry"]),
                relative_delay_fs=Decimal(_text(values["relative_delay_fs"])),
                reference_phase_rad=Decimal(_text(values["reference_phase_rad"])),
                design_r_squared=Decimal(_text(values["design_r_squared"])),
                design_maximum_residual_rad=Decimal(
                    _text(values["design_maximum_residual_rad"])
                ),
                holdout_maximum_residual_rad=Decimal(
                    _text(values["holdout_maximum_residual_rad"])
                ),
                minimum_converted_power=Decimal(
                    _text(values["minimum_converted_power"])
                ),
                maximum_leakage_power=Decimal(
                    _text(values["maximum_leakage_power"])
                ),
                is_eligible=cast(bool, values["is_eligible"]),
                ineligibility_reasons=tuple(
                    _text(item)
                    for item in _sequence(values["ineligibility_reasons"])
                ),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("spectral_cell_assessment_invalid") from error


class SpectralQualificationStatus(str, Enum):
    """
    Name every closed first-slice spectral qualification outcome.
    """

    CANDIDATE = "positive_single_rectangle_candidate"
    EVIDENCE_INCOMPLETE = "spectral_evidence_incomplete"
    NUMERICAL_INCOMPLETE = "spectral_numerical_incomplete"
    CONVERSION_INSUFFICIENT = "single_rectangle_conversion_insufficient"
    LEAKAGE_INSUFFICIENT = "single_rectangle_leakage_insufficient"
    LINEARITY_INSUFFICIENT = "single_rectangle_spectral_linearity_insufficient"
    INTERLEAVED_VALIDATION_INSUFFICIENT = (
        "single_rectangle_interleaved_validation_insufficient"
    )
    JOINT_COVERAGE_INSUFFICIENT = (
        "single_rectangle_joint_spectral_coverage_insufficient"
    )
    DELAY_SPAN_INSUFFICIENT = "single_rectangle_delay_span_insufficient"


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralLibraryQualification:
    """
    Close one target-specific screen without claiming a fabricated lens.
    """

    status: SpectralQualificationStatus
    required_relative_delay_fs: Decimal
    available_relative_delay_span_fs: Decimal
    maximum_reference_phase_gap_rad: Decimal | None
    assessments: tuple[SpectralCellAssessment, ...]
    eligible_geometries: tuple[SpectralRectangle, ...]
    reasons: tuple[str, ...]
    target_reference: Reference
    plan_reference: Reference
    library_reference: Reference
    profile_reference: Reference
    campaign_reference: Reference
    material_binding_reference: Reference

    def __post_init__(self) -> None:
        """
        Require one explicit verdict with finite metrics and cited evidence.
        """

        if (
            not isinstance(self.status, SpectralQualificationStatus)
            or not self.required_relative_delay_fs.is_finite()
            or self.required_relative_delay_fs <= 0
            or not self.available_relative_delay_span_fs.is_finite()
            or self.available_relative_delay_span_fs < 0
            or (
                self.maximum_reference_phase_gap_rad is not None
                and (
                    not self.maximum_reference_phase_gap_rad.is_finite()
                    or self.maximum_reference_phase_gap_rad < 0
                )
            )
            or not self.reasons
            or self.eligible_geometries
            != tuple(item.geometry for item in self.assessments if item.is_eligible)
        ):
            raise ValueError("spectral_library_qualification_invalid")

    @property
    def is_candidate(self) -> bool:
        """
        Report whether this qualification authorizes the next design stage.
        """

        return self.status is SpectralQualificationStatus.CANDIDATE

    def document(self) -> Document:
        available_delay = format(self.available_relative_delay_span_fs, "f")
        required_delay = format(self.required_relative_delay_fs, "f")
        return Document(
            QUALIFIED_SPECTRAL_LIBRARY_SCHEMA,
            {
                "assessments": [item.as_mapping() for item in self.assessments],
                "eligible_geometries": [
                    item.as_mapping() for item in self.eligible_geometries
                ],
                "available_relative_delay_span_fs": available_delay,
                "library_reference": self.library_reference.as_mapping(),
                "campaign_reference": self.campaign_reference.as_mapping(),
                "material_binding_reference": (
                    self.material_binding_reference.as_mapping()
                ),
                "maximum_reference_phase_gap_rad": (
                    None
                    if self.maximum_reference_phase_gap_rad is None
                    else format(self.maximum_reference_phase_gap_rad, "f")
                ),
                "plan_reference": self.plan_reference.as_mapping(),
                "profile_reference": self.profile_reference.as_mapping(),
                "reasons": list(self.reasons),
                "required_relative_delay_fs": required_delay,
                "status": self.status.value,
                "target_reference": self.target_reference.as_mapping(),
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> SpectralLibraryQualification:
        if document.schema_identifier != QUALIFIED_SPECTRAL_LIBRARY_SCHEMA:
            raise ValueError("spectral_library_qualification_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {
                "assessments",
                "eligible_geometries",
                "available_relative_delay_span_fs",
                "library_reference",
                "campaign_reference",
                "material_binding_reference",
                "maximum_reference_phase_gap_rad",
                "plan_reference",
                "profile_reference",
                "reasons",
                "required_relative_delay_fs",
                "status",
                "target_reference",
            },
            "spectral_library_qualification_document_invalid",
        )
        try:
            maximum_gap = values["maximum_reference_phase_gap_rad"]
            qualification = cls(
                status=SpectralQualificationStatus(_text(values["status"])),
                required_relative_delay_fs=Decimal(
                    _text(values["required_relative_delay_fs"])
                ),
                available_relative_delay_span_fs=Decimal(
                    _text(values["available_relative_delay_span_fs"])
                ),
                maximum_reference_phase_gap_rad=(
                    None if maximum_gap is None else Decimal(_text(maximum_gap))
                ),
                assessments=tuple(
                    SpectralCellAssessment.from_mapping(item)
                    for item in _sequence(values["assessments"])
                ),
                eligible_geometries=tuple(
                    SpectralRectangle.from_mapping(item)
                    for item in _sequence(values["eligible_geometries"])
                ),
                reasons=tuple(_text(item) for item in _sequence(values["reasons"])),
                target_reference=Reference.from_mapping(
                    _mapping(values["target_reference"])
                ),
                plan_reference=Reference.from_mapping(
                    _mapping(values["plan_reference"])
                ),
                library_reference=Reference.from_mapping(
                    _mapping(values["library_reference"])
                ),
                profile_reference=Reference.from_mapping(
                    _mapping(values["profile_reference"])
                ),
                campaign_reference=Reference.from_mapping(
                    _mapping(values["campaign_reference"])
                ),
                material_binding_reference=Reference.from_mapping(
                    _mapping(values["material_binding_reference"])
                ),
            )
        except (TypeError, ValueError) as error:
            raise ValueError(
                "spectral_library_qualification_document_invalid"
            ) from error
        if qualification.document().to_bytes() != document.to_bytes():
            raise ValueError("spectral_library_qualification_document_mismatch")
        return qualification


class BandVerificationStatus(str, Enum):
    """Name the immutable post-freeze dense-band verdict."""

    PASS = "pass"
    MISSING_BLIND = "missing_blind"
    NUMERICAL_INCOMPLETE = "numerical_incomplete"
    EVIDENCE_ORIGIN_MISMATCH = "evidence_origin_mismatch"
    DENSE_RESIDUAL = "dense_residual"
    CURVATURE = "curvature"


@dataclass(frozen=True, slots=True, kw_only=True)
class PostFreezeJonesLibrary:
    """Retain only observations made after one aperture identity freezes."""

    aperture_reference: Reference
    profile_reference: Reference
    plan_reference: Reference
    qualification_reference: Reference
    candidate_library_reference: Reference
    solver_binding_reference: Reference
    blind_wavelengths_nm: tuple[int, ...]
    used_geometries: tuple[SpectralRectangle, ...]
    observations: tuple[SpectralJonesObservation, ...]
    numerical_incompletion_references: tuple[Reference, ...] = ()
    missing_wavelengths_nm: tuple[int, ...] = ()
    unavailable_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        expected = {
            (geometry, wavelength)
            for geometry in self.used_geometries
            for wavelength in self.blind_wavelengths_nm
        }
        observed = {
            (item.geometry, item.wavelength_nm) for item in self.observations
        }
        if (
            not self.blind_wavelengths_nm
            or not self.used_geometries
            or len(observed) != len(self.observations)
            or observed - expected
            or self.missing_wavelengths_nm
            != tuple(sorted(set(self.missing_wavelengths_nm)))
            or any(item not in self.blind_wavelengths_nm for item in self.missing_wavelengths_nm)
            or len(self.unavailable_reasons) != len(self.missing_wavelengths_nm)
        ):
            raise ValueError("post_freeze_jones_library_invalid")

    @property
    def has_single_execution_origin(self) -> bool:
        return len({item.execution_origin for item in self.observations}) <= 1

    @property
    def is_complete(self) -> bool:
        expected_count = len(self.used_geometries) * len(self.blind_wavelengths_nm)
        return (
            len(self.observations) == expected_count
            and self.has_single_execution_origin
            and not self.numerical_incompletion_references
            and not self.missing_wavelengths_nm
        )

    def document(self) -> Document:
        return Document(
            POST_FREEZE_JONES_LIBRARY_SCHEMA,
            {
                "aperture_reference": self.aperture_reference.as_mapping(),
                "blind_wavelengths_nm": list(self.blind_wavelengths_nm),
                "candidate_library_reference": self.candidate_library_reference.as_mapping(),
                "missing_wavelengths_nm": list(self.missing_wavelengths_nm),
                "numerical_incompletion_references": [item.as_mapping() for item in self.numerical_incompletion_references],
                "observations": {
                    f"observation_{index:03d}": item.as_mapping()
                    for index, item in enumerate(self.observations, start=1)
                },
                "plan_reference": self.plan_reference.as_mapping(),
                "profile_reference": self.profile_reference.as_mapping(),
                "qualification_reference": self.qualification_reference.as_mapping(),
                "solver_binding_reference": self.solver_binding_reference.as_mapping(),
                "used_geometries": [item.as_mapping() for item in self.used_geometries],
                "unavailable_reasons": list(self.unavailable_reasons),
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> PostFreezeJonesLibrary:
        if document.schema_identifier != POST_FREEZE_JONES_LIBRARY_SCHEMA:
            raise ValueError("post_freeze_jones_library_schema_mismatch")
        values = _closed_mapping(document.values, {
            "aperture_reference", "blind_wavelengths_nm", "candidate_library_reference",
            "missing_wavelengths_nm", "numerical_incompletion_references", "observations",
            "plan_reference", "profile_reference", "qualification_reference",
            "solver_binding_reference", "used_geometries",
            "unavailable_reasons",
        }, "post_freeze_jones_library_document_invalid")
        try:
            restored = cls(
                aperture_reference=Reference.from_mapping(_mapping(values["aperture_reference"])),
                profile_reference=Reference.from_mapping(_mapping(values["profile_reference"])),
                plan_reference=Reference.from_mapping(_mapping(values["plan_reference"])),
                qualification_reference=Reference.from_mapping(_mapping(values["qualification_reference"])),
                candidate_library_reference=Reference.from_mapping(_mapping(values["candidate_library_reference"])),
                solver_binding_reference=Reference.from_mapping(_mapping(values["solver_binding_reference"])),
                blind_wavelengths_nm=tuple(_integer(item) for item in _sequence(values["blind_wavelengths_nm"])),
                used_geometries=tuple(SpectralRectangle.from_mapping(item) for item in _sequence(values["used_geometries"])),
                observations=tuple(SpectralJonesObservation.from_mapping(item) for item in _indexed_values(values["observations"], "observation")),
                numerical_incompletion_references=tuple(Reference.from_mapping(_mapping(item)) for item in _sequence(values["numerical_incompletion_references"])),
                missing_wavelengths_nm=tuple(_integer(item) for item in _sequence(values["missing_wavelengths_nm"])),
                unavailable_reasons=tuple(_text(item) for item in _sequence(values["unavailable_reasons"])),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("post_freeze_jones_library_document_invalid") from error
        if restored.document().to_bytes() != document.to_bytes():
            raise ValueError("post_freeze_jones_library_document_mismatch")
        return restored


@dataclass(frozen=True, slots=True, kw_only=True)
class BandVerificationEvidence:
    """Close the blind role without reopening qualification or assignment."""

    status: BandVerificationStatus
    aperture_reference: Reference
    profile_reference: Reference
    qualification_reference: Reference
    post_freeze_library_reference: Reference
    spectral_field_family_reference: Reference | None
    focus_reference: Reference | None
    maximum_dense_phase_residual_rad: Decimal | None
    maximum_phase_curvature_rad: Decimal | None
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.status, BandVerificationStatus)
            or not self.reasons
            or any(
                value is not None and (not value.is_finite() or value < 0)
                for value in (
                    self.maximum_dense_phase_residual_rad,
                    self.maximum_phase_curvature_rad,
                )
            )
            or (
                self.status is BandVerificationStatus.PASS
                and (
                    self.maximum_dense_phase_residual_rad is None
                    or self.maximum_phase_curvature_rad is None
                    or self.spectral_field_family_reference is None
                    or self.focus_reference is None
                )
            )
            or (
                self.status in {
                    BandVerificationStatus.MISSING_BLIND,
                    BandVerificationStatus.NUMERICAL_INCOMPLETE,
                    BandVerificationStatus.EVIDENCE_ORIGIN_MISMATCH,
                }
                and (
                    self.spectral_field_family_reference is not None
                    or self.focus_reference is not None
                    or self.maximum_dense_phase_residual_rad is not None
                    or self.maximum_phase_curvature_rad is not None
                )
            )
            or (
                self.status in {
                    BandVerificationStatus.DENSE_RESIDUAL,
                    BandVerificationStatus.CURVATURE,
                }
                and (
                    self.spectral_field_family_reference is None
                    or self.focus_reference is None
                )
            )
        ):
            raise ValueError("band_verification_evidence_invalid")

    @property
    def is_pass(self) -> bool:
        return self.status is BandVerificationStatus.PASS

    def document(self) -> Document:
        return Document(
            BAND_VERIFICATION_EVIDENCE_SCHEMA,
            {
                "aperture_reference": self.aperture_reference.as_mapping(),
                "focus_reference": None if self.focus_reference is None else self.focus_reference.as_mapping(),
                "maximum_dense_phase_residual_rad": (
                    None
                    if self.maximum_dense_phase_residual_rad is None
                    else format(self.maximum_dense_phase_residual_rad, "f")
                ),
                "maximum_phase_curvature_rad": (
                    None
                    if self.maximum_phase_curvature_rad is None
                    else format(self.maximum_phase_curvature_rad, "f")
                ),
                "post_freeze_library_reference": self.post_freeze_library_reference.as_mapping(),
                "profile_reference": self.profile_reference.as_mapping(),
                "qualification_reference": self.qualification_reference.as_mapping(),
                "reasons": list(self.reasons),
                "spectral_field_family_reference": None if self.spectral_field_family_reference is None else self.spectral_field_family_reference.as_mapping(),
                "status": self.status.value,
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> BandVerificationEvidence:
        if document.schema_identifier != BAND_VERIFICATION_EVIDENCE_SCHEMA:
            raise ValueError("band_verification_evidence_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {
                "aperture_reference",
                "focus_reference",
                "maximum_dense_phase_residual_rad",
                "maximum_phase_curvature_rad",
                "post_freeze_library_reference",
                "profile_reference",
                "qualification_reference",
                "reasons",
                "spectral_field_family_reference",
                "status",
            },
            "band_verification_evidence_document_invalid",
        )
        try:
            dense = values["maximum_dense_phase_residual_rad"]
            curvature = values["maximum_phase_curvature_rad"]
            restored = cls(
                status=BandVerificationStatus(_text(values["status"])),
                aperture_reference=Reference.from_mapping(_mapping(values["aperture_reference"])),
                profile_reference=Reference.from_mapping(_mapping(values["profile_reference"])),
                qualification_reference=Reference.from_mapping(_mapping(values["qualification_reference"])),
                post_freeze_library_reference=Reference.from_mapping(_mapping(values["post_freeze_library_reference"])),
                spectral_field_family_reference=(None if values["spectral_field_family_reference"] is None else Reference.from_mapping(_mapping(values["spectral_field_family_reference"]))),
                focus_reference=(None if values["focus_reference"] is None else Reference.from_mapping(_mapping(values["focus_reference"]))),
                maximum_dense_phase_residual_rad=(None if dense is None else Decimal(_text(dense))),
                maximum_phase_curvature_rad=(None if curvature is None else Decimal(_text(curvature))),
                reasons=tuple(_text(item) for item in _sequence(values["reasons"])),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("band_verification_evidence_document_invalid") from error
        if restored.document().to_bytes() != document.to_bytes():
            raise ValueError("band_verification_evidence_document_mismatch")
        return restored


_COMPENSATED_STRATEGY = "continuous compensation"
_PB_ONLY_STRATEGY = "pb-only baseline"
_ACHROMATIC_STRATEGIES = (_COMPENSATED_STRATEGY, _PB_ONLY_STRATEGY)
_APERTURE_SELECTION_POLICY = (
    "minimum absolute relative-delay error",
    "greater minimum converted power",
    "lower holdout phase residual",
    "smaller rectangular dimensions",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ApertureAdjacencyDiagnostics:
    """Immutable geometry-transition evidence for the frozen aperture."""

    is_right_adjacent: NDArray[numpy.bool_]
    is_down_adjacent: NDArray[numpy.bool_]
    right_dimension_jumps_nm: NDArray[numpy.integer]
    down_dimension_jumps_nm: NDArray[numpy.integer]
    right_transition_classes: NDArray[numpy.str_]
    down_transition_classes: NDArray[numpy.str_]

    def __post_init__(self) -> None:
        right = numpy.array(self.is_right_adjacent, dtype=numpy.bool_, copy=True)
        down = numpy.array(self.is_down_adjacent, dtype=numpy.bool_, copy=True)
        right_jumps = numpy.array(
            self.right_dimension_jumps_nm,
            dtype=numpy.int64,
            copy=True,
        )
        down_jumps = numpy.array(
            self.down_dimension_jumps_nm,
            dtype=numpy.int64,
            copy=True,
        )
        right_classes = numpy.array(
            self.right_transition_classes,
            dtype=numpy.str_,
            copy=True,
        )
        down_classes = numpy.array(
            self.down_transition_classes,
            dtype=numpy.str_,
            copy=True,
        )
        shape = right.shape
        if (
            right.ndim != 2
            or down.shape != shape
            or right_jumps.shape != (*shape, 2)
            or down_jumps.shape != (*shape, 2)
            or right_classes.shape != shape
            or down_classes.shape != shape
            or numpy.any(right_jumps < 0)
            or numpy.any(down_jumps < 0)
            or numpy.any(right_jumps[~right] != 0)
            or numpy.any(down_jumps[~down] != 0)
            or not numpy.array_equal(
                right_classes,
                _transition_classes(right_jumps, right),
            )
            or not numpy.array_equal(
                down_classes,
                _transition_classes(down_jumps, down),
            )
        ):
            raise ValueError("aperture_adjacency_diagnostics_invalid")
        for value in (
            right,
            down,
            right_jumps,
            down_jumps,
            right_classes,
            down_classes,
        ):
            value.setflags(write=False)
        object.__setattr__(self, "is_right_adjacent", right)
        object.__setattr__(self, "is_down_adjacent", down)
        object.__setattr__(self, "right_dimension_jumps_nm", right_jumps)
        object.__setattr__(self, "down_dimension_jumps_nm", down_jumps)
        object.__setattr__(self, "right_transition_classes", right_classes)
        object.__setattr__(self, "down_transition_classes", down_classes)

    def as_mapping(self) -> dict[str, object]:
        return {
            "down_dimension_jumps_nm": self.down_dimension_jumps_nm.tolist(),
            "is_down_adjacent": self.is_down_adjacent.tolist(),
            "down_transition_classes": self.down_transition_classes.tolist(),
            "right_dimension_jumps_nm": self.right_dimension_jumps_nm.tolist(),
            "is_right_adjacent": self.is_right_adjacent.tolist(),
            "right_transition_classes": self.right_transition_classes.tolist(),
        }

    @classmethod
    def from_mapping(cls, value: object) -> ApertureAdjacencyDiagnostics:
        values = _closed_mapping(
            value,
            {
                "down_dimension_jumps_nm",
                "is_down_adjacent",
                "down_transition_classes",
                "right_dimension_jumps_nm",
                "is_right_adjacent",
                "right_transition_classes",
            },
            "aperture_adjacency_diagnostics_invalid",
        )
        return cls(
            is_right_adjacent=numpy.asarray(
                values["is_right_adjacent"],
                dtype=numpy.bool_,
            ),
            is_down_adjacent=numpy.asarray(
                values["is_down_adjacent"],
                dtype=numpy.bool_,
            ),
            right_dimension_jumps_nm=numpy.asarray(
                values["right_dimension_jumps_nm"],
                dtype=numpy.int64,
            ),
            down_dimension_jumps_nm=numpy.asarray(
                values["down_dimension_jumps_nm"],
                dtype=numpy.int64,
            ),
            right_transition_classes=numpy.asarray(
                values["right_transition_classes"],
                dtype=numpy.str_,
            ),
            down_transition_classes=numpy.asarray(
                values["down_transition_classes"],
                dtype=numpy.str_,
            ),
        )


def _transition_classes(
    dimension_jumps_nm: NDArray[numpy.integer],
    is_adjacent: NDArray[numpy.bool_],
) -> NDArray[numpy.str_]:
    classes = numpy.full(is_adjacent.shape, "", dtype="<U18")
    has_short_jump = dimension_jumps_nm[..., 0] > 0
    has_long_jump = dimension_jumps_nm[..., 1] > 0
    classes[is_adjacent & ~has_short_jump & ~has_long_jump] = "same geometry"
    classes[is_adjacent & has_short_jump & ~has_long_jump] = "short-side jump"
    classes[is_adjacent & ~has_short_jump & has_long_jump] = "long-side jump"
    classes[is_adjacent & has_short_jump & has_long_jump] = "two-dimension jump"
    return classes


def _form_aperture_adjacency_diagnostics(
    is_occupied: NDArray[numpy.bool_],
    geometry_indices: NDArray[numpy.integer],
    geometries: tuple[SpectralRectangle, ...],
) -> ApertureAdjacencyDiagnostics:
    shape = is_occupied.shape
    dimensions_nm = numpy.zeros((*shape, 2), dtype=numpy.int64)
    geometry_dimensions_nm = numpy.asarray(
        [
            (geometry.short_side_nm, geometry.long_side_nm)
            for geometry in geometries
        ],
        dtype=numpy.int64,
    )
    dimensions_nm[is_occupied] = geometry_dimensions_nm[geometry_indices[is_occupied]]
    right = numpy.zeros(shape, dtype=numpy.bool_)
    right[:, :-1] = is_occupied[:, :-1] & is_occupied[:, 1:]
    down = numpy.zeros(shape, dtype=numpy.bool_)
    down[:-1, :] = is_occupied[:-1, :] & is_occupied[1:, :]
    right_jumps = numpy.zeros((*shape, 2), dtype=numpy.int64)
    right_jumps[:, :-1] = numpy.abs(
        dimensions_nm[:, 1:] - dimensions_nm[:, :-1]
    )
    right_jumps[~right] = 0
    down_jumps = numpy.zeros((*shape, 2), dtype=numpy.int64)
    down_jumps[:-1, :] = numpy.abs(
        dimensions_nm[1:, :] - dimensions_nm[:-1, :]
    )
    down_jumps[~down] = 0
    return ApertureAdjacencyDiagnostics(
        is_right_adjacent=right,
        is_down_adjacent=down,
        right_dimension_jumps_nm=right_jumps,
        down_dimension_jumps_nm=down_jumps,
        right_transition_classes=_transition_classes(right_jumps, right),
        down_transition_classes=_transition_classes(down_jumps, down),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class AchromaticAperture:
    """
    Freeze one geometry and one physical orientation at every aperture site.
    """

    target_reference: Reference
    lattice_reference: Reference
    plan_reference: Reference
    qualification_reference: Reference
    library_reference: Reference
    selection_binding_reference: Reference
    period_nm: int
    height_nm: int
    half_span_nm: int
    footprint: ApertureFootprint
    phase_sign: int
    geometries: tuple[SpectralRectangle, ...]
    baseline_geometry: SpectralRectangle
    adjacency_diagnostics: ApertureAdjacencyDiagnostics
    coordinates_nm: NDArray[numpy.integer]
    is_occupied: NDArray[numpy.bool_]
    geometry_indices: NDArray[numpy.integer]
    orientations_rad: NDArray[numpy.floating]
    baseline_orientations_rad: NDArray[numpy.floating]
    required_relative_delay_fs: NDArray[numpy.floating]
    selected_relative_delay_fs: NDArray[numpy.floating]
    delay_error_fs: NDArray[numpy.floating]
    propagation_reference_phase_rad: NDArray[numpy.floating]
    geometric_phase_rad: NDArray[numpy.floating]
    target_reference_phase_rad: NDArray[numpy.floating]
    realized_reference_phase_rad: NDArray[numpy.floating]

    def __post_init__(self) -> None:
        if (
            self.period_nm <= 0
            or self.height_nm <= 0
            or self.half_span_nm <= 0
            or self.phase_sign not in {-1, 1}
            or not self.geometries
            or len(set(self.geometries)) != len(self.geometries)
            or self.baseline_geometry not in self.geometries
        ):
            raise ValueError("achromatic_aperture_invalid")
        coordinates = numpy.array(self.coordinates_nm, dtype=numpy.int64, copy=True)
        occupied = numpy.array(self.is_occupied, dtype=numpy.bool_, copy=True)
        indices = numpy.array(self.geometry_indices, dtype=numpy.int64, copy=True)
        arrays = tuple(
            numpy.array(value, dtype=numpy.float64, copy=True)
            for value in (
                self.orientations_rad,
                self.baseline_orientations_rad,
                self.required_relative_delay_fs,
                self.selected_relative_delay_fs,
                self.delay_error_fs,
                self.propagation_reference_phase_rad,
                self.geometric_phase_rad,
                self.target_reference_phase_rad,
                self.realized_reference_phase_rad,
            )
        )
        shape = occupied.shape
        if (
            occupied.ndim != 2
            or coordinates.shape != (*shape, 2)
            or indices.shape != shape
            or any(value.shape != shape for value in arrays)
            or not numpy.any(occupied)
            or numpy.any(indices[~occupied] != -1)
            or numpy.any(indices[occupied] < 0)
            or numpy.any(indices[occupied] >= len(self.geometries))
            or any(not numpy.isfinite(value[occupied]).all() for value in arrays)
            or any(numpy.any(value[~occupied] != 0) for value in arrays)
            or numpy.any(arrays[0][occupied] < 0)
            or numpy.any(arrays[0][occupied] >= math.pi)
            or numpy.any(arrays[1][occupied] < 0)
            or numpy.any(arrays[1][occupied] >= math.pi)
            or numpy.any(arrays[2][occupied] < 0)
            or numpy.any(arrays[5][occupied] < 0)
            or numpy.any(arrays[5][occupied] >= 2 * math.pi)
            or numpy.any(arrays[6][occupied] < 0)
            or numpy.any(arrays[6][occupied] >= 2 * math.pi)
            or numpy.any(arrays[7][occupied] < 0)
            or numpy.any(arrays[7][occupied] >= 2 * math.pi)
            or numpy.any(arrays[8][occupied] < 0)
            or numpy.any(arrays[8][occupied] >= 2 * math.pi)
        ):
            raise ValueError("achromatic_aperture_map_invalid")
        composed_error = numpy.angle(
            numpy.exp(1j * (arrays[5][occupied] + arrays[6][occupied] - arrays[8][occupied]))
        )
        pb_error = numpy.angle(
            numpy.exp(
                1j
                * (
                    2 * self.phase_sign * arrays[0][occupied]
                    - arrays[6][occupied]
                )
            )
        )
        if (
            numpy.max(numpy.abs(composed_error)) > 1e-12
            or numpy.max(numpy.abs(pb_error)) > 1e-12
        ):
            raise ValueError("achromatic_aperture_phase_decomposition_invalid")
        if self.footprint is ApertureFootprint.CIRCULAR:
            distance_nm = numpy.hypot(coordinates[..., 0], coordinates[..., 1])
        elif self.footprint is ApertureFootprint.SQUARE:
            distance_nm = numpy.maximum(
                numpy.abs(coordinates[..., 0]),
                numpy.abs(coordinates[..., 1]),
            )
        else:
            raise ValueError("achromatic_aperture_footprint_invalid")
        if numpy.any(distance_nm[occupied] > self.half_span_nm):
            raise ValueError("achromatic_aperture_site_outside_footprint")
        expected_diagnostics = _form_aperture_adjacency_diagnostics(
            occupied,
            indices,
            self.geometries,
        )
        if (
            self.adjacency_diagnostics.as_mapping()
            != expected_diagnostics.as_mapping()
        ):
            raise ValueError("achromatic_aperture_adjacency_mismatch")
        for value in (coordinates, occupied, indices, *arrays):
            value.setflags(write=False)
        object.__setattr__(self, "coordinates_nm", coordinates)
        object.__setattr__(self, "is_occupied", occupied)
        object.__setattr__(self, "geometry_indices", indices)
        for name, value in zip(
            (
                "orientations_rad",
                "baseline_orientations_rad",
                "required_relative_delay_fs",
                "selected_relative_delay_fs",
                "delay_error_fs",
                "propagation_reference_phase_rad",
                "geometric_phase_rad",
                "target_reference_phase_rad",
                "realized_reference_phase_rad",
            ),
            arrays,
            strict=True,
        ):
            object.__setattr__(self, name, value)

    @property
    def site_count(self) -> int:
        return int(numpy.count_nonzero(self.is_occupied))

    @property
    def used_geometries(self) -> tuple[SpectralRectangle, ...]:
        assigned_indices = {
            int(index) for index in self.geometry_indices[self.is_occupied]
        }
        return tuple(
            geometry
            for index, geometry in enumerate(self.geometries)
            if index in assigned_indices or geometry == self.baseline_geometry
        )

    @property
    def selection_policy(self) -> tuple[str, ...]:
        return _APERTURE_SELECTION_POLICY

    def document(self) -> Document:
        return Document(
            ACHROMATIC_APERTURE_SCHEMA,
            {
                "adjacency_diagnostics": self.adjacency_diagnostics.as_mapping(),
                "baseline_geometry": self.baseline_geometry.as_mapping(),
                "baseline_orientations_rad": _float_grid(self.baseline_orientations_rad),
                "coordinates_nm": self.coordinates_nm.tolist(),
                "delay_error_fs": _float_grid(self.delay_error_fs),
                "geometries": [item.as_mapping() for item in self.geometries],
                "geometry_indices": self.geometry_indices.tolist(),
                "half_span_nm": self.half_span_nm,
                "height_nm": self.height_nm,
                "footprint": self.footprint.value,
                "lattice_reference": self.lattice_reference.as_mapping(),
                "library_reference": self.library_reference.as_mapping(),
                "occupied": self.is_occupied.tolist(),
                "orientations_rad": _float_grid(self.orientations_rad),
                "period_nm": self.period_nm,
                "phase_components": {
                    "continuous_compensation_phase": "propagation phase + PB phase",
                    "pb_phase": f"{2 * self.phase_sign:+d} theta",
                    "propagation_phase": "geometry-controlled spectral response",
                },
                "phase_sign": self.phase_sign,
                "plan_reference": self.plan_reference.as_mapping(),
                "qualification_reference": self.qualification_reference.as_mapping(),
                "propagation_reference_phase_rad": _float_grid(
                    self.propagation_reference_phase_rad
                ),
                "geometric_phase_rad": _float_grid(self.geometric_phase_rad),
                "realized_reference_phase_rad": _float_grid(
                    self.realized_reference_phase_rad
                ),
                "required_relative_delay_fs": _float_grid(
                    self.required_relative_delay_fs
                ),
                "selection_binding_reference": self.selection_binding_reference.as_mapping(),
                "selection_policy": list(self.selection_policy),
                "selected_relative_delay_fs": _float_grid(
                    self.selected_relative_delay_fs
                ),
                "target_reference": self.target_reference.as_mapping(),
                "target_reference_phase_rad": _float_grid(
                    self.target_reference_phase_rad
                ),
                "used_geometries": [
                    item.as_mapping() for item in self.used_geometries
                ],
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> AchromaticAperture:
        if document.schema_identifier != ACHROMATIC_APERTURE_SCHEMA:
            raise ValueError("achromatic_aperture_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {
                "adjacency_diagnostics",
                "baseline_geometry",
                "baseline_orientations_rad",
                "coordinates_nm",
                "delay_error_fs",
                "geometries",
                "geometry_indices",
                "half_span_nm",
                "height_nm",
                "footprint",
                "lattice_reference",
                "library_reference",
                "occupied",
                "orientations_rad",
                "period_nm",
                "phase_components",
                "phase_sign",
                "plan_reference",
                "qualification_reference",
                "propagation_reference_phase_rad",
                "geometric_phase_rad",
                "realized_reference_phase_rad",
                "required_relative_delay_fs",
                "selection_binding_reference",
                "selection_policy",
                "selected_relative_delay_fs",
                "target_reference",
                "target_reference_phase_rad",
                "used_geometries",
            },
            "achromatic_aperture_document_invalid",
        )
        try:
            phase_sign = _integer(values["phase_sign"])
            if _mapping(values["phase_components"]) != {
                "continuous_compensation_phase": "propagation phase + PB phase",
                "pb_phase": f"{2 * phase_sign:+d} theta",
                "propagation_phase": "geometry-controlled spectral response",
            }:
                raise ValueError("achromatic_aperture_document_invalid")
            if tuple(
                _text(item) for item in _sequence(values["selection_policy"])
            ) != _APERTURE_SELECTION_POLICY:
                raise ValueError("achromatic_aperture_document_invalid")
            aperture = cls(
                target_reference=Reference.from_mapping(_mapping(values["target_reference"])),
                lattice_reference=Reference.from_mapping(
                    _mapping(values["lattice_reference"])
                ),
                plan_reference=Reference.from_mapping(_mapping(values["plan_reference"])),
                qualification_reference=Reference.from_mapping(
                    _mapping(values["qualification_reference"])
                ),
                library_reference=Reference.from_mapping(
                    _mapping(values["library_reference"])
                ),
                selection_binding_reference=Reference.from_mapping(
                    _mapping(values["selection_binding_reference"])
                ),
                period_nm=_integer(values["period_nm"]),
                height_nm=_integer(values["height_nm"]),
                half_span_nm=_integer(values["half_span_nm"]),
                footprint=ApertureFootprint(_text(values["footprint"])),
                phase_sign=phase_sign,
                geometries=tuple(
                    SpectralRectangle.from_mapping(item)
                    for item in _sequence(values["geometries"])
                ),
                baseline_geometry=SpectralRectangle.from_mapping(
                    values["baseline_geometry"]
                ),
                adjacency_diagnostics=ApertureAdjacencyDiagnostics.from_mapping(
                    values["adjacency_diagnostics"]
                ),
                coordinates_nm=numpy.asarray(values["coordinates_nm"], dtype=numpy.int64),
                is_occupied=numpy.asarray(values["occupied"], dtype=numpy.bool_),
                geometry_indices=numpy.asarray(values["geometry_indices"], dtype=numpy.int64),
                orientations_rad=_restore_float_grid(values["orientations_rad"]),
                baseline_orientations_rad=_restore_float_grid(
                    values["baseline_orientations_rad"]
                ),
                required_relative_delay_fs=_restore_float_grid(
                    values["required_relative_delay_fs"]
                ),
                selected_relative_delay_fs=_restore_float_grid(
                    values["selected_relative_delay_fs"]
                ),
                delay_error_fs=_restore_float_grid(values["delay_error_fs"]),
                propagation_reference_phase_rad=_restore_float_grid(
                    values["propagation_reference_phase_rad"]
                ),
                geometric_phase_rad=_restore_float_grid(
                    values["geometric_phase_rad"]
                ),
                target_reference_phase_rad=_restore_float_grid(
                    values["target_reference_phase_rad"]
                ),
                realized_reference_phase_rad=_restore_float_grid(
                    values["realized_reference_phase_rad"]
                ),
            )
            recorded_used_geometries = tuple(
                SpectralRectangle.from_mapping(item)
                for item in _sequence(values["used_geometries"])
            )
            if recorded_used_geometries != aperture.used_geometries:
                raise ValueError("achromatic_aperture_document_invalid")
        except (TypeError, ValueError) as error:
            raise ValueError("achromatic_aperture_document_invalid") from error
        if aperture.document().to_bytes() != document.to_bytes():
            raise ValueError("achromatic_aperture_document_mismatch")
        return aperture


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralFieldEntry:
    strategy: str
    wavelength_nm: int
    field_reference: Reference
    focal_region_reference: Reference

    def __post_init__(self) -> None:
        if self.strategy not in _ACHROMATIC_STRATEGIES or self.wavelength_nm <= 0:
            raise ValueError("spectral_field_entry_invalid")

    def as_mapping(self) -> dict[str, object]:
        return {
            "field_reference": self.field_reference.as_mapping(),
            "focal_region_reference": self.focal_region_reference.as_mapping(),
            "strategy": self.strategy,
            "wavelength_nm": self.wavelength_nm,
        }

    @classmethod
    def from_mapping(cls, value: object) -> SpectralFieldEntry:
        values = _closed_mapping(
            value,
            {"field_reference", "focal_region_reference", "strategy", "wavelength_nm"},
            "spectral_field_entry_invalid",
        )
        return cls(
            strategy=_text(values["strategy"]),
            wavelength_nm=_integer(values["wavelength_nm"]),
            field_reference=Reference.from_mapping(_mapping(values["field_reference"])),
            focal_region_reference=Reference.from_mapping(
                _mapping(values["focal_region_reference"])
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectralFieldFamily:
    aperture_reference: Reference
    qualification_reference: Reference
    library_reference: Reference
    propagation_binding_reference: Reference
    design_wavelengths_nm: tuple[int, ...]
    holdout_wavelengths_nm: tuple[int, ...]
    blind_verification_wavelengths_nm: tuple[int, ...]
    post_freeze_library_reference: Reference
    entries: tuple[SpectralFieldEntry, ...]

    def __post_init__(self) -> None:
        wavelengths = tuple(sorted((
            *self.design_wavelengths_nm,
            *self.holdout_wavelengths_nm,
            *self.blind_verification_wavelengths_nm,
        )))
        expected = {(strategy, wavelength) for strategy in _ACHROMATIC_STRATEGIES for wavelength in wavelengths}
        actual = {(item.strategy, item.wavelength_nm) for item in self.entries}
        if (
            not self.design_wavelengths_nm
            or not self.holdout_wavelengths_nm
            or not self.blind_verification_wavelengths_nm
            or len(wavelengths) != len(set(wavelengths))
            or len(actual) != len(self.entries)
            or actual != expected
        ):
            raise ValueError("spectral_field_family_invalid")

    @property
    def wavelengths_nm(self) -> tuple[int, ...]:
        return tuple(sorted((
            *self.design_wavelengths_nm,
            *self.holdout_wavelengths_nm,
            *self.blind_verification_wavelengths_nm,
        )))

    def document(self) -> Document:
        return Document(
            SPECTRAL_FIELD_FAMILY_SCHEMA,
            {
                "aperture_reference": self.aperture_reference.as_mapping(),
                "blind_verification_wavelengths_nm": list(self.blind_verification_wavelengths_nm),
                "design_wavelengths_nm": list(self.design_wavelengths_nm),
                "entries": {
                    f"entry_{index:03d}": item.as_mapping()
                    for index, item in enumerate(self.entries, start=1)
                },
                "holdout_wavelengths_nm": list(self.holdout_wavelengths_nm),
                "library_reference": self.library_reference.as_mapping(),
                "propagation_binding_reference": self.propagation_binding_reference.as_mapping(),
                "post_freeze_library_reference": self.post_freeze_library_reference.as_mapping(),
                "qualification_reference": self.qualification_reference.as_mapping(),
                "strategies": list(_ACHROMATIC_STRATEGIES),
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> SpectralFieldFamily:
        if document.schema_identifier != SPECTRAL_FIELD_FAMILY_SCHEMA:
            raise ValueError("spectral_field_family_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {
                "aperture_reference",
                "blind_verification_wavelengths_nm",
                "design_wavelengths_nm",
                "entries",
                "holdout_wavelengths_nm",
                "library_reference",
                "propagation_binding_reference",
                "post_freeze_library_reference",
                "qualification_reference",
                "strategies",
            },
            "spectral_field_family_document_invalid",
        )
        if tuple(_text(item) for item in _sequence(values["strategies"])) != _ACHROMATIC_STRATEGIES:
            raise ValueError("spectral_field_family_document_invalid")
        try:
            family = cls(
                aperture_reference=Reference.from_mapping(_mapping(values["aperture_reference"])),
                qualification_reference=Reference.from_mapping(
                    _mapping(values["qualification_reference"])
                ),
                library_reference=Reference.from_mapping(_mapping(values["library_reference"])),
                propagation_binding_reference=Reference.from_mapping(
                    _mapping(values["propagation_binding_reference"])
                ),
                post_freeze_library_reference=Reference.from_mapping(
                    _mapping(values["post_freeze_library_reference"])
                ),
                design_wavelengths_nm=tuple(
                    _integer(item) for item in _sequence(values["design_wavelengths_nm"])
                ),
                holdout_wavelengths_nm=tuple(
                    _integer(item) for item in _sequence(values["holdout_wavelengths_nm"])
                ),
                blind_verification_wavelengths_nm=tuple(
                    _integer(item)
                    for item in _sequence(values["blind_verification_wavelengths_nm"])
                ),
                entries=tuple(
                    SpectralFieldEntry.from_mapping(item)
                    for item in _indexed_values(values["entries"], "entry")
                ),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("spectral_field_family_document_invalid") from error
        if family.document().to_bytes() != document.to_bytes():
            raise ValueError("spectral_field_family_document_mismatch")
        return family


@dataclass(frozen=True, slots=True, kw_only=True)
class AchromaticFocusEntry:
    strategy: str
    wavelength_nm: int
    focus_reference: Reference
    focus: Focus

    def __post_init__(self) -> None:
        if self.strategy not in _ACHROMATIC_STRATEGIES or self.wavelength_nm <= 0:
            raise ValueError("achromatic_focus_entry_invalid")
        require_complete_focus(self.focus)

    def as_mapping(self) -> dict[str, object]:
        return {
            "focus": self.focus.as_mapping(),
            "focus_reference": self.focus_reference.as_mapping(),
            "strategy": self.strategy,
            "wavelength_nm": self.wavelength_nm,
        }

    @classmethod
    def from_mapping(cls, value: object) -> AchromaticFocusEntry:
        values = _closed_mapping(
            value,
            {"focus", "focus_reference", "strategy", "wavelength_nm"},
            "achromatic_focus_entry_invalid",
        )
        return cls(
            strategy=_text(values["strategy"]),
            wavelength_nm=_integer(values["wavelength_nm"]),
            focus_reference=Reference.from_mapping(_mapping(values["focus_reference"])),
            focus=cast(Focus, Focus.from_mapping(_mapping(values["focus"]))),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AchromaticFocusSummary:
    strategy: str
    maximum_absolute_focal_shift_m: float
    mean_absolute_focal_shift_m: float
    maximum_spot_width_m: float
    mean_transmitted_fraction: float
    mean_focus_efficiency: float
    maximum_leakage_fraction: float

    def __post_init__(self) -> None:
        values = (
            self.maximum_absolute_focal_shift_m,
            self.mean_absolute_focal_shift_m,
            self.maximum_spot_width_m,
            self.mean_transmitted_fraction,
            self.mean_focus_efficiency,
            self.maximum_leakage_fraction,
        )
        if self.strategy not in _ACHROMATIC_STRATEGIES or any(
            not math.isfinite(value) or value < 0 for value in values
        ):
            raise ValueError("achromatic_focus_summary_invalid")

    def as_mapping(self) -> dict[str, object]:
        return {
            "maximum_absolute_focal_shift_m": _number(self.maximum_absolute_focal_shift_m),
            "maximum_leakage_fraction": _number(self.maximum_leakage_fraction),
            "maximum_spot_width_m": _number(self.maximum_spot_width_m),
            "mean_absolute_focal_shift_m": _number(self.mean_absolute_focal_shift_m),
            "mean_focus_efficiency": _number(self.mean_focus_efficiency),
            "mean_transmitted_fraction": _number(self.mean_transmitted_fraction),
            "strategy": self.strategy,
        }

    @classmethod
    def from_mapping(cls, value: object) -> AchromaticFocusSummary:
        values = _closed_mapping(
            value,
            {
                "maximum_absolute_focal_shift_m",
                "maximum_leakage_fraction",
                "maximum_spot_width_m",
                "mean_absolute_focal_shift_m",
                "mean_focus_efficiency",
                "mean_transmitted_fraction",
                "strategy",
            },
            "achromatic_focus_summary_invalid",
        )
        return cls(
            strategy=_text(values["strategy"]),
            maximum_absolute_focal_shift_m=float(_text(values["maximum_absolute_focal_shift_m"])),
            mean_absolute_focal_shift_m=float(_text(values["mean_absolute_focal_shift_m"])),
            maximum_spot_width_m=float(_text(values["maximum_spot_width_m"])),
            mean_transmitted_fraction=float(_text(values["mean_transmitted_fraction"])),
            mean_focus_efficiency=float(_text(values["mean_focus_efficiency"])),
            maximum_leakage_fraction=float(_text(values["maximum_leakage_fraction"])),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AchromaticFocusRoleSummary:
    """Expose one strategy's metrics for one predeclared wavelength role."""

    role: str
    summary: AchromaticFocusSummary

    def __post_init__(self) -> None:
        if self.role not in {"design", "interleaved_validation", "blind_verification"}:
            raise ValueError("achromatic_focus_role_summary_invalid")

    def as_mapping(self) -> dict[str, object]:
        return {"role": self.role, "summary": self.summary.as_mapping()}

    @classmethod
    def from_mapping(cls, value: object) -> AchromaticFocusRoleSummary:
        values = _closed_mapping(
            value,
            {"role", "summary"},
            "achromatic_focus_role_summary_invalid",
        )
        return cls(
            role=_text(values["role"]),
            summary=AchromaticFocusSummary.from_mapping(values["summary"]),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AchromaticFocus:
    spectral_field_family_reference: Reference
    evaluation_binding_reference: Reference
    design_wavelengths_nm: tuple[int, ...]
    holdout_wavelengths_nm: tuple[int, ...]
    blind_verification_wavelengths_nm: tuple[int, ...]
    entries: tuple[AchromaticFocusEntry, ...]
    summaries: tuple[AchromaticFocusSummary, AchromaticFocusSummary]
    role_summaries: tuple[AchromaticFocusRoleSummary, ...]

    def __post_init__(self) -> None:
        wavelengths = tuple(sorted((
            *self.design_wavelengths_nm,
            *self.holdout_wavelengths_nm,
            *self.blind_verification_wavelengths_nm,
        )))
        expected = {(strategy, wavelength) for strategy in _ACHROMATIC_STRATEGIES for wavelength in wavelengths}
        actual = {(item.strategy, item.wavelength_nm) for item in self.entries}
        if (
            not self.design_wavelengths_nm
            or not self.holdout_wavelengths_nm
            or not self.blind_verification_wavelengths_nm
            or len(wavelengths) != len(set(wavelengths))
            or len(actual) != len(self.entries)
            or actual != expected
            or tuple(item.strategy for item in self.summaries) != _ACHROMATIC_STRATEGIES
            or self.summaries != _focus_summaries(self.entries)
            or self.role_summaries
            != _focus_role_summaries(
                self.entries,
                design_wavelengths_nm=self.design_wavelengths_nm,
                holdout_wavelengths_nm=self.holdout_wavelengths_nm,
                blind_wavelengths_nm=self.blind_verification_wavelengths_nm,
            )
        ):
            raise ValueError("achromatic_focus_invalid")

    @property
    def compensated_focal_shift_improvement_m(self) -> float:
        compensated, baseline = self.summaries
        return baseline.maximum_absolute_focal_shift_m - compensated.maximum_absolute_focal_shift_m

    def document(self) -> Document:
        return Document(
            ACHROMATIC_FOCUS_SCHEMA,
            {
                "compensated_focal_shift_improvement_m": _number(
                    self.compensated_focal_shift_improvement_m
                ),
                "blind_verification_wavelengths_nm": list(self.blind_verification_wavelengths_nm),
                "design_wavelengths_nm": list(self.design_wavelengths_nm),
                "entries": {
                    f"entry_{index:03d}": item.as_mapping()
                    for index, item in enumerate(self.entries, start=1)
                },
                "holdout_wavelengths_nm": list(self.holdout_wavelengths_nm),
                "evaluation_binding_reference": self.evaluation_binding_reference.as_mapping(),
                "spectral_field_family_reference": (
                    self.spectral_field_family_reference.as_mapping()
                ),
                "role_summaries": [item.as_mapping() for item in self.role_summaries],
                "summaries": [item.as_mapping() for item in self.summaries],
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> AchromaticFocus:
        if document.schema_identifier != ACHROMATIC_FOCUS_SCHEMA:
            raise ValueError("achromatic_focus_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {
                "compensated_focal_shift_improvement_m",
                "blind_verification_wavelengths_nm",
                "design_wavelengths_nm",
                "entries",
                "evaluation_binding_reference",
                "holdout_wavelengths_nm",
                "spectral_field_family_reference",
                "role_summaries",
                "summaries",
            },
            "achromatic_focus_document_invalid",
        )
        try:
            summaries = tuple(
                AchromaticFocusSummary.from_mapping(item)
                for item in _sequence(values["summaries"])
            )
            if len(summaries) != 2:
                raise ValueError("achromatic_focus_document_invalid")
            focus = cls(
                spectral_field_family_reference=Reference.from_mapping(
                    _mapping(values["spectral_field_family_reference"])
                ),
                evaluation_binding_reference=Reference.from_mapping(
                    _mapping(values["evaluation_binding_reference"])
                ),
                design_wavelengths_nm=tuple(
                    _integer(item) for item in _sequence(values["design_wavelengths_nm"])
                ),
                holdout_wavelengths_nm=tuple(
                    _integer(item) for item in _sequence(values["holdout_wavelengths_nm"])
                ),
                blind_verification_wavelengths_nm=tuple(
                    _integer(item)
                    for item in _sequence(values["blind_verification_wavelengths_nm"])
                ),
                entries=tuple(
                    AchromaticFocusEntry.from_mapping(item)
                    for item in _indexed_values(values["entries"], "entry")
                ),
                summaries=(summaries[0], summaries[1]),
                role_summaries=tuple(
                    AchromaticFocusRoleSummary.from_mapping(item)
                    for item in _sequence(values["role_summaries"])
                ),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("achromatic_focus_document_invalid") from error
        if (
            _text(values["compensated_focal_shift_improvement_m"])
            != _number(focus.compensated_focal_shift_improvement_m)
            or focus.document().to_bytes() != document.to_bytes()
        ):
            raise ValueError("achromatic_focus_document_mismatch")
        return focus


def achromatic_strategies() -> tuple[str, str]:
    """Return the compensated design and its same-contract PB-only baseline."""

    return _ACHROMATIC_STRATEGIES


def assign_continuous_achromatic_aperture(
    target: AchromaticTarget,
    plan: SpectralCellStudyPlan,
    library: SpectralJonesLibrary,
    qualification: SpectralLibraryQualification,
    lattice: Lattice,
    *,
    target_reference: Reference,
    lattice_reference: Reference,
    plan_reference: Reference,
    library_reference: Reference,
    qualification_reference: Reference,
    selection_binding_reference: Reference,
) -> AchromaticAperture:
    """
    Select geometry for delay and orientation for reference-frequency phase.

    The returned layout is physical: neither selection changes with wavelength.
    """

    if not qualification.is_candidate:
        raise ValueError("achromatic_aperture_requires_candidate_library")
    if (
        not reference_matches(target_reference, target.document().to_bytes())
        or not reference_matches(lattice_reference, lattice.document().to_bytes())
        or not reference_matches(plan_reference, plan.document().to_bytes())
        or not reference_matches(library_reference, library.document().to_bytes())
        or not reference_matches(
            qualification_reference,
            qualification.document().to_bytes(),
        )
        or qualification.target_reference != target_reference
        or qualification.plan_reference != plan_reference
        or qualification.library_reference != library_reference
        or library.plan_reference != plan_reference
        or lattice.spacing_nm != plan.period_nm
        or lattice.spacing_source_reference != plan_reference
    ):
        raise ValueError("achromatic_aperture_evidence_mismatch")
    convention = library.convention
    expected_convention = (
        "exp(-i omega t); converted PB phase "
        f"{2 * convention.phase_sign:+d} theta"
    )
    if target.phase_convention != expected_convention:
        raise ValueError("achromatic_aperture_phase_convention_mismatch")
    by_geometry = {item.geometry: item for item in qualification.assessments}
    try:
        eligible = tuple(
            by_geometry[geometry] for geometry in qualification.eligible_geometries
        )
    except KeyError as error:
        raise ValueError("achromatic_aperture_eligible_geometry_mismatch") from error
    if not eligible:
        raise ValueError("achromatic_aperture_library_empty")
    geometries = tuple(item.geometry for item in eligible)
    delays = numpy.asarray(
        [float(item.relative_delay_fs) for item in eligible],
        dtype=numpy.float64,
    )
    reference_phases = numpy.asarray(
        [float(item.reference_phase_rad) for item in eligible],
        dtype=numpy.float64,
    )
    delay_gauge_fs = float(numpy.max(delays))
    focal_length_um = float(target.focal_length_um)
    half_span_nm = lattice.half_span_nm
    coordinates = numpy.array(lattice.coordinates_nm, dtype=numpy.int64, copy=True)
    occupied = numpy.array(lattice.is_occupied, dtype=numpy.bool_, copy=True)
    shape = occupied.shape
    radial_um = numpy.hypot(coordinates[..., 0], coordinates[..., 1]) / 1000
    path_difference_um = numpy.sqrt(focal_length_um**2 + radial_um**2) - focal_length_um
    path_delay_fs = path_difference_um / float(_LIGHT_SPEED_UM_PER_FS)
    required_delay = numpy.zeros(shape, dtype=numpy.float64)
    required_delay[occupied] = delay_gauge_fs - path_delay_fs[occupied]
    geometry_indices = numpy.full(shape, -1, dtype=numpy.int64)
    selected_delay = numpy.zeros(shape, dtype=numpy.float64)
    delay_error = numpy.zeros(shape, dtype=numpy.float64)
    target_phase = numpy.zeros(shape, dtype=numpy.float64)
    physical_rotation_map = numpy.zeros(shape, dtype=numpy.float64)
    realized_phase = numpy.zeros(shape, dtype=numpy.float64)
    propagation_phase = numpy.zeros(shape, dtype=numpy.float64)
    geometric_phase_map = numpy.zeros(shape, dtype=numpy.float64)
    for row, column in zip(*numpy.nonzero(occupied), strict=True):
        required = required_delay[row, column]
        ranked = sorted(
            range(len(eligible)),
            key=lambda index: (
                abs(delays[index] - required),
                -float(eligible[index].minimum_converted_power),
                float(eligible[index].holdout_maximum_residual_rad),
                eligible[index].geometry,
            ),
        )
        selected_index = ranked[0]
        geometry_indices[row, column] = selected_index
        selected_delay[row, column] = delays[selected_index]
        delay_error[row, column] = abs(delays[selected_index] - required)
        phase = float(lattice.target_phase[row, column]) % (2 * math.pi)
        target_phase[row, column] = phase
        orientation = (
            (phase - reference_phases[selected_index])
            / (2 * convention.phase_sign)
        ) % math.pi
        physical_rotation_map[row, column] = orientation
        propagation_phase[row, column] = reference_phases[selected_index] % (
            2 * math.pi
        )
        geometric_phase_map[row, column] = (
            2 * convention.phase_sign * orientation
        ) % (2 * math.pi)
        realized_phase[row, column] = (
            reference_phases[selected_index]
            + 2 * convention.phase_sign * orientation
        ) % (2 * math.pi)
    baseline_assessment = sorted(
        eligible,
        key=lambda item: (
            -float(item.minimum_converted_power),
            -float(item.design_r_squared),
            float(item.holdout_maximum_residual_rad),
            item.geometry,
        ),
    )[0]
    baseline_phase = float(baseline_assessment.reference_phase_rad)
    baseline_orientations = numpy.zeros(shape, dtype=numpy.float64)
    baseline_orientations[occupied] = (
        (target_phase[occupied] - baseline_phase)
        / (2 * convention.phase_sign)
    ) % math.pi
    return AchromaticAperture(
        target_reference=target_reference,
        lattice_reference=lattice_reference,
        plan_reference=plan_reference,
        qualification_reference=qualification_reference,
        library_reference=library_reference,
        selection_binding_reference=selection_binding_reference,
        period_nm=plan.period_nm,
        height_nm=plan.height_nm,
        half_span_nm=half_span_nm,
        footprint=lattice.footprint,
        phase_sign=convention.phase_sign,
        geometries=geometries,
        baseline_geometry=baseline_assessment.geometry,
        adjacency_diagnostics=_form_aperture_adjacency_diagnostics(
            occupied,
            geometry_indices,
            geometries,
        ),
        coordinates_nm=coordinates,
        is_occupied=occupied,
        geometry_indices=geometry_indices,
        orientations_rad=physical_rotation_map,
        baseline_orientations_rad=baseline_orientations,
        required_relative_delay_fs=required_delay,
        selected_relative_delay_fs=selected_delay,
        delay_error_fs=delay_error,
        propagation_reference_phase_rad=propagation_phase,
        geometric_phase_rad=geometric_phase_map,
        target_reference_phase_rad=target_phase,
        realized_reference_phase_rad=realized_phase,
    )


def form_achromatic_aperture_field(
    aperture: AchromaticAperture,
    library: SpectralJonesLibrary,
    *,
    post_freeze_library: PostFreezeJonesLibrary | None = None,
    wavelength_nm: int,
    strategy: str,
    aperture_reference: Reference,
) -> Field:
    """Form one wavelength from the unchanged compensated or PB-only layout."""

    if strategy not in _ACHROMATIC_STRATEGIES:
        raise ValueError("achromatic_field_strategy_invalid")
    if (
        not reference_matches(aperture_reference, aperture.document().to_bytes())
        or aperture.library_reference
        != reference_for(library.document().to_bytes())
        or library.convention.phase_sign != aperture.phase_sign
    ):
        raise ValueError("achromatic_field_evidence_mismatch")
    by_key = {
        (item.geometry, item.wavelength_nm): item for item in library.observations
    }
    if post_freeze_library is not None:
        if (
            post_freeze_library.aperture_reference != aperture_reference
            or post_freeze_library.candidate_library_reference
            != aperture.library_reference
            or not post_freeze_library.is_complete
        ):
            raise ValueError("achromatic_field_post_freeze_evidence_mismatch")
        by_key.update(
            {
                (item.geometry, item.wavelength_nm): item
                for item in post_freeze_library.observations
            }
        )
    if wavelength_nm not in {key[1] for key in by_key}:
        raise ValueError("achromatic_field_wavelength_missing")
    shape = aperture.is_occupied.shape
    converted_values = numpy.zeros(shape, dtype=numpy.complex128)
    retained_values = numpy.zeros(shape, dtype=numpy.complex128)
    observation_sources: list[Reference] = []
    baseline_index = aperture.geometries.index(aperture.baseline_geometry)
    physical_rotation_map = (
        aperture.orientations_rad
        if strategy == _COMPENSATED_STRATEGY
        else aperture.baseline_orientations_rad
    )
    for row, column in zip(*numpy.nonzero(aperture.is_occupied), strict=True):
        geometry_index = (
            int(aperture.geometry_indices[row, column])
            if strategy == _COMPENSATED_STRATEGY
            else baseline_index
        )
        geometry = aperture.geometries[geometry_index]
        try:
            observation = by_key[(geometry, wavelength_nm)]
        except KeyError as error:
            raise ValueError("achromatic_field_observation_missing") from error
        converted, retained = project_circular_channels(
            observation.response,
            library.convention,
        )
        normalization = math.sqrt(
            float(observation.transmitted_power_per_squared_amplitude)
        )
        converted_values[row, column] = (
            converted.complex_value()
            * normalization
            * numpy.exp(
                1j
                * 2
                * aperture.phase_sign
                * physical_rotation_map[row, column]
            )
        )
        retained_values[row, column] = retained.complex_value() * normalization
        observation_sources.extend(observation.source_references)
    converted_name = "left" if library.convention.circular_input == "right" else "right"
    retained_name = library.convention.circular_input
    values = {
        converted_name: _immutable_complex(converted_values),
        retained_name: _immutable_complex(retained_values),
    }
    return Field(
        wavelength_m=wavelength_nm * 1e-9,
        surface=PlaneSurface(0.0, aperture.period_nm * 1e-9, shape),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.CIRCULAR,
        electric_components=tuple(
            FieldComponent(name, values[name])
            for name in ComponentBasis.CIRCULAR.components
        ),
        source_references=tuple(
            dict.fromkeys(
                (
                    aperture_reference,
                    aperture.library_reference,
                    *(
                        ()
                        if post_freeze_library is None
                        else (
                            reference_for(post_freeze_library.document().to_bytes()),
                        )
                    ),
                    *observation_sources,
                )
            )
        ),
        incident_reference_power=float(aperture.site_count),
    )


def form_achromatic_focus(
    family: SpectralFieldFamily,
    entries: tuple[AchromaticFocusEntry, ...],
    *,
    family_reference: Reference,
    evaluation_binding_reference: Reference,
) -> AchromaticFocus:
    """Aggregate complete per-wavelength Focus facts without evaluating again."""

    if not reference_matches(family_reference, family.document().to_bytes()):
        raise ValueError("achromatic_focus_family_reference_mismatch")
    expected = {
        (item.strategy, item.wavelength_nm) for item in family.entries
    }
    if {(item.strategy, item.wavelength_nm) for item in entries} != expected:
        raise ValueError("achromatic_focus_entries_incomplete")
    return AchromaticFocus(
        spectral_field_family_reference=family_reference,
        evaluation_binding_reference=evaluation_binding_reference,
        design_wavelengths_nm=family.design_wavelengths_nm,
        holdout_wavelengths_nm=family.holdout_wavelengths_nm,
        blind_verification_wavelengths_nm=family.blind_verification_wavelengths_nm,
        entries=entries,
        summaries=_focus_summaries(entries),
        role_summaries=_focus_role_summaries(
            entries,
            design_wavelengths_nm=family.design_wavelengths_nm,
            holdout_wavelengths_nm=family.holdout_wavelengths_nm,
            blind_wavelengths_nm=family.blind_verification_wavelengths_nm,
        ),
    )


def _focus_summaries(
    entries: tuple[AchromaticFocusEntry, ...],
) -> tuple[AchromaticFocusSummary, AchromaticFocusSummary]:
    summaries = []
    for strategy in _ACHROMATIC_STRATEGIES:
        focuses = tuple(item.focus for item in entries if item.strategy == strategy)
        if not focuses:
            raise ValueError("achromatic_focus_strategy_missing")
        widths = tuple(
            max(
                _required_width(focus.x_half_maximum.width_m),
                _required_width(focus.y_half_maximum.width_m),
            )
            for focus in focuses
        )
        summaries.append(
            AchromaticFocusSummary(
                strategy=strategy,
                maximum_absolute_focal_shift_m=max(
                    abs(item.focal_shift_m) for item in focuses
                ),
                mean_absolute_focal_shift_m=float(
                    numpy.mean([abs(item.focal_shift_m) for item in focuses])
                ),
                maximum_spot_width_m=max(widths),
                mean_transmitted_fraction=float(
                    numpy.mean([item.transmitted_fraction for item in focuses])
                ),
                mean_focus_efficiency=float(
                    numpy.mean([item.focus_efficiency for item in focuses])
                ),
                maximum_leakage_fraction=max(
                    (
                        0.0
                        if item.leakage is None
                        else item.leakage.transmitted_fraction
                    )
                    for item in focuses
                ),
            )
        )
    return summaries[0], summaries[1]


def _focus_role_summaries(
    entries: tuple[AchromaticFocusEntry, ...],
    *,
    design_wavelengths_nm: tuple[int, ...],
    holdout_wavelengths_nm: tuple[int, ...],
    blind_wavelengths_nm: tuple[int, ...],
) -> tuple[AchromaticFocusRoleSummary, ...]:
    roles = (
        ("design", design_wavelengths_nm),
        ("interleaved_validation", holdout_wavelengths_nm),
        ("blind_verification", blind_wavelengths_nm),
    )
    return tuple(
        AchromaticFocusRoleSummary(
            role=role,
            summary=_focus_summary(
                strategy,
                tuple(
                    item.focus
                    for item in entries
                    if item.strategy == strategy
                    and item.wavelength_nm in wavelengths
                ),
            ),
        )
        for strategy in _ACHROMATIC_STRATEGIES
        for role, wavelengths in roles
    )


def _focus_summary(
    strategy: str,
    focuses: tuple[Focus, ...],
) -> AchromaticFocusSummary:
    if not focuses:
        raise ValueError("achromatic_focus_strategy_missing")
    widths = tuple(
        max(
            _required_width(focus.x_half_maximum.width_m),
            _required_width(focus.y_half_maximum.width_m),
        )
        for focus in focuses
    )
    return AchromaticFocusSummary(
        strategy=strategy,
        maximum_absolute_focal_shift_m=max(abs(item.focal_shift_m) for item in focuses),
        mean_absolute_focal_shift_m=float(numpy.mean([abs(item.focal_shift_m) for item in focuses])),
        maximum_spot_width_m=max(widths),
        mean_transmitted_fraction=float(numpy.mean([item.transmitted_fraction for item in focuses])),
        mean_focus_efficiency=float(numpy.mean([item.focus_efficiency for item in focuses])),
        maximum_leakage_fraction=max(0.0 if item.leakage is None else item.leakage.transmitted_fraction for item in focuses),
    )


def _required_width(value: float | None) -> float:
    if value is None:
        raise ValueError("achromatic_focus_width_incomplete")
    return value


def _immutable_complex(
    values: NDArray[numpy.complexfloating],
) -> NDArray[numpy.complex128]:
    samples = numpy.array(values, dtype="<c16", order="C", copy=True)
    samples.setflags(write=False)
    return samples


def _float_grid(values: NDArray[numpy.floating]) -> list[list[str]]:
    return [[_number(float(value)) for value in row] for row in values]


def _restore_float_grid(value: object) -> NDArray[numpy.float64]:
    rows = _sequence(value)
    return numpy.asarray(
        [[float(_text(item)) for item in _sequence(row)] for row in rows],
        dtype=numpy.float64,
    )


def _number(value: float) -> str:
    return format(value, ".17g")


def form_post_freeze_jones_library(
    plan: SpectralCellStudyPlan,
    aperture: AchromaticAperture,
    candidate_library: SpectralJonesLibrary,
    observations: tuple[SpectralJonesObservation, ...],
    *,
    profile: ResponseQualificationProfile,
    qualification_reference: Reference,
    solver_binding_reference: Reference,
    numerical_incompletion_references: tuple[Reference, ...] = (),
    missing_wavelengths_nm: tuple[int, ...] = (),
    unavailable_reasons: tuple[str, ...] = (),
) -> PostFreezeJonesLibrary:
    """Close one post-freeze observation collection without judging it."""

    aperture_reference = reference_for(aperture.document().to_bytes())
    plan_reference = reference_for(plan.document().to_bytes())
    profile_reference = reference_for(profile.document().to_bytes())
    candidate_library_reference = reference_for(candidate_library.document().to_bytes())
    if (
        aperture.plan_reference != plan_reference
        or aperture.library_reference != candidate_library_reference
        or aperture.qualification_reference != qualification_reference
        or plan.qualification_profile_reference != profile_reference
        or candidate_library.solver_binding_reference != solver_binding_reference
    ):
        raise ValueError("post_freeze_jones_library_context_mismatch")
    return PostFreezeJonesLibrary(
        aperture_reference=aperture_reference,
        profile_reference=profile_reference,
        plan_reference=plan_reference,
        qualification_reference=qualification_reference,
        candidate_library_reference=candidate_library_reference,
        solver_binding_reference=solver_binding_reference,
        blind_wavelengths_nm=plan.blind_verification_wavelengths_nm,
        used_geometries=aperture.used_geometries,
        observations=observations,
        numerical_incompletion_references=numerical_incompletion_references,
        missing_wavelengths_nm=missing_wavelengths_nm,
        unavailable_reasons=unavailable_reasons,
    )


def form_band_verification_evidence(
    plan: SpectralCellStudyPlan,
    aperture: AchromaticAperture,
    candidate_library: SpectralJonesLibrary,
    post_freeze_library: PostFreezeJonesLibrary,
    family: SpectralFieldFamily | None,
    focus: AchromaticFocus | None,
    *,
    profile: ResponseQualificationProfile,
    qualification_reference: Reference,
    family_reference: Reference | None,
    focus_reference: Reference | None,
) -> BandVerificationEvidence:
    """Judge dense spectral phase only after the complete device matrix exists."""

    aperture_reference = reference_for(aperture.document().to_bytes())
    post_freeze_reference = reference_for(post_freeze_library.document().to_bytes())
    profile_reference = reference_for(profile.document().to_bytes())
    if (
        post_freeze_library.aperture_reference != aperture_reference
        or post_freeze_library.profile_reference != profile_reference
        or post_freeze_library.qualification_reference != qualification_reference
    ):
        raise ValueError("band_verification_context_mismatch")
    dense: Decimal | None = None
    curvature: Decimal | None = None
    candidate_origins = {
        item.execution_origin for item in candidate_library.observations
    }
    post_freeze_origins = {
        item.execution_origin for item in post_freeze_library.observations
    }
    if len(post_freeze_origins) > 1 or (
        post_freeze_origins and post_freeze_origins != candidate_origins
    ):
        status = BandVerificationStatus.EVIDENCE_ORIGIN_MISMATCH
    elif post_freeze_library.missing_wavelengths_nm:
        status = BandVerificationStatus.MISSING_BLIND
    elif post_freeze_library.numerical_incompletion_references:
        status = BandVerificationStatus.NUMERICAL_INCOMPLETE
    elif not post_freeze_library.is_complete:
        status = BandVerificationStatus.MISSING_BLIND
    else:
        if (
            family is None
            or focus is None
            or family_reference is None
            or focus_reference is None
            or family.aperture_reference != aperture_reference
            or family.post_freeze_library_reference != post_freeze_reference
            or not reference_matches(family_reference, family.document().to_bytes())
            or focus.spectral_field_family_reference != family_reference
            or not reference_matches(focus_reference, focus.document().to_bytes())
            or family.wavelengths_nm != plan.full_band_wavelengths_nm
            or focus.blind_verification_wavelengths_nm
            != plan.blind_verification_wavelengths_nm
        ):
            raise ValueError("band_verification_complete_matrix_required")
        dense_value, curvature_value = _dense_phase_metrics(
            plan,
            aperture.used_geometries,
            candidate_library,
            post_freeze_library,
        )
        dense = Decimal(str(dense_value))
        curvature = Decimal(str(curvature_value))
        if dense > profile.maximum_dense_phase_residual_rad:
            status = BandVerificationStatus.DENSE_RESIDUAL
        elif curvature > profile.maximum_phase_curvature_rad:
            status = BandVerificationStatus.CURVATURE
        else:
            status = BandVerificationStatus.PASS
    return BandVerificationEvidence(
        status=status,
        aperture_reference=aperture_reference,
        profile_reference=profile_reference,
        qualification_reference=qualification_reference,
        post_freeze_library_reference=post_freeze_reference,
        spectral_field_family_reference=family_reference,
        focus_reference=focus_reference,
        maximum_dense_phase_residual_rad=dense,
        maximum_phase_curvature_rad=curvature,
        reasons=(status.value,),
    )


def _dense_phase_metrics(
    plan: SpectralCellStudyPlan,
    geometries: tuple[SpectralRectangle, ...],
    candidate_library: SpectralJonesLibrary,
    post_freeze_library: PostFreezeJonesLibrary,
) -> tuple[float, float]:
    by_key = {
        (item.geometry, item.wavelength_nm): item
        for item in (
            *candidate_library.observations,
            *post_freeze_library.observations,
        )
    }
    maximum_residual = 0.0
    maximum_curvature = 0.0
    for geometry in geometries:
        design = sorted(plan.design_wavelengths_nm, key=_angular_frequency)
        frequencies = numpy.asarray(
            [_angular_frequency(item) for item in design],
            dtype=numpy.float64,
        )
        design_phases = numpy.unwrap(numpy.asarray([
            _converted_phase(by_key[(geometry, item)], candidate_library.convention)
            for item in design
        ]))
        coefficients = numpy.polyfit(frequencies, design_phases, 1)
        dense_wavelengths = sorted(plan.full_band_wavelengths_nm, key=_angular_frequency)
        dense_phases = numpy.unwrap(numpy.asarray([
            _converted_phase(by_key[(geometry, item)], candidate_library.convention)
            for item in dense_wavelengths
        ]))
        predicted = numpy.polyval(
            coefficients,
            numpy.asarray([_angular_frequency(item) for item in dense_wavelengths]),
        )
        residuals = dense_phases - predicted
        maximum_residual = max(maximum_residual, float(numpy.max(numpy.abs(residuals))))
        maximum_curvature = max(
            maximum_curvature,
            float(numpy.max(numpy.abs(numpy.diff(residuals, n=2)))),
        )
    return maximum_residual, maximum_curvature


def _converted_phase(
    observation: SpectralJonesObservation,
    convention: PolarizationConvention,
) -> float:
    converted = project_circular_channels(observation.response, convention)[0].complex_value()
    return math.atan2(converted.imag, converted.real)


def qualify_spectral_jones_library(
    target: AchromaticTarget,
    plan: SpectralCellStudyPlan,
    library: SpectralJonesLibrary,
    *,
    profile: ResponseQualificationProfile | None = None,
    profile_reference: Reference | None = None,
) -> SpectralLibraryQualification:
    """
    Screen one full complex-Jones library for linear phase, power, and delay.
    """

    if profile is None:
        raise ValueError("response_qualification_profile_required")
    expected_profile_reference = reference_for(profile.document().to_bytes())
    if profile_reference is None:
        profile_reference = expected_profile_reference
    if (
        profile_reference != expected_profile_reference
        or plan.qualification_profile_reference != profile_reference
    ):
        raise ValueError("spectral_qualification_profile_reference_mismatch")
    if not reference_matches(library.plan_reference, plan.document().to_bytes()):
        raise ValueError("spectral_jones_plan_reference_mismatch")
    if any(geometry not in plan.geometries for geometry in library.selected_geometries):
        raise ValueError("spectral_jones_geometry_selection_mismatch")
    target_reference = reference_for(target.document().to_bytes())
    plan_reference = reference_for(plan.document().to_bytes())
    library_reference = reference_for(library.document().to_bytes())
    expected = {
        (geometry, wavelength)
        for geometry in library.selected_geometries
        for wavelength in plan.wavelengths_nm
    }
    observed = {(item.geometry, item.wavelength_nm) for item in library.observations}
    missing = tuple(sorted(expected - observed))
    if missing or observed - expected:
        return SpectralLibraryQualification(
            status=SpectralQualificationStatus.EVIDENCE_INCOMPLETE,
            required_relative_delay_fs=target.required_relative_delay_fs,
            available_relative_delay_span_fs=Decimal(0),
            maximum_reference_phase_gap_rad=None,
            assessments=(),
            eligible_geometries=(),
            reasons=tuple(
                f"{geometry.short_side_nm}x{geometry.long_side_nm}@{wavelength}nm"
                for geometry, wavelength in missing
            )
            or ("spectral_jones_observation_unexpected",),
            target_reference=target_reference,
            plan_reference=plan_reference,
            library_reference=library_reference,
            profile_reference=profile_reference,
            campaign_reference=plan.specification_reference,
            material_binding_reference=plan.material_binding_reference,
        )
    by_geometry = {
        geometry: tuple(
            item for item in library.observations if item.geometry == geometry
        )
        for geometry in library.selected_geometries
    }
    assessments = tuple(
        _assess_spectral_cell(
            geometry,
            by_geometry[geometry],
            plan=plan,
            convention=library.convention,
            reference_wavelength_nm=target.reference_wavelength_nm,
            profile=profile,
        )
        for geometry in library.selected_geometries
    )
    conversion_eligible = tuple(
        item
        for item in assessments
        if item.minimum_converted_power >= profile.minimum_full_band_converted_power
    )
    leakage_eligible = tuple(
        item
        for item in conversion_eligible
        if item.maximum_leakage_power <= profile.maximum_full_band_leakage_power
    )
    design_eligible = tuple(
        item
        for item in leakage_eligible
        if item.design_r_squared >= profile.minimum_design_r_squared
    )
    interleaved_eligible = tuple(
        item
        for item in design_eligible
        if item.holdout_maximum_residual_rad
        <= profile.maximum_interleaved_phase_residual_rad
    )
    eligible = tuple(item for item in interleaved_eligible if item.is_eligible)
    delays = tuple(float(item.relative_delay_fs) for item in eligible)
    available = Decimal(str(max(delays) - min(delays))) if delays else Decimal(0)
    phase_gap = Decimal(str(_maximum_circular_gap(eligible))) if eligible else None
    if not conversion_eligible:
        status = SpectralQualificationStatus.CONVERSION_INSUFFICIENT
    elif not leakage_eligible:
        status = SpectralQualificationStatus.LEAKAGE_INSUFFICIENT
    elif not design_eligible:
        status = SpectralQualificationStatus.LINEARITY_INSUFFICIENT
    elif not interleaved_eligible:
        status = SpectralQualificationStatus.INTERLEAVED_VALIDATION_INSUFFICIENT
    elif phase_gap is not None and phase_gap > profile.maximum_reference_phase_gap_rad:
        status = SpectralQualificationStatus.JOINT_COVERAGE_INSUFFICIENT
    elif available < target.required_relative_delay_fs:
        status = SpectralQualificationStatus.DELAY_SPAN_INSUFFICIENT
    else:
        status = SpectralQualificationStatus.CANDIDATE
    return SpectralLibraryQualification(
        status=status,
        required_relative_delay_fs=target.required_relative_delay_fs,
        available_relative_delay_span_fs=available,
        maximum_reference_phase_gap_rad=phase_gap,
        assessments=assessments,
        eligible_geometries=tuple(item.geometry for item in eligible),
        reasons=(status.value,),
        target_reference=target_reference,
        plan_reference=plan_reference,
        library_reference=library_reference,
        profile_reference=profile_reference,
        campaign_reference=plan.specification_reference,
        material_binding_reference=plan.material_binding_reference,
    )


def _assess_spectral_cell(
    geometry: SpectralRectangle,
    observations: tuple[SpectralJonesObservation, ...],
    *,
    plan: SpectralCellStudyPlan,
    convention: PolarizationConvention,
    reference_wavelength_nm: int,
    profile: ResponseQualificationProfile,
) -> SpectralCellAssessment:
    converted_by_wavelength = {
        item.wavelength_nm: project_circular_channels(item.response, convention)[
            0
        ].complex_value()
        for item in observations
    }
    retained_by_wavelength = {
        item.wavelength_nm: project_circular_channels(item.response, convention)[
            1
        ].complex_value()
        for item in observations
    }
    design_wavelengths = sorted(
        plan.design_wavelengths_nm,
        key=_angular_frequency,
    )
    design_frequencies = numpy.asarray(
        [_angular_frequency(wavelength) for wavelength in design_wavelengths],
        dtype=numpy.float64,
    )
    design_phases = numpy.unwrap(
        numpy.asarray(
            [
                math.atan2(
                    converted_by_wavelength[wavelength].imag,
                    converted_by_wavelength[wavelength].real,
                )
                for wavelength in design_wavelengths
            ]
        )
    )
    coefficients = numpy.polyfit(
        design_frequencies,
        design_phases,
        1,
    )
    design_predicted = numpy.polyval(coefficients, design_frequencies)
    design_residual = design_phases - design_predicted
    total = float(numpy.sum((design_phases - numpy.mean(design_phases)) ** 2))
    residual = float(numpy.sum(design_residual**2))
    maximum_design_residual = float(numpy.max(numpy.abs(design_residual)))
    r_squared = 1.0 if total <= 1e-24 and residual <= 1e-24 else 1.0 - residual / total
    holdout_errors = tuple(
        _cyclic_phase_error(
            math.atan2(
                converted_by_wavelength[wavelength].imag,
                converted_by_wavelength[wavelength].real,
            ),
            float(
                numpy.polyval(
                    coefficients,
                    _angular_frequency(wavelength),
                )
            ),
        )
        for wavelength in plan.holdout_wavelengths_nm
    )
    holdout_residual = max(holdout_errors)
    reference_phase = float(
        numpy.polyval(coefficients, _angular_frequency(reference_wavelength_nm))
        % (2 * math.pi)
    )
    minimum_converted_power = Decimal(
        str(
            min(
                abs(converted_by_wavelength[item.wavelength_nm]) ** 2
                * float(item.transmitted_power_per_squared_amplitude)
                for item in observations
            )
        )
    )
    maximum_leakage_power = Decimal(
        str(
            max(
                abs(retained_by_wavelength[item.wavelength_nm]) ** 2
                * float(item.transmitted_power_per_squared_amplitude)
                for item in observations
            )
        )
    )
    reasons = tuple(
        reason
        for failed, reason in (
            (
                minimum_converted_power
                < profile.minimum_full_band_converted_power,
                "conversion_insufficient",
            ),
            (
                maximum_leakage_power > profile.maximum_full_band_leakage_power,
                "leakage_insufficient",
            ),
            (
                Decimal(str(r_squared)) < profile.minimum_design_r_squared,
                "design_linearity_insufficient",
            ),
            (
                Decimal(str(holdout_residual))
                > profile.maximum_interleaved_phase_residual_rad,
                "interleaved_validation_insufficient",
            ),
        )
        if failed
    )
    return SpectralCellAssessment(
        geometry=geometry,
        relative_delay_fs=Decimal(str(float(coefficients[0]))),
        reference_phase_rad=Decimal(str(reference_phase)),
        design_r_squared=Decimal(str(r_squared)),
        design_maximum_residual_rad=Decimal(str(maximum_design_residual)),
        holdout_maximum_residual_rad=Decimal(str(holdout_residual)),
        minimum_converted_power=minimum_converted_power,
        maximum_leakage_power=maximum_leakage_power,
        is_eligible=not reasons,
        ineligibility_reasons=reasons,
    )


def _transmitted_power_per_squared_amplitude(
    response: JonesResponse,
    surface_x: PeriodicReferenceSurfaceObservation | None,
    surface_y: PeriodicReferenceSurfaceObservation | None,
) -> Decimal:
    if surface_x is None or surface_y is None:
        raise ValueError("spectral_periodic_power_normalization_missing")
    if (
        surface_x.requested_input_basis != "x linear"
        or surface_y.requested_input_basis != "y linear"
        or surface_x.wavelength_m != surface_y.wavelength_m
        or surface_x.output_basis != surface_y.output_basis
        or surface_x.order_regime != surface_y.order_regime
        or surface_x.surface != surface_y.surface
        or surface_x.frame != surface_y.frame
        or surface_x.medium != surface_y.medium
    ):
        raise ValueError("spectral_periodic_power_normalization_context_mismatch")
    columns = (
        (
            response.output_x_from_input_x,
            response.output_y_from_input_x,
            surface_x,
        ),
        (
            response.output_x_from_input_y,
            response.output_y_from_input_y,
            surface_y,
        ),
    )
    factors = []
    for first, second, surface in columns:
        squared_amplitude = sum(
            (
                coefficient.real_part**2 + coefficient.imaginary_part**2
                for coefficient in (first, second)
            ),
            start=Decimal(0),
        )
        transmitted_fraction = (
            surface.transmitted_power / surface.incident_reference_power
        )
        if squared_amplitude == 0:
            if transmitted_fraction != 0:
                raise ValueError("spectral_periodic_power_normalization_invalid")
            continue
        factors.append(transmitted_fraction / squared_amplitude)
    if not factors:
        raise ValueError("spectral_periodic_power_normalization_unresolved")
    normalization = sum(factors, start=Decimal(0)) / len(factors)
    tolerance = max(factors) * Decimal("0.000001")
    if any(abs(factor - normalization) > tolerance for factor in factors):
        raise ValueError("spectral_periodic_power_normalization_mismatch")
    return normalization


def _converted_power(
    observation: SpectralJonesObservation,
    convention: PolarizationConvention,
) -> float:
    converted = project_circular_channels(observation.response, convention)[0]
    return abs(converted.complex_value()) ** 2 * float(
        observation.transmitted_power_per_squared_amplitude
    )


def _require_spectral_screen_context(
    plan: SpectralCellStudyPlan,
    screen: SpectralCellScreen,
    *,
    solver_binding_reference: Reference,
) -> None:
    if (
        not reference_matches(screen.plan_reference, plan.document().to_bytes())
        or screen.solver_binding_reference != solver_binding_reference
        or screen.reference_wavelength_nm != plan.reference_wavelength_nm
        or tuple(item.geometry for item in screen.observations) != plan.geometries
    ):
        raise ValueError("spectral_cell_screen_context_mismatch")


def _cyclic_phase_error(observed: float, predicted: float) -> float:
    difference = observed - predicted
    return abs(math.atan2(math.sin(difference), math.cos(difference)))


def _maximum_circular_gap(assessments: tuple[SpectralCellAssessment, ...]) -> float:
    phases = sorted(float(item.reference_phase_rad) for item in assessments)
    gaps = [right - left for left, right in zip(phases, phases[1:], strict=False)]
    gaps.append(2 * math.pi - phases[-1] + phases[0])
    return max(gaps)


def _angular_frequency(wavelength_nm: int) -> float:
    return 2 * math.pi * _LIGHT_SPEED_NM_PER_FS / wavelength_nm


def _bounded_values(values: tuple[int, ...], count: int) -> tuple[int, ...]:
    if len(values) <= count:
        return values
    positions = tuple(
        round(index * (len(values) - 1) / (count - 1)) for index in range(count)
    )
    return tuple(values[position] for position in positions)


def _coefficient_mapping(value: ComplexCoefficient) -> dict[str, str]:
    return {
        "imaginary_part": format(value.imaginary_part, "f"),
        "real_part": format(value.real_part, "f"),
    }


def _jones_mapping(response: JonesResponse) -> dict[str, object]:
    return {
        "output_x_from_input_x": _coefficient_mapping(response.output_x_from_input_x),
        "output_x_from_input_y": _coefficient_mapping(response.output_x_from_input_y),
        "output_y_from_input_x": _coefficient_mapping(response.output_y_from_input_x),
        "output_y_from_input_y": _coefficient_mapping(response.output_y_from_input_y),
    }


def _jones_from_mapping(value: object) -> JonesResponse:
    values = _closed_mapping(
        value,
        {
            "output_x_from_input_x",
            "output_x_from_input_y",
            "output_y_from_input_x",
            "output_y_from_input_y",
        },
        "spectral_jones_response_invalid",
    )
    return JonesResponse(
        output_x_from_input_x=_coefficient_from_mapping(
            values["output_x_from_input_x"]
        ),
        output_y_from_input_x=_coefficient_from_mapping(
            values["output_y_from_input_x"]
        ),
        output_x_from_input_y=_coefficient_from_mapping(
            values["output_x_from_input_y"]
        ),
        output_y_from_input_y=_coefficient_from_mapping(
            values["output_y_from_input_y"]
        ),
    )


def _coefficient_from_mapping(value: object) -> ComplexCoefficient:
    values = _closed_mapping(
        value,
        {"imaginary_part", "real_part"},
        "spectral_complex_coefficient_invalid",
    )
    try:
        return ComplexCoefficient(
            real_part=Decimal(_text(values["real_part"])),
            imaginary_part=Decimal(_text(values["imaginary_part"])),
        )
    except (TypeError, ValueError) as error:
        raise ValueError("spectral_complex_coefficient_invalid") from error


def _convention_from_mapping(value: object) -> PolarizationConvention:
    values = _closed_mapping(
        value,
        {
            "channel_order",
            "circular_basis",
            "circular_input",
            "linear_basis",
            "phase_sign",
            "propagation_direction",
            "rotation_sign",
            "time_harmonic_sign",
            "viewing_direction",
        },
        "spectral_polarization_convention_invalid",
    )
    linear_basis = tuple(_text(item) for item in _sequence(values["linear_basis"]))
    circular_basis = tuple(_text(item) for item in _sequence(values["circular_basis"]))
    channel_order = tuple(_text(item) for item in _sequence(values["channel_order"]))
    if len(linear_basis) != 2 or len(circular_basis) != 2 or len(channel_order) != 2:
        raise ValueError("spectral_polarization_convention_invalid")
    convention = PolarizationConvention(
        linear_basis=(linear_basis[0], linear_basis[1]),
        circular_basis=(circular_basis[0], circular_basis[1]),
        channel_order=(channel_order[0], channel_order[1]),
        circular_input=_text(values["circular_input"]),
        time_harmonic_sign=_text(values["time_harmonic_sign"]),
        propagation_direction=_text(values["propagation_direction"]),
        viewing_direction=_text(values["viewing_direction"]),
        rotation_sign=_text(values["rotation_sign"]),
    )
    if values["phase_sign"] != convention.phase_sign:
        raise ValueError("spectral_polarization_convention_invalid")
    return convention


def _closed_mapping(
    value: object,
    keys: set[str],
    reason: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(reason)
    return value


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("spectral_mapping_invalid")
    return value


def _indexed_values(value: object, prefix: str) -> tuple[object, ...]:
    values = _mapping(value)
    expected = tuple(f"{prefix}_{index:03d}" for index in range(1, len(values) + 1))
    # Canonical document mappings are lexicographically ordered.  Numeric keys
    # therefore cease to be insertion-ordered once an evidence collection grows
    # beyond 999 items (for example 136 geometries across nine wavelengths).
    if set(values) != set(expected):
        raise ValueError("spectral_indexed_mapping_invalid")
    return tuple(values[key] for key in expected)


def _sequence(value: object) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("spectral_sequence_invalid")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("spectral_text_invalid")
    return value


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("spectral_integer_invalid")
    return value
