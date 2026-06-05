from ...agents.proposal import Proposal
from .base import BaseVotingStrategy

class ConsensusStrategy(BaseVotingStrategy):
    def __init__(self, min_confidence: float = 0.7):
        self.min_confidence = min_confidence

    def decide(self, proposals: list[Proposal]) -> list[Proposal]:
        if not proposals:
            return []
        winners = [p for p in proposals if p.confidence >= self.min_confidence]
        return winners if winners else [max(proposals, key=lambda p: p.confidence)]
