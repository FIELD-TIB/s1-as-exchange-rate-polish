"""SQLite persistence for locally collected KES/TZS rate samples."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


class RateStore:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fetched_at TEXT NOT NULL,
                    rate REAL NOT NULL,
                    provider_updated_at TEXT
                )
                """
            )

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def save_sample(self, fetched_at, rate, provider_updated_at):
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO rate_samples (fetched_at, rate, provider_updated_at)
                VALUES (?, ?, ?)
                """,
                (fetched_at, rate, provider_updated_at),
            )

    def get_samples(self, limit=100):
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, fetched_at, rate, provider_updated_at
                FROM rate_samples
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def get_latest(self):
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, fetched_at, rate, provider_updated_at
                FROM rate_samples
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        return dict(row) if row else None
