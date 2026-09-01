from __future__ import annotations

from typing import Protocol

from .._role_contract import _SourceCalculation, _SourceRole


class Source(Protocol):
    """
    公共结构化源角色契约

    组件结构上满足此 Protocol；``test_roles`` 据此静态验证组件符合角色契约，
    运行时语义权威在私有 ``_role_contract``。

    """

    @property
    def role(self) -> _SourceRole:
        """
        只读源角色

        Returns:
            返回 Source 组件的稳定角色标识 "source"

        """

        ...

    @property
    def forward(self) -> _SourceCalculation:
        """
        源计算

        Returns:
            返回给定 SpatialGrid 上生成的 OpticalField 或 RayBundle

        """

        ...
