from __future__ import annotations

import argparse
from pathlib import Path

from utils.devices.stage import VENDOR_DLL_PATH
from utils.devices.stage.motion import ACSMotionStage
from utils.devices.stage.motion import DEFAULT_CONTROLLER_IP
from utils.devices.stage.motion import DEFAULT_STAGE_AXIS
from utils.devices.stage.motion import DEFAULT_STAGE_PORT
from utils.devices.stage.motion import DEFAULT_STAGE_TIMEOUT_MS
from utils.devices.stage.motion import DEFAULT_STAGE_VELOCITY_MM_PER_SECOND


def main(argv: list[str] | None = None) -> int:
    """
    确认后移动一个运动轴

    参数:
        argv: 可选命令行参数

    返回:
        进程风格退出码
    """
    args = _parse_args(argv)
    if args.run_token != "RUN":
        print("Dry run only. Add --run-token RUN to send motion.")
        return 0

    stage = ACSMotionStage(
        dll_path=args.dll_path,
        ip_address=args.ip,
        port=args.port,
        axis=args.axis,
        default_velocity=args.velocity,
        default_timeout_ms=args.timeout_ms,
    )
    handle = stage.open()
    if handle is None:
        print("Failed to connect to ACS controller.")
        return 1

    try:
        if stage.enable() != stage.api.STATUS_SUCCESS:
            print("Failed to enable axis.")
            return 1
        stage.move_to(position=args.position)
        print("Final position: %s" % stage.get_position())
    finally:
        try:
            stage.disable()
        finally:
            stage.close()

    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Move one ACS motion axis.")
    parser.add_argument("--dll-path", type=Path, default=VENDOR_DLL_PATH)
    parser.add_argument("--ip", default=DEFAULT_CONTROLLER_IP)
    parser.add_argument("--port", type=int, default=DEFAULT_STAGE_PORT)
    parser.add_argument("--axis", type=int, default=DEFAULT_STAGE_AXIS)
    parser.add_argument("--position", type=float, required=True)
    parser.add_argument(
        "--velocity",
        type=float,
        default=DEFAULT_STAGE_VELOCITY_MM_PER_SECOND,
    )
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_STAGE_TIMEOUT_MS)
    parser.add_argument("--run-token", default="")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
