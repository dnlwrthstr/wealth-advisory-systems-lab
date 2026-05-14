"""FastAPI app for the profile and suitability service."""

import os

from advice.service import SuitabilityService
from audit import PostgresAuditStore
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from profiling.service import ProfilingService
from profiling.store import PostgresQuestionnaireStore

from .router import build_router

_database_url = os.getenv("DATABASE_URL")
_audit_store = PostgresAuditStore(_database_url) if _database_url else None
_questionnaire_store = PostgresQuestionnaireStore(_database_url) if _database_url else None

_profiling = ProfilingService(
    audit_store=_audit_store,
    questionnaire_store=_questionnaire_store,
)
_suitability = SuitabilityService()

app = FastAPI(
    title="Profile API",
    version="0.1.0",
    description="Client profile, questionnaire processing, and suitability service.",
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


app.include_router(build_router(profiling=_profiling, suitability=_suitability))
