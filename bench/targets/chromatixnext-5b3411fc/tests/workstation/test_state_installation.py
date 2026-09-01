
from __future__ import annotations

from collections.abc import Mapping
import copy
from typing import cast

import pytest
import torch

from chromatix_next import Workstation, install_state
from chromatix_next.errors import (
    OpticalError,
    OpticalRuntimeError,
    OpticalTypeError,
    OpticalValueError,
    WorkstationError,
)
from chromatix_next.optics import (
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.source import (
    CollimatedRaySource,
    GaussianBeam,
    PlaneWave,
    PointSource,
)
from chromatix_next.optics.surface.conic import ConicEvenAsphere


def _mono(wavelength: float = 0.5e-6) -> Spectrum:
    return Spectrum(
        wavelengths=(wavelength,),
        weights=(1.0,),
    )


def _multi() -> Spectrum:
    return Spectrum(
        wavelengths=(0.45e-6, 0.55e-6),
        weights=(0.5, 0.5),
    )


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(sample_counts=(8, 8), sample_spacing=(0.5e-6, 0.5e-6))


def _plane_wave(
    spectrum: Spectrum | None = None,
    relative_amplitude: float = 1.0,
) -> PlaneWave:
    return PlaneWave(
        spectrum=spectrum or _mono(),
        polarization=Polarization.linear_y(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=relative_amplitude,
    )


class _TransparentRoot(torch.nn.Module):
    pass


class _ScalarParam(torch.nn.Module):
    scale: torch.nn.Parameter

    def __init__(self, value: float = 1.0) -> None:
        """
        注册一个 float64 标量 Parameter
        """
        super().__init__()
        self.scale = torch.nn.Parameter(
            torch.tensor(value, dtype=torch.float64),
        )


def _make_transparent(*children: torch.nn.Module) -> _TransparentRoot:
    root = _TransparentRoot()
    for index, child in enumerate(children):
        root.add_module(f"child_{index}", child)
    return root


def _identity_of(error: OpticalError) -> str:
    return error.identity


def _clone_state(state: Mapping[str, object]) -> dict[str, object]:
    return {
        k: (v.clone() if isinstance(v, torch.Tensor) else copy.deepcopy(v))
        for k, v in state.items()
    }


def _assert_state_unchanged(
    module: torch.nn.Module,
    expected: Mapping[str, object],
) -> None:
    actual = module.state_dict()
    assert actual.keys() == expected.keys()
    for key, expected_value in expected.items():
        actual_value = actual[key]
        if isinstance(expected_value, torch.Tensor):
            assert isinstance(actual_value, torch.Tensor)
            assert torch.equal(actual_value, expected_value)
        else:
            assert actual_value == expected_value


class _OverrideLoadStateDict(_ScalarParam):
    def load_state_dict(  # type: ignore[override]
        self,
        state_dict: Mapping[str, object],
        is_strict: bool = True,
        is_assign: bool = False,
    ) -> object:
        """
        转发到基类 load_state_dict
        """
        return super().load_state_dict(state_dict, strict=is_strict, assign=is_assign)


class _LazyParam(torch.nn.Module):
    def __init__(self) -> None:
        """
        注册一个 None 参数槽
        """
        super().__init__()
        self.register_parameter("scale", None)


class TestInstallStateEvidence:
    """
    19 个独立证据
    """

    def test_cross_child_tied_parameter_installs_once(self) -> None:
        """
        两子模块共享同一 Parameter；install_state 保持身份与别名
        """
        c0 = _ScalarParam()
        c1 = _ScalarParam()
        shared = torch.nn.Parameter(torch.tensor(2.5, dtype=torch.float64))
        c0.scale = shared
        c1.scale = shared
        root = _make_transparent(c0, c1)
        state = _clone_state(root.state_dict())
        state["child_0.scale"] = torch.tensor(9.0, dtype=torch.float64)
        state["child_1.scale"] = torch.tensor(9.0, dtype=torch.float64)
        install_state(root, state)
        assert c0.scale is c1.scale
        assert torch.equal(c0.scale, torch.tensor(9.0, dtype=torch.float64))

    def test_two_children_sharing_exact_buffer_storage(self) -> None:
        """
        两子模块 Buffer 共享同一 storage；一致 incoming 值接受
        """
        c0 = _ScalarParam()
        c1 = _ScalarParam()
        shared_buffer = torch.tensor(7.0, dtype=torch.float64)
        c0.register_buffer("bias", shared_buffer)
        c1.register_buffer("bias", shared_buffer)
        root = _make_transparent(c0, c1)
        state = dict(root.state_dict())
        state["child_0.bias"] = torch.tensor(3.0, dtype=torch.float64)
        state["child_1.bias"] = torch.tensor(3.0, dtype=torch.float64)
        install_state(root, state)
        assert torch.equal(
            cast(torch.Tensor, c0.get_buffer("bias")),
            torch.tensor(3.0, dtype=torch.float64),
        )
        assert c0.get_buffer("bias") is c1.get_buffer("bias")

    def test_parameter_buffer_exact_alias_accepted(self) -> None:
        """
        Parameter↔Buffer 精确别名在一致 incoming 值下接受
        """
        c0 = _ScalarParam()
        c1 = _ScalarParam()
        shared = torch.tensor(4.0, dtype=torch.float64)
        c0.register_buffer("buf", shared.clone())
        c1.scale = torch.nn.Parameter(cast(torch.Tensor, c0.get_buffer("buf")).data)
        root = _make_transparent(c0, c1)
        state = _clone_state(root.state_dict())
        state["child_0.buf"] = torch.tensor(6.0, dtype=torch.float64)
        state["child_1.scale"] = torch.tensor(6.0, dtype=torch.float64)
        install_state(root, state)

    def test_distinct_partial_view_rejected_before_copy(self) -> None:
        """
        同一 storage 上两个相异局部视图在预检即拒绝，先于原生复制
        """
        c0 = _ScalarParam()
        c1 = _ScalarParam()
        base = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float64)
        c0.scale = torch.nn.Parameter(base)
        c1.scale = torch.nn.Parameter(base[::2])
        root = _make_transparent(c0, c1)
        state = _clone_state(root.state_dict())
        state_before = _clone_state(root.state_dict())
        parameter_identities = (id(c0.scale), id(c1.scale))
        storage_pointer = c0.scale.untyped_storage().data_ptr()
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, state)
        assert _identity_of(exc.value) == "state_installation_partial_storage_view"
        _assert_state_unchanged(root, state_before)
        assert (id(c0.scale), id(c1.scale)) == parameter_identities
        assert c0.scale.untyped_storage().data_ptr() == storage_pointer
        assert c1.scale.untyped_storage().data_ptr() == storage_pointer

    def test_dtype_violation_in_last_child_leaves_first_unchanged(self) -> None:
        """
        末子模块 dtype 违例；首子模块零变更，先于原生复制
        """
        c0 = _ScalarParam(1.0)
        c1 = _ScalarParam(2.0)
        root = _make_transparent(c0, c1)
        state = _clone_state(root.state_dict())
        state["child_1.scale"] = torch.tensor(9.0, dtype=torch.float32)
        state_before = _clone_state(root.state_dict())
        parameter_identities = (id(c0.scale), id(c1.scale))
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, state)
        assert _identity_of(exc.value) == "state_installation_dtype_unsupported"
        _assert_state_unchanged(root, state_before)
        assert (id(c0.scale), id(c1.scale)) == parameter_identities

    def test_unexpected_key_rejected_at_keys_check(self) -> None:
        """
        多余键在键集校验拒绝，先于其值 dtype 校验
        """
        root = _make_transparent(_ScalarParam())
        state = {**root.state_dict(), "ghost": torch.tensor(1.0, dtype=torch.float32)}
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, state)
        assert _identity_of(exc.value) == "state_installation_keys_mismatch"

    def test_alias_value_conflict_rejected_before_source_resize(self) -> None:
        """
        精确别名两键 incoming 值冲突；在 Source resize 前拒绝
        """
        c0 = _ScalarParam()
        c1 = _ScalarParam()
        shared = torch.tensor(1.0, dtype=torch.float64)
        c0.scale = torch.nn.Parameter(shared)
        c1.scale = torch.nn.Parameter(shared)
        root = _make_transparent(c0, c1)
        state = _clone_state(root.state_dict())
        state["child_0.scale"] = torch.tensor(5.0, dtype=torch.float64)
        state["child_1.scale"] = torch.tensor(6.0, dtype=torch.float64)
        state_before = _clone_state(root.state_dict())
        parameter_identities = (id(c0.scale), id(c1.scale))
        storage_pointer = c0.scale.untyped_storage().data_ptr()
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, state)
        assert _identity_of(exc.value) == "state_installation_alias_conflict"
        _assert_state_unchanged(root, state_before)
        assert (id(c0.scale), id(c1.scale)) == parameter_identities
        assert c0.scale.untyped_storage().data_ptr() == storage_pointer
        assert c1.scale.untyped_storage().data_ptr() == storage_pointer

    def test_wrong_shape_rejected(self) -> None:
        """
        错形状在预检拒绝
        """
        root = _make_transparent(_ScalarParam())
        state = _clone_state(root.state_dict())
        state["child_0.scale"] = torch.tensor([1.0, 2.0], dtype=torch.float64)
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, state)
        assert _identity_of(exc.value) == "state_installation_shape_mismatch"


    def test_non_tensor_payload_rejected(self) -> None:
        """
        张量位置的非张量载荷在预检拒绝
        """
        root = _make_transparent(_ScalarParam())
        state = dict(root.state_dict())
        state["child_0.scale"] = 1.0
        with pytest.raises(OpticalTypeError) as exc:
            install_state(root, state)
        assert _identity_of(exc.value) == "state_installation_tensor_unsupported"

    def test_variable_spectrum_install_preserves_target_lineage(self) -> None:
        """
        变谱 Source 载入成功；目标 Source Lineage 不被源谱系替换
        """
        target = _plane_wave(spectrum=_mono())
        donor = _plane_wave(spectrum=_multi())
        lineage_before = target._source_lineage
        install_state(target, donor.state_dict())
        assert target._source_lineage is lineage_before
        assert target._spectrum_value == donor._spectrum_value
        assert target._spectrum_value.count == 2

    def test_install_preserves_parameter_and_alias_identities(self) -> None:
        """
        install_state 保留 Parameter 对象身份与已登记别名
        """
        c0 = _ScalarParam()
        c1 = _ScalarParam()
        shared = torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float64))
        c0.scale = shared
        c1.scale = shared
        root = _make_transparent(c0, c1)
        scale_id_before = id(c0.scale)
        state = _clone_state(root.state_dict())
        state["child_0.scale"] = torch.tensor(8.0, dtype=torch.float64)
        state["child_1.scale"] = torch.tensor(8.0, dtype=torch.float64)
        install_state(root, state)
        assert id(c0.scale) == scale_id_before
        assert c0.scale is c1.scale
        assert torch.equal(c0.scale, torch.tensor(8.0, dtype=torch.float64))

    def test_discrete_dtype_mismatch_rejected(self) -> None:
        """
        离散 dtype（bool/int）不一致在 row 13 拒绝
        """
        root = _TransparentRoot()
        child = _ScalarParam()
        root.add_module("child_0", child)
        root.register_buffer("mask", torch.tensor([1, 0, 1], dtype=torch.uint8))
        state = {**root.state_dict()}
        state["mask"] = torch.tensor([True, False, True], dtype=torch.bool)
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, state)
        assert _identity_of(exc.value) == "state_installation_dtype_unsupported"

    def test_buffer_storage_and_alias_postcondition_holds(self) -> None:
        """
        成功载入后命名 Buffer 对象身份、storage _cdata 与精确别名关系不变
        """
        c0 = _ScalarParam()
        c1 = _ScalarParam()
        shared = torch.tensor(4.0, dtype=torch.float64)
        c0.register_buffer("bias", shared.clone())
        c1.register_buffer("bias", c0.get_buffer("bias"))
        root = _make_transparent(c0, c1)
        bias_before = cast(torch.Tensor, c0.get_buffer("bias"))
        bias_id_before = id(bias_before)
        bias_storage_before = bias_before.untyped_storage()._cdata
        state = _clone_state(root.state_dict())
        state["child_0.bias"] = torch.tensor(6.0, dtype=torch.float64)
        state["child_1.bias"] = torch.tensor(6.0, dtype=torch.float64)
        install_state(root, state)
        bias_after = cast(torch.Tensor, c0.get_buffer("bias"))
        assert id(bias_after) == bias_id_before
        assert bias_after.untyped_storage()._cdata == bias_storage_before
        assert c0.get_buffer("bias") is c1.get_buffer("bias")

    def test_hosted_root_rejected(self) -> None:
        """
        托管根不得 install_state
        """
        workstation = Workstation.cpu()
        source = _plane_wave()
        workstation.host(source)
        with pytest.raises(WorkstationError) as exc:
            install_state(source, source.state_dict())
        assert exc.value.identity == "workstation_hosted_state_load_forbidden"
        workstation.release(source)

    def test_storage_shared_with_hosted_tree_rejected(self) -> None:
        """
        与另一托管树共享 storage 的根不得 install_state
        """
        workstation = Workstation.cpu()
        hosted = _plane_wave()
        workstation.host(hosted)
        child = _ScalarParam()
        hosted_amplitude = cast(torch.Tensor, hosted.relative_amplitude)
        child.scale = torch.nn.Parameter(hosted_amplitude.data)
        root = _make_transparent(child)
        with pytest.raises(WorkstationError) as exc:
            install_state(root, root.state_dict())
        assert exc.value.identity == "workstation_hosted_state_load_forbidden"

    def test_release_install_host_recovery(self) -> None:
        """
        release 后 install_state 再 host 成功恢复运行路径
        """
        workstation = Workstation.cpu()
        source = _plane_wave(spectrum=_mono())
        workstation.host(source)
        grid = _grid()
        source(grid)
        workstation.release(source)
        donor = _plane_wave(spectrum=_multi())
        install_state(source, donor.state_dict())
        workstation.host(source)
        field = source(grid)
        assert field.envelope.shape[0] == 2

    def test_source_resize_aliased_to_sibling_rejected(self) -> None:
        """
        Source 缓冲 resize 时其槽位精确别名另一槽位，在 resize 前拒绝
        """
        source = _plane_wave(spectrum=_mono())
        sibling = _ScalarParam()
        wavelengths = cast(torch.Tensor, source.get_buffer("wavelengths"))
        sibling.register_buffer("tied", wavelengths)
        root = _make_transparent(source, sibling)
        donor = _plane_wave(spectrum=_multi())
        donor_state = donor.state_dict()
        state = _clone_state(root.state_dict())
        state["child_0.wavelengths"] = donor_state["wavelengths"].clone()
        state["child_0.spectral_weights"] = donor_state["spectral_weights"].clone()
        state["child_0.polarization_state"] = donor_state["polarization_state"].clone()
        state["child_0._extra_state"] = copy.deepcopy(donor_state["_extra_state"])
        state_before = _clone_state(root.state_dict())
        wavelength_identity = id(wavelengths)
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, state)
        assert exc.value.identity == "state_installation_resize_alias_conflict"
        _assert_state_unchanged(root, state_before)
        assert source.get_buffer("wavelengths") is wavelengths
        assert sibling.get_buffer("tied") is wavelengths
        assert id(wavelengths) == wavelength_identity

    def test_source_projection_shape_rejected_without_partial_install(self) -> None:
        first = _plane_wave(relative_amplitude=1.0)
        second = _plane_wave(relative_amplitude=2.0)
        root = _make_transparent(first, second)
        first_donor = _plane_wave(relative_amplitude=3.0)
        second_donor = _plane_wave(relative_amplitude=4.0)
        incoming_state = {
            **_prefixed("child_0", first_donor.state_dict()),
            **_prefixed("child_1", second_donor.state_dict()),
        }
        incoming_polarization = cast(
            torch.Tensor,
            incoming_state["child_1.polarization_state"],
        )
        incoming_state["child_1.polarization_state"] = (
            incoming_polarization.reshape(1, -1)
        )
        state_before = _clone_state(root.state_dict())
        parameter_identities = tuple(
            id(parameter) for parameter in root.parameters()
        )
        buffer_identities = tuple(
            id(buffer) for buffer in root.buffers()
        )

        with pytest.raises(OpticalRuntimeError) as rejected:
            install_state(root, incoming_state)

        assert rejected.value.identity == "plane_wave_extra_state_buffer_mismatch"
        _assert_state_unchanged(root, state_before)
        assert tuple(id(parameter) for parameter in root.parameters()) == (
            parameter_identities
        )
        assert tuple(id(buffer) for buffer in root.buffers()) == buffer_identities

    def test_one_source_two_module_paths_resizes_once(self) -> None:
        """
        同一 Source 经两条模块路径，wavelengths 槽位只 resize 一次
        """
        source = _plane_wave(spectrum=_mono())
        root = _make_transparent(source, source)
        donor = _plane_wave(spectrum=_multi())
        donor_state = donor.state_dict()
        full_state = {
            **_prefixed("child_0", donor_state),
            **_prefixed("child_1", donor_state),
        }
        install_state(root, full_state)
        wavelengths = cast(torch.Tensor, source.get_buffer("wavelengths"))
        assert wavelengths.shape[0] == 2

    def test_transparent_default_persistence_root_succeeds(self) -> None:
        """
        默认持久化的透明组合根载入成功
        """
        root = _make_transparent(_ScalarParam(1.0), _ScalarParam(2.0))
        state = {
            "child_0.scale": torch.tensor(3.0, dtype=torch.float64),
            "child_1.scale": torch.tensor(4.0, dtype=torch.float64),
        }
        install_state(root, state)
        c0 = cast(_ScalarParam, getattr(root, "child_0"))
        c1 = cast(_ScalarParam, getattr(root, "child_1"))
        assert torch.equal(c0.scale, torch.tensor(3.0, dtype=torch.float64))
        assert torch.equal(c1.scale, torch.tensor(4.0, dtype=torch.float64))


def _prefixed(prefix: str, donor_state: Mapping[str, object]) -> dict[str, object]:
    return {
        f"{prefix}.{k}": (
            v.clone() if isinstance(v, torch.Tensor) else copy.deepcopy(v)
        )
        for k, v in donor_state.items()
    }


class TestPersistenceRejection:
    """
    每种持久化覆盖、钩子、惰性、原生模式都拒绝
    """

    def test_load_state_dict_override_rejected(self) -> None:
        """
        覆盖 load_state_dict 的模块在 row 4 拒绝
        """
        root = _make_transparent(_OverrideLoadStateDict())
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, root.state_dict())
        assert exc.value.identity == "state_installation_persistence_unsupported"

    def test_external_load_pre_hook_rejected(self) -> None:
        """
        外部 load_state_dict 前置钩子在 row 4 拒绝
        """
        child = _ScalarParam()
        child.register_load_state_dict_pre_hook(lambda *a, **k: None)
        root = _make_transparent(child)
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, root.state_dict())
        assert exc.value.identity == "state_installation_persistence_unsupported"

    def test_lazy_parameter_rejected(self) -> None:
        """
        惰性参数槽在 row 4 拒绝
        """
        root = _make_transparent(_LazyParam())
        state = {"child_0.scale": torch.tensor(1.0, dtype=torch.float64)}
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, state)
        assert exc.value.identity == "state_installation_persistence_unsupported"

    def test_native_swap_mode_rejected(self) -> None:
        """
        启用 swap-module-params 模式在 row 5 拒绝
        """
        child = _ScalarParam()
        child.swap_module_params = True  # type: ignore[attr-defined]
        root = _make_transparent(child)
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, root.state_dict())
        assert exc.value.identity == "state_installation_native_mode_unsupported"

    def test_instance_load_from_state_dict_shadow_rejected(self) -> None:
        """
        实例级 _load_from_state_dict shadow 在 row 4 拒绝，shadow 不被触及
        """
        child = _ScalarParam()

        def _shadow(*args: object, **kwargs: object) -> None:
            shadow_message = "instance shadow must not be called"
            raise AssertionError(shadow_message)

        child._load_from_state_dict = _shadow  # type: ignore[assignment]
        root = _make_transparent(child)
        state_before = _clone_state(root.state_dict())
        parameter_identity = id(child.scale)
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, root.state_dict())
        assert exc.value.identity == "state_installation_persistence_unsupported"
        _assert_state_unchanged(root, state_before)
        assert id(child.scale) == parameter_identity

    def test_source_instance_persistence_shadow_rejected(self) -> None:
        """
        波源实例级状态载入 shadow 也在 row 4 拒绝
        """
        source = _plane_wave()
        source._load_from_state_dict = lambda *a, **k: None  # type: ignore[assignment]
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(source, source.state_dict())
        assert exc.value.identity == "state_installation_persistence_unsupported"

    def test_tensor_subclass_module_rejected(self) -> None:
        """
        作为 Tensor 子类的模块在 row 4 拒绝
        """

        class _TensorModule(torch.nn.Module, torch.Tensor):  # type: ignore[misc]
            def __init__(self) -> None:
                torch.nn.Module.__init__(self)

        tensor_module = cast(torch.nn.Module, _TensorModule())
        root = _make_transparent(_ScalarParam())
        root.add_module("tensor_child", tensor_module)
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, root.state_dict())
        assert exc.value.identity == "state_installation_persistence_unsupported"


class TestUnboundNativeEntry:
    """
    证明未绑定原生 entry 使根级覆盖不被触及
    """


    def test_root_level_override_rejected_before_call(self) -> None:
        """
        根级 load_state_dict 覆盖在 row 4 拒绝，覆盖函数体不被触及
        """

        class _RootOverride(_TransparentRoot):
            def load_state_dict(  # type: ignore[override]
                self,
                state_dict: Mapping[str, object],
                is_strict: bool = True,
                is_assign: bool = False,
            ) -> object:
                """
                拒绝被 install_state 触及
                """
                override_message = "root override must not be called"
                raise AssertionError(override_message)

        over = _RootOverride()
        over.add_module("child_0", _ScalarParam())
        state_before = _clone_state(over.state_dict())
        child = cast(_ScalarParam, over.get_submodule("child_0"))
        parameter_identity = id(child.scale)
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(over, over.state_dict())
        assert exc.value.identity == "state_installation_persistence_unsupported"
        _assert_state_unchanged(over, state_before)
        assert id(child.scale) == parameter_identity


class TestConicValidation:
    """
    Conic 投影态校验与实数域身份
    """

    def test_conic_pose_state_install_and_origin_axis_checkpoint_reject_atomically(
        self,
    ) -> None:
        """
        Conic 新姿态键可安装；旧 origin/axis 键在首写前原子拒绝
        """

        target = ConicEvenAsphere(
            vertex=(0.0, 0.0, 0.0),
            tangent_x=(1.0, 0.0, 0.0),
            tangent_y=(0.0, 1.0, 0.0),
            curvature=1.0,
            conic_constant=0.0,
        )
        incoming = _clone_state(target.state_dict())
        incoming["vertex"] = torch.tensor(
            (0.0, 0.0, 2.0e-6),
            dtype=torch.float64,
        )

        install_state(target, incoming)
        assert torch.equal(
            target.vertex,
            torch.tensor((0.0, 0.0, 2.0e-6), dtype=torch.float64),
        )

        state_before_rejection = _clone_state(target.state_dict())
        origin_axis_key_state = _clone_state(incoming)
        origin_axis_key_state["conic_origin"] = origin_axis_key_state.pop("vertex")
        origin_axis_key_state["conic_axis_y"] = origin_axis_key_state.pop("tangent_x")
        origin_axis_key_state["conic_axis_x"] = origin_axis_key_state.pop("tangent_y")

        with pytest.raises(OpticalRuntimeError) as rejected:
            install_state(target, origin_axis_key_state)

        assert rejected.value.identity == "state_installation_keys_mismatch"
        state_after_rejection = target.state_dict()
        assert state_after_rejection.keys() == state_before_rejection.keys()
        for key, value in state_before_rejection.items():
            assert isinstance(value, torch.Tensor)
            assert torch.equal(state_after_rejection[key], value)

    def test_invalid_final_conic_leaves_earlier_state_unchanged(self) -> None:
        """
        末子 Conic 非法；前面的 Source 缓冲、缓存与谱系零变更
        """
        source = _plane_wave(spectrum=_mono())
        good_conic = ConicEvenAsphere(
            curvature=0.01,
            conic_constant=-0.5,
            even_coefficients=(1.0,),
            clear_aperture_radius=0.005,
        )
        bad_conic = ConicEvenAsphere(
            curvature=0.01,
            conic_constant=-0.5,
            even_coefficients=(1.0,),
            clear_aperture_radius=0.005,
        )
        root = _make_transparent(source, good_conic, bad_conic)
        grid = _grid()
        source(grid)
        cache_before = source._buffers.get("_unit_envelope_cache")
        spectrum_before = source._spectrum_value
        lineage_before = source._source_lineage
        good_curvature_before = good_conic.curvature.detach().clone()
        state = {
            k: (v.clone() if isinstance(v, torch.Tensor) else v)
            for k, v in root.state_dict().items()
        }
        state["child_2.curvature"] = torch.tensor(float("nan"), dtype=torch.float64)
        with pytest.raises(OpticalValueError) as exc:
            install_state(root, state)
        assert exc.value.identity == "conic_curvature_invalid"
        assert source._spectrum_value == spectrum_before
        assert source._source_lineage is lineage_before
        assert source._buffers.get("_unit_envelope_cache") is cache_before
        assert torch.equal(good_conic.curvature, good_curvature_before)

    def test_aperture_outside_real_domain_rejected(self) -> None:
        """
        孔径越过圆锥面实数域以新身份拒绝
        """
        conic = ConicEvenAsphere(
            curvature=0.1,
            conic_constant=0.0,
            clear_aperture_radius=1.0,
        )
        incoming = _clone_state(conic.state_dict())
        incoming["curvature"] = torch.tensor(10.0, dtype=torch.float64)
        with pytest.raises(OpticalValueError) as exc:
            install_state(conic, incoming)
        assert exc.value.identity == "conic_even_asphere_aperture_outside_real_domain"


class TestErrorPrecedence:
    """
    相邻错误优先级组合报告靠前的行
    """

    def test_dtype_before_shape(self) -> None:
        """
        dtype 违例优先于形状错
        """
        root = _make_transparent(_ScalarParam())
        state = _clone_state(root.state_dict())
        state["child_0.scale"] = torch.tensor([1.0, 2.0], dtype=torch.float32)
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(root, state)
        assert _identity_of(exc.value) == "state_installation_dtype_unsupported"

    def test_hosted_before_checkpoint_type(self) -> None:
        """
        托管根优先于 checkpoint 类型
        """
        workstation = Workstation.cpu()
        source = _plane_wave()
        workstation.host(source)
        with pytest.raises(WorkstationError) as exc:
            install_state(source, ["not", "a", "mapping"])  # type: ignore[arg-type]
        assert exc.value.identity == "workstation_hosted_state_load_forbidden"
        workstation.release(source)

    def test_keys_before_source_validation(self) -> None:
        """
        键集错优先于 Source 规划校验
        """
        target = _plane_wave(spectrum=_mono())
        state = dict(target.state_dict())
        del state["wavelengths"]
        with pytest.raises(OpticalRuntimeError) as exc:
            install_state(target, state)
        assert _identity_of(exc.value) == "state_installation_keys_mismatch"




_REQUIRES_CUDA = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="No CUDA-capable PyTorch runtime on this host.",
)


class TestCudaInstallState:
    """
    CUDA 居留未托管根的 install_state
    """

    @_REQUIRES_CUDA
    def test_cuda_resident_unhosted_install_preserves_lineage(self) -> None:
        """
        CUDA 设备上的未托管 Source 经 install_state 后谱系与缓冲一致
        """
        device = torch.device("cuda", 0)
        target = _plane_wave(spectrum=_mono())
        donor = _plane_wave(spectrum=_multi())
        target.to(device=device)
        for tensor in target.state_dict().values():
            if isinstance(tensor, torch.Tensor):
                tensor.data = tensor.data.to(device=device)
        lineage_before = target._source_lineage
        donor_state = {
            k: (v.to(device=device) if isinstance(v, torch.Tensor) else v)
            for k, v in donor.state_dict().items()
        }
        install_state(target, donor_state)
        assert target._source_lineage is lineage_before
        wavelengths = cast(torch.Tensor, target.get_buffer("wavelengths"))
        assert wavelengths.device.type == "cuda"
        assert wavelengths.shape[0] == 2
