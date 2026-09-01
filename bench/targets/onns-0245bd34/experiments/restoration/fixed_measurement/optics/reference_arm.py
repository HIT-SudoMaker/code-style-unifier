from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class ReferenceArmParams:
    """
    描述从已加载前端提取的参考臂物理参数
    """

    split_ratio_reference: float
    amplitude_gain_reference: float
    phase_offset_reference: float

    def amplitude(self) -> float:
        """
        根据分束比与增益返回参考臂振幅
        """
        return math.sqrt(self.split_ratio_reference) * self.amplitude_gain_reference

    def phase_offset(self) -> float:
        """
        返回参考臂相位偏移
        """
        return self.phase_offset_reference


def reference_arm_from_frontend(frontend: object) -> ReferenceArmParams:
    """
    从已加载光学前端推导实时参考臂参数
    from the LIVE loaded parameter, not the frozen bench configuration.
    """
    bench_config = frontend.bench_config
    return ReferenceArmParams(
        split_ratio_reference=float(bench_config.split_ratio_reference),
        amplitude_gain_reference=float(bench_config.amplitude_gain_reference),
        phase_offset_reference=float(frontend.phase_offset_reference.detach()),
    )


def inject_live_reference_arm(model: object) -> None:
    """
    将加载后的实时参考臂注入兼容的混合后端

    Runs after the frozen frontend checkpoint is loaded, so the backend receives
    the trained ``phase_offset_reference`` rather than a provisional build-time value.
    Non-hybrid models, or backends without ``set_reference_arm`` (e.g. NAFNet), are
    a graceful no-op (duck-typed skip).
    """
    frontend = getattr(model, "frontend", None)
    backend = getattr(model, "backend", None)
    if frontend is None or backend is None:
        return
    setter = getattr(backend, "set_reference_arm", None)
    if not callable(setter):
        return
    setter(reference_arm_from_frontend(frontend))
