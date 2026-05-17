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
    STOP_LIMIT = "stop_limit"


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
    price: float           # execution price
    currency: str
    filled_at: datetime
    # Performance / settlement fields
    trade_date: str = ""               # ISO date of execution
    settlement_date: str = ""          # T+0/T+1/T+2 by instrument type
    fee: float = 0.0                   # brokerage commission
    net_amount: float = 0.0            # gross ± fee (negative = cash out, positive = cash in)
    fx_rate: float | None = None       # instrument_ccy → account_ccy (CHF) rate
    realized_pnl: float | None = None  # sell only: (price - avg_cost) × qty


@dataclass
class Order:
    order_id: str
    portfolio_id: str
    account_id: str
    isin: str
    instrument_name: str
    instrument_type: str               # OpenWealth FinancialInstrumentType for settlement
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
    reference_price: float | None = None
    filled_quantity: float = 0.0
    average_fill_price: float | None = None
    average_cost: float | None = None  # weighted average cost basis (updated on buys)
    fills: list[OrderFill] = field(default_factory=list)
    customer_id: str = ""
    remarks: str = ""
    rejection_reason: str | None = None
