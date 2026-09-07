from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from numbers import Integral, Real
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.pupil_aberrations import PupilAberrationState
from experiments.restoration.value_contracts import (
    finite_real,
    normalize_array_resolution,
)


OracleTargetName = Literal["siemens_star", "slanted_edge", "usaf_bars"]


@dataclass(frozen=True, slots=True)
class OracleLadderConfig:
    """Configure the falsification-first O1/O2/O3 Oracle Ladder."""

    project_root: Path | str = Path.cwd()
    array_resolution: tuple[int, int] = (512, 512)
    target_name: OracleTargetName = "siemens_star"
    aberration: PupilAberrationState = field(
        default_factory=lambda: PupilAberrationState(
            {"defocus": 1.25, "astigmatism_oblique": 0.55}
        )
    )
    input_blur_kernel_size: int = 5
    phase_optimization_iteration_count: int = 150
    phase_optimization_learning_rate: float = 0.08
    phase_levels: int = 256
    response_gain: float = 0.97
    drift_radians: float = 0.015
    crosstalk_mix: float = 0.04
    photon_count: float | None = None
    read_noise_standard_deviation: float = 0.0
    minimum_o3_gain_db: float = 1.0
    seed: int = 2026
    device: str = "cpu"

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", Path(self.project_root).resolve())
        object.__setattr__(
            self,
            "array_resolution",
            normalize_array_resolution(
                "array_resolution",
                self.array_resolution,
                minimum_size=16,
            ),
        )
        if self.target_name not in {"siemens_star", "slanted_edge", "usaf_bars"}:
            raise invalid_restoration_contract(
                "target_name must be one of: siemens_star, slanted_edge, usaf_bars"
            )
        if not isinstance(self.aberration, PupilAberrationState):
            raise TypeError("aberration must be a PupilAberrationState")
        for name in (
            "input_blur_kernel_size",
            "phase_optimization_iteration_count",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, Integral)
                or int(value) <= 0
            ):
                raise invalid_restoration_contract(f"{name} must be a positive integer")
            object.__setattr__(self, name, int(value))
        if self.input_blur_kernel_size % 2 == 0:
            raise invalid_restoration_contract("input_blur_kernel_size must be odd")
        if (
            isinstance(self.phase_levels, bool)
            or not isinstance(self.phase_levels, Integral)
            or int(self.phase_levels) < 2
        ):
            raise invalid_restoration_contract(
                "phase_levels must be an integer of at least 2"
            )
        object.__setattr__(self, "phase_levels", int(self.phase_levels))
        for name in (
            "response_gain",
            "drift_radians",
            "crosstalk_mix",
            "read_noise_standard_deviation",
            "minimum_o3_gain_db",
            "phase_optimization_learning_rate",
        ):
            object.__setattr__(self, name, finite_real(name, getattr(self, name)))
        if self.response_gain <= 0.0:
            raise invalid_restoration_contract("response_gain must be positive")
        if self.phase_optimization_learning_rate <= 0.0:
            raise invalid_restoration_contract(
                "phase_optimization_learning_rate must be positive"
            )
        if not 0.0 <= self.crosstalk_mix <= 1.0:
            raise invalid_restoration_contract("crosstalk_mix must be between 0 and 1")
        if self.read_noise_standard_deviation < 0.0:
            raise invalid_restoration_contract(
                "read_noise_standard_deviation must be nonnegative"
            )
        if self.photon_count is not None:
            photon_count = finite_real("photon_count", self.photon_count)
            if photon_count <= 0.0:
                raise invalid_restoration_contract("photon_count must be positive")
            object.__setattr__(self, "photon_count", photon_count)
        if (
            isinstance(self.seed, bool)
            or not isinstance(self.seed, Integral)
            or not 0 <= int(self.seed) <= 2**32 - 1
        ):
            raise invalid_restoration_contract(
                "seed must be an integer between 0 and 4294967295"
            )
        object.__setattr__(self, "seed", int(self.seed))
        if self.device not in {"cpu", "cuda"}:
            raise invalid_restoration_contract("device must be cpu or cuda")

    def _config_hash_payload(self) -> dict[str, object]:
        """Exclude filesystem and execution location from scientific identity."""
        return {
            "array_resolution": self.array_resolution,
            "target_name": self.target_name,
            "aberration": self.aberration,
            "input_blur_kernel_size": self.input_blur_kernel_size,
            "phase_optimization_iteration_count": (
                self.phase_optimization_iteration_count
            ),
            "phase_optimization_learning_rate": (self.phase_optimization_learning_rate),
            "phase_levels": self.phase_levels,
            "response_gain": self.response_gain,
            "drift_radians": self.drift_radians,
            "crosstalk_mix": self.crosstalk_mix,
            "photon_count": self.photon_count,
            "read_noise_standard_deviation": self.read_noise_standard_deviation,
            "minimum_o3_gain_db": self.minimum_o3_gain_db,
            "seed": self.seed,
        }


@dataclass(frozen=True, slots=True)
class OracleLadderResult:
    """Locate one immutable Adaptive oracle evidence record."""

    status: Literal["PASS", "FAIL"]
    run_id: str
    run_dir: Path
    metrics: Mapping[str, float]
    result_json: Path
    summary_md: Path

    def __post_init__(self) -> None:
        if self.status not in {"PASS", "FAIL"}:
            raise invalid_restoration_contract("status must be PASS or FAIL")
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise invalid_restoration_contract("run_id must be a non-empty string")
        object.__setattr__(self, "run_dir", Path(self.run_dir))
        object.__setattr__(self, "result_json", Path(self.result_json))
        object.__setattr__(self, "summary_md", Path(self.summary_md))
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))
