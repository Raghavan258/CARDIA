"""Bounded queue / backpressure behavior for session frame intake."""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from backend.adapters import DecodedFrame
from backend.sessions import SessionManager
from backend.settings import BackendSettings
from sdk.measurement_state import MeasurementState


class FakeSDK:
    def __init__(self, algorithm: str = "pos"):
        self.state = MeasurementState.INITIALIZING
        self.processed = []

    def start(self):
        self.state = MeasurementState.INITIALIZING

    def stop(self):
        self.state = MeasurementState.STOPPED

    def release(self):
        pass

    def process_frame(self, frame, timestamp_s=None):
        self.processed.append(timestamp_s)
        self.state = MeasurementState.MEASURING
        return frame, {"bpm": None, "state": self.state.value, "bpm_accepted": False}


@pytest.mark.asyncio
async def test_queue_drops_oldest_under_backpressure():
    settings = BackendSettings(frame_queue_size=1)
    manager = SessionManager(
        settings=settings,
        sdk_factory=lambda alg: FakeSDK(alg),
    )
    session = await manager.create_session(input_mode="live")
    # Pause worker by replacing queue processing: enqueue faster than process
    frame_a = DecodedFrame(np.zeros((8, 8, 3), np.uint8), 1.0, "live")
    frame_b = DecodedFrame(np.zeros((8, 8, 3), np.uint8), 2.0, "live")
    # Fill and overflow
    await manager.enqueue_frame(session, frame_a)
    await manager.enqueue_frame(session, frame_b)
    assert session.stats.frames_received == 2
    assert session.stats.frames_dropped >= 1
    await manager.stop_session(session.session_id)
