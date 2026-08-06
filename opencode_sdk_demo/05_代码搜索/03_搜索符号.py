"""搜索代码符号

find.symbols() 搜索项目中的代码符号（函数、类、变量等），
基于语言服务器协议（LSP）的语义分析。
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    query = input("请输入要搜索的符号名称（如函数名、类名）: ").strip()
    if not query:
        query = "run"
        print(f"  使用默认查询: {query}")

    print(f"正在搜索符号: '{query}'")
    result = client.find.symbols(query=query)
    d = result.to_dict() if hasattr(result, "to_dict") else {}
    symbols = d.get("symbols", d.get("files", []))
    print(f"  找到 {len(symbols)} 个匹配符号")
    print()

    for sym in symbols[:20]:
        sdict = sym if isinstance(sym, dict) else {}
        name = sdict.get("name", sdict.get("symbol", "?"))
        kind = sdict.get("kind", sdict.get("type", "?"))
        fpath = sdict.get("file", sdict.get("path", "?"))
        line = sdict.get("line", sdict.get("location", "?"))
        print(f"  [{kind}] {name}")
        print(f"          {fpath}:{line}")

    if len(symbols) > 20:
        print(f"  ... 共 {len(symbols)} 个符号")

    print()
    print("说明：")
    print("- find.symbols() 基于 LSP 进行语义级代码搜索")
    print("- 支持搜索函数、类、方法、变量等符号")
    print("- 返回符号名称、类型和定义位置")