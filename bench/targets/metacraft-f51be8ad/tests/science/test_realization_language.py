from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from metacraft.authority import Document, Reference
from metacraft.science.metalens.aperture import (Cell, Circle, Ellipse,
                                                 Material, Rectangle, Response)
from metacraft.science.metalens.focal_field_comparison import \
    FocalFieldComparison
from metacraft.science.metalens.focus import FocusConvergence, HalfMaximum
from metacraft.science.metalens.geometric_phase import OrientationRelation
from metacraft.science.metalens.propagation_phase import (
    PropagationCellLibrary, PropagationResponse)
from metacraft.science.result import EvidenceOrigin


def _reference(digit: str, size: int) -> Reference:
    return Reference(
        content_hash=f"sha256:{digit * 64}",
        media_type="application/json",
        metadata_content_hash=f"sha256:{str(int(digit) + 1) * 64}",
        size_bytes=size,
    )


def test_realization_names_encode_the_existing_boundary_shapes() -> None:
    """
    Public realization language changes without changing durable documents.
    """

    first = _reference("1", 3)
    second = _reference("3", 5)
    rectangle = Rectangle(short_side_nm=80, long_side_nm=140)
    ellipse = Ellipse(minor_axis_nm=100, major_axis_nm=300)
    response = Response(
        "converted",
        real_part=Decimal("0.5"),
        imaginary_part=Decimal("-0.25"),
        power=Decimal("0.3125"),
    )
    relation = OrientationRelation(
        cell_id="cell",
        converted_phase=Decimal("1.25"),
        phase_sign=1,
        cell_choice_reference=first,
        binding_reference=second,
        library_reference=first,
        convention_reference=second,
        source_references=(first, second),
    )

    assert rectangle.as_mapping() == {"length_nm": 140, "width_nm": 80}
    assert ellipse.as_mapping() == {"major_nm": 300, "minor_nm": 100}
    assert response.as_mapping() == {
        "channel": "converted",
        "imaginary": "-0.25",
        "power": "0.3125",
        "real": "0.5",
    }
    assert relation.identity == (
        "sha256:2b8d3951afa177e467ee7c25490ad5036e392105c88cfe8d"
        "717c4413a1ecf50e"
    )
    assert hashlib.sha256(relation.document().to_bytes()).hexdigest() == (
        "fc78808b63e08500a1cd7494219a457f9b0f7d112151a652"
        "9974de5c2c20f42b"
    )


def test_positive_predicates_keep_the_existing_serialized_keys() -> None:
    """
    Positive Python predicates map explicitly to established evidence names.
    """

    reference = _reference("1", 3)
    cell = Cell(
        identity="cell",
        atom=Material("silicon", "source"),
        substrate=Material("silica", "source"),
        period_nm=500,
        height_nm=600,
        geometry=Circle(100),
        source=reference,
    )
    response = PropagationResponse(
        binding_reference=reference,
        height_choice_reference=reference,
        phase_planes="input-to-output",
        cell=cell,
        transmission_real=Decimal("0.5"),
        transmission_imaginary=Decimal("-0.25"),
        realized_phase=Decimal("1.25"),
        useful_power=Decimal("0.3125"),
        leakage_power=Decimal("0"),
        solver_status="complete",
        warnings=(),
        is_construction_valid=True,
        execution_origin=EvidenceOrigin.NATIVE,
        source_reference=reference,
    )
    document = PropagationCellLibrary.document_from(
        binding_reference=reference,
        height_choice_reference=reference,
        phase_planes="input-to-output",
        responses=(response,),
    )

    assert HalfMaximum(1.0, 2.0, 1.0, is_bracketed=True).as_mapping() == {
        "bracketed": True,
        "lower_m": "1",
        "upper_m": "2",
        "width_m": "1",
    }
    assert FocusConvergence(
        5,
        0.1,
        is_locally_refined=True,
    ).as_mapping() == {
        "locally_refined": True,
        "sample_count": 5,
        "smallest_step_m": "0.10000000000000001",
    }
    assert document.values["responses"]["cell"]["construction_valid"] is True
    assert hashlib.sha256(document.to_bytes()).hexdigest() == (
        "929082830bcf8838d7ad56efc6758f60b95e861ec6775856"
        "b89cfb89927bdeb2"
    )


def test_focal_field_comparison_uses_one_current_scientific_schema() -> None:
    """
    Observed and ideal names remain explicit while the wire shape stays fixed.
    """

    first = _reference("1", 3)
    second = _reference("3", 5)
    comparison = FocalFieldComparison(
        observed_field_reference=first,
        ideal_field_reference=second,
        observed_binding_reference=second,
        ideal_binding_reference=first,
        observed_method="observed",
        ideal_method="ideal",
        aligned_complex_error=0.1,
        unit_integral_intensity_error=0.2,
        observed_to_ideal_scale=0.9 + 0.1j,
        input_longitudinal_power_w=0.4,
        output_longitudinal_power_w=0.5,
    )

    assert comparison.document().schema_identifier == (
        "metacraft.science.metalens.unit_integral_focal_field_comparison"
    )
    assert set(comparison.document().values) == {
        "observed_binding_reference",
        "observed_field_reference",
        "observed_method",
        "aligned_complex_error",
        "unit_integral_intensity_error",
        "observed_to_ideal_scale",
        "ideal_binding_reference",
        "ideal_field_reference",
        "ideal_method",
        "input_longitudinal_power_w",
        "output_longitudinal_power_w",
    }


def test_stale_focal_comparison_schema_fails_without_rewriting_root(
    tmp_path: Path,
) -> None:
    witness = json.loads(
        Path(
            "tests/fixtures/focal_comparison/fixed-point-c46e663.json"
        ).read_text(encoding="utf-8")
    )
    witnessed_document = witness["comparison_document"]
    stale = Document(
        str(witnessed_document["schema_identifier"]),
        witnessed_document["values"],
    )
    stale_body = stale.to_bytes()
    assert hashlib.sha256(stale_body).hexdigest() == (
        witness["comparison_document_sha256"]
    )
    retained = tmp_path / "authority" / "objects" / "stale-comparison.json"
    retained.parent.mkdir(parents=True)
    retained.write_bytes(stale_body)
    before = retained.read_bytes()

    with pytest.raises(ValueError, match="focal_comparison_schema_invalid"):
        FocalFieldComparison.from_document(
            Document.from_bytes(retained.read_bytes())
        )

    assert retained.read_bytes() == before
