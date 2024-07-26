import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from gatum_agent.models.ticket import Ticket


class TicketStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    conversation_snippet TEXT,
                    escalation_target TEXT,
                    resolved_by_ai INTEGER NOT NULL,
                    sentiment TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )

    def save(self, ticket: Ticket) -> Ticket:
        row = ticket.to_db_row()
        row["metadata"] = json.dumps(row["metadata"], ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tickets (
                    ticket_id, created_at, channel, client_id, category,
                    priority, summary, conversation_snippet, escalation_target,
                    resolved_by_ai, sentiment, metadata
                ) VALUES (
                    :ticket_id, :created_at, :channel, :client_id, :category,
                    :priority, :summary, :conversation_snippet, :escalation_target,
                    :resolved_by_ai, :sentiment, :metadata
                )
                """,
                row,
            )
        return ticket

    def get(self, ticket_id: str) -> Ticket | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_ticket(dict(row))

    def list_all(self) -> list[Ticket]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tickets ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_ticket(dict(r)) for r in rows]

    def _row_to_ticket(self, row: dict[str, Any]) -> Ticket:
        row = dict(row)
        row["resolved_by_ai"] = bool(row["resolved_by_ai"])
        row["metadata"] = json.loads(row["metadata"] or "{}")
        return Ticket.model_validate(row)
