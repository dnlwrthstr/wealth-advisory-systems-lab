"""Data access layer for custodian data."""

import json
import threading
import uuid
from datetime import date
from typing import Protocol

from .schemas import (
    Account,
    AccountReference,
    AccountType,
    AssetAllocation,
    Customer,
    FinancialInstrument,
    FinancialInstrumentType,
    ForeignExchangeRate,
    Movement,
    MovementType,
    PortfolioInformation,
    Quantity,
    QuantityUnit,
    Transaction,
    TransactionType,
    Valuation,
    ValuatedPosition,
    ValuationPrice,
    PriceType,
    CurrencyAmount,
)


class CustodianStore(Protocol):
    def list_customers(self) -> list[Customer]: ...
    def list_accounts(self, customer_id: str) -> list[Account]: ...
    def list_positions(
        self, customer_id: str, account_id: str | None = None
    ) -> list[ValuatedPosition]: ...
    def list_transactions(self, customer_id: str) -> list[Transaction]: ...


class InMemoryCustodianStore:
    """In-memory store backed by fixture data lists — used in tests and notebooks.

    account_owner maps account_id → customer_id because OpenWealth Account has no
    customer_id field; the association is tracked separately.
    """

    def __init__(
        self,
        customers: list[Customer],
        accounts: list[Account],
        positions: list[ValuatedPosition],
        transactions: list[Transaction],
        account_owner: dict[str, str],
    ) -> None:
        self._customers = {c.id: c for c in customers}
        self._accounts = accounts
        self._positions = list(positions)
        self._transactions = list(transactions)
        self._account_owner = account_owner
        self._lock = threading.Lock()
        self._avg_cost: dict[tuple[str, str], float] = {}  # (account_id, isin) → weighted avg price

    def list_customers(self) -> list[Customer]:
        return list(self._customers.values())

    def list_accounts(self, customer_id: str) -> list[Account]:
        owned = {aid for aid, cid in self._account_owner.items() if cid == customer_id}
        return [a for a in self._accounts if a.id in owned]

    def list_positions(
        self,
        customer_id: str,
        account_id: str | None = None,
    ) -> list[ValuatedPosition]:
        owned = {aid for aid, cid in self._account_owner.items() if cid == customer_id}
        positions = [p for p in self._positions if p.account.id in owned]
        if account_id is not None:
            positions = [p for p in positions if p.account.id == account_id]
        return positions

    def list_transactions(self, customer_id: str) -> list[Transaction]:
        return [t for t in self._transactions if t.customer_id == customer_id]

    def add_transaction(self, tx: Transaction) -> None:
        with self._lock:
            self._transactions.append(tx)

    def upsert_position(
        self,
        account_id: str,
        isin: str,
        quantity_delta: float,
        fill_price: float,
        instrument: FinancialInstrument,
        account_ref: AccountReference,
        position_date: str,
    ) -> ValuatedPosition:
        with self._lock:
            key = (account_id, isin)
            existing = next(
                (p for p in self._positions if p.account.id == account_id and p.financial_instrument.isin == isin),
                None,
            )
            if existing is not None:
                old_qty = existing.quantity.value
                old_avg = self._avg_cost.get(key, fill_price)
                new_qty = old_qty + quantity_delta
                if new_qty <= 0:
                    self._positions = [p for p in self._positions if not (p.account.id == account_id and p.financial_instrument.isin == isin)]
                    self._avg_cost.pop(key, None)
                    return existing
                new_avg = (old_qty * old_avg + quantity_delta * fill_price) / new_qty if quantity_delta > 0 else old_avg
                self._avg_cost[key] = new_avg
                existing.quantity.value = new_qty
                existing.valuation.total_value = round(new_qty * fill_price, 4)
                existing.position_date = position_date
                return existing
            else:
                self._avg_cost[key] = fill_price
                pos = ValuatedPosition(
                    id=str(uuid.uuid4()),
                    name=instrument.name,
                    currency=instrument.currency,
                    position_date=position_date,
                    end_of_day_indicator=False,
                    financial_instrument=instrument,
                    account=account_ref,
                    quantity=Quantity(value=quantity_delta, unit=QuantityUnit.PIECE),
                    valuation=Valuation(
                        total_value=round(quantity_delta * fill_price, 4),
                        currency=instrument.currency,
                    ),
                )
                self._positions.append(pos)
                return pos


def _v(val):
    """Return val, converting any pandas null (NaN, NA, NaT) to None."""
    try:
        import pandas as pd
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


class DuckDBCustodianStore:
    """Read-only store backed by Parquet files queried via DuckDB.

    Expected files under data_path/:
      customers.parquet, accounts.parquet, positions.parquet, transactions.parquet
    """

    def __init__(self, data_path: str) -> None:
        self.data_path = data_path.rstrip("/")

    def _connect(self):
        try:
            import duckdb
        except ModuleNotFoundError as exc:
            raise RuntimeError("duckdb is required for DuckDBCustodianStore") from exc
        return duckdb.connect(":memory:")

    def list_customers(self) -> list[Customer]:
        con = self._connect()
        rows = con.execute(
            f"SELECT * FROM read_parquet('{self.data_path}/customers.parquet')"
        ).fetchdf()
        con.close()
        return [
            Customer(
                id=row["id"],
                name=row["name"],
                status=row["status"],
                reference_currency=row["reference_currency"],
                number=_v(row.get("number")),
                opening_date=_v(row.get("opening_date")),
                language=_v(row.get("language")),
                customer_segment=_v(row.get("customer_segment")),
                bank_advisor=_v(row.get("bank_advisor")),
                bank_deputy_advisor=_v(row.get("bank_deputy_advisor")),
            )
            for _, row in rows.iterrows()
        ]

    def list_accounts(self, customer_id: str) -> list[Account]:
        con = self._connect()
        rows = con.execute(
            f"SELECT * FROM read_parquet('{self.data_path}/accounts.parquet')"
            f" WHERE customer_id = '{customer_id}'"
        ).fetchdf()
        con.close()
        result = []
        for _, row in rows.iterrows():
            pi = None
            pid = _v(row.get("portfolio_id"))
            if pid:
                pi = PortfolioInformation(
                    identification=pid,
                    name=_v(row.get("portfolio_name")),
                    reference_currency=_v(row.get("portfolio_reference_currency")),
                    mandate_type=_v(row.get("portfolio_mandate_type")),
                    strategy=_v(row.get("portfolio_strategy")),
                    inception_date=_v(row.get("portfolio_inception_date")),
                )
            result.append(
                Account(
                    id=row["id"],
                    type=AccountType(row["type"]),
                    reference_currency=row["reference_currency"],
                    name=_v(row.get("name")),
                    iban=_v(row.get("iban")),
                    number=_v(row.get("number")),
                    designation=_v(row.get("designation")),
                    portfolio_information=pi,
                )
            )
        return result

    def list_positions(
        self, customer_id: str, account_id: str | None = None
    ) -> list[ValuatedPosition]:
        con = self._connect()
        where = f"WHERE customer_id = '{customer_id}'"
        if account_id:
            where += f" AND account_id = '{account_id}'"
        rows = con.execute(
            f"SELECT * FROM read_parquet('{self.data_path}/positions.parquet') {where}"
        ).fetchdf()
        con.close()
        result = []
        for _, row in rows.iterrows():
            instrument = FinancialInstrument(
                id=row["instrument_id"],
                isin=_v(row.get("instrument_isin")),
                name=row["instrument_name"],
                type=FinancialInstrumentType(row["instrument_type"]),
                currency=row["instrument_currency"],
                country=_v(row.get("instrument_country")),
                sector=_v(row.get("instrument_sector")),
            )
            quantity = Quantity(
                value=float(row["quantity_value"]),
                unit=QuantityUnit(_v(row.get("quantity_unit")) or "piece"),
            )
            valuation = Valuation(
                total_value=float(row["total_value"]),
                currency=row["valuation_currency"],
                base_value=float(row["base_value"]) if _v(row.get("base_value")) is not None else None,
                base_currency=_v(row.get("base_currency")),
            )
            price = None
            if _v(row.get("price_value")) is not None:
                price = ValuationPrice(
                    value=float(row["price_value"]),
                    price_type=PriceType(_v(row.get("price_type")) or "market"),
                    currency=row["price_currency"],
                    source=_v(row.get("price_source")),
                )
            fx = None
            if _v(row.get("fx_base_rate")) is not None:
                fx = ForeignExchangeRate(
                    base_rate=float(row["fx_base_rate"]),
                    inverted_rate=float(row["fx_inverted_rate"]) if _v(row.get("fx_inverted_rate")) else None,
                    base_currency=row["fx_base_currency"],
                )
            accrued = None
            if _v(row.get("accrued_interest_value")) is not None:
                accrued = CurrencyAmount(
                    value=float(row["accrued_interest_value"]),
                    currency=row["accrued_interest_currency"],
                )
            result.append(
                ValuatedPosition(
                    id=row["id"],
                    name=_v(row.get("name")),
                    currency=row["currency"],
                    safekeeping_place=_v(row.get("safekeeping_place")),
                    position_date=str(row["position_date"]),
                    end_of_day_indicator=bool(row.get("end_of_day_indicator", True)),
                    financial_instrument=instrument,
                    account=AccountReference(
                        id=row["account_id"],
                        type=AccountType(row["account_type"]),
                    ),
                    quantity=quantity,
                    valuation=valuation,
                    price=price,
                    foreign_exchange_rate=fx,
                    accrued_interest=accrued,
                    weight=float(row["weight"]) if _v(row.get("weight")) is not None else None,
                )
            )
        return result

    def list_transactions(self, customer_id: str) -> list[Transaction]:
        con = self._connect()
        rows = con.execute(
            f"SELECT * FROM read_parquet('{self.data_path}/transactions.parquet')"
            f" WHERE customer_id = '{customer_id}' ORDER BY transaction_date"
        ).fetchdf()
        con.close()
        result = []
        for _, row in rows.iterrows():
            movements_raw = _v(row.get("movements_json")) or "[]"
            movements = []
            for m in json.loads(movements_raw):
                fi = None
                if m.get("instrument_id"):
                    fi = FinancialInstrument(
                        id=m["instrument_id"],
                        isin=m.get("instrument_isin"),
                        name=m.get("instrument_name", ""),
                        type=FinancialInstrumentType(m["instrument_type"]),
                        currency=m.get("instrument_currency", "CHF"),
                    )
                qty = None
                if m.get("quantity_value") is not None:
                    qty = Quantity(
                        value=float(m["quantity_value"]),
                        unit=QuantityUnit(m.get("quantity_unit", "piece")),
                    )
                mvt_price = None
                if m.get("price_value") is not None:
                    mvt_price = ValuationPrice(
                        value=float(m["price_value"]),
                        price_type=PriceType(m.get("price_type", "market")),
                        currency=m["price_currency"],
                    )
                movements.append(
                    Movement(
                        type=MovementType(m["type"]),
                        financial_instrument=fi,
                        quantity=qty,
                        price=mvt_price,
                        currency=m.get("currency"),
                        amount=float(m["amount"]) if m.get("amount") is not None else None,
                    )
                )
            result.append(
                Transaction(
                    id=row["id"],
                    type=TransactionType(row["type"]),
                    transaction_date=str(row["transaction_date"]),
                    customer_id=row["customer_id"],
                    reversal_indicator=bool(row.get("reversal_indicator", False)),
                    end_of_day_indicator=bool(row.get("end_of_day_indicator", True)),
                    reference=_v(row.get("reference")),
                    description=str(row["description"]),
                    trade_date=str(row["trade_date"]) if _v(row.get("trade_date")) else None,
                    settlement_date=str(row["settlement_date"]) if _v(row.get("settlement_date")) else None,
                    value_date=str(row["value_date"]) if _v(row.get("value_date")) else None,
                    movement_list=movements,
                )
            )
        return result


class PostgresCustodianStore:
    """Postgres-backed store — kept for completeness; use DuckDBCustodianStore for analytics."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
            return psycopg.connect(self.database_url, row_factory=dict_row)
        except ModuleNotFoundError as exc:
            raise RuntimeError("psycopg is required for PostgresCustodianStore") from exc

    def list_customers(self) -> list[Customer]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM custodian.custody_customer")
                rows = cur.fetchall()
        return [
            Customer(
                id=r["customer_id"],
                name=r["display_name"],
                status=r.get("status", "active"),
                reference_currency=r.get("reference_currency", "CHF"),
                customer_segment=r.get("segment"),
            )
            for r in rows
        ]

    def list_accounts(self, customer_id: str) -> list[Account]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT a.*, p.name AS portfolio_name, p.base_currency AS portfolio_currency,"
                    " p.mandate_type, p.strategy FROM custodian.custody_account a"
                    " LEFT JOIN custodian.custody_portfolio p USING (portfolio_id)"
                    " WHERE a.customer_id = %(cid)s",
                    {"cid": customer_id},
                )
                rows = cur.fetchall()
        result = []
        for r in rows:
            pi = None
            if r.get("portfolio_id"):
                pi = PortfolioInformation(
                    identification=r["portfolio_id"],
                    name=r.get("portfolio_name"),
                    reference_currency=r.get("portfolio_currency"),
                    mandate_type=r.get("mandate_type"),
                    strategy=r.get("strategy"),
                )
            result.append(
                Account(
                    id=r["account_id"],
                    type=AccountType(r["account_type"]),
                    reference_currency=r["currency"],
                    iban=r.get("iban"),
                    number=r.get("account_number"),
                    portfolio_information=pi,
                )
            )
        return result

    def list_positions(
        self, customer_id: str, account_id: str | None = None
    ) -> list[ValuatedPosition]:
        query = "SELECT * FROM custodian.custody_position WHERE customer_id = %(cid)s"
        params: dict = {"cid": customer_id}
        if account_id:
            query += " AND account_id = %(aid)s"
            params["aid"] = account_id
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        result = []
        for r in rows:
            result.append(
                ValuatedPosition(
                    id=r["position_id"],
                    currency=r["valuation_currency"],
                    safekeeping_place=r.get("safekeeping_place"),
                    position_date=str(r["valuation_date"]),
                    financial_instrument=FinancialInstrument(
                        id=r["instrument_id"],
                        isin=r.get("isin"),
                        name=r["instrument_name"],
                        type=FinancialInstrumentType(r["instrument_type"]),
                        currency=r["instrument_currency"],
                        country=r.get("instrument_country"),
                        sector=r.get("instrument_sector"),
                    ),
                    account=AccountReference(
                        id=r["account_id"],
                        type=AccountType(r.get("account_type", "safekeeping_account")),
                    ),
                    quantity=Quantity(value=float(r["quantity"])),
                    valuation=Valuation(
                        total_value=float(r["market_value"]),
                        currency=r["valuation_currency"],
                        base_value=float(r["base_market_value"]) if r.get("base_market_value") else None,
                        base_currency=r.get("base_currency"),
                    ),
                    price=ValuationPrice(
                        value=float(r["price"]),
                        currency=r["instrument_currency"],
                    ) if r.get("price") else None,
                    weight=float(r["weight"]) if r.get("weight") else None,
                )
            )
        return result

    def list_transactions(self, customer_id: str) -> list[Transaction]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM custodian.custody_transaction WHERE customer_id = %(cid)s",
                    {"cid": customer_id},
                )
                rows = cur.fetchall()
        result = []
        for r in rows:
            movements = []
            if r.get("amount") is not None:
                movements.append(
                    Movement(
                        type=MovementType.CASH,
                        currency=r.get("currency"),
                        amount=float(r["amount"]),
                    )
                )
            if r.get("quantity") is not None and r.get("instrument_id"):
                movements.append(
                    Movement(
                        type=MovementType.ASSET,
                        financial_instrument=FinancialInstrument(
                            id=r["instrument_id"],
                            name=r.get("description", ""),
                            type=FinancialInstrumentType.OTHER,
                            currency=r.get("currency", "CHF"),
                        ),
                        quantity=Quantity(value=float(r["quantity"])),
                    )
                )
            result.append(
                Transaction(
                    id=r["transaction_id"],
                    type=TransactionType(r["transaction_type"]),
                    transaction_date=str(r["booking_date"]),
                    customer_id=r["customer_id"],
                    description=r.get("description", ""),
                    value_date=str(r["value_date"]) if r.get("value_date") else None,
                    movement_list=movements,
                )
            )
        return result
