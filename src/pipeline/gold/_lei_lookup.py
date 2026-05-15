"""GLEIF ISIN → LEI lookup with on-disk caching.

Bond / fund parquet rows carry only the issuer name; we need the LEI so
the issuer aggregator can dedupe and `issuer_gleif` can enrich downstream.
GLEIF supports `filter[isin]=<isin>` against its lei-records endpoint —
this module wraps that call with a one-file-per-ISIN disk cache so a
re-run of the pipeline is free.

Cache layout:
    ~/.cache/wealth-advisory-systems-lab/gleif-isin/<isin>.txt
        - file content = the LEI string when GLEIF returned one
        - file content = the literal "NONE" when GLEIF had no record
        - missing file = lookup hasn't been attempted yet

GLEIF coverage is not universal — Eurobonds (XS prefix) in particular
often have no ISIN → LEI mapping in the GLEIF index. The function
returns `None` for misses; the caller decides how to handle it.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

GLEIF_API = "https://api.gleif.org/api/v1/lei-records"
USER_AGENT = (
    "wealth-advisory-systems-lab/0.1 "
    "(+https://github.com/dnlwrthstr/wealth-advisory-systems-lab)"
)
TIMEOUT = 30
CACHE_DIR = Path.home() / ".cache" / "wealth-advisory-systems-lab" / "gleif-isin"
_NONE_SENTINEL = "NONE"


def _cache_path(isin: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{isin}.txt"


def _http_get_json(url: str) -> Optional[dict]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.api+json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        if exc.code == 429:
            time.sleep(2.0)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        raise


def lei_for_isin(isin: str, *, use_cache: bool = True) -> Optional[str]:
    """Return the LEI for `isin` per GLEIF, or None when GLEIF has no record.

    Results (including "no record" outcomes) are cached on disk so retries
    are free. Pass `use_cache=False` to force a refetch.
    """
    if not isin:
        return None
    cached = _cache_path(isin)
    if use_cache and cached.exists():
        value = cached.read_text(encoding="utf-8").strip()
        return None if (not value or value == _NONE_SENTINEL) else value

    qs = urllib.parse.urlencode({"filter[isin]": isin})
    try:
        response = _http_get_json(f"{GLEIF_API}?{qs}")
    except urllib.error.HTTPError as exc:
        log.warning("GLEIF ISIN lookup %s failed: %s", isin, exc)
        return None

    data = (response or {}).get("data") or []
    if not data:
        cached.write_text(_NONE_SENTINEL, encoding="utf-8")
        return None

    try:
        lei = data[0]["attributes"]["lei"]
    except (KeyError, TypeError):
        cached.write_text(_NONE_SENTINEL, encoding="utf-8")
        return None

    cached.write_text(lei, encoding="utf-8")
    return lei
