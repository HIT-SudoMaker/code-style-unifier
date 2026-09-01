from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import copy
import io
import threading
from typing import Literal
from unittest.mock import patch
import weakref

import pytest
import torch

import chromatix_next._ownership as _ownership
from chromatix_next.errors import WorkstationError
from chromatix_next.optics import (
    Assembly,
    OpticalField,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


class _HostedElement(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造带一个实参数的最小独立元件
        """
        super().__init__()
        self.scale = torch.nn.Parameter(
            torch.tensor(1.0, dtype=torch.float64),
        )

    @property
    def role(self) -> Literal["element"]:
        """
        返回元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        保持输入光场
        """
        return field


class _HostedTree(_HostedElement):
    def __init__(self) -> None:
        """
        构造含一个内部模块的最小托管树
        """
        super().__init__()
        self.child = _HostedElement()


class _StatelessElement(torch.nn.Module):
    @property
    def role(self) -> Literal["element"]:
        """
        返回元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        保持输入光场
        """
        return field


@contextmanager
def _mock_cuda_factory() -> Iterator[None]:
    with (
        patch("torch.cuda.is_available", return_value=True),
        patch("torch.cuda.device_count", return_value=2),
        patch(
            "chromatix_next._execution_memory._default_memory_boundary_bytes",
            return_value=1024,
        ),
    ):
        yield


def _hostable_assembly() -> Assembly:
    grid = SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(1.0e-6, 1.0e-6),
    )
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=532.0e-9),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    detector = IntensityDetection()
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(detector, name="detector")
    assembly.connect(source, detector)
    assembly.expose(detector, name="intensity")
    assembly.freeze()
    return assembly


class TestExternalOwnership:
    """
    模块外弱所有权、显式解除与复制边界
    """

    def test_host_writes_no_instance_attribute(self) -> None:
        """
        托管身份不进入研究者模块的实例字典
        """
        module = _HostedElement()
        workstation = Workstation.cpu()

        workstation.host(module)

        assert "_chromatix_next_host" not in module.__dict__

    def test_release_and_rehost_preserve_parameter_identity(self) -> None:
        """
        host/release 成对且解除不移动状态，随后可由另一工作站托管
        """
        module = _HostedElement()
        first = Workstation.cpu()
        second = Workstation.cpu()
        parameter_identity = id(module.scale)

        first.host(module)
        released = first.release(module)

        assert released is module
        assert id(module.scale) == parameter_identity
        assert module.scale.dtype is torch.float64
        second.host(module)
        assert id(module.scale) == parameter_identity
        assert module.scale.dtype is torch.float64

    def test_release_requires_owner_and_original_root(self) -> None:
        """
        他站与内部模块都不能解除首次根的托管
        """
        root = _HostedTree()
        owner = Workstation.cpu()
        foreign = Workstation.cpu()
        owner.host(root)

        with pytest.raises(
            WorkstationError,
            match="workstation_release_hosted_elsewhere",
        ):
            foreign.release(root)
        with pytest.raises(
            WorkstationError,
            match="workstation_release_not_root",
        ):
            owner.release(root.child)

        assert owner.host(root) is root

    def test_release_recovers_a_changed_tree(self) -> None:
        """
        首次根即使改变拓扑也能清扫旧 claim 并重新托管
        """
        root = _HostedTree()
        workstation = Workstation.cpu()
        workstation.host(root)
        root.add_module("new_child", torch.nn.Identity())

        with pytest.raises(
            WorkstationError,
            match="workstation_host_tree_changed",
        ):
            workstation.host(root)

        workstation.release(root)
        assert workstation.host(root) is root

    def test_corrupted_partial_claim_is_rejected_and_releasable(self) -> None:
        """
        丢失内部登记的 claim 不能伪装成幂等，精确根仍可恢复
        """
        root = _HostedTree()
        workstation = Workstation.cpu()
        workstation.host(root)
        del _ownership._HOST_CLAIMS[root.child]  # noqa: SLF001

        with pytest.raises(
            WorkstationError,
            match="workstation_host_ownership_corrupted",
        ):
            workstation.host(root)

        workstation.release(root)
        assert workstation.host(root) is root

    def test_release_recovers_a_missing_root_key(self) -> None:
        """
        精确根从已移出当前树但仍存活的内部弱记录清扫损坏 claim
        """
        root = _HostedTree()
        workstation = Workstation.cpu()
        workstation.host(root)
        removed_child = root.child
        del _ownership._HOST_CLAIMS[root]  # noqa: SLF001
        del root.child

        assert workstation.release(root) is root
        assert workstation.host(root) is root
        assert workstation.host(removed_child) is removed_child

    def test_unhosted_release_is_rejected(self) -> None:
        """
        未托管对象不能伪装成成功解除
        """
        workstation = Workstation.cpu()
        with pytest.raises(
            WorkstationError,
            match="workstation_release_not_hosted",
        ):
            workstation.release(_HostedElement())

    def test_deleting_root_releases_it_immediately(self) -> None:
        """
        弱注册表不延长托管根寿命，也不依赖显式垃圾回收
        """
        workstation = Workstation.cpu()
        module = _HostedElement()
        module_reference = weakref.ref(module)
        workstation.host(module)

        del module

        assert module_reference() is None

    def test_deleting_assembly_releases_complete_tree_immediately(self) -> None:
        """
        弱注册表不保活装配、内部组件或其注册张量
        """
        workstation = Workstation.cpu()
        assembly = _hostable_assembly()
        workstation.host(assembly)
        assembly_reference = weakref.ref(assembly)
        module_references = tuple(
            weakref.ref(module)
            for module in assembly.modules()
        )
        state_references = tuple(
            weakref.ref(tensor)
            for tensor in (
                *assembly.parameters(),
                *assembly.buffers(),
            )
        )

        del assembly

        assert assembly_reference() is None
        assert all(reference() is None for reference in module_references)
        assert all(reference() is None for reference in state_references)

    def test_expired_workstation_allows_rehosting(self) -> None:
        """
        工作站先销毁时，下一次托管清扫其过期 claim
        """
        module = _HostedElement()
        workstation = Workstation.cpu()
        workstation_reference = weakref.ref(workstation)
        workstation.host(module)

        del workstation

        assert workstation_reference() is None
        replacement = Workstation.cpu()
        assert replacement.host(module) is module
        assert module.scale.dtype is torch.float64

    def test_deepcopy_and_save_do_not_transfer_ownership(self) -> None:
        """
        托管装配的深复制与 torch 序列化副本不继承工作站 claim
        """
        assembly = _hostable_assembly()
        owner = Workstation.cpu()
        owner.host(assembly)
        deep = copy.deepcopy(assembly)
        serialized = io.BytesIO()
        torch.save(assembly, serialized)
        serialized.seek(0)
        restored = torch.load(serialized, weights_only=False)
        receiver = Workstation.cpu()

        assert receiver.host(deep) is deep
        receiver.release(deep)
        assert receiver.host(restored) is restored
        receiver.release(restored)
        original_outputs, _ = owner.run(assembly)
        assert tuple(original_outputs) == ("intensity",)


class TestPlatformOwnershipPolicy:
    """
    Windows 单 CUDA 工作站与 Linux 多卡工作站策略
    """

    def test_windows_allows_only_one_live_cuda_workstation(self) -> None:
        """
        Windows 第二个存活 CUDA 工作站被稳定拒绝，销毁后可重建
        """
        with (
            patch.object(
                _ownership,
                "_is_windows_platform",
                return_value=True,
            ),
            patch.object(
                _ownership,
                "_WINDOWS_CUDA_WORKSTATION",
                None,
            ),
            _mock_cuda_factory(),
        ):
            first = Workstation.cuda(0)
            with pytest.raises(
                WorkstationError,
                match="workstation_windows_cuda_singleton_required",
            ):
                Workstation.cuda(1)
            first_reference = weakref.ref(first)
            del first
            assert first_reference() is None
            replacement = Workstation.cuda(0)
            assert replacement.device == torch.device("cuda", 0)

    def test_release_does_not_release_windows_cuda_singleton(self) -> None:
        """
        解除组件所有权不等于销毁 CUDA 工作站
        """
        with (
            patch.object(
                _ownership,
                "_is_windows_platform",
                return_value=True,
            ),
            patch.object(
                _ownership,
                "_WINDOWS_CUDA_WORKSTATION",
                None,
            ),
            _mock_cuda_factory(),
        ):
            workstation = Workstation.cuda(0)
            module = _StatelessElement()
            workstation.host(module)
            workstation.release(module)

            with pytest.raises(
                WorkstationError,
                match="workstation_windows_cuda_singleton_required",
            ):
                Workstation.cuda(1)

    @pytest.mark.skipif(
        not torch.cuda.is_available(),
        reason="真实 CUDA 显存引用释放证据需要当前环境存在可用 CUDA 设备",
    )
    def test_deleting_cuda_assembly_releases_allocated_memory(self) -> None:
        """
        删除完整 CUDA 装配立即释放其张量占用，不把缓存池 reserved 当成占用
        """
        device_index = 0
        torch.cuda.synchronize(device_index)
        baseline = torch.cuda.memory_allocated(device_index)
        workstation = Workstation.cuda(device_index)
        assembly = _hostable_assembly()
        workstation.host(assembly)
        torch.cuda.synchronize(device_index)
        hosted_allocation = torch.cuda.memory_allocated(device_index)
        assembly_reference = weakref.ref(assembly)
        state_references = tuple(
            weakref.ref(tensor)
            for tensor in (
                *assembly.parameters(),
                *assembly.buffers(),
            )
        )

        del assembly
        torch.cuda.synchronize(device_index)

        assert hosted_allocation > baseline
        assert assembly_reference() is None
        assert all(reference() is None for reference in state_references)
        assert torch.cuda.memory_allocated(device_index) <= baseline


class TestTransactionalHostInterface:
    """
    ownership 原子 host 接口与失败回滚契约
    """



    def test_concurrent_commit_host_serializes_without_corruption(
        self,
    ) -> None:
        """
        两线程并发托管同一根时仅执行一次 placement
        """
        workstation = Workstation.cpu()
        module = _HostedElement()
        barrier = threading.Barrier(2)
        placement_calls: list[int] = []
        placement_lock = threading.Lock()

        def _counting_place(modules: tuple[torch.nn.Module, ...]) -> None:
            with placement_lock:
                placement_calls.append(len(modules))

        def _attempt() -> None:
            barrier.wait()
            _ownership._commit_host(
                workstation,
                module,
                _counting_place,
            )

        threads = [threading.Thread(target=_attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(placement_calls) == 1
        assert _ownership._assert_hosted(
            workstation,
            module,
        ) == tuple(module.modules())

    def test_commit_host_rolls_back_claim_when_placement_raises(
        self,
    ) -> None:
        """
        placement 回调抛异常时，commit_host 不登记 claim 且可重试
        """
        workstation = Workstation.cpu()
        module = _HostedTree()
        original_dtype = module.scale.dtype

        def _failing_place(modules: tuple[torch.nn.Module, ...]) -> None:
            placement_identity = "placement_simulated_failure"
            raise RuntimeError(placement_identity)

        with pytest.raises(RuntimeError, match="placement_simulated_failure"):
            _ownership._commit_host(workstation, module, _failing_place)

        assert _ownership._HOST_CLAIMS.get(module) is None  # noqa: SLF001
        assert _ownership._HOST_CLAIMS.get(module.child) is None  # noqa: SLF001
        assert module.scale.dtype is original_dtype

        _ownership._commit_host(
            workstation,
            module,
            lambda modules: None,
        )
        assert _ownership._assert_hosted(
            workstation,
            module,
        ) == tuple(module.modules())


    def test_commit_host_recovers_after_manual_registry_corruption(
        self,
    ) -> None:
        """
        注册表被外部损坏后，commit_host 拒绝伪幂等，release 后可重新 commit
        """
        root = _HostedTree()
        workstation = Workstation.cpu()
        _ownership._commit_host(workstation, root, lambda modules: None)
        del _ownership._HOST_CLAIMS[root.child]  # noqa: SLF001

        with pytest.raises(
            WorkstationError,
            match="workstation_host_ownership_corrupted",
        ):
            _ownership._commit_host(workstation, root, lambda modules: None)

        workstation.release(root)
        _ownership._commit_host(
            workstation,
            root,
            lambda modules: None,
        )
        assert _ownership._assert_hosted(
            workstation,
            root,
        ) == tuple(root.modules())




class _SharedParameterElement(_HostedElement):
    def __init__(self, parameter: torch.nn.Parameter) -> None:
        """
        构造携带一个外部共享参数的独立元件
        """
        super().__init__()
        self.shared = parameter


class _SharedBufferElement(_HostedElement):
    def __init__(
        self,
        buffer: torch.Tensor,
        *,
        is_persistent: bool = True,
    ) -> None:
        """
        构造携带一个外部共享 Buffer 的独立元件
        """
        super().__init__()
        self.register_buffer(
            "shared_buf",
            buffer,
            persistent=is_persistent,
        )


class _TiedParameterElement(_HostedElement):
    def __init__(self) -> None:
        """
        构造同一 Parameter 在两个槽位复用的元件（tied weights）
        """
        super().__init__()
        self.tied = self.scale


class _SharedParameterPair(torch.nn.Module):
    def __init__(self, shared: torch.nn.Parameter) -> None:
        """
        构造两个子模块复用同一 Parameter 的最小树，供梯度共鸣证据使用
        """
        super().__init__()
        self.left = torch.nn.Module()
        self.left.w = shared
        self.right = torch.nn.Module()
        self.right.w = shared


class _PartialStorageViewRoot(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造同一 storage 的两个相异局部视图（full[0::2] 与 full），供 Part D 证据
        """
        super().__init__()
        full = torch.arange(8, dtype=torch.float32)
        self.sliced = torch.nn.Parameter(full[0::2])
        self.whole = torch.nn.Parameter(full)


class _ExactAliasViewRoot(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造同一 storage 的两个精确别名（相异对象、全同视图：full 与 full[:]）
        """
        super().__init__()
        full = torch.arange(8, dtype=torch.float32)
        self.primary = torch.nn.Parameter(full)
        self.alias = torch.nn.Parameter(full[:])


class TestIdentityScopeOwnership:
    """
    模块、裸 Parameter、aliased Storage 三类身份的 claim、同根复用与跨根原子拒绝
    """

    def test_host_claims_tied_parameter_once_per_root(self) -> None:
        """
        同一 Parameter 在同一根内多处复用合法，traversal 去重后只出现一次
        """
        workstation = Workstation.cpu()
        module = _TiedParameterElement()
        workstation.host(module)
        # tied 与 scale 是同一对象，hosting 后仍共享 storage（共鸣未断）
        assert module.scale is module.tied
        assert module.scale.data_ptr() == module.tied.data_ptr()
        # 普通 traversal 原生去重后只出现一次
        dedup_names = list(module.named_parameters(remove_duplicate=True))
        full_names = list(module.named_parameters(remove_duplicate=False))
        assert len(dedup_names) == 1
        assert len(full_names) == 2
        # 同根内复用的参数与存储不另开所有权记录
        scale_identity = id(module.scale)
        storage_identity = int(module.scale.untyped_storage()._cdata)
        assert _ownership._PARAMETER_CLAIMS.get(scale_identity) is not None
        assert _ownership._STORAGE_CLAIMS.get(storage_identity) is not None

    def test_cross_root_shared_parameter_rejected_atomically(self) -> None:
        """
        同一 Parameter 对象被第二个根触及时，在移动数据前原子拒绝
        """
        owner = Workstation.cpu()
        foreign = Workstation.cpu()
        shared = torch.nn.Parameter(
            torch.tensor([1.0, 2.0], dtype=torch.float64),
        )
        root_a = _SharedParameterElement(shared)
        root_b = _SharedParameterElement(shared)
        owner.host(root_a)
        with pytest.raises(
            WorkstationError,
            match="workstation_host_already_hosted",
        ):
            foreign.host(root_b)
        # 失败方的 placement 未执行：root_b 自有的 scale 仍是初始 float64
        assert root_b.scale.dtype is torch.float64

    def test_cross_root_shared_storage_rejected_atomically(self) -> None:
        """
        不同 Parameter 对象共享同一底层 Storage 时，第二个根被原子拒绝
        """
        owner = Workstation.cpu()
        foreign = Workstation.cpu()
        first = torch.nn.Parameter(
            torch.tensor([1.0, 2.0], dtype=torch.float64),
        )
        root_a = _SharedParameterElement(first)
        owner.host(root_a)
        # second 与 first 共享 host 之后当前 storage（即已被 claim 的身份）
        second = torch.nn.Parameter(first.data)
        root_b = _SharedParameterElement(second)
        with pytest.raises(
            WorkstationError,
            match="workstation_host_already_hosted",
        ):
            foreign.host(root_b)
        assert root_b.scale.dtype is torch.float64

    def test_cross_root_shared_buffer_rejected_atomically(self) -> None:
        """
        同一 persistent Buffer storage 被第二个根触及时，在移动数据前原子拒绝
        """
        owner = Workstation.cpu()
        foreign = Workstation.cpu()
        shared = torch.tensor([1.0, 2.0], dtype=torch.float64)
        root_a = _SharedBufferElement(shared)
        root_b = _SharedBufferElement(shared)
        placement_calls: list[int] = []

        def _observing_place(modules: tuple[torch.nn.Module, ...]) -> None:
            placement_calls.append(len(modules))

        _ownership._commit_host(owner, root_a, _observing_place)
        with pytest.raises(
            WorkstationError,
            match="workstation_host_already_hosted",
        ):
            _ownership._commit_host(foreign, root_b, _observing_place)
        # 失败方的 placement 未执行：跨根 Buffer 共享在移动数据前即被拒
        assert len(placement_calls) == 1
        assert _ownership._HOST_CLAIMS.get(root_b) is None  # noqa: SLF001
        # root_a 的 Buffer storage 已被 claim（存储归属跟随存储身份）
        shared_storage = int(shared.untyped_storage()._cdata)
        assert _ownership._STORAGE_CLAIMS.get(shared_storage) is not None

    def test_cross_root_shared_nonpersistent_buffer_rejected_atomically(
        self,
    ) -> None:
        """
        同一 nonpersistent Buffer storage 被第二个根触及时同样被原子拒绝
        """
        owner = Workstation.cpu()
        foreign = Workstation.cpu()
        cache = torch.zeros(3, dtype=torch.float64)
        root_a = _SharedBufferElement(cache, is_persistent=False)
        root_b = _SharedBufferElement(cache, is_persistent=False)
        _ownership._commit_host(owner, root_a, lambda modules: None)
        with pytest.raises(
            WorkstationError,
            match="workstation_host_already_hosted",
        ):
            _ownership._commit_host(foreign, root_b, lambda modules: None)
        cache_storage = int(cache.untyped_storage()._cdata)
        assert _ownership._STORAGE_CLAIMS.get(cache_storage) is not None

    def test_cross_root_shared_module_rejected_atomically(self) -> None:
        """
        第二个根触及已 claim 的子模块时，在移动数据前原子拒绝
        """
        owner = Workstation.cpu()
        foreign = Workstation.cpu()
        shared_tree = _HostedTree()
        root_b = torch.nn.Module()
        root_b.add_module("shared", shared_tree)
        owner.host(shared_tree)
        with pytest.raises(
            WorkstationError,
            match="workstation_host_already_hosted",
        ):
            foreign.host(root_b)

    def test_release_clears_parameter_and_storage_claims(self) -> None:
        """
        解除首次根一并清扫模块、Parameter、Storage 三类身份，他站随后可托管
        """
        owner = Workstation.cpu()
        foreign = Workstation.cpu()
        module = _TiedParameterElement()
        owner.host(module)
        scale_identity = id(module.scale)
        storage_identity = int(module.scale.untyped_storage()._cdata)
        assert _ownership._PARAMETER_CLAIMS.get(scale_identity) is not None
        assert _ownership._STORAGE_CLAIMS.get(storage_identity) is not None
        owner.release(module)
        assert _ownership._PARAMETER_CLAIMS.get(scale_identity) is None
        assert _ownership._STORAGE_CLAIMS.get(storage_identity) is None
        assert foreign.host(module) is module


class TestHostTransactionRollback:
    """
    失败托管事务不留 leaked claim、lock、partial placement 或改动的张量值
    """

    def test_failing_place_leaves_no_claim_and_no_value_change(self) -> None:
        """
        place 抛异常时三类注册表都不留新条目，且原 dtype 不变
        """
        workstation = Workstation.cpu()
        module = _HostedTree()
        original_dtype = module.scale.dtype
        parameters_before = dict(_ownership._PARAMETER_CLAIMS)
        storages_before = dict(_ownership._STORAGE_CLAIMS)

        def _failing(modules: tuple[torch.nn.Module, ...]) -> None:
            identity = "placement_simulated_failure"
            raise RuntimeError(identity)

        with pytest.raises(RuntimeError, match="placement_simulated_failure"):
            _ownership._commit_host(workstation, module, _failing)

        assert _ownership._HOST_CLAIMS.get(module) is None
        assert _ownership._HOST_CLAIMS.get(module.child) is None
        assert _ownership._PARAMETER_CLAIMS == parameters_before
        assert _ownership._STORAGE_CLAIMS == storages_before
        assert module.scale.dtype is original_dtype



class TestAliasPreservationAcrossCopy:
    """
    深复制与序列化保住根内别名且不跨根
    """

    def test_deepcopy_preserves_tie_and_carries_no_claim(self) -> None:
        """
        深复制保住 tied weights，副本不继承原根 claim，他站可直接托管
        """
        owner = Workstation.cpu()
        module = _TiedParameterElement()
        owner.host(module)
        deep = copy.deepcopy(module)
        assert deep.scale is deep.tied
        receiver = Workstation.cpu()
        assert receiver.host(deep) is deep

    def test_serialization_preserves_tie_and_carries_no_claim(self) -> None:
        """
        序列化与反序列化保住共享权重，副本不继承所有权
        """
        owner = Workstation.cpu()
        module = _TiedParameterElement()
        owner.host(module)
        buffer = io.BytesIO()
        torch.save(module, buffer)
        buffer.seek(0)
        restored = torch.load(buffer, weights_only=False)
        assert restored.scale is restored.tied
        receiver = Workstation.cpu()
        assert receiver.host(restored) is restored


class TestCopiedHostedGuardInert:
    """
    拷贝（deepcopy / 序列化）带过来的 hosted-load 守卫在副本独立托管前是 inert 的
    """

    def test_deepcopy_guard_is_inert_until_independently_hosted(self) -> None:
        """
        deepcopy 托管根：副本不继承 claim，原生 load_state_dict 不被拦截（守卫 no-op）
        """
        owner = Workstation.cpu()
        module = _TiedParameterElement()
        owner.host(module)
        deep = copy.deepcopy(module)
        assert deep is not module
        assert _ownership._HOST_CLAIMS.get(deep) is None  # noqa: SLF001
        assert deep.scale is deep.tied
        value = torch.tensor(9.0, dtype=torch.float32)
        # 拷贝过来的守卫在未托管副本上 no-op：load_state_dict 经原生 copy_ 写穿，不抛
        deep.load_state_dict({"scale": value, "tied": value.clone()})
        assert torch.equal(deep.scale.data, value.to(deep.scale.dtype))

    def test_serialization_guard_is_inert_then_rejects_after_independent_host(
        self,
    ) -> None:
        """
        torch.save/load 往返保持守卫零状态：未托管副本不拦截；独立托管后再生效拒绝
        """
        owner = Workstation.cpu()
        module = _TiedParameterElement()
        owner.host(module)
        buffer = io.BytesIO()
        torch.save(module, buffer)
        buffer.seek(0)
        restored = torch.load(buffer, weights_only=False)
        assert _ownership._HOST_CLAIMS.get(restored) is None  # noqa: SLF001
        value = torch.tensor(9.0, dtype=torch.float32)
        # 未托管的反序列化副本：load_state_dict 不抛（守卫 inert）
        restored.load_state_dict({"scale": value, "tied": value.clone()})
        # 独立托管后，守卫再次拒绝任何 hosted load（不只是一个别名冲突子集）
        receiver = Workstation.cpu()
        receiver.host(restored)
        with pytest.raises(
            WorkstationError,
            match="workstation_hosted_state_load_forbidden",
        ):
            restored.load_state_dict(
                {"scale": torch.tensor(5.0), "tied": torch.tensor(5.0)},
            )


class TestReleaseRehostTogglesHostedGuard:
    """
    解除托管后守卫不再拦截；重新托管后再次拒绝 hosted load
    """

    def test_release_then_rehost_toggles_load_rejection(self) -> None:
        """
        release 后 load_state_dict 回落到原生语义不抛；re-host 后再次被守卫拒绝
        """
        workstation = Workstation.cpu()
        module = _TiedParameterElement()
        workstation.host(module)
        workstation.release(module)
        # 解除后：守卫已移除，load_state_dict 不再被本站拦截
        module.load_state_dict(
            {"scale": torch.tensor(5.0), "tied": torch.tensor(7.0)},
        )
        # 重新托管：守卫重新登记，hosted load 再次被拒
        workstation.host(module)
        with pytest.raises(
            WorkstationError,
            match="workstation_hosted_state_load_forbidden",
        ):
            module.load_state_dict(
                {"scale": torch.tensor(5.0), "tied": torch.tensor(7.0)},
            )


class TestHostedLoadRejection:
    """
    托管根与子模块上的原生 load_state_dict 在任何 copy_/assign 前整体拒绝
    """

    def test_root_hosted_load_rejects_before_mutation(self) -> None:
        """
        托管根 load_state_dict 在任何 copy_ 前被拒，注册态原样未动
        """
        workstation = Workstation.cpu()
        module = _TiedParameterElement()
        workstation.host(module)
        before = module.scale.data.clone()
        with pytest.raises(
            WorkstationError,
            match="workstation_hosted_state_load_forbidden",
        ):
            module.load_state_dict({"scale": torch.tensor(5.0)})
        assert torch.equal(module.scale.data, before)

    def test_child_hosted_load_rejects_before_mutation(self) -> None:
        """
        子模块 load_state_dict 同样被拒：守卫登记在每个被 claim 的子模块上
        """
        workstation = Workstation.cpu()
        root = _HostedTree()
        workstation.host(root)
        before = root.child.scale.data.clone()
        with pytest.raises(
            WorkstationError,
            match="workstation_hosted_state_load_forbidden",
        ):
            root.child.load_state_dict({"scale": torch.tensor(5.0)})
        assert torch.equal(root.child.scale.data, before)

    def test_strict_false_hosted_load_rejects(self) -> None:
        """
        strict=False 仍触发守卫：pre-hook 与 strict 无关
        """
        workstation = Workstation.cpu()
        module = _TiedParameterElement()
        workstation.host(module)
        with pytest.raises(
            WorkstationError,
            match="workstation_hosted_state_load_forbidden",
        ):
            module.load_state_dict({"scale": torch.tensor(5.0)}, strict=False)

    def test_assign_true_hosted_load_rejects(self) -> None:
        """
        assign=True 仍触发守卫：pre-hook 在任何 assign 前先烧
        """
        workstation = Workstation.cpu()
        module = _TiedParameterElement()
        workstation.host(module)
        with pytest.raises(
            WorkstationError,
            match="workstation_hosted_state_load_forbidden",
        ):
            module.load_state_dict({"scale": torch.tensor(5.0)}, assign=True)

    def test_consistent_value_hosted_load_rejects(self) -> None:
        """
        一致值的 hosted load 也被拒：托管期禁止任何原生 load，不只是别名冲突
        """
        workstation = Workstation.cpu()
        module = _TiedParameterElement()
        workstation.host(module)
        consistent = torch.tensor(5.0)
        with pytest.raises(
            WorkstationError,
            match="workstation_hosted_state_load_forbidden",
        ):
            module.load_state_dict(
                {"scale": consistent, "tied": consistent.clone()},
            )


class TestHostedLoadGuardOrdering:
    """
    守卫位于 pre-hooks 字典首位，使其在任何外部 hook 前先抛
    """

    def test_guard_sits_first_and_external_hook_never_called(self) -> None:
        """
        守卫位于前置钩子字典首位；hosted load 触发时它先抛
        """
        workstation = Workstation.cpu()
        module = _HostedElement()
        workstation.host(module)
        external_calls: list[int] = []

        def _external_hook(
            module_: torch.nn.Module,
            state_dict: dict,
            prefix: str,
        ) -> None:
            external_calls.append(1)

        handle = module.register_load_state_dict_pre_hook(_external_hook)
        hooks = module._load_state_dict_pre_hooks  # noqa: SLF001
        guard_ids = [
            hid
            for hid, hk in hooks.items()
            if isinstance(getattr(hk, "hook", hk), _ownership._HostedStateLoadGuard)
        ]
        assert guard_ids, "守卫应已登记"
        assert next(iter(hooks)) == guard_ids[0], "守卫应位于 pre-hooks 首位"
        assert handle.id != guard_ids[0]
        with pytest.raises(
            WorkstationError,
            match="workstation_hosted_state_load_forbidden",
        ):
            module.load_state_dict({"scale": torch.tensor(5.0)})
        assert external_calls == [], "外部 side-effect hook 在守卫拒绝前不应被调用"

    def test_source_planning_never_entered_on_hosted_load(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        hosted load 不会进入 install_state 的 Source 规划/resize 路径
        """
        from chromatix_next import _state_installation

        planner_calls: list[int] = []

        def _fail_if_called(*args: object, **kwargs: object) -> None:
            planner_calls.append(1)
            planning_unexpected = "Source 规划路径不应在 hosted load 时进入"
            raise AssertionError(planning_unexpected)

        monkeypatch.setattr(
            _state_installation,
            "_run_source_and_conic_planners",
            _fail_if_called,
        )
        monkeypatch.setattr(
            _state_installation,
            "_plan_state_installation",
            _fail_if_called,
        )
        workstation = Workstation.cpu()
        assembly = _hostable_assembly()
        workstation.host(assembly)
        with pytest.raises(
            WorkstationError,
            match="workstation_hosted_state_load_forbidden",
        ):
            assembly.load_state_dict(assembly.state_dict())
        assert planner_calls == []


class TestHostFailureRollback:
    """
    8 步序失败语义：预检/守卫/staging 失败不动注册态、不留 claim；
    rebind/verify/claim 失败按快照复原原注册张量图、移除守卫、不留 claim
    """

    def test_guard_install_failure_leaves_no_guards_and_no_claim(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        守卫安装中途失败时已登记守卫全部自回滚，注册表不留 claim、注册态未动
        """
        workstation = Workstation.cpu()
        module = _HostedTree()
        original = module.child.scale.data.clone()
        original_root_hooks = dict(module._load_state_dict_pre_hooks)
        original_child_hooks = dict(module.child._load_state_dict_pre_hooks)
        register_calls = [0]
        real_register = torch.nn.Module.register_load_state_dict_pre_hook

        def _failing_register(
            self_: torch.nn.Module,
            hook: object,
        ) -> object:
            register_calls[0] += 1
            if register_calls[0] == 2:
                register_identity = "guard_register_simulated_failure"
                raise RuntimeError(register_identity)
            return real_register(self_, hook)

        monkeypatch.setattr(
            torch.nn.Module,
            "register_load_state_dict_pre_hook",
            _failing_register,
        )
        with pytest.raises(RuntimeError, match="guard_register_simulated_failure"):
            _ownership._commit_host(
                workstation,
                module,
                lambda modules: None,
            )
        # 自回滚：根与子模块的 pre-hooks 字典都回到原样
        assert dict(module._load_state_dict_pre_hooks) == original_root_hooks
        assert (
            dict(module.child._load_state_dict_pre_hooks)
            == original_child_hooks
        )
        assert _ownership._HOST_CLAIMS.get(module) is None  # noqa: SLF001
        assert _ownership._HOST_CLAIMS.get(module.child) is None  # noqa: SLF001
        assert torch.equal(module.child.scale.data, original)

    def test_staging_failure_leaves_no_claim_no_guard_no_mutation(self) -> None:
        """
        placement 在 staging 阶段抛异常：不留 claim、不留守卫、张量值未动
        """
        workstation = Workstation.cpu()
        module = _HostedTree()
        original = module.child.scale.data.clone()
        original_hooks = dict(module._load_state_dict_pre_hooks)

        def _failing_stage(
            modules: tuple[torch.nn.Module, ...],
        ) -> None:
            del modules
            staging_identity = "staging_simulated_failure"
            raise RuntimeError(staging_identity)

        with pytest.raises(RuntimeError, match="staging_simulated_failure"):
            _ownership._commit_host(workstation, module, _failing_stage)
        assert _ownership._HOST_CLAIMS.get(module) is None  # noqa: SLF001
        assert _ownership._HOST_CLAIMS.get(module.child) is None  # noqa: SLF001
        assert dict(module._load_state_dict_pre_hooks) == original_hooks
        assert torch.equal(module.child.scale.data, original)

    def test_verify_failure_restores_graph_and_removes_guards(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        post-placement 验证失败：按快照复原注册张量图、移除守卫、不留 claim
        """
        workstation = Workstation.cpu()
        module = _HostedTree()
        original = module.child.scale.data.clone()
        original_hooks = dict(module._load_state_dict_pre_hooks)

        def _failing_verify(
            snapshot: object,
            ws: object,
        ) -> None:
            del snapshot, ws
            raise WorkstationError(
                "workstation_host_identity_graph_unstable",
                "simulated",
            )

        monkeypatch.setattr(
            _ownership,
            "_verify_placed_identity_graph",
            _failing_verify,
        )
        with pytest.raises(
            WorkstationError,
            match="workstation_host_identity_graph_unstable",
        ):
            _ownership._commit_host(
                workstation,
                module,
                workstation._move_module_tree,  # noqa: SLF001
            )
        assert _ownership._HOST_CLAIMS.get(module) is None  # noqa: SLF001
        assert _ownership._HOST_CLAIMS.get(module.child) is None  # noqa: SLF001
        assert dict(module._load_state_dict_pre_hooks) == original_hooks
        assert torch.equal(module.child.scale.data, original)


    def test_rogue_placement_breaking_aliases_rejected_by_verify(self) -> None:
        """
        rogue placement 独立 stage 每个参数（断开精确别名但保持设备/dtype）被 step 7 拒
        """
        workstation = Workstation.cpu()
        module = _ExactAliasFloat64Root()
        assert module.primary is not module.alias
        original_primary_cdata = int(
            module.primary.untyped_storage()._cdata,
        )

        def _rogue_place(
            modules: tuple[torch.nn.Module, ...],
        ) -> None:
            # 每个 Parameter 独立 clone 到新 storage——设备/dtype 不变，但精确别名被断开
            for mod in modules:
                for parameter in mod._parameters.values():
                    if parameter is None:
                        continue
                    parameter.data = parameter.detach().clone()

        with pytest.raises(
            WorkstationError,
            match="workstation_host_identity_graph_unstable",
        ):
            _ownership._commit_host(workstation, module, _rogue_place)
        # 拒绝后不留 claim、原精确别名经快照复原（共享同一 storage _cdata）
        assert _ownership._HOST_CLAIMS.get(module) is None  # noqa: SLF001
        assert (
            int(module.primary.untyped_storage()._cdata)
            == int(module.alias.untyped_storage()._cdata)
            == original_primary_cdata
        )

    def test_rogue_placement_breaking_view_shape_rejected_by_verify(self) -> None:
        """
        rogue placement 改写形状（保持设备/dtype/storage）被 step 7 拒
        """
        workstation = Workstation.cpu()
        module = _ExactAliasFloat64Root()

        def _rogue_place(
            modules: tuple[torch.nn.Module, ...],
        ) -> None:
            for mod in modules:
                for parameter in mod._parameters.values():
                    if parameter is None:
                        continue
                    # 同 storage、同 dtype，但 shape 从 (8,) 改成 (2,4) —— 视图漂移
                    parameter.data = parameter.data.reshape(2, 4)

        with pytest.raises(
            WorkstationError,
            match="workstation_host_identity_graph_unstable",
        ):
            _ownership._commit_host(workstation, module, _rogue_place)
        assert _ownership._HOST_CLAIMS.get(module) is None  # noqa: SLF001

    def test_preexisting_guards_restored_after_staging_failure_on_copied_tree(
        self,
    ) -> None:
        """
        deepcopy 带过来的旧守卫在 staging 失败后被原位还原（pre-hooks 字典字节一致）
        """
        owner = Workstation.cpu()
        original = _TiedParameterElement()
        owner.host(original)
        deep = copy.deepcopy(original)
        deep_hooks = deep._load_state_dict_pre_hooks  # noqa: SLF001
        deep_hooks_before = list(deep_hooks.items())
        assert deep_hooks_before, "deepcopy 应携带拷贝来的守卫"
        receiver = Workstation.cpu()

        def _failing_stage(
            modules: tuple[torch.nn.Module, ...],
        ) -> None:
            del modules
            staging_identity = "staging_simulated_failure"
            raise RuntimeError(staging_identity)

        with pytest.raises(RuntimeError, match="staging_simulated_failure"):
            _ownership._commit_host(receiver, deep, _failing_stage)
        # staging 失败后，pre-hooks 字典按 host 前字节复原（dedup 删除的旧守卫原位还原）
        assert list(deep_hooks.items()) == deep_hooks_before
        assert _ownership._HOST_CLAIMS.get(deep) is None  # noqa: SLF001


class TestHostPersistencePreflight:
    """
    Host preflight：覆盖或实例 shadow 两个原生持久化方法之一即整体拒绝
    """

    def test_type_override_load_state_dict_rejected_at_preflight(self) -> None:
        """
        类型层覆盖 load_state_dict 在放置前以稳定身份拒绝，注册表不留 claim
        """
        workstation = Workstation.cpu()
        module = type(
            "_Overridden",
            (_HostedElement,),
            {"load_state_dict": lambda self, *args: None},
        )()
        with pytest.raises(
            WorkstationError,
            match="workstation_host_persistence_unsupported",
        ):
            workstation.host(module)
        assert _ownership._HOST_CLAIMS.get(module) is None  # noqa: SLF001

    def test_type_override_load_from_state_dict_rejected_at_preflight(self) -> None:
        """
        类型层覆盖 _load_from_state_dict 同样在放置前拒绝
        """
        workstation = Workstation.cpu()
        module = type(
            "_Overridden",
            (_HostedElement,),
            {"_load_from_state_dict": lambda self, *args: None},
        )()
        with pytest.raises(
            WorkstationError,
            match="workstation_host_persistence_unsupported",
        ):
            workstation.host(module)
        assert _ownership._HOST_CLAIMS.get(module) is None  # noqa: SLF001

    def test_instance_shadow_load_state_dict_rejected_at_preflight(self) -> None:
        """
        实例级 shadow load_state_dict 在放置前拒绝（绕过类型层覆盖检测）
        """
        workstation = Workstation.cpu()
        module = _HostedElement()
        module.__dict__["load_state_dict"] = lambda *args: None
        with pytest.raises(
            WorkstationError,
            match="workstation_host_persistence_unsupported",
        ):
            workstation.host(module)

    def test_instance_shadow_load_from_state_dict_rejected_at_preflight(
        self,
    ) -> None:
        """
        实例级 shadow _load_from_state_dict 在放置前拒绝
        """
        workstation = Workstation.cpu()
        module = _HostedElement()
        module.__dict__["_load_from_state_dict"] = lambda *args: None
        with pytest.raises(
            WorkstationError,
            match="workstation_host_persistence_unsupported",
        ):
            workstation.host(module)




class _ExactAliasFloat64Root(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造 primary 与 alias 两个相异对象共享同一 storage 全同视图（固定双精度）
        """
        super().__init__()
        full = torch.arange(8, dtype=torch.float64)
        self.primary = torch.nn.Parameter(full)
        self.alias = torch.nn.Parameter(full[:])


class TestExactAliasPlacement:
    """
    精确别名（相异对象、全同视图）在 CPU 与 CUDA 上 stage 一次并保持别名
    """

    def test_exact_aliases_remain_aliases_on_cpu(self) -> None:
        """
        CPU 上同 storage 只 stage 一次：两个相异对象仍精确别名
        """
        workstation = Workstation.cpu()
        module = _ExactAliasFloat64Root()
        assert module.primary is not module.alias
        _ownership._commit_host(  # noqa: SLF001
            workstation,
            module,
            workstation._move_module_tree,  # noqa: SLF001
        )
        assert module.primary.data_ptr() == module.alias.data_ptr()
        assert (
            int(module.primary.untyped_storage()._cdata)
            == int(module.alias.untyped_storage()._cdata)
        )

    @pytest.mark.skipif(
        not torch.cuda.is_available(),
        reason="CUDA 精确别名保持证据需要当前环境存在可用 CUDA 设备",
    )
    def test_exact_aliases_remain_aliases_on_cuda(self) -> None:
        """
        CUDA 上同 storage 只 stage 一次：两槽 rebind 到同一 staged 张量
        """
        workstation = Workstation.cuda(0)
        module = _ExactAliasFloat64Root()
        assert module.primary is not module.alias
        _ownership._commit_host(  # noqa: SLF001
            workstation,
            module,
            workstation._move_module_tree,  # noqa: SLF001
        )
        assert module.primary.device.type == "cuda"
        assert module.primary.data_ptr() == module.alias.data_ptr()
        assert (
            int(module.primary.untyped_storage()._cdata)
            == int(module.alias.untyped_storage()._cdata)
        )
        workstation.release(module)


class TestHostPartialStorageViewRejection:
    """
    托管放置前的局部视图 preflight：相异局部视图拒绝、精确别名与同对象复用放行
    """

    def test_distinct_partial_storage_views_rejected_at_host(self) -> None:
        """
        同一 storage 上两个相异局部视图（full[0::2] 与 full）在放置前以新稳定身份被拒
        """
        workstation = Workstation.cpu()
        module = _PartialStorageViewRoot()
        placement_calls: list[int] = []

        def _observing(modules: tuple[torch.nn.Module, ...]) -> None:
            placement_calls.append(len(modules))

        with pytest.raises(
            WorkstationError,
            match="workstation_host_partial_storage_view",
        ):
            _ownership._commit_host(workstation, module, _observing)  # noqa: SLF001
        # 拒绝发生在 placement 之前：place 一次都没跑，注册表不留 claim
        assert placement_calls == []
        assert _ownership._HOST_CLAIMS.get(module) is None  # noqa: SLF001

    def test_exact_alias_views_not_rejected_at_host(self) -> None:
        """
        同一 storage 上两个相异对象但精确同视图的别名不被局部视图 preflight 拒绝
        """
        workstation = Workstation.cpu()
        module = _ExactAliasViewRoot()
        placement_calls: list[int] = []

        def _observing(modules: tuple[torch.nn.Module, ...]) -> None:
            placement_calls.append(len(modules))

        _ownership._commit_host(workstation, module, _observing)  # noqa: SLF001
        # 精确别名放行：placement 正常执行，claim 已登记
        assert placement_calls == [1]
        assert _ownership._HOST_CLAIMS.get(module) is not None  # noqa: SLF001

    def test_same_object_reuse_not_rejected_at_host(self) -> None:
        """
        同一 Parameter 对象在多槽复用（tied weights）不被局部视图 preflight 拒绝
        """
        workstation = Workstation.cpu()
        module = _TiedParameterElement()
        placement_calls: list[int] = []

        def _observing(modules: tuple[torch.nn.Module, ...]) -> None:
            placement_calls.append(len(modules))

        _ownership._commit_host(workstation, module, _observing)  # noqa: SLF001
        assert placement_calls == [1]
        assert _ownership._HOST_CLAIMS.get(module) is not None  # noqa: SLF001


class TestSharedParameterGradient:
    """
    共享 Parameter 的梯度共鸣与 CPU/CUDA 覆盖
    """

    def test_shared_parameter_gradient_resonates_on_cpu(self) -> None:
        """
        同一 Parameter 两次使用在反向后把梯度累加进同一份（CPU）
        """
        workstation = Workstation.cpu()
        shared = torch.nn.Parameter(
            torch.tensor([2.0, 4.0], dtype=torch.float64),
        )
        root = _SharedParameterPair(shared)
        _ownership._commit_host(
            workstation,
            root,
            workstation._move_module_tree,  # noqa: SLF001
        )
        left_w = root.left.w
        right_w = root.right.w
        assert isinstance(left_w, torch.nn.Parameter)
        assert isinstance(right_w, torch.nn.Parameter)
        assert left_w is right_w
        assert left_w.data_ptr() == right_w.data_ptr()
        loss = (left_w * right_w).sum()
        loss.backward()
        assert shared.grad is not None
        assert torch.allclose(shared.grad, 2.0 * shared.detach())

    @pytest.mark.skipif(
        not torch.cuda.is_available(),
        reason="CUDA 共享参数梯度证据需要当前环境存在可用 CUDA 设备",
    )
    def test_shared_parameter_gradient_resonates_on_cuda(self) -> None:
        """
        同一 Parameter 两次使用在 CUDA 上反向把梯度累加进同一份
        """
        workstation = Workstation.cuda(0)
        shared = torch.nn.Parameter(
            torch.tensor([2.0, 4.0], dtype=torch.float64),
        )
        root = _SharedParameterPair(shared)
        _ownership._commit_host(
            workstation,
            root,
            workstation._move_module_tree,  # noqa: SLF001
        )
        left_w = root.left.w
        right_w = root.right.w
        assert isinstance(left_w, torch.nn.Parameter)
        assert isinstance(right_w, torch.nn.Parameter)
        assert shared.device.type == "cuda"
        assert left_w.data_ptr() == right_w.data_ptr()
        loss = (left_w * right_w).sum()
        loss.backward()
        assert shared.grad is not None
        assert torch.allclose(shared.grad, 2.0 * shared.detach())

    @pytest.mark.skipif(
        not torch.cuda.is_available(),
        reason="CUDA 跨根 Storage 拒绝证据需要当前环境存在可用 CUDA 设备",
    )
    def test_cross_root_shared_storage_rejected_on_cuda(self) -> None:
        """
        CUDA 上第二个根触及已 claim 的 Storage 时在移动前原子拒绝
        """
        owner = Workstation.cuda(0)
        foreign = Workstation.cpu()
        first = torch.nn.Parameter(
            torch.tensor([1.0, 2.0], dtype=torch.float64),
        )
        root_a = _SharedParameterElement(first)
        owner.host(root_a)
        second = torch.nn.Parameter(first.data)
        root_b = _SharedParameterElement(second)
        with pytest.raises(
            WorkstationError,
            match="workstation_host_already_hosted",
        ):
            foreign.host(root_b)


class TestOptimizerRemainsUserOwned:
    """
    工作站不持有优化器、损失、历史或可训练性登记表
    """

    def test_workstation_has_no_optimizer_or_history_slots(self) -> None:
        """
        工作站的 __slots__ 不含优化器、损失、历史或可训练性
        """
        slots = Workstation.__slots__
        assert "optimizer" not in slots
        assert "loss" not in slots
        assert "history" not in slots
        assert "trainability" not in slots

    def test_user_optimizer_runs_after_host(self) -> None:
        """
        用户在托管后自建的普通 PyTorch optimizer 可正常步进
        """
        workstation = Workstation.cpu()
        module = _HostedElement()
        workstation.host(module)
        optimizer = torch.optim.SGD(module.parameters(), lr=0.1)
        starting = module.scale.detach().clone()
        loss = (module.scale * module.scale).sum()
        loss.backward()
        optimizer.step()
        assert not torch.allclose(module.scale.detach(), starting)
