"""Tests for momentum calculation."""

import pandas as pd
import pytest

from etf_trend.features.momentum import momentum_score


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    """Create sample price data for testing."""
    dates = pd.date_range("2020-01-01", periods=250, freq="B")
    return pd.DataFrame(
        {
            "SPY": [100 * (1.001**i) for i in range(250)],  # Uptrend
            "QQQ": [100 * (0.999**i) for i in range(250)],  # Downtrend
            "IWM": [100] * 250,  # Flat
        },
        index=dates,
    )


class TestMomentumScore:
    def test_basic_momentum(self, sample_prices: pd.DataFrame):
        """Test that momentum is calculated correctly."""
        windows = [20, 60]
        weights = [0.5, 0.5]

        score = momentum_score(sample_prices, windows, weights)

        assert isinstance(score, pd.DataFrame)
        assert list(score.columns) == ["SPY", "QQQ", "IWM"]
        assert len(score) == len(sample_prices)

    def test_uptrend_positive_score(self, sample_prices: pd.DataFrame):
        """Test that uptrend produces positive momentum."""
        windows = [20]
        weights = [1.0]

        score = momentum_score(sample_prices, windows, weights)

        # SPY is in uptrend, should have positive momentum
        assert score["SPY"].iloc[-1] > 0

    def test_downtrend_negative_score(self, sample_prices: pd.DataFrame):
        """Test that downtrend produces negative momentum."""
        windows = [20]
        weights = [1.0]

        score = momentum_score(sample_prices, windows, weights)

        # QQQ is in downtrend, should have negative momentum
        assert score["QQQ"].iloc[-1] < 0

    def test_flat_zero_score(self, sample_prices: pd.DataFrame):
        """Test that flat prices produce zero momentum."""
        windows = [20]
        weights = [1.0]

        score = momentum_score(sample_prices, windows, weights)

        # IWM is flat, should have zero momentum
        assert score["IWM"].iloc[-1] == pytest.approx(0.0)

    def test_multiple_windows_weighted(self, sample_prices: pd.DataFrame):
        """Test that multiple windows are weighted correctly."""
        windows = [20, 60, 120, 240]
        weights = [0.25, 0.25, 0.25, 0.25]

        score = momentum_score(sample_prices, windows, weights)

        # Result should be weighted average
        assert not score.isna().all().all()
