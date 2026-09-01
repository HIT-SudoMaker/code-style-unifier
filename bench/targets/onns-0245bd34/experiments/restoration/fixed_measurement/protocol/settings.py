from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType


PROFILES = ("light", "medium", "heavy")
TRAINING_SEEDS = (42, 1337, 3407)
MICRO_BATCH_SIZE = 2
EFFECTIVE_BATCH_SIZE = 8
PRIMARY_MAX_OPTIMIZER_UPDATES = 6000
CAPACITY_MAX_OPTIMIZER_UPDATES = 3000

FIXED_TRAINING_POLICY = MappingProxyType(
    {
        ("optical", "light"): MappingProxyType(
            {
                "learning_rate": 3e-3,
                "loss_ssim_weight": 0.2,
                "loss_frequency_weight": 0.1,
                "phase_smoothness_weight": 0.0,
            }
        ),
        ("optical", "medium"): MappingProxyType(
            {
                "learning_rate": 3e-3,
                "loss_ssim_weight": 0.1,
                "loss_frequency_weight": 0.0,
                "phase_smoothness_weight": 0.0,
            }
        ),
        ("optical", "heavy"): MappingProxyType(
            {
                "learning_rate": 3e-3,
                "loss_ssim_weight": 0.1,
                "loss_frequency_weight": 0.0,
                "phase_smoothness_weight": 0.0,
            }
        ),
        ("digital", "light"): MappingProxyType(
            {"learning_rate": 1e-3, "loss_ssim_weight": 0.1}
        ),
        ("digital", "medium"): MappingProxyType(
            {"learning_rate": 1e-3, "loss_ssim_weight": 0.2}
        ),
        ("digital", "heavy"): MappingProxyType(
            {"learning_rate": 1e-3, "loss_ssim_weight": 0.2}
        ),
    }
)


@dataclass(frozen=True, slots=True)
class ProtocolInputs:
    """Immutable data, optics, and execution identity for Fixed Measurement."""

    project_root: Path | str
    operating_point_path: Path | str
    split_manifest: Mapping[str, object]
    dataset_root: str | Path = "data/raw"
    device: str = "auto"

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", Path(self.project_root))
        object.__setattr__(
            self,
            "operating_point_path",
            Path(self.operating_point_path),
        )
        object.__setattr__(
            self,
            "split_manifest",
            MappingProxyType(dict(self.split_manifest)),
        )
