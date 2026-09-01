from __future__ import annotations

from collections.abc import Callable
import copy
import math

import pytest
import torch

from chromatix_next.errors import (
    OpticalRuntimeError,
    OpticalTypeError,
    OpticalValueError,
)
from chromatix_next.optics.element.ideal_cube_beam_splitter import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
)
from chromatix_next.optics.element.ideal_planar_mirror import (
    IdealPlanarMirror,
    MirrorTerminal,
)
from tests.qualification.cube_oracles import (
    ROTATED_CUBE_POSE,
    OracleCoatingDiagonal,
    OracleRouteKind,
    OracleTerminal,
    coating_basis,
    coating_plane_normal,
    geometry_pair_kinds,
    terminal_frame_fixtures,
)


def _cube_geometry() -> dict[str, object]:
    return {
        "origin": (0.0, 0.0, 0.0),
        "route_right": (1.0, 0.0, 0.0),
        "route_top": (0.0, 1.0, 0.0),
        "coating_diagonal": CubeCoatingDiagonal.RISING,
    }


def _nbs(**replacements: object) -> IdealNonpolarizingCubeBeamSplitter:
    arguments = {
        **_cube_geometry(),
        "mixing_angle": math.pi / 4.0,
        **replacements,
    }
    return IdealNonpolarizingCubeBeamSplitter(**arguments)  # type: ignore[arg-type]


def _pbs(**replacements: object) -> IdealPolarizingCubeBeamSplitter:
    arguments = {
        **_cube_geometry(),
        **replacements,
    }
    return IdealPolarizingCubeBeamSplitter(**arguments)  # type: ignore[arg-type]


def _mirror(**replacements: object) -> IdealPlanarMirror:
    arguments = {
        "origin": (0.0, 0.0, 0.0),
        "outward_normal": (-1.0, 0.0, 0.0),
        "transverse_up": (0.0, 0.0, 1.0),
        **replacements,
    }
    return IdealPlanarMirror(**arguments)  # type: ignore[arg-type]


def _oracle_diagonal(
    diagonal: CubeCoatingDiagonal,
) -> OracleCoatingDiagonal:
    return OracleCoatingDiagonal(diagonal.value)


def _cube_terminal(terminal: OracleTerminal) -> CubeTerminal:
    return CubeTerminal(terminal.value)


# 该局部探针只记录故意失败的构造是否曾开始注册 owner 状态
class _RegistrationProbeNbs(IdealNonpolarizingCubeBeamSplitter):

    registration_calls = 0

    def register_buffer(  # type: ignore[override]
        self,
        name: str,
        tensor: torch.Tensor | None,
        persistent: bool = True,
    ) -> None:
        type(self).registration_calls += 1
        super().register_buffer(name, tensor, persistent)

    def register_parameter(  # type: ignore[override]
        self,
        name: str,
        parameter: torch.nn.Parameter | None,
    ) -> None:
        type(self).registration_calls += 1
        super().register_parameter(name, parameter)


def test_closed_directional_enums_have_only_the_frozen_values() -> None:
    """
    三个 string enum 不留任意 Terminal 或 diagonal 扩展入口
    """
    assert tuple(CubeTerminal) == (
        CubeTerminal.LEFT,
        CubeTerminal.TOP,
        CubeTerminal.RIGHT,
        CubeTerminal.BOTTOM,
    )
    assert tuple(CubeCoatingDiagonal) == (
        CubeCoatingDiagonal.RISING,
        CubeCoatingDiagonal.FALLING,
    )
    assert tuple(MirrorTerminal) == (MirrorTerminal.FRONT,)


@pytest.mark.parametrize("owner_factory", (_nbs, _pbs))
@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
def test_cube_topology_matches_independent_geometry_oracle(
    owner_factory: Callable[..., torch.nn.Module],
    diagonal: CubeCoatingDiagonal,
) -> None:
    """
    两条 coating 对角线的全部十六对 Terminal 与独立几何分类一致
    """
    owner = owner_factory(coating_diagonal=diagonal)
    pair_kinds = geometry_pair_kinds(_oracle_diagonal(diagonal))
    for oracle_incident in OracleTerminal:
        incident = _cube_terminal(oracle_incident)
        transmission = owner._transmitted_terminal(  # type: ignore[attr-defined]
            incident
        )
        reflection = owner._reflected_terminal(incident)  # type: ignore[attr-defined]
        for oracle_outgoing in OracleTerminal:
            outgoing = _cube_terminal(oracle_outgoing)
            route_kind = pair_kinds[oracle_incident, oracle_outgoing]
            assert (outgoing is transmission) is (
                route_kind is OracleRouteKind.TRANSMISSION
            )
            assert (outgoing is reflection) is (
                route_kind is OracleRouteKind.REFLECTION
            )
            if route_kind is OracleRouteKind.STRUCTURAL_ZERO:
                assert outgoing not in (transmission, reflection)


@pytest.mark.parametrize("owner_factory", (_nbs, _pbs))
def test_rotated_cube_terminal_frames_match_independent_fixture(
    owner_factory: Callable[..., torch.nn.Module],
) -> None:
    """
    非轴对齐 owner 的 incident/outgoing 半方向与 H/V 基逐 Terminal 匹配 oracle
    """
    owner = owner_factory(
        route_right=ROTATED_CUBE_POSE.route_right,
        route_top=ROTATED_CUBE_POSE.route_top,
    )
    for expected in terminal_frame_fixtures():
        frame = owner._terminal_frame(  # type: ignore[attr-defined]
            _cube_terminal(expected.terminal)
        )
        for name in (
            "incident_direction",
            "incident_horizontal",
            "incident_vertical",
            "outgoing_direction",
            "outgoing_horizontal",
            "outgoing_vertical",
        ):
            torch.testing.assert_close(
                getattr(frame, name),
                torch.tensor(getattr(expected, name), dtype=torch.float64),
                atol=5.0e-15,
                rtol=0.0,
            )
        assert torch.equal(frame.origin, owner.origin)  # type: ignore[attr-defined]
        assert frame.origin is not owner.origin  # type: ignore[attr-defined]


@pytest.mark.parametrize("owner_factory", (_nbs, _pbs))
@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
def test_coating_plane_and_p_s_bases_match_independent_geometry(
    owner_factory: Callable[..., torch.nn.Module],
    diagonal: CubeCoatingDiagonal,
) -> None:
    """
    owner 从固定 pose 派生 coating normal 及每个反向 incidence 的 p/s 基
    """
    owner = owner_factory(
        coating_diagonal=diagonal,
        route_right=ROTATED_CUBE_POSE.route_right,
        route_top=ROTATED_CUBE_POSE.route_top,
    )
    expected_normal = coating_plane_normal(
        _oracle_diagonal(diagonal),
        route_right=ROTATED_CUBE_POSE.route_right,
        route_top=ROTATED_CUBE_POSE.route_top,
    )
    actual_normal = owner._coating_normal()  # type: ignore[attr-defined]
    torch.testing.assert_close(
        actual_normal,
        expected_normal,
        atol=5.0e-15,
        rtol=0.0,
    )
    for expected_frame in terminal_frame_fixtures():
        for direction_values in (
            expected_frame.incident_direction,
            expected_frame.outgoing_direction,
        ):
            direction = torch.tensor(direction_values, dtype=torch.float64)
            expected_s, expected_p = coating_basis(
                direction,
                expected_normal,
            )
            actual_p, actual_s = owner._coating_p_s_basis(  # type: ignore[attr-defined]
                direction
            )
            torch.testing.assert_close(
                actual_p,
                expected_p,
                atol=5.0e-15,
                rtol=0.0,
            )
            torch.testing.assert_close(
                actual_s,
                expected_s,
                atol=5.0e-15,
                rtol=0.0,
            )


def test_mirror_terminal_frame_is_derived_from_fixed_front_geometry() -> None:
    """
    Mirror FRONT frame 由 outward normal 与 transverse up 派生且不成为状态
    """
    mirror = _mirror()
    frame = mirror._terminal_frame(MirrorTerminal.FRONT)
    assert torch.equal(
        frame.incident_direction,
        torch.tensor((1.0, 0.0, 0.0), dtype=torch.float64),
    )
    assert torch.equal(
        frame.outgoing_direction,
        torch.tensor((-1.0, 0.0, 0.0), dtype=torch.float64),
    )
    assert torch.equal(
        frame.incident_vertical,
        torch.tensor((0.0, 0.0, 1.0), dtype=torch.float64),
    )
    assert not any("frame" in name for name in mirror.state_dict())


def test_owner_state_is_fixed_double_persistent_and_minimal() -> None:
    """
    NBS 仅比 PBS 多一个 mixing_angle，Mirror 只持有三项固定几何
    """
    parameter = torch.nn.Parameter(
        torch.tensor(math.pi / 4.0, dtype=torch.float64),
    )
    nbs = _nbs(mixing_angle=parameter)
    pbs = _pbs()
    mirror = _mirror()
    assert set(nbs.state_dict()) == {
        "origin",
        "route_right",
        "route_top",
        "_coating_diagonal_code",
        "mixing_angle",
    }
    assert set(pbs.state_dict()) == {
        "origin",
        "route_right",
        "route_top",
        "_coating_diagonal_code",
    }
    assert set(mirror.state_dict()) == {
        "origin",
        "outward_normal",
        "transverse_up",
    }
    assert tuple(nbs.parameters()) == (parameter,)
    assert tuple(pbs.parameters()) == ()
    assert tuple(mirror.parameters()) == ()
    for owner in (nbs, pbs, mirror):
        floating_state = (
            value
            for value in owner.state_dict().values()
            if value.is_floating_point()
        )
        assert all(value.dtype is torch.float64 for value in floating_state)


@pytest.mark.parametrize("owner_factory", (_nbs, _pbs, _mirror))
def test_deepcopy_preserves_state_without_persisting_terminal_frames(
    owner_factory: Callable[..., torch.nn.Module],
) -> None:
    """
    deepcopy 复制唯一 owner 状态而 Terminal Frame 始终按需重建
    """
    owner = owner_factory()
    if isinstance(owner, IdealPlanarMirror):
        first_frame = owner._terminal_frame(MirrorTerminal.FRONT)
    else:
        first_frame = owner._terminal_frame(  # type: ignore[attr-defined]
            CubeTerminal.LEFT
        )
    copied = copy.deepcopy(owner)
    assert copied is not owner
    assert copied.state_dict().keys() == owner.state_dict().keys()
    for name, expected in owner.state_dict().items():
        assert torch.equal(copied.state_dict()[name], expected)
        assert copied.state_dict()[name] is not expected
    if isinstance(copied, IdealPlanarMirror):
        second_frame = copied._terminal_frame(MirrorTerminal.FRONT)
    else:
        second_frame = copied._terminal_frame(  # type: ignore[attr-defined]
            CubeTerminal.LEFT
        )
    assert second_frame is not first_frame
    assert not any("frame" in name for name in copied.state_dict())


@pytest.mark.parametrize("owner_factory", (_nbs, _pbs))
def test_state_dict_round_trip_restores_persistent_diagonal(
    owner_factory: Callable[..., torch.nn.Module],
) -> None:
    """
    coating diagonal 经普通 same-version state_dict 往返而不依赖派生 Python 状态
    """
    source = owner_factory(coating_diagonal=CubeCoatingDiagonal.FALLING)
    restored = owner_factory(coating_diagonal=CubeCoatingDiagonal.RISING)
    restored.load_state_dict(source.state_dict())
    assert (
        restored.coating_diagonal  # type: ignore[attr-defined]
        is CubeCoatingDiagonal.FALLING
    )


@pytest.mark.parametrize(
    ("field_name", "valid_value"),
    (
        ("origin", (0.0, 0.0, 0.0)),
        ("route_right", (1.0, 0.0, 0.0)),
        ("route_top", (0.0, 1.0, 0.0)),
    ),
)
@pytest.mark.parametrize(
    ("failure_kind", "replacement", "exception_type"),
    (
        ("type_invalid", [0.0, 0.0, 0.0], OpticalTypeError),
        (
            "dtype_invalid",
            torch.zeros(3, dtype=torch.float32),
            OpticalTypeError,
        ),
        (
            "shape_invalid",
            torch.zeros((1, 3), dtype=torch.float64),
            OpticalValueError,
        ),
        ("nonfinite", (math.nan, 0.0, 0.0), OpticalValueError),
    ),
)
def test_every_cube_vector_identity_and_exception_class_is_exact(
    field_name: str,
    valid_value: object,
    failure_kind: str,
    replacement: object,
    exception_type: type[Exception],
) -> None:
    """
    Cube 三个物理 field 依次覆盖 type、dtype、shape、nonfinite 封闭模板
    """
    assert valid_value == _cube_geometry()[field_name]
    with pytest.raises(exception_type) as rejected:
        _nbs(**{field_name: replacement})
    assert isinstance(rejected.value, (OpticalTypeError, OpticalValueError))
    assert rejected.value.identity == (  # type: ignore[attr-defined]
        f"cube_geometry_{field_name}_{failure_kind}"
    )
    assert (
        type(_nbs()).__name__
        in rejected.value.explanation  # type: ignore[attr-defined]
    )
    assert field_name in rejected.value.explanation  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("replacement", "identity", "field_name"),
    (
        (
            {"route_right": (2.0, 0.0, 0.0)},
            "cube_geometry_route_right_not_unit",
            "route_right",
        ),
        (
            {"route_top": (0.0, 2.0, 0.0)},
            "cube_geometry_route_top_not_unit",
            "route_top",
        ),
        (
            {"route_top": (1.0, 0.0, 0.0)},
            "cube_geometry_axes_not_orthogonal",
            "route_top",
        ),
        (
            {"coating_diagonal": "rising"},
            "cube_coating_diagonal_invalid",
            "coating_diagonal",
        ),
    ),
)
def test_remaining_cube_geometry_identities_are_exact(
    replacement: dict[str, object],
    identity: str,
    field_name: str,
) -> None:
    """
    Cube unit、orthogonality、diagonal identities 接续 vector 模板的物理顺序
    """
    exception_type = (
        OpticalTypeError
        if identity == "cube_coating_diagonal_invalid"
        else OpticalValueError
    )
    with pytest.raises(exception_type) as rejected:
        _nbs(**replacement)
    assert rejected.value.identity == identity  # type: ignore[attr-defined]
    assert field_name in rejected.value.explanation  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("replacement", "identity", "exception_type"),
    (
        (
            object(),
            "cube_beam_splitter_mixing_angle_type_invalid",
            OpticalTypeError,
        ),
        (
            torch.tensor(0.5, dtype=torch.float32),
            "cube_beam_splitter_mixing_angle_dtype_invalid",
            OpticalTypeError,
        ),
        (
            torch.tensor((0.5,), dtype=torch.float64),
            "cube_beam_splitter_mixing_angle_shape_invalid",
            OpticalValueError,
        ),
        (
            torch.tensor(math.inf, dtype=torch.float64),
            "cube_beam_splitter_mixing_angle_nonfinite",
            OpticalValueError,
        ),
    ),
)
def test_mixing_angle_failures_use_exact_identity_and_exception_class(
    replacement: object,
    identity: str,
    exception_type: type[Exception],
) -> None:
    """
    NBS mixing angle 的 type、dtype、shape、有限性边界互不折叠
    """
    with pytest.raises(exception_type) as rejected:
        _nbs(mixing_angle=replacement)
    assert rejected.value.identity == identity  # type: ignore[attr-defined]
    assert (
        "IdealNonpolarizingCubeBeamSplitter"
        in rejected.value.explanation  # type: ignore[attr-defined]
    )
    assert "mixing_angle" in rejected.value.explanation  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "field_name",
    (
        "origin",
        "outward_normal",
        "transverse_up",
    ),
)
@pytest.mark.parametrize(
    ("failure_kind", "replacement", "exception_type"),
    (
        ("type_invalid", [0.0, 0.0, 0.0], OpticalTypeError),
        (
            "dtype_invalid",
            torch.zeros(3, dtype=torch.float32),
            OpticalTypeError,
        ),
        (
            "shape_invalid",
            torch.zeros((1, 3), dtype=torch.float64),
            OpticalValueError,
        ),
        ("nonfinite", (math.inf, 0.0, 0.0), OpticalValueError),
    ),
)
def test_every_mirror_vector_identity_and_exception_class_is_exact(
    field_name: str,
    failure_kind: str,
    replacement: object,
    exception_type: type[Exception],
) -> None:
    """
    Mirror 三个物理 field 依次覆盖 type、dtype、shape、nonfinite 封闭模板
    """
    with pytest.raises(exception_type) as rejected:
        _mirror(**{field_name: replacement})
    assert rejected.value.identity == (  # type: ignore[attr-defined]
        f"ideal_planar_mirror_{field_name}_{failure_kind}"
    )
    assert (
        "IdealPlanarMirror"
        in rejected.value.explanation  # type: ignore[attr-defined]
    )
    assert field_name in rejected.value.explanation  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("replacement", "identity", "field_name"),
    (
        (
            {"outward_normal": (-2.0, 0.0, 0.0)},
            "ideal_planar_mirror_outward_normal_not_unit",
            "outward_normal",
        ),
        (
            {"transverse_up": (0.0, 0.0, 2.0)},
            "ideal_planar_mirror_transverse_up_not_unit",
            "transverse_up",
        ),
        (
            {"transverse_up": (-1.0, 0.0, 0.0)},
            "ideal_planar_mirror_axes_not_orthogonal",
            "transverse_up",
        ),
    ),
)
def test_remaining_mirror_geometry_identities_are_exact(
    replacement: dict[str, object],
    identity: str,
    field_name: str,
) -> None:
    """
    Mirror unit 与 orthogonality identities 接续 vector 模板的物理顺序
    """
    with pytest.raises(OpticalValueError) as rejected:
        _mirror(**replacement)
    assert rejected.value.identity == identity
    assert field_name in rejected.value.explanation


@pytest.mark.parametrize(
    "replacement",
    (
        torch.nn.Parameter(torch.zeros(3, dtype=torch.float64)),
        torch.zeros(3, dtype=torch.float64, requires_grad=True),
    ),
)
def test_fixed_owner_geometry_rejects_trainable_state(
    replacement: torch.Tensor,
) -> None:
    """
    固定 Cube/Mirror 几何不静默 detach Parameter 或 requires-grad Tensor
    """
    with pytest.raises(OpticalTypeError) as cube_rejected:
        _nbs(origin=replacement)
    assert cube_rejected.value.identity == "cube_geometry_origin_type_invalid"
    with pytest.raises(OpticalTypeError) as mirror_rejected:
        _mirror(origin=replacement)
    assert (
        mirror_rejected.value.identity
        == "ideal_planar_mirror_origin_type_invalid"
    )


@pytest.mark.parametrize(
    "invalid_replacement",
    (
        {"origin": [0.0, 0.0, 0.0]},
        {"mixing_angle": torch.tensor((0.5,), dtype=torch.float64)},
    ),
)
def test_invalid_nbs_input_fails_before_any_registration_mutation(
    invalid_replacement: dict[str, object],
) -> None:
    """
    构造失败在首个 Parameter/Buffer 注册之前发生
    """
    _RegistrationProbeNbs.registration_calls = 0
    arguments = {
        **_cube_geometry(),
        "mixing_angle": math.pi / 4.0,
        **invalid_replacement,
    }
    with pytest.raises((OpticalTypeError, OpticalValueError)):
        _RegistrationProbeNbs(**arguments)  # type: ignore[arg-type]
    assert _RegistrationProbeNbs.registration_calls == 0


def test_every_finite_real_mixing_angle_is_retained_without_canonicalization() -> None:
    """
    负角、大角及普通 Tensor 均保持作者值，不做 clamp 或 modulo
    """
    for angle in (-9.0 * math.pi, -0.7, 0.0, math.pi, 1.0e100):
        owner = _nbs(mixing_angle=angle)
        assert owner.mixing_angle.item() == angle
    tensor = torch.tensor(7.0 * math.pi, dtype=torch.float64)
    tensor_owner = _nbs(mixing_angle=tensor)
    assert tensor_owner.mixing_angle is tensor
    parameter = torch.nn.Parameter(
        torch.tensor(-5.0 * math.pi, dtype=torch.float64),
    )
    parameter_owner = _nbs(mixing_angle=parameter)
    assert parameter_owner.mixing_angle is parameter


def test_qualified_optimizer_update_above_sixteen_ulp_changes_parameter() -> None:
    """
    abs(angle) <= pi 内大于十六 ULP 的 proposed update 可由 float64 精确分辨
    """
    parameter = torch.nn.Parameter(
        torch.tensor(math.pi / 4.0, dtype=torch.float64),
    )
    owner = _nbs(mixing_angle=parameter)
    before = float(owner.mixing_angle.detach())
    update = 32.0 * math.ulp(before)
    with torch.no_grad():
        owner.mixing_angle.add_(update)
    assert abs(before) <= math.pi
    assert update > 16.0 * math.ulp(before)
    assert float(owner.mixing_angle.detach()) == before + update


@pytest.mark.parametrize(
    ("owner", "identity"),
    (
        (
            _nbs(),
            "ideal_nonpolarizing_cube_beam_splitter_has_no_forward_action",
        ),
        (
            _pbs(),
            "ideal_polarizing_cube_beam_splitter_has_no_forward_action",
        ),
        (
            _mirror(),
            "ideal_planar_mirror_has_no_forward_action",
        ),
    ),
)
def test_state_only_owner_rejects_standalone_forward(
    owner: torch.nn.Module,
    identity: str,
) -> None:
    """
    三个 owner 无 Optical Role/Port 且独立调用只产生精确 runtime identity
    """
    assert not hasattr(owner, "role")
    assert not hasattr(owner, "input_ports")
    assert not hasattr(owner, "output_ports")
    with pytest.raises(OpticalRuntimeError) as rejected:
        owner()
    assert rejected.value.identity == identity


def test_new_owner_modules_contain_no_forbidden_generic_surface() -> None:
    """
    T17 生产模块不引入 universal state、N-port、matrix 参数或 public base
    """
    module_sources = (
        __import__(
            "chromatix_next.optics.element.ideal_cube_beam_splitter",
            fromlist=["__file__"],
        ),
        __import__(
            "chromatix_next.optics.element.ideal_planar_mirror",
            fromlist=["__file__"],
        ),
    )
    forbidden = (
        "OpticalState",
        "NPort",
        "ScatteringMatrix",
        "DirectionalElementBase",
        "TerminalBase",
    )
    for module in module_sources:
        source = open(module.__file__, encoding="utf-8").read()
        assert not any(name in source for name in forbidden)
