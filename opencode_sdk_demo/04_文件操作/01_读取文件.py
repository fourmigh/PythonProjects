"""读取项目文件

file.read() 通过 opencode 服务读取工作区内的文件内容，
支持按行数和偏移量读取。
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    filepath = input("请输入要读取的文件路径（相对于项目根目录）: ").strip()
    if not filepath:
        filepath = "README.md"
        print(f"  使用默认文件: {filepath}")

    result = client.file.read(path=filepath)
    d = result.to_dict() if hasattr(result, "to_dict") else {}
    content = d.get("content", "")
    lines = content.split("\n")
    print(f"  文件: {filepath}")
    print(f"  行数: {len(lines)}")
    print(f"  大小: {len(content)} 字符")
    print()
    print("内容预览（前 15 行）:")
    print("-" * 40)
    for i, line in enumerate(lines[:15], 1):
        print(f"  {i:4d}| {line}")
    if len(lines) > 15:
        print(f"  ... 共 {len(lines)} 行")

    print()
    print("说明：")
    print("- file.read() 读取项目工作区内的文件")
    print("- 返回 FileReadResponse 对象，包含文件内容和元数据")
    print("- 路径相对于 opencode 服务的工作目录")