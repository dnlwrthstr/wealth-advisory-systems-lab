"""Stateless helpers for fill calculation: fees, settlement dates, FX rates."""

from __future__ import annotations

from datetime import date, timedelta

# ── Settlement conventions (business days after trade date) ──────────────────
SETTLEMENT_DAYS: dict[str, int] = {
    "equity": 2,
    "fund": 2,
    "commodity": 2,
    "real_estate": 1,
    "alternative": 1,
    "bond": 1,
    "precious_metal": 1,
    "future": 1,
    "option": 1,
    "index": 1,
    "crypto_asset": 0,
    "fx_forward": 0,
    "fx_swap": 0,
    "fx_option": 0,
    "other": 2,
}

# ── FX rates → CHF (mid-market, fixed simulation rates) ─────────────────────
# Key: (from_currency, to_currency)
_FX_RATES: dict[tuple[str, str], float] = {
    ("EUR", "CHF"): 0.9630,
    ("USD", "CHF"): 0.9048,
    ("GBP", "CHF"): 1.1450,
    ("JPY", "CHF"): 0.00620,
    ("KRW", "CHF"): 0.000680,
    ("CNY", "CHF"): 0.1248,
    ("AUD", "CHF"): 0.5920,
    ("CAD", "CHF"): 0.6680,
    ("SEK", "CHF"): 0.0872,
    ("NOK", "CHF"): 0.0864,
    ("DKK", "CHF"): 0.1292,
    ("CHF", "CHF"): 1.0,
    ("USD", "EUR"): 0.9390,
    ("CHF", "EUR"): 1.0384,
    ("CHF", "USD"): 1.1053,
    ("CHF", "GBP"): 0.8734,
}

# Minimum brokerage fee per fill (in the fill currency)
_MIN_FEE: dict[str, float] = {
    "CHF": 15.0,
    "USD": 15.0,
    "EUR": 13.0,
    "GBP": 12.0,
    "JPY": 1500.0,
}
_DEFAULT_MIN_FEE = 15.0
_FEE_RATE = 0.001  # 0.10% of gross


def calculate_settlement_date(instrument_type: str, trade_date: str) -> str:
    """Return ISO settlement date based on instrument type convention."""
    days = SETTLEMENT_DAYS.get(instrument_type, 2)
    td = date.fromisoformat(trade_date)
    # Advance by calendar days; real systems skip weekends/holidays
    settled = td + timedelta(days=days)
    return settled.isoformat()


def calculate_fee(gross_amount: float, currency: str) -> float:
    """Brokerage commission: 0.10% of gross, minimum per currency."""
    min_fee = _MIN_FEE.get(currency, _DEFAULT_MIN_FEE)
    return round(max(_FEE_RATE * abs(gross_amount), min_fee), 2)


def calculate_net_amount(gross: float, fee: float, side: str) -> float:
    """
    Net cash impact in the fill currency.
    BUY:  -(gross + fee)  — cash leaves the account
    SELL: +(gross - fee)  — cash enters the account
    """
    if side == "buy":
        return round(-(gross + fee), 4)
    else:
        return round(gross - fee, 4)


def fx_rate(instrument_ccy: str, account_ccy: str = "CHF") -> float | None:
    """
    Return the exchange rate to convert instrument_ccy → account_ccy.
    Returns None when currencies match (no conversion needed).
    """
    if instrument_ccy == account_ccy:
        return None
    direct = _FX_RATES.get((instrument_ccy, account_ccy))
    if direct is not None:
        return direct
    # Try inverse
    inverse = _FX_RATES.get((account_ccy, instrument_ccy))
    if inverse is not None:
        return round(1.0 / inverse, 6)
    return None  # unknown pair — caller should handle gracefully
