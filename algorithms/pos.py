"""Plane-Orthogonal-to-Skin (POS) rPPG algorithm (Wang et al., 2017)."""

from __future__ import annotations

import numpy as np
from scipy.signal import detrend

from algorithms.filters import bandpass


def pos(signal, fps, window_size=32):
    """Plane-Orthogonal-to-Skin (POS) rPPG algorithm.

    Reference: Wang et al., "Algorithmic Principles of Remote PPG" (2017).

    Args:
        signal: Numpy array of shape (N, 3) with temporal RGB means.
        fps: Frame rate of the video source.
        window_size: Sliding window length in frames.

    Returns:
        1-D numpy array of the extracted pulse signal.
    """
    n = signal.shape[0]
    pulse = np.zeros(n)

    for t in range(window_size - 1, n):
        start = t - window_size + 1
        window = signal[start : t + 1, :]  # (window_size, 3)

        means = np.mean(window, axis=0)
        means[means == 0] = 1.0
        cn = window / means

        xs = cn[:, 1] - cn[:, 2]  # G - B
        ys = -2.0 * cn[:, 0] + cn[:, 1] + cn[:, 2]  # -2R + G + B

        std_xs = np.std(xs)
        std_ys = np.std(ys)
        alpha = std_xs / std_ys if std_ys > 1e-10 else 0.0
        p = xs + alpha * ys
        pulse[start : t + 1] += p - np.mean(p)

    pulse = detrend(pulse)
    if n >= 2 * window_size:
        pulse = bandpass(pulse, fps)
    std = np.std(pulse)
    if std > 1e-10:
        pulse = pulse / std
    return pulse
