from ...agents.proposal import Proposal
from .base import BaseVotingStrategy

class MajorityVoteStrategy(BaseVotingStrategy):
    def decide(self, proposals: list[Proposal]) -> list[Proposal]:
        if not proposals:
            return []
        winners = [p for p in proposals if p.confidence > 0.5]
        return winners if winners else [max(proposals, key=lambda p: p.confidence)]
