from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional
import time
from core.board import Board, Position, PlayerColor
from core.rules import Rules


T = TypeVar("T")


@dataclass
class MoveInfo:
    position: Position
    think_time_ms: int
    metadata: dict


class Player(ABC, Generic[T]):
    def __init__(self, color: PlayerColor, name: str = ""):
        self.color = color
        self.name = name or f"{color.name} Player"

    @abstractmethod
    def choose_move(self, board: Board[T], rules: Rules[T]) -> MoveInfo:
        pass

    def __str__(self) -> str:
        return f"{self.name} ({self.color.name})"