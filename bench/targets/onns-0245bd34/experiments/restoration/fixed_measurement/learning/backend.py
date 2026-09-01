from __future__ import annotations

from dataclasses import dataclass

from torch import nn

from experiments.restoration.fixed_measurement.learning.backends.nafnet import NafNetRestorationBackend
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.fixed_measurement.learning.schemas import BACKEND_MODELS, BackendFamily, BackendModel


_SUPPORTED_BACKEND_MODELS = tuple(name for name in BACKEND_MODELS if name != "none")


@dataclass(frozen=True, slots=True)
class BackendConfig:
    """
    鎻忚堪澶嶅師鍘熺敓鏁板瓧鍚庣閰嶇疆
    """

    family: BackendFamily = "restoration_native"
    model_name: BackendModel = "nafnet_s"
    residual_learning: bool = True

    def __post_init__(self) -> None:
        """
        鏍￠獙澶嶅師鍘熺敓鏁板瓧鍚庣閰嶇疆
        """
        if self.family != "restoration_native":
            raise invalid_restoration_contract("family must be restoration_native")
        if self.model_name not in _SUPPORTED_BACKEND_MODELS:
            allowed = ", ".join(_SUPPORTED_BACKEND_MODELS)
            raise invalid_restoration_contract(
                f"model_name must be one of: {allowed}"
            )
        if not isinstance(self.residual_learning, bool):
            raise invalid_restoration_contract("residual_learning must be a boolean")


def build_restoration_backend(
    config: BackendConfig,
    *,
    defocus_operator: object | None = None,
    reference_arm: object | None = None,
) -> nn.Module:
    """
    浠庡凡鏍￠獙閰嶇疆鏋勫缓澶嶅師鍘熺敓鏁板瓧鍚庣

    ``defocus_operator`` and ``reference_arm`` are the canonical physics kwargs
    shared across backend families. The ``nafnet_*`` models ignore them; A/C
    backend dispatch (added by their own plans) require and consume them.
    """
    if config.family != "restoration_native":
        raise invalid_restoration_contract("family must be restoration_native")
    # 褰撳墠姝ｅ紡鍚庣涓嶆秷璐瑰彲閫夌墿鐞嗗崗浣滆€呫€?    del defocus_operator, reference_arm
    return NafNetRestorationBackend(
        model_name=config.model_name,
        residual_learning=config.residual_learning,
    )
