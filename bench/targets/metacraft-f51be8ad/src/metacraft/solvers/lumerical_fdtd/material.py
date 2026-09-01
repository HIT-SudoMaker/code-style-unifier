from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import Enum
import hashlib
from types import MappingProxyType

from ...authority import Document, Reference
from ...canonical import encode_bytes


SPEED_OF_LIGHT_M_PER_S = 299792458
FREQUENCY_LINEAR_INTERPOLATION = "linear_in_frequency"
MATERIAL_SAMPLE_SCHEMA = "metacraft.solver.lumerical_material_sample"


class MaterialVerificationRefusalKind(str, Enum):
    """
    Names the expected ways one native material request can be unavailable.
    """

    NATIVE_MATERIAL_ABSENT = "native_material_absent"
    WAVELENGTH_UNCOVERED = "wavelength_uncovered"


@dataclass(frozen=True, slots=True, kw_only=True)
class MaterialVerificationRefusal:
    """
    Returns one expected product-owned material verification outcome.
    """

    kind: MaterialVerificationRefusalKind
    family: str
    native_name: str
    wavelength_nm: int

    def __post_init__(self) -> None:
        """
        Require the exact request facts needed by application translation.
        """

        if (
            not isinstance(self.kind, MaterialVerificationRefusalKind)
            or not self.family.strip()
            or not self.native_name.strip()
            or self.wavelength_nm <= 0
        ):
            raise ValueError("material_verification_refusal_invalid")


def sample_frequency_hz(wavelength_nm: int) -> float:
    """
    Convert one registered vacuum wavelength to probe frequency.
    """

    if wavelength_nm <= 0:
        raise ValueError("sample_wavelength_invalid")
    return SPEED_OF_LIGHT_M_PER_S / (wavelength_nm * 1e-9)


def material_sample_key(
    sample: LumericalMaterialSample,
) -> str:
    """
    Name one sample from every exact source and fit condition it observes.
    """

    if sample.binding_reference is None:
        raise ValueError("solver_binding_reference_missing")
    if len(sample.grid_wavelengths_nm) != 1:
        raise ValueError("material_sample_wavelength_ambiguous")
    if not sample.registration_references:
        raise ValueError("solver_material_references_missing")
    identity = encode_bytes(
        {
            "fit_span": {
                "maximum_frequency_hz": format(
                    sample.maximum_fit_frequency_hz,
                    "f",
                ),
                "minimum_frequency_hz": format(
                    sample.minimum_fit_frequency_hz,
                    "f",
                ),
            },
            "registration_references": [
                reference.as_mapping()
                for _, reference in sorted(
                    sample.registration_references.items()
                )
            ],
            "requested_wavelength_nm": sample.grid_wavelengths_nm[0],
            "solver_binding_reference": (
                sample.binding_reference.as_mapping()
            ),
        }
    )
    digest = hashlib.sha256(identity).hexdigest()
    return f"lumerical_material_sample:sha256:{digest}"


@dataclass(frozen=True, slots=True)
class NativeIndexPoint:
    """
    Records index, extinction, and fit residual at one wavelength.
    """

    wavelength_nm: int
    frequency_hz: Decimal
    refractive_index: Decimal
    extinction_coefficient: Decimal
    fit_residual: Decimal

    def as_mapping(self) -> dict[str, object]:
        """
        Return exact decimal text suitable for canonical storage.
        """

        return {
            "extinction_coefficient": format(
                self.extinction_coefficient,
                "f",
            ),
            "fit_residual": format(self.fit_residual, "f"),
            "frequency_hz": format(self.frequency_hz, "f"),
            "refractive_index": format(self.refractive_index, "f"),
            "wavelength_nm": self.wavelength_nm,
        }


@dataclass(frozen=True, slots=True)
class NativeMaterialSample:
    """
    Holds one native material's table points and fit conditions.
    """

    family: str
    native_name: str
    fit_tolerance: Decimal
    fit_maximum_coefficients: int
    minimum_tabulated_frequency_hz: Decimal
    maximum_tabulated_frequency_hz: Decimal
    points: tuple[NativeIndexPoint, ...]
    findings: tuple[str, ...]

    def as_mapping(self) -> dict[str, object]:
        """
        Return this material sample without binary float loss.
        """

        return {
            "family": self.family,
            "findings": list(self.findings),
            "fit_maximum_coefficients": self.fit_maximum_coefficients,
            "fit_tolerance": format(self.fit_tolerance, "f"),
            "native_name": self.native_name,
            "points": [point.as_mapping() for point in self.points],
            "tabulated_band": {
                "maximum_frequency_hz": format(self.maximum_tabulated_frequency_hz, "f"),
                "minimum_frequency_hz": format(self.minimum_tabulated_frequency_hz, "f"),
            },
        }


@dataclass(frozen=True, slots=True)
class ResolvedNativeIndex:
    """
    Carries one wavelength resolved from an admitted native sample.
    """

    family: str
    native_name: str
    wavelength_nm: int
    refractive_index: Decimal
    extinction_coefficient: Decimal
    interpolation: str


@dataclass(frozen=True, slots=True)
class LumericalMaterialSample:
    """
    Records one task's native indices beside one solver binding.
    """

    grid_wavelengths_nm: tuple[int, ...]
    minimum_fit_frequency_hz: Decimal
    maximum_fit_frequency_hz: Decimal
    materials: Mapping[str, NativeMaterialSample]
    interpolation: str = FREQUENCY_LINEAR_INTERPOLATION
    binding_reference: Reference | None = None
    registration_references: Mapping[str, Reference] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """
        Freeze both family maps in canonical family order.
        """

        object.__setattr__(
            self,
            "materials",
            MappingProxyType(dict(sorted(self.materials.items()))),
        )
        object.__setattr__(
            self,
            "registration_references",
            MappingProxyType(
                dict(sorted(self.registration_references.items()))
            ),
        )

    def with_sources(
        self,
        *,
        binding_reference: Reference,
        registration_references: Mapping[str, Reference],
    ) -> LumericalMaterialSample:
        """
        Cite the admitted solver binding and exact material registrations.
        """

        return replace(
            self,
            binding_reference=binding_reference,
            registration_references=dict(registration_references),
        )

    def verify_readback(
        self,
        *,
        native_names: Mapping[str, str],
        wavelength_nm: int,
    ) -> MaterialVerificationRefusal | None:
        """
        Verify one task's exact, finite, canonically ordered native read-back.
        """

        self._verify_sources(native_names)
        self._verify_fit_span(wavelength_nm)
        self._verify_grid()
        for family, native_name in native_names.items():
            material = self.materials.get(family)
            if material is None:
                return MaterialVerificationRefusal(
                    kind=(
                        MaterialVerificationRefusalKind
                        .NATIVE_MATERIAL_ABSENT
                    ),
                    family=family,
                    native_name=native_name,
                    wavelength_nm=wavelength_nm,
                )
            if material.family != family:
                raise ValueError(
                    f"material_sample_family_changed:{family}"
                )
            if material.native_name != native_name:
                raise ValueError(
                    f"material_sample_native_name_changed:{family}"
                )
            self._verify_material(material)
            if material.findings:
                if material.findings == (
                    f"wavelength_out_of_band:{wavelength_nm}",
                ):
                    return MaterialVerificationRefusal(
                        kind=(
                            MaterialVerificationRefusalKind
                            .WAVELENGTH_UNCOVERED
                        ),
                        family=family,
                        native_name=native_name,
                        wavelength_nm=wavelength_nm,
                    )
                raise ValueError(f"material_sample_invalid:{family}")
            if not material.points:
                raise ValueError(f"material_sample_points_empty:{family}")
            expected_wavelengths = tuple(
                point.wavelength_nm for point in material.points
            )
            if expected_wavelengths != self.grid_wavelengths_nm:
                raise ValueError(
                    f"material_sample_points_not_canonical:{family}"
                )
            self.resolve(family, wavelength_nm)
        if self.grid_wavelengths_nm != (wavelength_nm,):
            raise ValueError("material_sample_wavelength_mismatch")
        return None

    def _verify_sources(
        self,
        native_names: Mapping[str, str],
    ) -> None:
        if self.binding_reference is None:
            raise ValueError("solver_binding_reference_missing")
        expected = set(native_names)
        if set(self.registration_references) != expected:
            raise ValueError("solver_material_references_mismatch")
        if set(self.materials) - expected:
            raise ValueError("material_sample_family_unrequested")
        if not expected:
            raise ValueError("material_sample_materials_empty")

    def _verify_fit_span(self, wavelength_nm: int) -> None:
        span = (
            self.minimum_fit_frequency_hz,
            self.maximum_fit_frequency_hz,
        )
        _require_finite(*span)
        if span[0] > span[1]:
            raise ValueError("material_sample_fit_span_invalid")
        frequency = Decimal(str(sample_frequency_hz(wavelength_nm)))
        if not span[0] <= frequency <= span[1]:
            raise ValueError("material_sample_fit_span_uncovered")

    def _verify_grid(self) -> None:
        if (
            not self.grid_wavelengths_nm
            or any(wavelength <= 0 for wavelength in self.grid_wavelengths_nm)
            or self.grid_wavelengths_nm
            != tuple(sorted(set(self.grid_wavelengths_nm)))
        ):
            raise ValueError("material_sample_grid_not_canonical")
        if self.interpolation != FREQUENCY_LINEAR_INTERPOLATION:
            raise ValueError("material_sample_interpolation_invalid")

    @staticmethod
    def _verify_material(material: NativeMaterialSample) -> None:
        if not material.family or not material.native_name:
            raise ValueError("material_sample_identity_invalid")
        _require_finite(
            material.fit_tolerance,
            material.minimum_tabulated_frequency_hz,
            material.maximum_tabulated_frequency_hz,
        )
        if (
            material.minimum_tabulated_frequency_hz
            > material.maximum_tabulated_frequency_hz
        ):
            raise ValueError("material_sample_band_invalid")
        if material.fit_maximum_coefficients <= 0:
            raise ValueError("material_fit_coefficients_invalid")
        wavelengths = tuple(point.wavelength_nm for point in material.points)
        if wavelengths != tuple(sorted(set(wavelengths))):
            raise ValueError("material_sample_points_not_canonical")
        for point in material.points:
            _require_finite(
                point.frequency_hz,
                point.refractive_index,
                point.extinction_coefficient,
                point.fit_residual,
            )
            expected_frequency = Decimal(
                str(sample_frequency_hz(point.wavelength_nm))
            )
            if point.frequency_hz != expected_frequency:
                raise ValueError("material_sample_point_frequency_changed")
            if not (
                material.minimum_tabulated_frequency_hz
                <= point.frequency_hz
                <= material.maximum_tabulated_frequency_hz
            ):
                raise ValueError("material_sample_point_out_of_band")

    def resolve(
        self,
        family: str,
        wavelength_nm: int,
    ) -> ResolvedNativeIndex:
        """
        Resolve one wavelength linearly in frequency, never beyond data.
        """

        material = self.materials.get(family)
        if material is None:
            raise ValueError(f"material_family_unsampled:{family}")
        frequency = Decimal(str(sample_frequency_hz(wavelength_nm)))
        if not (
            material.minimum_tabulated_frequency_hz
            <= frequency
            <= material.maximum_tabulated_frequency_hz
        ):
            raise ValueError(
                f"material_wavelength_out_of_band:{family}:{wavelength_nm}"
            )
        for point in material.points:
            if point.wavelength_nm == wavelength_nm:
                return _resolved(
                    material,
                    wavelength_nm,
                    point,
                    interpolation=self.interpolation,
                )
        ordered = sorted(
            material.points,
            key=lambda point: point.frequency_hz,
        )
        for lower, upper in zip(ordered, ordered[1:], strict=False):
            if lower.frequency_hz < frequency < upper.frequency_hz:
                fraction = (frequency - lower.frequency_hz) / (
                    upper.frequency_hz - lower.frequency_hz
                )
                return ResolvedNativeIndex(
                    family=material.family,
                    native_name=material.native_name,
                    wavelength_nm=wavelength_nm,
                    refractive_index=(
                        lower.refractive_index
                        + fraction
                        * (
                            upper.refractive_index
                            - lower.refractive_index
                        )
                    ),
                    extinction_coefficient=(
                        lower.extinction_coefficient
                        + fraction
                        * (
                            upper.extinction_coefficient
                            - lower.extinction_coefficient
                        )
                    ),
                    interpolation=self.interpolation,
                )
        raise ValueError(
            f"material_wavelength_outside_grid:{family}:{wavelength_nm}"
        )

    def to_document(self) -> Document:
        """
        Encode this binding-cited sample for Authority storage.
        """

        if self.binding_reference is None:
            raise ValueError("solver_binding_reference_missing")
        if set(self.registration_references) != set(self.materials):
            raise ValueError("solver_material_references_mismatch")
        return Document(
            MATERIAL_SAMPLE_SCHEMA,
            {
                "binding_reference": self.binding_reference.as_mapping(),
                "fit_span": {
                    "maximum_frequency_hz": format(self.maximum_fit_frequency_hz, "f"),
                    "minimum_frequency_hz": format(self.minimum_fit_frequency_hz, "f"),
                },
                "grid_wavelengths_nm": list(self.grid_wavelengths_nm),
                "interpolation": self.interpolation,
                "materials": {
                    family: material.as_mapping()
                    for family, material in sorted(self.materials.items())
                },
                "registration_references": {
                    family: reference.as_mapping()
                    for family, reference in sorted(
                        self.registration_references.items()
                    )
                },
            },
        )

    @classmethod
    def from_document_bytes(
        cls,
        value: bytes,
    ) -> LumericalMaterialSample:
        """
        Restore one canonical sample without losing exact decimals.
        """

        document = Document.from_bytes(value)
        if document.schema_identifier != MATERIAL_SAMPLE_SCHEMA:
            raise ValueError("material_sample_schema_invalid")
        values = document.values
        span = _mapping(values["fit_span"], "material_sample_span_invalid")
        raw_materials = _mapping(
            values["materials"],
            "material_sample_materials_invalid",
        )
        raw_registrations = _mapping(
            values["registration_references"],
            "material_sample_registrations_invalid",
        )
        sample = cls(
            grid_wavelengths_nm=tuple(
                int(wavelength)
                for wavelength in values["grid_wavelengths_nm"]
            ),
            minimum_fit_frequency_hz=Decimal(str(span["minimum_frequency_hz"])),
            maximum_fit_frequency_hz=Decimal(str(span["maximum_frequency_hz"])),
            materials={
                str(family): _decoded_material(
                    _mapping(
                        material,
                        "material_sample_material_invalid",
                    )
                )
                for family, material in raw_materials.items()
            },
            interpolation=str(values["interpolation"]),
            binding_reference=Reference.from_mapping(
                _mapping(
                    values["binding_reference"],
                    "material_sample_binding_invalid",
                )
            ),
            registration_references={
                str(family): Reference.from_mapping(
                    _mapping(
                        reference,
                        "material_sample_registration_invalid",
                    )
                )
                for family, reference in raw_registrations.items()
            },
        )
        if sample.to_document().to_bytes() != value:
            raise ValueError("material_sample_not_canonical")
        return sample


def _resolved(
    material: NativeMaterialSample,
    wavelength_nm: int,
    point: NativeIndexPoint,
    *,
    interpolation: str,
) -> ResolvedNativeIndex:
    return ResolvedNativeIndex(
        family=material.family,
        native_name=material.native_name,
        wavelength_nm=wavelength_nm,
        refractive_index=point.refractive_index,
        extinction_coefficient=point.extinction_coefficient,
        interpolation=interpolation,
    )


def _decoded_material(
    values: Mapping[str, object],
) -> NativeMaterialSample:
    band = _mapping(values["tabulated_band"], "material_band_invalid")
    raw_points = values["points"]
    raw_findings = values["findings"]
    if not isinstance(raw_points, list) or not isinstance(
        raw_findings,
        list,
    ):
        raise ValueError("material_sample_shape_invalid")
    return NativeMaterialSample(
        family=str(values["family"]),
        native_name=str(values["native_name"]),
        fit_tolerance=Decimal(str(values["fit_tolerance"])),
        fit_maximum_coefficients=int(
            str(values["fit_maximum_coefficients"])
        ),
        minimum_tabulated_frequency_hz=Decimal(str(band["minimum_frequency_hz"])),
        maximum_tabulated_frequency_hz=Decimal(str(band["maximum_frequency_hz"])),
        points=tuple(
            _decoded_point(
                _mapping(point, "material_sample_point_invalid")
            )
            for point in raw_points
        ),
        findings=tuple(str(finding) for finding in raw_findings),
    )


def _decoded_point(values: Mapping[str, object]) -> NativeIndexPoint:
    return NativeIndexPoint(
        wavelength_nm=int(str(values["wavelength_nm"])),
        frequency_hz=Decimal(str(values["frequency_hz"])),
        refractive_index=Decimal(str(values["refractive_index"])),
        extinction_coefficient=Decimal(
            str(values["extinction_coefficient"])
        ),
        fit_residual=Decimal(str(values["fit_residual"])),
    )


def _mapping(value: object, finding: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(finding)
    return value


def _require_finite(*values: Decimal) -> None:
    if not all(value.is_finite() for value in values):
        raise ValueError("material_sample_not_finite")
