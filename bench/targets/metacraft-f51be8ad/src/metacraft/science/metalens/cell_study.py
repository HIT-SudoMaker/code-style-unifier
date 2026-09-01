from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import hashlib

from ...authority.protocol import Document, Reference
from ...authority.reference import reference_matches
from ...canonical import encode_bytes
from ..consultation import (
    CONSULTATION_ANSWER_SCHEMA,
    ConsultationAnswer,
    ConsultationGround,
    EvidenceRequired,
    ExternalClaim,
    GroundKind,
    Recommendation,
    ResearchMode,
)
from .aperture import Circle, Ellipse, Geometry, Rectangle, Square
from .height import HeightChoice, HeightDomain

__all__ = [
    "CellInputBasis",
    "CellResponseChannel",
    "CellResponseWork",
    "CellStudy",
    "CellStudyConsultation",
    "CellStudyConsultationResult",
    "CellStudyEvidenceRequirement",
    "CellStudyFormationError",
    "CellStudyOption",
    "CellStudyPlan",
    "CellStudyRoute",
    "InvalidCellStudyAnswer",
    "LocalPbCellStudy",
    "PropagationCellStudy",
    "accept_cell_study_answer",
    "form_cell_study_consultation",
]


CELL_STUDY_CONSULTATION_SCHEMA = "metacraft.science.metalens.cell_study_consultation"
CELL_STUDY_PLAN_SCHEMA = "metacraft.science.metalens.cell_study_plan"
CELL_STUDY_PROMPT = (
    "Choose one existing option_id as a conservative first study. "
    "Do not alter values, constraints, or work extent. Use forecasts only "
    "to rank. If local grounds are insufficient, research primary or "
    "official sources and cite consequential claims. Otherwise return "
    "evidence_required. Solver evidence comes later."
)


class CellStudyRoute(str, Enum):
    """
    Name the two local-response studies accepted by this Module.
    """

    PROPAGATION_PHASE = "propagation_phase"
    LOCAL_PB = "local_pb"


class CellInputBasis(str, Enum):
    """
    Name one unrotated linear input used by a periodic response task.
    """

    X_LINEAR = "x_linear"
    Y_LINEAR = "y_linear"


class CellResponseChannel(str, Enum):
    """
    Name one complex response quantity requested from a solver task.
    """

    COMPLEX_TRANSMISSION = "complex_transmission"
    JONES_XX = "jones_xx"
    JONES_YX = "jones_yx"
    JONES_XY = "jones_xy"
    JONES_YY = "jones_yy"


_PROPAGATION_CHANNELS = (CellResponseChannel.COMPLEX_TRANSMISSION,)
_PB_X_CHANNELS = (
    CellResponseChannel.JONES_XX,
    CellResponseChannel.JONES_YX,
)
_PB_Y_CHANNELS = (
    CellResponseChannel.JONES_XY,
    CellResponseChannel.JONES_YY,
)
_PB_CHANNELS = (*_PB_X_CHANNELS, *_PB_Y_CHANNELS)


class CellStudyFormationError(ValueError):
    """
    Report an invalid planning input without impersonating consultation.
    """

    def __init__(self, reason: str) -> None:
        """
        Retain the exact invalid planning reason.
        """
        self.reason = reason
        super().__init__(reason)


class InvalidCellStudyAnswer(ValueError):
    """
    Report why one harness answer cannot close its cited consultation.
    """

    def __init__(self, reason: str) -> None:
        """
        Retain the exact invalid answer reason.
        """
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True, kw_only=True)
class CellResponseWork:
    """
    Describe one exact, orientation-free periodic response task.
    """

    route: CellStudyRoute
    geometry: Geometry
    input_basis: CellInputBasis
    response_channels: tuple[CellResponseChannel, ...]

    def __post_init__(self) -> None:
        """
        Require one route-consistent geometry, basis, and response set.
        """
        if not isinstance(self.route, CellStudyRoute) or not isinstance(
            self.input_basis,
            CellInputBasis,
        ):
            raise ValueError("cell_response_work_invalid")
        if self.route is CellStudyRoute.PROPAGATION_PHASE:
            is_valid = (
                isinstance(self.geometry, (Circle, Square))
                and self.response_channels == _PROPAGATION_CHANNELS
            )
        else:
            expected_channels = (
                _PB_X_CHANNELS
                if self.input_basis is CellInputBasis.X_LINEAR
                else _PB_Y_CHANNELS
            )
            is_valid = (
                isinstance(self.geometry, (Rectangle, Ellipse))
                and self.response_channels == expected_channels
            )
        if not is_valid:
            raise ValueError("cell_response_work_invalid")

    @property
    def identity(self) -> str:
        """
        Return the content identity of this complete solver obligation.
        """

        return _identity(self._identity_value())

    def as_mapping(self) -> dict[str, object]:
        """
        Encode this work with no implicit geometry or response channel.
        """

        return {"identity": self.identity, **self._identity_value()}

    def canonical_bytes(self) -> bytes:
        """
        Encode this work deterministically for harness hand-off.
        """

        return encode_bytes(self.as_mapping())

    def _identity_value(self) -> dict[str, object]:
        return {
            "geometry": _geometry_value(self.geometry),
            "input_basis": self.input_basis.value,
            "response_channels": [channel.value for channel in self.response_channels],
            "route": self.route.value,
        }

    @classmethod
    def from_mapping(cls, value: object) -> CellResponseWork:
        """
        Restore only an exact work mapping with a valid content identity.
        """

        values = _closed_mapping(
            value,
            {
                "geometry",
                "identity",
                "input_basis",
                "response_channels",
                "route",
            },
            "cell_response_work_invalid",
        )
        try:
            work = cls(
                route=CellStudyRoute(_text(values["route"])),
                geometry=_geometry_from_mapping(values["geometry"]),
                input_basis=CellInputBasis(_text(values["input_basis"])),
                response_channels=tuple(
                    CellResponseChannel(_text(channel))
                    for channel in _sequence(values["response_channels"])
                ),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("cell_response_work_invalid") from error
        if values["identity"] != work.identity:
            raise ValueError("cell_response_work_invalid")
        return work


@dataclass(frozen=True, slots=True, kw_only=True)
class PropagationCellStudy:
    """
    Own one scalar-transmission study over isotropic geometries.
    """

    work: tuple[CellResponseWork, ...]

    def __post_init__(self) -> None:
        """
        Require unique propagation-response work.
        """
        if not self.work or any(
            item.route is not CellStudyRoute.PROPAGATION_PHASE for item in self.work
        ):
            raise ValueError("propagation_cell_study_invalid")
        _require_unique(tuple(item.identity for item in self.work))

    @property
    def route(self) -> CellStudyRoute:
        """
        Return the closed route owned by this study variant.
        """

        return CellStudyRoute.PROPAGATION_PHASE

    @classmethod
    def from_geometries(
        cls,
        geometries: tuple[Circle | Square, ...],
        *,
        input_basis: CellInputBasis,
    ) -> PropagationCellStudy:
        """
        Expand each isotropic geometry into exactly one response task.
        """

        return cls(
            work=tuple(
                CellResponseWork(
                    route=CellStudyRoute.PROPAGATION_PHASE,
                    geometry=geometry,
                    input_basis=input_basis,
                    response_channels=_PROPAGATION_CHANNELS,
                )
                for geometry in geometries
            )
        )

    @property
    def response_channels(self) -> tuple[CellResponseChannel, ...]:
        """
        Return the one scalar transmission channel required per work.
        """

        return _PROPAGATION_CHANNELS

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the propagation route and its exact work items.
        """

        return {
            "route": CellStudyRoute.PROPAGATION_PHASE.value,
            "work": [item.as_mapping() for item in self.work],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LocalPbCellStudy:
    """
    Own the x/y Jones study of unrotated anisotropic geometries.
    """

    work: tuple[CellResponseWork, ...]

    def __post_init__(self) -> None:
        """
        Require paired Jones work for each unique anisotropic geometry.
        """
        if not self.work or any(
            item.route is not CellStudyRoute.LOCAL_PB for item in self.work
        ):
            raise ValueError("local_pb_cell_study_invalid")
        geometries = []
        for index in range(0, len(self.work), 2):
            geometry = self.work[index].geometry
            if not isinstance(geometry, (Rectangle, Ellipse)):
                raise ValueError("local_pb_cell_study_invalid")
            geometries.append(geometry)
        expected = _local_basis_work_from_geometries(tuple(geometries))
        if self.work != expected:
            raise ValueError("local_pb_cell_study_invalid")
        _require_unique(tuple(item.identity for item in self.work))

    @property
    def route(self) -> CellStudyRoute:
        """
        Return the closed route owned by this study variant.
        """

        return CellStudyRoute.LOCAL_PB

    @classmethod
    def from_geometries(
        cls,
        geometries: tuple[Rectangle | Ellipse, ...],
    ) -> LocalPbCellStudy:
        """
        Expand each unrotated geometry into its exact x/y Jones pair.
        """

        return cls(work=_local_basis_work_from_geometries(geometries))

    @property
    def response_channels(self) -> tuple[CellResponseChannel, ...]:
        """
        Return the complete x/y Jones channel vocabulary.
        """

        return _PB_CHANNELS

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the PB route and its exact unrotated work items.
        """

        return {
            "route": CellStudyRoute.LOCAL_PB.value,
            "work": [item.as_mapping() for item in self.work],
        }


CellStudy = PropagationCellStudy | LocalPbCellStudy


@dataclass(frozen=True, slots=True, kw_only=True)
class CellStudyOption:
    """
    Offer one height and one exact bounded local-response study.
    """

    height_nm: int
    study: CellStudy
    cautions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """
        Require one positive height and one supported study.
        """
        if self.height_nm <= 0 or not isinstance(
            self.study,
            (PropagationCellStudy, LocalPbCellStudy),
        ):
            raise ValueError("cell_study_option_invalid")
        _require_text_tuple(self.cautions, "cell_study_option_invalid")

    @property
    def identity(self) -> str:
        """
        Return the content identity of this exact offered option.
        """

        return _identity(self._identity_value())

    @property
    def work(self) -> tuple[CellResponseWork, ...]:
        """
        Return every periodic task owned by this option.
        """

        return self.study.work

    @property
    def response_channels(self) -> tuple[CellResponseChannel, ...]:
        """
        Return the response channels owned by the route variant.
        """

        return self.study.response_channels

    @property
    def response_requirement(self) -> str:
        """
        Describe the measured response obligation for this option.
        """

        if isinstance(self.study, PropagationCellStudy):
            return "complex periodic transmission"
        return "complete x/y Jones response with an explicit qualification profile"

    @property
    def work_count(self) -> int:
        """
        Return the exact number of periodic tasks in this option.
        """

        return len(self.work)

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the exact work, channels, and count owned by this option.
        """

        return {"identity": self.identity, **self._identity_value()}

    def canonical_bytes(self) -> bytes:
        """
        Return deterministic bytes for option identity and replay.
        """

        return encode_bytes(self.as_mapping())

    def _identity_value(self) -> dict[str, object]:
        return {
            "cautions": list(self.cautions),
            "height_nm": self.height_nm,
            "response_channels": [channel.value for channel in self.response_channels],
            "response_requirement": self.response_requirement,
            "study": self.study.as_mapping(),
            "work_count": self.work_count,
        }

    @classmethod
    def from_mapping(cls, value: object) -> CellStudyOption:
        """
        Restore one option and recheck all derived work ownership.
        """

        values = _closed_mapping(
            value,
            {
                "cautions",
                "height_nm",
                "identity",
                "response_channels",
                "response_requirement",
                "study",
                "work_count",
            },
            "cell_study_option_invalid",
        )
        try:
            option = cls(
                height_nm=_integer(values["height_nm"]),
                study=_study_from_mapping(values["study"]),
                cautions=tuple(_text(item) for item in _sequence(values["cautions"])),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("cell_study_option_invalid") from error
        if (
            values["identity"] != option.identity
            or values["work_count"] != option.work_count
            or list(_sequence(values["response_channels"]))
            != [channel.value for channel in option.response_channels]
            or values["response_requirement"] != option.response_requirement
        ):
            raise ValueError("cell_study_option_invalid")
        return option


@dataclass(frozen=True, slots=True, kw_only=True)
class CellStudyConsultation:
    """
    Present bounded cell-study options through one harness seam.
    """

    brief_identity: str
    height_choice_reference: Reference
    period_choice_content_hash: str
    wavelength_nm: int
    period_nm: int
    maximum_periodic_solver_tasks: int
    research_mode: ResearchMode
    grounds: tuple[ConsultationGround, ...]
    options: tuple[CellStudyOption, ...]
    exclusions: tuple[str, ...]
    cautions: tuple[str, ...]
    order_regime: str = "zeroth order"

    def __post_init__(self) -> None:
        """
        Require complete, bounded, and identity-stable consultation facts.
        """
        if (
            not self.brief_identity
            or not self.period_choice_content_hash
            or self.wavelength_nm <= 0
            or self.period_nm <= 0
            or self.order_regime not in {"zeroth order", "multi order"}
            or self.maximum_periodic_solver_tasks <= 0
            or not isinstance(self.research_mode, ResearchMode)
            or not self.grounds
            or not self.options
        ):
            raise ValueError("cell_study_consultation_invalid")
        _require_unique(tuple(ground.identity for ground in self.grounds))
        _require_unique(tuple(option.identity for option in self.options))
        _require_text_tuple(self.exclusions, "cell_study_consultation_invalid")
        _require_text_tuple(self.cautions, "cell_study_consultation_invalid")

    @property
    def identity(self) -> str:
        """
        Return the content identity of this consultation card.
        """

        return _identity(self._identity_value())

    @property
    def prompt(self) -> str:
        """
        Return the provider-free harness instruction for this card.
        """

        return CELL_STUDY_PROMPT

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the closed card with options, grounds, and contract.
        """

        return {
            "identity": self.identity,
            "schema_identifier": CELL_STUDY_CONSULTATION_SCHEMA,
            **self._identity_value(),
        }

    def canonical_bytes(self) -> bytes:
        """
        Return deterministic bytes for harness transfer and replay.
        """

        return encode_bytes(self.as_mapping())

    def document(self) -> Document:
        """
        Wrap the card as its exact Authority document.
        """

        return Document(CELL_STUDY_CONSULTATION_SCHEMA, self.as_mapping())

    @classmethod
    def from_document(cls, document: Document) -> "CellStudyConsultation":
        """
        Restore one canonical cell-study consultation.
        """
        if document.schema_identifier != CELL_STUDY_CONSULTATION_SCHEMA:
            raise ValueError("cell_study_consultation_schema_invalid")
        values = _closed_mapping(
            document.values,
            {
                "answer_contract",
                "brief_identity",
                "cautions",
                "exclusions",
                "grounds",
                "height_choice_reference",
                "identity",
                "maximum_periodic_solver_tasks",
                "options",
                "order_regime",
                "period_choice_content_hash",
                "period_nm",
                "prompt",
                "research_mode",
                "schema_identifier",
                "wavelength_nm",
            },
            "cell_study_consultation_document_invalid",
        )
        if values["schema_identifier"] != CELL_STUDY_CONSULTATION_SCHEMA:
            raise ValueError("cell_study_consultation_schema_invalid")
        if values["prompt"] != CELL_STUDY_PROMPT:
            raise ValueError("cell_study_consultation_prompt_invalid")
        try:
            request = cls(
                brief_identity=_text(values["brief_identity"]),
                height_choice_reference=_reference(
                    values["height_choice_reference"]
                ),
                period_choice_content_hash=_text(values["period_choice_content_hash"]),
                wavelength_nm=_integer(values["wavelength_nm"]),
                period_nm=_integer(values["period_nm"]),
                maximum_periodic_solver_tasks=_integer(
                    values["maximum_periodic_solver_tasks"]
                ),
                research_mode=ResearchMode(_text(values["research_mode"])),
                grounds=tuple(
                    ConsultationGround.from_mapping(item)
                    for item in _sequence(values["grounds"])
                ),
                options=tuple(
                    CellStudyOption.from_mapping(item)
                    for item in _sequence(values["options"])
                ),
                exclusions=tuple(
                    _text(item) for item in _sequence(values["exclusions"])
                ),
                cautions=tuple(_text(item) for item in _sequence(values["cautions"])),
                order_regime=_text(values["order_regime"]),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("cell_study_consultation_document_invalid") from error
        if (
            request.identity != values["identity"]
            or request.document().to_bytes() != document.to_bytes()
        ):
            raise ValueError("cell_study_consultation_document_mismatch")
        return request

    def _identity_value(self) -> dict[str, object]:
        return {
            "answer_contract": _answer_contract(),
            "brief_identity": self.brief_identity,
            "cautions": list(self.cautions),
            "exclusions": list(self.exclusions),
            "grounds": [ground.as_mapping() for ground in self.grounds],
            "height_choice_reference": self.height_choice_reference.as_mapping(),
            "maximum_periodic_solver_tasks": (self.maximum_periodic_solver_tasks),
            "options": [option.as_mapping() for option in self.options],
            "order_regime": self.order_regime,
            "period_choice_content_hash": self.period_choice_content_hash,
            "period_nm": self.period_nm,
            "prompt": CELL_STUDY_PROMPT,
            "research_mode": self.research_mode.value,
            "wavelength_nm": self.wavelength_nm,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class CellStudyPlan:
    """
    Close one selected option as exact work, not as a solver execution.
    """

    request_identity: str
    option_identity: str
    brief_identity: str
    height_choice_reference: Reference
    period_choice_content_hash: str
    period_nm: int
    height_nm: int
    study: CellStudy
    work: tuple[CellResponseWork, ...]
    response_channels: tuple[CellResponseChannel, ...]
    work_count: int
    reason: str
    decisive_ground_identities: tuple[str, ...]
    external_claims: tuple[ExternalClaim, ...]
    order_regime: str = "zeroth order"

    def __post_init__(self) -> None:
        """
        Require one answer-linked plan selected from its consultation.
        """
        if (
            not self.request_identity
            or not self.option_identity
            or not self.brief_identity
            or not self.period_choice_content_hash
            or self.period_nm <= 0
            or self.height_nm <= 0
            or self.work != self.study.work
            or self.response_channels != self.study.response_channels
            or self.work_count != len(self.work)
            or not self.reason.strip()
            or not self.decisive_ground_identities
            or self.order_regime not in {"zeroth order", "multi order"}
        ):
            raise ValueError("cell_study_plan_invalid")
        _require_unique(self.decisive_ground_identities)
        _require_unique(tuple(claim.identity for claim in self.external_claims))

    def as_mapping(self) -> dict[str, object]:
        """
        Encode every work item and response channel selected by the plan.
        """

        return {
            "brief_identity": self.brief_identity,
            "decisive_ground_identities": list(self.decisive_ground_identities),
            "external_claims": [claim.as_mapping() for claim in self.external_claims],
            "height_choice_reference": self.height_choice_reference.as_mapping(),
            "height_nm": self.height_nm,
            "option_identity": self.option_identity,
            "order_regime": self.order_regime,
            "period_choice_content_hash": self.period_choice_content_hash,
            "period_nm": self.period_nm,
            "reason": self.reason,
            "request_identity": self.request_identity,
            "response_channels": [channel.value for channel in self.response_channels],
            "schema_identifier": CELL_STUDY_PLAN_SCHEMA,
            "study": self.study.as_mapping(),
            "work": [item.as_mapping() for item in self.work],
            "work_count": self.work_count,
        }

    def canonical_bytes(self) -> bytes:
        """
        Return deterministic bytes for plan transfer and replay.
        """

        return encode_bytes(self.as_mapping())

    def document(self) -> Document:
        """
        Wrap the exact plan as its Authority document.
        """

        return Document(CELL_STUDY_PLAN_SCHEMA, self.as_mapping())

    @classmethod
    def from_document(cls, document: Document) -> "CellStudyPlan":
        """
        Restore one canonical cell-study plan.
        """
        if document.schema_identifier != CELL_STUDY_PLAN_SCHEMA:
            raise ValueError("cell_study_plan_schema_invalid")
        try:
            return cls.from_mapping(document.values)
        except ValueError as error:
            raise ValueError("cell_study_plan_document_invalid") from error

    @classmethod
    def from_mapping(cls, value: object) -> CellStudyPlan:
        """
        Restore one plan only when all denormalized work remains exact.
        """

        values = _closed_mapping(
            value,
            {
                "brief_identity",
                "decisive_ground_identities",
                "external_claims",
                "height_choice_reference",
                "height_nm",
                "option_identity",
                "order_regime",
                "period_choice_content_hash",
                "period_nm",
                "reason",
                "request_identity",
                "response_channels",
                "schema_identifier",
                "study",
                "work",
                "work_count",
            },
            "cell_study_plan_invalid",
        )
        if values["schema_identifier"] != CELL_STUDY_PLAN_SCHEMA:
            raise ValueError("cell_study_plan_invalid")
        try:
            return cls(
                request_identity=_text(values["request_identity"]),
                option_identity=_text(values["option_identity"]),
                brief_identity=_text(values["brief_identity"]),
                height_choice_reference=_reference(
                    values["height_choice_reference"]
                ),
                period_choice_content_hash=_text(values["period_choice_content_hash"]),
                period_nm=_integer(values["period_nm"]),
                height_nm=_integer(values["height_nm"]),
                study=_study_from_mapping(values["study"]),
                work=tuple(
                    CellResponseWork.from_mapping(item)
                    for item in _sequence(values["work"])
                ),
                response_channels=tuple(
                    CellResponseChannel(_text(item))
                    for item in _sequence(values["response_channels"])
                ),
                work_count=_integer(values["work_count"]),
                reason=_text(values["reason"]),
                decisive_ground_identities=tuple(
                    _text(item)
                    for item in _sequence(values["decisive_ground_identities"])
                ),
                external_claims=tuple(
                    ExternalClaim.from_mapping(item)
                    for item in _sequence(values["external_claims"])
                ),
                order_regime=_text(values["order_regime"]),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("cell_study_plan_invalid") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class CellStudyEvidenceRequirement:
    """
    Keep a consultation pause visibly distinct from an executable plan.
    """

    request_identity: str
    missing_fact: str
    reason: str

    def __post_init__(self) -> None:
        """
        Require one evidence requirement bound to an exact plan.
        """
        if not all(
            isinstance(value, str) and value.strip()
            for value in (self.request_identity, self.missing_fact, self.reason)
        ):
            raise ValueError("cell_study_evidence_requirement_invalid")


CellStudyConsultationResult = CellStudyPlan | CellStudyEvidenceRequirement


def form_cell_study_consultation(
    domain: HeightDomain,
    options: tuple[CellStudyOption, ...] | None = None,
    *,
    height_choice: HeightChoice,
    height_choice_reference: Reference,
    maximum_periodic_solver_tasks: int,
    research_mode: ResearchMode = ResearchMode.SOURCE_GROUNDED,
    grounds: tuple[ConsultationGround, ...] = (),
    exclusions: tuple[str, ...] = (),
    cautions: tuple[str, ...] = (),
) -> CellStudyConsultation:
    """
    Form one bounded choice after period and height domains are admitted.
    """

    if domain.evidence_reference is None:
        raise CellStudyFormationError("height_domain_not_admitted")
    _validate_height_choice_against_domain(
        height_choice,
        height_choice_reference,
        domain,
    )
    if (
        isinstance(maximum_periodic_solver_tasks, bool)
        or not isinstance(maximum_periodic_solver_tasks, int)
        or maximum_periodic_solver_tasks <= 0
    ):
        raise CellStudyFormationError("cell_study_task_limit_invalid")
    selected_options = (
        build_bounded_cell_study_options(
            domain,
            height_nm=height_choice.height_nm,
            maximum_periodic_solver_tasks=maximum_periodic_solver_tasks,
        )
        if options is None
        else options
    )
    if not selected_options:
        raise CellStudyFormationError("cell_study_options_missing")
    if not isinstance(research_mode, ResearchMode):
        raise CellStudyFormationError("cell_study_research_mode_invalid")

    for option in selected_options:
        _validate_option_against_domain(
            option,
            domain,
            height_nm=height_choice.height_nm,
            maximum_periodic_solver_tasks=maximum_periodic_solver_tasks,
        )

    domain_ground = ConsultationGround(
        statement=(
            f"The admitted period is {domain.period_nm} nm and the admitted "
            f"height is {height_choice.height_nm} nm."
        ),
        source_identity=height_choice_reference.content_hash,
        kind=GroundKind.CONSTRAINT,
    )
    task_limit_ground = ConsultationGround(
        statement=(
            "A selected option may contain at most "
            f"{maximum_periodic_solver_tasks} periodic solver tasks."
        ),
        source_identity=domain.brief_identity,
        kind=GroundKind.CONSTRAINT,
    )
    material_ground = ConsultationGround(
        statement=(
            f"atom material: {domain.atom.material.family}; "
            f"substrate material: {domain.substrate.family}"
        ),
        source_identity=domain.brief_identity,
        kind=GroundKind.FACT,
    )
    shape_ground = ConsultationGround(
        statement=f"meta-atom shape: {domain.atom.shape}",
        source_identity=domain.brief_identity,
        kind=GroundKind.FACT,
    )
    inherited_cautions = tuple(
        f"{item.concern}: {item.explanation}" for item in domain.cautions
    )
    try:
        return CellStudyConsultation(
            brief_identity=domain.brief_identity,
            height_choice_reference=height_choice_reference,
            period_choice_content_hash=(domain.period_choice_reference.content_hash),
            wavelength_nm=domain.wavelength_nm,
            period_nm=domain.period_nm,
            order_regime=domain.order_regime,
            maximum_periodic_solver_tasks=maximum_periodic_solver_tasks,
            research_mode=research_mode,
            grounds=(
                domain_ground,
                material_ground,
                shape_ground,
                task_limit_ground,
                *grounds,
            ),
            options=selected_options,
            exclusions=exclusions,
            cautions=(*inherited_cautions, *cautions),
        )
    except ValueError as error:
        raise CellStudyFormationError(str(error)) from error


def build_bounded_cell_study_options(
    domain: HeightDomain,
    *,
    height_nm: int | None = None,
    maximum_periodic_solver_tasks: int,
) -> tuple[CellStudyOption, ...]:
    """Form deterministic bounded options from one admitted height domain.

    The caller owns the task extent.  This function uses it as an upper bound
    and selects endpoints plus maximin-spaced legal dimensions; it never
    interprets a workstation budget or a paper value as a physical law.
    """

    if (
        isinstance(maximum_periodic_solver_tasks, bool)
        or not isinstance(maximum_periodic_solver_tasks, int)
        or maximum_periodic_solver_tasks <= 0
    ):
        raise CellStudyFormationError("cell_study_task_limit_invalid")
    shape = domain.atom.shape
    if shape in {"circular pillar", "square pillar"}:
        route = CellStudyRoute.PROPAGATION_PHASE
        geometry_budget = maximum_periodic_solver_tasks
    elif shape in {"rectangular fin", "elliptical pillar"}:
        route = CellStudyRoute.LOCAL_PB
        geometry_budget = maximum_periodic_solver_tasks // 2
    else:
        raise CellStudyFormationError("cell_study_atom_shape_unsupported")
    if geometry_budget <= 0:
        raise CellStudyFormationError("cell_study_task_limit_exceeded")
    options: list[CellStudyOption] = []
    selected_heights = domain.heights_nm if height_nm is None else (height_nm,)
    for selected_height_nm in selected_heights:
        fabrication = domain.resolve_fabrication_range(selected_height_nm)
        legal_values = tuple(
            range(
                fabrication.minimum_feature_nm,
                fabrication.maximum_feature_nm + 1,
                domain.dimension_step_nm,
            )
        )
        if not legal_values:
            continue
        selected_values = _bounded_axis_values(legal_values, geometry_budget)
        if route is CellStudyRoute.PROPAGATION_PHASE:
            if shape == "circular pillar":
                geometries = tuple(Circle(value) for value in selected_values)
            else:
                geometries = tuple(Square(value) for value in selected_values)
            study = PropagationCellStudy.from_geometries(
                geometries,
                input_basis=CellInputBasis.X_LINEAR,
            )
        elif shape == "rectangular fin":
            geometries = tuple(
                Rectangle(
                    short_side_nm=short_value,
                    long_side_nm=long_value,
                )
                for short_value, long_value in _bounded_anisotropic_values(
                    selected_values,
                    geometry_budget,
                )
            )
            study = LocalPbCellStudy.from_geometries(geometries)
        else:
            geometries = tuple(
                Ellipse(
                    minor_axis_nm=short_value,
                    major_axis_nm=long_value,
                )
                for short_value, long_value in _bounded_anisotropic_values(
                    selected_values,
                    geometry_budget,
                )
            )
            study = LocalPbCellStudy.from_geometries(geometries)
        if study.work:
            options.append(
                CellStudyOption(
                    height_nm=selected_height_nm,
                    study=study,
                    cautions=(
                        (
                            "order regime is a proof obligation, not a sampling veto"
                            if domain.order_regime == "multi order"
                            else "period sampling is admitted under the hard ceiling"
                        ),
                    ),
                )
            )
    if not options:
        raise CellStudyFormationError("cell_study_options_missing")
    return tuple(options)


def _bounded_axis_values(
    legal_values: tuple[int, ...],
    maximum_count: int,
) -> tuple[int, ...]:
    if len(legal_values) <= maximum_count:
        return legal_values
    if maximum_count == 1:
        return (legal_values[0],)
    positions = tuple(
        round(index * (len(legal_values) - 1) / (maximum_count - 1))
        for index in range(maximum_count)
    )
    return tuple(legal_values[index] for index in positions)


def _bounded_anisotropic_values(
    axis_values: tuple[int, ...],
    maximum_count: int,
) -> tuple[tuple[int, int], ...]:
    pairs = tuple(
        (axis_values[index], axis_values[index + 1])
        for index in range(len(axis_values) - 1)
    )
    if len(pairs) <= maximum_count:
        return pairs
    indices = _bounded_axis_values(tuple(range(len(pairs))), maximum_count)
    return tuple(pairs[index] for index in indices)


def accept_cell_study_answer(
    request: CellStudyConsultation,
    answer: ConsultationAnswer,
) -> CellStudyConsultationResult:
    """
    Accept one exact option identity or return an evidence requirement.
    """

    if answer.request_identity != request.identity:
        raise InvalidCellStudyAnswer("cell_study_answer_request_mismatch")
    claims = {claim.identity: claim for claim in answer.external_claims}
    if request.research_mode is ResearchMode.CLOSED_BOOK and claims:
        raise InvalidCellStudyAnswer("cell_study_external_claim_forbidden")
    if isinstance(answer.conclusion, EvidenceRequired):
        if claims:
            raise InvalidCellStudyAnswer("cell_study_external_claim_surplus")
        return CellStudyEvidenceRequirement(
            request_identity=request.identity,
            missing_fact=answer.conclusion.missing_fact,
            reason=answer.conclusion.reason,
        )

    conclusion = answer.conclusion
    assert isinstance(conclusion, Recommendation)
    option = next(
        (
            item
            for item in request.options
            if item.identity == conclusion.candidate_identity
        ),
        None,
    )
    if option is None:
        raise InvalidCellStudyAnswer("cell_study_option_unknown")
    ground_identities = {ground.identity for ground in request.grounds}
    if not set(conclusion.decisive_ground_identities) <= ground_identities:
        raise InvalidCellStudyAnswer("cell_study_ground_unknown")
    if set(conclusion.external_claim_identities) != set(claims):
        raise InvalidCellStudyAnswer("cell_study_external_claim_closure_invalid")

    return CellStudyPlan(
        request_identity=request.identity,
        option_identity=option.identity,
        brief_identity=request.brief_identity,
        height_choice_reference=request.height_choice_reference,
        period_choice_content_hash=request.period_choice_content_hash,
        period_nm=request.period_nm,
        height_nm=option.height_nm,
        study=option.study,
        work=option.work,
        response_channels=option.response_channels,
        work_count=option.work_count,
        reason=conclusion.reason,
        decisive_ground_identities=(conclusion.decisive_ground_identities),
        external_claims=answer.external_claims,
        order_regime=request.order_regime,
    )


def _validate_option_against_domain(
    option: CellStudyOption,
    domain: HeightDomain,
    *,
    height_nm: int,
    maximum_periodic_solver_tasks: int,
) -> None:
    if option.height_nm != height_nm:
        raise CellStudyFormationError("cell_study_height_choice_mismatch")
    if any(item.geometry.shape != domain.atom.shape for item in option.work):
        raise CellStudyFormationError("cell_study_geometry_shape_mismatch")
    if option.work_count > maximum_periodic_solver_tasks:
        raise CellStudyFormationError("cell_study_task_limit_exceeded")
    fabrication = domain.resolve_fabrication_range(option.height_nm)
    for item in option.work:
        dimensions = _geometry_dimensions(item.geometry)
        if any(
            dimension < fabrication.minimum_feature_nm
            or dimension > fabrication.maximum_feature_nm
            or dimension % domain.dimension_step_nm
            for dimension in dimensions
        ):
            raise CellStudyFormationError(
                "cell_study_geometry_outside_fabrication_domain"
            )


def _validate_height_choice_against_domain(
    choice: HeightChoice,
    choice_reference: Reference,
    domain: HeightDomain,
) -> None:
    if not reference_matches(choice_reference, choice.document().to_bytes()):
        raise CellStudyFormationError("height_choice_reference_mismatch")
    if (
        choice.brief_identity != domain.brief_identity
        or choice.domain_reference != domain.evidence_reference
    ):
        raise CellStudyFormationError("height_choice_domain_mismatch")
    if (
        choice.period_nm != domain.period_nm
        or choice.order_regime != domain.order_regime
        or choice.dimension_step_nm != domain.dimension_step_nm
        or choice.height_nm not in domain.heights_nm
    ):
        raise CellStudyFormationError("height_choice_context_mismatch")
    fabrication = domain.resolve_fabrication_range(choice.height_nm)
    if (
        choice.minimum_feature_nm != fabrication.minimum_feature_nm
        or choice.maximum_feature_nm != fabrication.maximum_feature_nm
    ):
        raise CellStudyFormationError("height_choice_fabrication_mismatch")


def _local_basis_work_from_geometries(
    geometries: tuple[Rectangle | Ellipse, ...],
) -> tuple[CellResponseWork, ...]:
    work = []
    for geometry in geometries:
        work.extend(
            (
                CellResponseWork(
                    route=CellStudyRoute.LOCAL_PB,
                    geometry=geometry,
                    input_basis=CellInputBasis.X_LINEAR,
                    response_channels=_PB_X_CHANNELS,
                ),
                CellResponseWork(
                    route=CellStudyRoute.LOCAL_PB,
                    geometry=geometry,
                    input_basis=CellInputBasis.Y_LINEAR,
                    response_channels=_PB_Y_CHANNELS,
                ),
            )
        )
    return tuple(work)


def _study_from_mapping(value: object) -> CellStudy:
    values = _closed_mapping(
        value,
        {"route", "work"},
        "cell_study_invalid",
    )
    try:
        route = CellStudyRoute(_text(values["route"]))
        work = tuple(
            CellResponseWork.from_mapping(item) for item in _sequence(values["work"])
        )
        if route is CellStudyRoute.PROPAGATION_PHASE:
            return PropagationCellStudy(work=work)
        return LocalPbCellStudy(work=work)
    except (TypeError, ValueError) as error:
        raise ValueError("cell_study_invalid") from error


def _geometry_value(geometry: Geometry) -> dict[str, object]:
    if isinstance(geometry, Circle):
        return {"kind": "circle", "diameter_nm": geometry.diameter_nm}
    if isinstance(geometry, Square):
        return {"kind": "square", "width_nm": geometry.width_nm}
    if isinstance(geometry, Rectangle):
        return {
            "kind": "rectangle",
            "long_side_nm": geometry.long_side_nm,
            "short_side_nm": geometry.short_side_nm,
        }
    if isinstance(geometry, Ellipse):
        return {
            "kind": "ellipse",
            "major_axis_nm": geometry.major_axis_nm,
            "minor_axis_nm": geometry.minor_axis_nm,
        }
    raise ValueError("cell_study_geometry_invalid")


def _geometry_from_mapping(value: object) -> Geometry:
    if not isinstance(value, Mapping):
        raise ValueError("cell_study_geometry_invalid")
    kind = value.get("kind")
    if kind == "circle" and set(value) == {"kind", "diameter_nm"}:
        return Circle(_integer(value["diameter_nm"]))
    if kind == "square" and set(value) == {"kind", "width_nm"}:
        return Square(_integer(value["width_nm"]))
    if kind == "rectangle" and set(value) == {
        "kind",
        "long_side_nm",
        "short_side_nm",
    }:
        return Rectangle(
            short_side_nm=_integer(value["short_side_nm"]),
            long_side_nm=_integer(value["long_side_nm"]),
        )
    if kind == "ellipse" and set(value) == {
        "kind",
        "major_axis_nm",
        "minor_axis_nm",
    }:
        return Ellipse(
            minor_axis_nm=_integer(value["minor_axis_nm"]),
            major_axis_nm=_integer(value["major_axis_nm"]),
        )
    raise ValueError("cell_study_geometry_invalid")


def _geometry_dimensions(geometry: Geometry) -> tuple[int, ...]:
    if isinstance(geometry, Circle):
        return (geometry.diameter_nm,)
    if isinstance(geometry, Square):
        return (geometry.width_nm,)
    if isinstance(geometry, Rectangle):
        return (geometry.short_side_nm, geometry.long_side_nm)
    if isinstance(geometry, Ellipse):
        return (geometry.minor_axis_nm, geometry.major_axis_nm)
    raise ValueError("cell_study_geometry_invalid")


def _answer_contract() -> dict[str, object]:
    return {
        "document_fields": [
            "conclusion",
            "external_claims",
            "request_identity",
        ],
        "evidence_required": {
            "fields": ["kind", "missing_fact", "reason"],
            "kind": "evidence_required",
        },
        "recommendation": {
            "candidate_rule": "one exact options[].identity",
            "fields": [
                "candidate_identity",
                "decisive_ground_identities",
                "external_claim_identities",
                "kind",
                "reason",
            ],
            "kind": "recommendation",
        },
        "schema_identifier": CONSULTATION_ANSWER_SCHEMA,
    }


def _identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(encode_bytes(value)).hexdigest()}"


def _closed_mapping(
    value: object,
    keys: set[str],
    finding: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(finding)
    return value


def _sequence(value: object) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        raise ValueError("cell_study_sequence_invalid")
    return value


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("cell_study_integer_invalid")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("cell_study_text_invalid")
    return value


def _reference(value: object) -> Reference:
    return Reference.from_mapping(
        _closed_mapping(
            value,
            {
                "content_hash",
                "media_type",
                "metadata_content_hash",
                "size_bytes",
            },
            "cell_study_reference_invalid",
        )
    )


def _require_unique(values: tuple[str, ...]) -> None:
    if len(set(values)) != len(values):
        raise ValueError("cell_study_identity_duplicate")


def _require_text_tuple(values: tuple[str, ...], finding: str) -> None:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) or not value.strip() for value in values
    ):
        raise ValueError(finding)


# Stable short names for callers that treat this Module as the deep seam.
form_cell_study = form_cell_study_consultation
accept_cell_study_reply = accept_cell_study_answer
