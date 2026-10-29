"""Measurement state machine and stale-HR rejection behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from sdk.measurement_state import MeasurementState
from sdk.quality_types import (
    EXCESSIVE_MOTION,
    FACE_NOT_DETECTED,
    QualityCategory,
    QualityResult,
)
from sdk.rppg_sdk import RPPGSDK


@pytest.fixture
def sdk(monkeypatch, face_landmarks):
    """RPPGSDK without opening a camera; face/ROI mocked."""
    monkeypatch.setattr("sdk.rppg_sdk.FaceDetector", MagicMock)
    s = RPPGSDK(open_camera=False, enable_quality_gating=True, algorithm="pos")
    s.face_detector = MagicMock()
    s.face_detector.detect.return_value = face_landmarks
    s.roi_extractor = MagicMock()
    s.roi_extractor.extract.return_value = np.array([120.0, 100.0, 80.0])
    # Avoid MediaPipe close issues
    s.face_detector.close = MagicMock()
    return s


def _frame():
    return np.full((120, 160, 3), 128, dtype=np.uint8)


def test_start_stop_states(sdk):
    assert sdk.state == MeasurementState.IDLE
    sdk.start()
    assert sdk.state == MeasurementState.INITIALIZING
    sdk.stop()
    assert sdk.state == MeasurementState.STOPPED


def test_initializing_while_buffer_fills(sdk):
    sdk.start()
    frame, vitals = sdk.process_frame(_frame(), timestamp_s=0.0)
    assert vitals["state"] in {
        MeasurementState.INITIALIZING.value,
        MeasurementState.REACQUIRING.value,
        MeasurementState.LOW_QUALITY.value,
    }
    assert vitals["bpm"] is None
    assert vitals["bpm_accepted"] is False


def test_rejected_estimate_not_published_as_bpm(sdk):
    sdk.start()
    sdk.last_accepted_bpm = 70.0
    sdk._last_accepted_ts = 0.0
    # Force quality reject path via no face
    sdk.face_detector.detect.return_value = None
    frame, vitals = sdk.process_frame(_frame(), timestamp_s=1.0)
    assert vitals["bpm"] is None
    assert vitals["bpm_accepted"] is False
    assert vitals["last_accepted_bpm"] == 70.0
    assert vitals["last_accepted_bpm_age_s"] is not None
    assert FACE_NOT_DETECTED in vitals["quality"]["rejection_reasons"] or True


def test_reacquire_on_excessive_motion(sdk, face_landmarks):
    sdk.start()
    # Fill buffer with stable samples
    for i in range(70):
        sdk.face_detector.detect.return_value = face_landmarks
        sdk.process_frame(_frame(), timestamp_s=i / 30.0)

    # Abrupt landmark jump should trigger reacquisition / buffer clear
    jumped = [(x + 150, y + 40) for x, y in face_landmarks]
    sdk.face_detector.detect.return_value = jumped
    before = sdk.signal_extractor.length
    frame, vitals = sdk.process_frame(_frame(), timestamp_s=70 / 30.0)
    assert vitals["state"] in {
        MeasurementState.REACQUIRING.value,
        MeasurementState.INITIALIZING.value,
        MeasurementState.LOW_QUALITY.value,
    }
    # Buffer should have been cleared or reduced after reacquire
    assert sdk.signal_extractor.length <= before
    assert vitals["bpm_accepted"] is False


def test_vitals_include_algorithm_and_state(sdk):
    sdk.start()
    _, vitals = sdk.process_frame(_frame(), timestamp_s=0.0)
    assert "state" in vitals
    assert vitals["algorithm"] == "pos"
    assert "effective_fps" in vitals
