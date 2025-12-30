from __future__ import annotations
import pandas as pd


def turnover(weights: pd.DataFrame) -> pd.Series:
    return (weights - weights.shift(1)).abs().sum(axis=1).fillna(0.0)


def cost_from_turnover(turnover: pd.Series, cost_bps: float) -> pd.Series:
    return (cost_bps / 10000.0) * turnover
