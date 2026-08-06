"""总结会话内容

session.summarize() 使用 AI 对指定会话生成摘要。

前置条件：已有会话 ID 且包含消息
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
        session = client.session.create(extra_body={"title": "Summarize Demo"})
        session_id = session.id
        print(f"已创建新会话: {session_id}")

        client.session.chat(
            session_id,
            parts=[{"type": "text", "text": "Python 和 JavaScript 的主要区别是什么？"}],
            provider_id="default",
            model_id="default",
        )

    print("正在生成会话摘要...")
    result = client.session.summarize(
        session_id,
        provider_id="default",
        model_id="default",
    )

    d = result.to_dict() if hasattr(result, "to_dict") else {}
    print(f"  摘要生成完成")
    print(f"  详情: {d}")

    print()
    print("说明：")
    print("- session.summarize() 使用 AI 生成会话摘要")
    print("- 需要指定 provider_id 和 model_id 进行摘要生成")
    print("- 适用于长会话的快速回顾")