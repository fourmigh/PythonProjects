GAME_REGISTRY = {
    "gomoku": {
        "name": "五子棋 (Gomoku)",
        "rules_module": "games.gomoku.rules",
        "rules_class": "GomokuRules",
        "board_size": 15,
    },
}


def import_rules(game_key: str):
    import importlib
    info = GAME_REGISTRY.get(game_key)
    if not info:
        raise ValueError(f"Unknown game: {game_key}")
    mod = importlib.import_module(info["rules_module"])
    cls = getattr(mod, info["rules_class"])
    return cls(info["board_size"]), info["board_size"]
