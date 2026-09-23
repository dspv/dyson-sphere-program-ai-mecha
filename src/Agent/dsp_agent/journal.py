"""Durable local command journal; it cannot establish game success by itself."""

import json
import sqlite3
import uuid
from pathlib import Path


class JournalConflict(ValueError):
    """An idempotency key was reused for a different command."""


class AgentJournal:
    def __init__(self, path):
        location = Path(path)
        location.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(location))
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS operations (
                operation_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                command_json TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT,
                UNIQUE (session_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @staticmethod
    def _json(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

    def record_command(self, session_id, idempotency_key, command):
        if not session_id or not idempotency_key or not isinstance(command, dict):
            raise ValueError("session, idempotency key, and object command are required")
        encoded = self._json(command)
        with self.connection:
            row = self.connection.execute(
                "SELECT operation_id, command_json, status FROM operations "
                "WHERE session_id = ? AND idempotency_key = ?",
                (session_id, idempotency_key),
            ).fetchone()
            if row is not None:
                if row[1] != encoded:
                    raise JournalConflict("idempotency key already names another command")
                return row[0], row[2]
            operation_id = str(uuid.uuid4())
            self.connection.execute(
                "INSERT INTO operations VALUES (?, ?, ?, ?, 'pending', NULL)",
                (operation_id, session_id, idempotency_key, encoded),
            )
            self.connection.execute(
                "INSERT INTO events (session_id, kind, payload_json) VALUES (?, 'command_recorded', ?)",
                (session_id, self._json({"operation_id": operation_id, "command": command})),
            )
            return operation_id, "pending"

    def record_result(self, operation_id, status, result):
        allowed = {"observed_success", "observed_failure", "partial", "unknown"}
        if status not in allowed or not isinstance(result, dict):
            raise ValueError("invalid result status or payload")
        with self.connection:
            row = self.connection.execute(
                "SELECT session_id, status FROM operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if row is None:
                raise KeyError(operation_id)
            if row[1] in {"observed_success", "observed_failure"}:
                raise JournalConflict("terminal operation cannot be rewritten")
            self.connection.execute(
                "UPDATE operations SET status = ?, result_json = ? WHERE operation_id = ?",
                (status, self._json(result), operation_id),
            )
            self.connection.execute(
                "INSERT INTO events (session_id, kind, payload_json) VALUES (?, 'result_recorded', ?)",
                (row[0], self._json({"operation_id": operation_id, "status": status, "result": result})),
            )

    def record_session_change(self, old_session_id, new_session_id):
        if not old_session_id or not new_session_id or old_session_id == new_session_id:
            raise ValueError("distinct old and new sessions are required")
        with self.connection:
            count = self.connection.execute(
                "UPDATE operations SET status = 'needs_reconciliation' "
                "WHERE session_id = ? AND status IN ('pending', 'partial', 'unknown')",
                (old_session_id,),
            ).rowcount
            self.connection.execute(
                "INSERT INTO events (session_id, kind, payload_json) VALUES (?, 'session_changed', ?)",
                (new_session_id, self._json({"previous_session_id": old_session_id, "unresolved_operations": count})),
            )
            return count

    def operation(self, operation_id):
        row = self.connection.execute(
            "SELECT session_id, idempotency_key, command_json, status, result_json "
            "FROM operations WHERE operation_id = ?",
            (operation_id,),
        ).fetchone()
        if row is None:
            raise KeyError(operation_id)
        return {
            "session_id": row[0],
            "idempotency_key": row[1],
            "command": json.loads(row[2]),
            "status": row[3],
            "result": json.loads(row[4]) if row[4] is not None else None,
        }
