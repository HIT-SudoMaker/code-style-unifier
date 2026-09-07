from __future__ import annotations

import pytest

from metacraft.external_activity import (
    ExternalActivityClosure,
    ExternalActivityOrigin,
)


def test_external_activity_requires_every_acquired_resource_to_be_settled() -> None:
    with pytest.raises(ValueError, match="external_activity_unsettled"):
        ExternalActivityClosure(
            origin=ExternalActivityOrigin.NATIVE,
            acquired_authority_work_count=1,
            settled_authority_work_count=0,
            started_external_execution_count=0,
            settled_external_execution_count=0,
            opened_product_session_count=0,
            closed_product_session_count=0,
            opened_local_placement_count=0,
            closed_local_placement_count=0,
        )


def test_recorded_external_activity_has_zero_current_call_counts() -> None:
    assert ExternalActivityClosure.recorded() == ExternalActivityClosure(
        origin=ExternalActivityOrigin.RECORDED,
        acquired_authority_work_count=0,
        settled_authority_work_count=0,
        started_external_execution_count=0,
        settled_external_execution_count=0,
        opened_product_session_count=0,
        closed_product_session_count=0,
        opened_local_placement_count=0,
        closed_local_placement_count=0,
    )
    with pytest.raises(
        ValueError,
        match="external_activity_origin_count_mismatch",
    ):
        ExternalActivityClosure(
            origin=ExternalActivityOrigin.RECORDED,
            acquired_authority_work_count=1,
            settled_authority_work_count=1,
            started_external_execution_count=0,
            settled_external_execution_count=0,
            opened_product_session_count=0,
            closed_product_session_count=0,
            opened_local_placement_count=0,
            closed_local_placement_count=0,
        )
