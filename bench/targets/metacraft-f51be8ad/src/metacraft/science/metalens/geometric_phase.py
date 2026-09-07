from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import math

from ...authority.protocol import Document, Reference
from ...authority.reference import reference_matches
from ...canonical import canonicalize, encode_bytes
from ..phase import FULL_TURN, canonical_phase, cyclic_distance
from ..result import EvidenceOrigin, require_exact_evidence
from ..study import Caution, Finding, FindingKind, Study

from .aperture import (
    Aperture,
    Cell,
    Ellipse,
    Lattice,
    Rectangle,
    assign_discrete_orientations,
)
from .brief import ControlStrategy
from .design import require_metalens_design
from .height import HeightBasis, HeightChoice, validate_height_choice

POLARIZATION_CONVENTION_SCHEMA = (
    "metacraft.science.metalens.geometric_phase.polarization_convention"
)
JONES_LIBRARY_SCHEMA = "metacraft.science.metalens.geometric_phase.jones_library"
CELL_CHOICE_SCHEMA = "metacraft.science.metalens.geometric_phase.cell_choice"
ORIENTATION_RELATION_SCHEMA = "metacraft.science.metalens.geometric_phase.orientations"
ORIENTATION_SET_SCHEMA = "metacraft.science.metalens.geometric_phase.orientation_set"


HALF_TURN = FULL_TURN / Decimal(2)


@dataclass(frozen=True, slots=True, kw_only=True)
class PbCellQualification:
    """
    States the explicit Jones-response contract for one PB cell choice.

    The qualification is caller-owned scientific policy.  Selection consumes
    its exact thresholds; it never manufactures a threshold from the observed
    library or from a benchmark value.
    """

    name: str
    minimum_transmitted_power: Decimal | None = None
    minimum_converted_power: Decimal | None = None
    maximum_retained_power: Decimal | None = None
    minimum_total_transmitted_power: Decimal | None = None
    maximum_cross_coupling_power: Decimal | None = None
    maximum_half_wave_retardance_error_rad: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("pb_cell_qualification_name_invalid")
        if (
            self.minimum_transmitted_power is None
            and self.minimum_total_transmitted_power is None
        ):
            raise ValueError("pb_cell_qualification_threshold_invalid")
        if (
            self.minimum_transmitted_power is not None
            and self.minimum_total_transmitted_power is not None
            and self.minimum_transmitted_power != self.minimum_total_transmitted_power
        ):
            raise ValueError("pb_cell_qualification_threshold_conflict")
        if self.minimum_converted_power is None or self.maximum_retained_power is None:
            raise ValueError("pb_cell_qualification_threshold_invalid")
        power_thresholds = (
            self.minimum_transmitted_power,
            self.minimum_converted_power,
            self.maximum_retained_power,
            self.minimum_total_transmitted_power,
            self.maximum_cross_coupling_power,
        )
        if any(
            not _valid_qualification_threshold(value) for value in power_thresholds
        ) or (
            self.maximum_half_wave_retardance_error_rad is not None
            and (
                not isinstance(self.maximum_half_wave_retardance_error_rad, Decimal)
                or not self.maximum_half_wave_retardance_error_rad.is_finite()
                or self.maximum_half_wave_retardance_error_rad < 0
                or self.maximum_half_wave_retardance_error_rad > FULL_TURN
            )
        ):
            raise ValueError("pb_cell_qualification_threshold_invalid")

    def accepts(
        self,
        *,
        converted_power: Decimal,
        retained_power: Decimal,
        total_transmitted_power: Decimal | None = None,
        cross_coupling_power: Decimal | None = None,
        half_wave_retardance_error_rad: Decimal | None = None,
    ) -> bool:
        """
        Apply the complete transmitted, converted, and retained-power gate.
        """

        total = (
            converted_power + retained_power
            if total_transmitted_power is None
            else total_transmitted_power
        )
        minimum_total = (
            self.minimum_transmitted_power
            if self.minimum_total_transmitted_power is None
            else self.minimum_total_transmitted_power
        )
        if (
            minimum_total is None
            or self.minimum_converted_power is None
            or self.maximum_retained_power is None
        ):
            return False
        if not (
            total >= minimum_total
            and converted_power >= self.minimum_converted_power
            and retained_power <= self.maximum_retained_power
        ):
            return False
        if self.maximum_cross_coupling_power is not None:
            if (
                cross_coupling_power is None
                or cross_coupling_power > self.maximum_cross_coupling_power
            ):
                return False
        if self.maximum_half_wave_retardance_error_rad is not None:
            if (
                half_wave_retardance_error_rad is None
                or half_wave_retardance_error_rad
                > self.maximum_half_wave_retardance_error_rad
            ):
                return False
        return True

    def as_mapping(self) -> dict[str, object]:
        """
        Retain the exact qualification contract beside the selected cell.
        """

        return {
            "kind": "qualified PB cell response",
            "maximum_cross_coupling_power": _format_optional(
                self.maximum_cross_coupling_power
            ),
            "maximum_half_wave_retardance_error_rad": _format_optional(
                self.maximum_half_wave_retardance_error_rad
            ),
            "maximum_retained_power": format(self.maximum_retained_power, "f"),
            "minimum_converted_power": format(self.minimum_converted_power, "f"),
            "minimum_total_transmitted_power": _format_optional(
                self.minimum_total_transmitted_power
            ),
            "minimum_transmitted_power": _format_optional(
                self.minimum_transmitted_power
            ),
            "name": self.name,
        }


@dataclass(frozen=True, slots=True)
class LegacyPbResponseRanking:
    """
    Marks the historical rank-without-qualification compatibility path.

    This value is deliberately stored in ``CellChoice``.  A historical
    result therefore cannot be mistaken for a choice that passed a response
    qualification.
    """

    kind: str = "legacy PB response ranking without qualification"

    def __post_init__(self) -> None:
        if self.kind != "legacy PB response ranking without qualification":
            raise ValueError("legacy_pb_response_ranking_invalid")

    def as_mapping(self) -> dict[str, str]:
        return {"kind": self.kind}


LEGACY_PB_RESPONSE_RANKING = LegacyPbResponseRanking()
PbCellSelection = PbCellQualification | LegacyPbResponseRanking


@dataclass(frozen=True, slots=True)
class ComplexCoefficient:
    """
    Keeps one complex coefficient canonical and finite.
    """

    real_part: Decimal
    imaginary_part: Decimal

    def __post_init__(self) -> None:
        if not self.real_part.is_finite() or not self.imaginary_part.is_finite():
            raise ValueError("complex_coefficient_not_finite")

    def complex_value(self) -> complex:
        """
        Return this coefficient as one complex value.
        """
        return complex(float(self.real_part), float(self.imaginary_part))


@dataclass(frozen=True, slots=True)
class JonesResponse:
    """
    Retains the complete linear Jones response in the declared basis.
    """

    output_x_from_input_x: ComplexCoefficient
    output_y_from_input_x: ComplexCoefficient
    output_x_from_input_y: ComplexCoefficient
    output_y_from_input_y: ComplexCoefficient


def project_circular_channels(
    response: JonesResponse,
    convention: PolarizationConvention,
) -> tuple[ComplexCoefficient, ComplexCoefficient]:
    """
    Project one complete linear Jones matrix into converted/retained PB channels.
    """

    scale = 1 / math.sqrt(2)
    input_sign = -1j if convention.circular_input == "right" else 1j
    input_x = complex(scale)
    input_y = input_sign * scale
    output_x = (
        response.output_x_from_input_x.complex_value() * input_x
        + response.output_x_from_input_y.complex_value() * input_y
    )
    output_y = (
        response.output_y_from_input_x.complex_value() * input_x
        + response.output_y_from_input_y.complex_value() * input_y
    )
    retained = scale * output_x - input_sign * scale * output_y
    converted = scale * output_x + input_sign * scale * output_y
    return (
        ComplexCoefficient(
            Decimal(str(converted.real)),
            Decimal(str(converted.imag)),
        ),
        ComplexCoefficient(
            Decimal(str(retained.real)),
            Decimal(str(retained.imag)),
        ),
    )


@dataclass(frozen=True, slots=True)
class PolarizationConvention:
    """
    Freezes the Jones and circular-basis sign conventions.
    """

    linear_basis: tuple[str, str] = ("x", "y")
    circular_basis: tuple[str, str] = ("right", "left")
    channel_order: tuple[str, str] = ("converted", "retained")
    circular_input: str = "right"
    time_harmonic_sign: str = "negative"
    propagation_direction: str = "positive_z"
    viewing_direction: str = "along_propagation"
    rotation_sign: str = "counterclockwise"

    def __post_init__(self) -> None:
        if self.circular_input not in {"left", "right"}:
            raise ValueError("circular_input_invalid")
        fixed = {
            "linear_basis": (self.linear_basis, ("x", "y")),
            "circular_basis": (
                self.circular_basis,
                ("right", "left"),
            ),
            "channel_order": (
                self.channel_order,
                ("converted", "retained"),
            ),
            "time_harmonic_sign": (self.time_harmonic_sign, "negative"),
            "propagation_direction": (
                self.propagation_direction,
                "positive_z",
            ),
            "viewing_direction": (
                self.viewing_direction,
                "along_propagation",
            ),
            "rotation_sign": (self.rotation_sign, "counterclockwise"),
        }
        for name, (actual, supported) in fixed.items():
            if actual != supported:
                raise ValueError(f"{name}_unsupported")

    @property
    def phase_sign(self) -> int:
        """
        State how positive physical rotation changes converted phase.
        """

        handedness = 1 if self.circular_input == "right" else -1
        rotation = 1 if self.rotation_sign == "counterclockwise" else -1
        return handedness * rotation

    def as_mapping(self) -> dict[str, object]:
        """
        Return the declared polarization convention.
        """
        return {
            "channel_order": self.channel_order,
            "circular_basis": self.circular_basis,
            "circular_input": self.circular_input,
            "linear_basis": self.linear_basis,
            "phase_sign": self.phase_sign,
            "propagation_direction": self.propagation_direction,
            "rotation_sign": self.rotation_sign,
            "time_harmonic_sign": self.time_harmonic_sign,
            "viewing_direction": self.viewing_direction,
        }

    def document(self) -> Document:
        """
        Form the canonical polarization-convention document.
        """
        return Document(
            POLARIZATION_CONVENTION_SCHEMA,
            self.as_mapping(),
        )


@dataclass(frozen=True, slots=True)
class JonesCell:
    """
    Projects one Jones response into converted and retained channels.
    """

    cell: Cell
    jones: JonesResponse
    converted: ComplexCoefficient
    converted_phase: Decimal
    converted_power: Decimal
    retained: ComplexCoefficient
    retained_phase: Decimal
    retained_power: Decimal
    source_references: tuple[Reference, Reference]
    execution_origin: EvidenceOrigin

    def __post_init__(self) -> None:
        if not all(
            value.is_finite()
            for value in (
                self.converted_phase,
                self.converted_power,
                self.retained_phase,
                self.retained_power,
            )
        ):
            raise ValueError("jones_cell_response_not_finite")
        if self.converted_power < 0 or self.retained_power < 0:
            raise ValueError("jones_cell_power_invalid")
        if len(set(self.source_references)) != 2:
            raise ValueError("jones_cell_basis_evidence_incomplete")
        object.__setattr__(
            self,
            "converted_phase",
            canonical_phase(self.converted_phase),
        )
        object.__setattr__(
            self,
            "retained_phase",
            canonical_phase(self.retained_phase),
        )

    @property
    def candidate(self) -> str:
        """
        Preserve the natural artifact name at the solver boundary.
        """

        return _cell_name(self.cell)

    @property
    def total_transmitted_power(self) -> Decimal:
        """
        Return the admitted useful-plus-retained transmitted power.
        """

        return self.converted_power + self.retained_power

    @property
    def cross_coupling_power(self) -> Decimal:
        """
        Return linear-basis off-diagonal Jones power.
        """

        return Decimal(
            str(
                abs(self.jones.output_y_from_input_x.complex_value()) ** 2
                + abs(self.jones.output_x_from_input_y.complex_value()) ** 2
            )
        )

    @property
    def half_wave_retardance_error_rad(self) -> Decimal:
        """
        Return the wrapped phase error from an ideal half-wave delay.
        """

        return cyclic_distance(
            canonical_phase(self.retained_phase - self.converted_phase),
            FULL_TURN / Decimal(2),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class JonesLibrary:
    """
    Holds anisotropic responses under one polarization convention.

    Identity follows the binding, height choice, convention, and admitted
    source references; no route name is carried.
    """

    cells: tuple[JonesCell, ...]
    binding_reference: Reference
    height_choice_reference: Reference
    convention: PolarizationConvention
    convention_reference: Reference
    evidence_reference: Reference
    source_references: tuple[Reference, ...]

    def __post_init__(self) -> None:
        """
        Keep one exact fixed-height geometric evidence closure.
        """

        if not self.cells:
            raise ValueError("jones_library_empty")
        if not self.source_references:
            raise ValueError("jones_library_sources_empty")
        if not reference_matches(
            self.convention_reference,
            self.convention.document().to_bytes(),
        ):
            raise ValueError("polarization_convention_reference_mismatch")
        if (
            tuple(
                reference for cell in self.cells for reference in cell.source_references
            )
            != self.source_references
        ):
            raise ValueError("jones_library_sources_mismatch")
        if len({cell.cell.identity for cell in self.cells}) != len(self.cells):
            raise ValueError("jones_library_cell_duplicate")
        if len({cell.cell.height_nm for cell in self.cells}) != 1:
            raise ValueError("jones_library_height_mixed")
        if len({cell.cell.period_nm for cell in self.cells}) != 1:
            raise ValueError("jones_library_period_mixed")
        materials = {(cell.cell.atom, cell.cell.substrate) for cell in self.cells}
        if len(materials) != 1:
            raise ValueError("jones_library_material_mixed")
        if len({cell.execution_origin for cell in self.cells}) != 1:
            raise ValueError("jones_library_execution_mixed")
        if len(set(self.source_references)) != len(self.source_references):
            raise ValueError("jones_library_evidence_duplicate")
        if not reference_matches(
            self.evidence_reference,
            self.document().to_bytes(),
        ):
            raise ValueError("jones_library_reference_mismatch")

    def document(self) -> Document:
        """
        Return the exact fixed-height Jones library named by this object.
        """

        return self.document_from(
            cells=self.cells,
            binding_reference=self.binding_reference,
            height_choice_reference=self.height_choice_reference,
            convention=self.convention,
            convention_reference=self.convention_reference,
            source_references=self.source_references,
        )

    @classmethod
    def document_from(
        cls,
        *,
        cells: tuple[JonesCell, ...],
        binding_reference: Reference,
        height_choice_reference: Reference,
        convention: PolarizationConvention,
        convention_reference: Reference,
        source_references: tuple[Reference, ...],
    ) -> Document:
        """
        Form one canonical Jones library before authority admission.
        """

        return Document(
            JONES_LIBRARY_SCHEMA,
            {
                "binding_reference": binding_reference.as_mapping(),
                "cells": {
                    cell.cell.identity: _jones_cell_mapping(cell) for cell in cells
                },
                "convention": convention.as_mapping(),
                "convention_reference": convention_reference.as_mapping(),
                "height_choice_reference": (height_choice_reference.as_mapping()),
                "source_references": {
                    cell.candidate: {
                        basis: reference.as_mapping()
                        for basis, reference in zip(
                            ("x", "y"),
                            cell.source_references,
                            strict=True,
                        )
                    }
                    for cell in cells
                },
            },
        )

    @property
    def execution_origin(self) -> EvidenceOrigin:
        """
        Return the common execution origin of every Jones cell.
        """

        return self.cells[0].execution_origin


@dataclass(frozen=True, slots=True, kw_only=True)
class CellChoice:
    """
    Records the deterministic anisotropic cell choice.

    Identity follows the cell, response, and admitted evidence closure;
    no route name is carried.
    """

    cell: Cell
    jones: JonesResponse
    converted: ComplexCoefficient
    converted_phase: Decimal
    retained: ComplexCoefficient
    retained_phase: Decimal
    useful_power: Decimal
    leakage_power: Decimal
    loss: Decimal
    binding_reference: Reference
    height_domain_reference: Reference
    height_basis: HeightBasis
    height_choice_reference: Reference
    library_reference: Reference
    convention: PolarizationConvention
    convention_reference: Reference
    source_references: tuple[Reference, Reference]
    cautions: tuple[Caution, ...]
    execution_origin: EvidenceOrigin
    selection_contract: PbCellSelection

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "converted_phase",
            canonical_phase(self.converted_phase),
        )
        object.__setattr__(
            self,
            "retained_phase",
            canonical_phase(self.retained_phase),
        )
        if any(
            caution.source_reference != self.height_domain_reference
            for caution in self.cautions
        ):
            raise ValueError("cell_choice_caution_source_mismatch")
        if len(set(self.source_references)) != 2:
            raise ValueError("cell_choice_basis_evidence_incomplete")
        if not isinstance(
            self.selection_contract,
            (PbCellQualification, LegacyPbResponseRanking),
        ):
            raise ValueError("cell_choice_selection_contract_invalid")
        if (
            not self.useful_power.is_finite()
            or not self.leakage_power.is_finite()
            or not self.loss.is_finite()
            or self.useful_power < 0
            or self.leakage_power < 0
            or self.loss != self.leakage_power - self.useful_power
        ):
            raise ValueError("cell_choice_power_invalid")
        if isinstance(
            self.selection_contract,
            PbCellQualification,
        ) and not self.selection_contract.accepts(
            converted_power=self.useful_power,
            retained_power=self.leakage_power,
            total_transmitted_power=self.useful_power + self.leakage_power,
            cross_coupling_power=self.cross_coupling_power,
            half_wave_retardance_error_rad=self.half_wave_retardance_error_rad,
        ):
            raise ValueError("cell_choice_response_unqualified")

    @property
    def candidate(self) -> str:
        """
        Return the selected cell's natural artifact name.
        """
        return _cell_name(self.cell)

    @property
    def total_transmitted_power(self) -> Decimal:
        """
        Return the selected cell's useful-plus-retained power.
        """

        return self.useful_power + self.leakage_power

    @property
    def cross_coupling_power(self) -> Decimal:
        """
        Return the selected cell's linear-basis off-diagonal power.
        """

        return Decimal(
            str(
                abs(self.jones.output_y_from_input_x.complex_value()) ** 2
                + abs(self.jones.output_x_from_input_y.complex_value()) ** 2
            )
        )

    @property
    def half_wave_retardance_error_rad(self) -> Decimal:
        """
        Return the selected cell's wrapped half-wave phase error.
        """

        return cyclic_distance(
            canonical_phase(self.retained_phase - self.converted_phase),
            FULL_TURN / Decimal(2),
        )

    def canonical_bytes(self) -> bytes:
        """
        Return the canonical cell-choice document bytes.
        """

        return self.document().to_bytes()

    def document(self) -> Document:
        """
        Wrap this exact cell choice for authority admission.
        """

        values = canonicalize(self)
        cell = canonicalize(self.cell)
        cell["geometry"] = self.cell.geometry.as_mapping()
        values["cell"] = cell
        values["jones"] = _jones_response_mapping(self.jones)
        values["converted"] = _coefficient_mapping(self.converted)
        values["retained"] = _coefficient_mapping(self.retained)
        values["convention"] = canonicalize(self.convention.as_mapping())
        values["selection_contract"] = canonicalize(
            self.selection_contract.as_mapping()
        )
        values["source_references"] = {
            basis: reference.as_mapping()
            for basis, reference in zip(
                ("x", "y"),
                self.source_references,
                strict=True,
            )
        }
        return Document(CELL_CHOICE_SCHEMA, values)

    def reference_matches(self, reference: Reference) -> bool:
        """
        Verify that one reference names this exact cell choice.
        """

        return reference_matches(reference, self.document().to_bytes())


def choose_cell(
    study: Study,
    height: HeightChoice,
    library: JonesLibrary,
    *,
    height_choice_reference: Reference,
    qualification: PbCellQualification | None = None,
) -> CellChoice | Finding:
    """
    Filter by one explicit PB cell qualification, then rank deterministically.
    """

    if qualification is None:
        raise TypeError("pb_cell_qualification_required")
    if not isinstance(qualification, PbCellQualification):
        raise TypeError("pb_cell_qualification_invalid")
    return _choose_cell(
        study,
        height,
        library,
        height_choice_reference=height_choice_reference,
        selection_contract=qualification,
    )


def choose_cell_by_legacy_ranking(
    study: Study,
    height: HeightChoice,
    library: JonesLibrary,
    *,
    height_choice_reference: Reference,
) -> CellChoice:
    """
    Preserve the historical unqualified ranking under an auditable name.

    New scientific work must call ``choose_cell`` with an explicit cell
    qualification.  This compatibility path exists only for the current
    compiled route until that route carries a qualification contract.
    """

    selected = _choose_cell(
        study,
        height,
        library,
        height_choice_reference=height_choice_reference,
        selection_contract=LEGACY_PB_RESPONSE_RANKING,
    )
    if isinstance(selected, Finding):
        raise RuntimeError("legacy_pb_response_ranking_refused")
    return selected


def _choose_cell(
    study: Study,
    height: HeightChoice,
    library: JonesLibrary,
    *,
    height_choice_reference: Reference,
    selection_contract: PbCellSelection,
) -> CellChoice | Finding:
    """
    Validate one library once and apply its declared selection contract.
    """

    if (
        require_metalens_design(study).control_strategy
        is not ControlStrategy.GEOMETRIC_PHASE
    ):
        raise ValueError("geometric_study_required")
    validate_height_choice(
        study,
        height,
        choice_reference=height_choice_reference,
    )
    facts = {fact.claim: fact for fact in study.evidence}
    required = {
        "height_choice",
        "polarization_convention",
        "jones_library",
    }
    if not required.issubset(facts):
        raise ValueError("cell_choice_evidence_incomplete")
    if facts["jones_library"].reference != library.evidence_reference:
        raise ValueError("jones_library_not_admitted")
    if facts["polarization_convention"].reference != library.convention_reference:
        raise ValueError("polarization_convention_mismatch")
    if facts["jones_library"].binding_reference != library.binding_reference:
        raise ValueError("jones_library_binding_mismatch")
    if library.height_choice_reference != height_choice_reference:
        raise ValueError("jones_library_height_choice_mismatch")
    if any(cell.cell.height_nm != height.height_nm for cell in library.cells):
        raise ValueError("jones_library_height_mismatch")
    if any(
        cell.cell.period_nm != height.period_nm
        or _short_axis(cell.cell) < height.minimum_feature_nm
        or _long_axis(cell.cell) > height.maximum_feature_nm
        or (_short_axis(cell.cell) - height.minimum_feature_nm)
        % height.dimension_step_nm
        or (_long_axis(cell.cell) - height.minimum_feature_nm)
        % height.dimension_step_nm
        for cell in library.cells
    ):
        raise ValueError("jones_library_fabrication_mismatch")
    qualified_cells = tuple(
        cell
        for cell in library.cells
        if not isinstance(selection_contract, PbCellQualification)
        or selection_contract.accepts(
            converted_power=cell.converted_power,
            retained_power=cell.retained_power,
            total_transmitted_power=cell.total_transmitted_power,
            cross_coupling_power=cell.cross_coupling_power,
            half_wave_retardance_error_rad=cell.half_wave_retardance_error_rad,
        )
    )
    if not qualified_cells:
        return Finding(
            claim="cell_choice",
            kind=FindingKind.REFUSAL,
            needs=("pb_cell_response_unqualified",),
            record_references=(library.evidence_reference,),
        )
    candidates = []
    for cell in qualified_cells:
        loss = cell.retained_power - cell.converted_power
        candidates.append(
            CellChoice(
                cell=cell.cell,
                jones=cell.jones,
                converted=cell.converted,
                converted_phase=cell.converted_phase,
                retained=cell.retained,
                retained_phase=cell.retained_phase,
                useful_power=cell.converted_power,
                leakage_power=cell.retained_power,
                loss=loss,
                binding_reference=library.binding_reference,
                height_domain_reference=height.domain_reference,
                height_basis=height.basis,
                height_choice_reference=height_choice_reference,
                library_reference=library.evidence_reference,
                convention=library.convention,
                convention_reference=library.convention_reference,
                source_references=cell.source_references,
                cautions=height.cautions,
                execution_origin=library.execution_origin,
                selection_contract=selection_contract,
            )
        )
    return min(
        candidates,
        key=lambda item: (
            item.loss,
            -item.useful_power,
            _long_axis(item.cell) * _short_axis(item.cell),
            _long_axis(item.cell),
            _short_axis(item.cell),
        ),
    )


def _long_axis(cell: Cell) -> int:
    if isinstance(cell.geometry, Rectangle):
        return cell.geometry.long_side_nm
    if isinstance(cell.geometry, Ellipse):
        return cell.geometry.major_axis_nm
    raise ValueError("anisotropic_cell_required")


def _short_axis(cell: Cell) -> int:
    if isinstance(cell.geometry, Rectangle):
        return cell.geometry.short_side_nm
    if isinstance(cell.geometry, Ellipse):
        return cell.geometry.minor_axis_nm
    raise ValueError("anisotropic_cell_required")


def _cell_name(cell: Cell) -> str:
    if isinstance(cell.geometry, Rectangle):
        dimensions = (
            f"length-{cell.geometry.long_side_nm:04d}nm-"
            f"width-{cell.geometry.short_side_nm:04d}nm"
        )
    elif isinstance(cell.geometry, Ellipse):
        dimensions = (
            f"major-{cell.geometry.major_axis_nm:04d}nm-"
            f"minor-{cell.geometry.minor_axis_nm:04d}nm"
        )
    else:
        raise ValueError("anisotropic_cell_required")
    return (
        f"{cell.shape.replace(' ', '-')}-height-{cell.height_nm:04d}nm-" f"{dimensions}"
    )


def _jones_cell_mapping(cell: JonesCell) -> dict[str, object]:
    values = canonicalize(cell)
    cell_values = canonicalize(cell.cell)
    cell_values["geometry"] = cell.cell.geometry.as_mapping()
    values["cell"] = cell_values
    values["jones"] = _jones_response_mapping(cell.jones)
    values["converted"] = _coefficient_mapping(cell.converted)
    values["retained"] = _coefficient_mapping(cell.retained)
    values["source_references"] = {
        basis: reference.as_mapping()
        for basis, reference in zip(
            ("x", "y"),
            cell.source_references,
            strict=True,
        )
    }
    return values


def _jones_response_mapping(
    response: JonesResponse,
) -> dict[str, dict[str, str]]:
    return {
        "output_x_from_input_x": _coefficient_mapping(response.output_x_from_input_x),
        "output_y_from_input_x": _coefficient_mapping(response.output_y_from_input_x),
        "output_x_from_input_y": _coefficient_mapping(response.output_x_from_input_y),
        "output_y_from_input_y": _coefficient_mapping(response.output_y_from_input_y),
    }


def _coefficient_mapping(
    coefficient: ComplexCoefficient,
) -> dict[str, str]:
    return {
        "real": format(coefficient.real_part, "f"),
        "imaginary": format(coefficient.imaginary_part, "f"),
    }


@dataclass(frozen=True, slots=True)
class OrientationRelation:
    """
    Relates continuous physical orientation to converted geometric phase.
    """

    cell_id: str
    converted_phase: Decimal
    phase_sign: int
    cell_choice_reference: Reference
    binding_reference: Reference
    library_reference: Reference
    convention_reference: Reference
    source_references: tuple[Reference, Reference]

    def __post_init__(self) -> None:
        """
        Keep the orientation law finite and backed by both basis responses.
        """

        object.__setattr__(
            self,
            "converted_phase",
            canonical_phase(self.converted_phase),
        )
        if self.phase_sign not in {-1, 1}:
            raise ValueError("orientation_phase_sign_invalid")
        if not self.cell_id or len(set(self.source_references)) != 2:
            raise ValueError("orientation_evidence_incomplete")

    def for_phase(self, target_phase: Decimal) -> Decimal:
        """
        Return the continuous physical orientation for one target phase.
        """

        target = canonical_phase(target_phase)
        return _normalize_orientation(
            (target - self.converted_phase) / Decimal(2 * self.phase_sign)
        )

    def realized_phase(self, orientation: Decimal) -> Decimal:
        """
        Return the converted phase established by one physical orientation.
        """

        if not orientation.is_finite():
            raise ValueError("orientation_not_finite")
        normalized = _normalize_orientation(orientation)
        return canonical_phase(
            self.converted_phase + Decimal(2 * self.phase_sign) * normalized
        )

    @property
    def identity(self) -> str:
        """
        Identify this exact continuous relation and its evidence.
        """

        return self.identity_without_recursion

    def as_mapping(self) -> dict[str, object]:
        """
        Return the continuous relation without fabricated phase levels.
        """

        return {
            "binding_reference": self.binding_reference.as_mapping(),
            "cell_choice_reference": self.cell_choice_reference.as_mapping(),
            "cell_id": self.cell_id,
            "convention_reference": self.convention_reference.as_mapping(),
            "converted_phase": format(self.converted_phase, "f"),
            "identity": self.identity_without_recursion,
            "library_reference": self.library_reference.as_mapping(),
            "phase_sign": self.phase_sign,
            "source_references": {
                basis: reference.as_mapping()
                for basis, reference in zip(
                    ("x", "y"),
                    self.source_references,
                    strict=True,
                )
            },
        }

    @property
    def identity_without_recursion(self) -> str:
        """
        Identify the relation without embedding its identity into itself.
        """

        return _identity(
            encode_bytes(
                {
                    "binding_reference": self.binding_reference,
                    "cell_choice_reference": self.cell_choice_reference,
                    "cell_id": self.cell_id,
                    "convention_reference": self.convention_reference,
                    "converted_phase": format(self.converted_phase, "f"),
                    "library_reference": self.library_reference,
                    "phase_sign": self.phase_sign,
                    "source_references": {
                        basis: reference
                        for basis, reference in zip(
                            ("x", "y"),
                            self.source_references,
                            strict=True,
                        )
                    },
                }
            )
        )

    def document(self) -> Document:
        """
        Wrap the analytic orientation relation for authority admission.
        """

        return Document(
            ORIENTATION_RELATION_SCHEMA,
            self.as_mapping(),
        )

    def reference_matches(self, reference: Reference) -> bool:
        """
        Verify that a reference names this exact orientation relation.
        """

        return reference_matches(reference, self.document().to_bytes())

    @classmethod
    def from_document(cls, document: Document) -> OrientationRelation:
        """
        Restore one continuous relation without deriving it again.
        """

        if document.schema_identifier != ORIENTATION_RELATION_SCHEMA:
            raise ValueError("orientations_schema_invalid")
        values = _mapping(document.values, "orientations_document_invalid")
        if set(values) != {
            "binding_reference",
            "cell_choice_reference",
            "cell_id",
            "convention_reference",
            "converted_phase",
            "identity",
            "library_reference",
            "phase_sign",
            "source_references",
        }:
            raise ValueError("orientations_document_invalid")
        sources = _mapping(
            values["source_references"],
            "orientations_document_invalid",
        )
        if set(sources) != {"x", "y"}:
            raise ValueError("orientations_document_invalid")
        restored = cls(
            cell_id=str(values["cell_id"]),
            converted_phase=Decimal(str(values["converted_phase"])),
            phase_sign=int(str(values["phase_sign"])),
            cell_choice_reference=_reference(values["cell_choice_reference"]),
            binding_reference=_reference(values["binding_reference"]),
            library_reference=_reference(values["library_reference"]),
            convention_reference=_reference(values["convention_reference"]),
            source_references=(
                _reference(sources["x"]),
                _reference(sources["y"]),
            ),
        )
        if (
            restored.identity != values["identity"]
            or restored.document().to_bytes() != document.to_bytes()
        ):
            raise ValueError("orientations_document_mismatch")
        return restored


@dataclass(frozen=True, slots=True)
class OrientationState:
    """
    Names one ordered physical rotation in a fabrication orientation set.
    """

    index: int
    target_phase: Decimal
    orientation_rad: Decimal
    realized_phase: Decimal

    def __post_init__(self) -> None:
        if self.index < 0 or not self.orientation_rad.is_finite():
            raise ValueError("orientation_state_invalid")
        if self.orientation_rad < 0 or self.orientation_rad >= HALF_TURN:
            raise ValueError("orientation_state_invalid")
        object.__setattr__(
            self,
            "target_phase",
            canonical_phase(self.target_phase),
        )
        object.__setattr__(
            self,
            "realized_phase",
            canonical_phase(self.realized_phase),
        )

    def as_mapping(self) -> dict[str, object]:
        """
        Return one fabrication rotation in canonical order.
        """

        return {
            "index": self.index,
            "orientation_rad": format(self.orientation_rad, "f"),
            "realized_phase": format(self.realized_phase, "f"),
            "target_phase": format(self.target_phase, "f"),
        }


@dataclass(frozen=True, slots=True)
class OrientationSet:
    """
    Holds one independently comparable geometric-phase fabrication set.
    """

    count: int
    cell_id: str
    converted_phase: Decimal
    phase_sign: int
    orientation_relation_identity: str
    orientation_relation_reference: Reference
    states: tuple[OrientationState, ...]

    def __post_init__(self) -> None:
        if self.count not in {8, 12, 16}:
            raise ValueError("orientation_count_unsupported")
        if tuple(state.index for state in self.states) != tuple(range(self.count)):
            raise ValueError("orientation_states_incomplete")
        object.__setattr__(
            self,
            "converted_phase",
            canonical_phase(self.converted_phase),
        )
        if self.phase_sign not in {-1, 1}:
            raise ValueError("orientation_phase_sign_invalid")
        for state in self.states:
            target = FULL_TURN * Decimal(state.index) / Decimal(self.count)
            if cyclic_distance(state.target_phase, target) > Decimal("1e-24"):
                raise ValueError("orientation_target_invalid")
            expected = canonical_phase(
                self.converted_phase
                + Decimal(2 * self.phase_sign) * state.orientation_rad
            )
            if cyclic_distance(state.realized_phase, expected) > Decimal(
                "1e-24"
            ) or cyclic_distance(state.realized_phase, target) > Decimal("1e-24"):
                raise ValueError("orientation_relation_invalid")
        if not self.cell_id or not self.orientation_relation_identity:
            raise ValueError("orientation_set_identity_invalid")

    @property
    def identity(self) -> str:
        """
        Identify one count, relation, and ordered fabrication set.
        """

        return _identity(
            encode_bytes(
                {
                    "cell_id": self.cell_id,
                    "converted_phase": format(
                        self.converted_phase,
                        "f",
                    ),
                    "count": self.count,
                    "orientations_identity": (self.orientation_relation_identity),
                    "orientations_reference": (self.orientation_relation_reference),
                    "phase_sign": self.phase_sign,
                    "states": tuple(state.as_mapping() for state in self.states),
                }
            )
        )

    def as_mapping(self) -> dict[str, object]:
        """
        Return the ordered orientation set without a phase-set fiction.
        """

        return {
            "cell_id": self.cell_id,
            "converted_phase": format(self.converted_phase, "f"),
            "count": self.count,
            "identity": self.identity,
            "orientations_identity": self.orientation_relation_identity,
            "orientations_reference": (
                self.orientation_relation_reference.as_mapping()
            ),
            "phase_sign": self.phase_sign,
            "states": [state.as_mapping() for state in self.states],
        }

    def document(self) -> Document:
        """
        Wrap one orientation set for authority admission.
        """

        return Document(ORIENTATION_SET_SCHEMA, self.as_mapping())

    def references(self) -> tuple[Reference, ...]:
        """
        Name the analytic relation and its admitted source closure once.
        """

        return (self.orientation_relation_reference,)

    def reference_matches(self, reference: Reference) -> bool:
        """
        Verify that one reference names this exact orientation set.
        """

        return reference_matches(reference, self.document().to_bytes())

    @classmethod
    def from_document(cls, document: Document) -> OrientationSet:
        """
        Restore one fabrication set without deriving rotations again.
        """

        if document.schema_identifier != ORIENTATION_SET_SCHEMA:
            raise ValueError("orientation_set_schema_invalid")
        values = _mapping(
            document.values,
            "orientation_set_document_invalid",
        )
        if set(values) != {
            "cell_id",
            "converted_phase",
            "count",
            "identity",
            "orientations_identity",
            "orientations_reference",
            "phase_sign",
            "states",
        }:
            raise ValueError("orientation_set_document_invalid")
        raw_states = values["states"]
        if not isinstance(raw_states, list):
            raise ValueError("orientation_set_document_invalid")
        restored = cls(
            count=int(str(values["count"])),
            cell_id=str(values["cell_id"]),
            converted_phase=Decimal(str(values["converted_phase"])),
            phase_sign=int(str(values["phase_sign"])),
            orientation_relation_identity=str(values["orientations_identity"]),
            orientation_relation_reference=_reference(values["orientations_reference"]),
            states=tuple(_orientation_state(item) for item in raw_states),
        )
        if (
            restored.identity != values["identity"]
            or restored.document().to_bytes() != document.to_bytes()
        ):
            raise ValueError("orientation_set_document_mismatch")
        return restored


def form_orientation_sets(
    relation: OrientationRelation,
    *,
    relation_reference: Reference,
) -> tuple[OrientationSet, ...]:
    """
    Form 8-, 12-, and 16-orientation fabrication sets from one relation.
    """

    if not relation.reference_matches(relation_reference):
        raise ValueError("orientations_reference_mismatch")
    sets = []
    for count in (8, 12, 16):
        states = []
        for index in range(count):
            target_phase = FULL_TURN * Decimal(index) / Decimal(count)
            orientation = relation.for_phase(target_phase)
            states.append(
                OrientationState(
                    index=index,
                    target_phase=target_phase,
                    orientation_rad=orientation,
                    realized_phase=relation.realized_phase(orientation),
                )
            )
        sets.append(
            OrientationSet(
                count=count,
                cell_id=relation.cell_id,
                converted_phase=relation.converted_phase,
                phase_sign=relation.phase_sign,
                orientation_relation_identity=relation.identity,
                orientation_relation_reference=relation_reference,
                states=tuple(states),
            )
        )
    return tuple(sets)


def derive_orientation_relation(
    choice: CellChoice,
    *,
    choice_reference: Reference,
) -> OrientationRelation:
    """
    Derive one continuous geometric-phase orientation without solver work.
    """

    if not choice.reference_matches(choice_reference):
        raise ValueError("cell_choice_reference_mismatch")
    if not reference_matches(
        choice.convention_reference,
        choice.convention.document().to_bytes(),
    ):
        raise ValueError("polarization_convention_reference_mismatch")
    return OrientationRelation(
        cell_id=choice.cell.identity,
        converted_phase=choice.converted_phase,
        phase_sign=choice.convention.phase_sign,
        cell_choice_reference=choice_reference,
        binding_reference=choice.binding_reference,
        library_reference=choice.library_reference,
        convention_reference=choice.convention_reference,
        source_references=choice.source_references,
    )


def assign_aperture(
    study: Study,
    choice: CellChoice,
    relation: OrientationRelation,
    orientation_set: OrientationSet,
    *,
    choice_reference: Reference,
    relation_reference: Reference,
    orientation_set_reference: Reference,
    lattice: Lattice | None = None,
    lattice_reference: Reference | None = None,
) -> Aperture:
    """
    Place one admitted fabrication orientation set over the aperture.
    """

    admitted_choice = require_exact_evidence(
        study,
        "cell_choice",
        choice.document(),
    )
    if admitted_choice != choice_reference:
        raise ValueError("cell_choice_reference_mismatch")
    admitted_relation = require_exact_evidence(
        study,
        "orientations",
        relation.document(),
    )
    if admitted_relation != relation_reference:
        raise ValueError("orientations_reference_mismatch")
    admitted_set = require_exact_evidence(
        study,
        "orientation_set",
        orientation_set.document(),
    )
    if admitted_set != orientation_set_reference:
        raise ValueError("orientation_set_reference_mismatch")
    return assign_discrete_orientations(
        require_metalens_design(study),
        spacing_nm=choice.cell.period_nm,
        choice=choice,
        orientation_relation=relation,
        orientation_set=orientation_set,
        choice_reference=choice_reference,
        orientation_relation_reference=relation_reference,
        orientation_set_reference=orientation_set_reference,
        lattice=lattice,
        lattice_reference=lattice_reference,
    )


def _normalize_orientation(value: Decimal) -> Decimal:
    remainder = value % HALF_TURN
    return remainder + HALF_TURN if remainder < 0 else remainder


def _orientation_state(value: object) -> OrientationState:
    values = _mapping(value, "orientation_set_document_invalid")
    if set(values) != {
        "index",
        "orientation_rad",
        "realized_phase",
        "target_phase",
    }:
        raise ValueError("orientation_set_document_invalid")
    return OrientationState(
        index=int(str(values["index"])),
        target_phase=Decimal(str(values["target_phase"])),
        orientation_rad=Decimal(str(values["orientation_rad"])),
        realized_phase=Decimal(str(values["realized_phase"])),
    )


def _identity(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _reference(value: object) -> Reference:
    try:
        return Reference.from_mapping(_mapping(value, "geometric_reference_invalid"))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("geometric_reference_invalid") from error


def _mapping(value: object, finding: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(finding)
    return value


def _valid_qualification_threshold(value: Decimal | None) -> bool:
    if value is None:
        return True
    return (
        isinstance(value, Decimal) and value.is_finite() and value >= 0 and value <= 1
    )


def _format_optional(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")
