from __future__ import annotations

import math

import torch
from torch import nn

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.optical_bench import (
    OpticalBenchConfig,
    propagate_interferometric_bench,
)


_SUPPORTED_PHASE_PARAMETERIZATIONS = {"direct", "sigmoid"}
_SUPPORTED_PHASE_INITIALIZATIONS = {"zeros", "uniform", "normal"}


def _real_dtype_for(dtype: torch.dtype) -> torch.dtype:
    if dtype == torch.complex128:
        return torch.float64
    return torch.float32


class RestorationFrontend(nn.Module):
    """
    鐩稿共鍌呴噷鍙堕潰鍏夊鎭㈠鍓嶇
    """

    def __init__(
        self,
        bench_config: OpticalBenchConfig,
        phase_parameterization: str = "direct",
        phase_initialization: str = "zeros",
        is_phase_offset_reference_trainable: bool = False,
    ) -> None:
        """
        鍙缁冨厜瀛︾浉浣嶅弬鏁?        """
        super().__init__()
        bench_config.validate()
        if phase_parameterization not in _SUPPORTED_PHASE_PARAMETERIZATIONS:
            raise invalid_restoration_contract(
                "phase_parameterization must be one of: direct, sigmoid"
            )
        if phase_initialization not in _SUPPORTED_PHASE_INITIALIZATIONS:
            raise invalid_restoration_contract(
                "phase_initialization must be one of: zeros, uniform, normal"
            )

        self.bench_config = bench_config
        self.phase_parameterization = phase_parameterization
        self.phase_initialization = phase_initialization
        self.phase_mask_fourier = nn.Parameter(self._initialize_phase_mask())
        self.phase_offset_reference = nn.Parameter(
            torch.tensor(
                float(bench_config.phase_offset_reference),
                dtype=torch.float32,
            ),
            requires_grad=is_phase_offset_reference_trainable,
        )

    def _initialize_phase_mask(self) -> torch.Tensor:
        shape = (
            self.bench_config.phase_mask_resolution,
            self.bench_config.phase_mask_resolution,
        )
        if self.phase_initialization == "zeros":
            return torch.zeros(shape, dtype=torch.float32)
        if self.phase_initialization == "uniform":
            return torch.rand(shape, dtype=torch.float32)
        return torch.randn(shape, dtype=torch.float32) * 0.5

    def _effective_phase_mask(self) -> torch.Tensor:
        if self.phase_parameterization == "direct":
            phase = self.phase_mask_fourier * (2.0 * math.pi)
        else:
            phase = torch.sigmoid(self.phase_mask_fourier) * (2.0 * math.pi)
        return torch.remainder(phase, 2.0 * math.pi)

    def _phase_on_fourier_grid(
        self,
        output_resolution: tuple[int, int],
    ) -> torch.Tensor:
        phase = self._effective_phase_mask()
        if tuple(phase.shape) != tuple(output_resolution):
            raise invalid_restoration_contract(
                "phase_mask_fourier must match the Fourier spectrum resolution"
            )
        return phase

    def _reference_phase_offset(self, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
        return self.phase_offset_reference.to(device=device, dtype=_real_dtype_for(dtype))

    def phase_zero_baselines(self, input_field: torch.Tensor) -> dict[str, torch.Tensor]:
        """
        杩斿洖闆剁浉浣嶅厜瀛﹀熀绾垮浘鍍?        """
        self._validate_input_field(input_field)
        fields = propagate_interferometric_bench(
            input_field,
            torch.zeros(
                self.bench_config.input_array_resolution,
                device=input_field.device,
                dtype=_real_dtype_for(input_field.dtype),
            ),
            self.bench_config,
            reference_phase_offset_radians=self._reference_phase_offset(
                input_field.device,
                input_field.dtype,
            ),
        )
        reference_field = fields.reference
        process_phase_zero_field = fields.processing
        full_phase_zero_field = fields.combined

        image_input_identity = input_field.abs().square().real
        image_reference_arm_only = reference_field.abs().square().real
        image_process_arm_phase_zero = process_phase_zero_field.abs().square().real
        image_full_frontend_phase_zero = full_phase_zero_field.abs().square().real
        image_interference_term = 2.0 * torch.real(
            reference_field * torch.conj(process_phase_zero_field)
        )

        return {
            "image_input_identity": image_input_identity,
            "image_reference_arm_only": image_reference_arm_only,
            "image_process_arm_phase_zero": image_process_arm_phase_zero,
            "image_full_frontend_phase_zero": image_full_frontend_phase_zero,
            "image_interference_term": image_interference_term,
            "e_field_reference": reference_field,
            "e_field_process_phase_zero": process_phase_zero_field,
            "e_field_full_phase_zero": full_phase_zero_field,
        }

    def forward_optical_fields(
        self,
        input_field: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        杩斿洖鍙傝€冭噦涓庡鐞嗚噦澶嶅満
        """
        self._validate_input_field(input_field)
        fields = propagate_interferometric_bench(
            input_field,
            self._phase_on_fourier_grid(input_field.shape[-2:]),
            self.bench_config,
            reference_phase_offset_radians=self._reference_phase_offset(
                input_field.device,
                input_field.dtype,
            ),
        )
        return fields.reference, fields.processing

    def forward(self, input_field: torch.Tensor) -> torch.Tensor:
        """
        鐩稿共鍙犲姞涓よ噦澶嶅満骞惰繑鍥炲師濮嬪己搴?        """
        reference_field, process_field = self.forward_optical_fields(input_field)
        optical_field = reference_field + process_field
        return optical_field.abs().square().real

    def trainable_parameter_names(self) -> list[str]:
        """
        杩斿洖鍙缁冨厜瀛﹀弬鏁板悕绉?        """
        return [name for name, parameter in self.named_parameters() if parameter.requires_grad]

    @staticmethod
    def _validate_input_field(input_field: torch.Tensor) -> None:
        if not isinstance(input_field, torch.Tensor):
            raise invalid_restoration_contract("input_field must be a torch.Tensor")
        if input_field.ndim != 4:
            raise invalid_restoration_contract("input_field must be a 4D tensor")
        if not torch.is_complex(input_field):
            raise invalid_restoration_contract("input_field must be a complex tensor")
        if input_field.numel() == 0 or any(size <= 0 for size in input_field.shape):
            raise invalid_restoration_contract("input_field must not be empty")
        if not bool(torch.isfinite(input_field).all()):
            raise invalid_restoration_contract(
                "input_field must contain only finite values"
            )
