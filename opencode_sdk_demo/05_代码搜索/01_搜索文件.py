"""搜索项目文件

find.files() 按文件名模式搜索项目中的文件，
支持 glob 通配符模式。
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    pattern = input("请输入文件搜索模式（默认为 *.py）: ").strip()
    if not pattern:
        pattern = "*.py"
        print(f"  使用默认模式: {pattern}")

    result = client.find.files(pattern=pattern)
    d = result.to_dict() if hasattr(result, "to_dict") else {}
    files = d.get("files", [])
    print(f"  找到 {len(files)} 个匹配文件")
    print()

    for f in files[:30]:
        fpath = f.get("path", "?") if isinstance(f, dict) else str(f)
        print(f"  {fpath}")
    if len(files) > 30:
        print(f"  ... 共 {len(files)} 个文件")

    print()
    print("说明：")
    print("- find.files() 支持 glob 模式匹配文件名")
    print("- 模式示例：*.py, **/*.ts, src/**/*.css")
    print("- 搜索范围是 opencode 服务的工作目录")