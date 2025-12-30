from __future__ import annotations
import pandas as pd


def month_end_trading_days(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    # last trading day in each month (based on your price index)
    dates = index.to_series().resample("ME").last().dropna().index
    return dates.intersection(index)
