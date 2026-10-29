"""Shared pytest fixtures for CARDIA / rPPG-SDK tests."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def face_landmarks():
    """Synthetic 478-point face oval-ish landmark cloud."""
    rng = np.random.default_rng(0)
    cx, cy, w, h = 320.0, 240.0, 160.0, 200.0
    pts = []
    for i in range(478):
        ang = 2 * np.pi * i / 478
        x = cx + 0.5 * w * np.cos(ang) + rng.normal(0, 0.5)
        y = cy + 0.5 * h * np.sin(ang) + rng.normal(0, 0.5)
        pts.append((float(x), float(y)))
    return pts


@pytest.fixture
def gray_frame():
    """Mid-gray BGR frame suitable for lighting OK."""
    return np.full((480, 640, 3), 128, dtype=np.uint8)


