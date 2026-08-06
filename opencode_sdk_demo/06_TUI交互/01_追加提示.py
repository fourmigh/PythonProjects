"""向 TUI 追加提示内容

tui.append_prompt() 可以向 opencode 的终端界面（TUI）的
输入框中追加文本，实现编程式输入。
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    prompt = input("请输入要追加到 TUI 的文本: ").strip()
    if not prompt:
        prompt = "请解释这个项目的结构"
        print(f"  使用默认文本: {prompt}")

    print(f"正在向 TUI 追加提示...")
    result = client.tui.append_prompt(prompt=prompt)

    print(f"  追加完成！文本已写入 TUI 输入框")
    print()
    print("说明：")
    print("- tui.append_prompt() 向 TUI 输入框追加文本")
    print("- 适用于从外部程序向 opencode TUI 发送指令")
    print("- 不会自动发送，需要用户在 TUI 中按回车执行")