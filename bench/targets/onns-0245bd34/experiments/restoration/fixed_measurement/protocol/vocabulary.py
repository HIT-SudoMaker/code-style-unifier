from __future__ import annotations

from types import MappingProxyType
from typing import Final, Literal

from experiments.restoration.fixed_measurement.learning.schemas import ModelRole


FixedTrainingRole = Literal[
    "trained_phase_frontend_only",
    "digital_backend_only",
    "frozen_frontend_serial",
    "joint_frontend_serial",
]

FIXED_TRAINING_ROLES: Final[tuple[FixedTrainingRole, ...]] = (
    "trained_phase_frontend_only",
    "digital_backend_only",
    "frozen_frontend_serial",
    "joint_frontend_serial",
)

FIXED_ROLE_BY_MODEL_ROLE: Final[
    MappingProxyType[ModelRole, FixedTrainingRole]
] = MappingProxyType(
    {
        "frontend_only": "trained_phase_frontend_only",
        "backend_only": "digital_backend_only",
        "frozen_optical_frontend_digital_backend": "frozen_frontend_serial",
        "joint_optical_frontend_digital_backend": "joint_frontend_serial",
    }
)

MODEL_ROLE_BY_FIXED_ROLE: Final[
    MappingProxyType[FixedTrainingRole, ModelRole]
] = MappingProxyType(
    {
        fixed_role: model_role
        for model_role, fixed_role in FIXED_ROLE_BY_MODEL_ROLE.items()
    }
)


def fixed_role_for_model_role(model_role: ModelRole) -> FixedTrainingRole:
    """Return the sole scientific role for an active model topology."""
    return FIXED_ROLE_BY_MODEL_ROLE[model_role]
