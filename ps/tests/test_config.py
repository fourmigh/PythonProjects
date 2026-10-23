from __future__ import annotations

import json

from psapp import config as config_module
from psapp.config import AppConfig, load_config, save_config


def test_load_config_ignores_secret_environment_variables(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setenv("SILICONFLOW_API_KEY", "secret")
    monkeypatch.setenv("ZHIPU_API_KEY", "secret2")
    config = load_config()
    assert config.api_key == ""
    assert config.zhipu_api_key == ""


def test_load_config_ignores_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    (tmp_path / ".env").write_text(
        "SILICONFLOW_API_KEY=secret\nZHIPU_API_KEY=secret2\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    config = load_config()
    assert config.api_key == ""
    assert config.zhipu_api_key == ""


def test_load_config_reads_non_secret_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setenv("SILICONFLOW_MODEL", "Qwen/Qwen-Image-Edit")
    monkeypatch.setenv("PS_PROXY", "http://127.0.0.1:7890")
    config = load_config()
    assert config.model == "Qwen/Qwen-Image-Edit"
    assert config.proxy == "http://127.0.0.1:7890"


def test_save_config_excludes_secrets(tmp_path, monkeypatch) -> None:
    path = tmp_path / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)
    config = AppConfig(api_key="secret", zhipu_api_key="secret2")
    save_config(config)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "api_key" not in data
    assert "zhipu_api_key" not in data
