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
    "fx_forward":     "FX Forward",
    "fx_swap":        "FX Swap",
    "fx_option":      "FX Option",
    "precious_metal": "Precious Metals",
    "real_estate":    "Real Estate",
    "crypto_asset":   "Digital Assets",
    "alternative":   "Alternatives",
    # CustomerSegment
    "retail":             "Retail",
    "private_client":      "Private Client",
    "high_net_worth":       "High Net Worth",
    "ultra_high_net_worth":  "Ultra HNW",
    "family_office":       "Family Office",
    "institutional":      "Institutional",
    "corporate":          "Corporate",
    # MandateType
    "discretionary":  "Discretionary",
    "advisory":       "Advisory",
    "execution_only":  "Execution Only",
    # InvestmentStrategy
    "capital_preservation": "Capital Preservation",
    "income":              "Income",
    "balanced":            "Balanced",
    "balanced_growth":      "Balanced Growth",
    "capital_growth":       "Capital Growth",
    "aggressive_growth":    "Aggressive Growth",
    # CustomerStatus
    "active":   "Active",
    "inactive": "Inactive",
    # AccountType
    "cash_account":        "Cash Account",
    "safekeeping_account": "Safekeeping Account",
    # TransactionType
    "buy":                      "Buy",
    "sell":                     "Sell",
    "buy_to_close":               "Buy to Close",
    "sell_to_open":               "Sell to Open",
    "inflow_cash":               "Cash Inflow",
    "outflow_cash":              "Cash Outflow",
    "internal_transfer":         "Internal Transfer",
    "dividend_cash":             "Dividend (Cash)",
    "dividend_reinvestment":     "Dividend Reinvestment",
    "dividend_stock":            "Dividend (Stock)",
    "dividend_choice":           "Dividend Choice",
    "coupon":                   "Coupon",
    "interest_payment":          "Interest Payment",
    "fees":                     "Fees",
    "taxes":                    "Taxes",
    "tax_corrections":           "Tax Corrections",
    "management_fee":            "Management Fee",
    "custody_fee":               "Custody Fee",
    "subscription":             "Subscription",
    "redemption":               "Redemption",
    "redemption_partial":        "Partial Redemption",
    "redemption_prior":          "Prior Redemption",
    "fx_spot":                   "FX Spot",
    "merger":                   "Merger",
    "stock_split":               "Stock Split",
    "spin_off":                  "Spin-off",
    "bonus":                    "Bonus Issue",
    "capital_increase":          "Capital Increase",
    "accumulation":             "Accumulation",
    "additional_payment":        "Additional Payment",
    "adjust_notional":           "Adjust Notional",
    "close_contract":            "Close Contract",
    "credit_event":              "Credit Event",
    "decrease_principal":        "Decrease Principal",
    "delivery_free_of_payment":    "Delivery Free of Payment",
    "delivery_vs_payment":        "Delivery vs. Payment",
    "exercise":                 "Exercise",
    "expiration":               "Expiration",
    "final_liquidation_payment":  "Final Liquidation",
    "increase_principal":        "Increase Principal",
    "instrument_exchange":       "Instrument Exchange",
    "liquidation_payment":       "Liquidation Payment",
    "open_contract":             "Open Contract",
    "prepayment_substitution":   "Prepayment Substitution",
    "receive_free_of_payment":     "Receive Free of Payment",
    "receive_vs_payment":         "Receive vs. Payment",
    "reduction_of_nominal":       "Reduction of Nominal",
    "reset_payment":             "Reset Payment",
    "right_distribution":        "Right Distribution",
    "transfer_metal_physical":    "Transfer Metal (Physical)",
    "unwind":                   "Unwind",
    "variation_margin":          "Variation Margin",
    # MovementType
    "accrued_interest":          "Accrued Interest",
    "additional_withholding_tax": "Additional WHT",
    "asset":                    "Asset",
    "brokerage_fee":             "Brokerage Fee",
    "capital_gain_tax":           "Capital Gains Tax",
    "commission":               "Commission",
    "exchange_fee":              "Exchange Fee",
    "financial_transaction_tax":  "Financial Transaction Tax",
    "interest":                 "Interest",
    "other_fee":                 "Other Fee",
    "other_tax":                 "Other Tax",
    "premium":                  "Premium",
    "reclaimable_tax":           "Reclaimable Tax",
    "reinvestment_amount":       "Reinvestment Amount",
    "stamp_duty":                "Stamp Duty",
    "third_party_fee":            "Third-party Fee",
    "transaction_fee":           "Transaction Fee",
    "value_added_tax":            "Value Added Tax",
    "withholding_tax":           "Withholding Tax",
    # QuantityUnit
    "piece":      "Piece",
    "nominal":    "Nominal",
    "gram":       "Gram",
    "troy_ounce":  "Troy Ounce",
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
        "customerSegment":         _entries(CustomerSegment),
        "customerStatus":          _entries(CustomerStatus),
        "mandateType":             _entries(MandateType),
        "investmentStrategy":      _entries(InvestmentStrategy),
        "financialInstrumentType": _entries(FinancialInstrumentType),
        "accountType":             _entries(AccountType),
        "transactionType":         _entries(TransactionType),
        "movementType":            _entries(MovementType),
        "quantityUnit":            _entries(QuantityUnit),
        "priceType":               _entries(PriceType),
        "currency":                CURRENCIES,
        "country":                 COUNTRIES,
        "region":                  REGIONS,
    }


# ---------------------------------------------------------------------------
# Currencies — ISO 4217, focused on wealth management relevant currencies
# ---------------------------------------------------------------------------

CURRENCIES: list[dict[str, str]] = [
    {"value": "CHF", "label": "Swiss Franc",          "symbol": "Fr.",  "region": "Europe"},
    {"value": "EUR", "label": "Euro",                  "symbol": "€",    "region": "Europe"},
    {"value": "USD", "label": "US Dollar",             "symbol": "$",    "region": "Americas"},
    {"value": "GBP", "label": "British Pound",         "symbol": "£",    "region": "Europe"},
    {"value": "JPY", "label": "Japanese Yen",          "symbol": "¥",    "region": "Asia Pacific"},
    {"value": "CAD", "label": "Canadian Dollar",       "symbol": "C$",   "region": "Americas"},
    {"value": "AUD", "label": "Australian Dollar",     "symbol": "A$",   "region": "Asia Pacific"},
    {"value": "NZD", "label": "New Zealand Dollar",    "symbol": "NZ$",  "region": "Asia Pacific"},
    {"value": "SEK", "label": "Swedish Krona",         "symbol": "kr",   "region": "Europe"},
    {"value": "NOK", "label": "Norwegian Krone",       "symbol": "kr",   "region": "Europe"},
    {"value": "DKK", "label": "Danish Krone",          "symbol": "kr",   "region": "Europe"},
    {"value": "SGD", "label": "Singapore Dollar",      "symbol": "S$",   "region": "Asia Pacific"},
    {"value": "HKD", "label": "Hong Kong Dollar",      "symbol": "HK$",  "region": "Asia Pacific"},
    {"value": "CNY", "label": "Chinese Yuan",          "symbol": "¥",    "region": "Asia Pacific"},
    {"value": "KRW", "label": "South Korean Won",      "symbol": "₩",    "region": "Asia Pacific"},
    {"value": "INR", "label": "Indian Rupee",          "symbol": "₹",    "region": "Asia Pacific"},
    {"value": "BRL", "label": "Brazilian Real",        "symbol": "R$",   "region": "Americas"},
    {"value": "MXN", "label": "Mexican Peso",          "symbol": "$",    "region": "Americas"},
    {"value": "ZAR", "label": "South African Rand",    "symbol": "R",    "region": "Africa"},
    {"value": "AED", "label": "UAE Dirham",            "symbol": "د.إ",  "region": "Middle East"},
    {"value": "SAR", "label": "Saudi Riyal",           "symbol": "﷼",    "region": "Middle East"},
    {"value": "TRY", "label": "Turkish Lira",          "symbol": "₺",    "region": "Europe"},
    {"value": "PLN", "label": "Polish Zloty",          "symbol": "zł",   "region": "Europe"},
    {"value": "CZK", "label": "Czech Koruna",          "symbol": "Kč",   "region": "Europe"},
    {"value": "HUF", "label": "Hungarian Forint",      "symbol": "Ft",   "region": "Europe"},
    {"value": "ILS", "label": "Israeli Shekel",        "symbol": "₪",    "region": "Middle East"},
    {"value": "THB", "label": "Thai Baht",             "symbol": "฿",    "region": "Asia Pacific"},
    {"value": "MYR", "label": "Malaysian Ringgit",     "symbol": "RM",   "region": "Asia Pacific"},
    {"value": "IDR", "label": "Indonesian Rupiah",     "symbol": "Rp",   "region": "Asia Pacific"},
    {"value": "PHP", "label": "Philippine Peso",       "symbol": "₱",    "region": "Asia Pacific"},
]

# ---------------------------------------------------------------------------
# Countries — ISO 3166-1 alpha-2, weighted toward financial centres
# ---------------------------------------------------------------------------

COUNTRIES: list[dict[str, str]] = [
    # Europe
    {"value": "CH", "label": "Switzerland",        "region": "Europe",        "currency": "CHF"},
    {"value": "DE", "label": "Germany",            "region": "Europe",        "currency": "EUR"},
    {"value": "FR", "label": "France",             "region": "Europe",        "currency": "EUR"},
    {"value": "GB", "label": "United Kingdom",     "region": "Europe",        "currency": "GBP"},
    {"value": "NL", "label": "Netherlands",        "region": "Europe",        "currency": "EUR"},
    {"value": "LU", "label": "Luxembourg",         "region": "Europe",        "currency": "EUR"},
    {"value": "IE", "label": "Ireland",            "region": "Europe",        "currency": "EUR"},
    {"value": "SE", "label": "Sweden",             "region": "Europe",        "currency": "SEK"},
    {"value": "NO", "label": "Norway",             "region": "Europe",        "currency": "NOK"},
    {"value": "DK", "label": "Denmark",            "region": "Europe",        "currency": "DKK"},
    {"value": "FI", "label": "Finland",            "region": "Europe",        "currency": "EUR"},
    {"value": "IT", "label": "Italy",              "region": "Europe",        "currency": "EUR"},
    {"value": "ES", "label": "Spain",              "region": "Europe",        "currency": "EUR"},
    {"value": "PT", "label": "Portugal",           "region": "Europe",        "currency": "EUR"},
    {"value": "BE", "label": "Belgium",            "region": "Europe",        "currency": "EUR"},
    {"value": "AT", "label": "Austria",            "region": "Europe",        "currency": "EUR"},
    {"value": "PL", "label": "Poland",             "region": "Europe",        "currency": "PLN"},
    {"value": "CZ", "label": "Czech Republic",     "region": "Europe",        "currency": "CZK"},
    {"value": "HU", "label": "Hungary",            "region": "Europe",        "currency": "HUF"},
    {"value": "TR", "label": "Turkey",             "region": "Europe",        "currency": "TRY"},
    # Americas
    {"value": "US", "label": "United States",      "region": "Americas",      "currency": "USD"},
    {"value": "CA", "label": "Canada",             "region": "Americas",      "currency": "CAD"},
    {"value": "BR", "label": "Brazil",             "region": "Americas",      "currency": "BRL"},
    {"value": "MX", "label": "Mexico",             "region": "Americas",      "currency": "MXN"},
    {"value": "AR", "label": "Argentina",          "region": "Americas",      "currency": "ARS"},
    {"value": "CL", "label": "Chile",              "region": "Americas",      "currency": "CLP"},
    {"value": "CO", "label": "Colombia",           "region": "Americas",      "currency": "COP"},
    # Asia Pacific
    {"value": "JP", "label": "Japan",              "region": "Asia Pacific",  "currency": "JPY"},
    {"value": "CN", "label": "China",              "region": "Asia Pacific",  "currency": "CNY"},
    {"value": "HK", "label": "Hong Kong",          "region": "Asia Pacific",  "currency": "HKD"},
    {"value": "SG", "label": "Singapore",          "region": "Asia Pacific",  "currency": "SGD"},
    {"value": "KR", "label": "South Korea",        "region": "Asia Pacific",  "currency": "KRW"},
    {"value": "AU", "label": "Australia",          "region": "Asia Pacific",  "currency": "AUD"},
    {"value": "NZ", "label": "New Zealand",        "region": "Asia Pacific",  "currency": "NZD"},
    {"value": "IN", "label": "India",              "region": "Asia Pacific",  "currency": "INR"},
    {"value": "TW", "label": "Taiwan",             "region": "Asia Pacific",  "currency": "TWD"},
    {"value": "TH", "label": "Thailand",           "region": "Asia Pacific",  "currency": "THB"},
    {"value": "MY", "label": "Malaysia",           "region": "Asia Pacific",  "currency": "MYR"},
    {"value": "ID", "label": "Indonesia",          "region": "Asia Pacific",  "currency": "IDR"},
    {"value": "PH", "label": "Philippines",        "region": "Asia Pacific",  "currency": "PHP"},
    # Middle East & Africa
    {"value": "AE", "label": "United Arab Emirates", "region": "Middle East", "currency": "AED"},
    {"value": "SA", "label": "Saudi Arabia",       "region": "Middle East",   "currency": "SAR"},
    {"value": "IL", "label": "Israel",             "region": "Middle East",   "currency": "ILS"},
    {"value": "QA", "label": "Qatar",              "region": "Middle East",   "currency": "QAR"},
    {"value": "KW", "label": "Kuwait",             "region": "Middle East",   "currency": "KWD"},
    {"value": "ZA", "label": "South Africa",       "region": "Africa",        "currency": "ZAR"},
    {"value": "NG", "label": "Nigeria",            "region": "Africa",        "currency": "NGN"},
    {"value": "EG", "label": "Egypt",              "region": "Africa",        "currency": "EGP"},
    {"value": "KE", "label": "Kenya",              "region": "Africa",        "currency": "KES"},
    # Offshore / booking centres
    {"value": "KY", "label": "Cayman Islands",     "region": "Offshore",      "currency": "KYD"},
    {"value": "VG", "label": "British Virgin Islands", "region": "Offshore",  "currency": "USD"},
    {"value": "LI", "label": "Liechtenstein",      "region": "Europe",        "currency": "CHF"},
    {"value": "MC", "label": "Monaco",             "region": "Europe",        "currency": "EUR"},
    {"value": "GG", "label": "Guernsey",           "region": "Offshore",      "currency": "GBP"},
    {"value": "JE", "label": "Jersey",             "region": "Offshore",      "currency": "GBP"},
    {"value": "IM", "label": "Isle of Man",        "region": "Offshore",      "currency": "GBP"},
    {"value": "MT", "label": "Malta",              "region": "Europe",        "currency": "EUR"},
    {"value": "CY", "label": "Cyprus",             "region": "Europe",        "currency": "EUR"},
]

# ---------------------------------------------------------------------------
# Regions — used for asset allocation and instrument classification
# ---------------------------------------------------------------------------

REGIONS: list[dict[str, str]] = [
    {"value": "Europe",       "label": "Europe"},
    {"value": "Americas",     "label": "Americas"},
    {"value": "Asia Pacific", "label": "Asia Pacific"},
    {"value": "Middle East",  "label": "Middle East"},
    {"value": "Africa",       "label": "Africa"},
    {"value": "Offshore",     "label": "Offshore / Booking Centres"},
    {"value": "Global",       "label": "Global"},
]
