"""Tests for backtest engine."""

import numpy as np
import pandas as pd
import pytest

from etf_trend.backtest.engine import run_backtest
from etf_trend.backtest.costs import turnover, cost_from_turnover


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    """Create sample price data for testing."""
    dates = pd.date_range("2020-01-01", periods=100, freq="B")
    return pd.DataFrame(
        {
            "SPY": [100 * (1.001**i) for i in range(100)],
            "QQQ": [100 * (1.0015**i) for i in range(100)],
        },
        index=dates,
    )


@pytest.fixture
def sample_weights(sample_prices: pd.DataFrame) -> pd.DataFrame:
    """Create sample weight data for testing."""
    return pd.DataFrame(
        {"SPY": 0.5, "QQQ": 0.5},
        index=sample_prices.index,
    )


class TestRunBacktest:
    def test_backtest_output_columns(
        self, sample_prices: pd.DataFrame, sample_weights: pd.DataFrame
    ):
        """Test that backtest returns expected columns."""
        result = run_backtest(sample_prices, sample_weights, cost_bps=2.0)

        expected_cols = ["port_ret", "net_ret", "nav", "drawdown", "turnover", "cost"]
        assert list(result.columns) == expected_cols

    def test_nav_starts_at_one(self, sample_prices: pd.DataFrame, sample_weights: pd.DataFrame):
        """Test that NAV starts close to 1.0."""
        result = run_backtest(sample_prices, sample_weights, cost_bps=2.0)

        # First NAV should be 1.0 (no return on day 1)
        assert result["nav"].iloc[0] == pytest.approx(1.0, rel=0.01)

    def test_positive_returns_increase_nav(
        self, sample_prices: pd.DataFrame, sample_weights: pd.DataFrame
    ):
        """Test that positive returns increase NAV."""
        result = run_backtest(sample_prices, sample_weights, cost_bps=2.0)

        # Uptrending prices should produce increasing NAV
        assert result["nav"].iloc[-1] > result["nav"].iloc[0]

    def test_drawdown_zero_or_negative(
        self, sample_prices: pd.DataFrame, sample_weights: pd.DataFrame
    ):
        """Test that drawdown is always <= 0."""
        result = run_backtest(sample_prices, sample_weights, cost_bps=2.0)

        assert (result["drawdown"] <= 0).all()

    def test_cost_proportional_to_turnover(
        self, sample_prices: pd.DataFrame, sample_weights: pd.DataFrame
    ):
        """Test that cost is proportional to turnover."""
        result = run_backtest(sample_prices, sample_weights, cost_bps=2.0)

        # cost = turnover * (cost_bps / 10000)
        expected_cost = result["turnover"] * (2.0 / 10000)
        pd.testing.assert_series_equal(result["cost"], expected_cost, check_names=False)

    def test_net_return_less_than_gross(
        self, sample_prices: pd.DataFrame, sample_weights: pd.DataFrame
    ):
        """Test that net return <= gross return (due to costs)."""
        result = run_backtest(sample_prices, sample_weights, cost_bps=2.0)

        assert (result["net_ret"] <= result["port_ret"] + 1e-10).all()


class TestTurnover:
    def test_no_change_zero_turnover(self, sample_weights: pd.DataFrame):
        """Test that constant weights produce zero turnover."""
        to = turnover(sample_weights)

        # After first day, turnover should be 0
        assert (to.iloc[1:] == 0).all()

    def test_full_rebalance_high_turnover(self):
        """Test that full position change produces high turnover."""
        dates = pd.date_range("2020-01-01", periods=3, freq="B")
        weights = pd.DataFrame(
            {
                "SPY": [0.5, 0.0, 0.5],  # 50% -> 0% -> 50%
                "QQQ": [0.5, 1.0, 0.5],  # 50% -> 100% -> 50%
            },
            index=dates,
        )

        to = turnover(weights)

        # Day 2: |0.5-0| + |1.0-0.5| = 1.0
        assert to.iloc[1] == pytest.approx(1.0)


class TestCostFromTurnover:
    def test_cost_calculation(self):
        """Test cost calculation from turnover."""
        to = pd.Series([0.0, 0.5, 1.0])
        cost = cost_from_turnover(to, cost_bps=10.0)

        expected = pd.Series([0.0, 0.0005, 0.001])
        pd.testing.assert_series_equal(cost, expected)
