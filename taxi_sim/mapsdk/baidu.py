"""百度地图 Provider: 驾车路线规划 v2。
坐标系 BD-09; 请求支持 coord_type=gcj02(输入火星坐标),
返回 path 为 BD-09 "lat,lng;..." 需转换为 GCJ-02。

服务端 AK 的鉴权方式二选一: IP 白名单 或 SN 签名校验。
开启 SN 时需配置 SK, 每请求追加 sn:
  sn = md5( urlencode( path + "?" + "k=v&..."(各value已urlencode) + SK ) )
即"双重 urlencode", 32 位小写; sn 必须作为最后一个参数。
"""
import hashlib
from urllib.parse import quote, urlsplit

from .base import MapProvider
from .coords import bd09_to_gcj02
from .errors import ApiError, InvalidKeyError, QuotaExceededError

QUOTA_STATUS = {4, 401, 402}  # 4: 配额校验失败


class BaiduProvider(MapProvider):
    name = "baidu"
    display_name = "百度"

    def __init__(self, ak, sk="", min_interval=0.35):
        super().__init__(min_interval)
        self.ak = ak
        self.sk = sk

    @property
    def api_ready(self):
        return bool(self.ak)

    @property
    def js_ready(self):
        return False

    # ---------------- SN 校验 ----------------

    def sign(self, url, params):
        """按百度 SN 规则追加 sn 参数(未配置 SK 则原样返回)。

        官方算法(GET): 参数保持请求顺序, value 各自 urlencode;
        拼成 path + "?" + query + SK 后再整体 urlencode, 取 md5 小写。
        sn 必须放在参数最后。
        """
        if not self.sk:
            return params
        query = "&".join(f"{k}={quote(str(v), safe='')}"
                         for k, v in params.items() if k != "sn")
        path = urlsplit(url).path
        whole = f"{path}?{query}{self.sk}"
        signed = dict(params)
        signed["sn"] = hashlib.md5(quote(whole, safe="").encode()).hexdigest()
        return signed

    def _get(self, url, params):
        return super()._get(url, self.sign(url, params))

    def _check(self, data):
        status = data.get("status", -1)
        if status == 0:
            return
        msg = data.get("message", "")
        if status == 211:
            raise InvalidKeyError(
                f"百度 SN 校验失败(211): 该 AK 选择了 SN 校验方式, "
                f"请填写与之一对的 SK (或改回 IP 白名单方式) ({msg})")
        if status == 210:
            raise InvalidKeyError(
                f"百度 IP 校验失败(210): 请求 IP 不在 AK 白名单, "
                f"请添加本机公网 IP 或改为 SN 校验 ({msg})")
        if status in (2, 3, 5, 6, 200, 201):
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
        except InvalidKeyError as e:
            # 211 是 SN 验签失败: 界面应引导用户填写 SK
            return (False, "key.sn_failed", "") if "211" in str(e) \
                else (False, None, str(e))
        except ApiError as e:
            return False, None, str(e)

    def route_driving(self, o_lat, o_lng, d_lat, d_lng):
        data = self._get("https://api.map.baidu.com/direction/v2/driving", {
            "origin": f"{o_lat:.6f},{o_lng:.6f}",
            "destination": f"{d_lat:.6f},{d_lng:.6f}",
            "coord_type": "gcj02",  # 输入GCJ-02, 返回仍为BD-09
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
                    # 百度 path 点串顺序为 "lng,lat"(经度在前)
                    lng_s, lat_s = pair.split(",")[:2]
                    lng, lat = bd09_to_gcj02(float(lng_s), float(lat_s))
                    points.append((lat, lng))
            if len(points) < 2:
                raise ValueError("折线点不足")
            return {"points": points,
                    "distance": float(route.get("distance", 0)),
                    "duration": float(route.get("duration", 0))}
        except (KeyError, IndexError, ValueError) as e:
            raise ApiError(f"百度路径解析失败: {e}") from e
