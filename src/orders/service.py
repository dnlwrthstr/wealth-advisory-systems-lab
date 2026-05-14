"""Order service — submit, track, and simulate execution of orders."""

from __future__ import annotations
import random
import threading
import time
from datetime import datetime

from .schemas import Order, OrderFill, OrderSide, OrderStatus, OrderType, TimeInForce
from .store import OrderStore


class OrderService:
    def __init__(self, store: OrderStore, fill_interval_seconds: float = 3.0):
        self._store = store
        self._fill_interval = fill_interval_seconds
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
            remarks=remarks,
        )
        self._store.save(order)
        return order

    def get(self, order_id: str) -> Order | None:
        return self._store.get(order_id)

    def list_for_portfolio(self, portfolio_id: str) -> list[Order]:
        orders = self._store.list_by_portfolio(portfolio_id)
        return sorted(orders, key=lambda o: o.submitted_at, reverse=True)

    def cancel(self, order_id: str) -> Order | None:
        return self._store.cancel(order_id)

    # ── Background fill simulation ──────────────────────────────────────────

    def _fill_loop(self) -> None:
        while True:
            time.sleep(self._fill_interval)
            try:
                self._process_pending()
            except Exception:
                pass  # never crash the daemon thread

    def _process_pending(self) -> None:
        pending = self._store.list_pending()
        for order in pending:
            age_seconds = (datetime.utcnow() - order.submitted_at).total_seconds()

            # Market orders fill quickly; limit orders take a bit longer
            min_age = 2.0 if order.order_type == OrderType.MARKET else 4.0
            if age_seconds < min_age:
                continue

            # Mark as validated on first check past min_age
            if order.status == OrderStatus.RECEIVED:
                order.status = OrderStatus.VALIDATED
                order.updated_at = datetime.utcnow()
                self._store.save(order)
                continue

            # Random fill probability per interval
            fill_prob = 0.45 if order.order_type == OrderType.MARKET else 0.30
            if random.random() > fill_prob:
                continue

            # Simulate fill price: market price ± up to 1.5%
            reference = order.limit_price or 100.0
            spread = reference * random.uniform(0.000, 0.015)
            if order.side == OrderSide.BUY:
                fill_price = reference + spread
            else:
                fill_price = reference - spread
            fill_price = max(fill_price, 0.01)

            # Fill the remaining quantity in one shot
            remaining = order.quantity - order.filled_quantity
            fill = OrderFill(
                fill_id=self._store.next_fill_id(order.order_id),
                quantity=remaining,
                price=round(fill_price, 4),
                currency=order.currency,
                filled_at=datetime.utcnow(),
            )
            self._store.apply_fill(order.order_id, fill)
