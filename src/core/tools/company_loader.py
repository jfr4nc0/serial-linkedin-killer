"""Pandas-based company dataset loader and filter."""

from typing import Dict, List, Optional

import pandas as pd


def load_companies(csv_path: str) -> pd.DataFrame:
    """Load company dataset from CSV into a DataFrame."""
    return pd.read_csv(csv_path, dtype=str, on_bad_lines="skip").fillna("")


def get_unique_values(df: pd.DataFrame, column: str) -> List[str]:
    """Get sorted unique non-empty values for a column."""
    values = df[column].str.strip().unique().tolist()
    return sorted([v for v in values if v])


def filter_companies(
    df: pd.DataFrame,
    filters: Dict[str, List[str]],
) -> pd.DataFrame:
    """Filter companies by industry, country, size, etc.

    Args:
        df: Full company DataFrame
        filters: Dict mapping column names to lists of accepted values.
                 Empty list means no filter (accept all).

    Returns:
        Filtered DataFrame
    """
    result = df.copy()

    for column, values in filters.items():
        if not values or column not in result.columns:
            continue
        # Case-insensitive matching
        lower_values = [v.lower().strip() for v in values]
        result = result[result[column].str.lower().str.strip().isin(lower_values)]

    return result
