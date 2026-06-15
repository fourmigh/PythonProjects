from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional
from core.board import Board, Position, PlayerColor


T = TypeVar("T")


@dataclass
class GameResult:
    winner: Optional[PlayerColor]
    is_draw: bool
    reason: str


class Rules(ABC, Generic[T]):
    @abstractmethod
    def initial_board(self) -> Board[T]:
        pass

    @abstractmethod
    def legal_moves(self, board: Board[T], player: PlayerColor) -> list[Position]:
        pass

    @abstractmethod
    def make_move(self, board: Board[T], player: PlayerColor, pos: Position) -> bool:
        pass

    @abstractmethod
    def check_winner(self, board: Board[T], last_move: Position, player: PlayerColor) -> Optional[PlayerColor]:
        pass

    @abstractmethod
    def is_draw(self, board: Board[T]) -> bool:
        pass

    @abstractmethod
    def evaluate(self, board: Board[T], player: PlayerColor) -> float:
        pass

    def get_result(self, board: Board[T], last_move: Optional[Position], current_player: PlayerColor) -> GameResult:
        if last_move is not None:
            winner = self.check_winner(board, last_move, current_player)
            if winner:
                return GameResult(winner=winner, is_draw=False, reason=f"{winner.name} wins")
        if self.is_draw(board):
            return GameResult(winner=None, is_draw=True, reason="Draw")
        return GameResult(winner=None, is_draw=False, reason="In progress")