from __future__ import annotations

import math
import time

import torch
from torch import nn

from experiments.restoration.errors import invalid_restoration_contract


def count_trainable_parameters(model: nn.Module) -> int:
    """
    统计容量对比所需的可训练参数量
    """
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def _snapshot_training_modes(model: nn.Module) -> dict[nn.Module, bool]:
    return {module: module.training for module in model.modules()}


def _restore_training_modes(training_modes: dict[nn.Module, bool]) -> None:
    for module, training in training_modes.items():
        module.train(training)


@torch.no_grad()
def count_conv2d_macs(model: nn.Module, example_input: torch.Tensor) -> int:
    """
    统计固定输入下二维卷积乘加量
    """
    total_macs = 0
    hooks: list[torch.utils.hooks.RemovableHandle] = []

    def hook(module: nn.Module, _inputs: tuple[torch.Tensor, ...], output: torch.Tensor) -> None:
        """
        累计一次前向传播中的二维卷积乘加量
        """
        nonlocal total_macs
        if not isinstance(module, nn.Conv2d):
            return
        output_elements = output.numel()
        kernel_height, kernel_width = module.kernel_size
        in_channels = module.in_channels // module.groups
        total_macs += output_elements * in_channels * kernel_height * kernel_width

    for module in model.modules():
        if isinstance(module, nn.Conv2d):
            hooks.append(module.register_forward_hook(hook))
    training_modes = _snapshot_training_modes(model)
    model.eval()
    try:
        model(example_input)
    finally:
        for handle in hooks:
            handle.remove()
        _restore_training_modes(training_modes)
    return total_macs


def fft2_macs(height: int, width: int) -> int:
    """
    计算一次二进制基二维傅里叶变换的乘加量
    """
    for name, value in (("height", height), ("width", width)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise invalid_restoration_contract(f"{name} must be a positive integer")
        if value & (value - 1) != 0:
            raise invalid_restoration_contract(f"{name} must be a power of two")
    return (height * width // 2) * (int(math.log2(height)) + int(math.log2(width)))


@torch.no_grad()
def count_model_macs(model: nn.Module, example_input: torch.Tensor) -> int:
    """
    汇总卷积与模块自报的额外乘加量

    Measure on the digital **backend shell** with a real (B, C_in, H, W) example — NOT on a
    frontend-wrapped hybrid (whose input is a complex field) — so each reporting module's
    ``spectral_macs`` receives the shape it actually sees. A forward hook captures every
    reporting module's true input shape rather than assuming the top-level input shape.
    """
    conv_macs = count_conv2d_macs(model, example_input)
    spectral_total = 0
    hooks: list[torch.utils.hooks.RemovableHandle] = []

    def _hook(
        module: nn.Module,
        inputs: tuple[torch.Tensor, ...],
        _output: object,
    ) -> None:
        nonlocal spectral_total
        reporter = getattr(module, "spectral_macs", None)
        if callable(reporter) and inputs:
            spectral_total += int(reporter(tuple(inputs[0].shape)))

    for module in model.modules():
        if callable(getattr(module, "spectral_macs", None)):
            hooks.append(module.register_forward_hook(_hook))
    training_modes = _snapshot_training_modes(model)
    model.eval()
    try:
        model(example_input)
    finally:
        for handle in hooks:
            handle.remove()
        _restore_training_modes(training_modes)
    return conv_macs + spectral_total


@torch.no_grad()
def measure_forward_seconds(
    model: nn.Module,
    example_input: torch.Tensor,
    *,
    warmup_steps: int = 3,
    timed_steps: int = 10,
) -> float:
    """
    测量固定输入的平均前向耗时
    """
    if warmup_steps < 0:
        raise invalid_restoration_contract("warmup_steps must be nonnegative")
    if timed_steps <= 0:
        raise invalid_restoration_contract("timed_steps must be positive")
    training_modes = _snapshot_training_modes(model)
    model.eval()
    try:
        for _ in range(warmup_steps):
            model(example_input)
        if example_input.is_cuda:
            torch.cuda.synchronize(example_input.device)
        start = time.perf_counter()
        for _ in range(timed_steps):
            model(example_input)
        if example_input.is_cuda:
            torch.cuda.synchronize(example_input.device)
        elapsed = time.perf_counter() - start
    finally:
        _restore_training_modes(training_modes)
    return elapsed / timed_steps
