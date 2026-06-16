"""Shared utilities for data validation and summaries."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
import pandas as pd


def clip(value: float, lower: float, upper: float) -> float:
    """Clip a scalar value to a closed interval."""

    return float(np.clip(value, lower, upper))


def logistic(value: float) -> float:
    """Numerically stable logistic transform for scalar values."""

    return float(1.0 / (1.0 + np.exp(-np.clip(value, -35, 35))))


def records_to_dataframe(records: Sequence[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    """Convert JSON-style records into a pandas DataFrame."""

    if isinstance(records, pd.DataFrame):
        return records.copy()
    if not records:
        raise ValueError("No data records were provided.")
    df = pd.DataFrame.from_records(records)
    if df.empty:
        raise ValueError("Data records produced an empty DataFrame.")
    return df


def validate_columns(df: pd.DataFrame, columns: Iterable[str], context: str = "data") -> None:
    """Raise a helpful error if required columns are missing."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        available = ", ".join(map(str, df.columns))
        raise ValueError(
            f"Missing required column(s) for {context}: {missing}. Available columns: {available}."
        )


def clean_numeric_frame(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """Select columns, coerce to numeric, and drop incomplete rows."""

    validate_columns(df, columns, context="numeric analysis")
    numeric = df.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce")
    return numeric.replace([np.inf, -np.inf], np.nan).dropna()


def dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame into JSON-serializable records."""

    out = df.copy()
    for column in out.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
        out[column] = out[column].dt.strftime("%Y-%m-%d")
    out = out.replace({np.nan: None})
    return out.to_dict(orient="records")


def summarize_binary(series: pd.Series) -> dict[str, Any]:
    """Return compact counts for a binary-like series."""

    counts = series.value_counts(dropna=False).sort_index()
    return {str(k): int(v) for k, v in counts.items()}


def infer_binary(series: pd.Series) -> bool:
    """Return True if a numeric series appears binary."""

    non_missing = pd.Series(series).dropna().unique()
    if len(non_missing) == 0:
        return False
    return set(non_missing).issubset({0, 1, 0.0, 1.0, False, True})


def numeric_summary(series: pd.Series) -> dict[str, float | int]:
    """Return mean, sd, min, and max for numeric data."""

    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return {"n": 0}
    return {
        "n": int(numeric.shape[0]),
        "mean": float(numeric.mean()),
        "sd": float(numeric.std(ddof=1)) if numeric.shape[0] > 1 else 0.0,
        "min": float(numeric.min()),
        "max": float(numeric.max()),
    }
