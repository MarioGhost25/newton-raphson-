"""Persistencia local de entradas y resumen; restauración mediante el motor."""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
from uuid import uuid4
from app.core.models import NewtonResult


@dataclass(frozen=True)
class Calculation:
    function: str
    derivative: str
    x0: float
    tolerance: float
    max_iterations: int
    result: NewtonResult


@dataclass(frozen=True)
class HistoryEntry:
    id: str
    created_at: str
    function: str
    derivative: str
    x0: float
    tolerance: float
    max_iterations: int
    root: float | None
    status: str
    iteration_count: int


class HistoryError(Exception):
    pass


def default_history_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return base / "NewtonLab" / "history.sqlite3"


class HistoryService:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else default_history_path()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=3)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("""CREATE TABLE IF NOT EXISTS calculations (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL, function TEXT NOT NULL,
                derivative TEXT NOT NULL, x0 REAL NOT NULL, tolerance REAL NOT NULL,
                max_iterations INTEGER NOT NULL, root REAL, status TEXT NOT NULL,
                iteration_count INTEGER NOT NULL)""")
            connection.commit()
        except sqlite3.Error:
            connection.close()
            raise
        return connection

    def _execute(self, sql: str, parameters: tuple = ()) -> list[sqlite3.Row]:
        connection = None
        try:
            connection = self._connect()
            with connection:
                return connection.execute(sql, parameters).fetchall()
        except (OSError, sqlite3.Error) as exc:
            raise HistoryError(f"No se pudo acceder al historial local: {exc}") from exc
        finally:
            if connection is not None:
                connection.close()

    def save(self, calculation: Calculation) -> str:
        identifier = str(uuid4())
        result = calculation.result
        self._execute("INSERT INTO calculations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (identifier, datetime.now(timezone.utc).isoformat(), calculation.function,
                       calculation.derivative, calculation.x0, calculation.tolerance,
                       calculation.max_iterations, result.root if result.converged else None,
                       result.status.value, len(result.iterations)))
        return identifier

    def recent(self, query: str = "") -> list[HistoryEntry]:
        # instr busca literalmente: %, _ y comillas no son comodines ni SQL.
        rows = self._execute("SELECT * FROM calculations WHERE instr(lower(function), lower(?)) > 0 ORDER BY created_at DESC, id DESC", (query,))
        return [HistoryEntry(**dict(row)) for row in rows]

    def get(self, identifier: str) -> HistoryEntry | None:
        rows = self._execute("SELECT * FROM calculations WHERE id = ?", (identifier,))
        return HistoryEntry(**dict(rows[0])) if rows else None

    def delete(self, identifier: str) -> None:
        self._execute("DELETE FROM calculations WHERE id = ?", (identifier,))

    def clear(self) -> None:
        self._execute("DELETE FROM calculations")
