"""KPI extraction and curve-derived metrics."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np


logger = logging.getLogger(__name__)


def _as_array(value) -> Optional[np.ndarray]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        arr = np.asarray(value, dtype=float)
        if arr.ndim > 1:
            # Reduce ROI/2D arrays to 1D by mean across rows
            arr = np.nanmean(arr, axis=0)
        return arr
    return None


def _nan() -> float:
    return float("nan")


def get_value(results: dict, key: str) -> float:
    value = results.get(key)
    if value is None:
        logger.warning("Missing JSON key: %s", key)
        return _nan()
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (list, tuple)):
        if not value:
            return _nan()
        return float(np.nanmean(value))
    return _nan()


def get_worst_summary(results: dict, key: str) -> float:
    value = results.get(key)
    if value is None:
        logger.warning("Missing JSON key: %s", key)
        return _nan()
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (list, tuple)):
        if not value:
            return _nan()
        return float(value[-1])
    return _nan()


def get_worst_with_fallbacks(results: dict, keys: Tuple[str, ...]) -> float:
    for key in keys:
        value = results.get(key)
        if value is None:
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, (list, tuple)) and value:
            return float(value[-1])
    logger.warning("Missing JSON key(s): %s", ", ".join(keys))
    return _nan()


def _find_mtf_curve(results: dict) -> Optional[np.ndarray]:
    if "MTF_Interpolated" in results:
        return _as_array(results.get("MTF_Interpolated"))
    for key in results:
        if key.startswith("MTFinterp"):
            return _as_array(results.get(key))
    return None


def _find_freq_curve(results: dict) -> Optional[np.ndarray]:
    return _as_array(results.get("MTFfreq_CP"))


def compute_kpis(record: dict) -> Tuple[Dict[str, float], Dict[str, np.ndarray]]:
    results = record.get("sfrregResults", {})
    if not isinstance(results, dict):
        results = {}

    kpis: Dict[str, float] = {}
    curves: Dict[str, np.ndarray] = {}

    # ROI-level metrics (mean if list)
    kpis["mtf50_mean"] = get_value(results, "mtf50")
    kpis["mtf30_mean"] = get_value(results, "mtf30")
    kpis["mtf20_mean"] = get_value(results, "mtf20")
    kpis["mtf10_mean"] = get_value(results, "mtf10")

    # ROI-level worst (cy/px) using mtf50 list last element when available
    kpis["mtf50_cy_px_worst"] = get_worst_with_fallbacks(
        results, ("mtf50",)
    )

    # Summary worst values
    kpis["mtf50_lwph_worst"] = get_worst_summary(results, "mtf50_LWPH_summary")
    kpis["secondary_1_worst"] = get_worst_summary(results, "secondary_1_summary")
    kpis["secondary_2_worst"] = get_worst_summary(results, "secondary_2_summary")
    kpis["mtf_area_pknorm_worst"] = get_worst_summary(results, "MTF_Area_PkNorm_summary")

    # ISP / Risk metrics
    kpis["overSharpening_Pct_worst"] = get_worst_summary(
        results, "overSharpening_Pct_summary"
    )
    kpis["overshoot_Pct_worst"] = get_worst_summary(results, "overshoot_Pct_summary")
    kpis["undershoot_Pct_worst"] = get_worst_with_fallbacks(
        results,
        ("undershoot_Pct_summary", "undershootPct", "undershoot_Pct"),
    )
    kpis["riseDistPxls_worst"] = get_worst_summary(results, "riseDistPxls_summary")
    kpis["LSF_PW50_pxls_worst"] = get_worst_summary(
        results, "LSF_PW50_pxls_summary"
    )

    # Optical stability
    kpis["CA_areaPxls_worst"] = get_worst_summary(results, "CA_areaPxls_summary")
    kpis["CA_R_G_Pixels_worst"] = get_worst_summary(
        results, "CA_R_G_Pixels_summary"
    )
    kpis["CA_B_G_Pixels_worst"] = get_worst_summary(
        results, "CA_B_G_Pixels_summary"
    )

    # Exposure sanity
    kpis["mean_ROI_worst"] = get_worst_summary(results, "mean_ROI_summary")
    kpis["mean_ROI_level_normalized"] = get_value(
        results, "mean_ROI_level_normalized"
    )

    # Chart angle (degrees)
    kpis["edge_angle_degrees_mean"] = get_value(results, "edge_angle_degrees")

    # Curve metrics
    freq = _find_freq_curve(results)
    mtf = _find_mtf_curve(results)
    if freq is not None and mtf is not None and len(freq) == len(mtf):
        curves["freq"] = freq
        curves["mtf"] = mtf
        high_band = mtf[freq > 0.3]
        if high_band.size:
            kpis["high_band_mean_mtf"] = float(np.nanmean(high_band))
        else:
            kpis["high_band_mean_mtf"] = _nan()
        try:
            kpis["mtf_curve_auc"] = float(np.trapz(mtf, freq))
        except Exception:
            kpis["mtf_curve_auc"] = _nan()
    elif freq is not None and mtf is not None:
        # Best-effort alignment when lengths mismatch: trim to min length
        min_len = min(len(freq), len(mtf))
        if min_len > 1:
            freq_trim = freq[:min_len]
            mtf_trim = mtf[:min_len]
            curves["freq"] = freq_trim
            curves["mtf"] = mtf_trim
            high_band = mtf_trim[freq_trim > 0.3]
            if high_band.size:
                kpis["high_band_mean_mtf"] = float(np.nanmean(high_band))
            else:
                kpis["high_band_mean_mtf"] = _nan()
            try:
                kpis["mtf_curve_auc"] = float(np.trapz(mtf_trim, freq_trim))
            except Exception:
                kpis["mtf_curve_auc"] = _nan()
            logger.warning("MTF curve length mismatch; trimmed to %d", min_len)
        else:
            logger.warning("MTF curve length mismatch")
            kpis["high_band_mean_mtf"] = _nan()
            kpis["mtf_curve_auc"] = _nan()
    else:
        if freq is None or mtf is None:
            logger.warning("Missing MTF curve data in JSON record")
        else:
            logger.warning("MTF curve length mismatch")
        kpis["high_band_mean_mtf"] = _nan()
        kpis["mtf_curve_auc"] = _nan()

    return kpis, curves
