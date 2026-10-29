"""Wrapper for pluggable rPPG pulse-extraction algorithms."""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algorithms.chrom import chrom
from algorithms.pos import pos

SUPPORTED_ALGORITHMS = ("pos", "chrom")


class RPPGAlgorithm:
    """Wrapper for rPPG pulse extraction algorithms (POS, CHROM)."""

    def __init__(self, algorithm: str = "pos", window_size: int = 32):
        """Initialize the rPPG algorithm.

        Args:
            algorithm: ``"pos"`` or ``"chrom"``.
            window_size: Sliding window length in frames.
        """
        name = algorithm.lower().strip()
        if name not in SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported algorithm: {algorithm}. "
                f"Choose from {SUPPORTED_ALGORITHMS}."
            )
        self.algorithm = name
        self.window_size = window_size

    def process(self, signal, fps):
        """Extract pulse signal from RGB temporal signal.

        Args:
            signal: Numpy array of shape (N, 3) with RGB values.
            fps: Effective sampling rate of the source.

        Returns:
            1-D pulse signal array, or None if signal is too short.
        """
        if signal is None or len(signal) < self.window_size:
            return None
        if self.algorithm == "chrom":
            return chrom(signal, fps, window_size=self.window_size)
        return pos(signal, fps, window_size=self.window_size)

    def process_both(self, signal, fps) -> dict[str, np.ndarray | None]:
        """Run POS and CHROM on the same window for comparison."""
        if signal is None or len(signal) < self.window_size:
            return {"pos": None, "chrom": None}
        return {
            "pos": pos(signal, fps, window_size=self.window_size),
            "chrom": chrom(signal, fps, window_size=self.window_size),
        }
