from __future__ import annotations

from typing import Protocol

from .._role_contract import _DetectionCalculation, _DetectionRole


class Detection(Protocol):
    """
    公共结构化探测角色契约

    组件结构上满足此 Protocol；``test_roles`` 据此静态验证组件符合角色契约，
    运行时语义权威在私有 ``_role_contract``。

    """

    @property
    def role(self) -> _DetectionRole:
        """
        只读探测角色

        Returns:
            返回 Detection 组件的稳定角色标识 "detection"

        """

        ...

    @property
    def forward(self) -> _DetectionCalculation:
        """
        探测计算

        Returns:
            返回检测组件执行后的强度值

        """

        ...
