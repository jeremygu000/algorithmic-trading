"""
交易执行层 (Trade Execution Layer)
==================================

本模块将"配置系统"的输出（目标权重）转化为"可执行的交易计划"。

核心功能：
1. 计算建议买入点 (Entry Point) - 基于回调到均线
2. 计算止损点 (Stop-Loss) - 基于 ATR 波动率
3. 计算移动止损 (Trailing Stop) - 跟踪最高价

使用场景：
---------
>>> from etf_trend.execution.executor import TradeExecutor
>>> executor = TradeExecutor()
>>> plans = executor.generate_trade_plans(prices, allocation_result)
>>> for plan in plans:
...     print(plan)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from etf_trend.allocator.core import AllocationResult


# =============================================================================
# 数据类定义
# =============================================================================


@dataclass
class TradePlan:
    """
    单个标的的交易计划 (含多级价位)

    Attributes:
        symbol: 标的代码
        action: 交易方向 (BUY / HOLD / SELL)
        target_weight: 目标权重
        current_price: 当前价格
        
        # 多级入场点 (Entry Levels)
        entry_aggressive: 激进入场 (MA20)
        entry_moderate: 稳健入场 (回调 2%)
        entry_conservative: 保守入场 (回调 5%)
        
        # 多级止损点 (Stop Loss Levels)
        stop_tight: 紧止损 (ATR × 1.5)
        stop_normal: 标准止损 (ATR × 2.0)
        stop_loose: 宽止损 (ATR × 3.0)
        
        # 多级止盈点 (Take Profit Levels)
        tp1: 第一止盈目标 (ATR × 2)
        tp2: 第二止盈目标 (ATR × 4)
        tp3: 第三止盈目标 (ATR × 6)
        
        atr: 14日平均真实波幅
        trailing_stop_pct: 移动止损百分比
        reason: 交易理由
    """

    symbol: str
    action: Literal["BUY", "HOLD", "SELL"]
    target_weight: float
    current_price: float

    # 多级入场
    entry_aggressive: float | None
    entry_moderate: float | None
    entry_conservative: float | None

    # 多级止损
    stop_tight: float | None
    stop_normal: float | None
    stop_loose: float | None

    # 多级止盈
    tp1: float | None
    tp2: float | None
    tp3: float | None

    atr: float
    trailing_stop_pct: float | None
    reason: str

    # 向后兼容属性
    @property
    def entry_price(self) -> float | None:
        """兼容旧代码：返回稳健入场价"""
        return self.entry_moderate

    @property
    def stop_loss(self) -> float | None:
        """兼容旧代码：返回标准止损"""
        return self.stop_normal

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "action": self.action,
            "target_weight": self.target_weight,
            "current_price": self.current_price,
            "entry_levels": {
                "aggressive": self.entry_aggressive,
                "moderate": self.entry_moderate,
                "conservative": self.entry_conservative,
            },
            "stop_levels": {
                "tight": self.stop_tight,
                "normal": self.stop_normal,
                "loose": self.stop_loose,
            },
            "take_profit_levels": {
                "tp1": self.tp1,
                "tp2": self.tp2,
                "tp3": self.tp3,
            },
            "atr": self.atr,
            "trailing_stop_pct": self.trailing_stop_pct,
            "reason": self.reason,
        }


# =============================================================================
# ATR 计算
# =============================================================================


def calculate_atr(prices: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    计算平均真实波幅 (Average True Range)

    ATR 是衡量资产波动性的经典指标，用于设置止损距离。

    计算方法:
    TR = max(High - Low, |High - PrevClose|, |Low - PrevClose|)
    ATR = SMA(TR, window)

    由于我们只有收盘价，使用简化版本:
    TR ≈ |Close - PrevClose|
    ATR = SMA(TR, window)

    Args:
        prices: 价格 DataFrame
        window: ATR 计算窗口

    Returns:
        ATR DataFrame
    """
    # 计算日收益率的绝对值作为 TR 的代理
    returns = prices.pct_change().abs()
    # 计算 ATR
    atr = returns.rolling(window=window).mean() * prices
    return atr


# =============================================================================
# 核心执行器
# =============================================================================


class TradeExecutor:
    """
    交易执行器

    将配置系统的"目标权重"转化为具体的交易计划，
    包括入场点、止损点和移动止损设置。

    这是趋势跟踪系统的"最后一公里"。
    """

    def __init__(
        self,
        atr_window: int = 14,
        atr_multiplier: float = 2.0,
        entry_pullback_pct: float = 0.02,
        trailing_stop_atr: float = 2.5,
        ma_window: int = 20,
    ):
        """
        初始化执行器

        Args:
            atr_window: ATR 计算窗口 (默认 14 天)
            atr_multiplier: 止损距离 = ATR × 倍数 (默认 2.0)
            entry_pullback_pct: 回调入场百分比 (默认 2%)
            trailing_stop_atr: 移动止损使用的 ATR 倍数 (默认 2.5)
            ma_window: 入场均线窗口 (默认 20 天)
        """
        self.atr_window = atr_window
        self.atr_multiplier = atr_multiplier
        self.entry_pullback_pct = entry_pullback_pct
        self.trailing_stop_atr = trailing_stop_atr
        self.ma_window = ma_window

    def generate_trade_plans(
        self,
        prices: pd.DataFrame,
        allocation: AllocationResult,
        as_of_date: pd.Timestamp | None = None,
    ) -> list[TradePlan]:
        """
        生成交易计划

        Args:
            prices: 价格数据
            allocation: 配置结果 (来自 CoreAllocator)
            as_of_date: 计算日期

        Returns:
            交易计划列表
        """
        if as_of_date is None:
            as_of_date = prices.index[-1]

        # 计算 ATR
        atr_df = calculate_atr(prices, self.atr_window)
        # 计算短期均线
        ma_df = prices.rolling(self.ma_window).mean()

        plans = []

        for symbol, weight in allocation.weights.items():
            if symbol not in prices.columns:
                continue

            # ---------------------------------------------------------------------
            # 获取当前价格和指标
            # ---------------------------------------------------------------------
            current_price = prices.loc[as_of_date, symbol]
            atr = atr_df.loc[as_of_date, symbol] if symbol in atr_df.columns else np.nan
            ma = ma_df.loc[as_of_date, symbol] if symbol in ma_df.columns else np.nan

            if pd.isna(current_price) or pd.isna(atr):
                continue

            # ---------------------------------------------------------------------
            # 计算多级入场点 (Entry Levels)
            # ---------------------------------------------------------------------
            entry_aggressive = ma if not pd.isna(ma) else current_price * 0.99
            entry_moderate = current_price * (1 - self.entry_pullback_pct)  # 默认 2%
            entry_conservative = current_price * 0.95  # 5% 回调

            # ---------------------------------------------------------------------
            # 计算多级止损点 (Stop Loss Levels)
            # ---------------------------------------------------------------------
            stop_tight = entry_moderate - (atr * 1.5)
            stop_normal = entry_moderate - (atr * self.atr_multiplier)  # 默认 2.0
            stop_loose = entry_moderate - (atr * 3.0)

            # ---------------------------------------------------------------------
            # 计算多级止盈点 (Take Profit Levels)
            # ---------------------------------------------------------------------
            tp1 = entry_moderate + (atr * 2)
            tp2 = entry_moderate + (atr * 4)
            tp3 = entry_moderate + (atr * 6)

            # ---------------------------------------------------------------------
            # 计算移动止损百分比 (Trailing Stop)
            # ---------------------------------------------------------------------
            trailing_stop_pct = (atr * self.trailing_stop_atr) / current_price

            # ---------------------------------------------------------------------
            # 确定交易方向
            # ---------------------------------------------------------------------
            if weight > 0.01:
                action = "BUY"
                reason = f"目标持仓 {weight*100:.1f}%"
            else:
                action = "SELL"
                reason = "目标权重为 0，建议清仓"
                entry_aggressive = entry_moderate = entry_conservative = None
                stop_tight = stop_normal = stop_loose = None
                tp1 = tp2 = tp3 = None
                trailing_stop_pct = None

            plans.append(
                TradePlan(
                    symbol=symbol,
                    action=action,
                    target_weight=weight,
                    current_price=current_price,
                    entry_aggressive=entry_aggressive,
                    entry_moderate=entry_moderate,
                    entry_conservative=entry_conservative,
                    stop_tight=stop_tight,
                    stop_normal=stop_normal,
                    stop_loose=stop_loose,
                    tp1=tp1,
                    tp2=tp2,
                    tp3=tp3,
                    atr=atr,
                    trailing_stop_pct=trailing_stop_pct,
                    reason=reason,
                )
            )

        # 按权重排序
        plans.sort(key=lambda x: x.target_weight, reverse=True)
        return plans

    def format_trade_plans(self, plans: list[TradePlan]) -> str:
        """
        格式化交易计划为可读文本

        Args:
            plans: 交易计划列表

        Returns:
            格式化的文本
        """
        lines = []
        lines.append("=" * 60)
        lines.append("         📊 交易执行计划 (Trade Execution Plan)")
        lines.append("=" * 60)
        lines.append("")

        for plan in plans:
            if plan.action == "BUY":
                lines.append(f"[{plan.symbol}] 买入计划")
                lines.append(f"  📍 当前价格: ${plan.current_price:.2f}")
                lines.append(f"  🎯 目标权重: {plan.target_weight*100:.1f}%")
                lines.append(f"  📉 建议入场: ${plan.entry_price:.2f} (回调入场)")
                lines.append(f"  🛑 止损价格: ${plan.stop_loss:.2f} (ATR × {self.atr_multiplier})")
                lines.append(f"  📈 移动止损: {plan.trailing_stop_pct*100:.1f}% (跟踪最高价)")
                lines.append(f"  💡 {plan.reason}")
            else:
                lines.append(f"[{plan.symbol}] 卖出信号")
                lines.append(f"  📍 当前价格: ${plan.current_price:.2f}")
                lines.append(f"  💡 {plan.reason}")
            lines.append("")

        lines.append("-" * 60)
        lines.append("【风险提示】")
        lines.append("  - 止损价格基于 ATR 波动率计算，市场极端时可能失效")
        lines.append("  - 建议分批入场，不要一次性 All-in")
        lines.append("  - 个股风险远大于 ETF，注意仓位控制")
        lines.append("=" * 60)

        return "\n".join(lines)

    def generate_stock_plans(
        self,
        prices: pd.DataFrame,
        stock_candidates: list,
        as_of_date: pd.Timestamp | None = None,
    ) -> list[TradePlan]:
        """
        为推荐个股生成交易计划

        Args:
            prices: 价格数据 (需包含个股)
            stock_candidates: StockCandidate 列表 (来自 StockSelector)
            as_of_date: 计算日期

        Returns:
            交易计划列表
        """
        if as_of_date is None:
            as_of_date = prices.index[-1]

        # 计算 ATR
        atr_df = calculate_atr(prices, self.atr_window)
        # 计算短期均线
        ma_df = prices.rolling(self.ma_window).mean()

        plans = []

        for candidate in stock_candidates:
            symbol = candidate.symbol
            if symbol not in prices.columns:
                continue

            # ---------------------------------------------------------------------
            # 获取当前价格和指标
            # ---------------------------------------------------------------------
            current_price = prices.loc[as_of_date, symbol]
            atr = atr_df.loc[as_of_date, symbol] if symbol in atr_df.columns else np.nan
            ma = ma_df.loc[as_of_date, symbol] if symbol in ma_df.columns else np.nan

            if pd.isna(current_price) or pd.isna(atr):
                continue

            # ---------------------------------------------------------------------
            # 计算多级入场点 (Entry Levels) - 个股稍微保守
            # ---------------------------------------------------------------------
            entry_aggressive = ma if not pd.isna(ma) else current_price * 0.99
            entry_moderate = current_price * (1 - self.entry_pullback_pct)  # 2%
            entry_conservative = current_price * 0.93  # 7% 回调 (比 ETF 更保守)

            # ---------------------------------------------------------------------
            # 计算多级止损点 (Stop Loss Levels) - 个股使用更宽止损
            # ---------------------------------------------------------------------
            stop_tight = entry_moderate - (atr * 2.0)
            stop_normal = entry_moderate - (atr * 3.0)  # 个股标准 ATR×3
            stop_loose = entry_moderate - (atr * 4.0)

            # ---------------------------------------------------------------------
            # 计算多级止盈点 (Take Profit Levels)
            # ---------------------------------------------------------------------
            tp1 = entry_moderate + (atr * 3)
            tp2 = entry_moderate + (atr * 6)
            tp3 = entry_moderate + (atr * 10)  # 个股可以更激进

            # ---------------------------------------------------------------------
            # 计算移动止损百分比 (Trailing Stop)
            # ---------------------------------------------------------------------
            trailing_stop_pct = (atr * self.trailing_stop_atr) / current_price

            # 使用候选股的推荐等级生成理由
            reason = f"{candidate.recommendation} | {candidate.reason}"

            plans.append(
                TradePlan(
                    symbol=symbol,
                    action="BUY",
                    target_weight=0.0,  # 个股不计算权重，由用户自行决定仓位
                    current_price=current_price,
                    entry_aggressive=entry_aggressive,
                    entry_moderate=entry_moderate,
                    entry_conservative=entry_conservative,
                    stop_tight=stop_tight,
                    stop_normal=stop_normal,
                    stop_loose=stop_loose,
                    tp1=tp1,
                    tp2=tp2,
                    tp3=tp3,
                    atr=atr,
                    trailing_stop_pct=trailing_stop_pct,
                    reason=reason,
                )
            )

        return plans

