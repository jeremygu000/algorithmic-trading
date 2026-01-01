"""
Verification Script for Phase 4
===============================

1. Test Feature Gen
2. Test ML Model Training/Prediction
3. Test Strategy Simulator (Backtest)
"""

import pandas as pd
import numpy as np
import shutil
from etf_trend.ml.features import generate_features, create_dataset
from etf_trend.ml.model import MLScorer
from etf_trend.backtest.simulator import StrategySimulator

def test_ml_pipeline():
    print(">>> Testing ML Pipeline...")
    
    # Mock Price Data
    dates = pd.date_range("2020-01-01", "2023-06-01", freq="B")
    prices = pd.DataFrame(index=dates)
    prices["A"] = 100 * (1.001 ** np.arange(len(dates))) + np.random.normal(0, 1, len(dates)) # Uptrend
    prices["B"] = 100 * (0.999 ** np.arange(len(dates))) + np.random.normal(0, 1, len(dates)) # Downtrend
    
    # 1. Feature Gen
    print("  Generating features...")
    feats = generate_features(prices)
    assert not feats.empty
    print(f"  Features shape: {feats.shape}")
    
    # 2. Dataset
    print("  Creating dataset...")
    dataset = create_dataset(prices, forward_window=5)
    assert 'target' in dataset.columns
    print(f"  Dataset shape: {dataset.shape}")
    
    # 3. Train
    print("  Training LightGBM...")
    scorer = MLScorer()
    scorer.train(dataset)
    print("  Model trained.")
    
    # 4. Predict
    print("  Predicting...")
    preds = scorer.predict(dataset)
    assert len(preds) == len(dataset)
    print("  Prediction done.")
    
    return scorer

def test_backtest_simulator():
    print("\n>>> Testing Backtest Simulator...")
    
    # Mock Data
    dates = pd.date_range("2020-01-01", "2023-03-31", freq="B")
    prices = pd.DataFrame(index=dates)
    # 3 Stocks
    prices["AAPL"] = 150 + np.cumsum(np.random.randn(len(dates)))
    prices["MSFT"] = 300 + np.cumsum(np.random.randn(len(dates)))
    prices["NVDA"] = 400 + np.cumsum(np.random.randn(len(dates)))
    # Add SPY for Regime Detection
    prices["SPY"] = 400 + np.cumsum(np.random.randn(len(dates)))
    
    # Run Sim
    sim = StrategySimulator(
        prices=prices,
        stock_pool=["AAPL", "MSFT", "NVDA"],
        initial_capital=100_000,
        rebalance_freq="ME" # Monthly
    )
    
    res = sim.run("2023-01-01", "2023-03-31")
    
    print("  Backtest Stats:")
    print(res.stats)
    
    # Basic Checks
    assert not res.nav.empty
    assert "nav" in res.nav.columns
    
    print("  Backtest completed successfully.")

if __name__ == "__main__":
    test_ml_pipeline()
    test_backtest_simulator()
    print("\n✅ Phase 4 Verification Passed!")
