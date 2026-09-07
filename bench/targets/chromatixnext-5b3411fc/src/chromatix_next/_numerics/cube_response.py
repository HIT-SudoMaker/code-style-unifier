from __future__ import annotations

import torch

_UNIT_ROUND_OFF = 2.0 ** -53


def apply_closed_nonpolarizing_cube_response(
    *,
    incident_terminal_p_s_values: torch.Tensor,
    mixing_angle: torch.Tensor,
    reflection_input_indices: tuple[int, int, int, int],
) -> torch.Tensor:
    """
    在固定 Terminal 顺序与 coating p/s 基内施加闭合无损 NBS 响应

    Args:
        incident_terminal_p_s_values: 末两轴依次为四个 incident Terminal 与 p/s
        mixing_angle: 唯一 NBS 混合角状态
        reflection_input_indices: 每个 outgoing Terminal 对应的反射入射索引

    Returns:
        按 left、top、right、bottom 顺序排列的完整复振幅响应

    """
    transmission_input_indices = torch.tensor(
        (2, 3, 0, 1),
        dtype=torch.int64,
        device=incident_terminal_p_s_values.device,
    )
    reflected_input_indices = torch.tensor(
        reflection_input_indices,
        dtype=torch.int64,
        device=incident_terminal_p_s_values.device,
    )
    transmitted = torch.index_select(
        incident_terminal_p_s_values,
        dim=-2,
        index=transmission_input_indices,
    )
    reflected = torch.index_select(
        incident_terminal_p_s_values,
        dim=-2,
        index=reflected_input_indices,
    )
    aligned_angle = mixing_angle.to(
        device=incident_terminal_p_s_values.device,
        dtype=torch.float64,
    )
    return torch.cos(aligned_angle) * transmitted + (
        1j * torch.sin(aligned_angle) * reflected
    )


def apply_closed_polarizing_cube_response(
    *,
    incident_terminal_p_s_values: torch.Tensor,
    reflection_input_indices: tuple[int, int, int, int],
) -> torch.Tensor:
    """
    在固定 Terminal 顺序与 coating p/s 基内施加理想 p 透射、s 反射响应

    Args:
        incident_terminal_p_s_values: 末两轴依次为四个 incident Terminal 与 p/s
        reflection_input_indices: 每个 outgoing Terminal 对应的反射入射索引

    Returns:
        按 left、top、right、bottom 顺序排列的完整复振幅响应

    """
    transmission_input_indices = torch.tensor(
        (2, 3, 0, 1),
        dtype=torch.int64,
        device=incident_terminal_p_s_values.device,
    )
    reflected_input_indices = torch.tensor(
        reflection_input_indices,
        dtype=torch.int64,
        device=incident_terminal_p_s_values.device,
    )
    transmitted = torch.index_select(
        incident_terminal_p_s_values,
        dim=-2,
        index=transmission_input_indices,
    )
    reflected = torch.index_select(
        incident_terminal_p_s_values,
        dim=-2,
        index=reflected_input_indices,
    )
    exact_zero = torch.zeros_like(transmitted[..., 0])
    p_transmission = torch.stack(
        (
            transmitted[..., 0],
            exact_zero,
        ),
        dim=-1,
    )
    s_reflection = torch.stack(
        (
            exact_zero,
            1j * reflected[..., 1],
        ),
        dim=-1,
    )
    return p_transmission + s_reflection


def closed_response_preserves_finite_power(
    *,
    incident_terminal_p_s_values: torch.Tensor,
    outgoing_terminal_p_s_values: torch.Tensor,
) -> torch.Tensor:
    """
    以 scale-first 功率比较检查闭合 Cube 响应的有限无损不变量

    Args:
        incident_terminal_p_s_values: 完整 incident Terminal p/s 复振幅
        outgoing_terminal_p_s_values: 对应的完整 outgoing Terminal p/s 复振幅

    Returns:
        有限输出是否在 fixed-double 预算内保持输入总模态功率

    """
    scale = incident_terminal_p_s_values.abs().amax()
    safe_scale = torch.where(
        scale == 0.0,
        torch.ones_like(scale),
        scale,
    )
    normalized_incident = incident_terminal_p_s_values / safe_scale
    normalized_outgoing = outgoing_terminal_p_s_values / safe_scale
    incident_power = normalized_incident.abs().square().sum()
    outgoing_power = normalized_outgoing.abs().square().sum()
    power_scale = torch.maximum(
        incident_power,
        torch.ones_like(incident_power),
    )
    nonzero_power_is_preserved = (
        (outgoing_power - incident_power).abs()
        <= 128.0 * _UNIT_ROUND_OFF * power_scale
    )
    exact_zero_is_preserved = torch.count_nonzero(
        outgoing_terminal_p_s_values
    ) == 0
    return torch.isfinite(outgoing_terminal_p_s_values).all() & torch.where(
        scale == 0.0,
        exact_zero_is_preserved,
        nonzero_power_is_preserved,
    )
