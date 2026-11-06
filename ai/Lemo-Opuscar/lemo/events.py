from __future__ import annotations

from dataclasses import dataclass, field
from queue import Queue
from typing import Any


@dataclass
class Event:
    kind: str
    text: str = ""
    value: float | None = None
    data: dict[str, Any] = field(default_factory=dict)


def event_queue() -> "Queue[Event]":
    return Queue()
