import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Optional, Callable
from core.board import Board, Position, PlayerColor
from core.rules import Rules, GameResult
from core.player import Player, MoveInfo
from core.game import GameEngine, GameRecord
from core.stats import MatchStats
from gui.renderer import GomokuCanvas, InfoPanel, ReplayBar


class GameState:
    def __init__(self):
        self.running = False
        self.paused = False
        self.finished = False
        self.move_count = 0
        self.current_player: Optional[PlayerColor] = PlayerColor.BLACK
        self.game_result: Optional[tuple[Optional[PlayerColor], str]] = None
        self.speed = 3
        self.replay_mode = False
        self.match_mode = False
        self.current_match_game = 0
        self.total_match_games = 0
        self.last_move_pos: Optional[Position] = None
        self.match_remaining = 0
        self.winning_positions: list[Position] = []


class GuiRunner:
    def __init__(
        self,
        rules: Rules,
        black_player_factory: Callable[[PlayerColor], Player],
        white_player_factory: Callable[[PlayerColor], Player],
        board_size: int = 15,
        cell_size: int = 38,
    ):
        self.rules = rules
        self.board_size = board_size
        self.black_player_factory = black_player_factory
        self.white_player_factory = white_player_factory
        self.state = GameState()
        self.match_stats = MatchStats(black_name="", white_name="")
        self.record: Optional[GameRecord] = None
        self.replay_index = 0

        self.root = tk.Tk()
        self.root.title("AI Battle - Gomoku")
        self.root.configure(bg="#2a2a2a")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Panel.TFrame", background="#333")
        style.configure("Control.TFrame", background="#444")

        top_frame = tk.Frame(self.root, bg="#2a2a2a")
        top_frame.pack(fill="x", pady=(5, 0))

        control_frame = tk.Frame(self.root, bg="#444", height=40)
        control_frame.pack(fill="x", padx=5, pady=2)

        main_frame = tk.Frame(self.root, bg="#2a2a2a")
        main_frame.pack(fill="both", expand=True, padx=5, pady=2)

        board_pixel = (board_size - 1) * cell_size + 2 * 35
        self.canvas = GomokuCanvas(main_frame, board_size, cell_size, width=board_pixel, height=board_pixel)
        self.canvas.pack(side="left", padx=(0, 10))

        self.panel = InfoPanel(main_frame, width=260)
        self.panel.pack(side="left", fill="y", expand=True)

        self.replay_bar = ReplayBar(self.root)
        self.replay_bar.pack(fill="x", padx=5, pady=2)

        self._build_controls(control_frame)

        bottom_label = tk.Label(self.root, text="SPACE=Replay | ←→=Step | R=Reset Replay | ESC=Exit",
                                font=("Consolas", 9), fg="#888", bg="#2a2a2a")
        bottom_label.pack(fill="x", padx=10, pady=(0, 5))

        self.canvas.draw_board()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Key>", self._on_key)
        self._engine: Optional[GameEngine] = None

    def _build_controls(self, parent: tk.Frame):
        buttons = [
            ("Start", self._on_start, 0),
            ("Pause", self._on_pause, 1),
            ("Step", self._on_step, 2),
            ("End", self._on_end, 3),
            ("Speed+", self._on_speed_up, 4),
            ("Speed-", self._on_speed_down, 5),
        ]
        for text, cmd, col in buttons:
            btn = tk.Button(parent, text=text, command=cmd, bg="#555", fg="white",
                            font=("Consolas", 10), padx=8, pady=2, bd=0)
            btn.pack(side="left", padx=3, pady=3)
            setattr(self, f"_btn_{text.lower().replace('+','p').replace('-','m')}", btn)

    def _on_start(self):
        self.state.paused = False

    def _on_pause(self):
        self.state.paused = not self.state.paused

    def _on_step(self):
        if self.state.replay_mode:
            self._replay_step(1)
        elif self._engine and self.state.running:
            self.state.paused = True
            self._engine.step()
            self._update_display()

    def _on_end(self):
        self.state.running = False
        if self._engine:
            self._engine.running = False

    def _on_speed_up(self):
        self.state.speed = min(10, self.state.speed + 1)

    def _on_speed_down(self):
        self.state.speed = max(1, self.state.speed - 1)

    def _on_key(self, event: tk.Event):
        key = event.keysym
        if key == "space" and self.state.finished:
            if self.state.match_mode and self.state.match_remaining > 0:
                self._next_match_game()
            else:
                self._enter_replay_mode()
        elif key == "Right":
            self._replay_step(1)
        elif key == "Left":
            self._replay_step(-1)
        elif key == "Up":
            self._replay_step(-10)
        elif key == "Down":
            self._replay_step(10)
        elif key == "r" and self.state.replay_mode:
            self.replay_index = 0
        elif key == "Escape":
            self._on_close()

    def _on_close(self):
        self.state.running = False
        if self._engine:
            self._engine.running = False
        if hasattr(self, "_after_id"):
            self.root.after_cancel(self._after_id)
        self.root.destroy()

    def _make_engine(self) -> GameEngine:
        black = self.black_player_factory(PlayerColor.BLACK)
        white = self.white_player_factory(PlayerColor.WHITE)
        self.match_stats.black_name = black.name
        self.match_stats.white_name = white.name

        def on_move(player: PlayerColor, move_info: MoveInfo, board: Board):
            self.state.move_count += 1
            self.state.current_player = player.opponent()
            self.state.last_move_pos = move_info.position

        def on_game_end(result: GameResult):
            self.state.finished = True
            self.state.current_player = None
            self.state.game_result = (result.winner, result.reason)
            if result.winner is not None and hasattr(self.rules, "find_winning_line") and self.state.last_move_pos:
                self.state.winning_positions = self.rules.find_winning_line(
                    self._engine.board, self.state.last_move_pos, result.winner
                )

        engine = GameEngine(self.rules, black, white, on_move=on_move, on_game_end=on_game_end)
        return engine

    def _update_display(self):
        if self._engine is None:
            return
        board = self._engine.board
        last_move = self.state.last_move_pos
        black_time = 0
        white_time = 0
        if hasattr(self._engine, "record") and self._engine.get_record().moves:
            rec = self._engine.get_record()
            black_time = rec.total_time_ms[PlayerColor.BLACK]
            white_time = rec.total_time_ms[PlayerColor.WHITE]

        self.canvas.draw_board()
        self.canvas.draw_stones(board, last_move)
        if self.state.winning_positions:
            self.canvas.draw_winning_line(self.state.winning_positions)
        self.panel.update_info(
            self.match_stats.black_name,
            self.match_stats.white_name,
            self.state.current_player,
            self.state.move_count,
            black_time,
            white_time,
            self.match_stats if self.state.match_mode and self.match_stats.total_games > 0 else None,
        )
        self.replay_bar.update(0, 0)
        self.root.update()

    def _replay_step(self, delta: int):
        if not self.record or not self.record.moves:
            return
        new_index = self.replay_index + delta
        self.replay_index = max(0, min(len(self.record.moves), new_index))
        self._update_replay_display()

    def _update_replay_display(self):
        if not self.record or not self.record.moves:
            return
        total = len(self.record.moves)
        idx = max(0, self.replay_index - 1) if self.replay_index > 0 else 0
        board = self.record.get_board_at_move(idx)
        if board is None and self.record.boards:
            board = self.record.boards[0]
        if board is None:
            return

        last_pos = None
        if self.replay_index > 0 and self.replay_index <= total:
            last_pos = self.record.moves[self.replay_index - 1].position

        black_time = 0
        white_time = 0
        for i in range(min(self.replay_index, total)):
            m = self.record.moves[i]
            if m.metadata.get("player") == PlayerColor.BLACK:
                black_time += m.think_time_ms
            else:
                white_time += m.think_time_ms

        curr_player = None
        if self.replay_index < total:
            curr_player = self.record.moves[self.replay_index].metadata.get("player")

        self.canvas.draw_board()
        self.canvas.draw_stones(board, last_pos)
        self.panel.update_info(
            self.match_stats.black_name,
            self.match_stats.white_name,
            curr_player,
            self.replay_index,
            black_time,
            white_time,
            self.match_stats if self.match_stats.total_games > 0 else None,
        )
        self.replay_bar.update(self.replay_index, total)

    def _enter_replay_mode(self):
        if not self.record or not self.record.moves:
            return
        self.state.replay_mode = True
        self.replay_index = 0
        self._update_replay_display()
        self._auto_replay()

    def _auto_replay(self):
        if not self.state.replay_mode or not self.record:
            return
        total = len(self.record.moves)
        move_delay = max(100, 800 - self.state.speed * 70)

        if self.replay_index < total:
            self._replay_step(1)
            self._after_id = self.root.after(move_delay, self._auto_replay)

    def _start_game(self, auto_start: bool = True):
        self._engine = self._make_engine()
        self.record = None
        self.state.move_count = 0
        self.state.finished = False
        self.state.current_player = PlayerColor.BLACK
        self.state.game_result = None
        self.state.last_move_pos = None
        self.state.paused = not auto_start
        self.state.running = True
        self.state.replay_mode = False
        self.state.winning_positions = []
        self.replay_index = 0

        self._engine.running = True
        self._game_loop()

    def _on_game_finished(self):
        if self._engine and self._engine.get_record() and self._engine.get_record().moves:
            self.record = self._engine.get_record()
            self.match_stats.add_game(self.record, self.match_stats.black_name, self.match_stats.white_name)

        self._update_display()
        if self.state.match_mode:
            self.state.match_remaining -= 1
            if self.state.match_remaining > 0 and self.state.running:
                return
        self.state.replay_mode = True
        self.root.after(2000, self._auto_replay)

    def _next_match_game(self):
        game_num = self.state.total_match_games - self.state.match_remaining
        self.state.current_match_game = game_num
        self._start_game(auto_start=True)

    def run_match(self, num_games: int):
        self.state.match_mode = True
        self.state.total_match_games = num_games
        self.state.match_remaining = num_games
        self.match_stats = MatchStats(
            black_name=self.black_player_factory(PlayerColor.BLACK).name,
            white_name=self.white_player_factory(PlayerColor.WHITE).name,
        )
        self._next_match_game()

    def _game_loop(self):
        if not self.state.running or not self._engine:
            return
        if not self.state.finished and not self.state.paused and self._engine.running:
            self.root.update_idletasks()
            self._engine.step()
            self._update_display()
        elif self.state.finished:
            self._update_display()
            self._on_game_finished()
            return

        delay = max(1, 200 - self.state.speed * 15) if not self.state.paused else 100
        self._after_id = self.root.after(delay, self._game_loop)

    def run(self, match_games: int = 0):
        self.state.running = True

        if match_games > 0:
            self.root.after(100, lambda: self.run_match(match_games))
        else:
            self.root.after(100, lambda: self._start_game(auto_start=False))

        self.root.mainloop()
        return self.match_stats if match_games > 0 else self.record