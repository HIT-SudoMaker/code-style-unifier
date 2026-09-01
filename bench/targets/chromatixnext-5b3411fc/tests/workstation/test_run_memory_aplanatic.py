from __future__ import annotations

from typing import Literal
import weakref

import pytest
import torch
from torch.utils._python_dispatch import TorchDispatchMode

from chromatix_next.errors import WorkstationError
from chromatix_next.optics import (
    Assembly,
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PolarizationRepresentation,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.propagation import AplanaticFocus
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation

from ._factory import cpu_workstation


class _VisibleStoragePeak(TorchDispatchMode):
    # 独立观察公开元件计算中仍存活的 PyTorch tensor storage

    def __init__(self) -> None:
        """
        建立不依赖生产 tracer 的弱引用 storage 账本
        """

        super().__init__()
        self._wrappers: dict[
            int,
            weakref.ReferenceType[torch.Tensor],
        ] = {}
        self._storage_by_wrapper: dict[int, int] = {}
        self._references_by_storage: dict[int, int] = {}
        self._bytes_by_storage: dict[int, int] = {}
        self._live_bytes = 0
        self.peak_bytes = 0

    def _observe(self, value: object) -> None:
        if isinstance(value, torch.Tensor):
            self._observe_tensor(value)
            return
        if isinstance(value, (tuple, list)):
            for item in value:
                self._observe(item)
            return
        if isinstance(value, dict):
            for item in value.values():
                self._observe(item)

    def _keep_saved_tensor(self, tensor: torch.Tensor) -> torch.Tensor:
        self._observe_tensor(tensor)
        return tensor

    @staticmethod
    def _restore_saved_tensor(tensor: torch.Tensor) -> torch.Tensor:
        return tensor

    def __torch_dispatch__(
        self,
        function: object,
        types: object,
        arguments: tuple[object, ...] = (),
        keywords: dict[str, object] | None = None,
    ) -> object:
        """
        观察公开 PyTorch 算子的输入与输出 storage
        """

        del types
        assert callable(function)
        resolved_keywords = keywords or {}
        self._observe(arguments)
        self._observe(resolved_keywords)
        result = function(*arguments, **resolved_keywords)
        self._observe(result)
        return result

    def _observe_tensor(self, tensor: torch.Tensor) -> None:
        tensor_identity = id(tensor)
        existing = self._wrappers.get(tensor_identity)
        if existing is not None and existing() is tensor:
            return
        storage_identity = int(tensor.untyped_storage()._cdata)

        def release(
            expired: weakref.ReferenceType[torch.Tensor],
        ) -> None:
            """
            在最后一个 tensor wrapper 消失时释放对应 storage
            """

            current = self._wrappers.get(tensor_identity)
            if current is not expired:
                return
            self._wrappers.pop(tensor_identity)
            released_storage = self._storage_by_wrapper.pop(
                tensor_identity,
            )
            reference_count = (
                self._references_by_storage[released_storage] - 1
            )
            if reference_count:
                self._references_by_storage[released_storage] = (
                    reference_count
                )
                return
            self._references_by_storage.pop(released_storage)
            self._live_bytes -= self._bytes_by_storage.pop(
                released_storage,
            )

        reference = weakref.ref(tensor, release)
        self._wrappers[tensor_identity] = reference
        self._storage_by_wrapper[tensor_identity] = storage_identity
        reference_count = self._references_by_storage.get(
            storage_identity,
            0,
        )
        if reference_count == 0:
            storage_bytes = tensor.untyped_storage().nbytes()
            conservative_bytes = (
                (storage_bytes + 511) // 512
            ) * 512
            self._bytes_by_storage[storage_identity] = (
                conservative_bytes
            )
            self._live_bytes += conservative_bytes
            self.peak_bytes = max(
                self.peak_bytes,
                self._live_bytes,
            )
        self._references_by_storage[storage_identity] = (
            reference_count + 1
        )


class _MetaPolarizationMismatch(torch.nn.Module):
    @property
    def role(self) -> Literal["element"]:
        """
        声明恶意反事实仍是合法元件角色
        """

        return "element"

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        返回同形同类但在 meta 阶段伪造不同偏振表示的恶意物理值
        """

        full_envelope = torch.cat(
            (
                field.envelope,
                torch.zeros_like(field.envelope[..., :1, :, :]),
            ),
            dim=-3,
        )
        result = OpticalField(
            envelope=full_envelope,
            grid=field.grid,
            spectrum=field.spectrum,
            polarization_representation=PolarizationRepresentation.FULL,
            medium=field.medium,
            normalization=field.normalization,
            path_reference=field.path_reference,
        )
        if field.envelope.device.type == "meta":
            object.__setattr__(
                result,
                "polarization_representation",
                PolarizationRepresentation.TRANSVERSE,
            )
        return result


def _polarization_mismatch_inputs(
    device: torch.device,
) -> tuple[OpticalField]:
    grid = SpatialGrid.centered(
        sample_counts=(3, 3),
        sample_spacing=(
            torch.tensor(
                1.0e-6,
                dtype=torch.float64,
                device=device,
            ),
            torch.tensor(
                1.0e-6,
                dtype=torch.float64,
                device=device,
            ),
        ),
    )
    return (
        OpticalField(
            envelope=torch.ones(
                (1, 2, 3, 3),
                dtype=torch.complex128,
                device=device,
            ),
            grid=grid,
            spectrum=Spectrum.monochromatic(0.55e-6),
            polarization_representation=(
                PolarizationRepresentation.TRANSVERSE
            ),
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(
                lengths=(
                    torch.tensor(
                        0.0,
                        dtype=torch.float64,
                        device=device,
                    ),
                ),
            ),
        ),
    )


def _calculate_polarization_mismatch(
    root: torch.nn.Module,
    field: OpticalField,
) -> dict[str, OpticalField]:
    result = root(field)
    assert isinstance(result, OpticalField)
    return {"field": result}


def _aplanatic_assembly() -> tuple[
    Assembly,
    PlaneWave,
    AplanaticFocus,
]:
    pupil_grid = SpatialGrid.centered(
        sample_counts=(11, 13),
        sample_spacing=(0.5e-6, 0.45e-6),
    )
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(0.55e-6),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=torch.nn.Parameter(
            torch.tensor(1.0, dtype=torch.float64),
        ),
    )
    focus = AplanaticFocus(
        focal_length=8.0e-6,
        maximum_convergence_angle=0.3,
        axial_distance_from_focus=torch.nn.Parameter(
            torch.tensor(0.1e-6, dtype=torch.float64),
        ),
        destination_grid=SpatialGrid.centered(
            sample_counts=(7, 9),
            sample_spacing=(0.2e-6, 0.18e-6),
        ),
    )
    assembly = Assembly()
    assembly.include(source, name="source", grid=pupil_grid)
    assembly.include(focus, name="focus")
    assembly.connect(source, focus)
    assembly.expose(focus, name="focused_field")
    assembly.freeze()
    return assembly, source, focus


def _direct_visible_storage_peak(
    *,
    is_gradient_enabled: bool,
) -> int:
    assembly, source, focus = _aplanatic_assembly()
    workstation = Workstation.cpu()
    workstation.host(assembly)
    trace = _VisibleStoragePeak()
    for tensor in (
        *assembly.parameters(),
        *assembly.buffers(),
    ):
        trace._observe(tensor)
    gradient_context = (
        torch.enable_grad()
        if is_gradient_enabled
        else torch.no_grad()
    )
    with (
        gradient_context,
        trace,
        torch.autograd.graph.saved_tensors_hooks(
            trace._keep_saved_tensor,
            trace._restore_saved_tensor,
        ),
    ):
        focused = focus(source(assembly._anchor_grid("source")))  # noqa: SLF001
        trace._observe(focused.envelope)
    return trace.peak_bytes


def _recorded_aplanatic_peak(
    *,
    is_gradient_enabled: bool,
) -> int:
    assembly, _source, _focus = _aplanatic_assembly()
    workstation = Workstation.cpu()
    workstation.host(assembly)
    gradient_context = (
        torch.enable_grad()
        if is_gradient_enabled
        else torch.no_grad()
    )
    with gradient_context:
        _outputs, record = workstation.run(assembly)
    return record.peak_memory_bytes


def test_aplanatic_run_covers_full_field_and_padded_storage() -> None:
    """
    公共运行以同一精度返回完整矢量场，内存峰覆盖大于最终裁剪结果的 CZT 暂存
    """

    for is_gradient_enabled in (False, True):
        assembly, source, focus = _aplanatic_assembly()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        gradient_context = (
            torch.enable_grad()
            if is_gradient_enabled
            else torch.no_grad()
        )

        with gradient_context:
            outputs, record = workstation.run(assembly)

        focused = outputs["focused_field"]
        assert isinstance(focused, OpticalField)
        assert (
            focused.polarization_representation
            is PolarizationRepresentation.FULL
        )
        assert focused.envelope.shape == (1, 3, 7, 9)
        assert focused.envelope.dtype is torch.complex128
        assert focused.envelope.device.type == "cpu"
        assert focused.envelope.requires_grad is is_gradient_enabled
        final_output_bytes = (
            focused.envelope.numel() * focused.envelope.element_size()
        )
        assert record.peak_memory_bytes > final_output_bytes
        if is_gradient_enabled:
            focused.envelope.abs().square().sum().backward()
            assert source.relative_amplitude.grad is not None
            assert focus.axial_distance_from_focus.grad is not None


def test_aplanatic_memory_check_rejects_before_real_field_allocation() -> None:
    """
    不足边界在真实光源缓存形成前拒绝，证明聚焦运行先完成保守 meta 预检
    """

    assembly, source, _focus = _aplanatic_assembly()
    workstation = cpu_workstation(1)
    workstation.host(assembly)

    with pytest.raises(
        WorkstationError,
        match="workstation_memory_check_infeasible",
    ):
        workstation.run(assembly)

    assert source.get_buffer("_unit_envelope_cache") is None


def test_aplanatic_peak_covers_independent_visible_storage() -> None:
    """
    meta 峰覆盖独立观察到的完整 CZT padding tensor 生命周期
    """

    visible_peak = _direct_visible_storage_peak(
        is_gradient_enabled=False,
    )
    recorded_peak = _recorded_aplanatic_peak(
        is_gradient_enabled=False,
    )

    assert recorded_peak >= visible_peak


def test_aplanatic_gradient_peak_includes_saved_tensor_storage() -> None:
    """
    启用梯度的峰值单独覆盖 autograd 保存量并严格高于无梯度路径
    """

    no_gradient_peak = _direct_visible_storage_peak(
        is_gradient_enabled=False,
    )
    gradient_peak = _direct_visible_storage_peak(
        is_gradient_enabled=True,
    )
    recorded_gradient_peak = _recorded_aplanatic_peak(
        is_gradient_enabled=True,
    )
    recorded_no_gradient_peak = _recorded_aplanatic_peak(
        is_gradient_enabled=False,
    )

    assert gradient_peak > no_gradient_peak
    assert recorded_gradient_peak > recorded_no_gradient_peak
    assert recorded_gradient_peak >= gradient_peak


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="Windows CUDA evidence requires an available CUDA device",
)
def test_aplanatic_workstation_run_matches_cpu_on_available_cuda() -> None:
    """
    可用 Windows CUDA 与 CPU 通过同一公共运行接口给出同一完整矢量结果
    """

    cpu_assembly, _, _ = _aplanatic_assembly()
    cuda_assembly, _, _ = _aplanatic_assembly()
    cpu_workstation = Workstation.cpu()
    cuda_workstation = Workstation.cuda(0)
    cpu_workstation.host(cpu_assembly)
    cuda_workstation.host(cuda_assembly)

    cpu_outputs, _ = cpu_workstation.run(cpu_assembly)
    cuda_outputs, _ = cuda_workstation.run(cuda_assembly)
    cpu_field = cpu_outputs["focused_field"]
    cuda_field = cuda_outputs["focused_field"]
    assert isinstance(cpu_field, OpticalField)
    assert isinstance(cuda_field, OpticalField)

    assert torch.allclose(
        cuda_field.envelope.cpu(),
        cpu_field.envelope,
        rtol=2.0e-5,
        atol=2.0e-5,
    )


def test_run_rejects_meta_and_real_polarization_mismatch() -> None:
    """
    输出形状与 dtype 相同仍不能掩盖 meta 和真实偏振表示分歧
    """

    component = _MetaPolarizationMismatch()
    workstation = Workstation.cpu()
    workstation.host(component)

    with pytest.raises(
        WorkstationError,
        match="workstation_replay_output_schema_mismatch",
    ):
        workstation.run(
            _calculate_polarization_mismatch,
            root=component,
            inputs=_polarization_mismatch_inputs,
        )
