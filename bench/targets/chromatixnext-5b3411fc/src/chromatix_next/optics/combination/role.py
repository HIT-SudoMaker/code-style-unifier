from __future__ import annotations

from typing import Protocol

from .._role_contract import _CombinationCalculation, _CombinationRole


class Combination(Protocol):
    """
    公共结构化组合角色契约

    组件结构上满足此 Protocol；``test_roles`` 据此静态验证组件符合角色契约，
    运行时语义权威在私有 ``_role_contract``。

    """

    @property
    def role(self) -> _CombinationRole:
        """
        只读组合角色

        Returns:
            返回 Combination 组件的稳定角色标识 "combination"

        """

        ...

    @property
    def forward(self) -> _CombinationCalculation:
        """
        组合计算

        Returns:
            返回两个 OpticalField 的相干组合 OpticalField，或两个 Intensity 的强度
            组合 Intensity

        """

        ...
