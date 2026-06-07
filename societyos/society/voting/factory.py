from .base import BaseVotingStrategy
from .weighted import WeightedVoteStrategy
from .majority import MajorityVoteStrategy
from .consensus import ConsensusStrategy

def build_voting_strategy(strategy: str) -> BaseVotingStrategy:
    if strategy == "weighted_vote":
        return WeightedVoteStrategy()
    if strategy == "majority":
        return MajorityVoteStrategy()
    if strategy in ("consensus", "dictator"):
        return ConsensusStrategy()
    raise ValueError(f"Unknown voting strategy: {strategy!r}")
