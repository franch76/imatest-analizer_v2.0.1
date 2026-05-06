"""Shared analysis runner for CLI and GUI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd

from .config import PRIMARY_KPIS
from .io_readers import (
    load_records,
    load_records_from_files,
    load_records_from_files_for_phase,
    load_records_from_phase_root,
)
from .kpi_compute import compute_kpis
from .pairing import pair_before_after, build_missing_pairs_report
from .repeatability import compute_repeatability
from .plots import (
    plot_delta_mtf50,
    plot_optional_heatmap,
    plot_repeatability,
    plot_mtf_curve_overlay,
    plot_mtf_curve_overlay_by_position,
    plot_risk_scatter,
    plot_before_after_by_position,
    plot_before_after_by_position_per_serial,
)
from .report import write_markdown_report, write_tables, write_chart_guide_korean


logger = logging.getLogger(__name__)


def build_summary(records) -> tuple[pd.DataFrame, Dict[str, List[dict]]]:
    rows = []
    curves = {"Before": [], "After": []}

    for record in records:
        kpis, curve_data = compute_kpis(record.data)
        row = {
            "event": record.event,
            "serial": record.serial,
            "phase": record.phase,
            "position": record.position,
            "repeat_index": record.repeat_index,
            "path": str(record.path),
        }
        row.update(kpis)
        rows.append(row)

        if curve_data.get("freq") is not None and curve_data.get("mtf") is not None:
            curve_entry = dict(curve_data)
            curve_entry["position"] = record.position
            curve_entry["serial"] = record.serial
            curves[record.phase].append(curve_entry)

    return pd.DataFrame(rows), curves


def _run_analysis_records(
    records,
    output_path: Path,
    cancel_check: Callable[[], bool],
    exclude_missing_pairs: bool = False,
) -> None:
    if not records:
        logger.warning("No records loaded. Aborting analysis.")
        return

    if cancel_check():
        logger.info("Analysis cancelled")
        return

    logger.info("Computing KPIs")
    summary_df, curve_data = build_summary(records)
    if cancel_check():
        logger.info("Analysis cancelled")
        return

    kpi_columns = [c for c in PRIMARY_KPIS if c in summary_df.columns]

    logger.info("Pairing before/after")
    delta_df = pair_before_after(summary_df, kpi_columns)
    if cancel_check():
        logger.info("Analysis cancelled")
        return

    missing_pairs_df = build_missing_pairs_report(summary_df)
    if not missing_pairs_df.empty:
        missing_pairs_df.to_csv(output_path / "missing_pairs_report.csv", index=False)

    if exclude_missing_pairs:
        key_cols = ["event", "serial", "position"]
        before_keys = set(
            tuple(x) for x in summary_df[summary_df["phase"] == "Before"][key_cols].to_numpy()
        )
        after_keys = set(
            tuple(x) for x in summary_df[summary_df["phase"] == "After"][key_cols].to_numpy()
        )
        common_keys = before_keys.intersection(after_keys)
        if common_keys:
            summary_df = summary_df[
                summary_df.apply(
                    lambda r: (r["event"], r["serial"], r["position"]) in common_keys,
                    axis=1,
                )
            ].copy()

            common_sp = {(k[1], k[2]) for k in common_keys}

            def _filter_curves(phase_items):
                return [
                    item
                    for item in phase_items
                    if (item.get("serial"), item.get("position")) in common_sp
                ]

            curve_data = {
                "Before": _filter_curves(curve_data.get("Before", [])),
                "After": _filter_curves(curve_data.get("After", [])),
            }

    logger.info("Computing repeatability")
    repeat_df = compute_repeatability(summary_df, kpi_columns)
    if cancel_check():
        logger.info("Analysis cancelled")
        return

    logger.info("Writing tables and reports")
    write_tables(summary_df, delta_df, repeat_df, output_path)
    write_markdown_report(summary_df, delta_df, repeat_df, output_path)
    write_chart_guide_korean(output_path)
    if cancel_check():
        logger.info("Analysis cancelled")
        return

    figures_dir = output_path / "figures"
    logger.info("Generating figures")
    plot_delta_mtf50(delta_df, figures_dir)
    plot_repeatability(summary_df, figures_dir)
    plot_mtf_curve_overlay(curve_data, figures_dir)
    plot_mtf_curve_overlay_by_position(curve_data, figures_dir)
    plot_risk_scatter(summary_df, figures_dir)
    plot_optional_heatmap(delta_df, figures_dir)
    plot_before_after_by_position(summary_df, figures_dir)
    plot_before_after_by_position_per_serial(summary_df, figures_dir)

    logger.info("Analysis complete. Output saved to %s", output_path)


def run_analysis(
    input_path: Path | List[Path],
    output_path: Path,
    cancel_check: Optional[Callable[[], bool]] = None,
    exclude_missing_pairs: bool = False,
) -> None:
    if cancel_check is None:
        cancel_check = lambda: False

    if isinstance(input_path, list):
        logger.info("Loading records from %d file(s)", len(input_path))
        records = load_records_from_files(input_path)
    else:
        logger.info("Loading records from %s", input_path)
        records = load_records(input_path)

    _run_analysis_records(records, output_path, cancel_check, exclude_missing_pairs)


def run_analysis_split(
    before_input: Path | List[Path],
    after_input: Path | List[Path],
    output_path: Path,
    cancel_check: Optional[Callable[[], bool]] = None,
    exclude_missing_pairs: bool = False,
) -> None:
    if cancel_check is None:
        cancel_check = lambda: False

    records = []

    if isinstance(before_input, list):
        logger.info("Loading BEFORE records from %d file(s)", len(before_input))
        records.extend(load_records_from_files_for_phase(before_input, "Before"))
    else:
        logger.info("Loading BEFORE records from %s", before_input)
        records.extend(load_records_from_phase_root(before_input, "Before"))

    if isinstance(after_input, list):
        logger.info("Loading AFTER records from %d file(s)", len(after_input))
        records.extend(load_records_from_files_for_phase(after_input, "After"))
    else:
        logger.info("Loading AFTER records from %s", after_input)
        records.extend(load_records_from_phase_root(after_input, "After"))

    _run_analysis_records(records, output_path, cancel_check, exclude_missing_pairs)
