"""HTTP routes for the custodian API — OpenWealth-compliant endpoints."""

import uuid
from typing import Optional

from custodian.reference import build_reference
from custodian.schemas import (
    Account,
    AccountReference,
    AccountType,
    Customer,
    CustomerSnapshot,
    FinancialInstrument,
    FinancialInstrumentType,
    Movement,
    MovementType,
    Quantity,
    QuantityUnit,
    Transaction,
    TransactionType,
    ValuatedPosition,
    ValuationPrice,
    PriceType,
)
from custodian.service import CustodianService
from custodian.store import InMemoryCustodianStore
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

_REFERENCE = build_reference()


class TradeBookingRequest(BaseModel):
    portfolio_id: str
    account_id: str
    customer_id: str
    isin: str
    instrument_name: str
    instrument_type: str
    instrument_currency: str
    side: str           # "buy" | "sell"
    quantity: float
    fill_price: float
    fill_currency: str
    trade_date: str
    settlement_date: str
    order_id: str
    fill_id: str
    fee: float = 0.0
    net_amount: float = 0.0
    fx_rate: Optional[float] = None


def build_router(service: CustodianService) -> APIRouter:
    router = APIRouter(prefix="/custody", tags=["custodian"])

    @router.get("/reference", tags=["reference"])
    def get_reference() -> dict[str, list[dict[str, str]]]:
        """Return all OpenWealth enum reference data for dropdowns and search."""
        return _REFERENCE


    @router.get("/customers", response_model=list[Customer])
    def list_customers() -> list[Customer]:
        return service.list_customers()

    @router.get("/customers/{customer_id}", response_model=Customer)
    def get_customer(customer_id: str) -> Customer:
        customer = service.get_customer(customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="customer not found")
        return customer

    @router.get("/customers/{customer_id}/accounts", response_model=list[Account])
    def list_accounts(customer_id: str) -> list[Account]:
        if service.get_customer(customer_id) is None:
            raise HTTPException(status_code=404, detail="customer not found")
        return service.list_accounts(customer_id)

    @router.get("/customers/{customer_id}/positions", response_model=list[ValuatedPosition])
    def list_positions(
        customer_id: str,
        account_id: str | None = None,
    ) -> list[ValuatedPosition]:
        if service.get_customer(customer_id) is None:
            raise HTTPException(status_code=404, detail="customer not found")
        return service.list_positions(customer_id, account_id=account_id)

    @router.get(
        "/customers/{customer_id}/transactions",
        response_model=list[Transaction],
    )
    def list_transactions(customer_id: str) -> list[Transaction]:
        if service.get_customer(customer_id) is None:
            raise HTTPException(status_code=404, detail="customer not found")
        return service.list_transactions(customer_id)

    @router.get("/customers/{customer_id}/snapshot", response_model=CustomerSnapshot)
    def snapshot(customer_id: str) -> CustomerSnapshot:
        result = service.build_snapshot(customer_id)
        if result is None:
            raise HTTPException(status_code=404, detail="customer not found")
        return result

    @router.post("/bookings")
    def create_booking(req: TradeBookingRequest) -> dict:
        store = service._store
        if not isinstance(store, InMemoryCustodianStore):
            return {"ok": False, "reason": "read-only store"}

        tx_id = str(uuid.uuid4())
        instrument = FinancialInstrument(
            id=str(uuid.uuid4()),
            isin=req.isin,
            name=req.instrument_name,
            type=FinancialInstrumentType(req.instrument_type) if req.instrument_type in [e.value for e in FinancialInstrumentType] else FinancialInstrumentType.OTHER,
            currency=req.instrument_currency,
        )
        account_ref = AccountReference(id=req.account_id, type=AccountType.SAFEKEEPING_ACCOUNT)
        quantity_delta = req.quantity if req.side == "buy" else -req.quantity

        movements = [
            Movement(
                type=MovementType.ASSET,
                financial_instrument=instrument,
                quantity=Quantity(value=req.quantity, unit=QuantityUnit.PIECE),
                price=ValuationPrice(value=req.fill_price, price_type=PriceType.MARKET, currency=req.instrument_currency),
            ),
            Movement(
                type=MovementType.CASH,
                currency=req.fill_currency,
                amount=req.net_amount,
            ),
        ]
        if req.fee > 0:
            movements.append(
                Movement(
                    type=MovementType.BROKERAGE_FEE,
                    currency=req.fill_currency,
                    amount=-req.fee,
                )
            )

        tx = Transaction(
            id=tx_id,
            type=TransactionType.BUY if req.side == "buy" else TransactionType.SELL,
            transaction_date=req.trade_date,
            customer_id=req.customer_id,
            description=f"{'Buy' if req.side == 'buy' else 'Sell'} {req.quantity} {req.instrument_name} @ {req.fill_price} {req.instrument_currency}",
            trade_date=req.trade_date,
            settlement_date=req.settlement_date,
            reference=req.order_id,
            movement_list=movements,
        )
        store.add_transaction(tx)
        store.upsert_position(
            account_id=req.account_id,
            isin=req.isin,
            quantity_delta=quantity_delta,
            fill_price=req.fill_price,
            instrument=instrument,
            account_ref=account_ref,
            position_date=req.trade_date,
        )
        return {"ok": True, "transaction_id": tx_id}

    return router
