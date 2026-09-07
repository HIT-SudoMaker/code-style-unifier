from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import InitVar, dataclass, field
from typing import cast

import torch


_FIELD_REQUIRED = "{field_name} is required"
_FIELD_TENSOR_REQUIRED = "{field_name} must be a tensor"
_FIELD_SHAPE_REQUIRED = "{field_name} must have shape {shape}"
_FIELD_FINITE_REQUIRED = "{field_name} must contain finite values"
_IMAGE_FLOAT_REQUIRED = "{field_name} must be a real floating-point tensor"
_SHARED_SHAPE_REQUIRED = (
    "clean_image, degraded_image, and input_field must share a shape"
)
_SINGLE_CHANNEL_REQUIRED = "restoration tensors must have exactly one channel"
_COMPLEX_FIELD_REQUIRED = "input_field must be complex"
_PROVENANCE_MAPPING_REQUIRED = "provenance must be a mapping"
_INTENSITY_MATCH_REQUIRED = "abs(input_field)^2 must match degraded_image"
_CANONICAL_BATCH_FIELDS = {
    "clean_image",
    "degraded_image",
    "input_field",
    "provenance",
}
_LEGACY_BATCH_FIELDS = {"input_image"}
_ADDITIONAL_FIELD_NAME_REQUIRED = "additional batch field names must be strings"
_CANONICAL_FIELD_SHADOWED = "additional fields must not shadow canonical fields"


class RestorationDataContractError(ValueError):
    """
    表示样本不满足复原数据契约
    """


@dataclass(frozen=True, slots=True)
class RestorationScene:
    """
    表示公共数据总线中的单个复原场景
    """

    clean_image: torch.Tensor
    degraded_image: torch.Tensor
    input_field: torch.Tensor
    provenance: Mapping[str, object]

    def __post_init__(self) -> None:
        """
        校验单场景物理语义
        """
        _validate_restoration_tensors(
            clean_image=self.clean_image,
            degraded_image=self.degraded_image,
            input_field=self.input_field,
            expected_dimensions=3,
            expected_shape_label="(C, H, W)",
        )
        _validate_provenance(self.provenance)

    @classmethod
    def from_sample(cls, sample: Mapping[str, object]) -> "RestorationScene":
        """
        从显式命名字段构造复原场景
        """
        return cls(
            clean_image=cast(torch.Tensor, _required(sample, "clean_image")),
            degraded_image=cast(torch.Tensor, _required(sample, "degraded_image")),
            input_field=cast(torch.Tensor, _required(sample, "input_field")),
            provenance=cast(Mapping[str, object], _required(sample, "provenance")),
        )


@dataclass(frozen=True, slots=True)
class RestorationBatch(Mapping[str, object]):
    """
    表示保持映射兼容性的复原批次
    """

    clean_image: torch.Tensor
    degraded_image: torch.Tensor
    input_field: torch.Tensor
    provenance: Mapping[str, object]
    additional_fields: InitVar[Mapping[str, object] | None] = None
    _fields: Mapping[str, object] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(
        self,
        additional_fields: Mapping[str, object] | None,
    ) -> None:
        """
        校验批量训练物理语义
        """
        _validate_restoration_tensors(
            clean_image=self.clean_image,
            degraded_image=self.degraded_image,
            input_field=self.input_field,
            expected_dimensions=4,
            expected_shape_label="(B, C, H, W)",
        )
        _validate_provenance(self.provenance)
        extras = dict(additional_fields or {})
        if any(not isinstance(name, str) for name in extras):
            raise RestorationDataContractError(_ADDITIONAL_FIELD_NAME_REQUIRED)
        if _CANONICAL_BATCH_FIELDS.intersection(extras):
            raise RestorationDataContractError(_CANONICAL_FIELD_SHADOWED)
        fields = {
            "clean_image": self.clean_image,
            "degraded_image": self.degraded_image,
            "input_field": self.input_field,
            "provenance": self.provenance,
            **extras,
        }
        object.__setattr__(self, "_fields", fields)

    @classmethod
    def from_collated(cls, batch: Mapping[str, object]) -> "RestorationBatch":
        """
        从公共管线批量输出构造复原批次
        """
        additional_fields = {
            name: value
            for name, value in batch.items()
            if name not in _CANONICAL_BATCH_FIELDS
            and name not in _LEGACY_BATCH_FIELDS
        }
        return cls(
            clean_image=cast(torch.Tensor, _required(batch, "clean_image")),
            degraded_image=cast(torch.Tensor, _required(batch, "degraded_image")),
            input_field=cast(torch.Tensor, _required(batch, "input_field")),
            provenance=cast(Mapping[str, object], _required(batch, "provenance")),
            additional_fields=additional_fields,
        )

    @property
    def batch_size(self) -> int:
        """
        返回批次场景数量
        """
        return int(self.degraded_image.shape[0])

    def __getitem__(self, key: str) -> object:
        """
        按字段名读取批次内容
        """
        return self._fields[key]

    def __iter__(self) -> Iterator[str]:
        """
        迭代批次字段名
        """
        return iter(self._fields)

    def __len__(self) -> int:
        """
        返回批次字段数量
        """
        return len(self._fields)


def _required(sample: Mapping[str, object], field_name: str) -> object:
    try:
        return sample[field_name]
    except KeyError:
        message = _FIELD_REQUIRED.format(field_name=field_name)
        raise RestorationDataContractError(message) from None


def _validate_restoration_tensors(
    *,
    clean_image: object,
    degraded_image: object,
    input_field: object,
    expected_dimensions: int,
    expected_shape_label: str,
) -> None:
    tensors = {
        "clean_image": clean_image,
        "degraded_image": degraded_image,
        "input_field": input_field,
    }
    for field_name, tensor in tensors.items():
        if not isinstance(tensor, torch.Tensor):
            message = _FIELD_TENSOR_REQUIRED.format(field_name=field_name)
            raise RestorationDataContractError(message)
        if tensor.ndim != expected_dimensions:
            message = _FIELD_SHAPE_REQUIRED.format(
                field_name=field_name,
                shape=expected_shape_label,
            )
            raise RestorationDataContractError(message)
        if tensor.numel() == 0 or not bool(torch.isfinite(tensor).all()):
            message = _FIELD_FINITE_REQUIRED.format(field_name=field_name)
            raise RestorationDataContractError(message)

    for field_name, image in (
        ("clean_image", clean_image),
        ("degraded_image", degraded_image),
    ):
        if not image.is_floating_point() or torch.is_complex(image):
            message = _IMAGE_FLOAT_REQUIRED.format(field_name=field_name)
            raise RestorationDataContractError(message)

    expected_shape = degraded_image.shape
    if clean_image.shape != expected_shape or input_field.shape != expected_shape:
        raise RestorationDataContractError(_SHARED_SHAPE_REQUIRED)
    channel_dimension = expected_dimensions - 3
    if expected_shape[channel_dimension] != 1:
        raise RestorationDataContractError(_SINGLE_CHANNEL_REQUIRED)
    if not torch.is_complex(input_field):
        raise RestorationDataContractError(_COMPLEX_FIELD_REQUIRED)
    input_intensity = input_field.abs().square().real.to(dtype=torch.float64)
    if not torch.allclose(
        input_intensity,
        degraded_image.to(dtype=torch.float64),
        atol=1e-5,
        rtol=0.0,
    ):
        raise RestorationDataContractError(_INTENSITY_MATCH_REQUIRED)


def _validate_provenance(provenance: object) -> None:
    if not isinstance(provenance, Mapping):
        raise RestorationDataContractError(_PROVENANCE_MAPPING_REQUIRED)
