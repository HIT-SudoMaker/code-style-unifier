from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

import pytest

import metacraft.science.periodic_response as periodic_response_contract
from metacraft.authority import Reference
from metacraft.external_activity import ExternalActivityClosure
from metacraft.science.compile import compile_study
from metacraft.science.metalens.geometric_phase import (
    PolarizationConvention,
)
from metacraft.science.metalens.field_execution import (
    require_coefficient_field_response,
)
from metacraft.science.metalens.height import (
    HeightChoice,
    HeightConstraintBasis,
)
from metacraft.science.metalens.periodic_cell_evidence import (
    JonesEvidenceBatch,
    PropagationEvidenceBatch,
)
from metacraft.science.periodic_response import (
    AdmittedPeriodicPolarization,
    AdmittedPeriodicTransmission,
    ObservedPeriodicPolarization,
    ObservedPeriodicTransmission,
    PeriodicMaterials,
    PeriodicPolarizationRequest,
    PeriodicResponseClosure,
    PeriodicTransmissionRequest,
    PeriodicWork,
    RectangularCrossSection,
    CircularCrossSection,
    periodic_request_identity,
)
from metacraft.science.study import Study
from tests.brief_fixtures import geometric_brief, propagation_brief


def _reference(character: str) -> Reference:
    return Reference(
        content_hash=f"sha256:{character * 64}",
        media_type="application/json",
        metadata_content_hash=f"sha256:{character.upper() * 64}",
        size_bytes=1,
    )


def _height() -> HeightChoice:
    return HeightChoice(
        brief_identity=f"sha256:{'1' * 64}",
        height_nm=600,
        period_nm=300,
        order_regime="zeroth order",
        minimum_feature_nm=80,
        maximum_feature_nm=120,
        dimension_step_nm=20,
        domain_reference=_reference("a"),
        basis=HeightConstraintBasis(),
        reason="projection completeness fixture",
    )


def _work(
    identity: str,
    *,
    cell_identity: str,
    geometry: CircularCrossSection | RectangularCrossSection,
    input_basis: str,
    output_basis: str,
) -> PeriodicWork:
    return PeriodicWork(
        cell_identity=cell_identity,
        work_identity=identity,
        observation_schema="fixture.periodic",
        wavelength_nm=400,
        period_nm=300,
        height_nm=600,
        geometry=geometry,
        materials=PeriodicMaterials(
            atom_native_identity="fixture atom",
            atom_refractive_index=Decimal("2.0"),
            atom_source_reference=_reference("b"),
            substrate_native_identity="fixture substrate",
            substrate_refractive_index=Decimal("1.45"),
            substrate_source_reference=_reference("b"),
        ),
        source_references=(_reference("c"),),
        binding_reference=_reference("d"),
        capacity_scope="fixture",
        input_basis=input_basis,
        output_basis=output_basis,
        order_regime="zeroth order",
    )


def _execution() -> dict[str, object]:
    return {
        "native": False,
        "placement": {},
        "project": "fixture.fsp",
        "return_code": 0,
        "source": "fixture",
    }


def test_multi_order_choice_cannot_form_a_complete_coefficient_field() -> None:
    multi_order = replace(_height(), order_regime="multi order")

    with pytest.raises(
        ValueError,
        match="^coefficient_field_requires_zeroth_order$",
    ):
        require_coefficient_field_response(multi_order)


def test_propagation_projection_refuses_a_self_consistent_partial_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import metacraft.science.metalens.periodic_cell_evidence as response_module

    monkeypatch.setattr(
        response_module,
        "validate_height_choice",
        lambda *_args, **_kwargs: None,
    )
    work = _work(
        "work-080",
        cell_identity=("circular-pillar-height-0600nm-diameter-0080nm"),
        geometry=CircularCrossSection(80),
        input_basis="x linear",
        output_basis="transverse linear",
    )
    request = PeriodicTransmissionRequest(
        periodic_request_identity("transmission", (work.work_identity,)),
        (work,),
    )
    document = periodic_response_contract.decode_periodic_transmission(
        {
            "candidate": {
                "diameter_nm": 80,
                "height_nm": 600,
                "name": work.cell_identity,
                "shape": "circular pillar",
            },
            "construction_valid": True,
            "execution": _execution(),
            "phase": {"value": "0"},
            "phase_planes": "fixture planes",
            "power": {"leakage": "0", "useful": "1"},
            "solver_status": "complete",
            "transmission": {
                "imaginary_part": "0",
                "real_part": "1",
            },
            "warnings": [],
        }
    )
    admitted = AdmittedPeriodicTransmission(
        work.work_identity,
        document.observation,
        _reference("e"),
        _reference("f"),
        document,
    )
    batch = PropagationEvidenceBatch(
        request,
        ObservedPeriodicTransmission(
            request.request_identity,
            (admitted,),
            PeriodicResponseClosure(
                request.request_identity,
                ExternalActivityClosure.none(),
                ExternalActivityClosure.none(),
            ),
        ),
    )
    study = cast(
        Study,
        SimpleNamespace(design=compile_study(propagation_brief()).design),
    )

    with pytest.raises(ValueError, match="grid_incomplete"):
        batch.cell_library_document(
            study,
            _height(),
            height_choice_reference=_reference("a"),
        )


def test_jones_projection_refuses_one_pair_from_a_larger_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import metacraft.science.metalens.periodic_cell_evidence as response_module

    validated: list[tuple[HeightChoice, Reference]] = []

    def record_height_validation(
        _study: Study,
        height: HeightChoice,
        *,
        choice_reference: Reference,
    ) -> None:
        validated.append((height, choice_reference))

    monkeypatch.setattr(
        response_module,
        "validate_height_choice",
        record_height_validation,
    )
    geometry = RectangularCrossSection(80, 100)
    cell_identity = "rectangular-fin-height-0600nm-length-0100nm-width-0080nm"
    works = tuple(
        _work(
            f"work-{basis}",
            cell_identity=cell_identity,
            geometry=geometry,
            input_basis=f"{basis} linear",
            output_basis="cartesian",
        )
        for basis in ("x", "y")
    )
    request = PeriodicPolarizationRequest(
        periodic_request_identity(
            "polarization",
            tuple(work.work_identity for work in works),
        ),
        works,
    )
    def admit_polarization(
        work: PeriodicWork,
        basis: str,
        body_character: str,
        receipt_character: str,
    ) -> AdmittedPeriodicPolarization:
        document = periodic_response_contract.decode_periodic_polarization(
            {
                "basis": basis,
                "candidate": {
                    "geometry": {
                        "length_nm": 100,
                        "width_nm": 80,
                    },
                    "height_nm": 600,
                    "name": cell_identity,
                    "shape": "rectangular fin",
                },
                "execution": _execution(),
                "output_x": {
                    "imaginary_part": "0",
                    "real_part": "1",
                },
                "output_y": {
                    "imaginary_part": "0",
                    "real_part": "0",
                },
                "phase_planes": "fixture planes",
                "solver_status": "complete",
                "warnings": [],
            }
        )
        return AdmittedPeriodicPolarization(
            work.work_identity,
            document.observation,
            _reference(body_character),
            _reference(receipt_character),
            document,
        )

    admitted = tuple(
        admit_polarization(
            work,
            basis,
            body_character,
            receipt_character,
        )
        for work, basis, body_character, receipt_character in zip(
            works,
            ("x", "y"),
            ("e", "f"),
            ("a", "b"),
            strict=True,
        )
    )
    batch = JonesEvidenceBatch(
        request,
        ObservedPeriodicPolarization(
            request.request_identity,
            admitted,
            PeriodicResponseClosure(
                request.request_identity,
                ExternalActivityClosure.none(),
                ExternalActivityClosure.none(),
            ),
        ),
        PolarizationConvention(circular_input="right"),
    )
    study = cast(
        Study,
        SimpleNamespace(design=compile_study(geometric_brief()).design),
    )
    height = _height()
    height_reference = _reference("a")

    with pytest.raises(ValueError, match="grid_incomplete"):
        batch.document(
            study,
            height,
            height_choice_reference=height_reference,
            convention_reference=_reference("c"),
        )
    assert validated == [(height, height_reference)]
