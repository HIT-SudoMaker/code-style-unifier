from __future__ import annotations

from collections.abc import Sequence
import ctypes
from ctypes import wintypes
from pathlib import Path

from ._bindings import configure_slm_dll_functions


_DISPLAY_NAME_BUFFER_SIZE = 4096


class UPOLabsSLMDeviceAPI:
    """
    HDSLM 空间光调制器 DLL 绑定
    """

    STATUS_OK = 1
    STATUS_GENERAL_ERROR = -1
    STATUS_MONITOR_NOT_OPEN = -2
    STATUS_OPEN_WINDOW_ERROR = -3
    STATUS_DATA_FORMAT_ERROR = -4
    STATUS_UNSUPPORTED_IMAGE = -5
    STATUS_FILE_READ_ERROR = -6
    STATUS_GAMMA_FILE_READ_ERROR = -7
    STATUS_UNSUPPORTED_GAMMA_FILE = -8
    STATUS_IMAGE_SPLICE_ERROR = -9

    GRAY_LEVEL_8BIT = 256
    GRAY_LEVEL_10BIT = 1024

    INTEGER_8BIT_CTYPE = ctypes.c_ubyte
    INTEGER_10BIT_CTYPE = ctypes.c_ushort

    def __init__(self, dll_path: str | Path) -> None:
        """
        加载 SLM DLL 并配置函数签名

        参数:
            dll_path: DLL 文件完整路径

        抛出:
            RuntimeError: DLL 加载失败时抛出
        """
        self._dll_path = Path(dll_path)
        self._last_dll_load_error: Exception | None = None

        try:
            self._dll = ctypes.WinDLL(str(self._dll_path))
        except Exception as error:
            self._last_dll_load_error = error
            message = "加载 SLM DLL 失败: %s" % self._dll_path
            raise RuntimeError(message) from error

        self._configure_functions()

    def _configure_functions(self) -> None:
        configure_slm_dll_functions(self._dll)

    def get_display_count_and_names(self) -> tuple[int, str | None]:
        """
        获取显示器数量和名称
        """
        display_count = ctypes.c_int()
        display_names = ctypes.create_string_buffer(_DISPLAY_NAME_BUFFER_SIZE)

        status = self._dll.SLM_Disp_Info_NumberName(
            ctypes.byref(display_count),
            display_names,
        )

        if status == self.STATUS_OK:
            return display_count.value, self._decode_display_names(display_names.value)

        return status, None

    def get_display_resolution(
        self,
        display_number: int,
    ) -> tuple[int | None, int | None]:
        """
        获取显示器分辨率

        参数:
            display_number: 显示器编号

        返回:
            成功时返回宽度和高度；失败时返回 None
        """
        width = ctypes.c_int()
        height = ctypes.c_int()

        status = self._dll.SLM_Disp_Info(
            display_number,
            ctypes.byref(width),
            ctypes.byref(height),
        )

        if status == self.STATUS_OK:
            return width.value, height.value

        return None, None

    def get_display_coordinate(
        self,
        display_number: int,
    ) -> tuple[int | None, int | None]:
        """
        获取显示器左上角坐标

        参数:
            display_number: 显示器编号

        返回:
            成功时返回 X 和 Y 坐标；失败时返回 None
        """
        x_coordinate = ctypes.c_int()
        y_coordinate = ctypes.c_int()

        status = self._dll.SLM_Disp_CoordInfo(
            display_number,
            ctypes.byref(x_coordinate),
            ctypes.byref(y_coordinate),
        )

        if status == self.STATUS_OK:
            return x_coordinate.value, y_coordinate.value

        return None, None

    def open_display(self, display_number: int) -> int:
        """
        打开显示窗口

        参数:
            display_number: 显示器编号

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Disp_Open(display_number)

    def close_display(self, display_number: int) -> int:
        """
        关闭显示窗口

        参数:
            display_number: 显示器编号

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Disp_Close(display_number)

    def set_user_display_size_enabled(
        self,
        display_number: int,
        enabled: int,
    ) -> int:
        """
        启用或关闭用户显示区域

        参数:
            display_number: 显示器编号
            enabled:        开关状态

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Set_UserDispSizeEnabled(display_number, enabled)

    def set_user_display_size(
        self,
        display_number: int,
        width: int,
        height: int,
        x_coordinate: int,
        y_coordinate: int,
    ) -> int:
        """
        写入用户显示区域矩形

        参数:
            display_number: 显示器编号
            width:          显示区域宽度
            height:         显示区域高度
            x_coordinate:   显示区域左上角 X 坐标
            y_coordinate:   显示区域左上角 Y 坐标

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Set_UserDispSize(
            display_number,
            width,
            height,
            x_coordinate,
            y_coordinate,
        )

    def get_user_display_size_enabled(self, display_number: int) -> int | None:
        """
        获取用户显示区域开关状态

        参数:
            display_number: 显示器编号

        返回:
            成功时返回开关状态；失败时返回 None
        """
        enabled = ctypes.c_int()

        status = self._dll.SLM_Get_UserDispSizeEnabled(
            display_number,
            ctypes.byref(enabled),
        )

        if status == self.STATUS_OK:
            return enabled.value

        return None

    def get_user_display_size(
        self,
        display_number: int,
    ) -> tuple[int | None, int | None, int | None, int | None]:
        """
        获取用户显示区域

        参数:
            display_number: 显示器编号

        返回:
            成功时返回宽度、高度、X 坐标和 Y 坐标；失败时返回 None
        """
        width = ctypes.c_int()
        height = ctypes.c_int()
        x_coordinate = ctypes.c_int()
        y_coordinate = ctypes.c_int()

        status = self._dll.SLM_Get_UserDispSize(
            display_number,
            ctypes.byref(width),
            ctypes.byref(height),
            ctypes.byref(x_coordinate),
            ctypes.byref(y_coordinate),
        )

        if status == self.STATUS_OK:
            return (
                width.value,
                height.value,
                x_coordinate.value,
                y_coordinate.value,
            )

        return None, None, None, None

    def display_grayscale_image(
        self,
        display_number: int,
        gray_level_count: int,
        gray_scale: int,
    ) -> int:
        """
        显示单一灰度图像

        参数:
            display_number:   显示器编号
            gray_level_count: 灰度级数
            gray_scale:       灰度值

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Disp_GrayScale(
            display_number,
            gray_level_count,
            gray_scale,
        )

    def display_hbitmap_image(
        self,
        display_number: int,
        gray_level_count: int,
        hbitmap: wintypes.HBITMAP,
    ) -> int:
        """
        显示 HBITMAP 图像

        参数:
            display_number:   显示器编号
            gray_level_count: 灰度级数
            hbitmap:          HBITMAP 句柄

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Disp_BMP(
            display_number,
            gray_level_count,
            hbitmap,
        )

    def display_integer_data(
        self,
        display_number: int,
        width: int,
        height: int,
        gray_level_count: int,
        data: (
            ctypes.Array
            | ctypes.POINTER(ctypes.c_ubyte)
            | ctypes.POINTER(ctypes.c_ushort)
        ),
    ) -> int:
        """
        显示整数灰度数据

        参数:
            display_number:   显示器编号
            width:            数据宽度
            height:           数据高度
            gray_level_count: 灰度级数
            data:             图像数据缓冲区

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Disp_Data(
            display_number,
            width,
            height,
            gray_level_count,
            data,
        )

    def display_normalized_float_data(
        self,
        display_number: int,
        width: int,
        height: int,
        gray_level_count: int,
        data: ctypes.Array | ctypes.POINTER(ctypes.c_double),
    ) -> int:
        """
        显示归一化浮点数据

        参数:
            display_number:   显示器编号
            width:            数据宽度
            height:           数据高度
            gray_level_count: 灰度级数
            data:             0 到 1 的浮点数据缓冲区

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Disp_Data_Double(
            display_number,
            width,
            height,
            gray_level_count,
            data,
        )

    def display_image_from_path(
        self,
        display_number: int,
        file_path: str | Path,
    ) -> int:
        """
        从宽字符路径读取并显示图像

        参数:
            display_number: 显示器编号
            file_path:      图像文件路径

        返回:
            DLL 状态码
        """
        wide_file_path = ctypes.c_wchar_p(str(file_path))
        return self._dll.SLM_Disp_ReadImage(display_number, wide_file_path)

    def display_image_from_ascii_path(
        self,
        display_number: int,
        file_path: str | Path,
    ) -> int:
        """
        从 ASCII 路径读取并显示图像

        参数:
            display_number: 显示器编号
            file_path:      图像文件路径

        抛出:
            ValueError: 路径包含非 ASCII 字符时抛出

        返回:
            DLL 状态码
        """
        path_string = str(file_path)
        self._validate_ascii_path(path_string)
        narrow_file_path = ctypes.c_char_p(path_string.encode("ascii"))
        return self._dll.SLM_Disp_ReadImage_A(
            display_number,
            narrow_file_path,
        )

    def display_csv_from_path(
        self,
        display_number: int,
        gray_level_count: int,
        file_path: str | Path,
    ) -> int:
        """
        从宽字符路径读取并显示 CSV 图像数据

        参数:
            display_number:   显示器编号
            gray_level_count: 灰度级数
            file_path:        CSV 文件路径

        返回:
            DLL 状态码
        """
        wide_file_path = ctypes.c_wchar_p(str(file_path))
        return self._dll.SLM_Disp_ReadCSV(
            display_number,
            gray_level_count,
            wide_file_path,
        )

    def display_csv_from_ascii_path(
        self,
        display_number: int,
        gray_level_count: int,
        file_path: str | Path,
    ) -> int:
        """
        从 ASCII 路径读取并显示 CSV 图像数据

        参数:
            display_number:   显示器编号
            gray_level_count: 灰度级数
            file_path:        CSV 文件路径

        抛出:
            ValueError: 路径包含非 ASCII 字符时抛出

        返回:
            DLL 状态码
        """
        path_string = str(file_path)
        self._validate_ascii_path(path_string)
        narrow_file_path = ctypes.c_char_p(path_string.encode("ascii"))
        return self._dll.SLM_Disp_ReadCSV_A(
            display_number,
            gray_level_count,
            narrow_file_path,
        )

    def set_display_offset(
        self,
        display_number: int,
        offset_x: int,
        offset_y: int,
    ) -> int:
        """
        写入显示窗口偏移量

        参数:
            display_number: 显示器编号
            offset_x:       水平偏移
            offset_y:       垂直偏移

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Set_Offset(display_number, offset_x, offset_y)

    def get_display_offset(
        self,
        display_number: int,
    ) -> tuple[int | None, int | None]:
        """
        获取显示偏移

        参数:
            display_number: 显示器编号

        返回:
            成功时返回水平和垂直偏移；失败时返回 None
        """
        offset_x = ctypes.c_int()
        offset_y = ctypes.c_int()

        status = self._dll.SLM_Get_Offset(
            display_number,
            ctypes.byref(offset_x),
            ctypes.byref(offset_y),
        )

        if status == self.STATUS_OK:
            return offset_x.value, offset_y.value

        return None, None

    def initialize_trigger(self, display_number: int) -> int:
        """
        重置显示器触发状态

        参数:
            display_number: 显示器编号

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Set_TriggerInit(display_number)

    def set_trigger_configuration(
        self,
        display_number: int,
        trigger_enabled: int,
        trigger_mode_1: int,
        trigger_mode_2: int,
        trigger_time: int,
        trigger_frame_header_enabled: int = 1,
    ) -> int:
        """
        写入显示器触发参数

        参数:
            display_number:               显示器编号
            trigger_enabled:              触发开关
            trigger_mode_1:               触发模式 1
            trigger_mode_2:               触发模式 2
            trigger_time:                 触发延时
            trigger_frame_header_enabled: 帧头开关

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Set_Trigger(
            display_number,
            trigger_enabled,
            trigger_mode_1,
            trigger_mode_2,
            trigger_time,
            trigger_frame_header_enabled,
        )

    def get_trigger_configuration(
        self,
        display_number: int,
    ) -> tuple[int | None, int | None, int | None, int | None, int | None]:
        """
        获取触发配置

        参数:
            display_number: 显示器编号

        返回:
            成功时返回触发开关、模式 1、模式 2、延时和帧头开关
        """
        trigger_enabled = ctypes.c_int()
        trigger_mode_1 = ctypes.c_int()
        trigger_mode_2 = ctypes.c_int()
        trigger_time = ctypes.c_int()
        trigger_frame_header_enabled = ctypes.c_int()

        status = self._dll.SLM_Get_Trigger(
            display_number,
            ctypes.byref(trigger_enabled),
            ctypes.byref(trigger_mode_1),
            ctypes.byref(trigger_mode_2),
            ctypes.byref(trigger_time),
            ctypes.byref(trigger_frame_header_enabled),
        )

        if status == self.STATUS_OK:
            return (
                trigger_enabled.value,
                trigger_mode_1.value,
                trigger_mode_2.value,
                trigger_time.value,
                trigger_frame_header_enabled.value,
            )

        return None, None, None, None, None

    def set_gamma_file_from_path(
        self,
        display_number: int,
        gamma_mode: int,
        file_path: str | Path,
    ) -> int:
        """
        使用宽字符路径加载硬件 Gamma 文件

        参数:
            display_number: 显示器编号
            gamma_mode:     Gamma 模式
            file_path:      Gamma 文件路径

        返回:
            DLL 状态码
        """
        wide_file_path = ctypes.c_wchar_p(str(file_path))
        return self._dll.SLM_Set_Gamma(
            display_number,
            gamma_mode,
            wide_file_path,
        )

    def set_gamma_file_from_ascii_path(
        self,
        display_number: int,
        gamma_mode: int,
        file_path: str | Path,
    ) -> int:
        """
        使用 ASCII 路径加载硬件 Gamma 文件

        参数:
            display_number: 显示器编号
            gamma_mode:     Gamma 模式
            file_path:      Gamma 文件路径

        抛出:
            ValueError: 路径包含非 ASCII 字符时抛出

        返回:
            DLL 状态码
        """
        path_string = str(file_path)
        self._validate_ascii_path(path_string)
        narrow_file_path = ctypes.c_char_p(path_string.encode("ascii"))
        return self._dll.SLM_Set_Gamma_A(
            display_number,
            gamma_mode,
            narrow_file_path,
        )

    def set_gamma_enabled(self, display_number: int, enabled: int) -> int:
        """
        启用或关闭硬件 Gamma 文件

        参数:
            display_number: 显示器编号
            enabled:        开关状态

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Set_GammaEnabled(display_number, enabled)

    def set_soft_gamma_enabled(self, display_number: int, enabled: int) -> int:
        """
        启用或关闭软件 Gamma

        参数:
            display_number: 显示器编号
            enabled:        开关状态

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Set_SoftGammaEnabled(display_number, enabled)

    def set_soft_gamma_value(self, display_number: int, value: float) -> int:
        """
        写入软件 Gamma 数值

        参数:
            display_number: 显示器编号
            value:          Gamma 数值

        返回:
            DLL 状态码
        """
        return self._dll.SLM_Set_SoftGammaValue(display_number, float(value))

    def get_soft_gamma_enabled(self, display_number: int) -> int | None:
        """
        获取软件 Gamma 开关状态

        参数:
            display_number: 显示器编号

        返回:
            成功时返回开关状态；失败时返回 None
        """
        enabled = ctypes.c_int()

        status = self._dll.SLM_Get_SoftGammaEnabled(
            display_number,
            ctypes.byref(enabled),
        )

        if status == self.STATUS_OK:
            return enabled.value

        return None

    def get_soft_gamma_value(self, display_number: int) -> float | None:
        """
        获取软件 Gamma 数值

        参数:
            display_number: 显示器编号

        返回:
            成功时返回 Gamma 数值；失败时返回 None
        """
        value = ctypes.c_double()

        status = self._dll.SLM_Get_SoftGammaValue(
            display_number,
            ctypes.byref(value),
        )

        if status == self.STATUS_OK:
            return value.value

        return None

    def set_splicing_screen_enabled(
        self,
        display_numbers: Sequence[int],
        enabled: bool | int,
    ) -> int:
        """
        启用或关闭多屏拼接

        参数:
            display_numbers: 参与拼接的显示器编号列表
            enabled:         开关状态

        抛出:
            ValueError: 显示器编号列表为空时抛出

        返回:
            DLL 状态码
        """
        if not display_numbers:
            message = "拼接显示器列表不能为空。"
            raise ValueError(message)

        display_array_type = ctypes.c_int * len(display_numbers)
        display_array = display_array_type(*[int(number) for number in display_numbers])
        return self._dll.SLM_Set_SplicingScreenEnabled(
            display_array,
            int(bool(enabled)),
            len(display_numbers),
        )

    def get_splicing_screen_enabled(self, display_number: int) -> int | None:
        """
        获取多屏拼接开关状态

        参数:
            display_number: 显示器编号

        返回:
            成功时返回开关状态；失败时返回 None
        """
        enabled = ctypes.c_int()

        status = self._dll.SLM_Get_SplicingScreenEnabled(
            display_number,
            ctypes.byref(enabled),
        )

        if status == self.STATUS_OK:
            return enabled.value

        return None

    def display_spliced_image(self) -> int:
        """
        显示多屏拼接图像
        """
        return self._dll.SLM_Disp_Splice()

    def _validate_ascii_path(self, path_string: str) -> None:
        if not path_string.isascii():
            message = "路径包含非 ASCII 字符: %s" % path_string
            raise ValueError(message)

    @staticmethod
    def _decode_display_names(raw_display_names: bytes) -> str:
        for encoding in ("utf-8", "mbcs"):
            try:
                return raw_display_names.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                continue
        return raw_display_names.decode("utf-8", errors="replace")
