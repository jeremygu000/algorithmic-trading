from __future__ import annotations

import numpy as np
import pandas as pd

from etf_trend.analysis.attribution import (
    calculate_alpha_beta,
    calculate_max_drawdown_duration,
    calculate_sortino_ratio,
)


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


def extended_stats(
    bt: pd.DataFrame,
    benchmark_returns: pd.Series | None = None,
    risk_free_rate: float = 0.0,
) -> pd.Series:
    base = perf_stats(bt)
    r = bt["net_ret"]

    # ── Sortino ──
    sortino = calculate_sortino_ratio(r, target_return=0.0, periods=252)

    # ── Win Rate / Profit Factor ──
    wins = r[r > 0]
    losses = r[r < 0]
    win_rate = len(wins) / max(len(r[r != 0]), 1)
    gross_profit = wins.sum() if len(wins) else 0.0
    gross_loss = abs(losses.sum()) if len(losses) else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    # ── Max Drawdown Duration ──
    max_dd_duration = calculate_max_drawdown_duration(r)

    # ── Tail Ratio: 95th-percentile gain / |5th-percentile loss| ──
    p95 = np.percentile(r, 95) if len(r) > 0 else np.nan
    p5 = np.percentile(r, 5) if len(r) > 0 else np.nan
    tail_ratio = p95 / abs(p5) if p5 != 0 else np.nan

    # ── Common Sense Ratio: Tail × Profit Factor ──
    csr = (
        tail_ratio * profit_factor
        if np.isfinite(tail_ratio) and np.isfinite(profit_factor)
        else np.nan
    )

    extra = pd.Series(
        {
            "Sortino": sortino,
            "Win Rate": win_rate,
            "Profit Factor": profit_factor,
            "Max DD Duration (days)": max_dd_duration,
            "Tail Ratio (95/5)": tail_ratio,
            "Common Sense Ratio": csr,
        }
    )

    # ── Alpha / Beta (optional, requires benchmark) ──
    if benchmark_returns is not None:
        ab = calculate_alpha_beta(r, benchmark_returns, risk_free_rate)
        extra["Alpha"] = ab["alpha"]
        extra["Beta"] = ab["beta"]
        extra["R²"] = ab["r_squared"]

        active = r - benchmark_returns.reindex(r.index).fillna(0)
        te = active.std() * np.sqrt(252)
        ir = (active.mean() * 252) / te if te > 0 else np.nan
        extra["Information Ratio"] = ir
        extra["Tracking Error"] = te

    return pd.concat([base, extra])
