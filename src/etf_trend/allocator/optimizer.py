"""
组合优化引擎
============

提供基于数学优化的资产配置算法。
核心算法：
1. 最小方差 (Minimum Variance) - 追求最低波动
2. 风险平价 (Risk Parity) - 追求风险贡献相等
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf


class PortfolioOptimizer:
    def __init__(self, returns: pd.DataFrame):
        """
        初始化优化器

        Args:
            returns: 资产收益率数据 (index=Date, columns=Asset)
        """
        self.returns = returns
        # 使用 Ledoit-Wolf 收缩估计协方差矩阵 (Robust)
        # 相比普通的 .cov()，它更能处理样本不足的情况
        lw = LedoitWolf()
        self.cov_matrix = lw.fit(returns).covariance_ * 252
        self.assets = returns.columns
        self.n_assets = len(self.assets)

    def optimize(
        self, method: str = "min_variance", max_weight: float = 1.0
    ) -> pd.Series:
        """
        执行组合优化

        Args:
            method: 优化方法 ("min_variance", "risk_parity")
            max_weight: 单资产最大权重

        Returns:
            pd.Series: 优化后的权重 (index=Asset)
        """
        if method == "min_variance":
            weights = self._min_variance(max_weight)
        elif method == "risk_parity":
            weights = self._risk_parity(max_weight)
        else:
            raise ValueError(f"Unknown method: {method}")

        return pd.Series(weights, index=self.assets)

    def _min_variance(self, max_weight: float) -> np.ndarray:
        """最小方差组合"""

        # 目标函数：最小化组合方差 w'Σw
        def objective(weights):
            return weights.T @ self.cov_matrix @ weights

        # 约束条件
        constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]  # 权重和为 1
        bounds = tuple((0, max_weight) for _ in range(self.n_assets))  # 权重限制

        # 初始猜测：等权
        init_guess = np.repeat(1 / self.n_assets, self.n_assets)

        result = minimize(
            objective,
            init_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result.x

    def _risk_parity(self, max_weight: float) -> np.ndarray:
        """风险平价组合 (ERC - Equal Risk Contribution)"""

        # 目标：最小化风险贡献差异
        # 风险贡献 RC_i = w_i * (Σw)_i / sqrt(w'Σw)
        # 为简化计算，目标设为 minimize sum((w_i * (Σw)_i - target_risk)^2)

        def calculate_portfolio_var(weights):
            return weights.T @ self.cov_matrix @ weights

        def calculate_risk_contribution(weights):
            portfolio_var = calculate_portfolio_var(weights)
            # Marginal Risk Contribution
            mrc = self.cov_matrix @ weights
            # Risk Contribution = w * MRC / std
            # 这里我们比较 w * MRC 即可，因为分母相同
            rc = weights * mrc
            return rc / portfolio_var  # 归一化

        def objective(weights):
            rc = calculate_risk_contribution(weights)
            target = 1 / self.n_assets  # 目标是每个资产贡献 1/N 的风险
            return np.sum((rc - target) ** 2)

        # 约束条件
        constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]
        bounds = tuple((0, max_weight) for _ in range(self.n_assets))
        init_guess = np.repeat(1 / self.n_assets, self.n_assets)

        result = minimize(
            objective,
            init_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            tol=1e-6,
        )

        return result.x
