from __future__ import annotations

import hashlib

from dataclasses import replace
from decimal import Decimal

import pytest

from metacraft.authority import Document, Reference, reference_for
from tests.brief_fixtures import (
    geometric_brief,
    propagation_brief,
)
from metacraft.science import compile_study
from metacraft.science.metalens.aperture import Cell, Material, Rectangle
from metacraft.science.metalens.design import require_metalens_design
from metacraft.science.metalens.height import (
    HeightAdviceBasis,
    HeightConstraintBasis,
    HeightDomain,
    resolve_height_choice,
)
from metacraft.science.metalens.brief import ControlStrategy
from metacraft.science.metalens.geometric_phase import (
    ComplexCoefficient,
    JonesCell,
    JonesLibrary,
    JonesResponse,
    LEGACY_PB_RESPONSE_RANKING,
    PbCellQualification,
    PolarizationConvention,
    choose_cell,
    choose_cell_by_legacy_ranking,
)
from metacraft.science.result import EvidenceOrigin
from metacraft.science.study import (
    Binding,
    Capability,
    Finding,
    FindingKind,
)
from tests.domain_fixtures import (
    compile_with_facts,
    height_advice as fixture_height_advice,
    height_domain,
    material_binding,
)


def _reference_hash(name: str) -> str:
    return f"sha256:{hashlib.sha256(name.encode()).hexdigest()}"

def _reference(name: str) -> Reference:
    return Reference(
        content_hash=_reference_hash(name),
        media_type="application/json",
        metadata_content_hash=_reference_hash("metadata-" + name),
        size_bytes=len(name),
    )


def _document_reference(document: Document) -> Reference:
    return reference_for(document.to_bytes())


def _advised_brief():
    """
    Use the geometric brief with a brief-stated period so the advised height
    flow can compile without a period consultation.
    """

    return replace(geometric_brief(), cell_period_nm=220)


def _constrained_brief():
    """
    Use the geometric brief with both period and height stated so the
    height_choice task admits without any consultation reference.
    """

    return replace(geometric_brief(), cell_period_nm=220, atom_height_nm=600)


def _domain(brief=None) -> HeightDomain:
    if brief is None:
        brief = _advised_brief()
    return height_domain(compile_study(brief))


def _foundation_capabilities():
    return (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
        Capability("deterministic_selection"),
    )


def _foundation_bindings():
    return (
        Binding("optical_material", _reference("material-binding")),
        Binding("fabrication_constraint", _reference("fabrication-binding")),
        Binding("deterministic_selection", _reference("selection-binding")),
    )


def _advised_choice_inputs():
    """
    Build one geometric study that admits target_phase, material_binding,
    period_domain, period_choice, and height_domain, leaving height_choice
    ready (not admitted) for the advised height flow. Returns the constructed
    domain alongside the study and advice.
    """

    brief = _advised_brief()
    base_study = compile_study(brief)
    binding = material_binding(base_study)
    domain = height_domain(base_study)
    advice = fixture_height_advice(brief, domain, height_nm=600)
    advice_reference = _document_reference(advice.document())
    from tests.domain_fixtures import (
        period_domain as period_domain_fixture,
        period_choice as period_choice_fixture,
    )
    pdomain = period_domain_fixture(base_study)
    pchoice = period_choice_fixture(base_study)
    references = {
        "target_phase": _reference("target"),
        "material_binding": binding.evidence_reference,
        "period_domain": pdomain.evidence_reference,
        "period_choice": pchoice.evidence_reference,
        "height_domain": domain.evidence_reference,
    }
    study, _facts = compile_with_facts(
        brief,
        references,
        advice=(advice,),
        capabilities=_foundation_capabilities(),
        bindings=_foundation_bindings(),
    )
    return domain, study, advice, advice_reference


def _constrained_choice_inputs():
    """
    Build one geometric study over a brief-stated height so the height_choice
    task admits without consultation. Used by cell-choice tests that must
    admit height_choice as evidence.
    """

    brief = _constrained_brief()
    base_study = compile_study(brief)
    binding = material_binding(base_study)
    domain = height_domain(base_study)
    from tests.domain_fixtures import (
        period_domain as period_domain_fixture,
        period_choice as period_choice_fixture,
    )
    pdomain = period_domain_fixture(base_study)
    pchoice = period_choice_fixture(base_study)
    references = {
        "target_phase": _reference("target"),
        "material_binding": binding.evidence_reference,
        "period_domain": pdomain.evidence_reference,
        "period_choice": pchoice.evidence_reference,
        "height_domain": domain.evidence_reference,
    }
    study, _facts = compile_with_facts(
        brief,
        references,
        capabilities=_foundation_capabilities(),
        bindings=_foundation_bindings(),
    )
    return domain, study


def test_geometric_height_choice_uses_its_twenty_nanometre_grid() -> None:
    domain, study, advice, advice_reference = _advised_choice_inputs()

    choice = resolve_height_choice(
        study,
        domain,
        advice,
    )

    assert (
        require_metalens_design(study).control_strategy
        is ControlStrategy.GEOMETRIC_PHASE
    )
    assert choice.height_nm == 600
    assert choice.period_nm == 220
    assert choice.order_regime == "zeroth order"
    assert choice.minimum_feature_nm == 80
    assert choice.maximum_feature_nm == 140
    assert choice.dimension_step_nm == 20
    assert choice.cautions == ()
    assert choice.domain_reference == domain.evidence_reference
    assert choice.basis == HeightAdviceBasis(advice_reference)


def test_propagation_height_domain_cannot_choose_a_geometric_height() -> None:
    propagation_domain = _domain(propagation_brief())
    _geometric_domain, study, advice, advice_reference = _advised_choice_inputs()

    with pytest.raises(ValueError, match="height_domain_brief_mismatch"):
        resolve_height_choice(
            study,
            propagation_domain,
            advice,
        )


def _fin(
    *,
    length_nm: int,
    width_nm: int,
    height_nm: int = 600,
) -> Cell:
    source = _reference(f"cell-{height_nm}-{length_nm}-{width_nm}")
    return Cell(
        identity=f"cell-{height_nm}-{length_nm}-{width_nm}",
        atom=Material("silicon nitride", "solver native"),
        substrate=Material("silica", "solver native"),
        period_nm=220,
        height_nm=height_nm,
        geometry=Rectangle(
            short_side_nm=width_nm,
            long_side_nm=length_nm,
        ),
        source=source,
    )


def _coefficient(real: str, imaginary: str = "0") -> ComplexCoefficient:
    return ComplexCoefficient(Decimal(real), Decimal(imaginary))


def _point(
    *,
    length_nm: int,
    width_nm: int,
    useful_power: str,
    leakage_power: str,
    source: str,
    height_nm: int = 600,
) -> JonesCell:
    return JonesCell(
        cell=_fin(
            length_nm=length_nm,
            width_nm=width_nm,
            height_nm=height_nm,
        ),
        jones=JonesResponse(
            output_x_from_input_x=_coefficient("0.8"),
            output_y_from_input_x=_coefficient("0.1"),
            output_x_from_input_y=_coefficient("0.1"),
            output_y_from_input_y=_coefficient("-0.8"),
        ),
        converted=_coefficient("0.7"),
        converted_phase=Decimal("0.2"),
        converted_power=Decimal(useful_power),
        retained=_coefficient("0.1"),
        retained_phase=Decimal("0.1"),
        retained_power=Decimal(leakage_power),
        source_references=(
            _reference(f"{source}-x"),
            _reference(f"{source}-y"),
        ),
        execution_origin=EvidenceOrigin.SYNTHETIC,
    )


def _cell_qualification() -> PbCellQualification:
    return PbCellQualification(
        name="fixture PB response contract",
        minimum_transmitted_power=Decimal("0.8"),
        minimum_converted_power=Decimal("0.8"),
        maximum_retained_power=Decimal("0.1"),
    )


def _selection_study(
    domain: HeightDomain,
    height_choice,
    cells: tuple[JonesCell, ...],
) -> tuple[object, dict[str, Reference]]:
    brief = _constrained_brief()
    base_study = compile_study(brief)
    binding = material_binding(base_study)
    from tests.domain_fixtures import (
        period_domain as period_domain_fixture,
        period_choice as period_choice_fixture,
    )
    pdomain = period_domain_fixture(base_study)
    pchoice = period_choice_fixture(base_study)
    references = {
        name: _reference(name)
        for name in (
            "target_phase",
            "material_binding",
            "period_domain",
            "period_choice",
            "height_domain",
            "height_choice",
            "polarization_convention",
            "jones_library",
        )
    }
    convention = PolarizationConvention(circular_input="right")
    references["polarization_convention"] = _document_reference(
        convention.document()
    )
    references["period_domain"] = pdomain.evidence_reference
    references["period_choice"] = pchoice.evidence_reference
    references["height_domain"] = domain.evidence_reference
    references["material_binding"] = binding.evidence_reference
    references["height_choice"] = _document_reference(height_choice.document())
    references["jones_library"] = _document_reference(
        JonesLibrary.document_from(
            cells=cells,
            binding_reference=_reference("lumerical"),
            height_choice_reference=references["height_choice"],
            convention=convention,
            convention_reference=references["polarization_convention"],
            source_references=tuple(
                reference
                for cell in cells
                for reference in cell.source_references
            ),
        )
    )
    capabilities = (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
        Capability("deterministic_selection"),
        Capability("polarization_convention"),
        Capability("periodic_polarization_response"),
    )
    bindings = (
        Binding("optical_material", _reference("material-binding")),
        Binding("fabrication_constraint", _reference("fabrication-binding")),
        Binding("deterministic_selection", _reference("selection-binding")),
        Binding(
            "polarization_convention",
            _reference("polarization-binding"),
        ),
        Binding(
            "periodic_polarization_response",
            _reference("lumerical"),
            "capacity:lumerical",
        ),
    )
    study, _facts = compile_with_facts(
        brief,
        references,
        capabilities=capabilities,
        bindings=bindings,
    )
    return study, references


def test_one_fixed_height_jones_library_selects_one_traceable_cell() -> None:
    domain, choice_study = _constrained_choice_inputs()
    choice = resolve_height_choice(choice_study, domain)
    cells = (
        _point(
            length_nm=140,
            width_nm=80,
            useful_power="0.90",
            leakage_power="0.03",
            source="jones-a",
        ),
        _point(
            length_nm=120,
            width_nm=80,
            useful_power="0.85",
            leakage_power="0.08",
            source="jones-b",
        ),
    )
    study, references = _selection_study(
        domain,
        choice,
        cells,
    )
    library = JonesLibrary(
        cells=cells,
        binding_reference=_reference("lumerical"),
        height_choice_reference=references["height_choice"],
        convention=PolarizationConvention(circular_input="right"),
        convention_reference=references["polarization_convention"],
        evidence_reference=references["jones_library"],
        source_references=tuple(
            reference
            for cell in cells
            for reference in cell.source_references
        ),
    )

    selected = choose_cell(
        study,
        choice,
        library,
        height_choice_reference=references["height_choice"],
        qualification=_cell_qualification(),
    )
    repeated = choose_cell(
        study,
        choice,
        replace(
            library,
            cells=tuple(reversed(cells)),
            source_references=tuple(
                reference
                for cell in reversed(cells)
                for reference in cell.source_references
            ),
        ),
        height_choice_reference=references["height_choice"],
        qualification=_cell_qualification(),
    )

    assert tuple(task.claim for task in study.ready_tasks) == (
        "cell_choice",
        "physical_lattice",
    )
    cell_choice_task = next(
        task for task in study.ready_tasks if task.claim == "cell_choice"
    )
    lattice_task = next(
        task for task in study.ready_tasks if task.claim == "physical_lattice"
    )
    assert cell_choice_task.method == "choose_cell"
    assert cell_choice_task.capacity_scope is None
    assert lattice_task.method == "resolve_physical_lattice"
    assert lattice_task.capacity_scope is None
    assert selected.cell == _fin(length_nm=140, width_nm=80)
    assert selected.useful_power == Decimal("0.90")
    assert selected.leakage_power == Decimal("0.03")
    assert selected.height_basis == HeightConstraintBasis()
    assert selected.height_domain_reference == domain.evidence_reference
    assert selected.height_choice_reference == references["height_choice"]
    assert selected.library_reference == references["jones_library"]
    assert selected.convention_reference == references["polarization_convention"]
    assert selected.binding_reference == _reference("lumerical")
    assert selected.source_references == (
        _reference("jones-a-x"),
        _reference("jones-a-y"),
    )
    assert repeated.cell == selected.cell
    assert repeated.loss == selected.loss
    assert selected.selection_contract == _cell_qualification()
    assert selected.document().values["selection_contract"] == (
        _cell_qualification().as_mapping()
    )


def test_cell_choice_uses_the_declared_power_and_geometry_tie_breaks() -> None:
    domain, choice_study = _constrained_choice_inputs()
    height = resolve_height_choice(choice_study, domain)
    higher_conversion = _point(
        length_nm=140,
        width_nm=80,
        useful_power="0.90",
        leakage_power="0.10",
        source="higher-conversion",
    )
    lower_conversion = _point(
        length_nm=120,
        width_nm=80,
        useful_power="0.85",
        leakage_power="0.05",
        source="lower-conversion",
    )
    cells = (lower_conversion, higher_conversion)
    study, references = _selection_study(
        domain,
        height,
        cells,
    )

    selected = choose_cell(
        study,
        height,
        JonesLibrary(
            cells=cells,
            binding_reference=_reference("lumerical"),
            height_choice_reference=references["height_choice"],
            convention=PolarizationConvention(circular_input="right"),
            convention_reference=references["polarization_convention"],
            evidence_reference=references["jones_library"],
            source_references=tuple(
                reference
                for cell in cells
                for reference in cell.source_references
            ),
        ),
        height_choice_reference=references["height_choice"],
        qualification=_cell_qualification(),
    )

    assert selected.cell == higher_conversion.cell

    same_response = replace(
        lower_conversion,
        converted=higher_conversion.converted,
        converted_phase=higher_conversion.converted_phase,
        converted_power=higher_conversion.converted_power,
        retained=higher_conversion.retained,
        retained_phase=higher_conversion.retained_phase,
        retained_power=higher_conversion.retained_power,
    )
    tied = (higher_conversion, same_response)
    tied_study, tied_references = _selection_study(
        domain,
        height,
        tied,
    )
    smaller = choose_cell(
        tied_study,
        height,
        JonesLibrary(
            cells=tied,
            binding_reference=_reference("lumerical"),
            height_choice_reference=tied_references["height_choice"],
            convention=PolarizationConvention(circular_input="right"),
            convention_reference=tied_references[
                "polarization_convention"
            ],
            evidence_reference=tied_references["jones_library"],
            source_references=tuple(
                reference
                for cell in tied
                for reference in cell.source_references
            ),
        ),
        height_choice_reference=tied_references["height_choice"],
        qualification=_cell_qualification(),
    )

    assert smaller.cell == same_response.cell


def test_pb_cell_qualification_filters_before_deterministic_ranking() -> None:
    domain, choice_study = _constrained_choice_inputs()
    height = resolve_height_choice(choice_study, domain)
    unqualified_but_better_ranked = _point(
        length_nm=140,
        width_nm=80,
        useful_power="0.89",
        leakage_power="0.11",
        source="unqualified",
    )
    qualified = _point(
        length_nm=120,
        width_nm=80,
        useful_power="0.80",
        leakage_power="0.10",
        source="qualified",
    )
    cells = (unqualified_but_better_ranked, qualified)
    study, references = _selection_study(domain, height, cells)
    library = JonesLibrary(
        cells=cells,
        binding_reference=_reference("lumerical"),
        height_choice_reference=references["height_choice"],
        convention=PolarizationConvention(circular_input="right"),
        convention_reference=references["polarization_convention"],
        evidence_reference=references["jones_library"],
        source_references=tuple(
            reference
            for cell in cells
            for reference in cell.source_references
        ),
    )

    selected = choose_cell(
        study,
        height,
        library,
        height_choice_reference=references["height_choice"],
        qualification=_cell_qualification(),
    )

    assert not isinstance(selected, Finding)
    assert selected.cell == qualified.cell


def test_pb_cell_qualification_retains_optional_response_metrics() -> None:
    domain, choice_study = _constrained_choice_inputs()
    height = resolve_height_choice(choice_study, domain)
    cell = _point(
        length_nm=120,
        width_nm=80,
        useful_power="0.85",
        leakage_power="0.05",
        source="optional-response-profile",
    )
    study, references = _selection_study(domain, height, (cell,))
    qualification = PbCellQualification(
        name="explicit Jones response profile",
        minimum_transmitted_power=Decimal("0.8"),
        minimum_converted_power=Decimal("0.8"),
        maximum_retained_power=Decimal("0.1"),
        maximum_cross_coupling_power=Decimal("0.03"),
        maximum_half_wave_retardance_error_rad=Decimal("3.2"),
    )
    selected = choose_cell(
        study,
        height,
        JonesLibrary(
            cells=(cell,),
            binding_reference=_reference("lumerical"),
            height_choice_reference=references["height_choice"],
            convention=PolarizationConvention(circular_input="right"),
            convention_reference=references["polarization_convention"],
            evidence_reference=references["jones_library"],
            source_references=cell.source_references,
        ),
        height_choice_reference=references["height_choice"],
        qualification=qualification,
    )

    assert not isinstance(selected, Finding)
    assert selected.cross_coupling_power <= Decimal("0.03")
    assert selected.half_wave_retardance_error_rad <= Decimal("3.2")


def test_pb_cell_qualification_returns_a_refusal_when_none_qualify() -> None:
    domain, choice_study = _constrained_choice_inputs()
    height = resolve_height_choice(choice_study, domain)
    cells = (
        _point(
            length_nm=140,
            width_nm=80,
            useful_power="0.70",
            leakage_power="0.02",
            source="low-conversion",
        ),
        _point(
            length_nm=120,
            width_nm=80,
            useful_power="0.79",
            leakage_power="0.01",
            source="still-low",
        ),
    )
    study, references = _selection_study(domain, height, cells)
    library = JonesLibrary(
        cells=cells,
        binding_reference=_reference("lumerical"),
        height_choice_reference=references["height_choice"],
        convention=PolarizationConvention(circular_input="right"),
        convention_reference=references["polarization_convention"],
        evidence_reference=references["jones_library"],
        source_references=tuple(
            reference
            for cell in cells
            for reference in cell.source_references
        ),
    )

    refusal = choose_cell(
        study,
        height,
        library,
        height_choice_reference=references["height_choice"],
        qualification=_cell_qualification(),
    )

    assert refusal == Finding(
        claim="cell_choice",
        kind=FindingKind.REFUSAL,
        needs=("pb_cell_response_unqualified",),
        record_references=(references["jones_library"],),
    )


def test_pb_cell_selection_requires_an_explicit_qualification() -> None:
    domain, choice_study = _constrained_choice_inputs()
    height = resolve_height_choice(choice_study, domain)
    cells = (
        _point(
            length_nm=140,
            width_nm=80,
            useful_power="0.90",
            leakage_power="0.03",
            source="unqualified-contract",
        ),
    )
    study, references = _selection_study(domain, height, cells)
    library = JonesLibrary(
        cells=cells,
        binding_reference=_reference("lumerical"),
        height_choice_reference=references["height_choice"],
        convention=PolarizationConvention(circular_input="right"),
        convention_reference=references["polarization_convention"],
        evidence_reference=references["jones_library"],
        source_references=cells[0].source_references,
    )

    with pytest.raises(
        TypeError,
        match="^pb_cell_qualification_required$",
    ):
        choose_cell(
            study,
            height,
            library,
            height_choice_reference=references["height_choice"],
        )


def test_legacy_pb_ranking_is_explicit_in_the_cell_choice() -> None:
    domain, choice_study = _constrained_choice_inputs()
    height = resolve_height_choice(choice_study, domain)
    cells = (
        _point(
            length_nm=140,
            width_nm=80,
            useful_power="0.02",
            leakage_power="0.01",
            source="legacy-only",
        ),
    )
    study, references = _selection_study(domain, height, cells)

    selected = choose_cell_by_legacy_ranking(
        study,
        height,
        JonesLibrary(
            cells=cells,
            binding_reference=_reference("lumerical"),
            height_choice_reference=references["height_choice"],
            convention=PolarizationConvention(circular_input="right"),
            convention_reference=references["polarization_convention"],
            evidence_reference=references["jones_library"],
            source_references=cells[0].source_references,
        ),
        height_choice_reference=references["height_choice"],
    )

    assert selected.selection_contract is LEGACY_PB_RESPONSE_RANKING
    assert selected.document().values["selection_contract"] == (
        LEGACY_PB_RESPONSE_RANKING.as_mapping()
    )


@pytest.mark.parametrize(
    "field,value",
    (
        ("minimum_transmitted_power", Decimal("NaN")),
        ("minimum_converted_power", Decimal("-0.01")),
        ("maximum_retained_power", Decimal("1.01")),
    ),
)
def test_pb_cell_qualification_rejects_invalid_thresholds(
    field: str,
    value: Decimal,
) -> None:
    values = {
        "name": "invalid fixture",
        "minimum_transmitted_power": Decimal("0.8"),
        "minimum_converted_power": Decimal("0.8"),
        "maximum_retained_power": Decimal("0.1"),
    }
    values[field] = value

    with pytest.raises(
        ValueError,
        match="pb_cell_qualification_threshold_invalid",
    ):
        PbCellQualification(**values)


def test_fixed_height_jones_library_rejects_mixed_heights() -> None:
    cells = (
        _point(
            length_nm=140,
            width_nm=80,
            useful_power="0.9",
            leakage_power="0.03",
            source="jones-a",
        ),
        _point(
            length_nm=120,
            width_nm=80,
            height_nm=650,
            useful_power="0.85",
            leakage_power="0.08",
            source="jones-b",
        ),
    )

    with pytest.raises(ValueError, match="jones_library_height_mixed"):
        JonesLibrary(
            cells=cells,
            binding_reference=_reference("lumerical"),
            height_choice_reference=_reference("height-choice"),
            convention=PolarizationConvention(circular_input="right"),
            convention_reference=_document_reference(
                PolarizationConvention(circular_input="right").document()
            ),
            evidence_reference=_reference("library"),
            source_references=tuple(
                reference
                for cell in cells
                for reference in cell.source_references
            ),
        )


def test_jones_library_rejects_an_unrelated_convention_reference() -> None:
    cell = _point(
        length_nm=140,
        width_nm=80,
        useful_power="0.9",
        leakage_power="0.03",
        source="jones-a",
    )

    with pytest.raises(
        ValueError,
        match="polarization_convention_reference_mismatch",
    ):
        JonesLibrary(
            cells=(cell,),
            binding_reference=_reference("lumerical"),
            height_choice_reference=_reference("height-choice"),
            convention=PolarizationConvention(circular_input="right"),
            convention_reference=_reference("unrelated-convention"),
            evidence_reference=_reference("library"),
            source_references=cell.source_references,
        )


def test_jones_library_rejects_an_unrelated_library_reference() -> None:
    cell = _point(
        length_nm=140,
        width_nm=80,
        useful_power="0.9",
        leakage_power="0.03",
        source="jones-a",
    )
    convention = PolarizationConvention(circular_input="right")

    with pytest.raises(ValueError, match="jones_library_reference_mismatch"):
        JonesLibrary(
            cells=(cell,),
            binding_reference=_reference("lumerical"),
            height_choice_reference=_reference("height-choice"),
            convention=convention,
            convention_reference=_document_reference(convention.document()),
            evidence_reference=_reference("unrelated-library"),
            source_references=cell.source_references,
        )


def test_jones_library_rejects_mixed_execution_provenance() -> None:
    fixture = _point(
        length_nm=140,
        width_nm=80,
        useful_power="0.9",
        leakage_power="0.03",
        source="jones-a",
    )
    native = replace(
        _point(
            length_nm=130,
            width_nm=80,
            useful_power="0.85",
            leakage_power="0.08",
            source="jones-b",
        ),
        execution_origin=EvidenceOrigin.NATIVE,
    )
    convention = PolarizationConvention(circular_input="right")

    with pytest.raises(ValueError, match="jones_library_execution_mixed"):
        JonesLibrary(
            cells=(fixture, native),
            binding_reference=_reference("lumerical"),
            height_choice_reference=_reference("height-choice"),
            convention=convention,
            convention_reference=_document_reference(convention.document()),
            evidence_reference=_reference("library"),
            source_references=(
                *fixture.source_references,
                *native.source_references,
            ),
        )
