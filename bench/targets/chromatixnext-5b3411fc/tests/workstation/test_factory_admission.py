from __future__ import annotations

from collections.abc import Callable
import inspect
from unittest.mock import patch

import pytest
import torch

from chromatix_next.errors import WorkstationError
from chromatix_next.workstation import Workstation


class TestWorkstationFactories:
    """
    工作站显式工厂与直接构造封闭面的行为保证
    """

    def test_direct_construction_forms_are_rejected(self) -> None:
        """
        任何直接构造形式都以稳定领域错误拒绝
        """
        constructors: tuple[Callable[[], Workstation], ...] = (
            lambda: Workstation(),
            lambda: Workstation(
                torch.device("cpu"),  # type: ignore[arg-type]
            ),
            lambda: Workstation(  # type: ignore[arg-type]
                device=torch.device("cpu"),
            ),
        )
        for constructor in constructors:
            with pytest.raises(WorkstationError) as exception:
                constructor()
            assert "workstation_factory_required" in str(exception.value)

    def test_direct_signature_exposes_no_construction_values(self) -> None:
        """
        直接构造签名不提供设备、精度或边界值
        """
        parameters = tuple(inspect.signature(Workstation).parameters.values())

        assert [parameter.kind for parameter in parameters] == [
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ]


    def test_workstation_subclass_is_rejected(self) -> None:
        """
        子类不能绕过精确 Workstation 工厂边界
        """
        with pytest.raises(
            WorkstationError,
            match="workstation_subclass_unsupported",
        ):

            class UnsupportedWorkstation(Workstation):
                """
                验证工作站继承边界的测试子类
                """

                pass

    def test_factories_take_no_precision_argument(self) -> None:
        """
        固定双精度核下两个正式工厂都不再接受精度参数
        """
        cpu_signature = inspect.signature(Workstation.cpu)
        assert "precision" not in cpu_signature.parameters
        cuda_signature = inspect.signature(Workstation.cuda)
        assert "precision" not in cuda_signature.parameters

    def test_cpu_factory_uses_the_cpu_device(self) -> None:
        """
        CPU 工厂固定选择无索引 CPU 设备
        """
        workstation = Workstation.cpu()

        assert type(workstation) is Workstation
        assert workstation.device == torch.device("cpu")

    def test_cuda_factory_rejects_non_integer_or_negative_indices(self) -> None:
        """
        CUDA 工厂拒绝布尔、非整数与负索引
        """
        for device_index in (True, 0.0, "0", -1):
            with (
                patch("torch.cuda.is_available", return_value=True),
                patch("torch.cuda.device_count", return_value=1),
                pytest.raises(WorkstationError) as exception,
            ):
                Workstation.cuda(
                    device_index,  # type: ignore[arg-type]
                )
            assert "workstation_cuda_index_unavailable" in str(exception.value)

    def test_cuda_factory_rejects_an_unavailable_runtime_without_fallback(
        self,
    ) -> None:
        """
        CUDA 不可用时在探测边界前拒绝且不回退 CPU
        """
        with (
            patch("torch.cuda.is_available", return_value=False),
            patch("torch.cuda.device_count") as device_count,
            patch(
                "chromatix_next._execution_memory._default_memory_boundary_bytes"
            ) as boundary,
            pytest.raises(WorkstationError) as exception,
        ):
            Workstation.cuda(0)

        assert "workstation_cuda_unavailable" in str(exception.value)
        device_count.assert_not_called()
        boundary.assert_not_called()

    def test_boundary_probe_is_consumed_only_through_a_factory(self) -> None:
        """
        窄测试边界经私有探针进入正式 CPU 工厂
        """
        with patch(
            "chromatix_next._execution_memory._default_memory_boundary_bytes",
            return_value=17,
        ):
            workstation = Workstation.cpu()

        assert workstation.memory_boundary_bytes == 17

    def test_representation_is_not_an_executable_constructor_form(self) -> None:
        """
        工作站表示不伪装成可复制执行的直接构造
        """
        workstation = Workstation.cpu()

        assert repr(workstation) == "<Workstation device=cpu>"
