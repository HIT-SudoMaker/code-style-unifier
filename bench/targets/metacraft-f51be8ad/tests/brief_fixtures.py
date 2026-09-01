from decimal import Decimal

from metacraft.materials import MaterialSource
from metacraft.science.metalens.brief import (
    ApertureExtent,
    ApertureIntent,
    AtomIntent,
    ControlStrategy,
    ContinuousBandSpectrum,
    MaterialIntent,
    MetalensBrief,
    MonochromaticSpectrum,
    Polarization,
)


def propagation_brief() -> MetalensBrief:
    """
    Keep the former compact propagation example as test support.
    """

    return MetalensBrief(
        wording=(
            "Design a compact 400 nm low-na metalens through propagation "
            "phase using circular silicon-nitride posts on silica."
        ),
        aim="metalens",
        objectives=("focus",),
        operating_spectrum=MonochromaticSpectrum(400),
        numerical_aperture=Decimal("0.30"),
        focal_length_um=Decimal("30"),
        incident_polarization=Polarization(kind="linear", axis="x"),
        control_strategy=ControlStrategy.PROPAGATION_PHASE,
        atom=AtomIntent(
            shape="circular pillar",
            material=MaterialIntent(
                "silicon nitride",
                MaterialSource.SOLVER_NATIVE,
            ),
        ),
        substrate=MaterialIntent("silica", MaterialSource.SOLVER_NATIVE),
        aspect_limit=8,
        solver_preference="lumerical_fdtd",
        dimension_step_nm=10,
        budget="compact",
        omissions=("large_na", "multiwavelength", "optimization"),
    )


def geometric_brief() -> MetalensBrief:
    """
    Keep the former compact geometric example as test support.
    """

    return MetalensBrief(
        wording=(
            "Design a compact 400 nm low-na metalens through geometric "
            "phase using rectangular silicon-nitride fins on silica."
        ),
        aim="metalens",
        objectives=("focus",),
        operating_spectrum=MonochromaticSpectrum(400),
        numerical_aperture=Decimal("0.30"),
        focal_length_um=Decimal("30"),
        incident_polarization=Polarization(
            kind="circular",
            handedness="right",
        ),
        control_strategy=ControlStrategy.GEOMETRIC_PHASE,
        atom=AtomIntent(
            shape="rectangular fin",
            material=MaterialIntent(
                "silicon nitride",
                MaterialSource.SOLVER_NATIVE,
            ),
        ),
        substrate=MaterialIntent("silica", MaterialSource.SOLVER_NATIVE),
        aspect_limit=8,
        solver_preference="lumerical_fdtd",
        dimension_step_nm=20,
        budget="compact",
        omissions=("large_na", "multiwavelength", "optimization"),
    )


def continuous_achromatic_brief() -> MetalensBrief:
    """Declare the local Chen-inspired feasibility target as user intent."""

    return MetalensBrief(
        wording=(
            "Design one transmissive continuous-achromatic metalens from "
            "470 to 590 nm with a fixed 49 um focus, NA 0.2, left-circular "
            "incidence, rectangular amorphous titanium-dioxide fins on glass, "
            "and one 20 um aperture diameter."
        ),
        aim="metalens",
        objectives=("focus",),
        operating_spectrum=ContinuousBandSpectrum(470, 590),
        numerical_aperture=Decimal("0.2"),
        focal_length_um=Decimal("49"),
        incident_polarization=Polarization(
            kind="circular",
            handedness="left",
        ),
        control_strategy=None,
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
        aperture=ApertureIntent(
            site_count=51,
            extent=ApertureExtent.DIAMETER,
        ),
        budget="one local workstation",
        omissions=(
            "atom_height_nm",
            "cell_period_nm",
            "control_strategy",
            "spectral sampling",
            "cell geometry",
            "optimization",
        ),
    )


def continuous_achromatic_publication_brief() -> MetalensBrief:
    """Declare the corrected publication target without rewriting the legacy fixture."""

    legacy = continuous_achromatic_brief()
    return MetalensBrief(
        wording=(
            "Design one transmissive continuous-achromatic metalens from "
            "470 to 590 nm with a fixed 49 um focus, NA 0.2, left-circular "
            "incidence, rectangular amorphous titanium-dioxide fins on glass, "
            "and 63 occupied unit-cell sites across the circular aperture diameter."
        ),
        aim=legacy.aim,
        objectives=legacy.objectives,
        operating_spectrum=legacy.operating_spectrum,
        numerical_aperture=legacy.numerical_aperture,
        focal_length_um=legacy.focal_length_um,
        incident_polarization=legacy.incident_polarization,
        control_strategy=legacy.control_strategy,
        atom=legacy.atom,
        substrate=legacy.substrate,
        aspect_limit=legacy.aspect_limit,
        solver_preference=legacy.solver_preference,
        dimension_step_nm=legacy.dimension_step_nm,
        aperture=ApertureIntent(
            site_count=63,
            extent=ApertureExtent.DIAMETER,
        ),
        budget=legacy.budget,
        omissions=legacy.omissions,
    )


def long_focus_propagation_brief() -> MetalensBrief:
    """
    Keep the former long-focus propagation example as test support.
    """

    return _long_focus_brief(
        wording=(
            "Aim: metalens. Objective: focus 355 nm light at 200 um with "
            "NA 0.28. Use propagation phase, x-linear incidence, and "
            "circular silicon-nitride posts on a silica substrate, both "
            "from Lumerical FDTD's solver-native material library. Keep "
            "the aspect ratio at or below 8:1. The full aperture diameter "
            "spans 185 occupied unit-cell sites. Prefer Lumerical FDTD and "
            "budget execution for one local workstation. Omit large-NA "
            "evaluation, multiwavelength operation, and optimization."
        ),
        incident_polarization=Polarization(kind="linear", axis="x"),
        control_strategy=ControlStrategy.PROPAGATION_PHASE,
        atom_shape="circular pillar",
    )


def long_focus_geometric_brief() -> MetalensBrief:
    """
    Keep the former long-focus geometric example as test support.
    """

    return _long_focus_brief(
        wording=(
            "Aim: metalens. Objective: focus 355 nm light at 200 um with "
            "NA 0.28. Use Pancharatnam-Berry (geometric) phase, "
            "right-circular incidence, and rectangular silicon-nitride "
            "fins on a silica substrate, both from Lumerical FDTD's "
            "solver-native material library. Keep the aspect ratio at or "
            "below 8:1. The full aperture diameter spans 185 occupied "
            "unit-cell sites. Prefer Lumerical FDTD. Omit large-NA, "
            "multiwavelength operation, and optimization. Budget execution "
            "for one local workstation."
        ),
        incident_polarization=Polarization(
            kind="circular",
            handedness="right",
        ),
        control_strategy=ControlStrategy.GEOMETRIC_PHASE,
        atom_shape="rectangular fin",
    )


def _long_focus_brief(
    *,
    wording: str,
    incident_polarization: Polarization,
    control_strategy: ControlStrategy,
    atom_shape: str,
) -> MetalensBrief:
    return MetalensBrief(
        wording=wording,
        aim="metalens",
        objectives=("focus",),
        operating_spectrum=MonochromaticSpectrum(355),
        numerical_aperture=Decimal("0.28"),
        focal_length_um=Decimal("200"),
        incident_polarization=incident_polarization,
        control_strategy=control_strategy,
        atom=AtomIntent(
            shape=atom_shape,
            material=MaterialIntent(
                "silicon nitride",
                MaterialSource.SOLVER_NATIVE,
            ),
        ),
        substrate=MaterialIntent("silica", MaterialSource.SOLVER_NATIVE),
        aspect_limit=8,
        solver_preference="lumerical_fdtd",
        dimension_step_nm=(
            10 if control_strategy is ControlStrategy.PROPAGATION_PHASE else 20
        ),
        budget="workstation",
        omissions=("large_na", "multiwavelength", "optimization"),
        aperture=ApertureIntent(
            site_count=185,
            extent=ApertureExtent.DIAMETER,
        ),
    )
