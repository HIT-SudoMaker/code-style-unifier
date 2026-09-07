from __future__ import annotations

import argparse
from pathlib import Path

from utils.devices.camera import VENDOR_DLL_PATH
from utils.devices.camera._bindings import ASI_IMG_RAW8
from utils.devices.camera.api import ZWOASICameraDeviceAPI


def main(argv: list[str] | None = None) -> int:
    """
    采集八位相机帧

    参数:
        argv: 可选命令行参数

    返回:
        进程风格退出码
    """
    args = _parse_args(argv)
    api = ZWOASICameraDeviceAPI(args.dll_path)

    camera_info = api.get_camera_info(args.camera_index)
    if camera_info is None:
        print("Failed to read camera info for index %s" % args.camera_index)
        return 1

    camera_id = camera_info.camera_id
    width = args.width or camera_info.max_width
    height = args.height or camera_info.max_height

    open_status = api.open_camera(camera_id)
    if open_status != api.STATUS_SUCCESS:
        print("Failed to open camera: status=%s" % open_status)
        return 1

    try:
        init_status = api.initialize_camera(camera_id)
        if init_status != api.STATUS_SUCCESS:
            print("Failed to initialize camera: status=%s" % init_status)
            return 1

        roi_status = api.set_roi_format(camera_id, width, height, 1, ASI_IMG_RAW8)
        if roi_status != api.STATUS_SUCCESS:
            print("Failed to set RAW8 ROI: status=%s" % roi_status)
            return 1

        start_status = api.start_video_capture(camera_id)
        if start_status != api.STATUS_SUCCESS:
            print("Failed to start video capture: status=%s" % start_status)
            return 1

        try:
            for frame_index in range(args.frames):
                status, frame = api.capture_raw8_frame(
                    camera_id=camera_id,
                    width=width,
                    height=height,
                    timeout_ms=args.timeout_ms,
                )
                if status != api.STATUS_SUCCESS or frame is None:
                    print("Failed to capture RAW8 frame: status=%s" % status)
                    return 1
                print(
                    "Frame %s: dtype=%s, shape=%sx%s"
                    % (
                        frame_index,
                        frame.data.dtype,
                        frame.height,
                        frame.width,
                    ),
                )
        finally:
            api.stop_video_capture(camera_id)
    finally:
        api.close_camera(camera_id)

    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture ZWO ASI RAW8 frames.")
    parser.add_argument("--dll-path", type=Path, default=VENDOR_DLL_PATH)
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--frames", type=int, default=1)
    parser.add_argument("--timeout-ms", type=int, default=1000)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
