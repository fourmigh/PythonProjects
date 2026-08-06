"""查看会话消息历史

session.messages() 返回一个会话的所有消息记录，
包括用户消息和 AI 回复。

前置条件：已有会话 ID（可先运行 01_创建会话.py 获取）
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    import sys
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
    else:
        print("未指定会话 ID，创建新会话并发送一条消息...")
        session = client.session.create(extra_body={"title": "Messages Demo"})
        session_id = session.id
        print(f"已创建新会话: {session_id}")
        client.session.chat(
            session_id,
            parts=[{"type": "text", "text": "用一句话介绍 Python"}],
            provider_id="default",
            model_id="default",
        )

    print("正在获取消息历史...")
    result = client.session.messages(session_id)

    msgs = result if isinstance(result, list) else list(result)
    print(f"共 {len(msgs)} 条消息")
    print()

    for i, msg in enumerate(msgs, 1):
        d = msg.to_dict() if hasattr(msg, "to_dict") else msg
        info = d.get("info", d)
        role = info.get("role", "?")
        parts = d.get("parts", [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"]
        preview = (texts[0][:80] + "...") if texts else "(无文本)"
        if role == "assistant":
            pid = info.get("providerID", "?")
            mid = info.get("modelID", "?")
            print(f"  [{i}] AI ({pid}/{mid}): {preview}")
        else:
            print(f"  [{i}] {role}: {preview}")

    print()
    print("说明：")
    print("- session.messages() 返回所有消息（用户 + AI 回复）")
    print("- 消息按时间正序排列")
    print("- AI 回复可通过 parts[].text 获取文本内容")