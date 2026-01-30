from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Tuple

import cv2
import numpy as np
from skimage.metrics import structural_similarity
from tqdm import tqdm

from .blur_filter import is_blurry
from .parallax_filter import FeatureExtractor, evaluate_parallax
from .video_io import iter_video_frames


logger = logging.getLogger(__name__)


class SamplingStats:
    def __init__(self):
        self.total = 0
        self.kept = 0
        self.rejected_blur = 0
        self.rejected_parallax = 0
        self.rejected_matches = 0
        self.rejected_ssim = 0

    def summary(self) -> Dict[str, int]:
        return {
            "total": self.total,
            "kept": self.kept,
            "rejected_blur": self.rejected_blur,
            "rejected_parallax": self.rejected_parallax,
            "rejected_matches": self.rejected_matches,
            "rejected_ssim": self.rejected_ssim,
        }


def _compute_ssim(gray_ref: np.ndarray, gray_cur: np.ndarray) -> float:
    data_range = float(gray_cur.max() - gray_cur.min())
    if data_range <= 0:
        data_range = 1.0
    return float(
        structural_similarity(
            gray_ref,
            gray_cur,
            data_range=data_range,
        )
    )


def sample_video(
    video_path: str | Path,
    output_dir: str | Path,
    config: Dict,
) -> Tuple[SamplingStats, Path]:
    sampling_cfg = config["sampling"]
    feature_cfg = config["features"]
    quality_cfg = config.get("quality", {})

    target_fps = float(sampling_cfg["initial_fps"])
    blur_threshold = float(sampling_cfg["blur_threshold"])
    parallax_threshold = float(sampling_cfg["parallax_threshold_px"])
    fallback_fps = float(sampling_cfg["fallback_fps"])
    start_time = sampling_cfg.get("start_time")
    end_time = sampling_cfg.get("end_time")
    min_matches = int(feature_cfg["min_matches"])

    use_ssim = bool(quality_cfg.get("use_ssim", False))
    ssim_max = float(quality_cfg.get("ssim_max", 0.98))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    extractor = FeatureExtractor(
        feature_type=feature_cfg["type"],
        max_features=int(feature_cfg["max_features"]),
    )

    stats = SamplingStats()
    last_kept_gray = None

    frame_iter = iter_video_frames(
        video_path,
        target_fps,
        fallback_fps,
        start_time=start_time,
        end_time=end_time,
    )
    for frame_idx, timestamp, frame in tqdm(frame_iter, desc="Sampling frames"):
        stats.total += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        is_blur, blur_score = is_blurry(gray, blur_threshold)
        if is_blur:
            stats.rejected_blur += 1
            logger.info(
                "Reject frame %s at %.3fs: blur=%.2f < %.2f",
                frame_idx,
                timestamp,
                blur_score,
                blur_threshold,
            )
            continue

        if last_kept_gray is not None:
            if use_ssim:
                ssim_score = _compute_ssim(last_kept_gray, gray)
                if ssim_score > ssim_max:
                    stats.rejected_ssim += 1
                    logger.info(
                        "Reject frame %s at %.3fs: ssim=%.4f > %.4f",
                        frame_idx,
                        timestamp,
                        ssim_score,
                        ssim_max,
                    )
                    continue

            match_count, mean_disp = evaluate_parallax(extractor, last_kept_gray, gray)
            if match_count < min_matches:
                stats.rejected_matches += 1
                logger.info(
                    "Reject frame %s at %.3fs: matches=%d < %d",
                    frame_idx,
                    timestamp,
                    match_count,
                    min_matches,
                )
                continue

            if mean_disp < parallax_threshold:
                stats.rejected_parallax += 1
                logger.info(
                    "Reject frame %s at %.3fs: parallax=%.2f < %.2f",
                    frame_idx,
                    timestamp,
                    mean_disp,
                    parallax_threshold,
                )
                continue

        output_path = output_dir / f"frame_{stats.kept:06d}.png"
        cv2.imwrite(str(output_path), frame)
        stats.kept += 1
        last_kept_gray = gray

        logger.info(
            "Keep frame %s at %.3fs -> %s",
            frame_idx,
            timestamp,
            output_path,
        )

    if stats.kept == 0:
        logger.warning("No frames were kept. Check thresholds or input quality.")

    return stats, output_dir
