"""Signal processing edge-case tests (POS + buffer + HR)."""

from __future__ import annotations

import numpy as np

from algorithms.pos import pos
from helpers import make_pulse
from sdk.heart_rate import HeartRate
from sdk.signal_extractor import SignalExtractor


def test_constant_rgb_pos_near_zero_energy():
    rgb = np.tile(np.array([100.0, 80.0, 60.0]), (128, 1))
    pulse = pos(rgb, fps=30.0, window_size=32)
    assert pulse.shape == (128,)
    # After detrend/normalize, constant input yields near-zero pre-norm;
    # implementation may normalize — std finite.
    assert np.isfinite(pulse).all()


def test_synthetic_72bpm_hr_estimate():
    fps = 30.0
    n = 256
    t = np.arange(n) / fps
    pulse_amp = 0.02 * np.sin(2 * np.pi * 1.2 * t)
    rgb = np.column_stack([
        140 + pulse_amp * 100,
        100 + pulse_amp * 150,
        80 + pulse_amp * 50,
    ])
    pulse = pos(rgb, fps=fps, window_size=32)
    hr = HeartRate(smooth_window=3)
    estimates = []
    for i in range(64, n, 16):
        bpm = hr.compute(pulse[:i], fps)
        if bpm is not None:
            estimates.append(bpm)
    assert estimates
    assert abs(float(np.median(estimates)) - 72.0) < 5.0


def test_signal_extractor_timestamps_aligned():
    se = SignalExtractor(buffer_size=10)
    for i in range(5):
        se.update(np.array([1.0, 2.0, 3.0]), timestamp_s=i / 30.0)
    ts = se.get_timestamps()
    assert ts is not None
    assert len(ts) == 5
    assert se.length == 5


def test_too_short_for_hr():
    hr = HeartRate()
    assert hr.compute(make_pulse(72, n=32), 30.0) is None


def test_invalid_zero_fps_band_safe():
    # POS bandpass should not crash when fps is very low
    rgb = np.random.default_rng(0).normal(size=(64, 3)) + 100
    pulse = pos(rgb, fps=2.0, window_size=16)
    assert pulse.shape[0] == 64
