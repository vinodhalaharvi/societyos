from __future__ import annotations
from ..connection import get_connection


async def insert_event(
    run_id: str,
    round_num: int,
    event_type: str,
    from_agent: str | None = None,
    to_agent: str | None = None,
    content: str = "",
    confidence: float | None = None,
) -> None:
    conn = await get_connection()
    async with conn:
        await conn.execute(
            """INSERT INTO events
               (run_id, round, event_type, from_agent, to_agent, content, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (run_id, round_num, event_type, from_agent, to_agent, content, confidence),
        )
        await conn.commit()


async def get_events(run_id: str, up_to_round: int | None = None) -> list[dict]:
    conn = await get_connection()
    async with conn:
        if up_to_round is not None:
            async with conn.execute(
                """SELECT * FROM events WHERE run_id = ? AND round <= ?
                   ORDER BY timestamp ASC""",
                (run_id, up_to_round),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with conn.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY timestamp ASC",
                (run_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_max_round(run_id: str) -> int:
    conn = await get_connection()
    async with conn:
        async with conn.execute(
            "SELECT MAX(round) as max_round FROM events WHERE run_id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["max_round"] or 0
