"""Tests for rebalance logic."""

import pandas as pd
import pytest

from etf_trend.portfolio.rebalance import build_monthly_weights
from etf_trend.data.calendar import month_end_trading_days


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    """Create sample price data spanning multiple months."""
    dates = pd.date_range("2020-01-01", periods=80, freq="B")
    return pd.DataFrame(
        {
            "SPY": [100 * (1.001**i) for i in range(80)],  # Uptrend
            "QQQ": [100 * (1.0015**i) for i in range(80)],  # Stronger uptrend
            "IWM": [100 * (0.999**i) for i in range(80)],  # Downtrend
        },
        index=dates,
    )


@pytest.fixture
def sample_score(sample_prices: pd.DataFrame) -> pd.DataFrame:
    """Create sample momentum score."""
    return pd.DataFrame(
        {
            "SPY": 0.05,  # Positive momentum
            "QQQ": 0.10,  # Higher positive momentum
            "IWM": -0.05,  # Negative momentum
        },
        index=sample_prices.index,
    )


@pytest.fixture
def sample_trend_on(sample_prices: pd.DataFrame) -> pd.DataFrame:
    """Create sample trend filter."""
    return pd.DataFrame(
        {
            "SPY": True,  # Above MA
            "QQQ": True,  # Above MA
            "IWM": False,  # Below MA
        },
        index=sample_prices.index,
    )


class TestBuildMonthlyWeights:
    def test_output_shape(
        self,
        sample_prices: pd.DataFrame,
        sample_score: pd.DataFrame,
        sample_trend_on: pd.DataFrame,
    ):
        """Test that output has same shape as input prices."""
        weights = build_monthly_weights(
            prices=sample_prices,
            score=sample_score,
            trend_on=sample_trend_on,
            vol_lookback=20,
            max_weight_single=0.4,
            max_weight_core=0.7,
            core_symbols=["SPY", "QQQ"],
        )

        assert weights.shape == sample_prices.shape
        assert list(weights.columns) == list(sample_prices.columns)

    def test_weights_sum_leq_one(
        self,
        sample_prices: pd.DataFrame,
        sample_score: pd.DataFrame,
        sample_trend_on: pd.DataFrame,
    ):
        """Test that weights sum to <= 1.0."""
        weights = build_monthly_weights(
            prices=sample_prices,
            score=sample_score,
            trend_on=sample_trend_on,
            vol_lookback=20,
            max_weight_single=0.4,
            max_weight_core=0.7,
            core_symbols=["SPY", "QQQ"],
        )

        assert (weights.sum(axis=1) <= 1.0 + 1e-10).all()

    def test_negative_momentum_zero_weight(
        self,
        sample_prices: pd.DataFrame,
        sample_score: pd.DataFrame,
        sample_trend_on: pd.DataFrame,
    ):
        """Test that assets with negative momentum get zero weight."""
        weights = build_monthly_weights(
            prices=sample_prices,
            score=sample_score,
            trend_on=sample_trend_on,
            vol_lookback=20,
            max_weight_single=0.4,
            max_weight_core=0.7,
            core_symbols=["SPY", "QQQ"],
        )

        # IWM has negative momentum, should have 0 weight
        assert (weights["IWM"] == 0).all()

    def test_trend_off_zero_weight(
        self,
        sample_prices: pd.DataFrame,
        sample_score: pd.DataFrame,
        sample_trend_on: pd.DataFrame,
    ):
        """Test that assets with trend_on=False get zero weight."""
        # IWM has trend_on=False, should have 0 weight
        weights = build_monthly_weights(
            prices=sample_prices,
            score=sample_score,
            trend_on=sample_trend_on,
            vol_lookback=20,
            max_weight_single=0.4,
            max_weight_core=0.7,
            core_symbols=["SPY", "QQQ"],
        )

        assert (weights["IWM"] == 0).all()


class TestMonthEndTradingDays:
    def test_returns_month_ends(self):
        """Test that function returns month-end trading days."""
        # Use 120 business days (~6 months) to ensure at least 2 month ends
        dates = pd.date_range("2020-01-01", periods=120, freq="B")

        month_ends = month_end_trading_days(dates)

        # Should have at least 2 month ends in 120 business days
        assert len(month_ends) >= 2

    def test_dates_in_original_index(self):
        """Test that returned dates are in the original index."""
        dates = pd.date_range("2020-01-01", periods=60, freq="B")

        month_ends = month_end_trading_days(dates)

        for d in month_ends:
            assert d in dates
