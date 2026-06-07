from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Proposal:
    agent: str
    claim: str
    confidence: float
    reasoning: str
    dependencies: list[str] = field(default_factory=list)
    round: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_llm_response(cls, agent_name: str, raw: str, round_num: int = 0) -> "Proposal":
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Agent '{agent_name}' returned invalid JSON:\n{raw}\nError: {exc}"
            ) from exc
        required = {"claim", "confidence", "reasoning"}
        missing = required - data.keys()
        if missing:
            raise ValueError(
                f"Agent '{agent_name}' JSON missing fields: {missing}\nGot: {data}"
            )
        confidence = max(0.0, min(1.0, float(data["confidence"])))
        return cls(
            agent=agent_name,
            claim=str(data["claim"]),
            confidence=confidence,
            reasoning=str(data["reasoning"]),
            dependencies=list(data.get("dependencies", [])),
            round=round_num,
        )

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "claim": self.claim,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "dependencies": self.dependencies,
            "round": self.round,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        return (
            f"[{self.agent} | round {self.round} | confidence {self.confidence:.2f}]\n"
            f"Claim: {self.claim}\n"
            f"Reasoning: {self.reasoning}"
        )
