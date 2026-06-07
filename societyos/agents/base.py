from __future__ import annotations
from dataclasses import dataclass, field
from ..config.models import AgentConfig
from ..qwen_client import chat
from .memory.base import BaseMemory
from .memory.factory import build_memory
from .proposal import Proposal
from .prompt import compile_system_prompt


@dataclass
class RoundContext:
    task: str
    round_num: int
    blackboard: dict = field(default_factory=dict)
    prior_proposals: list[Proposal] = field(default_factory=list)
    instructions: str = ""


class BaseAgent:
    def __init__(self, config: AgentConfig, rules: str = "", memory: BaseMemory | None = None):
        self.config = config
        self.name = config.name
        self.role = config.role
        self.weight = config.weight
        self.allowed_tools: list[str] = list(config.tools)
        self.system_prompt = compile_system_prompt(config, rules)
        self.memory: BaseMemory = memory or build_memory(config.memory)

    async def think(self, context: RoundContext) -> Proposal:
        user_message = self._build_user_message(context)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user",   "content": user_message},
        ]
        raw_response = await chat(messages=messages, temperature=0.7)
        proposal = Proposal.from_llm_response(
            agent_name=self.name,
            raw=raw_response,
            round_num=context.round_num,
        )
        self.memory.add(proposal)
        return proposal

    def _build_user_message(self, context: RoundContext) -> str:
        parts: list[str] = []
        parts.append(f"## Task\n{context.task}")
        if context.prior_proposals:
            parts.append("## What other agents have proposed so far")
            for p in context.prior_proposals:
                parts.append(
                    f"**{p.agent}** (round {p.round}, confidence {p.confidence:.2f}):\n"
                    f"{p.claim}\nReasoning: {p.reasoning}"
                )
        if context.blackboard:
            parts.append("## Shared blackboard (agreed facts so far)")
            for key, value in context.blackboard.items():
                parts.append(f"- {key}: {value}")
        memory_summary = self.memory.format_for_prompt(n=5)
        if memory_summary != "No prior memory.":
            parts.append(f"## Your memory from earlier rounds\n{memory_summary}")
        if context.instructions:
            parts.append(f"## Special instructions for this round\n{context.instructions}")
        parts.append("Now respond with your JSON proposal. Remember: only a raw JSON object, no markdown fences.")
        return "\n\n".join(parts)

    def __repr__(self) -> str:
        return f"<Agent {self.name!r} role={self.role!r} weight={self.weight}>"
