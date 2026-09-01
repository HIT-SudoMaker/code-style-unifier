from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
from types import MappingProxyType
from uuid import uuid4

import torch

from experiments.restoration.fixed_measurement.optics.frontend import RestorationFrontend


@dataclass(frozen=True, slots=True)
class FixedOpticalRecord:
    """Record branch-isolated intensities and reference-on interference outputs."""

    reference_arm_only: torch.Tensor
    zero_phase_processing_arm_only: torch.Tensor
    trained_phase_processing_arm_only: torch.Tensor
    zero_phase_interference_output: torch.Tensor
    trained_phase_interference_output: torch.Tensor
    zero_phase_interference_term: torch.Tensor
    trained_phase_interference_term: torch.Tensor
    input_intensity: torch.Tensor
    trained_phase_radians: torch.Tensor
    reference_phase_offset_radians: torch.Tensor

    @staticmethod
    def state_manifest() -> Mapping[str, Mapping[str, object]]:
        """Describe which arms and phase state produced each stored intensity."""
        return MappingProxyType(
            {
                "reference_arm_only": MappingProxyType(
                    {
                        "is_reference_enabled": True,
                        "is_processing_enabled": False,
                        "processing_phase_state": "not_applicable",
                    }
                ),
                "zero_phase_processing_arm_only": MappingProxyType(
                    {
                        "is_reference_enabled": False,
                        "is_processing_enabled": True,
                        "processing_phase_state": "zero",
                    }
                ),
                "trained_phase_processing_arm_only": MappingProxyType(
                    {
                        "is_reference_enabled": False,
                        "is_processing_enabled": True,
                        "processing_phase_state": "trained",
                    }
                ),
                "zero_phase_interference_output": MappingProxyType(
                    {
                        "is_reference_enabled": True,
                        "is_processing_enabled": True,
                        "processing_phase_state": "zero",
                    }
                ),
                "trained_phase_interference_output": MappingProxyType(
                    {
                        "is_reference_enabled": True,
                        "is_processing_enabled": True,
                        "processing_phase_state": "trained",
                    }
                ),
            }
        )

    def as_mapping(self) -> Mapping[str, torch.Tensor]:
        """Return the five directly observable optical states in narrative order."""
        return MappingProxyType(
            {
                "reference_arm_only": self.reference_arm_only,
                "zero_phase_processing_arm_only": (
                    self.zero_phase_processing_arm_only
                ),
                "trained_phase_processing_arm_only": (
                    self.trained_phase_processing_arm_only
                ),
                "zero_phase_interference_output": (
                    self.zero_phase_interference_output
                ),
                "trained_phase_interference_output": (
                    self.trained_phase_interference_output
                ),
            }
        )

    def write(
        self,
        path: Path | str,
        *,
        metadata: Mapping[str, object],
    ) -> Path:
        """Persist one immutable tensor record with its acquisition identity."""
        output_path = Path(path)
        if output_path.exists():
            raise FileExistsError(f"Fixed optical record already exists: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_name(
            f"._{output_path.name}.{uuid4().hex[:12]}.tmp"
        )
        payload = {
            "schema_version": "fixed_optical_record_v1",
            "metadata": dict(metadata),
            "state_manifest": {
                state_name: dict(state)
                for state_name, state in self.state_manifest().items()
            },
            "input_intensity": self.input_intensity,
            "trained_phase_radians": self.trained_phase_radians,
            "reference_phase_offset_radians": self.reference_phase_offset_radians,
            **dict(self.as_mapping()),
            "zero_phase_interference_term": self.zero_phase_interference_term,
            "trained_phase_interference_term": self.trained_phase_interference_term,
        }
        try:
            torch.save(payload, temporary_path)
            os.link(temporary_path, output_path)
        finally:
            temporary_path.unlink(missing_ok=True)
        return output_path


@torch.no_grad()
def record_fixed_optical_states(
    frontend: RestorationFrontend,
    input_field: torch.Tensor,
) -> FixedOpticalRecord:
    """Acquire the named Fixed controls without changing the trained phase."""
    if not isinstance(frontend, RestorationFrontend):
        raise TypeError("frontend must be a RestorationFrontend")
    zero_phase = frontend.phase_zero_baselines(input_field)
    reference_field, trained_processing_field = frontend.forward_optical_fields(
        input_field
    )
    zero_processing_field = zero_phase["e_field_process_phase_zero"]

    reference_arm_only = reference_field.abs().square().real
    zero_phase_processing_arm_only = zero_processing_field.abs().square().real
    trained_phase_processing_arm_only = (
        trained_processing_field.abs().square().real
    )
    zero_phase_interference_output = (
        reference_field + zero_processing_field
    ).abs().square().real
    trained_phase_interference_output = (
        reference_field + trained_processing_field
    ).abs().square().real
    zero_phase_interference_term = 2.0 * torch.real(
        reference_field * torch.conj(zero_processing_field)
    )
    trained_phase_interference_term = 2.0 * torch.real(
        reference_field * torch.conj(trained_processing_field)
    )

    return FixedOpticalRecord(
        reference_arm_only=_snapshot(reference_arm_only),
        zero_phase_processing_arm_only=_snapshot(
            zero_phase_processing_arm_only
        ),
        trained_phase_processing_arm_only=_snapshot(
            trained_phase_processing_arm_only
        ),
        zero_phase_interference_output=_snapshot(
            zero_phase_interference_output
        ),
        trained_phase_interference_output=_snapshot(
            trained_phase_interference_output
        ),
        zero_phase_interference_term=_snapshot(zero_phase_interference_term),
        trained_phase_interference_term=_snapshot(
            trained_phase_interference_term
        ),
        input_intensity=_snapshot(input_field.abs().square().real),
        trained_phase_radians=_snapshot(frontend._effective_phase_mask()),
        reference_phase_offset_radians=_snapshot(frontend.phase_offset_reference),
    )


def _snapshot(value: torch.Tensor) -> torch.Tensor:
    return value.detach().clone()
