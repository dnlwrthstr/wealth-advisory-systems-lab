"""Fetch real equities from Yahoo Finance and emit EquityGolden NDJSON.

Reads a named ticker universe (SMI, S&P 500, …) from Wikipedia, queries
yfinance for each ticker, builds a validated `EquityGolden` pydantic
instance, and writes one document per line to a UTF-8 NDJSON file.

The NDJSON file is the replay artifact for the gold stage — bulk-load
it into OpenSearch with `pipeline.gold.load`.

Yahoo coverage is partial: identifiers, listing, prices, sector,
market cap, EPS, P/E and dividend yield populate well. LEI, FIGI, CFI,
regulatory flags and credit/ESG profiles are left blank.
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from universe.models import (
    CurrencyAmount,
    Currency,
    Country,
    DividendPolicy,
    EquityGolden,
    FinancialInstrumentIdentification,
    GoldenRecordMeta,
    IndustrySector,
    IssuerSnapshot,
    KeyFigures,
    ListingSnapshot,
    MarketDataSnapshotEmbedded,
    Price,
    SourceAttribution,
)

log = logging.getLogger("equity_yahoo")

SCHEMA_VERSION = "0.2.0"
WIKI_USER_AGENT = (
    "wealth-advisory-systems-lab/0.1 "
    "(https://github.com/dnlwrthstr/wealth-advisory-systems-lab)"
)
WIKI_FETCH_TIMEOUT = 30
YFINANCE_RETRY = 2  # one retry on failure


# Yahoo exchange code → ISO 10383 MIC. Ported from pms-ontology; covers
# the majors. Unknown codes pass through unchanged.
YAHOO_EXCHANGE_TO_MIC: Dict[str, str] = {
    "NMS": "XNAS", "NGM": "XNAS", "NCM": "XNAS",
    "NYQ": "XNYS", "ASE": "XASE", "PCX": "ARCX", "BATS": "BATS",
    "LSE": "XLON",
    "GER": "XETR", "FRA": "XFRA",
    "PAR": "XPAR", "AMS": "XAMS", "BRU": "XBRU",
    "EBS": "XSWX", "SWX": "XSWX",
    "MIL": "MTAA", "MAD": "XMAD", "STO": "XSTO",
    "CPH": "XCSE", "HEL": "XHEL", "OSL": "XOSL",
    "TYO": "XTKS", "JPX": "XJPX",
    "HKG": "XHKG", "SHH": "XSHG", "SHZ": "XSHE",
    "ASX": "XASX", "TOR": "XTSE",
    "VIE": "XWBO", "ATH": "ASEX", "WAR": "XWAR",
    "BUE": "XBUE", "MEX": "XMEX", "SAO": "BVMF",
}

YAHOO_QUOTE_TYPE_TO_SUBTYPE: Dict[str, str] = {
    "EQUITY": "commonStock",
    "ADR": "adr",
    "GDR": "gdr",
    "REIT": "reit",
}

COUNTRY_NAME_TO_ISO2: Dict[str, str] = {
    "United States": "US", "United Kingdom": "GB",
    "Germany": "DE", "France": "FR", "Switzerland": "CH",
    "Netherlands": "NL", "Belgium": "BE", "Italy": "IT",
    "Spain": "ES", "Sweden": "SE", "Denmark": "DK",
    "Norway": "NO", "Finland": "FI", "Ireland": "IE",
    "Austria": "AT", "Luxembourg": "LU", "Portugal": "PT",
    "Poland": "PL", "Greece": "GR", "Czech Republic": "CZ",
    "Hungary": "HU", "Japan": "JP", "China": "CN",
    "Hong Kong": "HK", "Taiwan": "TW", "South Korea": "KR",
    "Singapore": "SG", "Australia": "AU", "New Zealand": "NZ",
    "Canada": "CA", "Mexico": "MX", "Brazil": "BR",
    "Argentina": "AR", "India": "IN", "Israel": "IL",
    "South Africa": "ZA", "Russia": "RU",
}


# Wikipedia universe sources. Same shape as pms-ontology so the schema
# is recognisable; SMI is the default smoke-test universe.
UNIVERSE_SOURCES: Dict[str, Dict[str, Any]] = {
    "smi": {
        "url": "https://en.wikipedia.org/wiki/Swiss_Market_Index",
        "ticker_column_candidates": ["Ticker", "Symbol"],
        "suffix": ".SW",
    },
    "sp500": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "table_index": 0,
        "ticker_column": "Symbol",
        "suffix": "",
    },
    "nasdaq100": {
        "url": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "ticker_column_candidates": ["Ticker", "Symbol"],
        "suffix": "",
    },
    "dax40": {
        "url": "https://en.wikipedia.org/wiki/DAX",
        "ticker_column_candidates": ["Ticker", "Ticker symbol", "Symbol"],
        "suffix": ".DE",
    },
    "ftse100": {
        "url": "https://en.wikipedia.org/wiki/FTSE_100_Index",
        "ticker_column_candidates": ["EPIC", "Ticker", "Symbol"],
        "suffix": ".L",
    },
}


# ---------------------------------------------------------------------------
# Universe loading
# ---------------------------------------------------------------------------

def _fetch_wikipedia(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=WIKI_FETCH_TIMEOUT) as r:
            return r.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        sys.exit(f"Wikipedia fetch failed for {url}: {exc}")


def load_universe(name: str) -> List[str]:
    if name not in UNIVERSE_SOURCES:
        raise ValueError(f"Unknown universe: {name!r}. Known: {list(UNIVERSE_SOURCES)}")
    spec = UNIVERSE_SOURCES[name]

    import pandas as pd

    html = _fetch_wikipedia(spec["url"])
    tables = pd.read_html(io.StringIO(html))

    df = None
    ticker_col: Optional[str] = None
    if spec.get("table_index") is not None:
        df = tables[spec["table_index"]]
        ticker_col = spec.get("ticker_column")
    else:
        for candidate in spec["ticker_column_candidates"]:
            for table in tables:
                cols = [
                    " ".join(str(c) for c in col).strip()
                    if isinstance(col, tuple)
                    else str(col).strip()
                    for col in table.columns
                ]
                table.columns = cols
                if candidate in cols:
                    df, ticker_col = table, candidate
                    break
            if df is not None:
                break

    if df is None or ticker_col is None:
        raise RuntimeError(
            f"Ticker column not found at {spec['url']}. "
            f"Tried: {spec.get('ticker_column_candidates') or spec.get('ticker_column')}"
        )

    raw = df[ticker_col].astype(str).str.strip()
    suffix = spec.get("suffix", "")
    tickers: List[str] = []
    for t in raw.tolist():
        if not t or t.lower() == "nan":
            continue
        full = t if (not suffix or t.endswith(suffix)) else t + suffix
        if full not in tickers:
            tickers.append(full)
    return tickers


# ---------------------------------------------------------------------------
# Yahoo → EquityGolden
# ---------------------------------------------------------------------------

def _safe(info: Dict[str, Any], key: str) -> Any:
    v = info.get(key)
    if v in (None, "", "N/A"):
        return None
    return v


def _country(name: Optional[str]) -> Optional[Country]:
    if not name:
        return None
    iso2 = COUNTRY_NAME_TO_ISO2.get(name)
    return Country(iso2) if iso2 else None


def _exchange_to_mic(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return YAHOO_EXCHANGE_TO_MIC.get(code, code)


def _epoch_to_iso(epoch: Optional[int]) -> Optional[str]:
    if not epoch:
        return None
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).date().isoformat()


def yahoo_info_to_golden(
    ticker_symbol: str,
    info: Dict[str, Any],
    isin: Optional[str],
    run_id: str,
    now: datetime,
    seed: Optional[Dict[str, Any]] = None,
) -> EquityGolden:
    """Map yfinance `Ticker.info` + ISIN to a validated EquityGolden.

    When `seed` is provided (parquet-seeded mode) the seed supplies the
    fallbacks for currency, name, ticker, valor and ISIN — Yahoo's values
    overwrite when present, but a record can still be built if Yahoo
    returns nothing.
    """
    now_iso = now.isoformat()
    seed = seed or {}

    # Prefer seed ISIN (parquet ground truth) over the value Yahoo reports.
    if seed.get("isin"):
        isin = seed["isin"]

    currency_code = (
        _safe(info, "currency")
        or _safe(info, "financialCurrency")
        or seed.get("nominal_currency")
    )
    if not currency_code:
        raise ValueError(f"{ticker_symbol}: no currency from yfinance or seed")
    currency = Currency(currency_code)

    mic = _exchange_to_mic(_safe(info, "exchange")) or seed.get("exchange_mic")
    if not mic:
        # Derive from ISIN country as a last resort so records always have a MIC.
        country2 = (isin or "")[:2].upper()
        mic = {
            "US": "XNAS", "DE": "XETR", "CH": "XSWX", "GB": "XLON",
            "FR": "XPAR", "NL": "XAMS", "IT": "MTAA", "ES": "XMAD",
            "JP": "XTKS", "HK": "XHKG", "AU": "XASX", "CA": "XTSE",
        }.get(country2, "XOFF")

    long_name = (
        _safe(info, "longName")
        or _safe(info, "shortName")
        or seed.get("name")
        or ticker_symbol
    )
    short_name = _safe(info, "shortName") or seed.get("ticker") or long_name[:32]

    sector = _safe(info, "sector") or seed.get("sector")
    industry = _safe(info, "industry") or seed.get("industry")
    quote_type = _safe(info, "quoteType")
    equity_sub_type = YAHOO_QUOTE_TYPE_TO_SUBTYPE.get(quote_type or "", "other")

    country = _country(_safe(info, "country")) or (
        Country(seed["country"]) if seed.get("country") else None
    )

    if isin and mic:
        golden_id = f"EQG-{isin}-{mic}-001"
    elif isin:
        golden_id = f"EQG-{isin}-001"
    else:
        golden_id = f"EQG-{ticker_symbol}-{mic}-001"

    identifier_list = []
    if isin:
        identifier_list.append(FinancialInstrumentIdentification(identifier=isin, type="isin"))
    if seed.get("valor_nr"):
        identifier_list.append(
            FinancialInstrumentIdentification(identifier=str(seed["valor_nr"]), type="valoren")
        )
    identifier_list.append(
        FinancialInstrumentIdentification(identifier=ticker_symbol, type="tickerSymbol")
    )

    industry_sector = None
    if sector or industry:
        industry_sector = IndustrySector(
            scheme="yahoo",
            sectorLabel=sector,
            industryLabel=industry,
            canonicalLabel=sector,
        )

    first_trading_date = _epoch_to_iso(_safe(info, "firstTradeDateEpochUtc"))
    primary_listing = ListingSnapshot(
        mic=mic,
        ticker=ticker_symbol,
        listingCurrency=currency,
        status="active",
        isPrimary=True,
        firstTradingDate=first_trading_date,
    )

    # Market data — pick the most-current available price.
    last_price = (
        _safe(info, "currentPrice")
        or _safe(info, "regularMarketPrice")
        or _safe(info, "previousClose")
    )
    md_kwargs: Dict[str, Any] = {"asOf": now_iso, "sourceMic": mic}
    if last_price is not None:
        md_kwargs["lastTradePrice"] = Price(type="actual", value=last_price, currency=currency)
    for field, key in (
        ("open", "regularMarketOpen"),
        ("high", "dayHigh"),
        ("low", "dayLow"),
        ("close", "previousClose"),
        ("volume", "volume"),
    ):
        v = _safe(info, key)
        if v is not None:
            md_kwargs[field] = v
    market_data = MarketDataSnapshotEmbedded(**md_kwargs)

    # Key figures
    kf_kwargs: Dict[str, Any] = {}
    market_cap = _safe(info, "marketCap")
    eps = _safe(info, "trailingEps")
    pe = _safe(info, "trailingPE") or _safe(info, "forwardPE")
    beta = _safe(info, "beta")
    if market_cap:
        kf_kwargs["marketCapitalization"] = CurrencyAmount(amount=market_cap, currency=currency)
    if eps is not None:
        kf_kwargs["earningsPerShare"] = CurrencyAmount(amount=eps, currency=currency)
    if pe is not None:
        kf_kwargs["priceToEarningsRatio"] = pe
    if beta is not None:
        kf_kwargs["volatility"] = beta
    key_figures = KeyFigures(**kf_kwargs) if kf_kwargs else None

    # Dividend
    dividend_yield = _safe(info, "dividendYield")
    last_div = _epoch_to_iso(_safe(info, "lastDividendDate"))
    dividend_status = bool(dividend_yield and dividend_yield > 0)
    dividend_policy = None
    if dividend_yield is not None or last_div:
        dividend_policy = DividendPolicy(
            dividendYield=dividend_yield,
            lastDividendDate=last_div,
            frequency="quarterly" if dividend_status else None,
        )

    issuer = IssuerSnapshot(
        issuerId=_safe(info, "uuid") or f"ISS-{ticker_symbol}",
        legalName=long_name,
        issuerType="corporate",
        domicileCountry=country,
        headquartersCountry=country,
    )

    populated = sum(1 for v in info.values() if v not in (None, "", "N/A"))
    quality = round(populated / max(len(info), 1), 3)
    meta = GoldenRecordMeta(
        schemaVersion=SCHEMA_VERSION,
        goldenAsOf=now_iso,
        ingestionRunId=run_id,
        sourceOfTruth=[
            SourceAttribution(fieldGroup="identifiers", source="yfinance"),
            SourceAttribution(fieldGroup="listing", source="yfinance"),
            SourceAttribution(fieldGroup="marketData", source="yfinance"),
        ],
        qualityScore=quality,
        isActive=True,
    )

    return EquityGolden(
        goldenId=golden_id,
        identifierList=identifier_list,
        longName=long_name,
        shortName=short_name,
        assetClass="Equity / Common Stock",
        assetClassId="AC-EQ-COMMON",
        equitySubType=equity_sub_type,
        industrySector=industry_sector,
        incorporationCountry=country,
        currencyOfDenomination=currency,
        sharesOutstanding=_safe(info, "sharesOutstanding"),
        firstTradingDate=first_trading_date,
        lifecycleStatus="active",
        issuer=issuer,
        primaryListing=primary_listing,
        marketData=market_data,
        dividendStatus=dividend_status,
        dividendPolicy=dividend_policy,
        keyFigures=key_figures,
        recordMeta=meta,
    )


# ---------------------------------------------------------------------------
# Per-ticker fetch with retry
# ---------------------------------------------------------------------------

def fetch_one(
    ticker_symbol: str,
    run_id: str,
    now: datetime,
    seed: Optional[Dict[str, Any]] = None,
) -> Optional[EquityGolden]:
    """Fetch yfinance info for `ticker_symbol` and build an EquityGolden.

    When `seed` is provided, the seed's identifiers + defaults are used as
    the baseline; yfinance values overwrite where present. If yfinance
    returns nothing at all, a seed-only record is still emitted (no
    market data).
    """
    import yfinance as yf

    attempt = 0
    last_exc: Optional[Exception] = None
    while attempt <= YFINANCE_RETRY:
        try:
            t = yf.Ticker(ticker_symbol)
            info = t.info or {}
            isin: Optional[str] = None
            try:
                raw_isin = (t.isin or "").strip()
                if len(raw_isin) == 12 and raw_isin.isalnum():
                    isin = raw_isin
            except Exception:  # noqa: BLE001 — Ticker.isin is flaky
                pass
            if not info:
                if seed:
                    log.info("  %s: no yfinance data, building seed-only record", ticker_symbol)
                    return yahoo_info_to_golden(ticker_symbol, {}, isin, run_id, now, seed=seed)
                raise RuntimeError("empty Ticker.info")
            return yahoo_info_to_golden(ticker_symbol, info, isin, run_id, now, seed=seed)
        except (ValueError, ValidationError) as exc:
            # Deterministic mapping failure — don't retry, just drop with warn.
            log.warning("  %s skipped: %s", ticker_symbol, exc)
            return None
        except Exception as exc:  # noqa: BLE001 — yfinance raises bare Exception too
            last_exc = exc
            attempt += 1
            if attempt <= YFINANCE_RETRY:
                time.sleep(2 ** attempt)
    if seed:
        # Yahoo unreachable but we still have the parquet seed — emit it.
        log.warning("  %s yfinance failed, falling back to seed-only", ticker_symbol)
        try:
            return yahoo_info_to_golden(ticker_symbol, {}, None, run_id, now, seed=seed)
        except (ValueError, ValidationError) as exc:
            log.warning("  %s seed-only build failed: %s", ticker_symbol, exc)
            return None
    log.warning("  %s failed after %d attempts: %s", ticker_symbol, YFINANCE_RETRY + 1, last_exc)
    return None


def write_ndjson(docs: List[EquityGolden], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(doc.model_dump_json(exclude_none=True))
            fh.write("\n")
    return len(docs)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch equities from Yahoo Finance and emit EquityGolden NDJSON."
    )
    parser.add_argument(
        "--universe", default="smi",
        choices=list(UNIVERSE_SOURCES.keys()),
        help="Named ticker universe to load (default: smi). Ignored if --from-parquet.",
    )
    parser.add_argument(
        "--from-parquet", action="store_true",
        help="Seed the run from data/universe/{seeds,equity}.parquet. ISIN and "
             "valor come from parquet; yfinance is queried per ticker (with the "
             "ISIN country → Yahoo suffix mapping) and overlays where present.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Cap on number of tickers to fetch (smoke testing).",
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        default=Path("data/opensearch/golden/equity/equities.ndjson"),
        help="Output NDJSON path (default: data/opensearch/golden/equity/equities.ndjson).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    run_id_tag = "parquet" if args.from_parquet else args.universe
    run_id = f"yahoo-{run_id_tag}-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    docs: List[EquityGolden] = []

    if args.from_parquet:
        from pipeline.silver import iter_equity_seeds, yahoo_ticker_for

        seeds = list(iter_equity_seeds())
        if args.limit:
            seeds = seeds[: args.limit]
        log.info("Parquet-seeded run: %d equity seeds", len(seeds))
        for i, seed in enumerate(seeds, 1):
            if not seed.get("ticker"):
                continue
            ticker = yahoo_ticker_for(seed.get("isin") or "", seed["ticker"])
            log.info("[%d/%d] %s (ISIN %s)", i, len(seeds), ticker, seed.get("isin"))
            doc = fetch_one(ticker, run_id, now, seed=seed)
            if doc is not None:
                docs.append(doc)
    else:
        log.info("Loading universe %r", args.universe)
        tickers = load_universe(args.universe)
        if args.limit:
            tickers = tickers[: args.limit]
        log.info("  %d tickers", len(tickers))
        for i, ticker in enumerate(tickers, 1):
            log.info("[%d/%d] %s", i, len(tickers), ticker)
            doc = fetch_one(ticker, run_id, now)
            if doc is not None:
                docs.append(doc)

    n = write_ndjson(docs, args.output)
    log.info("Wrote %d EquityGolden documents to %s", n, args.output)


if __name__ == "__main__":
    main()
