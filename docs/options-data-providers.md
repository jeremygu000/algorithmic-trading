# Historical Options Data Providers — Research & Recommendations

A detailed comparison of real historical options data providers for algorithmic trading backtesting, with specific focus on replacing synthetic options data in [options-signal-system](https://github.com/jeremygu000/options-signal-system).

---

## Summary

| Provider | Best For | Min Cost | History Depth | Data Granularity |
|----------|----------|----------|---------------|------------------|
| **ThetaData** ⭐ | Individual backtesting | $40/mo | 4–12 years | 1-min to tick |
| **Polygon.io** | Multi-asset unified source | $79/mo | Since 2014 | Tick-level |
| **ORATS** | Institutional / deep history | $599 + $99/mo | Since 2007 | EOD to 1-min |
| **FlashAlpha** | Options flow analytics | Free | Varies | Derived metrics |
| **Intrinio** | Enterprise / compliance | ~$100/mo | Deep | EOD to tick |

---

## 1. ThetaData (thetadata.net) — ⭐ Top Pick

**Best for individual developers doing options backtesting.**

| Plan | Price | History | Granularity | Key Features |
|------|-------|---------|-------------|--------------|
| **Options Value** | **$40/mo** | 4 years | 1-minute intervals | 3 request types, unlimited requests |
| Options Standard | $80/mo | 8 years | Tick-level | Option chain snapshots, NBBO quotes, 15K trade streams |
| Options Pro | $160/mo | 12 years | Tick-level | All request types, root snapshots, stream every trade |

**Why recommended:**
- Best price-to-value ratio — $40/mo gets 4 years of 1-min options data
- Python SDK ready to use out of the box
- 100% US market coverage
- Active community (most recommended on r/algotrading)
- Annual billing discounts available
- Real-time access included

**For options-signal-system:** The $40/mo Value plan provides enough history (4 years) to replace `synthetic_options.py` Black-Scholes generated data with real market data, gaining accurate IV skew, term structure, and liquidity information.

---

## 2. Polygon.io / Massive.com

**Best for unified data source across multiple projects.**

| Plan | Price | Options Data | Notes |
|------|-------|-------------|-------|
| Free | $0 | No | 5 calls/min, stocks only |
| Starter | $29/mo | No | Stocks only |
| **Developer** | **$79/mo** | ✅ Yes | Options data included |
| Business | $199/mo | ✅ Full | Complete options access |

**Key features:**
- US options data since 2014
- Tick-level granularity
- WebSocket streaming for real-time
- REST API with good documentation
- Covers stocks + options + crypto in one subscription

**Best scenario:** If both etf-trend (stocks) and options-signal-system (options) need data, a single Polygon subscription serves both projects.

---

## 3. ORATS (orats.com)

**Best for institutional-grade analysis and deep historical coverage.**

### Trading Tools
| Plan | Price |
|------|-------|
| Individual | $99/mo |
| Professional | $199/mo |

### API Access
| Plan | Price |
|------|-------|
| Delayed Data API | $99/mo |
| Live Data API | $199/mo |
| Live Intraday API | $399/mo |

### Historical Data (One-Time Purchase + Recurring)
| Dataset | One-Time | Recurring | History From |
|---------|----------|-----------|--------------|
| **Near EOD** | $599 | $99/mo | 2007 |
| 1-Min Intraday | $1,500 | $199/mo | Aug 2020 |
| 2-Min Snapshot | $2,000 | $199/mo | 2015 |

**Key features:**
- Deepest history available (back to 2007, covering the 2008 financial crisis)
- Built-in backtester with 800+ indicators
- Scanner and screening tools
- 14-day trial for $29
- Industry-standard data quality

**Best scenario:** When backtesting needs to cover extreme market events (2008 crisis, 2020 COVID crash) for stress-testing strategies.

---

## 4. FlashAlpha

**Best for options flow and sentiment analytics.**

| Plan | Price | Rate Limit | Notes |
|------|-------|-----------|-------|
| **Free** | **$0** | 10 calls/day | No credit card required |
| Basic | $49/mo | 100 calls/day | — |
| Growth | $299/mo | 2,500 calls/day | — |

**Unique capabilities (not available elsewhere):**
- GEX (Gamma Exposure)
- DEX (Delta Exposure)
- VEX (Vega Exposure)
- CHEX (Charm Exposure)
- Volatility surface data
- Server-side BSM Greeks computation
- Python SDK

**Best scenario:** Adding market-wide options sentiment signals (GEX/DEX) to trading systems. The free tier allows zero-cost experimentation.

---

## 5. Other Providers

| Provider | Pricing | Notes |
|----------|---------|-------|
| **Intrinio** | ~$100/mo (individual), enterprise custom | Deep history, regulatory-grade compliance |
| **IVolatility** | Contact for pricing | Options chains, Greeks, IV data |
| **OptionMetrics** | Contact for pricing | Academic/institutional, gold standard |
| **EOD Historical Data** | Varies | End-of-day summaries only |
| **Tradier** | $10/mo add-on | Also a broker, limited historical depth |
| **Alpha Vantage** | Varies | Unclear options coverage |

---

## Recommended Adoption Path

```
Phase 1 (Now)     → FlashAlpha Free          $0/mo    Try options sentiment data
Phase 2 (Validate) → ThetaData Value          $40/mo   Replace synthetic chain with real data
Phase 3 (Scale)    → Polygon Developer         $79/mo   Unified source for both projects
Phase 4 (If needed) → ORATS EOD Historical    $599+$99/mo  Deep history for stress testing
```

---

## Impact on options-signal-system

The most impactful upgrade is replacing `synthetic_options.py` (Black-Scholes generated chains) with real historical data. Current synthetic data limitations:

| Limitation | Impact on Backtest Accuracy |
|------------|---------------------------|
| No IV skew | Misprices OTM options significantly |
| No term structure | Incorrect time-value decay modeling |
| No liquidity data | Unrealistic fill assumptions |
| Uniform bid-ask (±5%) | Real spreads vary 1-50%+ by strike/expiry |
| No earnings/event IV spikes | Misses critical volatility events |

**ThetaData at $40/mo directly addresses all five limitations.**

---

*Last updated: April 2026*
