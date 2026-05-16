"""Build a partial EquityGolden from the FINFOX parquet seed alone.

This is the network-free, high-confidence baseline path for the agentic
platform's equity scope. The equity_yahoo source overlays live market
data on top via fill-empty-only merge.

Implementation note: reuses `pipeline.gold.equity_yahoo.yahoo_info_to_golden`
with `info={}`. That function already supports a seed-only build path
(used today by the legacy CLI when yfinance returns nothing), so the
behaviour and provenance shape match what the legacy pipeline produces.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pipeline.gold.equity_yahoo import _find_equity_seed_by_isin, yahoo_info_to_golden
from universe.models import EquityGolden


def fetch_by_isin(
    isin: str,
    *,
    run_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Optional[EquityGolden]:
    """Build an EquityGolden from the parquet seed for `isin`, no network.

    Returns None if the seed is absent from the local parquet store.
    The resulting record has identifiers, longName, currency, a basic
    issuer + primaryListing snapshot — but no live market data.
    """
    seed = _find_equity_seed_by_isin(isin)
    if seed is None or not seed.get("ticker"):
        return None
    run_id = run_id or f"parquet-seed-{uuid.uuid4().hex[:8]}"
    now = now or datetime.now(timezone.utc)
    from pipeline.silver import yahoo_ticker_for

    ticker = yahoo_ticker_for(isin, seed["ticker"])
    if not ticker:
        return None
    return yahoo_info_to_golden(ticker, info={}, isin=isin, run_id=run_id, now=now, seed=seed)
