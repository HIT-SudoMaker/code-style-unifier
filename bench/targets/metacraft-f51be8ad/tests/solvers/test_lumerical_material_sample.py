from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

from metacraft.authority import Authority, Reference
from metacraft.authority.session import AuthoritySession
from metacraft.authority.reference import reference_for
from metacraft.materials import (
    MaterialObservationRequest,
    MaterialVerificationRequest,
    VerifiedMaterialBatch,
)
from metacraft.science.metalens.material import (
    BoundMaterial,
    MaterialBinding,
)
from metacraft.solvers.lumerical_fdtd import (
    LumericalConfig,
    LumericalMaterialVerifier,
)
from metacraft.solvers.lumerical_fdtd.periodic_response import (
    restore_material_sample,
)
from metacraft.solvers.lumerical_fdtd.material import (
    LumericalMaterialSample,
    NativeIndexPoint,
    NativeMaterialSample,
    material_sample_key,
    sample_frequency_hz,
)
from metacraft.solvers.lumerical_fdtd.probe import (
    parse_license_capacity,
)
from metacraft.solvers.lumerical_fdtd.qualification import (
    InstallationObservation,
)
from metacraft.workstation import (
    Demand,
    Host,
    Layout,
    LogicalProcessor,
    Memory,
    plan,
)
from tests.solver_fakes import FakeProbe
from tests.lumerical_fixtures import (
    admit_solver_materials,
    fake_periodic_response,
)


GIBIBYTE = 1024**3
SAMPLE_WAVELENGTHS_NM = (355, 400)


def _config(tmp_path: Path) -> LumericalConfig:
    installation = tmp_path / "Lumerical"
    executable = installation / "bin" / "fdtd-solutions.exe"
    engine = installation / "bin" / "fdtd-engine.exe"
    api = installation / "api" / "python" / "lumapi.py"
    license_utility = tmp_path / "licensing" / "lmutil.exe"
    executable.parent.mkdir(parents=True)
    api.parent.mkdir(parents=True)
    license_utility.parent.mkdir(parents=True)
    executable.write_bytes(b"fixture")
    engine.write_bytes(b"fixture")
    api.write_text("# fixture", encoding="utf-8")
    license_utility.write_bytes(b"fixture")
    return LumericalConfig(
        executable=executable,
        python_api=api,
        license_utility=license_utility,
        license_server="fixture-license",
        runs_directory=tmp_path / "runs",
    )


def _layout(now: datetime) -> Layout:
    return plan(
        Demand(workers=4, worker_memory_bytes=GIBIBYTE),
        host=Host(
            identity="fixture-host",
            logical_processors=tuple(
                LogicalProcessor(index, 0, 0, index, 0, 0) for index in range(12)
            ),
            memory=(Memory(0, 64 * GIBIBYTE),),
            observed_at=now,
        ),
        now=now,
    )


def _point(wavelength_nm: int, index: str) -> NativeIndexPoint:
    return NativeIndexPoint(
        wavelength_nm=wavelength_nm,
        frequency_hz=Decimal(str(sample_frequency_hz(wavelength_nm))),
        refractive_index=Decimal(index),
        extinction_coefficient=Decimal("0.01"),
        fit_residual=Decimal("0.001"),
    )


def _sample() -> LumericalMaterialSample:
    frequencies = tuple(
        sample_frequency_hz(wavelength) for wavelength in SAMPLE_WAVELENGTHS_NM
    )
    material = NativeMaterialSample(
        family="silica",
        native_name="SiO2 fixture",
        fit_tolerance=Decimal("0.1"),
        fit_maximum_coefficients=6,
        minimum_tabulated_frequency_hz=Decimal(str(sample_frequency_hz(450))),
        maximum_tabulated_frequency_hz=Decimal(str(sample_frequency_hz(300))),
        points=(_point(355, "2.0"), _point(400, "3.0")),
        findings=(),
    )
    return LumericalMaterialSample(
        grid_wavelengths_nm=SAMPLE_WAVELENGTHS_NM,
        minimum_fit_frequency_hz=Decimal(str(min(frequencies))),
        maximum_fit_frequency_hz=Decimal(str(max(frequencies))),
        materials={"silica": material},
    )


def _cited_sample(
    sample: LumericalMaterialSample,
    *,
    binding: Reference | None = None,
    registration: Reference | None = None,
) -> LumericalMaterialSample:
    return sample.with_sources(
        binding_reference=binding or reference_for(b"solver binding"),
        registration_references={
            "silica": registration or reference_for(b"silica registration"),
        },
    )


def _task_sample(wavelength_nm: int) -> LumericalMaterialSample:
    frequency = Decimal(str(sample_frequency_hz(wavelength_nm)))
    material = NativeMaterialSample(
        family="silica",
        native_name="SiO2 fixture",
        fit_tolerance=Decimal("0.1"),
        fit_maximum_coefficients=6,
        minimum_tabulated_frequency_hz=frequency,
        maximum_tabulated_frequency_hz=frequency,
        points=(_point(wavelength_nm, "2.0"),),
        findings=(),
    )
    return LumericalMaterialSample(
        grid_wavelengths_nm=(wavelength_nm,),
        minimum_fit_frequency_hz=frequency,
        maximum_fit_frequency_hz=frequency,
        materials={"silica": material},
    )


def _verify_materials(
    *,
    authority: Authority,
    config: LumericalConfig,
    response,
    probe,
    materials,
    wavelength_nm: int,
) -> tuple[LumericalMaterialSample, Reference]:
    outcome = LumericalMaterialVerifier(
        session=AuthoritySession(authority),
        config=config,
        binding_reference=response.binding_reference,
        probe=probe,
    ).verify(
        MaterialVerificationRequest(
            observation_request=MaterialObservationRequest(
                families=tuple(selection.material.family for selection in materials),
                wavelength_nm=wavelength_nm,
            ),
            binding_reference=response.binding_reference,
            selections=materials,
        )
    )
    assert isinstance(outcome, VerifiedMaterialBatch)
    return restore_material_sample(
        authority,
        sample_reference=outcome.product_sample_reference,
    )


def _changed_material(
    sample: LumericalMaterialSample,
    **changes: object,
) -> LumericalMaterialSample:
    material = replace(sample.materials["silica"], **changes)
    return replace(sample, materials={"silica": material})


def _changed_point(
    sample: LumericalMaterialSample,
    **changes: object,
) -> LumericalMaterialSample:
    point = replace(sample.materials["silica"].points[0], **changes)
    return _changed_material(sample, points=(point,))


def _facts(
    now: datetime,
    sample: LumericalMaterialSample,
) -> InstallationObservation:
    return InstallationObservation(
        product_version="2025 r2",
        api_identity="fixture-api",
        lumerical_gui_limit=2,
        lumerical_solve_limit=2,
        resource_identity="fixture-resource",
        observed_at=now,
    )


def test_material_sample_round_trips_and_resolves_in_frequency() -> None:
    """
    Preserve sampled indices and interpolate only inside their grid.
    """

    sample = _sample()
    binding = Reference(
        f"sha256:{hashlib.sha256(b'binding').hexdigest()}",
        "application/json",
        f"sha256:{hashlib.sha256(b'metadata').hexdigest()}",
        12,
    )

    registration = reference_for(b"silica registration")
    restored = LumericalMaterialSample.from_document_bytes(
        sample.with_sources(
            binding_reference=binding,
            registration_references={"silica": registration},
        )
        .to_document()
        .to_bytes()
    )

    assert restored.binding_reference == binding
    assert restored.registration_references == {"silica": registration}
    assert restored.resolve("silica", 355).refractive_index == Decimal("2.0")
    middle = restored.resolve("silica", 375)
    assert Decimal("2.0") < middle.refractive_index < Decimal("3.0")
    with pytest.raises(ValueError, match="outside_grid"):
        restored.resolve("silica", 420)


def test_material_response_admits_sample_for_recovery(
    tmp_path: Path,
) -> None:
    """
    Recover the exact material sample from its solver binding.
    """

    now = datetime.now(UTC)
    authority_path = tmp_path / "authority"
    authority = Authority(authority_path)
    probe = FakeProbe(
        _facts(now, _sample()),
        material_sample=_task_sample(355),
    )
    config = _config(tmp_path)
    response = fake_periodic_response(
        authority=authority,
        config=config,
        probe=probe,
        planner=lambda _demand: _layout(now),
        now=now,
    )

    admitted, admitted_reference = _verify_materials(
        authority=authority,
        config=config,
        response=response,
        probe=probe,
        materials=admit_solver_materials(
            authority,
            {"silica": "SiO2 fixture"},
        ),
        wavelength_nm=355,
    )
    sample, reference = restore_material_sample(
        Authority(authority_path),
        sample_reference=admitted_reference,
    )

    assert reference == admitted_reference
    assert sample == admitted
    assert sample.binding_reference == response.binding_reference


def test_admitted_material_sample_closes_over_binding_and_registration(
    tmp_path: Path,
) -> None:
    """
    Keep every selected material reachable through admitted sample sources.
    """

    now = datetime.now(UTC)
    authority = Authority(tmp_path / "authority")
    probe = FakeProbe(
        _facts(now, _sample()),
        material_sample=_task_sample(355),
    )
    config = _config(tmp_path)
    response = fake_periodic_response(
        authority=authority,
        config=config,
        probe=probe,
        planner=lambda _demand: _layout(now),
        now=now,
    )
    admitted_materials = admit_solver_materials(
        authority,
        {"silica": "SiO2 fixture"},
    )

    _sampled, sample_reference = _verify_materials(
        authority=authority,
        config=config,
        response=response,
        probe=probe,
        materials=admitted_materials,
        wavelength_nm=355,
    )

    decision = next(
        decision
        for decision in authority.view().decisions
        if decision.body_reference == sample_reference
    )
    proposal = json.loads(authority.fetch(decision.proposal_reference))
    sources = tuple(
        Reference.from_mapping(reference) for reference in proposal["references"]
    )

    assert response.binding_reference in sources
    assert admitted_materials[0].reference in sources


def test_restore_material_sample_follows_its_exact_historical_reference(
    tmp_path: Path,
) -> None:
    """
    Restore immutable evidence after a later observation has the same key.
    """

    now = datetime.now(UTC)
    authority_path = tmp_path / "authority"
    authority = Authority(authority_path)
    probe = FakeProbe(
        _facts(now, _sample()),
        material_sample=_task_sample(355),
    )
    config = _config(tmp_path)
    response = fake_periodic_response(
        authority=authority,
        config=config,
        probe=probe,
        planner=lambda _demand: _layout(now),
        now=now,
    )
    materials = admit_solver_materials(
        authority,
        {"silica": "SiO2 fixture"},
    )
    first, first_reference = _verify_materials(
        authority=authority,
        config=config,
        response=response,
        probe=probe,
        materials=materials,
        wavelength_nm=355,
    )
    probe.material_sample = _changed_point(
        _task_sample(355),
        refractive_index=Decimal("2.1"),
    )
    _second, second_reference = _verify_materials(
        authority=authority,
        config=config,
        response=response,
        probe=probe,
        materials=materials,
        wavelength_nm=355,
    )

    restored, restored_reference = restore_material_sample(
        Authority(authority_path),
        sample_reference=first_reference,
    )

    assert second_reference != first_reference
    assert restored_reference == first_reference
    assert restored == first


def test_sample_key_retains_every_source_reference_and_the_fit_span() -> None:
    """
    Let any changed source or fit condition create a new sample identity.
    """

    sample = _cited_sample(_task_sample(355))
    changed_registration = _cited_sample(
        _task_sample(355),
        registration=reference_for(b"changed silica registration"),
    )
    changed_binding = _cited_sample(
        _task_sample(355),
        binding=reference_for(b"changed solver binding"),
    )
    changed_span = replace(
        sample,
        minimum_fit_frequency_hz=sample.minimum_fit_frequency_hz - Decimal("1"),
    )

    identities = {
        material_sample_key(candidate)
        for candidate in (
            sample,
            changed_registration,
            changed_binding,
            changed_span,
        )
    }

    assert len(identities) == 4


def test_sample_key_orders_registration_references_deterministically() -> None:
    """
    Let mapping order change no evidence identity.
    """

    first = reference_for(b"first registration")
    second = reference_for(b"second registration")
    sample = _task_sample(355)
    left = sample.with_sources(
        binding_reference=reference_for(b"solver binding"),
        registration_references={
            "silica": first,
            "silicon nitride": second,
        },
    )
    right = sample.with_sources(
        binding_reference=reference_for(b"solver binding"),
        registration_references={
            "silicon nitride": second,
            "silica": first,
        },
    )

    assert material_sample_key(left) == material_sample_key(right)


@pytest.mark.parametrize(
    "sample",
    (
        replace(
            _task_sample(355),
            minimum_fit_frequency_hz=Decimal("NaN"),
        ),
        replace(
            _task_sample(355),
            maximum_fit_frequency_hz=Decimal("Infinity"),
        ),
        _changed_material(
            _task_sample(355),
            fit_tolerance=Decimal("Infinity"),
        ),
        _changed_material(
            _task_sample(355),
            minimum_tabulated_frequency_hz=Decimal("NaN"),
        ),
        _changed_material(
            _task_sample(355),
            maximum_tabulated_frequency_hz=Decimal("Infinity"),
        ),
        _changed_point(
            _task_sample(355),
            frequency_hz=Decimal("NaN"),
        ),
        _changed_point(
            _task_sample(355),
            refractive_index=Decimal("NaN"),
        ),
        _changed_point(
            _task_sample(355),
            extinction_coefficient=Decimal("Infinity"),
        ),
        _changed_point(
            _task_sample(355),
            fit_residual=Decimal("NaN"),
        ),
    ),
)
def test_sample_rejects_non_finite_readback(
    sample: LumericalMaterialSample,
) -> None:
    """
    Reject non-finite fit, material, and point observations alike.
    """

    with pytest.raises(ValueError, match="material_sample_not_finite"):
        _cited_sample(sample).verify_readback(
            native_names={"silica": "SiO2 fixture"},
            wavelength_nm=355,
        )


@pytest.mark.parametrize(
    ("sample", "finding"),
    (
        (
            replace(
                _task_sample(355),
                minimum_fit_frequency_hz=Decimal("2"),
                maximum_fit_frequency_hz=Decimal("1"),
            ),
            "material_sample_fit_span_invalid",
        ),
        (
            replace(
                _task_sample(355),
                minimum_fit_frequency_hz=Decimal("1"),
                maximum_fit_frequency_hz=Decimal("2"),
            ),
            "material_sample_fit_span_uncovered",
        ),
        (
            replace(
                _task_sample(355),
                materials={
                    "silica": replace(
                        _task_sample(355).materials["silica"],
                        fit_maximum_coefficients=0,
                    ),
                },
            ),
            "material_fit_coefficients_invalid",
        ),
        (
            replace(
                _task_sample(355),
                materials={
                    "silica": replace(
                        _task_sample(355).materials["silica"],
                        points=(),
                    ),
                },
            ),
            "material_sample_points_empty",
        ),
        (
            _changed_material(
                _task_sample(355),
                minimum_tabulated_frequency_hz=Decimal("2"),
                maximum_tabulated_frequency_hz=Decimal("1"),
            ),
            "material_sample_band_invalid",
        ),
        (
            _changed_point(
                _task_sample(355),
                frequency_hz=Decimal("1"),
            ),
            "material_sample_point_frequency_changed",
        ),
        (
            _changed_material(
                _task_sample(355),
                minimum_tabulated_frequency_hz=Decimal("1"),
                maximum_tabulated_frequency_hz=Decimal("2"),
            ),
            "material_sample_point_out_of_band",
        ),
    ),
)
def test_sample_rejects_malformed_fit_and_point_shapes(
    sample: LumericalMaterialSample,
    finding: str,
) -> None:
    """
    Keep fit order, coverage, coefficients, and point presence explicit.
    """

    with pytest.raises(ValueError, match=finding):
        _cited_sample(sample).verify_readback(
            native_names={"silica": "SiO2 fixture"},
            wavelength_nm=355,
        )


def test_sample_rejects_noncanonical_point_order() -> None:
    """
    Require each native point sequence to follow the wavelength grid.
    """

    sample = _sample()
    material = sample.materials["silica"]
    reversed_points = replace(
        sample,
        materials={
            "silica": replace(
                material,
                points=tuple(reversed(material.points)),
            )
        },
    )

    with pytest.raises(ValueError, match="material_sample_points_not_canonical"):
        _cited_sample(reversed_points).verify_readback(
            native_names={"silica": "SiO2 fixture"},
            wavelength_nm=355,
        )


@pytest.mark.parametrize(
    ("role", "changed", "finding"),
    (
        (
            "atom",
            BoundMaterial(
                family="glass",
                source="solver native",
                native_name="SiO2 fixture",
                refractive_index=Decimal("2.0"),
                extinction_coefficient=Decimal("0.01"),
            ),
            "material_binding_family_mismatch:atom",
        ),
        (
            "substrate",
            BoundMaterial(
                family="silica",
                source="solver native",
                native_name="another native name",
                refractive_index=Decimal("2.0"),
                extinction_coefficient=Decimal("0.01"),
            ),
            "material_binding_native_name_mismatch:substrate",
        ),
    ),
)
def test_material_binding_rejects_identity_changed_from_its_sample(
    role: str,
    changed: BoundMaterial,
    finding: str,
) -> None:
    """
    Let one binding accept only family and native identity from its sample.
    """

    sample_reference = reference_for(b"material sample")
    sample = _cited_sample(_task_sample(355))
    silica = BoundMaterial(
        family="silica",
        source="solver native",
        native_name="SiO2 fixture",
        refractive_index=Decimal("2.0"),
        extinction_coefficient=Decimal("0.01"),
    )
    binding = MaterialBinding(
        brief_identity="sha256:" + "0" * 64,
        wavelength_nm=355,
        atom=changed if role == "atom" else silica,
        substrate=changed if role == "substrate" else silica,
        solver_binding_reference=sample.binding_reference,
        sample_reference=sample_reference,
        evidence_reference=reference_for(b"material binding"),
    )

    with pytest.raises(ValueError, match=finding):
        binding.require_sample_match(
            sample_reference=sample_reference,
            solver_binding_reference=sample.binding_reference,
            observed_wavelength_nm=355,
            observed_native_names={
                family: material.native_name
                for family, material in sample.materials.items()
            },
            observed_refractive_indices={"silica": Decimal("2.0")},
            observed_extinction_coefficients={"silica": Decimal("0.01")},
        )


@pytest.mark.parametrize(
    ("changed_field", "finding"),
    (
        ("wavelength", "material_binding_wavelength_mismatch"),
        (
            "refractive_index",
            "material_binding_refractive_index_mismatch:atom",
        ),
        (
            "extinction_coefficient",
            "material_binding_extinction_coefficient_mismatch:substrate",
        ),
    ),
)
def test_material_binding_rejects_optical_values_changed_from_its_sample(
    changed_field: str,
    finding: str,
) -> None:
    """
    Close wavelength and exact optical values over the cited sample.
    """

    sample_reference = reference_for(b"material sample")
    sample = _cited_sample(_task_sample(355))
    unchanged = BoundMaterial(
        family="silica",
        source="solver native",
        native_name="SiO2 fixture",
        refractive_index=Decimal("2.0"),
        extinction_coefficient=Decimal("0.01"),
    )
    changed = BoundMaterial(
        family="silica",
        source="solver native",
        native_name="SiO2 fixture",
        refractive_index=Decimal(
            "99" if changed_field == "refractive_index" else "2.0"
        ),
        extinction_coefficient=Decimal(
            "88" if changed_field == "extinction_coefficient" else "0.01"
        ),
    )
    binding = MaterialBinding(
        brief_identity="sha256:" + "0" * 64,
        wavelength_nm=999 if changed_field == "wavelength" else 355,
        atom=changed if changed_field == "refractive_index" else unchanged,
        substrate=(changed if changed_field == "extinction_coefficient" else unchanged),
        solver_binding_reference=sample.binding_reference,
        sample_reference=sample_reference,
        evidence_reference=reference_for(b"material binding"),
    )

    with pytest.raises(ValueError, match=finding):
        binding.require_sample_match(
            sample_reference=sample_reference,
            solver_binding_reference=sample.binding_reference,
            observed_wavelength_nm=355,
            observed_native_names={"silica": "SiO2 fixture"},
            observed_refractive_indices={"silica": Decimal("2.0")},
            observed_extinction_coefficients={"silica": Decimal("0.01")},
        )


def test_flexnet_parser_accepts_singular_and_plural_license_words() -> None:
    """
    Parse FlexNet's singular and plural usage reports alike.
    """

    singular = "Total of 500 licenses issued;  " "Total of 1 license in use"
    plural = "Total of 500 licenses issued;  " "Total of 12 licenses in use"

    assert parse_license_capacity(singular) == 499
    assert parse_license_capacity(plural) == 488
