"""
配置管理模块
============

本模块负责加载和管理应用配置，包括：
- 环境变量（API 密钥等敏感信息）
- YAML 配置文件（策略参数等）

配置结构：
---------
- EnvSettings: 从 .env 文件加载的环境变量
- AppConfig: 从 YAML 加载的应用配置
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# 环境变量配置（敏感信息，从 .env 加载）
# =============================================================================


class EnvSettings(BaseSettings):
    """
    环境变量配置

    从 .env 文件加载敏感信息，如 API 密钥。
    这些信息不应该放在代码或 YAML 中。
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Tiingo 数据 API 密钥
    tiingo_api_key: str = Field(alias="TIINGO_API_KEY")

    # LLM 提供商配置（支持千问和 OpenAI）
    llm_provider: Literal["qwen", "openai"] = Field(default="qwen", alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="qwen-plus", alias="LLM_MODEL")


# =============================================================================
# YAML 配置类定义
# =============================================================================


class UniverseCfg(BaseModel):
    """
    ETF 资产池配置

    定义可投资的 ETF 列表，分为股票类和防守类
    """

    # 股票类 ETF（大类、行业）
    equity_symbols: list[str] = []

    # 防守类 ETF（债券、黄金等）
    defensive_symbols: list[str] = []

    # 核心持仓 ETF（有权重上限）
    core_symbols: list[str] = []

    # 市场基准（用于判断大盘状态）
    market_benchmark: str = "SPY"

    # VIX 指数代码
    vix_symbol: str = "^VIX"

    # 兼容旧配置：如果有 symbols 字段
    symbols: list[str] = []

    # 个股池（用于个股扫描/推荐）
    stock_symbols: list[str] = []

    # 股票池构建模式
    # static: 直接使用 stock_symbols
    # dynamic: 从候选池中按流动性/价格/历史数据过滤
    stock_universe_mode: Literal["static", "dynamic"] = "static"

    # dynamic 模式候选池（为空时回退到 stock_symbols）
    dynamic_stock_symbols: list[str] = []
    # dynamic 模式外部候选池文件（支持前端 watchlist 动态写入）
    dynamic_stock_symbols_file: str = "cache/watchlist_symbols.txt"

    # dynamic 模式过滤参数
    dynamic_min_history_days: int = 120
    dynamic_min_price: float = 5.0
    # 平均成交额阈值（美元）= averageVolume * latest_price
    dynamic_min_avg_dollar_volume: float = 20_000_000.0
    dynamic_max_symbols: int = 300

    # 市值分层参考指数成分文件
    # small: Russell 2000 成分股
    # large: Russell 3000 中剔除 Russell 2000 后的剩余部分（近似 Russell 1000）
    russell_2000_symbols_file: str = "cache/index/russell2000.txt"
    russell_3000_symbols_file: str = "cache/index/russell3000.txt"


class RegimeCfg(BaseModel):
    """
    市场状态机配置

    控制 Regime Engine 的参数
    """

    # 长期趋势均线天数
    ma_window: int = 200

    # 中期动量计算天数
    momentum_window: int = 60

    # VIX 恐慌阈值
    vix_threshold: float = 20.0

    # 信号权重
    weight_trend: float = 0.4
    weight_vix: float = 0.3
    weight_momentum: float = 0.3


class RegimeAllocationCfg(BaseModel):
    """单个 Regime 状态下的配置比例"""

    equity: float = 0.5
    defensive: float = 0.5


class AllocationCfg(BaseModel):
    """
    资产配置参数

    控制不同市场状态下的资产配置比例
    """

    # 不同 Regime 状态下的配置
    regime_allocation: dict[str, RegimeAllocationCfg] = {
        "RISK_ON": RegimeAllocationCfg(equity=0.8, defensive=0.2),
        "NEUTRAL": RegimeAllocationCfg(equity=0.5, defensive=0.5),
        "RISK_OFF": RegimeAllocationCfg(equity=0.2, defensive=0.8),
    }

    # 选择 Top-N 个 ETF
    top_n_equity: int = 5
    top_n_defensive: int = 2


class OptimizationCfg(BaseModel):
    """组合优化配置"""

    method: Literal["min_variance", "risk_parity", "inverse_vol"] = "inverse_vol"
    lookback: int = 252  # 协方差矩阵计算窗口


class RebalanceCfg(BaseModel):
    """再平衡配置"""

    # 再平衡频率: M=月度, W=周度
    rule: Literal["M", "W"] = "M"


class SignalCfg(BaseModel):
    """信号参数配置"""

    # 趋势过滤均线
    ma_long: int = 200

    # 动量计算窗口
    mom_windows: list[int] = [20, 60, 120, 240]

    # 各周期权重
    mom_weights: list[float] = [0.25, 0.25, 0.25, 0.25]


class RiskCfg(BaseModel):
    """风险控制配置"""

    # 目标年化波动率
    target_vol_annual: float = 0.10

    # 波动率回溯天数
    vol_lookback: int = 60

    # 单一资产权重上限
    max_weight_single: float = 0.30

    # 核心资产组合权重上限
    max_weight_core: float = 0.50

    # 交易成本 (basis points)
    cost_bps: float = 5.0


class CacheCfg(BaseModel):
    """缓存配置"""

    enabled: bool = True
    dir: str = "cache"


class ProviderTiingoCfg(BaseModel):
    """Tiingo 数据源配置"""

    enabled: bool = True


class ProvidersCfg(BaseModel):
    """数据源配置"""

    tiingo: ProviderTiingoCfg = ProviderTiingoCfg()


# =============================================================================
# 主配置类
# =============================================================================


class AppConfig(BaseModel):
    """
    应用主配置

    从 YAML 文件加载的完整配置
    """

    universe: UniverseCfg = UniverseCfg()
    regime: RegimeCfg = RegimeCfg()
    allocation: AllocationCfg = AllocationCfg()
    optimizer: OptimizationCfg = OptimizationCfg()
    rebalance: RebalanceCfg = RebalanceCfg()
    signal: SignalCfg = SignalCfg()
    risk: RiskCfg = RiskCfg()
    cache: CacheCfg = CacheCfg()
    providers: ProvidersCfg = ProvidersCfg()


def load_config(path: str | Path) -> AppConfig:
    """
    加载配置文件

    Args:
        path: YAML 配置文件路径

    Returns:
        AppConfig: 解析后的配置对象
    """
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return AppConfig.model_validate(data)
