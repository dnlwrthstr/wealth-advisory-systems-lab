"""Fill BondGolden `marketData` with synthetic-from-terms values.

Yahoo Finance has no bond coverage and the lab has no paid feed. Until
we wire one up (per-issuer scraping of boerse-frankfurt.de /
investing.com, or a free sovereign-curve source like the German DSTA
data), we derive the parts of `marketData` that follow analytically
from the terms we already have:

    yieldToMaturity ≈ coupon_rate            (at par)
    currentYield     = coupon_rate
    macaulayDuration = (1/y) · (1 − (1+y)⁻ᵀ)
    modifiedDuration = macaulayDuration / (1+y)

We DO NOT fabricate a clean / dirty price, accrued interest, or
spreads — those would lie about what we know. Real-feed enrichers can
fill them later without overwriting what's here (this script appends
only the fields it computes).

The audit trail makes the synthetic origin explicit:
    recordMeta.sourceOfTruth += [
      { fieldGroup: "marketData",
        source:     "synthetic (coupon-as-YTM at par)",
        sourceTimestamp: <now> }
    ]

Only **active** bonds get enriched. Matured / cancelled bonds keep
empty marketData — computing duration on a bond whose maturity has
passed is meaningless.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .fund_yahoo_enrich import merge_source_of_truth

log = logging.getLogger("bond_synthetic_market_data")

SOURCE_LABEL = "synthetic (coupon-as-YTM at par)"


def _years_to_maturity(maturity_iso: Optional[str], now: dt.date) -> Optional[float]:
    if not maturity_iso:
        return None
    try:
        mat = dt.date.fromisoformat(maturity_iso)
    except ValueError:
        return None
    days = (mat - now).days
    return days / 365.25 if days > 0 else None


def _derive(coupon: float, T: float) -> Dict[str, float]:
    """Closed-form yield + duration at the par assumption."""
    y = coupon
    if y > 0:
        macaulay = (1.0 / y) * (1.0 - (1.0 + y) ** (-T))
    else:
        # Zero-coupon: Macaulay duration = years to maturity.
        macaulay = T
    modified = macaulay / (1.0 + y) if y > 0 else T
    return {
        "yieldToMaturity": round(y, 6),
        "currentYield": round(y, 6),
        "macaulayDuration": round(macaulay, 4),
        "modifiedDuration": round(modified, 4),
    }


def _apply(doc: Dict[str, Any], today: dt.date, now_iso: str) -> bool:
    """Mutates `doc` in place; returns True if something was filled."""
    if (doc.get("lifecycleStatus") or "") != "active":
        return False
    coupon = doc.get("currentCouponRate")
    if coupon is None:
        return False
    T = _years_to_maturity(doc.get("maturityDate"), today)
    if T is None:
        return False

    md = doc.get("marketData") or {}
    derived = _derive(float(coupon), T)

    touched: List[str] = []
    for key, value in derived.items():
        if md.get(key) is None:
            md[key] = value
            touched.append(key)
    if not touched:
        return False

    md.setdefault("asOf", now_iso)
    md.setdefault("sourceMic", (doc.get("primaryListing") or {}).get("mic"))
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
        [{"fieldGroup": "marketData", "source": SOURCE_LABEL, "sourceTimestamp": now_iso}],
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fill BondGolden marketData with synthetic-from-terms values "
            "(YTM / current yield / Macaulay + modified duration). "
            "Honest source label; only active bonds."
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

    now = datetime.now(timezone.utc)
    today = now.date()
    now_iso = now.isoformat()
    filled = 0
    skipped_matured = 0
    skipped_no_terms = 0
    for doc in docs:
        if (doc.get("lifecycleStatus") or "") != "active":
            skipped_matured += 1
            continue
        if doc.get("currentCouponRate") is None or doc.get("maturityDate") is None:
            skipped_no_terms += 1
            continue
        if _apply(doc, today, now_iso):
            filled += 1

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(json.dumps(doc, ensure_ascii=False))
            fh.write("\n")

    log.info(
        "Filled marketData on %d / %d bonds "
        "(%d skipped: matured/inactive; %d skipped: missing terms) → %s",
        filled, len(docs), skipped_matured, skipped_no_terms, out,
    )


if __name__ == "__main__":
    main()
