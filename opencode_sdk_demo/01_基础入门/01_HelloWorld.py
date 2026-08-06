"""Opencode SDK 入门第一课：Hello World

本示例演示了最基本的操作：
1. 导入 opencode SDK
2. 创建客户端连接
3. 调用一个 API 测试连通性

前置条件：opencode 服务已启动（默认监听 http://localhost:4096）
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    # ---------------------------------------------------------------
    # 第 1 步：创建客户端
    # Opencode() 会自动从环境变量 OPENCODE_BASE_URL 读取地址，
    # 也可以像下面这样手动传入 base_url 参数。
    # ---------------------------------------------------------------
    print("正在连接 opencode 服务...")
    client = Opencode(base_url=BASE_URL)
    print(f"客户端已创建，目标服务器: {BASE_URL}")

    # ---------------------------------------------------------------
    # 第 2 步：调用 API——列出当前所有会话
    # session.list() 不需要参数，返回当前 opencode 中的会话列表。
    # 如果 opencode 服务正常运行，这个调用就会成功返回。
    # ---------------------------------------------------------------
    print("正在获取会话列表（验证连通性）...")
    sessions = client.session.list()
    print(f"当前共有 {len(sessions)} 个会话")
    for i, s in enumerate(sessions, 1):
        print(f"  [{i}] {s.id}")

    print()
    print("恭喜！opencode SDK 已成功连接并正常工作。")
    print("你可以继续学习后续的 Demo 了。")
