"""Typed contracts for signal-quality assessment results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class QualityCategory(str, Enum):
    INITIALIZING = "initializing"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class FaceTrackStatus(str, Enum):
    OK = "ok"
    NOT_DETECTED = "not_detected"
    LOST = "lost"
    INVALID_ROI = "invalid_roi"
    UNSTABLE = "unstable"
    DISCONTINUITY = "discontinuity"


class MotionCategory(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class LightingStatus(str, Enum):
    OK = "ok"
    UNDEREXPOSED = "underexposed"
    OVEREXPOSED = "overexposed"
    UNSTABLE = "unstable"
    UNKNOWN = "unknown"


# Stable rejection / warning reason codes for API and UI.
FACE_NOT_DETECTED = "FACE_NOT_DETECTED"
FACE_TRACKING_LOST = "FACE_TRACKING_LOST"
INVALID_ROI = "INVALID_ROI"
ABRUPT_LANDMARK_DISPLACEMENT = "ABRUPT_LANDMARK_DISPLACEMENT"
UNSTABLE_ROI = "UNSTABLE_ROI"
EXCESSIVE_MOTION = "EXCESSIVE_MOTION"
POOR_LIGHTING = "POOR_LIGHTING"
ABRUPT_ILLUMINATION_CHANGE = "ABRUPT_ILLUMINATION_CHANGE"
INSUFFICIENT_SIGNAL_DURATION = "INSUFFICIENT_SIGNAL_DURATION"
IRREGULAR_SAMPLING = "IRREGULAR_SAMPLING"
WEAK_PULSE_AMPLITUDE = "WEAK_PULSE_AMPLITUDE"
UNSTABLE_PULSE_SIGNAL = "UNSTABLE_PULSE_SIGNAL"
IMPLAUSIBLE_HEART_RATE = "IMPLAUSIBLE_HEART_RATE"


@dataclass
class LightingStats:
    mean_brightness: Optional[float] = None
    median_brightness: Optional[float] = None
    underexposed_fraction: Optional[float] = None
    overexposed_fraction: Optional[float] = None
    brightness_delta: Optional[float] = None
    roi_brightness_spread: Optional[float] = None
    status: LightingStatus = LightingStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class PulseQualityMetrics:
    buffer_frames: int = 0
    buffer_duration_s: Optional[float] = None
    effective_fps: Optional[float] = None
    max_timestamp_gap_s: Optional[float] = None
    pulse_std: Optional[float] = None
    spectral_prominence_ratio: Optional[float] = None
    dominant_bpm: Optional[float] = None
    hr_delta: Optional[float] = None
    duration_ok: bool = False
    amplitude_ok: bool = False
    spectral_ok: bool = False
    hr_consistency_ok: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualityResult:
    """Structured quality output contract for one processed frame."""

    category: QualityCategory = QualityCategory.INITIALIZING
    overall_score: Optional[float] = None
    face_status: FaceTrackStatus = FaceTrackStatus.NOT_DETECTED
    motion_score: Optional[float] = None
    motion_category: MotionCategory = MotionCategory.UNKNOWN
    lighting: LightingStats = field(default_factory=LightingStats)
    pulse: PulseQualityMetrics = field(default_factory=PulseQualityMetrics)
    warnings: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    allow_new_hr_estimate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "overall_score": self.overall_score,
            "face_status": self.face_status.value,
            "motion_score": self.motion_score,
            "motion_category": self.motion_category.value,
            "lighting": self.lighting.to_dict(),
            "pulse": self.pulse.to_dict(),
            "warnings": list(self.warnings),
            "rejection_reasons": list(self.rejection_reasons),
            "allow_new_hr_estimate": self.allow_new_hr_estimate,
        }
