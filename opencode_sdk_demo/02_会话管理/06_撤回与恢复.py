"""撤回和恢复消息

session.revert() 可以撤回（回滚）某条消息及其之后的回复，
session.unrevert() 可以恢复被撤回的消息。

前置条件：已有会话 ID 且包含至少一条 AI 回复
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    import sys
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        print(f"使用指定的会话: {session_id}")
    else:
        print("未指定会话 ID，创建新会话并发送消息...")
        session = client.session.create(extra_body={"title": "Revert Demo"})
        session_id = session.id
        print(f"已创建新会话: {session_id}")

        client.session.chat(
            session_id,
            parts=[{"type": "text", "text": "用一句话介绍 Python"}],
            provider_id="default",
            model_id="default",
        )

    msgs = client.session.messages(session_id)
    assistant_msgs = []
    for m in msgs:
        d = m.to_dict() if hasattr(m, "to_dict") else m
        info = d.get("info", d)
        if info.get("role") == "assistant":
            assistant_msgs.append(info.get("id", ""))

    if not assistant_msgs:
        print("会话中没有 AI 回复，无法演示撤回。")
        print("请先发送一条消息。")
        return

    target_id = assistant_msgs[-1]
    print(f"正在撤回消息: {target_id}")
    result = client.session.revert(session_id, message_id=target_id)
    print(f"  撤回成功，当前版本: {getattr(result, 'version', '?')}")

    print("正在恢复撤回的消息...")
    result2 = client.session.unrevert(session_id)
    print(f"  恢复成功，当前版本: {getattr(result2, 'version', '?')}")

    print()
    print("说明：")
    print("- session.revert(msg_id) 撤回指定消息及其后续消息")
    print("- session.unrevert() 恢复最近一次撤回操作")
    print("- revert 会返回更新后的 Session 对象")
    print("- message_id 是 AI 回复的 ID，可从 messages() 获取")