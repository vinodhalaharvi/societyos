"""
SQLite database connection.

We use aiosqlite for async access.
WAL (Write-Ahead Logging) mode is enabled so that:
  - The FastAPI server can READ the DB while the society loop is WRITING
  - No "database is locked" errors during a live run
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from ..settings import settings


async def get_connection() -> aiosqlite.Connection:
    """
    Open (or create) the SQLite database and return a connection.
    WAL mode and foreign-key enforcement are always set.
    """
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row  # rows behave like dicts
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    return conn
