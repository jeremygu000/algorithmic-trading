"""
Unit Tests for ML Module (Phase 4)
==================================

Tests for:
- features.py: Feature generation and dataset creation.
- model.py: MLScorer training and prediction.
"""

import pytest
import pandas as pd
import numpy as np

from etf_trend.ml.features import generate_features, create_dataset
from etf_trend.ml.model import MLScorer


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_prices():
    """Generate mock price data with sufficient history for MA200."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", "2023-06-01", freq="B")
    prices = pd.DataFrame(index=dates)
    prices["AAPL"] = 100 * (1.001 ** np.arange(len(dates))) + np.random.normal(0, 1, len(dates))
    prices["MSFT"] = 150 * (1.0005 ** np.arange(len(dates))) + np.random.normal(0, 1, len(dates))
    return prices


# =============================================================================
# Feature Generation Tests
# =============================================================================


class TestFeatureGeneration:
    """Tests for generate_features function."""

    def test_generate_features_returns_dataframe(self, mock_prices):
        """Test that generate_features returns a valid DataFrame."""
        result = generate_features(mock_prices)

        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    def test_generate_features_has_expected_columns(self, mock_prices):
        """Test that generated features include expected columns."""
        result = generate_features(mock_prices)

        expected_cols = [
            "price_vs_ma20",
            "price_vs_ma50",
            "price_vs_ma200",
            "mom_1m",
            "mom_3m",
            "mom_6m",
            "vol_annual",
            "atr_pct",
            "rsi",
        ]

        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_generate_features_multiindex(self, mock_prices):
        """Test that result has MultiIndex (date, symbol)."""
        result = generate_features(mock_prices)

        assert result.index.nlevels == 2
        assert result.index.names == ["date", "symbol"]

    def test_create_dataset_includes_target(self, mock_prices):
        """Test that create_dataset adds a 'target' column."""
        result = create_dataset(mock_prices, forward_window=5)

        assert "target" in result.columns

    def test_create_dataset_binary_target(self, mock_prices):
        """Test that binary target contains only 0 and 1."""
        result = create_dataset(mock_prices, forward_window=5, binary_target=True)

        unique_vals = result["target"].unique()
        assert set(unique_vals).issubset({0, 1})


# =============================================================================
# ML Model Tests
# =============================================================================


class TestMLScorer:
    """Tests for MLScorer class."""

    def test_train_creates_model(self, mock_prices):
        """Test that training creates a valid model."""
        dataset = create_dataset(mock_prices, forward_window=5)

        scorer = MLScorer()
        scorer.train(dataset)

        assert scorer.model is not None

    def test_predict_returns_series(self, mock_prices):
        """Test that predict returns a pandas Series."""
        dataset = create_dataset(mock_prices, forward_window=5)

        scorer = MLScorer()
        scorer.train(dataset)
        preds = scorer.predict(dataset)

        assert isinstance(preds, pd.Series)
        assert len(preds) == len(dataset)

    def test_predict_probability_range(self, mock_prices):
        """Test that predictions are probabilities in [0, 1] range."""
        dataset = create_dataset(mock_prices, forward_window=5)

        scorer = MLScorer()
        scorer.train(dataset)
        preds = scorer.predict(dataset)

        assert preds.min() >= 0.0
        assert preds.max() <= 1.0

    def test_predict_without_training_raises(self):
        """Test that predicting without training raises an error."""
        scorer = MLScorer()

        dummy_df = pd.DataFrame(
            {
                "price_vs_ma20": [0.1],
                "price_vs_ma50": [0.1],
                "price_vs_ma200": [0.1],
                "mom_1m": [0.05],
                "mom_3m": [0.1],
                "mom_6m": [0.15],
                "vol_annual": [0.2],
                "atr_pct": [0.02],
                "rsi": [0.5],
            }
        )

        with pytest.raises(ValueError, match="Model not trained"):
            scorer.predict(dummy_df)
