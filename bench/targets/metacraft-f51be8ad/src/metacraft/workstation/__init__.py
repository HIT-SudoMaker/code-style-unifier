from __future__ import annotations

from datetime import datetime

from .model import (
    LANE_MEMORY_BYTES,
    Command,
    Demand,
    Host,
    Lane,
    Layout,
    LogicalProcessor,
    Memory,
    StaleLane,
    plan as _plan,
)
from .windows import Worker, observe, start


def plan(
    demand: Demand,
    *,
    host: Host | None = None,
    now: datetime | None = None,
) -> Layout:
    """
    Observe a missing Host at the package seam, then form one pure layout.
    """

    selected_host = observe() if host is None else host
    return _plan(demand, host=selected_host, now=now)

__all__ = [
    "Command",
    "Demand",
    "Host",
    "LANE_MEMORY_BYTES",
    "Lane",
    "Layout",
    "LogicalProcessor",
    "Memory",
    "StaleLane",
    "Worker",
    "plan",
    "start",
]
