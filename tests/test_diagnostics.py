"""Diagnostics payload uses measured buffers (no fabricated series)."""

from __future__ import annotations

import numpy as np

from sdk.diagnostics import build_diagnostics, downsample_series, pulse_spectrum


def test_downsample_preserves_endpoints():
    vals = np.arange(1000, dtype=float)
    out = downsample_series(vals, max_points=10)
    assert len(out) == 10
    assert out[0] == 0.0
    assert out[-1] == 999.0


def test_build_diagnostics_from_real_arrays():
    n = 128
    t = np.arange(n) / 30.0
    rgb = np.column_stack([100 + np.sin(t), 90 + np.sin(t), 80 + np.sin(t)])
    pulse = np.sin(2 * np.pi * 1.2 * t)
    diag = build_diagnostics(
        rgb_signal=rgb,
        pulse=pulse,
        timestamps_s=t,
        effective_fps=30.0,
        hr_history=[72.0, 73.0],
        landmarks=[(10.0, 20.0)] * 40,
        frame_shape=(100, 200),
        max_trace_points=32,
    )
    assert len(diag["rgb"]["r"]) == 32
    assert len(diag["pulse"]["y"]) == 32
    assert diag["hr_history"] == [72.0, 73.0]
    assert diag["spectrum"]["freq_hz"]
    assert diag["landmarks_norm"]


def test_empty_pulse_spectrum():
    assert pulse_spectrum(None, 30.0) == {"freq_hz": [], "psd": []}
