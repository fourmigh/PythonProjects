"""创建新会话

本示例演示如何创建一个新的 opencode 会话。
会话 (Session) 是 opencode 中一个对话的容器，
所有消息都在会话中组织和流转。
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    # ---------------------------------------------------------------
    # 创建会话
    # session.create() 不需要参数，返回一个 Session 对象。
    # Session 包含 id、title、time 等字段。
    # ---------------------------------------------------------------
    print("正在创建新会话...")
    session = client.session.create(extra_body={"title": "Demo Session"})
    print(f"会话创建成功！")
    sid = getattr(session, "id", str(session))
    print(f"  会话 ID:    {sid}")

    print()
    print("提示：每个会话都有一个唯一的 ID，后续操作（发消息、查历史）")
    print("都需要用到这个 ID。请留意保存。")
