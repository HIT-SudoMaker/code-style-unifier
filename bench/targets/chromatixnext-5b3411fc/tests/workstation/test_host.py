
from __future__ import annotations

from typing import Literal

import pytest
import torch

from chromatix_next.errors import WorkstationError
from chromatix_next.optics import (
    OpticalField,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
)
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


class _DummyParamModule(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造含实参数、复参数与固定缓冲的最小受测模块（固定双精度）
        """
        super().__init__()
        self.real_parameter = torch.nn.Parameter(
            torch.randn(2, 2, dtype=torch.float64)
        )
        self.complex_parameter = torch.nn.Parameter(
            torch.randn(2, 2, dtype=torch.complex128)
        )
        self.register_buffer(
            "fixed_buffer",
            torch.randn(2, 2, dtype=torch.float64),
            persistent=False,
        )

    @property
    def role(self) -> Literal["element"]:
        """
        返回只读元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        保持输入光场
        """
        return field


class TestWorkstationHost:
    """
    托管语义
    """

    def test_host_rejects_float32_state_before_device_movement(self) -> None:
        """
        托管前若有非固定双精度的浮点 Parameter，须在搬设备前即被拒绝
        """

        class _Float32ParamModule(_DummyParamModule):
            def __init__(self) -> None:
                super().__init__()
                # torch.randn 默认 float32；覆盖固定双精度的实参数以触发预检
                self.real_parameter = torch.nn.Parameter(torch.randn(2, 2))

        workstation = Workstation.cpu()
        module = _Float32ParamModule()

        with pytest.raises(WorkstationError, match="workstation_host_dtype_invalid"):
            workstation.host(module)


    def test_hosted_source_dtype_ignores_process_default(self) -> None:
        """
        托管不让进程默认 dtype 污染 Source 的 fixed-double 输出
        """

        source = PlaneWave(
            spectrum=Spectrum.monochromatic(wavelength=532.0e-9),
            polarization=Polarization.scalar(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        grid = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(1.0e-6, 1.0e-6),
        )
        previous_default = torch.get_default_dtype()
        try:
            torch.set_default_dtype(torch.float32)
            field = Workstation.cpu().host(source)(grid)
        finally:
            torch.set_default_dtype(previous_default)

        assert field.envelope.dtype is torch.complex128



    def test_loading_state_does_not_transfer_host_ownership(self) -> None:
        """
        加载已托管组件的 state_dict 不会把工作站身份带到新组件
        """
        owner = Workstation.cpu()
        restored_owner = Workstation.cpu()
        hosted = _DummyParamModule()
        restored = _DummyParamModule()
        owner.host(hosted)

        restored.load_state_dict(hosted.state_dict())

        assert restored_owner.host(restored) is restored
        assert restored.real_parameter.dtype is torch.float64
        assert restored.complex_parameter.dtype is torch.complex128
