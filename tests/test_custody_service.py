from custodian.data import ACCOUNT_OWNER, ACCOUNTS, CUSTOMERS, POSITIONS, TRANSACTIONS
from custodian.schemas import FinancialInstrumentType
from custodian.service import CustodianService
from custodian.store import InMemoryCustodianStore


def _service() -> CustodianService:
    return CustodianService(
        InMemoryCustodianStore(CUSTOMERS, ACCOUNTS, POSITIONS, TRANSACTIONS, ACCOUNT_OWNER)
    )


def test_snapshot_aggregates_customer_positions():
    snapshot = _service().build_snapshot("C-1001")

    assert snapshot is not None
    assert snapshot.customer.id == "C-1001"
    assert snapshot.total_market_value == 800_314.23
    assert {item.instrument_type for item in snapshot.asset_allocation} == {
        FinancialInstrumentType.BOND,
        FinancialInstrumentType.CASH,
        FinancialInstrumentType.EQUITY,
        FinancialInstrumentType.FUND,
    }


def test_account_filter_limits_positions():
    positions = _service().list_positions("C-1001", account_id="A-1001-CASH")

    assert [p.id for p in positions] == ["POS-1001-CASH-CHF"]


def test_accounts_are_customer_scoped():
    accounts = _service().list_accounts("C-1001")

    account_ids = {a.id for a in accounts}
    assert account_ids == {"A-1001-SEC", "A-1001-CASH"}

    portfolio_ids = {
        a.portfolio_information.identification
        for a in accounts
        if a.portfolio_information
    }
    assert portfolio_ids == {"PF-1001-CORE", "PF-1001-LIQ"}


def test_unknown_customer_returns_none():
    assert _service().get_customer("C-9999") is None
    assert _service().build_snapshot("C-9999") is None
