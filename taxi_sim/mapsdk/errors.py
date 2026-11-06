"""SDK 异常定义。"""


class ApiError(Exception):
    """SDK 调用失败(网络/参数/Key无效等)。"""


class InvalidKeyError(ApiError):
    """Key 无效或未开通对应服务, 该平台应被禁用。"""


class QuotaExceededError(ApiError):
    """当日配额已耗尽(QPS超限不算, 由上层重试)。"""


class RateLimitedError(ApiError):
    """QPS/请求频率超限, 可稍后重试。"""
