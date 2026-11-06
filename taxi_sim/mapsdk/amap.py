"""高德地图 Provider: Web服务路径规划 v3 + 地理编码(测试Key)。
注意: 高德坐标系 GCJ-02, origin/destination 参数为 "lng,lat"(经度在前)。
"""
from .base import MapProvider
from .errors import ApiError, InvalidKeyError, QuotaExceededError, RateLimitedError

DAILY_OVER = {"DAILY_QUERY_OVER_LIMIT", "CUQPS_HAS_EXCEEDED_THE_LIMIT",
              "DAILY_QUERY_OVER_LIMIT_,YEAR_LIMIT", "SERVICE_NOT_ACCEPTED"}
QPS_ERRORS = {"CUQPS_HAS_EXCEEDED_THE_LIMIT", "ACCESS_TOO_FREQUENT"}


class AMapProvider(MapProvider):
    name = "amap"
    display_name = "高德"

    def __init__(self, web_key, min_interval=0.35):
        super().__init__(min_interval)
        self.web_key = web_key

    @property
    def api_ready(self):
        return bool(self.web_key)

    @property
    def js_ready(self):
        return False  # JS Key 由 UI 层单独读取

    def _check(self, data):
        if data.get("status") == "1":
            return
        info = data.get("info", "")
        infocode = data.get("infocode", "")
        if infocode == "10001" or info in ("INVALID_USER_KEY", "USERKEY_PLAT_NOMATCH"):
            raise InvalidKeyError(f"高德 Key 无效: {info}")
        if info in DAILY_OVER or "OVER_LIMIT" in info:
            raise QuotaExceededError(f"高德配额耗尽: {info}")
        if info in QPS_ERRORS or "TOO_FREQUENT" in info:
            raise RateLimitedError(f"高德QPS超限: {info}")
        raise ApiError(f"高德错误: {infocode} {info}")

    def test_key(self):
        """返回 (ok, i18n_key 或 None, detail)。"""
        if not self.web_key:
            return False, "key.not_configured", ""
        try:
            data = self._get("https://restapi.amap.com/v3/geocode/geo",
                             {"key": self.web_key, "address": "北京市",
                              "city": "beijing"})
            self._check(data)
            return True, "key.valid", ""
        except QuotaExceededError:
            return True, "key.valid_quota", ""
        except RateLimitedError:
            return True, "key.valid_qps", ""
        except ApiError as e:
            return False, None, str(e)

    def route_driving(self, o_lat, o_lng, d_lat, d_lng):
        data = self._get("https://restapi.amap.com/v3/direction/driving", {
            "key": self.web_key,
            "origin": f"{o_lng:.6f},{o_lat:.6f}",
            "destination": f"{d_lng:.6f},{d_lat:.6f}",
            "extensions": "base", "strategy": "10",  # 10: 多备选, 稳定
        })
        self._check(data)
        try:
            path = data["route"]["paths"][0]
            points = []
            for step in path["steps"]:
                for pair in step["polyline"].split(";"):
                    lng_s, lat_s = pair.split(",")[:2]
                    points.append((float(lat_s), float(lng_s)))
            return {"points": points,
                    "distance": float(path.get("distance", 0)),
                    "duration": float(path.get("duration", 0))}
        except (KeyError, IndexError, ValueError) as e:
            raise ApiError(f"高德路径解析失败: {e}") from e
