from __future__ import annotations

import cv2
import numpy as np


def laplacian_variance(gray: np.ndarray) -> float:
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap.var())


def is_blurry(gray: np.ndarray, threshold: float) -> tuple[bool, float]:
    score = laplacian_variance(gray)
    return score < threshold, score
