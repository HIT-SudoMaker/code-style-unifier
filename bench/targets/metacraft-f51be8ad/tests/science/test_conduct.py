from __future__ import annotations

import cmath
from dataclasses import replace
from decimal import Decimal
import math
from pathlib import Path
from unittest.mock import patch

import pytest

from metacraft.authority import Authority, Document, Reference
from metacraft.authority.reference import reference_for
from metacraft.authority.session import AuthoritySession
from metacraft.external_activity import ExternalActivityClosure
from metacraft.materials import (
    AdmittedSolverMaterial,
    MaterialResponseContext,
    MaterialUnavailable,
    MaterialUnavailableReason,
    MaterialVerificationRequest,
    ObservedMaterials,
    SolverMaterial,
    VerifiedMaterial,
)
from metacraft.science.conduct import (
    CompletedResults,
    ConsultationAnswerRejected,
    ConsultationRequired,
    InvalidBrief,
    WaitingStudies,
    conduct,
)
from metacraft.science.conduct import _admit_completed_results, _admit_result
from metacraft.science.consultation import ConsultationAnswer, Recommendation
from metacraft.science.compile import compile_study
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.achromatic import (
    AchromaticAperture,
    AchromaticFocusEntry,
    BandVerificationEvidence,
    BandVerificationStatus,
    POST_FREEZE_JONES_LIBRARY_SCHEMA,
    PostFreezeJonesLibrary,
    ResponseQualificationProfile,
    SpectralCellStudyPlan,
    SpectralFieldFamily,
    SpectralLibraryQualification,
    SpectralQualificationStatus,
    form_achromatic_focus,
)
from metacraft.science.metalens.brief import MonochromaticSpectrum
from metacraft.science.metalens.aperture import Lattice
from metacraft.science.metalens.checkpoint import StudyFrontier
from metacraft.science.metalens.conduct import (
    advance_metalens,
    prepare_metalens_study,
)
from metacraft.science.metalens.evidence_adapter import MetalensEvidenceAdapter
from metacraft.science.metalens.evidence import MetalensEvidence
from metacraft.science.metalens.focus import (
    Focus,
    FocusConvergence,
    HalfMaximum,
    Leakage,
)
from metacraft.science.metalens.height import HeightDomain
from metacraft.science.metalens.period import (
    PeriodChoice,
    derive_period_domain,
    resolve_period_choice,
)
from metacraft.science.periodic_response import (
    ObservedPeriodicPolarization,
    PeriodicResponseClosure,
    PeriodicResponseContext,
    PeriodicResponseKind,
    PeriodicResponseUnavailable,
    PeriodicResponseUnavailableReason,
    PeriodicWork,
    RectangularCrossSection,
    decode_periodic_polarization,
    form_admitted_periodic_polarization,
)
from metacraft.solvers.lumerical_fdtd.qualification import (
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseProof,
    PeriodicResponseQualification,
)
from metacraft.science.study import (
    Binding,
    Capability,
    Finding,
    FindingKind,
    Study,
)
from metacraft.science.metalens.result import AchromaticResult, restore_conclusion
from tests.brief_fixtures import (
    continuous_achromatic_brief,
    continuous_achromatic_publication_brief,
    propagation_brief,
)
from tests.domain_fixtures import (
    compile_with_facts,
    height_domain,
    material_binding,
    period_choice,
    period_domain,
    phase_envelope,
)
from tests.achromatic_fixtures import incomplete_periodic_outcome
from tests.propagation_fixtures import fake_metalens_ports
from tests.result_fixtures import propagation_result


class _UnusedPeriodicResponse:
    def __init__(self, context: PeriodicResponseContext) -> None:
        self.context = context

    def observe(self, request):
        raise AssertionError("periodic response must wait for material evidence")


class _SentinelFailure(ValueError):
    pass


class _UnavailableMaterials:
    def __init__(self, context: MaterialResponseContext) -> None:
        self.context = context
        self.calls = 0
        self.requests = []

    def observe(self, request):
        self.calls += 1
        self.requests.append(request)
        return MaterialUnavailable(
            request=request,
            reason=MaterialUnavailableReason.REGISTRATION_ABSENT,
            family=request.families[0],
            activity=ExternalActivityClosure.none(),
        )


class _UnavailableEvidenceAdapter:
    def __init__(self) -> None:
        self.open_calls = 0
        self.materials: _UnavailableMaterials | None = None

    def open(self, *, authority: Authority, runs_directory: Path):
        self.open_calls += 1
        assert runs_directory.is_dir()
        session = AuthoritySession(authority)
        periodic_reference = session.admit_document(
            Document("fixture.periodic_response_binding", {"qualified": True})
        )
        material_reference = session.admit_document(
            Document("fixture.material_response_binding", {"qualified": True})
        )
        periodic_response = _UnusedPeriodicResponse(
            PeriodicResponseContext(
                binding_reference=periodic_reference,
                capacity_scope="fixture:periodic_response",
                response_kinds=tuple(PeriodicResponseKind),
            )
        )
        self.materials = _UnavailableMaterials(
            MaterialResponseContext(
                binding_reference=material_reference,
                capacity_scope="fixture:material_response",
            )
        )
        return periodic_response, self.materials


class _FullSpectrumMaterials:
    def __init__(
        self,
        context: MaterialResponseContext,
        session: AuthoritySession,
        selections: tuple[AdmittedSolverMaterial, ...],
        product_sample_reference: Reference,
    ) -> None:
        self.context = context
        self._session = session
        self._selections = selections
        self._product_sample_reference = product_sample_reference
        self.requests = []

    def observe(self, request):
        self.requests.append(request)
        verification = MaterialVerificationRequest(
            observation_request=request,
            binding_reference=self.context.binding_reference,
            selections=self._selections,
        )
        observed = ObservedMaterials.create(
            verification,
            product_sample_reference=self._product_sample_reference,
            materials=(
                VerifiedMaterial(
                    family="amorphous titanium dioxide",
                    native_name="TiO2 (Titanium Dioxide) - Siefke",
                    refractive_index=Decimal("2.45"),
                    extinction_coefficient=Decimal("0.0000002"),
                ),
                VerifiedMaterial(
                    family="glass",
                    native_name="SiO2 (Glass) - Palik",
                    refractive_index=Decimal("1.46"),
                    extinction_coefficient=Decimal(0),
                ),
            ),
            activity=ExternalActivityClosure.none(),
        )
        admitted = self._session.admit_document(
            observed.document(),
            references=(
                self.context.binding_reference,
                self._product_sample_reference,
                *(selection.reference for selection in self._selections),
            ),
        )
        assert admitted == observed.sample_reference
        return observed


class _SyntheticSpectralPeriodicResponse:
    def __init__(
        self,
        context: PeriodicResponseContext,
        session: AuthoritySession,
        *,
        post_freeze_unavailable: bool = False,
        post_freeze_numerical: bool = False,
        post_freeze_mixed_origin: bool = False,
    ) -> None:
        self.context = context
        self._session = session
        self.requests = []
        self._post_freeze_unavailable = post_freeze_unavailable
        self._post_freeze_numerical = post_freeze_numerical
        self._post_freeze_mixed_origin = post_freeze_mixed_origin
        self._has_emitted_native_post_freeze = False

    def observe(self, request):
        self.requests.append(request)
        is_post_freeze = all(
            item.observation_schema == POST_FREEZE_JONES_LIBRARY_SCHEMA
            for item in request.items
        )
        uses_native_origin = (
            self._post_freeze_mixed_origin
            and is_post_freeze
            and not self._has_emitted_native_post_freeze
        )
        if (
            self._post_freeze_unavailable
            and is_post_freeze
        ):
            return PeriodicResponseUnavailable(
                request.request_identity,
                PeriodicResponseUnavailableReason.RECORDED_RESPONSE_MISSING,
                PeriodicResponseClosure(
                    request.request_identity,
                    ExternalActivityClosure.none(),
                    ExternalActivityClosure.none(),
                ),
            )
        if (
            self._post_freeze_numerical
            and is_post_freeze
        ):
            incomplete = incomplete_periodic_outcome(request)
            for item in incomplete.incomplete_items:
                admitted = self._session.admit_document(
                    Document(
                        "metacraft.science.periodic_observation_incomplete",
                        item.outcome.as_mapping(),
                    )
                )
                assert admitted == item.body_reference
            return replace(incomplete, items=())
        decoded_items = []
        raw_items_by_basis = {"x": [], "y": []}
        legal_dimensions = tuple(range(80, 241, 10))
        canonical_geometries = tuple(
            (short_side, long_side)
            for index, short_side in enumerate(legal_dimensions)
            for long_side in legal_dimensions[index + 1 :]
        )
        geometry_count = len(canonical_geometries)
        for work in request.items:
            assert isinstance(work.geometry, RectangularCrossSection)
            geometry_index = canonical_geometries.index(
                (work.geometry.short_side_nm, work.geometry.long_side_nm)
            )
            delay_fs = 3.8 * geometry_index / (geometry_count - 1)
            reference_omega = 2 * math.pi * 299.792458 / 530
            intercept = (
                geometry_index * 2 * math.pi / geometry_count
                - delay_fs * reference_omega
            )
            omega = 2 * math.pi * 299.792458 / work.wavelength_nm
            converted = math.sqrt(0.8) * cmath.exp(1j * (intercept + delay_fs * omega))
            basis = work.input_basis.removesuffix(" linear")
            output_x = converted if basis == "x" else 0j
            output_y = 0j if basis == "x" else -converted
            values = {
                "basis": basis,
                "candidate": work.candidate_mapping(),
                "execution": {
                    "native": uses_native_origin,
                    "placement": {},
                    "project": "synthetic spectral response",
                    "return_code": 0,
                    "source": "test-only",
                },
                "output_x": {
                    "imaginary_part": format(Decimal(str(output_x.imag)), "f"),
                    "real_part": format(Decimal(str(output_x.real)), "f"),
                },
                "output_y": {
                    "imaginary_part": format(Decimal(str(output_y.imag)), "f"),
                    "real_part": format(Decimal(str(output_y.real)), "f"),
                },
                "phase_planes": "same input and output reference planes",
                "reference_surface": _synthetic_reference_surface(
                    work,
                    basis,
                    transmitted_power=abs(output_x) ** 2 + abs(output_y) ** 2,
                ),
                "solver_status": "complete",
                "warnings": [],
            }
            decoded = decode_periodic_polarization(values)
            raw_items_by_basis[basis].append(values)
            decoded_items.append((work, decoded))
        if uses_native_origin:
            self._has_emitted_native_post_freeze = True
        batch_references = {
            basis: self._session.admit_document(
                Document(
                    "fixture.synthetic_periodic_polarization_batch",
                    {
                        "basis": basis,
                        "request_identity": request.request_identity,
                        "observations": raw_items,
                    },
                )
            )
            for basis, raw_items in raw_items_by_basis.items()
        }
        admitted = tuple(
            (
                form_admitted_periodic_polarization(
                    work.work_identity,
                    decoded,
                    batch_references[work.input_basis.removesuffix(" linear")],
                    batch_references[work.input_basis.removesuffix(" linear")],
                )
            )
            for work, decoded in decoded_items
        )
        return ObservedPeriodicPolarization(
            request_identity=request.request_identity,
            items=admitted,
            closure=PeriodicResponseClosure(
                request.request_identity,
                ExternalActivityClosure.none(),
                ExternalActivityClosure.none(),
            ),
        )


def _synthetic_reference_surface(
    work: PeriodicWork,
    basis: str,
    *,
    transmitted_power: float,
) -> dict[str, object]:
    half_period_m = Decimal(work.period_nm) / Decimal(2_000_000_000)
    coordinates = [format(-half_period_m, "f"), "0", format(half_period_m, "f")]
    zero_patch = [["0", "0", "0"] for _ in range(3)]
    return {
        "electric_components": {
            component: {"imaginary": zero_patch, "real": zero_patch}
            for component in ("x", "y", "z")
        },
        "frame": {
            "normal_axis": "z",
            "propagation_direction": "positive",
            "sample_order": ["y", "x"],
        },
        "incident_reference_power": "1",
        "medium": "air",
        "order_regime": "zeroth order",
        "output_basis": "cartesian",
        "requested_input_basis": f"{basis} linear",
        "surface": {
            "position_m": "0.0000008",
            "x_coordinates_m": coordinates,
            "y_coordinates_m": coordinates,
        },
        "transmitted_power": format(Decimal(str(transmitted_power)), "f"),
        "wavelength_m": format(
            Decimal(work.wavelength_nm) / Decimal(1_000_000_000),
            "f",
        ),
    }


class _FullSpectrumEvidenceAdapter:
    def __init__(
        self,
        *,
        spectral_periodic: bool = False,
        post_freeze_unavailable: bool = False,
        post_freeze_numerical: bool = False,
        post_freeze_mixed_origin: bool = False,
    ) -> None:
        self.open_calls = 0
        self.materials: _FullSpectrumMaterials | None = None
        self.periodic: _SyntheticSpectralPeriodicResponse | None = None
        self._spectral_periodic = spectral_periodic
        self._post_freeze_unavailable = post_freeze_unavailable
        self._post_freeze_numerical = post_freeze_numerical
        self._post_freeze_mixed_origin = post_freeze_mixed_origin

    def open(self, *, authority: Authority, runs_directory: Path):
        self.open_calls += 1
        session = AuthoritySession(authority)
        periodic_reference = session.admit_document(
            Document("fixture.periodic_response_binding", {"qualified": True})
        )
        material_reference = session.admit_document(
            Document("fixture.material_response_binding", {"qualified": True})
        )
        product_reference = session.admit_document(
            Document("fixture.spectral_material_product", {"grid": "complete"})
        )
        registrations = tuple(
            SolverMaterial(
                solver="lumerical fdtd",
                family=family,
                native_name=native_name,
                provenance="test-only complete spectral fixture",
            )
            for family, native_name in (
                (
                    "amorphous titanium dioxide",
                    "TiO2 (Titanium Dioxide) - Siefke",
                ),
                ("glass", "SiO2 (Glass) - Palik"),
            )
        )
        selections = tuple(
            AdmittedSolverMaterial(
                material=registration,
                reference=session.admit_document(registration.document()),
            )
            for registration in registrations
        )
        self.materials = _FullSpectrumMaterials(
            MaterialResponseContext(
                binding_reference=material_reference,
                capacity_scope="fixture:spectral_material_response",
            ),
            session,
            selections,
            product_reference,
        )
        response_kinds = (
            (PeriodicResponseKind.POLARIZATION,)
            if self._spectral_periodic
            else (PeriodicResponseKind.TRANSMISSION,)
        )
        context = PeriodicResponseContext(
            binding_reference=periodic_reference,
            capacity_scope="fixture:periodic_response",
            response_kinds=response_kinds,
        )
        if self._spectral_periodic:
            self.periodic = _SyntheticSpectralPeriodicResponse(
                context,
                session,
                post_freeze_unavailable=self._post_freeze_unavailable,
                post_freeze_numerical=self._post_freeze_numerical,
                post_freeze_mixed_origin=self._post_freeze_mixed_origin,
            )
            periodic_response = self.periodic
        else:
            periodic_response = _UnusedPeriodicResponse(context)
        return periodic_response, self.materials


class _FailingEvidenceAdapter:
    def __init__(self) -> None:
        self.open_calls = 0

    def open(self, *, authority: Authority, runs_directory: Path):
        self.open_calls += 1
        raise RuntimeError("evidence_adapter_open_failed")


class _MalformedEvidenceAdapter:
    def __init__(self, opened: object) -> None:
        self._opened = opened

    def open(self, *, authority: Authority, runs_directory: Path):
        return self._opened


class _ForeignEvidenceAdapter:
    def __init__(
        self,
        foreign_authority_root: Path,
        *,
        should_foreign_materials: bool,
    ) -> None:
        self._foreign_authority_root = foreign_authority_root
        self._should_foreign_materials = should_foreign_materials
        self.materials: _UnavailableMaterials | None = None

    def open(self, *, authority: Authority, runs_directory: Path):
        local_session = AuthoritySession(authority)
        foreign_session = AuthoritySession(Authority(self._foreign_authority_root))
        periodic_session = (
            local_session if self._should_foreign_materials else foreign_session
        )
        material_session = (
            foreign_session if self._should_foreign_materials else local_session
        )
        periodic_reference = periodic_session.admit_document(
            Document(
                "fixture.foreign_periodic_response_binding",
                {"qualified": True},
            )
        )
        material_reference = material_session.admit_document(
            Document(
                "fixture.foreign_material_response_binding",
                {"qualified": True},
            )
        )
        periodic = _UnusedPeriodicResponse(
            PeriodicResponseContext(
                binding_reference=periodic_reference,
                capacity_scope="fixture:periodic_response",
                response_kinds=tuple(PeriodicResponseKind),
            )
        )
        self.materials = _UnavailableMaterials(
            MaterialResponseContext(
                binding_reference=material_reference,
                capacity_scope="fixture:material_response",
            )
        )
        return periodic, self.materials


def _material_capabilities() -> tuple[Capability, ...]:
    return (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
        Capability("deterministic_selection"),
    )


def _material_bindings() -> tuple[Binding, ...]:
    return (
        Binding("optical_material", reference_for(b"material solver")),
        Binding("fabrication_constraint", reference_for(b"fabrication")),
        Binding("deterministic_selection", reference_for(b"selection")),
    )


def _idle_evidence_ports(
    session: AuthoritySession,
) -> tuple[_UnusedPeriodicResponse, _UnavailableMaterials]:
    periodic_reference = session.admit_document(
        Document("fixture.periodic_response_binding", {"qualified": True})
    )
    material_reference = session.admit_document(
        Document("fixture.material_response_binding", {"qualified": True})
    )
    return (
        _UnusedPeriodicResponse(
            PeriodicResponseContext(
                binding_reference=periodic_reference,
                capacity_scope="fixture:periodic_response",
                response_kinds=tuple(PeriodicResponseKind),
            )
        ),
        _UnavailableMaterials(
            MaterialResponseContext(
                binding_reference=material_reference,
                capacity_scope="fixture:material_response",
            )
        ),
    )


def _conduct_until_material_wait(
    application_root: Path,
    evidence_adapter: _UnavailableEvidenceAdapter | None = None,
) -> tuple[WaitingStudies, _UnavailableEvidenceAdapter]:
    selected_adapter = evidence_adapter or _UnavailableEvidenceAdapter()
    adapter_contract: MetalensEvidenceAdapter = selected_adapter
    outcome = conduct(
        propagation_brief(),
        application_root=application_root,
        evidence_adapter=adapter_contract,
    )
    assert isinstance(outcome, WaitingStudies)
    return outcome, selected_adapter


def test_fresh_application_root_returns_the_complete_waiting_frontier(
    tmp_path: Path,
) -> None:
    outcome, adapter = _conduct_until_material_wait(tmp_path / "application-root")

    assert outcome.studies
    assert all(isinstance(study, Study) for study in outcome.studies)
    assert all(study.findings for study in outcome.studies)
    assert len({study.canonical_bytes() for study in outcome.studies}) == len(
        outcome.studies
    )
    assert adapter.open_calls == 1


def test_continuous_achromatic_conduct_forms_target_then_waits_for_spectral_material(
    tmp_path: Path,
) -> None:
    application_root = tmp_path / "application-root"

    outcome = conduct(
        continuous_achromatic_brief(),
        application_root=application_root,
    )

    assert isinstance(outcome, WaitingStudies)
    assert len(outcome.studies) == 1
    study = outcome.studies[0]
    assert tuple(fact.claim for fact in study.evidence) == (
        "achromatic_target",
        "response_qualification_profile",
        "spectral_study_specification",
    )
    material_finding = next(
        finding
        for finding in study.findings
        if finding.claim == "spectral_material_binding"
    )
    assert material_finding.kind is FindingKind.CAPABILITY
    assert material_finding.needs == ("spectral_optical_material",)
    profile_reference = next(
        fact.reference
        for fact in study.evidence
        if fact.claim == "response_qualification_profile"
    )
    session = AuthoritySession(Authority(application_root / "authority"))
    profile = ResponseQualificationProfile.from_document(
        Document.from_bytes(session.fetch(profile_reference))
    )
    assert profile.version == "pre-registered-engineering-v1"
    assert profile.source_references

    authority = Authority(application_root / "authority")
    revision = authority.view().revision
    repeated = conduct(
        continuous_achromatic_brief(),
        application_root=application_root,
    )

    assert repeated == outcome
    assert authority.view().revision == revision


def test_continuous_achromatic_material_request_stops_at_first_missing_band_point(
    tmp_path: Path,
) -> None:
    adapter = _UnavailableEvidenceAdapter()

    outcome = conduct(
        continuous_achromatic_brief(),
        application_root=tmp_path / "application-root",
        evidence_adapter=adapter,
    )

    assert isinstance(outcome, WaitingStudies)
    assert adapter.open_calls == 1
    assert adapter.materials is not None
    assert tuple(request.wavelength_nm for request in adapter.materials.requests) == (
        470,
    )
    finding = next(
        item
        for item in outcome.studies[0].findings
        if item.claim == "spectral_material_binding"
    )
    assert finding.kind is FindingKind.UNAVAILABLE
    assert finding.needs == (
        "spectral_material_unavailable:470:registration_absent:"
        "amorphous titanium dioxide",
    )


def test_continuous_achromatic_conduct_compiles_complete_materials_into_one_plan(
    tmp_path: Path,
) -> None:
    adapter = _FullSpectrumEvidenceAdapter()
    application_root = tmp_path / "application-root"

    outcome = conduct(
        continuous_achromatic_publication_brief(),
        application_root=application_root,
        evidence_adapter=adapter,
    )

    assert isinstance(outcome, WaitingStudies)
    assert adapter.open_calls == 1
    assert adapter.materials is not None
    assert tuple(request.wavelength_nm for request in adapter.materials.requests) == (
        tuple(range(470, 591, 5))
    )
    study = outcome.studies[0]
    assert tuple(fact.claim for fact in study.evidence) == (
        "achromatic_target",
        "response_qualification_profile",
        "spectral_study_specification",
        "spectral_material_binding",
        "spectral_cell_study_plan",
        "physical_lattice",
    )
    plan_reference = next(
        fact.reference
        for fact in study.evidence
        if fact.claim == "spectral_cell_study_plan"
    )
    plan = SpectralCellStudyPlan.from_document(
        Document.from_bytes(
            AuthoritySession(Authority(application_root / "authority")).fetch(
                plan_reference
            )
        )
    )
    assert plan.period_nm == 320
    assert plan.height_nm == 600
    assert plan.reference_screen_work_count == 272
    assert plan.maximum_followup_work_count == 2176
    assert plan.maximum_post_freeze_work_count == 4352
    assert plan.maximum_work_count == 6800
    lattice_reference = next(
        fact.reference for fact in study.evidence if fact.claim == "physical_lattice"
    )
    lattice = Lattice.from_document(
        Document.from_bytes(
            AuthoritySession(Authority(application_root / "authority")).fetch(
                lattice_reference
            )
        )
    )
    assert lattice.spacing_source_reference == plan_reference
    response_finding = next(
        finding for finding in study.findings if finding.claim == "spectral_cell_screen"
    )
    assert response_finding.kind is FindingKind.CAPABILITY
    assert response_finding.needs == ("periodic_polarization_response",)


def test_continuous_achromatic_conduct_stops_the_legacy_aperture_mismatch(
    tmp_path: Path,
) -> None:
    adapter = _FullSpectrumEvidenceAdapter()

    outcome = conduct(
        continuous_achromatic_brief(),
        application_root=tmp_path / "application-root",
        evidence_adapter=adapter,
    )

    assert isinstance(outcome, WaitingStudies)
    finding = next(
        item
        for item in outcome.studies[0].findings
        if item.claim == "physical_lattice"
    )
    assert finding.kind is FindingKind.REFUSAL
    assert finding.needs == ("aperture_intent_mismatch:51:63",)


def test_continuous_achromatic_conduct_qualifies_one_complete_spectral_library(
    tmp_path: Path,
) -> None:
    adapter = _FullSpectrumEvidenceAdapter(spectral_periodic=True)
    application_root = tmp_path / "application-root"
    brief = continuous_achromatic_publication_brief()

    outcome = conduct(
        brief,
        application_root=application_root,
        evidence_adapter=adapter,
    )

    assert isinstance(outcome, WaitingStudies)
    assert adapter.open_calls == 1
    assert adapter.periodic is not None
    assert len(adapter.periodic.requests) == 25
    study = outcome.studies[0]
    assert tuple(fact.claim for fact in study.evidence) == (
        "achromatic_target",
        "response_qualification_profile",
        "spectral_study_specification",
        "spectral_material_binding",
        "spectral_cell_study_plan",
        "physical_lattice",
        "spectral_cell_screen",
        "spectral_jones_library",
        "qualified_spectral_library",
        "achromatic_aperture",
        "post_freeze_jones_library",
        "spectral_field_family",
    )
    qualification_reference = next(
        fact.reference
        for fact in study.evidence
        if fact.claim == "qualified_spectral_library"
    )
    qualification = SpectralLibraryQualification.from_document(
        Document.from_bytes(
            AuthoritySession(Authority(application_root / "authority")).fetch(
                qualification_reference
            )
        )
    )
    assert qualification.status is SpectralQualificationStatus.CANDIDATE
    session = AuthoritySession(Authority(application_root / "authority"))
    aperture_reference = next(
        fact.reference for fact in study.evidence if fact.claim == "achromatic_aperture"
    )
    aperture = AchromaticAperture.from_document(
        Document.from_bytes(session.fetch(aperture_reference))
    )
    family_reference = next(
        fact.reference
        for fact in study.evidence
        if fact.claim == "spectral_field_family"
    )
    family = SpectralFieldFamily.from_document(
        Document.from_bytes(session.fetch(family_reference))
    )
    focus_finding = next(
        finding for finding in study.findings if finding.claim == "achromatic_focus"
    )
    assert aperture.site_count > 1
    assert len(family.entries) == 50
    assert sum(len(request.items) for request in adapter.periodic.requests) == (
        2448 + len(aperture.used_geometries) * 16 * 2
    )
    assert focus_finding.kind is FindingKind.INCOMPLETE
    assert focus_finding.needs == ("focus_incomplete",)

    replay = conduct(brief, application_root=application_root)

    assert isinstance(replay, WaitingStudies)
    assert replay.studies == outcome.studies


def test_continuous_achromatic_missing_blind_role_closes_typed_band_stop(
    tmp_path: Path,
) -> None:
    adapter = _FullSpectrumEvidenceAdapter(
        spectral_periodic=True,
        post_freeze_unavailable=True,
    )
    application_root = tmp_path / "application-root"

    outcome = conduct(
        continuous_achromatic_publication_brief(),
        application_root=application_root,
        evidence_adapter=adapter,
    )

    assert isinstance(outcome, WaitingStudies)
    finding = next(
        item
        for item in outcome.studies[0].findings
        if item.claim == "post_freeze_jones_library"
    )
    assert finding.kind is FindingKind.INCOMPLETE
    assert finding.needs == (BandVerificationStatus.MISSING_BLIND.value,)
    assert len(finding.record_references) == 2
    session = AuthoritySession(Authority(application_root / "authority"))
    post_freeze = PostFreezeJonesLibrary.from_document(
        Document.from_bytes(session.fetch(finding.record_references[0]))
    )
    verification = BandVerificationEvidence.from_document(
        Document.from_bytes(session.fetch(finding.record_references[1]))
    )
    assert verification.status is BandVerificationStatus.MISSING_BLIND
    assert verification.spectral_field_family_reference is None
    assert verification.focus_reference is None
    assert post_freeze.missing_wavelengths_nm == post_freeze.blind_wavelengths_nm
    assert len(post_freeze.missing_wavelengths_nm) == 16
    assert all("recorded_periodic_response_missing" in item for item in post_freeze.unavailable_reasons)


def test_continuous_achromatic_numerical_blind_stop_is_not_physics_refusal(
    tmp_path: Path,
) -> None:
    adapter = _FullSpectrumEvidenceAdapter(
        spectral_periodic=True,
        post_freeze_numerical=True,
    )
    application_root = tmp_path / "application-root"

    outcome = conduct(
        continuous_achromatic_publication_brief(),
        application_root=application_root,
        evidence_adapter=adapter,
    )

    assert isinstance(outcome, WaitingStudies)
    finding = next(
        item
        for item in outcome.studies[0].findings
        if item.claim == "post_freeze_jones_library"
    )
    assert finding.kind is FindingKind.INCOMPLETE
    assert finding.needs == (BandVerificationStatus.NUMERICAL_INCOMPLETE.value,)
    session = AuthoritySession(Authority(application_root / "authority"))
    verification = BandVerificationEvidence.from_document(
        Document.from_bytes(session.fetch(finding.record_references[1]))
    )
    assert verification.status is BandVerificationStatus.NUMERICAL_INCOMPLETE
    assert verification.spectral_field_family_reference is None
    assert verification.focus_reference is None


def test_continuous_achromatic_mixed_execution_origins_close_typed_stop(
    tmp_path: Path,
) -> None:
    adapter = _FullSpectrumEvidenceAdapter(
        spectral_periodic=True,
        post_freeze_mixed_origin=True,
    )
    application_root = tmp_path / "application-root"

    outcome = conduct(
        continuous_achromatic_publication_brief(),
        application_root=application_root,
        evidence_adapter=adapter,
    )

    assert isinstance(outcome, WaitingStudies)
    finding = next(
        item
        for item in outcome.studies[0].findings
        if item.claim == "post_freeze_jones_library"
    )
    assert finding.kind is FindingKind.INCOMPLETE
    assert finding.needs == (
        BandVerificationStatus.EVIDENCE_ORIGIN_MISMATCH.value,
    )
    session = AuthoritySession(Authority(application_root / "authority"))
    verification = BandVerificationEvidence.from_document(
        Document.from_bytes(session.fetch(finding.record_references[1]))
    )
    assert verification.status is BandVerificationStatus.EVIDENCE_ORIGIN_MISMATCH
    assert verification.spectral_field_family_reference is None
    assert verification.focus_reference is None


def test_continuous_achromatic_conduct_refuses_insufficient_delay_span(
    tmp_path: Path,
) -> None:
    adapter = _FullSpectrumEvidenceAdapter(spectral_periodic=True)
    brief = replace(
        continuous_achromatic_publication_brief(),
        numerical_aperture=Decimal("0.24719"),
        aperture=None,
        omissions=(
            *continuous_achromatic_publication_brief().omissions,
            "aperture intent",
        ),
    )

    outcome = conduct(
        brief,
        application_root=tmp_path / "application-root",
        evidence_adapter=adapter,
    )

    assert isinstance(outcome, WaitingStudies)
    study = outcome.studies[0]
    refusal = next(
        finding
        for finding in study.findings
        if finding.claim == "qualified_spectral_library"
    )
    assert refusal.kind is FindingKind.REFUSAL
    assert refusal.needs == ("single_rectangle_delay_span_insufficient",)
    assert len(refusal.record_references) == 1
    assert all(fact.claim != "qualified_spectral_library" for fact in study.evidence)


def _result_focus(*, focal_shift_m: float) -> Focus:
    span = HalfMaximum(-1e-6, 1e-6, 2e-6, True)
    distances = (48e-6, 49e-6, 50e-6)
    return Focus(
        expected_focus_m=49e-6,
        found_focus_m=49e-6 + focal_shift_m,
        focal_shift_m=focal_shift_m,
        x_half_maximum=span,
        y_half_maximum=span,
        depth_of_focus=span,
        transmitted_fraction=0.8,
        focused_fraction=0.6,
        focus_efficiency=0.48,
        peak_intensity=1.0,
        airy_radius_m=1.5e-6,
        is_focus_bracketed=True,
        observed_components=("right",),
        convergence=FocusConvergence(3, 1e-6, False),
        axial_distances_m=distances,
        axial_peak_intensities=(0.5, 1.0, 0.5),
        leakage=Leakage(
            channel="retained",
            role="leakage",
            observed_distance_m=49e-6,
            transmitted_fraction=0.03,
            peak_intensity=0.1,
            integrated_intensity=1.0,
            axial_distances_m=distances,
            axial_peak_intensities=(0.1, 0.2, 0.1),
        ),
    )


def test_continuous_achromatic_result_replays_without_numerical_work(
    tmp_path: Path,
) -> None:
    adapter = _FullSpectrumEvidenceAdapter(spectral_periodic=True)
    application_root = tmp_path / "application-root"
    waiting = conduct(
        continuous_achromatic_publication_brief(),
        application_root=application_root,
        evidence_adapter=adapter,
    )
    assert isinstance(waiting, WaitingStudies)
    session = AuthoritySession(Authority(application_root / "authority"))
    evidence = MetalensEvidence(session)
    ready = evidence.recompile(waiting.studies[0], reported_findings=())
    task = ready.ready_tasks[0]
    assert task.claim == "achromatic_focus"
    family_reference = next(
        fact.reference
        for fact in ready.evidence
        if fact.claim == "spectral_field_family"
    )
    family = SpectralFieldFamily.from_document(
        Document.from_bytes(session.fetch(family_reference))
    )
    entries = []
    focus_references = []
    for item in family.entries:
        focus = _result_focus(
            focal_shift_m=(
                0.1e-6 if item.strategy == "continuous compensation" else 1e-6
            )
        )
        focus_reference = evidence.admit_scientific_focus(
            focus,
            focal_region_reference=item.focal_region_reference,
        )
        focus_references.append(focus_reference)
        entries.append(
            AchromaticFocusEntry(
                strategy=item.strategy,
                wavelength_nm=item.wavelength_nm,
                focus_reference=focus_reference,
                focus=focus,
            )
        )
    binding_reference = task.binding_reference
    assert binding_reference is not None
    achromatic_focus = form_achromatic_focus(
        family,
        tuple(entries),
        family_reference=family_reference,
        evaluation_binding_reference=binding_reference,
    )
    focus_reference = evidence.admit_task(
        task,
        achromatic_focus.document(),
        sources=(family_reference, binding_reference, *focus_references),
    )
    focused = evidence.with_fact(ready, task, focus_reference)
    advanced = advance_metalens(
        focused,
        session=session,
        periodic_response=None,
        materials=None,
    )
    assert len(advanced) == 1
    completed = advanced[0]
    assert any(fact.claim == "focus" for fact in completed.evidence), completed.findings

    admitted = _admit_result(session, completed)
    with (
        patch(
            "metacraft.science.metalens._continuous_achromatic.propagate_field",
            side_effect=AssertionError("replay must not propagate"),
        ),
        patch(
            "metacraft.science.metalens._continuous_achromatic.evaluate_focus",
            side_effect=AssertionError("replay must not evaluate focus"),
        ),
    ):
        restored = restore_conclusion(admitted.document, fetch=session.fetch)

    assert isinstance(restored, AchromaticResult)
    assert restored.aperture_reference == family.aperture_reference
    assert restored.focus.compensated_focal_shift_improvement_m == 0.9e-6
    assert restored.document().to_bytes() == admitted.document.to_bytes()


def test_missing_material_registration_is_typed_as_unavailable(
    tmp_path: Path,
) -> None:
    outcome, _adapter = _conduct_until_material_wait(tmp_path / "application-root")

    material_findings = tuple(
        finding
        for study in outcome.studies
        for finding in study.findings
        if finding.claim == "material_binding"
    )

    assert material_findings
    assert all(finding.kind is FindingKind.UNAVAILABLE for finding in material_findings)


def test_typed_unavailability_retries_without_reading_its_reason(
    tmp_path: Path,
) -> None:
    brief = propagation_brief()
    waiting, facts = compile_with_facts(
        brief,
        {"target_phase": reference_for(b"target phase")},
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    waiting = compile_metalens(
        brief,
        evidence=tuple(facts.values()),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
        reported_findings=(
            Finding(
                claim="material_binding",
                kind=FindingKind.UNAVAILABLE,
                needs=("selected registration could not be observed",),
            ),
        ),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    periodic, materials = _idle_evidence_ports(session)

    successors = advance_metalens(
        waiting,
        session=session,
        periodic_response=periodic,
        materials=materials,
    )

    assert successors == ()
    assert materials.calls == 1


def test_refusal_does_not_retry_even_with_a_legacy_unavailable_reason(
    tmp_path: Path,
) -> None:
    brief = propagation_brief()
    waiting, facts = compile_with_facts(
        brief,
        {"target_phase": reference_for(b"target phase")},
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    waiting = compile_metalens(
        brief,
        evidence=tuple(facts.values()),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
        reported_findings=(
            Finding(
                claim="material_binding",
                kind=FindingKind.REFUSAL,
                needs=("material_unavailable:legacy-reason",),
            ),
        ),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    periodic, materials = _idle_evidence_ports(session)

    successors = advance_metalens(
        waiting,
        session=session,
        periodic_response=periodic,
        materials=materials,
    )

    assert successors == ()
    assert materials.calls == 0


def test_existing_application_root_resumes_the_same_brief(
    tmp_path: Path,
) -> None:
    application_root = tmp_path / "application-root"
    _first, adapter = _conduct_until_material_wait(application_root)

    repeated = conduct(
        propagation_brief(),
        application_root=application_root,
        evidence_adapter=adapter,
    )

    assert isinstance(repeated, WaitingStudies)
    assert adapter.open_calls == 2


def test_preparation_does_not_repeat_qualification_for_a_successor(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    session = AuthoritySession(Authority(workspace / "authority"))
    periodic_reference = session.admit_document(
        Document("fixture.periodic_response_binding", {"qualified": True})
    )
    material_reference = session.admit_document(
        Document("fixture.material_response_binding", {"qualified": True})
    )
    periodic = _UnusedPeriodicResponse(
        PeriodicResponseContext(
            binding_reference=periodic_reference,
            capacity_scope="fixture:periodic_response",
            response_kinds=tuple(PeriodicResponseKind),
        )
    )
    materials = _UnavailableMaterials(
        MaterialResponseContext(
            binding_reference=material_reference,
            capacity_scope="fixture:material_response",
        )
    )
    compiled = compile_study(propagation_brief())
    assert isinstance(compiled, Study)

    with patch(
        "metacraft.science.metalens.conduct.observe_angular_spectrum",
        wraps=__import__(
            "metacraft.field.angular_spectrum",
            fromlist=["observe_angular_spectrum"],
        ).observe_angular_spectrum,
    ) as observe:
        prepared = prepare_metalens_study(
            compiled,
            session=session,
            periodic_response=periodic,
            materials=materials,
        )
        repeated = prepare_metalens_study(
            prepared,
            session=session,
            periodic_response=periodic,
            materials=materials,
        )

    assert repeated is prepared
    assert observe.call_count == 1


def test_periodic_context_rejects_unsealed_response_kind() -> None:
    reference = reference_for(b"fixture")

    with pytest.raises(ValueError, match="periodic_response_context_invalid"):
        PeriodicResponseContext(
            binding_reference=reference,
            capacity_scope="fixture:periodic",
            response_kinds=(
                "periodic_transmission_response",  # type: ignore[arg-type]
            ),
        )


def test_one_conduct_call_opens_evidence_once(
    tmp_path: Path,
) -> None:
    adapter = _UnavailableEvidenceAdapter()
    outcome, _adapter = _conduct_until_material_wait(
        tmp_path / "application-root",
        adapter,
    )

    assert isinstance(outcome, WaitingStudies)
    assert adapter.open_calls == 1
    assert adapter.materials is not None
    assert adapter.materials.calls == 1


def test_invalid_brief_does_not_claim_application_root(
    tmp_path: Path,
) -> None:
    application_root = tmp_path / "application-root"
    adapter = _FailingEvidenceAdapter()

    outcome = conduct(
        replace(propagation_brief(), dimension_step_nm=None),
        application_root=application_root,
        evidence_adapter=adapter,
    )

    assert isinstance(outcome, InvalidBrief)
    assert not application_root.exists()
    assert adapter.open_calls == 0


def test_answer_for_absent_application_root_is_rejected_without_claiming_it(
    tmp_path: Path,
) -> None:
    application_root = tmp_path / "application-root"
    answer = ConsultationAnswer(
        request_identity="sha256:unrequested-answer",
        conclusion=Recommendation(
            candidate_identity="sha256:unrequested-candidate",
            reason="answer supplied before any consultation was requested",
            decisive_ground_identities=("sha256:unrequested-ground",),
            external_claim_identities=(),
        ),
        external_claims=(),
    )

    with pytest.raises(
        ConsultationAnswerRejected,
        match="^consultation_answer_rejected:not_required$",
    ) as rejected:
        conduct(
            propagation_brief(),
            application_root=application_root,
            consultation_answer=answer,
        )

    assert rejected.value.reason == "not_required"
    assert not application_root.exists()


def test_evidence_open_fault_leaves_a_resumable_checkpointed_root(
    tmp_path: Path,
) -> None:
    application_root = tmp_path / "application-root"
    adapter = _FailingEvidenceAdapter()

    with pytest.raises(RuntimeError, match="evidence_adapter_open_failed"):
        conduct(
            propagation_brief(),
            application_root=application_root,
            evidence_adapter=adapter,
        )

    assert adapter.open_calls == 1
    assert {path.name for path in application_root.iterdir()} == {
        "authority",
        "runs",
    }
    with pytest.raises(RuntimeError, match="evidence_adapter_open_failed"):
        conduct(
            propagation_brief(),
            application_root=application_root,
            evidence_adapter=adapter,
        )
    assert adapter.open_calls == 2


@pytest.mark.parametrize(
    "opened",
    (
        None,
        (),
        (object(),),
        [object(), object()],
    ),
)
def test_evidence_open_rejects_a_non_pair_shape(
    tmp_path: Path,
    opened: object,
) -> None:
    with pytest.raises(TypeError, match="^metalens_evidence_pair_invalid$"):
        conduct(
            propagation_brief(),
            application_root=tmp_path / "application-root",
            evidence_adapter=_MalformedEvidenceAdapter(opened),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("opened", "finding"),
    (
        ((object(), object()), "metalens_periodic_response_invalid"),
        (
            (
                _UnusedPeriodicResponse(
                    PeriodicResponseContext(
                        binding_reference=reference_for(b"unobserved"),
                        capacity_scope="fixture:periodic_response",
                        response_kinds=tuple(PeriodicResponseKind),
                    )
                ),
                object(),
            ),
            "metalens_material_response_invalid",
        ),
    ),
)
def test_evidence_open_rejects_unusable_ports(
    tmp_path: Path,
    opened: object,
    finding: str,
) -> None:
    with pytest.raises(TypeError, match=f"^{finding}$"):
        conduct(
            propagation_brief(),
            application_root=tmp_path / "application-root",
            evidence_adapter=_MalformedEvidenceAdapter(opened),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("should_foreign_materials", (False, True))
def test_evidence_open_rejects_foreign_authority_contexts(
    tmp_path: Path,
    should_foreign_materials: bool,
) -> None:
    adapter = _ForeignEvidenceAdapter(
        tmp_path / "foreign-authority",
        should_foreign_materials=should_foreign_materials,
    )

    with pytest.raises(RuntimeError, match="^reference_unresolvable"):
        conduct(
            propagation_brief(),
            application_root=tmp_path / "application-root",
            evidence_adapter=adapter,
        )

    assert adapter.materials is not None
    assert adapter.materials.calls == 0


def test_empty_height_domain_remains_admitted_until_choice_advice(
    tmp_path: Path,
) -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(940),
        cell_period_nm=520,
        dimension_step_nm=100,
    )
    initial = compile_metalens(brief)
    solver_body = b'"fixture solver"'
    sample_body = b'"fixture material sample"'
    binding = replace(
        material_binding(initial),
        solver_binding_reference=reference_for(solver_body),
        sample_reference=reference_for(sample_body),
    )
    binding = replace(
        binding,
        evidence_reference=reference_for(binding.document().to_bytes()),
    )
    domain = derive_period_domain(initial, binding)
    domain = domain.bind_evidence(reference_for(domain.document().to_bytes()))
    before_choice, _facts = compile_with_facts(
        brief,
        {
            "target_phase": reference_for(b"target phase"),
            "material_binding": binding.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    choice = resolve_period_choice(before_choice, domain)
    assert isinstance(choice, PeriodChoice)
    choice = choice.bind_evidence(reference_for(choice.document().to_bytes()))
    ready, _facts = compile_with_facts(
        brief,
        {
            "target_phase": reference_for(b"target phase"),
            "material_binding": binding.evidence_reference,
            "period_domain": domain.evidence_reference,
            "period_choice": choice.evidence_reference,
        },
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    assert (
        session.admit_object(
            solver_body,
            media_type="application/json",
            descriptive_metadata={},
        )
        == binding.solver_binding_reference
    )
    assert (
        session.admit_object(
            sample_body,
            media_type="application/json",
            descriptive_metadata={},
        )
        == binding.sample_reference
    )
    assert session.admit_document(binding.document()) == binding.evidence_reference
    assert session.admit_document(choice.document()) == choice.evidence_reference
    periodic, materials = _idle_evidence_ports(session)

    (after_domain,) = advance_metalens(
        ready,
        session=session,
        periodic_response=periodic,
        materials=materials,
    )

    height_fact = next(
        fact for fact in after_domain.evidence if fact.claim == "height_domain"
    )
    admitted_domain = HeightDomain.from_document(
        Document.from_bytes(session.fetch(height_fact.reference)),
        evidence_reference=height_fact.reference,
    )
    assert not admitted_domain.heights_nm
    assert not any(
        finding.needs == ("fabrication_domain_empty",)
        for finding in after_domain.findings
    )

    (after_envelope,) = advance_metalens(
        after_domain,
        session=session,
        periodic_response=periodic,
        materials=materials,
    )

    assert any(
        finding.claim == "height_choice"
        and finding.kind is FindingKind.ADVICE
        and finding.needs == ("height",)
        for finding in after_envelope.findings
    )


def test_period_consultation_unavailable_keeps_compiler_waiting_advice(
    tmp_path: Path,
) -> None:
    brief = propagation_brief()
    initial = compile_metalens(brief)
    domain = period_domain(initial)
    waiting, _facts = compile_with_facts(
        brief,
        {
            "target_phase": reference_for(b"target phase"),
            "material_binding": material_binding(initial).evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    assert session.admit_document(domain.document()) == domain.evidence_reference
    periodic, materials = _idle_evidence_ports(session)

    successors = advance_metalens(
        waiting,
        session=session,
        periodic_response=periodic,
        materials=materials,
    )

    assert successors == ()
    assert any(
        finding.claim == "period_choice"
        and finding.kind is FindingKind.ADVICE
        and finding.needs == ("period",)
        for finding in waiting.findings
    )


def test_height_consultation_unavailable_keeps_compiler_waiting_advice(
    tmp_path: Path,
) -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(940),
        cell_period_nm=520,
    )
    initial = compile_metalens(brief)
    domain = height_domain(initial)
    envelope = phase_envelope(initial, domain)
    waiting, _facts = compile_with_facts(
        brief,
        {
            "target_phase": reference_for(b"target phase"),
            "material_binding": material_binding(initial).evidence_reference,
            "period_domain": period_domain(initial).evidence_reference,
            "period_choice": period_choice(initial).evidence_reference,
            "height_domain": domain.evidence_reference,
            "phase_envelope": envelope.evidence_reference,
        },
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    assert session.admit_document(domain.document()) == domain.evidence_reference
    assert session.admit_document(envelope.document()) == envelope.evidence_reference
    periodic, materials = _idle_evidence_ports(session)

    successors = advance_metalens(
        waiting,
        session=session,
        periodic_response=periodic,
        materials=materials,
    )

    assert successors == ()
    assert any(
        finding.claim == "height_choice"
        and finding.kind is FindingKind.ADVICE
        and finding.needs == ("height",)
        for finding in waiting.findings
    )


def test_conduct_repeats_and_accepts_the_exact_period_request(
    tmp_path: Path,
    monkeypatch,
) -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(940),
        numerical_aperture=Decimal("0.3"),
    )
    application_root = tmp_path / "application-root"
    ports = fake_metalens_ports(
        brief,
        application_root,
        monkeypatch,
        response_proof=PeriodicResponseProof(
            response_qualifications=(
                PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
                PeriodicResponseQualification.qualified(PERIODIC_POLARIZATION_RESPONSE),
                PeriodicResponseQualification.qualified(
                    PERIODIC_REFERENCE_SURFACE_RESPONSE
                ),
            )
        ),
    )

    first = conduct(brief, **ports)
    assert isinstance(first, ConsultationRequired)
    assert first.request.question_kind.value == "period"
    authority = Authority(application_root / "authority")
    revision = authority.view().revision

    repeated = conduct(brief, application_root=application_root)
    assert isinstance(repeated, ConsultationRequired)
    assert repeated.request.document().to_bytes() == (
        first.request.document().to_bytes()
    )
    assert authority.view().revision == revision

    with pytest.raises(ValueError, match="^application_root_brief_mismatch$"):
        conduct(
            replace(brief, wording="A different immutable brief."),
            application_root=application_root,
        )
    assert authority.view().revision == revision

    stale = ConsultationAnswer(
        request_identity="sha256:stale-request",
        conclusion=Recommendation(
            candidate_identity=repeated.request.candidates[0].identity,
            reason="stale fixture answer",
            decisive_ground_identities=(repeated.request.grounds[-1].identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )
    with pytest.raises(
        ConsultationAnswerRejected,
        match="^consultation_answer_rejected:stale$",
    ) as rejected:
        conduct(
            brief,
            application_root=application_root,
            consultation_answer=stale,
        )
    assert authority.view().revision == revision
    assert rejected.value.reason == "stale"

    invalid = ConsultationAnswer(
        request_identity=repeated.request.identity,
        conclusion=Recommendation(
            candidate_identity="sha256:invented-candidate",
            reason="invented fixture answer",
            decisive_ground_identities=(repeated.request.grounds[-1].identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )
    with pytest.raises(
        ConsultationAnswerRejected,
        match="^consultation_answer_rejected:invalid$",
    ) as rejected_invalid:
        conduct(
            brief,
            application_root=application_root,
            consultation_answer=invalid,
        )
    assert rejected_invalid.value.reason == "invalid"
    assert authority.view().revision == revision

    candidate = next(
        item for item in repeated.request.candidates if item.quantity == Decimal(290)
    )
    answer = ConsultationAnswer(
        request_identity=repeated.request.identity,
        conclusion=Recommendation(
            candidate_identity=candidate.identity,
            reason="fixture period inside physical ceilings",
            decisive_ground_identities=(repeated.request.grounds[-1].identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )

    resumed = conduct(
        brief,
        application_root=application_root,
        consultation_answer=answer,
    )

    assert isinstance(resumed, ConsultationRequired)
    assert resumed.request.question_kind.value == "height"
    with pytest.raises(
        ConsultationAnswerRejected,
        match="^consultation_answer_rejected:duplicate$",
    ):
        conduct(
            brief,
            application_root=application_root,
            consultation_answer=answer,
        )

    height_candidate = next(
        item for item in resumed.request.candidates if item.quantity == Decimal(550)
    )
    height_answer = ConsultationAnswer(
        request_identity=resumed.request.identity,
        conclusion=Recommendation(
            candidate_identity=height_candidate.identity,
            reason="fixture height inside the admitted domain",
            decisive_ground_identities=(resumed.request.grounds[-1].identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )
    after_height = conduct(
        brief,
        application_root=application_root,
        consultation_answer=height_answer,
    )
    assert isinstance(after_height, WaitingStudies)


def _pending_period_answer(tmp_path: Path, monkeypatch):
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(940),
        numerical_aperture=Decimal("0.3"),
    )
    application_root = tmp_path / "application-root"
    ports = fake_metalens_ports(
        brief,
        application_root,
        monkeypatch,
        response_proof=PeriodicResponseProof(
            response_qualifications=(
                PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
                PeriodicResponseQualification.qualified(PERIODIC_POLARIZATION_RESPONSE),
                PeriodicResponseQualification.qualified(
                    PERIODIC_REFERENCE_SURFACE_RESPONSE
                ),
            )
        ),
    )
    required = conduct(brief, **ports)
    assert isinstance(required, ConsultationRequired)
    candidate = next(
        item for item in required.request.candidates if item.quantity == Decimal(290)
    )
    answer = ConsultationAnswer(
        request_identity=required.request.identity,
        conclusion=Recommendation(
            candidate_identity=candidate.identity,
            reason="fixture period inside physical ceilings",
            decisive_ground_identities=(required.request.grounds[-1].identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )
    return brief, application_root, answer


def test_advice_construction_fault_crosses_generic_conduct_directly(
    tmp_path: Path,
    monkeypatch,
) -> None:
    brief, application_root, answer = _pending_period_answer(
        tmp_path,
        monkeypatch,
    )

    with (
        patch(
            "metacraft.science.metalens.consultation.PeriodAdvice",
            side_effect=_SentinelFailure("advice construction sentinel"),
        ),
        pytest.raises(_SentinelFailure),
    ):
        conduct(
            brief,
            application_root=application_root,
            consultation_answer=answer,
        )


def test_authority_admission_fault_crosses_generic_conduct_directly(
    tmp_path: Path,
    monkeypatch,
) -> None:
    brief, application_root, answer = _pending_period_answer(
        tmp_path,
        monkeypatch,
    )

    with (
        patch(
            "metacraft.science.metalens.evidence.MetalensEvidence.admit_document",
            side_effect=_SentinelFailure("Authority admission sentinel"),
        ),
        pytest.raises(_SentinelFailure),
    ):
        conduct(
            brief,
            application_root=application_root,
            consultation_answer=answer,
        )


def test_authority_admission_reference_mismatch_remains_direct(
    tmp_path: Path,
    monkeypatch,
) -> None:
    brief, application_root, answer = _pending_period_answer(
        tmp_path,
        monkeypatch,
    )

    with (
        patch(
            "metacraft.science.metalens.evidence.MetalensEvidence.admit_document",
            return_value=reference_for(b"wrong admitted advice"),
        ),
        pytest.raises(
            RuntimeError,
            match="^advice_admission_reference_mismatch$",
        ),
    ):
        conduct(
            brief,
            application_root=application_root,
            consultation_answer=answer,
        )


def test_frontier_replacement_fault_crosses_generic_conduct_directly(
    tmp_path: Path,
    monkeypatch,
) -> None:
    brief, application_root, answer = _pending_period_answer(
        tmp_path,
        monkeypatch,
    )

    with (
        patch(
            "metacraft.science.conduct._try_admit_frontier",
            side_effect=_SentinelFailure("frontier replacement sentinel"),
        ),
        pytest.raises(_SentinelFailure),
    ):
        conduct(
            brief,
            application_root=application_root,
            consultation_answer=answer,
        )


def test_post_advice_frontier_conflict_does_not_advance_current_science(
    tmp_path: Path,
    monkeypatch,
) -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(940),
        numerical_aperture=Decimal("0.3"),
    )
    application_root = tmp_path / "application-root"
    ports = fake_metalens_ports(
        brief,
        application_root,
        monkeypatch,
        response_proof=PeriodicResponseProof(
            response_qualifications=(
                PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
                PeriodicResponseQualification.qualified(PERIODIC_POLARIZATION_RESPONSE),
                PeriodicResponseQualification.qualified(
                    PERIODIC_REFERENCE_SURFACE_RESPONSE
                ),
            )
        ),
    )
    required = conduct(brief, **ports)
    assert isinstance(required, ConsultationRequired)
    candidate = next(
        item for item in required.request.candidates if item.quantity == Decimal(290)
    )
    answer = ConsultationAnswer(
        request_identity=required.request.identity,
        conclusion=Recommendation(
            candidate_identity=candidate.identity,
            reason="fixture period inside physical ceilings",
            decisive_ground_identities=(required.request.grounds[-1].identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )
    authority = Authority(application_root / "authority")
    session = AuthoritySession(authority)
    frontier_key = StudyFrontier.start(required.studies[0]).key
    frontier_reference = session.current_reference(frontier_key)
    assert frontier_reference is not None
    frontier_bytes = session.fetch(frontier_reference)
    current_before = authority.view().current

    with (
        patch("metacraft.science.conduct._try_admit_frontier", return_value=None),
        pytest.raises(RuntimeError, match="^consultation_frontier_conflict$"),
    ):
        conduct(
            brief,
            application_root=application_root,
            consultation_answer=answer,
        )

    after = AuthoritySession(authority)
    assert authority.view().current == current_before
    assert after.current_reference(frontier_key) == frontier_reference
    assert after.fetch(frontier_reference) == frontier_bytes


def test_completed_application_root_restores_without_external_work(
    tmp_path: Path,
) -> None:
    application_root = tmp_path / "completed-root"
    recorded = propagation_result(application_root, 8)
    (application_root / "runs").mkdir()
    frontier = StudyFrontier.start(recorded.study)
    frontier_reference = recorded.session.admit_current(
        frontier.document(),
        key=frontier.key,
        supersedes=None,
        references=frontier.references(),
    )
    result = _admit_result(recorded.session, recorded.study)
    completed = CompletedResults((result,))
    _admit_completed_results(
        recorded.session,
        recorded.study,
        completed,
        frontier=frontier,
        frontier_reference=frontier_reference,
    )
    revision = recorded.authority.view().revision

    restored = conduct(
        recorded.study.brief,
        application_root=application_root,
    )

    assert isinstance(restored, CompletedResults)
    assert tuple(item.reference for item in restored.results) == (result.reference,)
    assert recorded.authority.view().revision == revision
