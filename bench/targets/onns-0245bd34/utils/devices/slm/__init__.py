from pathlib import Path
from .api import UPOLabsSLMDeviceAPI
from .converter import (
    intensity_to_slm_frame,
    phase_to_slm_frame,
)
from .frame import (
    SLMFrame,
    slm_frame_to_ctypes_buffer,
)

PACKAGE_ROOT = Path(__file__).resolve().parent
VENDOR_DLL_PATH = PACKAGE_ROOT / "vendor" / "hd_slm_function.dll"

__all__ = [
    "SLMFrame",
    "UPOLabsSLMDeviceAPI",
    "PACKAGE_ROOT",
    "VENDOR_DLL_PATH",
    "intensity_to_slm_frame",
    "phase_to_slm_frame",
    "slm_frame_to_ctypes_buffer",
]
