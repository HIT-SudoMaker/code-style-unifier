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
    CircleGeometryRange,
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


_CITATION = "doi:10.1038/ncomms8069"
_FIGURE_1D = SourceLocator(
    citation=_CITATION,
    location="Figure 1d and accompanying HCTA library discussion",
)
_COMPACT_NUMERICAL_LENS = SourceLocator(
    citation=_CITATION,
    location="Figure 2 and numerical-lens discussion",
)
_METHODS_AND_FIGURE_4D = SourceLocator(
    citation=_CITATION,
    location="Methods and Figure 4d",
)
_SUPPLEMENTARY_SECTION_S2 = SourceLocator(
    citation=_CITATION,
    location="Supplementary Information, Section S.2",
)
_FABRICATION_METHODS = SourceLocator(
    citation=_CITATION,
    location="Methods, fabrication of high-contrast transmitarrays",
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
    "1550",
    "nm",
    "Design wavelength of the HCTA platform and compact numerical lens.",
    _FIGURE_1D,
)
_APERTURE = ReportedFact(
    key=ReferenceFactName.APERTURE,
    value="circular aperture, 100 um diameter",
    meaning="Compact factor-of-four numerical counterpart of the lens family.",
    sources=(_COMPACT_NUMERICAL_LENS,),
)
_FOCAL_LENGTH = _reported_quantity(
    ReferenceFactName.FOCAL_LENGTH,
    "25",
    "um",
    "Focusing distance of the compact numerical lens.",
    _COMPACT_NUMERICAL_LENS,
)
_NUMERICAL_APERTURE = DerivedFact(
    key=ReferenceFactName.NUMERICAL_APERTURE,
    value=PublishedQuantity(Decimal("0.89"), "ratio"),
    meaning=(
        "Geometric numerical aperture of the 100 um-diameter, 25 um-focal-"
        "distance compact numerical lens, rounded to the reported precision."
    ),
    sources=(_COMPACT_NUMERICAL_LENS,),
    expression="R / sqrt(R^2 + f^2), rounded to 0.01",
    inputs=(ReferenceFactName.APERTURE, ReferenceFactName.FOCAL_LENGTH),
)
_INCIDENT_POLARIZATION = ReportedFact(
    key=ReferenceFactName.INCIDENT_POLARIZATION,
    value="scaled single-mode-fibre electric and magnetic incident fields",
    meaning=(
        "The paper simulation uses fields obtained from the scaled fibre "
        "geometry rather than a plane wave."
    ),
    sources=(_COMPACT_NUMERICAL_LENS,),
)
_CONTROL_STRATEGY = ReportedFact(
    key=ReferenceFactName.CONTROL_STRATEGY,
    value=ControlStrategy.PROPAGATION_PHASE,
    meaning="Diameter-controlled propagation phase of circular HCTA posts.",
    sources=(_FIGURE_1D,),
)
_ATOM_SHAPE = ReportedFact(
    key=ReferenceFactName.ATOM_SHAPE,
    value="circular pillar",
    meaning="Circular HCTA post cross-section.",
    sources=(_FIGURE_1D,),
)
_ATOM_MATERIAL = ReportedFact(
    key=ReferenceFactName.ATOM_MATERIAL,
    value="hydrogenated amorphous silicon",
    meaning="Hydrogenated amorphous-silicon meta-atom material family.",
    sources=(_FABRICATION_METHODS,),
)
_SUBSTRATE_MATERIAL = ReportedFact(
    key=ReferenceFactName.SUBSTRATE_MATERIAL,
    value="fused silica",
    meaning="Fused-silica substrate material family.",
    sources=(_FIGURE_1D,),
)
_CELL_PERIOD = _reported_quantity(
    ReferenceFactName.CELL_PERIOD,
    "800",
    "nm",
    "Nearest-neighbour period of the published hexagonal lattice.",
    _FIGURE_1D,
)
_ATOM_HEIGHT = _reported_quantity(
    ReferenceFactName.ATOM_HEIGHT,
    "940",
    "nm",
    "Height of the published HCTA posts.",
    _FIGURE_1D,
)
_LATERAL_GEOMETRY = ReportedFact(
    key=ReferenceFactName.LATERAL_GEOMETRY,
    value=CircleGeometryRange(
        minimum_diameter_nm=200,
        maximum_diameter_nm=550,
    ),
    meaning=(
        "Circular-post diameter range of the optically selected Figure 1d "
        "library on the hexagonal lattice."
    ),
    sources=(_FIGURE_1D,),
)
_MINIMUM_FEATURE = _reported_quantity(
    ReferenceFactName.MINIMUM_FEATURE,
    "200",
    "nm",
    "Minimum diameter in the published optical library.",
    _FIGURE_1D,
)
_FEATURE_ASPECT_RATIO = DerivedFact(
    key=ReferenceFactName.FEATURE_ASPECT_RATIO,
    value=PublishedQuantity(Decimal("4.70"), "ratio"),
    meaning="Largest height-to-diameter ratio in the published library.",
    sources=(_FIGURE_1D,),
    expression="940 nm / 200 nm",
    inputs=(ReferenceFactName.ATOM_HEIGHT, ReferenceFactName.MINIMUM_FEATURE),
)
_PHASE_COVERAGE = ReportedFact(
    key=ReferenceFactName.PHASE_COVERAGE,
    value="full transmission phase range",
    meaning="Full transmission-phase coverage over the selected diameter range.",
    sources=(_FIGURE_1D,),
)
_TRANSMITTED_MAGNITUDE = UnresolvedFact(
    key=ReferenceFactName.TRANSMITTED_MAGNITUDE,
    meaning="Reusable complex transmission-amplitude magnitude of the library.",
    reviewed_sources=(_FIGURE_1D,),
    reason=(
        "Figure 1d reports transmission and phase but does not publish a "
        "reusable complex response table with amplitude conventions."
    ),
)
_TRANSMITTED_POWER = ReportedFact(
    key=ReferenceFactName.TRANSMITTED_POWER,
    value="transmission above 92 percent across the selected diameter range",
    meaning="Reported power-transmission envelope of the Figure 1d library.",
    sources=(_FIGURE_1D,),
)
_SPATIAL_PHASE_SAMPLING = ReportedFact(
    key=ReferenceFactName.SPATIAL_PHASE_SAMPLING,
    value=(
        "high-angle loss follows under-sampling of a 2 pi ramp by "
        "wavelength / (period * sin(theta)) cells"
    ),
    meaning="Qualitative high-angle sampling mechanism for the HCTA family.",
    sources=(_SUPPLEMENTARY_SECTION_S2,),
)
_FOCUS_EFFICIENCY_MEANING = MeasureMeaning(
    unit="ratio",
    scope="fabricated 400 um-diameter, d=500 um fibre-illuminated family lens",
    normalization=("power inside radius three measured FWHM / incident fibre power"),
    definition=(
        "Incident-power fraction passing a focal-plane circular aperture whose "
        "radius is three times the measured FWHM spot size."
    ),
)
_FOCUS_EFFICIENCY = _reported_quantity(
    ReferenceFactName.FOCUS_EFFICIENCY,
    "0.82",
    "ratio",
    "Measured maximum focusing efficiency of the fabricated lens family.",
    _METHODS_AND_FIGURE_4D,
    measure_meaning=_FOCUS_EFFICIENCY_MEANING,
)
_TRANSMITTED_FRACTION = ReportedFact(
    key=ReferenceFactName.TRANSMITTED_FRACTION,
    value="total transmitted-power curve for the fibre-illuminated lens family",
    meaning=(
        "Family transmission measured with the focal-plane iris fully open; "
        "no scalar value belongs to the compact plane-wave standard."
    ),
    sources=(_METHODS_AND_FIGURE_4D,),
)


def _not_reported(
    key: ReferenceFactName,
    meaning: str,
    reason: str,
) -> NotReportedFact:
    return NotReportedFact(
        key=key,
        meaning=meaning,
        reviewed_sources=(
            _COMPACT_NUMERICAL_LENS,
            _METHODS_AND_FIGURE_4D,
            _SUPPLEMENTARY_SECTION_S2,
        ),
        reason=reason,
    )


_FOCAL_SHIFT = _not_reported(
    ReferenceFactName.FOCAL_SHIFT,
    "Focal shift of the compact numerical lens.",
    "No reusable focal-shift value is published for the compact lens.",
)
_X_WIDTH = _not_reported(
    ReferenceFactName.X_HALF_MAXIMUM_WIDTH,
    "Independent x half-maximum width of the compact numerical lens.",
    "No independent reusable x width is published for the compact lens.",
)
_Y_WIDTH = _not_reported(
    ReferenceFactName.Y_HALF_MAXIMUM_WIDTH,
    "Independent y half-maximum width of the compact numerical lens.",
    "No independent reusable y width is published for the compact lens.",
)
_MEAN_WIDTH = _not_reported(
    ReferenceFactName.MEAN_HALF_MAXIMUM_WIDTH,
    "Mean x/y half-maximum width of the compact numerical lens.",
    "No mean x/y width is published for the compact lens.",
)
_VERTICAL_WIDTH = _not_reported(
    ReferenceFactName.VERTICAL_CUT_HALF_MAXIMUM_WIDTH,
    "Vertical-cut half-maximum width of the compact numerical lens.",
    "No reusable vertical-cut width is published for the compact lens.",
)
_FOCUSED_FRACTION = _not_reported(
    ReferenceFactName.FOCUSED_FRACTION,
    "Focused fraction of transmitted power for the compact numerical lens.",
    "The paper's efficiency is incident-normalized, not focused/transmitted.",
)
_COMPLEX_FIELD = _not_reported(
    ReferenceFactName.COMPLEX_FOCAL_FIELD,
    "Reusable phase-bearing x/y/z complex focal-field observation.",
    "Figure 2 publishes field and Poynting plots without reusable complex arrays.",
)
_LONGITUDINAL_POWER = _not_reported(
    ReferenceFactName.LONGITUDINAL_POWER_FRACTION,
    "Longitudinal-component power fraction of the compact numerical lens.",
    "No reusable longitudinal-component power fraction is published.",
)


_REFERENCE = PublishedReference(
    citation=_CITATION,
    selected_device="compact HCTA-derived standard",
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
        _FEATURE_ASPECT_RATIO,
        _MINIMUM_FEATURE,
        _PHASE_COVERAGE,
        _TRANSMITTED_MAGNITUDE,
        _TRANSMITTED_POWER,
        _SPATIAL_PHASE_SAMPLING,
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
        "complete single-mode-fibre incident field reproduction",
        "fabricated 400 um lens family as the compact benchmark result",
        "paper-selected cell geometry as a production constraint",
    ),
)


_ALIGNMENT = BenchmarkAlignment(
    (
        MatchedAlignment(BenchmarkSubject.WAVELENGTH, _WAVELENGTH.key),
        MatchedAlignment(BenchmarkSubject.NUMERICAL_APERTURE, _NUMERICAL_APERTURE.key),
        MatchedAlignment(BenchmarkSubject.FOCAL_LENGTH, _FOCAL_LENGTH.key),
        AdaptedAlignment(
            BenchmarkSubject.INCIDENT_POLARIZATION,
            _INCIDENT_POLARIZATION.key,
            (
                "The compact benchmark supplies x-linear plane-wave incidence; "
                "the paper simulation uses scaled single-mode-fibre fields."
            ),
        ),
        MatchedAlignment(BenchmarkSubject.CONTROL_STRATEGY, _CONTROL_STRATEGY.key),
        MatchedAlignment(BenchmarkSubject.ATOM_SHAPE, _ATOM_SHAPE.key),
        AdaptedAlignment(
            BenchmarkSubject.ATOM_MATERIAL,
            _ATOM_MATERIAL.key,
            (
                "The blind brief uses solver-available silicon while the "
                "published HCTA platform remains hydrogenated amorphous silicon."
            ),
        ),
        MatchedAlignment(
            BenchmarkSubject.SUBSTRATE_MATERIAL,
            _SUBSTRATE_MATERIAL.key,
        ),
        WithheldAlignment(BenchmarkSubject.APERTURE, _APERTURE.key),
        IndependentAlignment(
            BenchmarkSubject.ASPECT_LIMIT,
            (
                "The brief supplies limit 8 for both feature and gap as one "
                "independent process input; the paper declares no numeric ceiling."
            ),
        ),
        IndependentAlignment(
            BenchmarkSubject.DIMENSION_STEP,
            "The 10 nm fabrication increment is a MetaCraft process input.",
        ),
        ExcludedAlignment(
            BenchmarkSubject.FABRICATION_ROUTE,
            (
                "The blind brief does not prescribe ZEP520A, the 70 nm alumina "
                "hard mask, or the C4F8/SF6 etch route."
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
            "The paper's hexagonal period is post-design context.",
        ),
        ContextRule(
            BenchmarkMeasure.ATOM_HEIGHT,
            _ATOM_HEIGHT.key,
            "The paper height is post-design context, not a blind constraint.",
        ),
        ContextRule(
            BenchmarkMeasure.LATERAL_GEOMETRY,
            _LATERAL_GEOMETRY.key,
            "The optical diameter range is context, not a production target.",
        ),
        ContextRule(
            BenchmarkMeasure.PHASE_COVERAGE,
            _PHASE_COVERAGE.key,
            "A qualitative full range is not a pointwise phase delta.",
        ),
        ContextRule(
            BenchmarkMeasure.TRANSMITTED_MAGNITUDE,
            _TRANSMITTED_MAGNITUDE.key,
            "No reusable complex-amplitude convention is resolved.",
        ),
        ContextRule(
            BenchmarkMeasure.TRANSMITTED_POWER,
            _TRANSMITTED_POWER.key,
            "The paper envelope and admitted selected-state range are unlike values.",
        ),
        ContextRule(
            BenchmarkMeasure.SPATIAL_PHASE_SAMPLING,
            _SPATIAL_PHASE_SAMPLING.key,
            "The published sampling mechanism is qualitative diagnostic context.",
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
            (
                "Device, fibre illumination, three-FWHM bucket, and "
                "normalization differ from the compact plane-wave standard."
            ),
        ),
        NotReportedRule(BenchmarkMeasure.FOCAL_SHIFT, _FOCAL_SHIFT.key),
        NotReportedRule(BenchmarkMeasure.X_HALF_MAXIMUM_WIDTH, _X_WIDTH.key),
        NotReportedRule(BenchmarkMeasure.Y_HALF_MAXIMUM_WIDTH, _Y_WIDTH.key),
        NotReportedRule(BenchmarkMeasure.MEAN_HALF_MAXIMUM_WIDTH, _MEAN_WIDTH.key),
        NotReportedRule(
            BenchmarkMeasure.VERTICAL_CUT_HALF_MAXIMUM_WIDTH,
            _VERTICAL_WIDTH.key,
        ),
        ContextRule(
            BenchmarkMeasure.TRANSMITTED_FRACTION,
            _TRANSMITTED_FRACTION.key,
            "The reported family curve uses a different device and incident field.",
        ),
        NotReportedRule(BenchmarkMeasure.FOCUSED_FRACTION, _FOCUSED_FRACTION.key),
        NotReportedRule(BenchmarkMeasure.COMPLEX_FOCAL_FIELD, _COMPLEX_FIELD.key),
        NotReportedRule(
            BenchmarkMeasure.LONGITUDINAL_POWER_FRACTION,
            _LONGITUDINAL_POWER.key,
        ),
    )
)


_ARBABI_BENCHMARK_CASE = MetalensBenchmarkCase(
    name="arbabi-2015-high-na-propagation",
    brief=MetalensBrief(
        wording=(
            "Design a high-NA metalens at 1550 nm with NA 0.89 and 25 um "
            "focal length. Use propagation phase, x-linear plane-wave "
            "incidence, and circular silicon pillars "
            "on fused silica. Use an aspect limit of 8 and a 10 nm fabrication "
            "increment for one local workstation."
        ),
        aim="metalens",
        objectives=("focus",),
        operating_spectrum=MonochromaticSpectrum(1550),
        numerical_aperture=Decimal("0.89"),
        focal_length_um=Decimal("25"),
        incident_polarization=Polarization(kind="linear", axis="x"),
        control_strategy=ControlStrategy.PROPAGATION_PHASE,
        atom=AtomIntent(
            shape="circular pillar",
            material=MaterialIntent(
                "silicon",
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
            "complete single-mode-fibre incident field",
            "multiwavelength",
            "optimization",
        ),
    ),
    reference=_REFERENCE,
    alignment=_ALIGNMENT,
    contract=_CONTRACT,
)


def arbabi_benchmark_case() -> MetalensBenchmarkCase:
    """Return the private Arbabi high-NA propagation benchmark case."""

    return _ARBABI_BENCHMARK_CASE
