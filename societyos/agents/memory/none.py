from .base import BaseMemory
from ..proposal import Proposal


class NoneMemory(BaseMemory):
    def add(self, proposal: Proposal) -> None:
        pass

    def recent(self, n: int = 10) -> list[Proposal]:
        return []

    def clear(self) -> None:
        pass
