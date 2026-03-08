# Phase 3
"""Data loading and cleaning utilities for InsightFlow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd


@dataclass
class CleanResult:
    """Container for cleaned dataframe and cleaning metadata."""

    df: pd.DataFrame
    original_rows: int
    cleaned_rows: int
    dropped_rows: int
    duplicates_removed: int
    columns_parsed: list[str]
    date_columns: list[str]
    numeric_columns: list[str]
    categorical_columns: list[str]
    warnings: list[str]


def load_file(file_path: str) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        last_error: Exception | None = None
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        if last_error:
            raise last_error
        return pd.read_csv(file_path)

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file_path)

    raise ValueError(f"Unsupported file type: {suffix}")


def _normalize_column_name(name: str) -> str:
    """Normalize column names for consistent downstream processing."""
    value = name.strip().lower()
    value = re.sub(r"[\s\-]+", "_", value)
    value = re.sub(r"\W", "", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "column"


def _safe_numeric_fill(series: pd.Series) -> pd.Series:
    """Fill missing numeric values with median, falling back to 0."""
    median = series.median()
    if pd.isna(median):
        median = 0.0
    return series.fillna(median)


def load_and_clean(file_path: str) -> CleanResult:
    """Load a dataset file and run the Phase 3 cleaning pipeline."""
    df = load_file(file_path)
    original_rows = len(df)

    # 1) Normalize columns.
    normalized_cols: list[str] = []
    used_names: dict[str, int] = {}
    for raw_col in df.columns:
        base = _normalize_column_name(str(raw_col))
        if base in used_names:
            used_names[base] += 1
            base = f"{base}_{used_names[base]}"
        else:
            used_names[base] = 0
        normalized_cols.append(base)
    df.columns = normalized_cols

    # 2) Drop fully empty rows/columns.
    df = df.dropna(how="all").dropna(axis=1, how="all")

    # 3) Remove duplicates.
    before_dupes = len(df)
    df = df.drop_duplicates()
    duplicates_removed = before_dupes - len(df)

    columns_parsed: list[str] = []
    date_columns: list[str] = []
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    warnings: list[str] = []

    date_pattern = re.compile(r"(?:\b\d{4}-\d{1,2}(?:-\d{1,2})?\b)|(?:\b\d{1,2}/\d{1,2}/\d{2,4}\b)")
    currency_pattern = re.compile(r"(?:[$€£¥])|(?:\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b)")

    # 4) Detect and process columns by priority.
    for col in df.columns:
        columns_parsed.append(col)
        series = df[col]
        non_null = series.dropna()

        if pd.api.types.is_numeric_dtype(series):
            df[col] = _safe_numeric_fill(pd.to_numeric(series, errors="coerce"))
            numeric_columns.append(col)
            continue

        non_null_count = len(non_null)
        if non_null_count == 0:
            df[col] = series.fillna("Unknown").astype(str).str.strip()
            categorical_columns.append(col)
            continue

        as_str = non_null.astype(str).str.strip()

        date_matches = as_str.str.contains(date_pattern, regex=True).sum()
        if date_matches / non_null_count > 0.5:
            df[col] = pd.to_datetime(series, errors="coerce")
            date_columns.append(col)
            continue

        currency_matches = as_str.str.contains(currency_pattern, regex=True).sum()
        if currency_matches / non_null_count > 0.4:
            converted = (
                series.astype(str)
                .str.replace(r"[$€£¥,]", "", regex=True)
                .str.replace(r"\(([^)]+)\)", r"-\1", regex=True)
            )
            numeric_series = pd.to_numeric(converted, errors="coerce")
            df[col] = _safe_numeric_fill(numeric_series)
            numeric_columns.append(col)
            continue

        coerced = pd.to_numeric(as_str, errors="coerce")
        numeric_ratio = coerced.notna().sum() / non_null_count
        if numeric_ratio > 0.7:
            numeric_series = pd.to_numeric(series, errors="coerce")
            df[col] = _safe_numeric_fill(numeric_series)
            numeric_columns.append(col)
            continue

        df[col] = series.fillna("Unknown").astype(str).str.strip()
        categorical_columns.append(col)

    # 5) Null warnings.
    for col in df.columns:
        null_pct = float(df[col].isna().mean())
        if null_pct > 0.3:
            warnings.append(f"Column '{col}' has {null_pct * 100:.1f}% null values")

    cleaned_rows = len(df)
    dropped_rows = max(0, original_rows - cleaned_rows)

    return CleanResult(
        df=df,
        original_rows=original_rows,
        cleaned_rows=cleaned_rows,
        dropped_rows=dropped_rows,
        duplicates_removed=duplicates_removed,
        columns_parsed=columns_parsed,
        date_columns=date_columns,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        warnings=warnings,
    )

