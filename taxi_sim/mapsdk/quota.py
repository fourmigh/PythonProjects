"""配额台账: 本地记录仅为预估, SDK 超限报错是权威(见 manager)。
首次触顶报错时, 当日已用次数即真实配额, 自动学习写入 learned_quota。
"""
from app_config import DEFAULT_QUOTAS
from data import store


class QuotaLedger:
    def __init__(self, defaults=None):
        self._defaults = defaults or DEFAULT_QUOTAS

    def limit(self, provider, api):
        learned = store.get_learned_quota(provider, api)
        return learned if learned is not None else self._defaults.get(
            (provider, api), 1000)

    def remaining(self, provider, api):
        return max(0, self.limit(provider, api) - store.quota_used(provider, api))

    def record(self, provider, api, n=1):
        store.quota_record(provider, api, n)

    def is_exhausted(self, provider, api):
        return self.remaining(provider, api) <= 0

    def mark_exhausted(self, provider, api):
        """SDK 返回超限错误时调用: 当日台账置满(次日自动恢复), 不污染学习值。"""
        used = store.quota_used(provider, api)
        if used <= 0:
            # 今日尚无成功调用: 只把当日台账置满, 保留已学习的真实配额
            store.quota_set_used(provider, api, self.limit(provider, api))
        else:
            # 今日有成功调用: 当日已用次数即真实配额, 学习之
            store.quota_set_used(provider, api, used)
            if store.get_learned_quota(provider, api) != used:
                store.learn_quota(provider, api, used)

    def snapshot(self):
        return store.quota_snapshot(self._defaults)
