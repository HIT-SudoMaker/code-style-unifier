
from __future__ import annotations

from typing import Any

import pytest
import torch

from chromatix_next.optics._grid_state import _GridState
import chromatix_next.optics.grid as grid_module
from chromatix_next.optics.grid import PropagationExterior, SpatialGrid


class TestSpatialGridTensorValues:
    """
    网格的连续空间量始终保留为零维实数张量
    """

    def test_python_values_materialize_as_float64(self) -> None:
        """
        Python 数值在物理值入口规范为固定双精度 float64 标量张量
        """
        grid = SpatialGrid(
            sample_counts=(4, 6),
            sample_spacing=(1.0e-6, 2.0e-6),
            first_sample_position=(-2.0e-6, -6.0e-6),
        )

        spatial_values = (
            *grid.sample_spacing,
            *grid.first_sample_position,
        )
        assert all(value.dim() == 0 for value in spatial_values)
        assert all(value.dtype is torch.float64 for value in spatial_values)
        assert all(
            value.device == torch.device("cpu")
            for value in spatial_values
        )

    def test_tensor_precision_and_identity_are_preserved(self) -> None:
        """
        已给出的浮点张量不被复制或悄悄改写精度
        """
        spacing_y = torch.nn.Parameter(torch.tensor(1.0e-6, dtype=torch.float64))
        spacing_x = torch.tensor(2.0e-6, dtype=torch.float64)
        position_y = torch.tensor(-2.0e-6, dtype=torch.float64)
        position_x = torch.tensor(-6.0e-6, dtype=torch.float64)

        grid = SpatialGrid(
            sample_counts=(4, 6),
            sample_spacing=(spacing_y, spacing_x),
            first_sample_position=(position_y, position_x),
        )

        assert grid.sample_spacing[0] is spacing_y
        assert grid.sample_spacing[1] is spacing_x
        assert grid.first_sample_position[0] is position_y
        assert grid.first_sample_position[1] is position_x

    @pytest.mark.parametrize(
        ("field_name", "invalid_value", "identity"),
        (
            (
                "sample_spacing",
                torch.ones(2),
                "spatial_grid_sample_spacing_invalid",
            ),
            (
                "sample_spacing",
                torch.tensor(1, dtype=torch.int64),
                "spatial_grid_sample_spacing_invalid",
            ),
            (
                "sample_spacing",
                torch.tensor(1.0 + 0.0j),
                "spatial_grid_sample_spacing_invalid",
            ),
            (
                "sample_spacing",
                torch.tensor(float("nan"), dtype=torch.float64),
                "spatial_grid_sample_spacing_nonfinite",
            ),
            (
                "sample_spacing",
                torch.tensor(0.0, dtype=torch.float64),
                "spatial_grid_sample_spacing_invalid",
            ),
            (
                "sample_spacing",
                torch.tensor(1.0e-6, dtype=torch.float32),
                "spatial_grid_sample_spacing_invalid",
            ),
            (
                "first_sample_position",
                torch.ones(2),
                "spatial_grid_first_sample_position_invalid",
            ),
            (
                "first_sample_position",
                torch.tensor(1, dtype=torch.int64),
                "spatial_grid_first_sample_position_invalid",
            ),
            (
                "first_sample_position",
                torch.tensor(float("inf"), dtype=torch.float64),
                "spatial_grid_first_sample_position_nonfinite",
            ),
            (
                "first_sample_position",
                torch.tensor(0.0, dtype=torch.float32),
                "spatial_grid_first_sample_position_invalid",
            ),
        ),
    )
    def test_invalid_tensor_values_are_rejected(
        self,
        field_name: str,
        invalid_value: torch.Tensor,
        identity: str,
    ) -> None:
        """
        batch、整数、复数、float32 和非法取值在网格物理值入口被拒绝
        """
        arguments: dict[str, Any] = {
            "sample_counts": (4, 4),
            "sample_spacing": (1.0e-6, 1.0e-6),
            "first_sample_position": (0.0, 0.0),
        }
        arguments[field_name] = (invalid_value, invalid_value)

        with pytest.raises(ValueError, match=identity):
            SpatialGrid(**arguments)

    def test_grid_rejects_float32_scalar_input(self) -> None:
        """
        单精度 float32 标量张量不得成为固定双精度网格的连续状态

        f32 在物理值入口显式拒绝（不再静默保留），与 固定双精度契约的
        SpatialGrid 行 "fp64 spacing/origin; f32 reject" 对齐。
        """
        with pytest.raises(
            ValueError,
            match="spatial_grid_sample_spacing_invalid",
        ):
            SpatialGrid(
                sample_counts=(4, 4),
                sample_spacing=(
                    torch.tensor(1.0e-6, dtype=torch.float32),
                    torch.tensor(1.0e-6, dtype=torch.float32),
                ),
                first_sample_position=(
                    torch.tensor(0.0, dtype=torch.float32),
                    torch.tensor(0.0, dtype=torch.float32),
                ),
            )

    def test_grid_rejects_mixed_scalar_placement(self) -> None:
        """
        同一网格的四个连续标量不得悄悄跨设备
        """
        with pytest.raises(
            ValueError,
            match="spatial_grid_scalar_placement_mismatch",
        ):
            SpatialGrid(
                sample_counts=(4, 4),
                sample_spacing=(
                    torch.tensor(1.0e-6, dtype=torch.float64),
                    torch.tensor(
                        1.0e-6,
                        dtype=torch.float64,
                        device="meta",
                    ),
                ),
                first_sample_position=(
                    torch.tensor(0.0, dtype=torch.float64),
                    torch.tensor(0.0, dtype=torch.float64),
                ),
            )

    def test_centered_position_tracks_trainable_spacing(self) -> None:
        """
        中心网格的原点按当前间距派生，不缓存会陈旧的非叶张量
        """
        spacing_y = torch.nn.Parameter(
            torch.tensor(2.0e-6, dtype=torch.float64),
        )
        spacing_x = torch.tensor(3.0e-6, dtype=torch.float64)
        grid = SpatialGrid.centered(
            sample_counts=(8, 6),
            sample_spacing=(spacing_y, spacing_x),
        )

        first_position_before = grid.first_sample_position[0]
        with torch.no_grad():
            spacing_y.add_(0.5e-6)
        first_position_after = grid.first_sample_position[0]

        assert first_position_before is not first_position_after
        torch.testing.assert_close(
            first_position_after,
            torch.tensor(-10.0e-6, dtype=torch.float64),
        )

    def test_centered_spacing_gradient_matches_finite_difference(
        self,
    ) -> None:
        """
        网格间距经中心原点和单元面积传播的梯度与有限差分一致
        """
        spacing_y = torch.nn.Parameter(
            torch.tensor(2.0e-6, dtype=torch.float64),
        )
        spacing_x = torch.tensor(3.0e-6, dtype=torch.float64)
        grid = SpatialGrid.centered(
            sample_counts=(8, 6),
            sample_spacing=(spacing_y, spacing_x),
        )
        observable = (
            grid.first_sample_position[0].square()
            + grid.cell_area
        )
        gradient = torch.autograd.grad(observable, spacing_y)[0]

        def _evaluate(candidate: float) -> float:
            candidate_grid = SpatialGrid.centered(
                sample_counts=(8, 6),
                sample_spacing=(
                    torch.tensor(candidate, dtype=torch.float64),
                    spacing_x,
                ),
            )
            value = (
                candidate_grid.first_sample_position[0].square()
                + candidate_grid.cell_area
            )
            return float(value)

        step = 1.0e-10
        finite_difference = (
            _evaluate(float(spacing_y.detach()) + step)
            - _evaluate(float(spacing_y.detach()) - step)
        ) / (2.0 * step)
        assert float(gradient) == pytest.approx(
            finite_difference,
            rel=1.0e-8,
            abs=1.0e-12,
        )

    def test_grid_moves_as_one_physical_value(self) -> None:
        """
        网格迁移后四个连续标量仍位于同一设备并使用同一实数精度
        """
        grid = SpatialGrid(
            sample_counts=(4, 6),
            sample_spacing=(1.0e-6, 2.0e-6),
            first_sample_position=(-2.0e-6, -6.0e-6),
        )
        moved = grid.to(device="meta", dtype=torch.float64)
        spatial_values = (
            *moved.sample_spacing,
            *moved.first_sample_position,
        )

        assert all(value.device.type == "meta" for value in spatial_values)
        assert all(value.dtype is torch.float64 for value in spatial_values)


class TestSpatialGridPhysicalEquivalence:
    """
    网格物理等价由唯一具名判定表达
    """

    def test_real_comparison_is_exact_and_does_not_build_a_graph(self) -> None:
        """
        真实张量比较脱离自动微分图且能区分任一坐标变化
        """
        spacing_y = torch.nn.Parameter(
            torch.tensor(1.0e-6, dtype=torch.float64),
        )
        grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(
                spacing_y,
                torch.tensor(1.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(0.0, dtype=torch.float64),
                torch.tensor(0.0, dtype=torch.float64),
            ),
        )
        equal_grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(
                spacing_y.detach().clone().requires_grad_(),
                torch.tensor(1.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(0.0, dtype=torch.float64),
                torch.tensor(0.0, dtype=torch.float64),
            ),
        )
        shifted_grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(
                torch.tensor(1.0e-6, dtype=torch.float64),
                torch.tensor(1.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(1.0e-9, dtype=torch.float64),
                torch.tensor(0.0, dtype=torch.float64),
            ),
        )

        assert grid.is_physically_equivalent_to(equal_grid)
        assert not grid.is_physically_equivalent_to(shifted_grid)
        assert spacing_y.grad is None

    def test_meta_comparison_uses_structure_without_reading_values(
        self,
    ) -> None:
        """
        meta 网格只有结构可读，不制造物理值孪生
        """
        grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(
                torch.empty((), dtype=torch.float64, device="meta"),
                torch.empty((), dtype=torch.float64, device="meta"),
            ),
            first_sample_position=(
                torch.empty((), dtype=torch.float64, device="meta"),
                torch.empty((), dtype=torch.float64, device="meta"),
            ),
        )
        structurally_equal = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(
                torch.empty((), dtype=torch.float64, device="meta"),
                torch.empty((), dtype=torch.float64, device="meta"),
            ),
            first_sample_position=(
                torch.empty((), dtype=torch.float64, device="meta"),
                torch.empty((), dtype=torch.float64, device="meta"),
            ),
        )
        different_shape = SpatialGrid(
            sample_counts=(5, 4),
            sample_spacing=grid.sample_spacing,
            first_sample_position=grid.first_sample_position,
        )

        assert grid.is_physically_equivalent_to(grid)
        assert not grid.is_physically_equivalent_to(structurally_equal)
        assert not grid.is_physically_equivalent_to(different_shape)

    def test_centered_grid_equivalence_ignores_derived_rounding(self) -> None:
        """
        中心网格跨表示比较相同间距，不重复比较派生原点的舍入

        固定双精度核下，比较两个独立的 float64 中心网格（同间距、
        不同 Python 标量来源）须判为物理等价；派生原点的舍入不重复进入比较。
        早先的单精度对照版被替换为固定双精度版（f32 不再是合法网格精度）。
        """
        grid_direct = SpatialGrid.centered(
            sample_counts=(7, 7),
            sample_spacing=(
                torch.tensor(0.5e-6, dtype=torch.float64),
                torch.tensor(0.5e-6, dtype=torch.float64),
            ),
        )
        grid_rebuilt = SpatialGrid.centered(
            sample_counts=(7, 7),
            sample_spacing=(
                torch.tensor(0.5e-6, dtype=torch.float64),
                torch.tensor(0.5e-6, dtype=torch.float64),
            ),
        )

        assert grid_direct.is_physically_equivalent_to(grid_rebuilt)

    def test_inference_compatibility_defers_unreadable_coordinates(self) -> None:
        """
        推导按结构延期 meta/meta 与 meta/real 的未知坐标
        """
        meta_grid_1 = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(
                torch.empty((), dtype=torch.float64, device="meta"),
                torch.empty((), dtype=torch.float64, device="meta"),
            ),
        )
        meta_grid_2 = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(
                torch.empty((), dtype=torch.float64, device="meta"),
                torch.empty((), dtype=torch.float64, device="meta"),
            ),
        )
        real_grid = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(1.0e-6, 1.0e-6),
        )

        assert meta_grid_1.is_inference_compatible_with(meta_grid_2)
        assert meta_grid_1.is_inference_compatible_with(real_grid)


class TestGridState:
    """
    模块拥有的网格通过一个私有状态适配器进入 PyTorch 模块树
    """

    def test_explicit_grid_preserves_parameter_identity(self) -> None:
        """
        显式网格的 Parameter 原样注册，其余连续标量注册为 Buffer
        """
        spacing_y = torch.nn.Parameter(
            torch.tensor(1.0e-6, dtype=torch.float64),
        )
        grid = SpatialGrid(
            sample_counts=(4, 6),
            sample_spacing=(
                spacing_y,
                torch.tensor(2.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(-2.0e-6, dtype=torch.float64),
                torch.tensor(-6.0e-6, dtype=torch.float64),
            ),
        )

        state = _GridState(grid)
        parameters = dict(state.named_parameters())
        buffers = dict(state.named_buffers())

        assert parameters["sample_spacing_y"] is spacing_y
        assert set(buffers) == {
            "sample_spacing_x",
            "first_sample_position_y",
            "first_sample_position_x",
        }
        assert state.value.sample_spacing[0] is spacing_y
        assert state.value.is_physically_equivalent_to(grid)

    def test_centered_grid_registers_only_independent_spacing(self) -> None:
        """
        中心网格不把派生原点缓存为长期模块状态
        """
        spacing_y = torch.nn.Parameter(
            torch.tensor(1.0e-6, dtype=torch.float64),
        )
        grid = SpatialGrid.centered(
            sample_counts=(4, 6),
            sample_spacing=(
                spacing_y,
                torch.tensor(2.0e-6, dtype=torch.float64),
            ),
        )
        state = _GridState(grid)

        assert set(state.state_dict()) == {
            "sample_spacing_y",
            "sample_spacing_x",
        }
        before = state.value.first_sample_position[0]
        with torch.no_grad():
            spacing_y.add_(0.5e-6)
        after = state.value.first_sample_position[0]

        assert before is not after
        torch.testing.assert_close(
            after,
            torch.tensor(-3.0e-6, dtype=torch.float64),
        )

    def test_state_dict_roundtrip_rebuilds_the_same_grid(self) -> None:
        """
        网格连续状态经标准 state_dict 往返后由同一适配器重建
        """
        source = _GridState(
            SpatialGrid(
                sample_counts=(4, 6),
                sample_spacing=(
                    torch.tensor(1.0e-6, dtype=torch.float64),
                    torch.tensor(2.0e-6, dtype=torch.float64),
                ),
                first_sample_position=(
                    torch.tensor(-2.0e-6, dtype=torch.float64),
                    torch.tensor(-6.0e-6, dtype=torch.float64),
                ),
            ),
        )
        restored = _GridState(
            SpatialGrid(
                sample_counts=(4, 6),
                sample_spacing=(
                    torch.tensor(4.0e-6, dtype=torch.float64),
                    torch.tensor(5.0e-6, dtype=torch.float64),
                ),
                first_sample_position=(
                    torch.tensor(0.0, dtype=torch.float64),
                    torch.tensor(0.0, dtype=torch.float64),
                ),
            ),
        )

        restored.load_state_dict(source.state_dict())

        assert restored.value.is_physically_equivalent_to(source.value)

    def test_module_device_move_keeps_float64_precision(self) -> None:
        """
        模块设备迁移保持 float64 精度；固定双精度下网格状态不降到单精度
        """
        spacing_y = torch.nn.Parameter(
            torch.tensor(1.0e-6, dtype=torch.float64),
        )
        state = _GridState(
            SpatialGrid.centered(
                sample_counts=(4, 6),
                sample_spacing=(
                    spacing_y,
                    torch.tensor(2.0e-6, dtype=torch.float64),
                ),
            ),
        )

        state.to(device="meta")
        moved_values = (
            *state.value.sample_spacing,
            *state.value.first_sample_position,
        )

        assert all(value.device.type == "meta" for value in moved_values)
        assert all(value.dtype is torch.float64 for value in moved_values)

    @pytest.mark.parametrize(
        "is_centered",
        (False, True),
    )
    def test_nonleaf_trainable_state_is_rejected(
        self,
        is_centered: bool,
    ) -> None:
        """
        无法按次重建公式的非叶可微张量不得成为长期网格状态
        """
        source = torch.nn.Parameter(
            torch.tensor(0.5e-6, dtype=torch.float64),
        )
        derived_spacing = source * 2.0
        spacing = (
            derived_spacing,
            torch.tensor(2.0e-6, dtype=torch.float64),
        )
        if is_centered:
            grid = SpatialGrid.centered(
                sample_counts=(4, 6),
                sample_spacing=spacing,
            )
        else:
            grid = SpatialGrid(
                sample_counts=(4, 6),
                sample_spacing=spacing,
                first_sample_position=(
                    torch.tensor(-2.0e-6, dtype=torch.float64),
                    torch.tensor(-6.0e-6, dtype=torch.float64),
                ),
            )

        with pytest.raises(
            ValueError,
            match="grid_state_nonleaf_tensor_unsupported",
        ):
            _GridState(grid)

    def test_explicit_nonleaf_position_is_rejected(self) -> None:
        """
        显式原点的派生公式同样不得被伪装成长寿命 Buffer
        """
        source = torch.nn.Parameter(
            torch.tensor(-1.0e-6, dtype=torch.float64),
        )
        grid = SpatialGrid(
            sample_counts=(4, 6),
            sample_spacing=(
                torch.tensor(1.0e-6, dtype=torch.float64),
                torch.tensor(2.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                source * 2.0,
                torch.tensor(-6.0e-6, dtype=torch.float64),
            ),
        )

        with pytest.raises(
            ValueError,
            match="grid_state_nonleaf_tensor_unsupported",
        ):
            _GridState(grid)


class TestSpatialGridOrientation:
    """
    真实网格朝向（网格方向是显式状态）
    """

    def test_default_orientation_is_increasing(self) -> None:
        """
        默认朝向为递增/递增，保持递增坐标约定
        """
        grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(1.0e-6, 1.0e-6),
            first_sample_position=(0.0, 0.0),
        )
        assert grid.orientation == ("increasing", "increasing")

    def test_orientation_accepted(self) -> None:
        """
        显式递减朝向被接受并保留
        """
        grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(1.0e-6, 1.0e-6),
            first_sample_position=(0.0, 0.0),
            orientation=("decreasing", "increasing"),
        )
        assert grid.orientation == ("decreasing", "increasing")

    def test_invalid_orientation_rejected(self) -> None:
        """
        非法朝向值以稳定身份拒绝
        """
        with pytest.raises(
            ValueError,
            match="spatial_grid_orientation_invalid",
        ):
            SpatialGrid(
                sample_counts=(4, 4),
                sample_spacing=(1.0e-6, 1.0e-6),
                first_sample_position=(0.0, 0.0),
                orientation=("sideways", "increasing"),
            )

    def test_signed_spacing_increasing(self) -> None:
        """
        递增朝向 ⇒ 带符号步进为正间距
        """
        grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(2.0e-6, 3.0e-6),
            first_sample_position=(0.0, 0.0),
        )
        assert grid.signed_spacing == (2.0e-6, 3.0e-6)

    def test_signed_spacing_decreasing(self) -> None:
        """
        递减朝向 ⇒ 带符号步进为负间距（坐标随索引递减）
        """
        grid = SpatialGrid(
            sample_counts=(4, 4),
            sample_spacing=(2.0e-6, 3.0e-6),
            first_sample_position=(0.0, 0.0),
            orientation=("decreasing", "decreasing"),
        )
        assert grid.signed_spacing == (-2.0e-6, -3.0e-6)

    def test_centered_decreasing_first_sample_at_positive_edge(self) -> None:
        """
        递减朝向中心网格 ⇒ 首样本在正边，为递增的镜像
        """
        counts = (8, 8)
        spacing = (1.0e-6, 1.0e-6)
        grid_inc = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=spacing,
        )
        grid_dec = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=spacing,
            orientation=("decreasing", "decreasing"),
        )
        # 递增首样本在 −(N//2)·s，递减首样本在 +(N//2)·s（镜像，符号步进为负）
        assert grid_inc.first_sample_position == (-4.0e-6, -4.0e-6)
        assert grid_dec.first_sample_position == (4.0e-6, 4.0e-6)
        assert grid_dec.signed_spacing == (-1.0e-6, -1.0e-6)
        # 索引 0 坐标 = 首样本（正边），索引增 ⇒ 坐标减
        first_y = 4.0e-6 + 0 * grid_dec.signed_spacing[0]
        second_y = 4.0e-6 + 1 * grid_dec.signed_spacing[0]
        assert first_y == 4.0e-6
        assert second_y == 3.0e-6

    def test_orientation_distinguishes_grid_identity(self) -> None:
        """
        仅朝向不同的两网格须不相等（坐标身份参与契约）
        """
        base: dict[str, Any] = dict(
            sample_counts=(4, 4),
            sample_spacing=(1.0e-6, 1.0e-6),
            first_sample_position=(0.0, 0.0),
        )
        grid_inc = SpatialGrid(
            orientation=("increasing", "increasing"),
            **base,
        )
        grid_dec = SpatialGrid(
            orientation=("decreasing", "decreasing"),
            **base,
        )
        assert not grid_inc.is_physically_equivalent_to(grid_dec)


class TestDestinationGrid:
    """
    目标网格就是完整的 ``SpatialGrid``，不另设装饰类型
    """

    def test_decorative_destination_types_are_absent(self) -> None:
        """
        目标网格公共表面不得残留 Aligned/Shifted/联合别名
        """
        assert not hasattr(grid_module, "AlignedDestinationGrid")
        assert not hasattr(grid_module, "ShiftedDestinationGrid")
        assert not hasattr(grid_module, "DestinationGrid")


class TestPropagationExterior:
    """
    传播外部语义（规约"传播外部"：周期延拓/孤立零场嵌埋）
    """

    def test_periodic_and_isolated_values(self) -> None:
        """
        两种外部枚举值存在且互斥
        """
        assert PropagationExterior.PERIODIC.value == "periodic"
        assert PropagationExterior.ISOLATED.value == "isolated"
        assert PropagationExterior.PERIODIC is not PropagationExterior.ISOLATED
