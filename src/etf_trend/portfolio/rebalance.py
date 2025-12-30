from __future__ import annotations
import pandas as pd

from etf_trend.data.calendar import month_end_trading_days
from etf_trend.features.volatility import realized_vol_annual
from etf_trend.portfolio.weighting import inv_vol_weights
from etf_trend.portfolio.constraints import apply_constraints


def build_monthly_weights(
    prices: pd.DataFrame,
    score: pd.DataFrame,
    trend_on: pd.DataFrame,
    vol_lookback: int,
    max_weight_single: float,
    max_weight_core: float,
    core_symbols: list[str],
) -> pd.DataFrame:
    rets = prices.pct_change()
    vol = realized_vol_annual(rets, vol_lookback)

    rb_dates = month_end_trading_days(prices.index)
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    for d in rb_dates:
        elig = ((score.loc[d] > 0) & (trend_on.loc[d])).reindex(prices.columns).fillna(False)
        if elig.sum() == 0:
            w = pd.Series(0.0, index=prices.columns)
        else:
            w = inv_vol_weights(vol.loc[d], elig)
            w = apply_constraints(w, max_weight_single, max_weight_core, core_symbols)

        weights.loc[d] = w

    return weights.ffill().fillna(0.0)
