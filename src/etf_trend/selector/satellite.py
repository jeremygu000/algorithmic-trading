"""
卫星选股器 (Satellite Stock Selector)
=====================================

本模块提供个股推荐功能，作为 ETF 核心配置的"卫星"补充。

设计原则：
---------
1. 仅在 RISK_ON 时启用 - 风险厌恶期不推荐个股
2. 输出候选清单，不直接给权重 - 降低风险
3. 严格的筛选标准 - 流动性、波动率、动量

使用方式：
---------
>>> from etf_trend.selector.satellite import StockSelector
>>> selector = StockSelector()
>>> watchlist = selector.select(prices, regime_state)
>>> print(watchlist)  # [("AAPL", {...}), ("MSFT", {...}), ...]

注意事项：
---------
- 个股波动远大于 ETF，需谨慎使用
- 本模块仅供参考，不构成投资建议
- 实盘前务必进行更详尽的研究
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from etf_trend.regime.engine import RegimeState
from etf_trend.features.momentum import momentum_score
from etf_trend.features.volatility import realized_vol_annual
from etf_trend.data.providers.yahoo_fundamentals import FundamentalData


# =============================================================================
# 数据类定义
# =============================================================================


@dataclass
class StockCandidate:
    """
    个股候选

    Attributes:
        symbol: 股票代码
        name: 股票名称
        price: 当前价格
        momentum_score: 动量得分
        volatility: 年化波动率
        above_ma200: 是否在 200 日均线之上
        signal_strength: 综合信号强度 (0~1)
        recommendation: 推荐等级
        reason: 推荐原因
    """

    symbol: str
    name: str
    price: float
    momentum_score: float
    volatility: float
    above_ma200: bool
    signal_strength: float
    recommendation: Literal["强烈推荐", "推荐", "观望"]
    reason: str


@dataclass
class StockSelectionResult:
    """
    选股结果

    Attributes:
        candidates: 候选股票列表（按信号强度排序）
        regime: 当前市场状态
        is_active: 是否启用个股推荐
        message: 状态说明
    """

    candidates: list[StockCandidate]
    regime: str
    is_active: bool
    message: str


# =============================================================================
# 卫星选股器
# =============================================================================


class StockSelector:
    """
    卫星选股器

    在 RISK_ON 环境下，从股票池中筛选动量强、趋势向上的个股。
    作为 ETF 核心配置的补充，用于追求超额收益。

    筛选标准：
    ---------
    1. 趋势过滤：价格 > MA200
    2. 动量排序：多周期动量加权
    3. 波动率上限：排除过于波动的"妖股"
    4. 综合评分：生成信号强度
    """

    # 默认的美股核心股票池（科技+消费+金融）
    DEFAULT_STOCK_POOL = [
        # 科技巨头
        "AAPL",  # Apple
        "MSFT",  # Microsoft
        "GOOGL",  # Google
        "AMZN",  # Amazon
        "META",  # Meta (Facebook)
        "NVDA",  # NVIDIA
        "TSLA",  # Tesla
        # 消费
        "WMT",  # Walmart
        "HD",  # Home Depot
        "MCD",  # McDonald's
        "COST",  # Costco
        "NKE",  # Nike
        # 金融
        "JPM",  # JPMorgan
        "V",  # Visa
        "MA",  # Mastercard
        # 医疗
        "JNJ",  # Johnson & Johnson
        "UNH",  # UnitedHealth
        "PFE",  # Pfizer
    ]

    # 股票代码 -> 名称映射
    STOCK_NAMES = {
        # 科技
        "AAPL": "苹果 Apple",
        "MSFT": "微软 Microsoft",
        "GOOGL": "谷歌 Google",
        "AMZN": "亚马逊 Amazon",
        "META": "Meta (Facebook)",
        "NVDA": "英伟达 NVIDIA",
        "TSLA": "特斯拉 Tesla",
        # 消费
        "WMT": "沃尔玛 Walmart",
        "HD": "家得宝 Home Depot",
        "MCD": "麦当劳 McDonald's",
        "COST": "好市多 Costco",
        "NKE": "耐克 Nike",
        # 金融
        "JPM": "摩根大通 JPMorgan",
        "V": "Visa 维萨",
        "MA": "万事达 Mastercard",
        # 医疗
        "JNJ": "强生 Johnson & Johnson",
        "UNH": "联合健康 UnitedHealth",
        "PFE": "辉瑞 Pfizer",
    }

    def __init__(
        self,
        stock_pool: list[str] | None = None,
        ma_window: int = 200,
        mom_windows: list[int] | None = None,
        mom_weights: list[float] | None = None,
        vol_lookback: int = 60,
        max_volatility: float = 0.60,  # 年化波动率上限 60%
        top_n: int = 10,
    ):
        """
        初始化选股器

        Args:
            stock_pool: 股票池，默认使用内置的核心股票
            ma_window: 均线窗口
            mom_windows: 动量计算窗口
            mom_weights: 动量各周期权重
            vol_lookback: 波动率回溯期
            max_volatility: 最大允许年化波动率
            top_n: 返回 Top-N 只股票
        """
        self.stock_pool = stock_pool or self.DEFAULT_STOCK_POOL
        self.ma_window = ma_window
        self.mom_windows = mom_windows or [20, 60, 120]
        self.mom_weights = mom_weights or [0.33, 0.34, 0.33]
        self.vol_lookback = vol_lookback
        self.max_volatility = max_volatility
        self.top_n = top_n

    def select(
        self,
        prices: pd.DataFrame,
        regime_state: RegimeState,
        as_of_date: pd.Timestamp | None = None,
        use_fundamental: bool = False,
        fundamentals: dict[str, FundamentalData] | None = None,
    ) -> StockSelectionResult:
        """
        根据策略筛选股票

        Args:
            prices: 价格 DataFrame（需包含股票池中的股票）
            regime_state: 市场状态
            as_of_date: 筛选日期（默认最新）
            use_fundamental: 是否使用基本面数据（默认为 False 以避免 Look-ahead Bias）

        Returns:
            StockSelectionResult: 包含候选股票和状态信息
        """
        if as_of_date is None:
            as_of_date = prices.index[-1]

        # ---------------------------------------------------------------------
        # 检查是否启用个股推荐
        # ---------------------------------------------------------------------
        # 仅在 RISK_ON 时推荐个股，其他状态输出空列表
        if regime_state.regime != "RISK_ON":
            return StockSelectionResult(
                candidates=[],
                regime=regime_state.regime,
                is_active=False,
                message=f"当前市场状态为【{regime_state.regime}】，不建议配置个股。请关注 ETF 核心持仓。",
            )

        # ---------------------------------------------------------------------
        # 计算指标
        # ---------------------------------------------------------------------
        # 筛选股票池中存在的股票
        available_stocks = [s for s in self.stock_pool if s in prices.columns]

        if not available_stocks:
            return StockSelectionResult(
                candidates=[],
                regime=regime_state.regime,
                is_active=True,
                message="股票池中没有可用的股票数据",
            )

        stock_prices = prices[available_stocks]

        # 计算动量
        mom = momentum_score(stock_prices, self.mom_windows, self.mom_weights)
        mom_latest = mom.loc[as_of_date] if as_of_date in mom.index else mom.iloc[-1]

        # 计算波动率（需要先转换为收益率）
        returns = stock_prices.pct_change().dropna()
        vol = realized_vol_annual(returns, self.vol_lookback)
        vol_latest = vol.loc[as_of_date] if as_of_date in vol.index else vol.iloc[-1]

        # 计算 MA200
        ma200 = stock_prices.rolling(self.ma_window).mean()
        ma200_latest = ma200.loc[as_of_date] if as_of_date in ma200.index else ma200.iloc[-1]
        price_latest = (
            stock_prices.loc[as_of_date]
            if as_of_date in stock_prices.index
            else stock_prices.iloc[-1]
        )

        # ---------------------------------------------------------------------
        # 筛选候选股票
        # ---------------------------------------------------------------------
        candidates = []

        for symbol in available_stocks:
            # 获取指标值
            price = price_latest.get(symbol)
            mom_val = mom_latest.get(symbol)
            vol_val = vol_latest.get(symbol)
            ma_val = ma200_latest.get(symbol)
            fund = fundamentals.get(symbol) if fundamentals else None

            # 跳过数据不完整的股票
            if any(pd.isna([price, mom_val, vol_val, ma_val])):
                continue

            # 过滤条件
            above_ma = price > ma_val
            low_vol = vol_val <= self.max_volatility
            positive_mom = mom_val > 0

            # 必须同时满足：在均线之上、波动率可接受、动量为正
            if not (above_ma and low_vol and positive_mom):
                continue

            # ---------------------------------------------------------------------
            # 计算综合多因子得分
            # ---------------------------------------------------------------------
            # 1. 动量因子 (40%)
            score_mom = min(1.0, max(0.0, mom_val * 5))
            
            # 2. 价值因子 (30%) 
            if use_fundamental and fund:
                # 使用真实基本面数据
                pe = fund.get("peRatio")
                peg = fund.get("pegRatio")
                
                # 估值打分 (0-1)
                score_val = 0.5
                if pe and pe > 0:
                   if pe < 20: score_val = 1.0
                   elif pe < 30: score_val = 0.7
                   elif pe > 50: score_val = 0.2
                   
                if peg and peg > 0:
                   if peg < 1.0: score_val = (score_val + 1.0) / 2
                   elif peg > 2.0: score_val = (score_val + 0.2) / 2
                   
                # 用波动率辅助质量
                score_vol = min(1.0, max(0.0, (0.4 - vol_val) / 0.2))
                
                score_quality = 0.6 * score_val + 0.4 * score_vol
            else:
                score_quality = min(1.0, max(0.0, (0.4 - vol_val) / 0.2)) # 仅用波动率代理

            # 3. 趋势因子 (30%)
            dist_ma = (price / ma_val) - 1
            score_trend = min(1.0, max(0.0, dist_ma * 10))
            
            # 综合评分
            if use_fundamental:
                signal_strength = 0.4 * score_mom + 0.3 * score_quality + 0.3 * score_trend
            else:
                # 回测模式：仅使用动量和趋势
                signal_strength = 0.6 * score_mom + 0.4 * score_trend

            # 推荐等级和原因
            if signal_strength >= 0.7:
                recommendation = "强烈推荐"
            elif signal_strength >= 0.5:
                recommendation = "推荐"
            else:
                recommendation = "观望"

            # 生成推荐原因
            reasons = []
            if score_mom > 0.7:
                reasons.append(f"强劲动量 ({mom_val*100:.1f}%)")
            elif score_mom > 0.4:
                reasons.append(f"良好动量")
                
            if score_quality > 0.7:
                reasons.append("低波动高质量")
            elif score_quality > 0.4:
                reasons.append("稳健波动")
                
            if score_trend > 0.5:
                reasons.append("趋势强劲")

            reason = "，".join(reasons)

            # 获取股票名称
            name = self.STOCK_NAMES.get(symbol, symbol)

            candidates.append(
                StockCandidate(
                    symbol=symbol,
                    name=name,
                    price=round(float(price), 2),
                    momentum_score=round(float(mom_val) * 100, 2),  # 转为百分比
                    volatility=round(float(vol_val) * 100, 2),  # 转为百分比
                    above_ma200=above_ma,
                    signal_strength=round(signal_strength, 2),
                    recommendation=recommendation,
                    reason=reason,
                )
            )

        # 按信号强度排序，取 Top-N
        candidates.sort(key=lambda x: x.signal_strength, reverse=True)
        candidates = candidates[: self.top_n]

        return StockSelectionResult(
            candidates=candidates,
            regime=regime_state.regime,
            is_active=True,
            message=f"在 RISK_ON 环境下，推荐以下 {len(candidates)} 只股票作为卫星持仓候选",
        )

    def get_recommendation_text(self, result: StockSelectionResult) -> str:
        """
        生成推荐文本

        Args:
            result: 选股结果

        Returns:
            格式化的推荐文本
        """
        lines = []
        lines.append("\n" + "=" * 55)
        lines.append("           个股候选清单 (卫星持仓)")
        lines.append("=" * 55)

        if not result.is_active:
            lines.append(f"\n{result.message}")
            lines.append("\n" + "=" * 55)
            return "\n".join(lines)

        lines.append(f"\n{result.message}")
        lines.append("")

        if not result.candidates:
            lines.append("  暂无符合条件的股票")
        else:
            for i, c in enumerate(result.candidates, 1):
                lines.append(f"\n  [{i}] {c.symbol} - {c.name}")
                lines.append(f"      价格: ${c.price:.2f}  |  {c.recommendation}")
                lines.append(f"      原因: {c.reason}")

        lines.append("")
        lines.append("【风险提示】")
        lines.append("  - 个股波动远大于 ETF，建议仓位控制在 20% 以内")
        lines.append("  - 本清单仅供参考，不构成投资建议")
        lines.append("  - 实盘前请进行更详尽的基本面研究")
        lines.append("\n" + "=" * 55)

        return "\n".join(lines)
