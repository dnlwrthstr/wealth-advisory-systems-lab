"""OpenWealth-compliant Pydantic schemas for custody services.

All API-facing models use camelCase aliases (via alias_generator=to_camel).
Internal code may use snake_case field names with populate_by_name=True.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class OpenWealthBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class FinancialInstrumentType(str, Enum):
    CASH = "cash"
    BOND = "bond"
    EQUITY = "equity"
    FUND = "fund"  # includes ETFs in OpenWealth
    INDEX = "index"
    COMMODITY = "commodity"
    OPTION = "option"
    FUTURE = "future"
    FX_FORWARD = "fx_forward"
    FX_SWAP = "fx_swap"
    FX_OPTION = "fx_option"
    PRECIOUS_METAL = "precious_metal"
    REAL_ESTATE = "real_estate"
    CRYPTO_ASSET = "crypto_asset"
    ALTERNATIVE = "alternative"
    OTHER = "other"


class TransactionType(str, Enum):
    ACCUMULATION = "accumulation"
    ADDITIONAL_PAYMENT = "additional_payment"
    ADJUST_NOTIONAL = "adjust_notional"
    BONUS = "bonus"
    BUY = "buy"
    BUY_TO_CLOSE = "buy_to_close"
    CAPITAL_INCREASE = "capital_increase"
    CLOSE_CONTRACT = "close_contract"
    COUPON = "coupon"
    CREDIT_EVENT = "credit_event"
    DECREASE_PRINCIPAL = "decrease_principal"
    DELIVERY_FREE_OF_PAYMENT = "delivery_free_of_payment"
    DELIVERY_VS_PAYMENT = "delivery_vs_payment"
    DIVIDEND_CASH = "dividend_cash"
    DIVIDEND_CHOICE = "dividend_choice"
    DIVIDEND_REINVESTMENT = "dividend_reinvestment"
    DIVIDEND_STOCK = "dividend_stock"
    EXERCISE = "exercise"
    EXPIRATION = "expiration"
    FEES = "fees"
    FINAL_LIQUIDATION_PAYMENT = "final_liquidation_payment"
    FX_SPOT = "fx_spot"
    INCREASE_PRINCIPAL = "increase_principal"
    INFLOW_CASH = "inflow_cash"
    INSTRUMENT_EXCHANGE = "instrument_exchange"
    INTEREST_PAYMENT = "interest_payment"
    INTERNAL_TRANSFER = "internal_transfer"
    LIQUIDATION_PAYMENT = "liquidation_payment"
    MERGER = "merger"
    OPEN_CONTRACT = "open_contract"
    OTHER = "other"
    OUTFLOW_CASH = "outflow_cash"
    PREMIUM = "premium"
    PREPAYMENT_SUBSTITUTION = "prepayment_substitution"
    RECEIVE_FREE_OF_PAYMENT = "receive_free_of_payment"
    RECEIVE_VS_PAYMENT = "receive_vs_payment"
    REDEMPTION = "redemption"
    REDEMPTION_PARTIAL = "redemption_partial"
    REDEMPTION_PRIOR = "redemption_prior"
    REDUCTION_OF_NOMINAL = "reduction_of_nominal"
    RESET_PAYMENT = "reset_payment"
    RIGHT_DISTRIBUTION = "right_distribution"
    SELL = "sell"
    SELL_TO_OPEN = "sell_to_open"
    SPIN_OFF = "spin_off"
    STOCK_SPLIT = "stock_split"
    SUBSCRIPTION = "subscription"
    TAX_CORRECTIONS = "tax_corrections"
    TAXES = "taxes"
    TRANSFER_METAL_PHYSICAL = "transfer_metal_physical"
    UNWIND = "unwind"
    VARIATION_MARGIN = "variation_margin"


class MovementType(str, Enum):
    ACCRUED_INTEREST = "accrued_interest"
    ADDITIONAL_WITHHOLDING_TAX = "additional_withholding_tax"
    ASSET = "asset"
    BROKERAGE_FEE = "brokerage_fee"
    CAPITAL_GAIN_TAX = "capital_gain_tax"
    CASH = "cash"
    COMMISSION = "commission"
    CUSTODY_FEE = "custody_fee"
    EXCHANGE_FEE = "exchange_fee"
    FINANCIAL_TRANSACTION_TAX = "financial_transaction_tax"
    INTEREST = "interest"
    MANAGEMENT_FEE = "management_fee"
    OTHER_FEE = "other_fee"
    OTHER = "other"
    OTHER_TAX = "other_tax"
    PREMIUM = "premium"
    RECLAIMABLE_TAX = "reclaimable_tax"
    REINVESTMENT_AMOUNT = "reinvestment_amount"
    STAMP_DUTY = "stamp_duty"
    THIRD_PARTY_FEE = "third_party_fee"
    TRANSACTION_FEE = "transaction_fee"
    VALUE_ADDED_TAX = "value_added_tax"
    WITHHOLDING_TAX = "withholding_tax"


class AccountType(str, Enum):
    CASH_ACCOUNT = "cash_account"
    SAFEKEEPING_ACCOUNT = "safekeeping_account"
    OTHER = "other"


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CustomerSegment(str, Enum):
    RETAIL = "retail"
    PRIVATE_CLIENT = "private_client"
    HIGH_NET_WORTH = "high_net_worth"
    ULTRA_HIGH_NET_WORTH = "ultra_high_net_worth"
    FAMILY_OFFICE = "family_office"
    INSTITUTIONAL = "institutional"
    CORPORATE = "corporate"


class MandateType(str, Enum):
    DISCRETIONARY = "discretionary"
    ADVISORY = "advisory"
    EXECUTION_ONLY = "execution_only"


class InvestmentStrategy(str, Enum):
    CAPITAL_PRESERVATION = "capital_preservation"
    INCOME = "income"
    BALANCED = "balanced"
    BALANCED_GROWTH = "balanced_growth"
    CAPITAL_GROWTH = "capital_growth"
    AGGRESSIVE_GROWTH = "aggressive_growth"


class QuantityUnit(str, Enum):
    PIECE = "piece"
    NOMINAL = "nominal"
    GRAM = "gram"
    TROY_OUNCE = "troy_ounce"
    LOT = "lot"


class PriceType(str, Enum):
    MARKET = "market"
    COST = "cost"
    THEO = "theo"
    BID = "bid"
    ASK = "ask"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


class CurrencyAmount(OpenWealthBase):
    value: float
    currency: str = Field(min_length=3, max_length=3)


class Quantity(OpenWealthBase):
    value: float
    unit: QuantityUnit = QuantityUnit.PIECE


class FinancialInstrument(OpenWealthBase):
    id: str
    isin: str | None = None
    name: str
    type: FinancialInstrumentType
    currency: str = Field(min_length=3, max_length=3)
    country: str | None = None
    sector: str | None = None


class Valuation(OpenWealthBase):
    total_value: float
    currency: str = Field(min_length=3, max_length=3)
    base_value: float | None = None
    base_currency: str | None = None


class ValuationPrice(OpenWealthBase):
    value: float
    price_type: PriceType = PriceType.MARKET
    currency: str = Field(min_length=3, max_length=3)
    source: str | None = None


class ForeignExchangeRate(OpenWealthBase):
    base_rate: float
    inverted_rate: float | None = None
    base_currency: str = Field(min_length=3, max_length=3)


class AccountReference(OpenWealthBase):
    id: str
    type: AccountType


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------


class ValuatedPosition(OpenWealthBase):
    id: str
    name: str | None = None
    currency: str = Field(min_length=3, max_length=3)
    safekeeping_place: str | None = None
    position_date: str
    end_of_day_indicator: bool = True
    financial_instrument: FinancialInstrument
    account: AccountReference
    quantity: Quantity
    valuation: Valuation
    price: ValuationPrice | None = None
    foreign_exchange_rate: ForeignExchangeRate | None = None
    accrued_interest: CurrencyAmount | None = None
    number_of_days_accrued: int | None = None
    weight: float | None = None


class Movement(OpenWealthBase):
    type: MovementType
    financial_instrument: FinancialInstrument | None = None
    quantity: Quantity | None = None
    price: ValuationPrice | None = None
    currency: str | None = None
    amount: float | None = None


class Transaction(OpenWealthBase):
    id: str
    type: TransactionType
    transaction_date: str
    customer_id: str
    reversal_indicator: bool = False
    end_of_day_indicator: bool = True
    reference: str | None = None
    description: str
    trade_date: str | None = None
    settlement_date: str | None = None
    value_date: str | None = None
    movement_list: list[Movement] = Field(default_factory=list)


class PortfolioInformation(OpenWealthBase):
    identification: str
    name: str | None = None
    reference_currency: str | None = None
    mandate_type: MandateType | None = None
    strategy: InvestmentStrategy | None = None
    inception_date: str | None = None


class Account(OpenWealthBase):
    id: str
    type: AccountType
    reference_currency: str = Field(min_length=3, max_length=3)
    name: str | None = None
    iban: str | None = None
    number: str | None = None
    designation: str | None = None
    portfolio_information: PortfolioInformation | None = None


class Customer(OpenWealthBase):
    id: str
    name: str
    status: CustomerStatus = CustomerStatus.ACTIVE
    reference_currency: str = Field(min_length=3, max_length=3)
    number: str | None = None
    opening_date: str | None = None
    language: str | None = None
    customer_segment: CustomerSegment | None = None
    bank_advisor: str | None = None
    bank_deputy_advisor: str | None = None


# ---------------------------------------------------------------------------
# Aggregate / snapshot (non-OpenWealth, advisory-lab extension)
# ---------------------------------------------------------------------------


class AssetAllocation(OpenWealthBase):
    instrument_type: FinancialInstrumentType
    label: str
    market_value: float
    weight: float


class CustomerSnapshot(OpenWealthBase):
    customer: Customer
    portfolios: list[PortfolioInformation]
    accounts: list[Account]
    positions: list[ValuatedPosition]
    transactions: list[Transaction]
    total_market_value: float
    base_currency: str
    asset_allocation: list[AssetAllocation]
