"""CHROM rPPG algorithm (de Haan & Jeanne, 2013).

Chrominance-based method: projects temporally normalized RGB onto a plane
that reduces specular reflection while retaining the pulse chrominance.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import detrend

from algorithms.filters import bandpass


def chrom(signal, fps, window_size=32):
    """Extract pulse via the CHROM method.

    Reference: de Haan, G. & Jeanne, V., "Robust Pulse Rate From
    Chrominance-Based rPPG" (IEEE TBME, 2013).

    Args:
        signal: Array of shape (N, 3) temporal RGB means.
        fps: Sampling rate in Hz (effective FPS when available).
        window_size: Sliding window length in frames.

    Returns:
        1-D pulse signal array.
    """
    n = signal.shape[0]
    pulse = np.zeros(n)

    for t in range(window_size - 1, n):
        start = t - window_size + 1
        window = signal[start : t + 1, :].astype(np.float64)
        means = np.mean(window, axis=0)
        means[means == 0] = 1.0
        cn = window / means

        # CHROM projection on normalized RGB
        xs = 0.77 * cn[:, 0] - 0.51 * cn[:, 1]
        ys = 0.77 * cn[:, 0] + 0.51 * cn[:, 1] - 0.77 * cn[:, 2]
        std_xs = np.std(xs)
        std_ys = np.std(ys)
        alpha = std_xs / std_ys if std_ys > 1e-10 else 0.0
        s = xs - alpha * ys
        pulse[start : t + 1] += s - np.mean(s)

    pulse = detrend(pulse)
    if n >= 2 * window_size:
        pulse = bandpass(pulse, fps)
    std = np.std(pulse)
    if std > 1e-10:
        pulse = pulse / std
    return pulse
