"""一键配置本地大模型（Ollama）

本示例演示如何通过程序自动部署和配置本地模型：
1. 检查 Ollama 是否安装
2. 检测本地已下载的模型，避免重复下载
3. 选择并下载（或直接使用本地已有模型）
4. 自动注册为 opencode 的 AI 提供商

前置条件：已安装 Ollama（https://ollama.com/download）
"""

import json
import pathlib
import shutil
import subprocess


BASE_URL = "http://localhost:4096"
OPENCODE_CONFIG = pathlib.Path.home() / ".config" / "opencode" / "opencode.json"

# 候选模型库
CANDIDATE_MODELS = [
    {"key": "1", "name": "qwen2.5:7b", "size": "~4.7 GB", "desc": "阿里通义千问 7B, 中文好"},
    {"key": "2", "name": "qwen2.5:1.5b", "size": "~1.1 GB", "desc": "轻量版, 适合低配机器"},
    {"key": "3", "name": "llama3.2:3b", "size": "~2.0 GB", "desc": "Meta LLaMA 3.2, 英文好"},
    {"key": "4", "name": "llama3.2:1b", "size": "~0.7 GB", "desc": "超轻量, 最快响应"},
]


def get_local_models():
    """执行 ollama list 获取本地已有模型列表"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        lines = result.stdout.strip().split("\n")
        # 跳过表头行（NAME, ID, SIZE, MODIFIED）
        local = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                local.append(parts[0])
        return local
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def get_all_ollama_models():
    """通过 Ollama API 获取本地所有可用模型"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        models = []
        for line in result.stdout.strip().split("\n")[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def build_ollama_models_dict():
    """构建包含所有本地 Ollama 模型的字典"""
    models = get_all_ollama_models()
    if not models:
        return {}
    return {m: {"name": m} for m in models}


def write_opencode_config(model_name):
    """写入正确的 opencode 配置文件并设为默认模型，注册全部本地 Ollama 模型"""
    ollama_models = build_ollama_models_dict()
    if not ollama_models:
        ollama_models = {model_name: {"name": model_name}}

    ollama_cfg = {
        "ollama": {
            "npm": "@ai-sdk/openai-compatible",
            "name": "Ollama (local)",
            "options": {
                "baseURL": "http://localhost:11434/v1",
            },
            "models": ollama_models,
        },
    }

    if OPENCODE_CONFIG.exists():
        raw = OPENCODE_CONFIG.read_text(encoding="utf-8").strip()
        cfg = json.loads(raw) if raw else {}
    else:
        cfg = {}

    provider_map = cfg.setdefault("provider", {})
    if "ollama" in provider_map:
        print("  Ollama 提供商已存在，更新配置...")
    provider_map.update(ollama_cfg)

    # 设为默认模型（格式：providerId/modelId）
    cfg["model"] = f"ollama/{model_name}"
    print(f"  已将默认模型设为: {cfg['model']}")
    print(f"  已注册 {len(ollama_models)} 个本地模型")

    OPENCODE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    OPENCODE_CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  配置已写入: {OPENCODE_CONFIG}")


def run():
    print("=" * 50)
    print("【本地模型配置助手】")
    print("=" * 50)
    print()

    # ---------------------------------------------------------------
    # 第 1 步：检查 Ollama 是否安装
    # ---------------------------------------------------------------
    print("[1/4] 检查 Ollama 安装状态...")
    ollama_path = shutil.which("ollama")
    if ollama_path:
        print(f"  已找到 Ollama: {ollama_path}")
    else:
        print("  [提示] 未检测到 Ollama，请先从 https://ollama.com/download 安装。")
        print("     Windows 用户下载安装包后，重启终端即可使用。")
        print()
        proceed = input("  继续尝试执行命令（如果已安装但未在 PATH 中）? (y/n): ").strip().lower()
        if proceed != "y":
            print("  已取消。请安装 Ollama 后重试。")
            return
    print()

    # ---------------------------------------------------------------
    # 第 2 步：检测本地已有模型 + 选择模型
    # ---------------------------------------------------------------
    local_models = get_local_models()
    local_set = set(local_models)

    print("[2/4] 选择要使用的模型：")
    print()

    if local_models:
        print("  本地已有模型（直接使用，无需下载）：")
        for i, m in enumerate(local_models, 1):
            tag = " [已下载]" if m in local_set else ""
            print(f"    [{i}] {m}{tag}")
        print()
        print("  或从推荐列表下载新模型：")
    else:
        print("  本地暂无模型，将从推荐列表中选择：")
    print()

    for m in CANDIDATE_MODELS:
        status = " [已下载]" if m["name"] in local_set else ""
        print(f"    [{m['key']}] {m['name']} ({m['size']}) - {m['desc']}{status}")
    print()

    # 构建选项映射
    local_options = {str(i + 1): name for i, name in enumerate(local_models)}
    candidate_map = {m["key"]: m["name"] for m in CANDIDATE_MODELS}
    all_keys = list(local_options.keys()) + list(candidate_map.keys())

    choice = input(f"  请输入编号 (1-{len(all_keys)}, 默认 1): ").strip() or "1"

    if choice in local_options:
        model_name = local_options[choice]
        need_download = False
        print(f"  已选择本地模型: {model_name}")
    elif choice in candidate_map:
        model_name = candidate_map[choice]
        need_download = model_name not in local_set
        if need_download:
            print(f"  已选择: {model_name}（需要下载）")
        else:
            print(f"  已选择: {model_name}（已下载，跳过下载）")
    else:
        model_name = local_models[0] if local_models else CANDIDATE_MODELS[0]["name"]
        need_download = model_name not in local_set
        print(f"  无效输入，使用默认: {model_name}")
    print()

    # ---------------------------------------------------------------
    # 第 3 步：下载模型（仅在需要时）
    # ---------------------------------------------------------------
    if need_download:
        print("[3/4] 正在下载模型，首次下载会拉取镜像文件，请保持网络通畅...")
        print()
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=False,
            )
            if result.returncode != 0:
                print(f"  [失败] ollama pull 返回码: {result.returncode}")
                print("  请确认 Ollama 服务是否已启动（在终端运行 ollama serve）")
                return
        except FileNotFoundError:
            print("  [失败] 找不到 ollama 命令。请确认 Ollama 已安装并添加到 PATH。")
            return
        print(f"  模型 {model_name} 下载完成！")
    else:
        print(f"[3/4] 跳过下载（{model_name} 已在本地）")
    print()

    # ---------------------------------------------------------------
    # 第 4 步：注册到 opencode 配置
    # ---------------------------------------------------------------
    print("[4/4] 注册到 opencode 提供商列表...")
    write_opencode_config(model_name)
    print()

    # ---------------------------------------------------------------
    # 验证：配置文件格式
    # ---------------------------------------------------------------
    print("正在验证配置文件格式...")
    try:
        raw = OPENCODE_CONFIG.read_text(encoding="utf-8").strip()
        saved = json.loads(raw) if raw else {}
        saved_ollama = saved.get("provider", {}).get("ollama", {})
        if saved_ollama:
            print(f"  [OK] Ollama 配置已写入: {saved_ollama.get('name', '?')}")
            saved_models = list(saved_ollama.get("models", {}).keys())
            print(f"       模型: {saved_models[0] if saved_models else '?'}")
        else:
            print("  [提示] 配置写入可能有问题，请检查文件内容。")
    except Exception as e:
        print(f"  [提示] 配置文件验证失败: {e}")

    print()
    print("配置完成！opencode 配置文件中已添加 Ollama 提供商。")
    print()
    print("=" * 50)
    print("  重要：需要重启 opencode 服务才能加载新配置")
    print("=" * 50)
    print()
    print("  1. 停止当前 opencode 服务（按 Ctrl+C）")
    print("  2. 重新启动: opencode serve --port 4096")
    print("  3. 重启后运行 Demo 6 即可使用本地模型")
    print("  4. 步骤 4 已自动将 ollama 设为默认模型")
