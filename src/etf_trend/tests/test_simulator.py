"""
Unit Tests for Backtest Simulator (Phase 4)
============================================

Tests for:
- simulator.py: StrategySimulator class.
"""

import pytest
import pandas as pd
import numpy as np

from etf_trend.backtest.simulator import StrategySimulator, BacktestResult


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_prices():
    """Generate mock price data for backtesting."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", "2023-03-31", freq="B")
    prices = pd.DataFrame(index=dates)

    # Stocks
    prices["AAPL"] = 150 + np.cumsum(np.random.randn(len(dates)) * 0.5)
    prices["MSFT"] = 300 + np.cumsum(np.random.randn(len(dates)) * 0.5)
    prices["NVDA"] = 400 + np.cumsum(np.random.randn(len(dates)) * 0.5)

    # Market benchmark (required by RegimeEngine)
    prices["SPY"] = 400 + np.cumsum(np.random.randn(len(dates)) * 0.3)

    return prices


# =============================================================================
# Simulator Tests
# =============================================================================


class TestStrategySimulator:
    """Tests for StrategySimulator class."""

    def test_init_creates_simulator(self, mock_prices):
        """Test that simulator initializes correctly."""
        sim = StrategySimulator(
            prices=mock_prices, stock_pool=["AAPL", "MSFT", "NVDA"], initial_capital=100_000
        )

        assert sim.initial_capital == 100_000
        assert sim.stock_pool == ["AAPL", "MSFT", "NVDA"]

    def test_run_returns_backtest_result(self, mock_prices):
        """Test that run() returns a BacktestResult."""
        sim = StrategySimulator(
            prices=mock_prices, stock_pool=["AAPL", "MSFT", "NVDA"], rebalance_freq="ME"  # Monthly
        )

        result = sim.run("2023-01-01", "2023-03-31")

        assert isinstance(result, BacktestResult)

    def test_nav_history_not_empty(self, mock_prices):
        """Test that NAV history is populated."""
        sim = StrategySimulator(
            prices=mock_prices, stock_pool=["AAPL", "MSFT", "NVDA"], rebalance_freq="ME"
        )

        result = sim.run("2023-01-01", "2023-03-31")

        assert not result.nav.empty
        assert "nav" in result.nav.columns

    def test_nav_starts_at_initial_capital(self, mock_prices):
        """Test that NAV starts at initial capital."""
        initial = 50_000
        sim = StrategySimulator(
            prices=mock_prices,
            stock_pool=["AAPL", "MSFT", "NVDA"],
            initial_capital=initial,
            rebalance_freq="ME",
        )

        result = sim.run("2023-01-01", "2023-03-31")

        # First NAV should be close to initial capital
        first_nav = result.nav["nav"].iloc[0]
        assert first_nav == pytest.approx(initial, rel=0.01)

    def test_stats_contains_expected_metrics(self, mock_prices):
        """Test that stats contains expected performance metrics."""
        sim = StrategySimulator(
            prices=mock_prices, stock_pool=["AAPL", "MSFT", "NVDA"], rebalance_freq="ME"
        )

        result = sim.run("2023-01-01", "2023-03-31")

        expected_metrics = ["Ann Return", "Ann Vol", "Sharpe", "Max Drawdown"]
        for metric in expected_metrics:
            assert metric in result.stats.index, f"Missing metric: {metric}"
