from __future__ import annotations
import pandas as pd


def inv_vol_weights(vol: pd.Series, eligible: pd.Series) -> pd.Series:
    inv = (1 / vol).replace([float("inf"), float("-inf")], pd.NA)
    inv = inv.where(eligible, 0.0).fillna(0.0)
    if inv.sum() == 0:
        return inv
    return inv / inv.sum()
