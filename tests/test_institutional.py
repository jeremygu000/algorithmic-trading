"""
验证机构级升级模块
"""

import pandas as pd
import numpy as np
from etf_trend.analysis.attribution import calculate_alpha_beta, calculate_advanced_metrics
from etf_trend.allocator.optimizer import PortfolioOptimizer

def test_attribution():
    print("\n=== Testing Attribution ===")
    
    # Generate dummy data
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=252)
    bench_returns = pd.Series(np.random.normal(0.0005, 0.01, 252), index=dates)
    # Portfolio = 1.2 * Benchmark + Alpha + Noise
    port_returns = 1.2 * bench_returns + 0.0001 + np.random.normal(0, 0.002, 252)
    
    metrics = calculate_advanced_metrics(port_returns, bench_returns)
    print("Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")
        
    assert "alpha" in metrics
    assert "beta" in metrics
    assert "sortino_ratio" in metrics

def test_optimizer():
    print("\n=== Testing Optimizer ===")
    
    # Generate dummy returns for 3 assets
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=252)
    df = pd.DataFrame({
        "AssetA": np.random.normal(0.0005, 0.01, 252), # Low vol
        "AssetB": np.random.normal(0.0008, 0.02, 252), # High vol
        "AssetC": np.random.normal(0.0006, 0.015, 252) # Med vol
    }, index=dates)
    
    opt = PortfolioOptimizer(df)
    
    # Min Variance
    w_min = opt.optimize("min_variance")
    print("\nMin Variance Weights:")
    print(w_min)
    assert np.isclose(w_min.sum(), 1.0)
    assert w_min["AssetA"] > w_min["AssetB"] # Low vol should have higher weight
    
    # Risk Parity
    w_rp = opt.optimize("risk_parity")
    print("\nRisk Parity Weights:")
    print(w_rp)
    assert np.isclose(w_rp.sum(), 1.0)
    assert w_rp["AssetA"] > w_rp["AssetB"]

if __name__ == "__main__":
    test_attribution()
    test_optimizer()
    print("\n✅ All Institutional Tests Passed!")
