"""OpenWealth reference data — enum labels derived from the canonical Python enum definitions.

Every category is a list of {value, label} dicts ready for dropdown rendering.
The `build_reference()` function returns the full map; the custodian-api router
exposes it at GET /custody/reference.
"""

from .schemas import (
    AccountType,
    CustomerSegment,
    CustomerStatus,
    FinancialInstrumentType,
    InvestmentStrategy,
    MandateType,
    MovementType,
    PriceType,
    QuantityUnit,
    TransactionType,
)

# ---------------------------------------------------------------------------
# Human-readable labels for each enum value.
# Only values that need a non-obvious label are listed here;
# the fallback auto-formats the camelCase value into Title Case.
# ---------------------------------------------------------------------------

_LABELS: dict[str, dict[str, str]] = {
    # FinancialInstrumentType
    "cash":          "Cash & Liquidity",
    "bond":          "Fixed Income",
    "equity":        "Equities",
    "fund":          "Funds & ETFs",
    "index":         "Indices",
    "commodity":     "Commodities",
    "option":        "Options",
    "future":        "Futures",
    "fxForward":     "FX Forward",
    "fxSwap":        "FX Swap",
    "fxOption":      "FX Option",
    "preciousMetal": "Precious Metals",
    "realEstate":    "Real Estate",
    "cryptoAsset":   "Digital Assets",
    "alternative":   "Alternatives",
    # CustomerSegment
    "retail":             "Retail",
    "privateClient":      "Private Client",
    "highNetWorth":       "High Net Worth",
    "ultraHighNetWorth":  "Ultra HNW",
    "familyOffice":       "Family Office",
    "institutional":      "Institutional",
    "corporate":          "Corporate",
    # MandateType
    "discretionary":  "Discretionary",
    "advisory":       "Advisory",
    "executionOnly":  "Execution Only",
    # InvestmentStrategy
    "capitalPreservation": "Capital Preservation",
    "income":              "Income",
    "balanced":            "Balanced",
    "balancedGrowth":      "Balanced Growth",
    "capitalGrowth":       "Capital Growth",
    "aggressiveGrowth":    "Aggressive Growth",
    # CustomerStatus
    "active":   "Active",
    "inactive": "Inactive",
    # AccountType
    "cashAccount":        "Cash Account",
    "safekeepingAccount": "Safekeeping Account",
    # TransactionType
    "buy":                      "Buy",
    "sell":                     "Sell",
    "buyToClose":               "Buy to Close",
    "sellToOpen":               "Sell to Open",
    "inflowCash":               "Cash Inflow",
    "outflowCash":              "Cash Outflow",
    "internalTransfer":         "Internal Transfer",
    "dividendCash":             "Dividend (Cash)",
    "dividendReinvestment":     "Dividend Reinvestment",
    "dividendStock":            "Dividend (Stock)",
    "dividendChoice":           "Dividend Choice",
    "coupon":                   "Coupon",
    "interestPayment":          "Interest Payment",
    "fees":                     "Fees",
    "taxes":                    "Taxes",
    "taxCorrections":           "Tax Corrections",
    "managementFee":            "Management Fee",
    "custodyFee":               "Custody Fee",
    "subscription":             "Subscription",
    "redemption":               "Redemption",
    "redemptionPartial":        "Partial Redemption",
    "redemptionPrior":          "Prior Redemption",
    "fxSpot":                   "FX Spot",
    "merger":                   "Merger",
    "stockSplit":               "Stock Split",
    "spinOff":                  "Spin-off",
    "bonus":                    "Bonus Issue",
    "capitalIncrease":          "Capital Increase",
    "accumulation":             "Accumulation",
    "additionalPayment":        "Additional Payment",
    "adjustNotional":           "Adjust Notional",
    "closeContract":            "Close Contract",
    "creditEvent":              "Credit Event",
    "decreasePrincipal":        "Decrease Principal",
    "deliveryFreeOfPayment":    "Delivery Free of Payment",
    "deliveryVsPayment":        "Delivery vs. Payment",
    "exercise":                 "Exercise",
    "expiration":               "Expiration",
    "finalLiquidationPayment":  "Final Liquidation",
    "increasePrincipal":        "Increase Principal",
    "instrumentExchange":       "Instrument Exchange",
    "liquidationPayment":       "Liquidation Payment",
    "openContract":             "Open Contract",
    "prepaymentSubstitution":   "Prepayment Substitution",
    "receiveFreeOfPayment":     "Receive Free of Payment",
    "receiveVsPayment":         "Receive vs. Payment",
    "reductionOfNominal":       "Reduction of Nominal",
    "resetPayment":             "Reset Payment",
    "rightDistribution":        "Right Distribution",
    "transferMetalPhysical":    "Transfer Metal (Physical)",
    "unwind":                   "Unwind",
    "variationMargin":          "Variation Margin",
    # MovementType
    "accruedInterest":          "Accrued Interest",
    "additionalWithholdingTax": "Additional WHT",
    "asset":                    "Asset",
    "brokerageFee":             "Brokerage Fee",
    "capitalGainTax":           "Capital Gains Tax",
    "commission":               "Commission",
    "exchangeFee":              "Exchange Fee",
    "financialTransactionTax":  "Financial Transaction Tax",
    "interest":                 "Interest",
    "otherFee":                 "Other Fee",
    "otherTax":                 "Other Tax",
    "premium":                  "Premium",
    "reclaimableTax":           "Reclaimable Tax",
    "reinvestmentAmount":       "Reinvestment Amount",
    "stampDuty":                "Stamp Duty",
    "thirdPartyFee":            "Third-party Fee",
    "transactionFee":           "Transaction Fee",
    "valueAddedTax":            "Value Added Tax",
    "withholdingTax":           "Withholding Tax",
    # QuantityUnit
    "piece":      "Piece",
    "nominal":    "Nominal",
    "gram":       "Gram",
    "troyOunce":  "Troy Ounce",
    "lot":        "Lot",
    # PriceType
    "market": "Market Price",
    "cost":   "Cost Price",
    "theo":   "Theoretical",
    "bid":    "Bid",
    "ask":    "Ask",
}


def _camel_to_title(value: str) -> str:
    """Fallback: camelCase → 'Camel Case'."""
    import re
    spaced = re.sub(r"([A-Z])", r" \1", value).strip()
    return spaced[0].upper() + spaced[1:] if spaced else value


def _entry(value: str) -> dict[str, str]:
    return {"value": value, "label": _LABELS.get(value, _camel_to_title(value))}


def _entries(enum_cls) -> list[dict[str, str]]:
    return [_entry(member.value) for member in enum_cls]


def build_reference() -> dict[str, list[dict[str, str]]]:
    """Return the complete OpenWealth reference data map."""
    return {
        "customerSegment":       _entries(CustomerSegment),
        "customerStatus":        _entries(CustomerStatus),
        "mandateType":           _entries(MandateType),
        "investmentStrategy":    _entries(InvestmentStrategy),
        "financialInstrumentType": _entries(FinancialInstrumentType),
        "accountType":           _entries(AccountType),
        "transactionType":       _entries(TransactionType),
        "movementType":          _entries(MovementType),
        "quantityUnit":          _entries(QuantityUnit),
        "priceType":             _entries(PriceType),
    }
