from typing import Generic, TypeVar, Optional
from core.player import Player, MoveInfo
from core.board import Board, Position, PlayerColor
from core.rules import Rules
import time
import subprocess
import json
import http.client
import urllib.parse


T = TypeVar("T")


class LLMConfig:
    def __init__(
        self,
        provider: str = "openai",
        api_key: str = "",
        model: str = "gpt-4o",
        api_base: str = "",
        temperature: float = 0.7,
        timeout: int = 120,
        log_path: str = "",
    ):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.api_base = api_base or self._default_base()
        self.temperature = temperature
        self.timeout = timeout
        self.log_path = log_path or "llm_debug.log"

    def _default_base(self) -> str:
        bases = {
            "openai": "api.openai.com",
            "ollama": "localhost:11434",
            "claude": "api.anthropic.com",
        }
        return bases.get(self.provider, bases["openai"])


class LLMAI(Player[T]):
    def __init__(
        self,
        color: PlayerColor,
        name: str = "",
        config: Optional[LLMConfig] = None,
        system_prompt: str = "",
    ):
        super().__init__(color, name or f"LLM-{color.name}")
        self.config = config or LLMConfig()
        self.system_prompt = system_prompt
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def choose_move(self, board: Board[T], rules: Rules[T]) -> MoveInfo:
        if board.is_empty():
            center = board.size // 2
            return MoveInfo(position=Position(center, center), think_time_ms=0,
                            metadata={"player": self.color})
        return self._do_query(board, rules)

    def _do_query(self, board: Board[T], rules: Rules[T]) -> MoveInfo:
        start_time = time.perf_counter()

        prompt = self._build_prompt(board, rules)
        response_text = self._query_llm(prompt)

        pos = self._parse_move(response_text, rules, board)

        import re as _re
        _patterns = [
            r'[（(]?\s*([A-Z])\s*[,，]\s*(\d+)\s*[）)]?',
            r'[（(]?\s*([a-z])\s*[,，]\s*(\d+)\s*[）)]?',
            r'[（(]?\s*([A-Z])\s*(\d+)\s*[）)]?',
            r'[（(]?\s*([a-z])\s*(\d+)\s*[）)]?',
            r'[（(]?\s*(\d+)\s*[,，]\s*(\d+)\s*[）)]?',
        ]
        _matched = None
        for _pi, _pat in enumerate(_patterns):
            _ms = list(_re.finditer(_pat, response_text))
            if _ms:
                _matched = (_pi, _ms[-1].group(0))
        _match_str = f"pat#{_matched[0]}={_matched[1]}" if _matched else "no_match"

        raw_preview = response_text[-1500:]
        log_line = f"[{time.strftime('%H:%M:%S')}] {self.color.name} | {self.config.model} | m={_match_str} | pos=({pos.row},{pos.col}) | tail={raw_preview}" if pos else f"[{time.strftime('%H:%M:%S')}] {self.color.name} | {self.config.model} | m={_match_str} | FALLBACK | tail={raw_preview}"
        print(log_line)
        with open(self.config.log_path, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

        if pos is None:
            legal = rules.legal_moves(board, self.color)
            if legal:
                center = board.size // 2
                pos = min(legal, key=lambda p: abs(p.row - center) + abs(p.col - center))
            else:
                pos = Position(0, 0)

        think_time_ms = int((time.perf_counter() - start_time) * 1000)
        return MoveInfo(position=pos, think_time_ms=think_time_ms, metadata={
            "player": self.color,
            "raw_response": response_text[:200],
        })

    def _build_prompt(self, board: Board[T], rules: Rules[T]) -> str:
        prompt = self.system_prompt or self._default_prompt()
        prompt += f"\n\nYou are {self.color.name}. Board {board.size}x{board.size}.\n"
        prompt += "State (B=Black, W=White, .=empty) | columns A-O:\n"

        for r in range(board.size):
            row_str = f"{board.size - r:2d} "
            for c in range(board.size):
                stone = board.get(Position(r, c))
                if stone == PlayerColor.BLACK:
                    row_str += "B"
                elif stone == PlayerColor.WHITE:
                    row_str += "W"
                else:
                    row_str += "."
            prompt += row_str + "\n"

        prompt += "\nPut your move on the LAST LINE like (H, 8) or (H8)."
        return prompt

    def _default_prompt(self) -> str:
        return (
            "You are an expert Gomoku (Five in a Row) player.\n\n"
            "The goal is to place 5 of your stones in a row (horizontally, vertically, or diagonally) "
            "before your opponent does.\n\n"
            "Columns are labeled A (left) to O (right). Rows are numbered 15 (top) to 1 (bottom).\n"
            "Example: (H, 8) is the center. (A, 15) is the top-left corner. (O, 1) is the bottom-right corner.\n\n"
            "Put your chosen move coordinates on the LAST LINE of your reply, like (H, 8) or (H8)."
        )

    def _query_llm(self, prompt: str) -> str:
        if self.config.provider == "ollama":
            return self._query_ollama(prompt)
        elif self.config.provider == "openai":
            return self._query_openai(prompt)
        return ""

    def _query_ollama(self, prompt: str) -> str:
        try:
            conn = http.client.HTTPConnection(
                self.config.api_base if ":" in self.config.api_base else f"{self.config.api_base}:11434",
                timeout=self.config.timeout,
            )
            payload = json.dumps({
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "temperature": self.config.temperature,
            })
            conn.request("POST", "/api/generate", payload, {"Content-Type": "application/json"})
            resp = conn.getresponse()
            data = json.loads(resp.read())
            conn.close()
            return data.get("response", "")
        except Exception as e:
            return f"ERROR: {e}"

    def _query_openai(self, prompt: str) -> str:
        try:
            host = urllib.parse.urlparse(self.config.api_base).hostname or self.config.api_base
            conn = http.client.HTTPSConnection(host, timeout=self.config.timeout)
            payload = json.dumps({
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt or self._default_prompt()},
                    {"role": "user", "content": prompt},
                ],
                "temperature": self.config.temperature,
            })
            conn.request("POST", "/v1/chat/completions", payload, {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            })
            resp = conn.getresponse()
            data = json.loads(resp.read())
            conn.close()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            self.total_prompt_tokens += usage.get("prompt_tokens", 0)
            self.total_completion_tokens += usage.get("completion_tokens", 0)
            return content
        except Exception as e:
            return f"ERROR: {e}"

    def _parse_move(self, response: str, rules: Rules[T], board: Board[T]) -> Optional[Position]:
        import re
        patterns = [
            r'[（(]?\s*([A-Z])\s*[,，]\s*(\d+)\s*[）)]?',
            r'[（(]?\s*([a-z])\s*[,，]\s*(\d+)\s*[）)]?',
            r'[（(]?\s*([A-Z])\s*(\d+)\s*[）)]?',
            r'[（(]?\s*([a-z])\s*(\d+)\s*[）)]?',
            r'[（(]?\s*(\d+)\s*[,，]\s*(\d+)\s*[）)]?',
        ]
        for pattern in patterns:
            matches = list(re.finditer(pattern, response))
            if not matches:
                continue
            match = matches[-1]
            try:
                g1, g2 = match.groups()
                if g1.isdigit() and g2.isdigit():
                    row, col = int(g1), int(g2)
                else:
                    col = ord(g1.upper()) - ord('A')
                    row = board.size - int(g2)
                pos = Position(row, col)
                if board.in_bounds(pos) and pos in rules.legal_moves(board, self.color):
                    return pos
            except (ValueError, IndexError):
                continue
        return None

