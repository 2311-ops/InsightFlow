# Phase 3
"""Feature engineering utilities for InsightFlow."""

from __future__ import annotations

from data_processing.clean_data import CleanResult
import numpy as np
import pandas as pd


def _find_col(df: pd.DataFrame, keywords: list[str]) -> str | None:
    """Return the first column containing any keyword (case-insensitive)."""
    lowered = {col: col.lower() for col in df.columns}
    for col, low_col in lowered.items():
        for keyword in keywords:
            if keyword in low_col:
                return col
    return None


def engineer_features(clean_result: CleanResult) -> CleanResult:
    """Add derived business features and return an updated CleanResult."""
    df = clean_result.df.copy()
    added_features: list[str] = []

    revenue_col = _find_col(df, ["revenue", "sales", "income", "total"])
    cost_col = _find_col(df, ["cost", "expense", "cogs"])
    profit_col = _find_col(df, ["profit", "margin", "net"])
    units_col = _find_col(df, ["units", "quantity", "qty", "count"])

    if revenue_col and cost_col and not profit_col:
        df["profit"] = pd.to_numeric(df[revenue_col], errors="coerce") - pd.to_numeric(
            df[cost_col], errors="coerce"
        )
        added_features.append("profit")
        profit_col = "profit"

    if revenue_col and profit_col:
        revenue_series = pd.to_numeric(df[revenue_col], errors="coerce").replace(0, np.nan)
        profit_series = pd.to_numeric(df[profit_col], errors="coerce")
        df["profit_margin_pct"] = (profit_series / revenue_series) * 100
        added_features.append("profit_margin_pct")

    if revenue_col and units_col:
        revenue_series = pd.to_numeric(df[revenue_col], errors="coerce")
        units_series = pd.to_numeric(df[units_col], errors="coerce").replace(0, np.nan)
        df["revenue_per_unit"] = revenue_series / units_series
        added_features.append("revenue_per_unit")

    if clean_result.date_columns:
        date_col = clean_result.date_columns[0]
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col)

        df["month"] = df[date_col].dt.month
        df["quarter"] = df[date_col].dt.quarter
        df["day_of_week"] = df[date_col].dt.dayofweek
        added_features.extend(["month", "quarter", "day_of_week"])

        if revenue_col:
            revenue_series = pd.to_numeric(df[revenue_col], errors="coerce")
            rolling_col = f"{revenue_col}_rolling_7d"
            delta_col = f"{revenue_col}_mom_delta"
            df[rolling_col] = revenue_series.rolling(window=7, min_periods=1).mean()
            df[delta_col] = revenue_series.diff()
            added_features.extend([rolling_col, delta_col])

    numeric_columns = list(clean_result.numeric_columns)
    for col in added_features:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]) and col not in numeric_columns:
            numeric_columns.append(col)

    warnings = list(clean_result.warnings)
    null_ratio = float(df.isnull().mean().mean())
    warnings.append(f"Data quality score: {(1 - null_ratio) * 100:.1f}%")
    feature_list = ", ".join(added_features) if added_features else "none"
    warnings.append(f"Added {len(added_features)} engineered features: {feature_list}")

    return CleanResult(
        df=df,
        original_rows=clean_result.original_rows,
        cleaned_rows=len(df),
        dropped_rows=clean_result.dropped_rows,
        duplicates_removed=clean_result.duplicates_removed,
        columns_parsed=clean_result.columns_parsed,
        date_columns=clean_result.date_columns,
        numeric_columns=numeric_columns,
        categorical_columns=clean_result.categorical_columns,
        warnings=warnings,
    )

