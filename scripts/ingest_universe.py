"""
Instrument universe ingestion script.

Reads seeds from IN_INSTRUMENTS_COMPLETE.csv, enriches equities via yfinance,
and writes golden records to data/universe/equity.parquet and simpleBond.parquet.

Usage:
    python scripts/ingest_universe.py [--csv PATH] [--limit N] [--out DIR]

The --limit flag caps how many instruments of each class to attempt (useful for
quick dev runs; omit for full ingestion which takes ~30 min for 2500 equities).
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from datetime import datetime, date
from pathlib import Path

# Allow running from project root without activating venv explicitly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import yfinance as yf

from universe.schemas import BondRecord, EquityRecord
from universe.store import ParquetUniverseStore

log = logging.getLogger("ingest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Constants ──────────────────────────────────────────────────────────────────

ISIN_COUNTRY = {
    "AD": "AD", "AE": "AE", "AF": "AF", "AG": "AG", "AL": "AL", "AM": "AM",
    "AO": "AO", "AR": "AR", "AT": "AT", "AU": "AU", "AZ": "AZ", "BA": "BA",
    "BB": "BB", "BD": "BD", "BE": "BE", "BG": "BG", "BH": "BH", "BI": "BI",
    "BJ": "BJ", "BN": "BN", "BO": "BO", "BR": "BR", "BS": "BS", "BT": "BT",
    "BW": "BW", "BY": "BY", "BZ": "BZ", "CA": "CA", "CD": "CD", "CF": "CF",
    "CG": "CG", "CH": "CH", "CI": "CI", "CL": "CL", "CM": "CM", "CN": "CN",
    "CO": "CO", "CR": "CR", "CU": "CU", "CV": "CV", "CY": "CY", "CZ": "CZ",
    "DE": "DE", "DJ": "DJ", "DK": "DK", "DM": "DM", "DO": "DO", "DZ": "DZ",
    "EC": "EC", "EE": "EE", "EG": "EG", "ER": "ER", "ES": "ES", "ET": "ET",
    "FI": "FI", "FJ": "FJ", "FM": "FM", "FR": "FR", "GA": "GA", "GB": "GB",
    "GD": "GD", "GE": "GE", "GH": "GH", "GM": "GM", "GN": "GN", "GQ": "GQ",
    "GR": "GR", "GT": "GT", "GW": "GW", "GY": "GY", "HK": "HK", "HN": "HN",
    "HR": "HR", "HT": "HT", "HU": "HU", "ID": "ID", "IE": "IE", "IL": "IL",
    "IN": "IN", "IQ": "IQ", "IR": "IR", "IS": "IS", "IT": "IT", "JM": "JM",
    "JO": "JO", "JP": "JP", "KE": "KE", "KG": "KG", "KH": "KH", "KI": "KI",
    "KM": "KM", "KN": "KN", "KP": "KP", "KR": "KR", "KW": "KW", "KZ": "KZ",
    "LA": "LA", "LB": "LB", "LC": "LC", "LI": "LI", "LK": "LK", "LR": "LR",
    "LS": "LS", "LT": "LT", "LU": "LU", "LV": "LV", "LY": "LY", "MA": "MA",
    "MC": "MC", "MD": "MD", "ME": "ME", "MG": "MG", "MH": "MH", "MK": "MK",
    "ML": "ML", "MM": "MM", "MN": "MN", "MR": "MR", "MT": "MT", "MU": "MU",
    "MV": "MV", "MW": "MW", "MX": "MX", "MY": "MY", "MZ": "MZ", "NA": "NA",
    "NE": "NE", "NG": "NG", "NI": "NI", "NL": "NL", "NO": "NO", "NP": "NP",
    "NR": "NR", "NZ": "NZ", "OM": "OM", "PA": "PA", "PE": "PE", "PG": "PG",
    "PH": "PH", "PK": "PK", "PL": "PL", "PT": "PT", "PW": "PW", "PY": "PY",
    "QA": "QA", "RO": "RO", "RS": "RS", "RU": "RU", "RW": "RW", "SA": "SA",
    "SB": "SB", "SC": "SC", "SD": "SD", "SE": "SE", "SG": "SG", "SI": "SI",
    "SK": "SK", "SL": "SL", "SM": "SM", "SN": "SN", "SO": "SO", "SR": "SR",
    "SS": "SS", "ST": "ST", "SV": "SV", "SY": "SY", "SZ": "SZ", "TD": "TD",
    "TG": "TG", "TH": "TH", "TJ": "TJ", "TL": "TL", "TM": "TM", "TN": "TN",
    "TO": "TO", "TR": "TR", "TT": "TT", "TV": "TV", "TW": "TW", "TZ": "TZ",
    "UA": "UA", "UG": "UG", "US": "US", "UY": "UY", "UZ": "UZ", "VA": "VA",
    "VC": "VC", "VE": "VE", "VN": "VN", "VU": "VU", "WS": "WS", "XS": "XS",
    "YE": "YE", "ZA": "ZA", "ZM": "ZM", "ZW": "ZW",
}

# yfinance exchange suffix by ISIN country code
EXCHANGE_SUFFIX = {
    "CH": ".SW",  "DE": ".DE",  "FR": ".PA",  "GB": ".L",
    "IT": ".MI",  "ES": ".MC",  "NL": ".AS",  "SE": ".ST",
    "DK": ".CO",  "NO": ".OL",  "FI": ".HE",  "AT": ".VI",
    "BE": ".BR",  "PT": ".LS",  "HK": ".HK",  "JP": ".T",
    "AU": ".AX",  "NZ": ".NZ",  "KR": ".KS",  "IN": ".NS",
    "SG": ".SI",  "CN": ".SS",  "CA": ".TO",  "MX": ".MX",
    "BR": ".SA",  "ZA": ".JO",
}

# Sector synthetic overrides by GICS-like code from vl_branche_cd
SECTOR_MAP = {
    "1000": "Energy", "1010": "Energy", "1500": "Materials",
    "2000": "Industrials", "2010": "Industrials", "2020": "Industrials", "2030": "Industrials",
    "2500": "Consumer Discretionary", "2510": "Consumer Discretionary",
    "2520": "Consumer Discretionary", "2530": "Consumer Discretionary",
    "3000": "Consumer Staples", "3010": "Consumer Staples", "3020": "Consumer Staples",
    "3510": "Health Care", "3520": "Health Care",
    "4010": "Financials", "4020": "Financials", "4030": "Financials",
    "4510": "Information Technology", "4520": "Information Technology", "4530": "Information Technology",
    "5010": "Communication Services", "5020": "Communication Services",
    "5510": "Utilities",
    "6010": "Real Estate",
}

ESG_LABEL_MAP = {
    "910": "AAA", "920": "AA", "930": "A", "940": "BBB",
    "950": "BB", "960": "B", "970": "CCC", "980": "CC", "990": "C",
}


def country_from_isin(isin: str) -> str:
    prefix = isin[:2].upper()
    return ISIN_COUNTRY.get(prefix, "")


def yf_ticker(isin: str, ticker_csv: str, country: str) -> str:
    """Construct a best-guess Yahoo Finance ticker symbol."""
    if not ticker_csv:
        return ""
    suffix = EXCHANGE_SUFFIX.get(country, "")
    if country == "US":
        return ticker_csv  # US tickers need no suffix on Yahoo
    return f"{ticker_csv}{suffix}"


def safe_float(val, default=None) -> float | None:
    try:
        f = float(val)
        return None if (f != f) else f  # NaN check
    except (TypeError, ValueError):
        return default


# ── CSV loading ────────────────────────────────────────────────────────────────

def load_csv(path: str) -> pd.DataFrame:
    """Parse FINFOX CSV format (semicolon-delimited, comment lines starting with #)."""
    headers = []
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if line.startswith("#") or line.startswith("IN_"):
                continue
            parts = line.split(";")
            if not headers:
                headers = parts
                continue
            rows.append(dict(zip(headers, parts)))
    return pd.DataFrame(rows)


# ── Equity ingestion ────────────────────────────────────────────────────────────

def ingest_equities(df: pd.DataFrame, limit: int | None, fetch_live: bool) -> list[EquityRecord]:
    eq_df = df[df["class"] == "equity"].copy()
    eq_df = eq_df[eq_df["isin"].str.len() == 12]  # valid ISINs only
    if limit:
        eq_df = eq_df.head(limit)

    records: list[EquityRecord] = []
    total = len(eq_df)
    log.info("Processing %d equities (live fetch: %s)", total, fetch_live)

    for i, (_, row) in enumerate(eq_df.iterrows()):
        isin = row.get("isin", "")
        valor = row.get("valorenNr", "")
        ticker_csv = row.get("tickerSymbol", "")
        currency = row.get("nominalCurrency", "")
        issuer = row.get("issuerId", "")
        name_de = row.get("name@de", "")
        short_de = row.get("shortName@de", "")
        branche = row.get("vl_branche_cd", "")
        esg_code = row.get("esg_rating_label", row.get("esg_rating", ""))
        country = country_from_isin(isin)

        rec = EquityRecord(
            isin=isin,
            valor_nr=valor,
            name=name_de,
            short_name=short_de,
            ticker=ticker_csv,
            nominal_currency=currency,
            issuer_name=issuer,
            country=country,
            sector=SECTOR_MAP.get(branche, ""),
            esg_label=ESG_LABEL_MAP.get(esg_code, ""),
            fetched_at=datetime.utcnow().isoformat(),
        )

        if fetch_live and ticker_csv:
            yf_sym = yf_ticker(isin, ticker_csv, country)
            try:
                info = yf.Ticker(yf_sym).info
                rec.name = info.get("longName") or name_de
                rec.exchange_mic = info.get("exchange", "")
                rec.sector = info.get("sector") or rec.sector
                rec.industry = info.get("industry", "")
                rec.country = info.get("country", country) or country
                rec.description = (info.get("longBusinessSummary") or "")[:500]
                rec.last_price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
                rec.price_currency = info.get("currency", currency)
                rec.market_cap = safe_float(info.get("marketCap"))
                rec.shares_outstanding = safe_float(info.get("sharesOutstanding"))
                rec.pe_ratio = safe_float(info.get("trailingPE"))
                rec.dividend_yield = safe_float(info.get("dividendYield"))
                rec.beta = safe_float(info.get("beta"))
                rec.esg_score = safe_float(info.get("esgScores", {}).get("totalEsg") if isinstance(info.get("esgScores"), dict) else None)
                rec.source = "yfinance"
                if i % 20 == 0:
                    log.info("  [%d/%d] %s (%s) → price %s %s", i + 1, total, isin, yf_sym, rec.last_price, rec.price_currency)
                time.sleep(0.25)  # polite rate limit
            except Exception as e:
                log.debug("  yfinance failed for %s (%s): %s", isin, yf_sym, e)
                _fill_synthetic_equity(rec, currency)
        else:
            _fill_synthetic_equity(rec, currency)

        records.append(rec)

    return records


def _fill_synthetic_equity(rec: EquityRecord, currency: str) -> None:
    """Fill realistic-but-synthetic market data when live fetch is skipped/fails."""
    if not rec.sector:
        rec.sector = random.choice([
            "Financials", "Information Technology", "Health Care",
            "Industrials", "Consumer Staples", "Consumer Discretionary",
            "Materials", "Energy", "Communication Services", "Utilities",
        ])
    rec.last_price = round(random.uniform(10, 800), 2)
    rec.price_currency = currency or "CHF"
    rec.market_cap = round(rec.last_price * random.uniform(50e6, 500e9), 0)
    rec.shares_outstanding = round(rec.market_cap / rec.last_price, 0) if rec.last_price else None
    rec.pe_ratio = round(random.uniform(8, 40), 1)
    rec.dividend_yield = round(random.uniform(0, 0.06), 4)
    rec.beta = round(random.uniform(0.4, 1.8), 2)
    rec.source = "synthetic"


# ── Bond ingestion ──────────────────────────────────────────────────────────────

def ingest_bonds(df: pd.DataFrame, limit: int | None) -> list[BondRecord]:
    bond_df = df[df["class"] == "simpleBond"].copy()
    bond_df = bond_df[bond_df["isin"].str.len() == 12]
    if limit:
        bond_df = bond_df.head(limit)

    records: list[BondRecord] = []
    log.info("Processing %d bonds", len(bond_df))

    for _, row in bond_df.iterrows():
        isin = row.get("isin", "")
        valor = row.get("valorenNr", "")
        name_de = (row.get("name@de", "") or "").replace("\xa0", " ").strip()
        short_de = (row.get("shortName@de", "") or "").replace("\xa0", " ").strip()
        currency = row.get("nominalCurrency", "")
        issuer = row.get("issuerId", "")
        rating = row.get("rating", "")
        interest_type_raw = row.get("interestType", "fixedinterest")
        coupon_str = row.get("actInterestRate", "")
        maturity = row.get("maturityDate", "")
        callable_str = row.get("isCallable", "false")
        duration_str = row.get("duration", "")
        country = country_from_isin(isin)

        interest_type = "floating" if "float" in (interest_type_raw or "").lower() else "fixed"
        coupon = safe_float(coupon_str)
        if coupon is not None and coupon > 1:
            coupon = coupon / 100  # convert percent to fraction

        duration = safe_float(duration_str)
        ytm = _estimate_ytm(coupon, maturity, duration)

        # Derive sector from issuer name heuristics
        sector = _bond_sector(issuer)

        rec = BondRecord(
            isin=isin,
            valor_nr=valor,
            name=name_de,
            short_name=short_de,
            nominal_currency=currency,
            issuer_name=issuer,
            issuer_country=country,
            sector=sector,
            coupon_rate=coupon,
            interest_type=interest_type,
            maturity_date=maturity,
            is_callable=callable_str.lower() == "true",
            duration=duration,
            yield_to_maturity=ytm,
            last_price=_estimate_bond_price(coupon, ytm),
            rating=rating,
            fetched_at=datetime.utcnow().isoformat(),
            source="csv_seed",
        )
        records.append(rec)

    return records


def _estimate_ytm(coupon: float | None, maturity: str, duration: float | None) -> float | None:
    """Rough YTM estimate: coupon + credit spread noise."""
    if coupon is None:
        return None
    spread = random.uniform(-0.003, 0.015)
    return round(coupon + spread, 4)


def _estimate_bond_price(coupon: float | None, ytm: float | None) -> float | None:
    """Simplified price estimate as % of face value."""
    if coupon is None or ytm is None or ytm <= 0:
        return None
    if abs(coupon - ytm) < 0.001:
        return 100.0
    return round(100.0 + (coupon - ytm) * 5 * 100, 2)  # rough approximation


def _bond_sector(issuer: str) -> str:
    issuer_lower = (issuer or "").lower()
    if any(w in issuer_lower for w in ["bank", "credit", "finance", "invest", "capital", "asset"]):
        return "Financials"
    if any(w in issuer_lower for w in ["pharma", "roche", "novartis", "health", "medical"]):
        return "Health Care"
    if any(w in issuer_lower for w in ["elektro", "power", "energie", "energy", "gas", "strom"]):
        return "Utilities"
    if any(w in issuer_lower for w in ["real estate", "immobil", "property", "wohn"]):
        return "Real Estate"
    if any(w in issuer_lower for w in ["tech", "software", "digital", "data", "systems"]):
        return "Information Technology"
    if any(w in issuer_lower for w in ["government", "republic", "canton", "kanton", "gemeinde", "bundesrepublik"]):
        return "Government"
    return "Industrials"


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest instrument universe from CSV seeds")
    parser.add_argument("--csv", default="/Users/danielwirth/PycharmProjects/financial-advisory-project/data/IN_INSTRUMENTS_COMPLETE.csv",
                        help="Path to IN_INSTRUMENTS_COMPLETE.csv")
    parser.add_argument("--out", default="data/universe", help="Output directory for parquet files")
    parser.add_argument("--limit", type=int, default=None, help="Max instruments per class (for dev runs)")
    parser.add_argument("--live", action="store_true", help="Fetch live data from yfinance (slow, rate-limited)")
    args = parser.parse_args()

    log.info("Loading CSV from %s", args.csv)
    df = load_csv(args.csv)
    log.info("Loaded %d instruments across %d classes", len(df), df["class"].nunique())

    store = ParquetUniverseStore(args.out)

    # Equities
    equities = ingest_equities(df, limit=args.limit, fetch_live=args.live)
    store.save_equities(equities)
    log.info("Saved %d equity records → %s/equity.parquet", len(equities), args.out)

    # Bonds
    bonds = ingest_bonds(df, limit=args.limit)
    store.save_bonds(bonds)
    log.info("Saved %d bond records → %s/simpleBond.parquet", len(bonds), args.out)

    # Summary
    snap = store.snapshot()
    for cls, info in snap.items():
        log.info("Snapshot %s: %s", cls, info)


if __name__ == "__main__":
    main()
