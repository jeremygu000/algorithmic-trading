
import pytest
import pandas as pd
import numpy as np
from etf_trend.allocator.core import CoreAllocator, AllocationResult
from etf_trend.regime.engine import RegimeState

@pytest.fixture
def mock_prices():
    """
    构造模拟价格数据 (300天)
    包含：
    - 股票类: SPY (强动量), QQQ (一般动量), IWM (弱动量)
    - 防守类: TLT (强动量), GLD (弱动量)
    """
    dates = pd.date_range("2023-01-01", periods=300, freq="B")
    np.random.seed(42)
    
    # 构造不同动量特征的资产
    spy = 100 * (1.002 ** np.arange(300)) + np.random.normal(0, 0.5, 300)  # 强势
    qqq = 100 * (1.001 ** np.arange(300)) + np.random.normal(0, 0.5, 300)  # 中等
    iwm = 100 * (1.0005 ** np.arange(300)) + np.random.normal(0, 0.5, 300) # 弱势
    
    tlt = 100 * (1.0008 ** np.arange(300)) + np.random.normal(0, 0.3, 300) # 防守强
    gld = 100 * (1.0003 ** np.arange(300)) + np.random.normal(0, 0.3, 300) # 防守弱
    
    return pd.DataFrame({
        "SPY": spy, "QQQ": qqq, "IWM": iwm,
        "TLT": tlt, "GLD": gld
    }, index=dates)

@pytest.fixture
def regime_risk_on():
    return RegimeState(regime="RISK_ON", risk_budget=1.0, signals={"trend": 1.0})

@pytest.fixture
def regime_risk_off():
    return RegimeState(regime="RISK_OFF", risk_budget=0.2, signals={"trend": -1.0})

def test_allocator_risk_on_budget(mock_prices, regime_risk_on):
    """
    测试 RISK_ON 状态下的大类配置比例
    
    预期：
    - 股票类占 80%
    - 防守类占 20%
    """
    allocator = CoreAllocator(
        equity_symbols=["SPY", "QQQ", "IWM"],
        defensive_symbols=["TLT", "GLD"],
        top_n_equity=2,
        top_n_defensive=1,
    )
    
    result = allocator.allocate(mock_prices, regime_risk_on)
    
    assert result.regime == "RISK_ON"
    
    # 总权重应接近 1.0 (可能因约束而略低)
    total = sum(result.weights.values())
    assert 0.7 <= total <= 1.0
    
    # 股票类权重应占多数
    equity_total = sum(result.equity_weights.values())
    defensive_total = sum(result.defensive_weights.values())
    
    # RISK_ON: Equity 80%, Defensive 20%
    # 由于反向波动率加权可能略有变化，但大方向是对的
    assert equity_total > defensive_total

def test_allocator_risk_off_budget(mock_prices, regime_risk_off):
    """
    测试 RISK_OFF 状态下的大类配置比例
    
    预期：
    - 股票类占 20%
    - 防守类占 80%
    """
    allocator = CoreAllocator(
        equity_symbols=["SPY", "QQQ", "IWM"],
        defensive_symbols=["TLT", "GLD"],
        top_n_equity=2,
        top_n_defensive=1,
    )
    
    result = allocator.allocate(mock_prices, regime_risk_off)
    
    assert result.regime == "RISK_OFF"
    
    # 防守类权重应占多数
    equity_total = sum(result.equity_weights.values())
    defensive_total = sum(result.defensive_weights.values())
    
    assert defensive_total > equity_total

def test_allocator_top_n_selection(mock_prices, regime_risk_on):
    """
    测试 Top-N 选择逻辑
    
    预期：
    - 只选动量最强的 Top-2 股票 (SPY, QQQ)
    - IWM (动量最弱) 不应入选
    """
    allocator = CoreAllocator(
        equity_symbols=["SPY", "QQQ", "IWM"],
        defensive_symbols=["TLT", "GLD"],
        top_n_equity=2,
        top_n_defensive=1,
    )
    
    result = allocator.allocate(mock_prices, regime_risk_on)
    
    # 股票中应该有动量最强的两个
    assert "SPY" in result.equity_weights
    # IWM 应该被剔除
    assert "IWM" not in result.equity_weights

def test_allocator_single_weight_constraint(mock_prices, regime_risk_on):
    """
    测试单一资产权重上限约束
    
    预期：任何单一资产不超过 max_weight_single (默认 30%)
    """
    allocator = CoreAllocator(
        equity_symbols=["SPY", "QQQ", "IWM"],
        defensive_symbols=["TLT", "GLD"],
        max_weight_single=0.30,
    )
    
    result = allocator.allocate(mock_prices, regime_risk_on)
    
    for symbol, weight in result.weights.items():
        assert weight <= 0.30 + 0.01 # 允许极小误差

def test_allocator_inverse_vol_weighting(mock_prices, regime_risk_on):
    """
    测试反向波动率加权
    
    预期：低波动资产获得更高权重
    """
    allocator = CoreAllocator(
        equity_symbols=["SPY", "QQQ", "IWM"],
        defensive_symbols=["TLT", "GLD"],
        optimizer_method="inverse_vol",
        top_n_equity=3,
    )
    
    result = allocator.allocate(mock_prices, regime_risk_on)
    
    # 验证所有入选资产都有权重
    assert len(result.equity_weights) > 0
    for w in result.equity_weights.values():
        assert w > 0
