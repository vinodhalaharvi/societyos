from __future__ import annotations
from ..connection import get_connection


async def insert_vote(run_id: str, round_num: int, agent: str, vote: int, weight: float) -> None:
    conn = await get_connection()
    async with conn:
        await conn.execute(
            "INSERT INTO votes (run_id, round, agent, vote, weight) VALUES (?, ?, ?, ?, ?)",
            (run_id, round_num, agent, vote, weight),
        )
        await conn.commit()


async def get_votes(run_id: str) -> list[dict]:
    conn = await get_connection()
    async with conn:
        async with conn.execute(
            "SELECT * FROM votes WHERE run_id = ? ORDER BY timestamp ASC", (run_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]
