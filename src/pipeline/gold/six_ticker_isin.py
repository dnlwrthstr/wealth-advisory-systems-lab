"""Curated SIX Swiss Exchange ticker → ISIN map.

The SIX listing of a CH-issued equity isn't in ESMA FIRDS (Swiss
issuers report to FINMA), and yfinance returns "-" for `.isin` on
Swiss tickers. The bundled YAML at `data/six_ticker_isin.yml` fills
the gap for the names the lab cares about.

Loaded once at import time. To add a ticker, edit the YAML and
restart the API.
"""
from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from typing import Dict, Optional

import yaml


@lru_cache(maxsize=1)
def _load() -> Dict[str, str]:
    raw = files("pipeline.gold.data").joinpath("six_ticker_isin.yml").read_text(
        encoding="utf-8"
    )
    parsed = yaml.safe_load(raw) or {}
    if not isinstance(parsed, dict):
        raise ValueError("six_ticker_isin.yml must be a YAML mapping of ticker→ISIN")
    return {k: v for k, v in parsed.items() if isinstance(v, str) and len(v) == 12}


def isin_for_ticker(ticker: str) -> Optional[str]:
    """Look up the SIX ISIN for a Yahoo-suffixed Swiss ticker.

    Case-insensitive on the ticker. Returns None if the ticker isn't
    in the curated map.
    """
    if not ticker:
        return None
    table = _load()
    # Try exact then upper-case match — covers both `LISN.SW` and `lisn.sw`.
    return table.get(ticker) or table.get(ticker.upper())


def known_tickers() -> list[str]:
    """Sorted list of every ticker in the curated map."""
    return sorted(_load().keys())
