"""Explicit monitoring session / measurement states."""

from __future__ import annotations

from enum import Enum


class MeasurementState(str, Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    MEASURING = "measuring"
    LOW_QUALITY = "low_quality"
    REACQUIRING = "reacquiring"
    ERROR = "error"
    STOPPED = "stopped"


# Reasons that should clear the signal buffer and enter reacquisition.
# Note: IRREGULAR_SAMPLING is intentionally excluded — web/live pipelines often
# have >250ms gaps under MediaPipe load; clearing the buffer prevents warm-up.
REACQUIRE_REASONS = frozenset(
    {
        "EXCESSIVE_MOTION",
        "FACE_TRACKING_LOST",
    }
)
