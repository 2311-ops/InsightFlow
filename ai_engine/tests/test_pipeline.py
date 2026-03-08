# Phase 3
"""Pipeline tests for InsightFlow Phase 3 AI engine."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest  

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_processing.clean_data import CleanResult, load_and_clean
from data_processing.feature_engineering import engineer_features
from data_processing.metrics import compute_metrics, metrics_to_summary


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Create a reproducible 30-row business dataset."""
    np.random.seed(42)
    n = 30
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="D"),
            "product": np.random.choice(["A", "B", "C"], size=n),
            "region": np.random.choice(["North", "South", "East", "West"], size=n),
            "units_sold": np.random.randint(10, 101, size=n),
            "unit_price": np.round(np.random.uniform(50, 500, size=n), 2),
            "revenue": np.round(np.random.uniform(1000, 50000, size=n), 2),
            "cost": np.round(np.random.uniform(500, 25000, size=n), 2),
            "profit": np.round(np.random.uniform(200, 20000, size=n), 2),
        }
    )


@pytest.fixture
def dirty_df() -> pd.DataFrame:
    """Create a small dataset with intentional data quality issues."""
    base = pd.DataFrame(
        {
            "Date": ["01/01/2024", "02/01/2024", None, "03/01/2024", "03/01/2024"],
            "Revenue": ["$1,234.56", "$2,500.00", None, "$3,300.00", "$3,300.00"],
            "Units": [10, None, 30, 40, 40],
            "Region": [" North", "South ", None, " East ", " East "],
        }
    )
    return base


def _write_df_csv(df: pd.DataFrame, tmp_path: Path, name: str) -> str:
    """Write a DataFrame to a CSV file and return path as string."""
    file_path = tmp_path / name
    df.to_csv(file_path, index=False)
    return str(file_path)


class TestCleanData:
    """Tests for load_and_clean and CleanResult behavior."""

    def test_returns_clean_result(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        result = load_and_clean(path)
        assert isinstance(result, CleanResult)

    def test_no_nulls_in_numeric(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        result = load_and_clean(path)
        for col in result.numeric_columns:
            assert int(result.df[col].isnull().sum()) == 0

    def test_column_names_normalized(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df.rename(columns={"units_sold": "Units Sold"}), tmp_path, "sample.csv")
        result = load_and_clean(path)
        assert all(col == col.lower() and " " not in col for col in result.df.columns)

    def test_duplicates_removed(self, dirty_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(dirty_df, tmp_path, "dirty.csv")
        result = load_and_clean(path)
        assert result.duplicates_removed > 0

    def test_currency_parsed(self, dirty_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(dirty_df, tmp_path, "dirty.csv")
        result = load_and_clean(path)
        assert "revenue" in result.numeric_columns

    def test_date_detected(self, dirty_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(dirty_df, tmp_path, "dirty.csv")
        result = load_and_clean(path)
        assert len(result.date_columns) > 0

    def test_whitespace_stripped(self, dirty_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(dirty_df, tmp_path, "dirty.csv")
        result = load_and_clean(path)
        values = result.df["region"].astype(str)
        assert not values.str.startswith(" ").any()

    def test_row_counts(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        result = load_and_clean(path)
        assert result.original_rows == len(sample_df)


class TestMetrics:
    """Tests for metrics report generation."""

    def test_returns_metrics_report(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        report = compute_metrics(load_and_clean(path))
        assert report is not None and isinstance(report.summary, dict)

    def test_row_count_in_summary(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        report = compute_metrics(load_and_clean(path))
        assert "row_count" in report.summary and report.summary["row_count"] > 0

    def test_numeric_stats_computed(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        report = compute_metrics(load_and_clean(path))
        keys = report.summary.keys()
        assert any(k.endswith("_sum") for k in keys)
        assert any(k.endswith("_mean") for k in keys)

    def test_trends_computed(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        report = compute_metrics(load_and_clean(path))
        assert isinstance(report.trends, list)

    def test_anomalies_list(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        report = compute_metrics(load_and_clean(path))
        assert isinstance(report.anomalies, list)

    def test_segments_list(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        report = compute_metrics(load_and_clean(path))
        assert isinstance(report.segments, list)

    def test_raw_metrics_serializable(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        report = compute_metrics(load_and_clean(path))
        json.dumps(report.raw_metrics)

    def test_correlations_between_minus1_and_1(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        report = compute_metrics(load_and_clean(path))
        assert all(-1.0 <= value <= 1.0 for value in report.correlations.values())


class TestFeatureEngineering:
    """Tests for feature engineering behavior."""

    def test_returns_clean_result(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        result = engineer_features(load_and_clean(path))
        assert isinstance(result, CleanResult)

    def test_adds_profit_margin(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        result = engineer_features(load_and_clean(path))
        if "profit_margin_pct" in result.df.columns:
            assert result.df["profit_margin_pct"].notna().sum() > 0

    def test_adds_time_features(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        base = load_and_clean(path)
        result = engineer_features(base)
        if base.date_columns:
            assert "month" in result.df.columns

    def test_no_new_nulls_introduced(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        before = load_and_clean(path)
        after = engineer_features(before)
        shared = [c for c in before.numeric_columns if c in after.numeric_columns]
        for col in shared:
            assert after.df[col].isnull().sum() <= before.df[col].isnull().sum()

    def test_more_numeric_cols_after_engineering(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        before = load_and_clean(path)
        after = engineer_features(before)
        assert len(after.numeric_columns) >= len(before.numeric_columns)


class TestFullPipeline:
    """End-to-end tests for full analytical pipeline."""

    def test_full_pipeline_no_crash(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        clean = load_and_clean(path)
        enriched = engineer_features(clean)
        report = compute_metrics(enriched)
        assert report.summary.get("row_count", 0) > 0
        assert len(report.raw_metrics) > 0

    def test_metrics_to_summary_string(self, sample_df: pd.DataFrame, tmp_path: Path):
        path = _write_df_csv(sample_df, tmp_path, "sample.csv")
        report = compute_metrics(engineer_features(load_and_clean(path)))
        summary = metrics_to_summary(report)
        assert isinstance(summary, str)
        assert len(summary) > 50
        assert "DATASET SUMMARY" in summary

