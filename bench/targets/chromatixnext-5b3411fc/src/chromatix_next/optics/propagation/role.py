from __future__ import annotations

from typing import Protocol

from .._role_contract import _PropagationCalculation, _PropagationRole


class Propagation(Protocol):
    """
    公共结构化传播角色契约

    组件结构上满足此 Protocol；``test_roles`` 据此静态验证组件符合角色契约，
    运行时语义权威在私有 ``_role_contract``。

    """

    @property
    def role(self) -> _PropagationRole:
        """
        只读传播角色

        Returns:
            返回 Propagation 组件的稳定角色标识 "propagation"

        """

        ...

    @property
    def forward(self) -> _PropagationCalculation:
        """
        传播计算

        Returns:
            返回传播后的 OpticalField 或 RayBundle，并保持模型的表示与采样语义

        """

        ...
