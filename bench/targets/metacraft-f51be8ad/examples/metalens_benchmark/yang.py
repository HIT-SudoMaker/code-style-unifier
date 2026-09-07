from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from metacraft.materials import MaterialSource
from metacraft.science.metalens.brief import (
    ApertureExtent,
    ApertureFootprint,
    ApertureIntent,
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
    EllipseGeometryRange,
    ExcludedAlignment,
    IndependentAlignment,
    MatchedAlignment,
    NotApplicableRule,
    NotReportedFact,
    NotReportedRule,
    PublishedQuantity,
    PublishedReference,
    ReferenceFactName,
    ReportedFact,
    SourceLocator,
    UnresolvedFact,
    WithheldAlignment,
)


_CITATION = "doi:10.1038/s41467-018-07056-6"
_DESIGN_DISCUSSION = SourceLocator(
    citation=_CITATION,
    location="Principle of metalens array design and circular-lens design discussion",
)
_FIGURE_2 = SourceLocator(
    citation=_CITATION,
    location="Figure 2b,c and accompanying meta-atom design text",
)
_EQUATIONS_2_AND_3 = SourceLocator(
    citation=_CITATION,
    location="Equations 2 and 3",
)
_SUPPORTING_NOTE_4 = SourceLocator(
    citation=_CITATION,
    location="Official supporting information, Note 4",
)


@dataclass(frozen=True, slots=True)
class CircularSublensFocusEfficiencies:
    """Keep the theoretical and measured Yang values visibly distinct."""

    theoretical: PublishedQuantity
    measured: PublishedQuantity


def _reported_quantity(
    key: ReferenceFactName,
    value: str,
    unit: str,
    meaning: str,
    source: SourceLocator = _DESIGN_DISCUSSION,
) -> ReportedFact[PublishedQuantity]:
    return ReportedFact(
        key=key,
        value=PublishedQuantity(Decimal(value), unit),
        meaning=meaning,
        sources=(source,),
    )


_WAVELENGTH = _reported_quantity(
    ReferenceFactName.WAVELENGTH,
    "1550",
    "nm",
    "Design wavelength of the selected circular-polarization sublens.",
)
_NUMERICAL_APERTURE = _reported_quantity(
    ReferenceFactName.NUMERICAL_APERTURE,
    "0.32",
    "ratio",
    "Numerical aperture of the selected circular-polarization sublens.",
)
_FOCAL_LENGTH = _reported_quantity(
    ReferenceFactName.FOCAL_LENGTH,
    "30",
    "um",
    "Focal length of the selected circular-polarization sublens.",
)
_INCIDENT_POLARIZATION = ReportedFact(
    key=ReferenceFactName.INCIDENT_POLARIZATION,
    value=Polarization(kind="circular", handedness="right"),
    meaning="Right-circular incident polarization for the selected sublens.",
    sources=(_DESIGN_DISCUSSION, _EQUATIONS_2_AND_3),
)
_CONTROL_STRATEGY = ReportedFact(
    key=ReferenceFactName.CONTROL_STRATEGY,
    value=ControlStrategy.GEOMETRIC_PHASE,
    meaning="Orientation-controlled geometric phase of one fixed Jones cell.",
    sources=(_EQUATIONS_2_AND_3,),
)
_ATOM_SHAPE = ReportedFact(
    key=ReferenceFactName.ATOM_SHAPE,
    value="elliptical pillar",
    meaning="Elliptical silicon meta atom selected for the circular sublens.",
    sources=(_FIGURE_2,),
)
_ATOM_MATERIAL = ReportedFact(
    key=ReferenceFactName.ATOM_MATERIAL,
    value="silicon",
    meaning="Meta-atom material family.",
    sources=(_FIGURE_2,),
)
_SUBSTRATE_MATERIAL = ReportedFact(
    key=ReferenceFactName.SUBSTRATE_MATERIAL,
    value="silicon dioxide",
    meaning="Substrate material family.",
    sources=(_FIGURE_2,),
)
_APERTURE_VALUE = ApertureIntent(
    site_count=15,
    extent=ApertureExtent.DIAMETER,
    footprint=ApertureFootprint.SQUARE,
)
_APERTURE = ReportedFact(
    key=ReferenceFactName.APERTURE,
    value=_APERTURE_VALUE,
    meaning="Square 15 by 15-site sublens with a 22.5 um side length.",
    sources=(_DESIGN_DISCUSSION,),
)
_CELL_PERIOD = _reported_quantity(
    ReferenceFactName.CELL_PERIOD,
    "1500",
    "nm",
    "Square-lattice period of the published sublens.",
    _FIGURE_2,
)
_ATOM_HEIGHT = _reported_quantity(
    ReferenceFactName.ATOM_HEIGHT,
    "340",
    "nm",
    "Height of the published silicon ellipse.",
    _FIGURE_2,
)
_LATERAL_GEOMETRY = ReportedFact(
    key=ReferenceFactName.LATERAL_GEOMETRY,
    value=EllipseGeometryRange(
        minimum_minor_axis_nm=480,
        maximum_minor_axis_nm=480,
        minimum_major_axis_nm=1350,
        maximum_major_axis_nm=1350,
    ),
    meaning="Fixed 1350 nm major axis and 480 nm minor axis.",
    sources=(_FIGURE_2,),
)
_PHASE_COVERAGE = ReportedFact(
    key=ReferenceFactName.PHASE_COVERAGE,
    value="orientation over [0, pi) covers one full 2 pi geometric-phase turn",
    meaning="Qualitative phase coverage of the fixed Jones cell.",
    sources=(_EQUATIONS_2_AND_3,),
)
_TRANSMITTED_MAGNITUDE = UnresolvedFact(
    key=ReferenceFactName.TRANSMITTED_MAGNITUDE,
    meaning="Complex-field transmission magnitude of the selected fixed ellipse.",
    reviewed_sources=(_FIGURE_2, _EQUATIONS_2_AND_3),
    reason=(
        "The reviewed source plots intensity transmittance and Jones terms but "
        "does not report one reusable complex-field magnitude for the selected cell."
    ),
)
_TRANSMITTED_POWER = UnresolvedFact(
    key=ReferenceFactName.TRANSMITTED_POWER,
    meaning="Opposite-handed transmitted power of the selected fixed ellipse.",
    reviewed_sources=(_FIGURE_2, _EQUATIONS_2_AND_3),
    reason=(
        "The ideal Jones-channel relation is stated without one exact measured "
        "power value for the selected cell."
    ),
)
_SPATIAL_PHASE_SAMPLING = ReportedFact(
    key=ReferenceFactName.SPATIAL_PHASE_SAMPLING,
    value="15 by 15 sites on a 1500 nm square lattice",
    meaning="Published spatial sampling of the selected sublens.",
    sources=(_DESIGN_DISCUSSION, _FIGURE_2),
)
_ORIENTATION_RELATION = ReportedFact(
    key=ReferenceFactName.ORIENTATION_RELATION,
    value=(
        "opposite-handed Jones terms carry handedness-dependent geometric "
        "phase with opposite signs"
    ),
    meaning=(
        "Orientation relation stated in the paper's propagation, handedness, "
        "viewing-direction, and angle-sign convention."
    ),
    sources=(_EQUATIONS_2_AND_3,),
)
_POLARIZATION_CONVERSION = ReportedFact(
    key=ReferenceFactName.POLARIZATION_CONVERSION,
    value="same-handed term ideally vanishes and the opposite-handed term remains",
    meaning="Ideal Jones-channel conversion of the selected fixed ellipse.",
    sources=(_EQUATIONS_2_AND_3,),
)
_FOCUS_EFFICIENCY = ReportedFact(
    key=ReferenceFactName.FOCUS_EFFICIENCY,
    value=CircularSublensFocusEfficiencies(
        theoretical=PublishedQuantity(Decimal("0.60"), "ratio"),
        measured=PublishedQuantity(Decimal("0.26"), "ratio"),
    ),
    meaning=(
        "Theoretical and measured circular-sublens focusing efficiencies, "
        "defined as focal-spot power divided by power impinging on the metalens; "
        "the focal-spot boundary is not reported."
    ),
    sources=(_DESIGN_DISCUSSION,),
)


def _not_reported(
    key: ReferenceFactName,
    meaning: str,
    reason: str,
) -> NotReportedFact:
    return NotReportedFact(
        key=key,
        meaning=meaning,
        reviewed_sources=(_DESIGN_DISCUSSION, _SUPPORTING_NOTE_4),
        reason=reason,
    )


_FOCAL_SHIFT = _not_reported(
    ReferenceFactName.FOCAL_SHIFT,
    "Focal shift of the selected circular sublens.",
    "No focal-shift value is published for the selected circular sublens.",
)
_X_WIDTH = _not_reported(
    ReferenceFactName.X_HALF_MAXIMUM_WIDTH,
    "Independent x half-maximum width.",
    "No independent x half-maximum width is published.",
)
_Y_WIDTH = _not_reported(
    ReferenceFactName.Y_HALF_MAXIMUM_WIDTH,
    "Independent y half-maximum width.",
    "No independent y half-maximum width is published.",
)
_MEAN_WIDTH = _not_reported(
    ReferenceFactName.MEAN_HALF_MAXIMUM_WIDTH,
    "Mean x/y half-maximum width.",
    "No mean x/y half-maximum width is published.",
)
_VERTICAL_WIDTH = _not_reported(
    ReferenceFactName.VERTICAL_CUT_HALF_MAXIMUM_WIDTH,
    "Vertical-cut half-maximum width.",
    "No vertical-cut half-maximum width is published.",
)
_TRANSMITTED_FRACTION = _not_reported(
    ReferenceFactName.TRANSMITTED_FRACTION,
    "Whole-sublens transmitted fraction.",
    "No compatible whole-sublens transmitted fraction is published.",
)
_FOCUSED_FRACTION = _not_reported(
    ReferenceFactName.FOCUSED_FRACTION,
    "Focused fraction of transmitted power.",
    "No compatible focused fraction of transmitted power is published.",
)
_COMPLEX_FIELD = _not_reported(
    ReferenceFactName.COMPLEX_FOCAL_FIELD,
    "Reusable complex focal-field observation.",
    "The source publishes focal intensities, not a reusable complex field.",
)


_REFERENCE = PublishedReference(
    citation=_CITATION,
    selected_device="one circular-polarization sublens",
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
    ),
    exclusions=(
        "complete six-sublens Hartmann-Shack array",
        "mean measured efficiency of the complete array",
        "paper-selected cell geometry as a production constraint",
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
        MatchedAlignment(BenchmarkSubject.APERTURE, _APERTURE.key),
        IndependentAlignment(
            BenchmarkSubject.ASPECT_LIMIT,
            "The brief supplies limit 8 for both feature and gap; it is not a paper scan.",
        ),
        IndependentAlignment(
            BenchmarkSubject.DIMENSION_STEP,
            "The 10 nm fabrication increment is a MetaCraft process input.",
        ),
        ExcludedAlignment(
            BenchmarkSubject.FABRICATION_ROUTE,
            "The blind brief does not prescribe the paper's fabrication route.",
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
            "The paper period is post-design context, not a production constraint.",
        ),
        ContextRule(
            BenchmarkMeasure.ATOM_HEIGHT,
            _ATOM_HEIGHT.key,
            "The paper height is post-design context, not a production constraint.",
        ),
        ContextRule(
            BenchmarkMeasure.LATERAL_GEOMETRY,
            _LATERAL_GEOMETRY.key,
            "The fixed paper ellipse is context, not a production geometry target.",
        ),
        ContextRule(
            BenchmarkMeasure.PHASE_COVERAGE,
            _PHASE_COVERAGE.key,
            "Continuous paper coverage and finite MetaCraft orientations are unlike values.",
        ),
        ContextRule(
            BenchmarkMeasure.TRANSMITTED_MAGNITUDE,
            _TRANSMITTED_MAGNITUDE.key,
            "The source does not resolve one compatible field-magnitude value.",
        ),
        ContextRule(
            BenchmarkMeasure.TRANSMITTED_POWER,
            _TRANSMITTED_POWER.key,
            "The paper Jones ideal and MetaCraft admitted state powers remain distinct.",
        ),
        ContextRule(
            BenchmarkMeasure.SPATIAL_PHASE_SAMPLING,
            _SPATIAL_PHASE_SAMPLING.key,
            "The paper lattice is context for the independently chosen MetaCraft aperture.",
        ),
        ContextRule(
            BenchmarkMeasure.ORIENTATION_RELATION,
            _ORIENTATION_RELATION.key,
            "Coordinate, handedness, viewing, and angle-sign conventions must stay visible.",
        ),
        ContextRule(
            BenchmarkMeasure.POLARIZATION_CONVERSION,
            _POLARIZATION_CONVERSION.key,
            "The ideal Jones-channel statement is not a unit-power observation.",
        ),
        ContextRule(
            BenchmarkMeasure.FOCUS_EFFICIENCY,
            _FOCUS_EFFICIENCY.key,
            "The paper does not define the focal-spot integration boundary.",
        ),
        NotReportedRule(BenchmarkMeasure.FOCAL_SHIFT, _FOCAL_SHIFT.key),
        NotReportedRule(BenchmarkMeasure.X_HALF_MAXIMUM_WIDTH, _X_WIDTH.key),
        NotReportedRule(BenchmarkMeasure.Y_HALF_MAXIMUM_WIDTH, _Y_WIDTH.key),
        NotReportedRule(BenchmarkMeasure.MEAN_HALF_MAXIMUM_WIDTH, _MEAN_WIDTH.key),
        NotReportedRule(
            BenchmarkMeasure.VERTICAL_CUT_HALF_MAXIMUM_WIDTH,
            _VERTICAL_WIDTH.key,
        ),
        NotReportedRule(
            BenchmarkMeasure.TRANSMITTED_FRACTION,
            _TRANSMITTED_FRACTION.key,
        ),
        NotReportedRule(BenchmarkMeasure.FOCUSED_FRACTION, _FOCUSED_FRACTION.key),
        NotReportedRule(BenchmarkMeasure.COMPLEX_FOCAL_FIELD, _COMPLEX_FIELD.key),
        NotApplicableRule(
            BenchmarkMeasure.LONGITUDINAL_POWER_FRACTION,
            "A low-NA Result does not establish longitudinal component power.",
        ),
    )
)


_YANG_BENCHMARK_CASE = MetalensBenchmarkCase(
    name="yang-2018-low-na-geometric",
    brief=MetalensBrief(
        wording=(
            "Design a low-NA metalens at 1550 nm with NA 0.32 and 30 um focal "
            "length. Use geometric phase, right-circular incidence, and "
            "elliptical silicon pillars on silicon dioxide. Use an aspect "
            "limit of 8 and a 10 nm fabrication increment for one local workstation."
        ),
        aim="metalens",
        objectives=("focus",),
        operating_spectrum=MonochromaticSpectrum(1550),
        numerical_aperture=Decimal("0.32"),
        focal_length_um=Decimal("30"),
        incident_polarization=Polarization(kind="circular", handedness="right"),
        control_strategy=ControlStrategy.GEOMETRIC_PHASE,
        atom=AtomIntent(
            shape="elliptical pillar",
            material=MaterialIntent("silicon", MaterialSource.SOLVER_NATIVE),
        ),
        substrate=MaterialIntent(
            "silicon dioxide",
            MaterialSource.SOLVER_NATIVE,
        ),
        aperture=_APERTURE_VALUE,
        aspect_limit=8,
        solver_preference="lumerical_fdtd",
        dimension_step_nm=10,
        budget="workstation",
        omissions=(
            "atom_height_nm",
            "cell_period_nm",
            "multiwavelength",
            "optimization",
        ),
    ),
    reference=_REFERENCE,
    alignment=_ALIGNMENT,
    contract=_CONTRACT,
)


def yang_benchmark_case() -> MetalensBenchmarkCase:
    """Return the private Yang low-NA geometric benchmark case."""

    return _YANG_BENCHMARK_CASE
