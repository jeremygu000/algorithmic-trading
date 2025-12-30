from __future__ import annotations
import numpy as np
import pandas as pd


def perf_stats(bt: pd.DataFrame) -> pd.Series:
    r = bt["net_ret"]
    nav = bt["nav"]
    dd = bt["drawdown"]

    ann_ret = (nav.iloc[-1] ** (252 / max(len(nav) - 1, 1)) - 1) if len(nav) > 1 else np.nan
    ann_vol = r.std() * np.sqrt(252)
    sharpe = (r.mean() / r.std()) * np.sqrt(252) if r.std() != 0 else np.nan
    max_dd = dd.min()
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else np.nan

    return pd.Series(
        {
            "Ann Return": ann_ret,
            "Ann Vol": ann_vol,
            "Sharpe": sharpe,
            "Max Drawdown": max_dd,
            "Calmar": calmar,
            "Avg Daily Turnover": bt["turnover"].mean(),
            "Avg Cost (bps/day)": bt["cost"].mean() * 10000,
        }
    )
