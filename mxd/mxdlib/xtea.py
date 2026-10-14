"""XTEA（文中称 TEAN）加解密。

移植自样本 tean.cs（TeanDecoder / TeanEncoder）：
  - 32 轮，delta = 0x9E3779B9，小端 32 位运算
  - 密钥为 16 字节（按小端拆成 4 个 uint32）
  - 不足 8 字节的分组用 0x20（空格）补齐
"""

import struct

DELTA = 0x9E3779B9
MASK = 0xFFFFFFFF


def _key_words(key: bytes):
    key = key[:16]
    if len(key) < 16:
        key = key + b"\x00" * (16 - len(key))
    return struct.unpack("<4I", key)


def _pad_block(block: bytes) -> bytes:
    if len(block) < 8:
        return block + b"\x20" * (8 - len(block))
    return block


def encrypt(data: bytes, key: bytes) -> bytes:
    k = _key_words(key)
    out = bytearray()
    for off in range(0, len(data), 8):
        block = _pad_block(data[off:off + 8])
        y, z = struct.unpack("<2I", block)
        s = 0
        for _ in range(32):
            y = (y + ((((z << 4) ^ (z >> 5)) + (z ^ s) + k[s & 3]) & MASK)) & MASK
            s = (s + DELTA) & MASK
            z = (z + ((((y << 4) ^ (y >> 5)) + (y ^ s) + k[(s >> 11) & 3]) & MASK)) & MASK
        out += struct.pack("<2I", y, z)
    return bytes(out)


def decrypt(data: bytes, key: bytes) -> bytes:
    k = _key_words(key)
    out = bytearray()
    for off in range(0, len(data), 8):
        block = _pad_block(data[off:off + 8])
        y, z = struct.unpack("<2I", block)
        s = (DELTA * 32) & MASK
        for _ in range(32):
            z = (z - ((((y << 4) ^ (y >> 5)) + (y ^ s) + k[(s >> 11) & 3]) & MASK)) & MASK
            s = (s - DELTA) & MASK
            y = (y - ((((z << 4) ^ (z >> 5)) + (z ^ s) + k[s & 3]) & MASK)) & MASK
        out += struct.pack("<2I", y, z)
    return bytes(out)
