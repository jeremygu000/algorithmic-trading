"""
WebSocket 连接管理器 + Alpaca TradingStream 桥接
================================================

架构:
  Alpaca WSS (trade_updates) ──► TradeStreamBridge ──► ConnectionManager ──► Browser WS clients

核心组件:
  - ConnectionManager: 管理多个浏览器 WebSocket 连接，广播消息
  - TradeStreamBridge: 连接 Alpaca TradingStream，转发事件给 ConnectionManager
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


# =============================================================================
# WebSocket 连接管理器
# =============================================================================


class ConnectionManager:
    """管理浏览器 WebSocket 客户端连接。"""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    @property
    def client_count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WS client connected (%d total)", self.client_count)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WS client disconnected (%d remaining)", self.client_count)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """向所有已连接客户端广播 JSON 消息。"""
        if not self._connections:
            return

        payload = json.dumps(message)
        dead: list[WebSocket] = []

        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self._connections.discard(ws)

    async def send_personal(self, ws: WebSocket, message: dict[str, Any]) -> None:
        """向单个客户端发送 JSON 消息。"""
        try:
            await ws.send_json(message)
        except Exception:
            self._connections.discard(ws)


# =============================================================================
# Alpaca TradingStream 桥接
# =============================================================================


class TradeStreamBridge:
    """
    桥接 Alpaca TradingStream → ConnectionManager。

    - 在后台线程运行 Alpaca TradingStream（它是阻塞的）
    - 将 trade_updates 事件转发到 asyncio 事件循环中的 ConnectionManager
    - 自动重连（指数退避，最大 60s）
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        paper: bool,
        manager: ConnectionManager,
    ) -> None:
        self._api_key = api_key
        self._secret_key = secret_key
        self._paper = paper
        self._manager = manager
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """启动 Alpaca stream 后台任务。"""
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_running_loop()
        self._task = asyncio.create_task(self._run_with_reconnect())
        logger.info("TradeStreamBridge started")

    async def stop(self) -> None:
        """停止 Alpaca stream。"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("TradeStreamBridge stopped")

    async def _run_with_reconnect(self) -> None:
        """带指数退避的重连循环。"""
        backoff = 1.0
        max_backoff = 60.0

        while self._running:
            try:
                await self._connect_and_listen()
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Alpaca stream error: %s — retrying in %.0fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    async def _connect_and_listen(self) -> None:
        """连接 Alpaca TradingStream 并监听事件。"""
        from alpaca.trading.stream import TradingStream

        stream = TradingStream(
            api_key=self._api_key,
            secret_key=self._secret_key,
            paper=self._paper,
        )

        async def _on_trade_update(data: Any) -> None:
            """Alpaca trade_updates 回调 → 广播给浏览器客户端。"""
            try:
                event = self._serialize_trade_event(data)
                await self._manager.broadcast(event)
            except Exception:
                logger.exception("Failed to broadcast trade event")

        stream.subscribe_trade_updates(_on_trade_update)

        logger.info("Connecting to Alpaca trade stream (paper=%s)...", self._paper)
        # TradingStream.run() 内部运行 asyncio 事件循环
        # 我们用 run_in_executor 在线程中运行，避免阻塞主循环
        await asyncio.get_running_loop().run_in_executor(None, stream._run_forever)

    @staticmethod
    def _serialize_trade_event(data: Any) -> dict[str, Any]:
        """将 Alpaca trade update 事件序列化为前端可用的 JSON。"""
        # alpaca-py TradeUpdate 对象有 event, order, timestamp 等属性
        order = data.order if hasattr(data, "order") else None

        event: dict[str, Any] = {
            "type": "trade_update",
            "event": str(data.event) if hasattr(data, "event") else "unknown",
            "timestamp": time.time(),
        }

        if order:
            event["order"] = {
                "order_id": str(order.id) if hasattr(order, "id") else None,
                "client_order_id": (
                    str(order.client_order_id) if hasattr(order, "client_order_id") else None
                ),
                "symbol": str(order.symbol) if hasattr(order, "symbol") else None,
                "side": str(order.side) if hasattr(order, "side") else None,
                "order_type": str(order.type) if hasattr(order, "type") else None,
                "qty": str(order.qty) if hasattr(order, "qty") else None,
                "status": str(order.status) if hasattr(order, "status") else None,
                "filled_qty": str(order.filled_qty) if hasattr(order, "filled_qty") else None,
                "filled_avg_price": (
                    str(order.filled_avg_price) if hasattr(order, "filled_avg_price") else None
                ),
                "limit_price": str(order.limit_price) if hasattr(order, "limit_price") else None,
                "stop_price": str(order.stop_price) if hasattr(order, "stop_price") else None,
            }

        if hasattr(data, "price") and data.price is not None:
            event["fill_price"] = str(data.price)
        if hasattr(data, "qty") and data.qty is not None:
            event["fill_qty"] = str(data.qty)
        if hasattr(data, "position_qty") and data.position_qty is not None:
            event["position_qty"] = str(data.position_qty)

        return event


# =============================================================================
# 模块级单例
# =============================================================================

ws_manager = ConnectionManager()
trade_bridge: TradeStreamBridge | None = None


def get_trade_bridge(api_key: str, secret_key: str, paper: bool) -> TradeStreamBridge:
    """获取或创建 TradeStreamBridge 单例。"""
    global trade_bridge
    if trade_bridge is None:
        trade_bridge = TradeStreamBridge(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper,
            manager=ws_manager,
        )
    return trade_bridge
