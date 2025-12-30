"""
业绩归因分析模块
================

提供机构级的业绩评估指标，包括：
1. Alpha/Beta 分解 (基于 CAPM 模型)
2. 风险调整后收益 (Sortino, Information Ratio)
3. 回撤分析 (Max Drawdown Duration)

"""

import numpy as np
import pandas as pd
import statsmodels.api as sm


def calculate_alpha_beta(
    returns: pd.Series, benchmark_returns: pd.Series, risk_free_rate: float = 0.0
) -> dict:
    """
    计算 Alpha 和 Beta (CAPM 模型)

    Formula: Rp - Rf = alpha + beta * (Rm - Rf) + epsilon

    Args:
        returns: 策略收益率序列
        benchmark_returns: 基准收益率序列
        risk_free_rate: 无风险利率 (年化，默认 0)

    Returns:
        dict: {
            "alpha": 年化 Alpha,
            "beta": Beta 系数,
            "r_squared": R平方 (拟合优度),
            "p_value": Alpha 的显著性 P值
        }
    """
    # 对齐数据
    df = pd.DataFrame({"port": returns, "bench": benchmark_returns}).dropna()

    if len(df) < 30:
        return {
            "alpha": np.nan,
            "beta": np.nan,
            "r_squared": np.nan,
            "p_value": np.nan,
        }

    # 计算超额收益
    y = df["port"] - risk_free_rate / 252
    x = df["bench"] - risk_free_rate / 252

    # 添加截距项 (Alpha)
    x = sm.add_constant(x)

    # OLS 回归
    model = sm.OLS(y, x).fit()

    alpha_daily = model.params["const"]
    beta = model.params["bench"]

    # 年化 Alpha
    alpha_annual = (1 + alpha_daily) ** 252 - 1

    return {
        "alpha": alpha_annual,
        "beta": beta,
        "r_squared": model.rsquared,
        "p_value": model.pvalues["const"],
    }


def calculate_sortino_ratio(
    returns: pd.Series, target_return: float = 0.0, periods: int = 252
) -> float:
    """
    计算 Sortino Ratio (只考虑下行风险)

    Args:
        returns: 收益率序列
        target_return: 目标收益率 (即使没有亏损，低于此收益也视为风险)
        periods: 年化周期

    Returns:
        float: Sortino Ratio
    """
    # 计算下行偏差 (Downside Deviation)
    downside_returns = returns[returns < target_return]

    if len(downside_returns) == 0:
        return np.inf

    downside_std = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(periods)

    annual_return = np.mean(returns) * periods

    if downside_std == 0:
        return np.inf

    return (annual_return - target_return * periods) / downside_std


def calculate_max_drawdown_duration(returns: pd.Series) -> int:
    """
    计算最长回撤持续时间 (交易日)

    Args:
        returns: 收益率序列

    Returns:
        int: 最长回撤天数
    """
    cumulative = (1 + returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak

    # 标记处于回撤状态的日子
    is_drawdown = drawdown < 0

    if not is_drawdown.any():
        return 0

    # 计算连续回撤天数
    # identifying run lengths of True values
    # Ref: https://stackoverflow.com/questions/24527006/pandas-consecutive-boolean-counts

    series = is_drawdown.astype(int)
    # 巧妙的方法：比较当前和前一个是否相等，不等则累加组号
    groups = series.ne(series.shift()).cumsum()
    # 既然只关心回撤(1)，筛选出处于回撤的组
    drawdown_groups = series[series == 1].groupby(groups)

    if len(drawdown_groups) == 0:
        return 0

    return drawdown_groups.size().max()


def calculate_advanced_metrics(
    returns: pd.Series, benchmark_returns: pd.Series | None = None
) -> dict:
    """计算综合高级指标"""

    metrics = {
        "sortino_ratio": calculate_sortino_ratio(returns),
        "max_drawdown_duration": calculate_max_drawdown_duration(returns),
    }

    if benchmark_returns is not None:
        metrics.update(calculate_alpha_beta(returns, benchmark_returns))

        # Information Ratio
        # IR = (Rp - Rb) / TrackingError
        active_return = returns - benchmark_returns
        tracking_error = active_return.std() * np.sqrt(252)
        mean_active_return = active_return.mean() * 252

        metrics["information_ratio"] = (
            mean_active_return / tracking_error if tracking_error != 0 else np.nan
        )

    return metrics
