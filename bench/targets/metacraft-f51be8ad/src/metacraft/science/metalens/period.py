from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import ROUND_CEILING, Decimal
import hashlib

from ...authority import Document, Reference
from ...authority.reference import reference_for, reference_matches
from ...canonical import canonicalize, encode_bytes
from ..consultation import EvidenceRequired
from ..study import Caution, Finding, FindingKind, Study

from .brief import MetalensBrief, require_monochromatic_wavelength
from .design import require_metalens_design
from .material import MaterialBinding
from .period_advice import PeriodAdvice, PeriodRecommendation


PERIOD_DOMAIN_SCHEMA = "metacraft.science.metalens.period_domain"
PERIOD_CHOICE_SCHEMA = "metacraft.science.metalens.period_choice"

PERIOD_GRID_NM = 10
ORDER_CAUTION = "higher orders possible"
ORDER_CAUTION_EXPLANATION = (
    "Nonzero diffraction orders may propagate; zeroth-order summaries alone "
    "cannot establish the sampled output field."
)
_ZEROTH_ORDER_RESPONSE_CAPABILITIES = {
    "periodic_transmission_response",
    "periodic_polarization_response",
}
_REFERENCE_SURFACE_CAPABILITY = "periodic_reference_surface_response"


@dataclass(frozen=True, slots=True)
class PeriodConstraintBasis:
    """
    Names the brief itself as the exclusive source of one period.
    """

    kind: str = field(default="brief constraint", init=False)


@dataclass(frozen=True, slots=True)
class PeriodAdviceBasis:
    """
    Names one exact consultation as the exclusive source of one period.
    """

    advice_reference: Reference
    kind: str = field(default="period advice", init=False)


PeriodBasis = PeriodConstraintBasis | PeriodAdviceBasis


@dataclass(frozen=True, slots=True, kw_only=True)
class PeriodDomain:
    """
    Owns the physical ceilings and the strict 10 nm period grid.

    Identity follows brief, wavelength, and admitted material evidence; no
    route name is persisted. The domain carries no period value; only the
    admitted ``PeriodChoice`` fixes one.
    """

    brief_identity: str
    wavelength_nm: int
    sampling_ceiling_nm: Decimal
    order_ceiling_nm: Decimal
    period_limit_nm: int
    field_response_capability: str
    substrate_refractive_index: Decimal
    material_binding_reference: Reference
    material_sample_reference: Reference
    evidence_reference: Reference | None = None

    def __post_init__(self) -> None:
        """
        Keep one period domain physically coherent and grid aligned.
        """

        if (
            self.wavelength_nm <= 0
            or self.sampling_ceiling_nm <= 0
            or self.order_ceiling_nm <= 0
            or self.period_limit_nm <= 0
            or self.substrate_refractive_index <= 0
        ):
            raise ValueError("period_domain_context_invalid")
        if not self.brief_identity:
            raise ValueError("period_domain_brief_missing")
        if self.field_response_capability not in {
            *_ZEROTH_ORDER_RESPONSE_CAPABILITIES,
            _REFERENCE_SURFACE_CAPABILITY,
        }:
            raise ValueError("period_domain_response_capability_invalid")
        if self.period_limit_nm % PERIOD_GRID_NM:
            raise ValueError("period_domain_limit_off_grid")
        if self.period_limit_nm != _strict_10nm_limit(self.sampling_ceiling_nm):
            raise ValueError("period_domain_limit_mismatch")

    def bind_evidence(self, reference: Reference) -> PeriodDomain:
        """
        Bind this exact domain value to its admitted Authority reference.
        """

        if not reference_matches(reference, self.document().to_bytes()):
            raise ValueError("period_domain_reference_mismatch")
        return PeriodDomain(
            brief_identity=self.brief_identity,
            wavelength_nm=self.wavelength_nm,
            sampling_ceiling_nm=self.sampling_ceiling_nm,
            order_ceiling_nm=self.order_ceiling_nm,
            period_limit_nm=self.period_limit_nm,
            field_response_capability=self.field_response_capability,
            substrate_refractive_index=self.substrate_refractive_index,
            material_binding_reference=self.material_binding_reference,
            material_sample_reference=self.material_sample_reference,
            evidence_reference=reference,
        )

    def document(self) -> Document:
        """
        Rebuild the exact physical period-domain document.
        """

        return Document(
            PERIOD_DOMAIN_SCHEMA,
            {
                "brief_identity": self.brief_identity,
                "field_response_capability": (self.field_response_capability),
                "material_binding_reference": (
                    self.material_binding_reference.as_mapping()
                ),
                "material_sample_reference": (
                    self.material_sample_reference.as_mapping()
                ),
                "order_ceiling_nm": format(self.order_ceiling_nm, "f"),
                "period_limit_nm": self.period_limit_nm,
                "sampling_ceiling_nm": format(
                    self.sampling_ceiling_nm,
                    "f",
                ),
                "substrate_refractive_index": format(
                    self.substrate_refractive_index,
                    "f",
                ),
                "wavelength_nm": self.wavelength_nm,
            },
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        evidence_reference: Reference,
    ) -> PeriodDomain:
        """
        Restore one exact admitted period domain.
        """

        if document.schema_identifier != PERIOD_DOMAIN_SCHEMA:
            raise ValueError("period_domain_schema_mismatch")
        values = document.values
        domain = cls(
            brief_identity=str(values["brief_identity"]),
            wavelength_nm=int(values["wavelength_nm"]),
            sampling_ceiling_nm=Decimal(str(values["sampling_ceiling_nm"])),
            order_ceiling_nm=Decimal(str(values["order_ceiling_nm"])),
            period_limit_nm=int(values["period_limit_nm"]),
            field_response_capability=str(values["field_response_capability"]),
            substrate_refractive_index=Decimal(
                str(values["substrate_refractive_index"])
            ),
            material_binding_reference=Reference.from_mapping(
                values["material_binding_reference"]
            ),
            material_sample_reference=Reference.from_mapping(
                values["material_sample_reference"]
            ),
            evidence_reference=evidence_reference,
        )
        if not reference_matches(
            evidence_reference,
            domain.document().to_bytes(),
        ):
            raise ValueError("period_domain_reference_mismatch")
        return domain


@dataclass(frozen=True, slots=True, kw_only=True)
class PeriodChoice:
    """
    Fixes one admitted period and its exclusive basis.

    Identity follows brief, period, basis, and exact domain reference; no
    route name is persisted. The chosen value is accepted unchanged from one
    explicit brief constraint or one exact period advice.
    """

    brief_identity: str
    period_nm: int
    order_regime: str
    basis: PeriodBasis
    domain_reference: Reference
    reason: str
    evidence_reference: Reference | None = None

    def __post_init__(self) -> None:
        """
        Keep the source of the period exclusive and explicit.
        """

        if self.period_nm <= 0:
            raise ValueError("cell_period_nonpositive")
        if self.order_regime not in {"zeroth order", "multi order"}:
            raise ValueError("period_choice_order_regime_invalid")
        if not isinstance(
            self.basis,
            (PeriodConstraintBasis, PeriodAdviceBasis),
        ):
            raise ValueError("period_basis_invalid")

    @property
    def cautions(self) -> tuple[Caution, ...]:
        """
        Preserve order risk against the exact domain behind this choice.
        """

        return _order_cautions(self.order_regime, self.domain_reference)

    def bind_evidence(self, reference: Reference) -> PeriodChoice:
        """
        Bind this exact choice to its admitted Authority reference.
        """

        if not reference_matches(reference, self.document().to_bytes()):
            raise ValueError("period_choice_reference_mismatch")
        return replace(self, evidence_reference=reference)

    @classmethod
    def from_document(cls, document: Document) -> PeriodChoice:
        """
        Restore one exact period choice.
        """

        if document.schema_identifier != PERIOD_CHOICE_SCHEMA:
            raise ValueError("period_choice_schema_mismatch")
        values = document.values
        choice = cls(
            brief_identity=str(values["brief_identity"]),
            period_nm=int(values["period_nm"]),
            order_regime=str(values["order_regime"]),
            basis=_period_basis(values["basis"]),
            domain_reference=Reference.from_mapping(values["domain_reference"]),
            reason=str(values["reason"]),
        )
        if choice.document().to_bytes() != document.to_bytes():
            raise ValueError("period_choice_document_mismatch")
        return choice

    def canonical_bytes(self) -> bytes:
        """
        Encode one exact choice for stable comparison.
        """

        return encode_bytes(canonicalize(replace(self, evidence_reference=None)))

    def document(self) -> Document:
        """
        Wrap one exact choice for Authority admission.
        """

        return Document(
            PERIOD_CHOICE_SCHEMA,
            canonicalize(replace(self, evidence_reference=None)),
        )

    def references(self) -> tuple[Reference, ...]:
        """
        Return the domain and advice behind this choice.
        """

        if isinstance(self.basis, PeriodAdviceBasis):
            return self.domain_reference, self.basis.advice_reference
        return (self.domain_reference,)


def derive_period_domain(
    study: Study,
    binding: MaterialBinding,
) -> PeriodDomain:
    """
    Derive physical period ceilings from admitted brief and material evidence.
    """

    if binding.brief_identity != study.brief_identity:
        raise ValueError("material_binding_brief_mismatch")
    wavelength_nm = require_monochromatic_wavelength(
        require_metalens_design(study).operating_spectrum
    )
    if binding.wavelength_nm != wavelength_nm:
        raise ValueError("material_binding_wavelength_mismatch")
    if not reference_matches(
        binding.evidence_reference,
        binding.document().to_bytes(),
    ):
        raise ValueError("material_binding_reference_mismatch")
    (
        sampling_ceiling_nm,
        order_ceiling_nm,
        period_limit_nm,
    ) = derive_period_limits(study, binding)
    field_response_capability = _field_response_capability(study)
    return PeriodDomain(
        brief_identity=study.brief_identity,
        wavelength_nm=wavelength_nm,
        sampling_ceiling_nm=sampling_ceiling_nm,
        order_ceiling_nm=order_ceiling_nm,
        period_limit_nm=period_limit_nm,
        field_response_capability=field_response_capability,
        substrate_refractive_index=binding.substrate.refractive_index,
        material_binding_reference=binding.evidence_reference,
        material_sample_reference=binding.sample_reference,
    )


def resolve_period_choice(
    study: Study,
    domain: PeriodDomain,
    *,
    period_advice: PeriodAdvice | None = None,
) -> PeriodChoice | Finding:
    """
    Adopt one explicit brief period or one exact advised period unchanged.
    """

    _validate_domain(study, domain)
    brief = study.brief
    if not isinstance(brief, MetalensBrief):
        raise ValueError("metalens_brief_required")
    if brief.cell_period_nm is not None:
        if period_advice is not None:
            raise ValueError("period_advice_forbidden")
        period_nm = brief.cell_period_nm
        basis: PeriodBasis = PeriodConstraintBasis()
        reason = "period stated by brief"
        issue = _period_value_issue(period_nm, domain)
        if issue is not None:
            return Finding(
                claim="period_choice",
                kind=FindingKind.REFUSAL,
                needs=(issue,),
            )
    else:
        if period_advice is None:
            return Finding(
                claim="period_choice",
                kind=FindingKind.ADVICE,
                needs=("period",),
            )
        if not isinstance(period_advice, PeriodAdvice):
            raise ValueError("period_advice_type_invalid")
        advice_reference = reference_for(period_advice.document().to_bytes())
        if period_advice.brief_identity != study.brief_identity:
            raise ValueError("period_advice_brief_mismatch")
        if period_advice.domain_reference != domain.evidence_reference:
            raise ValueError("period_advice_domain_mismatch")
        if isinstance(period_advice.conclusion, EvidenceRequired):
            return Finding(
                claim="period_choice",
                kind=FindingKind.ADVICE,
                needs=("period_evidence_required",),
                record_references=(advice_reference,),
            )
        ready = tuple(
            task for task in study.ready_tasks if task.claim == "period_choice"
        )
        if len(ready) != 1 or ready[0].consultations != (advice_reference,):
            raise ValueError("period_advice_not_bound")
        recommendation = period_advice.conclusion
        if not isinstance(recommendation, PeriodRecommendation):
            raise ValueError("period_advice_conclusion_invalid")
        if recommendation.period_nm <= 0:
            return Finding(
                claim="period_choice",
                kind=FindingKind.ADVICE,
                needs=("period_advice_nonpositive",),
                record_references=(advice_reference,),
            )
        if recommendation.period_nm % PERIOD_GRID_NM:
            return Finding(
                claim="period_choice",
                kind=FindingKind.ADVICE,
                needs=("period_advice_off_grid",),
                record_references=(advice_reference,),
            )
        period_nm = recommendation.period_nm
        basis = PeriodAdviceBasis(advice_reference)
        reason = recommendation.reason
        issue = _period_value_issue(period_nm, domain)
        if issue is not None:
            return Finding(
                claim="period_choice",
                kind=FindingKind.ADVICE,
                needs=("period_advice_outside_domain",),
                record_references=(advice_reference,),
            )
    assert domain.evidence_reference is not None
    return PeriodChoice(
        brief_identity=study.brief_identity,
        period_nm=period_nm,
        order_regime=(
            "zeroth order"
            if Decimal(period_nm) < domain.order_ceiling_nm
            else "multi order"
        ),
        basis=basis,
        domain_reference=domain.evidence_reference,
        reason=reason,
    )


def validate_period_choice_finding(
    study: Study,
    domain: PeriodDomain,
    period_advice: PeriodAdvice | None,
    finding: Finding,
) -> None:
    """
    Require the exact finding recomputed by the period-choice owner.
    """

    expected = resolve_period_choice(
        study,
        domain,
        period_advice=period_advice,
    )
    if not isinstance(expected, Finding) or expected != finding:
        raise ValueError("reported_finding_invalid")


def validate_period_choice(
    study: Study,
    choice: PeriodChoice,
    *,
    choice_reference: Reference,
) -> None:
    """
    Keep later work on the exact admitted physical period choice.
    """

    if choice.brief_identity != study.brief_identity:
        raise ValueError("period_choice_brief_mismatch")
    if not reference_matches(
        choice_reference,
        choice.document().to_bytes(),
    ):
        raise ValueError("period_choice_reference_mismatch")
    domains = tuple(
        fact.reference for fact in study.evidence if fact.claim == "period_domain"
    )
    if domains != (choice.domain_reference,):
        raise ValueError("period_choice_domain_mismatch")
    choices = tuple(
        fact.reference for fact in study.evidence if fact.claim == "period_choice"
    )
    if choices != (choice_reference,):
        raise ValueError("period_choice_not_admitted")
    brief = study.brief
    if not isinstance(brief, MetalensBrief):
        raise ValueError("metalens_brief_required")
    if brief.cell_period_nm is not None:
        if choice.period_nm != brief.cell_period_nm or not isinstance(
            choice.basis,
            PeriodConstraintBasis,
        ):
            raise ValueError("period_choice_basis_mismatch")
    elif not isinstance(choice.basis, PeriodAdviceBasis):
        raise ValueError("period_choice_basis_mismatch")


def derive_period_limits(
    study: Study,
    binding: MaterialBinding,
) -> tuple[Decimal, Decimal, int]:
    """
    Derive both exact physical ceilings and their strict 10 nm limit.
    """

    if binding.brief_identity != study.brief_identity:
        raise ValueError("material_binding_brief_mismatch")
    design = require_metalens_design(study)
    wavelength_nm = require_monochromatic_wavelength(design.operating_spectrum)
    if binding.wavelength_nm != wavelength_nm:
        raise ValueError("material_binding_wavelength_mismatch")
    sampling_ceiling_nm = design.sampling_ceiling_nm
    order_ceiling_nm = Decimal(wavelength_nm) / (
        binding.substrate.refractive_index + design.numerical_aperture
    )
    return (
        sampling_ceiling_nm,
        order_ceiling_nm,
        _strict_10nm_limit(sampling_ceiling_nm),
    )


def validate_period_domain(
    brief: MetalensBrief,
    domain: PeriodDomain,
) -> None:
    """
    Validate one period domain against its sole physical rule owner.
    """

    wavelength_nm = require_monochromatic_wavelength(brief.operating_spectrum)
    expected_sampling = Decimal(wavelength_nm) / (Decimal(2) * brief.numerical_aperture)
    expected_order = Decimal(wavelength_nm) / (
        domain.substrate_refractive_index + brief.numerical_aperture
    )
    expected_capability = domain.field_response_capability
    expected_limit = _strict_10nm_limit(expected_sampling)
    if domain.brief_identity != _identity(brief.canonical_bytes()):
        raise ValueError("period_domain_brief_mismatch")
    if domain.wavelength_nm != wavelength_nm:
        raise ValueError("period_domain_wavelength_mismatch")
    if (
        domain.sampling_ceiling_nm != expected_sampling
        or domain.order_ceiling_nm != expected_order
        or domain.period_limit_nm != expected_limit
        or domain.field_response_capability != expected_capability
    ):
        raise ValueError("period_domain_physics_mismatch")


def validate_period_value(period_nm: int, domain: PeriodDomain) -> None:
    """
    Apply the one period grid and physical-limit rule.
    """

    issue = _period_value_issue(period_nm, domain)
    if issue is not None:
        raise ValueError(issue)


def _period_value_issue(period_nm: int, domain: PeriodDomain) -> str | None:
    if period_nm <= 0:
        return "cell_period_nonpositive"
    if period_nm % PERIOD_GRID_NM:
        return "cell_period_not_10nm_aligned"
    if Decimal(period_nm) >= domain.sampling_ceiling_nm:
        return "cell_period_at_or_above_sampling_ceiling"
    if period_nm > domain.period_limit_nm:
        return "cell_period_above_period_limit"
    return None


def _validate_domain(study: Study, domain: PeriodDomain) -> None:
    """
    Verify one period domain against the exact study and admitted evidence.
    """

    brief = study.brief
    if not isinstance(brief, MetalensBrief):
        raise ValueError("metalens_brief_required")
    validate_period_domain(brief, domain)
    if domain.field_response_capability != _field_response_capability(study):
        raise ValueError("period_domain_response_capability_mismatch")
    if domain.evidence_reference is None or not reference_matches(
        domain.evidence_reference,
        domain.document().to_bytes(),
    ):
        raise ValueError("period_domain_reference_mismatch")
    admitted = tuple(fact for fact in study.evidence if fact.claim == "period_domain")
    if len(admitted) != 1 or (admitted[0].reference != domain.evidence_reference):
        raise ValueError("period_domain_not_admitted")


def _field_response_capability(study: Study) -> str:
    """
    Read the complete-field response rule from the compiled proof.
    """

    capabilities = {
        claim.capability for claim in study.proof.claims if claim.capability is not None
    }
    if _REFERENCE_SURFACE_CAPABILITY in capabilities:
        return _REFERENCE_SURFACE_CAPABILITY
    zeroth_order = tuple(sorted(capabilities & _ZEROTH_ORDER_RESPONSE_CAPABILITIES))
    if len(zeroth_order) != 1:
        raise ValueError("field_response_capability_unresolved")
    return zeroth_order[0]


def _strict_10nm_limit(value: Decimal) -> int:
    """
    Return the greatest 10 nm grid value strictly below one ceiling.
    """

    return int(
        (
            (value / Decimal(PERIOD_GRID_NM)).to_integral_value(rounding=ROUND_CEILING)
            - Decimal(1)
        )
        * Decimal(PERIOD_GRID_NM)
    )


def _order_cautions(
    order_regime: str,
    source_reference: Reference,
) -> tuple[Caution, ...]:
    if order_regime != "multi order":
        return ()
    return (
        Caution(
            concern=ORDER_CAUTION,
            explanation=ORDER_CAUTION_EXPLANATION,
            source_reference=source_reference,
        ),
    )


def _period_basis(value: object) -> PeriodBasis:
    if not isinstance(value, dict):
        raise ValueError("period_basis_invalid")
    kind = str(value.get("kind", ""))
    if kind == "brief constraint":
        if set(value) != {"kind"}:
            raise ValueError("period_basis_invalid")
        return PeriodConstraintBasis()
    if kind == "period advice":
        if set(value) != {"advice_reference", "kind"}:
            raise ValueError("period_basis_invalid")
        return PeriodAdviceBasis(Reference.from_mapping(value["advice_reference"]))
    raise ValueError("period_basis_invalid")


def _identity(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"
