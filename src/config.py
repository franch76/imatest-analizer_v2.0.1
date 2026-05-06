"""Configuration defaults for Imatest SFRreg batch analysis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RepeatabilityThresholds:
    green_cv_pct: float = 2.0
    yellow_cv_pct: float = 5.0


@dataclass(frozen=True)
class RiskThresholds:
    oversharpening_pct: float = 10.0


@dataclass(frozen=True)
class HeatmapConfig:
    position_order: tuple = ("L0.7", "L0.5", "C", "R0.5", "R0.7")


REPEATABILITY = RepeatabilityThresholds()
RISK = RiskThresholds()
HEATMAP = HeatmapConfig()

# KPI columns to prioritize in reports
PRIMARY_KPIS = (
    "mtf50_cy_px_worst",
    "secondary_1_worst",
    "secondary_2_worst",
    "mtf_area_pknorm_worst",
    "high_band_mean_mtf",
    "mtf_curve_auc",
    "overSharpening_Pct_worst",
    "overshoot_Pct_worst",
    "undershoot_Pct_worst",
    "riseDistPxls_worst",
    "LSF_PW50_pxls_worst",
    "CA_areaPxls_worst",
    "CA_R_G_Pixels_worst",
    "CA_B_G_Pixels_worst",
    "mean_ROI_worst",
    "mean_ROI_level_normalized",
    "edge_angle_degrees_mean",
)
