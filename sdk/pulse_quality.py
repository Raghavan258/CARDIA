"""Pulse-signal quality metrics (kept separate from hard rejection rules)."""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
from scipy.signal import welch

from sdk.config import PulseQualityConfig
from sdk.quality_types import (
    IMPLAUSIBLE_HEART_RATE,
    INSUFFICIENT_SIGNAL_DURATION,
    IRREGULAR_SAMPLING,
    UNSTABLE_PULSE_SIGNAL,
    WEAK_PULSE_AMPLITUDE,
    PulseQualityMetrics,
)


def _effective_fps(
    timestamps_s: Sequence[float],
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Return (median_fps, max_gap_s, latest_gap_s)."""
    if timestamps_s is None or len(timestamps_s) < 2:
        return None, None, None
    dts = np.diff(np.asarray(timestamps_s, dtype=np.float64))
    positive = dts[dts > 0]
    if len(positive) == 0:
        return None, None, None
    latest = float(dts[-1]) if dts[-1] > 0 else float(positive[-1])
    return float(1.0 / np.median(positive)), float(np.max(positive)), latest


def _spectral_prominence(pulse: np.ndarray, fps: float, lo_bpm: float, hi_bpm: float) -> tuple[Optional[float], Optional[float]]:
    if pulse is None or len(pulse) < 32 or fps <= 0:
        return None, None
    nperseg = min(len(pulse), 256)
    freqs, psd = welch(pulse, fs=fps, nperseg=nperseg, nfft=1024)
    mask = (freqs >= lo_bpm / 60.0) & (freqs <= hi_bpm / 60.0)
    if not np.any(mask):
        return None, None
    band = psd[mask]
    band_f = freqs[mask]
    peak = float(np.max(band))
    med = float(np.median(band))
    ratio = peak / med if med > 1e-12 else None
    dom_bpm = float(band_f[int(np.argmax(band))] * 60.0)
    return ratio, dom_bpm


class PulseQualityAssessor:
    """Compute pulse metrics and soft/hard quality flags."""

    def __init__(self, config: Optional[PulseQualityConfig] = None):
        self.config = config or PulseQualityConfig()
        self._last_hr: Optional[float] = None

    def reset(self) -> None:
        self._last_hr = None

    def assess(
        self,
        pulse: Optional[np.ndarray],
        timestamps_s: Optional[Sequence[float]],
        buffer_frames: int,
        fps_fallback: float,
        candidate_hr: Optional[float] = None,
    ) -> tuple[PulseQualityMetrics, list[str], list[str], float]:
        """Return (metrics, warnings, rejects, component_score in [0, 1])."""
        cfg = self.config
        warnings: list[str] = []
        rejects: list[str] = []

        if timestamps_s is None:
            eff_fps, max_gap, latest_gap = None, None, None
        else:
            eff_fps, max_gap, latest_gap = _effective_fps(timestamps_s)
        fps = eff_fps if eff_fps and eff_fps > 0 else fps_fallback
        duration = None
        if timestamps_s is not None and len(timestamps_s) >= 2:
            duration = float(timestamps_s[-1] - timestamps_s[0])
        elif fps > 0:
            duration = buffer_frames / fps

        # Frame count is the hard warm-up gate; duration is informational.
        duration_ok = buffer_frames >= cfg.min_frames
        if not duration_ok:
            rejects.append(INSUFFICIENT_SIGNAL_DURATION)
        elif duration is not None and duration < cfg.min_duration_s:
            warnings.append(INSUFFICIENT_SIGNAL_DURATION)

        # Only the latest gap matters for live rejection — a single historical
        # hitch must not poison the whole ring buffer.
        gap = latest_gap if latest_gap is not None else max_gap
        if gap is not None and gap > cfg.max_timestamp_gap_s:
            warnings.append(IRREGULAR_SAMPLING)
        if gap is not None and gap > cfg.reject_timestamp_gap_s:
            rejects.append(IRREGULAR_SAMPLING)

        if eff_fps is not None and eff_fps < cfg.min_effective_fps:
            warnings.append(IRREGULAR_SAMPLING)

        pulse_std = float(np.std(pulse)) if pulse is not None and len(pulse) else None
        amplitude_ok = pulse_std is not None and pulse_std >= cfg.min_pulse_std
        if pulse is not None and not amplitude_ok:
            rejects.append(WEAK_PULSE_AMPLITUDE)

        prominence, dom_bpm = _spectral_prominence(
            pulse, fps, cfg.min_bpm, cfg.max_bpm
        ) if pulse is not None else (None, None)
        spectral_ok = (
            prominence is not None
            and prominence >= cfg.min_peak_prominence_ratio
            and dom_bpm is not None
            and cfg.min_bpm <= dom_bpm <= cfg.max_bpm
        )
        if pulse is not None and duration_ok and not spectral_ok:
            rejects.append(UNSTABLE_PULSE_SIGNAL)

        hr_delta = None
        hr_consistency_ok = True
        hr_ref = candidate_hr if candidate_hr is not None else dom_bpm
        if hr_ref is not None and (
            hr_ref < cfg.min_bpm or hr_ref > cfg.max_bpm
        ):
            rejects.append(IMPLAUSIBLE_HEART_RATE)
            hr_consistency_ok = False
        if self._last_hr is not None and hr_ref is not None:
            hr_delta = abs(hr_ref - self._last_hr)
            if hr_delta > cfg.max_hr_delta:
                hr_consistency_ok = False
                warnings.append(UNSTABLE_PULSE_SIGNAL)
                rejects.append(UNSTABLE_PULSE_SIGNAL)

        metrics = PulseQualityMetrics(
            buffer_frames=buffer_frames,
            buffer_duration_s=duration,
            effective_fps=eff_fps,
            max_timestamp_gap_s=max_gap,
            pulse_std=pulse_std,
            spectral_prominence_ratio=prominence,
            dominant_bpm=dom_bpm,
            hr_delta=hr_delta,
            duration_ok=duration_ok,
            amplitude_ok=amplitude_ok,
            spectral_ok=spectral_ok,
            hr_consistency_ok=hr_consistency_ok,
        )
        score = self._component_score(metrics)
        return metrics, warnings, rejects, score

    def note_accepted_hr(self, hr: Optional[float]) -> None:
        if hr is not None:
            self._last_hr = hr

    def _component_score(self, m: PulseQualityMetrics) -> float:
        cfg = self.config
        dur = 1.0 if m.duration_ok else 0.0
        amp = 1.0 if m.amplitude_ok else 0.0
        spec = 1.0 if m.spectral_ok else 0.0
        cons = 1.0 if m.hr_consistency_ok else 0.0
        return (
            cfg.weight_duration * dur
            + cfg.weight_amplitude * amp
            + cfg.weight_spectral * spec
            + cfg.weight_hr_consistency * cons
        )
