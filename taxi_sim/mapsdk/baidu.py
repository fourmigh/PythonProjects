"""百度地图 Provider: 驾车路线规划 v2。
坐标系 BD-09; 请求支持 coord_type=gcj2(输入火星坐标),
返回 path 为 BD-09 "lat,lng;..." 需转换为 GCJ-02。
"""
from .base import MapProvider
from .coords import bd09_to_gcj02
from .errors import ApiError, InvalidKeyError, QuotaExceededError

QUOTA_STATUS = {4, 401, 402}  # 4: 配额校验失败


class BaiduProvider(MapProvider):
    name = "baidu"
    display_name = "百度"

    def __init__(self, ak, min_interval=0.35):
        super().__init__(min_interval)
        self.ak = ak

    @property
    def api_ready(self):
        return bool(self.ak)

    @property
    def js_ready(self):
        return False

    def _check(self, data):
        status = data.get("status", -1)
        if status == 0:
            return
        msg = data.get("message", "")
        if status in (2, 3, 6, 200, 201, 210):
            raise InvalidKeyError(f"百度 AK 无效/受限: {status} {msg}")
        if status in QUOTA_STATUS:
            raise QuotaExceededError(f"百度配额耗尽: {status} {msg}")
        raise ApiError(f"百度错误: {status} {msg}")

    def test_key(self):
        """返回 (ok, i18n_key 或 None, detail)。"""
        if not self.ak:
            return False, "key.not_configured", ""
        try:
            data = self._get("https://api.map.baidu.com/geocoding/v3/", {
                "address": "北京市", "ak": self.ak, "output": "json"})
            self._check(data)
            return True, "key.valid", ""
        except QuotaExceededError:
            return True, "key.valid_quota", ""
        except ApiError as e:
            return False, None, str(e)

    def route_driving(self, o_lat, o_lng, d_lat, d_lng):
        data = self._get("https://api.map.baidu.com/direction/v2/driving", {
            "origin": f"{o_lat:.6f},{o_lng:.6f}",
            "destination": f"{d_lat:.6f},{d_lng:.6f}",
            "coord_type": "gcj2",   # 输入GCJ-02, 返回仍为BD-09
            "ak": self.ak,
        })
        self._check(data)
        try:
            route = data["result"]["routes"][0]
            points = []
            for step in route.get("steps", []):
                path = step.get("path", "")
                for pair in path.split(";"):
                    if not pair:
                        continue
                    lat_s, lng_s = pair.split(",")[:2]
                    lng, lat = bd09_to_gcj02(float(lng_s), float(lat_s))
                    points.append((lat, lng))
            if len(points) < 2:
                raise ValueError("折线点不足")
            return {"points": points,
                    "distance": float(route.get("distance", 0)),
                    "duration": float(route.get("duration", 0))}
        except (KeyError, IndexError, ValueError) as e:
            raise ApiError(f"百度路径解析失败: {e}") from e
