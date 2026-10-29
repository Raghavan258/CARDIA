"""Pydantic request/response models for the CARDIA API."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class SessionCreateRequest(BaseModel):
    algorithm: Literal["pos", "chrom"] = "pos"
    input_mode: Literal["live", "recorded"] = "live"
    video_path: Optional[str] = None
    max_width: int = Field(default=640, ge=160, le=1280)
    target_fps: float = Field(default=15.0, ge=5.0, le=30.0)

    @field_validator("video_path")
    @classmethod
    def recorded_requires_path(cls, v: Optional[str], info):
        return v


class SessionCreateResponse(BaseModel):
    session_id: str
    input_mode: str
    algorithm: str
    ws_url: str
    state: str
    frame_protocol: dict[str, Any]


class SessionStopResponse(BaseModel):
    session_id: str
    state: str
    stopped: bool


class HealthResponse(BaseModel):
    status: str
    version: str


class ErrorBody(BaseModel):
    detail: str


FRAME_PROTOCOL = {
    "transport": "websocket",
    "client_to_server": {
        "frame": {
            "type": "frame",
            "timestamp_s": "float seconds (client clock, monotonic preferred)",
            "mime": "image/jpeg",
            "data_base64": "JPEG bytes, base64-encoded",
            "notes": [
                "Prefer width <= 640 and target ~15 FPS",
                "Server drops oldest queued frames under backpressure",
            ],
        },
        "ping": {"type": "ping"},
        "stop": {"type": "stop"},
    },
    "server_to_client": {
        "vitals": {
            "type": "vitals",
            "payload": "same keys as RPPGSDK vitals dict plus latency_ms and server_ts",
        },
        "error": {"type": "error", "message": "string", "code": "optional"},
        "status": {"type": "status", "state": "measurement state", "message": "optional"},
    },
}
