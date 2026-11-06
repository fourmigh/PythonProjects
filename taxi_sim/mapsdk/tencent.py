"""腾讯位置服务 Provider: WebService 驾车路线 v1。
坐标系 GCJ-02, from/to 参数为 "lat,lng"(纬度在前);
返回 polyline 为增量压缩格式(首个值为起点, 其余为 delta/1e6), 需解码。
"""
from .base import MapProvider
from .errors import ApiError, InvalidKeyError, QuotaExceededError, RateLimitedError

# 120:key每秒请求量达上限 121:key每日调用量达上限 122:账户每日调用量达上限
QUOTA_STATUS = {121, 122}


class TencentProvider(MapProvider):
    name = "tencent"
    display_name = "腾讯"

    def __init__(self, key, min_interval=0.15):
        super().__init__(min_interval)
        self.key = key

    @property
    def api_ready(self):
        return bool(self.key)

    @property
    def js_ready(self):
        return False

    def _check(self, data):
        status = data.get("status", -1)
        if status == 0:
            return
        msg = data.get("message", "")
        if status in (110, 111, 305, 306, 310, 311):
            raise InvalidKeyError(f"腾讯 Key 无效/受限: {status} {msg}")
        if status in QUOTA_STATUS:
            raise QuotaExceededError(f"腾讯配额耗尽: {status} {msg}")
        if status == 120:
            raise RateLimitedError(f"腾讯QPS超限: {msg}")
        raise ApiError(f"腾讯错误: {status} {msg}")

    def test_key(self):
        """返回 (ok, i18n_key 或 None, detail)。"""
        if not self.key:
            return False, "key.not_configured", ""
        try:
            data = self._get("https://apis.map.qq.com/ws/geocoder/v1/", {
                "address": "北京市", "key": self.key})
            self._check(data)
            return True, "key.valid", ""
        except QuotaExceededError:
            return True, "key.valid_quota", ""
        except RateLimitedError:
            return True, "key.valid_qps", ""
        except ApiError as e:
            return False, None, str(e)

    @staticmethod
    def _decode_polyline(raw):
        """官方解码算法: 前两个值为起点纬/经度, 之后为增量(×1e6)。"""
        coors = [float(x) for x in raw]
        kr = 1000000
        for i in range(2, len(coors)):
            coors[i] = coors[i - 2] + coors[i] / kr
        return [(coors[i], coors[i + 1]) for i in range(0, len(coors) - 1, 2)]

    def route_driving(self, o_lat, o_lng, d_lat, d_lng):
        data = self._get("https://apis.map.qq.com/ws/direction/v1/driving/", {
            "from": f"{o_lat:.6f},{o_lng:.6f}",
            "to": f"{d_lat:.6f},{d_lng:.6f}",
            "key": self.key,
        })
        self._check(data)
        try:
            route = data["result"]["routes"][0]
            points = self._decode_polyline(route["polyline"])
            return {"points": points,
                    "distance": float(route.get("distance", 0)) * 1000,  # km→m
                    "duration": float(route.get("duration", 0)) * 60}    # min→s
        except (KeyError, IndexError, ValueError, TypeError) as e:
            raise ApiError(f"腾讯路径解析失败: {e}") from e
