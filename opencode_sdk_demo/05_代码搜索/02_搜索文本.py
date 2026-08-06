"""搜索文件中的文本

find.text() 在项目文件中搜索指定的文本模式，
支持正则表达式搜索。
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    pattern = input("请输入要搜索的文本或正则表达式: ").strip()
    if not pattern:
        pattern = "def run"
        print(f"  使用默认模式: {pattern}")

    include = input("限制文件类型（如 *.py，留空不限）: ").strip()

    print(f"正在搜索: '{pattern}'")
    if include:
        print(f"  限定文件: {include}")

    result = client.find.text(pattern=pattern, include=include or None)
    d = result.to_dict() if hasattr(result, "to_dict") else {}
    matches = d.get("matches", d.get("files", []))
    print(f"  找到 {len(matches)} 个匹配")
    print()

    for m in matches[:15]:
        mdict = m if isinstance(m, dict) else {}
        fpath = mdict.get("path", mdict.get("file", str(m)[:60]))
        lines = mdict.get("lines", [])
        if isinstance(lines, list):
            for line in lines[:3]:
                ldict = line if isinstance(line, dict) else {}
                num = ldict.get("number", ldict.get("line", "?"))
                text = ldict.get("text", ldict.get("content", str(line)[:80]))
                print(f"  {fpath}:{num} | {text[:80]}")
        else:
            print(f"  {fpath}")

    if len(matches) > 15:
        print(f"  ... 共 {len(matches)} 个匹配")

    print()
    print("说明：")
    print("- find.text() 支持正则表达式搜索文件内容")
    print("- include 参数可限定文件类型")
    print("- 返回匹配位置（文件路径 + 行号）")