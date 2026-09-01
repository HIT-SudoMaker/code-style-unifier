from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ...field.evidence import FIELD_SCHEMA
from ..relationships import Method, Relationship

from . import aperture as aperture_science
from . import design as design_science
from . import focal_field_comparison as comparison_science
from . import focus as focus_science
from . import geometric_phase as geometric_science
from . import height as height_science
from . import material as material_science
from . import period as period_science
from . import pointwise as pointwise_science
from . import propagation_envelope as envelope_science
from . import propagation_phase as propagation_science
from .brief import ContinuousBandSpectrum, ControlStrategy, MonochromaticSpectrum
from .design import MetalensDesign


def resolve_metalens_relationship(
    design: MetalensDesign,
) -> Relationship:
    """
    Select one current metalens relationship within its supported range.
    """

    if isinstance(design.operating_spectrum, ContinuousBandSpectrum):
        from . import _continuous_achromatic

        return _continuous_achromatic.relationship()
    if not isinstance(design.operating_spectrum, MonochromaticSpectrum):
        raise ValueError("operating_spectrum_unsupported")
    strategy = design.control_strategy
    match strategy:
        case ControlStrategy.PROPAGATION_PHASE:
            return (
                _propagation()
                if design.numerical_aperture <= Decimal("0.5")
                else _pointwise_propagation()
            )
        case ControlStrategy.GEOMETRIC_PHASE:
            return (
                _geometric()
                if design.numerical_aperture <= Decimal("0.5")
                else _pointwise_geometric()
            )
    raise ValueError("control_strategy_unsupported")


def _propagation() -> Relationship:
    return Relationship(
        aim="metalens",
        objectives=("focus",),
        applicability=(
            "declared control strategy: propagation phase; "
            "numerical aperture: at most 0.5"
        ),
        methods=(
            *_metalens_foundation(has_phase_envelope=True),
            Method(
                "observe_periodic_transmission",
                "periodic_transmission",
                ("material_binding", "height_choice"),
                "periodic_transmission_response",
                propagation_science.PERIODIC_TRANSMISSION_SCHEMA,
            ),
            Method(
                "form_cell_library",
                "cell_library",
                ("periodic_transmission",),
                "cell_library",
                propagation_science.CELL_LIBRARY_SCHEMA,
            ),
            Method(
                "form_phase_set",
                "phase_set",
                ("cell_library",),
                None,
                propagation_science.PHASE_SET_SCHEMA,
            ),
            Method(
                "assign_aperture",
                "aperture",
                ("phase_set", "physical_lattice"),
                "deterministic_selection",
                aperture_science.APERTURE_SCHEMA,
            ),
            *_metalens_tail(),
        ),
    )


def _geometric() -> Relationship:
    return Relationship(
        aim="metalens",
        objectives=("focus",),
        applicability=(
            "declared control strategy: geometric phase; "
            "numerical aperture: at most 0.5"
        ),
        methods=(
            *_metalens_foundation(has_phase_envelope=False),
            Method(
                "establish_polarization_convention",
                "polarization_convention",
                ("target_phase",),
                "polarization_convention",
                geometric_science.POLARIZATION_CONVENTION_SCHEMA,
            ),
            Method(
                "observe_periodic_polarization",
                "jones_library",
                (
                    "material_binding",
                    "height_choice",
                    "polarization_convention",
                ),
                "periodic_polarization_response",
                geometric_science.JONES_LIBRARY_SCHEMA,
            ),
            Method(
                "choose_cell",
                "cell_choice",
                ("jones_library",),
                "deterministic_selection",
                geometric_science.CELL_CHOICE_SCHEMA,
            ),
            Method(
                "derive_orientations",
                "orientations",
                ("cell_choice",),
                None,
                geometric_science.ORIENTATION_RELATION_SCHEMA,
            ),
            Method(
                "form_orientation_set",
                "orientation_set",
                ("orientations",),
                None,
                geometric_science.ORIENTATION_SET_SCHEMA,
            ),
            Method(
                "assign_aperture",
                "aperture",
                ("orientation_set", "physical_lattice"),
                "deterministic_selection",
                aperture_science.APERTURE_SCHEMA,
            ),
            *_metalens_tail(),
        ),
    )


def _pointwise_propagation() -> Relationship:
    """
    Declare full-library assignment and vector focal evidence above 0.5.
    """

    return Relationship(
        aim="metalens",
        objectives=("focus",),
        applicability=(
            "declared control strategy: propagation phase; "
            "numerical aperture: above 0.5 and below 1"
        ),
        methods=(
            *_metalens_foundation(has_phase_envelope=True),
            Method(
                "observe_periodic_transmission",
                "periodic_transmission",
                ("material_binding", "height_choice"),
                "periodic_transmission_response",
                propagation_science.PERIODIC_TRANSMISSION_SCHEMA,
            ),
            Method(
                "form_cell_library",
                "cell_library",
                ("periodic_transmission",),
                "cell_library",
                propagation_science.CELL_LIBRARY_SCHEMA,
            ),
            Method(
                "gather_cell_surfaces",
                "cell_surface_table",
                ("cell_library",),
                "periodic_reference_surface_response",
                pointwise_science.CELL_SURFACE_TABLE_SCHEMA,
            ),
            Method(
                "assign_aperture",
                "aperture",
                ("cell_library", "cell_surface_table", "physical_lattice"),
                "deterministic_selection",
                aperture_science.APERTURE_SCHEMA,
            ),
            *_pointwise_tail(("aperture", "cell_surface_table")),
        ),
    )


def _pointwise_geometric() -> Relationship:
    """
    Declare analytic rotation and vector focal evidence above 0.5.
    """

    return Relationship(
        aim="metalens",
        objectives=("focus",),
        applicability=(
            "declared control strategy: geometric phase; "
            "numerical aperture: above 0.5 and below 1"
        ),
        methods=(
            *_metalens_foundation(has_phase_envelope=False),
            Method(
                "establish_polarization_convention",
                "polarization_convention",
                ("target_phase",),
                "polarization_convention",
                geometric_science.POLARIZATION_CONVENTION_SCHEMA,
            ),
            Method(
                "observe_periodic_polarization",
                "jones_library",
                (
                    "material_binding",
                    "height_choice",
                    "polarization_convention",
                ),
                "periodic_polarization_response",
                geometric_science.JONES_LIBRARY_SCHEMA,
            ),
            Method(
                "choose_cell",
                "cell_choice",
                ("jones_library",),
                "deterministic_selection",
                geometric_science.CELL_CHOICE_SCHEMA,
            ),
            Method(
                "derive_orientations",
                "orientations",
                ("cell_choice",),
                None,
                geometric_science.ORIENTATION_RELATION_SCHEMA,
            ),
            Method(
                "gather_geometric_surface_transform",
                "geometric_surface_transform",
                ("cell_choice", "orientations"),
                "periodic_reference_surface_response",
                pointwise_science.GEOMETRIC_SURFACE_TRANSFORM_SCHEMA,
            ),
            Method(
                "assign_aperture",
                "aperture",
                ("orientations", "physical_lattice"),
                "deterministic_selection",
                aperture_science.APERTURE_SCHEMA,
            ),
            *_pointwise_tail(("aperture", "geometric_surface_transform")),
        ),
    )


def _metalens_foundation(
    *,
    has_phase_envelope: bool,
) -> tuple[Method, ...]:
    foundation = [
        Method(
            "derive_target_phase",
            "target_phase",
            (),
            None,
            design_science.TARGET_PHASE_SCHEMA,
        ),
        Method(
            "bind_material",
            "material_binding",
            ("target_phase",),
            "optical_material",
            material_science.MATERIAL_BINDING_SCHEMA,
        ),
        Method(
            "derive_period_domain",
            "period_domain",
            ("material_binding",),
            "fabrication_constraint",
            period_science.PERIOD_DOMAIN_SCHEMA,
        ),
        Method(
            "resolve_period_choice",
            "period_choice",
            ("period_domain",),
            "deterministic_selection",
            period_science.PERIOD_CHOICE_SCHEMA,
        ),
        Method(
            "derive_height_domain",
            "height_domain",
            ("material_binding", "period_choice"),
            "fabrication_constraint",
            height_science.HEIGHT_DOMAIN_SCHEMA,
        ),
    ]
    if has_phase_envelope:
        foundation.append(
            Method(
                "estimate_phase_envelope",
                "phase_envelope",
                ("material_binding", "height_domain"),
                None,
                envelope_science.PHASE_ENVELOPE_SCHEMA,
            )
        )
    foundation.append(
        Method(
            "resolve_height_choice",
            "height_choice",
            (("phase_envelope",) if has_phase_envelope else ("height_domain",)),
            "deterministic_selection",
            height_science.HEIGHT_CHOICE_SCHEMA,
        )
    )
    foundation.append(
        Method(
            "resolve_physical_lattice",
            "physical_lattice",
            ("period_choice", "height_choice"),
            None,
            aperture_science.PHYSICAL_LATTICE_SCHEMA,
        )
    )
    return tuple(foundation)


def _metalens_tail() -> tuple[Method, ...]:
    """
    Declare the field-to-focus close shared by every metalens strategy.
    """

    return (
        Method(
            "form_field",
            "field",
            ("aperture",),
            None,
            FIELD_SCHEMA,
        ),
        Method(
            "propagate_field",
            "focal_region",
            ("field",),
            "angular_spectrum_propagation",
            focus_science.FOCAL_REGION_SCHEMA,
        ),
        Method(
            "evaluate_focus",
            "focus",
            ("focal_region",),
            "focus_evaluation",
            focus_science.FOCUS_SCHEMA,
        ),
    )


def _pointwise_tail(
    field_requirements: tuple[str, ...],
) -> tuple[Method, ...]:
    """
    Close one sampled vector field against one ideal Debye reference.
    """

    return (
        Method(
            "form_field",
            "field",
            field_requirements,
            None,
            FIELD_SCHEMA,
        ),
        Method(
            "propagate_field",
            "focal_region",
            ("field",),
            "vector_angular_spectrum_propagation",
            focus_science.FOCAL_REGION_SCHEMA,
        ),
        Method(
            "form_aplanatic_reference",
            "aplanatic_reference",
            ("target_phase", "focal_region"),
            "aplanatic_reference_formation",
            FIELD_SCHEMA,
        ),
        Method(
            "compare_focal_field",
            "focal_comparison",
            ("focal_region", "aplanatic_reference"),
            None,
            comparison_science.FOCAL_FIELD_COMPARISON_SCHEMA,
        ),
        Method(
            "evaluate_focus",
            "focus",
            ("focal_region", "focal_comparison"),
            "focus_evaluation",
            focus_science.FOCUS_SCHEMA,
        ),
    )
