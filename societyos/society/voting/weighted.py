from ...agents.proposal import Proposal
from .base import BaseVotingStrategy

class WeightedVoteStrategy(BaseVotingStrategy):
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def decide(self, proposals: list[Proposal]) -> list[Proposal]:
        if not proposals:
            return []
        scored = [(p.confidence * getattr(p, "weight", 1.0), p) for p in proposals]
        max_score = max(s for s, _ in scored)
        cutoff = max_score * self.threshold
        winners = [p for score, p in scored if score >= cutoff]
        return winners if winners else [max(proposals, key=lambda p: p.confidence)]
