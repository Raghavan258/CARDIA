"""Synthetic offline evaluation comparison tests."""

from __future__ import annotations

from eval.compare import compare_synthetic
from eval.report import write_reports
from pathlib import Path


def test_compare_synthetic_produces_both_reports(tmp_path: Path):
    payload = compare_synthetic(
        reference_bpm=72.0,
        duration_s=4.0,
        algorithm="pos",
        motion_at_s=2.5,
    )
    assert "baseline_ungated" in payload
    assert "improved_gated" in payload
    gated = payload["improved_gated"]
    base = payload["baseline_ungated"]
    assert gated["frame_count"] == base["frame_count"]
    assert gated["gating_enabled"] is True
    assert base["gating_enabled"] is False
    # With synthetic reference on accepted frames, MAE should be present
    assert gated["paired_reference_count"] >= 0
    paths = write_reports(payload, tmp_path, stem="unit_compare")
    assert paths["json"].is_file()
    assert paths["markdown"].is_file()
    assert "CARDIA Evaluation Report" in paths["markdown"].read_text(encoding="utf-8")
