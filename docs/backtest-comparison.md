# Backtest Engine Comparison: etf-trend vs options-signal-system

A detailed cross-project comparison of backtesting capabilities.

---

## 1. Positioning & Goals

| Dimension | etf-trend | options-signal-system |
|-----------|-----------|----------------------|
| **Core Asset** | ETF + Stocks (equity) | Options |
| **Strategy Type** | Trend-following + Momentum rotation | 10 options strategies (spreads, condors, straddles, etc.) |
| **Engine** | Custom dual-mode (vectorized + event-driven) | Built on **optopsy** library (specialized options backtesting) |
| **Pricing Model** | None (uses historical prices directly) | Black-Scholes + Greeks (`greeks.py`, 161 lines) |

## 2. Architecture

| Dimension | etf-trend | options-signal-system |
|-----------|-----------|----------------------|
| **Engine Code** | `engine.py` (31 lines) + `simulator.py` (229 lines) | `backtester.py` (287 lines) + `synthetic_options.py` (210 lines) + `multi_leg.py` (257 lines) + `greeks.py` (161 lines) |
| **Total Size** | ~260 lines | ~915 lines |
| **External Deps** | None (pure numpy/pandas) | optopsy library (simulation, signals, metrics) |
| **Data Generation** | Direct historical OHLCV | **Synthetic options chain generator** — Black-Scholes pricing, daily full chain generation (strike grid, bid/ask spread, Greeks) |

## 3. Strategy Coverage

| Strategy | etf-trend | options-signal-system |
|----------|-----------|----------------------|
| Long Call/Put | ❌ | ✅ |
| Short Call/Put | ❌ | ✅ |
| Bull/Bear Spreads | ❌ | ✅ (4 types) |
| Iron Condor | ❌ | ✅ |
| Straddle | ❌ | ✅ |
| Multi-leg Custom (≤4 legs) | ❌ | ✅ (`multi_leg.py`) |
| ETF Rotation | ✅ (Core + Satellite) | ❌ |
| Trend-following / Momentum | ✅ | ❌ |
| Regime Detection | ✅ (3-state) | ❌ |

## 4. Metrics

| Metric | etf-trend | options-signal-system |
|--------|-----------|----------------------|
| Sharpe Ratio | ✅ (RF=0%) | ✅ (via optopsy) |
| Sortino Ratio | ❌ | ✅ |
| Max Drawdown | ✅ | ✅ |
| Calmar Ratio | ✅ | ✅ |
| **Win Rate** | ❌ | ✅ |
| **Profit Factor** | ❌ | ✅ |
| Annualized Return/Vol | ✅ | ❌ (trade-level, not annualized) |
| Avg Turnover/Cost | ✅ | ❌ |
| Mean Return (per trade) | ❌ | ✅ |
| Equity Curve | ✅ (Matplotlib) | ✅ (API JSON response) |
| Trade Log | ❌ | ✅ (up to 200 entries) |

## 5. Options-Specific Capabilities (options-signal-system only)

| Capability | Details |
|------------|---------|
| **Greeks Calculation** | Delta, Gamma, Theta, Vega, Rho — vectorized Black-Scholes |
| **Synthetic Options Chain** | OHLCV → full historical options chain (weekly Friday expirations, ATM ±15%, $0.50/$1.00 increments) |
| **Delta Selection** | `leg1_delta=0.30, leg2_delta=0.16` + `TargetRange(±0.05)` tolerance |
| **DTE Management** | `max_entry_dte=45, exit_dte=21` |
| **Stop Loss / Take Profit** | Configurable per-backtest |
| **Multi-leg Analysis** | P&L curve, breakeven points, aggregated Greeks, max profit/loss (with infinity detection) |
| **Commission Model** | Per-contract / per-share / base fee / min fee |
| **LLM Interpretation** | `/api/v1/backtest/interpret` — backtest results → LLM streaming analysis |

## 6. etf-trend Exclusive Capabilities

| Capability | Details |
|------------|---------|
| **Market Regime** | 3-state detection → dynamic risk budget (0–1) |
| **Portfolio Optimization** | MinVariance / RiskParity / InverseVolatility |
| **Multi-tier Execution Plan** | 3-level entry + 3-level stop-loss + 3-level take-profit (ATR-based) |
| **Factor Stock Selection** | Momentum + MA200 Trend + Volatility |
| **AI Trifecta** | DTW + GBT + LLM |
| **Visualization** | 4 Matplotlib chart types |

## 7. Transaction Cost Model

| Dimension | etf-trend | options-signal-system |
|-----------|-----------|----------------------|
| Model | Simple bps (5 bps default) | `Commission` dataclass: per_contract=$0.65, per_share, base_fee, min_fee |
| Slippage | ❌ | ✅ (via bid/ask spread ±5%) |
| Realism | Low | Medium-High |

## 8. Summary

| Dimension | etf-trend Advantage | options-signal-system Advantage |
|-----------|--------------------|---------------------------------|
| **Breadth** | ETF + Stocks + Factors + AI | 10 options strategies + multi-leg |
| **Depth** | Regime + Portfolio Optimization | Greeks + Synthetic chain + Delta management |
| **Metrics Richness** | Annualized metrics | Trade-level metrics (Win Rate, Profit Factor, Sortino) |
| **Architecture Maturity** | Custom engine (flexible but simple) | Built on optopsy (professional but library-bound) |
| **Cost Model** | Simple | Precise |
| **Extensibility** | Monthly rebalancing only | Signal-driven entry + DTE management |

**High complementarity** — etf-trend handles the macro layer ("when to buy/sell which ETF/stock"), while options-signal-system handles the micro layer ("which options strategy to execute, how to manage Greeks"). Combined, they form a complete regime → allocation → execution pipeline.

---

*Last updated: April 2026*
