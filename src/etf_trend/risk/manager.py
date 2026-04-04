"""
实盘风控管理器
==============

核心组件:
  - RiskManager: 订单前校验（持仓限制、每日亏损限制、买入力校验）
  - RiskMonitor: 后台任务（止损监控、每日 P&L 追踪、风险告警广播）
  - RiskState: 当日风控状态快照
  - RiskAlert: 风控告警数据

架构:
  Pre-Trade:  trade endpoint → RiskManager.validate_order() → AlpacaBroker
  Background: RiskMonitor.run() 每 30s → check_stops() + update_pnl() → WebSocket risk_alert
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


# ── 数据类 ──────────────────────────────────────────────────────────────────


@dataclass
class RiskAlert:
    """单条风控告警。"""

    level: str  # "warning" | "critical"
    category: str  # "stop_loss" | "daily_pnl" | "position_limit" | "order_value"
    message: str
    symbol: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "risk_alert",
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
        }


@dataclass
class RiskState:
    """当日风控状态快照。"""

    date: str = ""
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    starting_equity: float = 0.0
    current_equity: float = 0.0
    position_count: int = 0
    safe_mode: bool = False  # 触发每日亏损限制时进入安全模式
    alerts: list[RiskAlert] = field(default_factory=list)
    last_check: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "daily_pnl": round(self.daily_pnl, 2),
            "daily_pnl_pct": round(self.daily_pnl_pct, 4),
            "starting_equity": round(self.starting_equity, 2),
            "current_equity": round(self.current_equity, 2),
            "position_count": self.position_count,
            "safe_mode": self.safe_mode,
            "alert_count": len(self.alerts),
            "recent_alerts": [a.to_dict() for a in self.alerts[-20:]],
            "last_check": self.last_check,
        }


# ── RiskManager: 订单前校验 ─────────────────────────────────────────────────


class RiskManager:
    """
    Pre-trade risk validation.

    在下单前校验：
    1. 持仓数量限制 (max_positions)
    2. 单笔订单金额限制 (max_order_value)
    3. 每日亏损限制 (daily_loss_limit_pct) — 安全模式下禁止新开仓
    4. 买入力缓冲 (buying_power)
    """

    def __init__(
        self,
        max_positions: int = 20,
        max_order_value: float = 50_000.0,
        daily_loss_limit_pct: float = 0.03,
        buying_power_buffer: float = 0.05,
    ) -> None:
        self.max_positions = max_positions
        self.max_order_value = max_order_value
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.buying_power_buffer = buying_power_buffer
        self.state = RiskState()

    def validate_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        position_count: int,
        buying_power: float,
        portfolio_value: float,
    ) -> list[str]:
        """
        校验订单。返回违规列表（空 = 通过）。

        Args:
            symbol: 股票代码
            side: "buy" | "sell"
            qty: 下单数量
            price: 当前/限价
            position_count: 当前持仓数
            buying_power: 可用买入力
            portfolio_value: 组合总值
        """
        violations: list[str] = []

        if side.lower() == "buy":
            # 1. 安全模式：每日亏损超限
            if self.state.safe_mode:
                violations.append(
                    f"安全模式已启动（日亏损 {self.state.daily_pnl_pct:.2%}），" f"禁止新开仓"
                )

            # 2. 持仓数量限制
            if position_count >= self.max_positions:
                violations.append(
                    f"持仓数已达上限 {self.max_positions}，" f"当前 {position_count} 个持仓"
                )

            # 3. 单笔订单金额
            order_value = qty * price
            if order_value > self.max_order_value:
                violations.append(
                    f"订单金额 ${order_value:,.0f} 超过单笔限额 " f"${self.max_order_value:,.0f}"
                )

            # 4. 买入力缓冲
            buffer = portfolio_value * self.buying_power_buffer
            if qty * price > buying_power - buffer:
                violations.append(
                    f"买入力不足：需要 ${qty * price:,.0f}，"
                    f"可用 ${buying_power:,.0f}（保留 {self.buying_power_buffer:.0%} 缓冲）"
                )

        return violations

    def update_state(
        self,
        equity: float,
        position_count: int,
    ) -> None:
        """更新当日风控状态。"""
        today = date.today().isoformat()

        # 新的交易日 → 重置
        if self.state.date != today:
            self.state = RiskState(
                date=today,
                starting_equity=equity,
                current_equity=equity,
                position_count=position_count,
            )
        else:
            self.state.current_equity = equity
            self.state.position_count = position_count

        # 计算日内 P&L
        if self.state.starting_equity > 0:
            self.state.daily_pnl = equity - self.state.starting_equity
            self.state.daily_pnl_pct = self.state.daily_pnl / self.state.starting_equity
        else:
            self.state.daily_pnl = 0.0
            self.state.daily_pnl_pct = 0.0

        # 安全模式检查
        if self.state.daily_pnl_pct < -self.daily_loss_limit_pct:
            if not self.state.safe_mode:
                self.state.safe_mode = True
                alert = RiskAlert(
                    level="critical",
                    category="daily_pnl",
                    message=(
                        f"每日亏损 {self.state.daily_pnl_pct:.2%} 超过限制 "
                        f"{self.daily_loss_limit_pct:.2%}，进入安全模式"
                    ),
                )
                self.state.alerts.append(alert)

        self.state.last_check = time.time()


# ── RiskMonitor: 后台监控任务 ───────────────────────────────────────────────


class RiskMonitor:
    """
    Background risk monitoring task.

    每隔 interval_sec 执行:
    1. 拉取 Alpaca 账户信息 → 更新 RiskState
    2. 拉取持仓 → 检查止损触发
    3. 如有告警 → 通过 WebSocket 广播
    """

    def __init__(
        self,
        risk_manager: RiskManager,
        interval_sec: float = 30.0,
    ) -> None:
        self._rm = risk_manager
        self._interval = interval_sec
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._broker_factory: Any = None  # 延迟注入，避免循环依赖
        self._ws_broadcast: Any = None  # async callable: broadcast(dict)

    def configure(
        self,
        broker_factory: Any,
        ws_broadcast: Any,
    ) -> None:
        """注入 broker 工厂和 WebSocket 广播函数。在 lifespan 中调用。"""
        self._broker_factory = broker_factory
        self._ws_broadcast = ws_broadcast

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("RiskMonitor started (interval=%.0fs)", self._interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("RiskMonitor stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._check()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("RiskMonitor check failed")
            await asyncio.sleep(self._interval)

    async def _check(self) -> None:
        """单次检查周期。"""
        if not self._broker_factory:
            return

        broker = self._broker_factory()
        alerts_before = len(self._rm.state.alerts)

        # 1. 更新账户状态
        try:
            acct = broker.get_account()
            positions = broker.get_positions()
            self._rm.update_state(
                equity=acct.equity,
                position_count=len(positions),
            )
        except Exception:
            logger.exception("Failed to fetch account data for risk check")
            return

        # 2. 检查止损
        await self._check_stops(broker, positions)

        # 3. 广播新告警
        new_alerts = self._rm.state.alerts[alerts_before:]
        if new_alerts and self._ws_broadcast:
            for alert in new_alerts:
                try:
                    await self._ws_broadcast(alert.to_dict())
                except Exception:
                    logger.exception("Failed to broadcast risk alert")

    async def _check_stops(self, broker: Any, positions: list[Any]) -> None:
        """检查持仓是否触及止损价。"""
        for pos in positions:
            symbol = pos.symbol
            current_price = pos.current_price
            unrealized_plpc = pos.unrealized_plpc

            # 如果未实现亏损超过 15%，发出警告
            if unrealized_plpc is not None and unrealized_plpc < -0.15:
                # 检查是否已有该 symbol 的近期止损告警（5 分钟内不重复）
                now = time.time()
                recent = any(
                    a.symbol == symbol and a.category == "stop_loss" and now - a.timestamp < 300
                    for a in self._rm.state.alerts
                )
                if not recent:
                    alert = RiskAlert(
                        level="warning",
                        category="stop_loss",
                        message=(
                            f"{symbol} 未实现亏损 {unrealized_plpc:.2%}，"
                            f"当前价 ${current_price}，建议检查止损"
                        ),
                        symbol=symbol,
                    )
                    self._rm.state.alerts.append(alert)

            # 如果未实现亏损超过 25%，发出严重警告
            if unrealized_plpc is not None and unrealized_plpc < -0.25:
                now = time.time()
                recent = any(
                    a.symbol == symbol
                    and a.category == "stop_loss"
                    and a.level == "critical"
                    and now - a.timestamp < 300
                    for a in self._rm.state.alerts
                )
                if not recent:
                    alert = RiskAlert(
                        level="critical",
                        category="stop_loss",
                        message=(
                            f"{symbol} 严重亏损 {unrealized_plpc:.2%}，"
                            f"当前价 ${current_price}，强烈建议止损"
                        ),
                        symbol=symbol,
                    )
                    self._rm.state.alerts.append(alert)


# ── 模块级单例 ──────────────────────────────────────────────────────────────

risk_manager = RiskManager()
risk_monitor = RiskMonitor(risk_manager=risk_manager)
