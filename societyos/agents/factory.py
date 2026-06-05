from ..config.models import SocietyConfig
from .base import BaseAgent
from .memory.factory import build_memory


class AgentFactory:

    @staticmethod
    def build_all(config: SocietyConfig) -> list[BaseAgent]:
        agents = []
        for agent_cfg in config.agents:
            memory = build_memory(agent_cfg.memory)
            agent = BaseAgent(config=agent_cfg, rules=config.rules, memory=memory)
            agents.append(agent)
        return agents

    @staticmethod
    def build_by_name(config: SocietyConfig, name: str) -> BaseAgent:
        for agent_cfg in config.agents:
            if agent_cfg.name == name:
                return BaseAgent(
                    config=agent_cfg,
                    rules=config.rules,
                    memory=build_memory(agent_cfg.memory),
                )
        raise ValueError(
            f"No agent named {name!r} in society {config.name!r}. "
            f"Available: {[a.name for a in config.agents]}"
        )
