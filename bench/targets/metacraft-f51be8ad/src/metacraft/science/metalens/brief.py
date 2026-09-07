from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import Enum
import json
from typing import TypeAlias, cast

from ..brief import Brief
from ...materials import MaterialSource
from ...materials.family import is_canonical_material_family


class ControlStrategy(str, Enum):
    """
    Names the supported strategies for controlling optical phase.
    """

    PROPAGATION_PHASE = "propagation phase"
    GEOMETRIC_PHASE = "geometric phase"
    # Stable public alias; the serialized historical value remains unchanged.
    PB_PHASE = "geometric phase"


class ApertureExtent(str, Enum):
    """
    Names whether a site count spans center-to-edge or the full footprint.
    """

    RADIUS = "radius"
    DIAMETER = "diameter"


class ApertureFootprint(str, Enum):
    """
    Names the two metalens footprints the aperture Module can arrange.
    """

    CIRCULAR = "circular"
    SQUARE = "square"


@dataclass(frozen=True, slots=True)
class MonochromaticSpectrum:
    """
    Declare one exact operating wavelength.
    """

    wavelength_nm: int

    def __post_init__(self) -> None:
        if type(self.wavelength_nm) is not int or self.wavelength_nm <= 0:
            raise ValueError("monochromatic_spectrum_invalid")


@dataclass(frozen=True, slots=True)
class ContinuousBandSpectrum:
    """
    Declare one closed continuous operating interval.
    """

    lower_wavelength_nm: int
    upper_wavelength_nm: int

    def __post_init__(self) -> None:
        if (
            type(self.lower_wavelength_nm) is not int
            or type(self.upper_wavelength_nm) is not int
            or self.lower_wavelength_nm <= 0
            or self.upper_wavelength_nm <= self.lower_wavelength_nm
        ):
            raise ValueError("continuous_band_spectrum_invalid")


OperatingSpectrum: TypeAlias = MonochromaticSpectrum | ContinuousBandSpectrum


def require_monochromatic_wavelength(spectrum: OperatingSpectrum) -> int:
    """
    Return the exact wavelength only for a monochromatic proof.
    """

    if not isinstance(spectrum, MonochromaticSpectrum):
        raise ValueError("monochromatic_spectrum_required")
    return spectrum.wavelength_nm


@dataclass(frozen=True, slots=True)
class Polarization:
    """
    Declares the incident polarization without solver conventions.
    """

    kind: str
    axis: str | None = None
    handedness: str | None = None


@dataclass(frozen=True, slots=True)
class MaterialIntent:
    """
    Names one material family and the source allowed to resolve it.
    """

    family: str
    source: MaterialSource

    def __post_init__(self) -> None:
        """
        Require one named family and one canonical material source.
        """

        if not is_canonical_material_family(self.family):
            raise ValueError("material_family_invalid")
        if not isinstance(self.source, MaterialSource):
            raise ValueError("material_source_invalid")


@dataclass(frozen=True, slots=True)
class AtomIntent:
    """
    Declares one meta-atom construction family and material intent.
    """

    shape: str
    material: MaterialIntent


@dataclass(frozen=True, slots=True)
class ApertureIntent:
    """
    Preserves one explicit site count, span meaning, and footprint.
    """

    site_count: int
    extent: ApertureExtent
    footprint: ApertureFootprint = ApertureFootprint.CIRCULAR


@dataclass(frozen=True, slots=True, kw_only=True)
class MetalensBrief(Brief):
    """
    Preserves one user's metalens facts and honest omissions.
    """

    operating_spectrum: OperatingSpectrum
    numerical_aperture: Decimal
    focal_length_um: Decimal
    incident_polarization: Polarization
    control_strategy: ControlStrategy | None
    atom: AtomIntent
    substrate: MaterialIntent
    aspect_limit: int
    solver_preference: str | None
    dimension_step_nm: int | None = None
    aperture: ApertureIntent | None = None
    cell_period_nm: int | None = None
    atom_height_nm: int | None = None

    def canonical_value(self) -> dict[str, object]:
        """
        Map canonical Python nouns to the established brief storage keys.
        """

        return {
            "aim": self.aim,
            "aperture": _aperture_intent_value(self.aperture),
            "aspect_limit": self.aspect_limit,
            "atom": _atom_intent_value(self.atom),
            "atom_height_nm": self.atom_height_nm,
            "budget": self.budget,
            "cell_period_nm": self.cell_period_nm,
            "control_strategy": self.control_strategy,
            "dimension_step_nm": self.dimension_step_nm,
            "focal_length_um": self.focal_length_um,
            "incident_polarization": self.incident_polarization,
            "numerical_aperture": self.numerical_aperture,
            "objectives": self.objectives,
            "omissions": self.omissions,
            "solver_preference": self.solver_preference,
            "substrate": _material_intent_value(self.substrate),
            "operating_spectrum": _operating_spectrum_value(self.operating_spectrum),
            "wording": self.wording,
        }

    @classmethod
    def decode_canonical_bytes(cls, source_bytes: bytes) -> MetalensBrief:
        """
        Restore one exact canonical metalens brief without changing user facts.

        Document structure is a transport contract. Scientific completeness
        and validity remain owned by ``compile_study`` after restoration.
        """

        try:
            source_text = source_bytes.decode("utf-8")
            decoded = json.loads(
                source_text,
                object_pairs_hook=_unique_mapping,
            )
        except _DuplicateBriefField as error:
            raise ValueError("metalens_brief_document_duplicate") from error
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("metalens_brief_document_invalid") from error

        try:
            values = _require_mapping(decoded, _BRIEF_FIELDS)
            brief = cls(
                wording=_require_text(values["wording"]),
                aim=_require_text(values["aim"]),
                objectives=_require_text_tuple(values["objectives"]),
                budget=_require_text(values["budget"]),
                omissions=_require_text_tuple(values["omissions"]),
                operating_spectrum=_restore_operating_spectrum(
                    values["operating_spectrum"]
                ),
                numerical_aperture=_require_decimal(values["numerical_aperture"]),
                focal_length_um=_require_decimal(values["focal_length_um"]),
                incident_polarization=_restore_polarization(
                    values["incident_polarization"]
                ),
                control_strategy=_restore_control_strategy(values["control_strategy"]),
                atom=_restore_atom_intent(values["atom"]),
                substrate=_restore_material_intent(values["substrate"]),
                aspect_limit=_require_integer(values["aspect_limit"]),
                solver_preference=_require_optional_text(values["solver_preference"]),
                dimension_step_nm=_require_optional_integer(
                    values["dimension_step_nm"]
                ),
                aperture=_restore_aperture_intent(values["aperture"]),
                cell_period_nm=_require_optional_integer(values["cell_period_nm"]),
                atom_height_nm=_require_optional_integer(values["atom_height_nm"]),
            )
        except (InvalidOperation, KeyError, TypeError, ValueError) as error:
            raise ValueError("metalens_brief_document_invalid") from error

        for fact in _NULLABLE_USER_FACTS:
            if getattr(brief, fact) is None and fact not in brief.omissions:
                raise ValueError(f"metalens_brief_omission_required:{fact}")
        if brief.canonical_bytes() != source_bytes:
            raise ValueError("metalens_brief_document_noncanonical")
        return brief

    def replace_numerical_aperture(self, value: str) -> MetalensBrief:
        """
        Return a copy with one explicit numerical aperture.
        """

        return replace(self, numerical_aperture=Decimal(value))


def _material_intent_value(intent: MaterialIntent) -> dict[str, object]:
    return {
        "material": intent.family,
        "source": intent.source.value,
    }


def _atom_intent_value(intent: AtomIntent) -> dict[str, object]:
    return {
        "material": _material_intent_value(intent.material),
        "shape": intent.shape,
    }


def _aperture_intent_value(
    intent: ApertureIntent | None,
) -> dict[str, object] | None:
    if intent is None:
        return None
    return {
        "cells": intent.site_count,
        "extent": intent.extent,
        "footprint": intent.footprint,
    }


def _operating_spectrum_value(
    spectrum: OperatingSpectrum,
) -> dict[str, object]:
    if isinstance(spectrum, MonochromaticSpectrum):
        return {
            "kind": "monochromatic",
            "wavelength_nm": spectrum.wavelength_nm,
        }
    if isinstance(spectrum, ContinuousBandSpectrum):
        return {
            "kind": "continuous band",
            "lower_wavelength_nm": spectrum.lower_wavelength_nm,
            "upper_wavelength_nm": spectrum.upper_wavelength_nm,
        }
    raise TypeError("operating_spectrum_invalid")


def _restore_operating_spectrum(value: object) -> OperatingSpectrum:
    if not isinstance(value, dict):
        raise TypeError("operating_spectrum_mapping_required")
    if value.get("kind") == "monochromatic" and set(value) == {
        "kind",
        "wavelength_nm",
    }:
        return MonochromaticSpectrum(_require_integer(value["wavelength_nm"]))
    if value.get("kind") == "continuous band" and set(value) == {
        "kind",
        "lower_wavelength_nm",
        "upper_wavelength_nm",
    }:
        return ContinuousBandSpectrum(
            lower_wavelength_nm=_require_integer(value["lower_wavelength_nm"]),
            upper_wavelength_nm=_require_integer(value["upper_wavelength_nm"]),
        )
    raise ValueError("operating_spectrum_invalid")


_BRIEF_FIELDS = {
    "aim",
    "aperture",
    "aspect_limit",
    "atom",
    "atom_height_nm",
    "budget",
    "cell_period_nm",
    "control_strategy",
    "dimension_step_nm",
    "focal_length_um",
    "incident_polarization",
    "numerical_aperture",
    "objectives",
    "omissions",
    "solver_preference",
    "substrate",
    "operating_spectrum",
    "wording",
}
_NULLABLE_USER_FACTS = {
    "aperture",
    "atom_height_nm",
    "cell_period_nm",
    "control_strategy",
    "dimension_step_nm",
    "solver_preference",
}


class _DuplicateBriefField(ValueError):
    pass


def _unique_mapping(pairs: list[tuple[str, object]]) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in pairs:
        if key in values:
            raise _DuplicateBriefField(key)
        values[key] = value
    return values


def _require_mapping(
    value: object,
    fields: set[str],
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("mapping_invalid")
    return cast(dict[str, object], value)


def _require_text(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("text_required")
    return value


def _require_optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _require_text(value)


def _require_text_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TypeError("text_array_required")
    return tuple(value)


def _require_integer(value: object) -> int:
    if type(value) is not int:
        raise TypeError("integer_required")
    return value


def _require_optional_integer(value: object) -> int | None:
    if value is None:
        return None
    return _require_integer(value)


def _require_decimal(value: object) -> Decimal:
    if not isinstance(value, str):
        raise TypeError("decimal_string_required")
    restored = Decimal(value)
    if not restored.is_finite():
        raise ValueError("decimal_finite_required")
    return restored


def _restore_control_strategy(value: object) -> ControlStrategy | None:
    if value is None:
        return None
    return ControlStrategy(_require_text(value))


def _restore_polarization(value: object) -> Polarization:
    values = _require_mapping(value, {"axis", "handedness", "kind"})
    return Polarization(
        kind=_require_text(values["kind"]),
        axis=_require_optional_text(values["axis"]),
        handedness=_require_optional_text(values["handedness"]),
    )


def _restore_material_intent(value: object) -> MaterialIntent:
    values = _require_mapping(value, {"material", "source"})
    return MaterialIntent(
        family=_require_text(values["material"]),
        source=MaterialSource(_require_text(values["source"])),
    )


def _restore_atom_intent(value: object) -> AtomIntent:
    values = _require_mapping(value, {"material", "shape"})
    return AtomIntent(
        shape=_require_text(values["shape"]),
        material=_restore_material_intent(values["material"]),
    )


def _restore_aperture_intent(value: object) -> ApertureIntent | None:
    if value is None:
        return None
    values = _require_mapping(value, {"cells", "extent", "footprint"})
    return ApertureIntent(
        site_count=_require_integer(values["cells"]),
        extent=ApertureExtent(_require_text(values["extent"])),
        footprint=ApertureFootprint(_require_text(values["footprint"])),
    )
