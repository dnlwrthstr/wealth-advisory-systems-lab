"""In-memory order store — mutable order book with status tracking."""

from __future__ import annotations
import threading
from datetime import datetime

from .schemas import Order, OrderFill, OrderStatus


class OrderStore:
    def __init__(self):
        self._orders: dict[str, Order] = {}
        self._lock = threading.Lock()
        self._seq = 0

    def next_id(self) -> str:
        with self._lock:
            self._seq += 1
            return f"ORD-{self._seq:06d}"

    def next_fill_id(self, order_id: str) -> str:
        order = self._orders.get(order_id)
        n = len(order.fills) + 1 if order else 1
        return f"{order_id}-F{n:02d}"

    def save(self, order: Order) -> Order:
        with self._lock:
            self._orders[order.order_id] = order
        return order

    def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def list_by_portfolio(self, portfolio_id: str) -> list[Order]:
        return [o for o in self._orders.values() if o.portfolio_id == portfolio_id]

    def list_pending(self) -> list[Order]:
        return [
            o for o in self._orders.values()
            if o.status in (OrderStatus.RECEIVED, OrderStatus.VALIDATED, OrderStatus.PENDING)
        ]

    def apply_fill(self, order_id: str, fill: OrderFill) -> Order | None:
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                return None
            order.fills.append(fill)
            order.filled_quantity += fill.quantity
            order.updated_at = datetime.utcnow()

            total_value = sum(f.price * f.quantity for f in order.fills)
            total_qty = sum(f.quantity for f in order.fills)
            order.average_fill_price = total_value / total_qty if total_qty else None

            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
            else:
                order.status = OrderStatus.PARTIAL
            return order

    def cancel(self, order_id: str) -> Order | None:
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                return None
            if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
                return order
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.utcnow()
            return order
