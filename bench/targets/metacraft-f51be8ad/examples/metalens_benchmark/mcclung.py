from __future__ import annotations

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
    AdaptedAlignment,
    BenchmarkAlignment,
    BenchmarkMeasure,
    BenchmarkSubject,
    ComparisonContract,
    ContextRule,
    DerivedFact,
    ExcludedAlignment,
    IndependentAlignment,
    MatchedAlignment,
    MeasureMeaning,
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


_DESIGN = SourceLocator(
    citation="doi:10.1002/adom.202301865",
    location="Results and discussion, Figure 2 and accompanying text",
)
_EFFICIENCY = SourceLocator(
    citation="doi:10.1002/adom.202301865",
    location="Results and discussion, Figure 4 and efficiency definition",
)
_METHODS = SourceLocator(
    citation="doi:10.1002/adom.202301865",
    location="Experimental section, Metalens fabrication",
)


def _reported_quantity(
    key: ReferenceFactName,
    value: str,
    unit: str,
    meaning: str,
    source: SourceLocator = _DESIGN,
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
    "550",
    "nm",
    "Design wavelength of the selected visible metalens.",
)
_NUMERICAL_APERTURE = _reported_quantity(
    ReferenceFactName.NUMERICAL_APERTURE,
    "0.2",
    "ratio",
    "Numerical aperture of the selected visible metalens.",
)
_APERTURE = ReportedFact(
    key=ReferenceFactName.APERTURE,
    value="circular aperture, 6 mm diameter",
    meaning="Circular aperture of the selected visible metalens.",
    sources=(_DESIGN,),
)
_FOCAL_LENGTH = ReportedFact(
    key=ReferenceFactName.FOCAL_LENGTH,
    value=PublishedQuantity(Decimal("14.7"), "mm"),
    meaning="Reported focal length of the selected visible metalens.",
    sources=(_DESIGN,),
)
_CONTROL_STRATEGY = ReportedFact(
    key=ReferenceFactName.CONTROL_STRATEGY,
    value=ControlStrategy.PROPAGATION_PHASE,
    meaning="Width-tuned propagation-phase design represented by Figure 2.",
    sources=(_DESIGN,),
)
_ATOM_SHAPE = ReportedFact(
    key=ReferenceFactName.ATOM_SHAPE,
    value="hexagonal post",
    meaning="Hexagonal nano-post cross-section.",
    sources=(_DESIGN,),
)
_ATOM_MATERIAL = ReportedFact(
    key=ReferenceFactName.ATOM_MATERIAL,
    value="silicon nitride",
    meaning="Meta-atom material family.",
    sources=(_DESIGN, _METHODS),
)
_SUBSTRATE_MATERIAL = ReportedFact(
    key=ReferenceFactName.SUBSTRATE_MATERIAL,
    value="fused silica",
    meaning="Substrate material family.",
    sources=(_DESIGN, _METHODS),
)
_ATOM_HEIGHT = _reported_quantity(
    ReferenceFactName.ATOM_HEIGHT,
    "650",
    "nm",
    "Nominal nano-post height of the selected design.",
)
_MINIMUM_FEATURE = ReportedFact(
    key=ReferenceFactName.MINIMUM_FEATURE,
    value=PublishedQuantity(Decimal("100"), "nm"),
    meaning="Minimum nano-post width admitted by the selected design.",
    sources=(_DESIGN,),
)
_FEATURE_ASPECT_RATIO = DerivedFact(
    key=ReferenceFactName.FEATURE_ASPECT_RATIO,
    value=PublishedQuantity(Decimal("6.5"), "ratio"),
    meaning="Maximum nominal height-to-width ratio of the selected design.",
    sources=(_DESIGN,),
    expression="650 nm / 100 nm",
    inputs=(
        ReferenceFactName.ATOM_HEIGHT,
        ReferenceFactName.MINIMUM_FEATURE,
    ),
)
_CELL_PERIOD = _reported_quantity(
    key=ReferenceFactName.CELL_PERIOD,
    value="430",
    unit="nm",
    meaning="Triangular-lattice constant of the selected design.",
)
_LATERAL_GEOMETRY = ReportedFact(
    key=ReferenceFactName.LATERAL_GEOMETRY,
    value=(
        "hexagonal posts, 100-310 nm width, at least 120 nm gap, "
        "on a triangular lattice"
    ),
    meaning="Reported lateral design family and fabrication bounds.",
    sources=(_DESIGN,),
)
_PHASE_COVERAGE = UnresolvedFact(
    key=ReferenceFactName.PHASE_COVERAGE,
    meaning="Exact phase span of the selected width-tuned library.",
    reviewed_sources=(_DESIGN,),
    reason="Figure 2 publishes a phase curve but the text states no exact span.",
)
_TRANSMITTED_MAGNITUDE = UnresolvedFact(
    key=ReferenceFactName.TRANSMITTED_MAGNITUDE,
    meaning="Complex-field transmission magnitude of the selected library.",
    reviewed_sources=(_DESIGN,),
    reason="The published transmittance curve is not field magnitude.",
)
_TRANSMITTED_POWER = UnresolvedFact(
    key=ReferenceFactName.TRANSMITTED_POWER,
    meaning="Power transmission of the selected width-tuned library.",
    reviewed_sources=(_DESIGN,),
    reason="The published curve does not state an exact power normalization.",
)
_FOCUS_EFFICIENCY_MEANING = MeasureMeaning(
    unit="ratio",
    scope="simulated 6 mm-diameter, NA 0.2 metalens design at 550 nm",
    normalization="fraction of normally incident power focused by the metalens",
    definition=(
        "Grating-averaging estimate reported as focusing efficiency; the "
        "numerical focal bucket is not resolved in the article."
    ),
)
_FOCUS_EFFICIENCY = _reported_quantity(
    ReferenceFactName.FOCUS_EFFICIENCY,
    "0.902",
    "ratio",
    "Simulated focusing efficiency of the selected design.",
    _DESIGN,
    measure_meaning=_FOCUS_EFFICIENCY_MEANING,
)


def _not_reported(
    key: ReferenceFactName,
    meaning: str,
    reason: str,
) -> NotReportedFact:
    return NotReportedFact(
        key=key,
        meaning=meaning,
        reviewed_sources=(_DESIGN, _EFFICIENCY),
        reason=reason,
    )


_FOCAL_SHIFT = _not_reported(
    ReferenceFactName.FOCAL_SHIFT,
    "Focal shift of the selected visible metalens.",
    "No focal-shift value is published for the selected design.",
)
_X_WIDTH = _not_reported(
    ReferenceFactName.X_HALF_MAXIMUM_WIDTH,
    "Independent x half-maximum width.",
    "No independent numeric x width is published for the selected design.",
)
_Y_WIDTH = _not_reported(
    ReferenceFactName.Y_HALF_MAXIMUM_WIDTH,
    "Independent y half-maximum width.",
    "No independent numeric y width is published for the selected design.",
)
_MEAN_WIDTH = _not_reported(
    ReferenceFactName.MEAN_HALF_MAXIMUM_WIDTH,
    "Mean x/y half-maximum width.",
    "No mean numeric x/y width is published for the selected design.",
)
_VERTICAL_WIDTH = _not_reported(
    ReferenceFactName.VERTICAL_CUT_HALF_MAXIMUM_WIDTH,
    "Vertical-cut half-maximum width.",
    "No numeric vertical-cut width is published for the selected design.",
)
_TRANSMITTED_FRACTION = _not_reported(
    ReferenceFactName.TRANSMITTED_FRACTION,
    "Whole-device transmitted fraction.",
    "No compatible whole-device transmitted fraction is published.",
)
_FOCUSED_FRACTION = _not_reported(
    ReferenceFactName.FOCUSED_FRACTION,
    "Focused fraction of transmitted power.",
    "No compatible focused fraction is published.",
)
_COMPLEX_FIELD = _not_reported(
    ReferenceFactName.COMPLEX_FOCAL_FIELD,
    "Reusable complex focal-field observation.",
    "The article publishes no reusable complex focal-field array.",
)


_REFERENCE = PublishedReference(
    citation="doi:10.1002/adom.202301865",
    selected_device="6 mm NA 0.2 silicon-nitride metalens design",
    facts=(
        _WAVELENGTH,
        _NUMERICAL_APERTURE,
        _APERTURE,
        _FOCAL_LENGTH,
        _CONTROL_STRATEGY,
        _ATOM_SHAPE,
        _ATOM_MATERIAL,
        _SUBSTRATE_MATERIAL,
        _ATOM_HEIGHT,
        _FEATURE_ASPECT_RATIO,
        _MINIMUM_FEATURE,
        _CELL_PERIOD,
        _LATERAL_GEOMETRY,
        _PHASE_COVERAGE,
        _TRANSMITTED_MAGNITUDE,
        _TRANSMITTED_POWER,
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
        "nanoimprint process reproduction",
        "electron-beam-lithography control reproduction",
        "measured efficiency at wavelengths other than the 550 nm design point",
    ),
)


_ALIGNMENT = BenchmarkAlignment(
    (
        MatchedAlignment(BenchmarkSubject.WAVELENGTH, _WAVELENGTH.key),
        MatchedAlignment(
            BenchmarkSubject.NUMERICAL_APERTURE,
            _NUMERICAL_APERTURE.key,
        ),
        AdaptedAlignment(
            BenchmarkSubject.FOCAL_LENGTH,
            _FOCAL_LENGTH.key,
            "The workstation brief uses 200 um rather than the paper's 14.7 mm.",
        ),
        IndependentAlignment(
            BenchmarkSubject.INCIDENT_POLARIZATION,
            "The blind brief supplies x-linear incidence as a test condition.",
        ),
        MatchedAlignment(
            BenchmarkSubject.CONTROL_STRATEGY,
            _CONTROL_STRATEGY.key,
        ),
        AdaptedAlignment(
            BenchmarkSubject.ATOM_SHAPE,
            _ATOM_SHAPE.key,
            "The brief uses circular pillars rather than the paper's hexagonal posts.",
        ),
        MatchedAlignment(BenchmarkSubject.ATOM_MATERIAL, _ATOM_MATERIAL.key),
        MatchedAlignment(
            BenchmarkSubject.SUBSTRATE_MATERIAL,
            _SUBSTRATE_MATERIAL.key,
        ),
        WithheldAlignment(BenchmarkSubject.APERTURE, _APERTURE.key),
        IndependentAlignment(
            BenchmarkSubject.ASPECT_LIMIT,
            (
                "The brief supplies limit 8 as a process input; the paper "
                "reports dimensions rather than the same process rule."
            ),
        ),
        IndependentAlignment(
            BenchmarkSubject.DIMENSION_STEP,
            "The 10 nm fabrication increment is a MetaCraft process input.",
        ),
        ExcludedAlignment(
            BenchmarkSubject.FABRICATION_ROUTE,
            "Reproducing either NIL or EBL fabrication is outside the brief.",
        ),
        WithheldAlignment(BenchmarkSubject.CELL_PERIOD, _CELL_PERIOD.key),
        WithheldAlignment(BenchmarkSubject.ATOM_HEIGHT, _ATOM_HEIGHT.key),
        WithheldAlignment(
            BenchmarkSubject.LATERAL_GEOMETRY,
            _LATERAL_GEOMETRY.key,
        ),
    )
)


_CONTRACT = ComparisonContract(
    (
        ContextRule(
            BenchmarkMeasure.CELL_PERIOD,
            _CELL_PERIOD.key,
            "The reported paper period is post-design context, not a constraint.",
        ),
        ContextRule(
            BenchmarkMeasure.ATOM_HEIGHT,
            _ATOM_HEIGHT.key,
            "The paper height is post-design context, not a constraint.",
        ),
        ContextRule(
            BenchmarkMeasure.LATERAL_GEOMETRY,
            _LATERAL_GEOMETRY.key,
            "The paper's hexagonal triangular-lattice family is context only.",
        ),
        ContextRule(
            BenchmarkMeasure.PHASE_COVERAGE,
            _PHASE_COVERAGE.key,
            "The exact published phase span remains unresolved.",
        ),
        ContextRule(
            BenchmarkMeasure.TRANSMITTED_MAGNITUDE,
            _TRANSMITTED_MAGNITUDE.key,
            "Transmission semantics remain unresolved.",
        ),
        ContextRule(
            BenchmarkMeasure.TRANSMITTED_POWER,
            _TRANSMITTED_POWER.key,
            "Power normalization remains unresolved.",
        ),
        NotApplicableRule(
            BenchmarkMeasure.SPATIAL_PHASE_SAMPLING,
            "The selected source carries no reusable sampling measure.",
        ),
        NotApplicableRule(
            BenchmarkMeasure.ORIENTATION_RELATION,
            "Propagation phase has no orientation relation.",
        ),
        NotApplicableRule(
            BenchmarkMeasure.POLARIZATION_CONVERSION,
            "The selected propagation-phase comparison has no PB conversion.",
        ),
        ContextRule(
            BenchmarkMeasure.FOCUS_EFFICIENCY,
            _FOCUS_EFFICIENCY.key,
            "The paper's simulation bucket is not a MetaCraft acceptance threshold.",
        ),
        NotReportedRule(BenchmarkMeasure.FOCAL_SHIFT, _FOCAL_SHIFT.key),
        NotReportedRule(BenchmarkMeasure.X_HALF_MAXIMUM_WIDTH, _X_WIDTH.key),
        NotReportedRule(BenchmarkMeasure.Y_HALF_MAXIMUM_WIDTH, _Y_WIDTH.key),
        NotReportedRule(
            BenchmarkMeasure.MEAN_HALF_MAXIMUM_WIDTH,
            _MEAN_WIDTH.key,
        ),
        NotReportedRule(
            BenchmarkMeasure.VERTICAL_CUT_HALF_MAXIMUM_WIDTH,
            _VERTICAL_WIDTH.key,
        ),
        NotReportedRule(
            BenchmarkMeasure.TRANSMITTED_FRACTION,
            _TRANSMITTED_FRACTION.key,
        ),
        NotReportedRule(
            BenchmarkMeasure.FOCUSED_FRACTION,
            _FOCUSED_FRACTION.key,
        ),
        NotReportedRule(
            BenchmarkMeasure.COMPLEX_FOCAL_FIELD,
            _COMPLEX_FIELD.key,
        ),
        NotApplicableRule(
            BenchmarkMeasure.LONGITUDINAL_POWER_FRACTION,
            "A low-NA Result does not establish longitudinal component power.",
        ),
    )
)


_MCCLUNG_BENCHMARK_CASE = MetalensBenchmarkCase(
    name="mcclung-2024-low-na-propagation",
    brief=MetalensBrief(
        wording=(
            "Design a low-NA metalens at 550 nm with NA 0.20 and 200 um "
            "focal length. Use propagation phase, x-linear incidence, and "
            "circular silicon-nitride pillars on fused silica. Use an aspect "
            "limit of 8 and a 10 nm fabrication increment for one local "
            "workstation."
        ),
        aim="metalens",
        objectives=("focus",),
        operating_spectrum=MonochromaticSpectrum(550),
        numerical_aperture=Decimal("0.20"),
        focal_length_um=Decimal("200"),
        incident_polarization=Polarization(kind="linear", axis="x"),
        control_strategy=ControlStrategy.PROPAGATION_PHASE,
        atom=AtomIntent(
            shape="circular pillar",
            material=MaterialIntent(
                "silicon nitride",
                MaterialSource.SOLVER_NATIVE,
            ),
        ),
        substrate=MaterialIntent(
            "fused silica",
            MaterialSource.SOLVER_NATIVE,
        ),
        aspect_limit=8,
        solver_preference="lumerical_fdtd",
        dimension_step_nm=10,
        budget="workstation",
        omissions=(
            "aperture",
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


def mcclung_benchmark_case() -> MetalensBenchmarkCase:
    """Return the one private McClung benchmark contract."""

    return _MCCLUNG_BENCHMARK_CASE
