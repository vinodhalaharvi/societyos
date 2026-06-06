from __future__ import annotations
from ..connection import get_connection


async def record_proposal(society_id: str, agent_name: str, won: bool, confidence: float) -> None:
    conn = await get_connection()
    async with conn:
        await conn.execute(
            "INSERT OR IGNORE INTO agent_reputation (society_id, agent_name) VALUES (?, ?)",
            (society_id, agent_name),
        )
        await conn.execute(
            """UPDATE agent_reputation
               SET total_proposals = total_proposals + 1,
                   proposals_won   = proposals_won + ?,
                   avg_confidence  = (avg_confidence * total_proposals + ?) / (total_proposals + 1),
                   updated_at      = CURRENT_TIMESTAMP
               WHERE society_id = ? AND agent_name = ?""",
            (1 if won else 0, confidence, society_id, agent_name),
        )
        await conn.commit()


async def get_reputation(society_id: str) -> list[dict]:
    conn = await get_connection()
    async with conn:
        async with conn.execute(
            """SELECT agent_name, total_proposals, proposals_won, avg_confidence
               FROM agent_reputation WHERE society_id = ? ORDER BY proposals_won DESC""",
            (society_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_win_rate(society_id: str, agent_name: str) -> float:
    conn = await get_connection()
    async with conn:
        async with conn.execute(
            """SELECT total_proposals, proposals_won FROM agent_reputation
               WHERE society_id = ? AND agent_name = ?""",
            (society_id, agent_name),
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row["total_proposals"] == 0:
                return 0.0
            return row["proposals_won"] / row["total_proposals"]
