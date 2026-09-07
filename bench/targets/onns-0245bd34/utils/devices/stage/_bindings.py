from __future__ import annotations

import ctypes


ACSC_INVALID = ctypes.c_void_p(-1).value
ACSC_NONE = -1

ACSC_SOCKET_DGRAM_PORT = 700
ACSC_SOCKET_STREAM_PORT = 701

ACSC_AXIS_X = 0
ACSC_AXIS_Y = 1
ACSC_AXIS_Z = 2
ACSC_AXIS_T = 3

ACSC_AMF_WAIT = 0x00000001
ACSC_AMF_RELATIVE = 0x00000002
ACSC_AMF_VELOCITY = 0x00000004

ACSC_MST_MOVE = 0x00000020


_HANDLE = ctypes.c_void_p
_WAIT_POINTER = ctypes.c_void_p
_INT_POINTER = ctypes.POINTER(ctypes.c_int)
_DOUBLE_POINTER = ctypes.POINTER(ctypes.c_double)

_FUNCTION_SIGNATURES: dict[str, tuple[object, list[object]]] = {
    "acsc_OpenCommEthernet": (_HANDLE, [ctypes.c_char_p, ctypes.c_int]),
    "acsc_OpenCommEthernetTCP": (_HANDLE, [ctypes.c_char_p, ctypes.c_int]),
    "acsc_CloseComm": (ctypes.c_int, [_HANDLE]),
    "acsc_GetLibraryVersion": (ctypes.c_uint, []),
    "acsc_GetFirmwareVersion": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_char_p, ctypes.c_int, _INT_POINTER, _WAIT_POINTER],
    ),
    "acsc_Send": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_char_p, ctypes.c_int, _WAIT_POINTER],
    ),
    "acsc_Receive": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_char_p, ctypes.c_int, _INT_POINTER, _WAIT_POINTER],
    ),
    "acsc_Enable": (ctypes.c_int, [_HANDLE, ctypes.c_int, _WAIT_POINTER]),
    "acsc_Disable": (ctypes.c_int, [_HANDLE, ctypes.c_int, _WAIT_POINTER]),
    "acsc_DisableAll": (ctypes.c_int, [_HANDLE, _WAIT_POINTER]),
    "acsc_SetAcceleration": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, ctypes.c_double, _WAIT_POINTER],
    ),
    "acsc_GetAcceleration": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, _DOUBLE_POINTER, _WAIT_POINTER],
    ),
    "acsc_SetDeceleration": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, ctypes.c_double, _WAIT_POINTER],
    ),
    "acsc_GetDeceleration": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, _DOUBLE_POINTER, _WAIT_POINTER],
    ),
    "acsc_SetVelocity": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, ctypes.c_double, _WAIT_POINTER],
    ),
    "acsc_GetVelocity": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, _DOUBLE_POINTER, _WAIT_POINTER],
    ),
    "acsc_ToPoint": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, ctypes.c_int, ctypes.c_double, _WAIT_POINTER],
    ),
    "acsc_Halt": (ctypes.c_int, [_HANDLE, ctypes.c_int, _WAIT_POINTER]),
    "acsc_Kill": (ctypes.c_int, [_HANDLE, ctypes.c_int, _WAIT_POINTER]),
    "acsc_KillAll": (ctypes.c_int, [_HANDLE, _WAIT_POINTER]),
    "acsc_GetFPosition": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, _DOUBLE_POINTER, _WAIT_POINTER],
    ),
    "acsc_GetRPosition": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, _DOUBLE_POINTER, _WAIT_POINTER],
    ),
    "acsc_GetTargetPosition": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, _DOUBLE_POINTER, _WAIT_POINTER],
    ),
    "acsc_GetMotorState": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, _INT_POINTER, _WAIT_POINTER],
    ),
    "acsc_WaitMotionEnd": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, ctypes.c_int],
    ),
    "acsc_GetLastError": (ctypes.c_int, []),
    "acsc_GetErrorString": (
        ctypes.c_int,
        [_HANDLE, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, _INT_POINTER],
    ),
}


def configure_stage_dll_functions(dll: object) -> None:
    """
    配置运动台函数签名
    """
    for function_name, (restype, argtypes) in _FUNCTION_SIGNATURES.items():
        function = getattr(dll, function_name)
        function.restype = restype
        function.argtypes = argtypes


__all__ = [
    "ACSC_AMF_RELATIVE",
    "ACSC_AMF_VELOCITY",
    "ACSC_AMF_WAIT",
    "ACSC_AXIS_T",
    "ACSC_AXIS_X",
    "ACSC_AXIS_Y",
    "ACSC_AXIS_Z",
    "ACSC_INVALID",
    "ACSC_MST_MOVE",
    "ACSC_NONE",
    "ACSC_SOCKET_DGRAM_PORT",
    "ACSC_SOCKET_STREAM_PORT",
    "configure_stage_dll_functions",
]
