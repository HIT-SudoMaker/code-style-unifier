from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ...authority import Authority
from ...materials import MaterialResponse
from ..periodic_response import PeriodicResponse


class MetalensEvidenceAdapter(Protocol):
    """
    Open the two evidence ports against one fresh application root.
    """

    def open(
        self,
        *,
        authority: Authority,
        runs_directory: Path,
    ) -> tuple[PeriodicResponse, MaterialResponse]:
        """
        Bind evidence work to the root's Authority and runs directory.
        """

        ...
