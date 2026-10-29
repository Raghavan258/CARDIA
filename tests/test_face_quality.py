"""Face tracking quality tests."""

from __future__ import annotations

import numpy as np

from sdk.face_quality import FaceTrackingAssessor
from sdk.quality_types import (
    ABRUPT_LANDMARK_DISPLACEMENT,
    FACE_NOT_DETECTED,
    FACE_TRACKING_LOST,
    INVALID_ROI,
    FaceTrackStatus,
)


def test_face_missing():
    assessor = FaceTrackingAssessor()
    status, warnings, rejects = assessor.assess(None, None)
    assert status == FaceTrackStatus.NOT_DETECTED
    assert FACE_NOT_DETECTED in rejects


def test_face_tracking_lost_after_detection(face_landmarks):
    assessor = FaceTrackingAssessor()
    assessor.assess(face_landmarks, np.array([100.0, 80.0, 60.0]))
    status, warnings, rejects = assessor.assess(None, None)
    assert status == FaceTrackStatus.LOST
    assert FACE_TRACKING_LOST in rejects


def test_invalid_roi_incomplete_landmarks():
    assessor = FaceTrackingAssessor()
    status, warnings, rejects = assessor.assess([(0, 0)] * 10, np.array([1.0, 1.0, 1.0]))
    assert status == FaceTrackStatus.INVALID_ROI
    assert INVALID_ROI in rejects


def test_abrupt_roi_jump(face_landmarks):
    assessor = FaceTrackingAssessor()
    rgb = np.array([120.0, 100.0, 80.0])
    status, _, _ = assessor.assess(face_landmarks, rgb)
    assert status == FaceTrackStatus.OK
    jumped = [(x + 220, y + 140) for x, y in face_landmarks]
    status, warnings, rejects = assessor.assess(jumped, rgb)
    assert status == FaceTrackStatus.DISCONTINUITY
    assert ABRUPT_LANDMARK_DISPLACEMENT in rejects
