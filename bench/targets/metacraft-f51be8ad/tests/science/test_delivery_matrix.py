from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

import metacraft.science.metalens.conduct as metalens_conduct
from metacraft.authority import Authority, Reference
from metacraft.authority.reference import reference_matches
from metacraft.field.fast_debye import CZTDebyeRealization, FFTDebyeRealization
from metacraft.science import CompletedResults, Result, conduct
from metacraft.science.metalens.brief import MonochromaticSpectrum
from metacraft.science.metalens.result import (
    GeometricResult,
    PointwiseGeometricResult,
    PointwisePropagationResult,
    PropagationResult,
    restore_conclusion,
)
from metacraft.solvers.lumerical_fdtd import LumericalMetalensEvidence
from metacraft.solvers.lumerical_fdtd.qualification import (
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseProof,
    PeriodicResponseQualification,
)
from tests.brief_fixtures import geometric_brief, propagation_brief
from tests.lumerical_fixtures import jones_response
from tests.propagation_fixtures import fake_metalens_ports
from tests.reference_surface_fakes import bounded_reference_surface
from tests.solver_fakes import FakeSession


def _result_science_signature(result: Result, authority: Authority) -> tuple:
    """Return explicit root-independent scientific result fields."""

    conclusion = restore_conclusion(result.document, fetch=authority.fetch)
    compiled = conclusion.closure.compiled
    aperture = conclusion.aperture
    common = (
        type(conclusion).__name__,
        conclusion.execution_origin,
        compiled.design.canonical_value(),
        tuple(
            (choice.claim, choice.method, choice.requires)
            for choice in compiled.route.choices
        ),
        tuple((fact.claim, fact.schema) for fact in compiled.evidence),
        aperture.footprint,
        tuple(int(size) for size in aperture.is_occupied.shape),
        aperture.site_count,
        aperture.spacing_nm,
        aperture.half_span_nm,
        (None if aperture.phase_levels is None else aperture.phase_levels.tolist()),
        conclusion.focus.as_mapping(),
    )
    if isinstance(conclusion, PropagationResult):
        specific = (
            conclusion.phase_set.levels,
            conclusion.phase_set.phase_planes,
            tuple(
                (
                    state.phase_level,
                    state.target_phase,
                    state.realized_phase,
                    state.transmission_real,
                    state.transmission_imaginary,
                    state.useful_power,
                    state.leakage_power,
                )
                for state in conclusion.phase_set.states
            ),
        )
    elif isinstance(conclusion, GeometricResult):
        specific = (
            conclusion.orientation_relation.converted_phase,
            conclusion.orientation_relation.phase_sign,
        )
    elif isinstance(conclusion, PointwisePropagationResult):
        comparison = conclusion.focal_comparison
        specific = (
            conclusion.surfaces.cell_identities,
            len(conclusion.library.responses),
            comparison.observed_method,
            comparison.ideal_method,
            comparison.aligned_complex_error,
            comparison.unit_integral_intensity_error,
            comparison.observed_to_ideal_scale,
            comparison.input_longitudinal_power_w,
            comparison.output_longitudinal_power_w,
        )
    elif isinstance(conclusion, PointwiseGeometricResult):
        comparison = conclusion.focal_comparison
        specific = (
            conclusion.orientation_relation.converted_phase,
            conclusion.orientation_relation.phase_sign,
            conclusion.transform.requested_input_basis,
            conclusion.transform.phase_sign,
            comparison.observed_method,
            comparison.ideal_method,
            comparison.aligned_complex_error,
            comparison.unit_integral_intensity_error,
            comparison.observed_to_ideal_scale,
            comparison.input_longitudinal_power_w,
            comparison.output_longitudinal_power_w,
        )
    else:
        raise AssertionError(type(conclusion).__name__)
    return common, specific


def _assert_result_provenance(
    result: Result,
    authority: Authority,
    *,
    brief_identity: str,
) -> None:
    """Prove closure shape and every root-local reference relationship."""

    conclusion = restore_conclusion(result.document, fetch=authority.fetch)
    closure = conclusion.closure
    compiled = closure.compiled
    assert closure.brief_identity == brief_identity == compiled.brief_identity
    assert closure.bindings == tuple(
        dict.fromkeys(
            fact.binding_reference
            for fact in compiled.evidence
            if fact.binding_reference is not None
        )
    )
    assert closure.evidence == tuple(fact.reference for fact in compiled.evidence)
    assert result.sources == conclusion.references()
    assert closure.study.reference in result.sources
    assert len(set(result.sources)) == len(result.sources)
    values = _mapping(result.document.values)
    assert values["provenance"] == {"replay": "authority"}
    assert values["origin"] == {"execution": conclusion.execution_origin.value}
    encoded_evidence = _mapping(values["evidence"])
    assert set(encoded_evidence) == {fact.claim for fact in compiled.evidence}
    assert all(
        _reference(encoded_evidence[fact.claim]) == fact.reference
        for fact in compiled.evidence
    )
    for reference in tuple(
        dict.fromkeys(
            (
                result.reference,
                *result.sources,
                *closure.references(),
            )
        )
    ):
        assert reference_matches(reference, authority.fetch(reference))


def _mapping(value: object) -> Mapping[str, object]:
    assert isinstance(value, Mapping)
    return value


def _reference(value: object) -> Reference:
    return Reference.from_mapping(_mapping(value))


def test_public_conduct_delivers_three_three_one_one_deterministically(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Complete the four bounded family representatives through public conduct.
    """

    brief_cases = (
        (
            "bounded-low-propagation",
            replace(
                propagation_brief(),
                operating_spectrum=MonochromaticSpectrum(wavelength_nm=940),
                cell_period_nm=290,
                atom_height_nm=550,
                focal_length_um=Decimal("20"),
                numerical_aperture=Decimal("0.48"),
            ),
        ),
        (
            "bounded-low-geometric",
            replace(
                geometric_brief(),
                operating_spectrum=MonochromaticSpectrum(wavelength_nm=940),
                cell_period_nm=290,
                atom_height_nm=550,
                focal_length_um=Decimal("20"),
                numerical_aperture=Decimal("0.48"),
                dimension_step_nm=29,
            ),
        ),
        (
            "bounded-pointwise-propagation",
            replace(
                propagation_brief(),
                operating_spectrum=MonochromaticSpectrum(wavelength_nm=1550),
                cell_period_nm=800,
                atom_height_nm=900,
                numerical_aperture=Decimal("0.8"),
                focal_length_um=Decimal("10"),
                dimension_step_nm=20,
            ),
        ),
        (
            "bounded-pointwise-geometric",
            replace(
                geometric_brief(),
                operating_spectrum=MonochromaticSpectrum(wavelength_nm=1550),
                cell_period_nm=800,
                atom_height_nm=900,
                numerical_aperture=Decimal("0.8"),
                focal_length_um=Decimal("10"),
                dimension_step_nm=100,
            ),
        ),
    )
    application_roots = {label: tmp_path / label for label, _brief in brief_cases}
    response_calls = {
        "linear_transmission": 0,
        "propagation": 0,
        "reference_surface": 0,
        "termination": 0,
    }
    native_result = FakeSession.result

    def routed_result(
        session: FakeSession,
        name: str,
        result_name: str,
    ) -> dict[str, object]:
        response_calls[result_name] += 1
        if result_name == "linear_transmission":
            return dict(jones_response(session._objects))
        if result_name == "reference_surface":
            return bounded_reference_surface(session)
        return dict(native_result(session, name, result_name))

    monkeypatch.setattr(FakeSession, "result", routed_result)
    monkeypatch.setattr(
        metalens_conduct,
        "observe_czt_debye",
        lambda: CZTDebyeRealization(device="cpu", pupil_samples=65),
    )
    monkeypatch.setattr(
        metalens_conduct,
        "observe_fft_debye",
        lambda: FFTDebyeRealization(device="cpu", pupil_samples=65),
    )
    proof = PeriodicResponseProof(
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.qualified(PERIODIC_POLARIZATION_RESPONSE),
            PeriodicResponseQualification.qualified(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        )
    )
    delivered: list[tuple[Result, Path]] = []
    result_counts = []
    for label, brief in brief_cases:
        ports = fake_metalens_ports(
            brief,
            application_roots[label],
            monkeypatch,
            response_proof=proof,
        )
        assert type(ports["evidence_adapter"]) is LumericalMetalensEvidence
        outcome = conduct(brief, **ports)
        assert isinstance(outcome, CompletedResults)
        result_counts.append(len(outcome.results))
        authority = Authority(application_roots[label] / "authority")
        for result in outcome.results:
            _assert_result_provenance(
                result,
                authority,
                brief_identity=outcome.brief_identity,
            )
            delivered.append((result, application_roots[label]))

    assert tuple(result_counts) == (3, 3, 1, 1)
    assert len(delivered) == 8
    assert len({result.reference for result, _root in delivered}) == 8
    assert all(response_calls.values())

    repeated: list[tuple[Result, Path]] = []
    for label, brief in brief_cases:
        repeated_root = tmp_path / f"{label}-repeat"
        outcome = conduct(
            brief,
            **fake_metalens_ports(
                brief,
                repeated_root,
                monkeypatch,
                response_proof=proof,
            ),
        )
        assert isinstance(outcome, CompletedResults)
        authority = Authority(repeated_root / "authority")
        for result in outcome.results:
            _assert_result_provenance(
                result,
                authority,
                brief_identity=outcome.brief_identity,
            )
            repeated.append((result, repeated_root))
    assert tuple(
        _result_science_signature(
            result,
            Authority(root / "authority"),
        )
        for result, root in repeated
    ) == tuple(
        _result_science_signature(
            result,
            Authority(root / "authority"),
        )
        for result, root in delivered
    )
