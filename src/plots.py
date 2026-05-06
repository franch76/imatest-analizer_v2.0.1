"""Matplotlib plotting utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .config import HEATMAP, RISK


logger = logging.getLogger(__name__)

plt.rcParams.update(
    {
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
    }
)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def plot_delta_mtf50(delta_df: pd.DataFrame, output_dir: Path) -> None:
    if delta_df.empty:
        logger.warning("Delta dataframe is empty; skipping delta plot")
        return
    _ensure_dir(output_dir)

    col = "mtf50_cy_px_worst_abs_delta"
    if col not in delta_df:
        logger.warning("Missing delta column: %s", col)
        return

    order = HEATMAP.position_order
    data = delta_df.groupby("position")[col].mean()
    data = data.reindex(order)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(data.index, data.values, color="#2b8cbe")
    ax.set_title("Delta MTF50 (cy/px) Before vs After")
    ax.set_ylabel("After - Before (cy/px)")
    ax.set_xlabel("Position")
    ax.axhline(0, color="#333333", linewidth=1)
    ax.tick_params(axis="x", labelrotation=15)
    fig.tight_layout()
    fig.savefig(output_dir / "delta_MTF50.png", dpi=150)
    plt.close(fig)


def plot_repeatability(df: pd.DataFrame, output_dir: Path) -> None:
    _ensure_dir(output_dir)
    for kpi, fname in [
        ("mtf50_cy_px_worst", "repeatability_MTF50.png"),
        ("high_band_mean_mtf", "repeatability_HighBand.png"),
    ]:
        if kpi not in df:
            logger.warning("Missing KPI column for repeatability plot: %s", kpi)
            continue

        fig, ax = plt.subplots(figsize=(9, 4.5))
        phases = ["Before", "After"]
        data = [df[df["phase"] == phase][kpi].dropna().values for phase in phases]
        ax.boxplot(data, labels=phases, showmeans=True)
        ax.set_title(f"Repeatability: {kpi}")
        ax.set_ylabel(kpi)
        fig.tight_layout()
        fig.savefig(output_dir / fname, dpi=150)
        plt.close(fig)


def _mtf_level_freq(freq: np.ndarray, mtf: np.ndarray, level: float) -> float:
    if len(freq) < 2:
        return float("nan")
    for i in range(len(mtf) - 1):
        if mtf[i] >= level and mtf[i + 1] <= level:
            x0, x1 = freq[i], freq[i + 1]
            y0, y1 = mtf[i], mtf[i + 1]
            if y0 == y1:
                return float(x0)
            return float(x0 + (level - y0) * (x1 - x0) / (y1 - y0))
    return float("nan")


def _missing_summary_from_df(df: pd.DataFrame) -> tuple[int, int, int]:
    key_cols = ["event", "serial", "position"]
    before = df[df["phase"] == "Before"].set_index(key_cols)
    after = df[df["phase"] == "After"].set_index(key_cols)
    missing_before = after.index.difference(before.index)
    missing_after = before.index.difference(after.index)
    return len(missing_before), len(missing_after), len(before), len(after)


def _missing_summary_from_curves(curves: Dict[str, List[Dict[str, np.ndarray]]]) -> tuple[int, int, int]:
    def _keys(phase: str):
        items = curves.get(phase, [])
        return {(item.get("serial"), item.get("position")) for item in items}

    before = _keys("Before")
    after = _keys("After")
    missing_before = after.difference(before)
    missing_after = before.difference(after)
    return len(missing_before), len(missing_after), len(before), len(after)


def _add_missing_banner(ax: plt.Axes, missing_before: int, missing_after: int, before_total: int, after_total: int) -> None:
    if missing_before == 0 and missing_after == 0:
        return
    ax.text(
        0.01,
        0.98,
        f"Missing Before: {missing_before} / Missing After: {missing_after}\n"
        f"Before total: {before_total}, After total: {after_total}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7,
        color="#7f0000",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff0f0", edgecolor="#d7301f"),
    )


def _plot_mtf_curve_overlay(
    curves: Dict[str, List[Dict[str, np.ndarray]]],
    output_dir: Path,
    filename: str,
    title: str,
) -> None:
    _ensure_dir(output_dir)

    def _aggregate(phase: str):
        items = curves.get(phase, [])
        if not items:
            return None
        min_len = min(len(item["freq"]) for item in items)
        if min_len < 2:
            return None
        freq = items[0]["freq"][:min_len]
        mtf_stack = np.vstack([item["mtf"][:min_len] for item in items])
        mean_curve = np.nanmean(mtf_stack, axis=0)
        worst_curve = np.nanmin(mtf_stack, axis=0)
        best_curve = np.nanmax(mtf_stack, axis=0)
        return freq, mean_curve, worst_curve, best_curve, mtf_stack

    before = _aggregate("Before")
    after = _aggregate("After")
    if not before or not after:
        logger.warning("Insufficient curve data for overlay plot: %s", title)
        return

    fig, ax = plt.subplots(figsize=(9, 5))

    mtf50_color = "#1f78b4"
    mtf30_color = "#ff7f00"
    list_entries = []

    def _add_entry(label: str, value: float, color: str, bold: bool, indent: int) -> None:
        if np.isfinite(value):
            list_entries.append(
                {
                    "text": f"{label}: {value:.3f}",
                    "color": color,
                    "bold": bold,
                    "indent": indent,
                }
            )

    mtf_levels = {}
    for phase, data, color in [
        ("Before", before, "#1f78b4"),
        ("After", after, "#e31a1c"),
    ]:
        freq, mean_curve, worst_curve, best_curve, mtf_stack = data
        for curve in mtf_stack:
            ax.plot(freq, curve, color=color, alpha=0.15, linewidth=0.8)

        ax.plot(freq, mean_curve, label=f"{phase} Mean", color=color, linewidth=2.0)
        ax.plot(freq, worst_curve, linestyle="--", label=f"{phase} Worst", color=color, linewidth=1.0)
        ax.plot(freq, best_curve, linestyle=":", label=f"{phase} Best", color=color, linewidth=1.0)

        mtf50_freq = _mtf_level_freq(freq, mean_curve, 0.5)
        mtf30_freq = _mtf_level_freq(freq, mean_curve, 0.3)
        mtf_levels[phase] = {
            "mtf50": mtf50_freq,
            "mtf30": mtf30_freq,
        }
        if np.isfinite(mtf50_freq):
            ax.axvline(mtf50_freq, color=mtf50_color, linestyle=":", linewidth=0.8)
            ax.axhline(0.5, color=mtf50_color, linestyle=":", linewidth=0.6, alpha=0.7)
        if np.isfinite(mtf30_freq):
            ax.axvline(mtf30_freq, color=mtf30_color, linestyle="-.", linewidth=1.0)
            ax.axhline(0.3, color=mtf30_color, linestyle="-.", linewidth=0.6, alpha=0.7)

        _add_entry(f"{phase} Mean MTF50", mtf50_freq, mtf50_color, True, 0)
        mtf50_best = _mtf_level_freq(freq, best_curve, 0.5)
        mtf50_worst = _mtf_level_freq(freq, worst_curve, 0.5)
        _add_entry(f"{phase} Best MTF50", mtf50_best, mtf50_color, False, 1)
        _add_entry(f"{phase} Worst MTF50", mtf50_worst, mtf50_color, False, 1)

        _add_entry(f"{phase} Mean MTF30", mtf30_freq, mtf30_color, True, 0)
        mtf30_best = _mtf_level_freq(freq, best_curve, 0.3)
        mtf30_worst = _mtf_level_freq(freq, worst_curve, 0.3)
        _add_entry(f"{phase} Best MTF30", mtf30_best, mtf30_color, False, 1)
        _add_entry(f"{phase} Worst MTF30", mtf30_worst, mtf30_color, False, 1)

    if "Before" in mtf_levels and "After" in mtf_levels:
        before_mtf50 = mtf_levels["Before"]["mtf50"]
        after_mtf50 = mtf_levels["After"]["mtf50"]
        before_mtf30 = mtf_levels["Before"]["mtf30"]
        after_mtf30 = mtf_levels["After"]["mtf30"]
        if np.isfinite(before_mtf50) and np.isfinite(after_mtf50):
            delta = after_mtf50 - before_mtf50
            ax.annotate(
                f"Delta MTF50: {delta:.3f}",
                xy=(0.98, 0.95),
                xycoords="axes fraction",
                ha="right",
                va="top",
                fontsize=7,
                color="#333333",
            )
        if np.isfinite(before_mtf30) and np.isfinite(after_mtf30):
            delta = after_mtf30 - before_mtf30
            ax.annotate(
                f"Delta MTF30: {delta:.3f}",
                xy=(0.98, 0.90),
                xycoords="axes fraction",
                ha="right",
                va="top",
                fontsize=7,
                color="#333333",
            )

    ax.set_title(title)
    ax.set_xlabel("Frequency (cy/px)")
    ax.set_ylabel("MTF")
    ax.legend()
    missing_before, missing_after, before_total, after_total = _missing_summary_from_curves(curves)
    _add_missing_banner(ax, missing_before, missing_after, before_total, after_total)

    # Value list in empty space to avoid label overlap
    y_start = 0.82
    y_step = 0.038
    for idx, entry in enumerate(list_entries):
        y = y_start - idx * y_step
        if y < 0.05:
            break
        x = 0.98 - entry["indent"] * 0.05
        ax.text(
            x,
            y,
            entry["text"],
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=7,
            color=entry["color"],
            fontweight="bold" if entry["bold"] else "normal",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="none", alpha=0.65),
        )
    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=150)
    plt.close(fig)


def plot_mtf_curve_overlay(curves: Dict[str, List[Dict[str, np.ndarray]]], output_dir: Path) -> None:
    _plot_mtf_curve_overlay(
        curves,
        output_dir,
        "MTF_curve_overlay.png",
        "MTF Curve Overlay",
    )


def plot_mtf_curve_overlay_by_position(
    curves: Dict[str, List[Dict[str, np.ndarray]]],
    output_dir: Path,
) -> None:
    position_labels = {
        "L0.7": "L0.7feild",
        "L0.5": "L0.5feild",
        "C": "center",
        "R0.5": "R0.5 feild",
        "R0.7": "R0.7feild",
    }

    for position in HEATMAP.position_order:
        filtered = {
            phase: [item for item in curves.get(phase, []) if item.get("position") == position]
            for phase in ("Before", "After")
        }
        title_pos = position_labels.get(position, position)
        _plot_mtf_curve_overlay(
            filtered,
            output_dir,
            f"MTF_curve_overlay_{position}.png",
            f"MTF Curve Overlay - {title_pos}",
        )


def plot_risk_scatter(df: pd.DataFrame, output_dir: Path) -> None:
    _ensure_dir(output_dir)
    x_col = "mtf50_cy_px_worst"
    y_col = "overSharpening_Pct_worst"
    if x_col not in df or y_col not in df:
        logger.warning("Missing columns for risk scatter")
        return

    x = df[x_col].astype(float)
    y = df[y_col].astype(float)
    risk = y > RISK.oversharpening_pct

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(x[~risk], y[~risk], c="#2ca25f", label="OK", alpha=0.7)
    ax.scatter(x[risk], y[risk], c="#de2d26", label="Risk", alpha=0.7)
    ax.axhline(RISK.oversharpening_pct, color="#444444", linestyle="--")
    ax.set_xlabel("MTF50 (cy/px)")
    ax.set_ylabel("OverSharpening %")
    ax.set_title("Risk Scatter")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "risk_scatter.png", dpi=150)
    plt.close(fig)


def plot_optional_heatmap(delta_df: pd.DataFrame, output_dir: Path) -> None:
    if delta_df.empty:
        return

    _ensure_dir(output_dir)
    positions = HEATMAP.position_order
    metrics = [
        "mtf50_cy_px_worst_rel_delta_pct",
        "high_band_mean_mtf_rel_delta_pct",
        "mtf_curve_auc_rel_delta_pct",
    ]
    available_metrics = [m for m in metrics if m in delta_df]
    if not available_metrics:
        return

    heat = []
    labels = []
    for metric in available_metrics:
        row = []
        for pos in positions:
            subset = delta_df[delta_df["position"] == pos][metric].astype(float)
            values = subset.to_numpy(dtype=float)
            finite = values[np.isfinite(values)]
            row.append(float(np.mean(finite)) if finite.size else float("nan"))
        heat.append(row)
        labels.append(metric)

    heat = np.array(heat, dtype=float)

    fig, ax = plt.subplots(figsize=(8, 3 + len(labels) * 0.4))
    im = ax.imshow(heat, aspect="auto", cmap="coolwarm")
    ax.set_xticks(range(len(positions)), positions)
    ax.set_yticks(range(len(labels)), labels)
    fig.colorbar(im, ax=ax, label="Delta %")
    ax.set_title("Delta Heatmap (Optional)")
    fig.tight_layout()
    fig.savefig(output_dir / "delta_heatmap.png", dpi=150)
    plt.close(fig)


def plot_before_after_by_position(df: pd.DataFrame, output_dir: Path) -> None:
    _ensure_dir(output_dir)
    kpi = "mtf50_cy_px_worst"
    angle_col = "edge_angle_degrees_mean"
    if kpi not in df:
        fallback = "mtf50_mean"
        if fallback in df:
            logger.warning("Missing KPI column %s; using %s instead", kpi, fallback)
            kpi = fallback
        else:
            logger.warning("Missing KPI column for before/after position plot: %s", kpi)
            return

    summary = (
        df.groupby(["position", "phase"], as_index=False)[[kpi, angle_col]]
        .mean(numeric_only=True)
    )
    order = HEATMAP.position_order
    positions = [p for p in order if p in summary["position"].unique()]
    if not positions:
        positions = sorted(summary["position"].unique())
        logger.warning("Position order mismatch; using data-driven positions: %s", positions)
    phases = ["Before", "After"]

    fig, ax = plt.subplots(figsize=(10, 5))
    width = 0.35
    x = np.arange(len(positions))

    for idx, phase in enumerate(phases):
        phase_data = summary[summary["phase"] == phase].set_index("position")
        values = [phase_data.loc[pos, kpi] if pos in phase_data.index else np.nan for pos in positions]
        bars = ax.bar(x + (idx - 0.5) * width, values, width=width, label=phase)

        # Plot all measurements per position (same format, with jitter)
        for j, pos in enumerate(positions):
            samples = df[(df["position"] == pos) & (df["phase"] == phase)][kpi].dropna().values
            if samples.size:
                jitter = (np.random.rand(samples.size) - 0.5) * (width * 0.35)
                ax.scatter(
                    np.full(samples.size, x[j] + (idx - 0.5) * width) + jitter,
                    samples,
                    color=bars.patches[0].get_facecolor() if bars.patches else "#333333",
                    s=8,
                    alpha=0.35,
                    linewidths=0,
                    zorder=3,
                )

        # Annotate angle above bars
        angles = [
            phase_data.loc[pos, angle_col] if pos in phase_data.index else np.nan
            for pos in positions
        ]
        for xi, val, ang in zip(x + (idx - 0.5) * width, values, angles):
            if np.isfinite(val) and np.isfinite(ang):
                ax.text(
                    xi,
                    val,
                    f"{ang:.1f}°",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    rotation=0,
                )

        # Mean trend line removed per request

    ax.set_title("MTF50 (cy/px) Before vs After by Position")
    ax.set_xlabel("Position")
    ax.set_ylabel("MTF50 (cy/px)")
    ax.set_xticks(x, positions)
    ax.tick_params(axis="x", labelrotation=15)
    ax.legend()
    missing_before, missing_after, before_total, after_total = _missing_summary_from_df(df)
    _add_missing_banner(ax, missing_before, missing_after, before_total, after_total)

    # Info box
    n_total = len(df)
    text = f"Records: {n_total}\\nAngle shown on bars (edge_angle_degrees)"
    ax.text(
        0.99,
        0.98,
        text,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f0f0", edgecolor="#cccccc"),
    )

    fig.tight_layout()
    fig.savefig(output_dir / "before_after_mtf50_by_position.png", dpi=150)
    plt.close(fig)


def plot_before_after_by_position_per_serial(df: pd.DataFrame, output_dir: Path) -> None:
    _ensure_dir(output_dir)
    kpi = "mtf50_cy_px_worst"
    angle_col = "edge_angle_degrees_mean"
    if kpi not in df:
        fallback = "mtf50_mean"
        if fallback in df:
            logger.warning("Missing KPI column %s; using %s instead", kpi, fallback)
            kpi = fallback
        else:
            logger.warning("Missing KPI column for per-serial plot: %s", kpi)
            return

    order = HEATMAP.position_order
    for serial, serial_df in df.groupby("serial"):
        summary = (
            serial_df.groupby(["position", "phase"], as_index=False)[[kpi, angle_col]]
            .mean(numeric_only=True)
        )
        positions = [p for p in order if p in summary["position"].unique()]
        if not positions:
            positions = sorted(summary["position"].unique())
            logger.warning(
                "Position order mismatch for serial %s; using data-driven positions: %s",
                serial,
                positions,
            )
        if not positions:
            continue

        phases = ["Before", "After"]
        fig, ax = plt.subplots(figsize=(10, 5))
        width = 0.35
        x = np.arange(len(positions))

        for idx, phase in enumerate(phases):
            phase_data = summary[summary["phase"] == phase].set_index("position")
            values = [
                phase_data.loc[pos, kpi] if pos in phase_data.index else np.nan
                for pos in positions
            ]
            bars = ax.bar(x + (idx - 0.5) * width, values, width=width, label=phase)

            angles = [
                phase_data.loc[pos, angle_col] if pos in phase_data.index else np.nan
                for pos in positions
            ]
            for xi, val, ang in zip(x + (idx - 0.5) * width, values, angles):
                if np.isfinite(val) and np.isfinite(ang):
                    ax.text(
                        xi,
                        val,
                        f"{ang:.1f}°",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        rotation=0,
                    )

            # Mean trend line removed per request

        ax.set_title(f"MTF50 (cy/px) Before vs After by Position - Serial {serial}")
        ax.set_xlabel("Position")
        ax.set_ylabel("MTF50 (cy/px)")
        ax.set_xticks(x, positions)
        ax.tick_params(axis="x", labelrotation=15)
        ax.legend()
        missing_before, missing_after, before_total, after_total = _missing_summary_from_df(serial_df)
        _add_missing_banner(ax, missing_before, missing_after, before_total, after_total)

        text = f"Serial: {serial}\\nAngle shown on bars (edge_angle_degrees)"
        ax.text(
            0.99,
            0.98,
            text,
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=8,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f0f0", edgecolor="#cccccc"),
        )

        fig.tight_layout()
        fig.savefig(output_dir / f"before_after_mtf50_by_position_serial_{serial}.png", dpi=150)
        plt.close(fig)
