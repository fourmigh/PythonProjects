"""中止正在进行的 AI 请求

session.abort() 可以取消一个正在等待 AI 回复的会话请求。

注意：此 Demo 需要手动在另一个终端先发一条耗时较长的消息，
然后在此 Demo 中输入该会话 ID 进行中止。
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
        print("请先创建会话并在另一个终端运行:")
        print("  python run_all.py")
        print("  选择 Demo 6 并输入一个复杂问题让 AI 长时间思考")
        print()
        session_id = input("然后输入该会话 ID: ").strip()
        if not session_id:
            print("未输入会话 ID，退出。")
            return

    print(f"正在中止会话 {session_id} 的请求...")
    result = client.session.abort(session_id)
    d = result.to_dict() if hasattr(result, "to_dict") else {}
    print(f"  中止状态: {d.get('status', 'done')}")

    print()
    print("说明：")
    print("- session.abort() 取消当前正在进行的 AI 请求")
    print("- 适用于用户不想继续等待 AI 回复的场景")
    print("- 中止后会话仍然存在，可以继续发送新消息")