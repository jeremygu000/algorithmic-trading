from __future__ import annotations
import pandas as pd


def momentum_score(
    prices: pd.DataFrame, windows: list[int], weights: list[float]
) -> pd.DataFrame:
    comps = [prices.pct_change(w) for w in windows]
    score = sum(wt * r for wt, r in zip(weights, comps))
    return score


def momentum_decay_signal(prices: pd.Series | pd.DataFrame, short: int = 5, long: int = 20) -> float | pd.Series:
    """
    检测动量是否正在衰减

    Args:
        prices: 价格序列 (Series) 或 DataFrame
        short: 短期动量窗口 (默认 5 天)
        long: 长期动量窗口 (默认 20 天)

    Returns:
        float: 衰减惩罚分数 (0.0 到 -0.3)
               0.0 表示动量健康 (短期 >= 0.5 * 长期)
               -0.3 表示严重衰减
    """
    if isinstance(prices, pd.DataFrame):
        # 如果是 DataFrame，对每一列分别计算
        return prices.apply(lambda col: momentum_decay_signal(col, short, long))
    
    # Series 计算
    # 注意：这里我们只看最新的那个点
    if len(prices) < long:
        return 0.0
        
    mom_short = prices.pct_change(short).iloc[-1]
    mom_long = prices.pct_change(long).iloc[-1]
    
    # 转换为年化或同比例比较
    # 5日动量 * 4 约等于 20日动量 (简单换算)
    # 不过直接对比收益率水平更直观：如果短期涨幅显著小于长期涨幅带来的平均速度
    
    # 逻辑：
    # 如果长期是上涨的 (mom_long > 0)，看短期是否乏力
    if mom_long > 0.02: # 只有长期有明显趋势时才判断衰减
        # 如果短期甚至是跌的，或者涨幅很小
        # 归一化比较：把长期收益率按时间比例缩小
        # 比如20天涨10%，期望5天涨2.5%
        expected_short = mom_long * (short / long)
        
        if mom_short < expected_short * 0.5:
            return -0.3 # 严重衰减
        elif mom_short < expected_short * 0.8:
            return -0.15 # 轻微衰减
            
    return 0.0
