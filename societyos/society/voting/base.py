from abc import ABC, abstractmethod
from ...agents.proposal import Proposal

class BaseVotingStrategy(ABC):
    @abstractmethod
    def decide(self, proposals: list[Proposal]) -> list[Proposal]:
        pass
