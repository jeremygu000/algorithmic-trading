"""
核心资产配置器 (Core Allocator)
==============================

本模块根据市场状态（Regime）和动量信号，选择 Top-N 个 ETF 并分配权重。

核心逻辑：
---------
1. 根据 Regime 确定股票/防守资产的大类比例
2. 在每个大类中，按动量排序选择 Top-N
3. 使用反向波动率加权分配权重
4. 应用单一资产和总权重上限约束

使用示例：
---------
>>> from etf_trend.allocator.core import CoreAllocator
>>> allocator = CoreAllocator(config)
>>> weights = allocator.allocate(prices, regime_state)
>>> print(weights)  # {"SPY": 0.25, "QQQ": 0.20, "TLT": 0.15, ...}
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from etf_trend.regime.engine import RegimeState
from etf_trend.features.momentum import momentum_score
from etf_trend.features.volatility import realized_vol_annual


# =============================================================================
# 数据类定义
# =============================================================================


@dataclass
class AllocationResult:
    """
    配置结果

    Attributes:
        weights: 各 ETF 的权重字典
        equity_weights: 股票类 ETF 权重
        defensive_weights: 防守类 ETF 权重
        regime: 当前市场状态
        risk_budget: 风险预算
        metadata: 其他元数据（用于调试）
    """

    weights: dict[str, float]
    equity_weights: dict[str, float]
    defensive_weights: dict[str, float]
    regime: str
    risk_budget: float
    metadata: dict


# =============================================================================
# 核心配置器
# =============================================================================


class CoreAllocator:
    """
    核心资产配置器

    根据市场状态动态调整股票和防守资产的配置比例，
    并在每个大类中选择动量最强的 Top-N 资产。

    这是一个"核心-卫星"策略的核心部分，
    目标是在不同市场环境下获得稳健的风险调整后收益。
    """

    def __init__(
        self,
        equity_symbols: list[str],
        defensive_symbols: list[str],
        core_symbols: list[str] | None = None,
        regime_allocation: dict | None = None,
        top_n_equity: int = 5,
        top_n_defensive: int = 2,
        vol_lookback: int = 60,
        max_weight_single: float = 0.30,
        max_weight_core: float = 0.50,
        mom_windows: list[int] | None = None,
        mom_weights: list[float] | None = None,
        optimizer_method: str = "inverse_vol",
    ):
        """
        初始化配置器

        Args:
            equity_symbols: 股票类 ETF 列表
            defensive_symbols: 防守类 ETF 列表
            core_symbols: 核心持仓 ETF（有权重上限）
            regime_allocation: 不同 Regime 下的大类配置比例
            top_n_equity: 股票类选 Top-N 个
            top_n_defensive: 防守类选 Top-N 个
            vol_lookback: 波动率计算回溯期
            max_weight_single: 单一资产权重上限
            max_weight_core: 核心资产组合权重上限
            mom_windows: 动量计算窗口
            mom_weights: 动量各窗口权重
            optimizer_method: 优化方法 (inverse_vol, min_variance, risk_parity)
        """
        self.equity_symbols = equity_symbols
        self.defensive_symbols = defensive_symbols
        self.core_symbols = core_symbols or []
        self.top_n_equity = top_n_equity
        self.top_n_defensive = top_n_defensive
        self.vol_lookback = vol_lookback
        self.max_weight_single = max_weight_single
        self.max_weight_core = max_weight_core
        self.mom_windows = mom_windows or [20, 60, 120]
        self.mom_weights = mom_weights or [0.33, 0.34, 0.33]
        self.optimizer_method = optimizer_method

        # 默认的 Regime 配置比例
        self.regime_allocation = regime_allocation or {
            "RISK_ON": {"equity": 0.80, "defensive": 0.20},
            "NEUTRAL": {"equity": 0.50, "defensive": 0.50},
            "RISK_OFF": {"equity": 0.20, "defensive": 0.80},
        }

    def allocate(
        self,
        prices: pd.DataFrame,
        regime_state: RegimeState,
        as_of_date: pd.Timestamp | None = None,
    ) -> AllocationResult:
        """
        执行资产配置

        Args:
            prices: 价格 DataFrame
            regime_state: 市场状态
            as_of_date: 配置日期（默认使用最新日期）

        Returns:
            AllocationResult: 包含权重和元数据
        """
        if as_of_date is None:
            as_of_date = prices.index[-1]

        # ---------------------------------------------------------------------
        # Step 1: 获取大类配置比例
        # ---------------------------------------------------------------------
        alloc = self.regime_allocation.get(regime_state.regime, {"equity": 0.5, "defensive": 0.5})
        equity_budget = alloc["equity"]
        defensive_budget = alloc["defensive"]

        # ---------------------------------------------------------------------
        # Step 2: 计算动量和波动率
        # ---------------------------------------------------------------------
        # 动量：用于排序选择 Top-N
        mom = momentum_score(prices, self.mom_windows, self.mom_weights)
        mom_latest = mom.loc[as_of_date] if as_of_date in mom.index else mom.iloc[-1]

        # 波动率：用于反向加权
        vol = realized_vol_annual(prices, self.vol_lookback)
        vol_latest = vol.loc[as_of_date] if as_of_date in vol.index else vol.iloc[-1]

        # ---------------------------------------------------------------------
        # Step 3: 选择 Top-N 股票类 ETF
        # ---------------------------------------------------------------------
        equity_weights = self._select_top_n(
            symbols=self.equity_symbols,
            momentum=mom_latest,
            volatility=vol_latest,
            budget=equity_budget,
            top_n=self.top_n_equity,
            prices=prices,
        )

        # ---------------------------------------------------------------------
        # Step 4: 选择 Top-N 防守类 ETF
        # ---------------------------------------------------------------------
        defensive_weights = self._select_top_n(
            symbols=self.defensive_symbols,
            momentum=mom_latest,
            volatility=vol_latest,
            budget=defensive_budget,
            top_n=self.top_n_defensive,
            prices=prices,
        )

        # ---------------------------------------------------------------------
        # Step 5: 合并并应用约束
        # ---------------------------------------------------------------------
        all_weights = {**equity_weights, **defensive_weights}
        all_weights = self._apply_constraints(all_weights)

        # 构建元数据
        metadata = {
            "as_of_date": str(as_of_date.date()),
            "equity_budget": equity_budget,
            "defensive_budget": defensive_budget,
            "equity_count": len(equity_weights),
            "defensive_count": len(defensive_weights),
            "total_weight": sum(all_weights.values()),
        }

        return AllocationResult(
            weights=all_weights,
            equity_weights=equity_weights,
            defensive_weights=defensive_weights,
            regime=regime_state.regime,
            risk_budget=regime_state.risk_budget,
            metadata=metadata,
        )

    def _select_top_n(
        self,
        symbols: list[str],
        momentum: pd.Series,
        volatility: pd.Series,
        budget: float,
        top_n: int,
        prices: pd.DataFrame | None = None,
    ) -> dict[str, float]:
        """
        选择 Top-N 资产并分配权重

        选择逻辑：
        1. 筛选出有效的资产（有动量和波动率数据）
        2. 按动量排序，选择前 N 个
        3. 使用反向波动率加权
        4. 调整使总权重等于 budget
        """
        # 筛选有效资产
        valid_symbols = [
            s
            for s in symbols
            if s in momentum.index
            and s in volatility.index
            and pd.notna(momentum[s])
            and pd.notna(volatility[s])
            and volatility[s] > 0
        ]

        if not valid_symbols:
            return {}

        # 按动量排序，选择 Top-N
        mom_subset = momentum[valid_symbols].sort_values(ascending=False)
        top_symbols = mom_subset.head(top_n).index.tolist()

        if not top_symbols:
            return {}

        if not top_symbols:
            return {}

        # ---------------------------------------------------------------------
        # 使用优化引擎分配权重
        # ---------------------------------------------------------------------
        if self.optimizer_method == "inverse_vol":
            # 传统方法：反向波动率加权
            vol_subset = volatility[top_symbols]
            inv_vol = 1.0 / vol_subset
            weights = inv_vol / inv_vol.sum()
            weights = weights.to_dict()
        else:
            # 机构级方法：最小方差 / 风险平价
            # 需要历史收益率数据来计算协方差矩阵
            # 注意：这里的 prices 是全量数据，我们需要切片
            if prices is not None:
                # 获取相关资产的收益率数据
                returns = prices[top_symbols].pct_change().dropna()
                # 截取最近的窗口
                returns = returns.tail(252)

                if len(returns) > 60: # 确保有足够数据
                    from etf_trend.allocator.optimizer import PortfolioOptimizer
                    opt = PortfolioOptimizer(returns)
                    weights_series = opt.optimize(self.optimizer_method)
                    weights = weights_series.to_dict()
                else:
                    # 数据不足回退到等权
                    weights = {s: 1.0 / len(top_symbols) for s in top_symbols}
            else:
                # 无法获取价格数据，回退到等权
                weights = {s: 1.0 / len(top_symbols) for s in top_symbols}

        # 调整使总权重等于 budget
        final_weights = {}
        for s, w in weights.items():
            final_weights[s] = w * budget

        return final_weights

    def _apply_constraints(self, weights: dict[str, float]) -> dict[str, float]:
        """
        应用权重约束

        1. 单一资产上限
        2. 核心资产组合上限
        3. 重新归一化
        """
        if not weights:
            return {}

        # 转换为 Series 便于操作
        w = pd.Series(weights)

        # 约束 1: 单一资产上限
        w = w.clip(upper=self.max_weight_single)

        # 约束 2: 核心资产组合上限
        core_weight = w[w.index.isin(self.core_symbols)].sum()
        if core_weight > self.max_weight_core:
            # 按比例缩减核心资产
            scale = self.max_weight_core / core_weight
            for s in self.core_symbols:
                if s in w.index:
                    w[s] = w[s] * scale

        # 重新归一化使总权重不超过 1
        total = w.sum()
        if total > 1.0:
            w = w / total

        # 过滤掉权重过小的资产（< 1%）
        w = w[w >= 0.01]

        return w.to_dict()

    def get_recommendation_text(self, result: AllocationResult) -> str:
        """
        生成推荐文本

        Args:
            result: 配置结果

        Returns:
            格式化的推荐文本
        """
        lines = []
        lines.append(f"\n{'=' * 50}")
        lines.append(f"  ETF 推荐配置 ({result.metadata['as_of_date']})")
        lines.append(f"{'=' * 50}")

        # 状态信息
        regime_icons = {
            "RISK_ON": "🟢 风险偏好",
            "NEUTRAL": "🟡 中性观望",
            "RISK_OFF": "🔴 风险厌恶",
        }
        lines.append(f"\n市场状态: {regime_icons.get(result.regime, result.regime)}")
        lines.append(f"风险预算: {result.risk_budget * 100:.0f}%")

        # 股票类推荐
        lines.append(f"\n{'-' * 40}")
        lines.append("  股票类 ETF (Top-N)")
        lines.append(f"{'-' * 40}")
        for symbol, weight in sorted(result.equity_weights.items(), key=lambda x: -x[1]):
            pct = weight * 100
            lines.append(f"  {symbol:6} {pct:5.1f}%")

        # 防守类推荐
        lines.append(f"\n{'-' * 40}")
        lines.append("  防守类 ETF")
        lines.append(f"{'-' * 40}")
        for symbol, weight in sorted(result.defensive_weights.items(), key=lambda x: -x[1]):
            pct = weight * 100
            lines.append(f"  {symbol:6} {pct:5.1f}%")

        # 总计
        total = sum(result.weights.values())
        cash = max(0, 1 - total)
        lines.append(f"\n{'-' * 40}")
        lines.append(f"  总持仓: {total * 100:.1f}%")
        if cash > 0.01:
            lines.append(f"  现金:  {cash * 100:.1f}%")
        lines.append(f"{'=' * 50}\n")

        return "\n".join(lines)
