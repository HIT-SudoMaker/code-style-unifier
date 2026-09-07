from __future__ import annotations

from dataclasses import dataclass

import torch

import chromatix_next.errors as _errors

from .._tensors import is_value_readable
from .spectrum import Spectrum

RAY_STATUS_ACTIVE = 1

RAY_STATUS_SURFACE_MISSED = 2

RAY_STATUS_VIGNETTED = 4

RAY_STATUS_TOTAL_INTERNAL_REFLECTION = 8

RAY_STATUS_KNOWN_MASK = (
    RAY_STATUS_ACTIVE
    | RAY_STATUS_SURFACE_MISSED
    | RAY_STATUS_VIGNETTED
    | RAY_STATUS_TOTAL_INTERNAL_REFLECTION
)

RAY_STATUS_FINISHED_MASK = (
    RAY_STATUS_SURFACE_MISSED
    | RAY_STATUS_VIGNETTED
    | RAY_STATUS_TOTAL_INTERNAL_REFLECTION
)

_RAY_REAL_DTYPE = torch.float64

_RAY_POLARIZATION_DTYPE = torch.complex128

_RAY_UNIT_ROUND_OFF: float = 2.0 ** -53

_RAY_GAMMA_5: float = (
    5.0 * _RAY_UNIT_ROUND_OFF / (1.0 - 5.0 * _RAY_UNIT_ROUND_OFF)
)

_RAY_GAMMA_11: float = (
    11.0 * _RAY_UNIT_ROUND_OFF / (1.0 - 11.0 * _RAY_UNIT_ROUND_OFF)
)

_DIRECTION_SQUARED_NORM_BUDGET: float = 16.0 * _RAY_GAMMA_5

_POLARIZATION_NORM_SQUARED_BUDGET: float = 16.0 * _RAY_GAMMA_11

_TRANSVERSALITY_SCALE_FACTOR: float = 16.0 * _RAY_GAMMA_5



def _status_contains_unknown_bits(status: torch.Tensor) -> bool | None:
    if status.is_meta:
        return None
    masked = status | RAY_STATUS_KNOWN_MASK
    all_subset = torch.equal(
        masked,
        torch.full_like(masked, RAY_STATUS_KNOWN_MASK),
    )
    return not all_subset


def _status_contains_zero_state(status: torch.Tensor) -> bool | None:
    if status.is_meta:
        return None
    return bool((status == 0).any())


def _status_contains_active_and_finished(
    status: torch.Tensor,
) -> bool | None:
    if status.is_meta:
        return None
    active_set = (status & RAY_STATUS_ACTIVE) != 0
    finished_set = (status & RAY_STATUS_FINISHED_MASK) != 0
    return bool((active_set & finished_set).any())


def _status_contains_multiple_finished(
    status: torch.Tensor,
) -> bool | None:
    if status.is_meta:
        return None
    finished = status & RAY_STATUS_FINISHED_MASK
    missed = (finished & RAY_STATUS_SURFACE_MISSED) != 0
    vignetted = (finished & RAY_STATUS_VIGNETTED) != 0
    tir = (finished & RAY_STATUS_TOTAL_INTERNAL_REFLECTION) != 0
    finished_bit_count = (
        missed.to(torch.uint8)
        + vignetted.to(torch.uint8)
        + tir.to(torch.uint8)
    )
    return bool((finished_bit_count >= 2).any())


def _require_finite_real_tensor(
    value: torch.Tensor,
    *,
    field_name: str,
    error_identity: str,
) -> None:
    is_finite = torch.isfinite(value).all()
    if is_value_readable(is_finite) and not bool(is_finite):
        message = (
            f"光线束的 {field_name} 必须处处有限，无穷或非数说明上游物理已经发散，"
            f"收到的形状是 {tuple(value.shape)}、dtype 是 {value.dtype}"
        )
        raise _errors.OpticalValueError(error_identity, message)


def _require_finite_complex_tensor(
    value: torch.Tensor,
    *,
    field_name: str,
    error_identity: str,
) -> None:
    is_finite = torch.isfinite(value).all()
    if is_value_readable(is_finite) and not bool(is_finite):
        message = (
            f"光线束的 {field_name} 必须处处有限（实部与虚部均有限），"
            "非数说明上游物理已经发散，"
            f"收到的形状是 {tuple(value.shape)}、dtype 是 {value.dtype}"
        )
        raise _errors.OpticalValueError(error_identity, message)


@dataclass(frozen=True, slots=True, eq=False)
class RayBundle:
    """
    不可变几何光线束物理值

    Args:
        position: 光线位置或点源位置的笛卡尔坐标
        direction: 光线传播方向的单位向量
        polarization_vector: 与传播方向横向正交的复偏振向量
        power: 每条光线携带的非负功率
        refractive_index: 每条光线当前位置的折射率
        optical_path: 每条光线已经累积的光程
        status: 每条光线的活动、渐晕或终止状态
        spectrum: 光谱采样、权重与波长语义

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    position: torch.Tensor
    direction: torch.Tensor
    polarization_vector: torch.Tensor
    power: torch.Tensor
    refractive_index: torch.Tensor
    optical_path: torch.Tensor
    status: torch.Tensor
    spectrum: Spectrum

    def __post_init__(self) -> None:
        self._validate_field_types()
        self._validate_status_contract()
        self._validate_real_state_dtypes()
        self._validate_polarization_dtype()
        self._validate_optical_path_dtype()
        self._validate_axis_layout()
        self._validate_shared_placement()
        self._validate_spectrum_metadata()
        self._validate_finite_real_state()
        self._validate_finite_polarization()
        self._validate_unit_direction()
        self._validate_unit_polarization()
        self._validate_polarization_transversality()
        self._validate_nonnegative_power()
        self._validate_positive_refractive_index()

    @property
    def batch_shape(self) -> tuple[int, ...]:
        """
        返回光谱轴之前的批量维形状

        Returns:
            光谱轴之前的批量维长度元组

        """
        return tuple(self.position.shape[:-3])

    @property
    def spectral_count(self) -> int:
        """
        返回光谱分量数目

        Returns:
            返回 RayBundle 的谱道数量

        """
        return int(self.position.shape[-3])

    @property
    def ray_count(self) -> int:
        """
        返回每光谱分量的光线数目

        Returns:
            返回 RayBundle 的射线数量

        """
        return int(self.position.shape[-2])

    @property
    def axis_meaning(self) -> tuple[str, ...]:
        """
        返回批量、光谱、光线与笛卡尔分量轴的自然语言含义

        Returns:
            批量、光谱、光线、笛卡尔分量轴含义的字符串元组

        """
        batch_axes = tuple(
            f"batch_{index}"
            for index in range(len(self.batch_shape))
        )
        return batch_axes + ("spectrum", "ray", "xyz")

    def _validate_field_types(self) -> None:
        tensor_fields = (
            ("position", self.position),
            ("direction", self.direction),
            ("polarization_vector", self.polarization_vector),
            ("power", self.power),
            ("refractive_index", self.refractive_index),
            ("optical_path", self.optical_path),
            ("status", self.status),
        )
        for field_name, value in tensor_fields:
            if not isinstance(value, torch.Tensor):
                message = (
                    f"光线束的 {field_name} 必须以张量承载逐 ray 物理量，"
                    f"收到的是 {type(value).__name__}"
                )
                raise _errors.OpticalTypeError(
                    f"ray_bundle_{field_name}_invalid",
                    message,
                )
        if not isinstance(self.spectrum, Spectrum):
            message = (
                "光线束的光谱要由光谱物理值给出，"
                f"收到的是 {type(self.spectrum).__name__}"
            )
            raise _errors.OpticalTypeError(
                "ray_bundle_spectrum_invalid",
                message,
            )

    def _validate_status_contract(self) -> None:
        # status 必须是非浮点整型张量；本基座固定 uint8 bitmask 表达
        if self.status.dtype is not torch.uint8:
            message = (
                "光线束的状态必须以非浮点 bitmask 表达，"
                "唯一支持的 dtype 是 uint8，"
                f"收到的是 {self.status.dtype}"
            )
            raise _errors.OpticalTypeError(
                "ray_bundle_status_dtype_invalid",
                message,
            )
        if _status_contains_unknown_bits(self.status):
            message = (
                "光线束的状态每条 ray 只能取 active、surface missed、vignetted "
                "与 total internal reflection 中的一个，出现未知位说明上游使用了"
                f"未定义的终止路径，收到的 dtype 是 {self.status.dtype}、形状是 "
                f"{tuple(self.status.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_status_bits_unknown",
                message,
            )
        if _status_contains_zero_state(self.status):
            message = (
                "每条光线必须恰好处于一个已知状态，零状态说明上游未给该 ray 指派"
                f"物理终止，收到的 dtype 是 {self.status.dtype}、形状是 "
                f"{tuple(self.status.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_status_zero",
                message,
            )
        if _status_contains_active_and_finished(self.status):
            message = (
                "光线束的状态不能让 active 与 surface missed、vignetted 或 total "
                "internal reflection 同时置位：一条 ray 不能既可传播又是 Finished Ray，"
                f"收到的 dtype 是 {self.status.dtype}、形状是 "
                f"{tuple(self.status.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_status_active_and_finished",
                message,
            )
        if _status_contains_multiple_finished(self.status):
            message = (
                "光线束的终止态互斥：surface missed、vignetted 与 total internal "
                "reflection 不能同时置位，一条 ray 只能有一个终止原因，"
                f"收到的 dtype 是 {self.status.dtype}、形状是 "
                f"{tuple(self.status.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_status_multiple_finished",
                message,
            )

    def _validate_real_state_dtypes(self) -> None:
        real_fields = (
            ("position", self.position),
            ("direction", self.direction),
            ("power", self.power),
            ("refractive_index", self.refractive_index),
        )
        for field_name, value in real_fields:
            if (
                torch.is_complex(value)
                or not value.is_floating_point()
                or value.dtype is not _RAY_REAL_DTYPE
            ):
                message = (
                    f"光线束的 {field_name} 必须以 float64 实精度承载，"
                    "单精度实光线状态不再被支持，"
                    f"收到的是 {value.dtype}"
                )
                raise _errors.OpticalTypeError(
                    f"ray_bundle_{field_name}_dtype_invalid",
                    message,
                )

    def _validate_polarization_dtype(self) -> None:
        value = self.polarization_vector
        if value.dtype is not _RAY_POLARIZATION_DTYPE:
            message = (
                "光线束的偏振方向必须以 complex128 复精度承载，"
                "实 dtype、complex64 或其它复 dtype 都不被支持，"
                f"收到的是 {value.dtype}"
            )
            raise _errors.OpticalTypeError(
                "ray_bundle_polarization_vector_dtype_invalid",
                message,
            )

    def _validate_optical_path_dtype(self) -> None:
        if self.optical_path.dtype is not torch.float64:
            message = (
                "光线束的逐 ray 光程必须以设备本地 float64 累加，"
                "避免在长光路上的小调整被实精度吃掉，"
                f"收到的是 {self.optical_path.dtype}"
            )
            raise _errors.OpticalTypeError(
                "ray_bundle_optical_path_dtype_invalid",
                message,
            )

    def _validate_axis_layout(self) -> None:
        if self.position.dim() < 3:
            message = (
                "光线束的位置至少需要 3 维 (批量..., 光谱, 光线, xyz)，"
                f"收到的秩是 {self.position.dim()}、"
                f"形状是 {tuple(self.position.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_position_axis_invalid",
                message,
            )
        if self.direction.dim() < 3:
            message = (
                "光线束的方向至少需要 3 维 (批量..., 光谱, 光线, xyz)，"
                f"收到的秩是 {self.direction.dim()}、"
                f"形状是 {tuple(self.direction.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_direction_axis_invalid",
                message,
            )
        if self.polarization_vector.dim() < 3:
            message = (
                "光线束的偏振方向至少需要 3 维 (批量..., 光谱, 光线, xyz)，"
                f"收到的秩是 {self.polarization_vector.dim()}、"
                f"形状是 {tuple(self.polarization_vector.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_polarization_vector_axis_invalid",
                message,
            )
        if self.position.shape[-1] != 3:
            message = (
                "光线束的位置尾维必须是长度为 3 的笛卡尔分量 (x, y, z)，"
                f"收到的形状是 {tuple(self.position.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_position_axis_invalid",
                message,
            )
        if self.direction.shape[-1] != 3:
            message = (
                "光线束的方向尾维必须是长度为 3 的笛卡尔分量 (x, y, z)，"
                f"收到的形状是 {tuple(self.direction.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_direction_axis_invalid",
                message,
            )
        if self.polarization_vector.shape[-1] != 3:
            message = (
                "光线束的偏振方向尾维必须是长度为 3 的笛卡尔分量 (x, y, z)，"
                f"收到的形状是 {tuple(self.polarization_vector.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_polarization_vector_axis_invalid",
                message,
            )
        position_prefix = tuple(self.position.shape[:-1])
        direction_prefix = tuple(self.direction.shape[:-1])
        polarization_prefix = tuple(self.polarization_vector.shape[:-1])
        scalar_prefix = tuple(self.power.shape)
        if (
            position_prefix != direction_prefix
            or position_prefix != polarization_prefix
            or position_prefix != scalar_prefix
            or position_prefix != tuple(self.refractive_index.shape)
            or position_prefix != tuple(self.optical_path.shape)
            or position_prefix != tuple(self.status.shape)
        ):
            message = (
                "位置/方向/偏振的前缀 (batch..., spectrum, ray) 须与"
                "功率/折射率/光程/状态的 (batch..., spectrum, ray) 完全一致，"
                f"位置前缀是 {position_prefix}、方向前缀是 {direction_prefix}、"
                f"偏振前缀是 {polarization_prefix}、"
                f"功率形状是 {tuple(self.power.shape)}、"
                f"折射率形状是 {tuple(self.refractive_index.shape)}、"
                f"光程形状是 {tuple(self.optical_path.shape)}、"
                f"状态形状是 {tuple(self.status.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_axes_mismatched",
                message,
            )

    def _validate_shared_placement(self) -> None:
        tensors = (
            self.position,
            self.direction,
            self.polarization_vector,
            self.power,
            self.refractive_index,
            self.optical_path,
            self.status,
        )
        first_device = tensors[0].device
        for value in tensors[1:]:
            if value.device != first_device:
                message = (
                    "同一光线束的位置、方向、偏振、功率、折射率、光程与状态必须位于"
                    "同一设备，"
                    f"位置在 {first_device}，却遇到了位于 {value.device} 的张量"
                )
                raise _errors.OpticalValueError(
                    "ray_bundle_placement_device_mismatched",
                    message,
                )
        real_dtypes = {
            self.position.dtype,
            self.direction.dtype,
            self.power.dtype,
            self.refractive_index.dtype,
        }
        if len(real_dtypes) != 1:
            message = (
                "位置、方向、功率与折射率必须共享同一 float64 实 dtype，"
                "收到的实 dtype 集合是 "
                f"{sorted(dtype.__str__() for dtype in real_dtypes)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_real_precision_mismatched",
                message,
            )

    def _validate_spectrum_metadata(self) -> None:
        if self.position.shape[-3] != self.spectrum.count:
            message = (
                f"光谱有 {self.spectrum.count} 个分量，位置轴对应维度却是 "
                f"{self.position.shape[-3]}；每个波长各占一层"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_spectrum_axis_mismatch",
                message,
            )

    def _validate_finite_real_state(self) -> None:
        _require_finite_real_tensor(
            self.position,
            field_name="位置",
            error_identity="ray_bundle_position_nonfinite",
        )
        _require_finite_real_tensor(
            self.direction,
            field_name="方向",
            error_identity="ray_bundle_direction_nonfinite",
        )
        _require_finite_real_tensor(
            self.power,
            field_name="功率",
            error_identity="ray_bundle_power_nonfinite",
        )
        _require_finite_real_tensor(
            self.refractive_index,
            field_name="折射率",
            error_identity="ray_bundle_refractive_index_nonfinite",
        )
        _require_finite_real_tensor(
            self.optical_path,
            field_name="光程",
            error_identity="ray_bundle_optical_path_nonfinite",
        )

    def _validate_finite_polarization(self) -> None:
        _require_finite_complex_tensor(
            self.polarization_vector,
            field_name="偏振方向",
            error_identity="ray_bundle_polarization_vector_nonfinite",
        )

    def _validate_unit_direction(self) -> None:
        squared_norm = (self.direction * self.direction).sum(dim=-1)
        residual = (squared_norm - 1.0).abs()
        is_unit_all = (residual <= _DIRECTION_SQUARED_NORM_BUDGET).all()
        if is_value_readable(is_unit_all) and not bool(is_unit_all):
            message = (
                "光线束的方向必须逐条归一化，构造不会静默修复非单位方向，"
                "请在源边界处显式归一化，"
                f"收到的方向形状是 {tuple(self.direction.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_direction_not_unit",
                message,
            )

    def _validate_unit_polarization(self) -> None:
        norms_squared = (self.polarization_vector.real**2).sum(dim=-1) + (
            self.polarization_vector.imag**2
        ).sum(dim=-1)
        residual = (norms_squared - 1.0).abs()
        is_unit_all = (
            residual <= _POLARIZATION_NORM_SQUARED_BUDGET
        ).all()
        if is_value_readable(is_unit_all) and not bool(is_unit_all):
            message = (
                "光线束的偏振方向必须逐条复单位归一化，构造不会静默修复非单位偏振，"
                "请在源边界处显式归一化琼斯分量，"
                f"收到的偏振形状是 {tuple(self.polarization_vector.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_polarization_vector_not_unit",
                message,
            )

    def _validate_polarization_transversality(self) -> None:
        projection = (self.polarization_vector * self.direction).sum(dim=-1)
        polarization_norm = torch.linalg.norm(self.polarization_vector, dim=-1)
        direction_norm = torch.linalg.norm(self.direction, dim=-1)
        transversality_budget = (
            _TRANSVERSALITY_SCALE_FACTOR
            * polarization_norm
            * direction_norm
        )
        real_in_budget = projection.real.abs() <= transversality_budget
        imag_in_budget = projection.imag.abs() <= transversality_budget
        is_transverse_all = (real_in_budget & imag_in_budget).all()
        if is_value_readable(is_transverse_all) and not bool(
            is_transverse_all
        ):
            message = (
                "光线束的偏振方向必须横截于实单位 ray 方向（复投影 p·d̂ 的实部与虚部"
                "均须为 0），纵向偏振无物理意义，"
                f"收到的偏振形状是 {tuple(self.polarization_vector.shape)}、"
                f"方向形状是 {tuple(self.direction.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_polarization_vector_longitudinal",
                message,
            )

    def _validate_nonnegative_power(self) -> None:
        is_nonnegative = self.power >= 0
        is_nonnegative_all = is_nonnegative.all()
        if is_value_readable(is_nonnegative_all) and not bool(
            is_nonnegative_all
        ):
            message = (
                "光线束的功率必须非负，负功率意味着上游已偏离能量守恒，"
                f"收到的功率形状是 {tuple(self.power.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_power_negative",
                message,
            )

    def _validate_positive_refractive_index(self) -> None:
        is_positive = self.refractive_index > 0
        is_positive_all = is_positive.all()
        if is_value_readable(is_positive_all) and not bool(
            is_positive_all
        ):
            message = (
                "光线束的逐 ray 折射率必须处处为正实数，"
                "零或负折射率说明上游已偏离物理介质契约，"
                f"收到的折射率形状是 {tuple(self.refractive_index.shape)}"
            )
            raise _errors.OpticalValueError(
                "ray_bundle_refractive_index_nonpositive",
                message,
            )


__all__ = ["RayBundle"]
