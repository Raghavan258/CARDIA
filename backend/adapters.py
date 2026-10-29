"""Input adapters for live browser frames vs prerecorded video."""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import cv2
import numpy as np

from backend.settings import PROJECT_ROOT, SETTINGS

logger = logging.getLogger("cardia.backend.adapters")


@dataclass
class DecodedFrame:
    bgr: np.ndarray
    timestamp_s: float
    source: str


def decode_jpeg_base64(
    data_base64: str,
    timestamp_s: float,
    max_bytes: int = SETTINGS.max_jpeg_bytes,
    max_width: int = SETTINGS.max_frame_width,
    max_height: int = SETTINGS.max_frame_height,
) -> DecodedFrame:
    """Decode a client JPEG frame; resize if larger than configured max."""
    raw = base64.b64decode(data_base64, validate=False)
    if len(raw) > max_bytes:
        raise ValueError(f"JPEG payload exceeds {max_bytes} bytes")
    arr = np.frombuffer(raw, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Failed to decode JPEG frame")
    h, w = bgr.shape[:2]
    if w > max_width or h > max_height:
        scale = min(max_width / w, max_height / h)
        bgr = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return DecodedFrame(bgr=bgr, timestamp_s=float(timestamp_s), source="live")


def resolve_video_path(video_path: str) -> Path:
    """Resolve and authorize a recorded-video path under allowed roots."""
    path = Path(video_path)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    else:
        path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")
    allowed = [(PROJECT_ROOT / root).resolve() for root in SETTINGS.allowed_video_roots]
    if not any(_is_relative_to(path, root) for root in allowed):
        raise PermissionError(
            f"Video path must be under one of {SETTINGS.allowed_video_roots}"
        )
    return path


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def iter_video_frames(
    video_path: Path,
    max_width: int = SETTINGS.max_frame_width,
    max_height: int = SETTINGS.max_frame_height,
) -> Iterator[DecodedFrame]:
    """Yield BGR frames from a prerecorded video with capture timestamps."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 1 else 30.0
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            h, w = frame.shape[:2]
            if w > max_width or h > max_height:
                scale = min(max_width / w, max_height / h)
                frame = cv2.resize(
                    frame,
                    (int(w * scale), int(h * scale)),
                    interpolation=cv2.INTER_AREA,
                )
            yield DecodedFrame(
                bgr=frame,
                timestamp_s=idx / fps,
                source="recorded",
            )
            idx += 1
    finally:
        cap.release()
