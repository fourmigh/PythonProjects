"""向会话发送消息

本示例演示如何向已有的会话发送一条文本消息。
opencode 会调用 AI 模型生成回复。

前置条件：已有会话 ID（可先运行 01_创建会话.py 获取）
"""

import time

from opencode_ai import Opencode, APITimeoutError
from opencode_ai.types.session_chat_params import TextPartInputParam


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    # ---------------------------------------------------------------
    # 第 1 步：准备会话 ID
    # 这里有两种方式获取会话 ID：
    #   a) 如果传入了参数，使用传入的会话 ID
    #   b) 否则创建一个新会话
    # ---------------------------------------------------------------
    import sys
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        print(f"使用指定的会话: {session_id}")
    else:
        print("未指定会话 ID，正在创建新会话...")
        session = client.session.create(extra_body={"title": "Chat Demo"})
        session_id = getattr(session, "id", str(session))
        print(f"已创建新会话: {session_id}")

    # ---------------------------------------------------------------
    # 第 2 步：构建消息内容
    # 使用 TextPartInputParam 构造文本消息。
    # type="text" 表示这是一个文本片段，
    # text 字段是实际的消息内容。
    # ---------------------------------------------------------------
    message = "用一句话解释什么是 Python"
    print(f"发送消息: \"{message}\"")
    parts = [TextPartInputParam(text=message, type="text")]

    # ---------------------------------------------------------------
    # 第 3 步：发送并等待回复
    # session.chat() 发送消息后会等待 AI 生成回复，
    # 然后返回 AssistantMessage 对象。
    #
    # 注意：
    #   - session.chat() 是同步阻塞的，会一直等到 AI 回复完毕
    #   - 本地模型（如 Ollama）首次加载可能耗时较长
    #   - 设置了 120 秒超时，超时后会抛出 APITimeoutError
    # ---------------------------------------------------------------
    print("正在等待 AI 回复...")
    print("  (使用服务端默认配置的 provider/model)")
    print("  (等待时间取决于 AI 模型速度，首次加载可能需要 10-60 秒)")
    print("  开始时间: ", time.strftime("%H:%M:%S"))

    try:
        reply = client.session.chat(
            session_id,
            parts=parts,
            model_id="default",
            provider_id="default",
            timeout=120,
        )
    except APITimeoutError:
        elapsed = time.strftime("%H:%M:%S")
        print(f"  超时时间: {elapsed}")
        print()
        print("=" * 50)
        print("  AI 回复超时（超过 120 秒）")
        print("=" * 50)
        print()
        print("可能的原因：")
        print("  1. 本地模型（Ollama）仍在加载中")
        print("  2. 模型响应较慢，可增加 timeout 参数")
        print("  3. 服务端配置的 provider 不可用")
        print()
        print("建议：")
        print("  - 等待几秒后重试（模型已缓存到内存，会更快）")
        print("  - 运行 run_all.py 后选 4 配置更轻量的本地模型")
        print("  - 检查 Ollama 状态: curl http://localhost:11434")
        return

    print(f"  完成时间: {time.strftime('%H:%M:%S')}")

    print()
    print("AI 回复完成！")
    d = reply.to_dict()
    info = d.get("info", {})
    rid = info.get("id") or d.get("id", "N/A")
    print(f"  回复 ID:     {rid}")
    print(f"  使用模型:    {info.get('providerID', '?')}/{info.get('modelID', '?')}")

    texts = []
    for part in d.get("parts", []):
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
            texts.append(part["text"])
    content = " | ".join(texts) if texts else "(无文本内容)"
    print(f"  回复内容:    {content[:200]}")

    print(f"  消耗:        ${info.get('cost', 0)} / {info.get('tokens', {}).get('input', 0)} in / {info.get('tokens', {}).get('output', 0)} out")

    err = info.get("error")
    if err:
        print(f"  错误:        [{err.get('name', '?')}] {str(err.get('data', {}))[:150]}")
    print(f"  耗时:        {info.get('time', {}).get('completed', 0) - info.get('time', {}).get('created', 0):.0f}ms")

    print()
    print("说明：")
    print("- session.chat() 是同步阻塞的，它会等待 AI 完整回复后才返回")
    print("- 使用 provider_id='default' / model_id='default' 让服务端按配置选择")
    print("- 回复内容通过 reply.to_dict()['parts'] 获取")
    print("- 元数据（cost/tokens/provider/model）在 reply.to_dict()['info'] 中")
