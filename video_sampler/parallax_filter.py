from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np


class FeatureExtractor:
    def __init__(self, feature_type: str, max_features: int):
        self.feature_type = feature_type.upper()
        self.max_features = max_features
        self.detector = self._create_detector()
        self.matcher = self._create_matcher()

    def _create_detector(self):
        if self.feature_type == "ORB":
            return cv2.ORB_create(nfeatures=self.max_features)
        if self.feature_type == "SIFT":
            if not hasattr(cv2, "SIFT_create"):
                raise RuntimeError("SIFT is not available in this OpenCV build")
            return cv2.SIFT_create(nfeatures=self.max_features)
        raise ValueError(f"Unsupported feature type: {self.feature_type}")

    def _create_matcher(self):
        if self.feature_type == "ORB":
            return cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        return cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)

    def detect_and_compute(self, gray: np.ndarray):
        keypoints, descriptors = self.detector.detectAndCompute(gray, None)
        return keypoints, descriptors

    def match(self, desc1: np.ndarray, desc2: np.ndarray):
        return self.matcher.match(desc1, desc2)


def parallax_mean_displacement(
    keypoints_a,
    keypoints_b,
    matches,
) -> float:
    if not matches:
        return 0.0
    displacements = []
    for m in matches:
        pt_a = np.array(keypoints_a[m.queryIdx].pt, dtype=np.float32)
        pt_b = np.array(keypoints_b[m.trainIdx].pt, dtype=np.float32)
        displacements.append(float(np.linalg.norm(pt_a - pt_b)))
    if not displacements:
        return 0.0
    return float(np.mean(displacements))


def evaluate_parallax(
    extractor: FeatureExtractor,
    gray_ref: np.ndarray,
    gray_cur: np.ndarray,
) -> Tuple[int, float]:
    kps_ref, desc_ref = extractor.detect_and_compute(gray_ref)
    kps_cur, desc_cur = extractor.detect_and_compute(gray_cur)

    if desc_ref is None or desc_cur is None:
        return 0, 0.0

    matches = extractor.match(desc_ref, desc_cur)
    mean_disp = parallax_mean_displacement(kps_ref, kps_cur, matches)
    return len(matches), mean_disp
