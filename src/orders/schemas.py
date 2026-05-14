"""Order management schemas — OpenWealth-aligned order instruction and status models."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stopLimit"


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"   # good till cancelled
    IOC = "ioc"   # immediate or cancel
    FOK = "fok"   # fill or kill


class OrderStatus(str, Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderFill:
    fill_id: str
    quantity: float
    price: float
    currency: str
    filled_at: datetime


@dataclass
class Order:
    order_id: str
    portfolio_id: str
    account_id: str
    isin: str
    instrument_name: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    currency: str
    time_in_force: TimeInForce
    status: OrderStatus
    submitted_at: datetime
    updated_at: datetime
    limit_price: float | None = None
    stop_price: float | None = None
    filled_quantity: float = 0.0
    average_fill_price: float | None = None
    fills: list[OrderFill] = field(default_factory=list)
    remarks: str = ""
    rejection_reason: str | None = None
