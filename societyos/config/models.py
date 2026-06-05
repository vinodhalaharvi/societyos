from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class ToolConfig(BaseModel):
    enabled: bool = True
    options: dict = Field(default_factory=dict)


class AgentConfig(BaseModel):
    name: str
    role: str
    personality: str
    weight: float = Field(default=1.0, ge=0.1, le=5.0)
    tools: list[str] = Field(default_factory=list)
    memory: Literal["none", "short_term", "episodic"] = "short_term"


class OutputConfig(BaseModel):
    format: Literal["markdown", "json", "html"] = "markdown"
    save_to: str = "./reports/"


class SocietyConfig(BaseModel):
    name: str
    decision_strategy: Literal["weighted_vote", "consensus", "majority", "dictator"] = "weighted_vote"
    max_rounds: int = Field(default=5, ge=1, le=20)
    benchmark_vs_single_agent: bool = True
    synthesizer: str | None = None
    agents: list[AgentConfig] = Field(min_length=1)
    rules: str = ""
    tools: dict[str, ToolConfig] = Field(default_factory=dict)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @field_validator("agents")
    @classmethod
    def agent_names_unique(cls, agents: list[AgentConfig]) -> list[AgentConfig]:
        names = [a.name for a in agents]
        if len(names) != len(set(names)):
            raise ValueError("Each agent must have a unique name.")
        return agents
