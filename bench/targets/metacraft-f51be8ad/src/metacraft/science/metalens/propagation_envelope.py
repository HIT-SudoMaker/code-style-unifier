from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import ROUND_FLOOR, Decimal, localcontext

from ...authority import Document, Reference
from ...authority.reference import reference_matches
from .height import FabricationRange, HeightDomain
from .material import MaterialBinding


PHASE_ENVELOPE_SCHEMA = (
    "metacraft.science.metalens.propagation_phase.phase_envelope"
)


@dataclass(frozen=True, slots=True)
class OpticalContrast:
    """
    Carries admitted optical values needed by a propagation forecast.
    """

    atom_refractive_index: Decimal
    substrate_refractive_index: Decimal
    ambient_refractive_index: Decimal
    material_binding_reference: Reference
    material_sample_reference: Reference

    @classmethod
    def from_binding(cls, binding: MaterialBinding) -> OpticalContrast:
        """
        Build contrast only from one exact admitted material binding.
        """

        return cls(
            atom_refractive_index=binding.atom.refractive_index,
            substrate_refractive_index=(
                binding.substrate.refractive_index
            ),
            ambient_refractive_index=Decimal(1),
            material_binding_reference=binding.evidence_reference,
            material_sample_reference=binding.sample_reference,
        )


@dataclass(frozen=True, slots=True)
class EndpointCheck:
    """
    Certifies one named material-bound endpoint.
    """

    expected_endpoint: Decimal
    certified_interval: tuple[Decimal, Decimal]
    is_satisfied: bool
    is_certified: bool

    @property
    def is_supported(self) -> bool:
        """
        Require the certified interval to contain its finite endpoint.
        """

        lower, upper = self.certified_interval
        return (
            self.is_certified
            and self.is_satisfied
            and self.expected_endpoint.is_finite()
            and lower.is_finite()
            and upper.is_finite()
            and lower <= self.expected_endpoint <= upper
        )

    def as_mapping(self) -> dict[str, object]:
        """
        Return the endpoint and the interval that supports the check.
        """

        return {
            "certified": self.is_certified,
            "certified_interval": {
                "lower": format(self.certified_interval[0], "f"),
                "upper": format(self.certified_interval[1], "f"),
            },
            "expected_endpoint": format(self.expected_endpoint, "f"),
            "holds": self.is_satisfied,
        }


@dataclass(frozen=True, slots=True)
class OrderingCheck:
    """
    Certifies the narrowest floor-to-ceiling separation.
    """

    minimum_certified_separation: Decimal
    is_satisfied: bool
    is_certified: bool

    @property
    def is_supported(self) -> bool:
        """
        Require a finite, strictly positive certified separation.
        """

        return (
            self.is_certified
            and self.is_satisfied
            and self.minimum_certified_separation.is_finite()
            and self.minimum_certified_separation > 0
        )

    def as_mapping(self) -> dict[str, object]:
        """
        Return the separation that supports the ordering check.
        """

        return {
            "certified": self.is_certified,
            "holds": self.is_satisfied,
            "minimum_certified_separation": format(
                self.minimum_certified_separation,
                "f",
            ),
        }


@dataclass(frozen=True, slots=True)
class BoundChecks:
    """
    Records the global endpoint and ordering checks behind hard bounds.
    """

    ceiling_reaches_pillar: EndpointCheck
    floor_reaches_ambient: EndpointCheck
    floor_stays_below_ceiling: OrderingCheck

    @property
    def authorizes_bounded_exclusion(self) -> bool:
        """
        Require every named check to hold under certified arithmetic.
        """

        return all(
            check.is_supported
            for check in (
                self.ceiling_reaches_pillar,
                self.floor_reaches_ambient,
                self.floor_stays_below_ceiling,
            )
        )

    def as_mapping(self) -> dict[str, object]:
        """
        Return the evidence that authorizes bounded exclusions.
        """

        return {
            "ceiling_reaches_pillar": (
                self.ceiling_reaches_pillar.as_mapping()
            ),
            "floor_reaches_ambient": (
                self.floor_reaches_ambient.as_mapping()
            ),
            "floor_stays_below_ceiling": (
                self.floor_stays_below_ceiling.as_mapping()
            ),
        }


@dataclass(frozen=True, slots=True)
class EnvelopeGrid:
    """
    Retains one height's exact fabrication grid arithmetic.
    """

    minimum_feature_nm: int
    maximum_feature_nm: int
    dimension_step_nm: int
    candidate_count: int

    @classmethod
    def from_range(
        cls,
        value: FabricationRange,
        step_nm: int,
    ) -> EnvelopeGrid:
        """
        Copy one height-domain range without recomputing it.
        """

        return cls(
            minimum_feature_nm=value.minimum_feature_nm,
            maximum_feature_nm=value.maximum_feature_nm,
            dimension_step_nm=step_nm,
            candidate_count=value.candidate_count,
        )

    def as_mapping(self) -> dict[str, int]:
        """
        Return exact candidate-count inputs.
        """

        return {
            "candidate_count": self.candidate_count,
            "dimension_step_nm": self.dimension_step_nm,
            "maximum_feature_nm": self.maximum_feature_nm,
            "minimum_feature_nm": self.minimum_feature_nm,
        }


@dataclass(frozen=True, slots=True)
class QuantizationStanding:
    """
    Gives one quantization a one-way exclusion standing.
    """

    levels: int
    standing: str
    deciding_tier: str
    reason: str

    def as_mapping(self) -> dict[str, object]:
        """
        Return one compact, non-duplicated standing.
        """

        return {
            "deciding_tier": self.deciding_tier,
            "levels": self.levels,
            "reason": self.reason,
            "standing": self.standing,
        }


@dataclass(frozen=True, slots=True)
class BoundedReasoning:
    """
    Carries the material interval behind one height's hard ceiling.
    """

    floor_index_at_minimum_feature: Decimal
    ceiling_index_at_maximum_feature: Decimal
    ceiling_polarization: str
    rigorous_turns_ceiling: Decimal

    def as_mapping(self) -> dict[str, str]:
        """
        Return the one bounded argument without quantization duplication.
        """

        return {
            "ceiling_index_at_maximum_feature": format(
                self.ceiling_index_at_maximum_feature,
                "f",
            ),
            "ceiling_polarization": self.ceiling_polarization,
            "floor_index_at_minimum_feature": format(
                self.floor_index_at_minimum_feature,
                "f",
            ),
            "rigorous_turns_ceiling": format(
                self.rigorous_turns_ceiling,
                "f",
            ),
        }


@dataclass(frozen=True, slots=True)
class ModelSpan:
    """
    Reports one named, non-authorizing model span.
    """

    model: str
    minimum_turns: Decimal
    maximum_turns: Decimal

    def as_mapping(self) -> dict[str, str]:
        """
        Return this named forecast without implying a bound.
        """

        return {
            "maximum_turns": format(self.maximum_turns, "f"),
            "minimum_turns": format(self.minimum_turns, "f"),
            "model": self.model,
        }


@dataclass(frozen=True, slots=True)
class LevelBudget:
    """
    Reports one quantization's maximum adjacent phase step.
    """

    levels: int
    maximum_adjacent_step_turns: Decimal

    def as_mapping(self) -> dict[str, object]:
        """
        Return this level's exact dimensionless budget.
        """

        return {
            "levels": self.levels,
            "maximum_adjacent_step_turns": format(
                self.maximum_adjacent_step_turns,
                "f",
            ),
        }


@dataclass(frozen=True, slots=True)
class PhaseForecast:
    """
    Keeps model estimates separate from every exclusion standing.
    """

    model_spans: tuple[ModelSpan, ...]
    steepest_adjacent_step_turns: Decimal | None
    level_budgets: tuple[LevelBudget, ...]
    annotation: str

    def as_mapping(self) -> dict[str, object]:
        """
        Omit an adjacent step when no model established one.
        """

        values: dict[str, object] = {
            "annotation": self.annotation,
            "level_budgets": [
                budget.as_mapping() for budget in self.level_budgets
            ],
            "model_spans": [
                span.as_mapping() for span in self.model_spans
            ],
        }
        if self.steepest_adjacent_step_turns is not None:
            values["steepest_adjacent_step_turns"] = format(
                self.steepest_adjacent_step_turns,
                "f",
            )
        return values


@dataclass(frozen=True, slots=True)
class Applicability:
    """
    Reports how much of the grid lies beyond the isolated-mode model.
    """

    single_mode_cutoff_diameter_nm: Decimal
    affected_candidate_count: int
    affected_candidate_fraction: Decimal

    def as_mapping(self) -> dict[str, object]:
        """
        Keep an empty affected set as an explicit applicability fact.
        """

        return {
            "affected_candidate_count": self.affected_candidate_count,
            "affected_candidate_fraction": format(
                self.affected_candidate_fraction,
                "f",
            ),
            "single_mode_cutoff_diameter_nm": format(
                self.single_mode_cutoff_diameter_nm,
                "f",
            ),
        }


@dataclass(frozen=True, slots=True)
class HeightReach:
    """
    Reports bounds, forecast, and standings for one candidate height.
    """

    height_nm: int
    grid: EnvelopeGrid
    bounded_reasoning: BoundedReasoning
    forecast: PhaseForecast
    applicability: Applicability
    standings: tuple[QuantizationStanding, ...]

    def as_mapping(self) -> dict[str, object]:
        """
        Return facts, bounds, forecast, then standings.
        """

        return {
            "applicability": self.applicability.as_mapping(),
            "bounded_reasoning": self.bounded_reasoning.as_mapping(),
            "forecast": self.forecast.as_mapping(),
            "grid": self.grid.as_mapping(),
            "height_nm": self.height_nm,
            "standings": [
                standing.as_mapping() for standing in self.standings
            ],
        }


@dataclass(frozen=True, slots=True)
class PhaseEnvelope:
    """
    Holds one zero-solver, one-way propagation-phase forecast.
    """

    brief_identity: str
    wavelength_nm: int
    height_domain_reference: Reference | None
    material_binding_reference: Reference
    material_sample_reference: Reference
    bound_checks: BoundChecks
    reaches: tuple[HeightReach, ...]
    evidence_reference: Reference | None = None

    def __post_init__(self) -> None:
        """
        Keep bounded standings behind their complete certified support.
        """

        if (
            not self.bound_checks.authorizes_bounded_exclusion
            and any(
                standing.deciding_tier == "bounded"
                for reach in self.reaches
                for standing in reach.standings
            )
        ):
            raise ValueError(
                "phase_envelope_uncertified_bounded_exclusion"
            )

    @property
    def source_references(self) -> tuple[Reference, ...]:
        """
        Return the exact sources in their natural evidence order.
        """

        return tuple(
            reference
            for reference in (
                self.height_domain_reference,
                self.material_binding_reference,
                self.material_sample_reference,
            )
            if reference is not None
        )

    def reach_for(self, height_nm: int) -> HeightReach:
        """
        Return the one reach entry for a declared height.
        """

        matches = tuple(
            reach
            for reach in self.reaches
            if reach.height_nm == height_nm
        )
        if len(matches) != 1:
            raise ValueError("phase_envelope_height_missing")
        return matches[0]

    def document(self) -> Document:
        """
        Rebuild this exact propagation-envelope document.
        """

        return Document(
            PHASE_ENVELOPE_SCHEMA,
            {
                "bound_checks": self.bound_checks.as_mapping(),
                "brief_identity": self.brief_identity,
                "reaches": [
                    reach.as_mapping() for reach in self.reaches
                ],
                "source_references": {
                    **(
                        {}
                        if self.height_domain_reference is None
                        else {
                            "height_domain": (
                                self.height_domain_reference.as_mapping()
                            )
                        }
                    ),
                    "material_binding": (
                        self.material_binding_reference.as_mapping()
                    ),
                    "material_sample": (
                        self.material_sample_reference.as_mapping()
                    ),
                },
                "wavelength_nm": self.wavelength_nm,
            },
        )

    def admitted(self, reference: Reference) -> PhaseEnvelope:
        """
        Bind this exact envelope to its admitted Authority reference.
        """

        if not reference_matches(reference, self.document().to_bytes()):
            raise ValueError("phase_envelope_reference_mismatch")
        return replace(self, evidence_reference=reference)

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        evidence_reference: Reference,
    ) -> PhaseEnvelope:
        """
        Restore one exact admitted envelope.
        """

        if document.schema_identifier != PHASE_ENVELOPE_SCHEMA:
            raise ValueError("phase_envelope_schema_mismatch")
        values = document.values
        checks = values["bound_checks"]
        reaches = values["reaches"]
        references = values["source_references"]
        if (
            not isinstance(checks, dict)
            or not isinstance(reaches, list)
            or not isinstance(references, dict)
        ):
            raise ValueError("phase_envelope_shape_invalid")
        envelope = cls(
            brief_identity=str(values["brief_identity"]),
            wavelength_nm=int(values["wavelength_nm"]),
            height_domain_reference=(
                None
                if "height_domain" not in references
                else Reference.from_mapping(
                    references["height_domain"]
                )
            ),
            material_binding_reference=Reference.from_mapping(
                references["material_binding"]
            ),
            material_sample_reference=Reference.from_mapping(
                references["material_sample"]
            ),
            bound_checks=_bound_checks(checks),
            reaches=tuple(_height_reach(reach) for reach in reaches),
            evidence_reference=evidence_reference,
        )
        if not reference_matches(
            evidence_reference,
            envelope.document().to_bytes(),
        ):
            raise ValueError("phase_envelope_reference_mismatch")
        return envelope


def estimate_phase_envelope(
    domain: HeightDomain,
    contrast: OpticalContrast,
) -> PhaseEnvelope:
    """
    Forecast phase reach without starting any external process.
    """

    if contrast.material_binding_reference != (
        domain.material_binding_reference
    ):
        raise ValueError("optical_contrast_binding_mismatch")
    if contrast.material_sample_reference != (
        domain.material_sample_reference
    ):
        raise ValueError("optical_contrast_sample_mismatch")
    separation = (
        contrast.atom_refractive_index
        - contrast.ambient_refractive_index
    )
    checks = BoundChecks(
        ceiling_reaches_pillar=EndpointCheck(
            expected_endpoint=contrast.atom_refractive_index,
            certified_interval=(
                contrast.atom_refractive_index,
                contrast.atom_refractive_index,
            ),
            is_satisfied=True,
            is_certified=True,
        ),
        floor_reaches_ambient=EndpointCheck(
            expected_endpoint=contrast.ambient_refractive_index,
            certified_interval=(
                contrast.ambient_refractive_index,
                contrast.ambient_refractive_index,
            ),
            is_satisfied=True,
            is_certified=True,
        ),
        floor_stays_below_ceiling=OrderingCheck(
            minimum_certified_separation=separation,
            is_satisfied=separation > 0,
            is_certified=True,
        ),
    )
    reaches = tuple(
        _estimate_height(
            domain,
            contrast,
            fabrication,
            checks=checks,
        )
        for fabrication in domain.fabrication_ranges
    )
    return PhaseEnvelope(
        brief_identity=domain.brief_identity,
        wavelength_nm=domain.wavelength_nm,
        height_domain_reference=domain.evidence_reference,
        material_binding_reference=domain.material_binding_reference,
        material_sample_reference=domain.material_sample_reference,
        bound_checks=checks,
        reaches=reaches,
    )


def _estimate_height(
    domain: HeightDomain,
    contrast: OpticalContrast,
    fabrication: FabricationRange,
    *,
    checks: BoundChecks,
) -> HeightReach:
    floor_index = contrast.ambient_refractive_index
    ceiling_index = contrast.atom_refractive_index
    with localcontext() as context:
        context.prec = 28
        rigorous_turns_ceiling = (
            Decimal(fabrication.height_nm)
            * (ceiling_index - floor_index)
            / Decimal(domain.wavelength_nm)
        )
        standings = tuple(
            _standing(
                levels,
                candidate_count=fabrication.candidate_count,
                rigorous_turns_ceiling=rigorous_turns_ceiling,
                is_certified=checks.authorizes_bounded_exclusion,
            )
            for levels in (8, 12, 16)
        )
        level_budgets = tuple(
            LevelBudget(
                levels=levels,
                maximum_adjacent_step_turns=(
                    Decimal(1) / Decimal(levels)
                ),
            )
            for levels in (8, 12, 16)
        )
    cutoff_diameter = _single_mode_cutoff_diameter(
        wavelength_nm=domain.wavelength_nm,
        pillar_index=contrast.atom_refractive_index,
        ambient_index=contrast.ambient_refractive_index,
    )
    affected_count = sum(
        Decimal(feature_nm) >= cutoff_diameter
        for feature_nm in range(
            fabrication.minimum_feature_nm,
            fabrication.maximum_feature_nm + 1,
            domain.dimension_step_nm,
        )
    )
    with localcontext() as context:
        context.prec = 28
        affected_fraction = (
            Decimal(0)
            if fabrication.candidate_count == 0
            else Decimal(affected_count)
            / Decimal(fabrication.candidate_count)
        )
    return HeightReach(
        height_nm=fabrication.height_nm,
        grid=EnvelopeGrid.from_range(
            fabrication,
            domain.dimension_step_nm,
        ),
        bounded_reasoning=BoundedReasoning(
            floor_index_at_minimum_feature=floor_index,
            ceiling_index_at_maximum_feature=ceiling_index,
            ceiling_polarization="polarization independent",
            rigorous_turns_ceiling=rigorous_turns_ceiling,
        ),
        forecast=PhaseForecast(
            model_spans=(),
            steepest_adjacent_step_turns=None,
            level_budgets=level_budgets,
            annotation="forecast insufficient",
        ),
        applicability=Applicability(
            single_mode_cutoff_diameter_nm=cutoff_diameter,
            affected_candidate_count=affected_count,
            affected_candidate_fraction=affected_fraction,
        ),
        standings=standings,
    )


def _standing(
    levels: int,
    *,
    candidate_count: int,
    rigorous_turns_ceiling: Decimal,
    is_certified: bool,
) -> QuantizationStanding:
    if candidate_count < levels:
        return QuantizationStanding(
            levels,
            "ruled out",
            "arithmetic",
            f"{candidate_count} candidates cannot fill {levels} levels",
        )
    required_turns = Decimal(levels - 1) / Decimal(levels)
    if is_certified and rigorous_turns_ceiling < required_turns:
        return QuantizationStanding(
            levels,
            "ruled out",
            "bounded",
            "certified phase-span ceiling is short of the level span",
        )
    return QuantizationStanding(
        levels,
        "not ruled out",
        "none",
        "no hard exclusion applies",
    )


def _height_reach(value: object) -> HeightReach:
    if not isinstance(value, dict):
        raise ValueError("phase_envelope_reach_invalid")
    grid = value["grid"]
    bounded = value["bounded_reasoning"]
    forecast = value["forecast"]
    standings = value["standings"]
    applicability = value["applicability"]
    if (
        not isinstance(grid, dict)
        or not isinstance(bounded, dict)
        or not isinstance(forecast, dict)
        or not isinstance(standings, list)
        or not isinstance(applicability, dict)
    ):
        raise ValueError("phase_envelope_reach_invalid")
    return HeightReach(
        height_nm=int(value["height_nm"]),
        grid=EnvelopeGrid(
            minimum_feature_nm=int(grid["minimum_feature_nm"]),
            maximum_feature_nm=int(grid["maximum_feature_nm"]),
            dimension_step_nm=int(grid["dimension_step_nm"]),
            candidate_count=int(grid["candidate_count"]),
        ),
        bounded_reasoning=BoundedReasoning(
            floor_index_at_minimum_feature=Decimal(
                str(bounded["floor_index_at_minimum_feature"])
            ),
            ceiling_index_at_maximum_feature=Decimal(
                str(bounded["ceiling_index_at_maximum_feature"])
            ),
            ceiling_polarization=str(
                bounded["ceiling_polarization"]
            ),
            rigorous_turns_ceiling=Decimal(
                str(bounded["rigorous_turns_ceiling"])
            ),
        ),
        forecast=_phase_forecast(forecast),
        applicability=Applicability(
            single_mode_cutoff_diameter_nm=Decimal(
                str(applicability["single_mode_cutoff_diameter_nm"])
            ),
            affected_candidate_count=int(
                applicability["affected_candidate_count"]
            ),
            affected_candidate_fraction=Decimal(
                str(applicability["affected_candidate_fraction"])
            ),
        ),
        standings=tuple(
            QuantizationStanding(
                levels=int(standing["levels"]),
                standing=str(standing["standing"]),
                deciding_tier=str(standing["deciding_tier"]),
                reason=str(standing["reason"]),
            )
            for standing in standings
        ),
    )


def _phase_forecast(value: dict[object, object]) -> PhaseForecast:
    model_spans = value["model_spans"]
    level_budgets = value["level_budgets"]
    if not isinstance(model_spans, list) or not isinstance(
        level_budgets,
        list,
    ):
        raise ValueError("phase_envelope_forecast_invalid")
    adjacent_step = value.get("steepest_adjacent_step_turns")
    return PhaseForecast(
        model_spans=tuple(_model_span(span) for span in model_spans),
        steepest_adjacent_step_turns=(
            None
            if adjacent_step is None
            else Decimal(str(adjacent_step))
        ),
        level_budgets=tuple(
            _level_budget(budget) for budget in level_budgets
        ),
        annotation=str(value["annotation"]),
    )


def _model_span(value: object) -> ModelSpan:
    if not isinstance(value, dict):
        raise ValueError("phase_envelope_model_span_invalid")
    return ModelSpan(
        model=str(value["model"]),
        minimum_turns=Decimal(str(value["minimum_turns"])),
        maximum_turns=Decimal(str(value["maximum_turns"])),
    )


def _level_budget(value: object) -> LevelBudget:
    if not isinstance(value, dict):
        raise ValueError("phase_envelope_level_budget_invalid")
    return LevelBudget(
        levels=int(value["levels"]),
        maximum_adjacent_step_turns=Decimal(
            str(value["maximum_adjacent_step_turns"])
        ),
    )


def _single_mode_cutoff_diameter(
    *,
    wavelength_nm: int,
    pillar_index: Decimal,
    ambient_index: Decimal,
) -> Decimal:
    contrast = pillar_index * pillar_index - ambient_index * ambient_index
    if contrast <= 0:
        raise ValueError("phase_envelope_optical_contrast_invalid")
    with localcontext() as context:
        context.prec = 50
        cutoff = (
            Decimal("2.404825557695772768621631879")
            * Decimal(wavelength_nm)
            / (
                Decimal(
                    "3.1415926535897932384626433832795028841971693993751"
                )
                * contrast.sqrt()
            )
        )
        return cutoff.quantize(
            Decimal("0.000001"),
            rounding=ROUND_FLOOR,
        )


def _bound_checks(value: dict[object, object]) -> BoundChecks:
    ceiling = value["ceiling_reaches_pillar"]
    floor = value["floor_reaches_ambient"]
    ordering = value["floor_stays_below_ceiling"]
    if (
        not isinstance(ceiling, dict)
        or not isinstance(floor, dict)
        or not isinstance(ordering, dict)
    ):
        raise ValueError("phase_envelope_bound_checks_invalid")
    return BoundChecks(
        ceiling_reaches_pillar=_endpoint_check(ceiling),
        floor_reaches_ambient=_endpoint_check(floor),
        floor_stays_below_ceiling=OrderingCheck(
            minimum_certified_separation=Decimal(
                str(ordering["minimum_certified_separation"])
            ),
            is_satisfied=bool(ordering["holds"]),
            is_certified=bool(ordering["certified"]),
        ),
    )


def _endpoint_check(value: dict[object, object]) -> EndpointCheck:
    interval = value["certified_interval"]
    if not isinstance(interval, dict):
        raise ValueError("phase_envelope_bound_check_invalid")
    return EndpointCheck(
        expected_endpoint=Decimal(str(value["expected_endpoint"])),
        certified_interval=(
            Decimal(str(interval["lower"])),
            Decimal(str(interval["upper"])),
        ),
        is_satisfied=bool(value["holds"]),
        is_certified=bool(value["certified"]),
    )
