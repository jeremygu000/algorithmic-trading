from __future__ import annotations
import pandas as pd


def trend_on(prices: pd.DataFrame, ma_long: int) -> pd.DataFrame:
    ma = prices.rolling(ma_long).mean()
    return prices > ma
