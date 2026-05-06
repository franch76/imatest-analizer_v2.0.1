"""Before/after pairing utilities."""

from __future__ import annotations

import logging
from typing import List, Tuple

import numpy as np
import pandas as pd


def build_missing_pairs_report(df: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["event", "serial", "position"]
    before = df[df["phase"] == "Before"].set_index(key_cols)
    after = df[df["phase"] == "After"].set_index(key_cols)

    missing_before = after.index.difference(before.index)
    missing_after = before.index.difference(after.index)

    rows = []
    for key in missing_before:
        after_path = None
        if "path" in after.columns:
            try:
                after_path = after.loc[key, "path"]
            except Exception:
                after_path = None
        rows.append(
            {
                "event": key[0],
                "serial": key[1],
                "position": key[2],
                "missing_phase": "Before",
                "before_path": None,
                "after_path": after_path,
            }
        )
    for key in missing_after:
        before_path = None
        if "path" in before.columns:
            try:
                before_path = before.loc[key, "path"]
            except Exception:
                before_path = None
        rows.append(
            {
                "event": key[0],
                "serial": key[1],
                "position": key[2],
                "missing_phase": "After",
                "before_path": before_path,
                "after_path": None,
            }
        )

    return pd.DataFrame(rows)


logger = logging.getLogger(__name__)


def pair_before_after(df: pd.DataFrame, kpi_columns: List[str]) -> pd.DataFrame:
    key_cols = ["event", "serial", "position"]
    before = df[df["phase"] == "Before"].set_index(key_cols)
    after = df[df["phase"] == "After"].set_index(key_cols)

    missing_before = after.index.difference(before.index)
    missing_after = before.index.difference(after.index)

    if len(missing_before) or len(missing_after):
        logger.warning(
            "Pairing summary: missing Before=%d, missing After=%d (total Before=%d, After=%d)",
            len(missing_before),
            len(missing_after),
            len(before),
            len(after),
        )
        for key in list(missing_before)[:10]:
            logger.warning("Missing Before for key: %s", key)
        for key in list(missing_after)[:10]:
            logger.warning("Missing After for key: %s", key)

    common_index = before.index.intersection(after.index)
    before_common = before.loc[common_index]
    after_common = after.loc[common_index]

    delta_rows = []
    for idx in common_index:
        row = {
            "event": idx[0],
            "serial": idx[1],
            "position": idx[2],
        }
        for col in kpi_columns:
            b = before_common.loc[idx, col]
            a = after_common.loc[idx, col]
            row[f"{col}_before"] = b
            row[f"{col}_after"] = a
            try:
                row[f"{col}_abs_delta"] = a - b
                if not np.isfinite(a) or not np.isfinite(b) or b == 0:
                    row[f"{col}_rel_delta_pct"] = float("nan")
                else:
                    row[f"{col}_rel_delta_pct"] = (a / b - 1.0) * 100.0
            except Exception:
                row[f"{col}_abs_delta"] = float("nan")
                row[f"{col}_rel_delta_pct"] = float("nan")
        delta_rows.append(row)

    return pd.DataFrame(delta_rows)
