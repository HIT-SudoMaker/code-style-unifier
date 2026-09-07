from __future__ import annotations


class RestorationContractError(ValueError):
    """
    表示复原领域输入或状态违反显式契约
    """


class RestorationArtifactNotFoundError(FileNotFoundError):
    """
    表示复原运行缺少必需产物
    """


class RestorationRuntimeError(RuntimeError):
    """
    表示复原运行环境无法满足执行要求
    """


class RestorationTypeError(TypeError):
    """
    表示复原接口接收到错误类型
    """


def invalid_restoration_contract(message: str) -> RestorationContractError:
    """
    构造复原领域契约异常
    """
    return RestorationContractError(message)


def missing_restoration_artifact(
    message: str,
) -> RestorationArtifactNotFoundError:
    """
    构造复原产物缺失异常
    """
    return RestorationArtifactNotFoundError(message)


def unavailable_restoration_runtime(message: str) -> RestorationRuntimeError:
    """
    构造复原运行环境异常
    """
    return RestorationRuntimeError(message)


def invalid_restoration_type(message: str) -> RestorationTypeError:
    """
    构造复原接口类型异常
    """
    return RestorationTypeError(message)
