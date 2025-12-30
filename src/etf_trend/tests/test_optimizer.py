import pytest
import pandas as pd
import numpy as np
from etf_trend.allocator.optimizer import PortfolioOptimizer


@pytest.fixture
def mock_returns():
    """
    构造模拟收益率数据 (252天, 3资产)

    资产特征：
    - A: 低波动 (std=0.01)
    - B: 中波动 (std=0.02)
    - C: 高波动 (std=0.03)
    """
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=252, freq="B")

    returns = pd.DataFrame(
        {
            "A": np.random.normal(0.0005, 0.01, 252),  # 低波动
            "B": np.random.normal(0.0003, 0.02, 252),  # 中波动
            "C": np.random.normal(0.0001, 0.03, 252),  # 高波动
        },
        index=dates,
    )

    return returns


def test_min_variance_weights_sum_to_one(mock_returns):
    """
    测试最小方差组合权重之和为 1
    """
    optimizer = PortfolioOptimizer(mock_returns)
    weights = optimizer.optimize(method="min_variance")

    assert abs(weights.sum() - 1.0) < 1e-6


def test_min_variance_prefers_low_vol(mock_returns):
    """
    测试最小方差组合更偏好低波动率资产

    预期：资产 A (低波动) 获得更高权重
    """
    optimizer = PortfolioOptimizer(mock_returns)
    weights = optimizer.optimize(method="min_variance")

    # A 应该是权重最大的
    assert weights["A"] > weights["B"]
    assert weights["A"] > weights["C"]


def test_risk_parity_weights_sum_to_one(mock_returns):
    """
    测试风险平价组合权重之和为 1
    """
    optimizer = PortfolioOptimizer(mock_returns)
    weights = optimizer.optimize(method="risk_parity")

    assert abs(weights.sum() - 1.0) < 1e-6


def test_risk_parity_balances_risk(mock_returns):
    """
    测试风险平价组合风险贡献平衡

    预期：低波动资产权重更高，使得各资产风险贡献接近
    """
    optimizer = PortfolioOptimizer(mock_returns)
    weights = optimizer.optimize(method="risk_parity")

    # 低波动资产 A 应该还是权重较高
    # (因为要贡献相同的风险，低波动资产需要更多权重)
    assert weights["A"] > weights["C"]


def test_max_weight_constraint(mock_returns):
    """
    测试单资产最大权重约束
    """
    optimizer = PortfolioOptimizer(mock_returns)
    weights = optimizer.optimize(method="min_variance", max_weight=0.5)

    for w in weights.values:
        assert w <= 0.5 + 1e-6  # 允许微小误差


def test_unknown_method_raises_error(mock_returns):
    """
    测试未知优化方法抛出错误
    """
    optimizer = PortfolioOptimizer(mock_returns)
    with pytest.raises(ValueError):
        optimizer.optimize(method="unknown_method")
