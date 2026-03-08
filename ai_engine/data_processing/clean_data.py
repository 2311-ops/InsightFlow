"""
clean_data.py
Ingests CSV/Excel files and returns a clean pandas DataFrame.
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_file(file_path: str) -> pd.DataFrame:
    """Load CSV or Excel file into a DataFrame."""
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(file_path)
    elif path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standard cleaning pipeline:
    1. Drop fully empty rows/columns
    2. Strip whitespace from string columns
    3. Parse date columns automatically
    4. Fill numeric NaN with column median
    5. Fill categorical NaN with 'Unknown'
    """
    # 1. Drop empty rows & cols
    df = df.dropna(how="all").dropna(axis=1, how="all")

    # 2. Strip strings
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # 3. Try to parse date-like columns
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                pass

    # 4. Fill numeric NaN with median
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].fillna(df[num_cols].median())

    # 5. Fill categorical NaN
    df[str_cols] = df[str_cols].fillna("Unknown")

    return df


def load_and_clean(file_path: str) -> pd.DataFrame:
    """One-shot: load and clean a dataset file."""
    df = load_file(file_path)
    return clean(df)
