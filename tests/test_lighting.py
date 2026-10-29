"""Lighting assessment tests."""

from __future__ import annotations

import numpy as np

from sdk.config import LightingConfig
from sdk.lighting import LightingAssessor
from sdk.quality_types import ABRUPT_ILLUMINATION_CHANGE, POOR_LIGHTING, LightingStatus


def test_mid_gray_ok(face_landmarks, gray_frame):
    assessor = LightingAssessor()
    stats, warnings, rejects = assessor.assess(gray_frame, face_landmarks)
    assert stats.status == LightingStatus.OK
    assert rejects == []
    assert stats.mean_brightness is not None
    assert 100 < stats.mean_brightness < 160


def test_underexposed_frame(face_landmarks):
    frame = np.full((480, 640, 3), 10, dtype=np.uint8)
    assessor = LightingAssessor(LightingConfig(reject_on_poor=True))
    stats, warnings, rejects = assessor.assess(frame, face_landmarks)
    assert stats.status == LightingStatus.UNDEREXPOSED
    assert POOR_LIGHTING in rejects


def test_overexposed_frame(face_landmarks):
    frame = np.full((480, 640, 3), 250, dtype=np.uint8)
    assessor = LightingAssessor(LightingConfig(reject_on_poor=True))
    stats, warnings, rejects = assessor.assess(frame, face_landmarks)
    assert stats.status == LightingStatus.OVEREXPOSED
    assert POOR_LIGHTING in rejects


def test_abrupt_illumination_change(face_landmarks):
    assessor = LightingAssessor(LightingConfig(abrupt_delta=20.0, reject_on_poor=True))
    dark = np.full((480, 640, 3), 40, dtype=np.uint8)
    bright = np.full((480, 640, 3), 180, dtype=np.uint8)
    assessor.assess(dark, face_landmarks)
    stats, warnings, rejects = assessor.assess(bright, face_landmarks)
    assert stats.status == LightingStatus.UNSTABLE
    assert ABRUPT_ILLUMINATION_CHANGE in rejects
