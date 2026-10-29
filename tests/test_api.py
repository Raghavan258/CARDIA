"""FastAPI session API and WebSocket protocol tests (no webcam)."""

from __future__ import annotations

import base64
import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.sessions import SessionManager
from sdk.measurement_state import MeasurementState


class FakeSDK:
    def __init__(self, algorithm: str = "pos"):
        self.algorithm = algorithm
        self.state = MeasurementState.IDLE
        self.calls = 0

    def start(self):
        self.state = MeasurementState.INITIALIZING

    def stop(self):
        self.state = MeasurementState.STOPPED

    def release(self):
        self.state = MeasurementState.STOPPED

    def process_frame(self, frame, timestamp_s=None):
        self.calls += 1
        self.state = MeasurementState.MEASURING
        return frame, {
            "bpm": 72.0,
            "bpm_raw": 72.0,
            "bpm_accepted": True,
            "last_accepted_bpm": 72.0,
            "last_accepted_bpm_age_s": 0.0,
            "state": self.state.value,
            "algorithm": self.algorithm,
            "effective_fps": 15.0,
            "spo2": None,
            "bp_sys": None,
            "bp_dia": None,
            "resp_rate": None,
            "quality": {
                "category": "good",
                "allow_new_hr_estimate": True,
                "rejection_reasons": [],
                "warnings": [],
            },
            "experimental": {
                "spo2": True,
                "bp_sys": True,
                "bp_dia": True,
                "resp_rate": True,
            },
        }


@pytest.fixture
def client():
    manager = SessionManager(sdk_factory=lambda alg: FakeSDK(alg))
    app = create_app(manager)
    with TestClient(app) as c:
        c.manager = manager
        yield c


def _jpeg_b64(width=64, height=48, color=128):
    img = np.full((height, width, 3), color, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return base64.b64encode(buf.tobytes()).decode("ascii")


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_config(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert "backend" in body and "quality" in body
    assert "frame_protocol" in body
    assert "disclaimer" in body


def test_create_and_stop_session(client):
    r = client.post("/api/sessions", json={"algorithm": "pos", "input_mode": "live"})
    assert r.status_code == 200
    data = r.json()
    sid = data["session_id"]
    assert data["ws_url"] == f"/ws/sessions/{sid}"
    assert data["state"] == MeasurementState.INITIALIZING.value

    g = client.get(f"/api/sessions/{sid}")
    assert g.status_code == 200

    s = client.post(f"/api/sessions/{sid}/stop")
    assert s.status_code == 200
    assert s.json()["stopped"] is True
    assert client.get(f"/api/sessions/{sid}").status_code == 404


def test_recorded_requires_path(client):
    r = client.post("/api/sessions", json={"input_mode": "recorded"})
    assert r.status_code == 400


def test_recorded_path_must_be_allowed(client, tmp_path):
    video = tmp_path / "outside.mp4"
    video.write_bytes(b"not-a-real-video")
    r = client.post(
        "/api/sessions",
        json={"input_mode": "recorded", "video_path": str(video)},
    )
    assert r.status_code in (403, 404, 500)


def test_websocket_live_frame_roundtrip(client):
    created = client.post("/api/sessions", json={"input_mode": "live"}).json()
    sid = created["session_id"]
    with client.websocket_connect(f"/ws/sessions/{sid}") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "status"
        ws.send_json(
            {
                "type": "frame",
                "timestamp_s": 0.0,
                "mime": "image/jpeg",
                "data_base64": _jpeg_b64(),
            }
        )
        # May receive vitals (and possibly more); wait for vitals
        msg = None
        for _ in range(10):
            msg = ws.receive_json()
            if msg.get("type") == "vitals":
                break
        assert msg is not None and msg["type"] == "vitals"
        assert msg["payload"]["bpm"] == 72.0
        assert "latency_ms" in msg
        ws.send_json({"type": "stop"})


def test_websocket_invalid_frame_rejected(client):
    created = client.post("/api/sessions", json={"input_mode": "live"}).json()
    sid = created["session_id"]
    with client.websocket_connect(f"/ws/sessions/{sid}") as ws:
        ws.receive_json()
        ws.send_json({"type": "frame", "timestamp_s": 0.0, "data_base64": ""})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "INVALID_FRAME"


def test_stop_unknown_session(client):
    assert client.post("/api/sessions/does-not-exist/stop").status_code == 404
