from __future__ import annotations

from typing import Protocol

from .._role_contract import _ElementCalculation, _ElementRole


class Element(Protocol):
    """
    公共结构化元件角色契约

    组件结构上满足此 Protocol；``test_roles`` 据此静态验证组件符合角色契约，
    运行时语义权威在私有 ``_role_contract``。

    """

    @property
    def role(self) -> _ElementRole:
        """
        只读元件角色

        Returns:
            返回 Element 组件的稳定角色标识 "element"

        """

        ...

    @property
    def forward(self) -> _ElementCalculation:
        """
        元件计算

        Returns:
            返回作用后的 OpticalField、RayBundle，或按端口顺序排列的同类物理值元组

        """

        ...
