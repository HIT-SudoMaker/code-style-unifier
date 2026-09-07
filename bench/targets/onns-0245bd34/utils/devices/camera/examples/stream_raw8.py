from __future__ import annotations

import argparse
from pathlib import Path

from utils.devices.camera import VENDOR_DLL_PATH
from utils.devices.camera.stream import ASI585MM_FULL_HEIGHT
from utils.devices.camera.stream import ASI585MM_FULL_WIDTH
from utils.devices.camera.stream import DEFAULT_TARGET_OUTPUT_FPS
from utils.devices.camera.stream import ZWOASICameraStream


def main(argv: list[str] | None = None) -> int:
    """
    流式采集八位相机帧

    参数:
        argv: 可选命令行参数

    返回:
        进程风格退出码
    """
    args = _parse_args(argv)
    target_output_fps = None if args.no_output_fps_limit else args.target_output_fps
    stream = ZWOASICameraStream(
        dll_path=args.dll_path,
        camera_index=args.camera_index,
        width=args.width,
        height=args.height,
        frame_queue_size=args.frame_queue_size,
        timeout_ms=args.timeout_ms,
        target_output_fps=target_output_fps,
    )

    stream.start()
    try:
        for frame_index in range(args.frames):
            frame = stream.get_frame(timeout=args.frame_timeout_seconds)
            if frame is None:
                print("Timed out while waiting for RAW8 frame %s" % frame_index)
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

        statistics = stream.get_statistics()
        print(
            "Stream statistics: output=%s, dropped=%s, sdk_dropped=%s"
            % (
                statistics.output_frame_count,
                statistics.dropped_frame_count,
                statistics.sdk_dropped_frame_count,
            ),
        )
    finally:
        stream.stop()

    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream ZWO ASI RAW8 frames.")
    parser.add_argument("--dll-path", type=Path, default=VENDOR_DLL_PATH)
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--width", type=int, default=ASI585MM_FULL_WIDTH)
    parser.add_argument("--height", type=int, default=ASI585MM_FULL_HEIGHT)
    parser.add_argument("--frames", type=int, default=1)
    parser.add_argument("--frame-queue-size", type=int, default=5)
    parser.add_argument("--timeout-ms", type=int, default=1000)
    parser.add_argument("--frame-timeout-seconds", type=float, default=2.0)
    parser.add_argument(
        "--target-output-fps",
        type=float,
        default=DEFAULT_TARGET_OUTPUT_FPS,
    )
    parser.add_argument("--no-output-fps-limit", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
