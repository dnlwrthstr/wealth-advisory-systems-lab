"""HTTP routes for the order API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from orders.schemas import OrderSide, OrderType, TimeInForce
from orders.service import OrderService


class SubmitOrderRequest(BaseModel):
    portfolio_id: str
    account_id: str
    customer_id: str = ""
    isin: str
    instrument_name: str
    instrument_type: str = "equity"
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(gt=0)
    currency: str
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    remarks: str = ""


class SetModeRequest(BaseModel):
    auto: bool


def build_router(service: OrderService) -> APIRouter:
    router = APIRouter(prefix="/orders", tags=["orders"])

    @router.get("/mode")
    def get_mode() -> dict:
        return {"mode": service.get_mode()}

    @router.post("/mode")
    def set_mode(body: SetModeRequest) -> dict:
        service.set_auto_mode(body.auto)
        return {"mode": service.get_mode()}

    @router.get("")
    def list_all_orders(status: Optional[str] = None, portfolio_id: Optional[str] = None) -> list[dict]:
        orders = service.list_all(status=status, portfolio_id=portfolio_id)
        return [_to_dict(o) for o in orders]

    @router.post("", status_code=201)
    def submit_order(body: SubmitOrderRequest) -> dict:
        try:
            order = service.submit(
                portfolio_id=body.portfolio_id,
                account_id=body.account_id,
                isin=body.isin,
                instrument_name=body.instrument_name,
                instrument_type=body.instrument_type,
                side=body.side,
                order_type=body.order_type,
                quantity=body.quantity,
                currency=body.currency,
                customer_id=body.customer_id,
                limit_price=body.limit_price,
                stop_price=body.stop_price,
                time_in_force=body.time_in_force,
                remarks=body.remarks,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _to_dict(order)

    @router.post("/{order_id}/execute")
    def execute_order(order_id: str) -> dict:
        try:
            order = service.execute(order_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return _to_dict(order)

    @router.get("/portfolio/{portfolio_id}")
    def list_orders_by_portfolio(portfolio_id: str) -> list[dict]:
        orders = service.list_for_portfolio(portfolio_id)
        return [_to_dict(o) for o in orders]

    @router.get("/{order_id}")
    def get_order(order_id: str) -> dict:
        order = service.get(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="order not found")
        return _to_dict(order)

    @router.delete("/{order_id}", status_code=200)
    def cancel_order(order_id: str) -> dict:
        order = service.cancel(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="order not found")
        return _to_dict(order)

    return router


def _dt(dt: datetime) -> str:
    return dt.isoformat() + "Z"


def _to_dict(o) -> dict:
    return {
        "orderId": o.order_id,
        "portfolioId": o.portfolio_id,
        "accountId": o.account_id,
        "customerId": getattr(o, "customer_id", ""),
        "isin": o.isin,
        "instrumentName": o.instrument_name,
        "instrumentType": getattr(o, "instrument_type", "equity"),
        "side": o.side.value,
        "orderType": o.order_type.value,
        "quantity": o.quantity,
        "currency": o.currency,
        "limitPrice": o.limit_price,
        "stopPrice": o.stop_price,
        "timeInForce": o.time_in_force.value,
        "status": o.status.value,
        "submittedAt": _dt(o.submitted_at),
        "updatedAt": _dt(o.updated_at),
        "filledQuantity": o.filled_quantity,
        "averageFillPrice": o.average_fill_price,
        "fills": [
            {
                "fillId": f.fill_id,
                "quantity": f.quantity,
                "price": f.price,
                "currency": f.currency,
                "filledAt": _dt(f.filled_at),
                "tradeDate": f.trade_date,
                "settlementDate": f.settlement_date,
                "fee": f.fee,
                "netAmount": f.net_amount,
                "fxRate": f.fx_rate,
                "realizedPnl": f.realized_pnl,
            }
            for f in o.fills
        ],
        "remarks": o.remarks,
        "rejectionReason": o.rejection_reason,
    }
