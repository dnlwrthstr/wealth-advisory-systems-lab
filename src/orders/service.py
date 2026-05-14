"""Order service — submit, track, and simulate execution of orders."""

from __future__ import annotations

import logging
import random
import threading
import time
from datetime import datetime
from typing import Callable

from .fill_engine import (
    calculate_fee,
    calculate_net_amount,
    calculate_settlement_date,
    fx_rate,
)
from .schemas import Order, OrderFill, OrderSide, OrderStatus, OrderType, TimeInForce
from .store import OrderStore

log = logging.getLogger(__name__)


class OrderService:
    def __init__(
        self,
        store: OrderStore,
        fill_interval_seconds: float = 3.0,
        on_fill_callback: Callable[[Order, OrderFill], None] | None = None,
    ):
        self._store = store
        self._fill_interval = fill_interval_seconds
        self._on_fill = on_fill_callback
        self._auto_mode = True
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._fill_loop, daemon=True)
        self._thread.start()

    # ── Public API ──────────────────────────────────────────────────────────

    def submit(
        self,
        portfolio_id: str,
        account_id: str,
        isin: str,
        instrument_name: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        currency: str,
        instrument_type: str = "equity",
        customer_id: str = "",
        limit_price: float | None = None,
        stop_price: float | None = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
        remarks: str = "",
    ) -> Order:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and limit_price is None:
            raise ValueError("limit_price required for limit/stop-limit orders")

        order_id = self._store.next_id()
        now = datetime.utcnow()
        order = Order(
            order_id=order_id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            isin=isin,
            instrument_name=instrument_name,
            instrument_type=instrument_type,
            side=side,
            order_type=order_type,
            quantity=quantity,
            currency=currency,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            status=OrderStatus.RECEIVED,
            submitted_at=now,
            updated_at=now,
            customer_id=customer_id,
            remarks=remarks,
        )
        self._store.save(order)
        return order

    def get(self, order_id: str) -> Order | None:
        return self._store.get(order_id)

    def list_for_portfolio(self, portfolio_id: str) -> list[Order]:
        orders = self._store.list_by_portfolio(portfolio_id)
        return sorted(orders, key=lambda o: o.submitted_at, reverse=True)

    def list_all(self, status: str | None = None, portfolio_id: str | None = None) -> list[Order]:
        orders = list(self._store.list_all())
        if status:
            orders = [o for o in orders if o.status.value == status]
        if portfolio_id:
            orders = [o for o in orders if o.portfolio_id == portfolio_id]
        return sorted(orders, key=lambda o: o.submitted_at, reverse=True)

    def cancel(self, order_id: str) -> Order | None:
        return self._store.cancel(order_id)

    def set_auto_mode(self, enabled: bool) -> None:
        with self._lock:
            self._auto_mode = enabled

    def get_mode(self) -> str:
        return "auto" if self._auto_mode else "manual"

    def execute(self, order_id: str) -> Order:
        """Manually execute a pending order immediately (manual mode)."""
        order = self._store.get(order_id)
        if order is None:
            raise KeyError(f"Order {order_id} not found")
        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED):
            raise ValueError(f"Order {order_id} is already terminal: {order.status.value}")

        # Advance to VALIDATED first if RECEIVED
        if order.status == OrderStatus.RECEIVED:
            order.status = OrderStatus.VALIDATED
            order.updated_at = datetime.utcnow()
            self._store.save(order)

        fill = self._build_fill(order)
        self._store.apply_fill(order.order_id, fill)
        order = self._store.get(order_id)
        self._fire_callback(order, fill)
        return order

    # ── Background fill simulation ──────────────────────────────────────────

    def _fill_loop(self) -> None:
        while True:
            time.sleep(self._fill_interval)
            try:
                with self._lock:
                    if not self._auto_mode:
                        continue
                self._process_pending()
            except Exception:
                pass  # never crash the daemon thread

    def _process_pending(self) -> None:
        pending = self._store.list_pending()
        for order in pending:
            age_seconds = (datetime.utcnow() - order.submitted_at).total_seconds()

            min_age = 2.0 if order.order_type == OrderType.MARKET else 4.0
            if age_seconds < min_age:
                continue

            if order.status == OrderStatus.RECEIVED:
                order.status = OrderStatus.VALIDATED
                order.updated_at = datetime.utcnow()
                self._store.save(order)
                continue

            fill_prob = 0.45 if order.order_type == OrderType.MARKET else 0.30
            if random.random() > fill_prob:
                continue

            fill = self._build_fill(order)
            self._store.apply_fill(order.order_id, fill)
            order = self._store.get(order.order_id)
            self._fire_callback(order, fill)

    def _build_fill(self, order: Order) -> OrderFill:
        """Construct an enriched OrderFill with all performance fields."""
        # Fill price: reference ± random spread
        reference = order.limit_price or 100.0
        spread = reference * random.uniform(0.000, 0.015)
        fill_price = (reference + spread) if order.side == OrderSide.BUY else (reference - spread)
        fill_price = round(max(fill_price, 0.01), 4)

        quantity = order.quantity - order.filled_quantity
        gross = round(quantity * fill_price, 4)
        fee = calculate_fee(gross, order.currency)
        net = calculate_net_amount(gross, fee, order.side.value)
        rate = fx_rate(order.currency)

        now = datetime.utcnow()
        trade_date = now.date().isoformat()
        settlement = calculate_settlement_date(order.instrument_type, trade_date)

        # Realized P&L for sells (requires avg_cost stored on order)
        realized_pnl: float | None = None
        if order.side == OrderSide.SELL and order.average_cost is not None:
            realized_pnl = round((fill_price - order.average_cost) * quantity, 4)

        return OrderFill(
            fill_id=self._store.next_fill_id(order.order_id),
            quantity=quantity,
            price=fill_price,
            currency=order.currency,
            filled_at=now,
            trade_date=trade_date,
            settlement_date=settlement,
            fee=fee,
            net_amount=net,
            fx_rate=rate,
            realized_pnl=realized_pnl,
        )

    def _fire_callback(self, order: Order | None, fill: OrderFill) -> None:
        if self._on_fill is None or order is None:
            return
        try:
            self._on_fill(order, fill)
        except Exception as exc:
            log.warning("on_fill_callback raised: %s", exc)
