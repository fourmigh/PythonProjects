from typing import Optional
from core.board import Board, Position, PlayerColor
from core.rules import Rules, GameResult


class GomokuRules(Rules[PlayerColor]):
    def __init__(self, size: int = 15, win_length: int = 5):
        self.size = size
        self.win_length = win_length
        self.directions = [(1, 0), (0, 1), (1, 1), (1, -1)]

    def initial_board(self) -> Board[PlayerColor]:
        return Board[PlayerColor](self.size)

    def legal_moves(self, board: Board[PlayerColor], player: PlayerColor) -> list[Position]:
        return board.empty_positions()

    def candidate_moves(self, board: Board[PlayerColor], radius: int = 2, max_moves: int = 30) -> list[Position]:
        has_stones = False
        candidates = set()
        for r in range(self.size):
            for c in range(self.size):
                if board.get(Position(r, c)) is not None:
                    has_stones = True
                    for dr in range(-radius, radius + 1):
                        for dc in range(-radius, radius + 1):
                            nr, nc = r + dr, c + dc
                            pos = Position(nr, nc)
                            if board.in_bounds(pos) and board.get(pos) is None:
                                candidates.add((nr, nc))
                            if len(candidates) >= max_moves * 3:
                                break
                    if len(candidates) >= max_moves * 3:
                        break
            if len(candidates) >= max_moves * 3:
                break

        if not has_stones:
            center = self.size // 2
            return [Position(center, center)]

        result = [Position(r, c) for r, c in candidates]
        if len(result) > max_moves:
            import random
            random.shuffle(result)
            result = result[:max_moves]
        return result

    def find_winning_line(self, board: Board[PlayerColor], last_move: Position, player: PlayerColor) -> list[Position]:
        for dr, dc in self.directions:
            line = [last_move]
            for direction in [1, -1]:
                r, c = last_move.row + dr * direction, last_move.col + dc * direction
                while 0 <= r < self.size and 0 <= c < self.size and board.get(Position(r, c)) == player:
                    line.append(Position(r, c))
                    r += dr * direction
                    c += dc * direction
            if len(line) >= self.win_length:
                return line
        return []

    def make_move(self, board: Board[PlayerColor], player: PlayerColor, pos: Position) -> bool:
        return board.set(pos, player)

    def check_winner(self, board: Board[PlayerColor], last_move: Position, player: PlayerColor) -> Optional[PlayerColor]:
        for dr, dc in self.directions:
            count = 1
            for direction in [1, -1]:
                r, c = last_move.row + dr * direction, last_move.col + dc * direction
                while 0 <= r < self.size and 0 <= c < self.size and board.get(Position(r, c)) == player:
                    count += 1
                    r += dr * direction
                    c += dc * direction
            if count >= self.win_length:
                return player
        return None

    def is_draw(self, board: Board[PlayerColor]) -> bool:
        return board.is_full()

    def evaluate(self, board: Board[PlayerColor], player: PlayerColor) -> float:
        score = 0.0
        for dr, dc in self.directions:
            score += self._eval_lines(board, dr, dc, player)
        return score if player == PlayerColor.BLACK else -score

    def _eval_lines(self, board: Board[PlayerColor], dr: int, dc: int, player: PlayerColor) -> float:
        opponent = player.opponent()
        score = 0.0
        weights = {
            (4, 2): 10000, (4, 1): 1000, (4, 0): 100,
            (3, 2): 1000, (3, 1): 100, (3, 0): 10,
            (2, 2): 100, (2, 1): 10, (2, 0): 1,
            (1, 2): 10, (1, 1): 1,
        }

        if dr == 1 and dc == 0:
            starts = [(r, 0) for r in range(self.size)]
        elif dr == 0 and dc == 1:
            starts = [(0, c) for c in range(self.size)]
        elif dr == 1 and dc == 1:
            starts = [(r, 0) for r in range(self.size)] + [(0, c) for c in range(1, self.size)]
        else:
            starts = [(r, self.size - 1) for r in range(self.size)] + [(0, c) for c in range(self.size - 2, -1, -1)]

        for start_r, start_c in starts:
            cells = []
            r, c = start_r, start_c
            while 0 <= r < self.size and 0 <= c < self.size:
                cells.append(board.get(Position(r, c)))
                r += dr
                c += dc

            if len(cells) < self.win_length:
                continue

            i = 0
            while i < len(cells):
                if cells[i] is None:
                    i += 1
                    continue
                if cells[i] != player and cells[i] != opponent:
                    i += 1
                    continue

                cur_player = cells[i]
                end = i + 1
                while end < len(cells) and cells[end] == cur_player:
                    end += 1

                count = end - i
                open_ends = 0
                if i > 0 and cells[i - 1] is None:
                    open_ends += 1
                if end < len(cells) and cells[end] is None:
                    open_ends += 1

                if count >= self.win_length:
                    return 100000 if cur_player == player else -100000

                weight = weights.get((count, open_ends), 0)
                score += weight if cur_player == player else -weight
                i = end

        return score


class GomokuBoard(Board[PlayerColor]):
    pass