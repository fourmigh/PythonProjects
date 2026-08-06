"""分析应用并生成项目理解（AGENTS.md 原理演示）

session.init() 会分析当前项目的文件结构和代码特征，
自动生成 AGENTS.md 文件，帮助 AI 更好地理解项目。

注意：
- init 首次运行需要扫描项目 + 调用 AI 模型，耗时较长（2-5 分钟）
- 需要将使用的模型提前注册到 opencode 配置文件
- 实际应用场景：大项目接手时，用 init 让 AI 快速了解项目架构
"""

import sys
import time

from opencode_ai import Opencode, APITimeoutError

BASE_URL = "http://localhost:4096"


def run():
    import httpx

    client = Opencode(base_url=BASE_URL)

    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        print(f"使用指定的会话: {session_id}", flush=True)
    else:
        print("未指定会话 ID，正在创建新会话...", flush=True)
        session = client.session.create(extra_body={"title": "Init Demo"})
        session_id = session.id
        print(f"已创建新会话: {session_id}", flush=True)

    print(flush=True)
    print("--- session.init() ---", flush=True)
    print("功能: 分析项目结构并生成 AGENTS.md", flush=True)
    print("注意事项:", flush=True)
    print("  - 首次运行会扫描所有文件，耗时较长", flush=True)
    print("  - provider_id/model_id 需使用已注册的真实模型", flush=True)
    print("  - 请耐心等待（本地模型 2-5 分钟）", flush=True)
    print(flush=True)

    t0 = time.time()
    try:
        result = client.session.init(
            session_id,
            message_id=f"msg_init_{session_id[-8:]}",
            provider_id="ollama",
            model_id="qwen2.5:1.5b",
            timeout=360,
        )
        elapsed = time.time() - t0
        d = result.to_dict() if hasattr(result, "to_dict") else {}
        print(f"init 完成！耗时 {elapsed:.0f} 秒", flush=True)
        print(f"状态: {d.get('status', 'OK')}", flush=True)
    except APITimeoutError:
        elapsed = time.time() - t0
        print(f"init 超时（{elapsed:.0f}秒），模型响应太慢", flush=True)
        print("提示: 可换用更轻量的模型如 llama3.2:1b", flush=True)
        return
    except Exception as e:
        elapsed = time.time() - t0
        err_name = type(e).__name__
        print(f"init 失败（{err_name}, {elapsed:.0f}秒）: {e}", flush=True)
        print("提示: 确保模型已注册到 opencode 配置中", flush=True)
        return

    # 获取 init 生成的会话消息
    print(flush=True)
    print("--- init 生成的会话内容 ---", flush=True)
    msgs = httpx.get(f"{BASE_URL}/session/{session_id}/message", timeout=10).json()
    for m in msgs:
        info = m.get("info", m)
        role = info.get("role", "?")
        parts = m.get("parts", [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text" and p.get("text")]
        text = "".join(texts) if texts else ""
        if text:
            print(f"  [{role}]: {text[:300]}", flush=True)

    print(flush=True)
    print("说明:", flush=True)
    print("- session.init() 分析项目结构后尝试生成 AGENTS.md", flush=True)
    print("- message_id 必须以 'msg' 开头", flush=True)
    print("- 确保模型已注册到 opencode 配置的 provider.models 中", flush=True)
    print("- 首次分析较慢，后续 run_all.py 过程会缓存模型", flush=True)
