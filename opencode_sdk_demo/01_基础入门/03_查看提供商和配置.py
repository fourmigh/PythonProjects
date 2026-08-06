"""查看 AI 提供商和系统配置

本示例演示如何：
1. 查看当前配置的所有 AI 提供商（如 Anthropic、OpenAI 等）
2. 获取 opencode 的系统配置信息

前置条件：opencode 服务已启动
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    # ---------------------------------------------------------------
    # 获取所有 AI 提供商
    # app.providers() 返回提供商配置信息。
    # ---------------------------------------------------------------
    print("=" * 50)
    print("【AI 提供商 (Providers)】")
    print("=" * 50)
    providers = client.app.providers()
    print(f"提供商信息: {providers}")

    # ---------------------------------------------------------------
    # 获取系统配置
    # config.get() 返回 opencode 的完整配置。
    # ---------------------------------------------------------------
    print()
    print("=" * 50)
    print("【系统配置 (Config)】")
    print("=" * 50)
    cfg = client.config.get()
    print(f"配置信息: {cfg}")

    print()
    print("提示：用 print() 打印响应对象可以查看其所有内容。")
