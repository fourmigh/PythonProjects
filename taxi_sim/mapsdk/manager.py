"""SDK 管理器: 按"剩余配额最多"自动选平台, 超限自动切换下一家, 全部耗尽返回 None。
本地台账只是预估, SDK 超限报错为权威: 触发 mark_exhausted + 自学习真实配额。
"""
import logging

from .amap import AMapProvider
from .baidu import BaiduProvider
from .base import MapProvider
from .errors import InvalidKeyError, QuotaExceededError, RateLimitedError
from .quota import QuotaLedger
from .tencent import TencentProvider

log = logging.getLogger(__name__)


class MapManager:
    def __init__(self, config):
        self.config = config
        self.ledger = QuotaLedger()
        self.providers = [
            AMapProvider(config.amap_web_key),
            TencentProvider(config.tencent_key),
            BaiduProvider(config.baidu_ak),
        ]
        # 连续QPS失败的暂时冷却
        self._cooldown = {}

    def reload_config(self):
        cfg = self.config
        for p in self.providers:
            if isinstance(p, AMapProvider):
                p.web_key = cfg.amap_web_key
            elif isinstance(p, TencentProvider):
                p.key = cfg.tencent_key
            elif isinstance(p, BaiduProvider):
                p.ak = cfg.baidu_ak

    def _candidates(self, api):
        """有 Key、有剩余配额、不在冷却中的平台, 按剩余配额降序。"""
        now = __import__("time").monotonic()
        out = []
        for p in self.providers:
            if not p.api_ready:
                continue
            if self.ledger.is_exhausted(p.name, api):
                continue
            if self._cooldown.get(p.name, 0) > now:
                continue
            out.append((self.ledger.remaining(p.name, api), p))
        out.sort(key=lambda t: -t[0])
        return [p for _, p in out]

    def route_driving(self, o_lat, o_lng, d_lat, d_lng):
        """依次尝试候选平台, 成功返回 (provider_name, result); 全部失败返回 (None, None)。"""
        last_err = None
        for p in self._candidates("route"):
            try:
                res = p.route_driving(o_lat, o_lng, d_lat, d_lng)
                self.ledger.record(p.name, "route")
                return p.name, res
            except QuotaExceededError as e:
                log.warning("%s 配额耗尽(以SDK报错为准), 切换下一家: %s", p.display_name, e)
                self.ledger.mark_exhausted(p.name, "route")
                last_err = e
            except InvalidKeyError as e:
                log.warning("%s Key无效, 跳过: %s", p.display_name, e)
                last_err = e
            except RateLimitedError as e:
                # QPS超限: 冷却10秒后本平台仍可用
                import time
                self._cooldown[p.name] = time.monotonic() + 10
                last_err = e
            except Exception as e:  # 其他错误不消耗配额, 换下一家
                log.warning("%s 调用失败: %s", p.display_name, e)
                last_err = e
        if last_err:
            log.warning("所有平台路径规划失败, 最后错误: %s", last_err)
        return None, None

    def test_key(self, provider_name):
        """透传 Provider 结果: (ok, i18n_key 或 None, detail)。"""
        for p in self.providers:
            if p.name == provider_name:
                return p.test_key()
        return False, None, "unknown provider"

    def quota_snapshot(self):
        return self.ledger.snapshot()
