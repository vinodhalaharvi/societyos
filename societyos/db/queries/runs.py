from __future__ import annotations
import uuid
from datetime import datetime, timezone
from ..connection import get_connection


async def create_society(name: str, config_yaml: str) -> str:
    society_id = str(uuid.uuid4())
    conn = await get_connection()
    async with conn:
        await conn.execute(
            "INSERT OR IGNORE INTO societies (id, name, config_yaml) VALUES (?, ?, ?)",
            (society_id, name, config_yaml),
        )
        await conn.commit()
    return society_id


async def get_or_create_society(name: str, config_yaml: str) -> str:
    conn = await get_connection()
    async with conn:
        async with conn.execute(
            "SELECT id FROM societies WHERE name = ?", (name,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row["id"]
    return await create_society(name, config_yaml)


async def create_run(society_id: str, task: str) -> str:
    run_id = str(uuid.uuid4())
    conn = await get_connection()
    async with conn:
        await conn.execute(
            "INSERT INTO runs (id, society_id, task, status) VALUES (?, ?, ?, 'running')",
            (run_id, society_id, task),
        )
        await conn.commit()
    return run_id


async def mark_run_complete(run_id: str) -> None:
    conn = await get_connection()
    async with conn:
        await conn.execute(
            "UPDATE runs SET status = 'complete', finished_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), run_id),
        )
        await conn.commit()


async def mark_run_failed(run_id: str) -> None:
    conn = await get_connection()
    async with conn:
        await conn.execute(
            "UPDATE runs SET status = 'failed', finished_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), run_id),
        )
        await conn.commit()


async def get_run(run_id: str) -> dict | None:
    conn = await get_connection()
    async with conn:
        async with conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_runs(society_id: str | None = None, limit: int = 20) -> list[dict]:
    conn = await get_connection()
    async with conn:
        if society_id:
            async with conn.execute(
                "SELECT * FROM runs WHERE society_id = ? ORDER BY started_at DESC LIMIT ?",
                (society_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with conn.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]
