
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next.optics import (
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
from chromatix_next.optics.element import (
    CircularPupil,
    SquarePupil,
    circular_pupil,
    square_pupil,
)
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


def _grid(
    counts: tuple[int, int] = (7, 7),
    spacing: tuple[float, float] = (0.5e-6, 0.5e-6),
) -> SpatialGrid:
    # 构造中心对齐的横向网格（样本物理对齐原点，便于对称孔径）
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=spacing,
    )


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    # 构造单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


@pytest.mark.parametrize(
    ("action", "action_arguments"),
    (
        (circular_pupil, {"radius": 1.0e-6}),
        (square_pupil, {"width": 2.0e-6}),
    ),
    ids=("circular", "square"),
)
@pytest.mark.parametrize(
    "polarization",
    (Polarization.scalar(), Polarization.transverse(), Polarization.full()),
    ids=("scalar", "transverse", "full"),
)
def test_pupil_preserves_field_representation_and_frame(
    action: object,
    action_arguments: dict[str, float],
    polarization: Polarization,
) -> None:
    """
    光瞳只改变透射并保留输入光场表征与参考框架
    """
    grid = _grid()
    field = PlaneWave(
        spectrum=_monochromatic(),
        polarization=polarization,
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )(grid)

    output = action(field, grid=grid, **action_arguments)  # type: ignore[operator]

    assert output.polarization_representation is polarization.representation
    assert output.grid.is_physically_equivalent_to(field.grid)
    assert output.spectrum == field.spectrum
    assert output.medium is field.medium
    assert output.normalization is field.normalization
    assert output.path_reference == field.path_reference


def _constant_field(
    grid: SpatialGrid,
    spectrum: Spectrum,
    amplitude: float = 1.0,
    *,
    dtype: torch.dtype = torch.complex128,
    device: torch.device | str | None = None,
) -> OpticalField:
    # 构造均匀常幅、零相位输入光场（直接控制包络，避免与源耦合）
    counts_y, counts_x = grid.sample_counts
    envelope = torch.full(
        (spectrum.count, 1, counts_y, counts_x),
        complex(amplitude, 0.0),
        dtype=dtype,
        device=device,
    )
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=spectrum,
        polarization_representation=(Polarization.scalar()).representation,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


class TestPupilFunctionComponentDuality:
    """
    圆形与方形光瞳的函数和 Component 共享同一物理实现
    """

    @pytest.mark.parametrize(
        ("function", "component_type", "physics"),
        (
            (
                circular_pupil,
                CircularPupil,
                {"radius": 1.0e-6},
            ),
            (
                square_pupil,
                SquarePupil,
                {"width": 2.0e-6},
            ),
        ),
    )
    def test_function_and_component_return_the_same_field(
        self,
        function: object,
        component_type: type[CircularPupil] | type[SquarePupil],
        physics: dict[str, float],
    ) -> None:
        """
        真实输入下函数与 Component 返回逐点相同的光场
        """
        grid = _grid()
        field = _constant_field(grid, _monochromatic())
        functional = function(field, grid=grid, **physics)  # type: ignore[operator]
        component = component_type(  # type: ignore[arg-type]
            grid=grid,
            **physics,
        )(field)

        assert torch.equal(functional.envelope, component.envelope)
        assert functional.grid is component.grid
        assert functional.spectrum is component.spectrum

    @pytest.mark.parametrize(
        ("function", "component_type", "physics"),
        (
            (
                circular_pupil,
                CircularPupil,
                {"radius": 1.0e-6},
            ),
            (
                square_pupil,
                SquarePupil,
                {"width": 2.0e-6},
            ),
        ),
    )
    def test_function_and_component_infer_the_same_meta_result(
        self,
        function: object,
        component_type: type[CircularPupil] | type[SquarePupil],
        physics: dict[str, float],
    ) -> None:
        """
        meta 输入下函数与 Component 保持相同形状和 dtype
        """
        grid = _grid()
        field = _constant_field(
            grid,
            _monochromatic(),
            dtype=torch.complex128,
            device="meta",
        )
        functional = function(field, grid=grid, **physics)  # type: ignore[operator]
        component = component_type(  # type: ignore[arg-type]
            grid=grid,
            **physics,
        )(field)

        assert functional.envelope.device.type == "meta"
        assert component.envelope.device.type == "meta"
        assert functional.envelope.shape == component.envelope.shape
        assert functional.envelope.dtype == component.envelope.dtype

    @pytest.mark.parametrize(
        ("function", "component_type", "physics"),
        (
            (
                circular_pupil,
                CircularPupil,
                {"radius": 1.0e-6},
            ),
            (
                square_pupil,
                SquarePupil,
                {"width": 2.0e-6},
            ),
        ),
    )
    def test_function_and_component_preserve_the_same_input_gradient(
        self,
        function: object,
        component_type: type[CircularPupil] | type[SquarePupil],
        physics: dict[str, float],
    ) -> None:
        """
        光瞳固定几何下两种入口向输入包络传回相同梯度
        """
        grid = _grid()
        functional_field = _constant_field(grid, _monochromatic())
        component_field = _constant_field(grid, _monochromatic())
        functional_field.envelope.requires_grad_()
        component_field.envelope.requires_grad_()

        functional = function(  # type: ignore[operator]
            functional_field,
            grid=grid,
            **physics,
        )
        component = component_type(grid=grid, **physics)(  # type: ignore[arg-type]
            component_field
        )
        functional.envelope.real.sum().backward()
        component.envelope.real.sum().backward()

        assert functional_field.envelope.grad is not None
        assert component_field.envelope.grad is not None
        assert torch.equal(
            functional_field.envelope.grad,
            component_field.envelope.grad,
        )


def _grid_coordinates(grid: SpatialGrid) -> tuple[torch.Tensor, torch.Tensor]:
    # 独立构造网格物理坐标 (y, x)，以米为单位（与迁移源坐标公式一致）
    counts_y, counts_x = grid.sample_counts
    spacing_y, spacing_x = grid.signed_spacing
    first_y, first_x = grid.first_sample_position
    coordinate_y = (
        torch.arange(counts_y, dtype=torch.float64) * float(spacing_y) + float(first_y)
    )
    coordinate_x = (
        torch.arange(counts_x, dtype=torch.float64) * float(spacing_x) + float(first_x)
    )
    return coordinate_y, coordinate_x


class TestCircularPupilPhysicalInvariants:
    """
    证据层 1（圆光瞳）：物理不变量
    """

    def test_transmittance_is_binary_inside_disk(self) -> None:
        """圆光瞳透射为二元 {0,1}，孔径内（(y-cy)²+(x-cx)² ≤ R²）为 1、孔径外为 0
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, amplitude=1.0)
        element = CircularPupil(grid=grid, radius=1.3e-6)
        output = element(field)
        coordinate_y, coordinate_x = _grid_coordinates(grid)
        radius_squared = (1.3e-6) ** 2
        expected_mask = (
            coordinate_y[:, None].square() + coordinate_x[None, :].square()
            <= radius_squared
        )
        # 输出包络实部须精确等于二元掩膜（输入为单位实数）；虚部为零
        assert torch.allclose(
            output.envelope.real,
            expected_mask.to(torch.float64),
            atol=1e-12,
        )
        assert torch.allclose(
            output.envelope.imag,
            expected_mask.to(torch.float64) * 0.0,
            atol=1e-12,
        )

    def test_phase_preserved_for_complex_input(self) -> None:
        """光瞳为实非负掩膜 ⇒ 复输入的相位在透射区逐点保持，孔径外包络为零
        """
        grid = _grid()
        spectrum = _monochromatic()
        counts_y, counts_x = grid.sample_counts
        # 构造逐点复相位输入
        phase_ramp = torch.linspace(
            0.0,
            1.5,
            steps=counts_y * counts_x,
        ).reshape(counts_y, counts_x)
        envelope = torch.complex(
            torch.cos(phase_ramp).unsqueeze(0).unsqueeze(0),
            torch.sin(phase_ramp).unsqueeze(0).unsqueeze(0),
        ).to(dtype=torch.complex128)
        field = OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(
                lengths=(0.0,) * spectrum.count,
            ),
        )
        radius = 0.9e-6
        element = CircularPupil(grid=grid, radius=radius)
        output = element(field)
        coordinate_y, coordinate_x = _grid_coordinates(grid)
        transmitted = (
            coordinate_y[:, None].square() + coordinate_x[None, :].square()
        ) <= radius ** 2
        # 透射区：相位须逐点相等（掩膜为实非负，乘法不旋转相位）
        output_phase = output.envelope.angle()[0, 0][transmitted]
        input_phase = field.envelope.angle()[0, 0][transmitted]
        assert torch.allclose(output_phase, input_phase, atol=1e-9)
        # 孔径外：包络须为零
        blocked = ~transmitted
        assert torch.allclose(
            output.envelope[0, 0][blocked],
            torch.zeros_like(output.envelope[0, 0][blocked]),
            atol=1e-12,
        )

    def test_grid_mismatch_rejected(self) -> None:
        """输入光场网格与光瞳注册网格不一致须以稳定身份拒绝
        """
        grid = _grid()
        other_grid = _grid(counts=(9, 7))
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum)
        element = CircularPupil(grid=other_grid, radius=1.0e-6)
        with pytest.raises(ValueError, match="circular_pupil_grid_mismatch"):
            element(field)

    def test_radius_nonpositive_rejected(self) -> None:
        """半径须为有限正实数；非正或非有限值须以稳定身份拒绝
        """
        grid = _grid()
        with pytest.raises(ValueError, match="circular_pupil_radius_invalid"):
            CircularPupil(grid=grid, radius=0.0)
        with pytest.raises(ValueError, match="circular_pupil_radius_invalid"):
            CircularPupil(grid=grid, radius=-1.0e-6)

class TestSquarePupilPhysicalInvariants:
    """
    证据层 1（方光瞳）：物理不变量
    """

    def test_transmittance_is_binary_inside_square(self) -> None:
        """方光瞳透射为二元 {0,1}，孔径内（max(|y-cy|,|x-cx|) ≤ w/2）为 1、孔径外为 0
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, amplitude=1.0)
        width = 2.4e-6
        element = SquarePupil(grid=grid, width=width)
        output = element(field)
        coordinate_y, coordinate_x = _grid_coordinates(grid)
        half_width = width / 2.0
        expected_mask = (
            torch.maximum(
                coordinate_y[:, None].abs(),
                coordinate_x[None, :].abs(),
            )
            <= half_width
        )
        assert torch.allclose(
            output.envelope.real,
            expected_mask.to(torch.float64),
            atol=1e-12,
        )

    def test_phase_preserved_for_complex_input(self) -> None:
        """
        验证实二元方形掩膜保持透射样本相位
        """

        grid = _grid()
        spectrum = _monochromatic()
        phase = torch.linspace(
            0.0,
            1.5,
            steps=grid.sample_counts[0] * grid.sample_counts[1],
            dtype=torch.float64,
        ).reshape(grid.sample_counts)
        envelope = torch.polar(
            torch.ones_like(phase),
            phase,
        ).unsqueeze(0).unsqueeze(0)
        field = OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )
        width = 1.8e-6
        output = SquarePupil(grid=grid, width=width)(field)
        coordinate_y, coordinate_x = _grid_coordinates(grid)
        transmitted = (
            torch.maximum(
                coordinate_y[:, None].abs(),
                coordinate_x[None, :].abs(),
            )
            <= width / 2.0
        )
        assert torch.allclose(
            output.envelope.angle()[0, 0][transmitted],
            field.envelope.angle()[0, 0][transmitted],
            atol=1.0e-12,
        )
        assert torch.count_nonzero(
            output.envelope[0, 0][~transmitted]
        ).item() == 0

    def test_grid_mismatch_rejected(self) -> None:
        """输入光场网格与光瞳注册网格不一致须以稳定身份拒绝
        """
        grid = _grid()
        other_grid = _grid(counts=(9, 7))
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum)
        element = SquarePupil(grid=other_grid, width=2.0e-6)
        with pytest.raises(ValueError, match="square_pupil_grid_mismatch"):
            element(field)

    def test_width_nonpositive_rejected(self) -> None:
        """宽度须为有限正实数；非正或非有限值须以稳定身份拒绝
        """
        grid = _grid()
        with pytest.raises(ValueError, match="square_pupil_width_invalid"):
            SquarePupil(grid=grid, width=0.0)
        with pytest.raises(ValueError, match="square_pupil_width_invalid"):
            SquarePupil(grid=grid, width=-1.0e-6)


class TestFixedGeometryRejectsGraphBearingTensor:
    """
    固定硬分类状态的闭包（trainable-claims H/F 决断）

    半径/宽度是固定 Buffer：``Parameter`` 与任何 ``requires_grad=True`` 张量（含
    非 Parameter 的叶张量）都按同一稳定身份 ``circular_pupil_radius_invalid``/
    ``square_pupil_width_invalid`` 拒绝；固定张量与 Python float 仍被接受。守卫同时
    覆盖 Component 构造与函数入口。
    """

    @pytest.mark.parametrize(
        ("component_type", "extent_name", "extent_value", "prefix"),
        (
            (CircularPupil, "radius", 1.5e-6, "circular"),
            (SquarePupil, "width", 2.0e-6, "square"),
        ),
        ids=("circular", "square"),
    )
    def test_parameter_rejected_at_construction(
        self,
        component_type: type,
        extent_name: str,
        extent_value: float,
        prefix: str,
    ) -> None:
        """``Parameter`` 在 Component 构造时即按稳定身份拒绝
        """
        grid = _grid()
        identity = f"{prefix}_pupil_{extent_name}_invalid"
        parameter = torch.nn.Parameter(torch.tensor(extent_value))
        with pytest.raises((TypeError, ValueError), match=identity):
            component_type(grid=grid, **{extent_name: parameter})

    @pytest.mark.parametrize(
        ("function", "component_type", "extent_name", "extent_value", "prefix"),
        (
            (circular_pupil, CircularPupil, "radius", 1.5e-6, "circular"),
            (square_pupil, SquarePupil, "width", 2.0e-6, "square"),
        ),
        ids=("circular", "square"),
    )
    def test_requires_grad_tensor_rejected_at_construction(
        self,
        function: object,
        component_type: type,
        extent_name: str,
        extent_value: float,
        prefix: str,
    ) -> None:
        """非 Parameter 的 ``requires_grad=True`` 张量在 Component 构造时按同一身份拒绝

        固定硬分类拒绝任何带计算图的张量：任何带计算图的张量都不允许进入
        固定几何槽位，与 ``clear_aperture_radius`` 守卫一致。
        """
        grid = _grid()
        identity = f"{prefix}_pupil_{extent_name}_invalid"
        graph_tensor = torch.tensor(extent_value, requires_grad=True)
        assert not isinstance(graph_tensor, torch.nn.Parameter)
        with pytest.raises((TypeError, ValueError), match=identity):
            component_type(grid=grid, **{extent_name: graph_tensor})

    @pytest.mark.parametrize(
        ("function", "extent_name", "extent_value", "prefix"),
        (
            (circular_pupil, "radius", 1.5e-6, "circular"),
            (square_pupil, "width", 2.0e-6, "square"),
        ),
        ids=("circular", "square"),
    )
    def test_requires_grad_tensor_rejected_at_function_entry(
        self,
        function: object,
        extent_name: str,
        extent_value: float,
        prefix: str,
    ) -> None:
        """函数入口同样拒绝 ``requires_grad=True`` 张量（同一稳定身份）
        """
        grid = _grid()
        field = _constant_field(grid, _monochromatic())
        identity = f"{prefix}_pupil_{extent_name}_invalid"
        graph_tensor = torch.tensor(extent_value, requires_grad=True)
        with pytest.raises((TypeError, ValueError), match=identity):
            function(  # type: ignore[operator]
                field,
                grid=grid,
                **{extent_name: graph_tensor},
            )

    @pytest.mark.parametrize(
        ("component_type", "extent_name", "extent_value"),
        (
            (CircularPupil, "radius", 1.5e-6),
            (SquarePupil, "width", 2.0e-6),
        ),
        ids=("circular", "square"),
    )
    def test_fixed_tensor_and_float_still_accepted(
        self,
        component_type: type,
        extent_name: str,
        extent_value: float,
    ) -> None:
        """``requires_grad=False`` 张量与 Python float 仍被接受，且结果为固定 Buffer
        """
        grid = _grid()
        from_tensor = component_type(
            grid=grid,
            **{
                extent_name: torch.tensor(
                    extent_value,
                    dtype=torch.float64,
                )
            },
        )
        from_float = component_type(
            grid=grid,
            **{extent_name: extent_value},
        )
        buffer_from_tensor = dict(from_tensor.named_buffers())[extent_name]
        buffer_from_float = dict(from_float.named_buffers())[extent_name]
        assert buffer_from_tensor.requires_grad is False
        assert buffer_from_float.requires_grad is False
        assert buffer_from_tensor.dtype is torch.float64


class TestPupilFixedDoubleAdmission:
    """
    光瞳几何在构造与直接消费边界遵守固定双精度
    """

    @pytest.mark.parametrize(
        ("function", "component_type", "extent_name", "identity"),
        (
            (
                circular_pupil,
                CircularPupil,
                "radius",
                "circular_pupil_radius_invalid",
            ),
            (
                square_pupil,
                SquarePupil,
                "width",
                "square_pupil_width_invalid",
            ),
        ),
        ids=("circular", "square"),
    )
    @pytest.mark.parametrize(
        "invalid_extent",
        (
            torch.tensor(1.0e-6, dtype=torch.float32),
            torch.tensor(1.0e-6, dtype=torch.complex128),
            torch.tensor(float("inf"), dtype=torch.float64),
            torch.tensor([1.0e-6], dtype=torch.float64),
            True,
        ),
        ids=("float32", "complex", "nonfinite", "nonscalar", "bool"),
    )
    def test_invalid_extent_rejected_by_function_and_component(
        self,
        function: object,
        component_type: type,
        extent_name: str,
        identity: str,
        invalid_extent: object,
    ) -> None:
        """
        非 exact-float64 固定标量不能在任一公共入口被静默改写
        """
        grid = _grid()
        field = _constant_field(grid, _monochromatic())
        with pytest.raises((TypeError, ValueError), match=identity):
            component_type(grid=grid, **{extent_name: invalid_extent})
        with pytest.raises((TypeError, ValueError), match=identity):
            function(  # type: ignore[operator]
                field,
                grid=grid,
                **{extent_name: invalid_extent},
            )

    @pytest.mark.parametrize(
        ("component_type", "extent_name", "extent_value", "identity"),
        (
            (
                CircularPupil,
                "radius",
                1.5e-6,
                "circular_pupil_radius_invalid",
            ),
            (
                SquarePupil,
                "width",
                2.0e-6,
                "square_pupil_width_invalid",
            ),
        ),
        ids=("circular", "square"),
    )
    def test_component_dtype_drift_rejected_before_pupil_arithmetic(
        self,
        component_type: type,
        extent_name: str,
        extent_value: float,
        identity: str,
    ) -> None:
        """
        ``module.to(float32)`` 产生的几何漂移在掩膜计算前稳定拒绝
        """
        grid = _grid()
        field = _constant_field(grid, _monochromatic())
        component = component_type(grid=grid, **{extent_name: extent_value})
        component.to(dtype=torch.float32)
        with pytest.raises(ValueError, match=identity):
            component(field)

    @pytest.mark.parametrize(
        ("component_type", "extent_name", "extent_value"),
        (
            (CircularPupil, "radius", 1.5e-6),
            (SquarePupil, "width", 2.0e-6),
        ),
        ids=("circular", "square"),
    )
    def test_float64_tensor_is_registered_without_dtype_conversion(
        self,
        component_type: type,
        extent_name: str,
        extent_value: float,
    ) -> None:
        """
        合格张量以原对象成为固定 Buffer；Python 数值才物化为 float64
        """
        authored_extent = torch.tensor(extent_value, dtype=torch.float64)
        from_tensor = component_type(
            grid=_grid(),
            **{extent_name: authored_extent},
        )
        from_python = component_type(
            grid=_grid(),
            **{extent_name: extent_value},
        )
        assert dict(from_tensor.named_buffers())[extent_name] is authored_extent
        assert dict(from_python.named_buffers())[extent_name].dtype is torch.float64

    @pytest.mark.parametrize(
        ("function", "extent_name", "extent_value"),
        (
            (circular_pupil, "radius", 1.5e-6),
            (square_pupil, "width", 2.0e-6),
        ),
        ids=("circular", "square"),
    )
    def test_meta_float64_extent_accepted_and_float32_rejected(
        self,
        function: object,
        extent_name: str,
        extent_value: float,
    ) -> None:
        """
        meta 入口只依赖结构与 dtype，且不尝试读取不可读数值
        """
        grid = _grid()
        field = _constant_field(
            grid,
            _monochromatic(),
            device="meta",
        )
        accepted = function(  # type: ignore[operator]
            field,
            grid=grid,
            **{
                extent_name: torch.tensor(
                    extent_value,
                    dtype=torch.float64,
                    device="meta",
                )
            },
        )
        assert accepted.envelope.device.type == "meta"
        with pytest.raises(ValueError):
            function(  # type: ignore[operator]
                field,
                grid=grid,
                **{
                    extent_name: torch.tensor(
                        extent_value,
                        dtype=torch.float32,
                        device="meta",
                    )
                },
            )

    @pytest.mark.cuda
    @pytest.mark.parametrize(
        ("function", "component_type", "extent_name", "extent_value"),
        (
            (circular_pupil, CircularPupil, "radius", 1.5e-6),
            (square_pupil, SquarePupil, "width", 2.0e-6),
        ),
        ids=("circular", "square"),
    )
    def test_cuda_float64_extent_remains_device_local(
        self,
        function: object,
        component_type: type,
        extent_name: str,
        extent_value: float,
    ) -> None:
        """
        原生 CUDA 上合格几何保持 float64，并由两种入口直接消费
        """
        grid = _grid()
        field = _constant_field(
            grid,
            _monochromatic(),
            device="cuda",
        )
        authored_extent = torch.tensor(
            extent_value,
            dtype=torch.float64,
            device="cuda",
        )
        direct = function(  # type: ignore[operator]
            field,
            grid=grid,
            **{extent_name: authored_extent},
        )
        component = component_type(
            grid=grid,
            **{extent_name: authored_extent},
        )
        delegated = component(field)
        assert dict(component.named_buffers())[extent_name] is authored_extent
        assert direct.envelope.device.type == "cuda"
        assert torch.equal(delegated.envelope, direct.envelope)


@pytest.mark.cuda
@pytest.mark.parametrize(
    ("function", "extent_name", "extent_value"),
    (
        (circular_pupil, "radius", 1.5e-6),
        (square_pupil, "width", 2.0e-6),
    ),
    ids=("circular", "square"),
)
def test_pupil_public_actions_match_cpu_on_cuda(
    function: object,
    extent_name: str,
    extent_value: float,
) -> None:
    """
    光瞳公共动作在 CUDA 上保持与 CPU 相同的复包络

    二元硬掩膜对包络只做 0/1 乘法，且几何分类 y²+x²≤R²（或
    Chebyshev 距离≤w/2）仅由正确舍入的乘加构成，属 Issue 16
    预算的逐点方程族（预算 0），故要求跨设备逐位一致。
    """

    grid = _grid()
    spectrum = _monochromatic()
    cpu_field = _constant_field(grid, spectrum, amplitude=2.5)
    cuda_field = _constant_field(
        grid,
        spectrum,
        amplitude=2.5,
        device="cuda",
    )

    cpu_output = function(  # type: ignore[operator]
        cpu_field,
        grid=grid,
        **{extent_name: extent_value},
    )
    cuda_output = function(  # type: ignore[operator]
        cuda_field,
        grid=grid,
        **{extent_name: extent_value},
    )

    torch.testing.assert_close(
        cpu_output.envelope,
        cuda_output.envelope.cpu(),
        rtol=0.0,
        atol=0.0,
    )


class TestIndependentReference:
    """
    证据层 2：独立解析参照

    独立参照刻意走与元件内部不同的构造路径：这里以 Python 标量构造半径平方/半宽并以
    ``torch.maximum``/``<=`` 显式比较；元件内部以张量广播构造。两者须逐点一致。
    """

    def test_circular_pupil_matches_independent_window(self) -> None:
        """圆光瞳输出须与独立计算的圆窗口一致（含边界闭区间约定）
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, amplitude=2.5)
        radius = 1.6e-6
        element = CircularPupil(grid=grid, radius=radius)
        output = element(field)
        coordinate_y, coordinate_x = _grid_coordinates(grid)
        # 独立窗口：逐点距离平方与半径平方比较（闭区间）
        window = (
            coordinate_y[:, None] ** 2 + coordinate_x[None, :] ** 2
        ) <= radius ** 2
        expected = (window.to(torch.complex128) * 2.5).unsqueeze(0).unsqueeze(0)
        assert torch.allclose(output.envelope, expected, atol=1e-12)

    def test_square_pupil_matches_independent_window(self) -> None:
        """方光瞳输出须与独立计算的方窗口一致（含边界闭区间约定）
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, amplitude=1.4)
        width = 2.2e-6
        element = SquarePupil(grid=grid, width=width)
        output = element(field)
        coordinate_y, coordinate_x = _grid_coordinates(grid)
        half_width = width / 2.0
        # 独立窗口：Chebyshev 距离与半宽比较（闭区间）
        window = torch.maximum(
            coordinate_y[:, None].abs(),
            coordinate_x[None, :].abs(),
        ) <= half_width
        expected = (window.to(torch.complex128) * 1.4).unsqueeze(0).unsqueeze(0)
        assert torch.allclose(output.envelope, expected, atol=1e-12)

    def test_circular_pupil_boundary_inclusive(self) -> None:
        """边界点（恰在半径上）须判定为孔径内（迁移源 ``<=`` 约定）

        构造一个样本恰落在指定半径上的网格，验证该样本透射为 1。
        """
        # 一维两样本网格：首样本在 -R，次样本在 +R（间距 2R，居中）
        radius = 1.0e-6
        grid = SpatialGrid(
            sample_counts=(1, 2),
            sample_spacing=(2.0 * radius, 2.0 * radius),
            first_sample_position=(0.0, -radius),
        )
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, amplitude=1.0)
        element = CircularPupil(grid=grid, radius=radius)
        output = element(field)
        # 两个 x 样本 (±R, y=0) 均满足 y²+x² = R² ≤ R² ⇒ 透射为 1
        assert torch.allclose(
            output.envelope.real,
            torch.ones_like(output.envelope.real),
            atol=1e-12,
        )

    def test_square_pupil_boundary_inclusive(self) -> None:
        """
        验证位于正负半宽处的样本仍然透射
        """

        half_width = 1.0e-6
        grid = SpatialGrid(
            sample_counts=(1, 2),
            sample_spacing=(2.0 * half_width, 2.0 * half_width),
            first_sample_position=(0.0, -half_width),
        )
        field = _constant_field(
            grid,
            _monochromatic(),
            amplitude=1.0,
        )
        output = SquarePupil(
            grid=grid,
            width=2.0 * half_width,
        )(field)
        assert torch.allclose(
            output.envelope,
            torch.ones_like(output.envelope),
            atol=1.0e-12,
        )

    @pytest.mark.parametrize(
        "element",
        [
            CircularPupil(
                grid=SpatialGrid(
                    sample_counts=(2, 4),
                    sample_spacing=(1.0, 0.5),
                    first_sample_position=(1.0, -1.0),
                    orientation=("decreasing", "increasing"),
                ),
                radius=0.5,
            ),
            SquarePupil(
                grid=SpatialGrid(
                    sample_counts=(2, 4),
                    sample_spacing=(1.0, 0.5),
                    first_sample_position=(1.0, -1.0),
                    orientation=("decreasing", "increasing"),
                ),
                width=1.0,
            ),
        ],
        ids=("circular", "square"),
    )
    def test_pupil_respects_decreasing_sampling_orientation(
        self,
        element: CircularPupil | SquarePupil,
    ) -> None:
        """
        元件把递减轴按带符号步进交给孔径数值所有者
        """

        grid = element.grid
        field = _constant_field(
            grid,
            _monochromatic(),
        )
        output = element(field)
        expected = torch.tensor(
            [
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 1.0, 1.0],
            ],
            dtype=torch.float64,
        ).reshape(1, 1, 2, 4)

        assert torch.equal(output.envelope.real, expected)

    @pytest.mark.parametrize(
        "element",
        [
            CircularPupil(grid=_grid(), radius=1.0e-6),
            SquarePupil(grid=_grid(), width=2.0e-6),
        ],
        ids=("circular", "square"),
    )
    def test_pupil_recomputes_without_retaining_derived_state(
        self,
        element: CircularPupil | SquarePupil,
    ) -> None:
        """
        无状态函数每次重算孔径且 Component 不保留派生掩膜
        """

        field = _constant_field(
            _grid(),
            _monochromatic(),
        )

        first = element(field)
        second = element(field)

        assert torch.equal(first.envelope, second.envelope)

    def test_pupil_recomputes_without_retaining_derived_state_single_dtype(
        self,
    ) -> None:
        """
        无状态函数每次重算孔径且 Component 不保留派生掩膜（固定 double 精度）
        """

        field = _constant_field(
            _grid(),
            _monochromatic(),
        )
        element = CircularPupil(grid=_grid(), radius=1.0e-6)

        first = element(field)
        second = element(field)

        assert torch.equal(first.envelope, second.envelope)
        assert first.envelope.dtype is torch.complex128


class TestGradientEvidence:
    """
    证据层 3：梯度证据

    规约"组件证据"：梯度证据针对**每可训练声明**。光瞳为固定孔径（半径/宽度固定
    Buffer，无 Parameter），无可训练声明，故该层为空。以断言固定 Buffer 身份记录该决断：
    光瞳不暴露可训练参数，autograd 图不穿过孔径几何。
    """

    def test_circular_pupil_has_no_trainable_parameters(self) -> None:
        """圆光瞳无可训练 Parameter；半径为固定 Buffer
        """
        grid = _grid()
        element = CircularPupil(grid=grid, radius=1.0e-6)
        parameters = list(element.parameters())
        assert parameters == []
        buffers = dict(element.named_buffers())
        # 半径以固定 Buffer 注册（非持久化缓存除外）
        assert "radius" in buffers

    def test_square_pupil_has_no_trainable_parameters(self) -> None:
        """方光瞳无可训练 Parameter；宽度为固定 Buffer
        """
        grid = _grid()
        element = SquarePupil(grid=grid, width=2.0e-6)
        parameters = list(element.parameters())
        assert parameters == []
        buffers = dict(element.named_buffers())
        assert "width" in buffers

    @pytest.mark.parametrize(
        "element",
        (
            CircularPupil(grid=_grid(), radius=1.0e-6),
            SquarePupil(grid=_grid(), width=2.0e-6),
        ),
        ids=("circular", "square"),
    )
    def test_owned_grid_moves_with_pupil_to_meta(
        self,
        element: CircularPupil | SquarePupil,
    ) -> None:
        """
        光瞳迁移到 meta 后公共 grid 只由同一模块树的 meta 状态重建
        """
        element.to(device="meta")

        assert all(
            value.device.type == "meta"
            for value in (
                *element.grid.sample_spacing,
                *element.grid.first_sample_position,
            )
        )

    @pytest.mark.parametrize(
        "element",
        [
            CircularPupil(grid=_grid(), radius=1.0e-6),
            SquarePupil(grid=_grid(), width=2.0e-6),
        ],
        ids=("circular", "square"),
    )
    def test_fixed_pupil_preserves_input_gradient(
        self,
        element: CircularPupil | SquarePupil,
    ) -> None:
        """
        验证固定光瞳几何不截断可训练输入光场
        """

        grid = _grid()
        spectrum = _monochromatic()
        envelope = torch.ones(
            (1, 1, *grid.sample_counts),
            dtype=torch.complex128,
            requires_grad=True,
        )
        field = OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )
        output = element(field)
        output.envelope.abs().square().sum().backward()
        assert envelope.grad is not None
        transmitted = output.envelope.abs() > 0.0
        assert torch.all(envelope.grad[transmitted] != 0.0)
        assert torch.all(envelope.grad[~transmitted] == 0.0)


class TestHostedExecution:
    """
    托管端到端：PlaneWave → 托管光瞳 → IntensityDetection
    """

    def test_hosted_circular_pupil_produces_aperture_intensity(self) -> None:
        """托管圆光瞳 ⇒ 光强在孔径内为 1、孔径外为 0（孔径形状正确）

        PlaneWave（单位振幅、前向、相对归一化）→ 托管圆光瞳 → IntensityDetection。
        单位振幅 ⇒ |E|² 在透射处为 1、阻拦处为 0。
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
        pupil = workstation.host(CircularPupil(grid=grid, radius=1.3e-6))
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        intensity = detection(pupil(field))
        coordinate_y, coordinate_x = _grid_coordinates(grid)
        expected_mask = (
            coordinate_y[:, None] ** 2 + coordinate_x[None, :] ** 2
        ) <= (1.3e-6) ** 2
        expected = expected_mask.to(torch.float64)
        assert torch.allclose(intensity.values, expected, atol=1e-6)

    def test_hosted_square_pupil_produces_aperture_intensity(self) -> None:
        """托管方光瞳 ⇒ 光强在孔径内为 1、孔径外为 0（孔径形状正确）
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
        pupil = workstation.host(SquarePupil(grid=grid, width=2.4e-6))
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        intensity = detection(pupil(field))
        coordinate_y, coordinate_x = _grid_coordinates(grid)
        expected_mask = torch.maximum(
            coordinate_y[:, None].abs(),
            coordinate_x[None, :].abs(),
        ) <= 1.2e-6
        expected = expected_mask.to(torch.float64)
        assert torch.allclose(intensity.values, expected, atol=1e-6)
