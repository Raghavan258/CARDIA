"""Structured logging helpers for reproducible HR estimates."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional


def get_logger(name: str = "cardia") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_estimate(
    logger: logging.Logger,
    *,
    state: str,
    algorithm: str,
    bpm_raw: Optional[float],
    bpm_accepted: bool,
    effective_fps: Optional[float],
    quality_category: str,
    rejection_reasons: list[str],
    buffer_frames: int,
    timestamp_s: float,
) -> None:
    """Emit one JSON line describing an HR decision for later investigation."""
    payload: dict[str, Any] = {
        "event": "hr_estimate",
        "state": state,
        "algorithm": algorithm,
        "bpm_raw": bpm_raw,
        "bpm_accepted": bpm_accepted,
        "effective_fps": effective_fps,
        "quality_category": quality_category,
        "rejection_reasons": rejection_reasons,
        "buffer_frames": buffer_frames,
        "timestamp_s": round(timestamp_s, 4),
    }
    logger.info(json.dumps(payload, default=str))
