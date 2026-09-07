
from __future__ import annotations

import copy
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
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import CircularPupil, IdealThinLens, ideal_thin_lens
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


def _grid(
    counts: tuple[int, int] = (7, 7),
    spacing: tuple[float, float] = (0.5e-6, 0.5e-6),
) -> SpatialGrid:
    # 构造中心对齐的横向网格（样本物理对齐原点）
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
    "polarization",
    (Polarization.scalar(), Polarization.transverse(), Polarization.full()),
    ids=("scalar", "transverse", "full"),
)
def test_ideal_thin_lens_preserves_field_representation_and_frame(
    polarization: Polarization,
) -> None:
    """
    理想薄透镜只施加相位并保留输入光场表征与参考框架
    """
    grid = _grid()
    field = PlaneWave(
        spectrum=_monochromatic(),
        polarization=polarization,
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )(grid)

    output = ideal_thin_lens(field, grid=grid, focal_length=12.0e-6)

    assert output.polarization_representation is polarization.representation
    assert output.grid.is_physically_equivalent_to(field.grid)
    assert output.spectrum == field.spectrum
    assert output.medium is field.medium
    assert output.normalization is field.normalization
    assert output.path_reference == field.path_reference


def _constant_field(
    grid: SpatialGrid,
    spectrum: Spectrum,
    medium: Vacuum | ConstantMedium = None,  # type: ignore[assignment]
    amplitude: float = 1.0,
    *,
    device: torch.device | str | None = None,
) -> OpticalField:
    # 构造均匀常幅、零相位输入光场
    if medium is None:
        medium = Vacuum()
    counts_y, counts_x = grid.sample_counts
    envelope = torch.full(
        (spectrum.count, 1, counts_y, counts_x),
        complex(amplitude, 0.0),
        dtype=torch.complex128,
        device=device,
    )
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=spectrum,
        polarization_representation=(Polarization.scalar()).representation,
        medium=medium,
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


def _grid_coordinates(grid: SpatialGrid) -> tuple[torch.Tensor, torch.Tensor]:
    # 独立构造网格物理坐标 (y, x)，以米为单位
    counts_y, counts_x = grid.sample_counts
    spacing_y, spacing_x = grid.sample_spacing
    first_y, first_x = grid.first_sample_position
    coordinate_y = (
        torch.arange(counts_y, dtype=torch.float64) * float(spacing_y) + float(first_y)
    )
    coordinate_x = (
        torch.arange(counts_x, dtype=torch.float64) * float(spacing_x) + float(first_x)
    )
    return coordinate_y, coordinate_x


def _independent_quadratic_phase(
    field: OpticalField,
    focal_length: float,
    center_y: float,
    center_x: float,
    real_dtype: torch.dtype,
) -> torch.Tensor:
    coordinate_y, coordinate_x = _grid_coordinates(field.grid)
    radius_squared = (coordinate_y[:, None] - center_y).square() + (
        coordinate_x[None, :] - center_x
    ).square()
    wavelengths = torch.tensor(field.spectrum.wavelengths, dtype=real_dtype)
    indices = field.medium.refractive_index(wavelengths).to(dtype=real_dtype)
    wave_number = 2.0 * math.pi * indices / wavelengths
    phase = (-wave_number.reshape(-1, 1, 1) * radius_squared.unsqueeze(0)) / (
        2.0 * focal_length
    )
    return torch.polar(torch.ones_like(phase), phase)


class TestIdealThinLensDuality:
    """
    理想薄透镜函数与组件共享同一物理动作
    """

    def test_function_and_component_return_the_same_field(self) -> None:
        """
        同一透镜参数经直接函数和有状态组件得到相同强物理值
        """

        grid = _grid()
        field = _constant_field(
            grid,
            _multispectral(),
            ConstantMedium(index=1.33),
        )
        focal_length = torch.tensor(9.0e-6, dtype=torch.float64)
        lens_center = (0.35e-6, -0.2e-6)

        direct = ideal_thin_lens(
            field,
            grid=grid,
            focal_length=focal_length,
            lens_center=lens_center,
        )
        component = IdealThinLens(
            grid=grid,
            focal_length=focal_length,
            lens_center=lens_center,
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
            ConstantMedium(index=1.33),
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
        component = IdealThinLens(
            grid=grid,
            focal_length=9.0e-6,
            lens_center=(0.35e-6, -0.2e-6),
        )
        isolated = copy.deepcopy(component)
        isolated.to_empty(device="meta")

        direct = ideal_thin_lens(
            field,
            grid=field.grid,
            focal_length=9.0e-6,
            lens_center=(0.35e-6, -0.2e-6),
        )
        delegated = isolated(field)

        assert delegated.envelope.shape == direct.envelope.shape
        assert delegated.envelope.dtype is direct.envelope.dtype
        assert delegated.envelope.device.type == "meta"
        assert direct.envelope.device.type == "meta"

    def test_function_and_component_preserve_the_same_focal_gradient(
        self,
    ) -> None:
        """
        两种入口都保留用户焦距 Parameter 的同一梯度行为
        """

        grid = _grid()
        field = _constant_field(
            grid,
            _monochromatic(),
            ConstantMedium(index=1.33),
        )
        direct_focal_length = torch.nn.Parameter(
            torch.tensor(9.0e-6, dtype=torch.float64),
        )
        component_focal_length = torch.nn.Parameter(
            direct_focal_length.detach().clone(),
        )
        component = IdealThinLens(
            grid=grid,
            focal_length=component_focal_length,
            lens_center=(0.35e-6, -0.2e-6),
        )

        direct = ideal_thin_lens(
            field,
            grid=grid,
            focal_length=direct_focal_length,
            lens_center=(0.35e-6, -0.2e-6),
        )
        delegated = component(field)
        direct_gradient = torch.autograd.grad(
            direct.envelope.real.sum(),
            direct_focal_length,
        )[0]
        delegated_gradient = torch.autograd.grad(
            delegated.envelope.real.sum(),
            component_focal_length,
        )[0]

        assert component.focal_length is component_focal_length
        assert torch.equal(delegated.envelope, direct.envelope)
        assert torch.equal(delegated_gradient, direct_gradient)


class TestIdealThinLensPhysicalInvariants:
    """
    证据层 1：物理不变量
    """

    def test_quadratic_phase_preserves_envelope_magnitude(self) -> None:
        """理想薄透镜 ⇒ 包络模逐点不变（仅二次相位，振幅模不变）
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        element = IdealThinLens(grid=grid, focal_length=8.0e-6)
        output = element(field)
        assert torch.allclose(
            output.envelope.abs(),
            field.envelope.abs(),
            atol=1e-7,
        )

    def test_owns_no_pupil_propagation_or_sensor(self) -> None:
        """理想薄透镜不拥有光瞳、传播或传感器（规约硬性：无任何子元件组合）
        """
        grid = _grid()
        element = IdealThinLens(grid=grid, focal_length=8.0e-6)
        # 唯一私有子模块只负责 PyTorch 网格状态生命周期，不执行任何光学动作
        assert set(dict(element.named_modules())) == {
            "",
            "_grid_state",
        }
        children = dict(element.named_children())
        assert set(children) == {"_grid_state"}

    def test_phase_depends_on_focal_length(self) -> None:
        """不同焦距 ⇒ 输出相位不同（焦距依赖不变量）
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        element_short = IdealThinLens(grid=grid, focal_length=6.0e-6)
        element_long = IdealThinLens(grid=grid, focal_length=12.0e-6)
        assert not torch.allclose(
            element_short(field).envelope,
            element_long(field).envelope,
            atol=1e-6,
        )

    def test_phase_depends_on_lens_center(self) -> None:
        """不同透镜中心 ⇒ 输出相位不同（中心依赖不变量）
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        element_centered = IdealThinLens(grid=grid, focal_length=8.0e-6)
        element_offset = IdealThinLens(
            grid=grid,
            focal_length=8.0e-6,
            lens_center=(0.4e-6, 0.0),
        )
        assert not torch.allclose(
            element_centered(field).envelope,
            element_offset(field).envelope,
            atol=1e-6,
        )

    def test_phase_depends_on_field_medium(self) -> None:
        """同一透镜作用于不同介质光场 ⇒ 输出相位不同（介质依赖不变量）

        规约"理想薄透镜"显式要求介质依赖。n(λ) 进入相位。
        """
        grid = _grid()
        spectrum = _monochromatic()
        vacuum_field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        medium_field = _constant_field(
            grid,
            spectrum,
            ConstantMedium(index=1.5),
            amplitude=1.0,
        )
        element = IdealThinLens(grid=grid, focal_length=8.0e-6)
        assert not torch.allclose(
            element(vacuum_field).envelope,
            element(medium_field).envelope,
            atol=1e-6,
        )

    def test_path_reference_preserved(self) -> None:
        """纯相位透镜不移动光程参考 anchor（规约光程参考行为）
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        element = IdealThinLens(grid=grid, focal_length=8.0e-6)
        output = element(field)
        assert output.path_reference == field.path_reference

    def test_zero_focal_length_rejected(self) -> None:
        """零焦距须以稳定身份拒绝（迁移源拒绝 == 0）
        """
        grid = _grid()
        with pytest.raises(ValueError, match="ideal_thin_lens_focal_length_invalid"):
            IdealThinLens(grid=grid, focal_length=0.0)

    def test_single_precision_focal_length_tensor_rejected(self) -> None:
        """单精度张量焦距须以稳定身份拒绝，而非静默提升为 float64（固定双精度核）
        """
        grid = _grid()
        with pytest.raises(
            ValueError,
            match="ideal_thin_lens_focal_length_invalid",
        ):
            IdealThinLens(
                grid=grid,
                focal_length=torch.tensor(8.0e-6, dtype=torch.float32),
            )

    def test_single_precision_focal_length_parameter_rejected(self) -> None:
        """
        单精度焦距 Parameter 以焦距拥有者身份拒绝
        """

        with pytest.raises(
            ValueError,
            match="ideal_thin_lens_focal_length_invalid",
        ):
            IdealThinLens(
                grid=_grid(),
                focal_length=torch.nn.Parameter(
                    torch.tensor(8.0e-6, dtype=torch.float32),
                ),
            )

    def test_focal_length_registration_preserves_fixed_double_identity(
        self,
    ) -> None:
        """
        Python 焦距物化为 float64，Parameter 焦距保持原身份
        """

        previous_default = torch.get_default_dtype()
        try:
            torch.set_default_dtype(torch.float32)
            fixed_lens = IdealThinLens(grid=_grid(), focal_length=8.0e-6)
        finally:
            torch.set_default_dtype(previous_default)
        focal_length = torch.nn.Parameter(
            torch.tensor(8.0e-6, dtype=torch.float64),
        )
        trainable_lens = IdealThinLens(
            grid=_grid(),
            focal_length=focal_length,
        )

        assert fixed_lens.focal_length.dtype is torch.float64
        assert trainable_lens.focal_length is focal_length

    @pytest.mark.parametrize(
        "trainable_center",
        (
            torch.nn.Parameter(torch.tensor(0.0, dtype=torch.float64)),
            torch.tensor(
                0.0,
                dtype=torch.float64,
                requires_grad=True,
            ),
        ),
    )
    def test_fixed_lens_center_rejects_trainable_tensor(
        self,
        trainable_center: torch.Tensor,
    ) -> None:
        """
        固定透镜中心拒绝会在 Buffer 注册时丢失可训练身份的张量
        """

        with pytest.raises(
            ValueError,
            match="ideal_thin_lens_center_trainable",
        ):
            IdealThinLens(
                grid=_grid(),
                focal_length=8.0e-6,
                lens_center=(trainable_center, 0.0),
            )

    def test_grid_mismatch_rejected(self) -> None:
        """输入光场网格与透镜注册网格不一致须以稳定身份拒绝
        """
        grid = _grid()
        other_grid = _grid(counts=(9, 7))
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum)
        element = IdealThinLens(grid=other_grid, focal_length=8.0e-6)
        with pytest.raises(ValueError, match="ideal_thin_lens_grid_mismatch"):
            element(field)


class TestIdealThinLensCenterFixedDoubleAdmission:
    """
    透镜中心在函数与组件边界保持固定双精度、固定几何
    """

    @pytest.mark.parametrize("center_index", (0, 1), ids=("center_y", "center_x"))
    @pytest.mark.parametrize(
        "invalid_coordinate",
        (
            torch.tensor(0.0, dtype=torch.float32),
            torch.tensor(0.0, dtype=torch.complex128),
            torch.tensor(float("nan"), dtype=torch.float64),
            torch.tensor([0.0], dtype=torch.float64),
            True,
        ),
        ids=("float32", "complex", "nonfinite", "nonscalar", "bool"),
    )
    def test_invalid_coordinate_rejected_by_function_and_component(
        self,
        center_index: int,
        invalid_coordinate: object,
    ) -> None:
        """
        任一中心分量不满足 exact-float64 固定标量时都以同一身份拒绝
        """
        grid = _grid()
        field = _constant_field(grid, _monochromatic())
        center: list[object] = [0.0, 0.0]
        center[center_index] = invalid_coordinate
        lens_center = tuple(center)
        with pytest.raises(ValueError, match="ideal_thin_lens_center_invalid"):
            IdealThinLens(
                grid=grid,
                focal_length=8.0e-6,
                lens_center=lens_center,  # type: ignore[arg-type]
            )
        with pytest.raises(ValueError, match="ideal_thin_lens_center_invalid"):
            ideal_thin_lens(
                field,
                grid=grid,
                focal_length=8.0e-6,
                lens_center=lens_center,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "trainable_coordinate",
        (
            torch.nn.Parameter(torch.tensor(0.0, dtype=torch.float64)),
            torch.tensor(0.0, dtype=torch.float64, requires_grad=True),
        ),
        ids=("parameter", "requires_grad"),
    )
    def test_direct_function_rejects_trainable_center(
        self,
        trainable_coordinate: torch.Tensor,
    ) -> None:
        """
        函数入口保留固定中心的独立 trainable 错误身份
        """
        grid = _grid()
        field = _constant_field(grid, _monochromatic())
        with pytest.raises(
            ValueError,
            match="ideal_thin_lens_center_trainable",
        ):
            ideal_thin_lens(
                field,
                grid=grid,
                focal_length=8.0e-6,
                lens_center=(trainable_coordinate, 0.0),
            )

    def test_float64_center_tensors_are_registered_without_conversion(self) -> None:
        """
        两个合格张量以原对象和原设备注册；Python 坐标才物化为 float64
        """
        center_y = torch.tensor(0.35e-6, dtype=torch.float64)
        center_x = torch.tensor(-0.2e-6, dtype=torch.float64)
        from_tensors = IdealThinLens(
            grid=_grid(),
            focal_length=8.0e-6,
            lens_center=(center_y, center_x),
        )
        from_python = IdealThinLens(
            grid=_grid(),
            focal_length=8.0e-6,
            lens_center=(0.35e-6, -0.2e-6),
        )
        assert from_tensors.lens_center_y is center_y
        assert from_tensors.lens_center_x is center_x
        assert from_python.lens_center_y.dtype is torch.float64
        assert from_python.lens_center_x.dtype is torch.float64

    def test_module_dtype_drifted_center_rejected_before_phase_arithmetic(
        self,
    ) -> None:
        """
        ``module.to(float32)`` 漂移的中心经公共函数消费时稳定拒绝
        """
        grid = _grid()
        field = _constant_field(grid, _monochromatic())
        component = IdealThinLens(
            grid=grid,
            focal_length=8.0e-6,
            lens_center=(0.35e-6, -0.2e-6),
        )
        component.to(dtype=torch.float32)
        with pytest.raises(ValueError, match="ideal_thin_lens_center_invalid"):
            component(field)

    def test_meta_float64_center_accepted_and_float32_rejected(self) -> None:
        """
        meta 中心只校验结构与 dtype，不读取不可读数值
        """
        real_field = _constant_field(_grid(), _monochromatic())
        field = OpticalField(
            envelope=torch.empty_like(real_field.envelope, device="meta"),
            grid=real_field.grid.to(device="meta", dtype=torch.float64),
            spectrum=real_field.spectrum,
            polarization_representation=real_field.polarization_representation,
            medium=real_field.medium,
            normalization=real_field.normalization,
            path_reference=real_field.path_reference,
        )
        accepted = ideal_thin_lens(
            field,
            grid=field.grid,
            focal_length=8.0e-6,
            lens_center=(
                torch.tensor(0.0, dtype=torch.float64, device="meta"),
                torch.tensor(0.0, dtype=torch.float64, device="meta"),
            ),
        )
        assert accepted.envelope.device.type == "meta"
        with pytest.raises(ValueError, match="ideal_thin_lens_center_invalid"):
            ideal_thin_lens(
                field,
                grid=field.grid,
                focal_length=8.0e-6,
                lens_center=(
                    torch.tensor(0.0, dtype=torch.float32, device="meta"),
                    torch.tensor(0.0, dtype=torch.float64, device="meta"),
                ),
            )

    @pytest.mark.cuda
    def test_cuda_float64_center_remains_device_local(self) -> None:
        """
        原生 CUDA 上两个中心 Buffer 保留用户设备并由组件直接消费
        """
        grid = _grid()
        field = _constant_field(
            grid,
            _monochromatic(),
            device="cuda",
        )
        center_y = torch.tensor(0.35e-6, dtype=torch.float64, device="cuda")
        center_x = torch.tensor(-0.2e-6, dtype=torch.float64, device="cuda")
        component = IdealThinLens(
            grid=grid,
            focal_length=torch.tensor(8.0e-6, dtype=torch.float64, device="cuda"),
            lens_center=(center_y, center_x),
        )
        output = component(field)
        assert component.lens_center_y is center_y
        assert component.lens_center_x is center_x
        assert output.envelope.device.type == "cuda"

@pytest.mark.cuda
def test_ideal_thin_lens_public_action_matches_cpu_on_cuda() -> None:
    """
    IdealThinLens 公共动作在 CUDA 上保持与 CPU 相同的复包络

    相位因子 exp(-i·k(λ,n)·r²/(2f)) 经周期化后由三角核求值，属
    Issue 16 预算的超越方程族，故取 rtol=atol=5e-12。
    """

    grid = _grid()
    spectrum = _multispectral()
    medium = ConstantMedium(index=1.33)
    cpu_field = _constant_field(grid, spectrum, medium)
    cuda_field = _constant_field(grid, spectrum, medium, device="cuda")

    cpu_output = ideal_thin_lens(
        cpu_field,
        grid=grid,
        focal_length=9.0e-6,
        lens_center=(0.35e-6, -0.2e-6),
    )
    cuda_output = ideal_thin_lens(
        cuda_field,
        grid=grid,
        focal_length=9.0e-6,
        lens_center=(0.35e-6, -0.2e-6),
    )

    torch.testing.assert_close(
        cpu_output.envelope,
        cuda_output.envelope.cpu(),
        rtol=5.0e-12,
        atol=5.0e-12,
    )

class TestIndependentReference:
    """
    证据层 2：独立解析参照
    """

    def test_monochromatic_vacuum_matches_independent_quadratic_phase(self) -> None:
        """单色真空：输出须与独立 φ = -k·r²/(2f) 一致（前向标准近轴形式）
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        focal_length = 9.0e-6
        element = IdealThinLens(grid=grid, focal_length=focal_length)
        output = element(field)
        reference = _independent_quadratic_phase(
            field,
            focal_length,
            0.0,
            0.0,
            torch.float64,
        ).unsqueeze(1)
        assert torch.allclose(output.envelope, reference, atol=1e-7)

    def test_offcenter_lens_matches_independent_quadratic_phase(self) -> None:
        """离心透镜：输出须与独立 φ = -k·((y-cy)²+(x-cx)²)/(2f) 一致
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0)
        focal_length = 9.0e-6
        center = (0.35e-6, -0.2e-6)
        element = IdealThinLens(
            grid=grid,
            focal_length=focal_length,
            lens_center=center,
        )
        output = element(field)
        reference = _independent_quadratic_phase(
            field,
            focal_length,
            center[0],
            center[1],
            torch.float64,
        ).unsqueeze(1)
        assert torch.allclose(output.envelope, reference, atol=1e-7)

    def test_multispectral_constant_medium_matches(self) -> None:
        """多光谱 + 恒定介质：每光谱分量相位须与独立 -k(λ)·r²/(2f) 一致

        一个透镜 ⇒ 各分量共享同一焦距与中心，相位随 λ 与介质变化。
        """
        grid = _grid()
        spectrum = _multispectral()
        medium = ConstantMedium(index=1.33)
        field = _constant_field(grid, spectrum, medium, amplitude=1.0)
        focal_length = 1.1e-5
        element = IdealThinLens(grid=grid, focal_length=focal_length)
        output = element(field)
        reference = _independent_quadratic_phase(
            field,
            focal_length,
            0.0,
            0.0,
            torch.float64,
        ).unsqueeze(1)
        assert output.envelope.shape == reference.shape
        assert torch.allclose(output.envelope, reference, atol=1e-7)


class TestGradientEvidence:
    """
    证据层 3：梯度证据（双精度，经元件→实部约减）
    """

    def test_gradcheck_on_trainable_focal_length(self) -> None:
        """对可训练焦距做 gradcheck（经透镜→包络实部和）

        焦距为 float64 叶子 Parameter，由元件直接持有；gradcheck 就地扰动该同一
        Parameter 对象。恒定介质 n=1.5 进入相位（固定，无梯度）；光场包络常幅零相位
        （无梯度）。损失取输出包络实部和（依赖相位 via cos），保证非零梯度且处处可微。

        注：相位对焦距敏感（中心像素 r²≈(1.5e-6)²，dφ/df ≈ k·r²/(2f²) 量级
        1e-2 rad/m），gradcheck 默认 eps=1e-6 m 跨越的相位变化远小于 1 rad，落在
        线性区内，无需缩 eps；但为稳健起见显式给出 eps。
        """
        grid = _grid()
        spectrum = _monochromatic()
        medium = ConstantMedium(index=1.5)
        field = _constant_field(grid, spectrum, medium, amplitude=1.0)
        focal_length = torch.nn.Parameter(torch.tensor(1.0e-5, dtype=torch.float64))
        element = IdealThinLens(grid=grid, focal_length=focal_length)

        def run(focal_value: torch.Tensor) -> torch.Tensor:
            """
            返回当前焦距下的输出包络实部和（依赖相位 via cos）
            """
            return element(field).envelope.real.sum()

        assert torch.autograd.gradcheck(
            run,
            (focal_length,),
            eps=1e-8,
            raise_exception=True,
        )


class TestIdealThinLensGridState:
    """
    薄透镜的配准网格参加标准状态保存与恢复
    """

    def test_state_dict_restores_registered_grid(self) -> None:
        """
        加载状态后公共 grid 属性从当前注册张量重建
        """
        source_grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(
                torch.tensor(1.0e-6, dtype=torch.float64),
                torch.tensor(1.5e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(-2.0e-6, dtype=torch.float64),
                torch.tensor(-3.0e-6, dtype=torch.float64),
            ),
        )
        restored_grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(
                torch.tensor(2.0e-6, dtype=torch.float64),
                torch.tensor(2.5e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(0.0, dtype=torch.float64),
                torch.tensor(0.0, dtype=torch.float64),
            ),
        )
        source = IdealThinLens(grid=source_grid, focal_length=1.0e-3)
        restored = IdealThinLens(grid=restored_grid, focal_length=1.0e-3)

        restored.load_state_dict(source.state_dict())

        assert restored.grid.is_physically_equivalent_to(source.grid)


class TestHostedExecution:
    """
    托管端到端：PlaneWave → 光瞳 → 理想薄透镜 → IntensityDetection

    透镜相位即便不传播也写入光场包络（规约"理想薄透镜"：仅二次相位元件）。
    """

    def test_hosted_lens_phase_appears_without_propagation(self) -> None:
        """托管理想薄透镜 ⇒ 包络相位非零（透镜相位写入光场），振幅模不变

        PlaneWave（单位振幅、前向）→ 托管理想薄透镜。无传播时，透镜二次相位仍出现在
        包络角度上；模不变（仅相位）。IntensityDetection 输出光强与无透镜时一致。
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
            )
        )
        lens = workstation.host(IdealThinLens(grid=grid, focal_length=9.0e-6))
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        lensed = lens(field)
        # 透镜相位须写入包络：除原点外至少有非零相位
        phases = lensed.envelope.angle()
        finite_phases = phases[phases.abs() > 1e-6]
        assert finite_phases.numel() > 0
        # 模仍为单位（仅相位）
        assert torch.allclose(
            lensed.envelope.abs(),
            torch.ones_like(lensed.envelope.abs()),
            atol=1e-5,
        )
        # 光强不变（|E|² 相位不变）
        intensity = detection(lensed)
        expected = torch.full(grid.sample_counts, 1.0, dtype=torch.float64)
        assert torch.allclose(intensity.values, expected, atol=1e-5)

    def test_hosted_pupil_then_lens_preserves_aperture(self) -> None:
        """PlaneWave → 圆光瞳 → 理想薄透镜：孔径形状保持，透镜相位出现在透射区

        光瞳限光到圆孔径；透镜对透射区施加二次相位。IntensityDetection 看到的光强仍为
        孔径形状（透镜不改光强），且包络在透射区具非零相位。
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
            )
        )
        pupil = workstation.host(CircularPupil(grid=_grid(), radius=1.3e-6))
        lens = workstation.host(IdealThinLens(grid=_grid(), focal_length=9.0e-6))
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        pupil_field = pupil(field)
        lensed = lens(pupil_field)
        intensity = detection(lensed)
        # 光强须仍为圆孔径形状（透镜仅相位，不改光强分布）
        coordinate_y, coordinate_x = _grid_coordinates(grid)
        expected_mask = (
            coordinate_y[:, None] ** 2 + coordinate_x[None, :] ** 2
        ) <= (1.3e-6) ** 2
        expected = expected_mask.to(torch.float64)
        assert torch.allclose(intensity.values, expected, atol=1e-6)
        # 透射区须出现非零透镜相位
        transmitted_region = expected_mask.unsqueeze(0).unsqueeze(0)
        transmitted_phases = lensed.envelope.angle()[transmitted_region]
        assert transmitted_phases.abs().max().item() > 1e-6
