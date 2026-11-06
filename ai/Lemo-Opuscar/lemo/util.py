from __future__ import annotations

import datetime as _dt
import re

_ANSI_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def timestamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def slugify(text: str, fallback: str = "film") -> str:
    lowered = text.strip().lower()
    slug = _SLUG_RE.sub("-", lowered).strip("-")
    if not slug:
        slug = fallback
    return slug[:48].strip("-") or fallback
