"""FastAPI app — order management service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from orders.service import OrderService
from orders.store import OrderStore

from .router import build_router

_store = OrderStore()
_service = OrderService(_store)

app = FastAPI(
    title="Order API",
    version="0.1.0",
    description="Trade order submission, tracking, and simulated execution.",
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
