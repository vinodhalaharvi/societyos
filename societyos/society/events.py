from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
import json

EventType = Literal["run_start","round_start","proposal","conflict","debate","vote","blackboard_update","synthesis","run_complete","error"]

@dataclass
class RunEvent:
    event_type: EventType
    round: int = 0
    from_agent: str | None = None
    to_agent: str | None = None
    content: str = ""
    confidence: float | None = None
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {"event": self.event_type, "round": self.round, "from": self.from_agent,
                "to": self.to_agent, "content": self.content, "confidence": self.confidence,
                "metadata": self.metadata, "timestamp": self.timestamp.isoformat()}

    def to_sse(self) -> str:
        return f"data: {json.dumps(self.to_dict())}\n\n"
