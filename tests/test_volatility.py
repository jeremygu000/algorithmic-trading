"""Tests for volatility calculation."""

import numpy as np
import pandas as pd
import pytest

from etf_trend.features.volatility import realized_vol_annual


@pytest.fixture
def sample_returns() -> pd.DataFrame:
    """Create sample return data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=100, freq="B")
    return pd.DataFrame(
        {
            "SPY": np.random.normal(0.0005, 0.01, 100),  # ~16% annual vol
            "QQQ": np.random.normal(0.0005, 0.02, 100),  # ~32% annual vol
        },
        index=dates,
    )


class TestRealizedVolAnnual:
    def test_basic_vol_calculation(self, sample_returns: pd.DataFrame):
        """Test that volatility is calculated correctly."""
        vol = realized_vol_annual(sample_returns, lookback=20)

        assert isinstance(vol, pd.DataFrame)
        assert list(vol.columns) == ["SPY", "QQQ"]
        assert len(vol) == len(sample_returns)

    def test_annualization_factor(self, sample_returns: pd.DataFrame):
        """Test that volatility is annualized with sqrt(252)."""
        lookback = 20
        vol = realized_vol_annual(sample_returns, lookback)

        # Manual calculation for comparison
        daily_std = sample_returns.rolling(lookback).std()
        expected_annual = daily_std * np.sqrt(252)

        pd.testing.assert_frame_equal(vol, expected_annual)

    def test_higher_vol_asset(self, sample_returns: pd.DataFrame):
        """Test that higher volatility asset has larger value."""
        vol = realized_vol_annual(sample_returns, lookback=20)

        # QQQ has 2x daily vol, should have higher annual vol
        assert vol["QQQ"].iloc[-1] > vol["SPY"].iloc[-1]

    def test_lookback_affects_smoothness(self, sample_returns: pd.DataFrame):
        """Test that longer lookback produces smoother volatility."""
        vol_short = realized_vol_annual(sample_returns, lookback=10)
        vol_long = realized_vol_annual(sample_returns, lookback=60)

        # Longer lookback should have lower variance in vol estimates
        # (comparing variance of the vol series itself)
        assert vol_long["SPY"].dropna().std() < vol_short["SPY"].dropna().std()

    def test_nan_at_start(self, sample_returns: pd.DataFrame):
        """Test that initial values are NaN due to rolling window."""
        vol = realized_vol_annual(sample_returns, lookback=20)

        # First 19 values should be NaN
        assert vol.iloc[:19].isna().all().all()
        assert vol.iloc[19:].notna().all().all()
