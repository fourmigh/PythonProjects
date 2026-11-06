"""国际化层: 代码中只引用 key, 文案全部在 i18n/zh_CN.py / en_US.py。
用法: from i18n import t; t("btn.start") / t("engine.start", city=..., n=...)
"""
_CURRENT = "zh_CN"
SUPPORTED = ("zh_CN", "en_US")


def set_language(lang):
    global _CURRENT
    if lang in SUPPORTED:
        _CURRENT = lang


def current_language():
    return _CURRENT


def t(key, **kwargs):
    from i18n import zh_CN, en_US
    tables = {"zh_CN": zh_CN.STRINGS, "en_US": en_US.STRINGS}
    s = tables[_CURRENT].get(key) or zh_CN.STRINGS.get(key)
    if s is None:
        return key
    return s.format(**kwargs) if kwargs else s
