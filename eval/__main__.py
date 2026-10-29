"""CLI: python -m eval [--synthetic] [--video path] [--reference path]"""

from __future__ import annotations

import argparse
from pathlib import Path

from eval.compare import compare_synthetic
from eval.report import write_reports
from eval.runner import report_for_video


def main() -> None:
    parser = argparse.ArgumentParser(description="CARDIA evaluation runner")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Run deterministic synthetic baseline vs gated comparison",
    )
    parser.add_argument("--video", type=Path, help="Prerecorded video under data/eval")
    parser.add_argument("--reference", type=Path, help="Optional CSV timestamp_s,bpm")
    parser.add_argument("--algorithm", choices=("pos", "chrom"), default="pos")
    parser.add_argument("--no-gating", action="store_true")
    parser.add_argument("--bpm", type=float, default=72.0)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("eval/reports"),
        help="Output directory for JSON/Markdown reports",
    )
    args = parser.parse_args()

    if args.synthetic or not args.video:
        payload = compare_synthetic(
            reference_bpm=args.bpm,
            duration_s=args.duration,
            algorithm=args.algorithm,
        )
        paths = write_reports(payload, args.out, stem="synthetic_compare")
        print(f"Wrote {paths['json']}")
        print(f"Wrote {paths['markdown']}")
        gated = payload["improved_gated"]
        print(
            f"Gated coverage={gated['valid_estimate_coverage']:.3f} "
            f"reject={gated['rejection_rate']:.3f} "
            f"fps={gated['processing_fps']:.1f} "
            f"mae={gated['hr_mae']}"
        )
        return

    report = report_for_video(
        args.video,
        algorithm=args.algorithm,
        enable_quality_gating=not args.no_gating,
        reference_csv=args.reference,
    )
    payload = {
        "dataset": {
            "type": "recorded_video",
            "path": str(args.video),
            "reference": str(args.reference) if args.reference else None,
            "split": "evaluation",
            "limitation": (
                "Results depend on recording conditions. "
                "MAE/RMSE only present when --reference CSV is provided."
            ),
        },
        "report": report.to_dict(),
    }
    paths = write_reports(payload, args.out, stem=args.video.stem)
    print(f"Wrote {paths['json']}")
    print(f"Wrote {paths['markdown']}")


if __name__ == "__main__":
    main()
