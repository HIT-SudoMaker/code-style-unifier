from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from utils.devices.slm import VENDOR_DLL_PATH
from utils.devices.slm.api import UPOLabsSLMDeviceAPI


_FAILURE_DISPLAY_DISCOVERY = "display_discovery"
_FAILURE_NO_DISPLAYS = "no_displays"
_FAILURE_DISPLAY_SELECTION = "display_selection"
_FAILURE_DISPLAY_RESOLUTION = "display_resolution"
_FAILURE_DISPLAY_OPEN = "display_open"
_FAILURE_GRAYSCALE = "grayscale"
_FAILURE_OFFSET_SET = "offset_set"
_FAILURE_OFFSET_GET = "offset_get"
_FAILURE_TRIGGER_SET = "trigger_set"
_FAILURE_TRIGGER_GET = "trigger_get"

_RUNTIME_FAILURE_MESSAGES = {
    _FAILURE_DISPLAY_DISCOVERY: (
        "The SLM bring-up example failed while detecting available "
        "displays."
    ),
    _FAILURE_NO_DISPLAYS: (
        "The SLM bring-up example could not find any SLM displays."
    ),
    _FAILURE_DISPLAY_SELECTION: (
        "The SLM bring-up example received a display number that is "
        "out of range."
    ),
    _FAILURE_DISPLAY_RESOLUTION: (
        "The SLM bring-up example failed while reading the display "
        "resolution."
    ),
    _FAILURE_DISPLAY_OPEN: (
        "The SLM bring-up example failed while opening the display."
    ),
    _FAILURE_GRAYSCALE: (
        "The SLM bring-up example failed while displaying the "
        "grayscale test pattern."
    ),
    _FAILURE_OFFSET_SET: (
        "The SLM bring-up example failed while configuring the "
        "display offset."
    ),
    _FAILURE_OFFSET_GET: (
        "The SLM bring-up example failed while reading back the "
        "display offset."
    ),
    _FAILURE_TRIGGER_SET: (
        "The SLM bring-up example failed while configuring the "
        "trigger settings."
    ),
    _FAILURE_TRIGGER_GET: (
        "The SLM bring-up example failed while reading back the "
        "trigger settings."
    ),
}


class _ExampleRuntimeError(RuntimeError):
    """
    带失败类别的示例运行异常
    """

    def __init__(self, category: str, internal_message: str) -> None:
        """
        初始化示例运行异常

        参数:
            category:         失败类别
            internal_message: 内部错误信息
        """
        super().__init__(internal_message)
        self.category = category


def _raise_failure(category: str, internal_message: str) -> None:
    """
    抛出带类别的示例运行异常

    参数:
        category:         失败类别
        internal_message: 内部错误信息
    """
    raise _ExampleRuntimeError(category, internal_message)


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """
    解析整合后的 SLM bring-up 示例命令行参数

    参数:
        arguments: 命令行参数序列；传入 None 时使用 sys.argv。

    返回:
        解析后的参数对象。
    """
    parser = argparse.ArgumentParser(
        description="Run the consolidated SLM bring-up example."
    )
    parser.add_argument("--dll-path", type=Path, default=VENDOR_DLL_PATH)
    parser.add_argument("--display-number", type=int, default=0)
    parser.add_argument("--gray-level-count", type=int, default=256)
    parser.add_argument("--gray-scale", type=int, default=122)
    parser.add_argument("--offset-x", type=int, default=100)
    parser.add_argument("--offset-y", type=int, default=100)
    parser.add_argument("--trigger-enabled", type=int, default=1)
    parser.add_argument("--trigger-mode-1", type=int, default=1)
    parser.add_argument("--trigger-mode-2", type=int, default=1)
    parser.add_argument("--trigger-time", type=int, default=1)
    parser.add_argument("--trigger-frame-header-enabled", type=int, default=1)
    return parser.parse_args(arguments)


def run_bring_up(
    dll_path: Path = VENDOR_DLL_PATH,
    display_number: int = 0,
    gray_level_count: int = 256,
    gray_scale: int = 122,
    offset_x: int = 100,
    offset_y: int = 100,
    trigger_enabled: int = 1,
    trigger_mode_1: int = 1,
    trigger_mode_2: int = 1,
    trigger_time: int = 1,
    trigger_frame_header_enabled: int = 1,
) -> None:
    """
    运行整合后的 SLM bring-up 示例

    参数:
        dll_path:                     厂商 DLL 路径。
        display_number:               显示器编号。
        gray_level_count:             灰度级数。
        gray_scale:                   灰度值。
        offset_x:                     水平偏移量。
        offset_y:                     垂直偏移量。
        trigger_enabled:              触发使能。
        trigger_mode_1:               第一触发模式。
        trigger_mode_2:               第二触发模式。
        trigger_time:                 触发延时。
        trigger_frame_header_enabled: 帧头使能。

    抛出:
        RuntimeError: 任一步骤失败时抛出。
    """
    slm_api = UPOLabsSLMDeviceAPI(dll_path)

    display_count, display_names = slm_api.get_display_count_and_names()
    if display_names is None:
        _raise_failure(
            _FAILURE_DISPLAY_DISCOVERY,
            "读取SLM显示器清单失败，状态码为%s。" % display_count,
        )

    print("Display count: %s" % display_count)
    print("Display names: %s" % display_names)

    if display_count <= 0:
        _raise_failure(
            _FAILURE_NO_DISPLAYS,
            "当前没有可用的SLM显示器。",
        )
    if not 0 <= display_number < display_count:
        _raise_failure(
            _FAILURE_DISPLAY_SELECTION,
            "显示器编号%s超出范围，当前仅检测到%s个显示器。"
            % (display_number, display_count),
        )

    width, height = slm_api.get_display_resolution(display_number)
    if width is None or height is None:
        _raise_failure(
            _FAILURE_DISPLAY_RESOLUTION,
            "读取显示器%s分辨率失败。" % display_number,
        )
    print("Display resolution: %sx%s" % (width, height))

    display_is_open = False
    try:
        open_status = slm_api.open_display(display_number)
        print("Open status: %s" % open_status)
        if open_status != UPOLabsSLMDeviceAPI.STATUS_OK:
            _raise_failure(
                _FAILURE_DISPLAY_OPEN,
                "打开显示器失败，状态码为%s。" % open_status,
            )

        display_is_open = True

        grayscale_status = slm_api.display_grayscale_image(
            display_number,
            gray_level_count,
            gray_scale,
        )
        print("Grayscale status: %s" % grayscale_status)
        if grayscale_status != UPOLabsSLMDeviceAPI.STATUS_OK:
            _raise_failure(
                _FAILURE_GRAYSCALE,
                "灰度显示失败，状态码为%s。" % grayscale_status,
            )

        offset_status = slm_api.set_display_offset(
            display_number,
            offset_x,
            offset_y,
        )
        print("Offset status: %s" % offset_status)
        if offset_status != UPOLabsSLMDeviceAPI.STATUS_OK:
            _raise_failure(
                _FAILURE_OFFSET_SET,
                "设置显示偏移失败，状态码为%s。" % offset_status,
            )

        current_offset_x, current_offset_y = slm_api.get_display_offset(
            display_number
        )
        if current_offset_x is None or current_offset_y is None:
            _raise_failure(
                _FAILURE_OFFSET_GET,
                "读取显示偏移失败，显示器编号为%s。"
                % display_number,
            )
        print(
            "Current offset: (%s, %s)"
            % (current_offset_x, current_offset_y)
        )

        trigger_status = slm_api.set_trigger_configuration(
            display_number,
            trigger_enabled,
            trigger_mode_1,
            trigger_mode_2,
            trigger_time,
            trigger_frame_header_enabled,
        )
        print("Trigger status: %s" % trigger_status)
        if trigger_status != UPOLabsSLMDeviceAPI.STATUS_OK:
            _raise_failure(
                _FAILURE_TRIGGER_SET,
                "设置触发参数失败，状态码为%s。" % trigger_status,
            )

        (
            current_trigger_enabled,
            current_trigger_mode_1,
            current_trigger_mode_2,
            current_trigger_time,
            current_trigger_frame_header_enabled,
        ) = slm_api.get_trigger_configuration(display_number)
        if (
            current_trigger_enabled is None
            or current_trigger_mode_1 is None
            or current_trigger_mode_2 is None
            or current_trigger_time is None
            or current_trigger_frame_header_enabled is None
        ):
            _raise_failure(
                _FAILURE_TRIGGER_GET,
                "读取触发参数失败，显示器编号为%s。"
                % display_number,
            )
        print(
            "Current trigger: (%s, %s, %s, %s, %s)"
            % (
                current_trigger_enabled,
                current_trigger_mode_1,
                current_trigger_mode_2,
                current_trigger_time,
                current_trigger_frame_header_enabled,
            )
        )
    finally:
        if display_is_open:
            close_status = slm_api.close_display(display_number)
            print("Close status: %s" % close_status)


def main() -> int:
    """
    运行命令行入口
    """
    try:
        arguments = parse_arguments()
        run_bring_up(
            dll_path=arguments.dll_path,
            display_number=arguments.display_number,
            gray_level_count=arguments.gray_level_count,
            gray_scale=arguments.gray_scale,
            offset_x=arguments.offset_x,
            offset_y=arguments.offset_y,
            trigger_enabled=arguments.trigger_enabled,
            trigger_mode_1=arguments.trigger_mode_1,
            trigger_mode_2=arguments.trigger_mode_2,
            trigger_time=arguments.trigger_time,
            trigger_frame_header_enabled=(
                arguments.trigger_frame_header_enabled
            ),
        )
    except Exception as exception:
        print(_translate_cli_failure(exception), file=sys.stderr)
        return 1

    return 0


def _translate_cli_failure(exception: Exception) -> str:
    """
    转换命令行异常为面向用户的失败信息

    参数:
        exception: 捕获到的异常

    返回:
        面向用户的失败信息
    """
    if isinstance(exception, _ExampleRuntimeError):
        return _translate_runtime_failure(exception.category)
    if isinstance(exception, RuntimeError):
        return "The SLM bring-up example failed during device setup."
    return "The SLM bring-up example failed due to an unexpected error."


def _translate_runtime_failure(category: str) -> str:
    """
    转换运行阶段类别为英文失败信息

    参数:
        category: 失败类别

    返回:
        英文失败信息
    """
    return _RUNTIME_FAILURE_MESSAGES.get(
        category,
        "The SLM bring-up example failed during device setup.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
