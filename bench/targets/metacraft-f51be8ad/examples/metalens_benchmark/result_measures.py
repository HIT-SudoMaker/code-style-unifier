from __future__ import annotations

from decimal import Decimal

from metacraft.authority import Reference
from metacraft.science.metalens.aperture import (Aperture, Circle, Ellipse,
                                                 Rectangle, Square)
from metacraft.science.metalens.result import (GeometricResult, MetalensResult,
                                               PointwiseGeometricResult,
                                               PointwisePropagationResult,
                                               PropagationResult)

from .contract import (BenchmarkResultMeasures, CircleGeometryRange,
                       EllipseGeometryRange, MeasureMeaning,
                       RectangleGeometryRange, ResultGeometryMeasure,
                       ResultMeasureUnavailable, ResultQuantityMeasure,
                       ResultRangeMeasure, ResultTextMeasure,
                       SquareGeometryRange)

_RESULT_SCOPE = "the admitted metalens Result"
_ABSOLUTE_LENGTH = "absolute length"


def restore_benchmark_result_measures(
    conclusion: MetalensResult,
) -> BenchmarkResultMeasures:
    """Project one closed metalens Result without attribute probing."""

    if isinstance(conclusion, PropagationResult):
        phase_coverage = ResultTextMeasure(
            value=f"{conclusion.phase_set.levels}-state propagation phase set",
            definition="One admitted finite propagation-phase realization.",
            source_references=(conclusion.phase_set_reference,),
        )
        magnitudes = tuple(
            (
                state.transmission_real * state.transmission_real
                + state.transmission_imaginary * state.transmission_imaginary
            ).sqrt()
            for state in conclusion.phase_set.states
        )
        powers = tuple(state.useful_power for state in conclusion.phase_set.states)
        transmitted_magnitude = ResultRangeMeasure(
            min(magnitudes),
            max(magnitudes),
            _meaning(
                unit="ratio",
                normalization="complex transmission amplitude magnitude",
                definition=(
                    "Range of admitted selected-state complex transmission "
                    "magnitudes."
                ),
            ),
            (conclusion.phase_set_reference,),
        )
        transmitted_power = ResultRangeMeasure(
            min(powers),
            max(powers),
            _meaning(
                unit="ratio",
                normalization="useful transmitted power / incident power",
                definition="Range of admitted selected-state useful powers.",
            ),
            (conclusion.phase_set_reference,),
        )
        orientation_relation = _unavailable(
            "A propagation-phase Result has no orientation relation."
        )
        polarization_conversion = _unavailable(
            "A propagation-phase Result has no geometric conversion channel."
        )
        complex_focal_field = _unavailable(
            "A low-NA Result has no aplanatic complex-field comparison."
        )
    elif isinstance(conclusion, GeometricResult):
        phase_coverage = _unavailable(
            "A geometric-phase Result has no propagation phase set."
        )
        transmitted_magnitude = _unavailable(
            "This Result does not establish one scalar transmission magnitude."
        )
        transmitted_power = _state_power_range(
            conclusion.aperture,
            conclusion.aperture_reference,
        )
        orientation_relation = ResultTextMeasure(
            value=(
                "geometric phase sign "
                f"{conclusion.orientation_relation.phase_sign:+d}"
            ),
            definition="Admitted orientation-to-phase relation.",
            source_references=(conclusion.orientation_relation_reference,),
        )
        polarization_conversion = _state_power_range(
            conclusion.aperture,
            conclusion.aperture_reference,
        )
        complex_focal_field = _unavailable(
            "A low-NA Result has no aplanatic complex-field comparison."
        )
    elif isinstance(conclusion, PointwisePropagationResult):
        phase_coverage = ResultTextMeasure(
            value="pointwise propagation-phase assignment",
            definition="One admitted full-library pointwise assignment.",
            source_references=(conclusion.library.evidence_reference,),
        )
        transmitted_magnitude = _unavailable(
            "The pointwise result retains response surfaces, not one scalar range."
        )
        transmitted_power = _state_power_range(
            conclusion.aperture,
            conclusion.aperture_reference,
        )
        orientation_relation = _unavailable(
            "A propagation-phase Result has no orientation relation."
        )
        polarization_conversion = _unavailable(
            "A propagation-phase Result has no geometric conversion channel."
        )
        complex_focal_field = _aligned_complex_error_measure(conclusion)
    elif isinstance(conclusion, PointwiseGeometricResult):
        phase_coverage = _unavailable(
            "A geometric-phase Result has no propagation phase set."
        )
        transmitted_magnitude = _unavailable(
            "The pointwise result retains response surfaces, not one scalar range."
        )
        transmitted_power = _state_power_range(
            conclusion.aperture,
            conclusion.aperture_reference,
        )
        orientation_relation = ResultTextMeasure(
            value=(
                "geometric phase sign "
                f"{conclusion.orientation_relation.phase_sign:+d}"
            ),
            definition="Admitted orientation-to-phase relation.",
            source_references=(conclusion.orientation_relation_reference,),
        )
        polarization_conversion = _state_power_range(
            conclusion.aperture,
            conclusion.aperture_reference,
        )
        complex_focal_field = _aligned_complex_error_measure(conclusion)
    else:
        raise TypeError("metalens_benchmark_result_type_unsupported")

    focus = conclusion.focus
    focus_reference = conclusion.focus_reference
    x_width = focus.x_half_maximum.width_m
    y_width = focus.y_half_maximum.width_m
    if x_width is None or y_width is None:
        raise ValueError("benchmark_result_half_maximum_incomplete")
    return BenchmarkResultMeasures(
        cell_period=_cell_period_measure(
            conclusion.aperture,
            conclusion.aperture_reference,
        ),
        atom_height=_atom_height_measure(
            conclusion.aperture,
            conclusion.aperture_reference,
        ),
        lateral_geometry=_geometry_measure(
            conclusion.aperture,
            conclusion.aperture_reference,
        ),
        phase_coverage=phase_coverage,
        transmitted_magnitude=transmitted_magnitude,
        transmitted_power=transmitted_power,
        spatial_phase_sampling=_unavailable(
            "The Result carries the realized aperture, not a paper sampling metric."
        ),
        orientation_relation=orientation_relation,
        polarization_conversion=polarization_conversion,
        focus_efficiency=_focus_quantity(
            focus.focus_efficiency,
            "ratio",
            "focused power / incident reference power",
            (
                "Focused power inside radius 0.61 wavelength / numerical "
                "aperture around the focal peak."
            ),
            focus_reference,
        ),
        focal_shift=_focus_quantity(
            focus.focal_shift_m,
            "m",
            _ABSOLUTE_LENGTH,
            "Found focal-plane coordinate minus expected coordinate.",
            focus_reference,
        ),
        x_half_maximum_width=_focus_quantity(
            x_width,
            "m",
            _ABSOLUTE_LENGTH,
            "Full width between half-maximum crossings along x.",
            focus_reference,
        ),
        y_half_maximum_width=_focus_quantity(
            y_width,
            "m",
            _ABSOLUTE_LENGTH,
            "Full width between half-maximum crossings along y.",
            focus_reference,
        ),
        mean_half_maximum_width=_focus_quantity(
            (
                x_width
                + y_width
            )
            / 2,
            "m",
            _ABSOLUTE_LENGTH,
            "Arithmetic mean of the admitted x and y half-maximum widths.",
            focus_reference,
        ),
        vertical_cut_half_maximum_width=_unavailable(
            "MetaCraft reports independent x and y cuts, not a paper vertical cut."
        ),
        transmitted_fraction=_focus_quantity(
            focus.transmitted_fraction,
            "ratio",
            "transmitted power / incident reference power",
            "Through-plane transmitted power fraction before focal bucketing.",
            focus_reference,
        ),
        focused_fraction=_focus_quantity(
            focus.focused_fraction,
            "ratio",
            "focused power / transmitted power",
            "Fraction of transmitted power inside the declared focal bucket.",
            focus_reference,
        ),
        complex_focal_field=complex_focal_field,
        longitudinal_power_fraction=_unavailable(
            "No admitted Result establishes longitudinal component power fraction."
        ),
    )


def _meaning(
    *,
    unit: str,
    normalization: str,
    definition: str,
) -> MeasureMeaning:
    return MeasureMeaning(
        unit=unit,
        scope=_RESULT_SCOPE,
        normalization=normalization,
        definition=definition,
    )


def _focus_quantity(
    value: float,
    unit: str,
    normalization: str,
    definition: str,
    source_reference: Reference,
) -> ResultQuantityMeasure:
    return ResultQuantityMeasure(
        Decimal(str(value)),
        _meaning(
            unit=unit,
            normalization=normalization,
            definition=definition,
        ),
        (source_reference,),
    )


def _unavailable(reason: str) -> ResultMeasureUnavailable:
    return ResultMeasureUnavailable(reason)


def _cell_period_measure(
    aperture: Aperture,
    aperture_reference: Reference,
) -> ResultQuantityMeasure:
    periods_nm = {cell.period_nm for cell in aperture.cells}
    if len(periods_nm) != 1:
        raise ValueError("benchmark_result_cell_period_mixed")
    return ResultQuantityMeasure(
        Decimal(next(iter(periods_nm))),
        _meaning(
            unit="nm",
            normalization=_ABSOLUTE_LENGTH,
            definition=(
                "Physical lattice period of every admitted aperture cell."
            ),
        ),
        (aperture_reference,),
    )


def _atom_height_measure(
    aperture: Aperture,
    aperture_reference: Reference,
) -> ResultQuantityMeasure:
    heights_nm = {cell.height_nm for cell in aperture.cells}
    if len(heights_nm) != 1:
        raise ValueError("benchmark_result_atom_height_mixed")
    return ResultQuantityMeasure(
        Decimal(next(iter(heights_nm))),
        _meaning(
            unit="nm",
            normalization=_ABSOLUTE_LENGTH,
            definition="Physical height of every admitted aperture cell.",
        ),
        (aperture_reference,),
    )


def _geometry_measure(
    aperture: Aperture,
    aperture_reference: Reference,
) -> ResultGeometryMeasure:
    geometries = tuple(cell.geometry for cell in aperture.cells)
    first = geometries[0]
    circles = tuple(item for item in geometries if isinstance(item, Circle))
    squares = tuple(item for item in geometries if isinstance(item, Square))
    rectangles = tuple(
        item for item in geometries if isinstance(item, Rectangle)
    )
    ellipses = tuple(item for item in geometries if isinstance(item, Ellipse))
    if isinstance(first, Circle) and len(circles) == len(geometries):
        diameters = tuple(item.diameter_nm for item in circles)
        geometry = CircleGeometryRange(min(diameters), max(diameters))
    elif isinstance(first, Square) and len(squares) == len(geometries):
        widths = tuple(item.width_nm for item in squares)
        geometry = SquareGeometryRange(min(widths), max(widths))
    elif isinstance(first, Rectangle) and len(rectangles) == len(geometries):
        short_sides = tuple(item.short_side_nm for item in rectangles)
        long_sides = tuple(item.long_side_nm for item in rectangles)
        geometry = RectangleGeometryRange(
            min(short_sides),
            max(short_sides),
            min(long_sides),
            max(long_sides),
        )
    elif isinstance(first, Ellipse) and len(ellipses) == len(geometries):
        minor_axes = tuple(item.minor_axis_nm for item in ellipses)
        major_axes = tuple(item.major_axis_nm for item in ellipses)
        geometry = EllipseGeometryRange(
            min(minor_axes),
            max(minor_axes),
            min(major_axes),
            max(major_axes),
        )
    else:
        raise ValueError("benchmark_result_geometry_mixed")
    return ResultGeometryMeasure(geometry, (aperture_reference,))


def _state_power_range(
    aperture: Aperture,
    aperture_reference: Reference,
) -> ResultRangeMeasure:
    powers = tuple(state.useful_power for state in aperture.states)
    return ResultRangeMeasure(
        min(powers),
        max(powers),
        _meaning(
            unit="ratio",
            normalization="useful channel power / incident power",
            definition="Range of admitted state useful-channel powers.",
        ),
        (aperture_reference,),
    )


def _aligned_complex_error_measure(
    conclusion: PointwisePropagationResult | PointwiseGeometricResult,
) -> ResultQuantityMeasure:
    return ResultQuantityMeasure(
        value=Decimal(str(conclusion.focal_comparison.aligned_complex_error)),
        meaning=_meaning(
            unit="ratio",
            normalization="phase-and-amplitude-aligned vector-field L2 error",
            definition=(
                "Relative L2 residual after one global complex alignment of "
                "the complete x/y/z focal field."
            ),
        ),
        source_references=(conclusion.focal_comparison_reference,),
    )
