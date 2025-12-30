
import numpy as np
import pandas as pd
from typing import TypedDict, List
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

class PatternMatchResult(TypedDict):
    similar_patterns_count: int
    avg_return: float
    win_rate: float
    confidence_score: float
    projection: str

def find_similar_patterns(
    current_prices: pd.Series,
    history_prices: pd.Series,
    window: int = 60,
    top_k: int = 5,
    future_window: int = 20
) -> PatternMatchResult:
    """
    寻找历史相似形态 (基于 DTW - Dynamic Time Warping)
    
    原理：
    使用 DTW 算法计算当前价格曲线与历史片段的"距离"。
    相比欧氏距离，DTW 对时间轴的"拉伸"或"压缩"不敏感，
    能更好地识别出形状相似但节奏略有不同的形态。
    
    Args:
        current_prices: 当前价格序列
        history_prices: 历史价格序列
        window: 形态匹配窗口长度
        top_k: 选取最相似的K个历史片段
        future_window: 预测未来窗口长度
        
    Returns:
        PatternMatchResult
    """
    if len(current_prices) < window or len(history_prices) < window + future_window:
        return {
            "similar_patterns_count": 0,
            "avg_return": 0.0,
            "win_rate": 0.0,
            "confidence_score": 0.0,
            "projection": "数据不足"
        }
        
    # 1. 准备目标序列 (归一化)
    target = current_prices.iloc[-window:].values
    target_norm = target / target[0] - 1.0
    
    # 将目标序列转换为二维数组 (fastdtw 需要)
    # 这里的 reshape 是为了让 fastdtw 认为是一维特征的时间序列
    # scipy 的 cdist 风格是 (N, features)，这里 features=1
    target_norm = target_norm.reshape(-1, 1)
    
    # 2. 准备历史搜索
    hist_values = history_prices.values
    distances = []
    search_end_idx = len(history_prices) - window - future_window
    
    # 优化：为了保证API响应速度，我们稍微放宽步长
    # DTW 计算比欧氏距离慢，step=5 可以显著提速且基本不漏掉重要形态
    step = 5 
    
    for i in range(0, search_end_idx, step):
        segment = hist_values[i : i + window]
        
        # 归一化
        seg_norm = segment / segment[0] - 1.0
        seg_norm = seg_norm.reshape(-1, 1)
        
        # 计算 DTW 距离
        # radius=1 限制搜索路径宽度，加速计算
        distance, path = fastdtw(target_norm, seg_norm, radius=1, dist=euclidean)
        
        # 记录索引和距离
        distances.append((i, distance))
        
    if not distances:
        return {
            "similar_patterns_count": 0,
            "avg_return": 0.0,
            "win_rate": 0.0,
            "confidence_score": 0.0,
            "projection": "无历史数据"
        }
        
    # 3. 找出 Top K
    distances.sort(key=lambda x: x[1])
    top_matches = distances[:top_k]
        
    # 4. 分析后续表现
    returns = []
    
    for idx, dist in top_matches:
        start_future = idx + window
        end_future = start_future + future_window
        future_prices = hist_values[start_future : end_future]
        
        ret = (future_prices[-1] / future_prices[0]) - 1.0
        returns.append(ret)
        
    avg_return = float(np.mean(returns))
    win_rate = float(np.sum(np.array(returns) > 0) / top_k)
    
    # 相似度打分 (DTW距离通常比欧氏距离大，因为是累积路径)
    # 需要根据经验调整缩放。简单归一化处理。
    avg_dist = float(np.mean([d[1] for d in top_matches]))
    # 假设 window=60, 平均每个点差异 0.05, 总差异约 3.0
    confidence = max(0.0, min(1.0, 1.0 - avg_dist / 10.0)) 
    
    direction = "看涨" if avg_return > 0.02 else ("看跌" if avg_return < -0.02 else "震荡")
    projection = f"DTW匹配{top_k}次: {win_rate*100:.0f}%概率{direction} (期望 {avg_return*100:.1f}%)"
    
    return {
        "similar_patterns_count": top_k,
        "avg_return": avg_return,
        "win_rate": win_rate,
        "confidence_score": confidence,
        "projection": projection
    }
