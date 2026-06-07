import pytest
from unittest.mock import AsyncMock, patch
from societyos.agents.proposal import Proposal
from societyos.agents.memory.none import NoneMemory
from societyos.agents.memory.short_term import ShortTermMemory
from societyos.agents.memory.factory import build_memory
from societyos.agents.prompt import compile_system_prompt
from societyos.agents.base import BaseAgent, RoundContext
from societyos.agents.factory import AgentFactory
from societyos.config.models import AgentConfig, SocietyConfig


def make_agent_config(**kwargs) -> AgentConfig:
    defaults = dict(name="TestAgent", role="Tester", personality="curious")
    defaults.update(kwargs)
    return AgentConfig(**defaults)

def make_society_config(agents=None) -> SocietyConfig:
    if agents is None:
        agents = [make_agent_config()]
    return SocietyConfig(name="Test Society", agents=agents)

VALID_RESPONSE = '{"claim": "We should expand.", "confidence": 0.85, "reasoning": "Growth metrics are strong.", "dependencies": []}'


class TestProposal:
    def test_parse_valid_json(self):
        raw = '{"claim": "We should pivot.", "confidence": 0.9, "reasoning": "Market data supports this.", "dependencies": []}'
        p = Proposal.from_llm_response("CEO", raw, round_num=1)
        assert p.agent == "CEO"
        assert p.claim == "We should pivot."
        assert p.confidence == 0.9
        assert p.round == 1

    def test_strips_markdown_fences(self):
        raw = '```json\n{"claim": "X", "confidence": 0.5, "reasoning": "Y"}\n```'
        p = Proposal.from_llm_response("CFO", raw)
        assert p.claim == "X"

    def test_confidence_clamped(self):
        raw = '{"claim": "X", "confidence": 1.5, "reasoning": "Y"}'
        p = Proposal.from_llm_response("CTO", raw)
        assert p.confidence == 1.0

    def test_missing_field_raises(self):
        raw = '{"claim": "X", "confidence": 0.5}'
        with pytest.raises(ValueError, match="missing fields"):
            Proposal.from_llm_response("Agent", raw)

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            Proposal.from_llm_response("Agent", "not json at all")

    def test_to_dict(self):
        raw = '{"claim": "C", "confidence": 0.7, "reasoning": "R"}'
        p = Proposal.from_llm_response("X", raw, round_num=2)
        d = p.to_dict()
        assert d["agent"] == "X"
        assert d["round"] == 2
        assert "timestamp" in d


class TestNoneMemory:
    def test_remembers_nothing(self):
        m = NoneMemory()
        p = Proposal(agent="A", claim="c", confidence=0.8, reasoning="r")
        m.add(p)
        assert m.recent() == []

    def test_format_returns_no_prior(self):
        assert NoneMemory().format_for_prompt() == "No prior memory."


class TestShortTermMemory:
    def _p(self, agent="A", round_num=1):
        return Proposal(agent=agent, claim="c", confidence=0.8, reasoning="r", round=round_num)

    def test_stores_and_retrieves(self):
        m = ShortTermMemory()
        m.add(self._p())
        assert len(m.recent()) == 1

    def test_respects_max_items(self):
        m = ShortTermMemory(max_items=3)
        for i in range(5):
            m.add(self._p(round_num=i))
        assert len(m.recent(10)) == 3

    def test_clear(self):
        m = ShortTermMemory()
        m.add(self._p())
        m.clear()
        assert m.recent() == []

    def test_format_for_prompt(self):
        m = ShortTermMemory()
        m.add(self._p(agent="CEO", round_num=1))
        text = m.format_for_prompt()
        assert "CEO" in text


class TestMemoryFactory:
    def test_none(self):
        assert isinstance(build_memory("none"), NoneMemory)

    def test_short_term(self):
        assert isinstance(build_memory("short_term"), ShortTermMemory)

    def test_episodic_falls_back(self):
        assert isinstance(build_memory("episodic"), ShortTermMemory)

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            build_memory("magic_memory")


class TestPromptCompiler:
    def test_contains_agent_name(self):
        cfg = make_agent_config(name="Architect")
        prompt = compile_system_prompt(cfg, rules="- Be concise")
        assert "Architect" in prompt

    def test_contains_rules(self):
        cfg = make_agent_config()
        prompt = compile_system_prompt(cfg, rules="- Always cite sources")
        assert "Always cite sources" in prompt

    def test_empty_rules_shows_fallback(self):
        cfg = make_agent_config()
        prompt = compile_system_prompt(cfg, rules="")
        assert "No specific rules defined." in prompt

    def test_json_instructions_present(self):
        cfg = make_agent_config()
        prompt = compile_system_prompt(cfg, rules="")
        assert '"claim"' in prompt


class TestBaseAgent:
    def _make_agent(self, **kwargs) -> BaseAgent:
        cfg = make_agent_config(**kwargs)
        return BaseAgent(cfg, rules="- Be concise")

    @pytest.mark.asyncio
    async def test_think_returns_proposal(self):
        agent = self._make_agent(name="CEO")
        context = RoundContext(task="Should we expand?", round_num=1)
        with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_RESPONSE)):
            proposal = await agent.think(context)
        assert isinstance(proposal, Proposal)
        assert proposal.agent == "CEO"
        assert proposal.confidence == 0.85

    @pytest.mark.asyncio
    async def test_think_stores_in_memory(self):
        agent = self._make_agent(memory="short_term")
        context = RoundContext(task="Test task", round_num=1)
        with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_RESPONSE)):
            await agent.think(context)
        assert len(agent.memory.recent()) == 1

    @pytest.mark.asyncio
    async def test_think_with_prior_proposals(self):
        agent = self._make_agent(name="CFO")
        prior = [Proposal(agent="CEO", claim="Expand now", confidence=0.9, reasoning="Good metrics", round=1)]
        context = RoundContext(task="Should we expand?", round_num=2, prior_proposals=prior)
        captured = []
        async def mock_chat(messages, **kwargs):
            captured.extend(messages)
            return VALID_RESPONSE
        with patch("societyos.agents.base.chat", new=mock_chat):
            await agent.think(context)
        user_msg = next(m for m in captured if m["role"] == "user")
        assert "CEO" in user_msg["content"]


class TestAgentFactory:
    def test_builds_all_agents(self):
        cfg = make_society_config(agents=[make_agent_config(name="A"), make_agent_config(name="B")])
        agents = AgentFactory.build_all(cfg)
        assert len(agents) == 2

    def test_build_by_name(self):
        cfg = make_society_config(agents=[make_agent_config(name="CEO"), make_agent_config(name="CFO")])
        agent = AgentFactory.build_by_name(cfg, "CFO")
        assert agent.name == "CFO"

    def test_build_by_name_missing_raises(self):
        cfg = make_society_config()
        with pytest.raises(ValueError, match="No agent named"):
            AgentFactory.build_by_name(cfg, "Ghost")

    def test_rules_injected_into_system_prompt(self):
        cfg = SocietyConfig(name="Test", agents=[make_agent_config(name="X")], rules="- Never lie")
        agents = AgentFactory.build_all(cfg)
        assert "Never lie" in agents[0].system_prompt
