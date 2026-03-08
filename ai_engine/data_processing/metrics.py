"""
metrics.py
Computes KPIs and business metrics from a cleaned DataFrame.
Returns a flat dict ready to pass to the LLM.
"""

import pandas as pd
import numpy as np
from typing import Any


def detect_numeric_cols(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=[np.number]).columns.tolist()


def compute_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """
    Auto-detect column types and compute relevant metrics.
    Returns a dictionary of metric_name → value.
    """
    metrics: dict[str, Any] = {}
    num_cols = detect_numeric_cols(df)

    metrics["row_count"] = int(len(df))
    metrics["column_count"] = int(len(df.columns))
    metrics["columns"] = df.columns.tolist()

    for col in num_cols:
        safe = col.lower().replace(" ", "_")
        series = df[col].dropna()
        metrics[f"{safe}_sum"] = round(float(series.sum()), 2)
        metrics[f"{safe}_mean"] = round(float(series.mean()), 2)
        metrics[f"{safe}_median"] = round(float(series.median()), 2)
        metrics[f"{safe}_std"] = round(float(series.std()), 2)
        metrics[f"{safe}_min"] = round(float(series.min()), 2)
        metrics[f"{safe}_max"] = round(float(series.max()), 2)

    # Detect date column → time-series growth
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if date_cols and num_cols:
        date_col = date_cols[0]
        df_sorted = df.sort_values(date_col)
        for col in num_cols[:3]:  # limit to 3 for brevity
            safe = col.lower().replace(" ", "_")
            first_val = df_sorted[col].iloc[0]
            last_val = df_sorted[col].iloc[-1]
            if first_val and first_val != 0:
                growth = round(((last_val - first_val) / abs(first_val)) * 100, 2)
                metrics[f"{safe}_growth_pct"] = growth

    # Anomaly: values beyond 3σ
    anomalies: dict[str, int] = {}
    for col in num_cols:
        mean = df[col].mean()
        std = df[col].std()
        outliers = df[(df[col] < mean - 3 * std) | (df[col] > mean + 3 * std)]
        if len(outliers) > 0:
            anomalies[col] = int(len(outliers))
    if anomalies:
        metrics["anomaly_columns"] = anomalies

    return metrics


def metrics_to_summary(metrics: dict[str, Any]) -> str:
    """Convert metrics dict to a human-readable summary string for the LLM."""
    lines = ["Business Metrics Summary:"]
    for key, value in metrics.items():
        if isinstance(value, dict):
            for k, v in value.items():
                lines.append(f"  - {key}.{k}: {v}")
        elif isinstance(value, list):
            lines.append(f"  - {key}: {', '.join(str(v) for v in value)}")
        else:
            lines.append(f"  - {key}: {value}")
    return "\n".join(lines)
