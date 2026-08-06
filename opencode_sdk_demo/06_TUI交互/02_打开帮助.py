"""打开 TUI 帮助页面

tui.open_help() 在 opencode 的终端界面（TUI）中
打开内置的帮助页面。
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    print("正在打开 TUI 帮助页面...")
    result = client.tui.open_help()

    print(f"  帮助页面已打开！")
    print()
    print("说明：")
    print("- tui.open_help() 在 TUI 中显示内置帮助")
    print("- 等同于在 TUI 中输入 /help 命令")
    print("- 适用于编程式引导用户查看帮助文档")