"""获取 opencode 系统配置信息

本示例演示如何获取系统配置信息，
包括用户名、默认模型等基本设置。

前置条件：opencode 服务已启动
"""

from opencode_ai import Opencode


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    # ---------------------------------------------------------------
    # 获取系统配置信息
    # config.get() 返回当前 opencode 的完整配置，
    # 包含用户名、主题、快捷键绑定等。
    # ---------------------------------------------------------------
    print("=" * 50)
    print("【系统配置信息】")
    print("=" * 50)
    cfg = client.config.get()
    username = getattr(cfg, "username", "?")
    model = getattr(cfg, "model", "?")
    print(f"用户名: {username}")
    print(f"默认模型: {model}")
