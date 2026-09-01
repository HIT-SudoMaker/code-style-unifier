from __future__ import annotations

from dataclasses import dataclass

import torch

from ._certified_predicates import dot_sign
from .jones_calculus import (
    _eigenstate_jones_vector,
    _eigenstate_projector_from_jones_vector,
    _retarder_matrix,
)
from .reflection import _householder_reflect


@dataclass(frozen=True, slots=True)
class _PlaneLocalJonesFrame:
    """
    承载逐光线局部 Jones 正交基与退化判定

    """

    axis_x: torch.Tensor
    axis_y: torch.Tensor
    is_interaction_degenerate: torch.Tensor
    is_projection_resolvable: torch.Tensor


def embed_collimated_polarization_in_global_frame(
    *,
    jones_components: torch.Tensor,
    launch_tangent_x: torch.Tensor,
    launch_tangent_y: torch.Tensor,
    reference: torch.Tensor,
) -> torch.Tensor:
    """
    把横向琼斯分量嵌入全局 SI frame，返回长度 3 的复单位横向偏振方向

    Jones x 分量投到 ``launch_tangent_x``、Jones y 分量投到
    ``launch_tangent_y``。两基向量单位正交，故结果垂直于
    ``launch_tangent_x × launch_tangent_y``。
    琼斯分量已归一化，结果保持复单位长度。
    ``reference`` 只用于对齐设备与精度，本函数不读取其数值

    """

    complex_dtype = torch.complex128
    jones = jones_components.to(
        device=reference.device,
        dtype=complex_dtype,
    )
    tangent_x = launch_tangent_x.to(device=reference.device, dtype=torch.float64)
    tangent_y = launch_tangent_y.to(device=reference.device, dtype=torch.float64)
    jones_x = jones[0]
    jones_y = jones[1]
    # polarization = Ex * tangent_x + Ey * tangent_y；横向 + 单位长度按构造成立
    return jones_x * tangent_x + jones_y * tangent_y


def reflect_polarization_direction(
    *,
    ray_polarization: torch.Tensor,
    unit_normal: torch.Tensor,
    is_interacted: torch.Tensor,
) -> torch.Tensor:
    """
    把对实方向使用的同一 Householder 实映射作用到复偏振方向上，非交互光线原样保留

    实 Householder 映射 ``H = I − 2 n̂ n̂ᵀ`` 是实正交矩阵，作用到复向量上保复单位范数
    与横向性，且对法线符号 ``n̂ ↔ −n̂`` 不变，与 ``_numerics/reflection.py`` 一致。
    只对 ``is_interacted`` 命中+孔径内的光线改写；未命中/遮挡/已 inactive 的光线
    精确保留入射偏振。

    """

    reflected_polarization = _householder_reflect(
        vector=ray_polarization,
        unit_normal=unit_normal,
    )
    return torch.where(
        is_interacted.unsqueeze(-1),
        reflected_polarization,
        ray_polarization,
    )


def rotate_polarization_minimal(
    *,
    incident_direction: torch.Tensor,
    transmitted_direction: torch.Tensor,
    ray_polarization: torch.Tensor,
    is_refracted: torch.Tensor,
) -> torch.Tensor:
    """
    把入射单位方向到透射单位方向的唯一最小真旋转作用到复偏振方向上

    使用未归一化叉积 ``v = d_i × d_t`` 与点积 ``c = d_i · d_t`` 的 Rodrigues 形式
    ``R = I + [v]_× + [v]_×² / (1 + c)``（``[v]_×`` 为 ``v`` 的反对称叉积矩阵）。
    当 ``d_i = d_t`` 时 ``v = 0``、``c = 1``，该式严格退化为单位矩阵，故正入射（与
    任何非折射通道）按构造恒等，无需特判。正折射率透射几何排除 ``d_t = −d_i`` 的反向
    情形（``1 + c = 0`` 不会出现在成功折射通道上）。实旋转保复单位范数与横向性。
    ``is_refracted`` 之外的通道（TIR、未命中、遮挡、已 inactive）精确保留入射偏振——
    尽管它们在 ``transmitted_direction`` 上已等于入射方向（旋转本就退化），仍显式
    ``where`` 以保证逐位精确保留。

    """

    rotation = _minimal_rotation_matrix(
        incident_direction=incident_direction,
        transmitted_direction=transmitted_direction,
    )
    rotated = torch.einsum(
        "...ij,...j->...i",
        rotation.to(dtype=ray_polarization.dtype),
        ray_polarization,
    )
    return torch.where(
        is_refracted.unsqueeze(-1),
        rotated,
        ray_polarization,
    )


def _exact_collinearity(
    first_direction: torch.Tensor,
    second_direction: torch.Tensor,
) -> torch.Tensor:
    first_x, first_y, first_z = first_direction.unbind(dim=-1)
    second_x, second_y, second_z = second_direction.unbind(dim=-1)
    xy_sign = dot_sign(
        torch.stack((first_x, first_y), dim=-1),
        torch.stack((second_y, -second_x), dim=-1),
    )
    yz_sign = dot_sign(
        torch.stack((first_y, first_z), dim=-1),
        torch.stack((second_z, -second_y), dim=-1),
    )
    zx_sign = dot_sign(
        torch.stack((first_z, first_x), dim=-1),
        torch.stack((second_x, -second_z), dim=-1),
    )
    return (xy_sign == 0) & (yz_sign == 0) & (zx_sign == 0)


def _scale_first_normalize(
    vector: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    vector_scale = vector.abs().amax(dim=-1)
    has_finite_nonzero_scale = (
        torch.isfinite(vector_scale) & (vector_scale > 0.0)
    )
    safe_vector_scale = torch.where(
        has_finite_nonzero_scale,
        vector_scale,
        torch.ones_like(vector_scale),
    )
    scaled_vector = vector / safe_vector_scale.unsqueeze(-1)
    scaled_norm = torch.linalg.norm(scaled_vector, dim=-1)
    has_finite_nonzero_norm = torch.isfinite(scaled_norm) & (scaled_norm > 0.0)
    safe_scaled_norm = torch.where(
        has_finite_nonzero_norm,
        scaled_norm,
        torch.ones_like(scaled_norm),
    )
    normalized_vector = scaled_vector / safe_scaled_norm.unsqueeze(-1)
    is_resolvable = (
        has_finite_nonzero_scale
        & has_finite_nonzero_norm
        & torch.isfinite(normalized_vector).all(dim=-1)
    )
    return normalized_vector, is_resolvable


def derive_plane_local_jones_frame(
    *,
    ray_direction: torch.Tensor,
    plane_tangent_x: torch.Tensor,
    is_interacted: torch.Tensor,
) -> _PlaneLocalJonesFrame:
    """
    从作者方向与 Plane 参考轴派生一次横向正交 Jones 帧及其适用性事实

    共线性由原始 binary64 操作数的精确二阶行列式判定。连续投影必须有至少一个分量严格
    超过按实际运算推导的 binary64 前向误差界，之后才用先缩放、后归一化的路径构造局部
    正交基底。精确共线与连续投影不可表示是两个不同事实；本函数不抛动作错误，也不发明
    交互通道的替代物理轴。

    """

    is_exactly_collinear = _exact_collinearity(
        ray_direction,
        plane_tangent_x,
    )
    is_interaction_degenerate = is_interacted & is_exactly_collinear
    direction_norm = torch.linalg.norm(ray_direction, dim=-1, keepdim=True)
    calculation_direction = ray_direction / direction_norm
    projection_products = plane_tangent_x * calculation_direction
    axial_component = projection_products.sum(dim=-1, keepdim=True)
    axial_projection = axial_component * calculation_direction
    projected_axis = plane_tangent_x - axial_projection
    floating_point = torch.finfo(ray_direction.dtype)
    unit_roundoff = floating_point.eps / 2.0
    smallest_subnormal = floating_point.tiny * floating_point.eps
    gamma_five = (5.0 * unit_roundoff) / (1.0 - 5.0 * unit_roundoff)
    dot_error_bound = (
        gamma_five * projection_products.abs().sum(dim=-1, keepdim=True)
        + 5.0 * smallest_subnormal
    )
    raw_component_error_bound = (
        calculation_direction.abs() * dot_error_bound
        + unit_roundoff * axial_projection.abs()
        + unit_roundoff * (plane_tangent_x.abs() + axial_projection.abs())
        + 3.0 * smallest_subnormal
    )
    component_error_bound = (
        (1.0 + gamma_five) * raw_component_error_bound
        + 5.0 * smallest_subnormal
    )
    has_certified_projection_component = (
        projected_axis.abs() > component_error_bound
    ).any(dim=-1)
    local_jones_axis_x, is_initial_axis_x_resolvable = _scale_first_normalize(
        projected_axis
    )
    axis_x_longitudinal = (
        local_jones_axis_x * calculation_direction
    ).sum(dim=-1, keepdim=True)
    conditioned_axis_x = local_jones_axis_x - (
        axis_x_longitudinal * calculation_direction
    )
    local_jones_axis_x, is_conditioned_axis_x_resolvable = (
        _scale_first_normalize(conditioned_axis_x)
    )
    axis_y_candidate = torch.linalg.cross(
        calculation_direction,
        local_jones_axis_x,
    )
    local_jones_axis_y, is_axis_y_resolvable = _scale_first_normalize(
        axis_y_candidate
    )
    reorthogonalized_axis_x = torch.linalg.cross(
        local_jones_axis_y,
        calculation_direction,
    )
    local_jones_axis_x, is_final_axis_x_resolvable = _scale_first_normalize(
        reorthogonalized_axis_x
    )
    is_continuously_resolvable = (
        has_certified_projection_component
        & is_initial_axis_x_resolvable
        & is_conditioned_axis_x_resolvable
        & is_axis_y_resolvable
        & is_final_axis_x_resolvable
        & torch.isfinite(local_jones_axis_x).all(dim=-1)
        & torch.isfinite(local_jones_axis_y).all(dim=-1)
    )
    fallback_axis_x = torch.zeros_like(local_jones_axis_x)
    fallback_axis_x[..., 0] = 1.0
    fallback_axis_y = torch.zeros_like(local_jones_axis_y)
    fallback_axis_y[..., 1] = 1.0
    safe_local_x = torch.where(
        is_interacted.unsqueeze(-1),
        local_jones_axis_x,
        fallback_axis_x,
    )
    safe_local_y = torch.where(
        is_interacted.unsqueeze(-1),
        local_jones_axis_y,
        fallback_axis_y,
    )
    is_projection_required = is_interacted & ~is_exactly_collinear
    is_projection_resolvable = (
        ~is_projection_required | is_continuously_resolvable
    )
    return _PlaneLocalJonesFrame(
        axis_x=safe_local_x,
        axis_y=safe_local_y,
        is_interaction_degenerate=is_interaction_degenerate,
        is_projection_resolvable=is_projection_resolvable,
    )


def retard_ray_polarization(
    *,
    ray_polarization: torch.Tensor,
    plane_local_frame: _PlaneLocalJonesFrame,
    is_interacted: torch.Tensor,
    retardance_cycles: torch.Tensor,
    retarded_eigenstate_azimuth_radians: torch.Tensor,
    retarded_eigenstate_ellipticity_radians: torch.Tensor,
) -> torch.Tensor:
    """
    把零均值 SU(2) 延迟律解析到每条光线的 Plane-local Jones 帧

    按 ADR-0010 的精确保留契约：输出 = 入射偏振 + 嵌入的琼斯增量，**不**投影再重嵌整
    入射向量。增量矩阵 ``M − I``：在严格单位琼斯矩阵（零延迟）下增量恰为零，入射张量值
    按构造逐位保留（``torch.equal``，非近似相等）。3D 复偏振投到本征正交的 (local_x,
    local_y) 二分量琼斯帧，经 ``_numerics/jones_calculus.py`` 的延迟矩阵作用，
    得到琼斯增量，再嵌回 3D 加到入射偏振上。琼斯本征态/投影算符/SU(2) 公式唯一归
    ``_numerics/jones_calculus.py``
    所有。本函数消费已经派生且验证的 Plane-local 帧，只负责 3D↔2D 投影、SU(2) 增量
    嵌回与逐光线安全掩码——既不派生几何帧，也不复制琼斯公式。延迟量、本征态方位角与
    椭率角均为标量（同一 SU(2) 律作用到所有光线的各自本地帧），与波延迟器同形契约。
    非交互光线精确保留入射偏振方向。

    """

    local_x = plane_local_frame.axis_x
    local_y = plane_local_frame.axis_y
    jones_component_x = (ray_polarization * local_x).sum(dim=-1)
    jones_component_y = (ray_polarization * local_y).sum(dim=-1)
    jones_components = torch.stack(
        (jones_component_x, jones_component_y),
        dim=-1,
    )
    retarded_eigenstate = _eigenstate_jones_vector(
        azimuth_radians=retarded_eigenstate_azimuth_radians,
        ellipticity_radians=retarded_eigenstate_ellipticity_radians,
    )
    retarded_eigenstate_projector = _eigenstate_projector_from_jones_vector(
        eigenstate=retarded_eigenstate,
    )
    retarder_matrix = _retarder_matrix(
        retardance_cycles=retardance_cycles,
        retarded_eigenstate_projector=retarded_eigenstate_projector,
    )
    polarization_identity = torch.eye(
        2,
        dtype=retarder_matrix.dtype,
        device=retarder_matrix.device,
    )
    retardance_delta_matrix = retarder_matrix - polarization_identity
    delta_jones = torch.einsum(
        "ij,...j->...i",
        retardance_delta_matrix.to(dtype=jones_components.dtype),
        jones_components,
    )
    # 把琼斯增量嵌回 3D 并加到入射偏振：单位正交实基底保单位范数与横向性（非零延迟）
    delta_jones_x = delta_jones[..., 0]
    delta_jones_y = delta_jones[..., 1]
    retarded_polarization = (
        ray_polarization
        + delta_jones_x.unsqueeze(-1) * local_x
        + delta_jones_y.unsqueeze(-1) * local_y
    )
    return torch.where(
        is_interacted.unsqueeze(-1),
        retarded_polarization,
        ray_polarization,
    )


def _minimal_rotation_matrix(
    *,
    incident_direction: torch.Tensor,
    transmitted_direction: torch.Tensor,
) -> torch.Tensor:
    incident_norm = torch.linalg.norm(incident_direction, dim=-1, keepdim=True)
    transmitted_norm = torch.linalg.norm(
        transmitted_direction,
        dim=-1,
        keepdim=True,
    )
    incident_unit = incident_direction / incident_norm
    transmitted_unit = transmitted_direction / transmitted_norm
    cos_angle = (incident_unit * transmitted_unit).sum(dim=-1)
    cross = torch.linalg.cross(incident_unit, transmitted_unit)
    one_plus_cos = 1.0 + cos_angle
    safe_one_plus_cos = torch.where(
        one_plus_cos > 0.0,
        one_plus_cos,
        torch.ones_like(one_plus_cos),
    )
    batch_shape = cross.shape[:-1]
    identity = torch.eye(
        3,
        dtype=cross.dtype,
        device=cross.device,
    ).expand(*batch_shape, 3, 3)
    rotation_cross_x = cross[..., 0]
    rotation_cross_y = cross[..., 1]
    rotation_cross_z = cross[..., 2]
    zero_component = torch.zeros_like(rotation_cross_x)
    cross_matrix_row_x = torch.stack(
        (zero_component, -rotation_cross_z, rotation_cross_y),
        dim=-1,
    )
    cross_matrix_row_y = torch.stack(
        (rotation_cross_z, zero_component, -rotation_cross_x),
        dim=-1,
    )
    cross_matrix_row_z = torch.stack(
        (-rotation_cross_y, rotation_cross_x, zero_component),
        dim=-1,
    )
    cross_product_matrix = torch.stack(
        (cross_matrix_row_x, cross_matrix_row_y, cross_matrix_row_z),
        dim=-2,
    )
    cross_product_matrix_squared = torch.einsum(
        "...ij,...jk->...ik",
        cross_product_matrix,
        cross_product_matrix,
    )
    denominator = safe_one_plus_cos.unsqueeze(-1).unsqueeze(-1)
    return (
        identity
        + cross_product_matrix
        + cross_product_matrix_squared / denominator
    )
