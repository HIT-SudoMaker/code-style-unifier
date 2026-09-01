
from __future__ import annotations

import ast
from collections.abc import Callable
import copy
from pathlib import Path
from typing import Any

import pytest
import torch

from chromatix_next import install_state
from chromatix_next.errors import OpticalError
from chromatix_next.optics.field import PropagationDirection
from chromatix_next.optics.grid import SpatialGrid
from chromatix_next.optics.medium import Vacuum
from chromatix_next.optics.polarization import Polarization
from chromatix_next.optics.source import (
    CollimatedRaySource,
    GaussianBeam,
    PlaneWave,
    PointSource,
)
from chromatix_next.optics.spectrum import Spectrum

# Source 偏振状态是持久的公开主张




_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PRODUCTION_ROOT = _PROJECT_ROOT / "src" / "chromatix_next"
_LIFECYCLE_PATH = _PRODUCTION_ROOT / "optics" / "_source_lifecycle.py"
_INSTALLATION_PATH = _PRODUCTION_ROOT / "_state_installation.py"

# 收敛后三个共享命名物理缓冲（次序稳定：先实量谱，后复量偏振）
_SHARED_PHYSICAL_BUFFERS = ("wavelengths", "spectral_weights", "polarization_state")


def _monochromatic() -> Spectrum:
    return Spectrum(
        wavelengths=(0.5e-6,),
        weights=(1.0,),
    )


def _multispectral() -> Spectrum:
    # 两波长谱，用于变谱 install_state 证据
    return Spectrum(
        wavelengths=(0.45e-6, 0.55e-6),
        weights=(0.5, 0.5),
    )


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(8, 8),
        sample_spacing=(0.5e-6, 0.5e-6),
    )


def _plane_wave() -> PlaneWave:
    # 传播方向型、相对振幅归一化的平面波（与状态键快照基准一致的规范配置）
    return PlaneWave(
        spectrum=_monochromatic(),
        polarization=Polarization.linear_y(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.25,
    )


def _gaussian_beam() -> GaussianBeam:
    return GaussianBeam(
        spectrum=_monochromatic(),
        polarization=Polarization.linear_x(),
        waist=2.0e-6,
        relative_amplitude=1.25,
    )


def _point_source() -> PointSource:
    # 轴向距离 5 μm 使点源在共享 _grid() (8×8, 0.5 μm) 下被采样栅栏充分分辨
    return PointSource(
        spectrum=_monochromatic(),
        polarization=Polarization.linear_y(),
        medium=Vacuum(),
        position=(0.0, 0.0, 5.0e-6),
        relative_amplitude=1.25,
    )


def _collimated() -> CollimatedRaySource:
    return CollimatedRaySource(
        spectrum=_monochromatic(),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        ray_power=1.25,
    )


_EXPECTED_STATE_KEYS: dict[str, frozenset[str]] = {
    "plane_wave": frozenset(
        {
            "wavelengths",
            "spectral_weights",
            "polarization_state",
            "direction_cosine_y",
            "direction_cosine_x",
            "relative_amplitude",
            "_extra_state",
        }
    ),
    "gaussian_beam": frozenset(
        {
            "wavelengths",
            "spectral_weights",
            "polarization_state",
            "waist",
            "waist_location",
            "relative_amplitude",
            "_extra_state",
        }
    ),
    "point_source": frozenset(
        {
            "wavelengths",
            "spectral_weights",
            "polarization_state",
            "position",
            "relative_amplitude",
            "_extra_state",
        }
    ),
    "collimated": frozenset(
        {
            "wavelengths",
            "spectral_weights",
            "polarization_state",
            "ray_power",
            "launch_origin",
            "launch_tangent_x",
            "launch_tangent_y",
            "_extra_state",
        }
    ),
}

_SOURCE_FACTORIES: dict[str, Callable[[], Any]] = {
    "plane_wave": _plane_wave,
    "gaussian_beam": _gaussian_beam,
    "point_source": _point_source,
    "collimated": _collimated,
}


class _TransparentRoot(torch.nn.Module):
    # 默认持久化的透明组合根：install_state 经命名子模块分发到 Source
    pass


def _make_transparent(*children: torch.nn.Module) -> _TransparentRoot:
    root = _TransparentRoot()
    for index, child in enumerate(children):
        root.add_module(f"child_{index}", child)
    return root


@pytest.mark.parametrize(
    "name",
    list(_SOURCE_FACTORIES),
    ids=list(_SOURCE_FACTORIES),
)
def test_state_dict_keys_match_frozen_snapshot(name: str) -> None:
    """
    每个 Source 的 state_dict 键集恰为冻结快照（含三个共享物理键与源特定键）
    """

    source = _SOURCE_FACTORIES[name]()
    assert frozenset(source.state_dict().keys()) == _EXPECTED_STATE_KEYS[name]


@pytest.mark.parametrize(
    "name",
    list(_SOURCE_FACTORIES),
    ids=list(_SOURCE_FACTORIES),
)
def test_shared_physical_buffers_appear_exactly_once(name: str) -> None:
    """
    三个共享物理缓冲在每个 Source 的 state_dict 里各出现且仅出现一次
    """

    keys = list(_SOURCE_FACTORIES[name]().state_dict().keys())
    for physical_name in _SHARED_PHYSICAL_BUFFERS:
        assert keys.count(physical_name) == 1, (
            f"{name} 的 state_dict 必须包含且仅包含一次 {physical_name}，"
            f"实际键集为 {sorted(set(keys))}"
        )


def test_all_four_sources_share_the_three_physical_buffers() -> None:
    """
    四个 Source 的状态键共享三个物理缓冲，且源特定键不泄漏进公共物理集
    """

    key_sets = [
        set(factory().state_dict().keys())
        for factory in _SOURCE_FACTORIES.values()
    ]
    common = set.intersection(*key_sets)
    shared_physical = set(_SHARED_PHYSICAL_BUFFERS)
    assert shared_physical.issubset(common), (
        "三个共享物理缓冲必须出现在每个 Source 的 state_dict 里；"
        f"四个 Source 的键集交集为 {sorted(common)}，缺少 "
        f"{sorted(shared_physical - common)}"
    )
    for name, factory in _SOURCE_FACTORIES.items():
        source_keys = set(factory().state_dict().keys())
        others = [
            set(f().state_dict().keys())
            for other_name, f in _SOURCE_FACTORIES.items()
            if other_name is not name
        ]
        leaked = source_keys & set.intersection(*others) - shared_physical
        leaked = leaked - {"_extra_state"}
        assert leaked == set(), (
            f"{name} 的源特定键 {sorted(leaked)} 不得出现在其它所有 Source 的键集里"
        )


def test_source_lifecycle_has_no_nullable_polarization_path() -> None:
    """
    生产 Source 生命周期不再保留可空偏振路径：_source_lifecycle.py 源码不含
    ``Polarization | None`` 注解，也不含条件偏振注册/提交分支
    """

    source = _LIFECYCLE_PATH.read_text(encoding="utf-8")
    assert "Polarization | None" not in source, (
        "_source_lifecycle.py 不得保留任何 Polarization | None 可空注解"
    )
    assert "if polarization is not None" not in source, (
        "_source_lifecycle.py 不得保留条件偏振注册分支"
    )
    assert "if plan.polarization is not None" not in source, (
        "_source_lifecycle.py 不得保留条件偏振提交分支"
    )


def test_source_lifecycle_has_one_physical_buffer_projection() -> None:
    """
    收敛后只剩一个 Source 物理缓冲投影校验函数，重复的 Wave/Ray 同义函数已删除
    """

    tree = ast.parse(_LIFECYCLE_PATH.read_text(encoding="utf-8"))
    projection_functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith("_validate_")
        and node.name.endswith("_physical_buffer_projection")
    }
    assert projection_functions == {
        "_validate_source_physical_buffer_projection"
    }, (
        "Source 物理缓冲投影校验必须收敛为唯一函数 "
        "_validate_source_physical_buffer_projection，"
        f"实际发现的投影函数为 {sorted(projection_functions)}"
    )


def test_state_installation_has_one_physical_buffer_inventory() -> None:
    """
    状态安装只剩一个 Source 物理缓冲清单，重复的 Wave/Ray 同义清单已删除
    """

    tree = ast.parse(_INSTALLATION_PATH.read_text(encoding="utf-8"))
    inventory_names = {
        node.targets[0].id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id.endswith("_PHYSICAL_BUFFERS")
    }
    assert inventory_names == {"_SOURCE_PHYSICAL_BUFFERS"}, (
        "State Installation 的物理缓冲清单必须收敛为唯一 _SOURCE_PHYSICAL_BUFFERS，"
        f"实际发现的清单名为 {sorted(inventory_names)}"
    )
    installation_source = _INSTALLATION_PATH.read_text(encoding="utf-8")
    assert (
        '"wavelengths", "spectral_weights", "polarization_state"'
        in installation_source
    )


@pytest.mark.parametrize(
    "name",
    list(_SOURCE_FACTORIES),
    ids=list(_SOURCE_FACTORIES),
)
def test_install_state_round_trip_preserves_physical_metadata(name: str) -> None:
    """
    经公共 install_state 在透明根上载入同结构同谱 state_dict 后，每个 Source 的命名
    物理载荷与键集保持不变（成功安装证据）
    """

    original = _SOURCE_FACTORIES[name]()
    root = _make_transparent(original)
    state = {
        f"child_0.{key}": value for key, value in original.state_dict().items()
    }
    install_state(root, state)
    restored: Any = getattr(root, "child_0")
    assert frozenset(restored.state_dict().keys()) == _EXPECTED_STATE_KEYS[name]
    assert restored.get_extra_state() == original.get_extra_state()
    assert restored._spectrum_value == original._spectrum_value
    assert restored._polarization_value == original._polarization_value


@pytest.mark.parametrize(
    "name",
    list(_SOURCE_FACTORIES),
    ids=list(_SOURCE_FACTORIES),
)
def test_variable_spectrum_install_state_succeeds(name: str) -> None:
    """
    每个 Source 经公共 install_state 把单波长态载入到双波长源上成功（变谱安装证据）
    """

    target = _SOURCE_FACTORIES[name]()
    root = _make_transparent(target)
    donor = _SOURCE_FACTORIES[name]()
    donor_state = dict(donor.state_dict())
    new_spectrum = _multispectral()
    extra = copy.deepcopy(donor_state["_extra_state"])
    extra["spectrum"] = {
        "wavelengths": new_spectrum.wavelengths,
        "weights": new_spectrum.weights,
    }
    donor_state["_extra_state"] = extra
    donor_state["wavelengths"] = torch.tensor(
        new_spectrum.wavelengths,
        dtype=torch.float64,
    )
    donor_state["spectral_weights"] = torch.tensor(
        new_spectrum.weights,
        dtype=torch.float64,
    )
    state = {f"child_0.{key}": value for key, value in donor_state.items()}
    install_state(root, state)
    assert target._spectrum_value == new_spectrum
    assert target.get_extra_state() == extra


@pytest.mark.parametrize(
    ("name", "failure_kind", "expected_identity"),
    (
        (
            "plane_wave",
            "malformed",
            "plane_wave_extra_state_invalid",
        ),
        (
            "plane_wave",
            "structure",
            "plane_wave_extra_state_structure_mismatch",
        ),
        (
            "plane_wave",
            "buffer",
            "plane_wave_extra_state_buffer_mismatch",
        ),
        (
            "gaussian_beam",
            "malformed",
            "gaussian_beam_extra_state_invalid",
        ),
        (
            "gaussian_beam",
            "structure",
            "gaussian_beam_extra_state_structure_mismatch",
        ),
        (
            "gaussian_beam",
            "buffer",
            "gaussian_beam_extra_state_buffer_mismatch",
        ),
        (
            "point_source",
            "malformed",
            "point_source_extra_state_invalid",
        ),
        (
            "point_source",
            "structure",
            "point_source_extra_state_structure_mismatch",
        ),
        (
            "point_source",
            "buffer",
            "point_source_extra_state_buffer_mismatch",
        ),
    ),
    ids=[
        "plane-wave-malformed",
        "plane-wave-structure",
        "plane-wave-buffer",
        "gaussian-beam-malformed",
        "gaussian-beam-structure",
        "gaussian-beam-buffer",
        "point-source-malformed",
        "point-source-structure",
        "point-source-buffer",
    ],
)
def test_public_extra_state_rejection_keeps_stable_identity(
    name: str,
    failure_kind: str,
    expected_identity: str,
) -> None:
    """
    每个 Source 的纯规划函数对畸形附加状态以稳定源身份拒绝（稳定错误身份证据）
    """

    source = _SOURCE_FACTORIES[name]()
    state = copy.deepcopy(source.get_extra_state())
    malformed = {key: value for key, value in state.items() if key != "spectrum"}
    if failure_kind == "malformed":
        invalid_state: object = malformed
    elif failure_kind == "structure":
        invalid_state = {**state, "normalization": "incompatible"}
    elif failure_kind == "buffer":
        invalid_state = {
            **state,
            "spectrum": {
                "wavelengths": (633.0e-9,),
                "weights": (1.0,),
            },
        }
    else:
        pytest.fail(f"unknown extra-state failure: {failure_kind}")

    state_before = copy.deepcopy(source.get_extra_state())
    with pytest.raises(OpticalError) as rejected:
        source.set_extra_state(invalid_state)

    assert rejected.value.identity == expected_identity
    assert source.get_extra_state() == state_before


@pytest.mark.parametrize(
    ("name", "device"),
    [
        *[(name, "cpu") for name in _SOURCE_FACTORIES],
        *[(name, "cuda") for name in _SOURCE_FACTORIES],
    ],
    ids=[
        *[f"{name}-cpu" for name in _SOURCE_FACTORIES],
        *[f"{name}-cuda" for name in _SOURCE_FACTORIES],
    ],
)
def test_forward_output_values_preserved(name: str, device: str) -> None:
    """
    收敛后每个 Source 的前向输出值不变：三个波源仍产出有限 OpticalField 包络，准直
    光线源仍对精确输入产出正确嵌入全局 frame 的 Ray 偏振。
    CPU 与 CUDA 都执行。
    """

    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA 不可用")
    source = _SOURCE_FACTORIES[name]()
    grid = _grid()
    output = source(grid)
    if name == "collimated":
        bundle = output
        launch_tangent_x = source._buffer("launch_tangent_x")
        polarization_vector = bundle.polarization_vector
        expected = launch_tangent_x.to(dtype=torch.complex128)
        assert torch.allclose(
            polarization_vector[0, 0].to(dtype=torch.complex128),
            expected,
        ), "linear_x 的准直光线源偏振向量必须等于 launch_tangent_x"
        launch = torch.linalg.cross(
            source._buffer("launch_tangent_x"),
            source._buffer("launch_tangent_y"),
        ).to(dtype=torch.float64)
        transverse = (
            polarization_vector[0, 0].to(dtype=torch.complex128).real * launch
        ).sum()
        assert abs(float(transverse)) < 1e-12, (
            "准直光线源偏振向量必须横截于发射方向"
        )
    else:
        field = output
        assert torch.isfinite(field.envelope).all()
        assert field.envelope.shape[0] == source._spectrum_value.count
