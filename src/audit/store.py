"""Postgres-backed audit persistence for profile processing runs."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class AuditRecord:
    client_id: str
    questionnaire_id: str
    questionnaire_version: str
    ontology_version: str
    raw_answers: dict[str, str | bool]
    score_contributions: list[dict[str, object]]
    derived_profile: dict[str, object] | None
    strategy_profile: dict[str, object] | None
    gates: list[dict[str, object]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    valid: bool = True


@dataclass(frozen=True)
class LatestProfileRecord:
    processing_run_id: int
    client_id: str
    questionnaire_id: str
    questionnaire_version: str
    derived_profile: dict[str, object] | None
    strategy_profile: dict[str, object] | None
    gates: list[dict[str, object]]
    warnings: list[str]
    errors: list[str]
    valid: bool
    processed_at: str  # ISO-8601 string


class AuditStore(Protocol):
    def save_profile_processing_run(self, record: AuditRecord) -> int:
        """Persist an audit record and return its processing run ID."""

    def get_latest_for_client(self, client_id: str) -> LatestProfileRecord | None:
        """Return the most recent processing run for client_id, or None."""


class PostgresAuditStore:
    """Persist profile processing audit trails in Postgres."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def save_profile_processing_run(self, record: AuditRecord) -> int:
        try:
            import psycopg
            from psycopg.types.json import Jsonb
        except ModuleNotFoundError as exc:
            raise RuntimeError("psycopg is required for Postgres audit persistence") from exc

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit.profile_processing_run (
                        client_id,
                        questionnaire_id,
                        questionnaire_version,
                        ontology_version,
                        raw_answers,
                        score_contributions,
                        derived_profile,
                        strategy_profile,
                        gates,
                        warnings,
                        errors,
                        valid
                    ) VALUES (
                        %(client_id)s,
                        %(questionnaire_id)s,
                        %(questionnaire_version)s,
                        %(ontology_version)s,
                        %(raw_answers)s,
                        %(score_contributions)s,
                        %(derived_profile)s,
                        %(strategy_profile)s,
                        %(gates)s,
                        %(warnings)s,
                        %(errors)s,
                        %(valid)s
                    )
                    RETURNING processing_run_id
                    """,
                    {
                        "client_id": record.client_id,
                        "questionnaire_id": record.questionnaire_id,
                        "questionnaire_version": record.questionnaire_version,
                        "ontology_version": record.ontology_version,
                        "raw_answers": Jsonb(record.raw_answers),
                        "score_contributions": Jsonb(record.score_contributions),
                        "derived_profile": Jsonb(record.derived_profile)
                        if record.derived_profile is not None
                        else None,
                        "strategy_profile": Jsonb(record.strategy_profile)
                        if record.strategy_profile is not None
                        else None,
                        "gates": Jsonb(record.gates),
                        "warnings": record.warnings,
                        "errors": record.errors,
                        "valid": record.valid,
                    },
                )
                processing_run_id = cursor.fetchone()[0]
            connection.commit()
        return int(processing_run_id)

    def get_latest_for_client(self, client_id: str) -> LatestProfileRecord | None:
        try:
            import psycopg
        except ModuleNotFoundError as exc:
            raise RuntimeError("psycopg is required for Postgres audit persistence") from exc

        with psycopg.connect(self.database_url, row_factory=psycopg.rows.dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT processing_run_id, client_id, questionnaire_id, questionnaire_version,
                           derived_profile, strategy_profile, gates, warnings, errors, valid,
                           processed_at
                    FROM audit.profile_processing_run
                    WHERE client_id = %(client_id)s
                    ORDER BY processed_at DESC
                    LIMIT 1
                    """,
                    {"client_id": client_id},
                )
                row = cursor.fetchone()

        if row is None:
            return None
        return LatestProfileRecord(
            processing_run_id=row["processing_run_id"],
            client_id=row["client_id"],
            questionnaire_id=row["questionnaire_id"],
            questionnaire_version=row["questionnaire_version"],
            derived_profile=row["derived_profile"],
            strategy_profile=row["strategy_profile"],
            gates=row["gates"] or [],
            warnings=list(row["warnings"] or []),
            errors=list(row["errors"] or []),
            valid=row["valid"],
            processed_at=row["processed_at"].isoformat(),
        )
