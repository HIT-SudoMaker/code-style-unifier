from __future__ import annotations

from enum import Enum


class MaterialSource(str, Enum):
    """
    Names the three ways MetaCraft may obtain material meaning.
    """

    LOCAL_TABLE = "local table"
    REFRACTIVEINDEX_INFO_DATASET = "refractiveindex.info dataset"
    SOLVER_NATIVE = "solver native"
