from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import final


class ExternalActivityOrigin(str, Enum):
    """
    Name how one call performed its external activity.
    """

    NONE = "none"
    NATIVE = "native"
    RECORDED = "recorded"


@final
@dataclass(frozen=True, slots=True)
class ExternalActivityClosure:
    """
    Prove that one call settled every acquired external resource.
    """

    origin: ExternalActivityOrigin
    acquired_authority_work_count: int
    settled_authority_work_count: int
    started_external_execution_count: int
    settled_external_execution_count: int
    opened_product_session_count: int
    closed_product_session_count: int
    opened_local_placement_count: int
    closed_local_placement_count: int

    def __post_init__(self) -> None:
        """
        Reject non-exact counts and any activity that remains unsettled.
        """

        counts = (
            self.acquired_authority_work_count,
            self.settled_authority_work_count,
            self.started_external_execution_count,
            self.settled_external_execution_count,
            self.opened_product_session_count,
            self.closed_product_session_count,
            self.opened_local_placement_count,
            self.closed_local_placement_count,
        )
        if type(self.origin) is not ExternalActivityOrigin:
            raise TypeError("external_activity_origin_invalid")
        if any(type(count) is not int or count < 0 for count in counts):
            raise ValueError("external_activity_count_invalid")
        if (
            self.acquired_authority_work_count
            != self.settled_authority_work_count
            or self.started_external_execution_count
            != self.settled_external_execution_count
            or self.opened_product_session_count
            != self.closed_product_session_count
            or self.opened_local_placement_count
            != self.closed_local_placement_count
        ):
            raise ValueError("external_activity_unsettled")
        if self.origin in {
            ExternalActivityOrigin.NONE,
            ExternalActivityOrigin.RECORDED,
        } and any(count != 0 for count in counts):
            raise ValueError("external_activity_origin_count_mismatch")

    @classmethod
    def none(cls) -> ExternalActivityClosure:
        """
        Return a call that performed no external activity.
        """

        return cls._zero(ExternalActivityOrigin.NONE)

    @classmethod
    def recorded(cls) -> ExternalActivityClosure:
        """
        Return an exact replay that performed no current-call activity.
        """

        return cls._zero(ExternalActivityOrigin.RECORDED)

    @classmethod
    def _zero(
        cls,
        origin: ExternalActivityOrigin,
    ) -> ExternalActivityClosure:
        return cls(origin, 0, 0, 0, 0, 0, 0, 0, 0)


def _native_activity(
    *,
    authority_work_count: int = 0,
    external_execution_count: int = 0,
    product_session_count: int = 0,
    local_placement_count: int = 0,
) -> ExternalActivityClosure:
    """
    Close one native call from its owner-produced exact counts.
    """

    return ExternalActivityClosure(
        origin=ExternalActivityOrigin.NATIVE,
        acquired_authority_work_count=authority_work_count,
        settled_authority_work_count=authority_work_count,
        started_external_execution_count=external_execution_count,
        settled_external_execution_count=external_execution_count,
        opened_product_session_count=product_session_count,
        closed_product_session_count=product_session_count,
        opened_local_placement_count=local_placement_count,
        closed_local_placement_count=local_placement_count,
    )


def _combine_external_activity(
    *closures: ExternalActivityClosure,
) -> ExternalActivityClosure:
    """
    Combine already-closed activity without inventing lifecycle facts.
    """

    if not closures:
        return ExternalActivityClosure.none()
    if any(
        closure.origin is ExternalActivityOrigin.NATIVE
        for closure in closures
    ):
        origin = ExternalActivityOrigin.NATIVE
    elif any(
        closure.origin is ExternalActivityOrigin.RECORDED
        for closure in closures
    ):
        origin = ExternalActivityOrigin.RECORDED
    else:
        origin = ExternalActivityOrigin.NONE
    if origin is not ExternalActivityOrigin.NATIVE:
        return ExternalActivityClosure._zero(origin)
    return ExternalActivityClosure(
        origin=origin,
        acquired_authority_work_count=sum(
            closure.acquired_authority_work_count
            for closure in closures
        ),
        settled_authority_work_count=sum(
            closure.settled_authority_work_count
            for closure in closures
        ),
        started_external_execution_count=sum(
            closure.started_external_execution_count
            for closure in closures
        ),
        settled_external_execution_count=sum(
            closure.settled_external_execution_count
            for closure in closures
        ),
        opened_product_session_count=sum(
            closure.opened_product_session_count
            for closure in closures
        ),
        closed_product_session_count=sum(
            closure.closed_product_session_count
            for closure in closures
        ),
        opened_local_placement_count=sum(
            closure.opened_local_placement_count
            for closure in closures
        ),
        closed_local_placement_count=sum(
            closure.closed_local_placement_count
            for closure in closures
        ),
    )

