from __future__ import annotations
import numpy as np
import pandas as pd


def realized_vol_annual(returns: pd.DataFrame, lookback: int) -> pd.DataFrame:
    return returns.rolling(lookback).std() * np.sqrt(252)
