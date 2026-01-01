"""
Strategy Simulator
==================

Event-driven backtesting engine to simulate the full strategy lifecycle:
Regime Detection -> Stock Selection -> Allocation -> Rebalancing
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass

from etf_trend.regime.engine import RegimeEngine
from etf_trend.selector.satellite import StockSelector
from etf_trend.execution.executor import TradeExecutor
from etf_trend.backtest.metrics import perf_stats


@dataclass
class BacktestResult:
    nav: pd.Series
    positions: pd.DataFrame
    trades: pd.DataFrame
    stats: pd.Series


class StrategySimulator:
    def __init__(
        self,
        prices: pd.DataFrame,
        stock_pool: List[str],
        initial_capital: float = 100_000.0,
        rebalance_freq: str = "W-FRI",  # Weekly rebalance
        cost_bps: float = 10.0,
        fundamentals: Optional[Dict] = None,
        ai_analysis: Optional[Dict] = None,
    ):
        self.prices = prices
        self.stock_pool = stock_pool
        self.initial_capital = initial_capital
        self.rebalance_freq = rebalance_freq
        self.cost_bps = cost_bps

        # Modules
        self.regime_engine = RegimeEngine()
        self.selector = StockSelector(stock_pool)
        self.executor = TradeExecutor()

        # External Data (Mocked or Passed)
        self.fundamentals = fundamentals
        self.ai_analysis = ai_analysis

    def run(self, start_date: str, end_date: str) -> BacktestResult:
        # 1. Setup Dates
        dates = self.prices.loc[start_date:end_date].index
        rebalance_dates = pd.date_range(start_date, end_date, freq=self.rebalance_freq)

        # 2. State tracking
        current_cash = self.initial_capital
        current_positions = {}  # Symbol -> Shares

        nav_history = []
        pos_history = []
        trade_log = []

        for date in dates:
            # Daily NAV calculation
            daily_value = current_cash
            current_prices = self.prices.loc[date]

            for sym, shares in current_positions.items():
                if sym in current_prices and not pd.isna(current_prices[sym]):
                    daily_value += shares * current_prices[sym]

            nav_history.append({"date": date, "nav": daily_value})

            # --- Rebalancing Logic ---
            if date in rebalance_dates:
                # 1. Regime
                # Slice data up to today to avoid lookahead (careful with iloc/loc)
                # Ideally pass history. For speed, we pass full DF but modules should respect 'as_of_date' logic if implemented,
                # otherwise we slice.
                # Since our modules mostly assume full DF and look at 'as_of_date' or last index:
                # Let's slice for safety.
                history = self.prices.loc[:date]
                regime_state = self.regime_engine.detect(history)

                # 2. Select
                # Note: This calls select(), which does heavy computing. Simulation might be slow.
                selection = self.selector.select(
                    history,
                    regime_state,
                    as_of_date=date,
                    use_fundamental=bool(self.fundamentals),
                    fundamentals=self.fundamentals,
                    ai_analysis=self.ai_analysis,
                )

                # 3. Allocation (Simplified Equal Weight or Risk Budget)
                target_weights = {}
                candidates = selection.candidates

                # Risk budget (0.0 - 1.0) determines total equity exposure
                # e.g. if Risk Budget is 0.8 and we have 4 stocks, each gets 0.2
                total_budget = regime_state.risk_budget

                if candidates:
                    # Filter candidates that are actually tradable today
                    valid_candidates = [
                        c
                        for c in candidates
                        if c.symbol in current_prices and pd.notna(current_prices[c.symbol])
                    ]

                    if valid_candidates:
                        # Weighting: Equal weight for now
                        weight_per_stock = total_budget / len(valid_candidates)
                        # Cap single stock weight at 0.25 (25%) to be safe
                        weight_per_stock = min(0.25, weight_per_stock)

                        for cand in valid_candidates:
                            target_weights[cand.symbol] = weight_per_stock

                # 4. Execution (determine target shares)

                # Sell first
                for sym in list(current_positions.keys()):
                    target_w = target_weights.get(sym, 0.0)
                    if target_w == 0:
                        # Full exit
                        shares = current_positions.pop(sym)
                        px = current_prices[sym]
                        amount = shares * px
                        cost = amount * (self.cost_bps / 10000)
                        current_cash += amount - cost
                        trade_log.append(
                            {
                                "date": date,
                                "symbol": sym,
                                "action": "SELL",
                                "shares": shares,
                                "price": px,
                                "cost": cost,
                            }
                        )

                # Re-calc nav valid for buying
                nav_avail = current_cash + sum(
                    shares * current_prices[sym]
                    for sym, shares in current_positions.items()
                    if sym in current_prices
                )

                # Buy
                for sym, w in target_weights.items():
                    if w > 0:
                        target_amt = nav_avail * w
                        current_shares = current_positions.get(sym, 0)
                        current_amt = current_shares * current_prices[sym]

                        diff_amt = target_amt - current_amt

                        # Only trade if diff is significant (e.g. > 1% change) to reduce churn
                        if abs(diff_amt) > nav_avail * 0.01:
                            px = current_prices[sym]
                            if pd.isna(px):
                                continue

                            diff_shares = int(diff_amt / px)

                            if diff_shares != 0:
                                cost = abs(diff_shares * px) * (self.cost_bps / 10000)
                                if diff_shares > 0:  # Buy
                                    if current_cash >= (diff_shares * px + cost):
                                        current_cash -= diff_shares * px + cost
                                        current_positions[sym] = current_shares + diff_shares
                                        trade_log.append(
                                            {
                                                "date": date,
                                                "symbol": sym,
                                                "action": "BUY",
                                                "shares": diff_shares,
                                                "price": px,
                                                "cost": cost,
                                            }
                                        )
                                elif diff_shares < 0:  # Sell
                                    # Logic handled above partially, but this handles rebalancing (reducing weight)
                                    sell_shares = abs(diff_shares)
                                    current_cash += sell_shares * px - cost
                                    current_positions[sym] = current_shares - sell_shares
                                    trade_log.append(
                                        {
                                            "date": date,
                                            "symbol": sym,
                                            "action": "SELL",
                                            "shares": sell_shares,
                                            "price": px,
                                            "cost": cost,
                                        }
                                    )

        # Compile Results
        nav_df = pd.DataFrame(nav_history).set_index("date")

        # Calculate Drawdown, Returns
        nav_df["pct_change"] = nav_df["nav"].pct_change().fillna(0)
        nav_df["cum_max"] = nav_df["nav"].cummax()
        nav_df["drawdown"] = nav_df["nav"] / nav_df["cum_max"] - 1

        # Adapter to match perf_stats expectation
        bt_df = pd.DataFrame(
            {
                "net_ret": nav_df["pct_change"],
                "nav": nav_df["nav"],
                "drawdown": nav_df["drawdown"],
                "turnover": 0,  # TODO: Track turnover properly
                "cost": 0,  # TODO: Track cost properly
            }
        )

        stats = perf_stats(bt_df)

        return BacktestResult(
            nav=nav_df,
            positions=pd.DataFrame(pos_history),
            trades=pd.DataFrame(trade_log),
            stats=stats,
        )
