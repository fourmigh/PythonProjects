from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_REPO_DIR = APP_DIR / "repo"
DEFAULT_TOOLS_DIR = APP_DIR / "tools"


@dataclass
class AppConfig:
    repo_dir: str = str(DEFAULT_REPO_DIR)
    tools_dir: str = str(DEFAULT_TOOLS_DIR)
    opencode_exe: str = ""
    ffmpeg_dir: str = ""
    git_bash: str = ""
    uv_exe: str = ""
    model: str = ""
    default_voice: bool = True
    language: str = "中文"
    duration: int = 40
    aspect: str = "16:9"
    last_style: str = ""
    last_topic: str = ""

    def __post_init__(self) -> None:
        for name in (
            "repo_dir",
            "tools_dir",
            "opencode_exe",
            "ffmpeg_dir",
            "git_bash",
            "uv_exe",
            "model",
            "language",
            "aspect",
            "last_style",
            "last_topic",
        ):
            value = getattr(self, name)
            if not isinstance(value, str):
                setattr(self, name, str(value) if value is not None else "")
        try:
            self.duration = max(15, min(90, int(self.duration)))
        except (TypeError, ValueError):
            self.duration = 40
        if not isinstance(self.default_voice, bool):
            self.default_voice = str(self.default_voice).strip().lower() not in ("0", "false", "no", "off", "")

    @property
    def repo(self) -> Path:
        return Path(self.repo_dir)

    @property
    def tools(self) -> Path:
        return Path(self.tools_dir)

    @property
    def logs(self) -> Path:
        return APP_DIR / "logs"

    @property
    def data(self) -> Path:
        return APP_DIR / "data"

    @property
    def opencode(self) -> Path:
        if self.opencode_exe:
            return Path(self.opencode_exe)
        return self.tools / "opencode" / "opencode.exe"

    @property
    def app_dir(self) -> Path:
        return APP_DIR

    def ensure_dirs(self) -> None:
        for path in (self.repo, self.tools, self.logs, self.data):
            path.mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_PATH.exists():
            return cls()
        try:
            raw: Any = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in raw.items() if key in allowed})
