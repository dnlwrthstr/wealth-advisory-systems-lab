"""FastAPI app — order management service."""

import logging
import os

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from orders.schemas import Order, OrderFill
from orders.service import OrderService
from orders.store import OrderStore

from .router import build_router

log = logging.getLogger(__name__)

CUSTODIAN_BOOKING_URL = os.getenv(
    "CUSTODIAN_BOOKING_URL", "http://localhost:8001/custody/bookings"
)


def _on_fill(order: Order, fill: OrderFill) -> None:
    payload = {
        "portfolio_id": order.portfolio_id,
        "account_id": order.account_id,
        "customer_id": getattr(order, "customer_id", ""),
        "isin": order.isin,
        "instrument_name": order.instrument_name,
        "instrument_type": order.instrument_type,
        "instrument_currency": order.currency,
        "side": order.side.value,
        "quantity": fill.quantity,
        "fill_price": fill.price,
        "fill_currency": fill.currency,
        "trade_date": fill.trade_date,
        "settlement_date": fill.settlement_date,
        "order_id": order.order_id,
        "fill_id": fill.fill_id,
        "fee": fill.fee,
        "net_amount": fill.net_amount,
        "fx_rate": fill.fx_rate,
    }
    try:
        resp = httpx.post(CUSTODIAN_BOOKING_URL, json=payload, timeout=3.0)
        if resp.status_code != 200:
            log.warning("Booking returned %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        log.warning("Booking post failed: %s", exc)


_store = OrderStore()
_service = OrderService(_store, on_fill_callback=_on_fill)

app = FastAPI(
    title="Order API",
    version="0.2.0",
    description="Trade order submission, tracking, and simulated execution.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(build_router(_service))
