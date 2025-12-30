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

import pandas as pd

from etf_trend.regime.engine import RegimeState
from etf_trend.features.momentum import momentum_score, momentum_decay_signal
from etf_trend.features.volatility import realized_vol_annual
from etf_trend.features.pattern_match import PatternMatchResult
from etf_trend.features.trend_pred import TrendPrediction
from etf_trend.execution.executor import calculate_atr
from etf_trend.features.indicators import calculate_rsi
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
        
        # New Risk Management Fields
        exit_price: 建议止损价
        trailing_stop_pct: 建议移动止损比例
        hold_days: 建议持有天数 (估算)
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
    
    # Defaults for backward compatibility (though we'll populate them)
    exit_price: float = 0.0
    trailing_stop_pct: float = 0.0
    hold_days: int = 20


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
    卫星选股器 (Enhanced)

    在 RISK_ON 环境下，从股票池中筛选动量强、趋势向上的个股。
    使用多因子评分：
    - 动量 (30%): 多周期动量 + 衰减惩罚
    - 质量 (20%): 基本面 (ROE, Margin, Debt) + 估值 (PE/PEG)
    - 趋势 (20%): 均线距离
    - AI预测 (30%): DTW 形态匹配 + 线性回归趋势
    """

    # 行业 ETF 映射
    SECTOR_ETF_MAP = {
        "Technology": "XLK",
        "Healthcare": "XLV",
        "Financial": "XLF",
        "Consumer Cyclical": "XLY",
        "Consumer Defensive": "XLP",
        "Energy": "XLE",
        "Industrials": "XLI",
        "Utilities": "XLU",
        "Basic Materials": "XLB",
        "Real Estate": "XLRE",
        "Communication Services": "XLC"
    }

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
        ai_analysis: dict[str, dict] | None = None,  # 新增 AI 分析结果
    ) -> StockSelectionResult:
        """
        根据策略筛选股票

        Args:
            prices: 价格 DataFrame
            regime_state: 市场状态
            as_of_date: 筛选日期
            use_fundamental: 是否使用基本面
            fundamentals: 基本面数据
            ai_analysis: AI 分析结果 {symbol: {'pattern': PatternMatchResult, 'trend': TrendPrediction}}

        Returns:
            StockSelectionResult
        """
        if as_of_date is None:
            as_of_date = prices.index[-1]

        # ---------------------------------------------------------------------
        # 检查是否启用个股推荐
        # ---------------------------------------------------------------------
        # 仅在 RISK_ON 时推荐个股 (或回测强制启用)
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
        available_stocks = [s for s in self.stock_pool if s in prices.columns]

        if not available_stocks:
            return StockSelectionResult(
                candidates=[],
                regime=regime_state.regime,
                is_active=True,
                message="股票池中没有可用的股票数据",
            )

        stock_prices = prices[available_stocks]

        # 1. 计算动量
        mom = momentum_score(stock_prices, self.mom_windows, self.mom_weights)
        mom_latest = mom.loc[as_of_date] if as_of_date in mom.index else mom.iloc[-1]
        
        # 2. 计算动量衰减
        # momentum_decay_signal 返回的是一个 Series (index=symbols)，包含了每只股票当前的衰减状态
        # 它不是一个时间序列 DataFrame，所以不需要 .loc[as_of_date]
        # 注意：momentum_decay_signal 内部使用了 iloc[-1]，已经取了最新值
        decay_latest = momentum_decay_signal(stock_prices)

        # 3. 计算波动率
        returns = stock_prices.pct_change().dropna()
        vol = realized_vol_annual(returns, self.vol_lookback)
        vol_latest = vol.loc[as_of_date] if as_of_date in vol.index else vol.iloc[-1]

        # 4. 计算 MA200
        ma200 = stock_prices.rolling(self.ma_window).mean()
        ma200_latest = ma200.loc[as_of_date] if as_of_date in ma200.index else ma200.iloc[-1]
        price_latest = (
            stock_prices.loc[as_of_date]
            if as_of_date in stock_prices.index
            else stock_prices.iloc[-1]
        )
        
        # 5. 计算 RSI (使用 14 日窗口)
        # 对每只股票分别计算 RSI
        rsi_map = {}
        for sym in available_stocks:
            rsi_series = calculate_rsi(stock_prices[sym])
            rsi_map[sym] = rsi_series.loc[as_of_date] if as_of_date in rsi_series.index else rsi_series.iloc[-1]

        # 6. 计算行业动量 (Sector Momentum)
        # 需要 prices 中包含行业 ETF 的数据
        sector_mom_map = {}
        for sector, etf in self.SECTOR_ETF_MAP.items():
            if etf in prices.columns:
                etf_series = prices[etf]
                # 使用 20 日动量作为短期板块强弱指标
                if len(etf_series) > 20:
                    mom20 = etf_series.pct_change(20).iloc[-1]
                    sector_mom_map[sector] = mom20
                else:
                    sector_mom_map[sector] = 0.0

        # 7. 计算 ATR (用于止损)
        # 默认 14 天
        atr_df = calculate_atr(stock_prices, window=14)
        atr_latest = atr_df.loc[as_of_date] if as_of_date in atr_df.index else atr_df.iloc[-1]

        # ---------------------------------------------------------------------
        # 筛选候选股票
        # ---------------------------------------------------------------------
        candidates = []

        for symbol in available_stocks:
            # 获取指标值
            price = price_latest.get(symbol)
            mom_val = mom_latest.get(symbol)
            decay_val = decay_latest.get(symbol)
            vol_val = vol_latest.get(symbol)
            ma_val = ma200_latest.get(symbol)
            rsi_val = rsi_map.get(symbol, 50.0)
            atr_val = atr_latest.get(symbol)
            
            fund = fundamentals.get(symbol) if fundamentals else None
            ai_data = ai_analysis.get(symbol) if ai_analysis else None

            # 跳过数据不完整的股票
            if any(pd.isna([price, mom_val, vol_val, ma_val, atr_val])):
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
            
            # --- 1. 动量因子 (30%) ---
            # 基础动量 + 衰减惩罚
            score_mom = min(1.0, max(0.0, mom_val * 5))
            # 叠加衰减惩罚 (decay_val 是 0 到 -0.3 的负数)
            # 如果动量很强但刚开始衰减，分数会受到轻微打击
            # 如果动量一般且衰减，分数会大幅下降
            
            # --- 2. 价值/质量因子 (20%) ---
            score_quality = 0.5 # 默认中等
            stock_sector = None
            
            if use_fundamental and fund:
                # 估值 (PE/PEG)
                pe = fund.get("peRatio")
                peg = fund.get("pegRatio")
                stock_sector = fund.get("sector")
                score_val = 0.5
                
                if pe and pe > 0:
                    score_val = 1.0 if pe < 25 else (0.7 if pe < 40 else 0.2)
                if peg and peg > 0:
                    # PEG < 1 是强信号
                    if peg < 1.0: score_val += 0.3
                    elif peg > 2.5: score_val -= 0.2
                
                score_val = min(1.0, max(0.0, score_val))

                # 质量 (ROE, Margins, Debt) - 越高越好
                roe = fund.get("returnOnEquity") or 0.15
                margin = fund.get("grossMargins") or 0.3
                debt = fund.get("debtToEquity") or 1.0
                
                qs = 0.0
                if roe > 0.2: qs += 0.4
                elif roe > 0.1: qs += 0.2
                
                if margin > 0.4: qs += 0.3
                elif margin > 0.2: qs += 0.1
                
                if debt < 0.5: qs += 0.3
                elif debt < 1.5: qs += 0.1
                
                score_fund_qual = min(1.0, qs)

                # 结合估值、基本面质量和低波动特性
                vol_score = min(1.0, max(0.0, (0.4 - vol_val) / 0.2))
                
                # 综合质量分: 40%估值 + 40%基本面 + 20%低波
                score_quality = 0.4 * score_val + 0.4 * score_fund_qual + 0.2 * vol_score
            else:
                # 仅用波动率代理质量
                score_quality = min(1.0, max(0.0, (0.4 - vol_val) / 0.2))

            # --- 3. 趋势因子 (20%) ---
            dist_ma = (price / ma_val) - 1
            score_trend = min(1.0, max(0.0, dist_ma * 10))
            
            # --- 4. AI 因子 (30%) ---
            score_ai_pattern = 0.5
            score_ai_trend = 0.5
            
            if ai_data:
                pattern_res = ai_data.get("pattern")
                trend_res = ai_data.get("trend")
                
                if pattern_res:
                    # Win Rate > 0.6 开始加分
                    wr = pattern_res.get("win_rate", 0)
                    score_ai_pattern = min(1.0, max(0.0, (wr - 0.4) * 2.5))
                
                if trend_res:
                    # R2 > 0.5 且 slope > 0 加分
                    r2 = trend_res.get("r_squared", 0)
                    slope = trend_res.get("slope", 0)
                    if slope > 0:
                        score_ai_trend = 0.5 + 0.5 * min(1.0, r2)
                    else:
                        score_ai_trend = 0.5 - 0.5 * min(1.0, r2) # 趋势向下减分

            # --- 5. 附加因子 (RSI & Sector) ---
            addon_score = 0.0
            reasons = []

            # RSI Penalty/Bonus
            if rsi_val > 75:
                addon_score -= 0.15 
                reasons.append(f"RSI超买({rsi_val:.0f})")
            elif rsi_val < 30:
                addon_score -= 0.1 # 趋势策略不喜欢超卖
                reasons.append(f"RSI超卖({rsi_val:.0f})")
            elif 50 < rsi_val < 70:
                addon_score += 0.05
            
            # Sector Bonus
            if stock_sector:
                # 尝试匹配 sector name
                # Yahoo sector name 可能和 keys 不完全一致，需要模糊匹配
                # 简单处理：包含关键词
                sec_mom = 0.0
                for k, v in sector_mom_map.items():
                    if k in stock_sector: # e.g. "Technology" in "Technology"
                        sec_mom = v
                        break
                
                if sec_mom > 0.05: # 板块动量 > 5% (20日)
                    addon_score += 0.1
                    reasons.append("板块强势")
                elif sec_mom < -0.05:
                    addon_score -= 0.05
                    reasons.append("板块弱势")

            # --- 综合评分 ---
            signal_strength = (
                0.30 * score_mom +
                0.20 * score_quality +
                0.20 * score_trend +
                0.15 * score_ai_pattern +
                0.15 * score_ai_trend +
                decay_val +   # 动量衰减惩罚
                addon_score   # RSI & Sector 修正
            )
            
            # 确保在 0-1 之间
            signal_strength = min(1.0, max(0.0, signal_strength))

            # 推荐等级和原因
            if signal_strength >= 0.75:
                recommendation = "强烈推荐"
            elif signal_strength >= 0.55:
                recommendation = "推荐"
            else:
                recommendation = "观望"

            # 生成推荐原因
            if score_mom > 0.7: reasons.append("强劲动量")
            if decay_val < -0.1: reasons.append("动量衰减警示")
            
            if score_quality > 0.7: reasons.append("高质量/低估值")
            
            if score_ai_pattern > 0.7: reasons.append("AI形态看涨")
            elif score_ai_pattern < 0.3: reasons.append("AI形态看跌")
            
            if score_ai_trend > 0.7: reasons.append("AI趋势强")

            reason = "，".join(reasons)
            name = self.STOCK_NAMES.get(symbol, symbol)
            
            # --- 计算风险指标 ---
            # 初始止损: 当前价格 - 2.5 * ATR
            exit_price = round(price - 2.5 * float(atr_val), 2)
            # 移动止损比例: 2.5 * ATR / Price
            trailing_stop_pct = round((2.5 * float(atr_val) / price), 3)
            # 建议持有天数: 基于趋势强度估算 (动量越强，持有越久，但最少5天，最多60天)
            hold_days = int(min(60, max(5, 20 + mom_val * 100)))

            candidates.append(
                StockCandidate(
                    symbol=symbol,
                    name=name,
                    price=round(float(price), 2),
                    momentum_score=round(float(mom_val) * 100, 2),
                    volatility=round(float(vol_val) * 100, 2),
                    above_ma200=above_ma,
                    signal_strength=round(signal_strength, 2),
                    recommendation=recommendation,
                    reason=reason,
                    exit_price=exit_price,
                    trailing_stop_pct=trailing_stop_pct,
                    hold_days=hold_days,
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
