
from __future__ import annotations

import ast
from collections.abc import Callable
import inspect
import math
import pathlib

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics import ConstantMedium, RayBundle, Spectrum, Vacuum
from chromatix_next.optics.element import refract_at
from chromatix_next.optics.paraxial_ray_transfer import (
    compose_ray_transfer_matrices,
    free_space_ray_transfer_matrix,
    spherical_refraction_ray_transfer_matrix,
    thin_lens_ray_transfer_matrix,
)
from chromatix_next.optics.propagation import trace_to
from chromatix_next.optics.ray_bundle import RAY_STATUS_ACTIVE
from chromatix_next.optics.surface import Plane, Sphere
from tests.architecture._python_import_facts import read_python_imports
from tests.optics._valid_ray_inputs import _transverse_polarization_for_direction

_RayTransferMatrixConstructor = Callable[..., torch.Tensor]


def _matrix_reference(
    rows: tuple[float, float, float, float],
) -> torch.Tensor:
    return torch.tensor(rows, dtype=torch.float64).reshape(2, 2)


class TestParaxialRayTransferMatrixFormulas:
    """
    paraxial ray-transfer matrix 矩阵与解析公式逐项一致
    """

    @pytest.mark.parametrize("distance", [0.0, 0.3, 1.0e-3])
    def test_free_space_matrix_matches_reference(
        self,
        distance: float,
    ) -> None:
        """
        自由空间 paraxial ray-transfer matrix = [[1, d], [0, 1]]
        """

        matrix = free_space_ray_transfer_matrix(distance, device=torch.device("cpu"))
        assert matrix.dtype is torch.float64
        expected = _matrix_reference((1.0, distance, 0.0, 1.0))
        assert torch.allclose(matrix, expected)

    @pytest.mark.parametrize("focal_length", [0.2, -0.1, 5.0])
    def test_thin_lens_matrix_matches_reference(
        self,
        focal_length: float,
    ) -> None:
        """
        薄透镜 paraxial ray-transfer matrix = [[1, 0], [-1/f, 1]]
        """

        matrix = thin_lens_ray_transfer_matrix(focal_length, device=torch.device("cpu"))
        assert matrix.dtype is torch.float64
        expected = _matrix_reference((1.0, 0.0, -1.0 / focal_length, 1.0))
        assert torch.allclose(matrix, expected)

    @pytest.mark.parametrize(
        ("curvature", "incident_index", "destination_index"),
        [
            (10.0, 1.0, 1.5),
            (-5.0, 1.5, 1.0),
            (2.0, 1.0, 1.0),
        ],
    )
    def test_spherical_refraction_matrix_matches_reference(
        self,
        curvature: float,
        incident_index: float,
        destination_index: float,
    ) -> None:
        """
        球面折射 paraxial ray-transfer matrix = [[1, 0], [-(n_t-n_i)c/n_t, n_i/n_t]]
        """

        matrix = spherical_refraction_ray_transfer_matrix(
            curvature,
            incident_index,
            destination_index,
            device=torch.device("cpu"),
        )
        assert matrix.dtype is torch.float64
        expected = _matrix_reference(
            (
                1.0,
                0.0,
                -(destination_index - incident_index)
                * curvature
                / destination_index,
                incident_index / destination_index,
            ),
        )
        assert torch.allclose(matrix, expected)


def test_compose_ray_transfer_matrices_chains_in_propagation_order() -> None:
    """
    compose 按光线前进顺序链乘：先折射、后自由空间 ⇒ M = free_space @ refract
    """

    incident_index = 1.0
    destination_index = 1.5
    curvature = 10.0
    image_distance = 0.3
    refract = spherical_refraction_ray_transfer_matrix(
        curvature,
        incident_index,
        destination_index,
        device=torch.device("cpu"),
    )
    free_space = free_space_ray_transfer_matrix(
        image_distance,
        device=torch.device("cpu"),
    )
    composed = compose_ray_transfer_matrices([refract, free_space])
    assert torch.allclose(composed, free_space @ refract)


def test_compose_ray_transfer_matrices_rejects_invalid_inputs() -> None:
    """
    空序列与形状不一致矩阵被拒绝（稳定身份）
    """

    with pytest.raises(
        OpticalValueError,
        match="paraxial_ray_transfer_compose_empty",
    ):
        compose_ray_transfer_matrices([])
    matrix = free_space_ray_transfer_matrix(0.1, device=torch.device("cpu"))
    bad = torch.zeros((3, 3), dtype=torch.float64)
    with pytest.raises(
        OpticalValueError,
        match="paraxial_ray_transfer_compose_matrix_invalid",
    ):
        compose_ray_transfer_matrices([matrix, bad])


class TestParaxialRayTransferInputValidation:
    """
    paraxial ray-transfer matrix 公开输入的稳定错误身份
    """

    def test_free_space_non_finite_rejected(self) -> None:
        """
        非有限的自由空间距离被稳定错误身份拒绝
        """
        with pytest.raises(
            OpticalValueError,
            match="paraxial_ray_transfer_free_space_distance_invalid",
        ):
            free_space_ray_transfer_matrix(float("inf"), device=torch.device("cpu"))

    def test_thin_lens_non_finite_rejected(self) -> None:
        """
        非有限的薄透镜焦距被稳定错误身份拒绝
        """
        with pytest.raises(
            OpticalValueError,
            match="paraxial_ray_transfer_thin_lens_focal_length_invalid",
        ):
            thin_lens_ray_transfer_matrix(float("nan"), device=torch.device("cpu"))

    def test_curvature_non_finite_rejected(self) -> None:
        """
        非有限的球面曲率被稳定错误身份拒绝
        """
        with pytest.raises(
            OpticalValueError,
            match="paraxial_ray_transfer_spherical_refraction_curvature_invalid",
        ):
            spherical_refraction_ray_transfer_matrix(
                float("inf"),
                1.0,
                1.5,
                device=torch.device("cpu"),
            )

    def test_incident_index_non_finite_rejected(self) -> None:
        """
        非有限的入射方折射率被稳定错误身份拒绝
        """
        with pytest.raises(
            OpticalValueError,
            match="paraxial_ray_transfer_spherical_refraction_incident_index_invalid",
        ):
            spherical_refraction_ray_transfer_matrix(
                10.0,
                float("nan"),
                1.5,
                device=torch.device("cpu"),
            )

    def test_destination_index_nonpositive_rejected(self) -> None:
        """
        非正的像方折射率被稳定错误身份拒绝
        """
        with pytest.raises(
            OpticalValueError,
            match=(
                "paraxial_ray_transfer_spherical_refraction_"
                "destination_index_nonpositive"
            ),
        ):
            spherical_refraction_ray_transfer_matrix(
                10.0,
                1.0,
                0.0,
                device=torch.device("cpu"),
            )

    def test_zero_focal_length_rejected(self) -> None:
        """
        零焦距薄透镜被稳定错误身份拒绝
        """
        with pytest.raises(
            OpticalValueError,
            match="paraxial_ray_transfer_thin_lens_focal_length_zero",
        ):
            thin_lens_ray_transfer_matrix(0.0, device=torch.device("cpu"))


def _parallel_bundle_at_height(height: float) -> RayBundle:
    gap = 0.05
    spectrum = Spectrum.monochromatic(wavelength=5.0e-7)
    position = torch.tensor(
        [[[0.0, height, -gap]]],
        dtype=torch.float64,
    )
    direction = torch.tensor(
        [[[0.0, 0.0, 1.0]]],
        dtype=torch.float64,
    )
    power = torch.ones((1, 1), dtype=torch.float64)
    optical_path = torch.zeros((1, 1), dtype=torch.float64)
    status = torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8)
    return RayBundle(
        position=position,
        direction=direction,
        polarization_vector=_transverse_polarization_for_direction(
            direction
        ),
        power=power,
        refractive_index=torch.ones_like(power),
        optical_path=optical_path,
        status=status,
        spectrum=spectrum,
    )


def _exact_ray_image_height(
    *,
    launch_height: float,
    image_distance: float,
    radius_of_curvature: float,
    destination_index: float,
) -> float:
    curvature = 1.0 / radius_of_curvature
    bundle = _parallel_bundle_at_height(launch_height)
    surface = Sphere(
        vertex=(0.0, 0.0, 0.0),
        radius_of_curvature=radius_of_curvature,
    )
    glass = ConstantMedium(index=destination_index)
    refracted = refract_at(
        bundle,
        surface=surface,
        destination_medium=glass,
    )
    image_plane = Plane(origin=(0.0, 0.0, image_distance))
    imaged = trace_to(refracted, surface=image_plane)
    return float(imaged.position[0, 0, 1].item())


class TestExactRayConvergesToParaxialRayTransferInParaxialLimit:
    """
        Exact rays converge to the paraxial prediction and depart outside it.
    """

    def test_paraxial_image_height_matches_paraxial_ray_transfer(self) -> None:
        """
        Small-height exact and paraxial predictions agree.
        """

        radius_of_curvature = 0.1
        incident_index = 1.0
        destination_index = 1.5
        curvature = 1.0 / radius_of_curvature
        image_distance = 0.12
        launch_height = 1.0e-5
        matrix = compose_ray_transfer_matrices(
            [
                spherical_refraction_ray_transfer_matrix(
                    curvature,
                    incident_index,
                    destination_index,
                    device=torch.device("cpu"),
                ),
                free_space_ray_transfer_matrix(
                    image_distance,
                    device=torch.device("cpu"),
                ),
            ],
        )
        paraxial_ray_transfer_height = float(matrix[0, 0].item()) * launch_height
        exact_height = _exact_ray_image_height(
            launch_height=launch_height,
            image_distance=image_distance,
            radius_of_curvature=radius_of_curvature,
            destination_index=destination_index,
        )
        # float64 下小高度 paraxial 残差远小于 launch_height 的 1e-6 相对量级
        assert math.isclose(
            exact_height,
            paraxial_ray_transfer_height,
            rel_tol=1.0e-7,
            abs_tol=1.0e-12,
        )

    def test_exact_ray_converges_across_decreasing_scales(
        self,
    ) -> None:
        """exact-Ray 像高残差在至少三个递减高度上呈 paraxial 渐近趋势

        Independent evidence uses a sphere and free-space chain.
        Use three decreasing heights; the residual must decrease with height.
        This independently anchors the paraxial limit.
        的 small-height 极限锚定而非自比。残差单调下降且最大尺度的相对残差远大于
        最小尺度，确保趋势可识别而非浮点噪声。
        """

        radius_of_curvature = 0.1
        destination_index = 1.5
        curvature = 1.0 / radius_of_curvature
        image_distance = 0.12
        matrix = compose_ray_transfer_matrices(
            [
                spherical_refraction_ray_transfer_matrix(
                    curvature,
                    1.0,
                    destination_index,
                    device=torch.device("cpu"),
                ),
                free_space_ray_transfer_matrix(
                    image_distance,
                    device=torch.device("cpu"),
                ),
            ],
        )
        paraxial_ray_transfer_multiplier = float(matrix[0, 0].item())
        launch_heights = (1.0e-3, 1.0e-5, 1.0e-7)
        relative_residuals: list[float] = []
        for launch_height in launch_heights:
            exact_height = _exact_ray_image_height(
                launch_height=launch_height,
                image_distance=image_distance,
                radius_of_curvature=radius_of_curvature,
                destination_index=destination_index,
            )
            absolute_error = abs(
                exact_height - paraxial_ray_transfer_multiplier * launch_height,
            )
            # 相对残差按入射高度归一化：球面像差对像高的 O(h²) 贡献会在这里出现
            relative_residuals.append(absolute_error / launch_height)
        # 三个尺度上相对残差须单调下降（paraxial 极限）
        assert relative_residuals[0] > relative_residuals[1]
        assert relative_residuals[1] > relative_residuals[2]
        # 最大尺度相对残差比最小尺度大若干量级，证明这是真正的渐近趋势
        assert relative_residuals[0] > 1.0e3 * relative_residuals[2]

    def test_focal_distance_recovers_paraxial_ray_transfer_prediction(self) -> None:
        """
        Exact-ray height crosses zero at the predicted focal distance.
        """

        radius_of_curvature = 0.1
        incident_index = 1.0
        destination_index = 1.5
        curvature = 1.0 / radius_of_curvature
        # Paraxial focal distance: f' = n_t / ((n_t - n_i) * c)
        focal_distance = destination_index / (
            (destination_index - incident_index) * curvature
        )
        launch_height = 1.0e-6
        exact_at_focus = _exact_ray_image_height(
            launch_height=launch_height,
            image_distance=focal_distance,
            radius_of_curvature=radius_of_curvature,
            destination_index=destination_index,
        )
        # 焦点处高度应近零（受 launch_height 与球面像差的二阶量级限制）
        assert abs(exact_at_focus) < 1.0e-6 * launch_height / (
            radius_of_curvature * 1.0e3
        ) or abs(exact_at_focus) < 1.0e-9

    def test_nonparaxial_height_departs_from_paraxial_ray_transfer(self) -> None:
        """
        Large height shows spherical aberration beyond the paraxial residual.
        """

        radius_of_curvature = 0.1
        destination_index = 1.5
        curvature = 1.0 / radius_of_curvature
        image_distance = 0.12
        matrix = compose_ray_transfer_matrices(
            [
                spherical_refraction_ray_transfer_matrix(
                    curvature,
                    1.0,
                    destination_index,
                    device=torch.device("cpu"),
                ),
                free_space_ray_transfer_matrix(
                    image_distance,
                    device=torch.device("cpu"),
                ),
            ],
        )
        small_height = 1.0e-5
        large_height = 2.0e-2
        small_error = abs(
            _exact_ray_image_height(
                launch_height=small_height,
                image_distance=image_distance,
                radius_of_curvature=radius_of_curvature,
                destination_index=destination_index,
            )
            - float(matrix[0, 0].item()) * small_height
        )
        large_error = abs(
            _exact_ray_image_height(
                launch_height=large_height,
                image_distance=image_distance,
                radius_of_curvature=radius_of_curvature,
                destination_index=destination_index,
            )
            - float(matrix[0, 0].item()) * large_height
        )
        # 非paraxial 误差不仅更大，其相对偏差也显著超出 paraxial 残差
        assert large_error > 1.0e3 * small_error
        assert large_error / large_height > small_error / small_height


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"


def _paraxial_ray_transfer_module_path() -> pathlib.Path:
    return pathlib.Path(inspect.getfile(compose_ray_transfer_matrices))


class TestParaxialRayTransferImportIndependence:
    """
    The matrix module is independent of exact-ray and Snell implementations.
    """

    @pytest.mark.parametrize(
        "forbidden_module_substring",
        (
            "surface",
            "_ray_surface_advance",
            "ray_bundle",
            "element",
            "propagation",
            "medium",
            "spectrum",
            "snell",
        ),
    )
    def test_paraxial_ray_transfer_module_does_not_import_exact_ray_or_snell(
        self,
        forbidden_module_substring: str,
    ) -> None:
        """
        paraxial ray-transfer matrix 源文件不导入任何精确 Ray 求交 / Snell / 物理值模块

        The AST gate permits only stdlib, torch, and errors imports.
        It must not load exact-ray, surface-intersection, or Snell modules.
        成可机器验证的事实。
        """

        imported_modules = read_python_imports(
            _paraxial_ray_transfer_module_path(),
            _SRC_ROOT,
        ).imported_modules
        for imported in imported_modules:
            assert forbidden_module_substring not in imported, (
                f"paraxial_ray_transfer.py forbids imports containing "
                f"发现 {imported!r}"
            )

    def test_paraxial_ray_transfer_module_bindings_do_not_reference_exact_ray_symbols(
        self,
    ) -> None:
        """
        paraxial ray-transfer matrix 模块内未绑定 refract_at / trace_to / Sphere / Plane
        / Snell 等符号
        """
        source = _paraxial_ray_transfer_module_path().read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_names = {
            "refract_at",
            "reflect_at",
            "trace_to",
            "Sphere",
            "Plane",
            "ConicEvenAsphere",
            "RayBundle",
            "Medium",
            "Spectrum",
            "snell",
            "intersect",
        }
        referenced: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                referenced.add(node.id)
            elif isinstance(node, ast.Attribute):
                referenced.add(node.attr)
        overlap = referenced & forbidden_names
        assert not overlap, (
            f"paraxial_ray_transfer.py forbids exact-ray symbol {overlap!r}"
        )


class TestParaxialRayTransferFixedDoubleContract:
    """
    Fixed-double input contract: float64, no gradients, and finite real scalars.
    """

    @pytest.mark.parametrize(
        ("constructor", "args", "identity_prefix"),
        (
            (
                free_space_ray_transfer_matrix,
                (0.1,),
                "paraxial_ray_transfer_free_space_distance_invalid",
            ),
            (
                thin_lens_ray_transfer_matrix,
                (0.1,),
                "paraxial_ray_transfer_thin_lens_focal_length_invalid",
            ),
            (
                spherical_refraction_ray_transfer_matrix,
                (10.0, 1.0, 1.5),
                "paraxial_ray_transfer_spherical_refraction_curvature_invalid",
            ),
        ),
    )
    def test_float32_scalar_tensor_input_rejected(
        self,
        constructor: _RayTransferMatrixConstructor,
        args: tuple[float, ...],
        identity_prefix: str,
    ) -> None:
        """
        Float32 scalar inputs must fail with the stable invalid identity.
        """
        f32_args = tuple(
            torch.tensor(value, dtype=torch.float32) for value in args
        )
        with pytest.raises(OpticalValueError, match=identity_prefix):
            constructor(*f32_args, device=torch.device("cpu"))

    def test_float32_compose_matrix_rejected(self) -> None:
        """
        float64 compose 矩阵链中夹带 float32 矩阵须以
        paraxial_ray_transfer_compose_matrix_invalid 拒绝
        """
        valid = free_space_ray_transfer_matrix(0.1, device=torch.device("cpu"))
        invalid = torch.eye(2, dtype=torch.float32)
        with pytest.raises(
            OpticalValueError,
            match="paraxial_ray_transfer_compose_matrix_invalid",
        ):
            compose_ray_transfer_matrices([valid, invalid])
        with pytest.raises(
            OpticalValueError,
            match="paraxial_ray_transfer_compose_matrix_invalid",
        ):
            compose_ray_transfer_matrices([invalid, valid])

    @pytest.mark.parametrize(
        ("constructor", "args", "identity_prefix"),
        (
            (
                free_space_ray_transfer_matrix,
                (0.1,),
                "paraxial_ray_transfer_free_space_distance_invalid",
            ),
            (
                thin_lens_ray_transfer_matrix,
                (0.1,),
                "paraxial_ray_transfer_thin_lens_focal_length_invalid",
            ),
            (
                spherical_refraction_ray_transfer_matrix,
                (10.0, 1.0, 1.5),
                "paraxial_ray_transfer_spherical_refraction_curvature_invalid",
            ),
        ),
    )
    def test_trainable_tensor_input_rejected(
        self,
        constructor: _RayTransferMatrixConstructor,
        args: tuple[float, ...],
        identity_prefix: str,
    ) -> None:
        """
        requires_grad=True float64 张量作为 paraxial ray-transfer matrix 输入须以
        *_invalid 稳定身份被拒绝

        The paraxial reference is independent and is not a trainable backend.
        不再"隐藏切断"——可训练图根本进不来，谈不上被悄悄 detach。
        """
        trainable_args = tuple(
            torch.tensor(value, dtype=torch.float64, requires_grad=True)
            for value in args
        )
        with pytest.raises(OpticalValueError, match=identity_prefix):
            constructor(*trainable_args, device=torch.device("cpu"))

    def test_trainable_compose_matrix_rejected(self) -> None:
        """
        A trainable matrix must be rejected with the stable compose identity.
        """
        trainable = torch.eye(2, dtype=torch.float64, requires_grad=True)
        valid = free_space_ray_transfer_matrix(0.1, device=torch.device("cpu"))
        with pytest.raises(
            OpticalValueError,
            match="paraxial_ray_transfer_compose_matrix_invalid",
        ):
            compose_ray_transfer_matrices([valid, trainable])

    def test_complex_scalar_tensor_input_rejected(self) -> None:
        """
        复数张量作为 paraxial ray-transfer matrix 物理量须以 *_invalid 拒绝
        """
        complex_distance = torch.tensor(0.1 + 0.0j, dtype=torch.complex128)
        with pytest.raises(
            OpticalValueError,
            match="paraxial_ray_transfer_free_space_distance_invalid",
        ):
            free_space_ray_transfer_matrix(complex_distance, device=torch.device("cpu"))

    def test_python_float_input_remains_float64_independent_of_default(
        self,
    ) -> None:
        """
        Python scalars still produce fixed-double paraxial matrices.

        构造与 ``torch.get_default_dtype()`` 无关。
        """
        original_default = torch.get_default_dtype()
        matrix_default = free_space_ray_transfer_matrix(0.1, device=torch.device("cpu"))
        torch.set_default_dtype(torch.float32)
        try:
            matrix_under_f32_default = free_space_ray_transfer_matrix(
                0.1,
                device=torch.device("cpu"),
            )
        finally:
            torch.set_default_dtype(original_default)
        assert matrix_default.dtype is torch.float64
        assert matrix_under_f32_default.dtype is torch.float64
        torch.testing.assert_close(matrix_default, matrix_under_f32_default)

    def test_no_hidden_float_detachment_of_trainable_input(self) -> None:
        """
        Trainable input is rejected directly; no hidden float conversion may detach it.

        This proves that a detached matrix can never be returned successfully.
        一个被 detach 的矩阵；这里验证它根本进不来。
        """
        trainable_distance = torch.tensor(
            0.1,
            dtype=torch.float64,
            requires_grad=True,
        )
        with pytest.raises(OpticalValueError):
            matrix = free_space_ray_transfer_matrix(
                trainable_distance,
                device=torch.device("cpu"),
            )
            # 若实现走错路悄悄 detach，这里就走到——后卫断言让它响铃
            assert matrix.requires_grad is False  # pragma: no cover


class TestParaxialRayTransferCompositionOrder:
    """
    compose 顺序为 M_n...M_2 M_1（先前进者后乘）；非交换矩阵可识别
    """

    def test_noncommuting_matrices_distinguish_order(self) -> None:
        """
        自由空间与薄透镜非交换：compose([M1, M2]) ≠ compose([M2, M1])

        手算 [[1, d],[0,1]] 与 [[1,0],[-1/f, 1]]：
        先自由空间后透镜（[M_free, M_lens] ⇒ M_lens @ M_free）=
        [[1, d],[-1/f, 1 - d/f]]
        先透镜后自由空间（[M_lens, M_free] ⇒ M_free @ M_lens）=
        [[1 - d/f, d],[-1/f, 1]]
        两者 (0,0) 与 (1,1) 元素交换，明显不同。
        """
        distance = 0.3
        focal = 0.2
        free = free_space_ray_transfer_matrix(distance, device=torch.device("cpu"))
        lens = thin_lens_ray_transfer_matrix(focal, device=torch.device("cpu"))
        free_then_lens = compose_ray_transfer_matrices([free, lens])
        lens_then_free = compose_ray_transfer_matrices([lens, free])
        # 手算参考（注意 compose 顺序：先入后乘）
        expected_free_then_lens = torch.tensor(
            [
                [1.0, distance],
                [-1.0 / focal, 1.0 - distance / focal],
            ],
            dtype=torch.float64,
        )
        expected_lens_then_free = torch.tensor(
            [
                [1.0 - distance / focal, distance],
                [-1.0 / focal, 1.0],
            ],
            dtype=torch.float64,
        )
        torch.testing.assert_close(free_then_lens, expected_free_then_lens)
        torch.testing.assert_close(lens_then_free, expected_lens_then_free)
        # 显式验证两种顺序结果不同（非交换）
        assert not torch.allclose(free_then_lens, lens_then_free)

    def test_three_matrix_chain_in_propagation_order(self) -> None:
        """
        三段链 [折射, 自由空间, 透镜] ⇒ 复合 = M_lens @ M_free @ M_refract
        """
        refract = spherical_refraction_ray_transfer_matrix(
            10.0,
            1.0,
            1.5,
            device=torch.device("cpu"),
        )
        free = free_space_ray_transfer_matrix(0.05, device=torch.device("cpu"))
        lens = thin_lens_ray_transfer_matrix(0.2, device=torch.device("cpu"))
        composed = compose_ray_transfer_matrices([refract, free, lens])
        torch.testing.assert_close(composed, lens @ free @ refract)


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA paraxial ray-transfer matrix 证据需要可用的 CUDA 设备",
)
class TestParaxialRayTransferCudaEvidence:
    """
    paraxial ray-transfer matrix 在 CUDA 设备上以 float64 运行；CPU 与 CUDA 构造一致
    """

    def test_matrices_are_float64_on_cuda(self) -> None:
        """
        四个构造器在 CUDA 上返回 float64、位于 CUDA 设备的 (2,2) 矩阵
        """
        device = torch.device("cuda")
        free = free_space_ray_transfer_matrix(0.1, device=device)
        lens = thin_lens_ray_transfer_matrix(0.2, device=device)
        refract = spherical_refraction_ray_transfer_matrix(
            10.0,
            1.0,
            1.5,
            device=device,
        )
        for matrix in (free, lens, refract):
            assert matrix.dtype is torch.float64
            assert matrix.device.type == "cuda"
            assert matrix.shape == (2, 2)

        composed = compose_ray_transfer_matrices([refract, free, lens])
        assert composed.dtype is torch.float64
        assert composed.device.type == "cuda"

    def test_cpu_and_cuda_constructions_agree(self) -> None:
        """
        同参数 CPU/CUDA 构造给出数值一致的 paraxial ray-transfer matrix 矩阵
        """
        cpu_refract = spherical_refraction_ray_transfer_matrix(
            10.0,
            1.0,
            1.5,
            device=torch.device("cpu"),
        )
        cuda_refract = spherical_refraction_ray_transfer_matrix(
            10.0,
            1.0,
            1.5,
            device=torch.device("cuda"),
        )
        torch.testing.assert_close(
            cpu_refract,
            cuda_refract.to(device="cpu"),
        )

        cpu_chain = compose_ray_transfer_matrices(
            [
                cpu_refract,
                free_space_ray_transfer_matrix(0.05, device=torch.device("cpu")),
                thin_lens_ray_transfer_matrix(0.2, device=torch.device("cpu")),
            ],
        )
        cuda_chain = compose_ray_transfer_matrices(
            [
                cuda_refract,
                free_space_ray_transfer_matrix(0.05, device=torch.device("cuda")),
                thin_lens_ray_transfer_matrix(0.2, device=torch.device("cuda")),
            ],
        )
        torch.testing.assert_close(
            cpu_chain,
            cuda_chain.to(device="cpu"),
        )
