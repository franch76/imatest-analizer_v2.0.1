"""Repeatability calculations."""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from .config import REPEATABILITY


def _cv_pct(mean: float, std: float) -> float:
    if mean == 0 or np.isnan(mean) or np.isnan(std):
        return float("nan")
    return float(std / mean * 100.0)


def _grade(cv_pct: float) -> str:
    if np.isnan(cv_pct):
        return "N/A"
    if cv_pct <= REPEATABILITY.green_cv_pct:
        return "Green"
    if cv_pct <= REPEATABILITY.yellow_cv_pct:
        return "Yellow"
    return "Red"


def compute_repeatability(df: pd.DataFrame, kpi_columns: List[str]) -> pd.DataFrame:
    group_cols = ["event", "serial", "phase", "position"]

    rows = []
    for keys, group in df.groupby(group_cols):
        base = dict(zip(group_cols, keys))
        for col in kpi_columns:
            series = group[col].astype(float)
            values = series.to_numpy(dtype=float)
            finite = values[np.isfinite(values)]
            mean = float(np.mean(finite)) if finite.size else float("nan")
            std = float(np.std(finite, ddof=1)) if finite.size > 1 else float("nan")
            cv = _cv_pct(mean, std)
            row = base.copy()
            row.update(
                {
                    "kpi": col,
                    "mean": mean,
                    "std": std,
                    "cv_pct": cv,
                    "min": float(np.min(finite)) if finite.size else float("nan"),
                    "max": float(np.max(finite)) if finite.size else float("nan"),
                    "grade": _grade(cv),
                    "n": len(series),
                }
            )
            rows.append(row)

    return pd.DataFrame(rows)
