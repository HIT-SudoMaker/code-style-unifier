from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from ...authority import Document
from .brief import (
    ApertureIntent,
    AtomIntent,
    ContinuousBandSpectrum,
    ControlStrategy,
    MetalensBrief,
    OperatingSpectrum,
    MaterialIntent,
    MonochromaticSpectrum,
    Polarization,
    _aperture_intent_value,
    _atom_intent_value,
    _material_intent_value,
    _operating_spectrum_value,
    require_monochromatic_wavelength,
)
from ..study import Design, Study


TARGET_PHASE_SCHEMA = "metacraft.science.metalens.target_phase"


class MethodApplicability(str, Enum):
    """
    Name the compiler's verdict for one implemented metalens Method.
    """

    SELECTED = "selected"
    INAPPLICABLE = "inapplicable"


@dataclass(frozen=True, slots=True)
class MethodAssessment:
    """
    Retain one compact aim-owned Method applicability judgment.
    """

    method: str
    applicability: MethodApplicability
    grounds: tuple[str, ...]

    def __post_init__(self) -> None:
        """
        Require one named Method, one verdict, and explicit grounds.
        """

        if (
            not self.method.strip()
            or not isinstance(self.applicability, MethodApplicability)
            or not self.grounds
            or any(not ground.strip() for ground in self.grounds)
        ):
            raise ValueError("metalens_method_assessment_invalid")

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the assessment under its closed mapping contract.
        """

        return {
            "applicability": self.applicability.value,
            "grounds": list(self.grounds),
            "method": self.method,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MetalensDesign(Design):
    """
    Resolves scientific intent while leaving local bindings late.
    """

    operating_spectrum: OperatingSpectrum
    numerical_aperture: Decimal
    focal_length_um: Decimal
    incident_polarization: Polarization
    control_strategy: ControlStrategy
    atom: AtomIntent
    substrate: MaterialIntent
    aspect_limit: int
    sampling_ceiling_nm: Decimal
    aperture: ApertureIntent | None
    method_assessments: tuple[MethodAssessment, ...]

    def canonical_value(self) -> dict[str, object]:
        """
        Map canonical Python nouns to established resolved-design keys.
        """

        return {
            "aim": self.aim,
            "capabilities": self.capabilities,
            "aperture": _aperture_intent_value(self.aperture),
            "aspect_limit": self.aspect_limit,
            "atom": _atom_intent_value(self.atom),
            "budget": self.budget,
            "control_strategy": self.control_strategy,
            "focal_length_um": self.focal_length_um,
            "incident_polarization": self.incident_polarization,
            "numerical_aperture": self.numerical_aperture,
            "objectives": self.objectives,
            "method_assessments": [
                assessment.as_mapping() for assessment in self.method_assessments
            ],
            "sampling_ceiling_nm": self.sampling_ceiling_nm,
            "substrate": _material_intent_value(self.substrate),
            "operating_spectrum": _operating_spectrum_value(self.operating_spectrum),
        }


def resolve_metalens_design(brief: MetalensBrief) -> MetalensDesign:
    """
    Resolve user facts before selecting a metalens Relationship.
    """

    if not isinstance(brief, MetalensBrief):
        raise ValueError("metalens_brief_required")
    spectrum = brief.operating_spectrum
    reference_wavelength_nm = (
        spectrum.wavelength_nm
        if isinstance(spectrum, MonochromaticSpectrum)
        else spectrum.lower_wavelength_nm
    )
    return MetalensDesign(
        aim=brief.aim,
        objectives=brief.objectives,
        operating_spectrum=spectrum,
        numerical_aperture=brief.numerical_aperture,
        focal_length_um=brief.focal_length_um,
        incident_polarization=brief.incident_polarization,
        control_strategy=_resolved_control_strategy(brief),
        atom=brief.atom,
        substrate=brief.substrate,
        aspect_limit=brief.aspect_limit,
        sampling_ceiling_nm=(
            Decimal(reference_wavelength_nm) / (Decimal(2) * brief.numerical_aperture)
        ),
        aperture=brief.aperture,
        method_assessments=_assess_methods(brief),
        capabilities=(),
        budget=brief.budget,
    )


def _resolved_control_strategy(brief: MetalensBrief) -> ControlStrategy:
    """
    Resolve only a Method-owned default for a continuous spectrum.
    """

    if brief.control_strategy is not None:
        return brief.control_strategy
    if isinstance(brief.operating_spectrum, ContinuousBandSpectrum):
        return ControlStrategy.GEOMETRIC_PHASE
    raise ValueError("control_strategy_missing")


def _assess_methods(brief: MetalensBrief) -> tuple[MethodAssessment, ...]:
    """
    Record the selected Method and the rejected alternatives.
    """

    if isinstance(brief.operating_spectrum, MonochromaticSpectrum):
        strategy = _resolved_control_strategy(brief)
        scale = "component" if brief.numerical_aperture <= Decimal("0.5") else "vector"
        return (
            MethodAssessment(
                method=f"monochromatic {strategy.value} {scale}",
                applicability=MethodApplicability.SELECTED,
                grounds=(
                    "monochromatic operating spectrum",
                    f"declared {strategy.value}",
                    f"numerical aperture {scale} regime",
                ),
            ),
        )
    positive_grounds = (
        "continuous operating spectrum",
        "circular incident polarization",
        "anisotropic primitive rectangle",
        "single-rectangle material response decided by spectral evidence",
    )
    failures = []
    if brief.incident_polarization.kind != "circular":
        failures.append("continuous_method_requires_circular_input")
    if brief.atom.shape != "rectangular fin":
        failures.append("continuous_method_requires_anisotropic_rectangle")
    if brief.control_strategy not in (None, ControlStrategy.GEOMETRIC_PHASE):
        failures.append("continuous_method_rejects_propagation_only_constraint")
    return (
        MethodAssessment(
            method="transmissive pb dispersion single rectangle",
            applicability=(
                MethodApplicability.SELECTED
                if not failures
                else MethodApplicability.INAPPLICABLE
            ),
            grounds=positive_grounds if not failures else tuple(failures),
        ),
    )


def require_metalens_design(study: Study) -> MetalensDesign:
    """
    Return one resolved metalens design or reject another aim's Study.
    """

    if not isinstance(study.design, MetalensDesign):
        raise RuntimeError("metalens_design_required")
    return study.design


@dataclass(frozen=True, slots=True)
class TargetPhase:
    """
    Records the exact hyperbolic phase law implied by one metalens design.
    """

    wavelength_nm: int
    numerical_aperture: Decimal
    focal_length_um: Decimal
    kind: str = "hyperbolic metalens phase"

    def __post_init__(self) -> None:
        """
        Reject values that cannot describe this phase law.
        """

        if (
            self.wavelength_nm <= 0
            or self.numerical_aperture <= 0
            or self.numerical_aperture >= 1
            or self.focal_length_um <= 0
            or self.kind != "hyperbolic metalens phase"
        ):
            raise ValueError("target_phase_invalid")

    @classmethod
    def from_design(cls, design: MetalensDesign) -> TargetPhase:
        """
        Derive the target phase law without sampling an aperture.
        """

        return cls(
            wavelength_nm=require_monochromatic_wavelength(design.operating_spectrum),
            numerical_aperture=design.numerical_aperture,
            focal_length_um=design.focal_length_um,
        )

    @classmethod
    def from_document(cls, document: Document) -> TargetPhase:
        """
        Restore one exact target phase law.
        """

        if document.schema_identifier != TARGET_PHASE_SCHEMA:
            raise ValueError("target_phase_schema_mismatch")
        values = document.values
        target = cls(
            wavelength_nm=int(values["wavelength_nm"]),
            numerical_aperture=Decimal(str(values["numerical_aperture"])),
            focal_length_um=Decimal(str(values["focal_length_um"])),
            kind=str(values["kind"]),
        )
        if target.document().to_bytes() != document.to_bytes():
            raise ValueError("target_phase_document_mismatch")
        return target

    def document(self) -> Document:
        """
        Encode the target phase law under its owned schema.
        """

        return Document(
            TARGET_PHASE_SCHEMA,
            {
                "focal_length_um": format(self.focal_length_um, "f"),
                "kind": self.kind,
                "numerical_aperture": format(
                    self.numerical_aperture,
                    "f",
                ),
                "wavelength_nm": self.wavelength_nm,
            },
        )
