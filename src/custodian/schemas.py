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
    FX_FORWARD = "fxForward"
    FX_SWAP = "fxSwap"
    FX_OPTION = "fxOption"
    PRECIOUS_METAL = "preciousMetal"
    REAL_ESTATE = "realEstate"
    CRYPTO_ASSET = "cryptoAsset"
    ALTERNATIVE = "alternative"
    OTHER = "other"


class TransactionType(str, Enum):
    ACCUMULATION = "accumulation"
    ADDITIONAL_PAYMENT = "additionalPayment"
    ADJUST_NOTIONAL = "adjustNotional"
    BONUS = "bonus"
    BUY = "buy"
    BUY_TO_CLOSE = "buyToClose"
    CAPITAL_INCREASE = "capitalIncrease"
    CLOSE_CONTRACT = "closeContract"
    COUPON = "coupon"
    CREDIT_EVENT = "creditEvent"
    DECREASE_PRINCIPAL = "decreasePrincipal"
    DELIVERY_FREE_OF_PAYMENT = "deliveryFreeOfPayment"
    DELIVERY_VS_PAYMENT = "deliveryVsPayment"
    DIVIDEND_CASH = "dividendCash"
    DIVIDEND_CHOICE = "dividendChoice"
    DIVIDEND_REINVESTMENT = "dividendReinvestment"
    DIVIDEND_STOCK = "dividendStock"
    EXERCISE = "exercise"
    EXPIRATION = "expiration"
    FEES = "fees"
    FINAL_LIQUIDATION_PAYMENT = "finalLiquidationPayment"
    FX_SPOT = "fxSpot"
    INCREASE_PRINCIPAL = "increasePrincipal"
    INFLOW_CASH = "inflowCash"
    INSTRUMENT_EXCHANGE = "instrumentExchange"
    INTEREST_PAYMENT = "interestPayment"
    INTERNAL_TRANSFER = "internalTransfer"
    LIQUIDATION_PAYMENT = "liquidationPayment"
    MERGER = "merger"
    OPEN_CONTRACT = "openContract"
    OTHER = "other"
    OUTFLOW_CASH = "outflowCash"
    PREMIUM = "premium"
    PREPAYMENT_SUBSTITUTION = "prepaymentSubstitution"
    RECEIVE_FREE_OF_PAYMENT = "receiveFreeOfPayment"
    RECEIVE_VS_PAYMENT = "receiveVsPayment"
    REDEMPTION = "redemption"
    REDEMPTION_PARTIAL = "redemptionPartial"
    REDEMPTION_PRIOR = "redemptionPrior"
    REDUCTION_OF_NOMINAL = "reductionOfNominal"
    RESET_PAYMENT = "resetPayment"
    RIGHT_DISTRIBUTION = "rightDistribution"
    SELL = "sell"
    SELL_TO_OPEN = "sellToOpen"
    SPIN_OFF = "spinOff"
    STOCK_SPLIT = "stockSplit"
    SUBSCRIPTION = "subscription"
    TAX_CORRECTIONS = "taxCorrections"
    TAXES = "taxes"
    TRANSFER_METAL_PHYSICAL = "transferMetalPhysical"
    UNWIND = "unwind"
    VARIATION_MARGIN = "variationMargin"


class MovementType(str, Enum):
    ACCRUED_INTEREST = "accruedInterest"
    ADDITIONAL_WITHHOLDING_TAX = "additionalWithholdingTax"
    ASSET = "asset"
    BROKERAGE_FEE = "brokerageFee"
    CAPITAL_GAIN_TAX = "capitalGainTax"
    CASH = "cash"
    COMMISSION = "commission"
    CUSTODY_FEE = "custodyFee"
    EXCHANGE_FEE = "exchangeFee"
    FINANCIAL_TRANSACTION_TAX = "financialTransactionTax"
    INTEREST = "interest"
    MANAGEMENT_FEE = "managementFee"
    OTHER_FEE = "otherFee"
    OTHER = "other"
    OTHER_TAX = "otherTax"
    PREMIUM = "premium"
    RECLAIMABLE_TAX = "reclaimableTax"
    REINVESTMENT_AMOUNT = "reinvestmentAmount"
    STAMP_DUTY = "stampDuty"
    THIRD_PARTY_FEE = "thirdPartyFee"
    TRANSACTION_FEE = "transactionFee"
    VALUE_ADDED_TAX = "valueAddedTax"
    WITHHOLDING_TAX = "withholdingTax"


class AccountType(str, Enum):
    CASH_ACCOUNT = "cashAccount"
    SAFEKEEPING_ACCOUNT = "safekeepingAccount"
    OTHER = "other"


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CustomerSegment(str, Enum):
    RETAIL = "retail"
    PRIVATE_CLIENT = "privateClient"
    HIGH_NET_WORTH = "highNetWorth"
    ULTRA_HIGH_NET_WORTH = "ultraHighNetWorth"
    FAMILY_OFFICE = "familyOffice"
    INSTITUTIONAL = "institutional"
    CORPORATE = "corporate"


class MandateType(str, Enum):
    DISCRETIONARY = "discretionary"
    ADVISORY = "advisory"
    EXECUTION_ONLY = "executionOnly"


class InvestmentStrategy(str, Enum):
    CAPITAL_PRESERVATION = "capitalPreservation"
    INCOME = "income"
    BALANCED = "balanced"
    BALANCED_GROWTH = "balancedGrowth"
    CAPITAL_GROWTH = "capitalGrowth"
    AGGRESSIVE_GROWTH = "aggressiveGrowth"


class QuantityUnit(str, Enum):
    PIECE = "piece"
    NOMINAL = "nominal"
    GRAM = "gram"
    TROY_OUNCE = "troyOunce"
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
