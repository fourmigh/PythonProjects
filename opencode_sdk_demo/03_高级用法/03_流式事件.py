"""处理流式事件

session.chat() 支持流式响应，实时获取 AI 生成的内容。
使用 with_streaming_response 可以逐块处理响应。
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    session = client.session.create(extra_body={"title": "Stream Demo"})
    print(f"会话: {session.id}")
    print()

    print("使用流式响应（with_streaming_response）:")
    print()

    with client.session.with_streaming_response.chat(
        session.id,
        parts=[{"type": "text", "text": "从 1 数到 5，用逗号分隔"}],
        provider_id="default",
        model_id="default",
    ) as response:
        print(f"  HTTP 状态: {response.status_code}")
        print(f"  响应类型: {response.headers.get('content-type', '?')}")
        print()
        print("  流式响应内容逐块输出:")
        for chunk in response.iter_bytes():
            text = chunk.decode("utf-8", errors="replace")
            print(f"    {text[:100]}", end="")
        print()

    print()
    print("说明：")
    print("- with_streaming_response 提供底层 HTTP 流式访问")
    print("- 适用于需要实时处理 AI 输出片段的场景")
    print("- 每次 yield 的数据块可能是 SSE 事件或原始字节")