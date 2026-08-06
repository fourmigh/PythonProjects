"""SDK 错误处理

opencode-ai SDK 定义了多种异常类型，用于处理不同的错误场景。
"""

from opencode_ai import Opencode
from opencode_ai import (
    APIConnectionError,
    APITimeoutError,
    BadRequestError,
    AuthenticationError,
    InternalServerError,
)


BASE_URL = "http://localhost:4096"


def run():
    client = Opencode(base_url=BASE_URL)

    test_cases = [
        ("无效 URL", lambda: Opencode(base_url="http://localhost:1").app.get()),
        ("超时", lambda: Opencode(base_url=BASE_URL).app.get()),
        ("无效会话", lambda: client.session.delete("invalid-session-id")),
    ]

    for label, fn in test_cases:
        print(f"测试: {label}")
        try:
            fn()
            print(f"  [OK] 调用成功")
        except APIConnectionError as e:
            print(f"  [连接错误] {e}")
        except APITimeoutError as e:
            print(f"  [超时] {e}")
        except BadRequestError as e:
            print(f"  [请求错误] {e}")
        except AuthenticationError as e:
            print(f"  [认证错误] {e}")
        except InternalServerError as e:
            print(f"  [服务端错误] {e}")
        except Exception as e:
            print(f"  [其他错误] {type(e).__name__}: {e}")
        print()

    print("说明：")
    print("- SDK 定义了多种异常类型，可精准捕获")
    print("- 常见异常: APIConnectionError, APITimeoutError, BadRequestError")
    print("- AuthenticationError 在 API key 无效时抛出")
    print("- InternalServerError 在服务端异常时抛出")