from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator, Tuple

import cv2
import numpy as np

try:  # optional
    import av  # type: ignore

    _HAS_AV = True
except Exception:  # pragma: no cover - optional dependency
    av = None
    _HAS_AV = False


FrameItem = Tuple[int, float, np.ndarray]

logger = logging.getLogger(__name__)


def _get_duration_av(video_path: Path) -> float | None:
    if not _HAS_AV:
        return None

    container = av.open(str(video_path))
    try:
        stream = container.streams.video[0]
        if stream.duration is not None and stream.time_base is not None:
            return float(stream.duration * stream.time_base)
        if container.duration is not None:
            return float(container.duration / 1_000_000)
        return None
    finally:
        container.close()


def _get_duration_cv2(video_path: Path, fallback_fps: float) -> float | None:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = fallback_fps
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if not frame_count or frame_count <= 0 or fps <= 0:
            return None
        return float(frame_count / fps)
    finally:
        cap.release()


def get_video_duration(video_path: Path, fallback_fps: float) -> float | None:
    duration = _get_duration_av(video_path)
    if duration is not None:
        return duration
    return _get_duration_cv2(video_path, fallback_fps)


def _normalize_time_range(
    duration: float | None,
    start_time: float | None,
    end_time: float | None,
) -> Tuple[float, float | None]:
    start = 0.0 if start_time is None else float(start_time)
    end = None if end_time is None else float(end_time)

    if start < 0:
        logger.warning("Start time %.3fs < 0, clamped to 0.", start)
        start = 0.0
    if end is not None and end < 0:
        logger.warning("End time %.3fs < 0, clamped to 0.", end)
        end = 0.0

    if duration is not None:
        if start > duration:
            logger.warning(
                "Start time %.3fs exceeds duration %.3fs, clamped.",
                start,
                duration,
            )
            start = duration
        if end is None:
            end = duration
        elif end > duration:
            logger.warning(
                "End time %.3fs exceeds duration %.3fs, clamped.",
                end,
                duration,
            )
            end = duration

    if end is not None and end < start:
        raise ValueError(
            f"End time ({end:.3f}s) must be >= start time ({start:.3f}s)."
        )

    return start, end


def _iter_frames_av(
    video_path: Path,
    target_fps: float,
    start_time: float,
    end_time: float | None,
    only_keyframes: bool,
) -> Generator[FrameItem, None, None]:
    container = av.open(str(video_path))
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"
    last_sample_time = None
    frame_idx = 0

    try:
        for frame in container.decode(video=0):
            timestamp = frame.time
            if timestamp is None and frame.pts is not None and stream.time_base is not None:
                timestamp = float(frame.pts * stream.time_base)
            if timestamp is None:
                timestamp = frame_idx / max(target_fps, 1e-6)

            if only_keyframes and not frame.key_frame:
                frame_idx += 1
                continue

            if timestamp < start_time:
                frame_idx += 1
                continue
            if end_time is not None and timestamp > end_time:
                break

            if last_sample_time is None or (timestamp - last_sample_time) >= 1.0 / target_fps:
                last_sample_time = timestamp
                image = frame.to_ndarray(format="bgr24")
                yield frame_idx, timestamp, image
            frame_idx += 1
    finally:
        container.close()


def _iter_frames_cv2(
    video_path: Path,
    target_fps: float,
    fallback_fps: float,
    start_time: float,
    end_time: float | None,
) -> Generator[FrameItem, None, None]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    if not source_fps or source_fps <= 0:
        source_fps = fallback_fps

    frame_idx = 0
    last_sample_time = None
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if timestamp <= 0:
                timestamp = frame_idx / source_fps

            if timestamp < start_time:
                frame_idx += 1
                continue
            if end_time is not None and timestamp > end_time:
                break

            if last_sample_time is None or (timestamp - last_sample_time) >= 1.0 / target_fps:
                last_sample_time = timestamp
                yield frame_idx, timestamp, frame
            frame_idx += 1
    finally:
        cap.release()


def iter_video_frames(
    video_path: str | Path,
    target_fps: float,
    fallback_fps: float,
    start_time: float | None = None,
    end_time: float | None = None,
    only_keyframes: bool = False,
) -> Generator[FrameItem, None, None]:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    duration = get_video_duration(video_path, fallback_fps)
    start_time, end_time = _normalize_time_range(duration, start_time, end_time)

    if _HAS_AV:
        yield from _iter_frames_av(
            video_path,
            target_fps,
            start_time,
            end_time,
            only_keyframes,
        )
    else:
        if only_keyframes:
            raise RuntimeError(
                "only_keyframes=True requires PyAV backend; OpenCV fallback does not expose keyframe flags."
            )
        yield from _iter_frames_cv2(video_path, target_fps, fallback_fps, start_time, end_time)
