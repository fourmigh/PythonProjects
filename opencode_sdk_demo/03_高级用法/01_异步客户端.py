"""使用异步客户端

Opencode 支持同步和异步两种客户端。
异步客户端 AsyncOpencode 适用于异步编程场景。
"""

import asyncio
from opencode_ai import AsyncOpencode


BASE_URL = "http://localhost:4096"


async def run():
    client = AsyncOpencode(base_url=BASE_URL)

    print("正在使用异步客户端...")

    info_task = asyncio.create_task(client.app.get())
    config_task = asyncio.create_task(client.config.get())

    info = await info_task
    config = await config_task

    info_str = getattr(info, "version", str(info)[:60])
    print(f"  服务版本: {info_str}")
    print(f"  已加载配置: {bool(config)}")

    session = await client.session.create(extra_body={"title": "Async Demo"})
    print(f"  异步创建会话: {session.id}")

    reply = await client.session.chat(
        session.id,
        parts=[{"type": "text", "text": "Hi"}],
        provider_id="default",
        model_id="default",
    )
    print(f"  异步发送消息完成")
    print()
    print("说明：")
    print("- AsyncOpencode 是所有 SDK API 的异步版本")
    print("- 所有方法都返回 awaitable 对象")
    print("- 支持 asyncio.gather() 等并发操作")