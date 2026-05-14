"""Default in-memory fixture data for the simulated custodian provider.

Two customers with realistic portfolios:
  C-1001  Anna Keller         — balanced discretionary mandate (CHF base)
  C-2002  Meyer Family Office — growth advisory mandate (CHF base)
"""

from .schemas import (
    Account,
    AccountReference,
    AccountType,
    CurrencyAmount,
    Customer,
    CustomerSegment,
    CustomerStatus,
    FinancialInstrument,
    FinancialInstrumentType,
    ForeignExchangeRate,
    InvestmentStrategy,
    MandateType,
    Movement,
    MovementType,
    PortfolioInformation,
    PriceType,
    Quantity,
    QuantityUnit,
    Transaction,
    TransactionType,
    Valuation,
    ValuatedPosition,
    ValuationPrice,
)

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

CUSTOMERS = [
    Customer(
        id="C-1001",
        name="Anna Keller",
        status=CustomerStatus.ACTIVE,
        reference_currency="CHF",
        number="700001",
        opening_date="2018-03-15",
        language="de",
        customer_segment=CustomerSegment.PRIVATE_CLIENT,
        bank_advisor="M. Brüggemann",
    ),
    Customer(
        id="C-2002",
        name="Meyer Family Office",
        status=CustomerStatus.ACTIVE,
        reference_currency="CHF",
        number="800002",
        opening_date="2015-11-01",
        language="de",
        customer_segment=CustomerSegment.FAMILY_OFFICE,
        bank_advisor="S. Wirth",
    ),
]

# ---------------------------------------------------------------------------
# Accounts  (no customer_id — tracked via ACCOUNT_OWNER below)
# ---------------------------------------------------------------------------

ACCOUNTS = [
    # C-1001 — safekeeping account for core mandate
    Account(
        id="A-1001-SEC",
        type=AccountType.SAFEKEEPING_ACCOUNT,
        reference_currency="CHF",
        name="Core securities account",
        number="700001.01",
        portfolio_information=PortfolioInformation(
            identification="PF-1001-CORE",
            name="Core discretionary mandate",
            reference_currency="CHF",
            mandate_type=MandateType.DISCRETIONARY,
            strategy=InvestmentStrategy.BALANCED,
            inception_date="2018-03-15",
        ),
    ),
    # C-1001 — cash account for liquidity reserve
    Account(
        id="A-1001-CASH",
        type=AccountType.CASH_ACCOUNT,
        reference_currency="CHF",
        name="Liquidity reserve",
        number="700001.03",
        iban="CH9300762011623852957",
        portfolio_information=PortfolioInformation(
            identification="PF-1001-LIQ",
            name="Liquidity reserve",
            reference_currency="CHF",
            mandate_type=MandateType.ADVISORY,
            strategy=InvestmentStrategy.CAPITAL_PRESERVATION,
            inception_date="2018-03-15",
        ),
    ),
    # C-2002 — safekeeping account for growth portfolio
    Account(
        id="A-2002-SEC",
        type=AccountType.SAFEKEEPING_ACCOUNT,
        reference_currency="CHF",
        name="Global growth securities",
        number="800002.01",
        portfolio_information=PortfolioInformation(
            identification="PF-2002-GROWTH",
            name="Global growth portfolio",
            reference_currency="CHF",
            mandate_type=MandateType.ADVISORY,
            strategy=InvestmentStrategy.CAPITAL_GROWTH,
            inception_date="2015-11-01",
        ),
    ),
    # C-2002 — cash account
    Account(
        id="A-2002-CASH",
        type=AccountType.CASH_ACCOUNT,
        reference_currency="CHF",
        name="Operating cash",
        number="800002.02",
        portfolio_information=PortfolioInformation(
            identification="PF-2002-GROWTH",
            name="Global growth portfolio",
            reference_currency="CHF",
            mandate_type=MandateType.ADVISORY,
            strategy=InvestmentStrategy.CAPITAL_GROWTH,
            inception_date="2015-11-01",
        ),
    ),
]

# Associates account_id → customer_id (OpenWealth Account has no customer_id field)
ACCOUNT_OWNER: dict[str, str] = {
    "A-1001-SEC": "C-1001",
    "A-1001-CASH": "C-1001",
    "A-2002-SEC": "C-2002",
    "A-2002-CASH": "C-2002",
}

# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

_DATE = "2026-05-14"

POSITIONS = [
    # ---- C-1001 liquidity ----
    ValuatedPosition(
        id="POS-1001-CASH-CHF",
        currency="CHF",
        position_date=_DATE,
        financial_instrument=FinancialInstrument(
            id="CASH-CHF",
            name="Swiss franc cash",
            type=FinancialInstrumentType.CASH,
            currency="CHF",
            country="CH",
        ),
        account=AccountReference(id="A-1001-CASH", type=AccountType.CASH_ACCOUNT),
        quantity=Quantity(value=85_000, unit=QuantityUnit.NOMINAL),
        valuation=Valuation(
            total_value=85_000,
            currency="CHF",
            base_value=85_000,
            base_currency="CHF",
        ),
        price=ValuationPrice(value=1.0, price_type=PriceType.MARKET, currency="CHF"),
        weight=0.106,
    ),
    # ---- C-1001 core mandate ----
    ValuatedPosition(
        id="POS-1001-CHSPI",
        currency="CHF",
        safekeeping_place="SIX SIS",
        position_date=_DATE,
        financial_instrument=FinancialInstrument(
            id="CHSPI",
            isin="CH0237935652",
            name="iShares Core SPI ETF",
            type=FinancialInstrumentType.FUND,
            currency="CHF",
            country="CH",
            sector="broad_market",
        ),
        account=AccountReference(id="A-1001-SEC", type=AccountType.SAFEKEEPING_ACCOUNT),
        quantity=Quantity(value=940, unit=QuantityUnit.PIECE),
        valuation=Valuation(
            total_value=143_256,
            currency="CHF",
            base_value=143_256,
            base_currency="CHF",
        ),
        price=ValuationPrice(value=152.4, price_type=PriceType.MARKET, currency="CHF"),
        weight=0.179,
    ),
    ValuatedPosition(
        id="POS-1001-WRLD",
        currency="USD",
        safekeeping_place="Clearstream",
        position_date=_DATE,
        financial_instrument=FinancialInstrument(
            id="WRLD",
            isin="IE00B4L5Y983",
            name="iShares Core MSCI World UCITS ETF",
            type=FinancialInstrumentType.FUND,
            currency="USD",
            country="IE",
            sector="global_equity",
        ),
        account=AccountReference(id="A-1001-SEC", type=AccountType.SAFEKEEPING_ACCOUNT),
        quantity=Quantity(value=2_350, unit=QuantityUnit.PIECE),
        valuation=Valuation(
            total_value=276_947.5,
            currency="USD",
            base_value=252_022.23,
            base_currency="CHF",
        ),
        price=ValuationPrice(value=117.85, price_type=PriceType.MARKET, currency="USD"),
        foreign_exchange_rate=ForeignExchangeRate(
            base_rate=0.91,
            inverted_rate=1.0989,
            base_currency="CHF",
        ),
        weight=0.315,
    ),
    ValuatedPosition(
        id="POS-1001-BOND",
        currency="CHF",
        safekeeping_place="SIX SIS",
        position_date=_DATE,
        financial_instrument=FinancialInstrument(
            id="CHGOV-2034",
            isin="CH0557778319",
            name="Swiss Confederation Bond 0.5% 2034",
            type=FinancialInstrumentType.BOND,
            currency="CHF",
            country="CH",
            sector="government",
        ),
        account=AccountReference(id="A-1001-SEC", type=AccountType.SAFEKEEPING_ACCOUNT),
        quantity=Quantity(value=220_000, unit=QuantityUnit.NOMINAL),
        valuation=Valuation(
            total_value=211_640,
            currency="CHF",
            base_value=212_252,
            base_currency="CHF",
        ),
        price=ValuationPrice(value=96.2, price_type=PriceType.MARKET, currency="CHF"),
        accrued_interest=CurrencyAmount(value=612, currency="CHF"),
        number_of_days_accrued=45,
        weight=0.265,
    ),
    ValuatedPosition(
        id="POS-1001-SPS",
        currency="CHF",
        safekeeping_place="SIX SIS",
        position_date=_DATE,
        financial_instrument=FinancialInstrument(
            id="SPSN",
            isin="CH0031069328",
            name="Swiss Prime Site AG",
            type=FinancialInstrumentType.EQUITY,
            currency="CHF",
            country="CH",
            sector="real_estate",
        ),
        account=AccountReference(id="A-1001-SEC", type=AccountType.SAFEKEEPING_ACCOUNT),
        quantity=Quantity(value=1_080, unit=QuantityUnit.PIECE),
        valuation=Valuation(
            total_value=107_784,
            currency="CHF",
            base_value=107_784,
            base_currency="CHF",
        ),
        price=ValuationPrice(value=99.8, price_type=PriceType.MARKET, currency="CHF"),
        weight=0.135,
    ),
    # ---- C-2002 growth portfolio ----
    ValuatedPosition(
        id="POS-2002-CASH-CHF",
        currency="CHF",
        position_date=_DATE,
        financial_instrument=FinancialInstrument(
            id="CASH-CHF",
            name="Swiss franc cash",
            type=FinancialInstrumentType.CASH,
            currency="CHF",
            country="CH",
        ),
        account=AccountReference(id="A-2002-CASH", type=AccountType.CASH_ACCOUNT),
        quantity=Quantity(value=150_000, unit=QuantityUnit.NOMINAL),
        valuation=Valuation(
            total_value=150_000,
            currency="CHF",
            base_value=150_000,
            base_currency="CHF",
        ),
        price=ValuationPrice(value=1.0, price_type=PriceType.MARKET, currency="CHF"),
        weight=0.12,
    ),
    ValuatedPosition(
        id="POS-2002-WRLD",
        currency="USD",
        safekeeping_place="Clearstream",
        position_date=_DATE,
        financial_instrument=FinancialInstrument(
            id="WRLD",
            isin="IE00B4L5Y983",
            name="iShares Core MSCI World UCITS ETF",
            type=FinancialInstrumentType.FUND,
            currency="USD",
            country="IE",
            sector="global_equity",
        ),
        account=AccountReference(id="A-2002-SEC", type=AccountType.SAFEKEEPING_ACCOUNT),
        quantity=Quantity(value=7_200, unit=QuantityUnit.PIECE),
        valuation=Valuation(
            total_value=848_520,
            currency="USD",
            base_value=772_153.2,
            base_currency="CHF",
        ),
        price=ValuationPrice(value=117.85, price_type=PriceType.MARKET, currency="USD"),
        foreign_exchange_rate=ForeignExchangeRate(
            base_rate=0.91,
            inverted_rate=1.0989,
            base_currency="CHF",
        ),
        weight=0.64,
    ),
    ValuatedPosition(
        id="POS-2002-NVDA",
        currency="USD",
        safekeeping_place="Clearstream",
        position_date=_DATE,
        financial_instrument=FinancialInstrument(
            id="NVDA",
            isin="US67066G1040",
            name="NVIDIA Corp",
            type=FinancialInstrumentType.EQUITY,
            currency="USD",
            country="US",
            sector="technology",
        ),
        account=AccountReference(id="A-2002-SEC", type=AccountType.SAFEKEEPING_ACCOUNT),
        quantity=Quantity(value=1_200, unit=QuantityUnit.PIECE),
        valuation=Valuation(
            total_value=158_460,
            currency="USD",
            base_value=144_198.6,
            base_currency="CHF",
        ),
        price=ValuationPrice(value=132.05, price_type=PriceType.MARKET, currency="USD"),
        foreign_exchange_rate=ForeignExchangeRate(
            base_rate=0.91,
            inverted_rate=1.0989,
            base_currency="CHF",
        ),
        weight=0.12,
    ),
    ValuatedPosition(
        id="POS-2002-AAPL",
        currency="USD",
        safekeeping_place="Clearstream",
        position_date=_DATE,
        financial_instrument=FinancialInstrument(
            id="AAPL",
            isin="US0378331005",
            name="Apple Inc",
            type=FinancialInstrumentType.EQUITY,
            currency="USD",
            country="US",
            sector="technology",
        ),
        account=AccountReference(id="A-2002-SEC", type=AccountType.SAFEKEEPING_ACCOUNT),
        quantity=Quantity(value=800, unit=QuantityUnit.PIECE),
        valuation=Valuation(
            total_value=153_680,
            currency="USD",
            base_value=139_848.8,
            base_currency="CHF",
        ),
        price=ValuationPrice(value=192.1, price_type=PriceType.MARKET, currency="USD"),
        foreign_exchange_rate=ForeignExchangeRate(
            base_rate=0.91,
            inverted_rate=1.0989,
            base_currency="CHF",
        ),
        weight=0.12,
    ),
]

# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

TRANSACTIONS = [
    # C-1001 — buy MSCI World ETF
    Transaction(
        id="TX-1001-001",
        type=TransactionType.BUY,
        transaction_date="2026-05-10",
        customer_id="C-1001",
        description="Purchase iShares MSCI World UCITS ETF",
        trade_date="2026-05-10",
        settlement_date="2026-05-12",
        value_date="2026-05-12",
        movement_list=[
            Movement(
                type=MovementType.ASSET,
                financial_instrument=FinancialInstrument(
                    id="WRLD",
                    isin="IE00B4L5Y983",
                    name="iShares Core MSCI World UCITS ETF",
                    type=FinancialInstrumentType.FUND,
                    currency="USD",
                ),
                quantity=Quantity(value=500, unit=QuantityUnit.PIECE),
                price=ValuationPrice(value=113.92, price_type=PriceType.MARKET, currency="USD"),
            ),
            Movement(
                type=MovementType.CASH,
                currency="CHF",
                amount=-54_418.0,
            ),
            Movement(
                type=MovementType.BROKERAGE_FEE,
                currency="CHF",
                amount=-54.42,
            ),
        ],
    ),
    # C-1001 — bond coupon
    Transaction(
        id="TX-1001-002",
        type=TransactionType.COUPON,
        transaction_date="2026-05-12",
        customer_id="C-1001",
        description="Bond coupon payment — Swiss Confederation 0.5% 2034",
        value_date="2026-05-14",
        movement_list=[
            Movement(
                type=MovementType.INTEREST,
                currency="CHF",
                amount=550.0,
            ),
            Movement(
                type=MovementType.WITHHOLDING_TAX,
                currency="CHF",
                amount=-82.5,
            ),
        ],
    ),
    # C-1001 — cash inflow
    Transaction(
        id="TX-1001-003",
        type=TransactionType.INFLOW_CASH,
        transaction_date="2026-05-13",
        customer_id="C-1001",
        description="Client cash deposit",
        value_date="2026-05-13",
        movement_list=[
            Movement(
                type=MovementType.CASH,
                currency="CHF",
                amount=25_000.0,
            ),
        ],
    ),
    # C-1001 — dividend
    Transaction(
        id="TX-1001-004",
        type=TransactionType.DIVIDEND_CASH,
        transaction_date="2026-04-15",
        customer_id="C-1001",
        description="Dividend — iShares Core SPI ETF",
        value_date="2026-04-17",
        movement_list=[
            Movement(
                type=MovementType.CASH,
                currency="CHF",
                amount=1_410.0,
            ),
            Movement(
                type=MovementType.WITHHOLDING_TAX,
                currency="CHF",
                amount=-211.5,
            ),
        ],
    ),
    # C-2002 — buy NVIDIA
    Transaction(
        id="TX-2002-001",
        type=TransactionType.BUY,
        transaction_date="2026-05-08",
        customer_id="C-2002",
        description="Purchase NVIDIA Corp",
        trade_date="2026-05-08",
        settlement_date="2026-05-10",
        value_date="2026-05-10",
        movement_list=[
            Movement(
                type=MovementType.ASSET,
                financial_instrument=FinancialInstrument(
                    id="NVDA",
                    isin="US67066G1040",
                    name="NVIDIA Corp",
                    type=FinancialInstrumentType.EQUITY,
                    currency="USD",
                ),
                quantity=Quantity(value=1_200, unit=QuantityUnit.PIECE),
                price=ValuationPrice(value=128.0, price_type=PriceType.MARKET, currency="USD"),
            ),
            Movement(
                type=MovementType.CASH,
                currency="CHF",
                amount=-139_776.0,
            ),
            Movement(
                type=MovementType.BROKERAGE_FEE,
                currency="CHF",
                amount=-139.78,
            ),
        ],
    ),
    # C-2002 — cash inflow
    Transaction(
        id="TX-2002-002",
        type=TransactionType.INFLOW_CASH,
        transaction_date="2026-05-01",
        customer_id="C-2002",
        description="Client cash deposit",
        value_date="2026-05-01",
        movement_list=[
            Movement(
                type=MovementType.CASH,
                currency="CHF",
                amount=200_000.0,
            ),
        ],
    ),
]
