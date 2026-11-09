"""腾讯位置服务 Provider: WebService 驾车路线 v1。
坐标系 GCJ-02, from/to 参数为 "lat,lng"(纬度在前);
返回 polyline 为增量压缩格式(首个值为起点, 其余为 delta/1e6), 需解码。

若控制台开启了「签名校验」, 需同时配置 Secret Key:
每请求在参数末尾附 sig = md5(按参数名ASCII排序拼接 k=v&... + SK), 32位小写;
未配置 Secret Key 时不加 sig(未开启签名校验的 Key 用这种模式)。
"""
import hashlib
from urllib.parse import urlsplit

from .base import MapProvider
from .errors import ApiError, InvalidKeyError, QuotaExceededError, RateLimitedError

# 121:key每日调用量达上限 122:账户每日调用量达上限
QUOTA_STATUS = {121, 122}


class TencentProvider(MapProvider):
    name = "tencent"
    display_name = "腾讯"

    def __init__(self, key, secret_key="", min_interval=0.15):
        super().__init__(min_interval)
        self.key = key
        self.secret_key = secret_key

    @property
    def api_ready(self):
        return bool(self.key)

    @property
    def js_ready(self):
        return False

    # ---------------- 签名校验 ----------------

    def sign(self, url, params):
        """按腾讯签名规则追加 sig 参数(未配置 SK 则原样返回)。

        官方算法: sig = md5( 请求路径 + "?" + 参数按名升序拼接 "k=v&..." + SK )
        参数值必须是未经 URL 编码的原始值; sig 本身不参与签名。
        """
        if not self.secret_key:
            return params
        items = sorted((k, str(v)) for k, v in params.items() if k != "sig")
        query = "&".join(f"{k}={v}" for k, v in items)
        path = urlsplit(url).path or "/"
        raw = f"{path}?{query}{self.secret_key}"
        signed = dict(params)
        signed["sig"] = hashlib.md5(raw.encode("utf-8")).hexdigest()
        return signed

    def _get(self, url, params):
        return super()._get(url, self.sign(url, params))

    def _check(self, data):
        status = data.get("status", -1)
        if status == 0:
            return
        msg = data.get("message", "")
        if status == 111:
            raise InvalidKeyError(
                f"腾讯签名校验失败(111): 该 Key 开启了签名校验, "
                f"请在设置中填写 Secret Key 并确认与当前 Key 匹配 ({msg})")
        if status in (110, 112, 113):
            raise InvalidKeyError(
                f"腾讯来源/IP/功能未授权({status}): 检查 Key 的域名或IP白名单、"
                f"是否勾选 WebServiceAPI ({msg})")
        if status in (190, 199, 311):
            raise InvalidKeyError(f"腾讯 Key 无效或未开通 WebService: "
                                   f"{status} {msg}")
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
        except InvalidKeyError as e:
            # 111 是验签失败: 界面应引导用户填写 Secret Key
            return (False, "key.sig_failed", "") if "111" in str(e) \
                else (False, None, str(e))
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
