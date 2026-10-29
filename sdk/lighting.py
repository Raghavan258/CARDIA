"""Frame / ROI lighting assessment for rPPG quality gating."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import cv2
import numpy as np

from sdk.config import LightingConfig
from sdk.quality_types import (
    ABRUPT_ILLUMINATION_CHANGE,
    POOR_LIGHTING,
    LightingStats,
    LightingStatus,
)

Point = Tuple[float, float]


def _roi_gray_pixels(
    frame_bgr: np.ndarray,
    landmarks: Sequence[Point],
    indices: Sequence[int],
) -> Optional[np.ndarray]:
    h, w = frame_bgr.shape[:2]
    pts = np.array(
        [landmarks[i] for i in indices if i < len(landmarks)],
        dtype=np.int32,
    )
    if len(pts) < 3:
        return None
    mask = np.zeros((h, w), dtype=np.uint8)
    hull = cv2.convexHull(pts)
    cv2.fillConvexPoly(mask, hull, 255)
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    pixels = gray[mask == 255]
    return pixels if len(pixels) else None


# Same landmark sets as ROIExtractor (forehead / cheeks).
_FOREHEAD = [10, 67, 69, 104, 108, 109, 151, 299, 297, 337, 338, 333, 332, 334]
_LEFT_CHEEK = [36, 205, 206, 207, 187, 123, 116, 117, 118, 119, 100, 126]
_RIGHT_CHEEK = [266, 425, 426, 427, 411, 352, 345, 346, 347, 348, 329, 355]


class LightingAssessor:
    """Compute luminance statistics and lighting status flags."""

    def __init__(self, config: Optional[LightingConfig] = None):
        self.config = config or LightingConfig()
        self._prev_mean: Optional[float] = None

    def reset(self) -> None:
        self._prev_mean = None

    def assess(
        self,
        frame_bgr: np.ndarray,
        landmarks: Optional[Sequence[Point]],
    ) -> tuple[LightingStats, list[str], list[str]]:
        """Return (stats, warnings, rejection_reasons)."""
        stats = LightingStats()
        warnings: list[str] = []
        rejects: list[str] = []

        if landmarks is None:
            return stats, warnings, rejects

        region_means: list[float] = []
        all_pixels: list[np.ndarray] = []
        for indices in (_FOREHEAD, _LEFT_CHEEK, _RIGHT_CHEEK):
            pix = _roi_gray_pixels(frame_bgr, landmarks, indices)
            if pix is None:
                continue
            region_means.append(float(np.mean(pix)))
            all_pixels.append(pix)

        if not all_pixels:
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            all_pixels = [gray.ravel()]
            region_means = [float(np.mean(gray))]

        combined = np.concatenate(all_pixels)
        mean_b = float(np.mean(combined))
        median_b = float(np.median(combined))
        under_frac = float(np.mean(combined < self.config.dark_pixel))
        over_frac = float(np.mean(combined > self.config.bright_pixel))
        spread = (
            float(np.max(region_means) - np.min(region_means))
            if len(region_means) >= 2
            else 0.0
        )

        delta = None
        if self._prev_mean is not None:
            delta = abs(mean_b - self._prev_mean)
        self._prev_mean = mean_b

        status = LightingStatus.OK
        underexposed = (
            mean_b <= self.config.underexposed_max_mean
            or under_frac >= self.config.underexposed_pixel_frac
        )
        overexposed = (
            mean_b >= self.config.overexposed_min_mean
            or over_frac >= self.config.overexposed_pixel_frac
        )
        if underexposed:
            status = LightingStatus.UNDEREXPOSED
            warnings.append(POOR_LIGHTING)
            if self.config.reject_on_poor:
                rejects.append(POOR_LIGHTING)
        elif overexposed:
            status = LightingStatus.OVEREXPOSED
            warnings.append(POOR_LIGHTING)
            if self.config.reject_on_poor:
                rejects.append(POOR_LIGHTING)

        if delta is not None and delta >= self.config.abrupt_delta:
            status = LightingStatus.UNSTABLE
            warnings.append(ABRUPT_ILLUMINATION_CHANGE)
            if self.config.reject_on_poor:
                rejects.append(ABRUPT_ILLUMINATION_CHANGE)

        stats = LightingStats(
            mean_brightness=mean_b,
            median_brightness=median_b,
            underexposed_fraction=under_frac,
            overexposed_fraction=over_frac,
            brightness_delta=delta,
            roi_brightness_spread=spread,
            status=status,
        )
        return stats, warnings, rejects
