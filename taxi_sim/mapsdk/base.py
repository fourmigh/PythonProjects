"""MapProvider 抽象基类: 统一三家平台的路径规划与 Key 测试接口。"""
import threading
import time
from abc import ABC, abstractmethod

import requests

from .errors import ApiError

HTTP_TIMEOUT = 10


class MapProvider(ABC):
    name = ""
    display_name = ""

    def __init__(self, min_interval=0.3):
        self._lock = threading.Lock()
        self._last_call = 0.0
        self._min_interval = min_interval
        self._session = requests.Session()

    def _throttle(self):
        with self._lock:
            wait = self._min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

    def _get(self, url, params):
        self._throttle()
        try:
            resp = self._session.get(url, params=params, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise ApiError(f"{self.display_name} 网络错误: {e}") from e
        except ValueError as e:
            raise ApiError(f"{self.display_name} 响应解析失败") from e

    @abstractmethod
    def test_key(self):
        """用最廉价接口验证 Key。返回 (ok: bool, message: str)。"""

    @abstractmethod
    def route_driving(self, o_lat, o_lng, d_lat, d_lng):
        """驾车路径规划。
        返回 dict(points=[(lat,lng)...]统一GCJ-02, distance=米, duration=秒)。
        配额超限抛 QuotaExceededError, Key无效抛 InvalidKeyError。
        """

    @property
    @abstractmethod
    def js_ready(self):
        """地图展示层是否可用(JS Key 是否配置)。"""

    @property
    @abstractmethod
    def api_ready(self):
        """路径规划层是否可用(Web Key 是否配置)。"""
