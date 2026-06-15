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
    ):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.api_base = api_base or self._default_base()
        self.temperature = temperature

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
        start_time = time.perf_counter()

        prompt = self._build_prompt(board, rules)
        response_text = self._query_llm(prompt)

        pos = self._parse_move(response_text, rules, board)

        coord = self._response_to_coord(response_text)
        if coord:
            pos = coord

        if pos is None:
            legal = rules.legal_moves(board, self.color)
            pos = legal[0] if legal else Position(0, 0)

        think_time_ms = int((time.perf_counter() - start_time) * 1000)
        return MoveInfo(position=pos, think_time_ms=think_time_ms, metadata={
            "player": self.color,
            "raw_response": response_text[:200],
        })

    def _build_prompt(self, board: Board[T], rules: Rules[T]) -> str:
        prompt = self.system_prompt or self._default_prompt()
        prompt += f"\n\nYou are {self.color.name}. The board is {board.size}x{board.size}.\n"
        prompt += f"Current board state (B={PlayerColor.BLACK.name[0]}, W={PlayerColor.WHITE.name[0]}, .=empty):\n"
        prompt += "Columns: " + " ".join(chr(ord('A') + c) if c < 26 else f"Z{c-25}" for c in range(board.size)) + "\n"

        for r in range(board.size):
            row_str = f"{board.size - r:2d} "
            for c in range(board.size):
                stone = board.get(Position(r, c))
                if stone == PlayerColor.BLACK:
                    row_str += "B "
                elif stone == PlayerColor.WHITE:
                    row_str += "W "
                else:
                    row_str += ". "
            prompt += row_str + "\n"

        prompt += "\nRespond with ONLY the coordinates where you want to place your stone, like: (row, col) or (letter, number). Example: (7, 7) or (H, 8)"
        return prompt

    def _default_prompt(self) -> str:
        return "You are an expert Gomoku (Five in a Row) player. Analyze the board and choose the best move."

    def _query_llm(self, prompt: str) -> str:
        if self.config.provider == "ollama":
            return self._query_ollama(prompt)
        elif self.config.provider == "openai":
            return self._query_openai(prompt)
        return ""

    def _query_ollama(self, prompt: str) -> str:
        try:
            conn = http.client.HTTPConnection(self.config.api_base if ":" in self.config.api_base else f"{self.config.api_base}:11434")
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
            conn = http.client.HTTPSConnection(host)
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
            r'\(?\s*(\d+)\s*[,，]\s*(\d+)\s*\)?',
            r'\(?\s*([A-Z])\s*[,，]\s*(\d+)\s*\)?',
            r'\(?\s*([a-z])\s*[,，]\s*(\d+)\s*\)?',
        ]
        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
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

    def _response_to_coord(self, response: str) -> Optional[Position]:
        import re
        match = re.search(r'\(?\s*(\d+)\s*[,，]\s*(\d+)\s*\)?', response)
        if match:
            try:
                row, col = int(match.group(1)), int(match.group(2))
                return Position(row, col)
            except (ValueError, IndexError):
                pass
        match = re.search(r'\(?\s*([A-Za-z])\s*[,，]?\s*(\d+)\s*\)?', response)
        if match:
            try:
                col = ord(match.group(1).upper()) - ord('A')
                row = int(match.group(2))
                return Position(row, col)
            except (ValueError, IndexError):
                pass
        return None