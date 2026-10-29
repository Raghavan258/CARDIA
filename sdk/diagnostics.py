"""Build compact diagnostic payloads for the live dashboard (real measured data)."""

from __future__ import annotations

from typing import Any, Optional, Sequence

import numpy as np
from scipy.signal import welch


def downsample_series(values: np.ndarray, max_points: int = 128) -> list[float]:
    if values is None or len(values) == 0:
        return []
    n = len(values)
    if n <= max_points:
        return [float(v) for v in values]
    idx = np.linspace(0, n - 1, max_points).astype(int)
    return [float(values[i]) for i in idx]


def pulse_spectrum(
    pulse: Optional[np.ndarray],
    fps: float,
    max_points: int = 64,
) -> dict[str, list[float]]:
    if pulse is None or len(pulse) < 32 or fps <= 0:
        return {"freq_hz": [], "psd": []}
    nperseg = min(len(pulse), 256)
    freqs, psd = welch(pulse, fs=fps, nperseg=nperseg, nfft=1024)
    mask = (freqs >= 0.5) & (freqs <= 3.5)
    freqs, psd = freqs[mask], psd[mask]
    if len(freqs) == 0:
        return {"freq_hz": [], "psd": []}
    if len(freqs) > max_points:
        idx = np.linspace(0, len(freqs) - 1, max_points).astype(int)
        freqs, psd = freqs[idx], psd[idx]
    return {
        "freq_hz": [float(f) for f in freqs],
        "psd": [float(p) for p in psd],
    }


def build_diagnostics(
    *,
    rgb_signal: Optional[np.ndarray],
    pulse: Optional[np.ndarray],
    timestamps_s: Optional[np.ndarray],
    effective_fps: float,
    hr_history: Sequence[float],
    landmarks: Optional[Sequence[tuple[float, float]]],
    frame_shape: Optional[tuple[int, int]] = None,
    max_trace_points: int = 128,
) -> dict[str, Any]:
    """Return JSON-serializable diagnostics derived from measured buffers."""
    rgb = {"r": [], "g": [], "b": [], "t": []}
    if rgb_signal is not None and len(rgb_signal) > 0:
        r = downsample_series(rgb_signal[:, 0], max_trace_points)
        g = downsample_series(rgb_signal[:, 1], max_trace_points)
        b = downsample_series(rgb_signal[:, 2], max_trace_points)
        if timestamps_s is not None and len(timestamps_s) == len(rgb_signal):
            t = downsample_series(timestamps_s, max_trace_points)
        else:
            t = [i / max(effective_fps, 1.0) for i in range(len(r))]
        rgb = {"r": r, "g": g, "b": b, "t": t}

    pulse_trace = {
        "y": downsample_series(pulse, max_trace_points) if pulse is not None else [],
        "t": [],
    }
    if pulse is not None and len(pulse_trace["y"]):
        if timestamps_s is not None and len(timestamps_s) >= len(pulse):
            pulse_trace["t"] = downsample_series(timestamps_s[-len(pulse) :], max_trace_points)
        else:
            pulse_trace["t"] = [
                i / max(effective_fps, 1.0) for i in range(len(pulse_trace["y"]))
            ]

    lm = None
    if landmarks is not None and frame_shape is not None:
        h, w = frame_shape
        # Send a sparse subset for overlay (every 8th landmark) as normalized coords.
        step = max(1, len(landmarks) // 60)
        lm = [
            {"x": float(x) / max(w, 1), "y": float(y) / max(h, 1)}
            for i, (x, y) in enumerate(landmarks)
            if i % step == 0
        ]

    return {
        "rgb": rgb,
        "pulse": pulse_trace,
        "spectrum": pulse_spectrum(pulse, effective_fps),
        "hr_history": [float(v) for v in hr_history],
        "landmarks_norm": lm,
    }
