"""FastAPI app — instrument universe search service.

Backed by OpenSearch (against the `pms_golden_equity` index produced by
the gold-tier pipeline) when `OPENSEARCH_URL` is set in the environment;
falls back to the in-memory fixture store otherwise.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from instruments.data import INSTRUMENTS
from instruments.opensearch_store import (
    OpenSearchInstrumentStore,
    opensearch_client_from_env,
)
from instruments.search_store import OpenSearchInstrumentSearch
from instruments.service import InstrumentService
from instruments.store import InstrumentStore

from .router import build_router

log = logging.getLogger("instrument_api")

_client = opensearch_client_from_env()
if _client is not None:
    log.info("instrument_api: using OpenSearch-backed store")
    _store = OpenSearchInstrumentStore(_client)
    _search_store: OpenSearchInstrumentSearch | None = OpenSearchInstrumentSearch(_client)
else:
    log.info("instrument_api: using in-memory fixture store (no OPENSEARCH_URL)")
    _store = InstrumentStore(INSTRUMENTS)
    _search_store = None
_service = InstrumentService(_store)

app = FastAPI(
    title="Instrument API",
    version="0.1.0",
    description="Instrument universe search and lookup.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(build_router(_service, search_store=_search_store))
