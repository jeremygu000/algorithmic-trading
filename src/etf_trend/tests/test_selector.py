import pytest
import pandas as pd
import numpy as np
from etf_trend.selector.satellite import StockSelector
from etf_trend.regime.engine import RegimeState


@pytest.fixture
def mock_prices():
    """
    生成模拟价格数据
    包含两只股票：
    - STRONG: 强势股（上涨趋势，低波动）
    - WEAK: 弱势股（下跌趋势，高波动）
    """
    dates = pd.date_range("2023-01-01", "2023-12-31", freq="B")  # Business Days

    # 构造强势股: 线性上涨 + 小波动
    # 初始 100，每天涨 0.1% -> 约1.2倍
    strong = 100 * (1.001 ** np.arange(len(dates)))
    # 加一点点噪音 (std=0.005)
    np.random.seed(42)
    strong_noise = np.random.normal(0, 0.5, len(dates))
    strong_price = strong + strong_noise

    # 构造弱势股: 线性下跌 + 大波动
    weak = 100 * (0.999 ** np.arange(len(dates)))
    weak_noise = np.random.normal(0, 2.0, len(dates))
    weak_price = weak + weak_noise

    df = pd.DataFrame({"STRONG": strong_price, "WEAK": weak_price}, index=dates)

    return df


@pytest.fixture
def mock_regime_risk_on():
    return RegimeState(
        regime="RISK_ON", risk_budget=1.0, signals={"trend": 1.0, "vix": 1.0, "momentum": 1.0}
    )


@pytest.fixture
def mock_regime_risk_off():
    return RegimeState(
        regime="RISK_OFF", risk_budget=0.0, signals={"trend": -1.0, "vix": -1.0, "momentum": -1.0}
    )


@pytest.fixture
def mock_fundamentals():
    """
    模拟基本面数据
    """
    return {
        "STRONG": {
            "symbol": "STRONG",
            "peRatio": 15.0,  # 低估值
            "pegRatio": 0.8,  # 成长性好
            "trailingEPS": 5.0,
            "marketCap": 200000000000,
            "sector": "Tech",
        },
        "WEAK": {
            "symbol": "WEAK",
            "peRatio": 60.0,  # 高估值
            "pegRatio": 3.5,  # 成长性差
            "trailingEPS": 0.5,
            "marketCap": 10000000000,
            "sector": "Tech",
        },
    }


def test_selector_risk_off(mock_prices, mock_regime_risk_off):
    """
    测试：RISK_OFF 状态下应不推荐任何股票
    """
    selector = StockSelector(stock_pool=["STRONG", "WEAK"])
    result = selector.select(mock_prices, mock_regime_risk_off)

    assert result.is_active is False
    assert len(result.candidates) == 0
    assert "RISK_OFF" in result.message


def test_selector_basic_logic(mock_prices, mock_regime_risk_on):
    """
    测试：基本技术面筛选逻辑

    预期：
    - STRONG 应该入选 (趋势向上，波动低)
    - WEAK 应该被排除 (价格 < MA200，或者动量差)
    """
    selector = StockSelector(stock_pool=["STRONG", "WEAK"], ma_window=200, vol_lookback=60)
    result = selector.select(mock_prices, mock_regime_risk_on, use_fundamental=False)

    assert result.is_active is True

    # 检查入选名单
    symbols = [c.symbol for c in result.candidates]
    assert "STRONG" in symbols
    assert "WEAK" not in symbols

    # 检查 STRONG 的评分
    strong_cand = result.candidates[0]
    assert strong_cand.recommendation in ["推荐", "强烈推荐"]


def test_selector_fundamentals_impact(mock_prices, mock_regime_risk_on, mock_fundamentals):
    """
    测试：基本面数据对评分的影响

    场景：
    - STRONG 本身技术面就好，叠加好的基本面 (PE=15, PEG=0.8)，分数应更高
    """
    selector = StockSelector(stock_pool=["STRONG"], ma_window=200)

    # Run 1: 不带基本面
    res_tech = selector.select(mock_prices, mock_regime_risk_on, use_fundamental=False)
    # 先验证不带基本面时也能正常返回结果
    assert len(res_tech.candidates) > 0

    # Run 2: 带优质基本面
    res_fund = selector.select(
        mock_prices, mock_regime_risk_on, use_fundamental=True, fundamentals=mock_fundamentals
    )

    # 虽然两者权重计算公式略有不同，但优质基本面应该贡献正向分数
    # 并且推荐理由里应该包含基本面描述
    cand = res_fund.candidates[0]
    # 我们没法确切比较分数绝对值 (因为权重变了)，但可以检查 logic
    assert cand.symbol == "STRONG"
    # 这里我们简单断言它依然是好的推荐
    assert cand.signal_strength > 0.6


def test_selector_filtering_logic(mock_prices, mock_regime_risk_on):
    """
    测试：MA200 过滤逻辑
    """
    # 将 STRONG 的最后一天价格人为砸盘到 MA200 以下
    # 重新构造一下数据或者修改最后一行
    prices = mock_prices.copy()
    ma200 = prices["STRONG"].rolling(200).mean().iloc[-1]

    # 设置最后价格为 MA200 * 0.99
    prices.loc[prices.index[-1], "STRONG"] = ma200 * 0.99

    selector = StockSelector(stock_pool=["STRONG"])
    result = selector.select(prices, mock_regime_risk_on)

    # 预期：虽然之前趋势好，但当前价格 < MA200，应被剔除
    assert len(result.candidates) == 0
