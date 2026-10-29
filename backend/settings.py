"""Backend runtime settings (env-overridable, no secrets required)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BackendSettings:
    """Streaming and session limits for the FastAPI service."""

    host: str = "127.0.0.1"
    port: int = 8000
    frame_queue_size: int = 2
    """Bounded queue depth; when full, oldest frame is dropped (backpressure)."""

    max_jpeg_bytes: int = 350_000
    """Reject oversized JPEG payloads (~VGA quality JPEG is typically smaller)."""

    max_frame_width: int = 640
    max_frame_height: int = 480
    default_target_fps: float = 15.0
    """Client guidance only; server also timestamps each accepted frame."""

    worker_threads: int = 2
    default_algorithm: str = "pos"
    allowed_video_roots: tuple[str, ...] = ("data/eval", "data/recordings")
    """Recorded-video paths must resolve under one of these project-relative roots."""

    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    def to_public_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["allowed_video_roots"] = list(self.allowed_video_roots)
        d["cors_origins"] = list(self.cors_origins)
        return d


SETTINGS = BackendSettings()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
