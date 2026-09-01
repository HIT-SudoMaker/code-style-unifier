from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import math
from typing import Literal

import torch
from torch import nn

from experiments.restoration.errors import invalid_restoration_contract

ConnectionMode = Literal[
    "serial",
    "degraded_image",
    "optical_residual_gate",
    "dual_channel",
    "dual_channel_optical_zeroed",
]

_CONNECTION_MODES: tuple[str, ...] = (
    "serial",
    "degraded_image",
    "optical_residual_gate",
    "dual_channel",
    "dual_channel_optical_zeroed",
)


@dataclass(frozen=True, slots=True)
class ConnectionConfig:
    """
    描述光学前端到数字后端的图像连接
    """

    mode: ConnectionMode = "serial"
    optical_residual_gate_logit: float = 0.0

    @classmethod
    def with_optical_residual_gate(
        cls,
        *,
        initial_gate: float = 0.99,
    ) -> ConnectionConfig:
        """
        构造从指定有界初值开始的光学残差门连接
        """
        initial_gate = float(initial_gate)
        if not math.isfinite(initial_gate) or not 0.0 < initial_gate < 1.0:
            raise invalid_restoration_contract(
                "initial_gate must be finite and strictly between zero and one"
            )
        initial_logit = math.log(initial_gate / (1.0 - initial_gate))
        return cls(
            mode="optical_residual_gate",
            optical_residual_gate_logit=initial_logit,
        )

    def __post_init__(self) -> None:
        """
        归一化标量并校验连接配置
        """
        object.__setattr__(self, "mode", str(self.mode))
        object.__setattr__(
            self,
            "optical_residual_gate_logit",
            float(self.optical_residual_gate_logit),
        )
        self.validate()

    def validate(self) -> None:
        """
        连接方式与标量门约束
        """
        if self.mode not in _CONNECTION_MODES:
            allowed = ", ".join(_CONNECTION_MODES)
            raise invalid_restoration_contract(
                f"connection mode must be one of: {allowed}"
            )
        if not math.isfinite(self.optical_residual_gate_logit):
            raise invalid_restoration_contract(
                "optical_residual_gate_logit must be finite"
            )

    @property
    def initial_optical_residual_gate(self) -> float | None:
        """
        返回光学残差门的语义初值
        """
        if self.mode != "optical_residual_gate":
            return None
        logit = self.optical_residual_gate_logit
        if logit >= 0.0:
            gate = 1.0 / (1.0 + math.exp(-logit))
        else:
            exp_logit = math.exp(logit)
            gate = exp_logit / (1.0 + exp_logit)
        return min(
            max(gate, math.nextafter(0.0, 1.0)),
            math.nextafter(1.0, 0.0),
        )

    def _config_hash_payload(self) -> dict[str, object]:
        if self.mode == "optical_residual_gate":
            return {
                "mode": self.mode,
                "optical_residual_gate_logit": self.optical_residual_gate_logit,
            }
        return {
            "mode": self.mode,
            "scalar_gate_initial_logit": self.optical_residual_gate_logit,
        }


class SerialOpticalRestorationConnection(nn.Module):
    """
    将光学复原图像直接传给数字后端
    """

    def forward(
        self,
        degraded_image: torch.Tensor,
        optical_restoration_image: torch.Tensor,
    ) -> torch.Tensor:
        """
        返回光学前端图像并忽略退化图像
        """
        del degraded_image
        return optical_restoration_image

    def trainable_parameter_names(self) -> list[str]:
        """
        返回可训练连接组件名称
        """
        return []


class DegradedImageConnection(nn.Module):
    """
    将退化图像直接传给数字后端
    """

    def forward(
        self,
        degraded_image: torch.Tensor,
        optical_restoration_image: torch.Tensor,
    ) -> torch.Tensor:
        """
        返回退化图像并忽略光学前端图像
        """
        del optical_restoration_image
        return degraded_image

    def trainable_parameter_names(self) -> list[str]:
        """
        返回可训练连接组件名称
        """
        return []


class OpticalResidualGateConnection(nn.Module):
    """
    向退化图像加入有界标量光学残差
    """

    def __init__(self, config: ConnectionConfig) -> None:
        """
        标量残差门配置
        """
        super().__init__()
        self.optical_residual_gate_logit = nn.Parameter(
            torch.tensor(
                float(config.optical_residual_gate_logit),
                dtype=torch.float32,
            )
        )

    @property
    def optical_residual_gate(self) -> torch.Tensor:
        """
        返回位于零和一之间的光学残差门值
        """
        return torch.sigmoid(self.optical_residual_gate_logit)

    def forward(
        self,
        degraded_image: torch.Tensor,
        optical_restoration_image: torch.Tensor,
    ) -> torch.Tensor:
        """
        返回退化图像与有界光学残差之和
        """
        optical_restoration_residual = optical_restoration_image - degraded_image
        return degraded_image + self.optical_residual_gate * optical_restoration_residual

    @contextmanager
    def override_optical_residual_gate(self, gate: float) -> Iterator[None]:
        """
        临时固定光学残差门并在干预结束后恢复学习值
        """
        gate = float(gate)
        if not math.isfinite(gate) or not 0.0 <= gate <= 1.0:
            raise invalid_restoration_contract(
                "optical_residual_gate override must be between zero and one"
            )
        if gate == 0.0:
            logit = float("-inf")
        elif gate == 1.0:
            logit = float("inf")
        else:
            logit = math.log(gate / (1.0 - gate))
        learned_logit = self.optical_residual_gate_logit.detach().clone()
        try:
            with torch.no_grad():
                self.optical_residual_gate_logit.fill_(logit)
            yield
        finally:
            with torch.no_grad():
                self.optical_residual_gate_logit.copy_(learned_logit)

    def trainable_parameter_names(self) -> list[str]:
        """
        返回可训练连接组件名称
        """
        return ["connection"]


class DualChannelConnection(nn.Module):
    """
    将退化图像、光学图像及其残差组成三通道数据
    """

    def forward(
        self,
        degraded_image: torch.Tensor,
        optical_restoration_image: torch.Tensor,
    ) -> torch.Tensor:
        """
        构造显式三通道连接张量
        """
        residual = optical_restoration_image - degraded_image
        return torch.cat([degraded_image, optical_restoration_image, residual], dim=1)

    def trainable_parameter_names(self) -> list[str]:
        """
        返回空的可训练连接参数列表
        """
        return []


class DualChannelOpticalZeroedConnection(nn.Module):
    """
    表示将光学通道置零的归因消融连接
    """

    def forward(
        self,
        degraded_image: torch.Tensor,
        optical_restoration_image: torch.Tensor,
    ) -> torch.Tensor:
        """
        构造光学信息置零的三通道张量
        """
        del optical_restoration_image
        zeros = torch.zeros_like(degraded_image)
        return torch.cat([degraded_image, zeros, zeros], dim=1)

    def trainable_parameter_names(self) -> list[str]:
        """
        返回空的可训练连接参数列表
        """
        return []


def build_connection(config: ConnectionConfig) -> nn.Module:
    """
    构建配置指定的连接模块
    """
    config.validate()
    if config.mode == "serial":
        return SerialOpticalRestorationConnection()
    if config.mode == "degraded_image":
        return DegradedImageConnection()
    if config.mode == "optical_residual_gate":
        return OpticalResidualGateConnection(config)
    if config.mode == "dual_channel":
        return DualChannelConnection()
    if config.mode == "dual_channel_optical_zeroed":
        return DualChannelOpticalZeroedConnection()
    raise invalid_restoration_contract(
        f"unsupported connection mode: {config.mode}"
    )
