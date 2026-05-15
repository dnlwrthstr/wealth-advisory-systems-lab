"""
Instrument universe ingestion — fetches master and market data from internet.

Reads seeds.parquet (produced by extract_universe_seeds.py), then:
  --step master  : fetch instrument master (issuer, sector, country, terms)
  --step market  : fetch market snapshots (price, cap, PE, YTM)
  --step all     : both in sequence (default)

Without --live, synthetic data is generated for all instruments (instant, for dev).
With --live, yfinance is called per instrument (slow, real data).

Usage:
    python scripts/ingest_universe.py --step all
    python scripts/ingest_universe.py --step master --live --type equity
    python scripts/ingest_universe.py --step market --live --limit 100
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yfinance as yf

from universe.schemas import BondMaster, EquityMaster, InstrumentSeed, MarketSnapshot
from universe.store import ParquetUniverseStore

log = logging.getLogger("ingest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Reference tables ───────────────────────────────────────────────────────────

# ISIN country prefix → ISO 3166-1 alpha-2
ISIN_COUNTRY: dict[str, str] = {
    p: p for p in [
        "AD","AE","AG","AL","AM","AO","AR","AT","AU","AZ","BA","BB","BD","BE",
        "BG","BH","BI","BN","BO","BR","BS","BT","BW","BY","BZ","CA","CD","CF",
        "CG","CH","CI","CL","CM","CN","CO","CR","CU","CV","CY","CZ","DE","DJ",
        "DK","DM","DO","DZ","EC","EE","EG","ER","ES","ET","FI","FJ","FR","GA",
        "GB","GD","GE","GH","GM","GN","GQ","GR","GT","GW","GY","HK","HN","HR",
        "HT","HU","ID","IE","IL","IN","IQ","IR","IS","IT","JM","JO","JP","KE",
        "KG","KH","KI","KM","KN","KP","KR","KW","KZ","LA","LB","LC","LI","LK",
        "LR","LS","LT","LU","LV","LY","MA","MC","MD","ME","MG","MH","MK","ML",
        "MM","MN","MR","MT","MU","MV","MW","MX","MY","MZ","NA","NE","NG","NI",
        "NL","NO","NP","NR","NZ","OM","PA","PE","PG","PH","PK","PL","PT","PW",
        "PY","QA","RO","RS","RU","RW","SA","SB","SC","SD","SE","SG","SI","SK",
        "SL","SM","SN","SO","SR","SS","ST","SV","SY","SZ","TD","TG","TH","TJ",
        "TL","TM","TN","TO","TR","TT","TV","TW","TZ","UA","UG","US","UY","UZ",
        "VA","VC","VE","VN","VU","WS","XS","YE","ZA","ZM","ZW",
    ]
}

# ISIN country prefix → Yahoo Finance exchange suffix
EXCHANGE_SUFFIX: dict[str, str] = {
    "CH": ".SW", "DE": ".DE", "FR": ".PA", "GB": ".L",
    "IT": ".MI", "ES": ".MC", "NL": ".AS", "SE": ".ST",
    "DK": ".CO", "NO": ".OL", "FI": ".HE", "AT": ".VI",
    "BE": ".BR", "PT": ".LS", "HK": ".HK", "JP": ".T",
    "AU": ".AX", "NZ": ".NZ", "KR": ".KS", "IN": ".NS",
    "SG": ".SI", "CA": ".TO", "MX": ".MX", "BR": ".SA",
    "ZA": ".JO",
}

# vl_branche_cd → GICS sector (equities only — not used after seed extraction,
# but kept here for synthetic fallback)
_SECTORS = [
    "Financials", "Information Technology", "Health Care", "Industrials",
    "Consumer Staples", "Consumer Discretionary", "Materials", "Energy",
    "Communication Services", "Utilities", "Real Estate",
]

_BOND_SECTORS = [
    "Financials", "Government", "Utilities", "Industrials",
    "Real Estate", "Health Care", "Consumer Staples",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(val) -> Optional[float]:
    try:
        f = float(val)
        return None if f != f else f  # NaN → None
    except (TypeError, ValueError):
        return None


def _country_from_isin(isin: str) -> str:
    return ISIN_COUNTRY.get(isin[:2].upper(), "")


def _yahoo_symbol(seed: InstrumentSeed) -> str:
    """Best-guess Yahoo Finance symbol for an equity seed."""
    ticker = seed.ticker.strip()
    if not ticker:
        return ""
    country = _country_from_isin(seed.isin)
    if country == "US":
        return ticker
    suffix = EXCHANGE_SUFFIX.get(country, "")
    return f"{ticker}{suffix}"


# ── Master ingestion ───────────────────────────────────────────────────────────

def ingest_equity_master(seeds: list[InstrumentSeed], live: bool) -> list[EquityMaster]:
    log.info("Equity master: %d seeds (live=%s)", len(seeds), live)
    records: list[EquityMaster] = []

    for i, seed in enumerate(seeds):
        rec = EquityMaster(
            isin=seed.isin,
            valor_nr=seed.valor_nr,
            instrument_type=seed.instrument_type,
            name=seed.name,
            ticker=seed.ticker,
            nominal_currency=seed.nominal_currency,
            country=_country_from_isin(seed.isin),
            fetched_at=_now(),
        )

        if live and seed.ticker:
            sym = _yahoo_symbol(seed)
            try:
                info = yf.Ticker(sym).info
                if info.get("quoteType"):  # valid response
                    rec.name = info.get("longName") or seed.name
                    rec.exchange_mic = info.get("exchange", "")
                    rec.sector = info.get("sector", "")
                    rec.industry = info.get("industry", "")
                    rec.country = info.get("country", rec.country) or rec.country
                    rec.issuer_name = info.get("longName") or seed.name
                    rec.description = (info.get("longBusinessSummary") or "")[:500]
                    rec.source = "yfinance"
                    if i % 50 == 0:
                        log.info("  [%d] %s (%s) sector=%s", i, seed.isin, sym, rec.sector)
                    time.sleep(0.25)
            except Exception as exc:
                log.debug("  yfinance failed %s (%s): %s", seed.isin, sym, exc)
                _synthetic_equity_master(rec)
        else:
            _synthetic_equity_master(rec)

        records.append(rec)

    return records


def _synthetic_equity_master(rec: EquityMaster) -> None:
    if not rec.sector:
        rec.sector = random.choice(_SECTORS)
    if not rec.issuer_name:
        rec.issuer_name = rec.name
    rec.source = "synthetic"


def ingest_bond_master(seeds: list[InstrumentSeed], raw_df, live: bool) -> list[BondMaster]:
    """Bond master uses CSV terms (coupon, maturity, rating) as the source of truth —
    these are fundamental contractual terms, not market data. Only issuer metadata
    could be enriched from internet, but yfinance doesn't support bonds."""
    log.info("Bond master: %d seeds", len(seeds))

    # Index raw CSV rows by isin for quick lookup
    csv_by_isin: dict[str, dict] = {}
    if raw_df is not None and not raw_df.empty:
        for _, row in raw_df.iterrows():
            isin = row.get("isin", "")
            if len(isin) == 12:
                csv_by_isin[isin] = row.to_dict()

    records: list[BondMaster] = []
    for seed in seeds:
        row = csv_by_isin.get(seed.isin, {})
        coupon_str = row.get("actInterestRate", "")
        coupon = _safe_float(coupon_str)
        if coupon is not None and coupon > 1:
            coupon = round(coupon / 100, 6)  # percent → fraction

        interest_type_raw = row.get("interestType", "fixedinterest")
        interest_type = "floating" if "float" in (interest_type_raw or "").lower() else "fixed"

        maturity = row.get("maturityDate", "")
        callable_str = row.get("isCallable", "false")
        rating = row.get("rating", "")
        duration = _safe_float(row.get("duration", ""))
        issuer = row.get("issuerId", "")

        rec = BondMaster(
            isin=seed.isin,
            valor_nr=seed.valor_nr,
            instrument_type=seed.instrument_type,
            name=seed.name,
            nominal_currency=seed.nominal_currency,
            issuer_name=issuer or seed.name,
            issuer_country=_country_from_isin(seed.isin),
            sector=_bond_sector(issuer),
            coupon_rate=coupon,
            interest_type=interest_type,
            maturity_date=maturity,
            is_callable=(callable_str or "false").lower() == "true",
            rating=rating,
            source="csv_terms",
            fetched_at=_now(),
        )
        records.append(rec)

    return records


def _bond_sector(issuer: str) -> str:
    lower = (issuer or "").lower()
    if any(w in lower for w in ["bank", "credit", "finance", "invest", "capital", "versicher"]):
        return "Financials"
    if any(w in lower for w in ["pharma", "roche", "novartis", "health", "medical", "spital"]):
        return "Health Care"
    if any(w in lower for w in ["elektro", "power", "energie", "energy", "gas", "strom", "utility"]):
        return "Utilities"
    if any(w in lower for w in ["real estate", "immobil", "property", "wohn", "realty"]):
        return "Real Estate"
    if any(w in lower for w in ["tech", "software", "digital", "data", "systems"]):
        return "Information Technology"
    if any(w in lower for w in ["government", "republic", "canton", "kanton", "gemeinde",
                                  "bundesrepublik", "confederation", "bundesland"]):
        return "Government"
    return "Industrials"


# ── Market snapshot ingestion ──────────────────────────────────────────────────

def ingest_equity_snapshots(equities: list[EquityMaster], live: bool) -> list[MarketSnapshot]:
    log.info("Equity snapshots: %d instruments (live=%s)", len(equities), live)
    snapshots: list[MarketSnapshot] = []
    as_of = _now()

    for i, eq in enumerate(equities):
        snap = MarketSnapshot(isin=eq.isin, instrument_type=eq.instrument_type, as_of=as_of)

        if live and eq.ticker:
            sym = _yahoo_symbol(_seed_from_equity(eq))
            try:
                fi = yf.Ticker(sym).fast_info
                snap.last_price = _safe_float(getattr(fi, "last_price", None))
                snap.price_currency = getattr(fi, "currency", eq.nominal_currency) or eq.nominal_currency
                snap.market_cap = _safe_float(getattr(fi, "market_cap", None))
                snap.shares_outstanding = _safe_float(getattr(fi, "shares", None))
                snap.week_52_high = _safe_float(getattr(fi, "year_high", None))
                snap.week_52_low = _safe_float(getattr(fi, "year_low", None))
                # pe, beta, dividend_yield require full .info
                info = yf.Ticker(sym).info
                snap.pe_ratio = _safe_float(info.get("trailingPE"))
                snap.forward_pe = _safe_float(info.get("forwardPE"))
                snap.dividend_yield = _safe_float(info.get("dividendYield"))
                snap.beta = _safe_float(info.get("beta"))
                snap.source = "yfinance"
                if i % 50 == 0:
                    log.info("  [%d] %s price=%s", i, eq.isin, snap.last_price)
                time.sleep(0.3)
            except Exception as exc:
                log.debug("  snapshot failed %s: %s", eq.isin, exc)
                _synthetic_equity_snapshot(snap, eq.nominal_currency)
        else:
            _synthetic_equity_snapshot(snap, eq.nominal_currency)

        snapshots.append(snap)

    return snapshots


def _seed_from_equity(eq: EquityMaster) -> InstrumentSeed:
    return InstrumentSeed(
        isin=eq.isin, valor_nr=eq.valor_nr, instrument_type=eq.instrument_type,
        name=eq.name, ticker=eq.ticker, nominal_currency=eq.nominal_currency,
    )


def _synthetic_equity_snapshot(snap: MarketSnapshot, currency: str) -> None:
    snap.last_price = round(random.uniform(5, 900), 2)
    snap.price_currency = currency or "USD"
    snap.market_cap = round(snap.last_price * random.uniform(10e6, 300e9), 0)
    snap.shares_outstanding = round(snap.market_cap / snap.last_price, 0) if snap.last_price else None
    snap.pe_ratio = round(random.uniform(7, 45), 1)
    snap.forward_pe = round(snap.pe_ratio * random.uniform(0.8, 1.1), 1)
    snap.dividend_yield = round(random.uniform(0.0, 0.06), 4)
    snap.beta = round(random.uniform(0.3, 2.0), 2)
    snap.week_52_high = round((snap.last_price or 100) * random.uniform(1.0, 1.5), 2)
    snap.week_52_low = round((snap.last_price or 100) * random.uniform(0.5, 1.0), 2)
    snap.source = "synthetic"


def ingest_bond_snapshots(bonds: list[BondMaster]) -> list[MarketSnapshot]:
    """Bond market data from internet is generally not freely available.
    Derive price estimate from coupon vs synthetic YTM."""
    log.info("Bond snapshots: %d instruments (synthetic)", len(bonds))
    as_of = _now()
    snapshots: list[MarketSnapshot] = []

    for bond in bonds:
        snap = MarketSnapshot(isin=bond.isin, instrument_type=bond.instrument_type, as_of=as_of)
        coupon = bond.coupon_rate or 0.0
        # Simulate YTM = coupon + credit spread noise
        spread = random.uniform(-0.003, 0.02)
        ytm = max(coupon + spread, 0.001)
        snap.yield_to_maturity = round(ytm, 4)

        # Rough dirty price: par adjusted for coupon vs yield difference
        if ytm > 0:
            price_pct = 100.0 + (coupon - ytm) * 4 * 100
            snap.last_price = round(max(min(price_pct, 130.0), 70.0), 2)
        snap.price_currency = bond.nominal_currency

        # Synthetic spread in basis points over benchmark
        snap.spread_bps = round(spread * 10_000, 0)
        snap.source = "synthetic"
        snapshots.append(snap)

    return snapshots


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest universe master and market data from internet")
    parser.add_argument("--seeds", default="data/universe", help="Directory containing seeds.parquet")
    parser.add_argument("--out", default="data/universe", help="Output directory")
    parser.add_argument("--step", choices=["master", "market", "all"], default="all")
    parser.add_argument("--type", dest="instrument_type", default=None,
                        help="Filter to a single instrument_type (e.g. equity)")
    parser.add_argument("--limit", type=int, default=None, help="Cap per type (dev mode)")
    parser.add_argument("--live", action="store_true", help="Fetch live data from yfinance")
    args = parser.parse_args()

    store = ParquetUniverseStore(args.out)
    seed_store = ParquetUniverseStore(args.seeds)

    equity_seeds = seed_store.list_seeds("equity")
    bond_seeds = [
        s for s in seed_store.list_seeds()
        if s.instrument_type in {"simpleBond", "floater", "convertibleBond", "moneyMarket"}
    ]

    if args.instrument_type:
        equity_seeds = [s for s in equity_seeds if s.instrument_type == args.instrument_type]
        bond_seeds = [s for s in bond_seeds if s.instrument_type == args.instrument_type]

    if args.limit:
        equity_seeds = equity_seeds[:args.limit]
        bond_seeds = bond_seeds[:args.limit]

    # Load raw CSV once for bond term lookup (bond master uses CSV terms)
    raw_df = None
    if args.step in ("master", "all") and bond_seeds:
        csv_path = "/Users/danielwirth/PycharmProjects/financial-advisory-project/data/IN_INSTRUMENTS_COMPLETE.csv"
        log.info("Loading bond terms from %s", csv_path)
        from extract_universe_seeds import parse_finfox_csv
        raw_df = parse_finfox_csv(csv_path)

    if args.step in ("master", "all"):
        if equity_seeds:
            equities = ingest_equity_master(equity_seeds, args.live)
            store.save_equities(equities)
            log.info("Saved %d equity master records", len(equities))

        if bond_seeds:
            bonds = ingest_bond_master(bond_seeds, raw_df, args.live)
            store.save_bonds(bonds)
            log.info("Saved %d bond master records", len(bonds))

    if args.step in ("market", "all"):
        equities = store.search_equities(limit=10_000)
        if args.limit:
            equities = equities[:args.limit]
        if equities:
            eq_snaps = ingest_equity_snapshots(equities, args.live)
            store.save_snapshots(eq_snaps)
            log.info("Saved %d equity snapshots", len(eq_snaps))

        bonds = store.search_bonds(limit=10_000)
        if args.limit:
            bonds = bonds[:args.limit]
        if bonds:
            bond_snaps = ingest_bond_snapshots(bonds)
            store.save_snapshots(bond_snaps)
            log.info("Saved %d bond snapshots", len(bond_snaps))

    snap = store.universe_snapshot()
    for layer, info in snap.items():
        log.info("Snapshot %-15s %s", layer + ":", info.get("count", 0))


if __name__ == "__main__":
    main()
