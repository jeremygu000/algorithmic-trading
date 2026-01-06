#!/usr/bin/env python
"""
Backtest Comparison: Before vs After Phase 5
=============================================

Compare strategy performance with and without the Phase 5 enhancements.
This script creates two different scoring methods to simulate baseline vs enhanced.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List

# Import strategy components
from etf_trend.regime.engine import RegimeEngine, RegimeState
from etf_trend.backtest.metrics import perf_stats


@dataclass
class SimpleCandidate:
    symbol: str
    score: float


def generate_realistic_prices(
    start_date: str = "2020-01-01",
    end_date: str = "2024-12-31",
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic-looking price data for backtesting."""
    np.random.seed(seed)
    dates = pd.date_range(start_date, end_date, freq="B")
    n = len(dates)

    prices = pd.DataFrame(index=dates)

    # SPY: ~10% annual return with 15% volatility
    spy_daily_ret = 0.10 / 252
    spy_daily_vol = 0.15 / np.sqrt(252)
    spy_returns = np.random.normal(spy_daily_ret, spy_daily_vol, n)
    prices["SPY"] = 300 * np.cumprod(1 + spy_returns)

    # Individual Stocks
    stock_params = {
        "AAPL": (0.15, 0.25),
        "MSFT": (0.12, 0.22),
        "NVDA": (0.25, 0.40),
        "GOOGL": (0.10, 0.20),
        "AMZN": (0.12, 0.28),
        "META": (0.08, 0.35),
        "TSLA": (0.20, 0.50),
        "JPM": (0.08, 0.20),
        "JNJ": (0.05, 0.12),
        "XOM": (0.06, 0.25),
    }

    for symbol, (ann_ret, ann_vol) in stock_params.items():
        daily_ret = ann_ret / 252
        daily_vol = ann_vol / np.sqrt(252)
        correlation = 0.5
        idio_vol = daily_vol * np.sqrt(1 - correlation**2)
        stock_returns = correlation * spy_returns + np.random.normal(daily_ret, idio_vol, n)

        # Market crash simulation
        crash_mask = (dates >= "2020-03-01") & (dates <= "2020-03-31")
        stock_returns[crash_mask] *= -1.5

        # Recovery
        recovery_mask = (dates >= "2020-04-01") & (dates <= "2020-12-31")
        stock_returns[recovery_mask] *= 1.3

        prices[symbol] = 100 * np.cumprod(1 + stock_returns)

    return prices


def calculate_baseline_scores(prices: pd.DataFrame, as_of_date: pd.Timestamp) -> List[SimpleCandidate]:
    """
    BASELINE scoring: Simple momentum only (Phase 1-3 style).
    Score = 60-day momentum + trend bonus
    """
    candidates = []
    history = prices.loc[:as_of_date]

    if len(history) < 200:
        return []

    for symbol in prices.columns:
        if symbol == "SPY":
            continue

        price = history[symbol].iloc[-1]
        ma200 = history[symbol].rolling(200).mean().iloc[-1]
        mom60 = history[symbol].pct_change(60).iloc[-1]

        if pd.isna(mom60) or pd.isna(ma200):
            continue

        # Simple scoring: momentum + trend
        score = 0.5 + mom60 * 2  # Momentum contribution
        if price > ma200:
            score += 0.1  # Trend bonus

        score = max(0.0, min(1.0, score))
        candidates.append(SimpleCandidate(symbol=symbol, score=score))

    return sorted(candidates, key=lambda x: -x.score)[:5]


def calculate_enhanced_scores(prices: pd.DataFrame, as_of_date: pd.Timestamp) -> List[SimpleCandidate]:
    """
    ENHANCED scoring: Phase 5 style with multiple factors.
    Score = momentum + trend + MACD + RSI + avoid-chasing
    """
    candidates = []
    history = prices.loc[:as_of_date]

    if len(history) < 200:
        return []

    for symbol in prices.columns:
        if symbol == "SPY":
            continue

        price = history[symbol].iloc[-1]
        ma20 = history[symbol].rolling(20).mean().iloc[-1]
        ma50 = history[symbol].rolling(50).mean().iloc[-1]
        ma200 = history[symbol].rolling(200).mean().iloc[-1]
        mom60 = history[symbol].pct_change(60).iloc[-1]
        mom5 = history[symbol].pct_change(5).iloc[-1]

        if any(pd.isna([mom60, ma200, ma20, ma50])):
            continue

        # Base score from momentum
        score = 0.5 + mom60 * 2

        # Trend bonus (enhanced: multi-MA alignment)
        if price > ma20 > ma50 > ma200:
            score += 0.15  # Strong bullish alignment
        elif price > ma200:
            score += 0.05  # Basic trend

        # RSI-like momentum check
        if mom60 > 0.3:  # Very strong momentum
            score += 0.05
        elif mom60 < -0.1:
            score -= 0.1

        # Avoid chasing (Phase 5 feature)
        if mom5 > 0.08:  # Up >8% in 5 days
            score -= 0.15  # Penalty for chasing
        elif mom5 < -0.08:  # Pullback
            score += 0.05  # Buy the dip bonus

        # MACD-like: short vs long momentum
        mom20 = history[symbol].pct_change(20).iloc[-1]
        if pd.notna(mom20):
            if mom20 > mom60 * 0.5:  # Accelerating momentum
                score += 0.05
            elif mom20 < 0 < mom60:  # Decelerating
                score -= 0.05

        score = max(0.0, min(1.0, score))
        candidates.append(SimpleCandidate(symbol=symbol, score=score))

    return sorted(candidates, key=lambda x: -x.score)[:5]


def run_backtest(
    prices: pd.DataFrame,
    scoring_func,
    start_date: str,
    end_date: str,
    initial_capital: float = 100_000,
    cost_bps: float = 10.0,
) -> pd.DataFrame:
    """Run simple backtest with given scoring function."""
    dates = prices.loc[start_date:end_date].index
    rebalance_dates = pd.date_range(start_date, end_date, freq="ME")

    cash = initial_capital
    positions = {}  # symbol -> shares
    nav_history = []

    for date in dates:
        # Calculate daily NAV
        nav = cash
        current_prices = prices.loc[date]
        for sym, shares in positions.items():
            if sym in current_prices:
                nav += shares * current_prices[sym]
        nav_history.append({"date": date, "nav": nav})

        # Rebalance monthly
        if date in rebalance_dates:
            # Get candidates
            candidates = scoring_func(prices, date)

            if not candidates:
                continue

            # Calculate target weights (equal weight among top picks)
            n_picks = len(candidates)
            weight_per_stock = 0.8 / n_picks  # 80% invested, 20% cash

            target_weights = {c.symbol: weight_per_stock for c in candidates}

            # Sell positions not in target
            for sym in list(positions.keys()):
                if sym not in target_weights:
                    shares = positions.pop(sym)
                    px = current_prices[sym]
                    amount = shares * px
                    cost = amount * cost_bps / 10000
                    cash += amount - cost

            # Rebalance positions
            total_nav = cash + sum(
                shares * current_prices[sym] for sym, shares in positions.items()
            )

            for sym, target_w in target_weights.items():
                target_value = total_nav * target_w
                current_shares = positions.get(sym, 0)
                current_value = current_shares * current_prices[sym] if current_shares > 0 else 0

                diff_value = target_value - current_value
                if abs(diff_value) > total_nav * 0.02:  # Only trade if >2% diff
                    diff_shares = int(diff_value / current_prices[sym])
                    cost = abs(diff_shares * current_prices[sym]) * cost_bps / 10000

                    if diff_shares > 0:  # Buy
                        if cash >= diff_shares * current_prices[sym] + cost:
                            cash -= diff_shares * current_prices[sym] + cost
                            positions[sym] = current_shares + diff_shares
                    elif diff_shares < 0:  # Sell
                        sell_shares = min(abs(diff_shares), current_shares)
                        cash += sell_shares * current_prices[sym] - cost
                        positions[sym] = current_shares - sell_shares

    nav_df = pd.DataFrame(nav_history).set_index("date")
    nav_df["pct_change"] = nav_df["nav"].pct_change().fillna(0)
    nav_df["cum_max"] = nav_df["nav"].cummax()
    nav_df["drawdown"] = nav_df["nav"] / nav_df["cum_max"] - 1

    return nav_df


def calculate_stats(nav_df: pd.DataFrame) -> pd.Series:
    """Calculate performance statistics."""
    returns = nav_df["pct_change"]
    ann_ret = returns.mean() * 252
    ann_vol = returns.std() * np.sqrt(252)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
    max_dd = nav_df["drawdown"].min()
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0

    return pd.Series({
        "Ann Return": ann_ret,
        "Ann Vol": ann_vol,
        "Sharpe": sharpe,
        "Max Drawdown": max_dd,
        "Calmar": calmar,
        "Final NAV": nav_df["nav"].iloc[-1],
    })


def main():
    print("=" * 60)
    print("  Backtest Comparison: Baseline vs Phase 5 Enhanced")
    print("=" * 60)
    print()

    # Generate price data
    print(">>> Generating historical price data (2020-2024)...")
    prices = generate_realistic_prices()
    print(f"    Generated {len(prices)} trading days for {len(prices.columns)} assets")
    print()

    # Run baseline backtest
    print(">>> Running Baseline Strategy (Momentum Only)...")
    baseline_nav = run_backtest(prices, calculate_baseline_scores, "2021-01-01", "2024-12-31")
    baseline_stats = calculate_stats(baseline_nav)
    print("    Baseline completed.")
    print()

    # Run enhanced backtest
    print(">>> Running Enhanced Strategy (Phase 5)...")
    enhanced_nav = run_backtest(prices, calculate_enhanced_scores, "2021-01-01", "2024-12-31")
    enhanced_stats = calculate_stats(enhanced_nav)
    print("    Enhanced completed.")
    print()

    # Compare results
    print("=" * 60)
    print("  Performance Comparison (2021-2024)")
    print("=" * 60)
    comparison = pd.DataFrame({
        "Baseline": baseline_stats,
        "Enhanced": enhanced_stats,
    })
    comparison["Improvement"] = comparison["Enhanced"] - comparison["Baseline"]
    print(comparison.to_string())
    print()

    # Summary
    print("-" * 60)
    print(f"  Annual Return: Baseline {baseline_stats['Ann Return']:.2%} → Enhanced {enhanced_stats['Ann Return']:.2%}")
    print(f"  Sharpe Ratio:  Baseline {baseline_stats['Sharpe']:.2f} → Enhanced {enhanced_stats['Sharpe']:.2f}")
    print(f"  Max Drawdown:  Baseline {baseline_stats['Max Drawdown']:.2%} → Enhanced {enhanced_stats['Max Drawdown']:.2%}")
    print(f"  Final NAV:     Baseline ${baseline_stats['Final NAV']:,.0f} → Enhanced ${enhanced_stats['Final NAV']:,.0f}")
    print("-" * 60)

    # Save comparison
    nav_comparison = pd.DataFrame({
        "Baseline": baseline_nav["nav"],
        "Enhanced": enhanced_nav["nav"],
    })
    nav_comparison.to_csv("backtest_nav_comparison.csv")
    print("\n  NAV comparison saved to: backtest_nav_comparison.csv")

    return comparison


if __name__ == "__main__":
    result = main()
