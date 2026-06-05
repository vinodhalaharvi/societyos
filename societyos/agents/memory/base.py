from abc import ABC, abstractmethod
from ..proposal import Proposal


class BaseMemory(ABC):

    @abstractmethod
    def add(self, proposal: Proposal) -> None:
        pass

    @abstractmethod
    def recent(self, n: int = 10) -> list[Proposal]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    def format_for_prompt(self, n: int = 5) -> str:
        items = self.recent(n)
        if not items:
            return "No prior memory."
        lines = []
        for p in items:
            lines.append(
                f"- Round {p.round} | {p.agent} (conf {p.confidence:.2f}): {p.claim}"
            )
        return "\n".join(lines)
