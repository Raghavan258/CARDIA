"""Aggregator and gating-contract tests."""

from __future__ import annotations

import numpy as np

from helpers import make_pulse, make_timestamps
from sdk.config import MotionConfig, QualityConfig
from sdk.quality_types import (
    EXCESSIVE_MOTION,
    FACE_NOT_DETECTED,
    QualityCategory,
)
from sdk.signal_quality import SignalQualityAssessor


def test_face_missing_blocks_hr(gray_frame):
    assessor = SignalQualityAssessor()
    result = assessor.assess_frame(
        frame_bgr=gray_frame,
        landmarks=None,
        rgb_mean=None,
        timestamp_s=0.0,
        buffer_frames=0,
        initializing=True,
    )
    assert result.allow_new_hr_estimate is False
    assert FACE_NOT_DETECTED in result.rejection_reasons
    assert result.category == QualityCategory.INITIALIZING


def test_excessive_motion_blocks_estimate(face_landmarks, gray_frame):
    cfg = QualityConfig(
        motion=MotionConfig(reject_above=0.05, abrupt_jump=0.05, ema_alpha=1.0)
    )
    assessor = SignalQualityAssessor(cfg)
    rgb = np.array([120.0, 100.0, 80.0])
    assessor.assess_frame(
        gray_frame, face_landmarks, rgb, 0.0,
        pulse=make_pulse(72), timestamps_s=make_timestamps(256),
        buffer_frames=256, candidate_hr=72.0, initializing=False,
    )
    jumped = [(x + 100, y) for x, y in face_landmarks]
    result = assessor.assess_frame(
        gray_frame, jumped, rgb, 0.05,
        pulse=make_pulse(72), timestamps_s=make_timestamps(256),
        buffer_frames=256, candidate_hr=72.0, initializing=False,
    )
    assert result.allow_new_hr_estimate is False
    assert result.rejection_reasons
    assert (
        EXCESSIVE_MOTION in result.rejection_reasons
        or any("MOTION" in r or "DISPLACEMENT" in r for r in result.rejection_reasons)
    )


def test_good_conditions_allow_estimate(face_landmarks, gray_frame):
    assessor = SignalQualityAssessor()
    rgb = np.array([120.0, 100.0, 80.0])
    pulse = make_pulse(72, n=256)
    ts = make_timestamps(256)
    # Prime motion with a stable frame
    assessor.assess_frame(
        gray_frame, face_landmarks, rgb, 0.0,
        pulse=pulse, timestamps_s=ts, buffer_frames=256,
        candidate_hr=72.0, initializing=False,
    )
    result = assessor.assess_frame(
        gray_frame, face_landmarks, rgb, 1 / 30,
        pulse=pulse, timestamps_s=ts, buffer_frames=256,
        candidate_hr=72.0, initializing=False,
    )
    assert result.allow_new_hr_estimate is True
    assert result.rejection_reasons == []
    assert result.category in (QualityCategory.GOOD, QualityCategory.FAIR)
    assert result.to_dict()["allow_new_hr_estimate"] is True


def test_score_does_not_override_hard_reject(face_landmarks, gray_frame):
    """Composite score must not permit acceptance when rejects exist."""
    assessor = SignalQualityAssessor()
    result = assessor.assess_frame(
        frame_bgr=gray_frame,
        landmarks=None,
        rgb_mean=None,
        timestamp_s=1.0,
        pulse=make_pulse(72),
        timestamps_s=make_timestamps(256),
        buffer_frames=256,
        candidate_hr=72.0,
        initializing=False,
    )
    assert result.allow_new_hr_estimate is False
    assert FACE_NOT_DETECTED in result.rejection_reasons
