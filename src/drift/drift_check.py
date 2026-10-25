"""Owner: Member 3 — Continuous Training: Evidently data drift monitor.

Compares a reference window against the current evaluation window across
numerical and categorical features. Writes drift_report.html and drift_metrics.json.
Always exits 0; the drift decision is recorded in the JSON payload.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.config import get_config


def compute_ks_drift(
    ref_col: pd.Series, curr_col: pd.Series, threshold: float = 0.05
) -> tuple[bool, float]:
    """Calculate drift using two-sample Kolmogorov-Smirnov test or empirical distance.

    Returns:
        (is_drifted, p_value_or_score)
    """
    try:
        from scipy import stats

        res = stats.ks_2samp(ref_col.dropna(), curr_col.dropna())
        p_val = float(res.pvalue)
        return p_val < threshold, p_val
    except Exception:
        # Fallback to normalized difference in means / medians if scipy not present
        r_mean = float(ref_col.mean())
        c_mean = float(curr_col.mean())
        r_std = float(ref_col.std()) or 1.0
        z_shift = abs(c_mean - r_mean) / r_std
        return z_shift > 1.5, round(float(z_shift), 4)


def run_drift_analysis(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    drift_threshold: float = 0.30,
    p_val_threshold: float = 0.05,
    html_output: Path | None = None,
    json_output: Path | None = None,
) -> dict[str, Any]:
    """Execute drift analysis using Evidently if installed, or high-fidelity statistical fallback.

    Args:
        reference_df: Baseline training or historical dataframe.
        current_df: Incoming evaluation or live prediction dataframe.
        drift_threshold: Share of drifted features required to flag overall dataset drift.
        p_val_threshold: Significance threshold for statistical tests.
        html_output: Destination path for HTML visualization.
        json_output: Destination path for machine-readable JSON metrics.

    Returns:
        Dict with drift_detected, share_drifted, and drifted_features list.
    """
    features_to_check = [
        col
        for col in [
            "pm25",
            "pm10",
            "no2",
            "so2",
            "co",
            "o3",
            "temperature",
            "humidity",
            "wind_speed",
            "aqi",
        ]
        if col in reference_df.columns and col in current_df.columns
    ]

    drift_results: dict[str, Any] = {}
    html_content = ""

    # Attempt Evidently Report
    evidently_success = False
    try:
        from evidently.metric_preset import DataDriftPreset
        from evidently.report import Report

        data_drift_report = Report(metrics=[DataDriftPreset()])
        data_drift_report.run(
            reference_data=reference_df[features_to_check],
            current_data=current_df[features_to_check],
        )

        if html_output:
            html_output.parent.mkdir(parents=True, exist_ok=True)
            data_drift_report.save_html(str(html_output))

        report_dict = data_drift_report.as_dict()
        preset_metrics = report_dict.get("metrics", [])[0].get("result", {})
        share_drifted = float(preset_metrics.get("share_of_drifted_columns", 0.0))
        drift_detected = bool(
            preset_metrics.get("dataset_drift", share_drifted >= drift_threshold)
        )

        drifted_cols = []
        for col_name, col_data in preset_metrics.get("drift_by_columns", {}).items():
            if col_data.get("drift_detected", False):
                drifted_cols.append(col_name)

        drift_results = {
            "drift_detected": drift_detected,
            "share_drifted": round(share_drifted, 4),
            "drifted_features": drifted_cols,
            "engine": "evidently",
        }
        evidently_success = True
    except Exception as e:
        print(
            f"[drift_check] Evidently report run skipped ({e}); using statistical drift engine."
        )

    if not evidently_success:
        # High-fidelity Statistical Fallback
        drifted_features: list[str] = []
        feature_scores: dict[str, dict[str, Any]] = {}

        for col in features_to_check:
            is_dr, score = compute_ks_drift(
                reference_df[col], current_df[col], threshold=p_val_threshold
            )
            feature_scores[col] = {
                "drift_detected": is_dr,
                "score": score,
                "ref_mean": float(reference_df[col].mean()),
                "curr_mean": float(current_df[col].mean()),
            }
            if is_dr:
                drifted_features.append(col)

        share_drifted = (
            len(drifted_features) / len(features_to_check) if features_to_check else 0.0
        )
        drift_detected = share_drifted >= drift_threshold

        drift_results = {
            "drift_detected": drift_detected,
            "share_drifted": round(share_drifted, 4),
            "drifted_features": drifted_features,
            "details": feature_scores,
            "engine": "statistical_ks",
        }

        # Generate standalone HTML report
        rows_html = "".join(
            f"<tr><td>{col}</td><td>{info['ref_mean']:.2f}</td><td>{info['curr_mean']:.2f}</td><td>{info['score']}</td><td style='color:{'red' if info['drift_detected'] else 'green'}'><b>{'DRIFT' if info['drift_detected'] else 'STABLE'}</b></td></tr>"
            for col, info in feature_scores.items()
        )
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>AQI Data Drift Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 30px; background: #f8fafc; color: #1e293b; }}
        .card {{ background: white; padding: 24px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); margin-bottom: 20px; }}
        h1 {{ color: #0f172a; margin-top: 0; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: bold; color: white; background: {'#ef4444' if drift_detected else '#10b981'}; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #f1f5f9; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>AQI Data Drift Assessment Report</h1>
        <p><b>Status:</b> <span class="badge">{'DRIFT DETECTED' if drift_detected else 'DATA STABLE'}</span></p>
        <p><b>Share Drifted:</b> {share_drifted * 100:.1f}% (Threshold: {drift_threshold * 100:.1f}%)</p>
        <p><b>Drifted Features:</b> {', '.join(drifted_features) if drifted_features else 'None'}</p>
    </div>
    <div class="card">
        <h2>Feature-Level Distribution Comparison</h2>
        <table>
            <tr><th>Feature</th><th>Ref Mean</th><th>Current Mean</th><th>P-value / Shift</th><th>Verdict</th></tr>
            {rows_html}
        </table>
    </div>
</body>
</html>"""
        if html_output:
            html_output.parent.mkdir(parents=True, exist_ok=True)
            html_output.write_text(html_content, encoding="utf-8")

    # Save JSON report
    if json_output:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(drift_results, f, indent=2)

    return drift_results


def parse_args() -> argparse.Namespace:
    cfg = get_config()
    default_ref = Path(cfg.paths.processed) / "features.csv"
    if not default_ref.exists():
        default_ref = Path(cfg.paths.raw) / "aqi_data.csv"

    default_curr = Path(cfg.paths.processed) / "drifted_data.csv"
    if not default_curr.exists():
        default_curr = default_ref

    default_json = Path(cfg.paths.reports) / "drift_metrics.json"
    default_html = Path(cfg.paths.reports) / "drift_report.html"

    parser = argparse.ArgumentParser(
        description="Monitor and compute data drift between reference and current AQI data"
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=default_ref,
        help="Path to baseline reference dataset",
    )
    parser.add_argument(
        "--current",
        type=Path,
        default=default_curr,
        help="Path to current/eval dataset",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=default_json,
        help="Path to write JSON output metrics",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=default_html,
        help="Path to write HTML visualization report",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=cfg.drift.share_drifted_threshold,
        help=f"Drifted feature share threshold (default: {cfg.drift.share_drifted_threshold})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(
        f"[drift_check] Running drift comparison: ref={args.reference}, curr={args.current}"
    )

    if not args.reference.exists():
        print(
            f"[drift_check] Reference file not found: {args.reference}. Exiting safely.",
            file=sys.stderr,
        )
        return 0

    ref_df = pd.read_csv(args.reference)
    curr_df = pd.read_csv(args.current) if args.current.exists() else ref_df.copy()

    results = run_drift_analysis(
        reference_df=ref_df,
        current_df=curr_df,
        drift_threshold=args.threshold,
        html_output=args.output_html,
        json_output=args.output_json,
    )

    print(
        f"[drift_check] Analysis complete: drift_detected={results['drift_detected']}, "
        f"share_drifted={results['share_drifted']}, drifted_features={results['drifted_features']}"
    )
    print(f"[drift_check] Metrics saved to: {args.output_json}")
    # Requirement: Always exits 0, decision is in the JSON
    return 0


if __name__ == "__main__":
    sys.exit(main())
