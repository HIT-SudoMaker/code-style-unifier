
from __future__ import annotations

from collections.abc import Callable
import copy
import inspect
import math

import pytest
import torch

from chromatix_next.optics import (
    ConstantMedium,
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PropagationDirection,
    SellmeierMedium,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import (
    AmplitudeTransmissionMap,
    OpticalPathModulation,
    amplitude_transmission_map,
    optical_path_modulation,
)
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


def _grid(
    counts: tuple[int, int] = (6, 5),
    spacing: tuple[float, float] = (0.4e-6, 0.4e-6),
) -> SpatialGrid:
    # 构造中心对齐的横向网格
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=spacing,
    )


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    # 构造单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _multispectral() -> Spectrum:
    # 构造双波长加权光谱（用于多光谱证据）
    wavelengths = (1.8e-6, 2.4e-6)
    weights = (0.45, 0.55)
    return Spectrum(wavelengths=wavelengths, weights=weights)


@pytest.mark.parametrize(
    ("action", "action_arguments"),
    (
        (
            amplitude_transmission_map,
            {"amplitude_transmission": torch.ones((6, 5), dtype=torch.float64)},
        ),
        (
            optical_path_modulation,
            {"optical_path_variation": torch.zeros((6, 5), dtype=torch.float64)},
        ),
    ),
    ids=("amplitude-transmission", "optical-path"),
)
@pytest.mark.parametrize(
    "polarization",
    (Polarization.scalar(), Polarization.transverse(), Polarization.full()),
    ids=("scalar", "transverse", "full"),
)
def test_modulation_preserves_field_representation_and_frame(
    action: Callable[..., OpticalField],
    action_arguments: dict[str, torch.Tensor],
    polarization: Polarization,
) -> None:
    """
    调制只改变包络定律并保留输入光场表征与参考框架
    """
    grid = _grid()
    field = _constant_field(
        grid,
        _monochromatic(),
        Vacuum(),
        polarization=polarization,
    )

    output = action(field, grid=grid, **action_arguments)

    assert output.polarization_representation is polarization.representation
    assert output.grid.is_physically_equivalent_to(field.grid)
    assert output.spectrum == field.spectrum
    assert output.medium is field.medium
    assert output.normalization is field.normalization
    assert output.path_reference == field.path_reference


def _constant_field(
    grid: SpatialGrid,
    spectrum: Spectrum,
    medium: Vacuum | ConstantMedium | SellmeierMedium,
    amplitude: float = 1.0,
    polarization: Polarization | None = None,
    device: torch.device | str = "cpu",
) -> OpticalField:
    # 构造均匀常幅、零相位输入光场（直接控制包络，避免与源耦合）
    polarization = polarization or Polarization.scalar()
    counts_y, counts_x = grid.sample_counts
    envelope = torch.full(
        (
            spectrum.count,
            polarization.component_count,
            counts_y,
            counts_x,
        ),
        complex(amplitude, 0.0),
        dtype=torch.complex128,
        device=device,
    )
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=spectrum,
        polarization_representation=(polarization).representation,
        medium=medium,
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


def _variation_map(grid: SpatialGrid) -> torch.Tensor:
    # 构造以米为单位的光程变化图：随 y、x 线性变化的斜坡，量级在亚波长
    counts_y, counts_x = grid.sample_counts
    wavelength = 2.0e-6
    row = torch.arange(counts_y, dtype=torch.float64) / max(counts_y - 1, 1)
    column = torch.arange(counts_x, dtype=torch.float64) / max(counts_x - 1, 1)
    # 量级取 0.3 个波长，保证相位覆盖足够范围且不引入数值精度问题
    return (row[:, None] + column[None, :]) * 0.15 * wavelength


def _amplitude_map(grid: SpatialGrid) -> torch.Tensor:
    # 构造无量纲、落在 [0,1] 的振幅透射图：随空间位置衰减
    counts_y, counts_x = grid.sample_counts
    row = torch.arange(counts_y, dtype=torch.float64) / max(counts_y - 1, 1)
    column = torch.arange(counts_x, dtype=torch.float64) / max(counts_x - 1, 1)
    return 0.4 + 0.5 * (row[:, None] * column[None, :])


def _independent_phase_factor(
    field: OpticalField,
    variation: torch.Tensor,
    real_dtype: torch.dtype,
) -> torch.Tensor:
    wavelengths = torch.tensor(field.spectrum.wavelengths, dtype=real_dtype)
    variation_cast = variation.to(dtype=real_dtype)
    vacuum_wave_number = (2.0 * math.pi / wavelengths).reshape(-1, 1, 1)
    phase = vacuum_wave_number * variation_cast.unsqueeze(0)
    return torch.polar(torch.ones_like(phase), phase)


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_modulation_public_actions_match_cpu_on_cuda() -> None:
    """
    两种调制公共动作在 CUDA 上保持与 CPU 相同的复包络
    """

    grid = _grid()
    spectrum = _monochromatic()
    cpu_field = _constant_field(grid, spectrum, Vacuum())
    cuda_field = _constant_field(grid, spectrum, Vacuum(), device="cuda:0")
    variation = _variation_map(grid)
    transmission = _amplitude_map(grid)

    cpu_phase = optical_path_modulation(
        cpu_field,
        grid=grid,
        optical_path_variation=variation,
    )
    cuda_phase = optical_path_modulation(
        cuda_field,
        grid=grid,
        optical_path_variation=variation.cuda(),
    )
    cpu_amplitude = amplitude_transmission_map(
        cpu_field,
        grid=grid,
        amplitude_transmission=transmission,
    )
    cuda_amplitude = amplitude_transmission_map(
        cuda_field,
        grid=grid,
        amplitude_transmission=transmission.cuda(),
    )

    torch.testing.assert_close(cpu_phase.envelope, cuda_phase.envelope.cpu())
    torch.testing.assert_close(
        cpu_amplitude.envelope,
        cuda_amplitude.envelope.cpu(),
    )


class TestAmplitudeTransmissionDuality:
    """
    振幅透射函数与组件共享同一物理动作
    """

    def test_function_and_component_return_the_same_field(self) -> None:
        """
        同一光场与透射图经直接函数和有状态组件得到相同强物理值
        """

        grid = _grid()
        field = _constant_field(
            grid,
            _monochromatic(),
            Vacuum(),
        )
        amplitude = _amplitude_map(grid)

        direct = amplitude_transmission_map(
            field,
            grid=grid,
            amplitude_transmission=amplitude,
        )
        component = AmplitudeTransmissionMap(
            grid=grid,
            amplitude_transmission=amplitude,
        )
        delegated = component(field)

        assert torch.equal(delegated.envelope, direct.envelope)
        assert delegated.grid.is_physically_equivalent_to(direct.grid)
        assert delegated.spectrum == direct.spectrum
        assert (
            delegated.polarization_representation
            is direct.polarization_representation
        )
        assert delegated.medium == direct.medium
        assert delegated.normalization is direct.normalization
        assert delegated.path_reference == direct.path_reference

    def test_function_and_component_infer_the_same_meta_result(self) -> None:
        """
        直接函数和隔离组件在 meta 设备上推导相同形状与精度
        """

        grid = _grid()
        real_field = _constant_field(
            grid,
            _multispectral(),
            Vacuum(),
        )
        field = OpticalField(
            envelope=torch.empty_like(
                real_field.envelope,
                device="meta",
            ),
            grid=real_field.grid.to(
                device="meta",
                dtype=real_field.envelope.real.dtype,
            ),
            spectrum=real_field.spectrum,
            polarization_representation=real_field.polarization_representation,
            medium=real_field.medium,
            normalization=real_field.normalization,
            path_reference=real_field.path_reference,
        )
        amplitude = _amplitude_map(grid)
        component = AmplitudeTransmissionMap(
            grid=grid,
            amplitude_transmission=amplitude,
        )
        isolated = copy.deepcopy(component)
        isolated.to_empty(device="meta")

        direct = amplitude_transmission_map(
            field,
            grid=field.grid,
            amplitude_transmission=amplitude,
        )
        delegated = isolated(field)

        assert delegated.envelope.shape == direct.envelope.shape
        assert delegated.envelope.dtype is direct.envelope.dtype
        assert delegated.envelope.device.type == "meta"
        assert direct.envelope.device.type == "meta"

    def test_function_and_component_preserve_the_same_parameter_gradient(
        self,
    ) -> None:
        """
        两种入口都保留用户振幅 Parameter 的同一梯度行为
        """

        grid = _grid()
        field = _constant_field(
            grid,
            _monochromatic(),
            Vacuum(),
        )
        direct_parameter = torch.nn.Parameter(_amplitude_map(grid))
        component_parameter = torch.nn.Parameter(
            direct_parameter.detach().clone(),
        )
        component = AmplitudeTransmissionMap(
            grid=grid,
            amplitude_transmission=component_parameter,
        )

        direct = amplitude_transmission_map(
            field,
            grid=grid,
            amplitude_transmission=direct_parameter,
        )
        delegated = component(field)
        direct_gradient = torch.autograd.grad(
            direct.envelope.real.sum(),
            direct_parameter,
        )[0]
        delegated_gradient = torch.autograd.grad(
            delegated.envelope.real.sum(),
            component_parameter,
        )[0]

        assert component.amplitude_transmission is component_parameter
        assert torch.equal(delegated.envelope, direct.envelope)
        assert torch.equal(delegated_gradient, direct_gradient)


class TestOpticalPathModulationDuality:
    """
    光程调制函数与组件共享同一物理动作
    """

    def test_function_and_component_return_the_same_field(self) -> None:
        """
        同一光程轮廓经直接函数和有状态组件得到相同强物理值
        """

        grid = _grid()
        field = _constant_field(
            grid,
            _monochromatic(),
            Vacuum(),
        )
        variation = _variation_map(grid)
        baseline = torch.tensor(0.3e-6, dtype=torch.float64)

        direct = optical_path_modulation(
            field,
            grid=grid,
            optical_path_variation=variation,
            optical_path_baseline=baseline,
        )
        component = OpticalPathModulation(
            grid=grid,
            optical_path_variation=variation,
            optical_path_baseline=baseline,
        )
        delegated = component(field)

        assert torch.equal(delegated.envelope, direct.envelope)
        assert delegated.path_reference == direct.path_reference

    def test_function_and_component_infer_the_same_meta_result(self) -> None:
        """
        直接函数和隔离组件在 meta 设备上推导相同形状与精度
        """

        grid = _grid()
        real_field = _constant_field(
            grid,
            _multispectral(),
            Vacuum(),
        )
        field = OpticalField(
            envelope=torch.empty_like(
                real_field.envelope,
                device="meta",
            ),
            grid=real_field.grid.to(
                device="meta",
                dtype=real_field.envelope.real.dtype,
            ),
            spectrum=real_field.spectrum,
            polarization_representation=real_field.polarization_representation,
            medium=real_field.medium,
            normalization=real_field.normalization,
            path_reference=real_field.path_reference,
        )
        variation = _variation_map(grid)
        component = OpticalPathModulation(
            grid=grid,
            optical_path_variation=variation,
            optical_path_baseline=0.3e-6,
        )
        isolated = copy.deepcopy(component)
        isolated.to_empty(device="meta")

        direct = optical_path_modulation(
            field,
            grid=field.grid,
            optical_path_variation=variation,
            optical_path_baseline=0.3e-6,
        )
        delegated = isolated(field)

        assert delegated.envelope.shape == direct.envelope.shape
        assert delegated.envelope.dtype is direct.envelope.dtype
        assert delegated.envelope.device.type == "meta"
        assert direct.envelope.device.type == "meta"
        assert all(
            isinstance(length, torch.Tensor)
            and length.device.type == "meta"
            for length in delegated.path_reference.lengths
        )

    def test_function_and_component_preserve_the_same_parameter_gradients(
        self,
    ) -> None:
        """
        两种入口都保留光程变化与均匀基线的同一梯度行为
        """

        grid = _grid()
        field = _constant_field(
            grid,
            _monochromatic(),
            Vacuum(),
        )
        direct_variation = torch.nn.Parameter(_variation_map(grid))
        direct_baseline = torch.nn.Parameter(
            torch.tensor(0.3e-6, dtype=torch.float64),
        )
        component_variation = torch.nn.Parameter(
            direct_variation.detach().clone(),
        )
        component_baseline = torch.nn.Parameter(
            direct_baseline.detach().clone(),
        )
        component = OpticalPathModulation(
            grid=grid,
            optical_path_variation=component_variation,
            optical_path_baseline=component_baseline,
        )

        direct = optical_path_modulation(
            field,
            grid=grid,
            optical_path_variation=direct_variation,
            optical_path_baseline=direct_baseline,
        )
        delegated = component(field)
        direct_loss = direct.envelope.real.sum() + sum(
            direct.path_reference.lengths,
        )
        delegated_loss = delegated.envelope.real.sum() + sum(
            delegated.path_reference.lengths,
        )
        direct_gradients = torch.autograd.grad(
            direct_loss,
            (direct_variation, direct_baseline),
        )
        delegated_gradients = torch.autograd.grad(
            delegated_loss,
            (component_variation, component_baseline),
        )

        assert component.optical_path_variation is component_variation
        assert component.optical_path_baseline is component_baseline
        assert torch.equal(delegated.envelope, direct.envelope)
        assert all(
            torch.equal(delegated_gradient, direct_gradient)
            for delegated_gradient, direct_gradient in zip(
                delegated_gradients,
                direct_gradients,
            )
        )


class TestOpticalPathModulationPhysicalInvariants:
    """
    证据层 1（光程调制）：物理不变量
    """

    @pytest.mark.parametrize(
        ("variation_factory", "baseline", "identity"),
        (
            (
                lambda grid: torch.zeros(grid.sample_counts, dtype=torch.float32),
                0.0,
                "optical_path_modulation_variation_invalid",
            ),
            (
                lambda grid: torch.nn.Parameter(
                    torch.zeros(grid.sample_counts, dtype=torch.float32),
                ),
                0.0,
                "optical_path_modulation_variation_invalid",
            ),
            (
                lambda grid: torch.zeros(grid.sample_counts, dtype=torch.float64),
                torch.nn.Parameter(torch.tensor(0.0, dtype=torch.float32)),
                "optical_path_modulation_baseline_invalid",
            ),
        ),
    )
    def test_float32_physical_parameters_rejected_with_owner_identity(
        self,
        variation_factory: Callable[[SpatialGrid], torch.Tensor],
        baseline: float | torch.Tensor,
        identity: str,
    ) -> None:
        """
        变化图、训练变化图和基线各自在调制边界拒绝 float32
        """

        grid = _grid()
        with pytest.raises(ValueError, match=identity):
            OpticalPathModulation(
                grid=grid,
                optical_path_variation=variation_factory(grid),
                optical_path_baseline=baseline,
            )

    def test_meta_variation_obeys_fixed_double_admission_and_executes(
        self,
    ) -> None:
        """
        Meta 变化图按结构拒绝 float32，并以 float64 Parameter 完成推导
        """

        grid = _grid()
        valid_variation = torch.nn.Parameter(
            torch.zeros(
                grid.sample_counts,
                dtype=torch.float64,
                device="meta",
            ),
        )
        component = OpticalPathModulation(
            grid=grid,
            optical_path_variation=valid_variation,
        )
        real_field = _constant_field(
            grid,
            _monochromatic(),
            Vacuum(),
        )
        field = OpticalField(
            envelope=torch.empty_like(real_field.envelope, device="meta"),
            grid=real_field.grid.to(device="meta", dtype=torch.float64),
            spectrum=real_field.spectrum,
            polarization_representation=real_field.polarization_representation,
            medium=real_field.medium,
            normalization=real_field.normalization,
            path_reference=real_field.path_reference,
        )

        output = component(field)

        assert component.optical_path_variation is valid_variation
        assert output.envelope.device.type == "meta"
        assert output.envelope.dtype is torch.complex128
        with pytest.raises(
            ValueError,
            match="optical_path_modulation_variation_invalid",
        ):
            OpticalPathModulation(
                grid=grid,
                optical_path_variation=torch.nn.Parameter(
                    torch.zeros(
                        grid.sample_counts,
                        dtype=torch.float32,
                        device="meta",
                    ),
                ),
            )

    @pytest.mark.parametrize(
        ("variation_factory", "baseline", "identity"),
        (
            (
                lambda grid: torch.zeros(
                    grid.sample_counts,
                    dtype=torch.complex128,
                ),
                0.0,
                "optical_path_modulation_variation_invalid",
            ),
            (
                lambda grid: torch.zeros(
                    grid.sample_counts,
                    dtype=torch.int64,
                ),
                0.0,
                "optical_path_modulation_variation_invalid",
            ),
            (
                lambda grid: torch.full(
                    grid.sample_counts,
                    float("inf"),
                    dtype=torch.float64,
                ),
                0.0,
                "optical_path_modulation_variation_invalid",
            ),
            (
                lambda grid: torch.zeros(
                    (grid.sample_counts[0] + 1, grid.sample_counts[1]),
                    dtype=torch.float64,
                ),
                0.0,
                "optical_path_modulation_variation_shape_mismatch",
            ),
            (
                lambda grid: torch.zeros(
                    grid.sample_counts,
                    dtype=torch.float64,
                ),
                torch.tensor(0.0 + 0.0j, dtype=torch.complex128),
                "optical_path_modulation_baseline_invalid",
            ),
            (
                lambda grid: torch.zeros(
                    grid.sample_counts,
                    dtype=torch.float64,
                ),
                torch.tensor(0, dtype=torch.int64),
                "optical_path_modulation_baseline_invalid",
            ),
            (
                lambda grid: torch.zeros(
                    grid.sample_counts,
                    dtype=torch.float64,
                ),
                torch.tensor(False, dtype=torch.bool),
                "optical_path_modulation_baseline_invalid",
            ),
            (
                lambda grid: torch.zeros(
                    grid.sample_counts,
                    dtype=torch.float64,
                ),
                torch.zeros((1,), dtype=torch.float64),
                "optical_path_modulation_baseline_invalid",
            ),
            (
                lambda grid: torch.zeros(
                    grid.sample_counts,
                    dtype=torch.float64,
                ),
                torch.tensor(float("nan"), dtype=torch.float64),
                "optical_path_modulation_baseline_invalid",
            ),
            (
                lambda grid: torch.zeros(
                    grid.sample_counts,
                    dtype=torch.float64,
                ),
                torch.tensor(float("inf"), dtype=torch.float64),
                "optical_path_modulation_baseline_invalid",
            ),
        ),
    )
    def test_invalid_state_fails_with_owner_identity(
        self,
        variation_factory: Callable[[SpatialGrid], torch.Tensor],
        baseline: torch.Tensor | float,
        identity: str,
    ) -> None:
        """
        复杂、非有限和错形状态在光程调制构造边界稳定失败
        """

        with pytest.raises(ValueError, match=identity):
            OpticalPathModulation(
                grid=_grid(),
                optical_path_variation=variation_factory(_grid()),
                optical_path_baseline=baseline,
            )

    def test_tensor_state_keeps_registered_buffer_identity(self) -> None:
        """
        合法变化图与基线普通张量保持同一 Buffer 对象
        """

        grid = _grid()
        variation = _variation_map(grid)
        baseline = torch.tensor(0.3e-6, dtype=torch.float64)
        component = OpticalPathModulation(
            grid=grid,
            optical_path_variation=variation,
            optical_path_baseline=baseline,
        )
        buffers = dict(component.named_buffers())

        assert component.optical_path_variation is variation
        assert component.optical_path_baseline is baseline
        assert buffers["optical_path_variation"] is variation
        assert buffers["optical_path_baseline"] is baseline

    def test_phase_only_preserves_envelope_magnitude(self) -> None:
        """光程调制 ⇒ 包络模逐点不变（仅相位，振幅模不变）
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.7)
        element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=_variation_map(grid),
        )
        output = element(field)
        input_magnitude = field.envelope.abs()
        output_magnitude = output.envelope.abs()
        assert torch.allclose(input_magnitude, output_magnitude, atol=1e-7)

    def test_optical_path_phase_is_independent_of_propagation_medium(
        self,
    ) -> None:
        """
        已定义的光程变化不再被传播介质重复乘以折射率
        """

        grid = _grid()
        spectrum = _monochromatic()
        variation = _variation_map(grid)
        element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=variation,
        )
        vacuum_output = element(
            _constant_field(grid, spectrum, Vacuum()),
        )
        material_output = element(
            _constant_field(
                grid,
                spectrum,
                ConstantMedium(index=1.5),
            ),
        )
        assert torch.allclose(
            vacuum_output.envelope,
            material_output.envelope,
            atol=1e-12,
            rtol=1e-12,
        )

    def test_phase_matches_optical_path_analytic_amount(self) -> None:
        """输出包络相位须与 2π·ΔL/λ 一致

        即使光场携带非单位折射率介质，已经定义的光程也不被重复换算。
        """
        grid = _grid()
        spectrum = _monochromatic()
        medium = ConstantMedium(index=1.5)
        field = _constant_field(grid, spectrum, medium, amplitude=1.0)
        variation = _variation_map(grid)
        element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=variation,
        )
        output = element(field)
        reference_phase = _independent_phase_factor(field, variation, torch.float64)
        expected = reference_phase.unsqueeze(1)  # 在偏振轴广播
        assert torch.allclose(output.envelope, expected, atol=1e-7)

    def test_vacuum_phase_matches_same_optical_path_rule(self) -> None:
        """真空情形遵守同一 2π·ΔL/λ 光程规则
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        variation = _variation_map(grid)
        element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=variation,
        )
        output = element(field)
        reference_phase = _independent_phase_factor(field, variation, torch.float64)
        expected = reference_phase.unsqueeze(1)
        assert torch.allclose(output.envelope, expected, atol=1e-7)

    def test_baseline_shifts_path_reference_only(self) -> None:
        """基线只移动路径参考，不写入包络相位

        与迁移源语义一致：基线进入光程参考 anchor，不进入包络。零变化 + 非零基线 ⇒
        包络逐点不变，路径参考移动基线量。
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        zero_variation = torch.zeros(grid.sample_counts, dtype=torch.float64)
        baseline = 1.3e-6
        element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=zero_variation,
            optical_path_baseline=baseline,
        )
        output = element(field)
        assert torch.allclose(output.envelope, field.envelope, atol=1e-12)
        assert output.path_reference.lengths == pytest.approx((baseline,))

    def test_baseline_adds_to_existing_path_reference(self) -> None:
        """基线须叠加到输入光场既有的路径参考上
        """
        grid = _grid()
        spectrum = _monochromatic()
        existing_reference = OpticalPathReference(lengths=(0.7e-6,))
        field = OpticalField(
            envelope=torch.full(
                (1, 1, grid.sample_counts[0], grid.sample_counts[1]),
                complex(1.0, 0.0),
                dtype=torch.complex128,
            ),
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=existing_reference,
        )
        baseline = 0.9e-6
        zero_variation = torch.zeros(grid.sample_counts, dtype=torch.float64)
        element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=zero_variation,
            optical_path_baseline=baseline,
        )
        output = element(field)
        output_length = output.path_reference.lengths[0]
        assert isinstance(output_length, torch.Tensor)
        assert output_length.dtype is torch.float64
        assert output.path_reference.lengths == pytest.approx(
            (existing_reference.lengths[0] + baseline,),
        )

    def test_grid_mismatch_rejected(self) -> None:
        """输入光场网格与元件注册网格不一致须以稳定身份拒绝
        """
        grid = _grid()
        other_grid = _grid(counts=(7, 5))
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum())
        other_zeros = torch.zeros(other_grid.sample_counts, dtype=torch.float64)
        element = OpticalPathModulation(
            grid=other_grid,
            optical_path_variation=other_zeros,
        )
        with pytest.raises(
            ValueError,
            match="optical_path_modulation_grid_mismatch",
        ):
            element(field)

    def test_user_parameter_identity_preserved(self) -> None:
        """用户 supplied 光程变化 Parameter 须保持身份注册，不被克隆
        """
        grid = _grid()
        variation = torch.nn.Parameter(_variation_map(grid))
        element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=variation,
        )
        assert element.optical_path_variation is variation
        assert any(parameter is variation for parameter in element.parameters())

    def test_output_dtype_ignores_process_default(self) -> None:
        """
        中性相位元件跟随输入 fixed-double 场，不读取进程默认 dtype
        """

        grid = _grid()
        field = _constant_field(grid, _monochromatic(), Vacuum())
        element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=torch.zeros(
                grid.sample_counts,
                dtype=torch.float64,
            ),
        )
        previous_default = torch.get_default_dtype()
        try:
            torch.set_default_dtype(torch.float32)
            output = element(field)
        finally:
            torch.set_default_dtype(previous_default)

        assert output.envelope.dtype is torch.complex128


class TestAmplitudeTransmissionPhysicalInvariants:
    """
    证据层 1（振幅透射）：物理不变量
    """

    def test_amplitude_multiply_preserves_phase(self) -> None:
        """振幅透射 ⇒ 复逐元素乘，输出相位与输入一致、模为输入模乘振幅
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        amplitude_map = _amplitude_map(grid)
        element = AmplitudeTransmissionMap(
            grid=grid,
            amplitude_transmission=amplitude_map,
        )
        output = element(field)
        expected = amplitude_map.to(dtype=torch.complex128).unsqueeze(0).unsqueeze(0)
        assert torch.allclose(output.envelope, expected, atol=1e-7)
        # 输出相位仍为零（输入为零相位），仅模被缩放
        assert torch.allclose(
            output.envelope.angle(),
            torch.zeros_like(output.envelope.angle()),
            atol=1e-7,
        )

    def test_intensity_transmission_is_squared_amplitude(self) -> None:
        """强度透射须为 |振幅|²

        经 IntensityDetection：输出光强与输入光强之比须等于振幅图的平方。
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        amplitude_map = _amplitude_map(grid)
        element = AmplitudeTransmissionMap(
            grid=grid,
            amplitude_transmission=amplitude_map,
        )
        detection = IntensityDetection()
        output_intensity = detection(element(field)).values
        input_intensity = detection(field).values
        ratio = output_intensity / input_intensity
        expected_ratio = (amplitude_map.to(dtype=torch.float64) ** 2)
        assert torch.allclose(ratio, expected_ratio, atol=1e-6)

    def test_constructor_accepts_only_amplitude_transmission(self) -> None:
        """
        构造接口只表达振幅透射，不伪装支持另一种物理输入
        """

        parameters = inspect.signature(
            AmplitudeTransmissionMap,
        ).parameters
        assert tuple(parameters) == (
            "grid",
            "amplitude_transmission",
        )

    def test_amplitude_out_of_range_rejected(self) -> None:
        """振幅值越出 [0,1]（被动，无增益）须以稳定身份拒绝
        """
        grid = _grid()
        invalid_map = _amplitude_map(grid) * 1.5  # 含大于 1 的值
        with pytest.raises(
            ValueError,
            match="amplitude_transmission_map_values_invalid",
        ):
            AmplitudeTransmissionMap(
                grid=grid,
                amplitude_transmission=invalid_map,
            )

    def test_single_precision_amplitude_map_rejected(self) -> None:
        """单精度振幅透射图须以稳定身份拒绝，而非静默提升为 float64（固定双精度核）
        """
        grid = _grid()
        with pytest.raises(
            ValueError,
            match="amplitude_transmission_map_values_invalid",
        ):
            AmplitudeTransmissionMap(
                grid=grid,
                amplitude_transmission=_amplitude_map(grid).to(
                    dtype=torch.float32,
                ),
            )

    def test_grid_mismatch_rejected(self) -> None:
        """输入光场网格与元件注册网格不一致须以稳定身份拒绝
        """
        grid = _grid()
        other_grid = _grid(counts=(6, 7))
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum())
        element = AmplitudeTransmissionMap(
            grid=other_grid,
            amplitude_transmission=_amplitude_map(other_grid),
        )
        with pytest.raises(
            ValueError,
            match="amplitude_transmission_map_grid_mismatch",
        ):
            element(field)

    def test_user_parameter_identity_preserved(self) -> None:
        """用户 supplied 振幅 Parameter 须保持身份注册，不被克隆
        """
        grid = _grid()
        amplitude = torch.nn.Parameter(_amplitude_map(grid))
        element = AmplitudeTransmissionMap(
            grid=grid,
            amplitude_transmission=amplitude,
        )
        assert element.amplitude_transmission is amplitude
        assert any(parameter is amplitude for parameter in element.parameters())


class TestIndependentReference:
    """
    证据层 2：独立解析参照
    """

    def test_multispectral_optical_path_phase_matches(self) -> None:
        """多光谱：每光谱分量相位须与独立 2π·ΔL/λ 一致

        一个光程变化由各分量共享，相位仅按其波长换算，不重复查询传播介质。
        """
        grid = _grid()
        spectrum = _multispectral()
        medium = ConstantMedium(index=1.33)
        field = _constant_field(grid, spectrum, medium, amplitude=1.0)
        variation = _variation_map(grid)
        element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=variation,
        )
        output = element(field)
        reference = _independent_phase_factor(field, variation, torch.float64)
        reference = reference.unsqueeze(1)
        assert torch.allclose(output.envelope, reference, atol=1e-7)

    def test_multispectral_amplitude_broadcast_matches(self) -> None:
        """多光谱、横向偏振：振幅图须在光谱与偏振轴上广播，与独立参照一致
        """
        grid = _grid()
        spectrum = _multispectral()
        field = _constant_field(
            grid,
            spectrum,
            Vacuum(),
            amplitude=1.0,
            polarization=Polarization.transverse(),
        )
        amplitude_map = _amplitude_map(grid)
        element = AmplitudeTransmissionMap(
            grid=grid,
            amplitude_transmission=amplitude_map,
        )
        output = element(field)
        # 期望形状 (光谱=2, 偏振=2, 高, 宽)，振幅图在光谱与偏振轴广播
        expected = amplitude_map.to(dtype=torch.complex128).unsqueeze(0).unsqueeze(0)
        expected = expected.expand(2, 2, grid.sample_counts[0], grid.sample_counts[1])
        assert output.envelope.shape == expected.shape
        assert torch.allclose(output.envelope, expected, atol=1e-7)

class TestGradientEvidence:
    """
    证据层 3：梯度证据（双精度，经元件→探测链路）
    """

    def test_gradcheck_on_trainable_optical_path_variation(self) -> None:
        """对可训练光程变化做 gradcheck（经光程调制→实部约减）

        光程变化为 float64 叶子 Parameter，由元件直接持有；gradcheck 就地扰动该同一
        Parameter 对象。光场介质不参与已定义光程的相位；光场包络常幅零相位（无梯度）。
        损失取输出包络实部和（依赖相位 via cos），保证非零梯度且处处可微。

        注：相位对光程高度敏感（dφ/dv = 2π/λ ≈ 3.1e6 rad/m），gradcheck 默认
        eps=1e-6 m 跨越约 3.1 rad，超出线性区。这里显式取 eps 使 c·eps ≪ 1（线性区），
        为振荡函数 gradcheck 的标准处置，而非物理改动。
        """
        grid = _grid()
        spectrum = _monochromatic()
        medium = ConstantMedium(index=1.5)
        field = _constant_field(grid, spectrum, medium, amplitude=1.0)
        variation = torch.nn.Parameter(_variation_map(grid))
        element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=variation,
        )

        def run(variation_value: torch.Tensor) -> torch.Tensor:
            """
            返回当前变化下的输出包络实部和（依赖相位 via cos）
            """
            return element(field).envelope.real.sum()

        assert torch.autograd.gradcheck(
            run,
            (variation,),
            eps=1e-11,
            raise_exception=True,
        )

    def test_gradcheck_on_trainable_amplitude_map(self) -> None:
        """对可训练振幅图做 gradcheck（经振幅透射→强度探测）

        振幅图为 float64 叶子 Parameter，由元件直接持有；gradcheck 就地扰动该同一
        Parameter 对象。光场常幅零相位。损失取 IntensityDetection 输出之和（依赖振幅
        平方），保证非零梯度。
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        amplitude = torch.nn.Parameter(_amplitude_map(grid))
        element = AmplitudeTransmissionMap(
            grid=grid,
            amplitude_transmission=amplitude,
        )
        detection = IntensityDetection()

        def run(amplitude_value: torch.Tensor) -> torch.Tensor:
            """
            返回当前振幅图下的光强总和（依赖振幅平方）
            """
            return detection(element(field)).values.sum()

        assert torch.autograd.gradcheck(run, (amplitude,), raise_exception=True)


class TestOpticalPathModulationStateRestoration:
    """
    固定光程状态恢复证据
    """

    def test_loaded_variation_controls_the_next_calculation(self) -> None:
        """
        载入新固定光程图后下一次计算立即使用新状态
        """

        grid = _grid()
        spectrum = _monochromatic()
        wavelength = spectrum.wavelengths[0]
        field = _constant_field(
            grid,
            spectrum,
            Vacuum(),
            amplitude=1.0,
        )
        restored = OpticalPathModulation(
            grid=grid,
            optical_path_variation=torch.zeros(
                grid.sample_counts,
                dtype=torch.float64,
            ),
        )
        expected_element = OpticalPathModulation(
            grid=grid,
            optical_path_variation=torch.full(
                grid.sample_counts,
                wavelength / 4.0,
                dtype=torch.float64,
            ),
            optical_path_baseline=wavelength / 8.0,
        )
        restored(field)

        restored.load_state_dict(expected_element.state_dict())
        output = restored(field)
        expected = expected_element(field)

        assert torch.allclose(output.envelope, expected.envelope, atol=1e-12)
        assert output.path_reference == expected.path_reference


class TestModulationGridState:
    """
    调制元件拥有的网格遵循标准 PyTorch 状态生命周期
    """

    @pytest.mark.parametrize(
        "component_factory",
        (
            lambda grid: AmplitudeTransmissionMap(
                grid=grid,
                amplitude_transmission=torch.ones(
                    grid.sample_counts,
                    dtype=torch.float64,
                ),
            ),
            lambda grid: OpticalPathModulation(
                grid=grid,
                optical_path_variation=torch.zeros(
                    grid.sample_counts,
                    dtype=torch.float64,
                ),
            ),
        ),
        ids=("amplitude", "optical-path"),
    )
    def test_grid_parameter_and_buffers_follow_component_lifecycle(
        self,
        component_factory: Callable[
            [SpatialGrid],
            AmplitudeTransmissionMap | OpticalPathModulation,
        ],
    ) -> None:
        """
        可训练间距保留 Parameter 身份，其余网格量可发现并随元件迁移

        固定双精度下网格状态不得漂移到单精度。元件 ``to(float64)``
        迁移后 Parameter 身份仍保留、网格仍可重建；任何 ``to(float32)`` 之后的
        重建须被物理值入口拒绝（f32 reject），证明网格不是单精度兼容表面。
        """
        spacing_y = torch.nn.Parameter(
            torch.tensor(1.0e-6, dtype=torch.float64),
        )
        grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(
                spacing_y,
                torch.tensor(1.5e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(-2.0e-6, dtype=torch.float64),
                torch.tensor(-3.0e-6, dtype=torch.float64),
            ),
        )
        component = component_factory(grid)

        assert any(parameter is spacing_y for parameter in component.parameters())
        assert len(tuple(component.buffers())) >= 3

        # 固定双精度迁移：Parameter 身份与可发现性保留，网格仍可重建
        component.to(dtype=torch.float64)
        assert component.grid.sample_spacing[0] is spacing_y
        assert all(
            value.dtype is torch.float64
            for value in (
                *component.grid.sample_spacing,
                *component.grid.first_sample_position,
            )
        )

        component.to(dtype=torch.float32)
        with pytest.raises(
            ValueError,
            match="spatial_grid_sample_spacing_invalid",
        ):
            component.grid  # noqa: B018


class TestHostedExecution:
    """
    托管端到端：PlaneWave → 托管调制元件 → IntensityDetection
    """

    def test_hosted_optical_path_modulation_does_not_change_intensity(self) -> None:
        """托管光程调制 ⇒ 仅相位，IntensityDetection 输出光强不变

        PlaneWave（单位振幅、前向、相对归一化）→ 托管光程调制 → IntensityDetection。
        相位调制不改包络模，故输出光强与无调制时一致。
        """
        grid = _grid()
        spectrum = _monochromatic()
        workstation = Workstation.cpu()
        source = workstation.host(
            PlaneWave(
                spectrum=spectrum,
                polarization=Polarization.scalar(),
                medium=Vacuum(),
                propagation_direction=PropagationDirection.forward(),
                relative_amplitude=1.0,
            ),
        )
        modulation = workstation.host(
            OpticalPathModulation(
                grid=grid,
                optical_path_variation=_variation_map(grid),
            ),
        )
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        modulated = modulation(field)
        intensity = detection(modulated)
        assert intensity.normalization is FieldNormalization.RELATIVE
        # 单位振幅、单位权重 ⇒ 每像素光强为 1
        expected = torch.full(grid.sample_counts, 1.0, dtype=torch.float64)
        assert torch.allclose(intensity.values, expected, atol=1e-5)

    def test_hosted_amplitude_transmission_scales_intensity_by_square(self) -> None:
        """托管振幅透射 ⇒ 光强按振幅平方缩放

        PlaneWave（单位振幅）→ 托管振幅透射 → IntensityDetection。输出光强须等于
        输入光强乘以振幅图的平方。
        """
        grid = _grid()
        spectrum = _monochromatic()
        amplitude_map = _amplitude_map(grid)
        workstation = Workstation.cpu()
        source = workstation.host(
            PlaneWave(
                spectrum=spectrum,
                polarization=Polarization.scalar(),
                medium=Vacuum(),
                propagation_direction=PropagationDirection.forward(),
                relative_amplitude=1.0,
            ),
        )
        modulation = workstation.host(
            AmplitudeTransmissionMap(
                grid=grid,
                amplitude_transmission=amplitude_map,
            ),
        )
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        modulated = modulation(field)
        intensity = detection(modulated)
        expected = (amplitude_map.to(dtype=torch.float64) ** 2)
        assert torch.allclose(intensity.values, expected, atol=1e-6)
