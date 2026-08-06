"""查看文件变更状态

file.status() 返回当前工作区的文件变更状态，
类似于 git status 但通过 opencode 的文件系统快照实现。
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    print("正在获取文件状态...")
    result = client.file.status()

    d = result.to_dict() if hasattr(result, "to_dict") else {}
    files = d.get("files", [])
    print(f"  变更文件数: {len(files)}")
    print()

    for f in files[:20]:
        fpath = f.get("path", "?")
        fstatus = f.get("status", "?")
        print(f"  [{fstatus}] {fpath}")
    if len(files) > 20:
        print(f"  ... 共 {len(files)} 个文件")

    print()
    print("说明：")
    print("- file.status() 展示工作区内的文件变更状态")
    print("- status 可能的值：created, modified, deleted, unchanged")
    print("- 基于 opencode 的文件系统快照机制")