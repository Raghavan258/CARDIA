"""Deterministic synthetic evaluation sequences (no personal video required).

Produces landmark tracks, mid-gray frames, and ROI RGB means modulated at a
known heart rate so POS/CHROM + quality gating can be exercised reproducibly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

import numpy as np


@dataclass
class SyntheticSample:
    frame_bgr: np.ndarray
    landmarks: Optional[list[tuple[float, float]]]
    rgb_mean: Optional[np.ndarray]
    timestamp_s: float
    reference_bpm: float
    inject_motion: bool = False


def _face_landmarks(cx: float, cy: float, w: float, h: float, n: int = 478):
    pts = []
    for i in range(n):
        ang = 2 * np.pi * i / n
        pts.append((cx + 0.5 * w * np.cos(ang), cy + 0.5 * h * np.sin(ang)))
    return pts


def iter_synthetic_session(
    *,
    reference_bpm: float = 72.0,
    fps: float = 30.0,
    duration_s: float = 8.0,
    motion_at_s: Optional[float] = 5.0,
    frame_size: tuple[int, int] = (240, 320),
) -> Iterator[SyntheticSample]:
    """Yield a synthetic monitoring session with optional motion discontinuity."""
    h, w = frame_size
    n = int(duration_s * fps)
    base = _face_landmarks(w * 0.5, h * 0.45, w * 0.35, h * 0.45)
    for i in range(n):
        t = i / fps
        pulse = 0.025 * np.sin(2 * np.pi * (reference_bpm / 60.0) * t)
        rgb = np.array([
            140 + pulse * 100,
            105 + pulse * 150,
            85 + pulse * 50,
        ], dtype=np.float64)
        frame = np.full((h, w, 3), 128, dtype=np.uint8)
        # Mild spatial gradient so lighting stats are non-degenerate
        frame[:, :, 1] = np.clip(frame[:, :, 1] + 5, 0, 255)

        inject = motion_at_s is not None and abs(t - motion_at_s) < (1.5 / fps)
        landmarks = base
        if inject:
            landmarks = [(x + 90, y + 35) for x, y in base]
        yield SyntheticSample(
            frame_bgr=frame,
            landmarks=landmarks,
            rgb_mean=rgb,
            timestamp_s=t,
            reference_bpm=reference_bpm,
            inject_motion=inject,
        )
