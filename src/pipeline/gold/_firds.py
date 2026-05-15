"""Thin client for the ESMA FIRDS public Solr endpoint.

FIRDS (Financial Instruments Reference Data System) is the free
authoritative source for MiFID II-reportable instruments. Both
`bond_firds` and `fund_firds` query it, so the client lives here.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterator, List

log = logging.getLogger(__name__)

FIRDS_BASE = "https://registers.esma.europa.eu/solr/esma_registers_firds/select"
FIRDS_USER_AGENT = (
    "wealth-advisory-systems-lab/0.1 "
    "(+https://github.com/dnlwrthstr/wealth-advisory-systems-lab)"
)
FIRDS_TIMEOUT = 60
FIRDS_PAGE_SIZE = 200
FIRDS_MAX_PAGES = 200
FIRDS_INTER_REQUEST_SLEEP = 0.2


def solr_get(params: Dict[str, str], retries: int = 5) -> Dict[str, Any]:
    """GET FIRDS Solr with exponential backoff on 5xx / connection errors."""
    qs = urllib.parse.urlencode(params, safe=":+")
    url = f"{FIRDS_BASE}?{qs}"
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": FIRDS_USER_AGENT})
            with urllib.request.urlopen(req, timeout=FIRDS_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            if 500 <= exc.code < 600 and attempt < retries:
                wait = min(2 ** (attempt + 1), 30)
                log.warning("FIRDS %d, retrying in %ds (attempt %d/%d)",
                            exc.code, wait, attempt + 1, retries)
                time.sleep(wait)
                last_exc = exc
                continue
            raise
        except urllib.error.URLError as exc:
            last_exc = exc
            if attempt < retries:
                wait = min(2 ** (attempt + 1), 30)
                log.warning("FIRDS connection error, retrying in %ds (attempt %d/%d)",
                            wait, attempt + 1, retries)
                time.sleep(wait)
                continue
            raise
    if last_exc:
        raise last_exc
    return {}


def iter_issuer_records(lei: str, fl: List[str]) -> Iterator[Dict[str, Any]]:
    """Yield FIRDS records for an issuer LEI, paginated."""
    fl_str = ",".join(fl)
    start = 0
    for _page in range(FIRDS_MAX_PAGES):
        params = {
            "q": f"lei:{lei}+AND+latest_received_flag:1",
            "wt": "json",
            "rows": str(FIRDS_PAGE_SIZE),
            "start": str(start),
            "fl": fl_str,
            "sort": "isin asc, valid_from_date desc",
        }
        try:
            data = solr_get(params)
        except Exception as exc:  # noqa: BLE001
            log.warning("page start=%d for %s: %s", start, lei, exc)
            return
        docs = data.get("response", {}).get("docs", []) or []
        if not docs:
            return
        yield from docs
        if len(docs) < FIRDS_PAGE_SIZE:
            return
        start += FIRDS_PAGE_SIZE
        time.sleep(FIRDS_INTER_REQUEST_SLEEP)
