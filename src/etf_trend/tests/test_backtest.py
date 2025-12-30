
import pytest
import pandas as pd
import numpy as np
from etf_trend.backtest.engine import run_backtest
from etf_trend.backtest.metrics import perf_stats

@pytest.fixture
def mock_prices():
    """构造模拟价格数据: 两资产, 稳定上涨"""
    dates = pd.date_range("2023-01-01", periods=252, freq="B")
    np.random.seed(42)

    # A: 涨 50%, B: 涨 20%
    a = 100 * (1.002 ** np.arange(252))
    b = 100 * (1.0008 ** np.arange(252))

    return pd.DataFrame({"A": a, "B": b}, index=dates)

@pytest.fixture
def mock_weights():
    """构造静态等权组合"""
    dates = pd.date_range("2023-01-01", periods=252, freq="B")
    return pd.DataFrame({"A": 0.5, "B": 0.5}, index=dates)

def test_backtest_nav_increases(mock_prices, mock_weights):
    """
    测试：上涨市场中 NAV 应该增长
    """
    result = run_backtest(mock_prices, mock_weights, cost_bps=10)

    # NAV 最终值 > 初始值
    assert result["nav"].iloc[-1] > result["nav"].iloc[0]

def test_backtest_drawdown_negative(mock_prices, mock_weights):
    """
    测试：回撤应该是非正数
    """
    result = run_backtest(mock_prices, mock_weights, cost_bps=10)

    assert all(result["drawdown"] <= 0)

def test_backtest_turnover_with_static_weights(mock_prices, mock_weights):
    """
    测试：静态权重下换手率应很低 (接近0)
    """
    result = run_backtest(mock_prices, mock_weights, cost_bps=10)

    # 静态等权情况下, 只有第一天有turnover
    # 之后应该接近0
    assert result["turnover"].iloc[2:].mean() < 0.01

def test_perf_stats_sharpe_positive(mock_prices, mock_weights):
    """
    测试：上涨市场中夏普比率应为正
    """
    bt = run_backtest(mock_prices, mock_weights, cost_bps=10)
    stats = perf_stats(bt)

    assert stats["Sharpe"] > 0

def test_perf_stats_max_dd_negative(mock_prices, mock_weights):
    """
    测试：最大回撤是负数
    """
    bt = run_backtest(mock_prices, mock_weights, cost_bps=10)
    stats = perf_stats(bt)

    assert stats["Max Drawdown"] <= 0
