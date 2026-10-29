"""Deterministic tests for landmark motion estimation."""

from __future__ import annotations

from sdk.config import MotionConfig
from sdk.motion import MotionEstimator
from sdk.quality_types import EXCESSIVE_MOTION, ABRUPT_LANDMARK_DISPLACEMENT, MotionCategory


def _shift(landmarks, dx, dy):
    return [(x + dx, y + dy) for x, y in landmarks]


def test_low_motion_stable(face_landmarks):
    est = MotionEstimator(MotionConfig(ema_alpha=1.0))
    score, cat, reject, reasons = est.update(face_landmarks, 0.0)
    assert cat == MotionCategory.LOW
    assert reject is False

    score, cat, reject, reasons = est.update(face_landmarks, 1 / 30)
    assert score is not None and score < 0.15
    assert cat == MotionCategory.LOW
    assert reject is False
    assert reasons == []


def test_abrupt_landmark_jump(face_landmarks):
    est = MotionEstimator(MotionConfig(abrupt_jump=0.1, abrupt_rate=1.0, ema_alpha=1.0))
    est.update(face_landmarks, 0.0)
    moved = _shift(face_landmarks, 80, 0)  # large vs ~face diagonal ~250
    score, cat, reject, reasons = est.update(moved, 1 / 30)
    assert reject is True
    assert ABRUPT_LANDMARK_DISPLACEMENT in reasons


def test_sparse_frame_small_move_not_abrupt(face_landmarks):
    """Low-FPS webcam frames with small motion must not clear warm-up."""
    est = MotionEstimator(MotionConfig(ema_alpha=1.0))
    est.update(face_landmarks, 0.0)
    moved = _shift(face_landmarks, 8, 0)
    score, cat, reject, reasons = est.update(moved, 0.4)  # 2.5 FPS spacing
    assert reject is False
    assert ABRUPT_LANDMARK_DISPLACEMENT not in reasons


def test_excessive_motion_rate(face_landmarks):
    cfg = MotionConfig(reject_above=0.2, abrupt_jump=10.0, ema_alpha=1.0)
    est = MotionEstimator(cfg)
    est.update(face_landmarks, 0.0)
    # Moderate pixel shift over a very small dt → high rate
    moved = _shift(face_landmarks, 20, 0)
    score, cat, reject, reasons = est.update(moved, 0.01)
    assert reject is True
    assert EXCESSIVE_MOTION in reasons
    assert cat == MotionCategory.HIGH


def test_missing_landmarks_resets_prev(face_landmarks):
    est = MotionEstimator()
    est.update(face_landmarks, 0.0)
    score, cat, reject, reasons = est.update(None, 0.1)
    assert cat == MotionCategory.UNKNOWN
    assert reject is False
