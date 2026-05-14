"""Data access layer for questionnaire definitions."""

from typing import Protocol

from .questionnaire import Questionnaire, questionnaire_from_dict, questionnaire_to_dict


class QuestionnaireStore(Protocol):
    def load_active(self) -> list[Questionnaire]: ...
    def save(self, questionnaire: Questionnaire, status: str = "active") -> None: ...


class PostgresQuestionnaireStore:
    """Loads and persists questionnaire definitions from admin.questionnaire_definition."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def load_active(self) -> list[Questionnaire]:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ModuleNotFoundError as exc:
            raise RuntimeError("psycopg is required for Postgres questionnaire store") from exc

        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT definition FROM admin.questionnaire_definition WHERE status = 'active'"
                )
                rows = cur.fetchall()

        return [questionnaire_from_dict(row["definition"]) for row in rows]

    def save(self, questionnaire: Questionnaire, status: str = "active") -> None:
        try:
            import psycopg
            from psycopg.types.json import Jsonb
        except ModuleNotFoundError as exc:
            raise RuntimeError("psycopg is required for Postgres questionnaire store") from exc

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO admin.questionnaire_definition
                        (questionnaire_id, version, definition, status)
                    VALUES
                        (%(qid)s, %(version)s, %(definition)s, %(status)s)
                    ON CONFLICT (questionnaire_id, version) DO UPDATE SET
                        definition = EXCLUDED.definition,
                        status = EXCLUDED.status,
                        updated_at = now()
                    """,
                    {
                        "qid": questionnaire.questionnaire_id,
                        "version": questionnaire.version,
                        "definition": Jsonb(questionnaire_to_dict(questionnaire)),
                        "status": status,
                    },
                )
            conn.commit()
