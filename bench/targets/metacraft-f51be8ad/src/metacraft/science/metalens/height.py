from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import TYPE_CHECKING

from ...authority import Document, Reference
from ...authority.reference import reference_for, reference_matches
from ...canonical import canonicalize, encode_bytes
from ...materials import MaterialSource
from metacraft.science.consultation import EvidenceRequired
from ..study import Caution, Finding, FindingKind, Study

from .brief import (
    AtomIntent,
    ControlStrategy,
    MaterialIntent,
    MetalensBrief,
    _atom_intent_value,
    _material_intent_value,
    require_monochromatic_wavelength,
)
from .design import require_metalens_design
from .height_advice import HeightAdvice
from .material import MaterialBinding
from .period import (
    PeriodChoice,
    validate_period_choice,
)

if TYPE_CHECKING:
    from .propagation_envelope import PhaseEnvelope


HEIGHT_DOMAIN_SCHEMA = "metacraft.science.metalens.height_domain"
HEIGHT_CHOICE_SCHEMA = "metacraft.science.metalens.height_choice"


@dataclass(frozen=True, slots=True)
class FabricationRange:
    """
    Counts one height's manufacturable lateral candidates.
    """

    height_nm: int
    minimum_feature_nm: int
    maximum_feature_nm: int
    candidate_count: int

    def as_mapping(self) -> dict[str, int]:
        """
        Return this height's exact fabrication arithmetic.
        """

        return {
            "candidate_count": self.candidate_count,
            "height_nm": self.height_nm,
            "maximum_feature_nm": self.maximum_feature_nm,
            "minimum_feature_nm": self.minimum_feature_nm,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class HeightDomain:
    """
    Owns finite height candidates and lateral fabrication arithmetic.

    Identity follows brief, the admitted period choice, and exact
    fabrication arithmetic; no route name is persisted. The period value is
    carried as a denormalized fact whose sole authority is the cited choice.
    """

    brief_identity: str
    wavelength_nm: int
    period_nm: int
    period_choice_reference: Reference
    order_regime: str
    heights_nm: tuple[int, ...]
    fabrication_ranges: tuple[FabricationRange, ...]
    aspect_limit: int
    dimension_step_nm: int
    atom: AtomIntent
    substrate: MaterialIntent
    material_binding_reference: Reference
    material_sample_reference: Reference
    evidence_reference: Reference | None = None

    def __post_init__(self) -> None:
        """
        Keep one height domain internally ordered and physically coherent.
        """

        if (
            self.wavelength_nm <= 0
            or self.period_nm <= 0
            or self.aspect_limit <= 0
            or self.dimension_step_nm <= 0
        ):
            raise ValueError("height_domain_context_invalid")
        if not self.brief_identity:
            raise ValueError("height_domain_brief_missing")
        if self.order_regime not in {"zeroth order", "multi order"}:
            raise ValueError("height_domain_order_regime_invalid")
        if self.period_nm % 10:
            raise ValueError("height_domain_period_off_grid")
        if len(set(self.heights_nm)) != len(self.heights_nm):
            raise ValueError("height_domain_heights_invalid")
        object.__setattr__(
            self,
            "heights_nm",
            tuple(sorted(self.heights_nm)),
        )
        if tuple(entry.height_nm for entry in self.fabrication_ranges) != tuple(
            sorted(entry.height_nm for entry in self.fabrication_ranges)
        ):
            raise ValueError("height_domain_ranges_unordered")

    @property
    def cautions(self) -> tuple[Caution, ...]:
        """
        Report order risk against the admitted period choice.
        """

        return _order_cautions(
            self.order_regime,
            self.period_choice_reference,
        )

    def bind_evidence(self, reference: Reference) -> HeightDomain:
        """
        Bind this exact domain value to its admitted Authority reference.
        """

        if not reference_matches(reference, self.document().to_bytes()):
            raise ValueError("height_domain_reference_mismatch")
        return HeightDomain(
            brief_identity=self.brief_identity,
            wavelength_nm=self.wavelength_nm,
            period_nm=self.period_nm,
            period_choice_reference=self.period_choice_reference,
            order_regime=self.order_regime,
            heights_nm=self.heights_nm,
            fabrication_ranges=self.fabrication_ranges,
            aspect_limit=self.aspect_limit,
            dimension_step_nm=self.dimension_step_nm,
            atom=self.atom,
            substrate=self.substrate,
            material_binding_reference=(self.material_binding_reference),
            material_sample_reference=self.material_sample_reference,
            evidence_reference=reference,
        )

    def document(self) -> Document:
        """
        Rebuild the exact physical height-domain document.
        """

        return Document(
            HEIGHT_DOMAIN_SCHEMA,
            {
                "aspect_limit": self.aspect_limit,
                "atom": _atom_intent_value(self.atom),
                "brief_identity": self.brief_identity,
                "cautions": [caution.as_mapping() for caution in self.cautions],
                "dimension_step_nm": self.dimension_step_nm,
                "fabrication_ranges": [
                    entry.as_mapping() for entry in self.fabrication_ranges
                ],
                "heights_nm": list(self.heights_nm),
                "material_binding_reference": (
                    self.material_binding_reference.as_mapping()
                ),
                "material_sample_reference": (
                    self.material_sample_reference.as_mapping()
                ),
                "order_regime": self.order_regime,
                "period_choice_reference": (self.period_choice_reference.as_mapping()),
                "period_nm": self.period_nm,
                "substrate": _material_intent_value(self.substrate),
                "wavelength_nm": self.wavelength_nm,
            },
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        evidence_reference: Reference,
    ) -> HeightDomain:
        """
        Restore one exact admitted height domain.
        """

        if document.schema_identifier != HEIGHT_DOMAIN_SCHEMA:
            raise ValueError("height_domain_schema_mismatch")
        values = document.values
        ranges = values["fabrication_ranges"]
        if not isinstance(ranges, list):
            raise ValueError("height_domain_ranges_invalid")
        domain = cls(
            brief_identity=str(values["brief_identity"]),
            wavelength_nm=int(values["wavelength_nm"]),
            period_nm=int(values["period_nm"]),
            period_choice_reference=Reference.from_mapping(
                values["period_choice_reference"]
            ),
            order_regime=str(values["order_regime"]),
            heights_nm=tuple(int(height) for height in values["heights_nm"]),
            fabrication_ranges=tuple(_fabrication_range(value) for value in ranges),
            aspect_limit=int(values["aspect_limit"]),
            dimension_step_nm=int(values["dimension_step_nm"]),
            atom=_atom_intent(values["atom"]),
            substrate=_material_intent(values["substrate"]),
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
            raise ValueError("height_domain_reference_mismatch")
        return domain

    def resolve_fabrication_range(
        self,
        height_nm: int,
    ) -> FabricationRange:
        """
        Return the fabrication arithmetic for one declared height.
        """

        matches = tuple(
            entry for entry in self.fabrication_ranges if entry.height_nm == height_nm
        )
        if len(matches) != 1:
            raise ValueError("height_domain_range_missing")
        return matches[0]


@dataclass(frozen=True, slots=True)
class HeightConstraintBasis:
    """
    Names the brief itself as the exclusive source of one height.
    """

    kind: str = field(default="brief constraint", init=False)


@dataclass(frozen=True, slots=True)
class HeightAdviceBasis:
    """
    Names one exact consultation as the exclusive source of one height.
    """

    advice_reference: Reference
    kind: str = field(default="height advice", init=False)


HeightBasis = HeightConstraintBasis | HeightAdviceBasis


@dataclass(frozen=True, slots=True, kw_only=True)
class HeightChoice:
    """
    Fixes one advised height and its physical fabrication domain.

    Identity follows brief, height, period choice, fabrication, and exact
    domain reference; no route name is persisted.
    """

    brief_identity: str
    height_nm: int
    period_nm: int
    order_regime: str
    minimum_feature_nm: int
    maximum_feature_nm: int
    dimension_step_nm: int
    domain_reference: Reference
    basis: HeightBasis
    reason: str

    def __post_init__(self) -> None:
        """
        Keep the source of the height exclusive and explicit.
        """

        if not isinstance(
            self.basis,
            (HeightConstraintBasis, HeightAdviceBasis),
        ):
            raise ValueError("height_basis_invalid")

    @property
    def cautions(self) -> tuple[Caution, ...]:
        """
        Preserve order risk against the exact domain behind this choice.
        """

        return _order_cautions(
            self.order_regime,
            self.domain_reference,
        )

    @classmethod
    def from_document(cls, document: Document) -> HeightChoice:
        """
        Restore one exact height choice.
        """

        if document.schema_identifier != HEIGHT_CHOICE_SCHEMA:
            raise ValueError("height_choice_schema_mismatch")
        values = document.values
        choice = cls(
            brief_identity=str(values["brief_identity"]),
            height_nm=int(values["height_nm"]),
            period_nm=int(values["period_nm"]),
            order_regime=str(values["order_regime"]),
            minimum_feature_nm=int(values["minimum_feature_nm"]),
            maximum_feature_nm=int(values["maximum_feature_nm"]),
            dimension_step_nm=int(values["dimension_step_nm"]),
            domain_reference=Reference.from_mapping(values["domain_reference"]),
            basis=_height_basis(values["basis"]),
            reason=str(values["reason"]),
        )
        if choice.document().to_bytes() != document.to_bytes():
            raise ValueError("height_choice_document_mismatch")
        return choice

    def canonical_bytes(self) -> bytes:
        """
        Encode one exact choice for stable comparison.
        """

        return encode_bytes(canonicalize(self))

    def document(self) -> Document:
        """
        Wrap one exact choice for Authority admission.
        """

        return Document(
            HEIGHT_CHOICE_SCHEMA,
            canonicalize(self),
        )

    def references(self) -> tuple[Reference, ...]:
        """
        Return the domain and advice behind this choice.
        """

        if isinstance(self.basis, HeightAdviceBasis):
            return self.domain_reference, self.basis.advice_reference
        return (self.domain_reference,)


def derive_height_domain(
    study: Study,
    period_choice: PeriodChoice,
    binding: MaterialBinding,
) -> HeightDomain | Finding:
    """
    Derive finite height candidates from the admitted period choice.
    """

    brief = study.brief
    if not isinstance(brief, MetalensBrief):
        raise ValueError("metalens_brief_required")
    if period_choice.evidence_reference is None:
        raise ValueError("period_choice_not_admitted")
    validate_period_choice(
        study,
        period_choice,
        choice_reference=period_choice.evidence_reference,
    )
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
    step_nm = brief.dimension_step_nm
    if step_nm is None:
        raise ValueError("dimension_step_missing")
    height_candidates = (
        (brief.atom_height_nm,)
        if brief.atom_height_nm is not None
        else _height_candidates(wavelength_nm)
    )
    ranges = tuple(
        _fabrication_range_for(
            height_nm,
            aspect_limit=require_metalens_design(study).aspect_limit,
            period_nm=period_choice.period_nm,
            step_nm=step_nm,
        )
        for height_nm in height_candidates
    )
    heights = tuple(
        entry.height_nm
        for entry in ranges
        if _has_sufficient_candidates(
            require_metalens_design(study).control_strategy,
            entry,
        )
    )
    if brief.atom_height_nm is not None and not heights:
        return Finding(
            claim="height_domain",
            kind=FindingKind.REFUSAL,
            needs=("fabrication_domain_empty",),
            record_references=(
                period_choice.evidence_reference,
                binding.evidence_reference,
            ),
        )
    return HeightDomain(
        brief_identity=study.brief_identity,
        wavelength_nm=wavelength_nm,
        period_nm=period_choice.period_nm,
        period_choice_reference=period_choice.evidence_reference,
        order_regime=period_choice.order_regime,
        heights_nm=heights,
        fabrication_ranges=ranges,
        aspect_limit=require_metalens_design(study).aspect_limit,
        dimension_step_nm=step_nm,
        atom=require_metalens_design(study).atom,
        substrate=require_metalens_design(study).substrate,
        material_binding_reference=binding.evidence_reference,
        material_sample_reference=binding.sample_reference,
    )


def resolve_height_choice(
    study: Study,
    domain: HeightDomain,
    advice: HeightAdvice | None = None,
    *,
    envelope: PhaseEnvelope | None = None,
) -> HeightChoice | Finding:
    """
    Adopt the exact recommendation allowed by the admitted domain.
    """

    _validate_domain(study, domain)
    assert domain.evidence_reference is not None
    brief = study.brief
    if not isinstance(brief, MetalensBrief):
        raise ValueError("metalens_brief_required")
    is_constrained = brief.atom_height_nm is not None
    advice_reference: Reference | None = None
    if is_constrained:
        if advice is not None:
            raise ValueError("height_advice_forbidden")
    else:
        if advice is None:
            return Finding(
                claim="height_choice",
                kind=FindingKind.ADVICE,
                needs=("height",),
            )
        if not isinstance(advice, HeightAdvice):
            raise ValueError("height_advice_type_invalid")
        advice_reference = reference_for(advice.document().to_bytes())
        if advice.brief_identity != study.brief_identity:
            raise ValueError("height_advice_brief_mismatch")
        if advice.domain_reference != domain.evidence_reference:
            raise ValueError("height_advice_stale")
    _validate_height_choice_grounds(
        study,
        domain,
        advice,
        envelope=envelope,
    )
    if not is_constrained:
        assert advice is not None
        assert advice_reference is not None
        if isinstance(advice.conclusion, EvidenceRequired):
            return Finding(
                claim="height_choice",
                kind=FindingKind.ADVICE,
                needs=("height_evidence_required",),
                record_references=(advice_reference,),
            )
        ready = tuple(
            task for task in study.ready_tasks if task.claim == "height_choice"
        )
        if len(ready) != 1 or ready[0].consultations != (advice_reference,):
            raise ValueError("height_advice_not_bound")

    if is_constrained:
        height_nm = brief.atom_height_nm
        assert height_nm is not None
        if domain.heights_nm != (height_nm,):
            return Finding(
                claim="height_choice",
                kind=FindingKind.REFUSAL,
                needs=("height_constraint_domain_mismatch",),
                record_references=(domain.evidence_reference,),
            )
        if envelope is not None and all(
            standing.standing == "ruled out"
            for standing in envelope.reach_for(height_nm).standings
        ):
            assert envelope.evidence_reference is not None
            return Finding(
                claim="height_choice",
                kind=FindingKind.REFUSAL,
                needs=("height_constraint_ruled_out",),
                record_references=(envelope.evidence_reference,),
            )
        recommendation = None
    else:
        assert advice is not None
        recommendation = advice.conclusion
        assert not isinstance(recommendation, EvidenceRequired)
        height_nm = recommendation.height_nm
    if recommendation is not None and height_nm not in domain.heights_nm:
        assert advice_reference is not None
        return Finding(
            claim="height_choice",
            kind=FindingKind.ADVICE,
            needs=("height_advice_outside_domain",),
            record_references=(advice_reference,),
        )
    if envelope is not None and all(
        standing.standing == "ruled out"
        for standing in envelope.reach_for(height_nm).standings
    ):
        assert advice_reference is not None
        assert envelope.evidence_reference is not None
        return Finding(
            claim="height_choice",
            kind=FindingKind.ADVICE,
            needs=("height_advice_ruled_out",),
            record_references=(
                advice_reference,
                envelope.evidence_reference,
            ),
        )
    fabrication = domain.resolve_fabrication_range(height_nm)
    if is_constrained:
        basis: HeightBasis = HeightConstraintBasis()
    else:
        assert advice_reference is not None
        basis = HeightAdviceBasis(advice_reference)
    return HeightChoice(
        brief_identity=study.brief_identity,
        height_nm=height_nm,
        period_nm=domain.period_nm,
        order_regime=domain.order_regime,
        minimum_feature_nm=fabrication.minimum_feature_nm,
        maximum_feature_nm=fabrication.maximum_feature_nm,
        dimension_step_nm=domain.dimension_step_nm,
        domain_reference=domain.evidence_reference,
        basis=basis,
        reason=(
            "height stated by brief"
            if recommendation is None
            else recommendation.reason
        ),
    )


def _validate_height_choice_grounds(
    study: Study,
    domain: HeightDomain,
    advice: HeightAdvice | None,
    *,
    envelope: PhaseEnvelope | None,
) -> None:
    if (
        require_metalens_design(study).control_strategy
        is ControlStrategy.PROPAGATION_PHASE
    ):
        if envelope is None or envelope.evidence_reference is None:
            raise ValueError("phase_envelope_required")
        envelopes = tuple(
            fact.reference for fact in study.evidence if fact.claim == "phase_envelope"
        )
        if envelopes != (envelope.evidence_reference,):
            raise ValueError("phase_envelope_not_admitted")
        if advice is not None and (
            advice.envelope_reference != envelope.evidence_reference
        ):
            raise ValueError("height_advice_envelope_stale")
        if domain.evidence_reference not in envelope.source_references:
            raise ValueError("phase_envelope_domain_mismatch")
    elif envelope is not None or (
        advice is not None and advice.envelope_reference is not None
    ):
        raise ValueError("geometric_phase_envelope_forbidden")


def validate_height_domain_finding(
    study: Study,
    period_choice: PeriodChoice,
    binding: MaterialBinding,
    finding: Finding,
) -> None:
    """
    Require the exact refusal recomputed by the height-domain owner.
    """

    expected = derive_height_domain(study, period_choice, binding)
    if not isinstance(expected, Finding) or expected != finding:
        raise ValueError("reported_finding_invalid")


def validate_height_choice_finding(
    study: Study,
    domain: HeightDomain,
    advice: HeightAdvice | None,
    finding: Finding,
    *,
    envelope: PhaseEnvelope | None = None,
) -> None:
    """
    Require the exact finding recomputed by the height-choice owner.
    """

    expected = resolve_height_choice(
        study,
        domain,
        advice,
        envelope=envelope,
    )
    if not isinstance(expected, Finding) or expected != finding:
        raise ValueError("reported_finding_invalid")


def validate_height_choice(
    study: Study,
    choice: HeightChoice,
    *,
    choice_reference: Reference,
) -> None:
    """
    Keep later work on the exact admitted physical height choice.
    """

    if choice.brief_identity != study.brief_identity:
        raise ValueError("height_choice_brief_mismatch")
    if not reference_matches(
        choice_reference,
        choice.document().to_bytes(),
    ):
        raise ValueError("height_choice_reference_mismatch")
    domains = tuple(
        fact.reference for fact in study.evidence if fact.claim == "height_domain"
    )
    if domains != (choice.domain_reference,):
        raise ValueError("height_choice_domain_mismatch")
    choices = tuple(
        fact.reference for fact in study.evidence if fact.claim == "height_choice"
    )
    if choices != (choice_reference,):
        raise ValueError("height_choice_not_admitted")
    brief = study.brief
    expected_heights = (
        (brief.atom_height_nm,)
        if (isinstance(brief, MetalensBrief) and brief.atom_height_nm is not None)
        else _height_candidates(
            require_monochromatic_wavelength(
                require_metalens_design(study).operating_spectrum
            )
        )
    )
    if choice.height_nm not in expected_heights:
        raise ValueError("height_choice_height_mismatch")
    if choice.order_regime not in {"zeroth order", "multi order"}:
        raise ValueError("height_choice_period_mismatch")
    expected = _fabrication_range_for(
        choice.height_nm,
        aspect_limit=require_metalens_design(study).aspect_limit,
        period_nm=choice.period_nm,
        step_nm=choice.dimension_step_nm,
    )
    if (
        choice.minimum_feature_nm != expected.minimum_feature_nm
        or choice.maximum_feature_nm != expected.maximum_feature_nm
        or choice.maximum_feature_nm <= choice.minimum_feature_nm
    ):
        raise ValueError("height_choice_fabrication_mismatch")


def _validate_domain(study: Study, domain: HeightDomain) -> None:
    if domain.brief_identity != study.brief_identity:
        raise ValueError("height_domain_brief_mismatch")
    if domain.evidence_reference is None or not reference_matches(
        domain.evidence_reference,
        domain.document().to_bytes(),
    ):
        raise ValueError("height_domain_reference_mismatch")
    admitted = tuple(fact for fact in study.evidence if fact.claim == "height_domain")
    if len(admitted) != 1 or (admitted[0].reference != domain.evidence_reference):
        raise ValueError("height_domain_not_admitted")
    brief = study.brief
    if not isinstance(brief, MetalensBrief):
        raise ValueError("metalens_brief_required")
    if domain.dimension_step_nm != brief.dimension_step_nm:
        raise ValueError("height_domain_dimension_step_mismatch")
    if domain.period_nm % 10:
        raise ValueError("height_domain_period_off_grid")
    period_choices = tuple(
        fact for fact in study.evidence if fact.claim == "period_choice"
    )
    if len(period_choices) != 1 or (
        period_choices[0].reference != domain.period_choice_reference
    ):
        raise ValueError("height_domain_period_choice_mismatch")
    expected_height_candidates = (
        (brief.atom_height_nm,)
        if (isinstance(brief, MetalensBrief) and brief.atom_height_nm is not None)
        else _height_candidates(
            require_monochromatic_wavelength(
                require_metalens_design(study).operating_spectrum
            )
        )
    )
    expected_ranges = tuple(
        _fabrication_range_for(
            height_nm,
            aspect_limit=require_metalens_design(study).aspect_limit,
            period_nm=domain.period_nm,
            step_nm=domain.dimension_step_nm,
        )
        for height_nm in expected_height_candidates
    )
    expected_heights = tuple(
        entry.height_nm
        for entry in expected_ranges
        if _has_sufficient_candidates(
            require_metalens_design(study).control_strategy,
            entry,
        )
    )
    if (
        domain.fabrication_ranges != expected_ranges
        or domain.heights_nm != expected_heights
    ):
        raise ValueError("height_domain_fabrication_mismatch")


def _fabrication_range_for(
    height_nm: int,
    *,
    aspect_limit: int,
    period_nm: int,
    step_nm: int,
) -> FabricationRange:
    raw_feature = Decimal(height_nm) / Decimal(aspect_limit)
    minimum_feature_nm = (
        int((raw_feature / Decimal(step_nm)).to_integral_value(rounding=ROUND_CEILING))
        * step_nm
    )
    maximum_feature_nm = period_nm - minimum_feature_nm
    candidate_count = (
        0
        if maximum_feature_nm < minimum_feature_nm
        else ((maximum_feature_nm - minimum_feature_nm) // step_nm) + 1
    )
    return FabricationRange(
        height_nm=height_nm,
        minimum_feature_nm=minimum_feature_nm,
        maximum_feature_nm=maximum_feature_nm,
        candidate_count=candidate_count,
    )


def _has_sufficient_candidates(
    control_strategy: ControlStrategy,
    fabrication: FabricationRange,
) -> bool:
    if control_strategy is ControlStrategy.PROPAGATION_PHASE:
        return fabrication.candidate_count >= 16
    return fabrication.candidate_count >= 2


def _height_candidates(wavelength_nm: int) -> tuple[int, ...]:
    """
    Return the control-strategy height prior for one spectral band.
    """

    if wavelength_nm <= 700:
        return tuple(range(500, 801, 50))
    lower_nm = _ceil_50nm(Decimal(wavelength_nm) * Decimal("0.5"))
    upper_nm = _floor_50nm(Decimal(wavelength_nm) * Decimal("0.6"))
    return tuple(range(lower_nm, upper_nm + 1, 50))


def _ceil_50nm(value: Decimal) -> int:
    return int(
        (value / Decimal(50)).to_integral_value(rounding=ROUND_CEILING) * Decimal(50)
    )


def _floor_50nm(value: Decimal) -> int:
    return int(
        (value / Decimal(50)).to_integral_value(rounding=ROUND_FLOOR) * Decimal(50)
    )


def _order_cautions(
    order_regime: str,
    source_reference: Reference,
) -> tuple[Caution, ...]:
    if order_regime != "multi order":
        return ()
    return (
        Caution(
            concern=_ORDER_CAUTION,
            explanation=_ORDER_CAUTION_EXPLANATION,
            source_reference=source_reference,
        ),
    )


_ORDER_CAUTION = "higher orders possible"
_ORDER_CAUTION_EXPLANATION = (
    "Nonzero diffraction orders may propagate; zeroth-order summaries alone "
    "cannot establish the sampled output field."
)


def _fabrication_range(value: object) -> FabricationRange:
    if not isinstance(value, dict):
        raise ValueError("height_domain_range_invalid")
    return FabricationRange(
        height_nm=int(value["height_nm"]),
        minimum_feature_nm=int(value["minimum_feature_nm"]),
        maximum_feature_nm=int(value["maximum_feature_nm"]),
        candidate_count=int(value["candidate_count"]),
    )


def _atom_intent(value: object) -> AtomIntent:
    if not isinstance(value, dict):
        raise ValueError("height_domain_atom_invalid")
    return AtomIntent(
        shape=str(value["shape"]),
        material=_material_intent(value["material"]),
    )


def _material_intent(value: object) -> MaterialIntent:
    if not isinstance(value, dict):
        raise ValueError("height_domain_material_invalid")
    return MaterialIntent(
        family=str(value["material"]),
        source=MaterialSource(str(value["source"])),
    )


def _height_basis(value: object) -> HeightBasis:
    if not isinstance(value, dict):
        raise ValueError("height_basis_invalid")
    kind = str(value.get("kind", ""))
    if kind == "brief constraint":
        if set(value) != {"kind"}:
            raise ValueError("height_basis_invalid")
        return HeightConstraintBasis()
    if kind == "height advice":
        if set(value) != {"advice_reference", "kind"}:
            raise ValueError("height_basis_invalid")
        return HeightAdviceBasis(Reference.from_mapping(value["advice_reference"]))
    raise ValueError("height_basis_invalid")
