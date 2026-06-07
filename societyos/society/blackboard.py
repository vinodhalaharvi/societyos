from __future__ import annotations
from datetime import datetime, timezone


class Blackboard:
    def __init__(self):
        self._state: dict[str, str] = {}
        self._history: list[dict] = []

    def write(self, key: str, value: str, author: str = "coordinator") -> None:
        self._state[key] = value
        self._history.append({"key": key, "value": value, "author": author,
                               "timestamp": datetime.now(timezone.utc).isoformat()})

    def read(self, key: str) -> str | None:
        return self._state.get(key)

    def snapshot(self) -> dict[str, str]:
        return dict(self._state)

    def history(self) -> list[dict]:
        return list(self._history)

    def __len__(self) -> int:
        return len(self._state)
