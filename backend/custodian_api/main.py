"""FastAPI app for the custodian data service."""

import os

from custodian.data import ACCOUNT_OWNER, ACCOUNTS, CUSTOMERS, POSITIONS, TRANSACTIONS
from custodian.service import CustodianService
from custodian.store import DuckDBCustodianStore, InMemoryCustodianStore
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import build_router

_data_path = os.getenv("CUSTODIAN_DATA_PATH")

if _data_path:
    _store = DuckDBCustodianStore(_data_path)
else:
    _store = InMemoryCustodianStore(CUSTOMERS, ACCOUNTS, POSITIONS, TRANSACTIONS, ACCOUNT_OWNER)

_service = CustodianService(_store)

app = FastAPI(
    title="Custodian API",
    version="0.2.0",
    description="OpenWealth-compliant custodian data service.",
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


app.include_router(build_router(_service))
