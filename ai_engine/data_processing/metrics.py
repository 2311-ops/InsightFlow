# Phase 3
"""Metrics computation and summarization for InsightFlow."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import isfinite

import numpy as np
import pandas as pd

from data_processing.clean_data import CleanResult


@dataclass
class AnomalyInfo:
    """Detected anomaly details for one numeric column and method."""

    column: str
    method: str
    count: int
    pct: float
    examples: list[float]


@dataclass
class TrendInfo:
    """Monthly trend summary for one numeric column."""

    column: str
    period: str
    growth_pct: float
    direction: str
    data_points: list[dict]


@dataclass
class SegmentInfo:
    """Segment performance summary for one categorical-numeric pair."""

    group_column: str
    metric_column: str
    segments: list[dict]
    top_segment: dict


@dataclass
class MetricsReport:
    """Aggregate metrics object for downstream LLM and API use."""

    summary: dict
    trends: list[TrendInfo]
    anomalies: list[AnomalyInfo]
    segments: list[SegmentInfo]
    correlations: dict[str, float]
    raw_metrics: dict


def _round_num(value: float) -> float:
    """Round numeric values to 2 decimals while handling NaN safely."""
    if not isfinite(float(value)):
        return 0.0
    return round(float(value), 2)


def _basic_stats(df: pd.DataFrame, numeric_cols: list[str]) -> dict:
    """Compute row/column counts and per-column aggregate stats."""
    stats: dict[str, int | float] = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
    }
    for col in numeric_cols:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            stats[f"{col}_sum"] = 0.0
            stats[f"{col}_mean"] = 0.0
            stats[f"{col}_median"] = 0.0
            stats[f"{col}_std"] = 0.0
            stats[f"{col}_min"] = 0.0
            stats[f"{col}_max"] = 0.0
            continue
        stats[f"{col}_sum"] = _round_num(series.sum())
        stats[f"{col}_mean"] = _round_num(series.mean())
        stats[f"{col}_median"] = _round_num(series.median())
        stats[f"{col}_std"] = _round_num(series.std(ddof=1) if len(series) > 1 else 0.0)
        stats[f"{col}_min"] = _round_num(series.min())
        stats[f"{col}_max"] = _round_num(series.max())
    return stats


def _detect_anomalies(df: pd.DataFrame, numeric_cols: list[str]) -> list[AnomalyInfo]:
    """Detect anomalies using Z-score and IQR rules."""
    results: list[AnomalyInfo] = []

    for col in numeric_cols:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 10:
            continue

        mean = float(series.mean())
        std = float(series.std(ddof=1))

        z_outliers = pd.Series([], dtype=float)
        if std > 0:
            z_scores = (series - mean) / std
            z_outliers = series[z_scores.abs() > 3]

        z_count = int(len(z_outliers))
        if z_count > 0:
            results.append(
                AnomalyInfo(
                    column=col,
                    method="zscore",
                    count=z_count,
                    pct=round((z_count / len(series)) * 100, 2),
                    examples=[float(v) for v in z_outliers.head(5).tolist()],
                )
            )

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        iqr_outliers = series[(series < lower) | (series > upper)]
        iqr_count = int(len(iqr_outliers))

        if iqr_count > 0 and iqr_count != z_count:
            results.append(
                AnomalyInfo(
                    column=col,
                    method="iqr",
                    count=iqr_count,
                    pct=round((iqr_count / len(series)) * 100, 2),
                    examples=[float(v) for v in iqr_outliers.head(5).tolist()],
                )
            )

    return results


def _compute_trends(df: pd.DataFrame, date_cols: list[str], numeric_cols: list[str]) -> list[TrendInfo]:
    """Compute monthly growth trends using the first date column."""
    if not date_cols or not numeric_cols:
        return []

    date_col = date_cols[0]
    work = df.copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])
    if work.empty:
        return []

    work = work.sort_values(date_col)
    work["_period"] = work[date_col].dt.to_period("M")

    results: list[TrendInfo] = []
    for col in numeric_cols[:5]:
        series = pd.to_numeric(work[col], errors="coerce")
        grouped = series.groupby(work["_period"]).sum(min_count=1).dropna()
        if len(grouped) < 2:
            continue

        first_val = float(grouped.iloc[0])
        last_val = float(grouped.iloc[-1])
        if first_val == 0:
            growth_pct = 0.0
        else:
            growth_pct = ((last_val - first_val) / abs(first_val)) * 100

        direction = "flat"
        if growth_pct > 2:
            direction = "up"
        elif growth_pct < -2:
            direction = "down"

        data_points = [
            {"period": str(period), "value": round(float(value), 2)}
            for period, value in grouped.items()
        ]

        results.append(
            TrendInfo(
                column=col,
                period="monthly",
                growth_pct=round(float(growth_pct), 2),
                direction=direction,
                data_points=data_points,
            )
        )

    return results


def _compute_segments(df: pd.DataFrame, cat_cols: list[str], numeric_cols: list[str]) -> list[SegmentInfo]:
    """Compute grouped segment stats for low-cardinality categorical columns."""
    if not cat_cols or not numeric_cols:
        return []

    valid_cat_cols = [
        col for col in cat_cols if df[col].nunique(dropna=False) <= 20
    ][:3]

    results: list[SegmentInfo] = []
    for group_col in valid_cat_cols:
        for metric_col in numeric_cols[:3]:
            grouped = (
                df.groupby(group_col, dropna=False)[metric_col]
                .agg(["sum", "mean", "count"])
                .reset_index()
            )
            if grouped.empty:
                continue

            total_sum = float(grouped["sum"].sum())
            segments: list[dict] = []
            for _, row in grouped.iterrows():
                sum_val = float(row["sum"])
                share_pct = 0.0 if total_sum == 0 else (sum_val / total_sum) * 100
                segments.append(
                    {
                        group_col: row[group_col],
                        "sum": round(sum_val, 2),
                        "mean": round(float(row["mean"]), 2),
                        "count": int(row["count"]),
                        "share_pct": round(float(share_pct), 2),
                    }
                )

            segments.sort(key=lambda x: x["sum"], reverse=True)
            top_segment = segments[0] if segments else {}

            results.append(
                SegmentInfo(
                    group_column=group_col,
                    metric_column=metric_col,
                    segments=segments,
                    top_segment=top_segment,
                )
            )

    return results


def _compute_correlations(df: pd.DataFrame, numeric_cols: list[str]) -> dict[str, float]:
    """Compute strong pairwise correlations among numeric columns."""
    if len(numeric_cols) < 2:
        return {}

    corr_df = df[numeric_cols].corr(numeric_only=True)
    results: dict[str, float] = {}
    for col_a, col_b in combinations(numeric_cols, 2):
        value = corr_df.loc[col_a, col_b]
        if pd.isna(value):
            continue
        if abs(float(value)) > 0.5:
            results[f"{col_a}_vs_{col_b}"] = round(float(value), 3)
    return results


def compute_metrics(clean_result: CleanResult) -> MetricsReport:
    """Compute a full metrics report from cleaned data."""
    df = clean_result.df
    numeric_cols = clean_result.numeric_columns
    date_cols = clean_result.date_columns
    cat_cols = clean_result.categorical_columns

    summary = _basic_stats(df, numeric_cols)
    anomalies = _detect_anomalies(df, numeric_cols)
    trends = _compute_trends(df, date_cols, numeric_cols)
    segments = _compute_segments(df, cat_cols, numeric_cols)
    correlations = _compute_correlations(df, numeric_cols)

    raw_metrics: dict[str, int | float | str | bool] = {}
    raw_metrics.update(summary)

    for trend in trends:
        raw_metrics[f"{trend.column}_growth_pct_{trend.period}"] = trend.growth_pct
        raw_metrics[f"{trend.column}_trend"] = trend.direction

    for anomaly in anomalies:
        raw_metrics[f"{anomaly.column}_anomaly_{anomaly.method}_count"] = anomaly.count

    for key, value in correlations.items():
        raw_metrics[f"corr_{key}"] = value

    return MetricsReport(
        summary=summary,
        trends=trends,
        anomalies=anomalies,
        segments=segments,
        correlations=correlations,
        raw_metrics=raw_metrics,
    )


def metrics_to_summary(report: MetricsReport) -> str:
    """Format the metrics report into a rich text block for LLM prompts."""
    lines: list[str] = []

    lines.append("DATASET SUMMARY")
    lines.append(f"- Rows: {report.summary.get('row_count', 0)}")
    lines.append(f"- Columns: {report.summary.get('column_count', 0)}")

    lines.append("\nKEY METRICS")
    for key in sorted(report.summary.keys()):
        if key in {"row_count", "column_count"}:
            continue
        lines.append(f"- {key}: {report.summary[key]}")

    lines.append("\nTRENDS")
    if report.trends:
        arrow_map = {"up": "?", "down": "?", "flat": "?"}
        for trend in report.trends:
            arrow = arrow_map.get(trend.direction, "?")
            lines.append(
                f"- {trend.column}: {arrow} {trend.growth_pct}% ({trend.period})"
            )
    else:
        lines.append("- No significant trend data available")

    lines.append("\nANOMALIES DETECTED")
    if report.anomalies:
        for anomaly in report.anomalies:
            lines.append(
                f"- {anomaly.column} ({anomaly.method}): {anomaly.count} ({anomaly.pct}%)"
            )
    else:
        lines.append("- No anomalies detected")

    lines.append("\nTOP SEGMENTS")
    if report.segments:
        for segment in report.segments[:5]:
            lines.append(
                f"- {segment.group_column} x {segment.metric_column}: {segment.top_segment}"
            )
    else:
        lines.append("- No segment breakdown available")

    lines.append("\nCORRELATIONS")
    if report.correlations:
        for key, value in report.correlations.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No strong correlations (>|0.5|)")

    return "\n".join(lines)

