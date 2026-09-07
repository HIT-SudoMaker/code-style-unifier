from __future__ import annotations

import argparse
from pathlib import Path

from utils.devices.camera import VENDOR_DLL_PATH
from utils.devices.camera.api import ZWOASICameraDeviceAPI


def main(argv: list[str] | None = None) -> int:
    """
    运行相机联通示例

    参数:
        argv: 可选命令行参数

    返回:
        进程风格退出码
    """
    args = _parse_args(argv)
    api = ZWOASICameraDeviceAPI(args.dll_path)

    print("SDK version: %s" % api.get_sdk_version())
    camera_count = api.get_camera_count()
    print("Camera count: %s" % camera_count)
    if args.camera_index < 0 or args.camera_index >= camera_count:
        print("Camera index is out of range: %s" % args.camera_index)
        return 1

    camera_info = api.get_camera_info(args.camera_index)
    if camera_info is None:
        print("Failed to read camera info for index %s" % args.camera_index)
        return 1

    camera_id = camera_info.camera_id
    open_status = api.open_camera(camera_id)
    if open_status != api.STATUS_SUCCESS:
        print("Failed to open camera: status=%s" % open_status)
        return 1

    try:
        init_status = api.initialize_camera(camera_id)
        if init_status != api.STATUS_SUCCESS:
            print("Failed to initialize camera: status=%s" % init_status)
            return 1

        control_count = api.get_control_count(camera_id)
        if control_count is None:
            print("Failed to read camera controls.")
            return 1

        print("Camera: %s" % camera_info.name)
        print("Resolution: %sx%s" % (camera_info.max_width, camera_info.max_height))
        print("Controls: %s" % control_count)
        for control_index in range(control_count):
            control_caps = api.get_control_caps(camera_id, control_index)
            if control_caps is not None:
                print(
                    "%s: %s..%s"
                    % (
                        control_caps.name,
                        control_caps.min_value,
                        control_caps.max_value,
                    ),
                )
    finally:
        api.close_camera(camera_id)

    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bring up a ZWO ASI camera.")
    parser.add_argument("--dll-path", type=Path, default=VENDOR_DLL_PATH)
    parser.add_argument("--camera-index", type=int, default=0)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
