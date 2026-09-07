from __future__ import annotations

import ctypes


ASI_IMG_RAW8 = 0
ASI_IMG_RGB24 = 1
ASI_IMG_RAW16 = 2
ASI_IMG_Y8 = 3
ASI_IMG_END = -1

ASI_SUCCESS = 0
ASI_ERROR_INVALID_INDEX = 1
ASI_ERROR_INVALID_ID = 2
ASI_ERROR_INVALID_CONTROL_TYPE = 3
ASI_ERROR_CAMERA_CLOSED = 4
ASI_ERROR_CAMERA_REMOVED = 5
ASI_ERROR_INVALID_PATH = 6
ASI_ERROR_INVALID_FILEFORMAT = 7
ASI_ERROR_INVALID_SIZE = 8
ASI_ERROR_INVALID_IMGTYPE = 9
ASI_ERROR_OUTOF_BOUNDARY = 10
ASI_ERROR_TIMEOUT = 11
ASI_ERROR_INVALID_SEQUENCE = 12
ASI_ERROR_BUFFER_TOO_SMALL = 13
ASI_ERROR_VIDEO_MODE_ACTIVE = 14
ASI_ERROR_EXPOSURE_IN_PROGRESS = 15
ASI_ERROR_GENERAL_ERROR = 16

ASI_GAIN = 0
ASI_EXPOSURE = 1
ASI_GAMMA = 2
ASI_WB_R = 3
ASI_WB_B = 4
ASI_OFFSET = 5
ASI_BANDWIDTHOVERLOAD = 6
ASI_HIGH_SPEED_MODE = 14


class ASI_CAMERA_INFO(ctypes.Structure):
    """
    相机信息结构映射
    """

    _fields_ = [
        ("Name", ctypes.c_char * 64),
        ("CameraID", ctypes.c_int),
        ("MaxHeight", ctypes.c_long),
        ("MaxWidth", ctypes.c_long),
        ("IsColorCam", ctypes.c_int),
        ("BayerPattern", ctypes.c_int),
        ("SupportedBins", ctypes.c_int * 16),
        ("SupportedVideoFormat", ctypes.c_int * 8),
        ("PixelSize", ctypes.c_double),
        ("MechanicalShutter", ctypes.c_int),
        ("ST4Port", ctypes.c_int),
        ("IsCoolerCam", ctypes.c_int),
        ("IsUSB3Host", ctypes.c_int),
        ("IsUSB3Camera", ctypes.c_int),
        ("ElecPerADU", ctypes.c_float),
        ("BitDepth", ctypes.c_int),
        ("IsTriggerCam", ctypes.c_int),
        ("Unused", ctypes.c_char * 16),
    ]


class ASI_CONTROL_CAPS(ctypes.Structure):
    """
    控制能力结构映射
    """

    _fields_ = [
        ("Name", ctypes.c_char * 64),
        ("Description", ctypes.c_char * 128),
        ("MaxValue", ctypes.c_long),
        ("MinValue", ctypes.c_long),
        ("DefaultValue", ctypes.c_long),
        ("IsAutoSupported", ctypes.c_int),
        ("IsWritable", ctypes.c_int),
        ("ControlType", ctypes.c_int),
        ("Unused", ctypes.c_char * 32),
    ]


_ASI_STATUS = ctypes.c_int
_INT_POINTER = ctypes.POINTER(ctypes.c_int)
_LONG_POINTER = ctypes.POINTER(ctypes.c_long)
_UCHAR_POINTER = ctypes.POINTER(ctypes.c_ubyte)

_FUNCTION_SIGNATURES: dict[str, tuple[object, list[object]]] = {
    "ASIGetNumOfConnectedCameras": (ctypes.c_int, []),
    "ASIGetCameraProperty": (
        _ASI_STATUS,
        [ctypes.POINTER(ASI_CAMERA_INFO), ctypes.c_int],
    ),
    "ASIOpenCamera": (_ASI_STATUS, [ctypes.c_int]),
    "ASIInitCamera": (_ASI_STATUS, [ctypes.c_int]),
    "ASICloseCamera": (_ASI_STATUS, [ctypes.c_int]),
    "ASIGetNumOfControls": (_ASI_STATUS, [ctypes.c_int, _INT_POINTER]),
    "ASIGetControlCaps": (
        _ASI_STATUS,
        [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ASI_CONTROL_CAPS)],
    ),
    "ASIGetControlValue": (
        _ASI_STATUS,
        [ctypes.c_int, ctypes.c_int, _LONG_POINTER, _INT_POINTER],
    ),
    "ASISetControlValue": (
        _ASI_STATUS,
        [ctypes.c_int, ctypes.c_int, ctypes.c_long, ctypes.c_int],
    ),
    "ASISetROIFormat": (
        _ASI_STATUS,
        [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int],
    ),
    "ASIGetROIFormat": (
        _ASI_STATUS,
        [ctypes.c_int, _INT_POINTER, _INT_POINTER, _INT_POINTER, _INT_POINTER],
    ),
    "ASIStartVideoCapture": (_ASI_STATUS, [ctypes.c_int]),
    "ASIGetVideoData": (
        _ASI_STATUS,
        [ctypes.c_int, _UCHAR_POINTER, ctypes.c_long, ctypes.c_int],
    ),
    "ASIStopVideoCapture": (_ASI_STATUS, [ctypes.c_int]),
    "ASIGetDroppedFrames": (_ASI_STATUS, [ctypes.c_int, _INT_POINTER]),
    "ASIGetSDKVersion": (ctypes.c_char_p, []),
}


def configure_camera_dll_functions(dll: object) -> None:
    """
    配置相机函数签名
    """
    for function_name, (restype, argtypes) in _FUNCTION_SIGNATURES.items():
        function = getattr(dll, function_name)
        function.restype = restype
        function.argtypes = argtypes


__all__ = [
    "ASI_CAMERA_INFO",
    "ASI_CONTROL_CAPS",
    "ASI_BANDWIDTHOVERLOAD",
    "ASI_ERROR_CAMERA_CLOSED",
    "ASI_ERROR_EXPOSURE_IN_PROGRESS",
    "ASI_ERROR_GENERAL_ERROR",
    "ASI_ERROR_INVALID_CONTROL_TYPE",
    "ASI_ERROR_INVALID_ID",
    "ASI_ERROR_INVALID_IMGTYPE",
    "ASI_ERROR_INVALID_INDEX",
    "ASI_ERROR_INVALID_PATH",
    "ASI_ERROR_INVALID_SEQUENCE",
    "ASI_ERROR_INVALID_SIZE",
    "ASI_ERROR_OUTOF_BOUNDARY",
    "ASI_ERROR_TIMEOUT",
    "ASI_EXPOSURE",
    "ASI_GAIN",
    "ASI_GAMMA",
    "ASI_HIGH_SPEED_MODE",
    "ASI_IMG_END",
    "ASI_IMG_RAW16",
    "ASI_IMG_RAW8",
    "ASI_IMG_RGB24",
    "ASI_IMG_Y8",
    "ASI_OFFSET",
    "ASI_SUCCESS",
    "configure_camera_dll_functions",
]
