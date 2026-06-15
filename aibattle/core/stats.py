from dataclasses import dataclass, field
from typing import Optional
from core.board import PlayerColor
from core.game import GameRecord
import csv
import json
from datetime import datetime
from collections import defaultdict


@dataclass
class MatchStats:
    black_name: str
    white_name: str
    total_games: int = 0
    black_wins: int = 0
    white_wins: int = 0
    draws: int = 0
    black_total_time_ms: int = 0
    white_total_time_ms: int = 0
    black_total_moves: int = 0
    white_total_moves: int = 0
    game_records: list[GameRecord] = field(default_factory=list)

    def add_game(self, record: GameRecord, black_name: str, white_name: str):
        self.total_games += 1
        self.game_records.append(record)

        if record.winner == PlayerColor.BLACK:
            self.black_wins += 1
        elif record.winner == PlayerColor.WHITE:
            self.white_wins += 1
        else:
            self.draws += 1

        self.black_total_time_ms += record.total_time_ms.get(PlayerColor.BLACK, 0)
        self.white_total_time_ms += record.total_time_ms.get(PlayerColor.WHITE, 0)
        self.black_total_moves += sum(1 for m in record.moves if m.metadata.get("player") == PlayerColor.BLACK)
        self.white_total_moves += sum(1 for m in record.moves if m.metadata.get("player") == PlayerColor.WHITE)

    @property
    def black_win_rate(self) -> float:
        return self.black_wins / self.total_games if self.total_games > 0 else 0.0

    @property
    def white_win_rate(self) -> float:
        return self.white_wins / self.total_games if self.total_games > 0 else 0.0

    @property
    def draw_rate(self) -> float:
        return self.draws / self.total_games if self.total_games > 0 else 0.0

    @property
    def avg_game_length(self) -> float:
        if not self.game_records:
            return 0.0
        return sum(len(r.moves) for r in self.game_records) / len(self.game_records)

    @property
    def avg_black_time_per_move(self) -> float:
        return self.black_total_time_ms / self.black_total_moves if self.black_total_moves > 0 else 0.0

    @property
    def avg_white_time_per_move(self) -> float:
        return self.white_total_time_ms / self.white_total_moves if self.white_total_moves > 0 else 0.0

    def summary(self) -> str:
        return (
            f"=== Match Statistics ===\n"
            f"{self.black_name} (Black) vs {self.white_name} (White)\n"
            f"Total Games: {self.total_games}\n"
            f"Black Wins: {self.black_wins} ({self.black_win_rate:.1%})\n"
            f"White Wins: {self.white_wins} ({self.white_win_rate:.1%})\n"
            f"Draws: {self.draws} ({self.draw_rate:.1%})\n"
            f"Avg Game Length: {self.avg_game_length:.1f} moves\n"
            f"Avg Black Time/Move: {self.avg_black_time_per_move:.1f} ms\n"
            f"Avg White Time/Move: {self.avg_white_time_per_move:.1f} ms\n"
        )

    def export_csv(self, filepath: str):
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Game", "Winner", "Moves", "Black Time (ms)", "White Time (ms)", "Reason"])
            for i, record in enumerate(self.game_records, 1):
                winner = "Black" if record.winner == PlayerColor.BLACK else ("White" if record.winner == PlayerColor.WHITE else "Draw")
                writer.writerow([
                    i,
                    winner,
                    len(record.moves),
                    record.total_time_ms.get(PlayerColor.BLACK, 0),
                    record.total_time_ms.get(PlayerColor.WHITE, 0),
                    record.reason
                ])

    def export_json(self, filepath: str):
        data = {
            "black_name": self.black_name,
            "white_name": self.white_name,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_games": self.total_games,
                "black_wins": self.black_wins,
                "white_wins": self.white_wins,
                "draws": self.draws,
                "black_win_rate": self.black_win_rate,
                "white_win_rate": self.white_win_rate,
                "draw_rate": self.draw_rate,
                "avg_game_length": self.avg_game_length,
            },
            "games": [
                {
                    "game": i,
                    "winner": "Black" if r.winner == PlayerColor.BLACK else ("White" if r.winner == PlayerColor.WHITE else "Draw"),
                    "moves": len(r.moves),
                    "black_time_ms": r.total_time_ms.get(PlayerColor.BLACK, 0),
                    "white_time_ms": r.total_time_ms.get(PlayerColor.WHITE, 0),
                    "reason": r.reason,
                    "move_details": [
                        {
                            "move": j + 1,
                            "player": "Black" if m.metadata.get("player") == PlayerColor.BLACK else "White",
                            "position": str(m.position),
                            "time_ms": m.think_time_ms,
                        }
                        for j, m in enumerate(r.moves)
                    ]
                }
                for i, r in enumerate(self.game_records, 1)
            ]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)