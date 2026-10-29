"""Shared deterministic helpers for tests."""

from __future__ import annotations

import numpy as np


def make_pulse(bpm: float, fps: float = 30.0, n: int = 256, noise: float = 0.0):
    t = np.arange(n) / fps
    sig = np.sin(2 * np.pi * (bpm / 60.0) * t)
    if noise:
        sig = sig + noise * np.random.default_rng(1).normal(size=n)
    return sig.astype(np.float64)


def make_timestamps(
    n: int,
    fps: float = 30.0,
    gap_at: int | None = None,
    gap_s: float = 0.5,
):
    ts = np.arange(n, dtype=np.float64) / fps
    if gap_at is not None and 0 < gap_at < n:
        ts[gap_at:] += gap_s
    return ts
