from __future__ import annotations

import ctypes
from ctypes import wintypes


_SLM_STATUS = ctypes.c_int
_INT_POINTER = ctypes.POINTER(ctypes.c_int)
_DOUBLE_POINTER = ctypes.POINTER(ctypes.c_double)


_FUNCTION_SIGNATURES: dict[str, list[object]] = {
    "SLM_Disp_Info_NumberName": [_INT_POINTER, ctypes.c_char_p],
    "SLM_Disp_Info": [ctypes.c_int, _INT_POINTER, _INT_POINTER],
    "SLM_Disp_CoordInfo": [ctypes.c_int, _INT_POINTER, _INT_POINTER],
    "SLM_Disp_Open": [ctypes.c_int],
    "SLM_Disp_Close": [ctypes.c_int],
    "SLM_Disp_GrayScale": [ctypes.c_int, ctypes.c_int, ctypes.c_int],
    "SLM_Disp_BMP": [ctypes.c_int, ctypes.c_int, wintypes.HBITMAP],
    "SLM_Disp_Data": [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_void_p,
    ],
    "SLM_Disp_Data_Double": [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        _DOUBLE_POINTER,
    ],
    "SLM_Disp_ReadImage": [ctypes.c_int, ctypes.c_wchar_p],
    "SLM_Disp_ReadImage_A": [ctypes.c_int, ctypes.c_char_p],
    "SLM_Disp_ReadCSV": [ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p],
    "SLM_Disp_ReadCSV_A": [ctypes.c_int, ctypes.c_int, ctypes.c_char_p],
    "SLM_Set_Offset": [ctypes.c_int, ctypes.c_int, ctypes.c_int],
    "SLM_Get_Offset": [ctypes.c_int, _INT_POINTER, _INT_POINTER],
    "SLM_Set_TriggerInit": [ctypes.c_int],
    "SLM_Set_Trigger": [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
    ],
    "SLM_Get_Trigger": [
        ctypes.c_int,
        _INT_POINTER,
        _INT_POINTER,
        _INT_POINTER,
        _INT_POINTER,
        _INT_POINTER,
    ],
    "SLM_Set_Gamma": [ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p],
    "SLM_Set_Gamma_A": [ctypes.c_int, ctypes.c_int, ctypes.c_char_p],
    "SLM_Set_GammaEnabled": [ctypes.c_int, ctypes.c_int],
    "SLM_Set_SoftGammaEnabled": [ctypes.c_int, ctypes.c_int],
    "SLM_Set_SoftGammaValue": [ctypes.c_int, ctypes.c_double],
    "SLM_Get_SoftGammaEnabled": [ctypes.c_int, _INT_POINTER],
    "SLM_Get_SoftGammaValue": [ctypes.c_int, _DOUBLE_POINTER],
    "SLM_Set_UserDispSizeEnabled": [ctypes.c_int, ctypes.c_int],
    "SLM_Set_UserDispSize": [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
    ],
    "SLM_Get_UserDispSizeEnabled": [ctypes.c_int, _INT_POINTER],
    "SLM_Get_UserDispSize": [
        ctypes.c_int,
        _INT_POINTER,
        _INT_POINTER,
        _INT_POINTER,
        _INT_POINTER,
    ],
    "SLM_Set_SplicingScreenEnabled": [
        _INT_POINTER,
        ctypes.c_int,
        ctypes.c_int,
    ],
    "SLM_Get_SplicingScreenEnabled": [ctypes.c_int, _INT_POINTER],
    "SLM_Disp_Splice": [],
}


def configure_slm_dll_functions(dll: object) -> None:
    """
    配置 HDSLM DLL 函数签名
    """
    for function_name, argtypes in _FUNCTION_SIGNATURES.items():
        function = getattr(dll, function_name)
        function.restype = _SLM_STATUS
        function.argtypes = argtypes
