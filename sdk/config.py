"""Configuration-driven thresholds for CARDIA signal-quality assessment.

Rationale for defaults is documented per field. Values are starting points for
Milestone B and should be tuned on held-out recordings in later milestones.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MotionConfig:
    """Landmark-normalized motion thresholds.

    Displacement is mean landmark shift divided by face diagonal, then divided
    by dt (seconds) to yield a rate. Categories are ordered low < moderate < high.
    """

    low_max: float = 0.15
    """Normalized motion rate at or below this is ``low`` (stable for rPPG)."""

    moderate_max: float = 0.45
    """Above ``low_max`` and at or below this is ``moderate`` (fair quality)."""

    reject_above: float = 0.90
    """Above this rate, samples are rejected as ``EXCESSIVE_MOTION``."""

    abrupt_jump: float = 0.25
    """Legacy absolute jump threshold; abruptness is primarily rate-based."""

    abrupt_rate: float = 1.2
    """Normalized displacement per second treated as an abrupt spike."""

    ema_alpha: float = 0.35
    """EMA smoothing for displayed/reported motion score."""


@dataclass(frozen=True)
class LightingConfig:
    """ROI / frame luminance checks (OpenCV BGR grayscale 0–255)."""

    underexposed_max_mean: float = 40.0
    """Mean luminance at or below this → underexposed warning / reject."""

    overexposed_min_mean: float = 220.0
    """Mean luminance at or above this → overexposed warning / reject."""

    underexposed_pixel_frac: float = 0.35
    """Fraction of ROI pixels below ``dark_pixel`` triggering underexposure."""

    overexposed_pixel_frac: float = 0.25
    """Fraction of ROI pixels above ``bright_pixel`` triggering overexposure."""

    dark_pixel: int = 25
    bright_pixel: int = 245

    abrupt_delta: float = 35.0
    """Absolute mean-luminance jump vs previous frame → lighting instability."""

    reject_on_poor: bool = True
    """If True, poor lighting blocks new accepted HR estimates."""


@dataclass(frozen=True)
class FaceTrackingConfig:
    """Face / ROI tracking quality gates."""

    min_landmarks: int = 400
    """MediaPipe FaceLandmarker returns 478; require most of them."""

    max_no_face_seconds: float = 1.0
    """Reset buffers after continuous face loss exceeding this duration."""

    max_roi_center_jump: float = 0.55
    """Normalized ROI-centroid jump (vs face size) marking unstable ROIs.

    Higher than a single-frame webcam threshold because live web sessions often
    sample below 10 FPS; absolute jumps look larger between sparse frames.
    """


@dataclass(frozen=True)
class PulseQualityConfig:
    """Pulse-signal diagnostics used for gating (metrics kept separate).

    Score weights below are documented explicitly so they are not opaque.
    Mandatory rejection rules do not rely on the composite score alone.
    """

    min_frames: int = 64
    min_duration_s: float = 2.0
    """Soft duration target once min_frames is met (warning only if shorter)."""

    min_effective_fps: float = 5.0
    """Warn when median FPS drops below this (web sessions are often 5–12 FPS)."""

    max_timestamp_gap_s: float = 1.5
    """Latest inter-frame gap above this → irregular-sampling warning."""

    reject_timestamp_gap_s: float = 3.0
    """Latest gap above this hard-rejects (tracking hole), without buffer clear."""

    min_pulse_std: float = 0.05
    """Normalized pulse std below this → weak / flat signal."""

    min_peak_prominence_ratio: float = 1.5
    """Peak PSD / median PSD in cardiac band; below → weak spectral peak."""

    min_bpm: float = 45.0
    max_bpm: float = 180.0

    max_hr_delta: float = 25.0
    """Consecutive accepted HR change above this → unstable estimate."""

    # Composite score weights (sum = 1.0). Exposed for debugging; rejection
    # still uses hard rules in SignalQualityAssessor.
    weight_duration: float = 0.20
    weight_amplitude: float = 0.25
    weight_spectral: float = 0.30
    weight_hr_consistency: float = 0.25


@dataclass(frozen=True)
class QualityConfig:
    """Top-level quality configuration bundle."""

    motion: MotionConfig = field(default_factory=MotionConfig)
    lighting: LightingConfig = field(default_factory=LightingConfig)
    face: FaceTrackingConfig = field(default_factory=FaceTrackingConfig)
    pulse: PulseQualityConfig = field(default_factory=PulseQualityConfig)

    fair_score_min: float = 0.45
    good_score_min: float = 0.70
    """Overall score thresholds for fair/good categories when no hard reject."""
