"""Shared signal filters for rPPG algorithms."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt


def bandpass(signal, fps, lo=0.75, hi=3.0, order=4):
    """Apply a Butterworth bandpass filter (~45-180 BPM by default)."""
    nyq = fps / 2.0
    if hi >= nyq:
        hi = nyq - 0.1
    if lo >= hi or len(signal) < 3:
        return signal
    b, a = butter(order, [lo / nyq, hi / nyq], btype="band")
    return filtfilt(b, a, signal, axis=0)
