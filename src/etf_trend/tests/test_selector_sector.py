import pytest
import pandas as pd
import numpy as np
from etf_trend.selector.satellite import StockSelector
from etf_trend.regime.engine import RegimeState


@pytest.fixture
def mock_regime_risk_on():
    return RegimeState(
        regime="RISK_ON", risk_budget=1.0, signals={"trend": 1.0, "vix": 1.0, "momentum": 1.0}
    )


@pytest.fixture
def mock_sector_prices():
    """
    Mock prices for Stocks and Sector ETFs.

    Stocks:
    - TECH_STOCK (in Technology, strong)
    - ENERGY_STOCK (in Energy, weak)

    ETFs:
    - XLK (Tech): Strong uptrend
    - XLE (Energy): Downtrend
    """
    dates = pd.date_range("2023-01-01", "2023-12-31", freq="B")

    # 1. Tech ETF (XLK) - Strong (Linear up ~0.3% daily -> >5% monthly)
    xlk = 100 * (1.003 ** np.arange(len(dates)))

    # 2. Energy ETF (XLE) - Weak (Linear down ~0.3% daily -> <-5% monthly)
    xle = 100 * (0.997 ** np.arange(len(dates)))

    # 3. TECH_STOCK (Moves with XLK)
    tech_stock = xlk * 1.1 + np.random.normal(0, 1, len(dates))

    # 4. ENERGY_STOCK (Moves with XLE)
    energy_stock = xle * 0.9 + np.random.normal(0, 1, len(dates))

    df = pd.DataFrame(
        {"XLK": xlk, "XLE": xle, "TECH_STOCK": tech_stock, "ENERGY_STOCK": energy_stock},
        index=dates,
    )

    return df


@pytest.fixture
def mock_fundamentals_sector():
    return {
        "TECH_STOCK": {
            "symbol": "TECH_STOCK",
            "sector": "Technology",  # Matches XLK
            "peRatio": 20,
            "pegRatio": 1.0,
            "returnOnEquity": 0.2,
            "grossMargins": 0.4,
            "debtToEquity": 0.5,
        },
        "ENERGY_STOCK": {
            "symbol": "ENERGY_STOCK",
            "sector": "Energy",  # Matches XLE
            "peRatio": 10,
            "pegRatio": 1.5,
            "returnOnEquity": 0.1,
            "grossMargins": 0.2,
            "debtToEquity": 1.0,
        },
    }


def test_sector_momentum_impact(mock_sector_prices, mock_regime_risk_on, mock_fundamentals_sector):
    """
    Test if stocks in strong sectors get a bonus.
    """
    # Use a dummy pool
    selector = StockSelector(stock_pool=["TECH_STOCK", "ENERGY_STOCK"])
    # We need to manually set SECTOR_ETF_MAP if the symbols differ,
    # but here "Technology" -> "XLK" is already in default map.

    result = selector.select(
        mock_sector_prices,
        mock_regime_risk_on,
        use_fundamental=True,
        fundamentals=mock_fundamentals_sector,
    )

    tech_cand = next((c for c in result.candidates if c.symbol == "TECH_STOCK"), None)
    energy_cand = next((c for c in result.candidates if c.symbol == "ENERGY_STOCK"), None)

    assert tech_cand is not None

    # Tech stock should have "板块强势" in reason
    assert "板块强势" in tech_cand.reason

    # Energy stock might be filtered out or have low score.
    # If it survived, it should NOT have "板块强势" (maybe "板块弱势" if logic implemented)
    if energy_cand:
        assert "板块强势" not in energy_cand.reason


def test_rsi_overbought_penalty(mock_sector_prices, mock_regime_risk_on):
    """
    Test RSI Penalty.
    Manually spike price to create overbought condition.
    """
    prices = mock_sector_prices.copy()

    # Spike TECH_STOCK price in last 5 days to drive RSI > 80
    # Original is ~100 growing slowly. Let's jump it to 120, 130, 140...
    last_idx = prices.index[-10:]
    spike_vals = prices.loc[last_idx, "TECH_STOCK"] * (1 + np.linspace(0, 0.2, 10))
    prices.loc[last_idx, "TECH_STOCK"] = spike_vals

    selector = StockSelector(stock_pool=["TECH_STOCK"])
    result = selector.select(prices, mock_regime_risk_on, use_fundamental=False)

    cand = result.candidates[0]

    # Should have Penalty reason
    assert "RSI超买" in cand.reason
