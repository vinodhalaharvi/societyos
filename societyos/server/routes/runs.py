from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ...config.loader import load_config
from ...db.queries.runs import get_run, list_runs
from ...db.queries.events import get_events, get_max_round
from ...db.queries.reports import get_report
from ...db.queries.reputation import get_reputation
from ...society.runner import run_society

router = APIRouter(prefix="/api/runs", tags=["runs"])


class StartRunRequest(BaseModel):
    config_path: str
    task: str


@router.post("")
async def start_run(req: StartRunRequest):
    try:
        config = load_config(req.config_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    async def event_stream():
        async for event in run_society(config, req.task):
            yield event.to_sse()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("")
async def list_runs_endpoint(society_id: str | None = None, limit: int = 20):
    return await list_runs(society_id=society_id, limit=limit)


@router.get("/{run_id}")
async def get_run_endpoint(run_id: str):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/replay")
async def replay_run(run_id: str, up_to_round: int | None = None):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    events = await get_events(run_id=run_id, up_to_round=up_to_round)
    max_round = await get_max_round(run_id)
    return {"run_id": run_id, "max_round": max_round, "up_to_round": up_to_round, "events": events}


@router.get("/{run_id}/report")
async def get_report_endpoint(run_id: str):
    report = await get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{run_id}/reputation")
async def get_run_reputation(run_id: str):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return await get_reputation(run["society_id"])
