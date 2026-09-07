from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from metacraft.authority import Document, reference_for
from metacraft.science.metalens.result import (
    PointwiseGeometricResult,
    PointwisePropagationResult,
    restore_result,
)
from tests.brief_fixtures import geometric_brief, propagation_brief
from tests.result_fixtures import (
    pointwise_geometric_result,
    pointwise_propagation_result,
)


def test_pointwise_propagation_result_replays_without_selection_or_field_work(
    tmp_path: Path,
    monkeypatch,
) -> None:
    brief = replace(
        propagation_brief(),
        numerical_aperture=Decimal("0.8"),
        focal_length_um=Decimal("0.25"),
    )
    recorded = pointwise_propagation_result(
        tmp_path / "propagation",
        brief,
        period_nm=240,
        height_nm=600,
    )
    result = cast(PointwisePropagationResult, recorded.conclusion)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("pointwise result replay repeated scientific work")

    monkeypatch.setattr(
        "metacraft.science.metalens.pointwise.select_pointwise_cells",
        forbidden,
    )
    monkeypatch.setattr(
        "metacraft.science.metalens.pointwise.form_pointwise_surface_field",
        forbidden,
    )
    restored = restore_result(
        result.document(),
        closure=recorded.closure,
        fetch=recorded.authority.fetch,
    )

    assert isinstance(restored, PointwisePropagationResult)
    assert restored.document().to_bytes() == result.document().to_bytes()
    assert restored.aperture.phase_levels is None


@pytest.mark.parametrize(
    ("brief", "record_result"),
    (
        (propagation_brief(), pointwise_propagation_result),
        (geometric_brief(), pointwise_geometric_result),
    ),
)
def test_pointwise_result_rejects_an_unrelated_caution_source(
    tmp_path: Path,
    brief,
    record_result,
) -> None:
    """
    A caution may cite only the scientific fabrication source that raised it.
    """

    prepared_brief = replace(
        brief,
        numerical_aperture=Decimal("0.8"),
        focal_length_um=Decimal("0.25"),
    )
    recorded = record_result(
        tmp_path / record_result.__name__,
        prepared_brief,
        period_nm=(240 if record_result is pointwise_propagation_result else 200),
        height_nm=600,
    )
    result = recorded.conclusion
    values = deepcopy(result.document().values)
    unrelated = Document("fixture.unrelated", {"kind": "unrelated"})
    values["conclusion"]["cautions"]["caution_001"]["source"] = (
        reference_for(unrelated.to_bytes()).as_mapping()
    )
    tampered = Document(result.document().schema_identifier, values)

    with pytest.raises(
        ValueError,
        match="result_caution_source_unreachable",
    ):
        restore_result(
            tampered,
            closure=recorded.closure,
            fetch=recorded.authority.fetch,
        )


def test_pointwise_geometric_result_replays_without_orientation_or_debye_work(
    tmp_path: Path,
    monkeypatch,
) -> None:
    brief = replace(
        geometric_brief(),
        numerical_aperture=Decimal("0.8"),
        focal_length_um=Decimal("0.25"),
    )
    recorded = pointwise_geometric_result(
        tmp_path / "geometric",
        brief,
        period_nm=200,
        height_nm=600,
    )
    result = cast(PointwiseGeometricResult, recorded.conclusion)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("geometric result replay repeated scientific work")

    monkeypatch.setattr(
        "metacraft.science.metalens.pointwise.form_geometric_surface_field",
        forbidden,
    )
    monkeypatch.setattr(
        "metacraft.science.metalens.focal_field_comparison.compare_vector_fields",
        forbidden,
    )
    restored = restore_result(
        result.document(),
        closure=recorded.closure,
        fetch=recorded.authority.fetch,
    )

    assert isinstance(restored, PointwiseGeometricResult)
    assert restored.document().to_bytes() == result.document().to_bytes()
    assert restored.aperture.phase_levels is None
