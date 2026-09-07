from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
import hashlib

from ...authority.protocol import Reference
from ...authority.reference import reference_for
from ...canonical import canonicalize

from ..brief import Brief
from ..compiler import MissingBriefFacts, assemble_study, prove_relationship
from ..consultation import EvidenceRequired
from ..study import (
    Advice,
    Binding,
    Capability,
    Claim,
    Evidence,
    Finding,
    FindingKind,
    Study,
)

from .brief import (
    ApertureExtent,
    ApertureFootprint,
    ApertureIntent,
    AtomIntent,
    ContinuousBandSpectrum,
    ControlStrategy,
    MaterialIntent,
    MetalensBrief,
    MonochromaticSpectrum,
    Polarization,
)
from .design import MethodApplicability, resolve_metalens_design
from .height_advice import HeightAdvice
from .period_advice import PeriodAdvice
from .relationship import resolve_metalens_relationship


DOMAIN_OWNED_FINDING_CLAIMS = frozenset(
    {"period_choice", "height_domain", "height_choice"}
)


def compile_metalens(
    brief: Brief,
    *,
    advice: tuple[Advice, ...] = (),
    evidence: tuple[Evidence, ...] = (),
    capabilities: tuple[Capability, ...] = (),
    bindings: tuple[Binding, ...] = (),
    reported_findings: tuple[Finding, ...] = (),
) -> Study:
    """
    Interpret one metalens brief and let generic science form its Study.
    """

    if not isinstance(brief, MetalensBrief):
        raise MissingBriefFacts(
            "operating_spectrum",
            "numerical_aperture",
            "focal_length_um",
            "incident_polarization",
            "control_strategy",
            "atom",
            "substrate",
            "aspect_limit",
        )
    _require_brief_facts(brief)
    design = resolve_metalens_design(brief)
    relationship = resolve_metalens_relationship(design)
    route, proof = prove_relationship(relationship, brief.objectives)
    period_advice = _resolve_period_advice(advice)
    height_advice = _resolve_height_advice(advice)
    if brief.cell_period_nm is not None and period_advice is not None:
        raise ValueError("period_advice_forbidden")

    period_reference = _derive_advice_reference(period_advice)
    height_reference = _derive_advice_reference(height_advice)
    consultations = {
        claim: reference
        for claim, reference in (
            ("period_choice", period_reference),
            ("height_choice", height_reference),
        )
        if reference is not None
    }

    def resolve_advice_finding(
        claim: Claim,
        admitted: Mapping[str, Evidence],
    ) -> Finding | None:
        """
        Interpret admitted evidence against one metalens claim.
        """

        if claim.name == "achromatic_target":
            assessment = design.method_assessments[0]
            if assessment.applicability is MethodApplicability.INAPPLICABLE:
                return Finding(
                    claim="achromatic_target",
                    kind=FindingKind.REFUSAL,
                    needs=assessment.grounds,
                )
        return _resolve_advice_finding(
            brief,
            period_advice,
            height_advice,
            admitted,
            claim=claim,
        )

    return assemble_study(
        brief,
        advice=advice,
        design=design,
        route=route,
        proof=proof,
        evidence=evidence,
        capabilities=capabilities,
        bindings=bindings,
        consultations=consultations,
        resolve_advice_finding=resolve_advice_finding,
        is_reported_finding_valid=_is_reported_finding_valid,
        reported_findings=reported_findings,
    )


def restore_metalens_inputs(
    study: Study,
) -> tuple[tuple[Advice, ...], tuple[Finding, ...]]:
    """
    Narrow one restored Study to the inputs metalens recompilation accepts.
    """

    if study.route.aim != "metalens":
        raise ValueError("metalens_study_required")
    restored: list[Advice] = []
    for item in study.advice:
        value = canonicalize(item.canonical_value())
        if not isinstance(value, Mapping):
            raise ValueError("metalens_advice_invalid")
        try:
            if "envelope_reference" in value:
                restored.append(HeightAdvice.from_canonical_value(value))
            elif "domain_reference" in value:
                restored.append(PeriodAdvice.from_canonical_value(value))
            else:
                raise ValueError("metalens_advice_invalid")
        except ValueError as error:
            raise ValueError("metalens_advice_invalid") from error
    restored_advice = tuple(restored)
    period_advice = _resolve_period_advice(restored_advice)
    height_advice = _resolve_height_advice(restored_advice)
    if not isinstance(study.brief, MetalensBrief):
        raise ValueError("metalens_brief_required")
    reported_findings: list[Finding] = []
    for finding in study.findings:
        if _is_compiler_owned_finding(
            finding,
            study.brief,
            period_advice,
            height_advice,
        ):
            continue
        if finding.claim in DOMAIN_OWNED_FINDING_CLAIMS:
            if finding.kind in (FindingKind.ADVICE, FindingKind.REFUSAL):
                reported_findings.append(finding)
        elif _is_reported_finding_valid(finding):
            reported_findings.append(finding)
    return restored_advice, tuple(reported_findings)


def _require_brief_facts(brief: MetalensBrief) -> None:
    finding = metalens_brief_finding(brief)
    if finding is not None:
        raise ValueError(finding)


def metalens_brief_finding(brief: MetalensBrief) -> str | None:
    """
    Return the first invalid supplied fact before scientific compilation.

    Missing required facts retain their typed diagnostic so the application
    boundary can distinguish absence from an implementation failure.
    """

    if not isinstance(
        brief.operating_spectrum,
        (MonochromaticSpectrum, ContinuousBandSpectrum),
    ):
        return "operating_spectrum_invalid"
    if (
        not isinstance(brief.focal_length_um, Decimal)
        or not brief.focal_length_um.is_finite()
        or brief.focal_length_um <= 0
    ):
        return "focal_length_invalid"
    if (
        not isinstance(brief.numerical_aperture, Decimal)
        or not brief.numerical_aperture.is_finite()
        or brief.numerical_aperture <= 0
        or brief.numerical_aperture > Decimal(1)
    ):
        return "numerical_aperture_invalid"
    has_monochromatic_spectrum = isinstance(
        brief.operating_spectrum,
        MonochromaticSpectrum,
    )
    if brief.control_strategy is None and has_monochromatic_spectrum:
        raise MissingBriefFacts("control_strategy")
    if brief.control_strategy is not None and not isinstance(
        brief.control_strategy,
        ControlStrategy,
    ):
        return "control_strategy_invalid"
    if not isinstance(brief.atom, AtomIntent):
        return "atom_intent_invalid"
    if not isinstance(brief.atom.material, MaterialIntent):
        return "material_intent_invalid"
    if not isinstance(brief.substrate, MaterialIntent):
        return "material_intent_invalid"
    if not isinstance(brief.atom.shape, str) or not brief.atom.shape.strip():
        return "atom_geometry_invalid"
    if not isinstance(brief.incident_polarization, Polarization):
        return "incident_polarization_invalid"
    polarization = brief.incident_polarization
    is_linear = (
        polarization.kind == "linear"
        and polarization.axis in ("x", "y")
        and polarization.handedness is None
    )
    is_circular = (
        polarization.kind == "circular"
        and polarization.axis is None
        and polarization.handedness in ("left", "right")
    )
    if not (is_linear or is_circular):
        return "incident_polarization_invalid"
    if type(brief.aspect_limit) is not int or brief.aspect_limit <= 0:
        return "aspect_limit_invalid"
    if brief.solver_preference is not None and (
        not isinstance(brief.solver_preference, str)
        or not brief.solver_preference.strip()
    ):
        return "solver_preference_invalid"
    if brief.dimension_step_nm is None:
        raise MissingBriefFacts("dimension_step_nm")
    if (
        isinstance(brief.dimension_step_nm, bool)
        or not isinstance(brief.dimension_step_nm, int)
        or brief.dimension_step_nm <= 0
    ):
        return "dimension_step_invalid"
    if brief.cell_period_nm is not None and (
        isinstance(brief.cell_period_nm, bool)
        or not isinstance(brief.cell_period_nm, int)
        or brief.cell_period_nm <= 0
    ):
        return "cell_period_invalid"
    if brief.atom_height_nm is not None and (
        isinstance(brief.atom_height_nm, bool)
        or not isinstance(brief.atom_height_nm, int)
        or brief.atom_height_nm <= 0
    ):
        return "atom_height_invalid"
    if (
        brief.control_strategy is ControlStrategy.PROPAGATION_PHASE
        and brief.atom.shape not in {"circular pillar", "square pillar"}
    ):
        return "propagation_atom_shape_unsupported"
    if (
        brief.control_strategy is ControlStrategy.GEOMETRIC_PHASE
        and brief.atom.shape not in {"rectangular fin", "elliptical pillar"}
    ):
        return "geometric_atom_shape_unsupported"
    aperture = brief.aperture
    if aperture is not None and not isinstance(aperture, ApertureIntent):
        return "aperture_intent_invalid"
    if aperture is not None and (
        type(aperture.site_count) is not int or aperture.site_count <= 0
    ):
        return "aperture_intent_invalid"
    if aperture is not None and not isinstance(aperture.extent, ApertureExtent):
        return "aperture_extent_invalid"
    if aperture is not None and not isinstance(aperture.footprint, ApertureFootprint):
        return "aperture_footprint_invalid"
    if (
        aperture is not None
        and aperture.footprint is ApertureFootprint.SQUARE
        and (
            aperture.extent is not ApertureExtent.DIAMETER
            or aperture.site_count % 2 == 0
        )
    ):
        return "square_aperture_intent_invalid"
    if brief.control_strategy is ControlStrategy.GEOMETRIC_PHASE and not is_circular:
        return "geometric_polarization_invalid"
    return None


def _resolve_advice_finding(
    brief: MetalensBrief,
    period_advice: PeriodAdvice | None,
    height_advice: HeightAdvice | None,
    evidence: Mapping[str, Evidence],
    *,
    claim: Claim,
) -> Finding | None:
    if claim.name == "period_choice" and brief.cell_period_nm is None:
        return _resolve_period_advice_finding(
            brief,
            period_advice,
            evidence,
        )
    if claim.name == "height_choice" and brief.atom_height_nm is None:
        if height_advice is None:
            return Finding(
                claim="height_choice",
                kind=FindingKind.ADVICE,
                needs=("height",),
            )
        _validate_height_advice_grounds(
            brief,
            height_advice,
            evidence,
        )
        if isinstance(height_advice.conclusion, EvidenceRequired):
            return Finding(
                claim="height_choice",
                kind=FindingKind.ADVICE,
                needs=("height_evidence_required",),
                record_references=(reference_for(height_advice.document().to_bytes()),),
            )
    return None


def _validate_height_advice_grounds(
    brief: MetalensBrief,
    advice: HeightAdvice,
    evidence: Mapping[str, Evidence],
) -> None:
    if advice.brief_identity != _identity(brief.canonical_bytes()):
        raise ValueError("height_advice_brief_mismatch")
    domain = evidence.get("height_domain")
    if domain is None or advice.domain_reference != domain.reference:
        raise ValueError("height_advice_stale")
    if brief.control_strategy is ControlStrategy.PROPAGATION_PHASE:
        envelope = evidence.get("phase_envelope")
        if envelope is None or advice.envelope_reference != envelope.reference:
            raise ValueError("height_advice_envelope_stale")
    elif advice.envelope_reference is not None:
        raise ValueError("geometric_phase_envelope_forbidden")


def _resolve_period_advice_finding(
    brief: MetalensBrief,
    record: PeriodAdvice | None,
    evidence: Mapping[str, Evidence],
) -> Finding | None:
    """
    Validate one period proposal without changing its value.
    """

    if record is None:
        return Finding(
            claim="period_choice",
            kind=FindingKind.ADVICE,
            needs=("period",),
        )
    if record.brief_identity != _identity(brief.canonical_bytes()):
        raise ValueError("period_advice_brief_mismatch")
    domain = evidence.get("period_domain")
    if domain is None or record.domain_reference != domain.reference:
        raise ValueError("period_advice_domain_mismatch")
    if isinstance(record.conclusion, EvidenceRequired):
        return Finding(
            claim="period_choice",
            kind=FindingKind.ADVICE,
            needs=("period_evidence_required",),
            record_references=(reference_for(record.document().to_bytes()),),
        )
    return None


def _resolve_period_advice(
    advice: tuple[Advice, ...],
) -> PeriodAdvice | None:
    """
    Return the sole period consultation without widening generic science.
    """

    records = tuple(item for item in advice if isinstance(item, PeriodAdvice))
    if len(records) > 1:
        raise ValueError("period_advice_duplicate")
    return None if not records else records[0]


def _resolve_height_advice(
    advice: tuple[Advice, ...],
) -> HeightAdvice | None:
    """
    Return the sole height consultation without widening generic science.
    """

    records = tuple(item for item in advice if isinstance(item, HeightAdvice))
    if len(records) > 1:
        raise ValueError("height_advice_duplicate")
    return None if not records else records[0]


def _derive_advice_reference(
    advice: PeriodAdvice | HeightAdvice | None,
) -> Reference | None:
    """
    Derive immutable consultation identity without claiming admission.
    """

    if advice is None:
        return None
    return reference_for(advice.document().to_bytes())


def _is_reported_finding_valid(finding: Finding) -> bool:
    if finding.claim in DOMAIN_OWNED_FINDING_CLAIMS:
        return False
    return (
        finding.kind is FindingKind.REFUSAL
        or (
            finding.kind is FindingKind.UNAVAILABLE
            and finding.claim
            in {
                "material_binding",
                "spectral_material_binding",
                "spectral_cell_screen",
                "spectral_jones_library",
                "spectral_field_family",
                "periodic_transmission",
                "jones_library",
            }
        )
        or (
            finding.kind is FindingKind.CAPABILITY
            and len(finding.needs) == 1
            and bool(finding.needs[0])
            and len(finding.record_references) == 1
        )
        or (
            finding.kind is FindingKind.INCOMPLETE
            and (
                (
                    finding.claim in {"focus", "achromatic_focus"}
                    and finding.needs == ("focus_incomplete",)
                )
                or (
                    finding.claim == "post_freeze_jones_library"
                    and finding.needs
                    in {
                        ("missing_blind",),
                        ("numerical_incomplete",),
                        ("evidence_origin_mismatch",),
                    }
                )
            )
            and bool(finding.record_references)
        )
    )


def _is_compiler_owned_finding(
    finding: Finding,
    brief: MetalensBrief,
    period_advice: PeriodAdvice | None,
    height_advice: HeightAdvice | None,
) -> bool:
    """
    Recognize advice findings the compiler can reproduce without a domain.
    """

    if finding.claim == "period_choice" and brief.cell_period_nm is None:
        if period_advice is None:
            return finding == Finding(
                claim="period_choice",
                kind=FindingKind.ADVICE,
                needs=("period",),
            )
        if isinstance(period_advice.conclusion, EvidenceRequired):
            return finding == Finding(
                claim="period_choice",
                kind=FindingKind.ADVICE,
                needs=("period_evidence_required",),
                record_references=(reference_for(period_advice.document().to_bytes()),),
            )
    if finding.claim == "height_choice" and brief.atom_height_nm is None:
        if height_advice is None:
            return finding == Finding(
                claim="height_choice",
                kind=FindingKind.ADVICE,
                needs=("height",),
            )
        if isinstance(height_advice.conclusion, EvidenceRequired):
            return finding == Finding(
                claim="height_choice",
                kind=FindingKind.ADVICE,
                needs=("height_evidence_required",),
                record_references=(reference_for(height_advice.document().to_bytes()),),
            )
    return False


def _identity(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"
