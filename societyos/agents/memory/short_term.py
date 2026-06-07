from collections import deque
from .base import BaseMemory
from ..proposal import Proposal


class ShortTermMemory(BaseMemory):
    def __init__(self, max_items: int = 20):
        self._store: deque[Proposal] = deque(maxlen=max_items)

    def add(self, proposal: Proposal) -> None:
        self._store.append(proposal)

    def recent(self, n: int = 10) -> list[Proposal]:
        items = list(self._store)
        return items[-n:] if len(items) > n else items

    def clear(self) -> None:
        self._store.clear()
