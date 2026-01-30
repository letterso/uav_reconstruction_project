from __future__ import annotations

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


def _iter_frames_av(video_path: Path, target_fps: float) -> Generator[FrameItem, None, None]:
    container = av.open(str(video_path))
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"
    last_sample_time = None
    frame_idx = 0

    for frame in container.decode(video=0):
        timestamp = frame.time
        if timestamp is None and frame.pts is not None and stream.time_base is not None:
            timestamp = float(frame.pts * stream.time_base)
        if timestamp is None:
            timestamp = frame_idx / max(target_fps, 1e-6)

        if last_sample_time is None or (timestamp - last_sample_time) >= 1.0 / target_fps:
            last_sample_time = timestamp
            image = frame.to_ndarray(format="bgr24")
            yield frame_idx, timestamp, image
        frame_idx += 1

    container.close()


def _iter_frames_cv2(
    video_path: Path,
    target_fps: float,
    fallback_fps: float,
) -> Generator[FrameItem, None, None]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    if not source_fps or source_fps <= 0:
        source_fps = fallback_fps

    frame_idx = 0
    last_sample_time = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if timestamp <= 0:
            timestamp = frame_idx / source_fps

        if last_sample_time is None or (timestamp - last_sample_time) >= 1.0 / target_fps:
            last_sample_time = timestamp
            yield frame_idx, timestamp, frame
        frame_idx += 1

    cap.release()


def iter_video_frames(
    video_path: str | Path,
    target_fps: float,
    fallback_fps: float,
) -> Generator[FrameItem, None, None]:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if _HAS_AV:
        yield from _iter_frames_av(video_path, target_fps)
    else:
        yield from _iter_frames_cv2(video_path, target_fps, fallback_fps)
