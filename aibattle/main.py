import argparse
import sys
import os
from typing import Optional
from core.board import PlayerColor
from core.player import Player
from core.game import GameEngine, GameRecord
from games.gomoku.rules import GomokuRules
from ai.random_ai import RandomAI
from ai.heuristic_ai import HeuristicAI


def resolve_player(name: str, color: PlayerColor, **kwargs) -> Player:
    name_lower = name.lower().strip()

    if name_lower == "random":
        seed = kwargs.get("seed")
        label = kwargs.get("label", "")
        return RandomAI(color, label, seed)

    if name_lower.startswith("heuristic"):
        parts = name_lower.split(":")
        depth = 2
        if len(parts) > 1:
            try:
                depth = int(parts[1])
            except ValueError:
                pass
        label = kwargs.get("label", "")
        return HeuristicAI(color, label, max_depth=depth)

    return HeuristicAI(color, f"HeuristicAI(d=2)-{color.name}", max_depth=2)


def run_headless(
    black_type: str,
    white_type: str,
    num_games: int,
    board_size: int = 15,
    max_moves: int = 10000,
    export_path: str = "",
) -> list[GameRecord]:
    from core.stats import MatchStats

    rules = GomokuRules(board_size)
    stats = MatchStats(
        black_name=resolve_player(black_type, PlayerColor.BLACK).name,
        white_name=resolve_player(white_type, PlayerColor.WHITE).name,
    )

    print(f"Running {num_games} game(s): {stats.black_name} (Black) vs {stats.white_name} (White)\n")

    for game_num in range(num_games):
        black = resolve_player(black_type, PlayerColor.BLACK)
        white = resolve_player(white_type, PlayerColor.WHITE)
        engine = GameEngine(rules, black, white)

        print(f"Game {game_num + 1}/{num_games}...", end=" ", flush=True)
        record = engine.run(max_moves)
        stats.add_game(record, black.name, white.name)
        winner = "Black" if record.winner == PlayerColor.BLACK else ("White" if record.winner == PlayerColor.WHITE else "Draw")
        print(f"{winner} ({len(record.moves)} moves)")

    print(f"\n{stats.summary()}")

    if export_path:
        if export_path.endswith(".csv"):
            stats.export_csv(export_path)
        elif export_path.endswith(".json"):
            stats.export_json(export_path)
        print(f"Results exported to {export_path}")

    return stats.game_records


def run_gui(
    black_type: str,
    white_type: str,
    match_games: int = 0,
    board_size: int = 15,
    cell_size: int = 38,
):
    from gui.runner import GuiRunner

    rules = GomokuRules(board_size)

    def black_factory(color: PlayerColor) -> Player:
        return resolve_player(black_type, color, label=resolve_player(black_type, color).name)

    def white_factory(color: PlayerColor) -> Player:
        return resolve_player(white_type, color, label=resolve_player(white_type, color).name)

    runner = GuiRunner(rules, black_factory, white_factory, board_size, cell_size)
    result = runner.run(match_games=match_games)

    if match_games > 0 and isinstance(result, object):
        print("Match complete!")
        if hasattr(result, "summary"):
            print(result.summary())


def main():
    parser = argparse.ArgumentParser(
        description="AI Battle - 让大模型对弈各种棋类",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # GUI模式：随机AI vs 启发式AI（深度2）
  python main.py random heuristic

  # GUI模式：启发式AI深度4 vs 随机AI
  python main.py heuristic:4 random

  # 无头模式：100局比赛，导出CSV
  python main.py --headless --games 100 --export results.csv random heuristic

  # GUI模式：10场比赛循环
  python main.py --match 10 heuristic random

  # 高级搜索 vs 随机
  python main.py heuristic:3 random
        """,
    )

    parser.add_argument("black", nargs="?", default="random", help="Black player type: random, heuristic[:depth]")
    parser.add_argument("white", nargs="?", default="heuristic:2", help="White player type: random, heuristic[:depth]")
    parser.add_argument("--headless", action="store_true", help="Run without GUI (headless mode)")
    parser.add_argument("--games", "-g", type=int, default=1, help="Number of games to play")
    parser.add_argument("--match", "-m", type=int, default=0, help="Match mode: play N games in GUI")
    parser.add_argument("--board-size", type=int, default=15, help="Board size (default: 15)")
    parser.add_argument("--export", type=str, default="", help="Export results to CSV or JSON file")
    parser.add_argument("--cell-size", type=int, default=38, help="GUI cell size in pixels (default: 38)")

    args = parser.parse_args()

    if args.headless or args.games > 1:
        run_headless(args.black, args.white, args.games, args.board_size, export_path=args.export)
    else:
        match_games = args.match or (args.games if args.games > 1 else 0)
        run_gui(args.black, args.white, match_games, args.board_size, args.cell_size)


if __name__ == "__main__":
    main()