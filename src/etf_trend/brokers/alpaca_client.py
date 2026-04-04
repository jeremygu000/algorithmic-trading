"""
Alpaca Broker 客户端
===================

封装 alpaca-py SDK，提供：
- 账户信息查询
- 持仓查询
- 订单提交（市价单、限价单、bracket 订单）
- 订单管理（查询、取消）
- TradePlan → Alpaca Order 转换

Paper Trading 模式默认开启，生产环境通过配置切换。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Literal

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
from alpaca.trading.requests import (
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)

from etf_trend.execution.executor import TradePlan

logger = logging.getLogger(__name__)

# =============================================================================
# 数据类
# =============================================================================


@dataclass
class AccountInfo:
    """账户概要"""

    account_id: str
    status: str
    currency: str
    cash: float
    portfolio_value: float
    equity: float
    buying_power: float
    pattern_day_trader: bool
    trading_blocked: bool


@dataclass
class PositionInfo:
    """持仓概要"""

    symbol: str
    qty: float
    avg_entry_price: float
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: float


@dataclass
class OrderResult:
    """订单结果"""

    order_id: str
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    qty: float
    status: str
    filled_qty: float | None = None
    filled_avg_price: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None
    error: str | None = None


# =============================================================================
# Alpaca 客户端
# =============================================================================


class AlpacaBroker:
    """
    Alpaca 交易客户端

    封装 alpaca-py TradingClient，提供类型安全的交易接口。
    默认使用 paper trading 模式。
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        paper: bool = True,
    ):
        self._client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper,
        )
        self._paper = paper
        logger.info(
            "AlpacaBroker initialized (mode=%s)",
            "paper" if paper else "LIVE",
        )

    # -----------------------------------------------------------------
    # 账户
    # -----------------------------------------------------------------

    def get_account(self) -> AccountInfo:
        """获取账户信息"""
        acct = self._client.get_account()
        return AccountInfo(
            account_id=str(acct.id),
            status=str(acct.status),
            currency=str(acct.currency),
            cash=float(acct.cash),
            portfolio_value=float(acct.portfolio_value),
            equity=float(acct.equity),
            buying_power=float(acct.buying_power),
            pattern_day_trader=bool(acct.pattern_day_trader),
            trading_blocked=bool(acct.trading_blocked),
        )

    # -----------------------------------------------------------------
    # 持仓
    # -----------------------------------------------------------------

    def get_positions(self) -> list[PositionInfo]:
        """获取所有持仓"""
        positions = self._client.get_all_positions()
        return [self._to_position_info(p) for p in positions]

    def get_position(self, symbol: str) -> PositionInfo | None:
        """获取单个持仓，不存在返回 None"""
        try:
            p = self._client.get_open_position(symbol)
            return self._to_position_info(p)
        except APIError:
            return None

    def close_position(self, symbol: str) -> OrderResult:
        """市价平仓"""
        try:
            order = self._client.close_position(symbol)
            return self._to_order_result(order)
        except APIError as e:
            logger.error("Failed to close position %s: %s", symbol, e)
            return OrderResult(
                order_id="",
                client_order_id="",
                symbol=symbol,
                side="sell",
                order_type="market",
                qty=0,
                status="error",
                error=str(e),
            )

    def close_all_positions(self) -> list[OrderResult]:
        """平仓所有持仓"""
        try:
            responses = self._client.close_all_positions(cancel_orders=True)
            results = []
            for resp in responses:
                if hasattr(resp, "body") and hasattr(resp.body, "id"):
                    results.append(self._to_order_result(resp.body))
            return results
        except APIError as e:
            logger.error("Failed to close all positions: %s", e)
            return []

    # -----------------------------------------------------------------
    # 订单提交
    # -----------------------------------------------------------------

    def submit_market_order(
        self,
        symbol: str,
        qty: float,
        side: Literal["buy", "sell"] = "buy",
        time_in_force: TimeInForce = TimeInForce.DAY,
    ) -> OrderResult:
        """提交市价单"""
        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=time_in_force,
            client_order_id=self._gen_client_id(symbol),
        )
        return self._submit(request)

    def submit_limit_order(
        self,
        symbol: str,
        qty: float,
        limit_price: float,
        side: Literal["buy", "sell"] = "buy",
        time_in_force: TimeInForce = TimeInForce.GTC,
    ) -> OrderResult:
        """提交限价单"""
        request = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            limit_price=round(limit_price, 2),
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=time_in_force,
            client_order_id=self._gen_client_id(symbol),
        )
        return self._submit(request)

    def submit_bracket_order(
        self,
        symbol: str,
        qty: float,
        limit_price: float | None = None,
        stop_loss_price: float | None = None,
        take_profit_price: float | None = None,
        side: Literal["buy", "sell"] = "buy",
    ) -> OrderResult:
        """
        提交 Bracket 订单（主单 + 止损 + 止盈）

        - 如果 limit_price 为 None，主单为市价单
        - stop_loss_price 和 take_profit_price 至少需要一个
        """
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        client_id = self._gen_client_id(symbol)

        # 构建止损/止盈参数
        sl = StopLossRequest(stop_price=round(stop_loss_price, 2)) if stop_loss_price else None
        tp = (
            TakeProfitRequest(limit_price=round(take_profit_price, 2))
            if take_profit_price
            else None
        )

        # 确定 order_class
        if sl and tp:
            order_class = OrderClass.BRACKET
        elif sl or tp:
            order_class = OrderClass.OTO
        else:
            order_class = None

        if limit_price is not None:
            request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                limit_price=round(limit_price, 2),
                side=order_side,
                time_in_force=TimeInForce.DAY,
                order_class=order_class,
                stop_loss=sl,
                take_profit=tp,
                client_order_id=client_id,
            )
        else:
            request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY,
                order_class=order_class,
                stop_loss=sl,
                take_profit=tp,
                client_order_id=client_id,
            )
        return self._submit(request)

    # -----------------------------------------------------------------
    # 从 TradePlan 执行
    # -----------------------------------------------------------------

    def execute_trade_plan(
        self,
        plan: TradePlan,
        portfolio_value: float,
        order_type: Literal["market", "limit", "bracket"] = "bracket",
    ) -> OrderResult:
        """
        将 TradePlan 转换为 Alpaca 订单并提交

        Args:
            plan: 交易计划（来自 TradeExecutor）
            portfolio_value: 当前账户总市值（用于计算仓位数量）
            order_type: 订单类型
                - market: 市价单（简单快速）
                - limit: 限价单（用 entry_moderate 价格）
                - bracket: 括号单（限价入场 + 止损 + 止盈）
        """
        if plan.action == "SELL":
            return self.close_position(plan.symbol)

        if plan.action != "BUY":
            return OrderResult(
                order_id="",
                client_order_id="",
                symbol=plan.symbol,
                side="hold",
                order_type="none",
                qty=0,
                status="skipped",
                error="HOLD action, no order needed",
            )

        # 计算买入数量
        target_value = (
            portfolio_value * plan.target_weight
            if plan.target_weight > 0
            else portfolio_value * 0.05
        )
        qty = int(target_value / plan.current_price)
        if qty < 1:
            return OrderResult(
                order_id="",
                client_order_id="",
                symbol=plan.symbol,
                side="buy",
                order_type=order_type,
                qty=0,
                status="skipped",
                error=f"Calculated qty < 1 (target_value=${target_value:.2f}, price=${plan.current_price:.2f})",
            )

        if order_type == "market":
            return self.submit_market_order(plan.symbol, qty, "buy")
        elif order_type == "limit":
            limit_price = plan.entry_moderate or plan.current_price
            return self.submit_limit_order(plan.symbol, qty, limit_price, "buy")
        else:  # bracket
            limit_price = plan.entry_moderate or plan.current_price
            return self.submit_bracket_order(
                symbol=plan.symbol,
                qty=qty,
                limit_price=limit_price,
                stop_loss_price=plan.stop_normal,
                take_profit_price=plan.tp1,
                side="buy",
            )

    # -----------------------------------------------------------------
    # 订单查询与管理
    # -----------------------------------------------------------------

    def get_orders(
        self,
        status: Literal["open", "closed", "all"] = "open",
        limit: int = 50,
    ) -> list[OrderResult]:
        """查询订单"""
        request = GetOrdersRequest(
            status=status if status != "all" else None,
            limit=limit,
        )
        orders = self._client.get_orders(request)
        return [self._to_order_result(o) for o in orders]

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            self._client.cancel_order_by_id(order_id)
            return True
        except APIError as e:
            logger.error("Failed to cancel order %s: %s", order_id, e)
            return False

    def cancel_all_orders(self) -> int:
        """取消所有挂单，返回取消数量"""
        try:
            responses = self._client.cancel_orders()
            return len(responses) if responses else 0
        except APIError as e:
            logger.error("Failed to cancel all orders: %s", e)
            return 0

    # -----------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------

    def _submit(self, request: MarketOrderRequest | LimitOrderRequest) -> OrderResult:
        """提交订单并处理错误"""
        try:
            order = self._client.submit_order(request)
            result = self._to_order_result(order)
            logger.info(
                "Order submitted: %s %s %s qty=%s status=%s",
                result.side,
                result.symbol,
                result.order_type,
                result.qty,
                result.status,
            )
            return result
        except APIError as e:
            logger.error("Order submission failed: %s", e)
            return OrderResult(
                order_id="",
                client_order_id=getattr(request, "client_order_id", ""),
                symbol=request.symbol,
                side=str(request.side),
                order_type=type(request).__name__,
                qty=float(request.qty),
                status="error",
                error=str(e),
            )

    @staticmethod
    def _to_position_info(p) -> PositionInfo:
        return PositionInfo(
            symbol=p.symbol,
            qty=float(p.qty),
            avg_entry_price=float(p.avg_entry_price),
            market_value=float(p.market_value),
            cost_basis=float(p.cost_basis),
            unrealized_pl=float(p.unrealized_pl),
            unrealized_plpc=float(p.unrealized_plpc),
            current_price=float(p.current_price),
        )

    @staticmethod
    def _to_order_result(order) -> OrderResult:
        return OrderResult(
            order_id=str(order.id),
            client_order_id=str(order.client_order_id) if order.client_order_id else "",
            symbol=order.symbol,
            side=str(order.side),
            order_type=str(order.type),
            qty=float(order.qty) if order.qty else 0,
            status=str(order.status),
            filled_qty=float(order.filled_qty) if order.filled_qty else None,
            filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None,
            limit_price=float(order.limit_price) if order.limit_price else None,
            stop_price=float(order.stop_price) if order.stop_price else None,
        )

    @staticmethod
    def _gen_client_id(symbol: str) -> str:
        return f"etf-trend-{symbol}-{uuid.uuid4().hex[:8]}"
