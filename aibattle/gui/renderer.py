import tkinter as tk
from tkinter import ttk, font
from typing import Optional, Callable
from core.board import Board, Position, PlayerColor
from core.game import GameRecord
from core.stats import MatchStats


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
            self._labels["timers"].config(text=f"Time: {black_time_ms//1000}s / {white_time_ms//1000}s")

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


class WinnerOverlay:
    def __init__(self, parent: tk.Tk, winner: Optional[PlayerColor], reason: str, on_replay: Callable, on_exit: Callable):
        self.top = tk.Toplevel(parent)
        self.top.overrideredirect(True)
        self.top.attributes("-alpha", 0.85)
        self.top.configure(bg="black")

        w, h = parent.winfo_width(), parent.winfo_height()
        x, y = parent.winfo_rootx(), parent.winfo_rooty()
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(self.top, bg="#111", bd=2, relief="raised")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        win_text = f"{winner.name} WINS!" if winner else "DRAW"
        title_lbl = tk.Label(frame, text=win_text, font=("Microsoft YaHei", 24, "bold"),
                             fg="#FFD700", bg="#111")
        title_lbl.pack(padx=40, pady=(20, 5))

        if reason:
            reason_lbl = tk.Label(frame, text=reason, font=("Consolas", 12),
                                  fg="#aaa", bg="#111")
            reason_lbl.pack(padx=40, pady=(0, 15))

        btn_frame = tk.Frame(frame, bg="#111")
        btn_frame.pack(pady=(5, 20))

        replay_btn = tk.Button(btn_frame, text="Replay (SPACE)", font=("Consolas", 11),
                               command=lambda: [self.top.destroy(), on_replay()],
                               bg="#444", fg="white", padx=15, pady=5)
        replay_btn.pack(side="left", padx=5)

        exit_btn = tk.Button(btn_frame, text="Exit (ESC)", font=("Consolas", 11),
                             command=lambda: [self.top.destroy(), on_exit()],
                             bg="#444", fg="white", padx=15, pady=5)
        exit_btn.pack(side="left", padx=5)