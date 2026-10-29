"""Face-landmark motion estimation with size normalization and timestamps."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

from sdk.config import MotionConfig
from sdk.quality_types import (
    ABRUPT_LANDMARK_DISPLACEMENT,
    EXCESSIVE_MOTION,
    MotionCategory,
)

Point = Tuple[float, float]


def _face_diagonal(landmarks: Sequence[Point]) -> float:
    xs = np.array([p[0] for p in landmarks], dtype=np.float64)
    ys = np.array([p[1] for p in landmarks], dtype=np.float64)
    return float(np.hypot(xs.max() - xs.min(), ys.max() - ys.min()))


def _mean_displacement(prev: Sequence[Point], curr: Sequence[Point]) -> float:
    n = min(len(prev), len(curr))
    if n == 0:
        return 0.0
    p = np.asarray(prev[:n], dtype=np.float64)
    c = np.asarray(curr[:n], dtype=np.float64)
    return float(np.mean(np.linalg.norm(c - p, axis=1)))


class MotionEstimator:
    """Estimate head/face motion from consecutive landmark sets."""

    def __init__(self, config: Optional[MotionConfig] = None):
        self.config = config or MotionConfig()
        self._prev_landmarks: Optional[list[Point]] = None
        self._prev_ts: Optional[float] = None
        self._ema_score: Optional[float] = None

    def reset(self) -> None:
        self._prev_landmarks = None
        self._prev_ts = None
        self._ema_score = None

    def update(
        self,
        landmarks: Optional[Sequence[Point]],
        timestamp_s: float,
    ) -> tuple[Optional[float], MotionCategory, bool, list[str]]:
        """Update motion state.

        Returns:
            (smoothed_score, category, reject, reasons)
            score is normalized displacement per second (face-size units / s).
        """
        if landmarks is None or len(landmarks) < 3:
            self._prev_landmarks = None
            self._prev_ts = timestamp_s
            return self._ema_score, MotionCategory.UNKNOWN, False, []

        curr = [(float(x), float(y)) for x, y in landmarks]
        if self._prev_landmarks is None or self._prev_ts is None:
            self._prev_landmarks = curr
            self._prev_ts = timestamp_s
            self._ema_score = 0.0
            return 0.0, MotionCategory.LOW, False, []

        dt = max(timestamp_s - self._prev_ts, 1e-6)
        diag = max(_face_diagonal(curr), 1.0)
        raw = _mean_displacement(self._prev_landmarks, curr) / diag
        rate = raw / dt
        reasons: list[str] = []

        # Use rate-based abrupt detection so sparse low-FPS frames with normal
        # head motion are not treated as discontinuities.
        abrupt = rate >= self.config.abrupt_rate and raw >= self.config.abrupt_jump
        if abrupt:
            reasons.append(ABRUPT_LANDMARK_DISPLACEMENT)

        alpha = self.config.ema_alpha
        if self._ema_score is None:
            self._ema_score = rate
        else:
            self._ema_score = alpha * rate + (1.0 - alpha) * self._ema_score

        category = self._categorize(self._ema_score)
        reject = self._ema_score > self.config.reject_above or abrupt
        if self._ema_score > self.config.reject_above:
            reasons.append(EXCESSIVE_MOTION)

        self._prev_landmarks = curr
        self._prev_ts = timestamp_s
        return self._ema_score, category, reject, reasons

    def _categorize(self, score: float) -> MotionCategory:
        if score <= self.config.low_max:
            return MotionCategory.LOW
        if score <= self.config.moderate_max:
            return MotionCategory.MODERATE
        return MotionCategory.HIGH
