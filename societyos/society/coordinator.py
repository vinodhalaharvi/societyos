from __future__ import annotations
import asyncio
from collections.abc import AsyncIterator
from ..agents.base import BaseAgent, RoundContext
from ..agents.proposal import Proposal
from ..config.models import SocietyConfig
from ..agents.factory import AgentFactory
from ..qwen_client import chat
from .blackboard import Blackboard
from .events import RunEvent
from .voting.factory import build_voting_strategy

CONFLICT_CONFIDENCE_THRESHOLD = 0.6

class Coordinator:
    def __init__(self, config: SocietyConfig):
        self.config = config
        self.agents: list[BaseAgent] = AgentFactory.build_all(config)
        self.blackboard = Blackboard()
        self.voting = build_voting_strategy(config.decision_strategy)
        self._synthesizer_name = config.synthesizer or config.agents[-1].name

    async def run(self, task: str) -> AsyncIterator[RunEvent]:
        all_proposals: list[Proposal] = []
        yield RunEvent(event_type="run_start", content=task,
                       metadata={"society": self.config.name, "agents": [a.name for a in self.agents]})

        for round_num in range(1, self.config.max_rounds + 1):
            yield RunEvent(event_type="round_start", round=round_num,
                           content=f"Round {round_num} of {self.config.max_rounds}")
            round_proposals = await self._run_round(task, round_num, all_proposals)
            for p in round_proposals:
                yield RunEvent(event_type="proposal", round=round_num, from_agent=p.agent,
                               content=p.claim, confidence=p.confidence,
                               metadata={"reasoning": p.reasoning, "dependencies": p.dependencies})

            conflicts = self._detect_conflicts(round_proposals)
            if conflicts:
                yield RunEvent(event_type="conflict", round=round_num,
                               content=f"{len(conflicts)} conflict(s) detected",
                               metadata={"agents": [p.agent for p in conflicts]})
                debate_proposals = await self._run_debate(task, round_num, conflicts, all_proposals)
                for p in debate_proposals:
                    yield RunEvent(event_type="debate", round=round_num, from_agent=p.agent,
                                   content=p.claim, confidence=p.confidence)
                round_proposals.extend(debate_proposals)

            winners = self.voting.decide(round_proposals)
            tally = {p.agent: p.confidence for p in round_proposals}
            yield RunEvent(event_type="vote", round=round_num,
                           content=f"{len(winners)} proposal(s) approved",
                           metadata={"tally": tally, "winners": [p.agent for p in winners]})

            for p in winners:
                key = f"round_{round_num}_{p.agent}"
                self.blackboard.write(key, p.claim, author=p.agent)
                yield RunEvent(event_type="blackboard_update", round=round_num,
                               from_agent=p.agent, content=f"{key} = {p.claim[:80]}")

            all_proposals.extend(round_proposals)
            if self._consensus_reached(winners):
                break

        report = await self._synthesize(task=task, all_proposals=all_proposals)
        yield RunEvent(event_type="synthesis", from_agent=self._synthesizer_name, content=report)
        yield RunEvent(event_type="run_complete", content="Society run complete.",
                       metadata={"total_proposals": len(all_proposals)})

    async def _run_round(self, task, round_num, all_proposals):
        context = RoundContext(task=task, round_num=round_num,
                               blackboard=self.blackboard.snapshot(), prior_proposals=all_proposals)
        results = await asyncio.gather(*[a.think(context) for a in self.agents], return_exceptions=True)
        proposals = []
        for agent, result in zip(self.agents, results):
            if isinstance(result, Exception):
                proposals.append(Proposal(agent=agent.name, claim="[Agent failed]",
                                          confidence=0.0, reasoning=str(result)))
            else:
                result.weight = agent.weight
                proposals.append(result)
        return proposals

    async def _run_debate(self, task, round_num, conflicts, all_proposals):
        debate_proposals = []
        for proposal in conflicts:
            agent = self._get_agent(proposal.agent)
            if agent is None:
                continue
            context = RoundContext(task=task, round_num=round_num,
                                   blackboard=self.blackboard.snapshot(), prior_proposals=all_proposals,
                                   instructions="DEBATE round: strengthen or revise your position with better evidence.")
            try:
                rebuttal = await agent.think(context)
                rebuttal.weight = agent.weight
                debate_proposals.append(rebuttal)
            except Exception:
                pass
        return debate_proposals

    async def _synthesize(self, task, all_proposals):
        agent = self._get_agent(self._synthesizer_name) or self.agents[-1]
        context = RoundContext(task=task, round_num=0, blackboard=self.blackboard.snapshot(),
                               prior_proposals=all_proposals,
                               instructions="Write the FINAL REPORT as structured markdown with Summary, Key Decisions, Risks, and Next Steps.")
        messages = [{"role": "system", "content": agent.system_prompt},
                    {"role": "user", "content": agent._build_user_message(context)}]
        return await chat(messages=messages, temperature=0.5, max_tokens=3000)

    def _detect_conflicts(self, proposals):
        return [p for p in proposals if p.confidence < CONFLICT_CONFIDENCE_THRESHOLD]

    def _consensus_reached(self, winners):
        if not winners:
            return False
        return all(p.confidence >= 0.85 for p in winners)

    def _get_agent(self, name):
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None
