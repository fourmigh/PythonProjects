"""分享和取消分享会话

session.share() 生成一个可分享的链接，
session.unshare() 取消分享。

前置条件：已有会话 ID
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
        print("未指定会话 ID，创建新会话...")
        session = client.session.create(extra_body={"title": "Share Demo"})
        session_id = session.id
        print(f"已创建新会话: {session_id}")

    print("正在分享会话...")
    result = client.session.share(session_id)
    d = result.to_dict() if hasattr(result, "to_dict") else {}
    share_url = d.get("share", {}).get("url", "N/A")
    print(f"  分享链接: {share_url}")
    print()

    print("正在取消分享...")
    result2 = client.session.unshare(session_id)
    print("  已取消分享")

    print()
    print("说明：")
    print("- session.share() 生成分享链接，其他人可查看会话")
    print("- session.unshare() 使之前的分享链接失效")
    print("- 分享功能需要在 opencode 配置中启用")