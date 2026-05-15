"""Enrich BondGolden `marketData` with real prices from boerse-frankfurt.

Boerse Frankfurt's public API at `api.boerse-frankfurt.de/v1/data/quote_box`
returns a live quote per ISIN as a Server-Sent-Events stream. We read just
the first `data:` line (the actual quote payload, before the
`health_event` heartbeats), close the connection, and project it into
`BondGolden.marketData.cleanPrice` plus a timestamp.

Once we have a real clean price (in % of nominal), the analytic
identities give us a real YTM and duration too:

    P(y) = c · annuity(y, n) + (1+y)^-n        (price-yield equation)
    y    = bisection-solve P(y) = clean / 100
    macaulay = sum(t · CF_t / (1+y)^t) / P
    modified = macaulay / (1+y)

The earlier synthetic enricher (`bond_synthetic_market_data`) populated
the same fields under the `synthetic (coupon-as-YTM at par)` provenance.
This enricher **overwrites** those values with real-feed numbers when
boerse-frankfurt returns a quote, and appends a separate
`marketData → boerse-frankfurt.de` row to `sourceOfTruth` (the dedupe
key is `(fieldGroup, source)`, so both rows coexist as an audit trail).

Coverage caveat: boerse-frankfurt lists European bonds well but not US
Treasuries. For ISINs that return an empty payload, we leave the
synthetic values untouched.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .fund_yahoo_enrich import merge_source_of_truth

log = logging.getLogger("bond_boerse_frankfurt_enrich")

USER_AGENT = (
    "wealth-advisory-systems-lab/0.1 "
    "(+https://github.com/dnlwrthstr/wealth-advisory-systems-lab)"
)
CACHE_DIR = Path.home() / ".cache" / "wealth-advisory-systems-lab" / "boerse-frankfurt"
QUOTE_TIMEOUT = 8         # seconds for the SSE socket
INTER_REQUEST_SLEEP = 0.15
SOURCE_LABEL = "boerse-frankfurt.de"


# ---------------------------------------------------------------------------
# Quote fetch — read the first data: line of the SSE stream
# ---------------------------------------------------------------------------

def _cache_path(isin: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{isin}.json"


def fetch_quote(isin: str, *, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """Return the first JSON quote payload for `isin`, or None if the
    venue has no quote for it. Cached on disk between runs.
    """
    cached = _cache_path(isin)
    if use_cache and cached.exists():
        try:
            payload = json.loads(cached.read_text(encoding="utf-8"))
            return None if payload.get("_negative") else payload
        except json.JSONDecodeError:
            cached.unlink(missing_ok=True)

    url = "https://api.boerse-frankfurt.de/v1/data/quote_box?" + urllib.parse.urlencode(
        {"isin": isin, "mic": "XFRA"}
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/event-stream"},
    )
    try:
        with urllib.request.urlopen(req, timeout=QUOTE_TIMEOUT) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                body = line[len("data:"):].strip()
                if not body or body == "health_event":
                    continue
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict) or payload.get("lastPrice") in (None, 0):
                    continue
                cached.write_text(json.dumps(payload), encoding="utf-8")
                return payload
    except urllib.error.URLError as exc:
        log.warning("  %s: HTTP %s", isin, exc)
        return None
    except Exception as exc:  # noqa: BLE001 — broad: socket errors, sse weirdness
        log.warning("  %s: %s", isin, exc)
        return None

    cached.write_text(json.dumps({"_negative": True}), encoding="utf-8")
    return None


# ---------------------------------------------------------------------------
# YTM / duration math
# ---------------------------------------------------------------------------

def _periods(years: float, freq: int = 1) -> int:
    return max(1, int(round(years * freq)))


def ytm_from_price(
    clean_price_pct: float,
    coupon_rate: float,
    years_to_maturity: float,
    freq: int = 1,
) -> Optional[float]:
    """Bisection-solve the price-yield equation. Returns the annualized
    YTM as a decimal (0.0537 for 5.37 %), or None if it doesn't converge.
    """
    if years_to_maturity <= 0:
        return None
    n = _periods(years_to_maturity, freq)
    c = coupon_rate / freq
    target = clean_price_pct / 100.0

    def pv(y_per_period: float) -> float:
        # Periodic YTM y_per_period; cash flows c each period, plus 1.0 at maturity.
        if y_per_period <= -1.0:
            return float("inf")
        if abs(y_per_period) < 1e-12:
            return c * n + 1.0
        annuity = (1.0 - (1.0 + y_per_period) ** -n) / y_per_period
        return c * annuity + (1.0 + y_per_period) ** -n

    lo, hi = -0.05 / freq, 1.0 / freq
    f_lo, f_hi = pv(lo) - target, pv(hi) - target
    # If the target is outside the bracket, expand once; otherwise give up.
    if f_lo * f_hi > 0:
        hi = 5.0 / freq
        f_hi = pv(hi) - target
        if f_lo * f_hi > 0:
            return None

    for _ in range(80):
        mid = 0.5 * (lo + hi)
        f_mid = pv(mid) - target
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
        if hi - lo < 1e-10:
            break
    return (lo + hi) * 0.5 * freq


def duration_from_ytm(
    ytm: float,
    coupon_rate: float,
    years_to_maturity: float,
    freq: int = 1,
) -> Optional[Dict[str, float]]:
    """Macaulay and modified duration in years."""
    if years_to_maturity <= 0:
        return None
    n = _periods(years_to_maturity, freq)
    c = coupon_rate / freq
    y_per = ytm / freq

    pv_total = 0.0
    weighted = 0.0
    for t in range(1, n + 1):
        cf = c if t < n else c + 1.0
        disc = (1.0 + y_per) ** t
        pv_t = cf / disc
        pv_total += pv_t
        weighted += t * pv_t

    if pv_total <= 0:
        return None
    mac_periods = weighted / pv_total
    macaulay_years = mac_periods / freq
    modified_years = macaulay_years / (1.0 + y_per) if y_per > -1.0 else macaulay_years
    return {"macaulayDuration": macaulay_years, "modifiedDuration": modified_years}


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def _years_to_maturity(maturity_iso: Optional[str], today_iso: str) -> Optional[float]:
    if not maturity_iso:
        return None
    try:
        mat = datetime.fromisoformat(maturity_iso).date()
        today = datetime.fromisoformat(today_iso).date()
    except ValueError:
        return None
    days = (mat - today).days
    return days / 365.25 if days > 0 else None


def _isin_of(doc: Dict[str, Any]) -> Optional[str]:
    for entry in doc.get("identifierList") or []:
        if (entry.get("type") or "").lower() == "isin":
            return entry.get("identifier")
    return None


def _apply(doc: Dict[str, Any], quote: Dict[str, Any], now_iso: str) -> bool:
    """Overlay real quote + recomputed yield + duration onto `doc`.

    The synthetic enricher's values get overwritten. Returns True if
    anything changed, False if there was nothing to do.
    """
    last_price = quote.get("lastPrice")
    if last_price in (None, 0):
        return False

    currency = doc.get("currencyOfDenomination")
    md = doc.get("marketData") or {}

    md["asOf"] = quote.get("timestampLastPrice") or quote.get("timestamp") or now_iso
    md["sourceMic"] = "XFRA"
    md["cleanPrice"] = {
        "type": "actual",
        "value": float(last_price),
        "currency": currency,
    }

    coupon = doc.get("currentCouponRate")
    maturity = doc.get("maturityDate")
    T = _years_to_maturity(maturity, now_iso[:10])
    if coupon is not None and T is not None:
        ytm = ytm_from_price(float(last_price), float(coupon), T)
        if ytm is not None:
            md["yieldToMaturity"] = round(ytm, 6)
            md["currentYield"] = round(float(coupon) / (float(last_price) / 100.0), 6)
            dur = duration_from_ytm(ytm, float(coupon), T)
            if dur:
                md["macaulayDuration"] = round(dur["macaulayDuration"], 4)
                md["modifiedDuration"] = round(dur["modifiedDuration"], 4)

    doc["marketData"] = md

    record_meta = doc.setdefault("recordMeta", {
        "schemaVersion": "0.1.0",
        "goldenAsOf": now_iso,
        "sourceOfTruth": [],
        "isActive": True,
    })
    record_meta["goldenAsOf"] = now_iso
    merge_source_of_truth(
        record_meta,
        [{"fieldGroup": "marketData", "source": SOURCE_LABEL, "sourceTimestamp": md["asOf"]}],
    )
    return True


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Enrich BondGolden marketData with real prices from "
            "boerse-frankfurt.de. Real-feed price overwrites the synthetic "
            "par-assumption values written by bond_synthetic_market_data."
        )
    )
    parser.add_argument(
        "-i", "--input", required=True, type=Path,
        help="Input BondGolden NDJSON file.",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output NDJSON (defaults to overwriting --input).",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Cap on number of bonds to enrich (smoke testing).",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Bypass the on-disk per-ISIN cache for this run.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.input.exists():
        sys.exit(f"Input not found: {args.input}")
    out = args.output or args.input

    docs: List[Dict[str, Any]] = []
    with args.input.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                docs.append(json.loads(line))
            except json.JSONDecodeError as exc:
                log.warning("  bad JSON: %s", exc)

    now_iso = datetime.now(timezone.utc).isoformat()
    enriched = 0
    missing = 0
    inactive = 0
    no_isin = 0
    queried = 0

    for i, doc in enumerate(docs, 1):
        if (doc.get("lifecycleStatus") or "") != "active":
            inactive += 1
            continue
        isin = _isin_of(doc)
        if not isin:
            no_isin += 1
            continue
        if args.limit and queried >= args.limit:
            break

        quote = fetch_quote(isin, use_cache=not args.no_cache)
        queried += 1
        if not quote:
            missing += 1
            log.info("  %s: no quote on boerse-frankfurt", isin)
            time.sleep(INTER_REQUEST_SLEEP)
            continue

        if _apply(doc, quote, now_iso):
            enriched += 1
            log.info(
                "  %s → cleanPrice=%s YTM=%s modDur=%s",
                isin, quote.get("lastPrice"),
                (doc.get("marketData") or {}).get("yieldToMaturity"),
                (doc.get("marketData") or {}).get("modifiedDuration"),
            )
        time.sleep(INTER_REQUEST_SLEEP)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(json.dumps(doc, ensure_ascii=False))
            fh.write("\n")

    log.info(
        "Enriched %d / %d bonds (%d missing on venue, %d inactive, %d no ISIN) → %s",
        enriched, len(docs), missing, inactive, no_isin, out,
    )


if __name__ == "__main__":
    main()
