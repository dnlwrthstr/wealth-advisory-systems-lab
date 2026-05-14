"""CustodianService — use-case facade over a CustodianStore."""

from collections import defaultdict

from .schemas import (
    Account,
    AssetAllocation,
    Customer,
    CustomerSnapshot,
    FinancialInstrumentType,
    Transaction,
    ValuatedPosition,
)
from .store import CustodianStore


class CustodianService:
    def __init__(self, store: CustodianStore) -> None:
        self._store = store

    def list_customers(self) -> list[Customer]:
        return self._store.list_customers()

    def get_customer(self, customer_id: str) -> Customer | None:
        return next(
            (c for c in self._store.list_customers() if c.id == customer_id),
            None,
        )

    def list_accounts(self, customer_id: str) -> list[Account]:
        return self._store.list_accounts(customer_id)

    def list_positions(self, customer_id: str, account_id: str | None = None) -> list[ValuatedPosition]:
        return self._store.list_positions(customer_id, account_id=account_id)

    def list_transactions(self, customer_id: str) -> list[Transaction]:
        return self._store.list_transactions(customer_id)

    def build_snapshot(self, customer_id: str) -> CustomerSnapshot | None:
        customer = self.get_customer(customer_id)
        if customer is None:
            return None

        accounts = self._store.list_accounts(customer_id)
        positions = self._store.list_positions(customer_id)
        transactions = self._store.list_transactions(customer_id)

        base_currency = customer.reference_currency

        allocations: dict[FinancialInstrumentType, float] = defaultdict(float)
        total = 0.0
        for p in positions:
            base_val = (
                p.valuation.base_value
                if p.valuation.base_value is not None
                else p.valuation.total_value
            )
            total += base_val
            allocations[p.financial_instrument.type] += base_val

        total = round(total, 2)

        portfolios = [
            a.portfolio_information
            for a in accounts
            if a.portfolio_information is not None
        ]

        asset_allocation = [
            AssetAllocation(
                instrument_type=itype,
                label=itype.value,
                market_value=round(mv, 2),
                weight=round(mv / total, 4) if total else 0.0,
            )
            for itype, mv in sorted(allocations.items(), key=lambda x: x[0].value)
        ]

        return CustomerSnapshot(
            customer=customer,
            portfolios=portfolios,
            accounts=accounts,
            positions=positions,
            transactions=transactions,
            total_market_value=total,
            base_currency=base_currency,
            asset_allocation=asset_allocation,
        )
