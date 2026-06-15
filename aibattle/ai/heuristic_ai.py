from typing import Generic, TypeVar, Optional
from core.player import Player, MoveInfo
from core.board import Board, Position, PlayerColor
from core.rules import Rules
import time


T = TypeVar("T")


class HeuristicAI(Player[T]):
    def __init__(self, color: PlayerColor, name: str = "", max_depth: int = 2, time_limit_ms: int = 5000):
        super().__init__(color, name or f"HeuristicAI-{color.name}(d={max_depth})")
        self.max_depth = max_depth
        self.time_limit_ms = time_limit_ms
        self._start_time = 0.0

    def _get_candidates(self, board: Board[T], rules: Rules[T]) -> list[Position]:
        if hasattr(rules, "candidate_moves"):
            return rules.candidate_moves(board)
        return rules.legal_moves(board, self.color)

    def choose_move(self, board: Board[T], rules: Rules[T]) -> MoveInfo:
        self._start_time = time.perf_counter()
        candidates = self._get_candidates(board, rules)

        if not candidates:
            return MoveInfo(position=Position(0, 0), think_time_ms=0, metadata={"player": self.color, "error": "no moves"})

        if len(candidates) == 1:
            return MoveInfo(position=candidates[0], think_time_ms=0, metadata={"player": self.color})

        best_move = candidates[0]
        best_score = float("-inf")
        alpha = float("-inf")
        beta = float("inf")

        scored = []
        for move in candidates:
            if self._time_up():
                break
            board.set(move, self.color)
            score = rules.evaluate(board, self.color)
            board.remove(move)
            scored.append((score, move))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_moves = scored[:min(15, len(scored))]

        for score, move in top_moves:
            if self._time_up():
                break
            board.set(move, self.color)
            if self.max_depth > 1:
                score = -self._negamax(board, rules, self.max_depth - 1, -beta, -alpha, self.color.opponent())
            board.remove(move)

            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)

        think_time_ms = int((time.perf_counter() - self._start_time) * 1000)
        return MoveInfo(position=best_move, think_time_ms=think_time_ms, metadata={"player": self.color, "score": best_score})

    def _negamax(self, board: Board[T], rules: Rules[T], depth: int, alpha: float, beta: float, player: PlayerColor) -> float:
        if self._time_up():
            return rules.evaluate(board, self.color)

        result = rules.get_result(board, None, player)
        if result.winner is not None:
            return 100000 if result.winner == self.color else -100000
        if result.is_draw:
            return 0

        if depth == 0:
            return rules.evaluate(board, self.color)

        candidates = self._get_ordered_moves(board, rules, player)
        max_score = float("-inf")

        for move in candidates:
            board.set(move, player)
            score = -self._negamax(board, rules, depth - 1, -beta, -alpha, player.opponent())
            board.remove(move)

            max_score = max(max_score, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break

        return max_score

    def _get_ordered_moves(self, board: Board[T], rules: Rules[T], player: PlayerColor) -> list[Position]:
        candidates = self._get_candidates(board, rules)
        if len(candidates) <= 20:
            return candidates

        scored_moves = []
        for move in candidates:
            board.set(move, player)
            score = rules.evaluate(board, player)
            board.remove(move)
            scored_moves.append((score, move))

        scored_moves.sort(key=lambda x: x[0], reverse=True)
        return [move for _, move in scored_moves[:20]]

    def _time_up(self) -> bool:
        return (time.perf_counter() - self._start_time) * 1000 >= self.time_limit_ms