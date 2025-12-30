"""Tests for portfolio constraints."""

import pandas as pd
import pytest

from etf_trend.portfolio.constraints import apply_constraints


class TestApplyConstraints:
    def test_single_asset_cap(self):
        """Test that single asset weight is capped after normalization."""
        w = pd.Series({"SPY": 0.8, "QQQ": 0.2})

        result = apply_constraints(w, max_single=0.4, max_core=1.0, core_symbols=[])

        # Both assets capped at 0.4, then renormalized to sum to 1.0
        # SPY: min(0.8, 0.4) = 0.4, QQQ: min(0.2, 0.4) = 0.2
        # After renorm: SPY = 0.4/0.6 = 0.667, QQQ = 0.2/0.6 = 0.333
        assert result["SPY"] <= 0.67
        assert result.sum() == pytest.approx(1.0)

    def test_core_group_cap(self):
        """Test that core group weight is capped."""
        w = pd.Series({"SPY": 0.5, "QQQ": 0.4, "IWM": 0.1})

        result = apply_constraints(w, max_single=1.0, max_core=0.7, core_symbols=["SPY", "QQQ"])

        core_weight = result["SPY"] + result["QQQ"]
        assert core_weight <= 0.7 + 1e-10
        assert result.sum() == pytest.approx(1.0)

    def test_zero_weights_unchanged(self):
        """Test that all-zero weights remain zero."""
        w = pd.Series({"SPY": 0.0, "QQQ": 0.0})

        result = apply_constraints(w, max_single=0.4, max_core=0.7, core_symbols=["SPY"])

        assert result.sum() == 0.0

    def test_negative_weights_clipped(self):
        """Test that negative weights are clipped to zero."""
        w = pd.Series({"SPY": -0.5, "QQQ": 1.5})

        result = apply_constraints(w, max_single=0.4, max_core=1.0, core_symbols=[])

        assert (result >= 0).all()

    def test_weights_sum_to_one(self):
        """Test that final weights sum to 1.0."""
        w = pd.Series({"SPY": 0.3, "QQQ": 0.3, "IWM": 0.4})

        result = apply_constraints(w, max_single=0.4, max_core=0.7, core_symbols=["SPY", "QQQ"])

        assert result.sum() == pytest.approx(1.0)

    def test_core_symbol_not_in_weights(self):
        """Test handling when core_symbol is not in weights index."""
        w = pd.Series({"SPY": 0.5, "QQQ": 0.5})

        # XLF is not in weights, should not cause error
        result = apply_constraints(w, max_single=0.5, max_core=0.7, core_symbols=["SPY", "XLF"])

        assert result.sum() == pytest.approx(1.0)
