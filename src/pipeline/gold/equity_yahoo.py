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
    "EQUITY": "common_stock",
    "ADR": "adr",
    "GDR": "gdr",
    "REIT": "reit",
}

# Default CFI (ISO 10962) per equity sub-type. CFI is six chars:
#   pos 1: category    (E = Equity)
#   pos 2: subcategory (S = Shares/common, D = Depository receipts, P = Preferred)
#   pos 3: voting      (V = voting, N = non-voting, R = restricted)
#   pos 4: ownership   (U = unrestricted, R = restricted)
#   pos 5: payment     (F = fully paid)
#   pos 6: form        (R = registered, B = bearer)
# These are the conservative defaults; the real CFI for a specific share
# class can override via the find-and-parse-factsheet skill.
CFI_BY_SUBTYPE: Dict[str, str] = {
    "common_stock": "ESVUFR",
    "adr":         "EDSXFR",
    "gdr":         "EDSXFR",
    "reit":        "ESVUFR",
    "other":       "ESXXXR",
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


# SIX tickers (Yahoo .SW suffix) where yfinance's `Ticker.isin` returns
# "-". The curated table lives in `data/six_ticker_isin.yml` and is shared
# with the agentic `six_ticker_isin` source so both paths see the same
# names. Imported here for backward compatibility with anything that
# already references SMI_ISIN_MAP.
from pipeline.gold.six_ticker_isin import _load as _load_six_ticker_isin
SMI_ISIN_MAP: Dict[str, str] = _load_six_ticker_isin()


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
) -> EquityGolden:
    """Map yfinance `Ticker.info` + ISIN to a validated EquityGolden."""
    now_iso = now.isoformat()

    currency_code = _safe(info, "currency") or _safe(info, "financialCurrency")
    if not currency_code:
        raise ValueError(f"{ticker_symbol}: no currency from yfinance")
    currency = Currency(currency_code)

    mic = _exchange_to_mic(_safe(info, "exchange"))
    if not mic:
        # Derive from ISIN country as a last resort so records always have a MIC.
        country2 = (isin or "")[:2].upper()
        mic = {
            "US": "XNAS", "DE": "XETR", "CH": "XSWX", "GB": "XLON",
            "FR": "XPAR", "NL": "XAMS", "IT": "MTAA", "ES": "XMAD",
            "JP": "XTKS", "HK": "XHKG", "AU": "XASX", "CA": "XTSE",
        }.get(country2, "XOFF")

    long_name = _safe(info, "longName") or _safe(info, "shortName") or ticker_symbol
    short_name = _safe(info, "shortName") or long_name[:32]

    sector = _safe(info, "sector")
    industry = _safe(info, "industry")
    quote_type = _safe(info, "quoteType")
    equity_sub_type = YAHOO_QUOTE_TYPE_TO_SUBTYPE.get(quote_type or "", "other")

    country = _country(_safe(info, "country"))

    if isin and mic:
        golden_id = f"EQG-{isin}-{mic}-001"
    elif isin:
        golden_id = f"EQG-{isin}-001"
    else:
        golden_id = f"EQG-{ticker_symbol}-{mic}-001"

    identifier_list = []
    if isin:
        identifier_list.append(FinancialInstrumentIdentification(identifier=isin, type="isin"))
    # Deterministic CH-ISIN valor derivation — when the ISIN encodes one,
    # surface it as a separate identifier entry.
    if isin:
        from pipeline.silver import valor_from_isin
        valor_value = valor_from_isin(isin)
        if valor_value:
            identifier_list.append(
                FinancialInstrumentIdentification(identifier=valor_value, type="valoren")
            )
    identifier_list.append(
        FinancialInstrumentIdentification(identifier=ticker_symbol, type="ticker_symbol")
    )

    industry_sector = None
    if sector or industry:
        industry_sector = IndustrySector(
            sectorLabel=sector,
            industryLabel=industry,
            source="yfinance",
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

    # CFI code — derived from the equity sub-type. ISO 10962 default for
    # common stock is ESVUFR (Equity / Shares / Voting / Unrestricted /
    # Fully paid / Registered). Tagged as `derived-from-cfi-table` in the
    # provenance, separate from yfinance.
    cfi_code = CFI_BY_SUBTYPE.get(equity_sub_type, "ESXXXR")

    populated = sum(1 for v in info.values() if v not in (None, "", "N/A"))
    quality = round(populated / max(len(info), 1), 3)

    # Build provenance entries reflecting which sources actually filled what.
    sot_entries: List[SourceAttribution] = [
        SourceAttribution(fieldGroup="identifiers", source="yfinance", sourceTimestamp=now_iso),
        SourceAttribution(fieldGroup="primaryListing", source="yfinance", sourceTimestamp=now_iso),
        SourceAttribution(fieldGroup="marketData", source="yfinance", sourceTimestamp=now_iso),
        SourceAttribution(fieldGroup="classification", source="cfi-default-table", sourceTimestamp=now_iso),
    ]
    if sector or industry:
        sot_entries.append(
            SourceAttribution(fieldGroup="industrySector", source="yfinance", sourceTimestamp=now_iso)
        )

    meta = GoldenRecordMeta(
        schemaVersion=SCHEMA_VERSION,
        goldenAsOf=now_iso,
        ingestionRunId=run_id,
        sourceOfTruth=sot_entries,
        qualityScore=quality,
        isActive=True,
    )

    return EquityGolden(
        goldenId=golden_id,
        cfiCode=cfi_code,
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
) -> Optional[EquityGolden]:
    """Fetch yfinance info for `ticker_symbol` and build an EquityGolden."""
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
            # yfinance gives "-" for Swiss tickers. Fall back to the curated
            # SMI map so CH-ISIN valor derivation actually has an ISIN to bite.
            if not isin and ticker_symbol in SMI_ISIN_MAP:
                isin = SMI_ISIN_MAP[ticker_symbol]
            if not info:
                raise RuntimeError("empty Ticker.info")
            return yahoo_info_to_golden(ticker_symbol, info, isin, run_id, now)
        except (ValueError, ValidationError) as exc:
            # Deterministic mapping failure — don't retry, just drop with warn.
            log.warning("  %s skipped: %s", ticker_symbol, exc)
            return None
        except Exception as exc:  # noqa: BLE001 — yfinance raises bare Exception too
            last_exc = exc
            attempt += 1
            if attempt <= YFINANCE_RETRY:
                time.sleep(2 ** attempt)
    log.warning("  %s failed after %d attempts: %s", ticker_symbol, YFINANCE_RETRY + 1, last_exc)
    return None


def fetch_by_identifier(
    kind: str,
    value: str,
    *,
    run_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Optional[EquityGolden]:
    """Identifier-agnostic equity fetch — hands ISIN or ticker to yfinance.

    Used by the agentic source adapter at
    `pipeline.agentic.sources.equity_yahoo`. yfinance's `Ticker(isin)`
    resolves many ISINs directly; the agentic platform's `openfigi` and
    parquet_seed sources cover the rest by setting a tickerSymbol entry
    in the running state before this source is called.
    """
    if kind not in ("isin", "ticker"):
        raise ValueError(f"unsupported identifier kind {kind!r}; expected 'isin' or 'ticker'")
    if not value:
        raise ValueError("identifier value must be non-empty")
    if run_id is None:
        run_id = f"yahoo-{kind}-{uuid.uuid4().hex[:8]}"
    if now is None:
        now = datetime.now(timezone.utc)
    return fetch_one(value, run_id, now)


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
        help="Named ticker universe to load (default: smi).",
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

    run_id = f"yahoo-{args.universe}-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    docs: List[EquityGolden] = []

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
