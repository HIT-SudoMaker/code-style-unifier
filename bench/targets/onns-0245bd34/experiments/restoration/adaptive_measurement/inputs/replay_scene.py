from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import cast

import torch
from torch.utils.data import Dataset

from data import encode, load, perturb, prepare
from data.configs import (
    EncodingConfig,
    PerturbationConfig,
    PreparationConfig,
    SourceConfig,
)
from experiments.restoration.degradation import restoration_profile
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.input_protocol import (
    STANDARD_RESTORATION_ENCODING,
    STANDARD_RESTORATION_PREPARATION,
)


@dataclass(frozen=True, slots=True)
class AdaptiveReplayDataConfig:
    """Assemble a degraded SLM1 scene from the shared restoration pipeline."""

    source: SourceConfig
    preparation: PreparationConfig = STANDARD_RESTORATION_PREPARATION
    perturbation: PerturbationConfig = field(
        default_factory=lambda: restoration_profile("medium")
    )
    encoding: EncodingConfig = STANDARD_RESTORATION_ENCODING

    def __post_init__(self) -> None:
        if self.encoding.encoding_method != "intensity":
            raise invalid_restoration_contract(
                "Adaptive SLM replay requires zero-phase intensity encoding"
            )
        if self.preparation.array_resolution != (512, 512):
            raise invalid_restoration_contract(
                "Adaptive SLM replay requires the frozen 512 by 512 array"
            )


@dataclass(frozen=True, slots=True, eq=False)
class AdaptiveReplayScene:
    """A degraded SLM1 field plus an evaluator-only clean target."""

    scene_id: str
    degraded_intensity: torch.Tensor
    input_field: torch.Tensor
    evaluator_target_intensity: torch.Tensor
    provenance: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.scene_id, str) or not self.scene_id.strip():
            raise invalid_restoration_contract("scene_id must be non-empty")
        if (
            not isinstance(self.degraded_intensity, torch.Tensor)
            or tuple(self.degraded_intensity.shape) != (1, 512, 512)
            or torch.is_complex(self.degraded_intensity)
        ):
            raise invalid_restoration_contract(
                "degraded_intensity must be a real [1, 512, 512] tensor"
            )
        if (
            not isinstance(self.input_field, torch.Tensor)
            or tuple(self.input_field.shape) != (1, 512, 512)
            or not torch.is_complex(self.input_field)
        ):
            raise invalid_restoration_contract(
                "input_field must be a complex [1, 512, 512] tensor"
            )
        if (
            not isinstance(self.evaluator_target_intensity, torch.Tensor)
            or tuple(self.evaluator_target_intensity.shape) != (1, 512, 512)
            or torch.is_complex(self.evaluator_target_intensity)
        ):
            raise invalid_restoration_contract(
                "evaluator_target_intensity must be a real [1, 512, 512] tensor"
            )
        if not all(
            bool(torch.isfinite(value).all())
            for value in (
                self.degraded_intensity,
                self.input_field,
                self.evaluator_target_intensity,
            )
        ):
            raise invalid_restoration_contract("Adaptive replay tensors must be finite")
        if bool(torch.any(self.degraded_intensity < 0.0)):
            raise invalid_restoration_contract("degraded_intensity must be nonnegative")
        if bool(torch.any(self.evaluator_target_intensity < 0.0)):
            raise invalid_restoration_contract(
                "evaluator_target_intensity must be nonnegative"
            )
        encoded_intensity = self.input_field.abs().square().real
        if not torch.allclose(
            encoded_intensity,
            self.degraded_intensity,
            atol=1e-6,
            rtol=1e-5,
        ):
            raise invalid_restoration_contract(
                "input_field intensity must equal the degraded SLM1 scene"
            )
        object.__setattr__(
            self,
            "degraded_intensity",
            self.degraded_intensity.to(dtype=torch.float32).detach().clone(),
        )
        object.__setattr__(
            self,
            "input_field",
            self.input_field.to(dtype=torch.complex64).detach().clone(),
        )
        object.__setattr__(
            self,
            "evaluator_target_intensity",
            self.evaluator_target_intensity.to(dtype=torch.float32).detach().clone(),
        )
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))


class AdaptiveReplayDataset(Dataset):
    """Name prepared encoded samples as policy-hidden Adaptive scenes."""

    def __init__(self, source: Dataset) -> None:
        self._source = source
        scene_ids = _source_scene_ids(source)
        if scene_ids is None:
            scene_ids = tuple(
                _scene_id_from_encoded_sample(source[index])
                for index in range(len(source))  # type: ignore[arg-type]
            )
        if len(scene_ids) != len(source):  # type: ignore[arg-type]
            raise invalid_restoration_contract(
                "Adaptive replay metadata must identify every scene"
            )
        scene_indices: dict[str, int] = {}
        for index, scene_id in enumerate(scene_ids):
            if scene_id in scene_indices:
                raise invalid_restoration_contract(
                    f"duplicate Adaptive replay scene_id: {scene_id}"
                )
            scene_indices[scene_id] = index
        self._scene_indices = MappingProxyType(scene_indices)

    def __len__(self) -> int:
        return len(self._source)  # type: ignore[arg-type]

    def __getitem__(self, index: int) -> AdaptiveReplayScene:
        sample = self._source[index]
        if not isinstance(sample, Mapping):
            raise invalid_restoration_contract(
                "encoded replay sample must be a mapping"
            )
        provenance = sample.get("provenance")
        degraded_intensity = sample.get("input_image")
        input_field = sample.get("input_field")
        evaluator_target_intensity = sample.get("reference_image")
        if not isinstance(provenance, Mapping):
            raise invalid_restoration_contract(
                "encoded replay sample must preserve provenance"
            )
        for field_name, value in (
            ("input_image", degraded_intensity),
            ("input_field", input_field),
            ("reference_image", evaluator_target_intensity),
        ):
            if not isinstance(value, torch.Tensor):
                raise invalid_restoration_contract(
                    f"encoded replay sample {field_name} must be a tensor"
                )
        degraded_intensity = cast(torch.Tensor, degraded_intensity)
        input_field = cast(torch.Tensor, input_field)
        evaluator_target_intensity = cast(
            torch.Tensor,
            evaluator_target_intensity,
        )
        scene_id = provenance.get("image_id")
        if not isinstance(scene_id, str) or not scene_id:
            raise invalid_restoration_contract(
                "encoded replay provenance must include image_id"
            )
        return AdaptiveReplayScene(
            scene_id=scene_id,
            degraded_intensity=degraded_intensity,
            input_field=input_field,
            evaluator_target_intensity=evaluator_target_intensity,
            provenance=provenance,
        )

    def scene_by_id(self, scene_id: str) -> AdaptiveReplayScene:
        """Return the exact manifest-selected scene without positional guessing."""
        index = self._scene_indices.get(scene_id)
        if index is None:
            raise KeyError(f"Adaptive replay scene_id is unavailable: {scene_id}")
        return self[index]

    @property
    def scene_ids(self) -> tuple[str, ...]:
        return tuple(self._scene_indices)


def build_adaptive_replay_dataset(
    config: AdaptiveReplayDataConfig,
) -> AdaptiveReplayDataset:
    """Run the shared load, prepare, perturb, and zero-phase encode stages."""
    if not isinstance(config, AdaptiveReplayDataConfig):
        raise TypeError("config must be an AdaptiveReplayDataConfig")
    source = load(config.source)
    prepared = prepare(source, config.preparation)
    degraded = perturb(prepared, config.perturbation)
    encoded = encode(degraded, config.encoding)
    return AdaptiveReplayDataset(encoded)


def _scene_id_from_encoded_sample(sample: object) -> str:
    if not isinstance(sample, Mapping):
        raise invalid_restoration_contract("encoded replay sample must be a mapping")
    provenance = sample.get("provenance")
    scene_id = provenance.get("image_id") if isinstance(provenance, Mapping) else None
    if not isinstance(scene_id, str) or not scene_id:
        raise invalid_restoration_contract(
            "encoded replay provenance must include image_id"
        )
    return scene_id


def _source_scene_ids(source: object) -> tuple[str, ...] | None:
    records = getattr(source, "records", None)
    if records is not None:
        record_scene_ids = tuple(
            getattr(record, "image_id", None) for record in records
        )
        if all(isinstance(scene_id, str) and scene_id for scene_id in record_scene_ids):
            return cast(tuple[str, ...], record_scene_ids)
        return None
    for attribute_name in ("source_dataset", "prepared_dataset"):
        nested_source = getattr(source, attribute_name, None)
        if nested_source is None:
            continue
        nested_scene_ids = _source_scene_ids(nested_source)
        if nested_scene_ids is not None:
            return nested_scene_ids
    return None
