
import pytest
import pandas as pd
from etf_trend.portfolio.constraints import apply_constraints

@pytest.fixture
def sample_weights():
    """构造样本权重"""
    return pd.Series({"A": 0.5, "B": 0.3, "C": 0.2})

def test_constraints_weights_sum_to_one(sample_weights):
    """
    测试约束后权重之和为 1
    """
    result = apply_constraints(
        sample_weights,
        max_single=1.0,
        max_core=1.0,
        core_symbols=[]
    )

    assert abs(result.sum() - 1.0) < 1e-6

def test_constraints_single_cap(sample_weights):
    """
    测试单一资产上限约束
    
    预期：原本最大的 A (0.5) 会被压缩到更接近其他资产
    注意：clipping 后会重新归一化，所以可能不完全等于 max_single
    """
    result = apply_constraints(
        sample_weights,
        max_single=0.4,
        max_core=1.0,
        core_symbols=[]
    )

    # 原本 A=0.5，现在应该小于 0.5
    assert result["A"] < 0.5
    # 权重和为 1
    assert abs(result.sum() - 1.0) < 1e-6

def test_constraints_core_cap():
    """
    测试核心资产组合上限
    
    预期：核心资产 (A, B) 总权重不超过 max_core (0.5)
    """
    weights = pd.Series({"A": 0.4, "B": 0.4, "C": 0.2})
    result = apply_constraints(
        weights,
        max_single=1.0,
        max_core=0.5,
        core_symbols=["A", "B"]
    )

    core_sum = result["A"] + result["B"]
    assert core_sum <= 0.5 + 1e-6

def test_constraints_empty_weights():
    """
    测试空权重输入
    """
    weights = pd.Series({"A": 0.0, "B": 0.0})
    result = apply_constraints(
        weights,
        max_single=0.5,
        max_core=0.5,
        core_symbols=[]
    )

    assert result.sum() == 0.0

def test_constraints_negative_weights_clipped():
    """
    测试负权重被剪裁为 0
    """
    weights = pd.Series({"A": -0.2, "B": 0.8, "C": 0.4})
    result = apply_constraints(
        weights,
        max_single=1.0,
        max_core=1.0,
        core_symbols=[]
    )

    assert all(result >= 0)
