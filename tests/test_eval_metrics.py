"""Evaluation metric aggregation tests."""

from __future__ import annotations

from eval.metrics import FrameRecord, summarize


def test_summarize_without_reference_omits_accuracy():
    records = [
        FrameRecord(0.0, True, "initializing", [], False, None, None),
        FrameRecord(1.0, True, "good", [], True, 72.0, 72.0),
        FrameRecord(2.0, True, "poor", ["EXCESSIVE_MOTION"], False, None, 90.0),
    ]
    report = summarize(
        records,
        name="t",
        mode="unit",
        algorithm="pos",
        gating_enabled=True,
        wall_time_s=0.5,
    )
    assert report.hr_mae is None
    assert report.paired_reference_count == 0
    assert report.valid_estimate_coverage == 1 / 3
    assert report.rejection_rate == 1 / 3
    assert "EXCESSIVE_MOTION" in report.rejection_reason_counts


def test_summarize_with_reference_computes_mae_rmse():
    records = [
        FrameRecord(0.0, True, "good", [], True, 70.0, 70.0, reference_bpm=72.0),
        FrameRecord(1.0, True, "good", [], True, 74.0, 74.0, reference_bpm=72.0),
    ]
    report = summarize(
        records,
        name="t",
        mode="unit",
        algorithm="pos",
        gating_enabled=True,
        wall_time_s=0.2,
    )
    assert report.paired_reference_count == 2
    assert report.hr_mae == 2.0
    assert abs(report.hr_rmse - 2.0) < 1e-9
    assert report.hr_bias == 0.0
