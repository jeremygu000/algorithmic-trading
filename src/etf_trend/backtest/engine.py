from __future__ import annotations
import pandas as pd

from etf_trend.backtest.costs import turnover as calc_turnover, cost_from_turnover


def run_backtest(prices: pd.DataFrame, weights: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    rets = prices.pct_change().fillna(0.0)

    # avoid lookahead: use yesterday's weights
    w_lag = weights.shift(1).fillna(0.0)

    port_ret = (w_lag * rets).sum(axis=1)

    to = calc_turnover(weights)
    cost = cost_from_turnover(to, cost_bps)

    net_ret = port_ret - cost
    nav = (1 + net_ret).cumprod()
    dd = nav / nav.cummax() - 1

    return pd.DataFrame(
        {
            "port_ret": port_ret,
            "net_ret": net_ret,
            "nav": nav,
            "drawdown": dd,
            "turnover": to,
            "cost": cost,
        }
    )
