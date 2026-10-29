"""Pulse-signal quality metric tests."""

from __future__ import annotations

import numpy as np

from helpers import make_pulse, make_timestamps
from sdk.config import PulseQualityConfig
from sdk.pulse_quality import PulseQualityAssessor
from sdk.quality_types import (
    INSUFFICIENT_SIGNAL_DURATION,
    IRREGULAR_SAMPLING,
    UNSTABLE_PULSE_SIGNAL,
    WEAK_PULSE_AMPLITUDE,
)


def test_too_short_buffer():
    assessor = PulseQualityAssessor()
    pulse = make_pulse(72, n=30)
    metrics, warnings, rejects, score = assessor.assess(
        pulse=pulse,
        timestamps_s=make_timestamps(30),
        buffer_frames=30,
        fps_fallback=30.0,
    )
    assert metrics.duration_ok is False
    assert INSUFFICIENT_SIGNAL_DURATION in rejects
    assert score < 1.0


def test_constant_weak_pulse():
    assessor = PulseQualityAssessor(PulseQualityConfig(min_frames=64, min_duration_s=1.0))
    pulse = np.ones(128, dtype=np.float64)
    metrics, warnings, rejects, score = assessor.assess(
        pulse=pulse,
        timestamps_s=make_timestamps(128),
        buffer_frames=128,
        fps_fallback=30.0,
    )
    assert metrics.amplitude_ok is False
    assert WEAK_PULSE_AMPLITUDE in rejects


def test_clean_periodic_pulse_ok():
    assessor = PulseQualityAssessor()
    pulse = make_pulse(72, n=256)
    # POS-normalized pulses have std ~1; raw sinusoid also fine
    metrics, warnings, rejects, score = assessor.assess(
        pulse=pulse,
        timestamps_s=make_timestamps(256),
        buffer_frames=256,
        fps_fallback=30.0,
        candidate_hr=72.0,
    )
    assert metrics.duration_ok
    assert metrics.amplitude_ok
    assert metrics.spectral_ok
    assert INSUFFICIENT_SIGNAL_DURATION not in rejects
    assert WEAK_PULSE_AMPLITUDE not in rejects


def test_historical_gap_is_warning_not_reject():
    """A gap in the middle of the buffer must not permanently block HR."""
    assessor = PulseQualityAssessor(
        PulseQualityConfig(max_timestamp_gap_s=0.2, reject_timestamp_gap_s=3.0)
    )
    pulse = make_pulse(72, n=128)
    ts = make_timestamps(128, gap_at=64, gap_s=0.5)
    metrics, warnings, rejects, score = assessor.assess(
        pulse=pulse,
        timestamps_s=ts,
        buffer_frames=128,
        fps_fallback=30.0,
    )
    assert metrics.max_timestamp_gap_s is not None
    assert metrics.max_timestamp_gap_s >= 0.5
    assert IRREGULAR_SAMPLING not in rejects


def test_latest_extreme_gap_rejects():
    assessor = PulseQualityAssessor(
        PulseQualityConfig(max_timestamp_gap_s=0.5, reject_timestamp_gap_s=1.0)
    )
    pulse = make_pulse(72, n=64)
    ts = make_timestamps(64)
    ts[-1] = ts[-2] + 2.5  # latest gap only
    metrics, warnings, rejects, score = assessor.assess(
        pulse=pulse,
        timestamps_s=ts,
        buffer_frames=64,
        fps_fallback=30.0,
    )
    assert IRREGULAR_SAMPLING in rejects


def test_hr_inconsistency_flagged():
    cfg = PulseQualityConfig(max_hr_delta=10.0, min_frames=64, min_duration_s=1.0)
    assessor = PulseQualityAssessor(cfg)
    pulse = make_pulse(72, n=128)
    assessor.note_accepted_hr(72.0)
    metrics, warnings, rejects, score = assessor.assess(
        pulse=pulse,
        timestamps_s=make_timestamps(128),
        buffer_frames=128,
        fps_fallback=30.0,
        candidate_hr=120.0,
    )
    assert metrics.hr_consistency_ok is False
    assert UNSTABLE_PULSE_SIGNAL in rejects
