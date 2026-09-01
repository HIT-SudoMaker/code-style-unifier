from pathlib import Path

from .api import ACSMotionStageDeviceAPI
from .motion import ACSMotionStage
from .motion import DEFAULT_CONTROLLER_IP
from .motion import DEFAULT_STAGE_AXIS
from .motion import DEFAULT_STAGE_PORT
from .motion import DEFAULT_STAGE_TIMEOUT_MS
from .motion import DEFAULT_STAGE_VELOCITY_MM_PER_SECOND
from .motion import STAGE_MAX_POSITION_MM
from .motion import STAGE_MIN_POSITION_MM

PACKAGE_ROOT = Path(__file__).resolve().parent
VENDOR_DLL_PATH = PACKAGE_ROOT / "vendor" / "acs_motion_stage.dll"

__all__ = [
    "ACSMotionStage",
    "ACSMotionStageDeviceAPI",
    "DEFAULT_CONTROLLER_IP",
    "DEFAULT_STAGE_AXIS",
    "DEFAULT_STAGE_PORT",
    "DEFAULT_STAGE_TIMEOUT_MS",
    "DEFAULT_STAGE_VELOCITY_MM_PER_SECOND",
    "PACKAGE_ROOT",
    "STAGE_MAX_POSITION_MM",
    "STAGE_MIN_POSITION_MM",
    "VENDOR_DLL_PATH",
]
