from __future__ import annotations

import argparse
from collections.abc import Sequence
import ctypes
from pathlib import Path
import random
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from utils.devices.slm import VENDOR_DLL_PATH
from utils.devices.slm.api import UPOLabsSLMDeviceAPI

DEFAULT_DEMO_IMAGE_PATH = (
    Path(__file__).resolve().parent / "assets" / "demo_image_1920x1200.bmp"
)
DEFAULT_FIXED_GRAY_LEVEL_COUNT = 256
DEFAULT_FIXED_GRAY_VALUE = 122
DEFAULT_ARRAY_GRAY_LEVEL_COUNT = 1024
DEFAULT_PATTERN_SEED = 20260408
DEMO_IMAGE_WIDTH = 1920
DEMO_IMAGE_HEIGHT = 1200

_FAILURE_DISPLAY_DISCOVERY = "display_discovery"
_FAILURE_NO_DISPLAYS = "no_displays"
_FAILURE_DISPLAY_SELECTION = "display_selection"
_FAILURE_DISPLAY_RESOLUTION = "display_resolution"
_FAILURE_DISPLAY_OPEN = "display_open"
_FAILURE_STAGE_1_GRAYSCALE = "stage_1_grayscale"
_FAILURE_STAGE_2_IMAGE_FILE = "stage_2_image_file"
_FAILURE_STAGE_3_ARRAY_PATTERN = "stage_3_array_pattern"

_RUNTIME_FAILURE_MESSAGES = {
    _FAILURE_DISPLAY_DISCOVERY: (
        "The SLM display example failed while detecting available "
        "displays."
    ),
    _FAILURE_NO_DISPLAYS: (
        "The SLM display example could not find any SLM displays."
    ),
    _FAILURE_DISPLAY_SELECTION: (
        "The SLM display example received a display number that is "
        "out of range."
    ),
    _FAILURE_DISPLAY_RESOLUTION: (
        "The SLM display example failed while reading the display "
        "resolution."
    ),
    _FAILURE_DISPLAY_OPEN: (
        "The SLM display example failed while opening the display."
    ),
    _FAILURE_STAGE_1_GRAYSCALE: (
        "The SLM display example failed during stage 1 while "
        "displaying the grayscale image."
    ),
    _FAILURE_STAGE_2_IMAGE_FILE: (
        "The SLM display example failed during stage 2 while "
        "displaying the image file."
    ),
    _FAILURE_STAGE_3_ARRAY_PATTERN: (
        "The SLM display example failed during stage 3 while "
        "displaying the array pattern."
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
    解析整合后的 SLM 显示演示命令行参数

    参数:
        arguments: 命令行参数序列；传入 None 时使用 sys.argv。

    返回:
        解析后的参数对象。
    """
    parser = argparse.ArgumentParser(
        description="Run the consolidated SLM display example."
    )
    parser.add_argument("--dll-path", type=Path, default=VENDOR_DLL_PATH)
    parser.add_argument("--display-number", type=int, default=0)
    parser.add_argument(
        "--image-path",
        type=Path,
        default=DEFAULT_DEMO_IMAGE_PATH,
    )
    parser.add_argument(
        "--grayscale-gray-level-count",
        "--gray-level-count",
        dest="grayscale_gray_level_count",
        type=int,
        default=DEFAULT_FIXED_GRAY_LEVEL_COUNT,
    )
    parser.add_argument(
        "--grayscale-value",
        "--gray-scale",
        dest="grayscale_value",
        type=int,
        default=DEFAULT_FIXED_GRAY_VALUE,
    )
    parser.add_argument(
        "--array-gray-level-count",
        type=int,
        default=DEFAULT_ARRAY_GRAY_LEVEL_COUNT,
    )
    parser.add_argument(
        "--pattern-seed",
        type=int,
        default=DEFAULT_PATTERN_SEED,
    )
    return parser.parse_args(arguments)


def build_array_pattern(
    width: int,
    height: int,
    gray_level_count: int,
    pattern_seed: int,
) -> ctypes.Array:
    """
    构造数组显示阶段使用的确定性图样数据

    参数:
        width:            图样宽度。
        height:           图样高度。
        gray_level_count: 灰度级数。
        pattern_seed:     固定伪随机种子。

    返回:
        可直接传给DLL的连续整数数组。
    """
    random_generator = random.Random(pattern_seed)
    pixel_count = width * height
    if gray_level_count <= 256:
        pattern_data = (ctypes.c_ubyte * pixel_count)()
    else:
        pattern_data = (ctypes.c_ushort * pixel_count)()

    for pixel_index in range(pixel_count):
        pattern_data[pixel_index] = random_generator.randrange(
            gray_level_count
        )

    return pattern_data


build_integer_pattern = build_array_pattern


def run_display(
    dll_path: Path = VENDOR_DLL_PATH,
    display_number: int = 0,
    image_path: Path = DEFAULT_DEMO_IMAGE_PATH,
    grayscale_gray_level_count: int = DEFAULT_FIXED_GRAY_LEVEL_COUNT,
    grayscale_value: int = DEFAULT_FIXED_GRAY_VALUE,
    array_gray_level_count: int = DEFAULT_ARRAY_GRAY_LEVEL_COUNT,
    pattern_seed: int = DEFAULT_PATTERN_SEED,
) -> None:
    """
    按顺序运行三种 SLM 显示方式的排查示例

    参数:
        dll_path:                   厂商 DLL 路径。
        display_number:             显示器编号。
        image_path:                 示例图像路径。
        grayscale_gray_level_count: 固定灰度阶段的灰度级数。
        grayscale_value:            固定灰度阶段的灰度值。
        array_gray_level_count:     数组图样阶段的灰度级数。
        pattern_seed:               数组图样阶段的固定伪随机种子。

    抛出:
        RuntimeError: 任一阶段失败时抛出。
    """
    slm_api = UPOLabsSLMDeviceAPI(dll_path)
    display_is_open = False

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
    print(
        "Demo asset resolution: %sx%s"
        % (DEMO_IMAGE_WIDTH, DEMO_IMAGE_HEIGHT)
    )
    if width != DEMO_IMAGE_WIDTH or height != DEMO_IMAGE_HEIGHT:
        print(
            "Resolution note: current display is %sx%s "
            "while the demo asset is %sx%s."
            % (width, height, DEMO_IMAGE_WIDTH, DEMO_IMAGE_HEIGHT)
        )

    try:
        open_status = slm_api.open_display(display_number)
        print("Open status: %s" % open_status)
        if open_status != UPOLabsSLMDeviceAPI.STATUS_OK:
            _raise_failure(
                _FAILURE_DISPLAY_OPEN,
                "打开显示器失败，状态码为%s。" % open_status,
            )

        display_is_open = True

        print("Stage 1/3: Grayscale display")
        grayscale_status = slm_api.display_grayscale_image(
            display_number,
            grayscale_gray_level_count,
            grayscale_value,
        )
        print("Grayscale status: %s" % grayscale_status)
        if grayscale_status != UPOLabsSLMDeviceAPI.STATUS_OK:
            _raise_failure(
                _FAILURE_STAGE_1_GRAYSCALE,
                "固定灰度显示失败，状态码为%s。" % grayscale_status,
            )
        _pause_after_stage()

        print("Stage 2/3: Image file display")
        image_status = slm_api.display_image_from_path(
            display_number,
            image_path,
        )
        print("Image file status: %s" % image_status)
        if image_status != UPOLabsSLMDeviceAPI.STATUS_OK:
            _raise_failure(
                _FAILURE_STAGE_2_IMAGE_FILE,
                "图像文件显示失败，状态码为%s。" % image_status,
            )
        _pause_after_stage()

        print("Stage 3/3: Array pattern display")
        pattern_data = build_array_pattern(
            width=width,
            height=height,
            gray_level_count=array_gray_level_count,
            pattern_seed=pattern_seed,
        )
        pattern_status = slm_api.display_integer_data(
            display_number,
            width,
            height,
            array_gray_level_count,
            pattern_data,
        )
        print("Array pattern status: %s" % pattern_status)
        if pattern_status != UPOLabsSLMDeviceAPI.STATUS_OK:
            _raise_failure(
                _FAILURE_STAGE_3_ARRAY_PATTERN,
                "数组图样显示失败，状态码为%s。" % pattern_status,
            )
        _pause_after_stage()
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
        run_display(
            dll_path=arguments.dll_path,
            display_number=arguments.display_number,
            image_path=arguments.image_path,
            grayscale_gray_level_count=arguments.grayscale_gray_level_count,
            grayscale_value=arguments.grayscale_value,
            array_gray_level_count=arguments.array_gray_level_count,
            pattern_seed=arguments.pattern_seed,
        )
    except Exception as exception:
        print(_translate_cli_failure(exception), file=sys.stderr)
        return 1

    return 0


def _pause_after_stage() -> None:
    """
    暂停等待用户确认下一阶段
    """
    input("Press Enter to continue.")


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
        return "The SLM display example failed during the display sequence."
    return "The SLM display example failed due to an unexpected error."


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
        "The SLM display example failed during the display sequence.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
