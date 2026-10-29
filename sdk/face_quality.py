"""Face-tracking and ROI stability assessment."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

from sdk.config import FaceTrackingConfig
from sdk.quality_types import (
    ABRUPT_LANDMARK_DISPLACEMENT,
    FACE_NOT_DETECTED,
    FACE_TRACKING_LOST,
    INVALID_ROI,
    UNSTABLE_ROI,
    FaceTrackStatus,
)
from sdk.roi_extractor import ROIExtractor

Point = Tuple[float, float]


def _face_size(landmarks: Sequence[Point]) -> float:
    xs = np.array([p[0] for p in landmarks], dtype=np.float64)
    ys = np.array([p[1] for p in landmarks], dtype=np.float64)
    return float(np.hypot(xs.max() - xs.min(), ys.max() - ys.min()))


def _roi_centroid(
    landmarks: Sequence[Point],
    indices: Sequence[int],
) -> Optional[np.ndarray]:
    pts = [landmarks[i] for i in indices if i < len(landmarks)]
    if len(pts) < 3:
        return None
    return np.mean(np.asarray(pts, dtype=np.float64), axis=0)


class FaceTrackingAssessor:
    """Assess face presence, landmark completeness, and ROI stability."""

    def __init__(self, config: Optional[FaceTrackingConfig] = None):
        self.config = config or FaceTrackingConfig()
        self._had_face = False
        self._prev_centroids: Optional[list[np.ndarray]] = None
        self._roi = ROIExtractor()

    def reset(self) -> None:
        self._had_face = False
        self._prev_centroids = None

    def assess(
        self,
        landmarks: Optional[Sequence[Point]],
        rgb_mean: Optional[np.ndarray],
    ) -> tuple[FaceTrackStatus, list[str], list[str]]:
        """Return (status, warnings, rejection_reasons)."""
        warnings: list[str] = []
        rejects: list[str] = []

        if landmarks is None:
            if self._had_face:
                rejects.append(FACE_TRACKING_LOST)
                return FaceTrackStatus.LOST, warnings, rejects
            rejects.append(FACE_NOT_DETECTED)
            return FaceTrackStatus.NOT_DETECTED, warnings, rejects

        self._had_face = True
        if len(landmarks) < self.config.min_landmarks:
            rejects.append(INVALID_ROI)
            return FaceTrackStatus.INVALID_ROI, warnings, rejects

        if rgb_mean is None:
            rejects.append(INVALID_ROI)
            return FaceTrackStatus.INVALID_ROI, warnings, rejects

        status, extra_w, extra_r = self._check_roi_stability(landmarks)
        warnings.extend(extra_w)
        rejects.extend(extra_r)
        return status, warnings, rejects

    def _check_roi_stability(
        self,
        landmarks: Sequence[Point],
    ) -> tuple[FaceTrackStatus, list[str], list[str]]:
        warnings: list[str] = []
        rejects: list[str] = []
        size = max(_face_size(landmarks), 1.0)
        centroids: list[np.ndarray] = []
        for indices in (
            self._roi._region_map["forehead"],
            self._roi._region_map["left_cheek"],
            self._roi._region_map["right_cheek"],
        ):
            c = _roi_centroid(landmarks, indices)
            if c is None:
                rejects.append(INVALID_ROI)
                return FaceTrackStatus.INVALID_ROI, warnings, rejects
            centroids.append(c)

        if self._prev_centroids is not None:
            jumps = [
                float(np.linalg.norm(a - b)) / size
                for a, b in zip(centroids, self._prev_centroids)
            ]
            max_jump = max(jumps) if jumps else 0.0
            # Warn on moderate jumps; only hard-reject on extreme discontinuities
            # so sparse/low-FPS webcam frames do not constantly reset warm-up.
            hard_jump = self.config.max_roi_center_jump * 1.35
            if max_jump >= hard_jump:
                warnings.append(UNSTABLE_ROI)
                rejects.append(ABRUPT_LANDMARK_DISPLACEMENT)
                self._prev_centroids = centroids
                return FaceTrackStatus.DISCONTINUITY, warnings, rejects
            if max_jump >= self.config.max_roi_center_jump * 0.5:
                warnings.append(UNSTABLE_ROI)
                self._prev_centroids = centroids
                return FaceTrackStatus.UNSTABLE, warnings, rejects

        self._prev_centroids = centroids
        return FaceTrackStatus.OK, warnings, rejects
