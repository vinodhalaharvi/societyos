from __future__ import annotations
import yaml
from collections.abc import AsyncIterator
from ..config.models import SocietyConfig
from ..db.migrations import run_migrations
from ..db.queries.runs import get_or_create_society, create_run, mark_run_complete, mark_run_failed
from ..db.queries.events import insert_event
from ..db.queries.votes import insert_vote
from ..db.queries.reports import save_report
from ..db.queries.reputation import record_proposal
from .coordinator import Coordinator
from .events import RunEvent


async def run_society(config: SocietyConfig, task: str) -> AsyncIterator[RunEvent]:
    await run_migrations()
    config_yaml = yaml.dump(config.model_dump())
    society_id = await get_or_create_society(config.name, config_yaml)
    run_id = await create_run(society_id, task)
    coordinator = Coordinator(config)
    try:
        async for event in coordinator.run(task):
            await insert_event(
                run_id=run_id, round_num=event.round, event_type=event.event_type,
                from_agent=event.from_agent, to_agent=event.to_agent,
                content=event.content, confidence=event.confidence,
            )
            if event.event_type == "vote":
                tally = event.metadata.get("tally", {})
                winners = event.metadata.get("winners", [])
                for agent_name, confidence in tally.items():
                    won = agent_name in winners
                    await insert_vote(run_id=run_id, round_num=event.round,
                                      agent=agent_name, vote=1 if won else 0,
                                      weight=_get_agent_weight(config, agent_name))
                    await record_proposal(society_id=society_id, agent_name=agent_name,
                                          won=won, confidence=confidence)
            if event.event_type == "synthesis":
                await save_report(run_id=run_id, content=event.content)
            if event.event_type == "run_complete":
                await mark_run_complete(run_id)
            yield event
    except Exception as exc:
        await mark_run_failed(run_id)
        yield RunEvent(event_type="error", content=str(exc))
        raise


def _get_agent_weight(config: SocietyConfig, agent_name: str) -> float:
    for agent in config.agents:
        if agent.name == agent_name:
            return agent.weight
    return 1.0
