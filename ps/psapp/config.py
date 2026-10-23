from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "Qwen/Qwen-Image-Edit-2509"
DEFAULT_ZHIPU_MODEL = "glm-4-flash-250414"
DEFAULT_ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

SECRET_KEYS = ("api_key", "zhipu_api_key")


@dataclass
class AppConfig:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    zhipu_api_key: str = ""
    zhipu_model: str = DEFAULT_ZHIPU_MODEL
    zhipu_url: str = DEFAULT_ZHIPU_URL
    rewrite_enabled: bool = True
    candidates: int = 2
    steps: int = 30
    cfg: float = 4.0
    seed: int | None = None
    feather: int = 6
    paste_back: bool = True
    max_edge: int = 1536
    timeout: int = 180
    output_dir: str = ""
    proxy: str = ""
    total_cost: float = 0.0

    def __post_init__(self) -> None:
        if not self.output_dir:
            self.output_dir = str(APP_DIR / "outputs")

    @property
    def provider_ready(self) -> bool:
        return bool(self.api_key.strip())

    @property
    def rewrite_ready(self) -> bool:
        return self.rewrite_enabled and bool(self.zhipu_api_key.strip())


def load_config() -> AppConfig:
    config = AppConfig()
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            for key, value in data.items():
                if hasattr(config, key) and key not in SECRET_KEYS:
                    setattr(config, key, value)
        except (json.JSONDecodeError, OSError):
            pass

    for key, env_name in (
        ("base_url", "SILICONFLOW_BASE_URL"),
        ("model", "SILICONFLOW_MODEL"),
        ("zhipu_model", "ZHIPU_MODEL"),
        ("proxy", "PS_PROXY"),
    ):
        value = os.environ.get(env_name)
        if value:
            setattr(config, key, value)

    return config


def save_config(config: AppConfig) -> None:
    data = asdict(config)
    for key in SECRET_KEYS:
        data.pop(key, None)
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
