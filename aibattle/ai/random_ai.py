import random
from typing import Generic, TypeVar
from core.player import Player, MoveInfo
from core.board import Board, Position, PlayerColor
from core.rules import Rules


T = TypeVar("T")


class RandomAI(Player[T]):
    def __init__(self, color: PlayerColor, name: str = "", seed: int | None = None):
        super().__init__(color, name or f"RandomAI-{color.name}")
        self._rng = random.Random(seed)

    def choose_move(self, board: Board[T], rules: Rules[T]) -> MoveInfo:
        legal_moves = rules.legal_moves(board, self.color)
        if not legal_moves:
            return MoveInfo(position=Position(0, 0), think_time_ms=0, metadata={"player": self.color, "error": "no legal moves"})
        pos = self._rng.choice(legal_moves)
        return MoveInfo(position=pos, think_time_ms=0, metadata={"player": self.color})