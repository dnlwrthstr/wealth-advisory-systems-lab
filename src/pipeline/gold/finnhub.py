"""Finnhub equity client — live quote + company profile by ticker.

A second equity overlay alongside yfinance: when Yahoo is throttled,
returns "-", or just misses fields, Finnhub's free tier (60 req/min with
FINNHUB_API_KEY) covers the same surface and adds reliable issuer
country + IPO date + Finnhub industry classification.

Endpoints:
  GET /quote?symbol=…       → current/open/high/low/prev-close + timestamp
  GET /stock/profile2?…     → name, country, exchange, currency, IPO date,
                              market cap, shares outstanding, industry

Network-free without a key: the source returns None when FINNHUB_API_KEY
isn't set, so the planner just skips it.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("finnhub")

FINNHUB_BASE = "https://finnhub.io/api/v1"
USER_AGENT = (
    "wealth-advisory-systems-lab/0.1 "
    "(+https://github.com/dnlwrthstr/wealth-advisory-systems-lab)"
)
TIMEOUT = 30
CACHE_DIR = Path.home() / ".cache" / "wealth-advisory-systems-lab" / "finnhub"


def _cache_path(ticker: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = ticker.replace("/", "_")
    return CACHE_DIR / f"{safe}.json"


def _get_json(endpoint: str, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
    qs = urllib.parse.urlencode(params)
    url = f"{FINNHUB_BASE}{endpoint}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            log.warning("finnhub rate-limited: %s", url)
        else:
            log.warning("finnhub HTTP %s for %s", exc.code, url)
        return None
    except urllib.error.URLError as exc:
        log.warning("finnhub URL error %s for %s", exc, url)
        return None


def fetch_by_ticker(ticker: str, *, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """Fetch quote + profile for `ticker`, return a flat projection or None.

    Returns None when:
      - FINNHUB_API_KEY isn't set (signals "skip me" to the agentic planner)
      - Finnhub returns an empty profile (unknown ticker)
      - Any HTTP error
    """
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        return None

    cached = _cache_path(ticker)
    if use_cache and cached.exists():
        try:
            data = json.loads(cached.read_text(encoding="utf-8"))
            return None if data.get("_negative") else data
        except json.JSONDecodeError:
            cached.unlink(missing_ok=True)

    profile = _get_json("/stock/profile2", {"symbol": ticker, "token": api_key}) or {}
    if not profile.get("ticker"):
        cached.write_text(json.dumps({"_negative": True}), encoding="utf-8")
        return None

    quote = _get_json("/quote", {"symbol": ticker, "token": api_key}) or {}
    projected = {
        "ticker": profile.get("ticker"),
        "name": profile.get("name"),
        "country": profile.get("country"),
        "currency": profile.get("currency"),
        "exchange": profile.get("exchange"),
        "ipo": profile.get("ipo"),
        "marketCapitalization": profile.get("marketCapitalization"),
        "shareOutstanding": profile.get("shareOutstanding"),
        "finnhubIndustry": profile.get("finnhubIndustry"),
        "quote": {
            "current": quote.get("c"),
            "open": quote.get("o"),
            "high": quote.get("h"),
            "low": quote.get("l"),
            "previousClose": quote.get("pc"),
            "timestamp": quote.get("t"),
        },
    }
    try:
        cached.write_text(json.dumps(projected), encoding="utf-8")
    except OSError as exc:
        log.warning("finnhub cache write failed for %s: %s", ticker, exc)
    return projected
