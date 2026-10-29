"""CHROM algorithm and POS/CHROM comparison on synthetic RGB."""

from __future__ import annotations

import numpy as np

from algorithms.chrom import chrom
from algorithms.pos import pos
from sdk.heart_rate import HeartRate
from sdk.rppg_algorithm import RPPGAlgorithm, SUPPORTED_ALGORITHMS


def _synthetic_rgb(bpm: float = 72.0, fps: float = 30.0, n: int = 256):
    t = np.arange(n) / fps
    amp = 0.02 * np.sin(2 * np.pi * (bpm / 60.0) * t)
    return np.column_stack([
        140 + amp * 100,
        100 + amp * 150,
        80 + amp * 50,
    ])


def _median_hr(pulse, fps: float) -> float:
    hr = HeartRate(smooth_window=3)
    vals = []
    for i in range(64, len(pulse), 16):
        b = hr.compute(pulse[:i], fps)
        if b is not None:
            vals.append(b)
    assert vals, "expected HR estimates"
    return float(np.median(vals))


def test_chrom_recovers_72bpm():
    rgb = _synthetic_rgb(72.0)
    pulse = chrom(rgb, fps=30.0, window_size=32)
    assert pulse.shape == (256,)
    assert abs(_median_hr(pulse, 30.0) - 72.0) < 6.0


def test_pos_and_chrom_agree_on_synthetic():
    rgb = _synthetic_rgb(80.0)
    pos_hr = _median_hr(pos(rgb, 30.0, 32), 30.0)
    chrom_hr = _median_hr(chrom(rgb, 30.0, 32), 30.0)
    assert abs(pos_hr - 80.0) < 6.0
    assert abs(chrom_hr - 80.0) < 6.0
    assert abs(pos_hr - chrom_hr) < 8.0


def test_rppg_algorithm_supports_chrom():
    assert "chrom" in SUPPORTED_ALGORITHMS
    alg = RPPGAlgorithm(algorithm="chrom", window_size=32)
    pulse = alg.process(_synthetic_rgb(), 30.0)
    assert pulse is not None
    both = alg.process_both(_synthetic_rgb(), 30.0)
    assert both["pos"] is not None and both["chrom"] is not None


def test_unsupported_algorithm_raises():
    try:
        RPPGAlgorithm(algorithm="ica")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unsupported" in str(exc)
