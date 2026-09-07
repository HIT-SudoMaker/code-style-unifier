from __future__ import annotations

import argparse
from pathlib import Path

from utils.devices.stage import VENDOR_DLL_PATH
from utils.devices.stage.motion import ACSMotionStage
from utils.devices.stage.motion import DEFAULT_CONTROLLER_IP
from utils.devices.stage.motion import DEFAULT_STAGE_AXIS
from utils.devices.stage.motion import DEFAULT_STAGE_PORT


def main(argv: list[str] | None = None) -> int:
    """
    运行运动台联通示例

    参数:
        argv: 可选命令行参数

    返回:
        进程风格退出码
    """
    args = _parse_args(argv)
    stage = ACSMotionStage(
        dll_path=args.dll_path,
        ip_address=args.ip,
        port=args.port,
        axis=args.axis,
    )
    handle = stage.open()
    if handle is None:
        print("Failed to connect to ACS controller.")
        return 1

    try:
        print("Library version: %s" % stage.api.get_library_version())
        firmware_version = stage.api.get_firmware_version()
        if firmware_version:
            print("Firmware version: %s" % firmware_version)
        print("Axis %s position: %s" % (args.axis, stage.get_position()))
    finally:
        stage.close()

    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bring up an ACS motion stage.")
    parser.add_argument("--dll-path", type=Path, default=VENDOR_DLL_PATH)
    parser.add_argument("--ip", default=DEFAULT_CONTROLLER_IP)
    parser.add_argument("--port", type=int, default=DEFAULT_STAGE_PORT)
    parser.add_argument("--axis", type=int, default=DEFAULT_STAGE_AXIS)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
