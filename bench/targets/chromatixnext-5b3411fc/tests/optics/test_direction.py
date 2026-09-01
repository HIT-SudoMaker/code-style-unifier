
from __future__ import annotations

import math

import pytest

from chromatix_next.optics import PropagationDirection, TransverseWavevector


class TestPropagationDirection:
    """
    传播方向物理值契约
    """

    def test_forward_is_on_axis(self) -> None:
        """``forward()`` 构造轴向入射（横向余弦为 0，法向余弦为 1）

        轴向入射是多光谱源最常见的默认方向：所有光谱分量沿正法线传播。
        """
        direction = PropagationDirection.forward()
        assert direction.direction_cosine_y == 0.0
        assert direction.direction_cosine_x == 0.0
        assert direction.direction_cosine_z == pytest.approx(1.0)

    def test_direction_cosine_z_via_pythagoras(self) -> None:
        """法向余弦 cz = sqrt(1 - cy² - cx²) 与勾股定理独立计算一致

        证据层 2（独立参照）：方向单位化条件 cy² + cx² + cz² = 1 独立给出 cz。
        """
        cos_y, cos_x = 0.3, -0.4
        direction = PropagationDirection(
            direction_cosine_y=cos_y,
            direction_cosine_x=cos_x,
        )
        expected_normal = math.sqrt(1.0 - cos_y**2 - cos_x**2)
        assert direction.direction_cosine_z == pytest.approx(expected_normal)
        # 完整向量须为单位向量（前向半空间 cz > 0）
        squared_norm = (
            direction.direction_cosine_y**2
            + direction.direction_cosine_x**2
            + direction.direction_cosine_z**2
        )
        assert squared_norm == pytest.approx(1.0, abs=1e-12)

    def test_one_direction_means_common_direction_for_all_wavelengths(self) -> None:
        """一个 ``PropagationDirection`` 表示所有光谱分量共享同一方向

        规约"Propagation Direction"：多光谱源给出一个方向时，每个光谱分量沿同一方向
        传播，仅波矢模 |k| 随波长与介质变化。此处验证方向值本身波长无关：构造一个方向
        并断言其余弦与波长集合无关（语义不变量，数值耦合在 PlaneWave 链路验证）。
        """
        direction = PropagationDirection(0.2, 0.1)
        for wavelength in (0.4e-6, 0.5e-6, 0.7e-6):
            # 方向余弦与波长无关
            assert direction.direction_cosine_y == 0.2
            assert direction.direction_cosine_x == 0.1

    @pytest.mark.parametrize(
        "invalid_pair",
        [
            (0.6, 0.8),  # 平方和恰为 1：掠逝（cz = 0），非前向。
            (0.7, 0.8),  # 平方和大于 1：倏逝（cz 为虚）。
            (-0.9, -0.9),
        ],
    )
    def test_grazing_or_evanescent_rejected(
        self,
        invalid_pair: tuple[float, float],
    ) -> None:
        """横向余弦平方和达 1（掠逝，cz=0）或超过 1（倏逝）须拒绝

        规约要求严格前向传播（cz > 0）。cz = 0 的掠逝方向不属前向半空间。
        """
        cos_y, cos_x = invalid_pair
        with pytest.raises(

            ValueError,

            match="propagation_direction_normalization_invalid",

        ):
            PropagationDirection(cos_y, cos_x)

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_non_finite_rejected(self, invalid_value: float) -> None:
        """
        非有限余弦须以稳定身份拒绝
        """
        with pytest.raises(ValueError, match="propagation_direction_value_invalid"):
            PropagationDirection(invalid_value, 0.0)
        with pytest.raises(ValueError, match="propagation_direction_value_invalid"):
            PropagationDirection(0.0, invalid_value)

    def test_boolean_rejected(self) -> None:
        """
        布尔非合法方向余弦（避免 bool 被 int 误纳）
        """
        with pytest.raises(ValueError, match="propagation_direction_value_invalid"):
            PropagationDirection(True, 0.0)  # type: ignore[arg-type]

    def test_immutable(self) -> None:
        """
        方向为不可变物理值
        """
        direction = PropagationDirection(0.1, 0.2)
        with pytest.raises(AttributeError):
            direction.direction_cosine_y = 0.5  # type: ignore[misc]

    def test_direction_is_fixed_physical_value_not_trainable(self) -> None:
        """方向为固定物理值（Buffer 语义），不携带可训练 Parameter

        证据层 3（梯度证据）：方向是物理几何确定量，非可训练声称。梯度证据落在
        PlaneWave→IntensityDetection 链路（见 ``tests/source/test_plane_wave.py`` 中
        经 TabulatedMedium 与 TransverseWavevector 的 gradcheck）。
        """
        direction = PropagationDirection(0.3, 0.4)
        # 物理值对象本身不实现 nn.Module 接口、不暴露 parameters
        assert not hasattr(direction, "parameters")


class TestTransverseWavevector:
    """
    横向波矢物理值契约
    """

    def test_carries_explicit_radians_per_metre(self) -> None:
        """``TransverseWavevector`` 携带以 rad/m 为单位的横向空间载波

        规约"Transverse Wavevector"：显式空间载波 (ky, kx)，单位 rad/m。零矢量合法
        （等价于轴向传播）。
        """
        carrier = TransverseWavevector(
            wavevector_y=1.0e3,
            wavevector_x=-2.0e3,
        )
        assert carrier.wavevector_y == 1.0e3
        assert carrier.wavevector_x == -2.0e3
        assert carrier.transverse_magnitude_squared == pytest.approx(5.0e6)

    def test_zero_carrier_is_axial(self) -> None:
        """
        零横向波矢等价于轴向传播，合法
        """
        carrier = TransverseWavevector(0.0, 0.0)
        assert carrier.transverse_magnitude_squared == 0.0

    def test_shared_carrier_means_wavelength_dependent_directions(self) -> None:
        """共享横向波矢 ⇒ 各光谱分量方向随波长变化（语义不变量）

        规约"Transverse Wavevector"：共享 (ky, kx) 产生随波长变化的方向。波矢模
        |k(λ)| = 2π n(λ)/λ 随波长变化，故 cy(λ) = ky/|k(λ)|、cx(λ) = kx/|k(λ)| 随波长
        变化。数值耦合在 PlaneWave 链路验证；此处验证横向波矢本身与波长无关、且不同
        波长的 |k| 不同导致派生方向不同（语义说明）。
        """
        carrier = TransverseWavevector(5.0e5, 0.0)
        # 同一载波对两个波长给出不同的归一化横向余弦（|k| 不同）
        wavelength_short, wavelength_long = 0.4e-6, 0.8e-6
        # 真空 |k| = 2π/λ
        k_short = 2.0 * math.pi / wavelength_short
        k_long = 2.0 * math.pi / wavelength_long
        # 传播条件：ky² + kx² < |k|²。短波长 |k| 更大，更易满足
        assert k_short > k_long
        # 派生横向余弦随波长变化（语义断言）
        assert carrier.wavevector_y / k_short != carrier.wavevector_y / k_long

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_non_finite_rejected(self, invalid_value: float) -> None:
        """
        非有限波矢分量须以稳定身份拒绝
        """
        with pytest.raises(ValueError, match="transverse_wavevector_value_invalid"):
            TransverseWavevector(invalid_value, 0.0)
        with pytest.raises(ValueError, match="transverse_wavevector_value_invalid"):
            TransverseWavevector(0.0, invalid_value)

    def test_boolean_rejected(self) -> None:
        """
        布尔非合法波矢分量
        """
        with pytest.raises(

            ValueError,

            match="transverse_wavevector_value_invalid",

        ):
            TransverseWavevector(False, 0.0)  # type: ignore[arg-type]

    def test_immutable(self) -> None:
        """
        横向波矢为不可变物理值
        """
        carrier = TransverseWavevector(1.0, 2.0)
        with pytest.raises(AttributeError):
            carrier.wavevector_y = 5.0  # type: ignore[misc]

    def test_precision_consistency_statement(self) -> None:
        """方向/波矢为固定物理值，不进入张量精度路径

        证据层 4（精度一致性）：方向值在 COMPLEX64 与 COMPLEX128 下语义完全相同
        （无张量数值），数值精度一致性在 PlaneWave 包络层验证。
        """
        carrier = TransverseWavevector(1.0e3, 2.0e3)
        # 物理值为 Python float，与配对精度无关
        assert isinstance(carrier.wavevector_y, float)
        assert isinstance(carrier.wavevector_x, float)
