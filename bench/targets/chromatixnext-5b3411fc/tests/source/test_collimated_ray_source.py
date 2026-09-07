
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next import install_state
from chromatix_next.errors import OpticalTypeError, OpticalValueError
from chromatix_next.optics import (
    ConstantMedium,
    Polarization,
    RayBundle,
    SellmeierMedium,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics._meta_inference import _meta_inference
from chromatix_next.optics.ray_bundle import RAY_STATUS_ACTIVE
from chromatix_next.optics.source import CollimatedRaySource


def _grid(
    counts: tuple[int, int] = (3, 4),
    spacing: tuple[float, float] = (1.0, 2.0),
) -> SpatialGrid:
    # 中心对齐的小型横向网格
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=spacing,
    )


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    # 单色光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _independent_launch_positions(
    grid: SpatialGrid,
    origin: tuple[float, float, float],
    tangent_x: tuple[float, float, float],
    tangent_y: tuple[float, float, float],
    real_dtype: torch.dtype,
) -> torch.Tensor:
    counts_y, counts_x = grid.sample_counts
    spacing_y, spacing_x = grid.signed_spacing
    first_y, first_x = grid.first_sample_position
    indices_y = torch.arange(counts_y, dtype=torch.float64)
    indices_x = torch.arange(counts_x, dtype=torch.float64)
    coords_y = (
        first_y.detach().to(dtype=torch.float64)
        + indices_y * spacing_y.detach().to(dtype=torch.float64)
    )
    coords_x = (
        first_x.detach().to(dtype=torch.float64)
        + indices_x * spacing_x.detach().to(dtype=torch.float64)
    )
    origin_tensor = torch.tensor(origin, dtype=torch.float64)
    tangent_x_tensor = torch.tensor(tangent_x, dtype=torch.float64)
    tangent_y_tensor = torch.tensor(tangent_y, dtype=torch.float64)
    positions = []
    for coord_y in coords_y.tolist():
        for coord_x in coords_x.tolist():
            position = (
                origin_tensor
                + coord_x * tangent_x_tensor
                + coord_y * tangent_y_tensor
            )
            positions.append(position)
    return torch.stack(positions, dim=0).to(dtype=real_dtype)


class TestCollimatedSourceRoleContract:
    """
    Source 角色字面量；Assembly/Host 公共路径接纳
    """

    def test_role_is_source_literal(self) -> None:
        """
        CollimatedRaySource 声明唯一不可改写的 source 角色
        """
        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        assert source.role == "source"
        with pytest.raises(AttributeError):
            source.role = "element"  # type: ignore[misc]

    def test_forward_returns_ray_bundle(self) -> None:
        """
        真实前向只产生 RayBundle 强物理值
        """
        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        result = source(_grid())
        assert isinstance(result, RayBundle)


class TestCollimatedSourcePoseValidation:
    """
    发射面基向量校验：单位、正交；ray_power 为正有限标量
    """

    def test_default_pose_yields_plus_z_direction(self) -> None:
        """
        默认切向基生成 +z 发射方向
        """
        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        direction = source._launch_direction()  # noqa: SLF001
        assert torch.allclose(
            direction,
            torch.tensor([0.0, 0.0, 1.0], dtype=direction.dtype),
            atol=1.0e-6,
        )

    def test_non_unit_tangent_x_rejected(self) -> None:
        """
        非单位 launch_tangent_x ⇒ 拒绝；源不静默归一化 authored 物理
        """
        with pytest.raises(OpticalValueError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),

                polarization=Polarization.linear_x(),
                ray_power=1.0,
                launch_tangent_x=(2.0, 0.0, 0.0),
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_launch_tangent_x_not_unit"
        )

    def test_parallel_axes_rejected(self) -> None:
        """
        平行两轴 ⇒ 非正交拒绝
        """
        with pytest.raises(OpticalValueError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),

                polarization=Polarization.linear_x(),
                ray_power=1.0,
                launch_tangent_x=(1.0, 0.0, 0.0),
                launch_tangent_y=(1.0, 0.0, 0.0),
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_launch_basis_not_orthogonal"
        )

    def test_invalid_origin_shape_rejected(self) -> None:
        """
        发射面原点必须是三元实数；其他形状拒绝
        """
        with pytest.raises(OpticalValueError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),

                polarization=Polarization.linear_x(),
                ray_power=1.0,
                launch_origin=(0.0, 0.0),  # type: ignore[arg-type]
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_launch_origin_invalid"
        )

    def test_swapped_basis_yields_minus_z_direction(self) -> None:
        """
        交换切向基后，发射方向反向；姿态决定发射方向
        """
        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=1.0,
            launch_tangent_x=(0.0, 1.0, 0.0),
            launch_tangent_y=(1.0, 0.0, 0.0),
        )
        direction = source._launch_direction()  # noqa: SLF001
        assert torch.allclose(
            direction,
            torch.tensor([0.0, 0.0, -1.0], dtype=direction.dtype),
            atol=1.0e-6,
        )


class TestCollimatedSourcePowerValidation:
    """
    ray_power 校验：正实有限标量
    """

    def test_float32_parameter_rejected_with_owner_identity(self) -> None:
        """
        单精度 ray_power Parameter 在 Source 边界拒绝
        """

        with pytest.raises(OpticalValueError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),
                polarization=Polarization.linear_x(),
                ray_power=torch.nn.Parameter(
                    torch.tensor(1.0, dtype=torch.float32),
                ),
            )
        assert rejected.value.identity == "collimated_ray_source_ray_power_invalid"

    def test_meta_power_parameter_checks_fixed_double_structure(self) -> None:
        """
        Meta 参数只读取结构：float32 拒绝，float64 保留
        """

        with pytest.raises(OpticalValueError):
            CollimatedRaySource(
                spectrum=_monochromatic(),
                polarization=Polarization.linear_x(),
                ray_power=torch.nn.Parameter(
                    torch.empty((), dtype=torch.float32, device="meta"),
                ),
            )
        ray_power = torch.nn.Parameter(
            torch.empty((), dtype=torch.float64, device="meta"),
        )
        source = CollimatedRaySource(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            ray_power=ray_power,
        )
        assert source.ray_power is ray_power

    def test_python_power_materializes_as_fixed_double_buffer(self) -> None:
        """
        Python 功率不受默认 dtype 影响，并物化为 float64 Buffer
        """

        previous_default = torch.get_default_dtype()
        try:
            torch.set_default_dtype(torch.float32)
            source = CollimatedRaySource(
                spectrum=_monochromatic(),
                polarization=Polarization.linear_x(),
                ray_power=1.0,
            )
        finally:
            torch.set_default_dtype(previous_default)

        assert source.ray_power.dtype is torch.float64
        assert source.get_buffer("ray_power") is source.ray_power

    def test_float64_power_parameter_keeps_identity(self) -> None:
        """
        合法可训练功率保持用户 Parameter 身份
        """

        ray_power = torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float64))
        source = CollimatedRaySource(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            ray_power=ray_power,
        )
        assert source.ray_power is ray_power

    @pytest.mark.parametrize(
        "invalid_power",
        (0.0, -1.0, float("nan"), float("inf")),
    )
    def test_non_positive_power_rejected(
        self,
        invalid_power: float,
    ) -> None:
        """
        零、负、非有限 ray_power ⇒ 拒绝
        """
        with pytest.raises(OpticalValueError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),

                polarization=Polarization.linear_x(),
                ray_power=invalid_power,
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_ray_power_invalid"
        )

    def test_complex_power_rejected(self) -> None:
        """
        复数 ray_power ⇒ 拒绝；功率是实数可观测量
        """
        complex_power = torch.nn.Parameter(
            torch.tensor(1.0 + 0.0j, dtype=torch.complex64),
        )
        with pytest.raises(OpticalValueError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),

                polarization=Polarization.linear_x(),
                ray_power=complex_power,
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_ray_power_invalid"
        )

    def test_plain_non_parameter_tensor_power_rejected(self) -> None:
        """
        普通（非 Parameter）张量 ray_power ⇒ 稳定域错误，不泄漏 AssertionError
        """
        plain_tensor_power = torch.tensor(1.25, dtype=torch.float64)
        with pytest.raises(OpticalTypeError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),

                polarization=Polarization.linear_x(),
                ray_power=plain_tensor_power,  # type: ignore[arg-type]
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_ray_power_invalid"
        )

    def test_unsupported_medium_rejected(self) -> None:
        """
        准直光线源只接受真空或恒定折射率介质，可训练色散介质被拒绝
        """
        sellmeier = SellmeierMedium(
            b_coefficients=(1.0,),
            c_coefficients=(0.01,),
            wavelength_min=0.4e-6,
            wavelength_max=0.7e-6,
        )
        with pytest.raises(OpticalTypeError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),

                polarization=Polarization.linear_x(),
                medium=sellmeier,
                ray_power=1.0,
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_medium_unsupported"
        )


class TestCollimatedSourceForwardContract:
    """
    forward 输出与独立 analytic 参考一致；轴布局与 dtype 满足 RayBundle 契约
    """

    def test_position_matches_independent_reference(
        self,
    ) -> None:
        """
        source 输出位置与独立构造的 launch plane 采样逐元素一致
        """
        real_dtype = torch.float64
        grid = _grid()
        origin = (0.1, -0.2, 0.05)
        tangent_x = (1.0, 0.0, 0.0)
        tangent_y = (0.0, 1.0, 0.0)
        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            medium=ConstantMedium(index=1.3),
            launch_origin=origin,
            launch_tangent_x=tangent_x,
            launch_tangent_y=tangent_y,
            ray_power=2.5,
        )
        bundle = source(grid)
        expected = _independent_launch_positions(
            grid,
            origin=origin,
            tangent_x=tangent_x,
            tangent_y=tangent_y,
            real_dtype=real_dtype,
        )
        assert bundle.position.dtype is real_dtype
        expected_ray_count = grid.sample_counts[0] * grid.sample_counts[1]
        assert bundle.position.shape == (1, expected_ray_count, 3)
        assert torch.allclose(
            bundle.position[0],
            expected,
            atol=2.0 * torch.finfo(real_dtype).eps,
        )

    def test_rotated_pose_maps_each_grid_coordinate_to_its_authored_tangent(
        self,
    ) -> None:
        """
        非中心各向异性网格在旋转姿态下保持 x/y 坐标的独立切向映射
        """

        real_dtype = torch.float64
        grid = SpatialGrid(
            sample_counts=(2, 3),
            sample_spacing=(0.7e-3, 1.3e-3),
            first_sample_position=(0.35e-3, -0.8e-3),
        )
        azimuth = math.radians(31.0)
        tilt = math.radians(23.0)
        tangent_x = (
            math.cos(tilt) * math.cos(azimuth),
            math.cos(tilt) * math.sin(azimuth),
            -math.sin(tilt),
        )
        tangent_y = (-math.sin(azimuth), math.cos(azimuth), 0.0)
        origin = (1.2e-3, -0.7e-3, 0.9e-3)
        source = CollimatedRaySource(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            medium=ConstantMedium(index=1.2),
            launch_origin=origin,
            launch_tangent_x=tangent_x,
            launch_tangent_y=tangent_y,
            ray_power=2.5,
        )

        bundle = source(grid)
        expected = _independent_launch_positions(
            grid,
            origin=origin,
            tangent_x=tangent_x,
            tangent_y=tangent_y,
            real_dtype=real_dtype,
        )

        assert grid.sample_counts == (2, 3)
        assert bundle.position.shape == (1, 6, 3)
        assert torch.allclose(
            bundle.position[0],
            expected,
            atol=2.0 * torch.finfo(real_dtype).eps,
        )
        expected_x_step = (
            grid.signed_spacing[1].to(dtype=real_dtype)
            * torch.tensor(tangent_x, dtype=real_dtype)
        )
        expected_y_step = (
            grid.signed_spacing[0].to(dtype=real_dtype)
            * torch.tensor(tangent_y, dtype=real_dtype)
        )
        assert torch.allclose(
            expected[1] - expected[0],
            expected_x_step,
            atol=2.0 * torch.finfo(real_dtype).eps,
        )
        assert torch.allclose(
            expected[3] - expected[0],
            expected_y_step,
            atol=2.0 * torch.finfo(real_dtype).eps,
        )

    def test_direction_is_cross_product_of_axes(self) -> None:
        """
        发射方向由两个切向基的叉积得到，所有 ray 共享该方向
        """
        tangent_x = (0.0, 0.0, 1.0)
        tangent_y = (0.0, 1.0, 0.0)
        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=1.0,
            launch_tangent_x=tangent_x,
            launch_tangent_y=tangent_y,
        )
        bundle = source(_grid())
        expected_direction = torch.tensor(
            [
                tangent_x[1] * tangent_y[2] - tangent_x[2] * tangent_y[1],
                tangent_x[2] * tangent_y[0] - tangent_x[0] * tangent_y[2],
                tangent_x[0] * tangent_y[1] - tangent_x[1] * tangent_y[0],
            ],
            dtype=bundle.direction.dtype,
        )
        assert torch.allclose(bundle.direction[0, 0], expected_direction)
        # 共享方向：所有 ray 方向一致
        assert torch.allclose(
            bundle.direction,
            bundle.direction[0:1, 0:1].expand_as(bundle.direction),
        )

    def test_power_is_per_ray_and_optical_path_starts_at_zero(self) -> None:
        """
        每 ray 功率等于 ray_power；光程从零起累加；状态全 active
        """
        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=3.0,
        )
        bundle = source(_grid())
        assert torch.allclose(bundle.power, torch.full_like(bundle.power, 3.0))
        assert torch.allclose(
            bundle.optical_path,
            torch.zeros_like(bundle.optical_path),
        )
        assert torch.equal(
            bundle.status,
            torch.full_like(bundle.status, RAY_STATUS_ACTIVE),
        )

    def test_polychromatic_spectrum_spans_spectrum_axis(self) -> None:
        """
        多波长光谱沿 spectrum 轴展开；方向与功率共享
        """
        spectrum = Spectrum(
            wavelengths=(1.0e-6, 2.0e-6, 3.0e-6),
            weights=(0.2, 0.3, 0.5),
        )
        source = CollimatedRaySource(
            spectrum=spectrum,

            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        bundle = source(_grid())
        assert bundle.spectral_count == 3
        assert bundle.position.shape == (3, 12, 3)
        assert bundle.direction.shape == (3, 12, 3)

    def test_forward_on_meta_preserves_shape_and_dtype(self) -> None:
        """
        meta 设备上前向返回同形同 dtype RayBundle（供 Workstation 预检推导）
        """
        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        grid = _grid()
        with _meta_inference((source,)) as sandbox:
            bundle = sandbox.module(source)(grid)
        assert bundle.position.is_meta
        assert bundle.position.shape == (1, 12, 3)
        assert bundle.position.dtype is torch.float64
        assert bundle.optical_path.dtype is torch.float64
        assert bundle.status.dtype is torch.uint8

    @pytest.mark.cuda
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
    def test_public_source_matches_cpu_on_cuda(self) -> None:
        """
        公共源在 CUDA 上保持与 CPU 相同的逐 ray 光线束张量
        预算依据 Issue 16 方程预算族的 ray 类上界收紧为逐位相等：
        发射几何是原点加坐标切向线性组合、方向是切向基叉积、
        偏振向量是 Jones 分量在发射基上的线性嵌入、常数介质折射率
        为解析常数填充，均为 IEEE 双精度乘加的逐位确定运算。
        """
        azimuth = math.radians(31.0)
        tilt = math.radians(23.0)
        tangent_x = (
            math.cos(tilt) * math.cos(azimuth),
            math.cos(tilt) * math.sin(azimuth),
            -math.sin(tilt),
        )
        tangent_y = (-math.sin(azimuth), math.cos(azimuth), 0.0)
        grid = SpatialGrid(
            sample_counts=(2, 3),
            sample_spacing=(0.7e-3, 1.3e-3),
            first_sample_position=(0.35e-3, -0.8e-3),
        )
        spectrum = Spectrum(
            wavelengths=(1.0e-6, 2.0e-6, 3.0e-6),
            weights=(0.2, 0.3, 0.5),
        )

        def make_source() -> CollimatedRaySource:
            # 以同一 authoring 参数构造源，仅宿主设备不同
            return CollimatedRaySource(
                spectrum=spectrum,
                polarization=Polarization.linear_x(),
                medium=ConstantMedium(index=1.2),
                launch_origin=(1.2e-3, -0.7e-3, 0.9e-3),
                launch_tangent_x=tangent_x,
                launch_tangent_y=tangent_y,
                ray_power=2.5,
            )

        cpu_bundle = make_source()(grid)
        cuda_bundle = make_source().cuda()(grid)

        for quantity in (
            "position",
            "direction",
            "polarization_vector",
            "power",
            "refractive_index",
            "optical_path",
            "status",
        ):
            torch.testing.assert_close(
                getattr(cpu_bundle, quantity),
                getattr(cuda_bundle, quantity).cpu(),
                rtol=0.0,
                atol=0.0,
            )


class TestCollimatedSourceGradient:
    """
    可训练 ray_power 经源→光线束链路保持 autograd；解析梯度与有限差分一致
    """

    def test_power_gradient_is_one_per_ray(self) -> None:
        """
        总功率对 ray_power 的梯度等于光谱数乘以光线数
        """
        ray_power = torch.nn.Parameter(torch.tensor(1.25, dtype=torch.float64))
        spectrum = Spectrum(
            wavelengths=(1.0e-6, 2.0e-6),
            weights=(0.5, 0.5),
        )
        source = CollimatedRaySource(
            spectrum=spectrum,

            polarization=Polarization.linear_x(),
            ray_power=ray_power,
        )
        bundle = source(_grid())
        bundle.power.sum().backward()
        assert ray_power.grad is not None
        assert bundle.power.shape == (2, 12)
        assert torch.allclose(
            ray_power.grad,
            torch.tensor(24.0, dtype=torch.float64),
        )

    def test_position_does_not_depend_on_ray_power(self) -> None:
        """
        位置由固定 pose buffer 派生，与可训练 ray_power 在计算图上独立
        """
        ray_power = torch.nn.Parameter(torch.tensor(0.7, dtype=torch.float64))
        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=ray_power,
        )
        bundle = source(_grid())
        assert bundle.position.requires_grad is False
        assert bundle.direction.requires_grad is False
        assert bundle.optical_path.requires_grad is False
        # power 依赖于 ray_power；它把 ray_power 的训练图传到下游光学计算
        assert bundle.power.requires_grad is True

    def test_finite_difference_matches_autograd(self) -> None:
        """
        中心差分与 autograd 对 ray_power 一致（光滑路径）
        """
        grid = _grid()
        ray_power = torch.nn.Parameter(
            torch.tensor(1.0, dtype=torch.float64),
        )

        def _sum_of_squared_power(value: float) -> float:
            # 在独立源实例上累加功率，供中心差分与自动微分比对
            ray_power_copy = torch.nn.Parameter(
                torch.tensor(value, dtype=torch.float64)
            )
            source = CollimatedRaySource(
                spectrum=_monochromatic(),

                polarization=Polarization.linear_x(),
                ray_power=ray_power_copy,
            )
            bundle = source(grid)
            return float(bundle.power.sum().detach())

        step = 1.0e-6
        central = (
            _sum_of_squared_power(1.0 + step)
            - _sum_of_squared_power(1.0 - step)
        ) / (2.0 * step)
        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=ray_power,
        )
        bundle = source(grid)
        bundle.power.sum().backward()
        assert ray_power.grad is not None
        autograd = float(ray_power.grad.detach())
        assert math.isclose(autograd, central, rel_tol=1.0e-5, abs_tol=1.0e-5)


def test_rotated_launch_pose_embeds_jones_components_in_authored_basis() -> None:
    """
    旋转发射面把 Jones 分量嵌入作者基底，并保持单位范数与横向性
    """

    rotation_radians = math.radians(35.0)
    tangent_x = (
        math.cos(rotation_radians),
        math.sin(rotation_radians),
        0.0,
    )
    tangent_y = (
        -math.sin(rotation_radians),
        math.cos(rotation_radians),
        0.0,
    )
    source = CollimatedRaySource(
        spectrum=_monochromatic(),
        polarization=Polarization.left_circular(),
        launch_tangent_x=tangent_x,
        launch_tangent_y=tangent_y,
        ray_power=1.0,
    )
    bundle = source(_grid(counts=(1, 1)))
    circular_scale = 1.0 / math.sqrt(2.0)
    expected = circular_scale * (
        torch.tensor(tangent_x, dtype=torch.complex128)
        - 1j * torch.tensor(tangent_y, dtype=torch.complex128)
    )
    actual = bundle.polarization_vector[0, 0]

    assert torch.allclose(actual, expected, atol=1.0e-15, rtol=0.0)
    assert torch.allclose(
        actual.abs().square().sum(),
        torch.ones((), dtype=torch.float64),
        atol=1.0e-15,
        rtol=0.0,
    )
    assert torch.allclose(
        (actual * bundle.direction[0, 0]).sum(),
        torch.zeros((), dtype=torch.complex128),
        atol=1.0e-15,
        rtol=0.0,
    )


class TestCollimatedSourceStateLoad:
    """
    state_dict round-trip 保留物理元数据；命名载荷与计算 Buffer 同步
    """

    def test_state_dict_round_trip_preserves_spectrum(self) -> None:
        """
        序列化与载入保留光谱；medium 身份结构同构
        """
        spectrum = Spectrum(
            wavelengths=(0.5e-6, 0.6e-6),
            weights=(0.5, 0.5),
        )
        source = CollimatedRaySource(
            spectrum=spectrum,

            polarization=Polarization.linear_x(),
            medium=ConstantMedium(index=1.4),
            ray_power=1.5,
        )
        state = source.state_dict()
        round_trip = CollimatedRaySource(
            spectrum=Spectrum.monochromatic(0.55e-6),

            polarization=Polarization.linear_x(),
            medium=ConstantMedium(index=1.4),
            ray_power=1.0,
        )
        install_state(round_trip, state)
        assert (
            round_trip._spectrum_value.wavelengths  # noqa: SLF001
            == spectrum.wavelengths
        )
        assert (
            round_trip._spectrum_value.weights  # noqa: SLF001
            == spectrum.weights
        )
