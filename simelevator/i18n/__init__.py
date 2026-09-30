from __future__ import annotations

from i18n import en_US, zh_CN

_TABLES = {
    "zh_CN": zh_CN.TEXT,
    "en_US": en_US.TEXT,
}
_DEFAULT = "zh_CN"
_current = _DEFAULT
_listeners: list = []


def languages() -> list[str]:
    return list(_TABLES)


def current_language() -> str:
    return _current


def set_language(lang: str) -> None:
    global _current
    if lang not in _TABLES:
        return
    _current = lang
    for listener in list(_listeners):
        listener()


def add_listener(listener) -> None:
    if listener not in _listeners:
        _listeners.append(listener)


def remove_listener(listener) -> None:
    if listener in _listeners:
        _listeners.remove(listener)


def tr(key: str, **kwargs) -> str:
    table = _TABLES.get(_current, _TABLES[_DEFAULT])
    text = table.get(key)
    if text is None:
        text = _TABLES[_DEFAULT].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
