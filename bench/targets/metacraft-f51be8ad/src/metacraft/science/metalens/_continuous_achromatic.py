from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Protocol

from ...authority import Document, Reference
from ...authority.session import AuthoritySession
from ...field import Field
from ...field.angular_spectrum import (
    ANGULAR_SPECTRUM_REALIZATION,
    AngularSpectrumRealization,
    FieldMemoryUnavailable,
    observe_angular_spectrum,
    propagate_field,
    qualify_angular_spectrum,
)
from ...materials import (
    MaterialObservationRequest,
    MaterialResponse,
    MaterialUnavailable,
)

from ..periodic_response import (
    ObservedPeriodicPolarization,
    PeriodicPolarizationIncomplete,
    PeriodicResponse,
    PeriodicResponseKind,
    PeriodicResponseUnavailable,
)
from ..relationships import Method, Relationship
from ..study import Binding, Capability, Evidence, Finding, FindingKind, Study, Task

from . import achromatic
from . import aperture as aperture_science
from .brief import ContinuousBandSpectrum, MetalensBrief
from .design import require_metalens_design
from .geometric_phase import PolarizationConvention
from .focus import (
    FOCUS_SURVEY_SCHEMA,
    FocalRegion,
    Focus,
    FocusSurvey,
    evaluate_focus,
    observe_focal_region,
)
from .focus_evidence import restore_focal_region
from .material import validate_material_observation


class _Evidence(Protocol):
    """
    Expose only Authority-backed operations needed by this Method.
    """

    def admit_task(
        self,
        task: Task,
        document: Document,
        *,
        sources: tuple[Reference, ...] = (),
    ) -> Reference:
        """
        Admit one exact task result and its direct sources.
        """

        ...

    def with_fact(
        self,
        study: Study,
        task: Task,
        reference: Reference,
    ) -> Study:
        """
        Recompile with one admitted task fact.
        """

        ...

    def with_unavailable(
        self,
        study: Study,
        task: Task,
        reason: str,
    ) -> Study:
        """
        Recompile with one typed external-unavailability finding.
        """

        ...

    def with_finding(self, study: Study, finding: Finding) -> Study:
        """
        Recompile with one aim-owned finding.
        """

        ...

    def recompile(
        self,
        study: Study,
        *,
        capabilities: tuple[Capability, ...] | None = None,
        bindings: tuple[Binding, ...] | None = None,
    ) -> Study:
        """
        Recompile with the selected exact capabilities and bindings.
        """

        ...

    def fact(self, study: Study, claim: str) -> Evidence:
        """
        Return the sole admitted evidence for a claim.
        """

        ...

    def fetch(self, reference: Reference) -> bytes:
        """
        Fetch exact admitted bytes.
        """

        ...

    def observe_admitted(self, reference: Reference) -> None:
        """
        Require a reference already admitted to Authority.
        """

        ...

    def admit_scientific_field(self, field: Field) -> Reference:
        """Admit one exact child Field."""

        ...

    def admit_scientific_focal_region(
        self,
        region: FocalRegion,
        *,
        binding_reference: Reference,
        field_reference: Reference,
    ) -> Reference:
        """Admit one exact child focal region."""

        ...

    def admit_scientific_focus(
        self,
        focus: Focus,
        *,
        focal_region_reference: Reference,
    ) -> Reference:
        """Admit one exact child Focus."""

        ...

    def admit_document(
        self,
        document: Document,
        *,
        sources: tuple[Reference, ...] = (),
    ) -> Reference:
        """Admit one compound child document."""

        ...


def relationship() -> Relationship:
    """
    Declare the bounded transmissive PB-dispersion proof as one deep Method.
    """

    return Relationship(
        aim="metalens",
        objectives=("focus",),
        applicability=(
            "continuous operating spectrum; circular input; primitive "
            "anisotropic rectangular fin with evidence-supported materials; square-period "
            "transmissive PB-dispersion realization"
        ),
        methods=(
            Method(
                "derive_achromatic_target",
                "achromatic_target",
                (),
                None,
                achromatic.ACHROMATIC_TARGET_SCHEMA,
            ),
            Method(
                "retain_response_qualification_profile",
                "response_qualification_profile",
                ("achromatic_target",),
                None,
                achromatic.RESPONSE_QUALIFICATION_PROFILE_SCHEMA,
            ),
            Method(
                "specify_spectral_campaign",
                "spectral_study_specification",
                ("achromatic_target", "response_qualification_profile"),
                None,
                achromatic.SPECTRAL_STUDY_SPECIFICATION_SCHEMA,
            ),
            Method(
                "bind_spectral_materials",
                "spectral_material_binding",
                ("achromatic_target", "spectral_study_specification"),
                "spectral_optical_material",
                achromatic.SPECTRAL_MATERIAL_BINDING_SCHEMA,
            ),
            Method(
                "plan_spectral_cell_study",
                "spectral_cell_study_plan",
                (
                    "achromatic_target",
                    "spectral_material_binding",
                    "spectral_study_specification",
                ),
                "fabrication_constraint",
                achromatic.SPECTRAL_CELL_STUDY_PLAN_SCHEMA,
            ),
            Method(
                "resolve_physical_lattice",
                "physical_lattice",
                ("spectral_cell_study_plan",),
                None,
                aperture_science.PHYSICAL_LATTICE_SCHEMA,
            ),
            Method(
                "screen_spectral_cells",
                "spectral_cell_screen",
                ("spectral_cell_study_plan", "physical_lattice"),
                "periodic_polarization_response",
                achromatic.SPECTRAL_CELL_SCREEN_SCHEMA,
            ),
            Method(
                "observe_spectral_jones",
                "spectral_jones_library",
                ("spectral_cell_study_plan", "spectral_cell_screen"),
                "periodic_polarization_response",
                achromatic.SPECTRAL_JONES_LIBRARY_SCHEMA,
            ),
            Method(
                "qualify_spectral_response",
                "qualified_spectral_library",
                ("achromatic_target", "spectral_jones_library"),
                None,
                achromatic.QUALIFIED_SPECTRAL_LIBRARY_SCHEMA,
            ),
            Method(
                "assign_achromatic_aperture",
                "achromatic_aperture",
                (
                    "achromatic_target",
                    "qualified_spectral_library",
                    "physical_lattice",
                ),
                "deterministic_selection",
                achromatic.ACHROMATIC_APERTURE_SCHEMA,
            ),
            Method(
                "observe_post_freeze_jones",
                "post_freeze_jones_library",
                ("achromatic_aperture", "response_qualification_profile"),
                "periodic_polarization_response",
                achromatic.POST_FREEZE_JONES_LIBRARY_SCHEMA,
            ),
            Method(
                "form_spectral_fields",
                "spectral_field_family",
                (
                    "achromatic_aperture",
                    "qualified_spectral_library",
                    "post_freeze_jones_library",
                ),
                "angular_spectrum_propagation",
                achromatic.SPECTRAL_FIELD_FAMILY_SCHEMA,
            ),
            Method(
                "evaluate_achromatic_focus",
                "achromatic_focus",
                ("spectral_field_family",),
                "focus_evaluation",
                achromatic.ACHROMATIC_FOCUS_SCHEMA,
            ),
            Method(
                "verify_achromatic_band",
                "focus",
                (
                    "post_freeze_jones_library",
                    "spectral_field_family",
                    "achromatic_focus",
                ),
                None,
                achromatic.BAND_VERIFICATION_EVIDENCE_SCHEMA,
            ),
        ),
    )


def owns(study: Study) -> bool:
    """
    Report whether this Module owns the Study's compiled spectrum.
    """

    return isinstance(
        require_metalens_design(study).operating_spectrum,
        ContinuousBandSpectrum,
    )


def prepare(
    study: Study,
    *,
    evidence: _Evidence,
    session: AuthoritySession,
    periodic_response: PeriodicResponse | None,
    materials: MaterialResponse | None,
) -> Study:
    """
    Bind every capability named by this exact continuous proof once.
    """

    required = {
        claim.capability for claim in study.proof.claims if claim.capability is not None
    }
    selected = {
        binding.capability: binding
        for binding in study.bindings
        if binding.capability in required
    }
    missing = required - set(selected)
    if not missing:
        return study
    bindings: list[Binding] = []
    local_operations = {
        "fabrication_constraint": ("plan_spectral_cell_study",),
        "deterministic_selection": ("assign_achromatic_aperture",),
        "focus_evaluation": ("evaluate_achromatic_focus",),
    }
    for capability in sorted(missing & set(local_operations)):
        bindings.append(
            Binding(
                capability,
                _admit_binding(
                    session,
                    capability,
                    local_operations[capability],
                ),
            )
        )
    if "periodic_polarization_response" in missing and periodic_response is not None:
        context = periodic_response.context
        session.observe_admitted(context.binding_reference)
        if PeriodicResponseKind.POLARIZATION in context.response_kinds:
            bindings.append(
                Binding(
                    PeriodicResponseKind.POLARIZATION.value,
                    context.binding_reference,
                    context.capacity_scope,
                )
            )
    if "spectral_optical_material" in missing and materials is not None:
        context = materials.context
        session.observe_admitted(context.binding_reference)
        bindings.append(
            Binding(
                "spectral_optical_material",
                context.binding_reference,
                context.capacity_scope,
            )
        )
    if "angular_spectrum_propagation" in missing:
        realization = observe_angular_spectrum()
        qualification = qualify_angular_spectrum(realization)
        if qualification.is_qualified:
            bindings.append(
                Binding(
                    "angular_spectrum_propagation",
                    session.admit_document(
                        Document(
                            "metacraft.binding.angular_spectrum_propagation",
                            {
                                "operations": ["propagate_field"],
                                "qualification": qualification.as_mapping(),
                                "qualified": True,
                                "realization": realization.as_mapping(),
                            },
                        )
                    ),
                )
            )
    for binding in bindings:
        if binding.capability in required:
            selected.setdefault(binding.capability, binding)
    if not bindings:
        return study
    return evidence.recompile(
        study,
        capabilities=tuple(Capability(name) for name in sorted(selected)),
        bindings=tuple(selected[name] for name in sorted(selected)),
    )


def advance(
    evidence: _Evidence,
    study: Study,
    task: Task,
    *,
    periodic_response: PeriodicResponse | None,
    materials: MaterialResponse | None,
) -> Study:
    """
    Interpret one ready task under the closed continuous Method vocabulary.
    """

    match task.method:
        case "derive_achromatic_target":
            return _derive_target(evidence, study, task)
        case "retain_response_qualification_profile":
            return _retain_response_qualification_profile(evidence, study, task)
        case "specify_spectral_campaign":
            return _specify_spectral_campaign(evidence, study, task)
        case "bind_spectral_materials":
            return (
                study
                if materials is None
                else _bind_materials(evidence, materials, study, task)
            )
        case "plan_spectral_cell_study":
            return _plan_cell_study(evidence, study, task)
        case "resolve_physical_lattice":
            return _resolve_physical_lattice(evidence, study, task)
        case "screen_spectral_cells":
            return (
                study
                if periodic_response is None
                else _screen_cells(
                    evidence,
                    periodic_response,
                    study,
                    task,
                )
            )
        case "observe_spectral_jones":
            return (
                study
                if periodic_response is None
                else _observe_jones(
                    evidence,
                    periodic_response,
                    study,
                    task,
                )
            )
        case "qualify_spectral_response":
            return _qualify(evidence, study, task)
        case "assign_achromatic_aperture":
            return _assign_aperture(evidence, study, task)
        case "observe_post_freeze_jones":
            return (
                study
                if periodic_response is None
                else _observe_post_freeze_jones(
                    evidence,
                    periodic_response,
                    study,
                    task,
                )
            )
        case "form_spectral_fields":
            return _form_spectral_fields(evidence, study, task)
        case "evaluate_achromatic_focus":
            return _evaluate_achromatic_focus(evidence, study, task)
        case "verify_achromatic_band":
            return _verify_achromatic_band(evidence, study, task)
        case _:
            raise RuntimeError(f"continuous_achromatic_method_unbound:{task.method}")


def _admit_binding(
    session: AuthoritySession,
    capability: str,
    operations: tuple[str, ...],
) -> Reference:
    return session.admit_document(
        Document(
            f"metacraft.binding.{capability}",
            {"capability": capability, "operations": list(operations)},
        )
    )


def _derive_target(
    evidence: _Evidence,
    study: Study,
    task: Task,
) -> Study:
    target = achromatic.AchromaticTarget.from_design(require_metalens_design(study))
    reference = evidence.admit_task(task, target.document())
    return evidence.with_fact(study, task, reference)


def _retain_response_qualification_profile(
    evidence: _Evidence,
    study: Study,
    task: Task,
) -> Study:
    """Freeze the pre-Native engineering gates and their review identity."""

    review = Document(
        achromatic.RESPONSE_QUALIFICATION_PROFILE_REVIEW_SCHEMA,
        {
            "classification": "pre-registered engineering qualification; not a device publication gate",
            "decision": "continuous-achromatic single-rectangle engineering profile v1",
            "frozen_before_native_outcomes": True,
            "sources": [
                "ADR 0024 bounded response work",
                "ADR 0028 continuous PB and spectral response",
                "owner-approved continuous-achromatic-scientific-compilation spec",
                "owner-approved ticket 03 qualification contract (2026-08-15)",
            ],
            "threshold_rationale": {
                "maximum_dense_phase_residual_rad": "0.20 engineering interpolation diagnostic",
                "maximum_full_band_leakage_power": "0.20 cell eligibility ceiling",
                "maximum_interleaved_phase_residual_rad": "0.15 pre-freeze interpolation diagnostic",
                "maximum_phase_curvature_rad": "0.10 dense-grid smoothness diagnostic",
                "maximum_reference_phase_gap_rad": "pi/2 reference-phase coverage ceiling",
                "minimum_design_r_squared": "0.99 angular-frequency linearity diagnostic",
                "minimum_full_band_converted_power": "0.05 cell eligibility floor",
                "minimum_reference_converted_power": "0.05 reference-screen floor",
            },
        },
    )
    review_reference = evidence.admit_document(review)
    profile = achromatic.ResponseQualificationProfile(
        version="pre-registered-engineering-v1",
        provenance=(
            "engineering cell eligibility only",
            "device publication gates remain outside candidate qualification",
        ),
        source_references=(review_reference,),
        minimum_reference_converted_power=Decimal("0.05"),
        minimum_full_band_converted_power=Decimal("0.05"),
        maximum_full_band_leakage_power=Decimal("0.20"),
        minimum_design_r_squared=Decimal("0.99"),
        maximum_interleaved_phase_residual_rad=Decimal("0.15"),
        maximum_reference_phase_gap_rad=Decimal("1.5707963267948966"),
        maximum_dense_phase_residual_rad=Decimal("0.20"),
        maximum_phase_curvature_rad=Decimal("0.10"),
    )
    profile_reference = evidence.admit_task(
        task,
        profile.document(),
        sources=(review_reference,),
    )
    return evidence.with_fact(study, task, profile_reference)


def _specify_spectral_campaign(
    evidence: _Evidence,
    study: Study,
    task: Task,
) -> Study:
    target = _restore_target(evidence, study)
    profile_reference = evidence.fact(
        study,
        "response_qualification_profile",
    ).reference
    profile = achromatic.ResponseQualificationProfile.from_document(
        Document.from_bytes(evidence.fetch(profile_reference))
    )
    specification = achromatic.form_spectral_study_specification(
        target,
        qualification_profile_reference=profile_reference,
    )
    reference = evidence.admit_task(
        task,
        specification.document(),
        sources=(profile_reference,),
    )
    return evidence.with_fact(study, task, reference)


def _bind_materials(
    evidence: _Evidence,
    materials: MaterialResponse,
    study: Study,
    task: Task,
) -> Study:
    brief = _require_brief(study)
    target = _restore_target(evidence, study)
    specification_reference = evidence.fact(
        study,
        "spectral_study_specification",
    ).reference
    specification = achromatic.SpectralStudySpecification.from_document(
        Document.from_bytes(evidence.fetch(specification_reference))
    )
    expected_binding = _required_reference(task.binding_reference)
    points: list[achromatic.SpectralMaterialPoint] = []
    sources: list[Reference] = []
    native_names: dict[str, str] = {}
    for wavelength_nm in specification.full_band_wavelengths_nm:
        request = MaterialObservationRequest(
            families=(brief.atom.material.family, brief.substrate.family),
            wavelength_nm=wavelength_nm,
        )
        outcome = materials.observe(request)
        if isinstance(outcome, MaterialUnavailable):
            if outcome.request_identity != request.identity:
                raise RuntimeError("material_outcome_request_mismatch")
            suffix = (
                f":{outcome.native_name}" if outcome.native_name is not None else ""
            )
            return evidence.with_unavailable(
                study,
                task,
                (
                    f"spectral_material_unavailable:{wavelength_nm}:"
                    f"{outcome.reason.value}:{outcome.family}{suffix}"
                ),
            )
        validate_material_observation(
            request,
            outcome,
            expected_binding_reference=expected_binding,
        )
        for selection in outcome.selections:
            evidence.observe_admitted(selection.reference)
        evidence.observe_admitted(outcome.sample_reference)
        sources.append(outcome.sample_reference)
        by_family = {material.family: material for material in outcome.materials}
        atom = by_family[brief.atom.material.family]
        substrate = by_family[brief.substrate.family]
        native_names.setdefault(atom.family, atom.native_name)
        native_names.setdefault(substrate.family, substrate.native_name)
        if (
            native_names[atom.family] != atom.native_name
            or native_names[substrate.family] != substrate.native_name
        ):
            raise RuntimeError("spectral_material_native_identity_mismatch")
        points.append(
            achromatic.SpectralMaterialPoint(
                wavelength_nm=wavelength_nm,
                atom_refractive_index=atom.refractive_index,
                atom_extinction_coefficient=atom.extinction_coefficient,
                substrate_refractive_index=substrate.refractive_index,
                substrate_extinction_coefficient=substrate.extinction_coefficient,
            )
        )
    binding = achromatic.SpectralMaterialBinding(
        atom_family=brief.atom.material.family,
        atom_native_name=native_names[brief.atom.material.family],
        substrate_family=brief.substrate.family,
        substrate_native_name=native_names[brief.substrate.family],
        points=tuple(points),
        solver_binding_reference=expected_binding,
        source_references=tuple(sources),
    )
    reference = evidence.admit_task(
        task,
        binding.document(),
        sources=(expected_binding, *sources),
    )
    return evidence.with_fact(study, task, reference)


def _plan_cell_study(
    evidence: _Evidence,
    study: Study,
    task: Task,
) -> Study:
    design = require_metalens_design(study)
    brief = _require_brief(study)
    if brief.dimension_step_nm is None:
        raise RuntimeError("dimension_step_missing_after_compilation")
    target = _restore_target(evidence, study)
    material_reference = evidence.fact(
        study,
        "spectral_material_binding",
    ).reference
    binding = achromatic.SpectralMaterialBinding.from_document(
        Document.from_bytes(evidence.fetch(material_reference))
    )
    specification_reference = evidence.fact(
        study,
        "spectral_study_specification",
    ).reference
    specification = achromatic.SpectralStudySpecification.from_document(
        Document.from_bytes(evidence.fetch(specification_reference))
    )
    plan = achromatic.form_spectral_cell_study_plan(
        target,
        binding,
        material_binding_reference=material_reference,
        dimension_step_nm=brief.dimension_step_nm,
        aspect_limit=design.aspect_limit,
        specification=specification,
        specification_reference=specification_reference,
    )
    if isinstance(plan, achromatic.SpectralEvidenceRequirement):
        return evidence.with_unavailable(study, task, plan.reason)
    if isinstance(plan, achromatic.SpectralCampaignStop):
        return evidence.with_finding(
            study,
            Finding(
                claim=task.claim,
                kind=FindingKind.REFUSAL,
                needs=(
                    plan.reason,
                    f"projected_work_count:{plan.projected_work_count}",
                    f"authorized_work_ceiling:{plan.authorized_work_ceiling}",
                ),
                record_references=(material_reference, specification_reference),
            ),
        )
    reference = evidence.admit_task(
        task,
        plan.document(),
        sources=(material_reference, specification_reference),
    )
    return evidence.with_fact(study, task, reference)


def _resolve_physical_lattice(
    evidence: _Evidence,
    study: Study,
    task: Task,
) -> Study:
    plan_reference = evidence.fact(study, "spectral_cell_study_plan").reference
    plan = achromatic.SpectralCellStudyPlan.from_document(
        Document.from_bytes(evidence.fetch(plan_reference))
    )
    resolved = aperture_science.resolve_lattice(
        require_metalens_design(study),
        spacing_nm=plan.period_nm,
        spacing_source_reference=plan_reference,
    )
    if isinstance(resolved, aperture_science.ApertureIntentMismatch):
        return evidence.with_finding(
            study,
            Finding(
                claim=task.claim,
                kind=FindingKind.REFUSAL,
                needs=(resolved.reason,),
                record_references=(plan_reference,),
            ),
        )
    reference = evidence.admit_task(
        task,
        resolved.document(),
        sources=(plan_reference,),
    )
    return evidence.with_fact(study, task, reference)


def _screen_cells(
    evidence: _Evidence,
    periodic_response: PeriodicResponse,
    study: Study,
    task: Task,
) -> Study:
    plan_reference = evidence.fact(
        study,
        "spectral_cell_study_plan",
    ).reference
    plan = achromatic.SpectralCellStudyPlan.from_document(
        Document.from_bytes(evidence.fetch(plan_reference))
    )
    binding = achromatic.SpectralMaterialBinding.from_document(
        Document.from_bytes(evidence.fetch(plan.material_binding_reference))
    )
    lattice_reference = evidence.fact(study, "physical_lattice").reference
    request = achromatic.project_spectral_reference_request(
        plan,
        binding,
        task=task,
        lattice_reference=lattice_reference,
    )
    outcome = periodic_response.observe(request)
    if isinstance(outcome, PeriodicResponseUnavailable):
        if outcome.request_identity != request.request_identity:
            raise RuntimeError("spectral_periodic_outcome_request_mismatch")
        return evidence.with_unavailable(
            study,
            task,
            f"spectral_reference_screen_unavailable:{outcome.reason.value}",
        )
    if not isinstance(
        outcome,
        (ObservedPeriodicPolarization, PeriodicPolarizationIncomplete),
    ):
        raise RuntimeError("spectral_periodic_response_mismatch")
    incomplete_items = (
        outcome.incomplete_items
        if isinstance(outcome, PeriodicPolarizationIncomplete)
        else ()
    )
    for item in (*outcome.items, *incomplete_items):
        evidence.observe_admitted(item.body_reference)
    binding_reference = _required_reference(task.binding_reference)
    profile_reference = plan.qualification_profile_reference
    profile = achromatic.ResponseQualificationProfile.from_document(
        Document.from_bytes(evidence.fetch(profile_reference))
    )
    screen = achromatic.form_spectral_cell_screen(
        plan,
        request,
        outcome,
        convention=_polarization_convention(study),
        solver_binding_reference=binding_reference,
        profile=profile,
        profile_reference=profile_reference,
    )
    body_references = tuple(
        reference
        for observation in screen.observations
        for reference in observation.source_references
    ) + tuple(
        reference
        for incompletion in screen.incompletions
        for reference in incompletion.source_references
    )
    reference = evidence.admit_task(
        task,
        screen.document(),
        sources=(
            plan_reference,
            profile_reference,
            binding_reference,
            *body_references,
        ),
    )
    if screen.eligible_geometries:
        return evidence.with_fact(study, task, reference)
    return evidence.with_finding(
        study,
        Finding(
            claim=task.claim,
            kind=(
                FindingKind.INCOMPLETE if screen.incompletions else FindingKind.REFUSAL
            ),
            needs=(
                (
                    achromatic.SpectralQualificationStatus.NUMERICAL_INCOMPLETE.value
                    if screen.incompletions
                    else achromatic.SpectralQualificationStatus.CONVERSION_INSUFFICIENT.value
                ),
            ),
            record_references=(reference,),
        ),
    )


def _observe_jones(
    evidence: _Evidence,
    periodic_response: PeriodicResponse,
    study: Study,
    task: Task,
) -> Study:
    plan_reference = evidence.fact(
        study,
        "spectral_cell_study_plan",
    ).reference
    plan = achromatic.SpectralCellStudyPlan.from_document(
        Document.from_bytes(evidence.fetch(plan_reference))
    )
    binding = achromatic.SpectralMaterialBinding.from_document(
        Document.from_bytes(evidence.fetch(plan.material_binding_reference))
    )
    screen_reference = evidence.fact(study, "spectral_cell_screen").reference
    screen = achromatic.SpectralCellScreen.from_document(
        Document.from_bytes(evidence.fetch(screen_reference))
    )
    requests = achromatic.project_spectral_periodic_requests(
        plan,
        binding,
        screen,
        task=task,
    )
    outcomes: list[ObservedPeriodicPolarization] = []
    for request in requests:
        outcome = periodic_response.observe(request)
        if isinstance(outcome, PeriodicResponseUnavailable):
            if outcome.request_identity != request.request_identity:
                raise RuntimeError("spectral_periodic_outcome_request_mismatch")
            return evidence.with_unavailable(
                study,
                task,
                (
                    "spectral_periodic_response_unavailable:"
                    f"{request.items[0].wavelength_nm}:{outcome.reason.value}"
                ),
            )
        if isinstance(outcome, PeriodicPolarizationIncomplete):
            for item in (*outcome.items, *outcome.incomplete_items):
                evidence.observe_admitted(item.body_reference)
            return evidence.with_finding(
                study,
                Finding(
                    claim=task.claim,
                    kind=FindingKind.INCOMPLETE,
                    needs=(
                        achromatic.SpectralQualificationStatus.NUMERICAL_INCOMPLETE.value,
                    ),
                    record_references=tuple(
                        item.body_reference for item in outcome.incomplete_items
                    ),
                ),
            )
        if not isinstance(outcome, ObservedPeriodicPolarization):
            raise RuntimeError("spectral_periodic_response_mismatch")
        for item in outcome.items:
            evidence.observe_admitted(item.body_reference)
        outcomes.append(outcome)
    binding_reference = _required_reference(task.binding_reference)
    library = achromatic.form_spectral_jones_library(
        plan,
        screen,
        requests,
        tuple(outcomes),
        convention=_polarization_convention(study),
        solver_binding_reference=binding_reference,
    )
    body_references = tuple(
        reference
        for observation in library.observations
        for reference in observation.source_references
    )
    reference = evidence.admit_task(
        task,
        library.document(),
        sources=(
            plan_reference,
            screen_reference,
            binding_reference,
            *body_references,
        ),
    )
    return evidence.with_fact(study, task, reference)


def _qualify(
    evidence: _Evidence,
    study: Study,
    task: Task,
) -> Study:
    target = _restore_target(evidence, study)
    target_reference = evidence.fact(study, "achromatic_target").reference
    library_reference = evidence.fact(
        study,
        "spectral_jones_library",
    ).reference
    library = achromatic.SpectralJonesLibrary.from_document(
        Document.from_bytes(evidence.fetch(library_reference))
    )
    plan_reference = library.plan_reference
    plan = achromatic.SpectralCellStudyPlan.from_document(
        Document.from_bytes(evidence.fetch(plan_reference))
    )
    profile_reference = plan.qualification_profile_reference
    profile = achromatic.ResponseQualificationProfile.from_document(
        Document.from_bytes(evidence.fetch(profile_reference))
    )
    qualification = achromatic.qualify_spectral_jones_library(
        target,
        plan,
        library,
        profile=profile,
        profile_reference=profile_reference,
    )
    reference = evidence.admit_task(
        task,
        qualification.document(),
        sources=(
            target_reference,
            plan_reference,
            library_reference,
            profile_reference,
        ),
    )
    if (
        qualification.status
        is achromatic.SpectralQualificationStatus.EVIDENCE_INCOMPLETE
    ):
        return evidence.with_finding(
            study,
            Finding(
                claim=task.claim,
                kind=FindingKind.INCOMPLETE,
                needs=(qualification.status.value,),
                record_references=(reference,),
            ),
        )
    if qualification.is_candidate:
        return evidence.with_fact(study, task, reference)
    return evidence.with_finding(
        study,
        Finding(
            claim=task.claim,
            kind=FindingKind.REFUSAL,
            needs=(qualification.status.value,),
            record_references=(reference,),
        ),
    )


def _assign_aperture(
    evidence: _Evidence,
    study: Study,
    task: Task,
) -> Study:
    target_reference = evidence.fact(study, "achromatic_target").reference
    target = _restore_target(evidence, study)
    lattice_reference = evidence.fact(study, "physical_lattice").reference
    lattice = aperture_science.Lattice.from_document(
        Document.from_bytes(evidence.fetch(lattice_reference))
    )
    qualification_reference = evidence.fact(
        study,
        "qualified_spectral_library",
    ).reference
    qualification = achromatic.SpectralLibraryQualification.from_document(
        Document.from_bytes(evidence.fetch(qualification_reference))
    )
    plan_reference = qualification.plan_reference
    plan = achromatic.SpectralCellStudyPlan.from_document(
        Document.from_bytes(evidence.fetch(plan_reference))
    )
    library_reference = qualification.library_reference
    library = achromatic.SpectralJonesLibrary.from_document(
        Document.from_bytes(evidence.fetch(library_reference))
    )
    aperture = achromatic.assign_continuous_achromatic_aperture(
        target,
        plan,
        library,
        qualification,
        lattice,
        target_reference=target_reference,
        lattice_reference=lattice_reference,
        plan_reference=plan_reference,
        library_reference=library_reference,
        qualification_reference=qualification_reference,
        selection_binding_reference=_required_reference(task.binding_reference),
    )
    reference = evidence.admit_task(
        task,
        aperture.document(),
        sources=(
            target_reference,
            lattice_reference,
            plan_reference,
            library_reference,
            qualification_reference,
            _required_reference(task.binding_reference),
        ),
    )
    return evidence.with_fact(study, task, reference)


def _observe_post_freeze_jones(
    evidence: _Evidence,
    periodic_response: PeriodicResponse,
    study: Study,
    task: Task,
) -> Study:
    aperture_reference = evidence.fact(study, "achromatic_aperture").reference
    aperture = achromatic.AchromaticAperture.from_document(
        Document.from_bytes(evidence.fetch(aperture_reference))
    )
    profile_reference = evidence.fact(
        study,
        "response_qualification_profile",
    ).reference
    profile = achromatic.ResponseQualificationProfile.from_document(
        Document.from_bytes(evidence.fetch(profile_reference))
    )
    plan = achromatic.SpectralCellStudyPlan.from_document(
        Document.from_bytes(evidence.fetch(aperture.plan_reference))
    )
    binding = achromatic.SpectralMaterialBinding.from_document(
        Document.from_bytes(evidence.fetch(plan.material_binding_reference))
    )
    candidate = achromatic.SpectralJonesLibrary.from_document(
        Document.from_bytes(evidence.fetch(aperture.library_reference))
    )
    requests = achromatic.project_post_freeze_blind_requests(
        plan,
        binding,
        aperture,
        profile=profile,
        task=task,
    )
    observations: list[achromatic.SpectralJonesObservation] = []
    incomplete_references: list[Reference] = []
    missing_wavelengths: list[int] = []
    unavailable_reasons: list[str] = []
    for request in requests:
        wavelength_nm = request.items[0].wavelength_nm
        outcome = periodic_response.observe(request)
        if isinstance(outcome, PeriodicResponseUnavailable):
            if outcome.request_identity != request.request_identity:
                raise RuntimeError("spectral_periodic_outcome_request_mismatch")
            missing_wavelengths.append(wavelength_nm)
            unavailable_reasons.append(
                f"{wavelength_nm}:{outcome.reason.value}"
            )
            continue
        if isinstance(outcome, PeriodicPolarizationIncomplete):
            for item in (*outcome.items, *outcome.incomplete_items):
                evidence.observe_admitted(item.body_reference)
            incomplete_references.extend(
                item.body_reference for item in outcome.incomplete_items
            )
            break
        if not isinstance(outcome, ObservedPeriodicPolarization):
            raise RuntimeError("spectral_periodic_response_mismatch")
        for item in outcome.items:
            evidence.observe_admitted(item.body_reference)
        observations.extend(
            achromatic.form_spectral_observations(
                aperture.used_geometries,
                wavelength_nm=wavelength_nm,
                request=request,
                outcome=outcome,
                solver_binding_reference=_required_reference(task.binding_reference),
            )
        )
    post_freeze = achromatic.form_post_freeze_jones_library(
        plan,
        aperture,
        candidate,
        tuple(observations),
        profile=profile,
        qualification_reference=aperture.qualification_reference,
        solver_binding_reference=_required_reference(task.binding_reference),
        numerical_incompletion_references=tuple(incomplete_references),
        missing_wavelengths_nm=tuple(missing_wavelengths),
        unavailable_reasons=tuple(unavailable_reasons),
    )
    observation_sources = tuple(
        reference
        for observation in post_freeze.observations
        for reference in observation.source_references
    )
    reference = evidence.admit_task(
        task,
        post_freeze.document(),
        sources=tuple(dict.fromkeys((
            aperture_reference,
            profile_reference,
            aperture.plan_reference,
            aperture.qualification_reference,
            aperture.library_reference,
            _required_reference(task.binding_reference),
            *observation_sources,
            *post_freeze.numerical_incompletion_references,
        ))),
    )
    if not post_freeze.is_complete:
        verification = achromatic.form_band_verification_evidence(
            plan,
            aperture,
            candidate,
            post_freeze,
            None,
            None,
            profile=profile,
            qualification_reference=aperture.qualification_reference,
            family_reference=None,
            focus_reference=None,
        )
        verification_reference = evidence.admit_document(
            verification.document(),
            sources=(
                aperture_reference,
                profile_reference,
                aperture.qualification_reference,
                reference,
            ),
        )
        return evidence.with_finding(
            study,
            Finding(
                claim=task.claim,
                kind=FindingKind.INCOMPLETE,
                needs=(verification.status.value,),
                record_references=(reference, verification_reference),
            ),
        )
    return evidence.with_fact(study, task, reference)


def _form_spectral_fields(
    evidence: _Evidence,
    study: Study,
    task: Task,
) -> Study:
    binding_reference = _required_reference(task.binding_reference)
    realization = _restore_angular_spectrum(evidence, binding_reference)
    aperture_reference = evidence.fact(study, "achromatic_aperture").reference
    aperture = achromatic.AchromaticAperture.from_document(
        Document.from_bytes(evidence.fetch(aperture_reference))
    )
    qualification_reference = aperture.qualification_reference
    library_reference = aperture.library_reference
    library = achromatic.SpectralJonesLibrary.from_document(
        Document.from_bytes(evidence.fetch(library_reference))
    )
    post_freeze_reference = evidence.fact(
        study,
        "post_freeze_jones_library",
    ).reference
    post_freeze = achromatic.PostFreezeJonesLibrary.from_document(
        Document.from_bytes(evidence.fetch(post_freeze_reference))
    )
    if not post_freeze.is_complete:
        raise RuntimeError("post_freeze_library_fact_incomplete")
    plan = achromatic.SpectralCellStudyPlan.from_document(
        Document.from_bytes(evidence.fetch(aperture.plan_reference))
    )
    expected_focus_m = float(require_metalens_design(study).focal_length_um) * 1e-6
    incident = library.convention.circular_input
    converted_component = "left" if incident == "right" else "right"
    entries: list[achromatic.SpectralFieldEntry] = []
    child_references: list[Reference] = []
    try:
        for strategy in achromatic.achromatic_strategies():
            for wavelength_nm in plan.full_band_wavelengths_nm:
                field = achromatic.form_achromatic_aperture_field(
                    aperture,
                    library,
                    post_freeze_library=post_freeze,
                    wavelength_nm=wavelength_nm,
                    strategy=strategy,
                    aperture_reference=aperture_reference,
                )
                field_reference = evidence.admit_scientific_field(field)
                propagation = propagate_field(
                    field,
                    distance_range_m=(
                        0.8 * expected_focus_m,
                        1.2 * expected_focus_m,
                    ),
                    preferred_distance_m=expected_focus_m,
                    components=(converted_component,),
                    realization=realization,
                )
                region = observe_focal_region(
                    propagation,
                    field_reference=field_reference,
                    expected_focus_m=expected_focus_m,
                )
                region_reference = evidence.admit_scientific_focal_region(
                    region,
                    binding_reference=binding_reference,
                    field_reference=field_reference,
                )
                entries.append(
                    achromatic.SpectralFieldEntry(
                        strategy=strategy,
                        wavelength_nm=wavelength_nm,
                        field_reference=field_reference,
                        focal_region_reference=region_reference,
                    )
                )
                child_references.extend((field_reference, region_reference))
    except FieldMemoryUnavailable:
        return evidence.with_unavailable(study, task, "field_memory_unavailable")
    family = achromatic.SpectralFieldFamily(
        aperture_reference=aperture_reference,
        qualification_reference=qualification_reference,
        library_reference=library_reference,
        propagation_binding_reference=binding_reference,
        post_freeze_library_reference=post_freeze_reference,
        design_wavelengths_nm=plan.design_wavelengths_nm,
        holdout_wavelengths_nm=plan.holdout_wavelengths_nm,
        blind_verification_wavelengths_nm=plan.blind_verification_wavelengths_nm,
        entries=tuple(entries),
    )
    reference = evidence.admit_task(
        task,
        family.document(),
        sources=tuple(
            dict.fromkeys(
                (
                    aperture_reference,
                    qualification_reference,
                    library_reference,
                    post_freeze_reference,
                    binding_reference,
                    *child_references,
                )
            )
        ),
    )
    return evidence.with_fact(study, task, reference)


def _evaluate_achromatic_focus(
    evidence: _Evidence,
    study: Study,
    task: Task,
) -> Study:
    family_reference = evidence.fact(study, "spectral_field_family").reference
    family = achromatic.SpectralFieldFamily.from_document(
        Document.from_bytes(evidence.fetch(family_reference))
    )
    numerical_aperture = float(require_metalens_design(study).numerical_aperture)
    incident = _polarization_convention(study).circular_input
    focus_entries: list[achromatic.AchromaticFocusEntry] = []
    focus_references: list[Reference] = []
    for entry in family.entries:
        region = restore_focal_region(
            Document.from_bytes(evidence.fetch(entry.focal_region_reference)),
            evidence.fetch,
        )
        if abs(region.wavelength_m - entry.wavelength_nm * 1e-9) > 1e-18:
            raise ValueError("spectral_field_family_wavelength_mismatch")
        focus = evaluate_focus(
            region,
            numerical_aperture=numerical_aperture,
            leakage_component=incident,
        )
        if isinstance(focus, FocusSurvey) and not isinstance(focus, Focus):
            diagnostic = Document(
                FOCUS_SURVEY_SCHEMA,
                {
                    "claim": task.claim,
                    "focal_region": entry.focal_region_reference.as_mapping(),
                    "need": "focus_incomplete",
                    "strategy": entry.strategy,
                    "survey": focus.as_mapping(),
                    "wavelength_nm": entry.wavelength_nm,
                },
            )
            reference = evidence.admit_document(
                diagnostic,
                sources=(entry.focal_region_reference,),
            )
            return evidence.with_finding(
                study,
                Finding(
                    claim=task.claim,
                    kind=FindingKind.INCOMPLETE,
                    needs=("focus_incomplete",),
                    record_references=(reference,),
                ),
            )
        assert isinstance(focus, Focus)
        focus_reference = evidence.admit_scientific_focus(
            focus,
            focal_region_reference=entry.focal_region_reference,
        )
        focus_entries.append(
            achromatic.AchromaticFocusEntry(
                strategy=entry.strategy,
                wavelength_nm=entry.wavelength_nm,
                focus_reference=focus_reference,
                focus=focus,
            )
        )
        focus_references.append(focus_reference)
    result = achromatic.form_achromatic_focus(
        family,
        tuple(focus_entries),
        family_reference=family_reference,
        evaluation_binding_reference=_required_reference(task.binding_reference),
    )
    reference = evidence.admit_task(
        task,
        result.document(),
        sources=(
            family_reference,
            _required_reference(task.binding_reference),
            *focus_references,
        ),
    )
    return evidence.with_fact(study, task, reference)


def _verify_achromatic_band(
    evidence: _Evidence,
    study: Study,
    task: Task,
) -> Study:
    post_freeze_reference = evidence.fact(
        study,
        "post_freeze_jones_library",
    ).reference
    post_freeze = achromatic.PostFreezeJonesLibrary.from_document(
        Document.from_bytes(evidence.fetch(post_freeze_reference))
    )
    if not post_freeze.is_complete:
        raise RuntimeError("post_freeze_library_fact_incomplete")
    aperture = achromatic.AchromaticAperture.from_document(
        Document.from_bytes(evidence.fetch(post_freeze.aperture_reference))
    )
    plan = achromatic.SpectralCellStudyPlan.from_document(
        Document.from_bytes(evidence.fetch(post_freeze.plan_reference))
    )
    candidate = achromatic.SpectralJonesLibrary.from_document(
        Document.from_bytes(evidence.fetch(post_freeze.candidate_library_reference))
    )
    profile = achromatic.ResponseQualificationProfile.from_document(
        Document.from_bytes(evidence.fetch(post_freeze.profile_reference))
    )
    family_reference = evidence.fact(study, "spectral_field_family").reference
    focus_reference = evidence.fact(study, "achromatic_focus").reference
    family = achromatic.SpectralFieldFamily.from_document(
        Document.from_bytes(evidence.fetch(family_reference))
    )
    focus = achromatic.AchromaticFocus.from_document(
        Document.from_bytes(evidence.fetch(focus_reference))
    )
    verification = achromatic.form_band_verification_evidence(
        plan,
        aperture,
        candidate,
        post_freeze,
        family,
        focus,
        profile=profile,
        qualification_reference=post_freeze.qualification_reference,
        family_reference=family_reference,
        focus_reference=focus_reference,
    )
    sources = tuple(
        reference
        for reference in (
            post_freeze.aperture_reference,
            post_freeze.profile_reference,
            post_freeze.qualification_reference,
            post_freeze_reference,
            family_reference,
            focus_reference,
        )
        if reference is not None
    )
    reference = evidence.admit_task(task, verification.document(), sources=sources)
    if verification.is_pass:
        return evidence.with_fact(study, task, reference)
    return evidence.with_finding(
        study,
        Finding(
            claim=task.claim,
            kind=(
                FindingKind.REFUSAL
                if verification.status
                in {
                    achromatic.BandVerificationStatus.DENSE_RESIDUAL,
                    achromatic.BandVerificationStatus.CURVATURE,
                }
                else FindingKind.INCOMPLETE
            ),
            needs=(verification.status.value,),
            record_references=(reference,),
        ),
    )


def _restore_angular_spectrum(
    evidence: _Evidence,
    reference: Reference,
) -> AngularSpectrumRealization:
    try:
        document = Document.from_bytes(evidence.fetch(reference))
    except (FileNotFoundError, ValueError) as error:
        raise RuntimeError("angular_spectrum_binding_mismatch") from error
    realization = document.values.get("realization")
    if (
        document.schema_identifier != "metacraft.binding.angular_spectrum_propagation"
        or document.values.get("operations") != ["propagate_field"]
        or document.values.get("qualified") is not True
        or not isinstance(realization, Mapping)
    ):
        raise RuntimeError("angular_spectrum_binding_mismatch")
    try:
        restored = AngularSpectrumRealization.from_mapping(realization)
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("angular_spectrum_binding_mismatch") from error
    if restored.identity != ANGULAR_SPECTRUM_REALIZATION:
        raise RuntimeError("angular_spectrum_binding_mismatch")
    return restored


def _restore_target(
    evidence: _Evidence,
    study: Study,
) -> achromatic.AchromaticTarget:
    reference = evidence.fact(study, "achromatic_target").reference
    return achromatic.AchromaticTarget.from_document(
        Document.from_bytes(evidence.fetch(reference))
    )


def _polarization_convention(study: Study) -> PolarizationConvention:
    handedness = require_metalens_design(study).incident_polarization.handedness
    if handedness not in {"left", "right"}:
        raise RuntimeError("achromatic_circular_polarization_required")
    return PolarizationConvention(circular_input=handedness)


def _required_reference(reference: Reference | None) -> Reference:
    if reference is None:
        raise RuntimeError("task_binding_missing")
    return reference


def _require_brief(study: Study) -> MetalensBrief:
    if not isinstance(study.brief, MetalensBrief):
        raise TypeError("metalens_brief_required")
    return study.brief
