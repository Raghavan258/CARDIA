"""Write evaluation reports as JSON and Markdown."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_reports(payload: dict[str, Any], out_dir: Path, stem: str = "eval_report") -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        **payload,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": (
            "Not a medical device. Metrics are for engineering evaluation only."
        ),
    }
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def _to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# CARDIA Evaluation Report",
        "",
        f"Generated: `{payload.get('generated_at')}`",
        "",
        payload.get("disclaimer", ""),
        "",
        "## Dataset",
        "",
    ]
    ds = payload.get("dataset") or {}
    for k, v in ds.items():
        lines.append(f"- **{k}**: {v}")

    for key, title in (
        ("baseline_ungated", "Baseline (quality gating off)"),
        ("improved_gated", "Improved (quality gating on)"),
        ("report", "Report"),
    ):
        block = payload.get(key)
        if not block:
            continue
        lines.extend(["", f"## {title}", ""])
        lines.extend(_report_table(block))

    delta = payload.get("delta")
    if delta:
        lines.extend(["", "## Delta (gated − baseline)", ""])
        for k, v in delta.items():
            lines.append(f"- **{k}**: {v}")

    lines.extend(["", "## Notes", ""])
    for note in (payload.get("notes") or []):
        lines.append(f"- {note}")
    if not payload.get("notes"):
        for key in ("baseline_ungated", "improved_gated", "report"):
            block = payload.get(key) or {}
            for note in block.get("notes") or []:
                lines.append(f"- ({key}) {note}")

    lines.append("")
    return "\n".join(lines)


def _report_table(block: dict[str, Any]) -> list[str]:
    keys = [
        "name",
        "mode",
        "algorithm",
        "gating_enabled",
        "duration_s",
        "frame_count",
        "processing_fps",
        "mean_latency_ms",
        "face_track_fraction",
        "valid_estimate_coverage",
        "rejection_rate",
        "hr_mae",
        "hr_rmse",
        "hr_bias",
        "paired_reference_count",
    ]
    lines = ["| Metric | Value |", "|---|---|"]
    for k in keys:
        if k in block:
            lines.append(f"| `{k}` | {block[k]} |")
    qf = block.get("quality_fractions") or {}
    for k, v in qf.items():
        lines.append(f"| quality_fraction.{k} | {v} |")
    reasons = block.get("rejection_reason_counts") or {}
    for k, v in reasons.items():
        lines.append(f"| rejection.{k} | {v} |")
    return lines
