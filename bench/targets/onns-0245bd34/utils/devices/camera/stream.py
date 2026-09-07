from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import queue
import threading
import time
from types import TracebackType

from ._bindings import ASI_IMG_RAW8
from .api import ZWOASICameraDeviceAPI
from .frame import CameraFrame


ASI585MM_FULL_WIDTH = 3840
ASI585MM_FULL_HEIGHT = 2160
DEFAULT_FRAME_QUEUE_SIZE = 5
DEFAULT_TIMEOUT_MS = 1000
DEFAULT_TARGET_OUTPUT_FPS = 30.0
DEFAULT_STOP_TIMEOUT_SECONDS = 2.0
DEFAULT_VENDOR_DLL_PATH = (
    Path(__file__).resolve().parent / "vendor" / "zwo_asi_camera.dll"
)


@dataclass(frozen=True)
class ZWOASICameraStreamStatistics:
    """
    采集流运行统计

    参数:
        captured_frame_count:    从 SDK 采集到的帧数
        output_frame_count:      发布到输出流的帧数
        dropped_frame_count:     本地队列丢弃的帧数
        sdk_dropped_frame_count: SDK 侧丢帧数，若可用
        last_status:             最近一次 SDK 采集状态
        is_running:              采集线程是否运行
    """

    captured_frame_count: int
    output_frame_count: int
    dropped_frame_count: int
    sdk_dropped_frame_count: int | None
    last_status: int | None
    is_running: bool


class ZWOASICameraStream:
    """
    连续八位采集流
    """

    def __init__(
        self,
        dll_path: str | Path = DEFAULT_VENDOR_DLL_PATH,
        *,
        camera_index: int = 0,
        width: int = ASI585MM_FULL_WIDTH,
        height: int = ASI585MM_FULL_HEIGHT,
        frame_queue_size: int = DEFAULT_FRAME_QUEUE_SIZE,
        drop_oldest_frame: bool = True,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        target_output_fps: float | None = DEFAULT_TARGET_OUTPUT_FPS,
        stop_timeout_seconds: float = DEFAULT_STOP_TIMEOUT_SECONDS,
    ) -> None:
        """
        初始化采集流

        参数:
            dll_path:             ZWO ASI 相机 DLL 完整路径
            camera_index:         SDK 相机索引
            width:                RAW8 ROI 宽度，单位为像素
            height:               RAW8 ROI 高度，单位为像素
            frame_queue_size:     输出帧队列深度
            drop_oldest_frame:    队列满时丢弃最旧帧
            timeout_ms:           SDK 帧等待超时时间，单位为毫秒
            target_output_fps:    输出帧率限制；None 表示不限制
            stop_timeout_seconds: 采集线程等待结束超时时间

        抛出:
            ValueError:   采集流配置无效时抛出
            RuntimeError: DLL 加载失败时抛出
        """
        _validate_stream_configuration(
            camera_index=camera_index,
            width=width,
            height=height,
            frame_queue_size=frame_queue_size,
            timeout_ms=timeout_ms,
            target_output_fps=target_output_fps,
            stop_timeout_seconds=stop_timeout_seconds,
        )

        self.dll_path = Path(dll_path)
        self.camera_index = int(camera_index)
        self.width = int(width)
        self.height = int(height)
        self.frame_queue_size = int(frame_queue_size)
        self.drop_oldest_frame = bool(drop_oldest_frame)
        self.timeout_ms = int(timeout_ms)
        self.target_output_fps = (
            None if target_output_fps is None else float(target_output_fps)
        )
        self.stop_timeout_seconds = float(stop_timeout_seconds)

        self._api = ZWOASICameraDeviceAPI(self.dll_path)
        self._frame_queue: queue.Queue[CameraFrame] = queue.Queue(
            maxsize=self.frame_queue_size,
        )
        self._frame_lock = threading.Lock()
        self._state_lock = threading.RLock()
        self._stop_event = threading.Event()

        self._latest_frame: CameraFrame | None = None
        self._camera_id: int | None = None
        self._acquisition_thread: threading.Thread | None = None
        self._is_running = False
        self._captured_frame_count = 0
        self._output_frame_count = 0
        self._dropped_frame_count = 0
        self._sdk_dropped_frame_count: int | None = None
        self._last_status: int | None = None
        self._last_error: Exception | None = None
        self._last_output_time = 0.0

    def start(self) -> None:
        """
        启动采集线程
        """
        with self._state_lock:
            if self._is_running:
                return
            self._reset_runtime_state()

        camera_id = self._start_camera_video_capture()
        acquisition_thread = threading.Thread(
            target=self._acquisition_loop,
            name="zwo-asi-camera-stream",
            args=(camera_id,),
            daemon=True,
        )

        with self._state_lock:
            self._camera_id = camera_id
            self._is_running = True
            self._acquisition_thread = acquisition_thread
            self._stop_event.clear()

        acquisition_thread.start()

    def stop(self) -> None:
        """
        停止采集并释放资源
        """
        with self._state_lock:
            acquisition_thread = self._acquisition_thread
            camera_id = self._camera_id
            self._is_running = False
            self._stop_event.set()

        if (
            acquisition_thread is not None
            and acquisition_thread is not threading.current_thread()
        ):
            acquisition_thread.join(timeout=self.stop_timeout_seconds)
            if acquisition_thread.is_alive():
                with self._state_lock:
                    self._last_error = RuntimeError(
                        "camera acquisition thread did not stop in time",
                    )

        if camera_id is not None:
            self._refresh_sdk_dropped_frame_count(camera_id)
            self._api.stop_video_capture(camera_id)
            self._api.close_camera(camera_id)

        with self._state_lock:
            self._camera_id = None
            self._acquisition_thread = None
        with self._frame_lock:
            self._latest_frame = None
        self._drain_frame_queue()

    def get_latest_frame(self) -> CameraFrame | None:
        """
        返回最新帧副本
        """
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return _copy_camera_frame(self._latest_frame)

    def get_frame(self, timeout: float | None = None) -> CameraFrame | None:
        """
        读取一个输出帧

        参数:
            timeout: 队列等待超时时间，单位为秒；None 表示一直等待

        返回:
            下一帧 CameraFrame；等待超时时返回 None
        """
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_statistics(self) -> ZWOASICameraStreamStatistics:
        """
        返回运行统计快照
        """
        with self._state_lock:
            camera_id = self._camera_id
        if camera_id is not None:
            self._refresh_sdk_dropped_frame_count(camera_id)

        with self._state_lock:
            return ZWOASICameraStreamStatistics(
                captured_frame_count=self._captured_frame_count,
                output_frame_count=self._output_frame_count,
                dropped_frame_count=self._dropped_frame_count,
                sdk_dropped_frame_count=self._sdk_dropped_frame_count,
                last_status=self._last_status,
                is_running=self._is_running,
            )

    def get_last_error(self) -> Exception | None:
        """
        返回最后采集错误
        """
        with self._state_lock:
            return self._last_error

    def is_running(self) -> bool:
        """
        返回采集是否运行
        """
        with self._state_lock:
            return self._is_running

    def __enter__(self) -> ZWOASICameraStream:
        """
        进入上下文时启动采集
        """
        self.start()
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: TracebackType | None,
    ) -> None:
        """
        离开上下文时停止采集

        参数:
            exception_type:      托管代码块抛出的异常类型
            exception_value:     托管代码块抛出的异常值
            exception_traceback: 托管代码块抛出的异常回溯
        """
        self.stop()

    def _start_camera_video_capture(self) -> int:
        camera_info = self._api.get_camera_info(self.camera_index)
        if camera_info is None:
            message = "failed to read camera information"
            raise RuntimeError(message)

        _validate_roi_against_camera(
            width=self.width,
            height=self.height,
            max_width=camera_info.max_width,
            max_height=camera_info.max_height,
        )

        camera_id = int(camera_info.camera_id)
        has_opened_camera = False
        has_started_video_capture = False
        try:
            self._raise_on_status(self._api.open_camera(camera_id), "open camera")
            has_opened_camera = True
            self._raise_on_status(
                self._api.initialize_camera(camera_id),
                "initialize camera",
            )
            self._raise_on_status(
                self._api.set_roi_format(
                    camera_id,
                    self.width,
                    self.height,
                    1,
                    ASI_IMG_RAW8,
                ),
                "set RAW8 ROI",
            )
            self._raise_on_status(
                self._api.start_video_capture(camera_id),
                "start video capture",
            )
            has_started_video_capture = True
            return camera_id
        except Exception:
            if has_started_video_capture:
                self._api.stop_video_capture(camera_id)
            if has_opened_camera:
                self._api.close_camera(camera_id)
            raise

    def _acquisition_loop(self, camera_id: int) -> None:
        try:
            while not self._stop_event.is_set():
                status, frame = self._api.capture_raw8_frame(
                    camera_id=camera_id,
                    width=self.width,
                    height=self.height,
                    timeout_ms=self.timeout_ms,
                )
                with self._state_lock:
                    self._last_status = status

                if status != self._api.STATUS_SUCCESS or frame is None:
                    continue

                with self._state_lock:
                    self._captured_frame_count += 1

                if self._should_publish_frame():
                    self._publish_frame(frame)
        except Exception as error:
            with self._state_lock:
                self._last_error = error
                self._is_running = False
            self._stop_event.set()

    def _should_publish_frame(self) -> bool:
        if self.target_output_fps is None:
            return True

        output_interval = 1.0 / self.target_output_fps
        current_time = time.monotonic()
        if self._last_output_time == 0.0:
            self._last_output_time = current_time
            return True
        if current_time - self._last_output_time >= output_interval:
            self._last_output_time = current_time
            return True
        return False

    def _publish_frame(self, frame: CameraFrame) -> None:
        latest_frame = _copy_camera_frame(frame)
        with self._frame_lock:
            self._latest_frame = latest_frame

        with self._state_lock:
            self._output_frame_count += 1

        queued_frame = _copy_camera_frame(frame)
        try:
            if self.drop_oldest_frame and self._frame_queue.full():
                self._discard_oldest_frame()
            self._frame_queue.put_nowait(queued_frame)
        except queue.Full:
            with self._state_lock:
                self._dropped_frame_count += 1

    def _discard_oldest_frame(self) -> None:
        try:
            self._frame_queue.get_nowait()
        except queue.Empty:
            return
        with self._state_lock:
            self._dropped_frame_count += 1

    def _drain_frame_queue(self) -> None:
        while True:
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                break

    def _refresh_sdk_dropped_frame_count(self, camera_id: int) -> None:
        try:
            sdk_dropped_frame_count = self._api.get_dropped_frames(camera_id)
        except Exception as error:
            with self._state_lock:
                self._last_error = error
            return

        with self._state_lock:
            self._sdk_dropped_frame_count = sdk_dropped_frame_count

    def _raise_on_status(self, status: int, operation_name: str) -> None:
        if status != self._api.STATUS_SUCCESS:
            message = "%s failed: status=%s" % (operation_name, status)
            raise RuntimeError(message)

    def _reset_runtime_state(self) -> None:
        self._stop_event.set()
        self._camera_id = None
        self._acquisition_thread = None
        self._is_running = False
        self._captured_frame_count = 0
        self._output_frame_count = 0
        self._dropped_frame_count = 0
        self._sdk_dropped_frame_count = None
        self._last_status = None
        self._last_error = None
        self._last_output_time = 0.0
        with self._frame_lock:
            self._latest_frame = None
        self._drain_frame_queue()


def _copy_camera_frame(frame: CameraFrame) -> CameraFrame:
    return CameraFrame(
        data=frame.data.copy(),
        width=frame.width,
        height=frame.height,
        image_type=frame.image_type,
    )


def _validate_stream_configuration(
    *,
    camera_index: int,
    width: int,
    height: int,
    frame_queue_size: int,
    timeout_ms: int,
    target_output_fps: float | None,
    stop_timeout_seconds: float,
) -> None:
    if int(camera_index) < 0:
        message = "camera_index must be non-negative"
        raise ValueError(message)
    if int(width) <= 0 or int(width) > ASI585MM_FULL_WIDTH:
        message = "width must be in range 1..%d" % ASI585MM_FULL_WIDTH
        raise ValueError(message)
    if int(height) <= 0 or int(height) > ASI585MM_FULL_HEIGHT:
        message = "height must be in range 1..%d" % ASI585MM_FULL_HEIGHT
        raise ValueError(message)
    if int(frame_queue_size) <= 0:
        message = "frame_queue_size must be positive"
        raise ValueError(message)
    if int(timeout_ms) <= 0:
        message = "timeout_ms must be positive"
        raise ValueError(message)
    if target_output_fps is not None:
        target_output_fps_value = float(target_output_fps)
        if (
            not math.isfinite(target_output_fps_value)
            or target_output_fps_value <= 0.0
        ):
            message = "target_output_fps must be positive finite or None"
            raise ValueError(message)

    stop_timeout_seconds_value = float(stop_timeout_seconds)
    if (
        not math.isfinite(stop_timeout_seconds_value)
        or stop_timeout_seconds_value <= 0.0
    ):
        message = "stop_timeout_seconds must be positive finite"
        raise ValueError(message)


def _validate_roi_against_camera(
    *,
    width: int,
    height: int,
    max_width: int,
    max_height: int,
) -> None:
    if int(width) > int(max_width):
        message = "width exceeds camera maximum width"
        raise ValueError(message)
    if int(height) > int(max_height):
        message = "height exceeds camera maximum height"
        raise ValueError(message)


__all__ = [
    "ASI585MM_FULL_HEIGHT",
    "ASI585MM_FULL_WIDTH",
    "DEFAULT_FRAME_QUEUE_SIZE",
    "DEFAULT_TARGET_OUTPUT_FPS",
    "DEFAULT_TIMEOUT_MS",
    "ZWOASICameraStream",
    "ZWOASICameraStreamStatistics",
]
