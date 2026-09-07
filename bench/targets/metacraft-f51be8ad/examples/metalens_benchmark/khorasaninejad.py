from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from metacraft.materials import MaterialSource
from metacraft.science.metalens.brief import (
    AtomIntent,
    ControlStrategy,
    MaterialIntent,
    MetalensBrief,
    MonochromaticSpectrum,
    Polarization,
)

from .case import MetalensBenchmarkCase
from .contract import (
    BenchmarkAlignment,
    BenchmarkMeasure,
    BenchmarkSubject,
    ComparisonContract,
    ContextRule,
    ExcludedAlignment,
    IndependentAlignment,
    MatchedAlignment,
    MeasureMeaning,
    NotReportedFact,
    NotReportedRule,
    PublishedQuantity,
    PublishedReference,
    RectangleGeometryRange,
    ReferenceFactName,
    ReportedFact,
    SourceLocator,
    UnresolvedFact,
    WithheldAlignment,
)


_CITATION = "doi:10.1126/science.aaf6644"
_FIGURE_1 = SourceLocator(
    citation=_CITATION,
    location="Figure 1, Figure 1F caption, and planar-lens design text",
)
_EQUATIONS_1_AND_2 = SourceLocator(
    citation=_CITATION,
    location="Design Equations 1 and 2",
)
_FABRICATION = SourceLocator(
    citation=_CITATION,
    location="Planar lens design and fabrication section",
)
_FIGURE_2 = SourceLocator(
    citation=_CITATION,
    location="Figure 2B/H and caption",
)
_FIGURE_3 = SourceLocator(
    citation=_CITATION,
    location="Characterizing metalens performance section and Figure 3A",
)


@dataclass(frozen=True, slots=True)
class RotationAwareRectangleGeometry:
    """Keep reported fin dimensions and their rotated clearance together."""

    rectangle: RectangleGeometryRange
    period_nm: Decimal
    height_nm: Decimal
    minimum_feature_nm: Decimal
    feature_aspect_ratio: Decimal
    axis_aligned_minimum_gap_nm: Decimal
    diagonal_nm: Decimal
    minimum_orientation_envelope_gap_nm: Decimal
    orientation_envelope_gap_aspect_ratio: Decimal

    def __post_init__(self) -> None:
        values = (
            self.period_nm,
            self.height_nm,
            self.minimum_feature_nm,
            self.feature_aspect_ratio,
            self.axis_aligned_minimum_gap_nm,
            self.diagonal_nm,
            self.minimum_orientation_envelope_gap_nm,
            self.orientation_envelope_gap_aspect_ratio,
        )
        if any(not value.is_finite() or value <= 0 for value in values):
            raise ValueError("rotation_aware_rectangle_geometry_invalid")
        if self.minimum_orientation_envelope_gap_nm >= self.axis_aligned_minimum_gap_nm:
            raise ValueError("rotation_aware_rectangle_envelope_invalid")
        rectangle = self.rectangle
        if (
            rectangle.minimum_short_side_nm != rectangle.maximum_short_side_nm
            or rectangle.minimum_long_side_nm != rectangle.maximum_long_side_nm
        ):
            raise ValueError("rotation_aware_rectangle_not_fixed")
        short_side = Decimal(rectangle.minimum_short_side_nm)
        long_side = Decimal(rectangle.minimum_long_side_nm)
        diagonal = (long_side**2 + short_side**2).sqrt()
        envelope_gap = self.period_nm - diagonal
        expected = (
            short_side,
            (self.height_nm / short_side).quantize(Decimal("0.0001")),
            self.period_nm - long_side,
            diagonal.quantize(Decimal("0.0001")),
            envelope_gap.quantize(Decimal("0.0001")),
            (self.height_nm / envelope_gap).quantize(Decimal("0.0001")),
        )
        actual = (
            self.minimum_feature_nm,
            self.feature_aspect_ratio,
            self.axis_aligned_minimum_gap_nm,
            self.diagonal_nm,
            self.minimum_orientation_envelope_gap_nm,
            self.orientation_envelope_gap_aspect_ratio,
        )
        if actual != expected:
            raise ValueError("rotation_aware_rectangle_derivation_invalid")

    @classmethod
    def from_cell(
        cls,
        *,
        period_nm: int,
        height_nm: int,
        long_side_nm: int,
        short_side_nm: int,
    ) -> RotationAwareRectangleGeometry:
        """Derive the all-orientation gap instead of using one axis cut."""

        period = Decimal(period_nm)
        height = Decimal(height_nm)
        long_side = Decimal(long_side_nm)
        short_side = Decimal(short_side_nm)
        diagonal = (long_side**2 + short_side**2).sqrt()
        envelope_gap = period - diagonal
        return cls(
            rectangle=RectangleGeometryRange(
                minimum_short_side_nm=short_side_nm,
                maximum_short_side_nm=short_side_nm,
                minimum_long_side_nm=long_side_nm,
                maximum_long_side_nm=long_side_nm,
            ),
            period_nm=period,
            height_nm=height,
            minimum_feature_nm=short_side,
            feature_aspect_ratio=(height / short_side).quantize(Decimal("0.0001")),
            axis_aligned_minimum_gap_nm=period - long_side,
            diagonal_nm=diagonal.quantize(Decimal("0.0001")),
            minimum_orientation_envelope_gap_nm=envelope_gap.quantize(
                Decimal("0.0001")
            ),
            orientation_envelope_gap_aspect_ratio=(height / envelope_gap).quantize(
                Decimal("0.0001")
            ),
        )


def _reported_quantity(
    key: ReferenceFactName,
    value: str,
    unit: str,
    meaning: str,
    source: SourceLocator,
    *,
    measure_meaning: MeasureMeaning | None = None,
) -> ReportedFact[PublishedQuantity]:
    return ReportedFact(
        key=key,
        value=PublishedQuantity(Decimal(value), unit),
        meaning=meaning,
        sources=(source,),
        measure_meaning=measure_meaning,
    )


_WAVELENGTH = _reported_quantity(
    ReferenceFactName.WAVELENGTH,
    "532",
    "nm",
    "Design wavelength of the selected visible metalens.",
    _FIGURE_1,
)
_NUMERICAL_APERTURE = _reported_quantity(
    ReferenceFactName.NUMERICAL_APERTURE,
    "0.8",
    "ratio",
    "Numerical aperture of the selected 532 nm device.",
    _FIGURE_1,
)
_FOCAL_LENGTH = _reported_quantity(
    ReferenceFactName.FOCAL_LENGTH,
    "90",
    "um",
    "Focal length of the selected 532 nm device.",
    _FIGURE_1,
)
_INCIDENT_POLARIZATION = ReportedFact(
    key=ReferenceFactName.INCIDENT_POLARIZATION,
    value=Polarization(kind="circular", handedness="right"),
    meaning="Right-circular illumination used for the reported device results.",
    sources=(_EQUATIONS_1_AND_2, _FIGURE_3),
)
_CONTROL_STRATEGY = ReportedFact(
    key=ReferenceFactName.CONTROL_STRATEGY,
    value=ControlStrategy.GEOMETRIC_PHASE,
    meaning="Rotation-controlled Pancharatnam-Berry geometric phase.",
    sources=(_EQUATIONS_1_AND_2,),
)
_ATOM_SHAPE = ReportedFact(
    key=ReferenceFactName.ATOM_SHAPE,
    value="rectangular fin",
    meaning="Rectangular amorphous-titanium-dioxide nanofin.",
    sources=(_FIGURE_1,),
)
_ATOM_MATERIAL = ReportedFact(
    key=ReferenceFactName.ATOM_MATERIAL,
    value="amorphous titanium dioxide",
    meaning="Amorphous titanium-dioxide meta-atom material family.",
    sources=(_FIGURE_1, _FABRICATION),
)
_SUBSTRATE_MATERIAL = ReportedFact(
    key=ReferenceFactName.SUBSTRATE_MATERIAL,
    value="glass",
    meaning="Glass substrate material family.",
    sources=(_FIGURE_1,),
)
_APERTURE = ReportedFact(
    key=ReferenceFactName.APERTURE,
    value="circular aperture, 240 um diameter",
    meaning="Circular aperture of the selected 532 nm device.",
    sources=(_FIGURE_1,),
)
_CELL_PERIOD = _reported_quantity(
    ReferenceFactName.CELL_PERIOD,
    "325",
    "nm",
    "Square-cell period of the selected 532 nm device.",
    _FIGURE_1,
)
_ATOM_HEIGHT = _reported_quantity(
    ReferenceFactName.ATOM_HEIGHT,
    "600",
    "nm",
    "Height of the selected amorphous-titanium-dioxide nanofin.",
    _FIGURE_1,
)
_LATERAL_GEOMETRY = ReportedFact(
    key=ReferenceFactName.LATERAL_GEOMETRY,
    value=RotationAwareRectangleGeometry.from_cell(
        period_nm=325,
        height_nm=600,
        long_side_nm=250,
        short_side_nm=95,
    ),
    meaning=(
        "The source reports a 250 by 95 nm rectangle. The typed audit keeps "
        "its 75 nm axis-aligned gap separate from the approximately 57.5584 "
        "nm all-orientation envelope derived from the rectangle diagonal."
    ),
    sources=(_FIGURE_1,),
)
_PHASE_COVERAGE = ReportedFact(
    key=ReferenceFactName.PHASE_COVERAGE,
    value="orientation over [0, pi) covers one full 2 pi geometric-phase turn",
    meaning="Continuous geometric-phase coverage of the selected fin family.",
    sources=(_EQUATIONS_1_AND_2,),
)
_TRANSMITTED_MAGNITUDE = UnresolvedFact(
    key=ReferenceFactName.TRANSMITTED_MAGNITUDE,
    meaning="Reusable complex transmission magnitude of the selected cell.",
    reviewed_sources=(_FIGURE_1, _EQUATIONS_1_AND_2),
    reason=(
        "The accessible article reports conversion efficiency rather than one "
        "reusable phase-bearing complex transmission value."
    ),
)
_TRANSMITTED_POWER = ReportedFact(
    key=ReferenceFactName.TRANSMITTED_POWER,
    value="simulated cell-family conversion efficiency reaches up to 95 percent",
    meaning="Cell-level opposite-helicity transmitted-power context.",
    sources=(_FIGURE_1,),
)
_SPATIAL_PHASE_SAMPLING = ReportedFact(
    key=ReferenceFactName.SPATIAL_PHASE_SAMPLING,
    value="325 nm square lattice with continuously rotated nanofins",
    meaning="Published cell sampling context for the selected device.",
    sources=(_FIGURE_1,),
)
_ORIENTATION_RELATION = ReportedFact(
    key=ReferenceFactName.ORIENTATION_RELATION,
    value="right-circular incidence gives geometric phase +2 * orientation",
    meaning=(
        "Orientation relation in the paper's propagation, handedness, viewing, "
        "and angle-sign convention."
    ),
    sources=(_EQUATIONS_1_AND_2,),
)
_POLARIZATION_CONVERSION = _reported_quantity(
    ReferenceFactName.POLARIZATION_CONVERSION,
    "0.95",
    "ratio",
    (
        "Maximum simulated opposite-helicity conversion efficiency reported "
        "for the wavelength-specific cell families."
    ),
    _FIGURE_1,
)
_FOCUS_EFFICIENCY = _reported_quantity(
    ReferenceFactName.FOCUS_EFFICIENCY,
    "0.73",
    "ratio",
    (
        "Measured focusing efficiency of the 532 nm device; the accessible "
        "article does not establish its denominator or focal bucket."
    ),
    _FIGURE_3,
)
_VERTICAL_WIDTH_MEANING = MeasureMeaning(
    unit="nm",
    scope="measured 532 nm device vertical focal-spot intensity cut",
    normalization="absolute length",
    definition="Measured FWHM of the single published vertical intensity cut.",
)
_VERTICAL_WIDTH = _reported_quantity(
    ReferenceFactName.VERTICAL_CUT_HALF_MAXIMUM_WIDTH,
    "375",
    "nm",
    "Measured FWHM of the single vertical focal-spot intensity cut.",
    _FIGURE_2,
    measure_meaning=_VERTICAL_WIDTH_MEANING,
)


def _not_reported(
    key: ReferenceFactName,
    meaning: str,
    reason: str,
) -> NotReportedFact:
    return NotReportedFact(
        key=key,
        meaning=meaning,
        reviewed_sources=(_FIGURE_2, _FIGURE_3),
        reason=reason,
    )


_FOCAL_SHIFT = _not_reported(
    ReferenceFactName.FOCAL_SHIFT,
    "Focal shift of the selected 532 nm device.",
    "No reusable focal-shift value is reported in the accessible article.",
)
_X_WIDTH = _not_reported(
    ReferenceFactName.X_HALF_MAXIMUM_WIDTH,
    "Independent x half-maximum width.",
    "The paper reports one vertical cut, not an independent x width.",
)
_Y_WIDTH = _not_reported(
    ReferenceFactName.Y_HALF_MAXIMUM_WIDTH,
    "Independent y half-maximum width.",
    "The paper reports one vertical cut, not an independent y width.",
)
_MEAN_WIDTH = _not_reported(
    ReferenceFactName.MEAN_HALF_MAXIMUM_WIDTH,
    "Mean x/y half-maximum width.",
    "The paper does not report an arithmetic mean of independent x and y widths.",
)
_TRANSMITTED_FRACTION = _not_reported(
    ReferenceFactName.TRANSMITTED_FRACTION,
    "Whole-device transmitted fraction.",
    "No compatible whole-device transmitted fraction is reported.",
)
_FOCUSED_FRACTION = _not_reported(
    ReferenceFactName.FOCUSED_FRACTION,
    "Focused fraction of transmitted power.",
    "No compatible focused-over-transmitted fraction is reported.",
)
_COMPLEX_FIELD = _not_reported(
    ReferenceFactName.COMPLEX_FOCAL_FIELD,
    "Reusable phase-bearing x/y/z complex focal field.",
    (
        "The accessible article publishes intensity profiles and cuts, not a "
        "reusable complex field; the official supplement remained inaccessible."
    ),
)
_LONGITUDINAL_POWER = _not_reported(
    ReferenceFactName.LONGITUDINAL_POWER_FRACTION,
    "Longitudinal-component power fraction.",
    (
        "The accessible article reports no longitudinal-component power "
        "fraction; the official supplement remained inaccessible."
    ),
)


_REFERENCE = PublishedReference(
    citation=_CITATION,
    selected_device="532 nm device",
    facts=(
        _WAVELENGTH,
        _NUMERICAL_APERTURE,
        _FOCAL_LENGTH,
        _INCIDENT_POLARIZATION,
        _CONTROL_STRATEGY,
        _ATOM_SHAPE,
        _ATOM_MATERIAL,
        _SUBSTRATE_MATERIAL,
        _APERTURE,
        _CELL_PERIOD,
        _ATOM_HEIGHT,
        _LATERAL_GEOMETRY,
        _PHASE_COVERAGE,
        _TRANSMITTED_MAGNITUDE,
        _TRANSMITTED_POWER,
        _SPATIAL_PHASE_SAMPLING,
        _ORIENTATION_RELATION,
        _POLARIZATION_CONVERSION,
        _FOCUS_EFFICIENCY,
        _FOCAL_SHIFT,
        _X_WIDTH,
        _Y_WIDTH,
        _MEAN_WIDTH,
        _VERTICAL_WIDTH,
        _TRANSMITTED_FRACTION,
        _FOCUSED_FRACTION,
        _COMPLEX_FIELD,
        _LONGITUDINAL_POWER,
    ),
    exclusions=(
        "405 nm device",
        "660 nm device",
        "paper-selected cell geometry as a production constraint",
        "whole-device Maxwell and fabrication reproduction",
    ),
)


_ALIGNMENT = BenchmarkAlignment(
    (
        MatchedAlignment(BenchmarkSubject.WAVELENGTH, _WAVELENGTH.key),
        MatchedAlignment(BenchmarkSubject.NUMERICAL_APERTURE, _NUMERICAL_APERTURE.key),
        MatchedAlignment(BenchmarkSubject.FOCAL_LENGTH, _FOCAL_LENGTH.key),
        MatchedAlignment(
            BenchmarkSubject.INCIDENT_POLARIZATION,
            _INCIDENT_POLARIZATION.key,
        ),
        MatchedAlignment(BenchmarkSubject.CONTROL_STRATEGY, _CONTROL_STRATEGY.key),
        MatchedAlignment(BenchmarkSubject.ATOM_SHAPE, _ATOM_SHAPE.key),
        MatchedAlignment(BenchmarkSubject.ATOM_MATERIAL, _ATOM_MATERIAL.key),
        MatchedAlignment(
            BenchmarkSubject.SUBSTRATE_MATERIAL,
            _SUBSTRATE_MATERIAL.key,
        ),
        WithheldAlignment(BenchmarkSubject.APERTURE, _APERTURE.key),
        IndependentAlignment(
            BenchmarkSubject.ASPECT_LIMIT,
            (
                "The brief supplies limit 8 as one process input without a "
                "scan. It is not the paper cell's rotation-envelope ratio."
            ),
        ),
        IndependentAlignment(
            BenchmarkSubject.DIMENSION_STEP,
            (
                "The 10 nm fabrication increment is a MetaCraft input and "
                "does not reproduce the paper's 325 and 95 nm dimensions."
            ),
        ),
        ExcludedAlignment(
            BenchmarkSubject.FABRICATION_ROUTE,
            (
                "The blind brief does not prescribe the resist-mold, conformal "
                "ALD, blanket-RIE, and resist-removal fabrication route."
            ),
        ),
        WithheldAlignment(BenchmarkSubject.CELL_PERIOD, _CELL_PERIOD.key),
        WithheldAlignment(BenchmarkSubject.ATOM_HEIGHT, _ATOM_HEIGHT.key),
        WithheldAlignment(BenchmarkSubject.LATERAL_GEOMETRY, _LATERAL_GEOMETRY.key),
    )
)


_CONTRACT = ComparisonContract(
    (
        ContextRule(
            BenchmarkMeasure.CELL_PERIOD,
            _CELL_PERIOD.key,
            "The 325 nm paper period is post-design context.",
        ),
        ContextRule(
            BenchmarkMeasure.ATOM_HEIGHT,
            _ATOM_HEIGHT.key,
            "The 600 nm paper height is post-design context.",
        ),
        ContextRule(
            BenchmarkMeasure.LATERAL_GEOMETRY,
            _LATERAL_GEOMETRY.key,
            (
                "The paper rectangle and its rotation-aware clearance are "
                "context, not a production geometry target."
            ),
        ),
        ContextRule(
            BenchmarkMeasure.PHASE_COVERAGE,
            _PHASE_COVERAGE.key,
            "Continuous paper coverage and admitted finite orientations differ.",
        ),
        ContextRule(
            BenchmarkMeasure.TRANSMITTED_MAGNITUDE,
            _TRANSMITTED_MAGNITUDE.key,
            "No reusable complex-amplitude value is resolved.",
        ),
        ContextRule(
            BenchmarkMeasure.TRANSMITTED_POWER,
            _TRANSMITTED_POWER.key,
            "The paper maximum and admitted selected-state range are unlike values.",
        ),
        ContextRule(
            BenchmarkMeasure.SPATIAL_PHASE_SAMPLING,
            _SPATIAL_PHASE_SAMPLING.key,
            "The paper lattice is context for an independently selected aperture.",
        ),
        ContextRule(
            BenchmarkMeasure.ORIENTATION_RELATION,
            _ORIENTATION_RELATION.key,
            "Coordinate, handedness, viewing, and angle-sign conventions stay visible.",
        ),
        ContextRule(
            BenchmarkMeasure.POLARIZATION_CONVERSION,
            _POLARIZATION_CONVERSION.key,
            "A cell-family maximum is not a selected-state numeric delta.",
        ),
        ContextRule(
            BenchmarkMeasure.FOCUS_EFFICIENCY,
            _FOCUS_EFFICIENCY.key,
            (
                "The denominator and focal collection bucket are unavailable "
                "from the accessible primary source."
            ),
        ),
        NotReportedRule(BenchmarkMeasure.FOCAL_SHIFT, _FOCAL_SHIFT.key),
        NotReportedRule(BenchmarkMeasure.X_HALF_MAXIMUM_WIDTH, _X_WIDTH.key),
        NotReportedRule(BenchmarkMeasure.Y_HALF_MAXIMUM_WIDTH, _Y_WIDTH.key),
        NotReportedRule(BenchmarkMeasure.MEAN_HALF_MAXIMUM_WIDTH, _MEAN_WIDTH.key),
        ContextRule(
            BenchmarkMeasure.VERTICAL_CUT_HALF_MAXIMUM_WIDTH,
            _VERTICAL_WIDTH.key,
            (
                "The paper reports one measured vertical cut, while MetaCraft "
                "retains independent x and y widths and their derived mean."
            ),
        ),
        NotReportedRule(
            BenchmarkMeasure.TRANSMITTED_FRACTION,
            _TRANSMITTED_FRACTION.key,
        ),
        NotReportedRule(BenchmarkMeasure.FOCUSED_FRACTION, _FOCUSED_FRACTION.key),
        NotReportedRule(BenchmarkMeasure.COMPLEX_FOCAL_FIELD, _COMPLEX_FIELD.key),
        NotReportedRule(
            BenchmarkMeasure.LONGITUDINAL_POWER_FRACTION,
            _LONGITUDINAL_POWER.key,
        ),
    )
)


_KHORASANINEJAD_BENCHMARK_CASE = MetalensBenchmarkCase(
    name="khorasaninejad-2016-high-na-geometric",
    brief=MetalensBrief(
        wording=(
            "Design a high-NA metalens at 532 nm with NA 0.8 and 90 um focal "
            "length. Use geometric phase, right-circular incidence, and "
            "rectangular amorphous titanium dioxide nanofins on glass. Use an "
            "aspect limit of 8 and a 10 nm fabrication increment for one local "
            "workstation."
        ),
        aim="metalens",
        objectives=("focus",),
        operating_spectrum=MonochromaticSpectrum(532),
        numerical_aperture=Decimal("0.8"),
        focal_length_um=Decimal("90"),
        incident_polarization=Polarization(kind="circular", handedness="right"),
        control_strategy=ControlStrategy.GEOMETRIC_PHASE,
        atom=AtomIntent(
            shape="rectangular fin",
            material=MaterialIntent(
                "amorphous titanium dioxide",
                MaterialSource.SOLVER_NATIVE,
            ),
        ),
        substrate=MaterialIntent("glass", MaterialSource.SOLVER_NATIVE),
        aspect_limit=8,
        solver_preference="lumerical_fdtd",
        dimension_step_nm=10,
        budget="workstation",
        omissions=(
            "aperture",
            "atom_height_nm",
            "cell_period_nm",
            "paper-selected cell geometry",
            "multiwavelength",
            "optimization",
        ),
    ),
    reference=_REFERENCE,
    alignment=_ALIGNMENT,
    contract=_CONTRACT,
)


def khorasaninejad_benchmark_case() -> MetalensBenchmarkCase:
    """Return the private Khorasaninejad high-NA geometric benchmark case."""

    return _KHORASANINEJAD_BENCHMARK_CASE
