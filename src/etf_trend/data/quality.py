from __future__ import annotations
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DataQualityReport:
    """Report summarizing data quality issues found."""

    original_rows: int
    final_rows: int
    missing_filled: int
    outliers_detected: int
    symbols_with_issues: list[str]


def detect_outliers(
    prices: pd.DataFrame,
    max_daily_return: float = 0.5,
) -> pd.DataFrame:
    """
    Detect outliers based on extreme daily returns.

    Args:
        prices: DataFrame of prices with dates as index and symbols as columns.
        max_daily_return: Maximum allowed absolute daily return (default 50%).

    Returns:
        Boolean DataFrame where True indicates an outlier.
    """
    returns = prices.pct_change()
    outliers = returns.abs() > max_daily_return
    return outliers


def _interpolate_outliers(
    prices: pd.DataFrame,
    outliers: pd.DataFrame,
) -> pd.DataFrame:
    """Replace outlier values with linearly interpolated values."""
    prices_clean = prices.copy()
    prices_clean[outliers] = np.nan
    prices_clean = prices_clean.interpolate(method="linear", limit_direction="both")
    return prices_clean


def clean_prices(
    prices: pd.DataFrame,
    max_daily_return: float = 0.5,
    max_gap_days: int = 5,
    min_data_pct: float = 0.8,
) -> tuple[pd.DataFrame, DataQualityReport]:
    """
    Clean price data with comprehensive handling of missing values and outliers.

    Args:
        prices: DataFrame of prices with dates as index and symbols as columns.
        max_daily_return: Maximum allowed absolute daily return for outlier detection.
        max_gap_days: Maximum consecutive missing days to forward-fill.
        min_data_pct: Minimum percentage of non-null data required per symbol.

    Returns:
        Tuple of (cleaned prices DataFrame, DataQualityReport).
    """
    original_rows = len(prices)
    original_missing = prices.isna().sum().sum()

    # Step 1: Detect outliers
    outliers = detect_outliers(prices, max_daily_return)
    outlier_count = outliers.sum().sum()

    if outlier_count > 0:
        symbols_with_outliers = outliers.any()[outliers.any()].index.tolist()
        logger.warning(f"Detected {outlier_count} outliers in symbols: {symbols_with_outliers}")
        prices = _interpolate_outliers(prices, outliers)

    # Step 2: Forward fill with limit
    prices = prices.ffill(limit=max_gap_days)

    # Step 3: Backward fill remaining (for leading NaNs)
    prices = prices.bfill(limit=max_gap_days)

    # Step 4: Drop symbols with too much missing data
    data_pct = prices.notna().mean()
    valid_symbols = data_pct[data_pct >= min_data_pct].index.tolist()
    dropped_symbols = [s for s in prices.columns if s not in valid_symbols]

    if dropped_symbols:
        logger.warning(
            f"Dropping symbols with insufficient data (<{min_data_pct*100:.0f}%): {dropped_symbols}"
        )

    prices = prices[valid_symbols]

    # Step 5: Drop rows that still have any NaN
    prices = prices.dropna(how="any")

    # Build report
    report = DataQualityReport(
        original_rows=original_rows,
        final_rows=len(prices),
        missing_filled=original_missing - prices.isna().sum().sum(),
        outliers_detected=outlier_count,
        symbols_with_issues=dropped_symbols,
    )

    logger.info(
        f"Data cleaning complete: {report.original_rows} -> {report.final_rows} rows, "
        f"{report.outliers_detected} outliers fixed"
    )

    return prices, report


def validate_prices(prices: pd.DataFrame) -> list[str]:
    """
    Validate price data and return a list of issues found.

    Args:
        prices: DataFrame of prices with dates as index and symbols as columns.

    Returns:
        List of validation issue strings (empty if no issues).
    """
    issues = []

    # Check for empty DataFrame
    if prices.empty:
        issues.append("Price DataFrame is empty")
        return issues

    # Check for non-positive prices
    if (prices <= 0).any().any():
        bad_symbols = prices.columns[(prices <= 0).any()].tolist()
        issues.append(f"Non-positive prices found in: {bad_symbols}")

    # Check for duplicate dates
    if prices.index.duplicated().any():
        issues.append("Duplicate dates found in index")

    # Check for unsorted index
    if not prices.index.is_monotonic_increasing:
        issues.append("Date index is not sorted in ascending order")

    # Check for large gaps
    date_diffs = pd.Series(prices.index).diff().dt.days
    max_gap = date_diffs.max()
    if max_gap > 10:
        issues.append(f"Large date gap found: {max_gap} days")

    return issues
