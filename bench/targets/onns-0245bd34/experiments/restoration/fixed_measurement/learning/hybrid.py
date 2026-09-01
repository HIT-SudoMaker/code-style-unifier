from __future__ import annotations

import torch
from torch import nn

from experiments.restoration.fixed_measurement.learning.connection import ConnectionConfig, build_connection
from experiments.restoration.fixed_measurement.optics.frontend import RestorationFrontend


def _default_connection() -> nn.Module:
    return build_connection(ConnectionConfig())


def _set_connection_trainable(connection: nn.Module, is_trainable: bool) -> None:
    for parameter in connection.parameters():
        parameter.requires_grad_(is_trainable)


def _trainable_connection_parameter_names(connection: nn.Module) -> list[str]:
    if not any(parameter.requires_grad for parameter in connection.parameters()):
        return []
    name_getter = getattr(connection, "trainable_parameter_names", None)
    if callable(name_getter):
        return list(name_getter())
    return ["connection"]


def _degraded_image_from_field(input_field: torch.Tensor) -> torch.Tensor:
    return input_field.abs().square().real.to(dtype=torch.float32)


class FrozenFrontendBackend(nn.Module):
    """
    鍐荤粨鍏夊鍓嶇涓庡彲璁粌鏁板瓧鍚庣
    """

    def __init__(
        self,
        frontend: RestorationFrontend,
        backend: nn.Module,
        *,
        connection: nn.Module | None = None,
        is_connection_trainable: bool = False,
    ) -> None:
        """
        鍐荤粨鍓嶇鍙傛暟骞舵寕杞藉悗绔?        """
        super().__init__()
        self.frontend = frontend
        self.connection = connection if connection is not None else _default_connection()
        self.backend = backend
        for parameter in self.frontend.parameters():
            parameter.requires_grad_(False)
        _set_connection_trainable(self.connection, is_connection_trainable)

    @property
    def bench_config(self) -> object:
        """
        杩斿洖鍓嶇鍏夊鍑犱綍
        """
        return self.frontend.bench_config

    def _effective_phase_mask(self) -> torch.Tensor:
        return self.frontend._effective_phase_mask()

    def phase_zero_baselines(self, input_field: torch.Tensor) -> dict[str, torch.Tensor]:
        """
        杩斿洖鍓嶇闆剁浉浣嶅熀绾?        """
        return self.frontend.phase_zero_baselines(input_field)

    def trainable_parameter_names(self) -> list[str]:
        """
        杩斿洖鍙缁冪粍浠跺悕绉?        """
        names = _trainable_connection_parameter_names(self.connection)
        if any(parameter.requires_grad for parameter in self.backend.parameters()):
            names.append("backend")
        return names

    def forward(self, input_field: torch.Tensor) -> torch.Tensor:
        """
        瑙ｇ爜鍐荤粨鍓嶇鐨勫厜瀛﹁緭鍑?        """
        with torch.no_grad():
            optical_image = self.frontend(input_field)
        connected_image = self.connection(
            _degraded_image_from_field(input_field),
            optical_image.to(dtype=torch.float32),
        )
        return self.backend(connected_image.to(dtype=torch.float32))


class JointFrontendBackend(nn.Module):
    """
    鑱斿悎璁粌鍏夊鍓嶇涓庢暟瀛楀悗绔?    """

    def __init__(
        self,
        frontend: RestorationFrontend,
        backend: nn.Module,
        *,
        connection: nn.Module | None = None,
        is_connection_trainable: bool = False,
    ) -> None:
        """
        鎸傝浇鍙缁冨墠绔笌鍚庣
        """
        super().__init__()
        self.frontend = frontend
        self.connection = connection if connection is not None else _default_connection()
        self.backend = backend
        _set_connection_trainable(self.connection, is_connection_trainable)

    @property
    def bench_config(self) -> object:
        """
        杩斿洖鍓嶇鍏夊鍑犱綍
        """
        return self.frontend.bench_config

    def _effective_phase_mask(self) -> torch.Tensor:
        return self.frontend._effective_phase_mask()

    def phase_zero_baselines(self, input_field: torch.Tensor) -> dict[str, torch.Tensor]:
        """
        杩斿洖鍓嶇闆剁浉浣嶅熀绾?        """
        return self.frontend.phase_zero_baselines(input_field)

    def trainable_parameter_names(self) -> list[str]:
        """
        杩斿洖鍙缁冪粍浠跺悕绉?        """
        names: list[str] = []
        if self.frontend.phase_mask_fourier.requires_grad:
            names.append("phase_mask_fourier")
        if self.frontend.phase_offset_reference.requires_grad:
            names.append("phase_offset_reference")
        names.extend(_trainable_connection_parameter_names(self.connection))
        if any(parameter.requires_grad for parameter in self.backend.parameters()):
            names.append("backend")
        return names

    def forward(self, input_field: torch.Tensor) -> torch.Tensor:
        """
        瑙ｇ爜鍙缁冨墠绔殑鍏夊杈撳嚭
        """
        optical_image = self.frontend(input_field)
        connected_image = self.connection(
            _degraded_image_from_field(input_field),
            optical_image.to(dtype=torch.float32),
        )
        return self.backend(connected_image.to(dtype=torch.float32))
