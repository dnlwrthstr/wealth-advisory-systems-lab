"""ESMA FIRDS lookup by ISIN — equity enrichment.

FIRDS is the free authoritative source for MiFID II-reportable
instruments. Equities admitted to trading on any EU/UK/CH venue have
records here. The schema doesn't carry market tickers (so this is not
a ticker→ISIN solution), but given an ISIN it returns LEI, full
issuer name, CFI code, every venue/MIC combination and the
status/lifecycle dates per venue — material the openfigi + yahoo
sources don't supply.

FIRDS status codes are *change states* per submission, not lifecycle
states: NEWS=new record, UNCH=unchanged from prior submission,
MODI=modified, TERM=listing terminated, CANC=cancelled. A venue is
"currently listed" iff its most-recent record is NOT in {TERM, CANC}
AND its mrkt_trdng_trmination_date is empty or in the future.

CH-issued equities' SIX listing is NOT in FIRDS — Swiss issuers
report to FINMA, not ESMA. So for CH ISINs FIRDS gives us LEI + CFI
+ alternative venues, while the SIX primary listing still has to
come from yfinance.

The agentic source adapter at `pipeline.agentic.sources.equity_firds`
slots this between openfigi and equity_yahoo: openfigi seeds the FIGI
+ ticker, FIRDS adds LEI + multi-venue listings + regulator-quality
naming, equity_yahoo overlays market data on top.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from pipeline.gold._firds import solr_get

log = logging.getLogger("equity_firds")

# Fields we ask FIRDS Solr to return per equity record.
FIRDS_FL = [
    "isin",
    "lei",
    "gnr_full_name",
    "gnr_short_name",
    "gnr_cfi_code",
    "gnr_notional_curr_code",
    "mic",
    "rca_mic",
    "mrkt_trdng_start_date",
    "mrkt_trdng_trmination_date",
    "status",
    "status_label",
    "valid_from_date",
    "publication_date",
]

# FIRDS Solr ISIN-page settings. Per ISIN we get one record per venue
# per validity-window. 200 covers any real equity (Lindt PSR has 57).
FIRDS_PAGE_SIZE = 500


def fetch_firds_by_isin(isin: str) -> List[Dict[str, Any]]:
    """Return every FIRDS record for `isin` (latest_received_flag=1).

    No filtering — caller decides what to do with multi-venue rows.
    Returns [] when FIRDS has no match or the API is unreachable.
    """
    params = {
        "q": f"isin:{isin}+AND+latest_received_flag:1",
        "wt": "json",
        "rows": str(FIRDS_PAGE_SIZE),
        "fl": ",".join(FIRDS_FL),
        "sort": "valid_from_date desc",
    }
    try:
        data = solr_get(params)
    except Exception as exc:  # noqa: BLE001 — broad: HTTP / URL errors all here
        log.warning("FIRDS query failed for %s: %s", isin, exc)
        return []
    return data.get("response", {}).get("docs", []) or []


def fetch_by_isin(isin: str) -> Optional[Dict[str, Any]]:
    """Resolve `isin` to a partial EquityGolden-shaped patch.

    Returns None when FIRDS has no record for the ISIN, signalling
    "no_data" to the agentic planner. The returned dict is a partial
    patch — agentic merger uses fill-empty semantics, so caller-set
    fields (e.g. openfigi's identifierList) won't be overwritten.
    """
    docs = fetch_firds_by_isin(isin)
    if not docs:
        return None

    patch: Dict[str, Any] = {}

    long_name = _pick_long_name(docs)
    if long_name:
        patch["longName"] = long_name

    cfi = _first_non_empty(d.get("gnr_cfi_code") for d in docs)
    if cfi:
        patch["cfiCode"] = cfi

    currency = _first_non_empty(d.get("gnr_notional_curr_code") for d in docs)
    if currency:
        patch["currencyOfDenomination"] = currency

    lei = _first_non_empty(d.get("lei") for d in docs)
    if lei:
        patch["issuer"] = {
            "issuerId": f"ISS-{lei}",
            "legalName": long_name or "",
            "lei": lei,
        }

    earliest_trading = _earliest_date(d.get("mrkt_trdng_start_date") for d in docs)
    if earliest_trading:
        patch["firstTradingDate"] = earliest_trading

    patch["lifecycleStatus"] = "active" if _any_active_listing(docs) else "delisted"

    secondary = _build_secondary_listings(docs, currency)
    if secondary:
        patch["secondaryListings"] = secondary

    return patch


def _first_non_empty(iterable) -> Optional[Any]:
    """First non-empty value from the iterable, or None."""
    for v in iterable:
        if v:
            return v
    return None


def _pick_long_name(docs: List[Dict[str, Any]]) -> Optional[str]:
    """Pick the cleanest gnr_full_name across all FIRDS records.

    FIRDS submissions vary wildly per venue: some carry the proper
    legal name ("Chocoladefabriken Lindt and Spruengli AG"), others
    add lot/ratio/ISIN descriptors ("APPLE COMPUTER IN (FFURT) ISIN:
    US0378331005"), others double the name string. The cleanest
    submissions tend to be proper-case (mixed upper/lower) and short.

    Heuristic: prefer mixed-case names without obvious junk markers,
    then short over long. ALL-CAPS names are typically venue descriptor
    rows and get a heavy penalty.
    """
    candidates = [d.get("gnr_full_name") for d in docs if d.get("gnr_full_name")]
    if not candidates:
        return None

    junk_markers = ("DeltaH", "ISIN:", "ISIN ", "(", ")", " VAL ", " SHS ", " RG ")

    def _score(name: str) -> tuple[int, int, int]:
        stripped = name.strip()
        all_caps_penalty = 0 if any(c.islower() for c in stripped) else 10
        junk_penalty = sum(3 for m in junk_markers if m in stripped)
        # Doubled-string detection: many bad FIRDS submissions concat the
        # name to itself ("X CORP X CORP PAR"). A halved match flags it.
        half = len(stripped) // 2
        doubled_penalty = 5 if half > 10 and stripped[:half] == stripped[half:half*2] else 0
        return (
            all_caps_penalty + junk_penalty + doubled_penalty,
            len(stripped),  # tie-break: prefer shorter
            0,
        )

    return min(candidates, key=_score).strip()


def _any_active_listing(docs: List[Dict[str, Any]]) -> bool:
    """True iff at least one venue's most-recent record is still active.

    A venue record is active when status is not TERM/CANC AND the
    termination date is empty or in the future.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    by_mic: Dict[str, Dict[str, Any]] = {}
    for d in docs:
        mic = d.get("mic")
        if not mic:
            continue
        if mic not in by_mic:
            by_mic[mic] = d

    for d in by_mic.values():
        status = d.get("status") or ""
        if status in ("TERM", "CANC"):
            continue
        term_date = d.get("mrkt_trdng_trmination_date") or ""
        if term_date and term_date < now:
            continue
        return True
    return False


def _earliest_date(iterable) -> Optional[str]:
    """Earliest ISO-date string from the iterable; ignores empty/None."""
    candidates = [d for d in iterable if d]
    if not candidates:
        return None
    earliest = min(candidates)
    # FIRDS returns e.g. "2017-01-03T00:00:00Z" — strip to a date.
    return earliest[:10] if isinstance(earliest, str) else None


def _build_secondary_listings(
    docs: List[Dict[str, Any]],
    fallback_currency: Optional[str],
) -> List[Dict[str, Any]]:
    """Collapse multi-record FIRDS docs into one ListingSnapshot per MIC.

    Picks the most recent record per MIC (FIRDS returns one row per
    validity window). Filters out venue-less rows. `listingCurrency` is
    required on ListingSnapshot, so we fall back to the instrument's
    notional currency when the FIRDS row itself doesn't carry one.
    """
    by_mic: Dict[str, Dict[str, Any]] = {}
    for d in docs:
        mic = d.get("mic")
        if not mic:
            continue
        # First occurrence wins because docs are sorted valid_from_date desc.
        if mic in by_mic:
            continue
        by_mic[mic] = d

    listings: List[Dict[str, Any]] = []
    for mic, d in by_mic.items():
        listing: Dict[str, Any] = {
            "mic": mic,
            "listingCurrency": d.get("gnr_notional_curr_code") or fallback_currency,
            "status": _listing_status(d.get("status")),
            "isPrimary": False,
        }
        # Drop the listing if we can't honour the schema's required listingCurrency.
        if not listing["listingCurrency"]:
            continue
        first_trading = d.get("mrkt_trdng_start_date")
        if first_trading:
            listing["firstTradingDate"] = first_trading[:10]
        listings.append(listing)
    return listings


def _listing_status(firds_status: Optional[str]) -> str:
    """Map FIRDS *change-state* codes to a listing status string.

    NEWS/UNCH/MODI mean the most-recent record is alive → "active".
    TERM/CANC mean the venue is no longer carrying the security.
    """
    if firds_status in ("TERM",):
        return "terminated"
    if firds_status in ("CANC",):
        return "cancelled"
    return "active"
