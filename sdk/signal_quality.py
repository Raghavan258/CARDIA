"""Signal-quality aggregator: face, motion, lighting, and pulse checks.

Hard rejection rules are evaluated separately from the optional composite
overall_score. Callers must not publish a new accepted HR when
``allow_new_hr_estimate`` is False.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

from sdk.config import QualityConfig
from sdk.face_quality import FaceTrackingAssessor
from sdk.lighting import LightingAssessor
from sdk.motion import MotionEstimator
from sdk.pulse_quality import PulseQualityAssessor
from sdk.quality_types import (
    EXCESSIVE_MOTION,
    FaceTrackStatus,
    MotionCategory,
    QualityCategory,
    QualityResult,
)

Point = Tuple[float, float]


class SignalQualityAssessor:
    """Compose per-frame quality assessment for the rPPG pipeline."""

    def __init__(self, config: Optional[QualityConfig] = None):
        self.config = config or QualityConfig()
        self.face = FaceTrackingAssessor(self.config.face)
        self.motion = MotionEstimator(self.config.motion)
        self.lighting = LightingAssessor(self.config.lighting)
        self.pulse = PulseQualityAssessor(self.config.pulse)

    def reset(self) -> None:
        self.face.reset()
        self.motion.reset()
        self.lighting.reset()
        self.pulse.reset()

    def assess_frame(
        self,
        frame_bgr: Optional[np.ndarray],
        landmarks: Optional[Sequence[Point]],
        rgb_mean: Optional[np.ndarray],
        timestamp_s: float,
        pulse: Optional[np.ndarray] = None,
        timestamps_s: Optional[Sequence[float]] = None,
        buffer_frames: int = 0,
        fps_fallback: float = 30.0,
        candidate_hr: Optional[float] = None,
        initializing: bool = False,
    ) -> QualityResult:
        """Assess quality for the current frame / buffer state."""
        result = QualityResult()
        warnings: list[str] = []
        rejects: list[str] = []

        face_status, fw, fr = self.face.assess(landmarks, rgb_mean)
        result.face_status = face_status
        warnings.extend(fw)
        rejects.extend(fr)

        motion_score, motion_cat, motion_reject, mr = self.motion.update(
            landmarks, timestamp_s
        )
        result.motion_score = motion_score
        result.motion_category = motion_cat
        warnings.extend(mr)
        if motion_reject:
            rejects.extend(mr if mr else [EXCESSIVE_MOTION])

        if frame_bgr is not None and landmarks is not None:
            lighting, lw, lr = self.lighting.assess(frame_bgr, landmarks)
            result.lighting = lighting
            warnings.extend(lw)
            rejects.extend(lr)

        pulse_metrics, pw, pr, pulse_score = self.pulse.assess(
            pulse=pulse,
            timestamps_s=timestamps_s,
            buffer_frames=buffer_frames,
            fps_fallback=fps_fallback,
            candidate_hr=candidate_hr,
        )
        result.pulse = pulse_metrics
        warnings.extend(pw)
        rejects.extend(pr)

        # Deduplicate while preserving order
        result.warnings = list(dict.fromkeys(warnings))
        result.rejection_reasons = list(dict.fromkeys(rejects))

        result.overall_score = self._overall_score(
            face_status, motion_cat, pulse_score, result.lighting.status.value
        )
        result.category = self._category(
            initializing=initializing,
            rejects=result.rejection_reasons,
            score=result.overall_score,
        )
        # Hard rejects always block; score alone never overrides a reject.
        # UNSTABLE face is a warning state and may still publish HR.
        face_ok = face_status in (FaceTrackStatus.OK, FaceTrackStatus.UNSTABLE)
        result.allow_new_hr_estimate = (
            not initializing
            and len(result.rejection_reasons) == 0
            and face_ok
            and motion_cat != MotionCategory.HIGH
        )
        return result

    def note_accepted_hr(self, hr: Optional[float]) -> None:
        self.pulse.note_accepted_hr(hr)

    def _overall_score(
        self,
        face_status: FaceTrackStatus,
        motion_cat: MotionCategory,
        pulse_score: float,
        lighting_status: str,
    ) -> float:
        face_s = 1.0 if face_status == FaceTrackStatus.OK else 0.0
        if face_status == FaceTrackStatus.UNSTABLE:
            face_s = 0.5
        motion_s = {
            MotionCategory.LOW: 1.0,
            MotionCategory.MODERATE: 0.55,
            MotionCategory.HIGH: 0.1,
            MotionCategory.UNKNOWN: 0.3,
        }[motion_cat]
        light_s = 1.0 if lighting_status == "ok" else 0.25
        # Equal contribution across subsystems; documented, not opaque magic.
        return float(0.25 * face_s + 0.25 * motion_s + 0.25 * light_s + 0.25 * pulse_score)

    def _category(
        self,
        initializing: bool,
        rejects: list[str],
        score: Optional[float],
    ) -> QualityCategory:
        if initializing:
            return QualityCategory.INITIALIZING
        if rejects or score is None:
            return QualityCategory.POOR
        if score >= self.config.good_score_min:
            return QualityCategory.GOOD
        if score >= self.config.fair_score_min:
            return QualityCategory.FAIR
        return QualityCategory.POOR
