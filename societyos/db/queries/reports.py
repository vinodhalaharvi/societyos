from __future__ import annotations
from ..connection import get_connection


async def save_report(run_id: str, content: str, fmt: str = "markdown") -> None:
    conn = await get_connection()
    async with conn:
        await conn.execute(
            "INSERT OR REPLACE INTO reports (run_id, content, format) VALUES (?, ?, ?)",
            (run_id, content, fmt),
        )
        await conn.commit()


async def get_report(run_id: str) -> dict | None:
    conn = await get_connection()
    async with conn:
        async with conn.execute(
            "SELECT * FROM reports WHERE run_id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
