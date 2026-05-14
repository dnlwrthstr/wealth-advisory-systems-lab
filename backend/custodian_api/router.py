"""HTTP routes for the custodian API — OpenWealth-compliant endpoints."""

from custodian.reference import build_reference
from custodian.schemas import (
    Account,
    Customer,
    CustomerSnapshot,
    Transaction,
    ValuatedPosition,
)
from custodian.service import CustodianService
from fastapi import APIRouter, HTTPException

_REFERENCE = build_reference()


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

    return router
