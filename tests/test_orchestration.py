import pytest
from unittest.mock import AsyncMock, patch
from societyos.agents.proposal import Proposal
from societyos.society.blackboard import Blackboard
from societyos.society.events import RunEvent
from societyos.society.voting.weighted import WeightedVoteStrategy
from societyos.society.voting.majority import MajorityVoteStrategy
from societyos.society.voting.consensus import ConsensusStrategy
from societyos.society.voting.factory import build_voting_strategy
from societyos.society.coordinator import Coordinator
from societyos.config.models import SocietyConfig, AgentConfig

def make_proposal(agent="A", confidence=0.8, claim="Do X"):
    p = Proposal(agent=agent, claim=claim, confidence=confidence, reasoning="reason")
    p.weight = 1.0
    return p

def make_config(n_agents=2, max_rounds=1):
    agents = [AgentConfig(name=f"Agent{i}", role=f"Role{i}", personality="neutral") for i in range(n_agents)]
    return SocietyConfig(name="Test", agents=agents, max_rounds=max_rounds)

VALID_JSON = '{"claim": "Move forward.", "confidence": 0.8, "reasoning": "Data supports it.", "dependencies": []}'
SYNTH_TEXT = "# Final Report\nSummary: All good."

class TestBlackboard:
    def test_write_and_read(self):
        bb = Blackboard()
        bb.write("key1", "value1")
        assert bb.read("key1") == "value1"

    def test_missing_key_returns_none(self):
        assert Blackboard().read("nope") is None

    def test_snapshot_is_copy(self):
        bb = Blackboard()
        bb.write("k", "v")
        snap = bb.snapshot()
        snap["k"] = "modified"
        assert bb.read("k") == "v"

    def test_history_recorded(self):
        bb = Blackboard()
        bb.write("k", "v", author="CEO")
        assert bb.history()[0]["author"] == "CEO"

    def test_len(self):
        bb = Blackboard()
        bb.write("a", "1")
        bb.write("b", "2")
        assert len(bb) == 2

class TestWeightedVote:
    def test_high_confidence_wins(self):
        winners = WeightedVoteStrategy().decide([make_proposal("A", 0.9), make_proposal("B", 0.3)])
        assert any(p.agent == "A" for p in winners)

    def test_empty_returns_empty(self):
        assert WeightedVoteStrategy().decide([]) == []

    def test_always_returns_at_least_one(self):
        assert len(WeightedVoteStrategy().decide([make_proposal("A", 0.1), make_proposal("B", 0.2)])) >= 1

class TestMajorityVote:
    def test_above_threshold_wins(self):
        winners = MajorityVoteStrategy().decide([make_proposal("A", 0.8), make_proposal("B", 0.3)])
        assert any(p.agent == "A" for p in winners)

    def test_fallback_when_none_pass(self):
        winners = MajorityVoteStrategy().decide([make_proposal("A", 0.3), make_proposal("B", 0.4)])
        assert winners[0].agent == "B"

class TestConsensusStrategy:
    def test_high_confidence_passes(self):
        winners = ConsensusStrategy(min_confidence=0.7).decide([make_proposal("A", 0.9), make_proposal("B", 0.5)])
        assert any(p.agent == "A" for p in winners)

class TestVotingFactory:
    def test_weighted_vote(self):
        assert isinstance(build_voting_strategy("weighted_vote"), WeightedVoteStrategy)

    def test_majority(self):
        assert isinstance(build_voting_strategy("majority"), MajorityVoteStrategy)

    def test_consensus(self):
        assert isinstance(build_voting_strategy("consensus"), ConsensusStrategy)

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            build_voting_strategy("coin_flip")

class TestRunEvent:
    def test_to_dict(self):
        d = RunEvent(event_type="proposal", round=1, from_agent="CEO", content="Do X").to_dict()
        assert d["event"] == "proposal"
        assert "timestamp" in d

    def test_to_sse(self):
        sse = RunEvent(event_type="vote", round=2, content="passed").to_sse()
        assert sse.startswith("data: ")
        assert sse.endswith("\n\n")

class TestCoordinator:
    def _make_coordinator(self, n_agents=2, max_rounds=1):
        return Coordinator(make_config(n_agents=n_agents, max_rounds=max_rounds))

    async def _collect(self, coordinator, task):
        events = []
        async for event in coordinator.run(task):
            events.append(event)
        return events

    @pytest.mark.asyncio
    async def test_run_emits_run_start(self):
        coord = self._make_coordinator()
        with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_JSON)), \
             patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT)):
            events = await self._collect(coord, "Test task")
        assert "run_start" in [e.event_type for e in events]

    @pytest.mark.asyncio
    async def test_run_emits_proposals(self):
        coord = self._make_coordinator(n_agents=2)
        with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_JSON)), \
             patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT)):
            events = await self._collect(coord, "Test task")
        assert len([e for e in events if e.event_type == "proposal"]) >= 2

    @pytest.mark.asyncio
    async def test_run_emits_synthesis(self):
        coord = self._make_coordinator()
        with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_JSON)), \
             patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT)):
            events = await self._collect(coord, "Test task")
        synth = [e for e in events if e.event_type == "synthesis"]
        assert len(synth) == 1
        assert synth[0].content == SYNTH_TEXT

    @pytest.mark.asyncio
    async def test_run_emits_run_complete(self):
        coord = self._make_coordinator()
        with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_JSON)), \
             patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT)):
            events = await self._collect(coord, "Test task")
        assert events[-1].event_type == "run_complete"

    @pytest.mark.asyncio
    async def test_blackboard_updated_after_round(self):
        coord = self._make_coordinator()
        with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_JSON)), \
             patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT)):
            await self._collect(coord, "Test task")
        assert len(coord.blackboard) > 0

    @pytest.mark.asyncio
    async def test_agent_failure_does_not_crash_run(self):
        coord = self._make_coordinator(n_agents=2)
        call_count = 0
        async def flaky_chat(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("LLM timeout")
            return VALID_JSON
        with patch("societyos.agents.base.chat", new=flaky_chat), \
             patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT)):
            events = await self._collect(coord, "Test task")
        assert events[-1].event_type == "run_complete"


# --- standalone async tests (class-based async has issues with Python 3.14) ---

VALID_JSON2 = '{"claim": "Move forward.", "confidence": 0.8, "reasoning": "Data supports it.", "dependencies": []}'
SYNTH_TEXT2 = "# Final Report\nSummary: All good."

def _make_coord(n_agents=2, max_rounds=1):
    from societyos.config.models import SocietyConfig, AgentConfig
    from societyos.society.coordinator import Coordinator
    agents = [AgentConfig(name=f"Agent{i}", role=f"Role{i}", personality="neutral") for i in range(n_agents)]
    cfg = SocietyConfig(name="Test", agents=agents, max_rounds=max_rounds)
    return Coordinator(cfg)

async def _collect(coordinator, task):
    events = []
    async for event in coordinator.run(task):
        events.append(event)
    return events

@pytest.mark.asyncio
async def test_coordinator_run_start():
    coord = _make_coord()
    with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_JSON2)), \
         patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT2)):
        events = await _collect(coord, "Test task")
    assert "run_start" in [e.event_type for e in events]

@pytest.mark.asyncio
async def test_coordinator_emits_proposals():
    coord = _make_coord(n_agents=2)
    with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_JSON2)), \
         patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT2)):
        events = await _collect(coord, "Test task")
    assert len([e for e in events if e.event_type == "proposal"]) >= 2

@pytest.mark.asyncio
async def test_coordinator_emits_synthesis():
    coord = _make_coord()
    with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_JSON2)), \
         patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT2)):
        events = await _collect(coord, "Test task")
    synth = [e for e in events if e.event_type == "synthesis"]
    assert len(synth) == 1
    assert synth[0].content == SYNTH_TEXT2

@pytest.mark.asyncio
async def test_coordinator_emits_run_complete():
    coord = _make_coord()
    with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_JSON2)), \
         patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT2)):
        events = await _collect(coord, "Test task")
    assert events[-1].event_type == "run_complete"

@pytest.mark.asyncio
async def test_coordinator_blackboard_updated():
    coord = _make_coord()
    with patch("societyos.agents.base.chat", new=AsyncMock(return_value=VALID_JSON2)), \
         patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT2)):
        await _collect(coord, "Test task")
    assert len(coord.blackboard) > 0

@pytest.mark.asyncio
async def test_coordinator_agent_failure_does_not_crash():
    coord = _make_coord(n_agents=2)
    call_count = 0
    async def flaky(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("timeout")
        return VALID_JSON2
    with patch("societyos.agents.base.chat", new=flaky), \
         patch("societyos.society.coordinator.chat", new=AsyncMock(return_value=SYNTH_TEXT2)):
        events = await _collect(coord, "Test task")
    assert events[-1].event_type == "run_complete"
