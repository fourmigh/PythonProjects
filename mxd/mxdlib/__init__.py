"""mxdlib - Python 实现的 MXD 文件（Metric Extensible Data）解析与生成库。

当前版本聚焦 DKL（Dallas Key List）文件的解析与生成，
核心算法均依据 doc/MXD File Format.doc、Kotlin 源码与样本文件实验确认。
"""

from .errors import MXDError
from .dkl import DKL, KeyGroup, KeyEntry, AccessTime, Time, HourMinute
from .dallas import (dallas_key_to_dkl_key, dkl_key_to_dallas_key,
                     dallas_crc8, is_valid_dallas_key)

__all__ = [
    "MXDError",
    "DKL",
    "KeyGroup",
    "KeyEntry",
    "AccessTime",
    "Time",
    "HourMinute",
    "dallas_key_to_dkl_key",
    "dkl_key_to_dallas_key",
    "dallas_crc8",
    "is_valid_dallas_key",
]

__version__ = "0.1.0"
