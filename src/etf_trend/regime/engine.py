"""
市场状态机 (Regime Engine)
========================

本模块用于判断当前市场处于什么状态，输出风险预算指导仓位管理。

核心概念：
---------
- RISK_ON (风险偏好): 市场趋势向上，适合高仓位持有股票 ETF
- NEUTRAL (中性): 市场方向不明，建议降低仓位或分散配置
- RISK_OFF (风险厌恶): 市场趋势向下或恐慌，应减少股票、增加防守资产

判断依据：
---------
1. 长期趋势: SPY 是否在 200 日均线之上 (权重 40%)
2. 恐慌指数: VIX 是否低于 20 (权重 30%)
3. 中期动量: 60 日收益率是否为正 (权重 30%)

使用示例：
---------
>>> from etf_trend.regime.engine import RegimeEngine
>>> engine = RegimeEngine()
>>> state = engine.detect(prices)
>>> print(state.regime)  # "RISK_ON" / "NEUTRAL" / "RISK_OFF"
>>> print(state.risk_budget)  # 0.85 (表示可以使用 85% 仓位)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


# =============================================================================
# 数据类定义
# =============================================================================


@dataclass
class RegimeState:
    """
    市场状态结果类

    Attributes:
        regime: 市场状态，取值为 "RISK_ON" / "NEUTRAL" / "RISK_OFF"
        risk_budget: 风险预算，0.0 到 1.0 之间的浮点数
                     例如 0.8 表示建议使用 80% 的仓位
        signals: 各个信号的具体值，用于调试和展示
    """

    regime: Literal["RISK_ON", "NEUTRAL", "RISK_OFF"]
    risk_budget: float
    signals: dict


# =============================================================================
# 市场状态机
# =============================================================================


class RegimeEngine:
    """
    市场状态机

    通过多个技术指标综合判断当前市场处于什么状态，
    并输出一个连续的风险预算值，用于指导仓位管理。

    为什么不用 0/1 二元判断？
    ----------------------
    传统策略往往是"满仓或空仓"，这会导致：
    - 频繁交易，增加成本
    - 在震荡市中反复被打脸
    - 错过大部分上涨行情

    连续风险预算的好处：
    - 仓位随信号强度渐变，更平滑
    - 即使判断错误，也不会完全错过行情
    - 更符合机构的实际操作方式
    """

    def __init__(
        self,
        ma_window: int = 200,
        momentum_window: int = 60,
        vix_threshold: float = 20.0,
        weight_trend: float = 0.4,
        weight_vix: float = 0.3,
        weight_momentum: float = 0.3,
    ):
        """
        初始化市场状态机

        Args:
            ma_window: 长期均线窗口，默认 200 日
            momentum_window: 动量计算窗口，默认 60 日
            vix_threshold: VIX 恐慌阈值，低于此值认为市场平静
            weight_trend: 趋势信号权重
            weight_vix: VIX 信号权重
            weight_momentum: 动量信号权重
        """
        self.ma_window = ma_window
        self.momentum_window = momentum_window
        self.vix_threshold = vix_threshold

        # 权重必须加起来等于 1
        total = weight_trend + weight_vix + weight_momentum
        self.weight_trend = weight_trend / total
        self.weight_vix = weight_vix / total
        self.weight_momentum = weight_momentum / total

    def detect(
        self,
        prices: pd.DataFrame,
        vix: pd.Series | None = None,
        market_symbol: str = "SPY",
    ) -> RegimeState:
        """
        检测当前市场状态

        Args:
            prices: 价格 DataFrame，index 为日期，columns 为资产代码
            vix: VIX 指数 Series（可选），如果不提供则只用趋势和动量
            market_symbol: 用于判断市场状态的基准资产，默认 SPY

        Returns:
            RegimeState: 包含 regime、risk_budget 和 signals

        Example:
            >>> state = engine.detect(prices, vix=vix_series)
            >>> if state.regime == "RISK_ON":
            >>>     # 可以高仓位持有股票
            >>>     pass
        """
        if market_symbol not in prices.columns:
            raise ValueError(f"市场基准 {market_symbol} 不在价格数据中")

        market_prices = prices[market_symbol]

        # ---------------------------------------------------------------------
        # 信号 1: 长期趋势 (SPY > MA200)
        # ---------------------------------------------------------------------
        # 原理：如果价格在长期均线之上，说明长期趋势向上
        # 这是最经典的趋势跟踪指标，避免在熊市中被套
        ma = market_prices.rolling(self.ma_window).mean()
        trend_signal = 1.0 if market_prices.iloc[-1] > ma.iloc[-1] else 0.0

        # ---------------------------------------------------------------------
        # 信号 2: VIX 恐慌指数
        # ---------------------------------------------------------------------
        # 原理：VIX 高表示市场恐慌，应该减少风险敞口
        # VIX < 15: 非常平静（贪婪）
        # VIX 15-20: 正常
        # VIX 20-30: 担忧
        # VIX > 30: 恐慌
        if vix is not None and len(vix) > 0:
            current_vix = vix.iloc[-1]
            # 将 VIX 转换为 0-1 的信号
            # VIX=10 → 1.0, VIX=20 → 0.5, VIX=30 → 0.0
            vix_signal = max(0.0, min(1.0, (30 - current_vix) / 20))
        else:
            # 没有 VIX 数据时，假设正常状态
            current_vix = None
            vix_signal = 0.5

        # ---------------------------------------------------------------------
        # 信号 3: 中期动量
        # ---------------------------------------------------------------------
        # 原理：如果过去 60 天是上涨的，说明中期动量为正
        # 动量效应是量化投资最稳定的因子之一
        momentum = market_prices.pct_change(self.momentum_window).iloc[-1]
        # 将动量转换为 0-1 的信号
        # -10% → 0.0, 0% → 0.5, +10% → 1.0
        momentum_signal = max(0.0, min(1.0, (momentum + 0.1) / 0.2))

        # ---------------------------------------------------------------------
        # 综合评分
        # ---------------------------------------------------------------------
        # 加权平均得到总分
        weighted_score = (
            self.weight_trend * trend_signal
            + self.weight_vix * vix_signal
            + self.weight_momentum * momentum_signal
        )

        # 风险预算：将评分映射到合理范围
        # 最低 20%（即使全部信号为负，也保留一点仓位）
        # 最高 100%
        risk_budget = 0.2 + 0.8 * weighted_score

        # 确定 Regime 状态
        if weighted_score >= 0.6:
            regime = "RISK_ON"
        elif weighted_score >= 0.4:
            regime = "NEUTRAL"
        else:
            regime = "RISK_OFF"

        # 构建信号详情
        signals = {
            "market_symbol": market_symbol,
            "price": float(market_prices.iloc[-1]),
            "ma200": float(ma.iloc[-1]) if pd.notna(ma.iloc[-1]) else None,
            "trend_above_ma": trend_signal == 1.0,
            "vix": float(current_vix) if current_vix is not None else None,
            "vix_signal": round(vix_signal, 2),
            "momentum_60d": round(momentum * 100, 2) if pd.notna(momentum) else None,
            "momentum_signal": round(momentum_signal, 2),
            "weighted_score": round(weighted_score, 2),
        }

        return RegimeState(regime=regime, risk_budget=round(risk_budget, 2), signals=signals)

    def get_regime_description(self, state: RegimeState) -> str:
        """
        获取 Regime 的中文描述

        Args:
            state: RegimeState 对象

        Returns:
            中文描述字符串
        """
        descriptions = {
            "RISK_ON": "【风险偏好】市场趋势向上，建议高仓位持有股票 ETF",
            "NEUTRAL": "【中性观望】市场方向不明，建议降低仓位或分散配置",
            "RISK_OFF": "【风险厌恶】市场趋势向下或恐慌，应减少股票、增加防守资产",
        }
        return descriptions.get(state.regime, "未知状态")
