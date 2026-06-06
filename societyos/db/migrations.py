import aiosqlite
from .connection import get_connection

SCHEMA = """
CREATE TABLE IF NOT EXISTS societies (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, config_yaml TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY, society_id TEXT REFERENCES societies(id),
    task TEXT NOT NULL, status TEXT DEFAULT 'running',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP, finished_at DATETIME
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT REFERENCES runs(id),
    round INTEGER NOT NULL, event_type TEXT NOT NULL,
    from_agent TEXT, to_agent TEXT, content TEXT, confidence REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT REFERENCES runs(id),
    round INTEGER NOT NULL, agent TEXT NOT NULL, vote INTEGER NOT NULL,
    weight REAL NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT REFERENCES runs(id) UNIQUE,
    content TEXT NOT NULL, format TEXT DEFAULT 'markdown',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS agent_reputation (
    id INTEGER PRIMARY KEY AUTOINCREMENT, society_id TEXT REFERENCES societies(id),
    agent_name TEXT NOT NULL, total_proposals INTEGER DEFAULT 0,
    proposals_won INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0.0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(society_id, agent_name)
);
"""

async def run_migrations() -> None:
    conn: aiosqlite.Connection = await get_connection()
    async with conn:
        await conn.executescript(SCHEMA)
        await conn.commit()
    print("✓ Database migrations complete")
