from __future__ import annotations
import pandas as pd


def momentum_score(prices: pd.DataFrame, windows: list[int], weights: list[float]) -> pd.DataFrame:
    comps = [prices.pct_change(w) for w in windows]
    score = sum(wt * r for wt, r in zip(weights, comps))
    return score
