from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional
from enum import Enum


class PlayerColor(Enum):
    BLACK = 1
    WHITE = 2

    def opponent(self) -> "PlayerColor":
        return PlayerColor.WHITE if self == PlayerColor.BLACK else PlayerColor.BLACK


@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def __str__(self) -> str:
        return f"({self.row}, {self.col})"


T = TypeVar("T")


class Board(ABC, Generic[T]):
    def __init__(self, size: int):
        self.size = size
        self._grid: list[list[Optional[T]]] = [[None for _ in range(size)] for _ in range(size)]

    def in_bounds(self, pos: Position) -> bool:
        return 0 <= pos.row < self.size and 0 <= pos.col < self.size

    def get(self, pos: Position) -> Optional[T]:
        if not self.in_bounds(pos):
            return None
        return self._grid[pos.row][pos.col]

    def set(self, pos: Position, value: T) -> bool:
        if not self.in_bounds(pos) or self._grid[pos.row][pos.col] is not None:
            return False
        self._grid[pos.row][pos.col] = value
        return True

    def remove(self, pos: Position) -> Optional[T]:
        if not self.in_bounds(pos):
            return None
        value = self._grid[pos.row][pos.col]
        self._grid[pos.row][pos.col] = None
        return value

    def empty_positions(self) -> list[Position]:
        return [Position(r, c) for r in range(self.size) for c in range(self.size) if self._grid[r][c] is None]

    def is_empty(self) -> bool:
        return all(self._grid[r][c] is None for r in range(self.size) for c in range(self.size))

    def is_full(self) -> bool:
        return all(self._grid[r][c] is not None for r in range(self.size) for c in range(self.size))

    def copy(self) -> "Board[T]":
        new_board = self.__class__(self.size)
        new_board._grid = [row[:] for row in self._grid]
        return new_board

    def __str__(self) -> str:
        lines = []
        for r in range(self.size):
            row_str = " ".join(str(self._grid[r][c]) if self._grid[r][c] is not None else "." for c in range(self.size))
            lines.append(f"{r:2d} {row_str}")
        header = "   " + " ".join(f"{c:1d}" for c in range(self.size))
        return header + "\n" + "\n".join(lines)