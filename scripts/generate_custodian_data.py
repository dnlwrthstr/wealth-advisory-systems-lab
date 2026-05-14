#!/usr/bin/env python3
"""Generate realistic OpenWealth-structured custodian data as Parquet files.

Output (data/custodian/):
  customers.parquet      — 15 private-bank customers
  accounts.parquet       — ~30 accounts (cash + securities per portfolio)
  positions.parquet      — ~450 positions (valuation snapshot, latest date)
  transactions.parquet   — ~4 500 transactions (3 years of history)

Run:
  python scripts/generate_custodian_data.py
  python scripts/generate_custodian_data.py --out-dir /custom/path
"""

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

random.seed(42)

# ---------------------------------------------------------------------------
# Instrument catalog — real ISINs
# ---------------------------------------------------------------------------

INSTRUMENTS = [
    # Equities — Switzerland
    {"id": "NESN", "isin": "CH0012221716", "name": "Nestlé SA", "type": "equity", "currency": "CHF", "country": "CH", "sector": "consumer_staples"},
    {"id": "ROG",  "isin": "CH0012032048", "name": "Roche Holding AG", "type": "equity", "currency": "CHF", "country": "CH", "sector": "healthcare"},
    {"id": "NOVN", "isin": "CH0012005267", "name": "Novartis AG", "type": "equity", "currency": "CHF", "country": "CH", "sector": "healthcare"},
    {"id": "ABBN", "isin": "CH0012221716", "name": "ABB Ltd", "type": "equity", "currency": "CHF", "country": "CH", "sector": "industrials"},
    {"id": "SPSN", "isin": "CH0031069328", "name": "Swiss Prime Site AG", "type": "equity", "currency": "CHF", "country": "CH", "sector": "real_estate"},
    {"id": "SREN", "isin": "CH0126881561", "name": "Swiss Re AG", "type": "equity", "currency": "CHF", "country": "CH", "sector": "financials"},
    # Equities — US
    {"id": "AAPL", "isin": "US0378331005", "name": "Apple Inc", "type": "equity", "currency": "USD", "country": "US", "sector": "technology"},
    {"id": "MSFT", "isin": "US5949181045", "name": "Microsoft Corp", "type": "equity", "currency": "USD", "country": "US", "sector": "technology"},
    {"id": "NVDA", "isin": "US67066G1040", "name": "NVIDIA Corp", "type": "equity", "currency": "USD", "country": "US", "sector": "technology"},
    {"id": "AMZN", "isin": "US0231351067", "name": "Amazon.com Inc", "type": "equity", "currency": "USD", "country": "US", "sector": "consumer_discretionary"},
    {"id": "GOOGL","isin": "US02079K3059", "name": "Alphabet Inc", "type": "equity", "currency": "USD", "country": "US", "sector": "technology"},
    {"id": "JPM",  "isin": "US46625H1005", "name": "JPMorgan Chase & Co", "type": "equity", "currency": "USD", "country": "US", "sector": "financials"},
    # Equities — Europe
    {"id": "SAP",  "isin": "DE0007164600", "name": "SAP SE", "type": "equity", "currency": "EUR", "country": "DE", "sector": "technology"},
    {"id": "ASML", "isin": "NL0010273215", "name": "ASML Holding NV", "type": "equity", "currency": "EUR", "country": "NL", "sector": "technology"},
    {"id": "SIE",  "isin": "DE0007236101", "name": "Siemens AG", "type": "equity", "currency": "EUR", "country": "DE", "sector": "industrials"},
    {"id": "MC",   "isin": "FR0000121014", "name": "LVMH Moët Hennessy", "type": "equity", "currency": "EUR", "country": "FR", "sector": "consumer_discretionary"},
    # Funds / ETFs
    {"id": "CHSPI","isin": "CH0237935652", "name": "iShares Core SPI ETF", "type": "fund", "currency": "CHF", "country": "CH", "sector": "broad_market"},
    {"id": "WRLD", "isin": "IE00B4L5Y983", "name": "iShares Core MSCI World UCITS ETF", "type": "fund", "currency": "USD", "country": "IE", "sector": "global_equity"},
    {"id": "EMIM", "isin": "IE00BKM4GZ66", "name": "iShares Core MSCI EM IMI UCITS ETF", "type": "fund", "currency": "USD", "country": "IE", "sector": "emerging_markets"},
    {"id": "SXR8", "isin": "IE00B5BMR087", "name": "iShares Core S&P 500 UCITS ETF", "type": "fund", "currency": "USD", "country": "IE", "sector": "us_large_cap"},
    {"id": "VEUR", "isin": "IE00B945VV12", "name": "Vanguard FTSE Europe UCITS ETF", "type": "fund", "currency": "EUR", "country": "IE", "sector": "european_equity"},
    {"id": "XREA", "isin": "IE00B8GF1M35", "name": "iShares Developed Real Estate ETF", "type": "fund", "currency": "USD", "country": "IE", "sector": "real_estate"},
    # Bonds
    {"id": "CHGOV-2030", "isin": "CH0224392001", "name": "Swiss Confederation Bond 0% 2030", "type": "bond", "currency": "CHF", "country": "CH", "sector": "government"},
    {"id": "CHGOV-2034", "isin": "CH0557778319", "name": "Swiss Confederation Bond 0.5% 2034", "type": "bond", "currency": "CHF", "country": "CH", "sector": "government"},
    {"id": "CHGOV-2040", "isin": "CH0420446075", "name": "Swiss Confederation Bond 1% 2040", "type": "bond", "currency": "CHF", "country": "CH", "sector": "government"},
    {"id": "NOBE-EUR",   "isin": "XS2134155547", "name": "Nestlé Finance Intl 0.375% 2029", "type": "bond", "currency": "EUR", "country": "CH", "sector": "corporate"},
    {"id": "CRED-USD",   "isin": "XS2310961167", "name": "Credit Suisse 3% 2027 (legacy)", "type": "bond", "currency": "USD", "country": "CH", "sector": "corporate"},
]

INST_BY_ID = {i["id"]: i for i in INSTRUMENTS}

# Base prices (approximate, CHF/USD/EUR)
BASE_PRICES: dict[str, float] = {
    "NESN": 85.0, "ROG": 255.0, "NOVN": 88.0, "ABBN": 36.0, "SPSN": 99.0, "SREN": 105.0,
    "AAPL": 190.0, "MSFT": 420.0, "NVDA": 130.0, "AMZN": 210.0, "GOOGL": 175.0, "JPM": 220.0,
    "SAP": 240.0, "ASML": 750.0, "SIE": 185.0, "MC": 680.0,
    "CHSPI": 152.0, "WRLD": 117.0, "EMIM": 39.0, "SXR8": 510.0, "VEUR": 32.0, "XREA": 43.0,
    "CHGOV-2030": 98.5, "CHGOV-2034": 96.2, "CHGOV-2040": 91.0,
    "NOBE-EUR": 97.8, "CRED-USD": 82.0,
}

# FX rates (to CHF base)
FX_TO_CHF: dict[str, float] = {"CHF": 1.0, "USD": 0.91, "EUR": 0.97}

# ---------------------------------------------------------------------------
# Portfolio strategy → typical instrument mix
# ---------------------------------------------------------------------------

STRATEGY_MIX: dict[str, dict[str, float]] = {
    "capitalPreservation": {
        "CHGOV-2030": 0.30, "CHGOV-2034": 0.30, "CHGOV-2040": 0.15,
        "CHSPI": 0.10, "VEUR": 0.05, "NOBE-EUR": 0.10,
    },
    "income": {
        "CHGOV-2034": 0.20, "CHGOV-2040": 0.15, "NOBE-EUR": 0.15,
        "CHSPI": 0.15, "WRLD": 0.15, "NESN": 0.10, "SREN": 0.10,
    },
    "balanced": {
        "CHSPI": 0.18, "WRLD": 0.22, "CHGOV-2034": 0.20,
        "SPSN": 0.10, "VEUR": 0.08, "EMIM": 0.07, "NESN": 0.08, "NOVN": 0.07,
    },
    "balancedGrowth": {
        "WRLD": 0.28, "SXR8": 0.12, "CHSPI": 0.12, "EMIM": 0.10,
        "AAPL": 0.07, "MSFT": 0.07, "ASML": 0.07, "CHGOV-2034": 0.10, "VEUR": 0.07,
    },
    "capitalGrowth": {
        "WRLD": 0.22, "SXR8": 0.18, "EMIM": 0.10,
        "NVDA": 0.10, "AAPL": 0.08, "MSFT": 0.08, "ASML": 0.08, "GOOGL": 0.08, "SAP": 0.08,
    },
    "aggressiveGrowth": {
        "NVDA": 0.15, "AAPL": 0.12, "MSFT": 0.12, "GOOGL": 0.10,
        "AMZN": 0.10, "ASML": 0.10, "SXR8": 0.15, "EMIM": 0.08, "JPM": 0.08,
    },
}

# ---------------------------------------------------------------------------
# Customer definitions
# ---------------------------------------------------------------------------

CUSTOMER_DEFS = [
    ("C-1001", "Anna Keller",              "CH", "de", "privateClient",     "balanced",        1_200_000),
    ("C-1002", "Thomas Müller",            "CH", "de", "privateClient",     "balancedGrowth",  2_500_000),
    ("C-1003", "Claire Dubois",            "CH", "fr", "privateClient",     "income",            850_000),
    ("C-1004", "Karin Hofmann",            "CH", "de", "highNetWorth",      "balanced",        4_200_000),
    ("C-1005", "Oliver Fischer",           "DE", "de", "highNetWorth",      "capitalGrowth",   3_800_000),
    ("C-1006", "Emma Bernasconi",          "CH", "it", "privateClient",     "capitalPreservation", 620_000),
    ("C-1007", "Pierre Favre",             "CH", "fr", "highNetWorth",      "balancedGrowth",  5_100_000),
    ("C-1008", "Sophia Wagner",            "AT", "de", "retail",            "balanced",          380_000),
    ("C-2001", "Helvetia Investments AG",  "CH", "de", "institutional",     "capitalGrowth",  18_000_000),
    ("C-2002", "Meyer Family Office",      "CH", "de", "familyOffice",      "aggressiveGrowth",22_000_000),
    ("C-2003", "Albrecht Family Trust",    "LI", "de", "ultraHighNetWorth", "capitalGrowth",  45_000_000),
    ("C-2004", "Bergmann Stiftung",        "CH", "de", "institutional",     "income",          8_500_000),
    ("C-3001", "LuzernTech Pension",       "CH", "de", "institutional",     "balanced",       32_000_000),
    ("C-3002", "Midland Corporate SA",     "CH", "fr", "corporate",         "capitalPreservation", 6_200_000),
    ("C-3003", "Horizon Endowment Fund",   "CH", "en", "institutional",     "balancedGrowth", 12_000_000),
]

SEGMENT_ADVISORS = {
    "retail": "A. Huber",
    "privateClient": "M. Brüggemann",
    "highNetWorth": "S. Keller",
    "ultraHighNetWorth": "C. Bauer",
    "familyOffice": "S. Wirth",
    "institutional": "R. Zimmermann",
    "corporate": "P. Schmid",
}

MANDATE_BY_SEGMENT = {
    "retail": "advisory",
    "privateClient": "discretionary",
    "highNetWorth": "discretionary",
    "ultraHighNetWorth": "discretionary",
    "familyOffice": "advisory",
    "institutional": "discretionary",
    "corporate": "advisory",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _price_walk(base: float, n_days: int, vol: float = 0.015) -> list[float]:
    """Simple random walk for price simulation."""
    prices = [base]
    for _ in range(n_days):
        prices.append(round(max(prices[-1] * (1 + random.gauss(0.0002, vol)), 0.01), 4))
    return prices


def _date_range(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


def _business_days(start: date, end: date) -> list[date]:
    return [d for d in _date_range(start, end) if d.weekday() < 5]


# ---------------------------------------------------------------------------
# Build DataFrames
# ---------------------------------------------------------------------------

SNAPSHOT_DATE = date(2026, 5, 14)
HISTORY_START = date(2023, 1, 2)


def build_customers() -> pd.DataFrame:
    rows = []
    for cid, name, country, lang, segment, strategy, aum in CUSTOMER_DEFS:
        rows.append({
            "id": cid,
            "name": name,
            "status": "active",
            "reference_currency": "CHF",
            "number": cid.replace("C-", ""),
            "opening_date": "2018-01-15",
            "language": lang,
            "customer_segment": segment,
            "bank_advisor": SEGMENT_ADVISORS[segment],
            "bank_deputy_advisor": None,
        })
    return pd.DataFrame(rows)


def build_accounts_and_positions_and_transactions(
    customers_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    accounts = []
    positions = []
    transactions = []

    tx_seq: dict[str, int] = {}
    pos_seq: dict[str, int] = {}

    for _, cust in customers_df.iterrows():
        cid = cust["id"]
        segment = cust["customer_segment"]
        mandate = MANDATE_BY_SEGMENT[segment]
        _, _, _, _, _, strategy, aum = next(d for d in CUSTOMER_DEFS if d[0] == cid)
        aum = float(aum)

        # One core portfolio + optionally a liquidity reserve for larger clients
        portfolios = [
            {
                "portfolio_id": f"PF-{cid[2:]}-CORE",
                "portfolio_name": "Core mandate",
                "portfolio_mandate_type": mandate,
                "portfolio_strategy": strategy,
                "portfolio_reference_currency": "CHF",
                "portfolio_inception_date": cust["opening_date"],
                "strategy": strategy,
                "aum_share": 0.85 if aum > 1_000_000 else 1.0,
            },
        ]
        if aum > 1_000_000:
            portfolios.append({
                "portfolio_id": f"PF-{cid[2:]}-LIQ",
                "portfolio_name": "Liquidity reserve",
                "portfolio_mandate_type": "advisory",
                "portfolio_strategy": "capitalPreservation",
                "portfolio_reference_currency": "CHF",
                "portfolio_inception_date": cust["opening_date"],
                "strategy": "capitalPreservation",
                "aum_share": 0.15,
            })

        for pf in portfolios:
            pf_id = pf["portfolio_id"]
            sec_acct_id = f"A-{cid[2:]}-{pf_id.split('-')[-1]}-SEC"
            cash_acct_id = f"A-{cid[2:]}-{pf_id.split('-')[-1]}-CASH"

            for acct_id, acct_type, ref_ccy in [
                (sec_acct_id, "safekeepingAccount", "CHF"),
                (cash_acct_id, "cashAccount", "CHF"),
            ]:
                accounts.append({
                    "id": acct_id,
                    "customer_id": cid,
                    "type": acct_type,
                    "reference_currency": ref_ccy,
                    "name": f"{pf['portfolio_name']} {'securities' if 'SEC' in acct_id else 'cash'}",
                    "iban": None,
                    "number": acct_id.replace("A-", ""),
                    "designation": None,
                    "portfolio_id": pf_id,
                    "portfolio_name": pf["portfolio_name"],
                    "portfolio_reference_currency": pf["portfolio_reference_currency"],
                    "portfolio_mandate_type": pf["portfolio_mandate_type"],
                    "portfolio_strategy": pf["portfolio_strategy"],
                    "portfolio_inception_date": pf["portfolio_inception_date"],
                })

            pf_aum = aum * pf["aum_share"]
            cash_allocation = pf_aum * 0.05  # 5% cash
            invested = pf_aum - cash_allocation

            # Cash position
            pos_seq.setdefault(cid, 0)
            pos_seq[cid] += 1
            positions.append({
                "id": f"POS-{cid[2:]}-{pos_seq[cid]:04d}",
                "customer_id": cid,
                "account_id": cash_acct_id,
                "account_type": "cashAccount",
                "currency": "CHF",
                "safekeeping_place": None,
                "position_date": str(SNAPSHOT_DATE),
                "end_of_day_indicator": True,
                "name": "Swiss franc cash",
                "instrument_id": "CASH-CHF",
                "instrument_isin": None,
                "instrument_name": "Swiss franc cash",
                "instrument_type": "cash",
                "instrument_currency": "CHF",
                "instrument_country": "CH",
                "instrument_sector": None,
                "quantity_value": cash_allocation,
                "quantity_unit": "nominal",
                "total_value": cash_allocation,
                "valuation_currency": "CHF",
                "base_value": cash_allocation,
                "base_currency": "CHF",
                "price_value": 1.0,
                "price_type": "market",
                "price_currency": "CHF",
                "price_source": None,
                "fx_base_rate": None,
                "fx_inverted_rate": None,
                "fx_base_currency": None,
                "accrued_interest_value": None,
                "accrued_interest_currency": None,
                "number_of_days_accrued": None,
                "weight": round(cash_allocation / pf_aum, 4),
            })

            # Securities positions according to strategy mix
            mix = STRATEGY_MIX.get(pf["strategy"], STRATEGY_MIX["balanced"])
            total_weight = sum(mix.values())
            for inst_id, weight in mix.items():
                actual_weight = weight / total_weight
                target_value = invested * actual_weight
                inst = INST_BY_ID[inst_id]
                price = BASE_PRICES[inst_id] * random.uniform(0.93, 1.07)
                lot_size = 1 if inst["type"] in ("equity", "fund") else 1000
                qty = max(lot_size, round(target_value / (price * FX_TO_CHF[inst["currency"]]) / lot_size) * lot_size)
                total_val = round(qty * price, 2)
                fx_rate = FX_TO_CHF[inst["currency"]]
                base_val = round(total_val * fx_rate, 2)
                accrued = round(total_val * 0.003, 2) if inst["type"] == "bond" else None

                pos_seq[cid] += 1
                safekeeping = "SIX SIS" if inst["currency"] == "CHF" else "Clearstream"
                positions.append({
                    "id": f"POS-{cid[2:]}-{pos_seq[cid]:04d}",
                    "customer_id": cid,
                    "account_id": sec_acct_id,
                    "account_type": "safekeepingAccount",
                    "currency": inst["currency"],
                    "safekeeping_place": safekeeping,
                    "position_date": str(SNAPSHOT_DATE),
                    "end_of_day_indicator": True,
                    "name": inst["name"],
                    "instrument_id": inst_id,
                    "instrument_isin": inst["isin"],
                    "instrument_name": inst["name"],
                    "instrument_type": inst["type"],
                    "instrument_currency": inst["currency"],
                    "instrument_country": inst["country"],
                    "instrument_sector": inst["sector"],
                    "quantity_value": float(qty),
                    "quantity_unit": "piece" if inst["type"] in ("equity", "fund") else "nominal",
                    "total_value": total_val,
                    "valuation_currency": inst["currency"],
                    "base_value": base_val,
                    "base_currency": "CHF",
                    "price_value": round(price, 4),
                    "price_type": "market",
                    "price_currency": inst["currency"],
                    "price_source": "Bloomberg",
                    "fx_base_rate": fx_rate if inst["currency"] != "CHF" else None,
                    "fx_inverted_rate": round(1 / fx_rate, 4) if inst["currency"] != "CHF" else None,
                    "fx_base_currency": "CHF" if inst["currency"] != "CHF" else None,
                    "accrued_interest_value": accrued,
                    "accrued_interest_currency": inst["currency"] if accrued else None,
                    "number_of_days_accrued": random.randint(20, 80) if accrued else None,
                    "weight": round(base_val / pf_aum, 4),
                })

            # Transaction history -----------------------------------------------
            biz_days = _business_days(HISTORY_START, SNAPSHOT_DATE)
            tx_seq.setdefault(cid, 0)

            # Initial funding
            tx_seq[cid] += 1
            txid = f"TX-{cid[2:]}-{tx_seq[cid]:05d}"
            transactions.append({
                "id": txid,
                "type": "inflowCash",
                "transaction_date": str(HISTORY_START),
                "customer_id": cid,
                "reversal_indicator": False,
                "end_of_day_indicator": True,
                "reference": None,
                "description": "Initial client funding",
                "trade_date": str(HISTORY_START),
                "settlement_date": str(HISTORY_START),
                "value_date": str(HISTORY_START),
                "movements_json": json.dumps([
                    {"type": "cash", "currency": "CHF", "amount": round(pf_aum, 2)}
                ]),
            })

            # Initial buys
            for inst_id, weight in mix.items():
                actual_weight = weight / total_weight
                target_value = invested * actual_weight
                inst = INST_BY_ID[inst_id]
                price = BASE_PRICES[inst_id] * random.uniform(0.90, 1.02)
                lot_size = 1 if inst["type"] in ("equity", "fund") else 1000
                qty = max(lot_size, round(target_value / (price * FX_TO_CHF[inst["currency"]]) / lot_size) * lot_size)
                gross = round(qty * price, 2)
                fee = round(gross * 0.001, 2)
                buy_date = HISTORY_START + timedelta(days=random.randint(1, 10))
                settle = buy_date + timedelta(days=2)

                tx_seq[cid] += 1
                txid = f"TX-{cid[2:]}-{tx_seq[cid]:05d}"
                movements = [
                    {
                        "type": "asset",
                        "instrument_id": inst_id,
                        "instrument_isin": inst["isin"],
                        "instrument_name": inst["name"],
                        "instrument_type": inst["type"],
                        "instrument_currency": inst["currency"],
                        "quantity_value": float(qty),
                        "quantity_unit": "piece" if inst["type"] in ("equity", "fund") else "nominal",
                        "price_value": round(price, 4),
                        "price_type": "market",
                        "price_currency": inst["currency"],
                    },
                    {"type": "cash", "currency": inst["currency"], "amount": -gross},
                    {"type": "brokerageFee", "currency": inst["currency"], "amount": -fee},
                ]
                transactions.append({
                    "id": txid,
                    "type": "buy",
                    "transaction_date": str(buy_date),
                    "customer_id": cid,
                    "reversal_indicator": False,
                    "end_of_day_indicator": True,
                    "reference": None,
                    "description": f"Initial purchase {inst['name']}",
                    "trade_date": str(buy_date),
                    "settlement_date": str(settle),
                    "value_date": str(settle),
                    "movements_json": json.dumps(movements),
                })

            # Ongoing transactions — quarterly rebalances, dividends, coupons
            quarters_start = HISTORY_START
            while quarters_start < SNAPSHOT_DATE:
                q_end = quarters_start + timedelta(days=90)
                q_date = quarters_start + timedelta(days=random.randint(5, 85))
                if q_date >= SNAPSHOT_DATE:
                    break

                # Cash flow (deposit or withdrawal)
                if random.random() < 0.3:
                    direction = 1 if random.random() < 0.7 else -1
                    amount = round(pf_aum * random.uniform(0.01, 0.04) * direction, 2)
                    tx_type = "inflowCash" if direction > 0 else "outflowCash"
                    tx_seq[cid] += 1
                    transactions.append({
                        "id": f"TX-{cid[2:]}-{tx_seq[cid]:05d}",
                        "type": tx_type,
                        "transaction_date": str(q_date),
                        "customer_id": cid,
                        "reversal_indicator": False,
                        "end_of_day_indicator": True,
                        "reference": None,
                        "description": "Cash transfer",
                        "trade_date": None,
                        "settlement_date": None,
                        "value_date": str(q_date),
                        "movements_json": json.dumps([
                            {"type": "cash", "currency": "CHF", "amount": amount}
                        ]),
                    })

                # Dividends for equity/fund positions
                for inst_id in list(mix.keys())[:4]:
                    inst = INST_BY_ID[inst_id]
                    if inst["type"] not in ("equity", "fund"):
                        continue
                    div_amount = round(pf_aum * actual_weight * 0.008, 2)
                    wht = round(div_amount * 0.15, 2)
                    tx_seq[cid] += 1
                    transactions.append({
                        "id": f"TX-{cid[2:]}-{tx_seq[cid]:05d}",
                        "type": "dividendCash",
                        "transaction_date": str(q_date + timedelta(days=random.randint(1, 5))),
                        "customer_id": cid,
                        "reversal_indicator": False,
                        "end_of_day_indicator": True,
                        "reference": None,
                        "description": f"Dividend {inst['name']}",
                        "trade_date": None,
                        "settlement_date": None,
                        "value_date": str(q_date + timedelta(days=7)),
                        "movements_json": json.dumps([
                            {"type": "cash", "currency": inst["currency"], "amount": div_amount},
                            {"type": "withholdingTax", "currency": inst["currency"], "amount": -wht},
                        ]),
                    })

                # Bond coupon (semi-annual)
                for inst_id in list(mix.keys()):
                    inst = INST_BY_ID[inst_id]
                    if inst["type"] != "bond":
                        continue
                    if random.random() < 0.5:
                        coupon = round(pf_aum * (mix[inst_id] / total_weight) * 0.005, 2)
                        tx_seq[cid] += 1
                        transactions.append({
                            "id": f"TX-{cid[2:]}-{tx_seq[cid]:05d}",
                            "type": "coupon",
                            "transaction_date": str(q_date),
                            "customer_id": cid,
                            "reversal_indicator": False,
                            "end_of_day_indicator": True,
                            "reference": None,
                            "description": f"Bond coupon {inst['name']}",
                            "trade_date": None,
                            "settlement_date": None,
                            "value_date": str(q_date + timedelta(days=3)),
                            "movements_json": json.dumps([
                                {"type": "interest", "currency": inst["currency"], "amount": coupon},
                            ]),
                        })

                # Rebalancing trade (buy/sell one instrument)
                if random.random() < 0.4:
                    inst_id = random.choice(list(mix.keys()))
                    inst = INST_BY_ID[inst_id]
                    price = BASE_PRICES[inst_id] * random.uniform(0.85, 1.15)
                    direction = random.choice(["buy", "sell"])
                    lot_size = 1 if inst["type"] in ("equity", "fund") else 1000
                    qty = lot_size * random.randint(1, 20)
                    gross = round(qty * price, 2)
                    fee = round(gross * 0.001, 2)
                    settle = q_date + timedelta(days=2)
                    cash_sign = -1 if direction == "buy" else 1
                    asset_sign = 1 if direction == "buy" else -1

                    tx_seq[cid] += 1
                    transactions.append({
                        "id": f"TX-{cid[2:]}-{tx_seq[cid]:05d}",
                        "type": direction,
                        "transaction_date": str(q_date),
                        "customer_id": cid,
                        "reversal_indicator": False,
                        "end_of_day_indicator": True,
                        "reference": None,
                        "description": f"Rebalancing {'purchase' if direction == 'buy' else 'sale'} {inst['name']}",
                        "trade_date": str(q_date),
                        "settlement_date": str(settle),
                        "value_date": str(settle),
                        "movements_json": json.dumps([
                            {
                                "type": "asset",
                                "instrument_id": inst_id,
                                "instrument_isin": inst["isin"],
                                "instrument_name": inst["name"],
                                "instrument_type": inst["type"],
                                "instrument_currency": inst["currency"],
                                "quantity_value": float(qty * asset_sign),
                                "quantity_unit": "piece" if inst["type"] in ("equity", "fund") else "nominal",
                                "price_value": round(price, 4),
                                "price_type": "market",
                                "price_currency": inst["currency"],
                            },
                            {"type": "cash", "currency": inst["currency"], "amount": gross * cash_sign},
                            {"type": "brokerageFee", "currency": inst["currency"], "amount": -fee},
                        ]),
                    })

                # Management fee (annual)
                if quarters_start.month in (3, 4):
                    mgmt_fee = round(pf_aum * 0.0065 / 4, 2)
                    tx_seq[cid] += 1
                    transactions.append({
                        "id": f"TX-{cid[2:]}-{tx_seq[cid]:05d}",
                        "type": "fees",
                        "transaction_date": str(q_date),
                        "customer_id": cid,
                        "reversal_indicator": False,
                        "end_of_day_indicator": True,
                        "reference": None,
                        "description": "Quarterly management fee",
                        "trade_date": None,
                        "settlement_date": None,
                        "value_date": str(q_date),
                        "movements_json": json.dumps([
                            {"type": "managementFee", "currency": "CHF", "amount": -mgmt_fee},
                        ]),
                    })

                quarters_start = q_end

    return (
        pd.DataFrame(accounts),
        pd.DataFrame(positions),
        pd.DataFrame(transactions),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(out_dir: str) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("Generating customers …")
    customers_df = build_customers()
    customers_df.to_parquet(out_path / "customers.parquet", index=False)
    print(f"  {len(customers_df)} customers")

    print("Generating accounts, positions, transactions …")
    accounts_df, positions_df, transactions_df = build_accounts_and_positions_and_transactions(
        customers_df
    )

    accounts_df.to_parquet(out_path / "accounts.parquet", index=False)
    positions_df.to_parquet(out_path / "positions.parquet", index=False)
    transactions_df.to_parquet(out_path / "transactions.parquet", index=False)

    print(f"  {len(accounts_df)} accounts")
    print(f"  {len(positions_df)} positions")
    print(f"  {len(transactions_df)} transactions")
    print(f"\nParquet files written to {out_path.resolve()}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default="data/custodian",
        help="Output directory for Parquet files (default: data/custodian)",
    )
    args = parser.parse_args()
    main(args.out_dir)
