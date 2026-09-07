
from __future__ import annotations

from copy import deepcopy

import pytest
import torch

from chromatix_next import install_state
from chromatix_next.errors import (
    OpticalRuntimeError,
    OpticalTypeError,
    OpticalValueError,
)
from chromatix_next.optics import (
    Polarization,
    PolarizationRepresentation,
    SpatialGrid,
    Spectrum,
)
from chromatix_next.optics.source import CollimatedRaySource


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(3, 4),
        sample_spacing=(1.0, 1.0),
    )


def _spectrum() -> Spectrum:
    return Spectrum.monochromatic(wavelength=2.0e-6)


@pytest.mark.parametrize(
    "polarization",
    (
        Polarization.linear_x(),
        Polarization.linear_y(),
        Polarization.left_circular(),
        Polarization.right_circular(),
        Polarization.transverse(components=(0.6 + 0.8j, 0.0)),
    ),
    ids=["linear_x", "linear_y", "left_circular", "right_circular", "arbitrary"],
)
def test_collimated_authors_transverse_polarization_as_complex128_state(
    polarization: Polarization,
) -> None:
    """
    横向偏振（线/圆/任意椭圆）作者为固定 complex128 命名物理载荷与 2 分量
    """
    assert polarization.representation is PolarizationRepresentation.TRANSVERSE
    source = CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=polarization,
        ray_power=1.0,
    )
    state = source._buffer("polarization_state")  # noqa: SLF001
    assert state.dtype is torch.complex128
    assert state.shape == torch.Size((2,))
    bundle = source(_grid())
    assert bundle.polarization_vector.dtype is torch.complex128


@pytest.mark.parametrize(
    "polarization",
    (Polarization.scalar(), Polarization.full()),
    ids=["scalar", "full"],
)
def test_collimated_rejects_non_transverse_representations(
    polarization: Polarization,
) -> None:
    """
    标量与完整偏振表示 ⇒ Source 稳定身份拒绝；无默认横向态
    """
    with pytest.raises(OpticalTypeError) as rejected:
        CollimatedRaySource(
            spectrum=_spectrum(),
            polarization=polarization,
            ray_power=1.0,
        )
    assert (
        rejected.value.identity
        == "collimated_ray_source_polarization_representation_invalid"
    )


def test_collimated_polarized_checkpoint_round_trips_through_install_state() -> None:
    """
    同版本偏振 checkpoint 经状态安装、托管、运行往返不变
    """
    from chromatix_next import Workstation

    original = CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.left_circular(),
        ray_power=torch.nn.Parameter(torch.tensor(0.7, dtype=torch.float64)),
    )
    state_dict = original.state_dict()
    target = CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        ray_power=1.0,
    )
    install_state(target, state_dict)
    workstation = Workstation.cpu()
    workstation.host(target)
    bundle_target = target(_grid())
    bundle_original = original(_grid())
    assert torch.equal(
        bundle_target.polarization_vector,
        bundle_original.polarization_vector,
    )


def test_power_only_checkpoint_without_polarization_state_fails_atomically(
) -> None:
    """
    缺少 polarization_state 键的纯功率 checkpoint 在任何注册态变更前以单一
    稳定 schema 身份失败；不猜测、不翻译、不注入默认偏振
    """
    source = CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        ray_power=1.0,
    )
    power_only_state_dict = {
        key: value
        for key, value in source.state_dict().items()
        if key != "polarization_state"
    }
    target = CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.linear_y(),
        ray_power=1.0,
    )
    with pytest.raises(OpticalRuntimeError) as rejected:
        install_state(target, power_only_state_dict)
    assert rejected.value.identity == "state_installation_keys_mismatch"


def test_launch_plane_pose_keys_fail_without_translation() -> None:
    """
    旧 launch plane 键集在安装前整体拒绝，不做轴交换或兼容翻译
    """

    source = CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        ray_power=1.0,
    )
    target = CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.linear_y(),
        ray_power=1.0,
    )
    state = deepcopy(source.state_dict())
    launch_plane_key_state = dict(state)
    launch_plane_key_state["launch_plane_origin"] = launch_plane_key_state.pop(
        "launch_origin"
    )
    launch_plane_key_state["launch_plane_axis_y"] = launch_plane_key_state.pop(
        "launch_tangent_x"
    )
    launch_plane_key_state["launch_plane_axis_x"] = launch_plane_key_state.pop(
        "launch_tangent_y"
    )
    before_state = deepcopy(target.state_dict())

    with pytest.raises(OpticalRuntimeError) as rejected:
        install_state(target, launch_plane_key_state)

    assert rejected.value.identity == "state_installation_keys_mismatch"
    for key, value in target.state_dict().items():
        if isinstance(value, torch.Tensor):
            assert torch.equal(value, before_state[key])
        else:
            assert value == before_state[key]


def test_mutated_launch_pose_is_rejected_by_source_before_ray_bundle() -> None:
    """
    源在 RayBundle 构造前重新验证 authored Pose
    """

    source = CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        ray_power=1.0,
    )
    with torch.no_grad():
        source._buffer("launch_tangent_x").copy_(  # noqa: SLF001
            torch.tensor((2.0, 0.0, 0.0), dtype=torch.float64)
        )

    with pytest.raises(OpticalValueError) as rejected:
        source(_grid())

    assert (
        rejected.value.identity
        == "collimated_ray_source_launch_tangent_x_not_unit"
    )


def test_invalid_launch_pose_is_rejected_before_state_copy() -> None:
    """
    状态安装在原生复制前拒绝无效 launch Pose
    """

    target = CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        ray_power=1.0,
    )
    incoming_state = deepcopy(target.state_dict())
    incoming_state["launch_tangent_y"] = torch.tensor(
        (2.0, 0.0, 0.0),
        dtype=torch.float64,
    )
    before_state = deepcopy(target.state_dict())

    with pytest.raises(OpticalValueError) as rejected:
        install_state(target, incoming_state)

    assert (
        rejected.value.identity
        == "collimated_ray_source_launch_tangent_y_not_unit"
    )
    for key, value in target.state_dict().items():
        if isinstance(value, torch.Tensor):
            assert torch.equal(value, before_state[key])
        else:
            assert value == before_state[key]
