from .base import BaseMemory
from .none import NoneMemory
from .short_term import ShortTermMemory


def build_memory(memory_type: str) -> BaseMemory:
    if memory_type == "none":
        return NoneMemory()
    if memory_type in ("short_term", "episodic"):
        return ShortTermMemory()
    raise ValueError(f"Unknown memory type: {memory_type!r}")
