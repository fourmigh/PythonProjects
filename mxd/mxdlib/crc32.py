"""CustomerCRC32：MXD 使用的 CRC32。

实验确认：crc = (~zlib.crc32(data)) & 0xFFFFFFFF，以小端 4 字节存储。
（等价于 反射式、多项式 0x04C11DB7、初值 0xFFFFFFFF、无异或输出）
"""

import zlib


def calc(data: bytes) -> int:
    return (~zlib.crc32(data)) & 0xFFFFFFFF


def calc_bytes(data: bytes) -> bytes:
    return calc(data).to_bytes(4, "little")


def check(data: bytes) -> bool:
    """校验末尾 4 字节是否为前面内容的 CRC。"""
    if len(data) < 4:
        return False
    body = data[:-4]
    expected = int.from_bytes(data[-4:], "little")
    return calc(body) == expected
