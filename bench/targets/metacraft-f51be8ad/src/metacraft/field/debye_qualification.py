from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
import math
from types import MappingProxyType

import torch

from ..authority import Document, Reference, ReferenceUnresolvable, reference_for
from .debye import (
    AplanaticPupil,
    AplanaticSurface,
    DebyeObservation,
    FocalCoordinates,
    PupilPolarization,
)
from .agreement import compare_complex_vector_fields
from .fast_debye import (
    CZTDebyeRealization,
    FFTDebyeRealization,
    _evaluate_prepared_czt_debye,
    _evaluate_prepared_fft_debye,
    _prepare_aplanatic_pupil,
    evaluate_czt_debye,
    evaluate_fft_debye,
    fft_focal_axis,
)
from .sample import CoordinateFrame, Medium

_REFERENCE_METHOD = "analytic Richards--Wolf invariants"
_REFERENCE_FIXTURES = (
    "low na analytic on-axis field",
    "high na analytic on-axis field",
    "transverse reflection symmetry",
    "longitudinal reflection antisymmetry",
    "positive quadrature handedness",
    "selected device",
)
_ERROR_LIMITS = MappingProxyType(
    {
        "low na analytic on-axis field": 5e-3,
        "high na analytic on-axis field": 5e-3,
        "transverse reflection symmetry": 1e-10,
        "longitudinal reflection antisymmetry": 1e-10,
        "positive quadrature handedness": 1e-10,
        "selected device": 0.0,
    }
)
_JOINT_ERROR_LIMIT = 1e-10
_JOINT_FIXTURE_MATRIX = tuple(
    {
        "axial_offset_wavelengths": axial_offset,
        "numerical_aperture": numerical_aperture,
        "polarization": polarization,
        "transverse_indices": ((0, 0), (1, 0), (0, 1), (-1, -1)),
    }
    for numerical_aperture in ("0.35", "0.8")
    for polarization in ("linear", "circular")
    for axial_offset in ("-0.08", "0.0", "0.08")
)
APLANATIC_FOCUS_QUALIFICATION_SCHEMA = (
    "metacraft.qualification.aplanatic_fourier_realization"
)
APLANATIC_REFERENCE_QUALIFICATION_SCHEMA = (
    "metacraft.qualification.aplanatic_reference_agreement"
)
APLANATIC_REFERENCE_BINDING_SCHEMA = "metacraft.binding.aplanatic_reference_formation"

FourierDebyeRealization = FFTDebyeRealization | CZTDebyeRealization
DebyeEvaluator = Callable[
    [AplanaticPupil, FocalCoordinates, FourierDebyeRealization],
    DebyeObservation,
]
CoordinateBuilder = Callable[
    [AplanaticPupil, FourierDebyeRealization],
    tuple[FocalCoordinates, tuple[int, int, int]],
]


@dataclass(frozen=True, slots=True)
class AplanaticFocusQualification:
    """
    Record one Fourier realization against independent physical facts.
    """

    realization: FourierDebyeRealization
    reference_method: str
    realization_facts: Mapping[str, object]
    reference_fixtures: tuple[str, ...]
    fixture_errors: Mapping[str, float]
    is_qualified: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        """
        Freeze the exact binding and reject inconsistent evidence.
        """

        if self.reference_method != _REFERENCE_METHOD:
            raise ValueError("aplanatic_focus_reference_method_unsupported")
        if dict(self.realization_facts) != self.realization.as_mapping():
            raise ValueError("aplanatic_focus_realization_mismatch")
        if self.reference_fixtures != _REFERENCE_FIXTURES:
            raise ValueError("aplanatic_focus_fixtures_invalid")
        if self.is_qualified != (self.reason is None):
            raise ValueError("aplanatic_focus_qualification_inconsistent")
        if self.is_qualified and set(self.fixture_errors) != set(
            self.reference_fixtures
        ):
            raise ValueError("aplanatic_focus_errors_incomplete")
        if any(
            not math.isfinite(error) or error < 0
            for error in self.fixture_errors.values()
        ):
            raise ValueError("aplanatic_focus_error_invalid")
        object.__setattr__(
            self,
            "realization_facts",
            MappingProxyType(dict(self.realization_facts)),
        )
        object.__setattr__(
            self,
            "fixture_errors",
            MappingProxyType(dict(self.fixture_errors)),
        )

    @property
    def binding(self) -> FourierDebyeRealization | None:
        """
        Return the realization only after every physical check passes.
        """

        return self.realization if self.is_qualified else None

    def as_mapping(self) -> dict[str, object]:
        """
        Return the realization and its independent qualification facts.
        """

        return {
            "fixture_errors": {
                name: repr(error) for name, error in self.fixture_errors.items()
            },
            "qualified": self.is_qualified,
            "realization": dict(self.realization_facts),
            "reason": self.reason,
            "reference_fixtures": list(self.reference_fixtures),
            "reference_method": self.reference_method,
        }

    def document(self) -> Document:
        """
        Return one independently restorable qualification fact.
        """

        return Document(APLANATIC_FOCUS_QUALIFICATION_SCHEMA, self.as_mapping())


@dataclass(frozen=True, slots=True)
class AplanaticReferenceQualification:
    """
    Bind independent FFT/CZT facts to matched-grid agreement.
    """

    fft_realization: FFTDebyeRealization
    czt_realization: CZTDebyeRealization
    fft_qualification_reference: Reference
    czt_qualification_reference: Reference
    fixture_agreements: Mapping[str, Mapping[str, float]]
    is_qualified: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        if (
            self.fft_realization.device != self.czt_realization.device
            or self.fft_realization.pupil_samples != self.czt_realization.pupil_samples
            or self.fft_realization.convention != self.czt_realization.convention
            or self.is_qualified != (self.reason is None)
        ):
            raise ValueError("aplanatic_reference_qualification_inconsistent")
        expected_names = {_joint_fixture_name(item) for item in _JOINT_FIXTURE_MATRIX}
        if self.is_qualified and set(self.fixture_agreements) != expected_names:
            raise ValueError("aplanatic_reference_fixture_matrix_incomplete")
        frozen = {}
        for name, agreement in self.fixture_agreements.items():
            values = dict(agreement)
            if set(values) != {
                "aligned_complex_error",
                "unit_integral_intensity_error",
            } or any(
                not math.isfinite(value) or value < 0 for value in values.values()
            ):
                raise ValueError("aplanatic_reference_agreement_invalid")
            frozen[name] = MappingProxyType(values)
        object.__setattr__(self, "fixture_agreements", MappingProxyType(frozen))

    def document(self) -> Document:
        """
        Return the exact independent and matched-grid qualification closure.
        """

        return Document(
            APLANATIC_REFERENCE_QUALIFICATION_SCHEMA,
            {
                "czt_qualification_reference": (
                    self.czt_qualification_reference.as_mapping()
                ),
                "czt_realization": self.czt_realization.as_mapping(),
                "error_limit": repr(_JOINT_ERROR_LIMIT),
                "fft_qualification_reference": (
                    self.fft_qualification_reference.as_mapping()
                ),
                "fft_realization": self.fft_realization.as_mapping(),
                "fixture_agreements": {
                    name: {metric: repr(value) for metric, value in agreement.items()}
                    for name, agreement in self.fixture_agreements.items()
                },
                "fixture_matrix": _joint_fixture_matrix(),
                "qualified": self.is_qualified,
                "reason": self.reason,
            },
        )


def aplanatic_reference_binding(
    qualification: AplanaticReferenceQualification,
    *,
    joint_qualification_reference: Reference,
) -> Document:
    """
    Bind both exact realizations and their complete qualification closure.
    """

    if (
        not qualification.is_qualified
        or reference_for(qualification.document().to_bytes())
        != joint_qualification_reference
    ):
        raise ValueError("aplanatic_reference_qualification_required")
    return Document(
        APLANATIC_REFERENCE_BINDING_SCHEMA,
        {
            "czt_realization": qualification.czt_realization.as_mapping(),
            "fft_realization": qualification.fft_realization.as_mapping(),
            "operations": ["form_aplanatic_reference"],
            "qualification_references": {
                "czt": qualification.czt_qualification_reference.as_mapping(),
                "fft": qualification.fft_qualification_reference.as_mapping(),
                "joint": joint_qualification_reference.as_mapping(),
            },
            "qualified": True,
        },
    )


def restore_aplanatic_reference_binding(
    document: Document,
    fetch: Callable[[Reference], bytes],
) -> tuple[FFTDebyeRealization, CZTDebyeRealization]:
    """
    Restore a complete joint binding or fail before numerical execution.
    """

    try:
        values = document.values
        if (
            document.schema_identifier != APLANATIC_REFERENCE_BINDING_SCHEMA
            or set(values)
            != {
                "czt_realization",
                "fft_realization",
                "operations",
                "qualification_references",
                "qualified",
            }
            or values["operations"] != ["form_aplanatic_reference"]
            or values["qualified"] is not True
        ):
            raise ValueError("aplanatic_reference_binding_invalid")
        fft = _restore_fft_realization(_mapping(values["fft_realization"]))
        czt = _restore_czt_realization(_mapping(values["czt_realization"]))
        references = _mapping(values["qualification_references"])
        if set(references) != {"fft", "czt", "joint"}:
            raise ValueError("aplanatic_reference_binding_invalid")
        fft_reference = Reference.from_mapping(_mapping(references["fft"]))
        czt_reference = Reference.from_mapping(_mapping(references["czt"]))
        joint_reference = Reference.from_mapping(_mapping(references["joint"]))
        fft_document = _fetch_document(fetch, fft_reference)
        czt_document = _fetch_document(fetch, czt_reference)
        joint_document = _fetch_document(fetch, joint_reference)
        _require_independent_document(fft_document, fft.as_mapping())
        _require_independent_document(czt_document, czt.as_mapping())
        _require_joint_document(
            joint_document,
            fft=fft,
            czt=czt,
            fft_reference=fft_reference,
            czt_reference=czt_reference,
        )
    except (
        FileNotFoundError,
        KeyError,
        ReferenceUnresolvable,
        TypeError,
        ValueError,
    ) as error:
        raise ValueError("aplanatic_reference_binding_mismatch") from error
    return fft, czt


def qualify_fft_debye(
    realization: FFTDebyeRealization,
) -> AplanaticFocusQualification:
    """
    Qualify one FFT realization on its conjugate focal coordinates.
    """

    return _qualify_realization(
        realization,
        evaluator=_evaluate_fft,
        coordinate_builder=_fft_coordinates,
    )


def qualify_czt_debye(
    realization: CZTDebyeRealization,
) -> AplanaticFocusQualification:
    """
    Qualify one CZT realization on an explicit Cartesian focal grid.
    """

    return _qualify_realization(
        realization,
        evaluator=_evaluate_czt,
        coordinate_builder=_czt_coordinates,
    )


def qualify_aplanatic_reference(
    fft_qualification: AplanaticFocusQualification,
    czt_qualification: AplanaticFocusQualification,
    *,
    fft_qualification_reference: Reference,
    czt_qualification_reference: Reference,
) -> AplanaticReferenceQualification:
    """
    Qualify FFT and CZT together on one frozen natural-grid matrix.
    """

    if (
        not isinstance(fft_qualification.realization, FFTDebyeRealization)
        or not isinstance(czt_qualification.realization, CZTDebyeRealization)
        or reference_for(fft_qualification.document().to_bytes())
        != fft_qualification_reference
        or reference_for(czt_qualification.document().to_bytes())
        != czt_qualification_reference
    ):
        raise ValueError("aplanatic_reference_independent_qualification_mismatch")
    fft = fft_qualification.realization
    czt = czt_qualification.realization
    if (
        not fft_qualification.is_qualified
        or not czt_qualification.is_qualified
        or fft.device != czt.device
        or fft.pupil_samples != czt.pupil_samples
        or fft.convention != czt.convention
    ):
        return AplanaticReferenceQualification(
            fft,
            czt,
            fft_qualification_reference,
            czt_qualification_reference,
            {},
            False,
            "aplanatic_reference_independent_qualification_failed",
        )
    agreements: dict[str, Mapping[str, float]] = {}
    try:
        for fixture in _JOINT_FIXTURE_MATRIX:
            pupil = _joint_pupil(fixture)
            axis = fft_focal_axis(pupil, realization=fft)
            center = len(axis) // 2
            axial = float(fixture["axial_offset_wavelengths"]) * pupil.wavelength_m
            indices = fixture["transverse_indices"]
            assert isinstance(indices, tuple)
            coordinates = FocalCoordinates(
                tuple(axis[center + int(item[0])] for item in indices),
                tuple(axis[center + int(item[1])] for item in indices),
                tuple(axial for _ in indices),
            )
            prepared = _prepare_aplanatic_pupil(
                pupil,
                sample_count=fft.pupil_samples,
                device=torch.device(fft.device),
            )
            fft_observation = _evaluate_prepared_fft_debye(
                prepared,
                coordinates,
                realization=fft,
            )
            czt_observation = _evaluate_prepared_czt_debye(
                prepared,
                coordinates,
                realization=czt,
            )
            agreement = compare_complex_vector_fields(
                dict(zip(("x", "y", "z"), fft_observation.electric_components)),
                dict(zip(("x", "y", "z"), czt_observation.electric_components)),
            )
            agreements[_joint_fixture_name(fixture)] = {
                "aligned_complex_error": agreement.aligned_complex_error,
                "unit_integral_intensity_error": (
                    agreement.unit_integral_intensity_error
                ),
            }
    except (RuntimeError, ValueError) as error:
        return AplanaticReferenceQualification(
            fft,
            czt,
            fft_qualification_reference,
            czt_qualification_reference,
            {},
            False,
            type(error).__name__,
        )
    is_qualified = all(
        error <= _JOINT_ERROR_LIMIT
        for agreement in agreements.values()
        for error in agreement.values()
    )
    return AplanaticReferenceQualification(
        fft,
        czt,
        fft_qualification_reference,
        czt_qualification_reference,
        agreements,
        is_qualified,
        None if is_qualified else "aplanatic_reference_agreement_failed",
    )


def form_aplanatic_reference(
    pupil: AplanaticPupil,
    *,
    horizontal_axis_m: tuple[float, ...],
    vertical_axis_m: tuple[float, ...],
    axial_offset_m: float,
    fft_realization: FFTDebyeRealization,
    czt_realization: CZTDebyeRealization,
) -> DebyeObservation:
    """
    Form one requested Cartesian reference after matched-grid agreement.

    The implementation prepares the pupil once, compares FFT and CZT on the
    FFT conjugate grid, then evaluates the requested Cartesian region by CZT.
    Neither realization is selected, averaged, retried, or used as fallback.
    """

    if (
        fft_realization.device != czt_realization.device
        or fft_realization.pupil_samples != czt_realization.pupil_samples
        or fft_realization.convention != czt_realization.convention
        or not horizontal_axis_m
        or not vertical_axis_m
        or not math.isfinite(axial_offset_m)
    ):
        raise ValueError("aplanatic_reference_realizations_incompatible")
    prepared = _prepare_aplanatic_pupil(
        pupil,
        sample_count=fft_realization.pupil_samples,
        device=torch.device(fft_realization.device),
    )
    natural_axis = fft_focal_axis(pupil, realization=fft_realization)
    natural_coordinates = _cartesian_coordinates(
        natural_axis,
        natural_axis,
        axial_offset_m=axial_offset_m,
    )
    fft_observation = _evaluate_prepared_fft_debye(
        prepared,
        natural_coordinates,
        realization=fft_realization,
    )
    czt_observation = _evaluate_prepared_czt_debye(
        prepared,
        natural_coordinates,
        realization=czt_realization,
    )
    agreement = compare_complex_vector_fields(
        dict(zip(("x", "y", "z"), fft_observation.electric_components)),
        dict(zip(("x", "y", "z"), czt_observation.electric_components)),
    )
    if (
        agreement.aligned_complex_error > _JOINT_ERROR_LIMIT
        or agreement.unit_integral_intensity_error > _JOINT_ERROR_LIMIT
    ):
        raise RuntimeError("aplanatic_reference_numerical_agreement_failed")
    return _evaluate_prepared_czt_debye(
        prepared,
        _cartesian_coordinates(
            horizontal_axis_m,
            vertical_axis_m,
            axial_offset_m=axial_offset_m,
        ),
        realization=czt_realization,
    )


def _qualify_realization(
    realization: FourierDebyeRealization,
    *,
    evaluator: DebyeEvaluator,
    coordinate_builder: CoordinateBuilder,
) -> AplanaticFocusQualification:
    errors = {name: 0.0 for name in _REFERENCE_FIXTURES}
    try:
        for numerical_aperture, fixture_name in (
            (0.35, "low na analytic on-axis field"),
            (0.8, "high na analytic on-axis field"),
        ):
            pupil = _linear_pupil(numerical_aperture)
            coordinates, reflection_indices = coordinate_builder(
                pupil,
                realization,
            )
            observed = evaluator(pupil, coordinates, realization)
            fixture_errors = _physical_errors(
                observed,
                pupil,
                reflection_indices=reflection_indices,
                selected_device=realization.device,
            )
            errors[fixture_name] = fixture_errors["analytic on-axis field"]
            for name in (
                "transverse reflection symmetry",
                "longitudinal reflection antisymmetry",
                "selected device",
            ):
                errors[name] = max(errors[name], fixture_errors[name])
        errors["positive quadrature handedness"] = _handedness_error(
            realization,
            evaluator=evaluator,
        )
    except (RuntimeError, ValueError) as error:
        return _failed_qualification(realization, reason=type(error).__name__)
    is_qualified = all(errors[name] <= limit for name, limit in _ERROR_LIMITS.items())
    return AplanaticFocusQualification(
        realization=realization,
        reference_method=_REFERENCE_METHOD,
        realization_facts=realization.as_mapping(),
        reference_fixtures=_REFERENCE_FIXTURES,
        fixture_errors=errors,
        is_qualified=is_qualified,
        reason=None if is_qualified else "aplanatic_focus_fixture_failed",
    )


def _physical_errors(
    observed: DebyeObservation,
    pupil: AplanaticPupil,
    *,
    reflection_indices: tuple[int, int, int],
    selected_device: str,
) -> dict[str, float]:
    negative_index, center_index, positive_index = reflection_indices
    center = observed.horizontal_component[center_index]
    scale = float(torch.abs(center).item())
    analytic = torch.tensor(
        _analytic_on_axis(pupil),
        dtype=torch.complex128,
        device=center.device,
    )
    transverse_error = (
        max(
            float(
                torch.abs(
                    observed.horizontal_component[negative_index]
                    - observed.horizontal_component[positive_index]
                ).item()
            ),
            float(
                torch.abs(
                    observed.vertical_component[negative_index]
                    - observed.vertical_component[positive_index]
                ).item()
            ),
        )
        / scale
    )
    longitudinal_error = float(
        torch.abs(
            observed.longitudinal_component[negative_index]
            + observed.longitudinal_component[positive_index]
        ).item()
        / scale
    )
    expected_device = torch.device(selected_device)
    return {
        "analytic on-axis field": float(
            torch.abs(center - analytic).item() / torch.abs(analytic).item()
        ),
        "transverse reflection symmetry": transverse_error,
        "longitudinal reflection antisymmetry": longitudinal_error,
        "selected device": (
            0.0
            if all(
                component.device == expected_device
                for component in observed.electric_components
            )
            else 1.0
        ),
    }


def _handedness_error(
    realization: FourierDebyeRealization,
    *,
    evaluator: DebyeEvaluator,
) -> float:
    component = 2.0**-0.5
    pupil = replace(
        _linear_pupil(0.8),
        polarization=PupilPolarization(component, 1j * component),
    )
    observed = evaluator(
        pupil,
        FocalCoordinates((0.0,), (0.0,), (0.0,)),
        realization,
    )
    horizontal = observed.horizontal_component[0]
    return float(
        torch.abs(observed.vertical_component[0] - 1j * horizontal).item()
        / torch.abs(horizontal).item()
    )


def _analytic_on_axis(pupil: AplanaticPupil) -> complex:
    edge_cosine = math.cos(pupil.surface.angular_radius_rad)
    angular_integral = 2.0 / 3.0 * (1.0 - edge_cosine**1.5) + 2.0 / 5.0 * (
        1.0 - edge_cosine**2.5
    )
    wave_number = 2.0 * math.pi * pupil.medium_refractive_index / pupil.wavelength_m
    return -1j * wave_number * pupil.surface.focal_length_m / 2.0 * angular_integral


def _linear_pupil(numerical_aperture: float) -> AplanaticPupil:
    return AplanaticPupil(
        surface=AplanaticSurface(
            focal_length_m=4.0e-6,
            angular_radius_rad=math.asin(numerical_aperture),
        ),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        medium_refractive_index=1.0,
        polarization=PupilPolarization(1.0 + 0.0j, 0.0 + 0.0j),
        wavelength_m=532e-9,
    )


def _joint_pupil(fixture: Mapping[str, object]) -> AplanaticPupil:
    polarization = str(fixture["polarization"])
    component = 2.0**-0.5
    return AplanaticPupil(
        surface=AplanaticSurface(
            focal_length_m=4.0e-6,
            angular_radius_rad=math.asin(float(str(fixture["numerical_aperture"]))),
        ),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        medium_refractive_index=1.0,
        polarization=(
            PupilPolarization(1.0 + 0.0j, 0.0 + 0.0j)
            if polarization == "linear"
            else PupilPolarization(component, 1j * component)
        ),
        wavelength_m=532e-9,
    )


def _joint_fixture_name(fixture: Mapping[str, object]) -> str:
    return ":".join(
        (
            f"na={fixture['numerical_aperture']}",
            f"polarization={fixture['polarization']}",
            f"z={fixture['axial_offset_wavelengths']}lambda",
        )
    )


def _joint_fixture_matrix() -> list[dict[str, object]]:
    return [
        {
            **dict(item),
            "transverse_indices": [
                list(indices) for indices in item["transverse_indices"]
            ],
        }
        for item in _JOINT_FIXTURE_MATRIX
    ]


def _fft_coordinates(
    pupil: AplanaticPupil,
    realization: FourierDebyeRealization,
) -> tuple[FocalCoordinates, tuple[int, int, int]]:
    if not isinstance(realization, FFTDebyeRealization):
        raise TypeError("fft_debye_realization_required")
    axis = fft_focal_axis(pupil, realization=realization)
    center = len(axis) // 2
    coordinates = FocalCoordinates(
        horizontal_m=(axis[center - 1], axis[center], axis[center + 1]),
        vertical_m=(0.0, 0.0, 0.0),
        axial_m=(0.0, 0.0, 0.0),
    )
    return coordinates, (0, 1, 2)


def _czt_coordinates(
    pupil: AplanaticPupil,
    realization: FourierDebyeRealization,
) -> tuple[FocalCoordinates, tuple[int, int, int]]:
    if not isinstance(realization, CZTDebyeRealization):
        raise TypeError("czt_debye_realization_required")
    offset = 0.12 * pupil.wavelength_m
    return (
        FocalCoordinates(
            horizontal_m=(-offset, 0.0, offset),
            vertical_m=(0.0, 0.0, 0.0),
            axial_m=(0.0, 0.0, 0.0),
        ),
        (0, 1, 2),
    )


def _evaluate_fft(
    pupil: AplanaticPupil,
    coordinates: FocalCoordinates,
    realization: FourierDebyeRealization,
) -> DebyeObservation:
    if not isinstance(realization, FFTDebyeRealization):
        raise TypeError("fft_debye_realization_required")
    return evaluate_fft_debye(pupil, coordinates, realization=realization)


def _evaluate_czt(
    pupil: AplanaticPupil,
    coordinates: FocalCoordinates,
    realization: FourierDebyeRealization,
) -> DebyeObservation:
    if not isinstance(realization, CZTDebyeRealization):
        raise TypeError("czt_debye_realization_required")
    return evaluate_czt_debye(pupil, coordinates, realization=realization)


def _failed_qualification(
    realization: FourierDebyeRealization,
    *,
    reason: str,
) -> AplanaticFocusQualification:
    return AplanaticFocusQualification(
        realization=realization,
        reference_method=_REFERENCE_METHOD,
        realization_facts=realization.as_mapping(),
        reference_fixtures=_REFERENCE_FIXTURES,
        fixture_errors={},
        is_qualified=False,
        reason=reason,
    )


def _fetch_document(
    fetch: Callable[[Reference], bytes],
    reference: Reference,
) -> Document:
    body = fetch(reference)
    if reference_for(body) != reference:
        raise ValueError("aplanatic_reference_qualification_reference_mismatch")
    return Document.from_bytes(body)


def _require_independent_document(
    document: Document,
    realization: Mapping[str, object],
) -> None:
    values = document.values
    fixture_errors = _mapping(values.get("fixture_errors"))
    if (
        document.schema_identifier != APLANATIC_FOCUS_QUALIFICATION_SCHEMA
        or values.get("qualified") is not True
        or values.get("reason") is not None
        or values.get("realization") != realization
        or values.get("reference_method") != _REFERENCE_METHOD
        or values.get("reference_fixtures") != list(_REFERENCE_FIXTURES)
        or set(fixture_errors) != set(_REFERENCE_FIXTURES)
    ):
        raise ValueError("aplanatic_reference_independent_qualification_invalid")
    for fixture_name in _REFERENCE_FIXTURES:
        fixture_error = float(str(fixture_errors[fixture_name]))
        if (
            not math.isfinite(fixture_error)
            or fixture_error < 0
            or fixture_error > _ERROR_LIMITS[fixture_name]
        ):
            raise ValueError("aplanatic_reference_independent_qualification_invalid")


def _require_joint_document(
    document: Document,
    *,
    fft: FFTDebyeRealization,
    czt: CZTDebyeRealization,
    fft_reference: Reference,
    czt_reference: Reference,
) -> None:
    values = document.values
    agreements = _mapping(values.get("fixture_agreements"))
    if (
        document.schema_identifier != APLANATIC_REFERENCE_QUALIFICATION_SCHEMA
        or values.get("qualified") is not True
        or values.get("reason") is not None
        or values.get("error_limit") != repr(_JOINT_ERROR_LIMIT)
        or values.get("fixture_matrix") != _joint_fixture_matrix()
        or values.get("fft_realization") != fft.as_mapping()
        or values.get("czt_realization") != czt.as_mapping()
        or Reference.from_mapping(_mapping(values.get("fft_qualification_reference")))
        != fft_reference
        or Reference.from_mapping(_mapping(values.get("czt_qualification_reference")))
        != czt_reference
        or set(agreements)
        != {_joint_fixture_name(item) for item in _JOINT_FIXTURE_MATRIX}
    ):
        raise ValueError("aplanatic_reference_joint_qualification_invalid")
    for value in agreements.values():
        metrics = _mapping(value)
        if set(metrics) != {
            "aligned_complex_error",
            "unit_integral_intensity_error",
        } or any(
            not math.isfinite(float(str(error)))
            or float(str(error)) > _JOINT_ERROR_LIMIT
            or float(str(error)) < 0
            for error in metrics.values()
        ):
            raise ValueError("aplanatic_reference_joint_qualification_invalid")


def _restore_fft_realization(
    values: Mapping[str, object],
) -> FFTDebyeRealization:
    sampling = _mapping(values.get("sampling"))
    realization = FFTDebyeRealization(
        device=str(values["device"]),
        pupil_samples=int(str(sampling["direction_cosine_samples_per_axis"])),
    )
    if realization.as_mapping() != values:
        raise ValueError("aplanatic_reference_fft_realization_invalid")
    return realization


def _restore_czt_realization(
    values: Mapping[str, object],
) -> CZTDebyeRealization:
    sampling = _mapping(values.get("sampling"))
    realization = CZTDebyeRealization(
        device=str(values["device"]),
        pupil_samples=int(str(sampling["direction_cosine_samples_per_axis"])),
    )
    if realization.as_mapping() != values:
        raise ValueError("aplanatic_reference_czt_realization_invalid")
    return realization


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("aplanatic_reference_mapping_invalid")
    return value


def _cartesian_coordinates(
    horizontal_axis_m: tuple[float, ...],
    vertical_axis_m: tuple[float, ...],
    *,
    axial_offset_m: float,
) -> FocalCoordinates:
    point_count = len(horizontal_axis_m) * len(vertical_axis_m)
    return FocalCoordinates(
        tuple(
            horizontal
            for _vertical in vertical_axis_m
            for horizontal in horizontal_axis_m
        ),
        tuple(
            vertical
            for vertical in vertical_axis_m
            for _horizontal in horizontal_axis_m
        ),
        (axial_offset_m,) * point_count,
    )


__all__ = [
    "APLANATIC_REFERENCE_BINDING_SCHEMA",
    "AplanaticFocusQualification",
    "AplanaticReferenceQualification",
    "aplanatic_reference_binding",
    "form_aplanatic_reference",
    "qualify_aplanatic_reference",
    "qualify_czt_debye",
    "qualify_fft_debye",
    "restore_aplanatic_reference_binding",
]
