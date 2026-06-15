from dataclasses import dataclass, field
from typing import Generic, TypeVar, Optional, Callable
from core.board import Board, Position, PlayerColor
from core.rules import Rules, GameResult
from core.player import Player, MoveInfo
import time
import copy


T = TypeVar("T")


@dataclass
class GameRecord:
    moves: list[MoveInfo] = field(default_factory=list)
    boards: list[Board] = field(default_factory=list)
    winner: Optional[PlayerColor] = None
    is_draw: bool = False
    reason: str = ""
    total_time_ms: dict = field(default_factory=lambda: {PlayerColor.BLACK: 0, PlayerColor.WHITE: 0})

    def add_move(self, move: MoveInfo, board: Board, player: PlayerColor):
        self.moves.append(move)
        self.boards.append(board.copy())
        self.total_time_ms[player] += move.think_time_ms

    def get_board_at_move(self, move_index: int) -> Optional[Board]:
        if 0 <= move_index < len(self.boards):
            return self.boards[move_index]
        return None

    def final_board(self) -> Optional[Board]:
        return self.boards[-1] if self.boards else None


class GameEngine(Generic[T]):
    def __init__(
        self,
        rules: Rules[T],
        black_player: Player[T],
        white_player: Player[T],
        on_move: Optional[Callable[[PlayerColor, MoveInfo, Board], None]] = None,
        on_game_end: Optional[Callable[[GameResult], None]] = None,
    ):
        self.rules = rules
        self.players = {PlayerColor.BLACK: black_player, PlayerColor.WHITE: white_player}
        self.on_move = on_move
        self.on_game_end = on_game_end
        self.record = GameRecord()
        self.current_player = PlayerColor.BLACK
        self.board = rules.initial_board()
        self.last_move: Optional[Position] = None
        self.running = False

    def step(self) -> bool:
        if not self.running:
            return False

        player = self.players[self.current_player]
        start_time = time.perf_counter()
        move_info = player.choose_move(self.board, self.rules)
        think_time_ms = int((time.perf_counter() - start_time) * 1000)
        move_info.think_time_ms = think_time_ms

        if not self.rules.make_move(self.board, self.current_player, move_info.position):
            move_info.metadata["invalid"] = True
            self.record.add_move(move_info, self.board, self.current_player)
            result = GameResult(
                winner=self.current_player.opponent(),
                is_draw=False,
                reason=f"Invalid move by {self.current_player.name}"
            )
            self._end_game(result)
            return False

        self.last_move = move_info.position
        self.record.add_move(move_info, self.board, self.current_player)

        if self.on_move:
            self.on_move(self.current_player, move_info, self.board)

        result = self.rules.get_result(self.board, self.last_move, self.current_player)
        if result.winner is not None or result.is_draw:
            self._end_game(result)
            return False

        self.current_player = self.current_player.opponent()
        return True

    def run(self, max_moves: int = 10000) -> GameRecord:
        self.running = True
        self.record = GameRecord()
        self.board = self.rules.initial_board()
        self.current_player = PlayerColor.BLACK
        self.last_move = None

        for _ in range(max_moves):
            if not self.step():
                break
        return self.record

    def _end_game(self, result: GameResult):
        self.running = False
        self.record.winner = result.winner
        self.record.is_draw = result.is_draw
        self.record.reason = result.reason
        if self.on_game_end:
            self.on_game_end(result)

    def get_record(self) -> GameRecord:
        return self.record