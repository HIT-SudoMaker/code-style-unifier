from __future__ import annotations

from copy import deepcopy

import pytest

from metacraft.authority import Document
from metacraft.field.evidence import FIELD_SCHEMA
from metacraft.science.metalens.focus import FOCAL_REGION_SCHEMA
from metacraft.science.metalens.result import (
    GeometricResult,
    PropagationResult,
    conclude,
    restore_result,
)
from tests.result_fixtures import (
    RecordedResult,
    geometric_result,
    propagation_results,
)


@pytest.fixture(scope="module")
def propagation_records(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[int, RecordedResult]:
    """
    Share one admitted prefix across all three quantization assertions.
    """

    records = propagation_results(
        tmp_path_factory.mktemp("propagation-results")
    )
    return {
        record.conclusion.phase_level_count: record
        for record in records
        if isinstance(record.conclusion, PropagationResult)
    }


@pytest.fixture(scope="module")
def recorded_geometric(
    tmp_path_factory: pytest.TempPathFactory,
) -> RecordedResult:
    """
    Share one recorded geometric conclusion across boundary assertions.
    """

    return geometric_result(tmp_path_factory.mktemp("geometric-result"))


@pytest.mark.parametrize("levels", (8, 12, 16))
def test_propagation_concludes_one_exact_fabrication(
    propagation_records: dict[int, RecordedResult],
    levels: int,
) -> None:
    recorded = propagation_records[levels]
    result = recorded.conclusion

    assert isinstance(result, PropagationResult)
    assert result.phase_level_count == levels
    assert set(result.document().values) == {
        "closure",
        "conclusion",
        "evidence",
        "evaluation",
        "fabrication",
        "origin",
        "provenance",
    }
    assert result.document().values["fabrication"] == {
        "aperture": result.aperture_reference.as_mapping(),
        "phase_set": result.phase_set_reference.as_mapping(),
    }
    if levels == 8:
        assert conclude(
            recorded.study,
            recorded.closure,
            fetch=recorded.authority.fetch,
        ).document().to_bytes() == result.document().to_bytes()


def test_geometric_concludes_one_continuous_fabrication(
    recorded_geometric: RecordedResult,
) -> None:
    recorded = recorded_geometric
    result = recorded.conclusion

    assert isinstance(result, GeometricResult)
    assert result.aperture.phase_levels is None
    assert set(result.document().values["fabrication"]) == {
        "aperture",
        "cell_choice",
        "orientations",
    }
    encoded = str(result.document().values)
    for copied_authority in (
        "aim",
        "objective",
        "strategy",
            "regime",
            "proof",
            "advice",
        ):
        assert copied_authority not in encoded


@pytest.mark.parametrize(
    "foreign_part",
    ("phase_set", "focus", "closure"),
)
def test_result_rejects_a_reference_from_another_closure(
    propagation_records: dict[int, RecordedResult],
    recorded_geometric: RecordedResult,
    foreign_part: str,
) -> None:
    own = propagation_records[8]
    other = (
        recorded_geometric
        if foreign_part == "focus"
        else propagation_records[12]
    )
    values = deepcopy(dict(own.conclusion.document().values))
    if foreign_part == "phase_set":
        values["fabrication"]["phase_set"] = (
            other.conclusion.phase_set_reference.as_mapping()
        )
    elif foreign_part == "focus":
        values["conclusion"]["focus"] = (
            other.conclusion.focus_reference.as_mapping()
        )
    else:
        values["closure"] = other.closure.study.reference.as_mapping()

    with pytest.raises(ValueError):
        restore_result(
            Document(
                own.conclusion.document().schema_identifier,
                values,
            ),
            closure=own.closure,
            fetch=own.authority.fetch,
        )


@pytest.mark.parametrize(
    ("evaluation_name", "schema"),
    (
        ("field", FIELD_SCHEMA),
        ("focal_region", FOCAL_REGION_SCHEMA),
    ),
)
def test_result_rejects_foreign_evaluation_in_the_same_authority(
    propagation_records: dict[int, RecordedResult],
    evaluation_name: str,
    schema: str,
) -> None:
    recorded = propagation_records[8]
    foreign_reference = recorded.session.admit_document(
        Document(schema, {"foreign": evaluation_name})
    )
    values = deepcopy(dict(recorded.conclusion.document().values))
    values["evaluation"][evaluation_name] = (
        foreign_reference.as_mapping()
    )

    with pytest.raises(
        ValueError,
        match=f"{evaluation_name}_reference_mismatch",
    ):
        restore_result(
            Document(
                recorded.conclusion.document().schema_identifier,
                values,
            ),
            closure=recorded.closure,
            fetch=recorded.authority.fetch,
        )


def test_conclude_rejects_a_foreign_task_and_proof_closure(
    propagation_records: dict[int, RecordedResult],
) -> None:
    own = propagation_records[8]
    other = propagation_records[12]

    with pytest.raises(ValueError, match="result_study_mismatch"):
            conclude(
                own.study,
                other.closure,
                fetch=own.authority.fetch,
            )
