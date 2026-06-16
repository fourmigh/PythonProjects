import tkinter as tk
from tkinter import ttk, font
from typing import Optional, Callable
import urllib.request
import json
from core.board import Board, Position, PlayerColor
from core.game import GameRecord
from core.stats import MatchStats
from games import GAME_REGISTRY


_OLLAMA_CACHE = None

def _fetch_ollama_models():
    global _OLLAMA_CACHE
    if _OLLAMA_CACHE is not None:
        return _OLLAMA_CACHE
    try:
        resp = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        data = json.loads(resp.read())
        _OLLAMA_CACHE = sorted(f"ollama:{m['name']}" for m in data.get("models", []))
    except Exception:
        _OLLAMA_CACHE = []
    return _OLLAMA_CACHE


class GomokuCanvas(tk.Canvas):
    def __init__(self, master, board_size: int = 15, cell_size: int = 38, width=None, height=None, **kwargs):
        self.board_size = board_size
        self.cell_size = cell_size
        self.margin = 35
        board_pixel = (board_size - 1) * cell_size
        canvas_size = board_pixel + 2 * self.margin
        super().__init__(master, width=canvas_size, height=canvas_size, bg="#DEB887", highlightthickness=0, **kwargs)
        self.stone_radius = cell_size // 2 - 4
        self._last_move_marker: Optional[int] = None

    def draw_board(self):
        self.delete("all")
        ox, oy = self.margin, self.margin
        board_pixel = (self.board_size - 1) * self.cell_size

        for i in range(self.board_size):
            x = ox + i * self.cell_size
            self.create_line(x, oy, x, oy + board_pixel, fill="#333", width=1)
            y = oy + i * self.cell_size
            self.create_line(ox, y, ox + board_pixel, y, fill="#333", width=1)

        for r in range(self.board_size):
            label = str(self.board_size - r)
            x = ox - 18
            y = oy + r * self.cell_size - 6
            self.create_text(x, y, text=label, fill="#555", font=("Consolas", 9))
            label2 = chr(ord('A') + r) if r < 26 else f"Z{r-25}"
            x2 = ox + r * self.cell_size - 4
            y2 = oy + board_pixel + 10
            self.create_text(x2, y2, text=label2, fill="#555", font=("Consolas", 9))

        if self.board_size % 2 == 1:
            center = self.board_size // 2
            cx, cy = ox + center * self.cell_size, oy + center * self.cell_size
            self.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#333", outline="")
            for sr, sc in [(3, 3), (3, self.board_size - 4), (self.board_size - 4, 3), (self.board_size - 4, self.board_size - 4)]:
                if self.board_size > 8:
                    sx, sy = ox + sc * self.cell_size, oy + sr * self.cell_size
                    self.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, fill="#333", outline="")

    def draw_stones(self, board: Board[PlayerColor], last_move_pos: Optional[Position] = None):
        self._last_move_marker = None
        for r in range(self.board_size):
            for c in range(self.board_size):
                pos = Position(r, c)
                stone = board.get(pos)
                if stone is None:
                    continue
                x = self.margin + c * self.cell_size
                y = self.margin + r * self.cell_size
                is_last = last_move_pos is not None and pos == last_move_pos
                self._draw_stone(x, y, stone, is_last)

    def _draw_stone(self, x: int, y: int, color: PlayerColor, is_last: bool = False):
        r = self.stone_radius
        if color == PlayerColor.BLACK:
            self.create_oval(x - r, y - r, x + r, y + r, fill="#1a1a1a", outline="#000", width=1)
            self.create_oval(x - r + 3, y - r + 3, x + r - 3, y + r - 3, fill="#333", outline="")
        else:
            self.create_oval(x - r, y - r, x + r, y + r, fill="#f0f0f0", outline="#aaa", width=1)
            self.create_oval(x - r + 3, y - r + 3, x + r - 3, y + r - 3, fill="#fff", outline="")

        if is_last:
            marker_size = 4
            self._last_move_marker = self.create_oval(
                x - marker_size, y - marker_size, x + marker_size, y + marker_size,
                fill="#FF3333", outline=""
            )

    def draw_winning_line(self, positions: list[Position]):
        if not positions:
            return
        for pos in positions:
            x = self.margin + pos.col * self.cell_size
            y = self.margin + pos.row * self.cell_size
            self.create_oval(x - self.stone_radius - 2, y - self.stone_radius - 2,
                             x + self.stone_radius + 2, y + self.stone_radius + 2,
                             outline="#00CC00", width=3, tags="winning")

    def screen_to_board(self, sx: int, sy: int) -> Optional[Position]:
        col = round((sx - self.margin) / self.cell_size)
        row = round((sy - self.margin) / self.cell_size)
        if 0 <= row < self.board_size and 0 <= col < self.board_size:
            return Position(row, col)
        return None


class InfoPanel(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._labels = {}

        lines = [
            ("title", "AI Battle", 16, "bold"),
            ("game_info", "", 11, ""),
            ("", "", 5, ""),
            ("black_name", "", 10, ""),
            ("white_name", "", 10, ""),
            ("", "", 5, ""),
            ("turn", "", 12, "bold"),
            ("", "", 5, ""),
            ("timers", "", 10, ""),
            ("", "", 5, ""),
            ("match_title", "", 11, "bold"),
            ("match_info", "", 10, ""),
        ]

        for key, text, size, weight in lines:
            if key == "title":
                lbl = tk.Label(self, text=text, font=("Microsoft YaHei", size, weight), fg="#FFD700", bg="#333")
            elif key:
                lbl = tk.Label(self, text=text, font=("Consolas", size, weight), fg="#ddd", bg="#333", anchor="w", justify="left")
            else:
                lbl = tk.Label(self, text="", bg="#333")
            lbl.pack(fill="x", padx=10, pady=1)
            if key:
                self._labels[key] = lbl

        self.configure(style="Panel.TFrame")

    def update_info(self, black_name: str, white_name: str, current_player: Optional[PlayerColor],
                    move_count: int, black_time_ms: int, white_time_ms: int,
                    match_stats: Optional[MatchStats] = None):
        if "black_name" in self._labels:
            self._labels["black_name"].config(text=f"{chr(9679)} Blk: {black_name}")
        if "white_name" in self._labels:
            self._labels["white_name"].config(text=f"{chr(9675)} Wht: {white_name}")
        if "turn" in self._labels:
            if current_player:
                self._labels["turn"].config(text=f"Turn: {current_player.name}")
            else:
                self._labels["turn"].config(text="Game Over")
        if "game_info" in self._labels:
            self._labels["game_info"].config(text=f"Moves: {move_count}")
        if "timers" in self._labels:
            self._labels["timers"].config(text=f"Time: {black_time_ms}ms / {white_time_ms}ms")

        if match_stats and match_stats.total_games > 0:
            if "match_title" in self._labels:
                self._labels["match_title"].config(text=f"Match ({match_stats.total_games} games)")
            if "match_info" in self._labels:
                self._labels["match_info"].config(
                    text=(
                        f"Black: {match_stats.black_wins} ({match_stats.black_win_rate:.0%})\n"
                        f"White: {match_stats.white_wins} ({match_stats.white_win_rate:.0%})\n"
                        f"Draws: {match_stats.draws}\n"
                        f"Avg: {match_stats.avg_game_length:.0f} moves"
                    )
                )


    def hide_result(self):
        for attr in ("_result_sep", "_result_title", "_result_stat", "_result_btns", "_result_stat_extra"):
            w = getattr(self, attr, None)
            if w:
                w.destroy()
                setattr(self, attr, None)

    def hide_choice(self):
        for attr in ("_choice_sep", "_choice_game_label", "_choice_game",
                     "_choice_black_label", "_choice_black",
                     "_choice_white_label", "_choice_white", "_choice_btn"):
            w = getattr(self, attr, None)
            if w:
                w.destroy()
                setattr(self, attr, None)

    def show_choice(self, callback: Callable):
        self.hide_choice()
        self.hide_result()

        base_choices = ["random", "heuristic:1", "heuristic:2", "heuristic:3",
                        "openai:gpt-4o-mini", "openai:gpt-4o"]
        ollama_models = _fetch_ollama_models()
        AI_CHOICES = base_choices + ollama_models

        self._choice_sep = tk.Frame(self, bg="#555", height=1)
        self._choice_sep.pack(fill="x", padx=10, pady=(5, 3))

        game_names = [v["name"] for v in GAME_REGISTRY.values()]
        game_keys = list(GAME_REGISTRY.keys())

        self._choice_game_label = tk.Label(self, text="Game:", font=("Consolas", 9), fg="#ddd", bg="#333", anchor="w")
        self._choice_game_label.pack(fill="x", padx=10)
        self._choice_game = ttk.Combobox(self, values=game_names, state="readonly",
                                          font=("Consolas", 9), width=22)
        self._choice_game.set(game_names[0])
        self._choice_game.pack(fill="x", padx=10, pady=(0, 3))
        self._choice_game_keys = game_keys

        self._choice_black_label = tk.Label(self, text="Black AI:", font=("Consolas", 9), fg="#ddd", bg="#333", anchor="w")
        self._choice_black_label.pack(fill="x", padx=10)
        self._choice_black = ttk.Combobox(self, values=AI_CHOICES, state="readonly",
                                          font=("Consolas", 9), width=22)
        self._choice_black.set("heuristic:2")
        self._choice_black.pack(fill="x", padx=10, pady=(0, 3))

        self._choice_white_label = tk.Label(self, text="White AI:", font=("Consolas", 9), fg="#ddd", bg="#333", anchor="w")
        self._choice_white_label.pack(fill="x", padx=10)
        self._choice_white = ttk.Combobox(self, values=AI_CHOICES, state="readonly",
                                          font=("Consolas", 9), width=22)
        self._choice_white.set("random")
        self._choice_white.pack(fill="x", padx=10, pady=(0, 5))

        self._choice_btn = tk.Button(self, text="Start", font=("Consolas", 11, "bold"),
                                     command=lambda: self._choice_confirm(callback, game_keys),
                                     bg="#5a8", fg="white", padx=10, pady=3, bd=0)
        self._choice_btn.pack(padx=10, pady=(0, 8), fill="x")

    def _choice_confirm(self, callback: Callable, game_keys: list):
        name = self._choice_game.get()
        game_key = next(k for k, v in GAME_REGISTRY.items() if v["name"] == name)
        black_ai = self._choice_black.get()
        white_ai = self._choice_white.get()
        self.hide_choice()
        self.master.after_idle(callback, game_key, black_ai, white_ai)

    def show_result(self, winner: Optional[PlayerColor], reason: str, black_name: str, white_name: str,
                    move_count: int, black_time_ms: int, white_time_ms: int,
                    match_mode: bool, match_remaining: int,
                    on_restart: Callable, on_next: Callable, on_replay: Callable, on_exit: Callable):
        self.hide_result()

        self._result_sep = tk.Frame(self, bg="#555", height=1)
        self._result_sep.pack(fill="x", padx=10, pady=(5, 3))

        win_text = f"{winner.name} WINS!" if winner else "DRAW"
        fg_color = "#FFD700"
        self._result_title = tk.Label(self, text=win_text, font=("Microsoft YaHei", 14, "bold"),
                                      fg=fg_color, bg="#333")
        self._result_title.pack(fill="x", padx=10, pady=1)

        if reason:
            self._result_stat = tk.Label(self, text=reason, font=("Consolas", 9),
                                         fg="#aaa", bg="#333")
            self._result_stat.pack(fill="x", padx=10, pady=(0, 2))

        stat_text = (
            f"Black: {black_time_ms}ms  |  White: {white_time_ms}ms\n"
            f"Moves: {move_count}"
        )
        if self._result_stat is None or not reason:
            self._result_stat = tk.Label(self, text=stat_text, font=("Consolas", 9),
                                         fg="#ccc", bg="#333", justify="center")
            self._result_stat.pack(fill="x", padx=10, pady=(0, 2))
        else:
            extra = tk.Label(self, text=stat_text, font=("Consolas", 9),
                             fg="#ccc", bg="#333", justify="center")
            extra.pack(fill="x", padx=10, pady=(0, 2))
            self._result_stat_extra = extra

        self._result_btns = tk.Frame(self, bg="#333")
        self._result_btns.pack(fill="x", padx=10, pady=(3, 8))

        if match_mode and match_remaining > 0:
            pairs = [("Next Game", on_next), ("Replay", on_replay), ("Exit", on_exit)]
        elif match_mode and match_remaining == 0:
            pairs = [("Rematch", on_restart), ("Replay", on_replay), ("Exit", on_exit)]
        else:
            pairs = [("Restart", on_restart), ("Replay", on_replay), ("Exit", on_exit)]

        for text, cmd in pairs:
            btn = tk.Button(self._result_btns, text=text, font=("Consolas", 10),
                            command=cmd, bg="#555", fg="white", padx=10, pady=2, bd=0)
            btn.pack(side="left", padx=3)


class ReplayBar(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.current_move = 0
        self.total_moves = 0

        self.label = tk.Label(self, text="Move 0 / 0", font=("Consolas", 10), bg="#2a2a2a", fg="#ccc")
        self.label.pack(side="left", padx=5)

        self.progress = ttk.Progressbar(self, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(side="left", padx=5, fill="x", expand=True)

    def update(self, current: int, total: int):
        self.current_move = current
        self.total_moves = total
        self.label.config(text=f"Move {current} / {total}")
        if total > 0:
            self.progress["value"] = current / total * 100
        else:
            self.progress["value"] = 0





