"""Report and table generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import PRIMARY_KPIS


def write_tables(
    summary_df: pd.DataFrame,
    delta_df: pd.DataFrame,
    repeat_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_df.to_csv(output_dir / "summary_per_json.csv", index=False)

    if not summary_df.empty:
        agg_cols = [c for c in PRIMARY_KPIS if c in summary_df.columns]
        summary_agg = (
            summary_df.groupby(["event", "serial", "phase", "position"], as_index=False)[agg_cols]
            .mean(numeric_only=True)
        )
        counts = (
            summary_df.groupby(["event", "serial", "phase", "position"])
            .size()
            .reset_index(name="n")
        )
        summary_agg = summary_agg.merge(
            counts, on=["event", "serial", "phase", "position"], how="left"
        )
        summary_agg.to_csv(output_dir / "summary_per_serial_position.csv", index=False)
    else:
        pd.DataFrame().to_csv(output_dir / "summary_per_serial_position.csv", index=False)

    delta_df.to_csv(output_dir / "delta_report.csv", index=False)
    repeat_df.to_csv(output_dir / "repeatability_report.csv", index=False)


def write_markdown_report(
    summary_df: pd.DataFrame,
    delta_df: pd.DataFrame,
    repeat_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Imatest SFRreg Batch Analysis Report")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Total JSON records: {len(summary_df)}")
    lines.append(f"- Delta pairs: {len(delta_df)}")
    lines.append(f"- Repeatability rows: {len(repeat_df)}")
    lines.append("")

    lines.append("## Output Files")
    lines.append("")
    lines.append("- summary_per_json.csv")
    lines.append("- summary_per_serial_position.csv")
    lines.append("- delta_report.csv")
    lines.append("- repeatability_report.csv")
    lines.append("- figures/")

    report_path = output_dir / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_chart_guide_korean(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Imatest SFRreg Chart Interpretation Guide")
    lines.append("")
    lines.append("## 1. Delta MTF50 (cy/px)")
    lines.append("- Purpose: Compare average change in MTF50 between Before and After by position.")
    lines.append("- Interpretation: Value > 0 means improvement in After, value < 0 means degradation.")
    lines.append("")
    lines.append("## 2. Repeatability: MTF50, High-band MTF")
    lines.append("- Purpose: Check measurement spread for repeated captures under same conditions.")
    lines.append("- Interpretation: Narrower box/whisker spread indicates better repeatability.")
    lines.append("")
    lines.append("## 3. MTF Curve Overlay")
    lines.append("- Purpose: Compare mean/worst/best MTF curves between Before and After.")
    lines.append("- Interpretation: If the After mean curve is generally above Before, performance improved.")
    lines.append("- Extra: MTF50 and MTF30 crossing frequencies are annotated.")
    lines.append("")
    lines.append("## 4. Risk Scatter")
    lines.append("- Purpose: Inspect MTF50 versus oversharpening risk.")
    lines.append("- Interpretation: Points above threshold indicate potential oversharpening risk.")
    lines.append("")
    lines.append("## 5. Before/After by Position (MTF50 + Angle)")
    lines.append("- Purpose: Compare Before/After MTF50 by chart position.")
    lines.append("- Interpretation: Labels above bars show `edge_angle_degrees` (degree value).")
    lines.append("- Note: Angle values indicate chart orientation and should be used as context.")
    lines.append("")
    lines.append("## 6. Delta Heatmap (Optional)")
    lines.append("- Purpose: Compare percent KPI changes by position at a glance.")
    lines.append("- Interpretation: Warmer color generally indicates improvement, cooler indicates degradation.")

    guide_path = output_dir / "chart_guide_ko.md"
    guide_path.write_text("\n".join(lines), encoding="utf-8")
