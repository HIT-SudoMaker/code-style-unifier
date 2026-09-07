from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .portable import (
    MaterialColumns,
    MaterialRecord,
    MaterialSample,
    OpticalPoint,
    parse_local_table,
    parse_refractiveindex_info,
)
from .solver import (
    AdmittedSolverMaterial,
    MaterialConfirmationQuestion,
    SOLVER_MATERIAL_SCHEMA,
    SolverMaterial,
    SolverMaterialLibrary,
)
from .verification import (
    MaterialOutcome,
    MATERIAL_OBSERVATION_SCHEMA,
    MaterialObservationRequest,
    MaterialResponse,
    MaterialResponseContext,
    MaterialUnavailable,
    MaterialUnavailableReason,
    MaterialVerificationOutcome,
    MaterialVerificationRequest,
    ObservedMaterials,
    VerifiedMaterial,
    VerifiedMaterialBatch,
    material_observation_key,
)
from .source import MaterialSource

if TYPE_CHECKING:
    from .response import (
        RecordedMaterialResponse as RecordedMaterialResponse,
    )
    from .response import open_material_response as open_material_response

_LAZY_EXPORTS = {
    "RecordedMaterialResponse": (
        ".response",
        "RecordedMaterialResponse",
    ),
    "open_material_response": (
        ".response",
        "open_material_response",
    ),
}

__all__ = [
    "MaterialRecord",
    "MaterialSample",
    "MaterialColumns",
    "MaterialSource",
    "OpticalPoint",
    "AdmittedSolverMaterial",
    "MaterialConfirmationQuestion",
    "SOLVER_MATERIAL_SCHEMA",
    "SolverMaterial",
    "SolverMaterialLibrary",
    "MaterialOutcome",
    "MATERIAL_OBSERVATION_SCHEMA",
    "MaterialObservationRequest",
    "MaterialResponse",
    "MaterialResponseContext",
    "MaterialUnavailable",
    "MaterialUnavailableReason",
    "MaterialVerificationOutcome",
    "MaterialVerificationRequest",
    "ObservedMaterials",
    "RecordedMaterialResponse",
    "VerifiedMaterial",
    "VerifiedMaterialBatch",
    "material_observation_key",
    "open_material_response",
    "parse_local_table",
    "parse_refractiveindex_info",
]


def __getattr__(name: str) -> Any:
    """
    Keep material values importable without opening runtime response work.
    """

    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError as error:
        raise AttributeError(name) from error
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value
