
import pytest
import pandas as pd
import numpy as np
from etf_trend.execution.executor import TradeExecutor, calculate_atr, TradePlan
from etf_trend.allocator.core import AllocationResult
from etf_trend.selector.satellite import StockCandidate

@pytest.fixture
def mock_prices():
    """
    构造模拟价格数据：100天，每天涨1%，无波动（方便计算ATR）
    """
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    
    # 构造两个资产
    # SPY: 线性上涨，方便计算收益率 ATR
    spy_price = 100 * (1.01 ** np.arange(100))
    
    # GLD: 波动大一点
    gld_price = 100 * (1.005 ** np.arange(100))
    gld_price += np.random.normal(0, 1, 100)
    
    return pd.DataFrame({
        "SPY": spy_price,
        "GLD": gld_price
    }, index=dates)

@pytest.fixture
def allocation_result():
    return AllocationResult(
        weights={"SPY": 0.6, "GLD": 0.0}, # SPY 买入, GLD 卖出
        equity_weights={"SPY": 0.6},
        defensive_weights={"GLD": 0.0},
        regime="RISK_ON",
        risk_budget=1.0,
        metadata={}
    )

def test_calculate_atr():
    """
    测试 ATR 计算
    """
    # 构造极简数据: 每天涨10% (pct_change=0.1)
    # Price: 100, 110, 121...
    dates = pd.date_range("2023-01-01", periods=20, freq="B")
    prices = pd.DataFrame({"A": [100 * (1.1**i) for i in range(20)]}, index=dates)
    
    # ATR = Rolling(abs(pct_change)).mean() * Price
    # pct_change 恒定为 0.1
    # ATR = 0.1 * Price
    
    atr = calculate_atr(prices, window=5)
    
    # 验证最后一天的 ATR
    last_price = prices["A"].iloc[-1]
    expected_atr = last_price * 0.1
    
    # 允许微小误差 (浮点精度)
    assert abs(atr["A"].iloc[-1] - expected_atr) < 0.01

def test_trade_plan_generation(mock_prices, allocation_result):
    """
    测试 ETF 交易计划生成
    """
    executor = TradeExecutor(
        atr_window=14,
        atr_multiplier=2.0,
        entry_pullback_pct=0.02
    )
    
    plans = executor.generate_trade_plans(mock_prices, allocation_result)
    
    # 应该有 2 个计划 (SPY, GLD)
    assert len(plans) == 2
    
    # 验证 SPY (买入)
    spy_plan = next(p for p in plans if p.symbol == "SPY")
    assert spy_plan.action == "BUY"
    assert spy_plan.target_weight == 0.6
    
    # 验证价格逻辑
    # Entry Moderate = Current * (1 - 0.02)
    assert spy_plan.entry_moderate == spy_plan.current_price * 0.98
    
    # Stop Normal = Entry Moderate - (ATR * 2.0)
    expected_stop = spy_plan.entry_moderate - (spy_plan.atr * 2.0)
    assert abs(spy_plan.stop_normal - expected_stop) < 0.01

    # 验证 GLD (卖出/清仓)
    gld_plan = next(p for p in plans if p.symbol == "GLD")
    assert gld_plan.action == "SELL"
    # 卖出计划没有入场点
    assert gld_plan.entry_moderate is None

def test_stock_plan_generation(mock_prices):
    """
    测试个股交易计划生成 (更宽的止损止盈)
    """
    executor = TradeExecutor()
    
    # 构造个股候选
    candidates = [
        StockCandidate(
            symbol="SPY", # 复用数据里的 SPY 当做个股测试
            name="Test Stock",
            price=100.0,
            momentum_score=90.0,
            volatility=20.0,
            above_ma200=True,
            signal_strength=0.8,
            recommendation="强烈推荐",
            reason="Test"
        )
    ]
    
    plans = executor.generate_stock_plans(mock_prices, candidates)
    
    assert len(plans) == 1
    plan = plans[0]
    
    assert plan.symbol == "SPY"
    assert plan.action == "BUY"
    
    # 个股参数校验
    # Stop Normal = Entry - (ATR * 3.0) (代码里写死的个股倍数)
    expected_stop = plan.entry_moderate - (plan.atr * 3.0)
    assert abs(plan.stop_normal - expected_stop) < 0.01
    
    # TP3 = Entry + (ATR * 10.0)
    expected_tp3 = plan.entry_moderate - (plan.atr * 10.0) # 修正: 是 + 
    expected_tp3_correct = plan.entry_moderate + (plan.atr * 10.0)
    
    assert abs(plan.tp3 - expected_tp3_correct) < 0.01

def test_missing_data_handling():
    """测试缺失数据处理"""
    executor = TradeExecutor()
    alloc = AllocationResult(
        weights={"UNKNOWN": 0.5}, 
        equity_weights={},
        defensive_weights={},
        regime="RISK_ON", 
        risk_budget=1.0, 
        metadata={}
    )
    prices = pd.DataFrame({"A": [1,2,3]}) # 没有 UNKNOWN
    
    plans = executor.generate_trade_plans(prices, alloc)
    assert len(plans) == 0
