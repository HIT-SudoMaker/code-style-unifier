from __future__ import annotations

__all__ = [
    "AssemblyError",
    "OpticalError",
    "OpticalRuntimeError",
    "OpticalTypeError",
    "OpticalValueError",
    "WorkstationError",
]



class OpticalError(Exception):
    """
    光学域失败的基类，携带稳定标识与面向使用者的说明

    Args:
        identity: 可由调用者稳定匹配的失败标识
        explanation: 面向使用者的完整失败说明

    """

    def __init__(self, identity: str, explanation: str) -> None:
        """
        以稳定标识与完整中文说明构造一次光学域失败

        """
        super().__init__(identity, explanation)
        self.identity = identity
        self.explanation = explanation

    def __str__(self) -> str:
        """
        返回标识与说明以全角冒号连接而成的消息

        """
        return f"{self.identity}：{self.explanation}"


class OpticalTypeError(OpticalError, TypeError):
    """
    物理量类型不符合契约的光学域失败

    """


class OpticalValueError(OpticalError, ValueError):
    """
    物理量取值不符合契约的光学域失败

    """


class OpticalRuntimeError(OpticalError, RuntimeError):
    """
    状态恢复等运行期约定不成立的光学域失败

    """


class AssemblyError(OpticalError):
    """
    无效装配拓扑、连接、兼容性或命名输出的光学域失败

    """


class WorkstationError(OpticalError):
    """
    不可用平台、设备、精度或失败内存检查的光学域失败

    """
