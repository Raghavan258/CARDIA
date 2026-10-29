"""Temporal RGB signal buffer with optional per-sample timestamps."""

from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np


class SignalExtractor:
    """Maintains a temporal buffer of RGB signal values with EMA smoothing."""

    def __init__(self, buffer_size=256, ema_alpha=0.4):
        """Initialize the signal buffer.

        Args:
            buffer_size: Maximum number of frames to keep in the buffer.
            ema_alpha: EMA factor (0=max smooth, 1=no smooth).
        """
        self.buffer_size = buffer_size
        self._buffer = deque(maxlen=buffer_size)
        self._timestamps = deque(maxlen=buffer_size)
        self._ema_alpha = ema_alpha
        self._prev = None

    def update(self, rgb_mean, timestamp_s: Optional[float] = None):
        """Add a new RGB mean value to the buffer with EMA smoothing.

        Args:
            rgb_mean: Array of shape (3,) with mean R, G, B values.
            timestamp_s: Optional monotonic/capture timestamp in seconds.
        """
        val = rgb_mean.copy()
        if self._prev is not None:
            val = self._ema_alpha * val + (1.0 - self._ema_alpha) * self._prev
        self._prev = val.copy()
        self._buffer.append(val)
        if timestamp_s is not None:
            self._timestamps.append(float(timestamp_s))
        elif len(self._timestamps) == len(self._buffer) - 1:
            # Keep lengths aligned when prior samples had timestamps.
            self._timestamps.clear()

    def get_signal(self):
        """Return the buffered RGB signal as (N, 3), or None if empty."""
        if len(self._buffer) == 0:
            return None
        return np.array(self._buffer)

    def get_timestamps(self) -> Optional[np.ndarray]:
        """Return timestamps aligned with the buffer, or None if unavailable."""
        if len(self._timestamps) == 0 or len(self._timestamps) != len(self._buffer):
            return None
        return np.array(self._timestamps, dtype=np.float64)

    @property
    def length(self):
        """Current number of frames in the buffer."""
        return len(self._buffer)

    def reset(self):
        """Clear the signal buffer."""
        self._buffer.clear()
        self._timestamps.clear()
        self._prev = None
